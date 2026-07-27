<a id="erdos-257-mersenne-support-subseries"></a>

# Forced Structure in Mersenne Subseries

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Erdős #257 asks whether $`X_A=\sum_{a\in A}(2^a-1)^{-1}`$ is irrational for every infinite $`A\subseteq\mathbb{N}_{>0}`$. It is open. Writing $`\operatorname{sc}_A(n)`$ for the number of divisors of $`n`$ lying in $`A`$, one has $`X_A=\sum_{n\ge1}\operatorname{sc}_A(n)2^{-n}`$, and every argument below reads the divisor-incidence sequence $`\operatorname{sc}_A`$ rather than $`A`$.

For *finite* supports the position is exact. For every finite nonempty $`F\subseteq\mathbb{N}_{>0}`$ and every integer $`b\ge2`$, the multiplicative order of $`b`$ modulo the reduced denominator of $`\sum_{n\in F}(b^n-1)^{-1}`$ is exactly $`\operatorname{lcm}(F)`$, and that denominator strictly exceeds $`\operatorname{lcm}(F)`$.

For *infinite* supports we record what rationality would force on an arbitrary $`A`$, which is the part of this development that meets the universal quantifier rather than sampling it. A rational value is equivalent to a tempered integer carry orbit; for infinite $`A`$ that orbit is unbounded; the zero windows of $`\operatorname{sc}_A`$ then have length at most $`\varepsilon\log_2 N+O(1)`$ uniformly in $`A`$; a summable support has reciprocal mass at least $`1/\operatorname{ord}_v(2)`$; and rational values correspond exactly to Boolean–Möbius carry certificates, from which the support is reconstructed rather than guessed. These are necessary conditions on a counterexample. Jointly they are not yet contradictory, and we do not present them as progress towards the universal statement.

Finally we correct a frontier this note previously misreported. The squarefree support was listed here as open; Duverney and Tachiya settled it at base $`2`$ in 2019. Its divisor incidence $`2^{\omega(n)}-1`$ is odd for every $`n\ge2`$, so the two block-certificate engines that require first-block divisibility provably have no instance at any even base; at $`b=2`$, where the value is now known to be irrational, that exhibits both engines failing on a settled value. Adjoining $`1`$ to the support changes the value by the rational $`1/(b-1)`$ and the incidence by one, so the obstruction is a property of a normalisation and not of the value. Rationality is in fact invariant under every finite change of support, which is the general form of that observation.

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

<a id="sec:problem"></a>

# The problem and its coordinate

<div id="res:problem" class="problem">

**Problem 1** (Erdős \#257). For every infinite $`A\subseteq\mathbb{N}_{>0}`$, is $`X_A=\sum_{a\in A}\dfrac1{2^a-1}`$ irrational?

</div>

Numbering and status follow [Bloom’s catalogue](https://www.erdosproblems.com/257). Write $`w_{n}=(2^n-1)^{-1}`$. Expanding each weight as a geometric series and interchanging the two nonnegative sums gives the coordinate this note works in. With the *divisor incidence* $`\operatorname{sc}_A(n)=\#\{d\mid n: d\in A\}`$,
``` math
X_A=\sum_{a\in A}\frac1{2^a-1}=\sum_{n\ge1}\frac{\operatorname{sc}_A(n)}{2^n}.
  \tag{1}\label{eq:incidence}
```
The transform is worth reading carefully, because it is where the arithmetic of the problem enters. The datum is a $`0/1`$ selector, the indicator of $`A`$; what appears in <a href="#eq:incidence" data-reference-type="eqref" data-reference="eq:incidence">[eq:incidence]</a> is not that selector but its divisor transform, a nonnegative integer sequence bounded by the divisor function, $`\operatorname{sc}_A(n)\le d(n)`$. So \#257 is not a generic question about binary digit sequences. Its constraint is that the coefficients of the binary expansion are divisor counts drawn from a single support, and every theorem below is a statement about sequences of that shape.

<a id="sec:period"></a>

# Exact periods of finite partial sums

For a finite nonempty $`F\subseteq\mathbb{N}_{>0}`$ and an integer $`b\ge2`$, write
``` math
x_F(b)=\sum_{n\in F}\frac1{b^n-1}=\frac{N_F}{D_F}
  \qquad (\gcd(N_F,D_F)=1,\ D_F>0).
```

<div id="res:period" class="theorem">

**Theorem 2** (finite-period noncollapse). *The reduced denominator is coprime to $`b`$, and
``` math
\operatorname{ord}_{D_F}(b)=\operatorname{lcm}\{n:n\in F\}.
```
If moreover $`\operatorname{lcm}(F)\ge2`$, then $`\operatorname{lcm}(F)<D_F`$.*

</div>

The order statement is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L5091), its reduced-denominator form is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L5246), coprimality is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L5221), and the growth clause is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L5260).

