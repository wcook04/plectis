<a id="erdos-257-mersenne-support-subseries"></a>

# Denominator Periods, Rational-Value Constraints and Achievement-Set Geometry

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Let $`F\subseteq\mathbb{N}_{>0}`$ be finite and nonempty, let $`b\ge2`$, and write
``` math
\sum_{n\in F}\frac1{b^n-1}=\frac{N_F}{D_F}
  \qquad (\gcd(N_F,D_F)=1,\ D_F>0).
```
The lead result is the exact identity $`\operatorname{ord}_{D_F}(b)=\operatorname{lcm}(F)`$, with the convention $`\operatorname{ord}_1(b)=1`$. If $`\operatorname{lcm}(F)\ge2`$, then also $`\operatorname{lcm}(F)<D_F`$. Without that hypothesis the conclusion can fail: at $`b=2`$ and $`F=\{1\}`$ one has $`D_F=1`$.

Erdős #257 asks whether $`X_A=\sum_{a\in A}(2^a-1)^{-1}`$ is irrational for every infinite $`A\subseteq\mathbb{N}_{>0}`$. It remains open. The coordinate used here is the divisor incidence $`\operatorname{sc}_A(n)=\#\{d\mid n:d\in A\}`$, for which $`X_A=\sum_{n\ge1}\operatorname{sc}_A(n)2^{-n}`$; these coefficients are nonnegative divisor counts and need not be binary digits. If $`X_A`$ is rational, its integral scaled-tail sequence satisfies an exact long-division recurrence. For infinite $`A`$ that sequence is unbounded, and every zero window of $`\operatorname{sc}_A`$ at $`c+N`$ has length at most $`\varepsilon\log_2(N+1)+O_{\varepsilon,c,v}(1)`$. Under the additional hypotheses that $`\sum_{a\in A}1/a`$ converges and that the reduced odd denominator part $`v>1`$ is coprime to the numerator, rationality also forces
``` math
\sum_{a\in A}\frac1a\ge\frac1{\operatorname{ord}_v(2)}.
```
Finally, rational values admit an exact Boolean–Möbius scaled-tail characterisation from which the support is reconstructed. These constraints are not known to be contradictory. We also record the squarefree support, whose values at every power-of-two base are jointly controlled by the literature and on which two of the arguments used here fail for a reason internal to a normalisation rather than to the value itself. We then record the achievement-set geometry and the exact status of the candidate $`1/2`$: membership would refute \#257, while non-membership would eliminate only this one candidate.

<a id="sec:problem"></a>

# Introduction and main results

<div id="res:problem" class="problem">

**Problem 1** (Erdős \#257). For every infinite $`A\subseteq\mathbb{N}_{>0}`$, is $`X_A=\sum_{a\in A}\dfrac1{2^a-1}`$ irrational?

</div>

See Erdős \[erdos1968, p. 222\], Erdős and Graham \[erdosgraham1980, p. 62\], and Erdős \[erdos1988, p. 105\]. Bloom’s current catalogue record reproduces the displayed problem and labels it open, while explicitly warning that the status is the website owner’s present assessment and may omit relevant literature \[erdosproblems\]. We therefore use the catalogue for numbering and current reported status only; the original publications and the later cited papers carry the mathematical claims. Write $`w_{n}=(2^n-1)^{-1}`$. Expanding each weight as a geometric series and interchanging the two nonnegative sums gives the coordinate this note works in. With the *divisor incidence* $`\operatorname{sc}_A(n)=\#\{d\mid n: d\in A\}`$,
``` math
X_A=\sum_{a\in A}\frac1{2^a-1}=\sum_{n\ge1}\frac{\operatorname{sc}_A(n)}{2^n}.
  \tag{1}\label{eq:incidence}
```
The transform is worth reading carefully, because it is where the arithmetic of the problem enters. The datum is a $`0/1`$ selector, the indicator of $`A`$; what appears in <a href="#eq:incidence" data-reference-type="eqref" data-reference="eq:incidence">[eq:incidence]</a> is not that selector but its divisor transform, a nonnegative integer sequence bounded by the divisor function, $`\operatorname{sc}_A(n)\le d(n)`$. So \#257 is not a generic question about binary digit sequences. Equation <a href="#eq:incidence" data-reference-type="eqref" data-reference="eq:incidence">[eq:incidence]</a> is a power-series representation, not a binary expansion: its coefficients are divisor counts drawn from a single support and may exceed $`1`$. Every theorem below is a statement about sequences of that shape.

A small instance fixes the notation. At $`A=\{2,3\}`$ the incidence sequence begins
``` math
\operatorname{sc}_A(1),\dots,\operatorname{sc}_A(12)=0,1,1,1,0,2,0,1,1,1,0,2,
```
the value $`2`$ occurring at the multiples of $`6`$ and the value $`0`$ at the integers prime to $`6`$, and <a href="#eq:incidence" data-reference-type="eqref" data-reference="eq:incidence">[eq:incidence]</a> reads $`\tfrac13+\tfrac17=\tfrac{10}{21}`$.

Several statements below hold at every integer base, so we write $`X_A(b)=\sum_{a\in A}(b^a-1)^{-1}`$ for the value at an integer base $`b\ge2`$, with $`X_A=X_A(2)`$. Base $`2`$ is the case Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> asks about and is meant whenever no base is named.

<a id="the-finite-support-theorem."></a>

#### The finite-support theorem.

For a finite nonempty $`F\subseteq\mathbb{N}_{>0}`$ and an integer $`b\ge2`$, write
``` math
x_F(b)=\sum_{n\in F}\frac1{b^n-1}=\frac{N_F}{D_F}
  \qquad (\gcd(N_F,D_F)=1,\ D_F>0).
```
We use the standard trivial-modulus convention $`\operatorname{ord}_1(b)=1`$.

<div id="res:period" class="theorem">

**Theorem 2** (finite-period noncollapse). *Let $`F\subseteq\mathbb{N}_{>0}`$ be finite and nonempty, let $`b\ge2`$ be an integer, and let $`D_F>0`$ be the denominator of $`x_F(b)`$ in lowest terms. Then $`D_F`$ is coprime to $`b`$, and
``` math
\operatorname{ord}_{D_F}(b)=\operatorname{lcm}\{n:n\in F\}.
```
If moreover $`\operatorname{lcm}(F)\ge2`$, then $`\operatorname{lcm}(F)<D_F`$.*

</div>

The order statement is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L5091), its reduced-denominator form is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L5246), coprimality is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L5221), and the growth clause is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L5260).

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

<a id="structure."></a>

#### Structure.

Section <a href="#sec:period" data-reference-type="ref" data-reference="sec:period">2</a> develops the arithmetic of Theorem <a href="#res:period" data-reference-type="ref" data-reference="res:period">2</a>. Section <a href="#sec:forced" data-reference-type="ref" data-reference="sec:forced">3</a> collects what rationality would force on an arbitrary infinite support, which is the part of this note that quantifies over every support rather than sampling. Section <a href="#sec:map" data-reference-type="ref" data-reference="sec:map">4</a> gives representative supports already known to give irrational values, grouped by the argument that reaches them. Section <a href="#sec:squarefree" data-reference-type="ref" data-reference="sec:squarefree">5</a> treats the squarefree support, whose values are known at every power-of-two base and which two of the arguments used here provably cannot reach at any even base. Section <a href="#sec:geometry" data-reference-type="ref" data-reference="sec:geometry">6</a> is the geometry of the set of attainable values, and the value $`1/2`$ inside it. Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">7</a> states what remains.