The content is a noncollapse statement. Clearing denominators over $`b^{\operatorname{lcm}(F)}-1`$ makes the period at most $`\operatorname{lcm}(F)`$ immediately; what is not immediate is that cancellation in the numerator cannot bring it below. The mechanism is that each selected exponent $`n`$ contributes, by the cyclotomic route, a prime-power modulus dividing $`b^{n}-1`$ on which $`b`$ has order exactly $`n`$; no single reduction can remove all of them at once. Prime powers rather than primes is not a technicality. At $`(b,n)=(2,6)`$ no prime divisor of $`2^6-1=63`$ has order $`6`$ — the Zsigmondy exception — while $`9`$ does, and it is the prime power that carries the witness. The growth clause then follows formally, since the order divides $`\varphi(D_F)<D_F`$.

Two boundaries. This is an unconditional statement about every finite support, not a bounded table of examples, and not an implication with an open hypothesis; but it settles no infinite support, and no limit of it does. Denominator-period control is part of the classical engine behind Erdős’s 1948 argument \[erdos1948\]. Whether this exact sharp form appears in the literature has not been assessed, and no novelty is claimed.

<a id="sec:forced"></a>

# What a rational value would force

The families of Section <a href="#sec:map" data-reference-type="ref" data-reference="sec:map">4</a> are supports for which irrationality is known. This section is the other half, and the half that meets Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> rather than sampling it: statements that hold for *every* infinite support whose value is rational. Fix base $`2`$ and suppose throughout that $`A\subseteq\mathbb{N}_{>0}`$ has $`X_A\in\mathbb{Q}`$.

<a id="a-carry-orbit-and-it-is-unbounded."></a>

#### A carry orbit, and it is unbounded.

Binary long division turns a hypothetical rational value into an integer recurrence. For any coefficient sequence with $`c(n)\le n`$ — and $`\operatorname{sc}_A(n)\le d(n)\le n`$ qualifies — the series $`\sum c(n)2^{-n}`$ is rational exactly when a *tempered* integer carry orbit exists, and every such orbit is then the scaled tail, so the orbit is unique rather than merely available ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/GenericTailOrbitRigidity.lean#L425)).

<div id="res:unbounded" class="theorem">

**Theorem 3** (unbounded carry states). *Let $`A`$ be infinite with $`X_A=p/(2^cv)`$, $`v\ge1`$. Then there is $`u\colon\mathbb{N}\to\mathbb{N}_{>0}`$ with $`u(n)=v\cdot(\text{binary tail of }\operatorname{sc}_A\text{ at }c+n)`$ satisfying the exact recurrence
``` math
u(n+1)+v\,\operatorname{sc}_A(c+n+1)=2u(n),
  \qquad u(n)\equiv p\,2^{n}\ (\mathrm{mod}\ v),
```
and $`u`$ is unbounded.*

</div>