<a id="sec:period"></a>

# Finite-support denominator periods

A finite support has a rational value, so for a finite support the question is not irrationality but arithmetic: how large the denominator is, and how the base sits inside it. Theorem <a href="#res:period" data-reference-type="ref" data-reference="res:period">2</a> answers the second exactly and, under its stated hypothesis $`\operatorname{lcm}(F)\ge2`$, gives a strict lower bound for the first. The omitted boundary is genuine: at $`b=2`$ and $`F=\{1\}`$ the two quantities are both $`1`$.

Six instances at $`b=2`$, which also show what the hypothesis $`\operatorname{lcm}(F)\ge2`$ is for:

<div class="center">

| $`F`$ | $`x_F(2)`$ | $`D_F`$ | $`\operatorname{lcm}(F)`$ | $`\operatorname{ord}_{D_F}(2)`$ |
|:---|:---|:---|:---|:---|
| $`\{1\}`$ | $`1`$ | $`1`$ | $`1`$ | $`1`$ |
| $`\{2\}`$ | $`1/3`$ | $`3`$ | $`2`$ | $`2`$ |
| $`\{2,3\}`$ | $`10/21`$ | $`21`$ | $`6`$ | $`6`$ |
| $`\{1,2,3\}`$ | $`31/21`$ | $`21`$ | $`6`$ | $`6`$ |
| $`\{2,6\}`$ | $`22/63`$ | $`63`$ | $`6`$ | $`6`$ |
| $`\{4,6\}`$ | $`26/315`$ | $`315`$ | $`12`$ | $`12`$ |

</div>

The last two columns agree in every row, which is the order statement. In the worked case $`F=\{1,2,3\}`$, the rational sum is $`1+1/3+1/7=31/21`$ and $`2^6\equiv1\pmod {21}`$, whereas no smaller positive exponent gives $`1`$. The first row is the only finite nonempty support with $`\operatorname{lcm}(F)=1`$, and the only one on which $`\operatorname{lcm}(F)<D_F`$ fails; that is what the hypothesis $`\operatorname{lcm}(F)\ge2`$ excludes.

The content is a noncollapse statement. Clearing denominators over $`b^{\operatorname{lcm}(F)}-1`$ makes the period at most $`\operatorname{lcm}(F)`$ immediately; what is not immediate is that cancellation in the numerator cannot bring it below. The mechanism is that each selected exponent $`n`$ contributes, by the cyclotomic route, a prime-power modulus dividing $`b^{n}-1`$ on which $`b`$ has order exactly $`n`$; no single reduction can remove all of them at once. Prime powers rather than primes is not a technicality. At $`(b,n)=(2,6)`$ no prime divisor of $`2^6-1=63`$ has order $`6`$ — one of the exceptional cases in Zsigmondy’s theorem — while $`9`$ does, and it is the prime power that carries the witness. The row $`F=\{2,6\}`$ above is that case in full: $`D_F=63=9\cdot7`$, and since $`2`$ has order $`2`$ modulo $`3`$ and order $`3`$ modulo $`7`$, the order $`6`$ can only come from $`9`$. The growth clause then follows formally, since the order divides $`\varphi(D_F)<D_F`$, where $`\varphi`$ is Euler’s totient.

Two boundaries. This is an unconditional statement about every finite support, not a bounded table of examples, and not an implication with an open hypothesis; but it settles no infinite support, and no limit of it does. Denominator-period control is part of the classical method behind Erdős’s 1948 argument \[erdos1948\]. Whether this exact sharp form appears in the literature has not been assessed, and no novelty is claimed.

<a id="sec:forced"></a>

# Rational values and scaled tails

Section <a href="#sec:map" data-reference-type="ref" data-reference="sec:map">4</a> below lists supports for which irrationality is known. This section is the other half, and the half that meets Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> rather than sampling it: statements that hold for *every* infinite support whose value is rational. The base is $`2`$ throughout, and each statement carries its own hypotheses.

<a id="integral-scaled-tails-and-unboundedness."></a>

#### Integral scaled tails, and unboundedness.

Binary long division turns a hypothetical rational value into an integer recurrence. Fix an integer $`v\ge1`$ and a sequence $`f\colon\mathbb{N}_{>0}\to\mathbb{N}`$ of coefficients. Call an integer sequence $`u\colon\mathbb{N}\to\mathbb{Z}`$ a *tempered scaled-tail sequence* for $`f`$ with multiplier $`v`$ if
``` math
u(n+1)=2u(n)-v\,f(n+1)\quad\text{for every }n\ge0,
  \qquad\text{and}\qquad u(n)=o(2^{n}).
```
The recurrence is one step of long division in base $`2`$: double the remainder, then pay out the next coefficient. The growth condition is what pins the solution down, since two solutions of the recurrence differ by $`C\,2^{n}`$ for a constant $`C`$, and only $`C=0`$ survives $`u(n)=o(2^{n})`$. For any coefficient sequence with $`f(n)\le n`$ — and $`\operatorname{sc}_A(n)\le d(n)\le n`$ qualifies, $`d`$ being the divisor function — the series $`\sum f(n)2^{-n}`$ is rational exactly when a tempered scaled-tail sequence exists for some $`v\ge1`$, and every such sequence is then the scaled tail $`u(n)=v\sum_{j\ge1}f(n+j)2^{-j}`$, so the orbit is unique rather than merely available ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/GenericTailOrbitRigidity.lean#L426)). The next theorem exhibits such an orbit for $`X_A`$ itself, with the coefficient sequence shifted past the power of $`2`$ in the denominator.

<div id="res:unbounded" class="theorem">

**Theorem 3** (unbounded scaled-tail states). *Let $`A\subseteq\mathbb{N}_{>0}`$ be infinite with $`X_A=p/(2^cv)`$, $`v\ge1`$. Then there is $`u\colon\mathbb{N}\to\mathbb{N}_{>0}`$ with
``` math
u(n)=v\sum_{j\ge1}\operatorname{sc}_A(c+n+j)2^{-j}
```
satisfying the exact recurrence
``` math
u(n+1)+v\,\operatorname{sc}_A(c+n+1)=2u(n),
  \qquad u(n)\equiv p\,2^{n}\ (\mathrm{mod}\ v),
```
and $`u`$ is unbounded.*

</div>

Checked as [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/RationalSupportCarrySkeleton.lean#L2377). The useful clause is exact: these scaled-tail states cannot remain bounded. In particular they cannot eventually cycle through a finite set of states.

<a id="divisor-coverage-cannot-have-long-gaps."></a>

#### Divisor coverage cannot have long gaps.

Say that $`\operatorname{sc}_A`$ has a *zero window* of length $`h`$ at $`N`$ if $`\operatorname{sc}_A(N+1)=\dots=\operatorname{sc}_A(N+h)=0`$, that is, if no element of $`A`$ divides any of $`h`$ consecutive integers. At $`A=\{2,3\}`$, for instance, $`\operatorname{sc}_A`$ vanishes exactly on the integers prime to $`6`$, so every zero window has length at most $`1`$: one of any two consecutive integers is even.

<div id="res:sublog" class="theorem">

**Theorem 4** (sublogarithmic zero windows). *Let $`A\subseteq\mathbb{N}_{>0}`$ be nonempty with $`X_A=p/(2^cv)`$, $`v\ge1`$. For every $`\varepsilon>0`$ there is a constant $`B`$, depending only on $`\varepsilon`$, $`c`$ and $`v`$, such that every zero window of $`\operatorname{sc}_A`$ at $`c+N`$ has length
``` math
h\le\varepsilon\log_2(N+1)+B .
```
The bound is uniform in the support $`A`$, in the numerator $`p`$, and in $`N`$ and $`h`$.*

</div>

Checked as [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/SublogDivisorCoverage.lean#L392). Read as a constraint on counterexamples, this rules out zero windows of any fixed positive proportion of $`\log_2N`$ once $`N`$ is large. The proof compares an exponential lower bound forced on the scaled tail with an upper bound for divisor sums that grows more slowly than any fixed power of $`N`$.

<a id="a-reciprocal-sum-lower-bound."></a>

#### A reciprocal-sum lower bound.

Let $`\operatorname{ord}_v(2)`$ denote the multiplicative order of $`2`$ modulo an odd $`v>1`$, and write the reciprocal mass of $`A`$ for $`\sum_{a\in A}1/a`$.

<div id="res:mass" class="theorem">

**Theorem 5** (reciprocal mass bound). *Let $`A\subseteq\mathbb{N}_{>0}`$ be such that $`\sum_{a\in A}1/a`$ converges, and suppose $`X_A=p/(2^cv)`$ with $`v>1`$ odd and $`\gcd(p,v)=1`$. Then
``` math
\sum_{a\in A}\frac1a\;\ge\;\frac1{\operatorname{ord}_v(2)} .
```*

</div>

Checked as [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/RationalSupportCarrySkeleton.lean#L1478). A finite support already supplies an instance: $`A=\{2,3\}`$ has $`X_A=10/21`$, so $`c=0`$, $`v=21`$, $`\gcd(p,v)=1`$ and $`\operatorname{ord}_{21}(2)=6`$, and the bound reads $`\tfrac12+\tfrac13\ge\tfrac16`$. The summability hypothesis is doing real work: a rational value with fixed odd denominator part $`v`$ and a convergent reciprocal sum requires mass at least $`1/\operatorname{ord}_v(2)`$. The statement does not apply when the reciprocal sum diverges, and it gives no positive lower bound uniform in $`v`$; it constrains the pair (support, denominator) jointly.

<a id="a-booleanmöbius-characterisation."></a>

#### A Boolean–Möbius characterisation.

The three theorems above give necessary conditions. The next statement is an equivalence, and is the sharpest description of rational-valued supports the development has. It removes the support from the description altogether, which is possible because the support can always be read back off the incidence sequence: with $`\mu`$ the Möbius function, $`*`$ Dirichlet convolution $`(g*h)(n)=\sum_{d\mid n}g(d)h(n/d)`$ and $`\mathbf 1_A`$ the indicator of $`A`$, the identity $`\operatorname{sc}_A=\mathbf 1_A*1`$ inverts to $`\mu*\operatorname{sc}_A=\mathbf 1_A`$.

For $`p\in\mathbb{Z}`$, $`q\ge1`$ and $`U\colon\mathbb{N}\to\mathbb{Z}`$, set
``` math
Q_U(0)=0,\qquad
  Q_U(n)=\frac{2U(n-1)-U(n)}q\quad(n\ge1).
```
Call $`U`$ an *admissible Boolean–Möbius scaled-tail sequence* for $`(p,q)`$ if
``` math
\begin{gathered}
 U(0)=p,\quad U(N)>0,\quad
 U(N)\le q\bigl(2\sqrt N+4\bigr)\quad(N\ge0),\\
 q\mid 2U(N)-U(N+1)\quad(N\ge0),\qquad
 (\mu*Q_U)(n)\in\{0,1\}\quad(n\ge1).
\end{gathered}
\tag{2}\label{eq:bmc}
```
The divisibility condition makes $`Q_U`$ integral; the last condition says that Möbius inversion of the quotient is the indicator of a set.

<div id="res:bmc" class="theorem">

**Theorem 6** (Boolean–Möbius scaled-tail correspondence). *Let $`p\in\mathbb{Z}`$ and $`q\ge1`$. There exists a support $`A`$ with $`0\notin A`$, with some positive element, and with $`X_A=p/q`$, if and only if there exists an admissible Boolean–Möbius scaled-tail sequence $`U`$ for $`(p,q)`$. In that case the support is recovered as
``` math
A=\{n:(\mu*Q_U)(n)=1\},
```
with $`Q_U`$ as in <a href="#eq:bmc" data-reference-type="eqref" data-reference="eq:bmc">[eq:bmc]</a>.*

</div>

Checked as [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/BooleanMobiusCarry.lean#L948). The finite example $`A=\{2,3\}`$ makes the definition concrete. Here $`p/q=10/21`$, and
``` math
Q_U(1),\ldots,Q_U(6)=0,1,1,1,0,2,\qquad
 U(0),\ldots,U(6)=10,20,19,17,13,26,10.
```
Möbius inversion gives $`(\mu*Q_U)(1),\ldots,(\mu*Q_U)(6)=0,1,1,0,0,0`$, the indicator of $`\{2,3\}`$ through that range. This finite calculation illustrates the correspondence; the admissible scaled-tail sequence itself is an infinite object, and the finite support is not a counterexample to Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a>.

One boundary on the equivalence. The support it produces is not required to be infinite, and a finite support supplies an admissible scaled-tail sequence for its own value, so existence of such a sequence is not by itself a counterexample to Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a>. What the equivalence changes is the search space, not the difficulty.

<a id="combined-constraints-on-a-rational-counterexample."></a>

#### Combined constraints on a rational counterexample.

Taken together: a counterexample to Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> would have an unbounded scaled-tail sequence obeying an exact linear recurrence and sublogarithmic divisor-coverage gaps. If its reciprocal sum converged and its reduced odd denominator part were greater than $`1`$, it would also satisfy Theorem <a href="#res:mass" data-reference-type="ref" data-reference="res:mass">5</a>. Theorem <a href="#res:bmc" data-reference-type="ref" data-reference="res:bmc">6</a> reconstructs every rational value, but by itself does not force the reconstructed support to be infinite. These qualifications matter: the four statements have different hypotheses, and no jointly contradictory combination has been proved.

<a id="sec:map"></a>

# Representative known irrational supports

The following table is representative, not exhaustive. It groups the displayed supports by five mechanisms rather than suggesting that its rows classify all known cases.

| Support $`A`$ | Bases | Mechanism and authority |
|:---|:---|:---|
|  |  |  |
| all of $`\mathbb{N}_{>0}`$ | every $`b\ge2`$ | Erdős 1948 \[erdos1948\]; [formalised here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L8717) |
| multiples of a fixed $`d`$ | every $`b\ge2`$ | dilation: the multiples series at base $`b`$ *is* the full-support series at base $`b^d`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L8775)) |
|  |  |  |
| eventually periodic | every $`b\ge2`$ | [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L11276); Luca–Tachiya prove the nonnegative purely-periodic case \[lucatachiya2017, Theorem 1, p. 139; proof pp. 149–150\]; finite rational prefixes give the infinite eventual case |
| a residue class; the odd numbers | every $`b\ge2`$ | special cases of the row above ([residue class](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L11344), [odd](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L11358)); Luca–Tachiya’s Example 2 strengthens the odd row to joint linear independence of every finite divisor-convolution ladder, also for negative integer bases with absolute value greater than one \[lucatachiya2017, Example 2, p. 140\] |
|  |  |  |
| factorials $`\{n!\}`$ | every $`b\ge2`$ | [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L5707) |
| powers of two $`\{2^k\}`$ | every $`b\ge2`$ | [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L5731) |
| pairwise coprime, $`\sum_{a\in A}a^{-1}<\infty`$ | every $`b\ge2`$ | Erdős \[erdos1968\], theorem on p. 222; [formalised here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L10448) |
|  |  |  |
| $`F_s(E)`$ and the monomial images $`\{j n^i:n\in F_s(E)\}`$ | $`b=q^j`$ with $`|q|^L\le s`$, $`L=\operatorname{lcm}(1,\dots,\ell)`$ | Duverney–Tachiya \[duverneytachiya, Cor. 1.2, author-preprint p. 4\]; linear independence, not only irrationality; not formalised here |
| $`s`$-free positive integers, with or without $`1`$ | $`b=q^j`$, $`2\le |q|\le s`$, $`j\ge1`$ | *ibid.*, with $`E`$ the primes and $`\ell=i=1`$; deleting $`1`$ changes the value by $`1/(b-1)\in\mathbb{Q}`$ |
| squarefree | every $`b=2^j`$, $`j\ge1`$ | Duverney–Tachiya \[duverneytachiya, Cor. 1.2 and Ex. 1.1, author-preprint p. 4\]; joint linear independence for every finite set of such bases; not formalised here |
| coprime to a fixed $`N`$; sums of two squares | every $`b\ge2`$ | *ibid.*, Examples 1.3 and 1.2; not formalised here |
|  |  |  |
| primes | $`b=2`$ proved | Tao–Teräväinen \[taoteravainen2025\], Thm. 1.3, p. 4; proof pp. 44–56; not formalised here |
| primes, $`b\ge3`$; prime powers | — | *ibid.*, asserted as modifications with details omitted in the cited version |
| arbitrary infinite $`A`$ | — | **Open** (Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a>) |

In the sentence immediately following the p. 222 theorem, Erdős says that pairwise coprimality can be removed by a more complicated argument, but he does not give that argument; p. 226 repeats that boundary. Accordingly the table uses only the fully printed pairwise-coprime theorem, not the stronger unproved-in-print extension.

Five remarks on the table: one on containment between the mechanisms, three on the literature rows, and one on what “checked here” means.

*The mechanisms are not nested, and one non-containment is proved.* The base-$`b`$ full-support theorem is exactly the $`A=\mathbb{N}_{>0}`$ statement; the multiples rows genuinely specialise it after a base change, but the sparse rows do not, and this is not merely an artefact of how they were proved. The denominator-gap criterion behind the factorial and power-of-two rows *provably cannot* reach the full support: the prefix lcm grows too slowly for its hypothesis to hold ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L5944)). Conversely the analytic method of \[taoteravainen2025\] reaches the primes, which are neither eventually periodic nor pairwise coprime with summable reciprocals. No list contains another, and their union does not exhaust the infinite supports.