Checked as [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/RationalSupportCarrySkeleton.lean#L2377). The unboundedness is the useful clause: it closes every finite-state reading of the carry system. A counterexample to Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> cannot be one whose carry dynamics eventually cycle through a bounded set of states.

<a id="divisor-coverage-cannot-have-long-gaps."></a>

#### Divisor coverage cannot have long gaps.

Say that $`\operatorname{sc}_A`$ has a *zero window* of length $`h`$ at $`N`$ if $`\operatorname{sc}_A(N+1)=\dots=\operatorname{sc}_A(N+h)=0`$, that is, if no element of $`A`$ divides any of $`h`$ consecutive integers.

<div id="res:sublog" class="theorem">

**Theorem 4** (sublogarithmic zero windows). *Let $`A`$ be nonempty with $`X_A=p/(2^cv)`$, $`v\ge1`$. For every $`\varepsilon>0`$ there is a constant $`B`$, depending only on $`\varepsilon`$, $`c`$ and $`v`$, such that every zero window of $`\operatorname{sc}_A`$ at $`c+N`$ has length
``` math
h\le\varepsilon\log_2(N+1)+B .
```
The bound is uniform in the support $`A`$, in the numerator $`p`$, and in $`N`$ and $`h`$.*

</div>

Checked as [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/SublogDivisorCoverage.lean#L392). Read as a constraint on counterexamples, this says a rational-valued support must divide into the integers densely: its divisor coverage may not be absent across a run of length even $`\varepsilon\log_2N`$, for arbitrarily small $`\varepsilon`$, once $`N`$ is large. The proof compares an exponential lower bound forced on the tail by the carry recurrence with a subpower envelope for divisor sums.

<a id="reciprocal-mass."></a>

#### Reciprocal mass.

Let $`\operatorname{ord}_v(2)`$ denote the multiplicative order of $`2`$ modulo an odd $`v>1`$, and write the reciprocal mass of $`A`$ for $`\sum_{a\in A}1/a`$.

<div id="res:mass" class="theorem">

**Theorem 5** (reciprocal mass bound). *Suppose $`\sum_{a\in A}1/a`$ converges, $`X_A=p/(2^cv)`$ with $`v>1`$ odd and $`\gcd(p,v)=1`$. Then
``` math
\sum_{a\in A}\frac1a\;\ge\;\frac1{\operatorname{ord}_v(2)} .
```*

</div>

Checked as [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/RationalSupportCarrySkeleton.lean#L1478). The summability hypothesis is doing real work: the theorem says that a rational value with odd denominator part $`v`$ is available only to supports that are either thick enough to have reciprocal mass at least $`1/\operatorname{ord}_v(2)`$, or thick enough for the reciprocal sum to diverge outright. It does not bound $`\operatorname{ord}_v(2)`$, so it does not by itself exclude anything; it constrains the pair (support, denominator) jointly.

<a id="rational-values-are-exactly-booleanmöbius-carry-certificates."></a>

#### Rational values are exactly Boolean–Möbius carry certificates.

The four statements above are consequences. The next is an equivalence, and is the sharpest description of rational-valued supports the development has.

<div id="res:bmc" class="theorem">

**Theorem 6** (Boolean–Möbius carry correspondence). *Let $`p\in\mathbb{Z}`$ and $`q\ge1`$. There exists a support $`A`$ with $`0\notin A`$, with some positive element, and with $`X_A=p/q`$, if and only if there exists an integer orbit $`U\colon\mathbb{N}\to\mathbb{Z}`$ carrying a Boolean–Möbius carry certificate for $`(p,q)`$. In that case the support is not guessed: it is recovered as
``` math
A=\{n:(\mu*Q_U)(n)=1\},
```
where $`Q_U`$ is the carry quotient of $`U`$.*

</div>

Checked as [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/BooleanMobiusCarry.lean#L948). The certificate asks for a positive orbit obeying the carry recurrence, with a square-root growth bound, whose Möbius quotient takes only the values $`0`$ and $`1`$. That Boolean condition is exactly the statement that the quotient is the indicator of a set, and Möbius inversion then returns that set. So the search for a rational-valued Mersenne subseries is, without loss, a search for one integer orbit with a divisibility-flavoured Boolean condition.

<a id="what-this-does-and-does-not-amount-to."></a>

#### What this does and does not amount to.

Taken together: a counterexample to Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> would have an unbounded carry orbit obeying an exact linear recurrence, sublogarithmic divisor-coverage gaps uniformly in the support, reciprocal mass bounded below or divergent, and an exact Boolean–Möbius certificate reconstructing it. Each of these is a genuine restriction, and unlike the family list of Section <a href="#sec:map" data-reference-type="ref" data-reference="sec:map">4</a> each quantifies over all infinite supports. None is a contradiction, and no two of them have been shown to be jointly unsatisfiable. We state them because they are the shape of the remaining problem, not because they narrow it.

<a id="sec:map"></a>

# The settled supports, by mechanism

The supports for which irrationality is known are more usefully grouped by the argument that reaches them than counted. There are five mechanisms.

| Support $`A`$ | Bases | Mechanism and authority |
|:---|:---|:---|
|  |  |  |
| all of $`\mathbb{N}_{>0}`$ | every $`b\ge2`$ | Erdős 1948 \[erdos1948\]; [formalised here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L8717) |
| multiples of a fixed $`d`$ | every $`b\ge2`$ | dilation: the multiples series at base $`b`$ *is* the full-support series at base $`b^d`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L8775)) |
|  |  |  |
| eventually periodic | every $`b\ge2`$ | [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L11276); Luca–Tachiya prove a broader periodic theorem \[lucatachiya\] |
| a residue class; the odd numbers | every $`b\ge2`$ | special cases of the row above ([residue class](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L11344), [odd](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L11358)) |
|  |  |  |
| factorials $`\{n!\}`$ | every $`b\ge2`$ | [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L5707) |
| powers of two $`\{2^k\}`$ | every $`b\ge2`$ | [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L5731) |
| pairwise coprime, $`\sum_{a\in A}a^{-1}<\infty`$ | every $`b\ge2`$ | [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L10448) |
|  |  |  |
| squarefree | $`b=2`$ only | Duverney–Tachiya \[duverneytachiya\], Cor. 1.2 with $`F_2(P)`$ and Ex. 1.1; not formalised here |
| coprime to a fixed $`N`$; sums of two squares | every $`b\ge2`$ | *ibid.*, Examples 1.3 and 1.2; not formalised here |
|  |  |  |
| primes | $`b=2`$ proved | Tao–Teräväinen \[taoteravainen2025\], Thm. 1.3; not formalised here |
| primes, $`b\ge3`$; prime powers | — | *ibid.*, asserted as modifications with the details left to the reader; not proved there |
| arbitrary infinite $`A`$ | — | **Open** (Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a>) |

Four remarks, each correcting something an earlier draft of this note got wrong or left unsaid.

*The mechanisms are not nested, and one non-containment is proved.* The base-$`b`$ full-support theorem is exactly the $`A=\mathbb{N}_{>0}`$ statement; the multiples rows genuinely specialise it after a base change, but the sparse rows do not, and this is not merely an artefact of how they were proved. The denominator-gap criterion behind the factorial and power-of-two rows *provably cannot* reach the full support: the prefix lcm grows too slowly for its hypothesis to hold ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L5944)). Conversely the analytic method of \[taoteravainen2025\] reaches the primes, which are neither eventually periodic nor pairwise coprime with summable reciprocals. No list contains another, and their union does not exhaust the infinite supports.