*One theorem of Duverney and Tachiya generates several rows.* Their refinement of the Chowla–Erdős method  \[duverneytachiya, Cor. 1.2, author-preprint p. 4; proof pp. 9–11\] proves, for a pairwise coprime sequence $`E`$ of polynomial growth and the set $`F_s(E)`$ of products of its members with exponents below $`s`$, that $`1`$ and the values $`\sum_{n\in F_s}(q^{jn^i}-1)^{-1}`$ are linearly independent over $`\mathbb{Q}`$ whenever $`|q|^{L}\le s`$, with $`L=\operatorname{lcm}(1,\dots,\ell)`$ and $`\ell`$ bounding the exponent $`i`$. This is a row-generating theorem, not an isolated example: with $`E`$ the primes, $`s=\infty`$ returns the full support at every base, while $`s=2`$ returns the squarefree support. For $`s=2`$, the constraint forces $`\ell=1`$ and $`|q|\le2`$, but the free exponent $`j`$ gives every base $`b=2^j`$. Thus this route excludes bases that are not powers of $`2`$, rather than all bases $`b\ge3`$; it also excludes higher monomial degrees $`i\ge2`$. Their conclusion is stronger than irrationality, being linear independence of the whole finite family across the chosen exponents $`j`$.

*The classical full-support value now has a digit-level refinement.* At base $`2`$, Campbell writes the Erdős–Borwein constant in the equivalent forms
``` math
E=\sum_{n\ge1}\frac1{2^n-1}
   =\sum_{n\ge1}\frac{d(n)}{2^n}
```
and proves that the binary block $`11`$ occurs infinitely often in its base-$`2`$ expansion \[campbell2026, Theorem 1, p. 12; proof pp. 12–24\]. This adds genuine digit-distribution information to the full-support row, but it neither proves normality nor addresses an arbitrary infinite support $`A`$, so it does not change the open status of Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a>.

*The two analytic rows do not have the same standing.* Theorem 1.3 on p. 4, proved in Section 5 on pp. 44–56, of \[taoteravainen2025\] proves the prime-support case at base $`2`$, the series there being $`\sum_{n\ge1}\omega(n)/2^n`$. The extension to every integer base, and the prime-power support — which those authors themselves identify with Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> — are asserted by remark, with the modifications explicitly left to the reader. The table keeps the three apart, and only the first is proved.

*Formalisation is not priority.* Rows marked “checked here” are Lean statements accepted by the pinned kernel. For the full support that is a formalisation of Erdős; Luca and Tachiya’s RIMS paper already proves the nonnegative purely-periodic case and its finite rational-prefix extension \[lucatachiya2017, Theorem 1, p. 139; proof pp. 149–150\], while Theorem A restates the broader signed purely-periodic theorem without reproducing its earlier proof. No priority is claimed anywhere in this table.

<div id="res:signed" class="remark">

*Remark 1* (signed periodic weights: a gap in the method, not in the mathematics). Dropping nonnegativity weakens the conclusion available, and it is worth being exact about where. For $`u\colon\mathbb{N}_{>0}\to\mathbb{Z}`$ periodic and $`b\ge2`$, what is checked here is a *dichotomy*: the series $`\sum_{n\ge1}u(n)/(b^n-1)`$ is irrational, *or* some power of $`b`$ times its value is an integer ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L13847)). For a nonnegative support indicator the terminating alternative is excluded by the rows above; for mixed signs this argument does not exclude it.

The terminating alternative never in fact occurs. Theorem A in Luca and Tachiya’s 2017 RIMS paper explicitly restates their earlier Theorem 1.1 in the exact form needed here: $`\sum_{n\ge1}a_n/(q^n-1)`$ is irrational for every integer $`q`$ with $`|q|>1`$ and every nonzero purely periodic integer sequence $`(a_n)`$ \[lucatachiya2017, Theorem A, p. 139\]. Thus the disjunction above is an artefact of the route taken, not a feature of the problem: the second branch is empty, and their author restatement is what shows it. The RIMS paper does not reproduce the earlier proof or verify the broader eventual-rational formulation, so neither is claimed here. The local statement retains only the interest of being an independently checked argument with a visible boundary. Section <a href="#sec:squarefree" data-reference-type="ref" data-reference="sec:squarefree">5</a> records a second, sharper instance of the same phenomenon.