*Duverney and Tachiya belong in this table, and were missing from it.* Their refinement of the Chowla–Erdős method \[duverneytachiya\] proves, for a pairwise coprime sequence $`E`$ of polynomial growth and the set $`F_s(E)`$ of products of its members with exponents below $`s`$, that $`1`$ and the values $`\sum_{n\in F_s}(q^{jn^i}-1)^{-1}`$ are linearly independent over $`\mathbb{Q}`$ whenever $`|q|^{L}\le s`$, with $`L=\operatorname{lcm}(1,\dots,\ell)`$. This is a row-generating theorem, not an isolated example: with $`E`$ the primes, $`s=\infty`$ returns the full support at every base, while $`s=2`$ returns the squarefree support. The constraint is what confines the squarefree case to base $`2`$, and it is sharp in an unusually rigid way: $`s=2`$ forces $`\ell=1`$ and then $`|q|\le2`$, so no integer base $`b\ge3`$ and no higher index $`i\ge2`$ is reachable for that support by this route. Their conclusion is also stronger than irrationality, being linear independence of a whole family. We had cited none of this.

*The two analytic rows do not have the same standing.* Theorem 1.3 of \[taoteravainen2025\] proves the prime-support case at base $`2`$, the series there being $`\sum_{n\ge1}\omega(n)/2^n`$. The extension to every integer base, and the prime-power support — which those authors themselves identify with Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> — are asserted by remark, with the modifications explicitly left to the reader. Printing all three at one tier, as this note previously did, overstated two of them.

*Formalisation is not priority.* Rows marked “checked here” are Lean statements accepted by the pinned kernel. For the full support that is a formalisation of Erdős; for eventually periodic supports Luca and Tachiya prove a broader theorem by other methods. No priority is claimed anywhere in this table.

<div id="res:signed" class="remark">

*Remark 1* (signed periodic weights: a gap in the method, not in the mathematics). Dropping nonnegativity weakens what the certificate machinery returns, and it is worth being exact about where. For $`u\colon\mathbb{N}_{>0}\to\mathbb{Z}`$ periodic and $`b\ge2`$, what is checked here is a *dichotomy*: the series $`\sum_{n\ge1}u(n)/(b^n-1)`$ is irrational, *or* some power of $`b`$ times its value is an integer ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L13847)). For a nonnegative support indicator the terminating alternative is excluded by the rows above; for mixed signs this argument does not exclude it.

The terminating alternative never in fact occurs. Luca and Tachiya’s Theorem 1.1 gives outright irrationality of $`\sum_{n\ge1}a_n/(q^n-1)`$ for every integer $`q`$ with $`|q|>1`$ and every eventually periodic rational sequence $`(a_n)`$ that is not eventually zero \[lucatachiya\], and a nonzero periodic integer weight satisfies that hypothesis automatically, since a nonzero value recurs. So the disjunction above is an artefact of the route taken, not a feature of the problem: the second branch is empty, and their theorem is what shows it. The local statement retains only the interest of being an independently checked argument with a visible boundary. Section <a href="#sec:squarefree" data-reference-type="ref" data-reference="sec:squarefree">5</a> records a second, sharper instance of the same phenomenon.

</div>

<a id="sec:squarefree"></a>

# A removable obstruction: the squarefree support

Let $`A_{\mathrm{sf}}=\{d\ge2: d\text{ squarefree}\}`$: a support of density $`6/\pi^2`$, far denser than the primes, and not periodic. An earlier version of this note listed its value as open and asked for help deciding it. That was wrong, and the correction is the point of this section.

<div id="res:sfcount" class="theorem">

**Theorem 7** (squarefree divisor incidence). *For every $`n\ge1`$ the number of squarefree divisors of $`n`$ is $`2^{\omega(n)}`$, where $`\omega(n)`$ is the number of distinct prime factors, and hence
``` math
\operatorname{sc}_{A_{\mathrm{sf}}}(n)=2^{\omega(n)}-1 .
```
In particular $`\operatorname{sc}_{A_{\mathrm{sf}}}(n)`$ is *odd* for every $`n\ge2`$.*