</div>

<a id="sec:squarefree"></a>

# Squarefree support and a coordinate-dependent obstruction

Let $`A_{\mathrm{sf}}=\{d\ge2: d\text{ squarefree}\}`$: a support of density $`6/\pi^2`$, far denser than the primes, and not periodic. Its values at all power-of-two bases are jointly linearly independent with $`1`$, by a theorem of Duverney and Tachiya recalled below. This section establishes that two block-certificate arguments used here cannot reach that support at any even base, and that the reason lies in a normalisation rather than in the value.

<div id="res:sfcount" class="theorem">

**Theorem 7** (squarefree divisor incidence). *For every $`n\ge1`$ the number of squarefree divisors of $`n`$ is $`2^{\omega(n)}`$, where $`\omega(n)`$ is the number of distinct prime factors, and hence
``` math
\operatorname{sc}_{A_{\mathrm{sf}}}(n)=2^{\omega(n)}-1 .
```
In particular $`\operatorname{sc}_{A_{\mathrm{sf}}}(n)`$ is *odd* for every $`n\ge2`$.*

</div>

The count is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L94), the incidence formula is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L111), and the parity conclusion is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L140). The proof is the bijection between squarefree divisors of $`n`$ and subsets of its prime factors ([Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L71)), so the count is $`2^{\omega(n)}`$; removing $`d=1`$ leaves an odd number whenever $`\omega(n)\ge1`$. At $`n=12=2^2\cdot3`$ the squarefree divisors are $`1,2,3,6`$, so $`\operatorname{sc}_{A_{\mathrm{sf}}}(12)=3`$; at $`n=30`$ they are the eight divisors of $`30`$ and $`\operatorname{sc}_{A_{\mathrm{sf}}}(30)=7`$.

<a id="the-values-are-known-at-every-power-of-two-base"></a>

## The values are known at every power-of-two base

Duverney and Tachiya’s Corollary 1.2, applied with $`E`$ the primes, $`s=2`$ and $`\ell=1`$, gives $`L=\operatorname{lcm}(1)=1`$ and the admissibility condition $`|q|\le2`$. The exponent $`j`$ in their displayed family remains arbitrary. Thus, for every $`h\ge1`$, their Example 1.1 says that the numbers
``` math
1,\qquad
  \sum_{n\ge1}\frac{|\mu(n)|}{2^{jn}-1}\quad(1\le j\le h)
```
are linearly independent over $`\mathbb{Q}`$  \[duverneytachiya, Cor. 1.2 and Ex. 1.1, author-preprint p. 4\]. Since $`|\mu|`$ is the indicator of the squarefree integers including $`n=1`$, and $`A_{\mathrm{sf}}`$ omits only $`n=1`$, whose weight at base $`2^j`$ is $`(2^j-1)^{-1}\in\mathbb{Q}`$,
``` math
X_{A_{\mathrm{sf}}}(2^j)
  =\sum_{n\ge1}\frac{|\mu(n)|}{2^{jn}-1}-\frac1{2^j-1},
```
and rational translation preserves the joint linear independence with $`1`$.

<div id="res:sfsettled" class="corollary">

**Corollary 8** (joint power-of-two-base theorem). *For every $`h\ge1`$, the $`h+1`$ numbers
``` math
1,\quad X_{A_{\mathrm{sf}}}(2),\quad X_{A_{\mathrm{sf}}}(4),\quad\ldots,\quad X_{A_{\mathrm{sf}}}(2^h)
```
are linearly independent over $`\mathbb{Q}`$. In particular, every $`X_{A_{\mathrm{sf}}}(2^j)`$, $`j\ge1`$, is irrational.*

</div>

Two boundaries on that. It is a citation, not a formalisation: nothing in this development proves it. The admissibility condition $`|q|^L\le s`$ at $`s=2`$ allows only $`|q|=2`$, so this citation covers the bases $`2^j`$ and does not cover bases that are not powers of $`2`$; this note proves no result about those remaining values.

<a id="two-block-certificate-hypotheses-have-no-instance"></a>

## Two block-certificate hypotheses have no instance

Fix $`b\ge2`$ and a nonnegative coefficient sequence $`f`$. The two hypotheses used below are best printed rather than named. For every precision $`q\ge1`$, they ask for $`N,K,L,C\in\mathbb{N}`$ with $`K\le L`$ satisfying the common conditions
``` math
\begin{gathered}
 \sum_{r=K+1}^{L}f(N+r)b^{L-r}\le C,\qquad
 \exists t\in\mathbb{N}:\ f(N+L+1+t)>0,\\
 q(C+N+L+2)<b^L,
\end{gathered}
\tag{3}\label{eq:block-common}
```
together with one of the two first-block conditions
``` math
\begin{array}{ll}
\text{digitwise:}& b^r\mid f(N+r)\quad(1\le r\le K),\\[2mm]
\text{weighted:}&
b^K\mid\displaystyle\sum_{r=1}^{K}f(N+r)b^{K-r}.
\end{array}
\tag{4}\label{eq:block-first}
```
Thus the data $`N,K,L,C`$ may depend on $`q`$. The parity of Theorem <a href="#res:sfcount" data-reference-type="ref" data-reference="res:sfcount">7</a> refutes both alternatives for the squarefree incidence sequence at every even base.

<div id="res:blind" class="corollary">

**Corollary 9** (neither divisibility-first hypothesis has an instance). *For the squarefree support $`A_{\mathrm{sf}}`$ and every even base $`b\ge2`$, neither the digitwise nor the carry-aware block-certificate hypothesis holds. Both fail already at precision $`q=b^2`$.*

</div>

<div class="proof">

*Proof.* The hypothesis quantifies over every precision, so it is enough to exhibit one precision at which no admissible data exist; we take $`q=b^{2}`$ and split on whether the first block is empty.

Both hypotheses ask, for every precision $`q`$, for $`N`$, $`K\le L`$ and $`C`$ with a first-block condition on $`\operatorname{sc}_{A_{\mathrm{sf}}}(N+1),\dots,\operatorname{sc}_{A_{\mathrm{sf}}}(N+K)`$, a middle bound $`\sum_{r=K+1}^{L}\operatorname{sc}_{A_{\mathrm{sf}}}(N+r)b^{L-r}\le C`$, a nonzero coefficient beyond $`N+L`$, and $`q(C+N+L+2)<b^{L}`$. Take $`q=b^2`$ and write $`f=\operatorname{sc}_{A_{\mathrm{sf}}}`$.

Suppose $`K\ge1`$. The digitwise condition requires $`b^{r}\mid f(N+r)`$ for $`1\le r\le K`$. If $`N+K\ge2`$, its instance at $`r=K`$ makes the even number $`b`$ divide the odd number $`f(N+K)`$. The carry-aware condition requires $`b^{K}\mid\sum_{r=1}^{K}f(N+r)b^{K-r}`$; reducing modulo $`b`$ kills every term but $`r=K`$, so the same contradiction follows when $`N+K\ge2`$.

The only remaining case with $`K\ge1`$ is $`N=0`$, $`K=1`$. If $`L=1`$, then $`q(C+N+L+2)\ge3b^2>b`$; if $`L\ge2`$, the $`r=2`$ term in the middle sum is $`f(2)b^{L-2}=b^{L-2}`$, so $`qC\ge b^L`$. Both contradict the strict size inequality.

Suppose $`K=0`$, where both first-block conditions are vacuous. If $`L=0`$ the middle sum is empty and $`q(C+N+2)<b^{0}=1`$ is impossible. If $`L\ge1`$ the $`r=1`$ term gives $`C\ge b^{L-1}`$ whenever $`N\ge1`$, and again the size inequality fails. If $`N=0`$ and $`L=1`$, its left side is at least $`3b^2>b`$; if $`N=0`$ and $`L\ge2`$, the $`r=2`$ term gives $`C\ge b^{L-2}`$ and hence $`qC\ge b^L`$. These exhaust the cases. ◻

</div>

This is an argument in the prose, drawn from the checked incidence and parity lemmas, and is marked as such in *Statements and declarations*.

<a id="the-obstruction-is-a-normalisation-not-the-value"></a>

## The obstruction is a normalisation, not the value

Corollary <a href="#res:blind" data-reference-type="ref" data-reference="res:blind">9</a> is a statement about two arguments failing on a value that Corollary <a href="#res:sfsettled" data-reference-type="ref" data-reference="res:sfsettled">8</a> shows to be irrational. The question it raises is therefore not whether the value can be reached, but what the failure is a property *of*. It is a property of where the support starts.

Adjoin $`1`$ to the support and write $`A_{\mathrm{sf}}^{+}=A_{\mathrm{sf}}\cup\{1\}`$, the full squarefree support. Then
``` math
X_{A_{\mathrm{sf}}^{+}}(b)-X_{A_{\mathrm{sf}}}(b)=\frac1{b-1}\in\mathbb{Q},
```
so the two supports pose the same irrationality question at every base, while the divisor incidence changes from $`2^{\omega(n)}-1`$ to $`2^{\omega(n)}`$ — from odd to even at every $`n\ge2`$. The parity obstruction of Corollary <a href="#res:blind" data-reference-type="ref" data-reference="res:blind">9</a> evaporates under a shift that provably cannot change the answer. More is true: the shifted first-block condition at base $`2`$ asks for $`2^{r}\mid 2^{\omega(N+r)}`$, that is $`\omega(N+r)\ge r`$ for $`1\le r\le K`$, and a Chinese-remainder construction reserving $`r`$ fresh primes for each shift $`r`$ supplies such an $`N`$ for every $`K`$.

It does *not* follow that either argument certifies the shifted support: the opening block is one of the conditions listed above, and the middle bound and the arithmetic inequality are untouched by this observation. What does follow is a methodological point: an obstruction stated against a coefficient sequence can be an artefact of the normalisation chosen for that sequence. Before a no-go result is reported as a property of a problem, the coordinate it is stated in should be varied by a transformation the problem is known to be invariant under. Here the transformation is adding one rational number, and it removes the obstruction entirely.

The same invariance holds for every finite change, not only this one. If $`A\mathbin{\triangle}B`$ is finite, choose $`M`$ above all of its elements. The two support series then have the same tail beyond $`M`$, while each omitted prefix is rational. The two directions of this argument are exactly the checked prefix lemmas [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L9139) and [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/CertificateKernel.lean#L9148). Thus $`X_A(b)`$ is irrational if and only if $`X_B(b)`$ is irrational for every integer $`b\ge2`$. The present shift is the smallest instance of a general checked finite-change principle.

This is the second time in this note that a boundary turns out to belong to the method rather than to the mathematics. In Remark <a href="#res:signed" data-reference-type="ref" data-reference="res:signed">1</a> the terminating alternative of the signed periodic dichotomy is empty, and a theorem of Luca and Tachiya is what shows it; here a parity obstruction survives only until the support is shifted by one element. In each case the correction came from outside the development — once from the literature, once from asking what the statement was invariant under. A formalised no-go result carries exactly the authority of its hypotheses, and its hypotheses include the coordinates it was written in.

<a id="sec:geometry"></a>

# Achievement-set geometry and the value $`1/2`$

Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> asks whether every value obtainable from infinitely many of the weights $`w_{n}=(2^n-1)^{-1}`$ is irrational. The set of all values obtainable, from finite and infinite selections alike, is the achievement set $`\mathcal A=\{\sum_{n\ge1}\varepsilon_nw_{n}:\varepsilon_n\in\{0,1\}\}`$, and this section is about its geometry.

<div id="res:geometry" class="theorem">

**Theorem 10** (geometry of $`\mathcal A`$). *$`\mathcal A`$ is compact, perfect, totally disconnected and nowhere dense, and has Lebesgue measure $`1`$.*

</div>

Checked as [compact](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/GreedyAchievementSet.lean#L656), [perfect](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/GreedyAchievementSet.lean#L1620), [totally disconnected](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/GreedyAchievementSet.lean#L1636), [nowhere dense](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/GreedyAchievementSet.lean#L1645), and [of measure one](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/GreedyAchievementSet.lean#L996). So $`\mathcal A`$ is a fat Cantor set: strict tail domination $`\sum_{\ell>n}w_{\ell}<w_{n}`$ opens a gap at every level, while the total measure is not lost. The division of credit is exact. The strict inequality, the resulting distinctness of subsums over distinct supports, and the Cantor conclusion for every integer base are Remark 4.1 (p. 13) of Kovač and Tao \[kovactao\]; no novelty is claimed for any of the three. That remark makes no metric assertion, and strict tail domination does not determine the measure: the weights $`3^{-n}`$ satisfy $`\sum_{\ell>n}3^{-\ell}=3^{-n}/2<3^{-n}`$ and produce a null achievement set, the base-$`3`$ digits-in-$`\{0,1\}`$ Cantor set. So the measure-one clause is added here rather than formalised from there, and it is the arithmetic of the Mersenne weights that supplies it. With $`T_n=\sum_{k>n}w_{k}`$, the standard level-$`n`$ convex-hull cover consists of $`2^n`$ disjoint intervals of length $`T_n`$, its nested intersection is $`\mathcal A`$, and
``` math
2^nT_n=\sum_{j\ge1}\frac{2^n}{2^{n+j}-1}\longrightarrow\sum_{j\ge1}2^{-j}=1,
```
dominated by $`2^{1-j}`$. Continuity of measure from above therefore gives $`\lambda(\mathcal A)=1`$.

Membership is characterised level by level, by a greedy expansion. Run through $`n=1,2,\dots`$ carrying a remainder, initially the target $`x`$, and at level $`n`$ subtract $`w_{n}`$ from the remainder if $`w_{n}`$ does not exceed it, leaving the remainder unchanged otherwise; call a level at which nothing is subtracted *skipped*. Say that the expansion *survives* level $`n`$ if the remainder after that level is at most the remaining mass $`T_n`$. Then $`x\in\mathcal A`$ if and only if $`x\ge0`$ and the expansion survives every level ([Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/GreedyAchievementSet.lean#L1445)). Non-membership of a nonnegative target is therefore visible at a single level, and for a rational target the check is exact rational arithmetic. For $`x=3/4`$, the greedy algorithm skips $`w_{1}=1`$ and leaves residual $`3/4`$, while the exact zero-lookahead upper bound for the remaining tail is $`2w_{2}=2/3<3/4`$; hence $`3/4\notin\mathcal A`$ ([Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/GreedyAchievementSet.lean#L1748)).

The selector-to-subsum map sending a $`0/1`$ string $`(\varepsilon_n)`$ to $`\sum_n\varepsilon_nw_{n}`$, which the strict tail inequality makes injective, remains injective after restriction to any subfamily. That matters because Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> quantifies over every infinite support rather than over $`\mathbb{N}_{>0}`$. For a set $`J`$ of future offsets write $`T_J(n)=\sum_{k\in J}w_{n+k+1}`$ for the tail restricted to $`J`$ ([definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L20), summable at [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L24)). Then $`T_J(n)<w_{n}`$ for every $`J`$ and every $`n\ge1`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L30)), since deleting weights only shrinks a tail that already sits below $`w_{n}`$ at the full support. Consequently the digit map is injective on strings supported in $`J`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L54)), stated on the subtype of [digit strings vanishing off $`J`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L45) and evaluated by the [restricted digit map](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L49), so the statement is about the subseries itself and not a projection of the full one. Thus uniqueness of the selector survives passage to an arbitrary subfamily; this is an injectivity statement, not a statement about binary digits of the value. That is a constraint on the shape of an argument, not on the supports: it decides no value, and it is weaker than any statement in Section <a href="#sec:forced" data-reference-type="ref" data-reference="sec:forced">3</a>.