</div>

The count is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L53), the incidence formula is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L70), and the parity conclusion is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L100). The proof is the bijection between squarefree divisors of $`n`$ and subsets of its prime factors ([Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L30)), so the count is $`2^{\omega(n)}`$; removing $`d=1`$ leaves an odd number whenever $`\omega(n)\ge1`$.

<a id="the-value-is-known-at-base-2"></a>

## The value is known, at base 2

Duverney and Tachiya’s Corollary 1.2, applied with $`E`$ the primes, $`s=2`$ and $`\ell=1`$, gives $`L=\operatorname{lcm}(1)=1`$ and the admissibility condition $`|q|\le2`$. At $`q=2`$ their Example 1.1 reads: the numbers
``` math
1,\quad \sum_{n\ge1}\frac{|\mu(n)|}{2^n-1},\quad
  \sum_{n\ge1}\frac{|\mu(n)|}{2^{2n}-1},\quad\dots
```
are linearly independent over $`\mathbb{Q}`$ \[duverneytachiya\]. Since $`|\mu|`$ is the indicator of the squarefree integers including $`n=1`$, and $`A_{\mathrm{sf}}`$ omits only $`n=1`$, whose weight is $`1/(2^1-1)=1`$,
``` math
X_{A_{\mathrm{sf}}}
  =\sum_{n\ge1}\frac{|\mu(n)|}{2^n-1}-1 ,
```
and linear independence of $`1`$ and the first sum makes both irrational.

<div id="res:sfsettled" class="corollary">

**Corollary 8**. *$`X_{A_{\mathrm{sf}}}=\sum_{d\ \mathrm{squarefree},\ d\ge2}(2^d-1)^{-1}`$ is irrational.*

</div>

Two boundaries on that. It is a citation, not a formalisation: nothing in this development proves it. And it is base $`2`$ only. The admissibility condition $`|q|^L\le s`$ fails at $`s=2`$ for every $`|q|\ge3`$, so the squarefree support at bases $`b\ge3`$ is not covered by their corollary and remains, as far as we know, open.

<a id="two-certificate-engines-are-nevertheless-blind-to-it"></a>

## Two certificate engines are nevertheless blind to it

The development reaches its infinite supports through block certificates. Two of the engines share a first-block divisibility condition, and the parity of Theorem <a href="#res:sfcount" data-reference-type="ref" data-reference="res:sfcount">7</a> refutes it outright.

<div id="res:blind" class="corollary">

**Corollary 9** (both divisibility-first engines have no instance). *For the squarefree support and every even base $`b\ge2`$, neither the digitwise nor the carry-aware block-certificate hypothesis holds. Both fail already at precision $`q=b^2`$.*

</div>

<div class="proof">

*Proof.* Both engines ask, for every precision $`q`$, for $`N`$, $`K\le L`$ and $`C`$ with a first-block condition on $`\operatorname{sc}_{A_{\mathrm{sf}}}(N+1),\dots,\operatorname{sc}_{A_{\mathrm{sf}}}(N+K)`$, a middle bound $`\sum_{r=K+1}^{L}\operatorname{sc}_{A_{\mathrm{sf}}}(N+r)b^{L-r}\le C`$, a nonzero coefficient beyond $`N+L`$, and $`q(C+N+L+2)<b^{L}`$. Take $`q=b^2`$ and write $`f=\operatorname{sc}_{A_{\mathrm{sf}}}`$.

Suppose $`K\ge1`$. The digitwise condition requires $`b^{r}\mid f(N+r)`$ for $`1\le r\le K`$; at $`r=1`$ this makes the even number $`b`$ divide the odd number $`f(N+1)`$. The carry-aware condition requires $`b^{K}\mid\sum_{r=1}^{K}f(N+r)b^{K-r}`$; reducing modulo $`b`$ kills every term but $`r=K`$, so again $`b\mid f(N+K)`$. Either way Theorem <a href="#res:sfcount" data-reference-type="ref" data-reference="res:sfcount">7</a> is contradicted, since $`N+r\ge2`$.

Suppose $`K=0`$, where both first-block conditions are vacuous. If $`L=0`$ the middle sum is empty and $`q(C+N+2)<b^{0}=1`$ is impossible. If $`L\ge1`$ the $`r=1`$ term of the middle sum is $`f(N+1)b^{L-1}\ge b^{L-1}`$, since $`f(m)=2^{\omega(m)}-1\ge1`$ for every $`m\ge2`$ by Theorem <a href="#res:sfcount" data-reference-type="ref" data-reference="res:sfcount">7</a>, so $`C\ge b^{L-1}`$ and therefore $`q(C+N+L+2)\ge b^{2}\cdot b^{L-1}=b^{L+1}>b^{L}`$. ◻

</div>