<a id="geometry-after-restricting-the-allowed-exponents"></a>

## Geometry after restricting the allowed exponents

The injectivity statement has a geometric completion for every set $`J\subseteq\mathbb{N}`$ of allowed digit positions. Let
``` math
\mathcal A_J=
  \left\{\sum_{k\in J}\varepsilon_kw_{k+1}:
    \varepsilon_k\in\{0,1\}\right\}.
```
Formally, the allowed strings form the [supported digit set](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L63), which is [closed](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L66). Its range is the [restricted achievement set](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L76); the range and image descriptions agree by [the image theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L79). Consequently $`\mathcal A_J`$ is [compact](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L90) and [closed](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L96). It lies inside $`\mathcal A`$ by [support restriction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L103) and is therefore [nowhere dense](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L112). If $`J`$ is infinite, the digit space is [preperfect](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L120); injectivity transfers that property to [$`\mathcal A_J`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L150), so the closed set is [perfect](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L167). Thus every infinite allowed support gives a compact perfect nowhere-dense set with a unique selector for each point.

The metric classification is exact. The summability lemma [controls digit terms](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L175), and changing one coordinate changes the value by precisely its signed weight by [the update formula](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L182). If $`k\notin J`$, allowing $`k`$ splits the new set into $`\mathcal A_J`$ and its translate by $`w_{k+1}`$ [exactly](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L203). The two pieces are [disjoint](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L262), so adjoining one coordinate [doubles the volume](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L286). At $`J=\mathbb{N}`$, the restricted set is the full set $`\mathcal A`$ [by definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L300).

<div id="res:supportvolume" class="theorem">

**Theorem 11** (volume dichotomy for every allowed support). *For every $`J\subseteq\mathbb{N}`$, exactly one of the following measure formulas applies:
``` math
\begin{array}{ll}
J=F^{\,c}\text{ for a finite }F,
  &\lambda(\mathcal A_J)=2^{-|F|},\\[2mm]
J^c\text{ is infinite},
  &\lambda(\mathcal A_J)=0.
\end{array}
```*

</div>

For finite $`F`$, the division-free identity [multiplies the face volume by $`2^{|F|}`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L313) and its solved form [gives $`2^{-|F|}`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L349). Monotonicity under enlarging $`J`$ is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L358). It traps a set with infinitely many forbidden coordinates below finite-codimension faces of arbitrarily small dyadic measure, yielding [measure zero](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L368). The two cases are assembled in [the formal dichotomy](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L397). This theorem classifies the size of the value set generated inside any prescribed family of exponents. It does not classify the arithmetic nature of its individual points and therefore does not settle Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a>.

<a id="the-value-12"></a>

## The value $`1/2`$

A rational point of $`\mathcal A`$ attained by an infinite support refutes Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a>. The distinguished candidate is $`1/2`$, and Theorem <a href="#res:half" data-reference-type="ref" data-reference="res:half">12</a> gives a self-contained pair of exact alternatives.

The greedy expansion of $`1/2`$ is an exact finite computation as far as one cares to take it. Through level $`21`$ it takes the exponents
``` math
2,\ 3,\ 6,\ 7,\ 14,\ 20,\ 21
```
and skips the others, the skipped runs being $`\{1\}`$, $`\{4,5\}`$, $`\{8,\dots,13\}`$ and $`\{15,\dots,19\}`$; every level through $`21`$ is survived. The second condition below asks whether the list of skipped exponents is infinite, and no finite computation answers that.

In the statement, $`u=(u_1,\dots,u_d)\in\{0,1\}^{d}`$ is a finite prefix, $`V(u)=\sum_{n\le d}u_nw_{n}`$ is its value, and $`T_n=\sum_{k>n}w_{k}`$ as above.

<div id="res:half" class="theorem">

**Theorem 12** (membership and non-membership at $`1/2`$). *The value $`1/2`$ belongs to $`\mathcal A`$ if and only if its canonical greedy expansion omits infinitely many exponents. Dually, $`1/2\notin\mathcal A`$ is equivalent to the existence of a finite *fatal gap* — a prefix $`u`$ through rank $`d`$ with $`V(u)+T_{d+1}<\tfrac12<V(u)+w_{d+1}`$, which makes every continuation miss — and to the greedy orbit having a last skipped exponent. Moreover no finite support has value $`1/2`$.*

</div>