This is an argument in the prose, drawn from the checked incidence and parity lemmas, and is marked as such in *Statements and declarations*.

<a id="the-obstruction-is-a-normalisation-not-the-value"></a>

## The obstruction is a normalisation, not the value

Corollary <a href="#res:blind" data-reference-type="ref" data-reference="res:blind">9</a> is now a statement about two engines failing on a value that Corollary <a href="#res:sfsettled" data-reference-type="ref" data-reference="res:sfsettled">8</a> shows to be irrational. So the interesting question is not whether the value can be reached, but what the failure is a property *of*. It is a property of where the support starts.

Adjoin $`1`$ to the support and write $`A_{\mathrm{sf}}^{+}=A_{\mathrm{sf}}\cup\{1\}`$, the full squarefree support. Then
``` math
X_{A_{\mathrm{sf}}^{+}}(b)-X_{A_{\mathrm{sf}}}(b)=\frac1{b-1}\in\mathbb{Q},
```
so the two supports pose the same irrationality question at every base, while the divisor incidence changes from $`2^{\omega(n)}-1`$ to $`2^{\omega(n)}`$ — from odd to even at every $`n\ge2`$. The parity obstruction of Corollary <a href="#res:blind" data-reference-type="ref" data-reference="res:blind">9</a> evaporates under a shift that provably cannot change the answer. Better: the shifted first-block condition at base $`2`$ asks for $`2^{r}\mid 2^{\omega(N+r)}`$, that is $`\omega(N+r)\ge r`$ for $`1\le r\le K`$, and a Chinese-remainder construction reserving $`r`$ fresh primes for each shift $`r`$ supplies such an $`N`$ for every $`K`$.

We are deliberate about what follows. It does *not* follow that either engine certifies the shifted support: the opening block is one of three conditions, and the middle bound and the arithmetic inequality are untouched by this observation. What does follow is a methodological point worth more than the original corollary was: an obstruction stated against a coefficient sequence can be an artefact of the normalisation chosen for that sequence. Before a no-go result is reported as a property of a problem, the coordinate it is stated in should be varied by a transformation the problem is known to be invariant under. Here the transformation is adding one rational number, and it removes the obstruction entirely.

The same invariance holds for every finite change, not only this one. If $`A\mathbin{\triangle}B`$ is finite, choose $`M`$ above all of its elements. The two support series then have the same tail beyond $`M`$, while each omitted prefix is rational. The two directions of this argument are exactly the checked prefix lemmas [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L9139) and [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/CertificateKernel.lean#L9148). Thus $`X_A(b)`$ is irrational if and only if $`X_B(b)`$ is irrational for every integer $`b\ge2`$. The present shift is the smallest instance of a general checked finite-change principle.

This is the second time in this note that a boundary turns out to belong to the method rather than to the mathematics. In Remark <a href="#res:signed" data-reference-type="ref" data-reference="res:signed">1</a> the terminating alternative of the signed periodic dichotomy is empty, and a theorem of Luca and Tachiya is what shows it; here a parity obstruction survives only until the support is shifted by one element. Both were originally written up as frontiers. Neither was one, and in each case the correction came from outside the development — once from the literature, once from asking what the statement was invariant under. A formalised no-go result carries exactly the authority of its hypotheses, and its hypotheses include the coordinates it was written in.

<a id="sec:geometry"></a>

# Achievement-set geometry and the value $`1/2`$

The set of all values obtainable from the base-$`2`$ Mersenne weights is the achievement set $`\mathcal A=\{\sum_{n\ge1}\varepsilon_nw_{n}:\varepsilon_n\in\{0,1\}\}`$.

<div id="res:geometry" class="theorem">

**Theorem 10** (geometry of $`\mathcal A`$). *$`\mathcal A`$ is compact, perfect, totally disconnected and nowhere dense, and has Lebesgue measure $`1`$.*

</div>

Checked as [compact](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/GreedyAchievementSet.lean#L656), [perfect](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/GreedyAchievementSet.lean#L1620), [totally disconnected](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/GreedyAchievementSet.lean#L1636), [nowhere dense](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/GreedyAchievementSet.lean#L1645), and [of measure one](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/GreedyAchievementSet.lean#L996). So $`\mathcal A`$ is a fat Cantor set: strict tail domination $`\sum_{\ell>n}w_{\ell}<w_{n}`$ opens a gap at every level, while the total measure is not lost. The division of credit is exact. The strict inequality, the resulting distinctness of subsums over distinct supports, and the Cantor conclusion are Remark 4.1 of Kovač and Tao \[kovactao\]; no novelty is claimed for any of the three. That remark makes no metric assertion, and strict tail domination does not determine the measure: the weights $`3^{-n}`$ satisfy $`\sum_{\ell>n}3^{-\ell}=3^{-n}/2<3^{-n}`$ and produce a null achievement set, the base-$`3`$ digits-in-$`\{0,1\}`$ Cantor set. So the measure-one clause is added here rather than formalised from there, and it is the arithmetic of the Mersenne weights that supplies it. With $`T_n=\sum_{k>n}w_{k}`$, the standard level-$`n`$ convex-hull cover consists of $`2^n`$ disjoint intervals of length $`T_n`$, its nested intersection is $`\mathcal A`$, and
``` math
2^nT_n=\sum_{j\ge1}\frac{2^n}{2^{n+j}-1}\longrightarrow\sum_{j\ge1}2^{-j}=1,
```
dominated by $`2^{1-j}`$. Continuity of measure from above therefore gives $`\lambda(\mathcal A)=1`$.

Membership is equivalent to survival of the greedy expansion at every level ([Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/GreedyAchievementSet.lean#L1445)), and exact rational death certificates prove non-membership: $`3/4\notin\mathcal A`$ ([Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/GreedyAchievementSet.lean#L1748)).

The coding is also hereditary, which matters because Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> quantifies over every infinite support rather than over $`\mathbb{N}_{>0}`$. For a set $`J`$ of future offsets write $`T_J(n)=\sum_{k\in J}w_{n+k+1}`$ for the tail restricted to $`J`$ ([definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L17), summable at [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L21)). Then $`T_J(n)<w_{n}`$ for every $`J`$ and every $`n\ge1`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L27)), since deleting weights only shrinks a tail that already sits below $`w_{n}`$ at the full support. Consequently the digit map is injective on strings supported in $`J`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L51)), stated on the subtype of [digit strings vanishing off $`J`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L42) and evaluated by the [restricted digit map](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L46), so the statement is about the subseries itself and not a projection of the full one. So unique binary coding survives passing to an arbitrary subfamily, and no counterexample can be obtained by weakening the coding. That is a constraint on the shape of an argument, not on the supports: it decides no value, and it is weaker than any statement in Section <a href="#sec:forced" data-reference-type="ref" data-reference="sec:forced">3</a>.

<a id="the-value-12"></a>

## The value $`1/2`$

A rational point of $`\mathcal A`$ attained by an infinite support refutes Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a>. The distinguished candidate is $`1/2`$, and its membership has an exact and unusually complete classification.

<div id="res:half" class="theorem">

**Theorem 11** (classification at $`1/2`$). *The following are equivalent: $`1/2\in\mathcal A`$; the canonical greedy expansion of $`1/2`$ omits infinitely many exponents; the seam has false successor terminal bits beyond every bound; there is a cofinal integer-seam sequence whose skipped ranks tend to infinity. Dually, $`1/2\notin\mathcal A`$ is equivalent to the existence of a finite *fatal gap* — a prefix $`u`$ through rank $`d`$ with $`V(u)+T_{d+1}<\tfrac12<V(u)+w_{d+1}`$, which makes every continuation miss — and to the greedy orbit having a last skipped exponent. Moreover no finite support has value $`1/2`$.*

</div>

Checked as [the greedy form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/GreedyAchievementSet.lean#L2514), [the terminal-bit form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L126), [the skipped-rank form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L213), [the fatal-gap equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/HalfCylinderFatalGapRightTail.lean#L781), [its transfer to non-membership](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/HalfCylinderFatalGapRightTail.lean#L787), and [the finite-support exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/HalfCarryReachability.lean#L589).

These are equivalences and we mark them as such. Proving statements equivalent decides neither. Their value is that they fix what a counterexample would have to look like, and that the two sides are genuinely asymmetric: non-membership is witnessed by a *finite* fatal gap and is therefore semi-decidable, whereas membership is an infinite conjunction. Computing the greedy orbit further can only raise a lower bound on where death could occur; it cannot establish survival.

One natural route to $`1/2`$ is closed. The Boolean support selected by the negative values of the Möbius function has value exactly $`1/2`$ plus the positive Möbius tail, hence at least $`1/2+1/63`$ ([identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/MobiusSignSupportNoGo.lean#L111), [bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/571ec44f2aad98b44d51bdf607b70b33fd2079d0/Erdos249257/MobiusSignSupportNoGo.lean#L150)). That closes the sign-truncation construction; it excludes no other support.

<a id="sec:open"></a>

# The exact frontier

Two propositions remain. They are not independent, and the relation between them is asymmetric. No finite support has value $`1/2`$ (Theorem <a href="#res:half" data-reference-type="ref" data-reference="res:half">11</a>), so $`1/2\in\mathcal A`$ would exhibit an *infinite* support with a rational value and thereby refute Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a>; equivalently, a positive answer to Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> puts $`1/2`$ outside $`\mathcal A`$. The converse direction carries nothing: $`1/2\notin\mathcal A`$ eliminates one candidate and leaves the universal statement exactly where it was. The half-value question is therefore a one-sided test of \#257, not a second problem beside it.

1.  **Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> itself**, for arbitrary infinite $`A`$. Section <a href="#sec:map" data-reference-type="ref" data-reference="sec:map">4</a> is a list of families and does not approach a universal statement; Section <a href="#sec:forced" data-reference-type="ref" data-reference="sec:forced">3</a> constrains every hypothetical counterexample without excluding one. The concrete question we would most like answered is whether the constraints of Section <a href="#sec:forced" data-reference-type="ref" data-reference="sec:forced">3</a> can be made jointly contradictory: an infinite support with an unbounded Boolean–Möbius carry certificate, sublogarithmic divisor-coverage gaps and the reciprocal-mass lower bound is not yet known to be impossible, and showing that it is would settle the problem.

2.  **Membership of $`1/2`$ in $`\mathcal A`$.** Theorem <a href="#res:half" data-reference-type="ref" data-reference="res:half">11</a> makes this exactly equivalent to infinitely many greedy skips, and to a fatal gap on the other side; neither is proved. A proof of non-membership would take the form of one finite fatal gap.

Two questions that were listed here as open are now withdrawn. The squarefree value at base $`2`$ is settled by \[duverneytachiya\] (Corollary <a href="#res:sfsettled" data-reference-type="ref" data-reference="res:sfsettled">8</a>); we should have found that citation before asking for it. The reach of the analytic method of \[taoteravainen2025\] is a question its own authors raise, and belongs to them rather than to this note. The squarefree value at bases $`b\ge3`$ is, as far as we know, genuinely open, and is a well-posed question with a known answer at $`b=2`$.

<a id="statements-and-declarations"></a>

# Statements and declarations

This manuscript is authored exposition, not proof authority. The linked Lean snapshot is authoritative only for its exact propositions; kernel checking establishes that a proposition was proved, not that it is interesting, novel, or sufficient. The proof of Corollary <a href="#res:blind" data-reference-type="ref" data-reference="res:blind">9</a>, the derivation of Corollary <a href="#res:sfsettled" data-reference-type="ref" data-reference="res:sfsettled">8</a> from \[duverneytachiya\], the finite-change argument (from the two checked prefix lemmas), the shift identity and Chinese-remainder remark in Section <a href="#sec:squarefree" data-reference-type="ref" data-reference="sec:squarefree">5</a>, and the hereditary-coding sentence in Section <a href="#sec:geometry" data-reference-type="ref" data-reference="sec:geometry">6</a> are arguments in the prose rather than checked statements; each is drawn from the checked lemmas cited beside it or from the cited literature. Results attributed to Duverney and Tachiya, to Tao and Teräväinen, to Luca and Tachiya, and to Kovač and Tao are cited from the literature and are not formalised here.

*Scope of the AI declaration.* The note on the first page states that the prose was model-generated. The scope is wider than that sentence alone conveys, and the wider statement is the accurate one: large-language-model agents assisted throughout, drafting and revising this exposition, the Lean developments it links to, and the repository software that checks them. Will Cook set the objectives, selected and reviewed the public claims, checked the cited literature, and authorised this manuscript, and is responsible for its contents. Formal authority is the pinned kernel’s acceptance of an exact proposition; no model output carries any, and neither does this sentence.

Erdős Problem #257 remains open.

<div class="thebibliography">

9 D. Duverney and Y. Tachiya, *Refinement of the Chowla–Erdős method and linear independence of certain Lambert series*, Forum Math. 31 (2019), no. 6, 1557–1566, [DOI](https://doi.org/10.1515/forum-2018-0299). Corollary 1.2 and Example 1.1 settle the squarefree support at base $`2`$. T. Tao and J. Teräväinen, *Quantitative correlations and some problems on prime factors of consecutive integers*, arXiv:2512.01739 (submitted December 2025, revised April 2026). Theorem 1.3 proves $`\sum_{n\ge1}\omega(n)/2^n=\sum_p(2^p-1)^{-1}`$ irrational, settling the prime-support case of \#257 at base $`2`$; the extension to every integer base and the prime-power support are stated as remarks with the modifications left to the reader. F. Luca and Y. Tachiya, *Irrationality of Lambert series associated with a periodic sequence*, Int. J. Number Theory 10 (2014), no. 3, 623–636, [DOI](https://doi.org/10.1142/S1793042113501121). V. Kovač and T. Tao, *On several irrationality problems for Ahmes series*, Acta Math. Hungar. 175 (2025), 572–608, [DOI](https://doi.org/10.1007/s10474-025-01528-0). Remark 4.1 records the strict tail inequality and the Cantor structure. P. Erdős, *On arithmetical properties of Lambert series*, J. Indian Math. Soc. 12 (1948), 63–66. T. Bloom, *Erdős Problems*, <https://www.erdosproblems.com/257>.

</div>