Checked as [the greedy form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/GreedyAchievementSet.lean#L2514), [the terminal-bit form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L126), [the skipped-rank form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L213), [the fatal-gap equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/HalfCylinderFatalGapRightTail.lean#L781), [its transfer to non-membership](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/HalfCylinderFatalGapRightTail.lean#L787), and [the finite-support exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/HalfCarryReachability.lean#L589).

The formal source also proves equivalent terminal-bit and unbounded skipped-rank formulations in its internal half-cylinder seam coordinate; the two middle source links above are those versions. Their definitions are not needed for the self-contained greedy and fatal-gap statement used here. The two sides are asymmetric: non-membership is witnessed by a *finite* fatal gap and is therefore semi-decidable, whereas membership is an infinite condition. Computing further can only raise a lower bound on where a fatal gap could occur; it cannot establish survival.

One natural route to $`1/2`$ is closed. The Boolean support selected by the negative values of the Möbius function has value exactly $`1/2`$ plus the positive Möbius tail, hence at least $`1/2+1/63`$ ([identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/MobiusSignSupportNoGo.lean#L111), [bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ae9ef27b040934b70f2418431d58d30a4b01974b/Erdos249257/MobiusSignSupportNoGo.lean#L150)). That closes the sign-truncation construction; it excludes no other support.

<a id="sec:open"></a>

# Open problems

For the base-$`2`$ universal problem, two endpoint propositions organise the remaining discussion. They are not independent, and the relation between them is asymmetric. No finite support has value $`1/2`$ (Theorem <a href="#res:half" data-reference-type="ref" data-reference="res:half">12</a>), so $`1/2\in\mathcal A`$ would exhibit an *infinite* support with a rational value and thereby refute Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a>; equivalently, a positive answer to Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> puts $`1/2`$ outside $`\mathcal A`$. The converse direction does not follow: $`1/2\notin\mathcal A`$ would give a finite fatal-gap witness and eliminate this candidate, but would not imply the universal statement. The half-value question is therefore a one-sided test of \#257, not a second problem beside it.

1.  **Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">1</a> itself**, for arbitrary infinite $`A`$. Section <a href="#sec:map" data-reference-type="ref" data-reference="sec:map">4</a> is a list of families and does not approach a universal statement; Section <a href="#sec:forced" data-reference-type="ref" data-reference="sec:forced">3</a> constrains every hypothetical counterexample without excluding one. Every counterexample would have unbounded scaled-tail states, sublogarithmic divisor-coverage gaps and an admissible Boolean–Möbius scaled-tail sequence; Theorem <a href="#res:mass" data-reference-type="ref" data-reference="res:mass">5</a> adds its lower bound only under its stated convergence and odd-denominator hypotheses. No contradiction among the applicable constraints is known.

2.  **Membership of $`1/2`$ in $`\mathcal A`$.** Theorem <a href="#res:half" data-reference-type="ref" data-reference="res:half">12</a> makes this exactly equivalent to infinitely many greedy skips, and to a fatal gap on the other side; neither is proved. A proof of non-membership would take the form of one finite fatal gap.

For scope, all squarefree values at power-of-two bases, jointly in each finite family, are settled by Corollary 1.2 and Example 1.1 of  \[duverneytachiya, author-preprint p. 4\] (Corollary <a href="#res:sfsettled" data-reference-type="ref" data-reference="res:sfsettled">8</a>). Their cited corollary does not cover bases that are not powers of $`2`$, and this note makes no global open-status or priority claim for those values.

<a id="statements-and-declarations"></a>

# Statements and declarations

This manuscript is authored exposition, not proof authority. The linked Lean snapshot is authoritative only for its exact propositions; kernel checking establishes that a proposition was proved, not that it is interesting, novel, or sufficient. The proof of Corollary <a href="#res:blind" data-reference-type="ref" data-reference="res:blind">9</a>, the derivation of Corollary <a href="#res:sfsettled" data-reference-type="ref" data-reference="res:sfsettled">8</a> from  \[duverneytachiya, Cor. 1.2 and Ex. 1.1, author-preprint p. 4\], the finite-change argument (from the two checked prefix lemmas), the shift identity and Chinese-remainder remark in Section <a href="#sec:squarefree" data-reference-type="ref" data-reference="sec:squarefree">5</a>, and the restricted selector-injectivity sentence in Section <a href="#sec:geometry" data-reference-type="ref" data-reference="sec:geometry">6</a> are arguments in the prose rather than checked statements; each is drawn from the checked lemmas cited beside it or from the cited literature. The numerical instances — the table of finite supports in Section <a href="#sec:period" data-reference-type="ref" data-reference="sec:period">2</a>, the incidence and zero-window examples, the reciprocal-mass and Boolean–Möbius instances, the $`3/4`$ certificate, and the greedy expansion of $`1/2`$ through level $`21`$ — are direct computations, reported as computations and not as theorems. Results attributed to Campbell, to Duverney and Tachiya, to Tao and Teräväinen, to Luca and Tachiya, and to Kovač and Tao are cited from the literature and are not formalised here.

*Scope of the AI declaration.* The declaration on the first page applies in full: large-language-model agents assisted throughout, drafting and revising this exposition, the Lean developments it links to, and the repository software that checks them. Will Cook set the objectives, selected and reviewed the public claims, checked the cited literature, and authorised this manuscript, and is responsible for its contents. Formal authority is the pinned kernel’s acceptance of an exact proposition; no model output carries any, and neither does this sentence.

Erdős Problem #257 remains open.

<div class="thebibliography">

10 J. M. Campbell, [*On the binary digits of the Erdős–Borwein constant*](https://arxiv.org/abs/2605.24160), arXiv:2605.24160v1, 2026. Theorem 1 on p. 12 proves that the binary block $`11`$ occurs infinitely often in the base-$`2`$ expansion of the full-support value; its proof occupies pp. 12–24. D. Duverney and Y. Tachiya, [*Refinement of the Chowla–Erdős method and linear independence of certain Lambert series*](https://danielduverney.fr/documents/theorie-des-nombres/DuverneyTachiya190522.pdf), Forum Math. 31 (2019), no. 6, 1557–1566, [DOI](https://doi.org/10.1515/forum-2018-0299). Corollary 1.2 gives the general $`F_s(E)`$ theorem and its monomial images under $`|q|^{\operatorname{lcm}(1,\dots,\ell)}\le s`$; Example 1.1 gives the joint squarefree family at all bases $`2^j`$, $`j\ge1`$. Both are on p. 4 of the linked author preprint; the proof is on pp. 9–11. T. Tao and J. Teräväinen, *Quantitative correlations and some problems on prime factors of consecutive integers*, arXiv:2512.01739 (submitted December 2025, revised April 2026). Theorem 1.3 proves $`\sum_{n\ge1}\omega(n)/2^n=\sum_p(2^p-1)^{-1}`$ irrational, settling the prime-support case of \#257 at base $`2`$; the extension to every integer base and the prime-power support are stated as remarks with the modifications left to the reader. The theorem is on p. 4 and its proof is Section 5, pp. 44–56, in arXiv v2. F. Luca and Y. Tachiya, [*Linear independence results for the values of divisor functions series*](https://www.kurims.kyoto-u.ac.jp/~kyodo/kokyuroku/contents/pdf/2014-14.pdf), RIMS Kôkyûroku No. 2014 (2017), 138–150. Theorem A on p. 139 explicitly restates their earlier Theorem 1.1 for nonzero purely periodic integer weights. Theorem 1 is on p. 139, its examples are on p. 140, and its proof is on pp. 149–150. V. Kovač and T. Tao, *On several irrationality problems for Ahmes series*, Acta Math. Hungar. 175 (2025), 572–608, [DOI](https://doi.org/10.1007/s10474-025-01528-0). Remark 4.1 (p. 13) records the strict tail inequality and the Cantor structure. Theorem 2.3 (p. 5; proof pp. 13–14) constructs rational merged sums from several bases under its mass hypothesis; it is not a fixed-base counterexample. P. Erdős, *On arithmetical properties of Lambert series*, J. Indian Math. Soc. 12 (1948), 63–66. P. Erdős, [*On the irrationality of certain series*](https://users.renyi.hu/~p_erdos/1969-09.pdf), Math. Student 36 (1968), 222–226 (issued 1969). The theorem on p. 222 treats pairwise-coprime support with convergent reciprocal sum at every integer base $`b\ge2`$; the claimed removal of pairwise coprimality is stated without proof. P. Erdős and R. L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory*](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf), Monogr. Enseign. Math. 28, Geneva, 1980, p. 62. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). T. F. Bloom, [*Erdős Problem \#257*](https://www.erdosproblems.com/257), `erdosproblems.com/257`, accessed 28 July 2026 (page displays “last edited 15 April 2026”). The current record labels the universal fixed-base problem open, cites `[Er68d]`, `[ErGr80, p. 62]` and `[Er88c, p. 105]`, records the Tao–Teräväinen prime and prime-power cases and the Kovač–Tao refutation of a broader varying-denominator speculation, and explicitly describes its status as the website owner’s present assessment rather than a literature-completeness guarantee.

</div>
