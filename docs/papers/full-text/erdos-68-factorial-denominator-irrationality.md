<a id="erdos-68-factorial-denominator-irrationality"></a>

# Factorial Carries and Finite Channel Obstructions

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Erdős asked whether
``` math
S=\sum_{n\ge2}\frac1{n!-1}
```
is irrational. The problem remains open. Put $`H_m=\sum_{2\le n\le m}(n!-1)^{-1}`$ and let $`Z_m=\lfloor m!H_m\rfloor+1`$ be its strict factorial successor. Write $`b_m`$ for the integer in $`Z_m=mZ_{m-1}+1-b_m`$. The central formal equivalence is
``` math
S\notin\mathbb Q
  \quad\Longleftrightarrow\quad
  (\forall B)(\exists m>B)\;b_m\ne1
  \quad\Longleftrightarrow\quad
  (\forall B)(\exists m>B)\;m\nmid Z_m .
```
An independently regenerated exact GMP certificate supplies a miss at $`m=300000`$; the corresponding Lean theorem proves that every representation $`S=a/q`$ with $`q>0`$ has $`q\ge300000`$.

The finite channel algebra gives a second rigorous layer. In each channel $`d`$, the channel numerator is congruent to the factorial moment modulo $`d!-1`$; simultaneous cancellation through a cutoff $`D`$ therefore forces a specified least common multiple to divide that moment. A two-term prime correction isolates one channel, and a Cramer construction gives arbitrarily remote finite supports that cancel any prescribed finite set of channels and have residual of absolute value at most $`1/2`$. That rounded residual may be zero. Separately, endpoint congruences turn sufficiently large residues or disagreement between two projections into finite exclusions.

No theorem constructs cofinally many non-unit carries, a cofinal family of strictly nonzero translated residuals, or the quantitative residue and scale bounds required by the endpoint arguments. The note therefore proves a carry normal form, finite channel obstructions, and a denominator exclusion—not irrationality of $`S`$.

> **Contribution.** The paper proves exact carry and divisibility equivalences for the factorial-gap series and records a finite denominator exclusion through $`q<300000`$, whose arithmetic certificate is checked outside Lean.
>
> **Relation to the open problem.** The equivalences identify the missing cofinal input without supplying it. A finite denominator exclusion does not change the quantifier, and Problem #68 remains open.
>
> **Executable review object.** Comparator selects both exact equivalences: cofinal failure of the strict factorial-successor divisibility test and cofinally many non-unit carries. The mixed Lean-plus-certificate denominator computation is reported separately. The repository’s external-verification job compares these exact Lean propositions with separately declared challenge statements and an axiom budget, then asks Lean’s kernel to check the submitted proofs. The [formalisation manifest](https://github.com/wcook04/plectis-lean-erdos249-257/blob/main/formalization.yaml) and the commit-bound CI receipt record that check; they do not assess novelty, significance, or whether the original problem is solved.

<a id="sec:problem"></a>

# The problem

<div id="res:problem" class="problem">

**Problem 1** (Erdős \#68). Is
``` math
S=\sum_{n\ge2}\frac1{n!-1}
```
irrational?

</div>

<div class="center">

| Contribution | Exact scope |
|:---|:---|
| Denominator exclusion | If $`S=a/q`$ with $`q>0`$, then $`q\ge300000`$. |
| Integral frontier | $`S\notin\mathbb Q`$ iff for every $`B`$ some $`m>B`$ satisfies $`m\nmid Z_m`$. |
| Structural reductions | Finite channel congruences, a two-term prime corrector, and endpoint projections isolate explicit missing inputs. |
| Not a contribution | No cofinal miss, cofinal strict residual nonvanishing, or irrationality theorem is proved. |

</div>

Erdős states the problem on p. 102 of his 1988 survey and, in the same passage, records the broader expectation that $`\sum_n1/(n!+t)`$ is irrational—indeed transcendental—for every integer $`t`$ \[erdos1988, p. 102\]. This is conjectural context, not a theorem proved in that source.

Numbering and current status follow [Bloom’s Erdős problem catalogue](https://www.erdosproblems.com/68) \[bloom\]. The problem is open. The companion series $`\sum_{n\ge0}1/n!=e`$ and $`\sum_{n\ge2}1/(n!+1)`$ sit in the same family, and the difficulty here is the same one that makes the Erdős–Borwein constant hard: the denominators $`n!-1`$ grow fast enough that convergence is trivial and slow enough, in the arithmetic sense, that no single congruence controls them.

The definitions and claim boundary are repeated here so that the note is self-contained.

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

| Statement | Status | Exact boundary |
|:---|:---|:---|
| Irrationality of $`S`$ | Open | No proof is claimed. |
| Canonical factorial digit kernel | Checked | Floor formula, digit bounds, remainder recurrence, finite expansion, zero-tail propagation. |
| Channel integrality | Checked | $`(d!)^{\lfloor i/d\rfloor}\mid i!`$, with exact denominator cancellation. |
| Channel congruence and LCM obstruction | Checked | $`V_{d}(\lambda)\equiv M\pmod{d!-1}`$; annihilating channels through $`D`$ forces $`L_D\mid M`$. |
| Two-term prime channel corrector | Checked | The pair $`(p,-1)`$ on $`(p-1,p)`$ has moment $`0`$, all channels $`0`$ except $`d=p`$, and $`p`$-channel numerator $`p!-1`$. |
| Weighted projection rigidity | Checked | If $`Z\equiv T\pmod R`$, $`Q_i\mid R`$, and $`Z\le B<Q_i`$, then unequal residues $`T\bmod Q_1`$ and $`T\bmod Q_2`$ exclude that endpoint. |
| Factor-split projection reduction | Checked | Two divisor factors of one private modulus support the same cancellation and disagreement bounds; coprime factors give a branch-free floor and may lie in one private quotient. |
| Zero plateau and first-exit carry | Checked | Grid threshold, plateau equality of grid integers, forced zero digit, carry $`b\in\{0,-1\}`$. |
| Prime-power prefix obstruction | Checked | Rationality forces $`p^k`$ to divide the strict successor at $`kp`$ whenever the factorial clears the denominator and $`p`$ is coprime to it. |
| Exact carry characterization | Checked | The normalized strict successors converge to $`S`$; $`S`$ is rational exactly when $`b_m=1`$ eventually, equivalently $`S`$ is irrational exactly when non-unit carries occur cofinally. |
| Explicit denominator bound | Checked implication; exact finite certificate | Exact reduction gives $`60\nmid Z_{60}`$, $`64\nmid Z_{64}`$, and $`67\nmid Z_{67}`$. An exact GMP computation certifies all carries through $`300000`$ and $`b_{300000}\ne1`$; the Lean-checked carry theorem gives $`q\ge300000`$ in every rational representation $`S=a/q`$ with $`q>0`$. |
| Digits eventually zero $`\iff`$ $`S`$ rational | Returned derivation | Complete on the return; not yet kernel-checked here. |
| Factorial-gap lcm growth $`\gg N^{4/3}\log N`$ | Derived, source-verified | Derived below from a cited factorial-congruence theorem; not kernel-checked and not used as an input to any claim below. |
| Finite certificates ($`D=3`$, $`D=9`$, $`D\le12`$) | Verified finite instances | Each excludes only the denominators it names. |
| Unbounded strict nonvanishing | Open | Required to turn the channel rounding argument into an irrationality proof. |

<a id="sec:digits"></a>

# Canonical factorial digits

Write $`\theta_0=\{x\}=x-\lfloor x\rfloor`$ and, for $`m\ge1`$,
``` math
d_m=\lfloor m\,\theta_{m-1}\rfloor,
  \qquad
  \theta_m=m\,\theta_{m-1}-d_m .
```
This is the factorial base taken in its canonical form. The kernel checks the floor formula, the digit bounds $`0\le d_m<m`$, the recurrence $`\theta_{m+1}=(m+1)\theta_m-d_{m+1}`$, the finite telescoping expansion
``` math
x=\lfloor x\rfloor+\sum_{m=2}^{N}\frac{d_m}{m!}
   +\frac{\theta_N}{N!},
```
and the propagation rule: a zero remainder at one index forces every later digit to vanish. These are *canonical digit eq floor mul remainder*, *canonical digit nonneg*, *canonical digit lt radix*, *canonical remainder recurrence*, the [finite factorial expansion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/CanonicalFactorialDigits.lean#L196), and the [zero-remainder termination theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/CanonicalFactorialDigits.lean#L269); they hold for every real $`x`$, not only for $`S`$.

The rational direction is also kernel-checked. If $`q>0`$ and $`q\le n`$, then
``` math
\operatorname{facFloor}(a/q,n)=((n!/q):\mathbb{Z})a,
```
and the canonical digit at radix $`n+1`$ vanishes. These are the [cleared-floor formula](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/CanonicalFactorialDigits.lean#L47) and the [rational-input termination theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/CanonicalFactorialDigits.lean#L81). They imply that every rational input has an eventually zero canonical factorial-digit expansion. They do not decide whether $`S`$ is rational and supply no recurrence estimate for its digits or remainders.

The returned derivation additionally gives the converse for this particular representation: the digits $`d_m(S)`$ are eventually zero only if $`S`$ is rational, equivalently the factorial tail state is eventually integral. That converse is not yet kernel-checked here, and nothing below uses it as though it were.

Note what the criterion is not. Canonical normalisation is an exact reformulation of rationality. It does not by itself supply an obstruction, and a zero digit is not the same event as a zero-branch hit: the returned data contain canonical zero digits at $`m=5`$ and $`m=23`$, while the zero-branch list is empty through $`m=100000`$.

A second exact reformulation runs through a defect automaton. For a rational centre recurrence $`F_m=mF_{m-1}+1+\varepsilon_m-C_m`$, the kernel checks that the integer ceiling defect code equals $`\lfloor m\delta_{m-1}-\varepsilon_m\rfloor`$ and that $`\delta_m=m\delta_{m-1}-\varepsilon_m-q_m`$, with the specialisation $`\varepsilon_m=1/(m!-1)`$ written out. What is checked is the algebra of the automaton. Proving that the finite-sum residual centre satisfies the premise is a separate step and is not done.

A nearby floor criterion makes one tempting shortcut precise and also shows where it breaks. Koepf and Schmersau prove that eventual equality between the floors of $`n`$ times a partial sum and $`n`$ times its limit forces irrationality \[koepf-schmersau, Theorem 1.1, p. 117\]; their rational-term version obtains that equality from prefix integrality at a scale $`p_n`$ and the strict tail bound $`a-s_n<1/(np_n)`$ \[koepf-schmersau, Theorems 2.2–2.3, pp. 119–120\]. For the natural termwise clearing choice
``` math
p_n=\operatorname{lcm}\{k!-1:2\le k\le n\},
```
the last two denominators already show the obstruction:
``` math
p_n\ge
  \frac{(n!-1)((n-1)!-1)}{n-1},
```
because $`\gcd(n!-1,(n-1)!-1)=\gcd((n-1)!-1,n-1)\le n-1`$. For $`n\ge4`$, the first omitted summand $`1/((n+1)!-1)`$ is then already larger than $`1/(np_n)`$, so this natural $`p_n`$ cannot satisfy their tail hypothesis. Cancellation in the reduced prefix denominator could in principle give a smaller scale, but proving enough cancellation is another form of the present denominator problem. Thus the source supplies an exact comparison boundary, not a proof of Problem #68.

Duverney’s fast-series criteria fail at a different, equally exact boundary. His Theorem 3.1 assumes two-sided quadratic denominator growth $`cu_n^2\le u_{n+1}\le c'u_n^2`$, while for $`u_n=n!-1`$ one has $`u_{n+1}/u_n^2\to0`$ \[duverney, pp. 275, 285–286\]. The all-positive specialization in Corollary 3.2 additionally requires
``` math
\sum_n\left|\frac{u_{n+1}}{u_n^2}-1\right|<\infty,
```
whereas the summands tend to one here \[duverney, Corollary 3.2, p. 287\]. Neither criterion applies.

The sharp recent theorem of Barreto, Kang, Kim, Kovač, and Zhang has a similarly explicit ceiling. Its $`d=1`$ case proves irrationality of $`\sum_n1/a_n`$ when $`a_n^{1/2^n}\to\infty`$, whereas
``` math
(n!-1)^{1/2^n}\longrightarrow1
```
for the present choice $`a_n=n!-1`$ \[barreto-et-al, Theorems 2–3, pp. 2–4\]. The proof nevertheless identifies a useful exact criterion: Mahler’s elementary rationality floor is contradicted by prefix-clearing integers $`D_N`$ for which the cleared positive tails satisfy $`\liminf_ND_Nr_N=0`$ \[barreto-et-al, Lemma 8 and Proposition 12, pp. 6, 9–12\]. The ordinary product of the factorial-gap denominators is far too large for that estimate; a transfer would need a low-height clearing subsequence, or enough exact cancellation in their least common multiple. Thus the new theorem supplies a precise target inequality and adaptive-cutoff architecture, but not the missing arithmetic bound.

The ordinary factorial-series direction survives more usefully. Dividing the strict-successor recurrence $`Z_m=mZ_{m-1}+1-b_m`$ by $`m!`$ and telescoping gives the exact finite identity
``` math
\frac{Z_M}{M!}
  =\frac{Z_2}{2!}
   +\sum_{m=3}^{M}\frac{1-b_m}{m!}.
```
Thus the carry defects $`1-b_m`$ are genuine factorial-series coefficients. Hančl and Tijdeman give exact rationality classifications for polynomial coefficients and finite-difference criteria for broader ordinary factorial series \[hancl-tijdeman, Theorem 3.1 and Corollary 3.1, pp. 390–391\]. Their denominator is the cumulative linear product $`\prod_{n\le N}(an+b)`$, not the individual number $`N!-1`$. Applied to the display above, the classical Cantor–Oppenheim criterion still needs $`1-b_m\ne0`$ infinitely often—precisely the missing cofinal non-unit-carry assertion that remains open. The identity is therefore a rigorous literature bridge, not a hidden solution.

<a id="sec:channels"></a>

# Finite channel congruences and the LCM obstruction

Fix $`d\ge2`$. The kernel proves the divisibility
``` math
(d!)^{\lfloor i/d\rfloor}\ \Big|\ i!
  \qquad(i\ge0),
```
defines the integral channel weight $`W_{d,i}`$ obtained by cancelling that factor, and checks the exact cancellation. It also checks the consecutive channel event
``` math
n\,W_{d,n-1}-W_{d,n}=0
  \qquad\text{whenever } d\nmid n .
```
So the channel weight is arithmetically inert except at multiples of $`d`$. The formal statements are *factorial pow floor dvd factorial*, *channel weight mul denominator*, and *channel event eq zero of not dvd*.

Let $`\lambda`$ be a finitely supported integer vector on indices $`n\ge2`$, let $`M=M(\lambda)`$ be its factorial moment, and let $`V_{d}(\lambda)`$ be the $`d`$-th channel numerator. The kernel checks two facts about them.

<div id="res:congruence" class="theorem">

**Theorem 2** (channel congruence). *For every finite integer support and every $`d\ge2`$,
``` math
V_{d}(\lambda)\equiv M(\lambda)\pmod{d!-1}.
```
Consequently $`d!-1`$ divides $`M(\lambda)-V_{d}(\lambda)`$, a vanishing $`d`$-th channel forces $`(d!-1)\mid M(\lambda)`$, and annihilating every channel $`2\le d\le D`$ forces
``` math
L_D=\operatorname{lcm}_{2\le d\le D}(d!-1)\ \Big|\ M(\lambda).
```*

</div>

<div id="res:normalform" class="theorem">

**Theorem 3** (integral normal form). *For every finite integer support and every $`d\ge2`$ there is an integer $`k`$ with $`V_{d}(\lambda)=M(\lambda)+(d!-1)k`$.*

</div>

Theorem <a href="#res:normalform" data-reference-type="ref" data-reference="res:normalform">3</a> is the sharper of the two for design purposes. It says that every zero-moment variation of the support changes the normalised $`d`$-th channel contribution by an integer only. Zero-moment variations therefore cannot manufacture an extra fractional cancellation coordinate: the congruence forces every normalised channel defect to be integral.

Theorem <a href="#res:congruence" data-reference-type="ref" data-reference="res:congruence">2</a> is an obstruction rather than a source of cancellation. Any finite family that kills the low channels must have moment divisible by $`L_D`$, and $`L_D`$ grows faster than the tail shrinks. The returned analysis proposes the quantitative form
``` math
\log \operatorname{lcm}_{2\le n\le N}(n!-1)\ \gg\ N^{4/3}\log N
  \qquad(N\to\infty).
```
For the derivation from the cited multiplicity theorem, put
``` math
Q_N=\prod_{2\le n\le N}(n!-1),
  \qquad
  L_N=\operatorname{lcm}_{2\le n\le N}(n!-1).
```
For an odd prime $`p`$, let $`m_p`$ count the indices $`2\le n\le N`$ for which $`p\mid n!-1`$. Such an index necessarily satisfies $`n<p`$. The factorial congruence multiplicity estimate of Garaev, Luca, and Shparlinski \[garaev-luca-shparlinski, arXiv v1, Thm. 12, p. 16\], applied on the interval $`1\le n\le\min(N,p-1)`$, therefore gives $`m_p\ll N^{2/3}`$. (The prime $`2`$ divides none of these factors.) If
``` math
E_p=\max_{2\le n\le N}v_p(n!-1),
```
then
``` math
\log Q_N
  =\sum_p\sum_{n=2}^{N}v_p(n!-1)\log p
  \le \bigl(\max_p m_p\bigr)\sum_p E_p\log p
  \ll N^{2/3}\log L_N .
```
On the other hand, Stirling summation gives $`\log Q_N\asymp N^2\log N`$, proving the displayed lower bound for $`\log L_N`$. The source states the multiplicity theorem, not this lcm corollary; the latter is derived here and is not kernel-checked. It is recorded because it is the shape of the obstruction the returns describe, and it is used nowhere below.

The primitive lcm divisibility after cofactor removal is factorial valuations do not remove the obstruction once every common cofactor divisor has been removed. A separate corank-one cofactor/determinant argument for constructing such primitive kernels remains advisory pending Lean formalisation; the divisibility theorem does not establish that construction.

<a id="sec:translator"></a>

# A two-term prime channel corrector

The channel obstruction raises a natural question: can a finite support affect exactly one channel? The following two-term construction does so.

<div id="res:translator" class="theorem">

**Theorem 4** (two-term prime channel corrector). *Let $`p`$ be prime and take the coefficient–index pair $`(p,-1)`$ on the indices $`(p-1,p)`$. Then the factorial moment is $`0`$; every channel $`d<p`$ vanishes, by the exact quotient identity $`\lfloor(p-1)/d\rfloor=\lfloor p/d\rfloor`$; every channel $`d>p`$ vanishes, because both indices lie below $`d`$; and the $`p`$-channel numerator is exactly $`p!-1`$.*

</div>

The theorem holds for every prime, not merely for sampled primes. Its use is arithmetic rather than analytic: it supplies, at cost zero in the moment, a unit in the $`p`$-channel. Adding an integer multiple of this corrector to any candidate kernel shifts the $`p`$-channel numerator by multiples of $`p!-1`$ and leaves every other channel and the moment untouched.

The consequence is already uniform in the support location. For every channel rank and every prescribed cutoff, Lean constructs a factorial-grid kernel and a remote prime-corrector pair entirely beyond that cutoff, with all requested low channels zero, nonzero factorial moment, and residual in $`[-1/2,1/2]`$; see *exists remote factorial grid prime translator reduction*. What is not available is strict nonvanishing: nothing proved here rules out the rounded residual being exactly zero, and no cofinal family with a strictly nonzero rounded residual has been produced. This is the most direct remaining hypothesis, stated in §<a href="#sec:open" data-reference-type="ref" data-reference="sec:open">9</a>.

<a id="sec:plateau"></a>

# Zero plateaux, first exit, and denominator bounds

A second, independent route works on the rational grid rather than on channels. Let $`H`$ be a partial sum and $`q`$ a candidate denominator. The kernel checks the algebraic grid threshold: writing $`qH=k+r`$ and $`q(S-H)=u`$, the next $`q^{-1}`$ grid point $`(k+1)/q`$ lies below $`S`$ exactly when $`1\le r+u`$. It also checks the factorial plateau theorem: if $`H<G\le S`$, if $`n!G`$ is integral, and if $`n!(S-H)<1`$, then the strict successor of $`n!H`$ and the canonical floor of $`n!S`$ are the same grid integer.

Two rigidity statements follow. Consecutive plateau floors, scaled by the next radix, force the canonical factorial digit to vanish. And any first-exit offset $`\delta\in[0,2)`$ with carry $`b=-\lfloor\delta\rfloor`$ satisfies $`b\in\{0,-1\}`$: the exit is rigid, with exactly two alternatives.

The first-crossing argument continues from the exit to a denominator lower bound. For a rational grid level $`G`$, suppose that $`\tau`$ is its first crossing by the literal partial sums and write
``` math
G-H_{\tau-1}=\frac{a}{v},\qquad a,v>0.
```
Then $`v\ge\tau!-1`$. On the $`-1`$ exit branch this strengthens to $`v\ge\tau!(\tau!-1)`$. No coprimality hypothesis on $`a`$ and $`v`$ is required.

There is also a direct obstruction at prime indices. Let
``` math
H_m=\sum_{2\le n\le m}\frac1{n!-1},\qquad
  Z_m=\lfloor m!H_m\rfloor+1,
```
and let $`\Delta_m`$ be the distance from $`(m-1)!H_{m-1}`$ to its strict integer successor. The kernel checks, for $`m\ge3`$, the exact criterion
``` math
m\mid Z_m
  \quad\Longleftrightarrow\quad
  1+\frac1{m!-1}<m\Delta_m\le2+\frac1{m!-1}.
```
If $`S=a/q`$ with $`q>0`$, then for every prime $`p>q`$ the tail bound forces $`p\mid Z_p`$. Consequently, one exact missed prime $`p`$ implies $`q\ge p`$. The rational implementation of $`Z_p`$ agrees with the real-floor definition, and exact kernel reduction gives $`11\nmid Z_{11}`$. Thus every rational representation of $`S`$ has denominator at least $`11`$.

The all-index recurrence is stronger. Define its exact carry by
``` math
Z_m=mZ_{m-1}+1-b_m .
```
If $`S=a/q`$ and $`m-1\ge q`$, the plateau theorem identifies
``` math
Z_{m-1}=\frac{(m-1)!}{q}\,a,\qquad
  Z_m=\frac{m!}{q}\,a=mZ_{m-1},
```
so necessarily $`b_m=1`$. Hence one exact non-unit carry at index $`m`$ forces $`q\ge m`$. Conversely, if $`b_m=1`$ eventually, then $`Z_m/m!`$ is eventually constant. The one-cell bound
``` math
H_m<\frac{Z_m}{m!}\le H_m+\frac1{m!}
```
and the exact tail estimate show that $`Z_m/m!\to S`$; hence that eventual constant is $`S`$ and is rational. Thus
``` math
S\notin\mathbb Q
  \quad\Longleftrightarrow\quad
  (\forall B)(\exists m>B)\ b_m\ne1.
```
The full Erdős problem is now reduced without loss to producing those cofinally many non-unit carries. Exact rational normalization gives
``` math
60\nmid Z_{60},\qquad 64\nmid Z_{64},\qquad 67\nmid Z_{67}.
```
At $`m=60`$ the recurrence also proves $`b_{60}\ne1`$, and hence $`q\ge60`$. Since $`67`$ is prime, the prime-miss theorem applied at $`67`$ gives the stronger checked bound
``` math
S=\frac aq,\ q>0 \quad\Longrightarrow\quad q\ge67.
```

There is a second, more arithmetic mechanism at doubled prime indices. For every odd prime $`p`$, the kernel now specializes the strict-successor prime-power criterion to the literal prefixes:
``` math
p^2\mid Z_{2p}
  \quad\Longleftrightarrow\quad
  \bigl(b_{2p}=1\ \text{and}\ p\mid Z_{2p-1}\bigr)
  \ \text{or}\
  \bigl(b_{2p}=1+p\ \text{and}\ p\mid 2Z_{2p-1}-1\bigr).
```
Consequently, failure of both displayed branches for a cofinal family of odd primes proves $`S`$ irrational. This is a sharper two-stage target than a bare square nondivisibility assertion: it exposes separately the only two carry values and predecessor residues that can survive. It remains a criterion, not the missing cofinal input.

The formal theorem is not restricted to those hand-reduced indices. A separately implemented exact GMP integer computation certifies all $`299998`$ carry cells for $`3\le m\le300000`$. Its unit carries occur exactly at
``` math
52,\ 591,\ 1030,\ 1407,\ 1438,\ 2164,\ 4258,\ 10991,\ 21236,
```
so no further unit carry occurs through the endpoint, where $`b_{300000}\ne1`$. Feeding that exact finite fact to the non-unit-carry theorem strengthens the bound to
``` math
S=\frac aq,\ q>0 \quad\Longrightarrow\quad q\ge300000.
```
The computation uses no floating-point arithmetic; its canonical payload, Python driver, and GMP backend are hash-bound in the companion research packet. This remains a finite exclusion. The new target is to rule out an eventual all-unit carry tail.

There is also a finite peeling identity. For $`x\ne0,1`$ and $`K\ge0`$,
``` math
\frac1{x-1}
  =\sum_{j=1}^{K}\frac1{x^j}
   +\frac1{x^K(x-1)}.
```
When $`x=k!`$ and a chosen factorial scale is divisible by $`(k!)^K`$, the scaled finite sum is integral and only the last term retains the factor $`k!-1`$ in its denominator. The identity isolates one residual fraction before exact bounding; it does not yet give a cofinal family of nonzero residuals.

One proposed strengthening is false and is recorded as such: the divisibility $`(m!-1)\mid\operatorname{den}(V_m)`$ fails at the reported strict events $`m=52`$ and $`m=591`$. Only the Archimedean first-crossing lower bound survives.

<a id="sec:projection"></a>

# Weighted projection rigidity

The third formal layer converts modular disagreement into exclusion.

<div id="res:projection" class="theorem">

**Theorem 5** (projection rigidity). *Suppose the natural endpoint numerator $`Z`$ is congruent to a weighted numerator $`T`$ modulo $`R`$. Then every divisor $`Q`$ of $`R`$ with $`Z\le B<Q`$ satisfies $`T\bmod Q=Z`$. Consequently two divisors $`Q_1,Q_2>B`$ with unequal projected residues exclude any such bounded endpoint; and unequal projections force $`\min(Q_1,Q_2)\le T`$.*

</div>

The leave-one-out specialisation $`Q=R/r`$ also follows. More generally, let $`a,b`$ divide $`R`$ and take the complementary projection moduli $`R/a`$ and $`R/b`$. Lean checks the same quotient cancellation and collision-cap comparison for these factor projections. If $`\gcd(a,b)=1`$, then $`\operatorname{lcm}(R/a,R/b)=R`$, and the resulting branch-free factor-pair floor is at most the global complementary residue. The factors $`a,b`$ may both divide one private quotient. Thus the reduction needs no analytic input and no pair of distinct denominator indices, only suitable factors whose projections or factor-pair floor satisfy the stated bound. This is checked in *factorial block factor projection lcm eq private modulus* and *factorial block complementary factor pair floor le global*.

The transport to the literal factorial block is established directly rather than advisory. Lean builds the collision core $`C`$, private quotients $`r_i`$, private modulus $`R`$, and weighted numerator $`T`$ for the actual denominators $`i!-1`$, and proves both the endpoint congruence modulo $`R`$ and the required coprimality. Moreover, if $`m!-1`$ has canonical large prefix-private primes, then their complete prime-power product divides the single quotient owned by $`m`$ on the tailored block with parameter $`\lfloor m/2\rfloor+1`$, hence divides that block’s $`R`$.

The collision core itself has an exact incremental law. For the positive factorial-gap denominators, adjoining $`d_a`$ to an old finite family $`S`$ gives
``` math
C(S\cup\{a\})
 =\operatorname{lcm}\!\left(C(S),\,
     \gcd\!\left(d_a,\operatorname{lcm}_{j\in S}d_j\right)\right).
```
Indeed, finite-family gcd–lcm distributivity collapses the lcm of all pairwise gcds against $`d_a`$ to this single gcd. The same formula holds after adjoining the distinguished base; see *pairwise collision core insert gcd lcm* and *collision core insert gcd lcm*. Thus each step needs only the old denominator lcm and the old collision core, with no pairwise rescan.

There is also an exact product–lcm bound. If $`\widetilde C(S)`$ denotes the collision core after cancelling a positive distinguished base, while $`L(S)=\operatorname{lcm}_{j\in S}d_j`$ and $`P(S)=\prod_{j\in S}d_j`$, then Lean proves
``` math
\widetilde C(S)L(S)\mid P(S),
 \qquad\text{hence}\qquad
 \widetilde C(S)\le \frac{P(S)}{L(S)}.
```
See *collision core div base mul denominator lcm dvd denominator prod*. For the actual factorial block this specializes to
``` math
\operatorname{factorialBlockNormalizedCollisionCore}(p)
 \le
 \frac{\displaystyle\prod_{n\in I_p}(n!-1)}
      {\displaystyle\operatorname{lcm}_{n\in I_p}(n!-1)},
```
where $`I_p`$ is the block index set; see *factorial block normalized collision core le gap prod div gap lcm*. This is an exact quantitative bridge from lower estimates for the factorial-gap lcm to upper estimates for the normalized collision core. It does not itself close the local scale bound: one still needs cofinal estimates strong enough at the selected private factor and factorial scale. A fixed-modulus hit count alone does not supply such control.

The distinguished-base cancellation is now exact prime by prime. Writing $`B=(p-1)!`$ and $`C`$ for the unnormalised factorial-block collision core,
``` math
\widetilde C_p=\frac{\operatorname{lcm}(B,C)}{B}
 =\frac{C}{\gcd(B,C)},\qquad
 v_q(\widetilde C_p)=v_q(C)-\min\{v_q(B),v_q(C)\}.
```
See *collision core div base eq pairwise collision core div gcd*, *collision core div base factorization*, and *factorial block normalized collision core factorization*. Consequently $`q^e\mid\widetilde C_p`$ exactly when the pairwise core carries $`q^{e+v_q(B)}`$; in the factorial block this forces two distinct gaps to be divisible by that higher power. Lean moreover proves the sharp surviving valuation cap
``` math
v_q(\widetilde C_p)+v_q((p-1)!)<q.
```
Thus every support prime satisfies $`p-1<q(q-1)<q^2`$, and, whenever $`k(k-1)\le p-1`$, $`\widetilde C_p`$ is coprime to $`k!`$; see *factorial block normalized collision factorization add base lt prime*, *factorial block prime sq gt pred of dvd normalized collision core*, and *factorial block normalized collision core coprime factorial of mul pred le*. This removes every factorial channel below the moving square-root cutoff, but does not yet bound the aggregate product of the remaining large prime powers at the selected quotient, nor force the complementary projections or residues cofinally. It therefore supplies a stronger exact reduction, not an irrationality proof.

For collision estimates that already provide an upper-half hit, no exponent is lost to normalization. If $`q`$ divides a displayed factorial gap at some $`n\ge p`$, then $`q\nmid(p-1)!`$, and Lean proves for every $`e>0`$ that
``` math
q^e\mid\widetilde C_p\quad\Longleftrightarrow\quad q^e\mid C_p.
```
See *factorial block prime not dvd base of upper hit* and *factorial block prime power dvd normalized collision core iff of upper hit*. Combined with the two-hit theorem, this identifies every complete normalized upper-hit contribution with repeated full-power load in two distinct displayed gaps. The remaining arithmetic task is to aggregate those moving loads strongly enough for the normalized collision cap; this equivalence does not provide that estimate or the complementary-residue bound.

This bridge has an exact incidence-count form. For an upper-hit prime $`q`$ and every $`e>0`$, Lean proves
``` math
q^e\mid\widetilde C_p
 \quad\Longleftrightarrow\quad
 1<\#\{i\in I_p:q^e\mid i!-1\}.
```
See *factorial block prime power dvd normalized collision core iff one lt hit count*. Hence a source estimate giving at most one $`q^e`$-hit deletes that exponent from the normalized core and yields $`v_q(\widetilde C_p)<e`$; see *factorial block normalized collision core factorization lt of hit count le one*. The remaining problem is genuinely aggregate: obtain sufficiently uniform incidence bounds over all moving support primes and exponents, multiply the surviving valuation contributions, and still close the complementary-residue coordinate.

The local aggregation is now exact. For every upper-hit prime $`q`$, Lean proves
``` math
v_q(\widetilde C_p)
 =
 \#\left\{e\in[1,q-1]:
   1<\#\{i\in I_p:q^e\mid i!-1\}\right\};
```
see *factorial block normalized collision core factorization eq repeated hit layer count*. There is therefore no additional valuation loss between prime-power incidence estimates and the complete local collision exponent. The open step is to bound these layer counts uniformly as $`q`$ and $`p`$ move, then control the product over all surviving primes strongly enough for the normalized collision cap; this theorem does not supply that global estimate.

The same local load now has a distance-sensitive witness. Put $`B=(p-1)!`$. If $`q`$ is prime, $`e>0`$, and $`q^e\mid\widetilde C_p`$, Lean produces $`i<j`$ in $`I_p`$ such that
``` math
q^{e+v_q(B)}\mid i!-1,\qquad
 q^{e+v_q(B)}\mid j!-1,\qquad
 q^{e+v_q(B)}\le j^{\,j-i}.
```
See *exists factorial block hit pair with normalized prime power le gap pow*. Consequently, if
``` math
(2p-1)^d<q^{e+v_q(B)},
```
then some such two hits satisfy $`d<j-i`$; see *exists factorial block hit pair distance gt of endpoint pow lt normalized prime power*. The spacing hypothesis in that reduction is now discharged internally. If $`q`$ is prime, then any two $`q^e`$-hits $`i<j`$ satisfy $`e<j-i`$, without an endpoint or large-prime hypothesis; see *factorial block prime hit pair distance gt exponent*. The point is that $`q\mid j!-1`$ already forces $`j<q`$, while the preceding gap-power inequality converts this automatic size relation into strict separation. Consequently Lean proves the global primewise diameter ceiling
``` math
q\mid\widetilde C_p
 \quad\Longrightarrow\quad
 v_q(\widetilde C_p)+v_q((p-1)!)<2p-3
```
for every prime $`q`$ and $`p\ge2`$; see *factorial block normalized collision factorization add base lt block diameter*. The exponent-level version is *factorial block normalized collision exponent add base factorization lt block diameter*. Thus the earlier endpoint-prime estimate is a special case, and even primes already present in the normalization base pay for their base valuation inside the same block-diameter budget. This still does not control how many collision primes occur or the product of their bounded powers; those global estimates, together with the complementary-residue bound, remain open.

The pairwise statement is stronger than the selected-witness form used in that proof. For arbitrary $`q,e`$ and any displayed hits $`i<j`$, Lean proves
``` math
q^e\mid(i!-1),\quad q^e\mid(j!-1)
 \quad\Longrightarrow\quad q^e\le j^{\,j-i};
```
see *factorial block prime power le gap pow of two hits*. Consequently, when $`q`$ is prime and $`e>0`$, every two $`q^e`$-hits in the block—not just one chosen pair—satisfy $`e<j-i`$; see *factorial block prime hit pair distance gt exponent*. Every prime-power hit layer is therefore an $`e`$-separated subset of the block. Lean now proves the finite cardinality corollary itself:
``` math
(e+1)\#\{i\in I_p:q^e\mid i!-1\}\le 2p+e-2
```
for $`p\ge2`$, prime $`q`$, and $`e>0`$; see *factorial block prime power hit count mul succ le*. The unweighted packing step is therefore complete. What remains is to combine it with the exact repeated-layer valuation identity, sum the prime-power weights over all moving collision primes, and prove a global product bound strong enough for the normalized collision cap.

For an endpoint prime carrying one upper-half hit, Lean now performs the first combination exactly. If $`p\ge2`$, $`q`$ is prime, and $`2p-1<q`$, then
``` math
v_q(\widetilde C_p)
 =
 \#\left\{e\in[1,2p-4]:
   1<\#\{i\in I_p:q^e\mid i!-1\}\right\};
```
see *factorial block normalized collision core factorization eq truncated repeated hit layer count*. Thus every repeated-hit layer outside the block-diameter window has been removed from the exact local valuation formula. The remaining estimate is still global and weighted: these truncated layer counts must be aggregated over the moving endpoint primes strongly enough to bound their complete prime-power product, and the independent complementary-residue coordinate remains open.

The endpoint incidence criterion itself no longer needs a selected upper-half anchor. For every prime $`q>2p-1`$ and $`e>0`$, Lean proves
``` math
q^e\mid\widetilde C_p
 \quad\Longleftrightarrow\quad
 1<\#\{i\in I_p:q^e\mid i!-1\};
```
see *factorial block prime power dvd normalized collision core iff one lt hit count of endpoint lt base*. Thus an at-most-one $`q^e`$ incidence estimate forces $`v_q(\widetilde C_p)<e`$ without first choosing an upper hit; see *factorial block normalized collision core factorization lt of endpoint lt base of hit count le one*. At $`e=2`$ this gives the conditional squarefree conclusion $`v_q(\widetilde C_p)\le1`$; see *factorial block normalized collision core factorization le one of endpoint lt base of prime sq hit count le one*. More generally the endpoint inequality can be replaced by the exact condition $`q\nmid(p-1)!`$. For every such prime and every $`e>0`$, Lean proves the same hit-count equivalence; see *factorial block prime power dvd normalized collision core iff one lt hit count of not dvd base*. The at-most-one estimate cuts the normalized valuation below $`e`$, and its $`e=2`$ specialization gives conditional squarefreeness; see *factorial block normalized collision core factorization lt of not dvd base of hit count le one* and *factorial block normalized collision core factorization le one of not dvd base of prime sq hit count le one*. Every prime $`q\ge p`$ is absent from $`(p-1)!`$, so this covers the entire moving prime range at and above the block parameter. The result remains conditional: no theorem here supplies the uniform prime-square incidence premise or the global weighted product estimate. The squarefreeness premise is not proved. An exhaustive modular scan through $`q\le2{,}000{,}000`$ and $`n\le240`$ found four individual square hits and no prime with two such hits. Separately, all $`498{,}501`$ pairs $`2\le a<b\le1000`$ have squarefree $`\gcd(a!-1,b!-1)`$, and the aggregate squarefree-collision scan through $`p=499`$ stays below $`0.374`$ of the upper-descending-factorial logarithmic scale. These are finite exact computations, not theorem authority or an asymptotic incidence bound.

Cofinal prefix-private support itself is unconditional. Given any cutoff $`B`$, Lean chooses a prime $`q\ge B!+5`$, uses Wilson’s theorem to obtain $`q\mid(q-2)!-1`$, and takes the least factorial-gap hit $`m`$ of $`q`$. If $`m\le B`$, then $`q\le m!-1\le B!`$, a contradiction. Hence $`m>B`$; see *cofinal prefix private factorial gap hits*. A finite variant compares the product of a chosen set of primes, each at least $`5`$, with
``` math
\prod_{2\le k\le B}(k!-1).
```
If the prime product is larger, at least one chosen prime has no hit through $`B`$, while Wilson still bounds its least hit by $`q-2`$; see *exists late prefix private factorial gap hit of prime product lt*. These statements supply private factors, but they do not prove either scale estimate below. In particular, the unconditional construction gives no useful upper bound for $`q`$ in terms of its least hit $`m`$.

Wilson reflection also limits what can be inferred from a prime factor merely because it is linear in a later index. If $`n`$ is odd, $`n<q`$, and $`q\mid n!-1`$, then $`q\mid(q-n-1)!-1`$. When both indices lie in the same block and the reflected hit is earlier, equivalently $`q<2n+1`$, this repeated hit survives predecessor-factorial normalization and its full-block incidence count exceeds one; see *prime dvd reflected factorial gap of odd* and *prime dvd factorial block normalized collision core of odd reflection* and *one lt factorial block prime hit count of odd reflection*. Thus a linear-size divisor need not be private.

This warning applies to a genuine source theorem, not an inferred change of sign. Stewart states that for every $`\varepsilon>0`$ there are infinitely many odd $`n`$ whose least prime factor $`q`$ of $`n!-1`$ satisfies
``` math
n<q<
 \left(\frac{\sqrt{145}-1}{8}+\varepsilon\right)n;
```
the printed text explicitly transfers estimate (9) from $`n!+1`$ to $`n!-1`$ \[stewart2004, p. 464\]. Wilson reflection then supplies the earlier hit $`q\mid(q-n-1)!-1`$. The source controls $`q`$ relative to the later index $`n`$, but it does not control $`q`$ relative to the private first-hit index $`m`$. Accordingly it is collision-core input, not the missing private-anchor or global product estimate.

In fact one selected prime $`q`$ already furnishes the exact coprime factor pair $`(1,q)`$: its projection moduli are $`R`$ and $`R/q`$, whose least common multiple is $`R`$. Thus no second selected prime is needed; see *factorial gap large prefix private power modulus dvd tailored block private quotient* and *factorial gap large prefix private primes unit factor pair tailored block*. There is no hidden equality/disagreement branch in this specialization. Writing $`\rho`$ for the global complementary residue, Lean proves that the unit-pair floor is exactly
``` math
\min\{\rho,R/q\};
```
see *factorial block unit factor pair floor eq min*. Consequently the remaining factor-pair scale comparison must simultaneously beat the global complementary-residue coordinate and the local $`R/q`$ coordinate. After using $`L=CR`$, the latter is precisely the collision-cap comparison with the selected factor $`q`$, while the former is the global complementary-residue lower bound. Lean records this as the exact equivalence
``` math
(2p+1)L < 2p^2(2p-1)!\min\{\rho,R/q\}
 \quad\Longleftrightarrow\quad
 \begin{cases}
  (2p+1)L < 2p^2(2p-1)!\rho,\\
  (2p+1)Cq < 2p^2(2p-1)!,
 \end{cases}
```
see *factorial block unit factor pair floor scale iff*. Thus the factor reduction has no opaque floor premise left: the two surviving arithmetic estimates are exposed independently and neither follows merely from the existence of the selected prime. The irrationality implication also works for every natural block parameter at least three, not only prime parameters. What remains open is the arithmetic input. Wilson supplies cofinal prefix-private factors without analytic input. The stronger source-backed large-prime selection remains relevant because it supplies a positive-density family and a linear lower bound for $`q`$ relative to the original hit; neither result proves the global complementary-residue bound or the local collision-core bound. The surviving obligation is therefore to prove both sides of this exact branch-free scale split cofinally, packaged by *irrational factorial gap series of cofinal large prefix private unit scale split*.

<a id="sec:nogo"></a>

# What the returns rule out

The following are closed routes. They are part of the result, not caveats attached to it.

- Residue vectors, their recurrences, and window widths admit synthetic all-hit blocks. They cannot prove irrationality on their own.

- Known pointwise prime congruences, prime-dilation congruences, parity, and the exact prime coefficient formula admit a synthetic rational countermodel. A congruence family that a rational number could also satisfy decides nothing.

- Wilson quotients, harmonic sums, $`p`$-adic gamma identities, and factorial residues do not control the required Archimedean floor without an additional coupling theorem. Every prime-window test factors into a sharp Archimedean strict-ceiling condition and a modular divisibility condition, and the missing ingredient is the coupling between them, not more congruences.

- Fixed-denominator scalar canonical-product localisers and rank-saturated consecutive-jet Hermite–Padé systems pay the full factorial-gap denominator. For $`E(z)=\prod_{n\ge2}(1-z/n!)`$ the genus-zero product satisfies $`-E'(1)/E(1)=S`$, and the natural scalar linear form carries the coefficient $`Q_N=\prod_{2\le n\le N}(n!-1)`$, for which $`Q_N`$ times the tail diverges. Exact first-order interpolation, scalar residue weighting, the natural Wronskian, and rank-saturated consecutive jets all reassemble the same prohibitive denominator.

- Zero-moment variations cannot create an additional fractional cancellation coordinate (§<a href="#sec:channels" data-reference-type="ref" data-reference="sec:channels">3</a>), and factorial valuations cannot absorb the channel LCM obstruction.

- A fixed pair of low-index private owners cannot make the projection route cofinal. If the owner index $`n`$ is fixed and $`p>n!-1`$, then $`n!-1\mid(p-1)!`$, so its private quotient in the factorial block at $`p`$ is exactly one. Lean checks this uniformly in *factorial block private quotient eq one of gap lt* and checks the two-owner consequence in *factorial block fixed pair private quotients eq one*. Thus the large private quotients seen at small blocks—for example the factor $`719`$ owned at $`n=6`$—are finite-range phenomena. The factor-level reduction does not require two moving denominator indices: two factors inside one moving private quotient can suffice. It still requires selected nontrivial factors that escape with $`p`$.

<a id="sec:finite"></a>

# Finite certificates

The following are computations. Each excludes exactly the denominators it names and nothing more.

The finite-support vector $`\lambda=2e_3-e_4`$ has, by kernel check, $`V_2=0`$, factorial moment $`-12`$, $`V_3=-2`$, $`V_4=11`$, and $`V_d=-12`$ for every $`d\ge5`$. Under the exact rational tail enclosure $`1/119<\Theta_4<1/50`$, its residual lies strictly between $`-93/575`$ and $`-309/13685`$; in particular it is nonzero and subunit.

Exact integer regeneration verifies the canonical primitive kernels for every $`2\le D\le12`$: channels $`2`$ through $`D`$ vanish, the factorial moment is $`L_D`$, and the coefficient content is one. At $`D=9`$ the moment is $`L_9=31540008254514077395`$ and, after the stated prime-unit shift, $`1353/100000<R_9<1354/100000`$. At $`D=3`$ the vector $`c=(-40,55,-10,1)`$ on the support $`(3,4,5,6)`$ annihilates channels $`2`$ and $`3`$, has moment $`600`$, and satisfies
``` math
0.09925341997208298<L_3(c)<0.09925341997208300 .
```
This excludes denominators dividing $`600`$.

There are two different computations at the same endpoint. A returned interval computation reports the stronger geometric statement that no zero-branch event occurs at any $`m\le100000`$; its cited executable and source digest were not supplied, so that zero-branch classification remains external finite evidence. The strict-successor carry computation used above is local and independently regenerated: its exact source, GMP backend, canonical payload, and receipt digests form the certificate archive. The two claims must not be conflated. The local certificate establishes $`b_{300000}\ne1`$, and the checked theorem converts precisely that fact into $`q\ge300000`$.

None of these changes a quantifier.

<a id="sec:open"></a>

# The missing cofinal inputs

The exact frontier comes first:
``` math
S\notin\mathbb{Q}
 \quad\Longleftrightarrow\quad
 (\forall B)(\exists m>B)\;m\nmid Z_m
 \quad\Longleftrightarrow\quad
 (\forall B)(\exists m>B)\;b_m\ne1.
\tag{9.1}\label{eq:exact-frontier68}
```
This is a formal theorem, not a heuristic reduction. The remaining gap is quantified: the finite mechanisms in the preceding sections need one of the following cofinal inputs. The table separates those missing inputs from the formal results that would consume them.

<div class="center">

| Missing input | Available consequence | Present limitation |
|:---|:---|:---|
| Cofinal non-unit carries, or equivalently cofinal misses $`m\nmid Z_m`$ | Irrationality by <a href="#eq:exact-frontier68" data-reference-type="eqref" data-reference="eq:exact-frontier68">[eq:exact-frontier68]</a> | Only isolated finite misses are known. |
| Cofinal quantitative private-residue and collision-scale bounds | Endpoint exclusion on an unbounded family of prime blocks | Private-prime hits are qualitative; no required lower bound is proved. |
| Cofinal lower-endpoint escape or failure of both doubled-prime branches | A non-unit carry at each selected index | The relevant cylinder and branch theorems are conditional. |
| Cofinal strictly nonzero translated Cramer residuals | Remote finite channel cancellation without integral collapse | Rounding gives absolute value at most $`1/2`$, but the residual may be zero. |

</div>

Each problem below gives a sufficient input for <a href="#eq:exact-frontier68" data-reference-type="eqref" data-reference="eq:exact-frontier68">[eq:exact-frontier68]</a>; none is an equivalent reformulation.

<a id="weighted-collision-mass-and-the-complementary-residue"></a>

## 1. Weighted collision mass and the complementary residue

For the factorial block $`I_p=\{2,\ldots,2p-1\}`$, let $`\widetilde C_p`$ be the normalised collision core and put
``` math
h_{r,e}(p)=\#\{i\in I_p:r^e\mid i!-1\}.
```
The formal spacing bound is
``` math
h_{r,e}(p)(e+1)\le2p+e-2,
```
and on the relevant upper-hit or base-omitted support the complete local valuation is the repeated-layer count
``` math
v_r(\widetilde C_p)=\#\{e\ge1:h_{r,e}(p)>1\}.
```
Let $`M_p`$ denote the moving private modulus, let $`q\mid M_p`$ be the selected prefix-private factor, let $`L_p=\widetilde C_pM_p`$, and write $`\rho_p=(-T_p)\bmod M_p`$ for the least nonnegative complementary residue of the explicit reciprocal-tail numerator.

<div id="prob:weighted-collision68" class="problem">

**Problem 6** (weighted collision-product control). Prove on an unbounded family of tailored prime blocks both
``` math
\sum_r\#\{e:h_{r,e}(p)>1\}\log r
 <
 \log\!\left(
  \frac{2p^2}{2p+1}\,
  \frac{\prod_{j=p}^{2p-1}j}{q}\right),
\tag{9.2}\label{eq:weighted-collision68}
```
and the independent complementary-residue inequality
``` math
(2p+1)L_p<2p^2(2p-1)!\rho_p.
\tag{9.3}\label{eq:complementary68}
```
An average-over-$`p`$ theorem is admissible if its constants force these strict inequalities cofinally.

</div>

The first inequality is the local collision-core half of the exact factor-pair scale split; the second is its Archimedean half. A count of collisions without the weights $`\log r`$, a terminal Wilson event by itself, or a fixed finite scan does not answer the problem. Nor may reflected hits be discarded: the reflection theorem shows that they can contribute genuine collision primes.

<a id="nonterminal-prime-power-amplification"></a>

## 2. Nonterminal prime-power amplification

Write the reduced predecessor gap as
``` math
\Delta_n=\frac{u_n}{v_n},
```
and let $`B_n`$ be the repeated-support part of $`n!-1`$. The amplification modulus is
``` math
A_n=\prod_{\substack{q\mid B_n\\
             v_q(v_n)<v_q(n!-1)}}q^{v_q(n!-1)}.
```
Lean proves $`A_n\mid v_{n+1}`$ and, when $`A_n>1`$, that the new numerator has a nonzero projection modulo the whole product.

<div id="prob:amplification68" class="problem">

**Problem 7** (cofinal valuation amplification). Prove that there is $`\eta>0`$ and infinitely many genuinely nonterminal indices $`n`$ such that
``` math
\log A_n\ge\eta\log v_{n+1},
\tag{9.4}\label{eq:amplification-mass68}
```
or, closer to the endpoint criterion, that with $`m=n+1`$ and $`d=A_n`$,
``` math
\bigl((m+2)m!-2\bigr)v_m
 \le m^2(m!-1)(u_m\bmod d).
\tag{9.5}\label{eq:amplification-endpoint68}
```
Equivalently, establish an infinitude or quantitative frequency theorem for the exact first-order lift
``` math
q^2\mid n!-1
 \quad\Longleftrightarrow\quad
 \frac{k!-1}{q}+\frac{D-1}{q}\equiv0\pmod q,
 \qquad D=n(n-1)\cdots(k+1),
```
at repeated nonterminal hits $`q\mid k!-1`$ and $`q\mid n!-1`$.

</div>

Mere nonzero projection is insufficient: the least representative in <a href="#eq:amplification-endpoint68" data-reference-type="eqref" data-reference="eq:amplification-endpoint68">[eq:amplification-endpoint68]</a> must be of order roughly $`v_m/m`$. Fixed-modulus $`q`$-adic convergence and finitely many record events do not change the quantifier.

<a id="escape-from-the-lower-endpoint-interval"></a>

## 3. Escape from the lower endpoint interval

Let
``` math
\mathcal E_p=p!\sum_{n>p}\frac1{n!-1}.
```
The lower unit-carry branch is exactly
``` math
1+\frac1{p!-1}<p\Delta_p
 \le1+\frac1{p!-1}+\mathcal E_p,
 \qquad \mathcal E_p<\frac2p.
```

<div id="prob:lower-cylinder68" class="problem">

**Problem 8** (cofinal lower-endpoint escape). Prove for infinitely many primes $`p`$ that
``` math
1+\frac1{p!-1}+\frac2p\le p\Delta_p.
\tag{9.6}\label{eq:lower-cylinder68}
```
Equivalently, prove the integer inequality
``` math
\bigl((p+2)p!-2\bigr)v_p
 \le p^2(p!-1)u_p,
```
or a growing-modulus version with $`u_p`$ replaced by $`u_p\bmod d_p`$ for a specified divisor $`d_p\mid v_p`$.

</div>

Any positive answer yields a non-unit carry directly and proves irrationality. Congruence recurrences alone do not count: synthetic models satisfy the available congruences while remaining in the unit-carry branch. Nor is a zero canonical digit the same statement as membership in this narrow Archimedean cylinder.

<a id="failure-of-the-two-exact-doubled-prime-branches"></a>

## 4. Failure of the two exact doubled-prime branches

For every odd prime $`p`$, the specialisation is
``` math
p^2\mid Z_{2p}
 \quad\Longleftrightarrow\quad
 \begin{cases}
 b_{2p}=1\ \text{and}\ p\mid Z_{2p-1},\\
 \text{or}\\
 b_{2p}=1+p\ \text{and}\ p\mid2Z_{2p-1}-1.
 \end{cases}
\tag{9.7}\label{eq:double-prime68}
```

<div id="prob:double-prime68" class="problem">

**Problem 9** (cofinal doubled-prime branch failure). Prove that infinitely many odd primes $`p`$ satisfy simultaneously
``` math
\neg\bigl(b_{2p}=1\land p\mid Z_{2p-1}\bigr),
 \qquad
 \neg\bigl(b_{2p}=1+p\land p\mid2Z_{2p-1}-1\bigr).
\tag{9.8}\label{eq:double-branch-fail68}
```
A valid generalisation may replace $`2p`$ by $`kp`$ for one fixed $`k`$, provided it uses the checked unique-slot prime-power criterion.

</div>

Controlling only the predecessor residue or only the possible Archimedean carry does not meet the hypotheses; the theorem must couple them.

<a id="a-finite-cramer-block-across-floor-discontinuities"></a>

## 5. A finite Cramer block across floor discontinuities

For $`n,t\ge0`$, put $`s_n=((n+2)!)^2`$ and $`i_{n,t}(j)=(t+j)s_n`$ for $`0\le j\le n+1`$. Let $`A_{n,t}`$ be the $`(n+2)\times(n+2)`$ integer matrix whose first row is $`i_{n,t}(j)!`$ and whose row indexed by $`d\in\{2,\ldots,n+2\}`$ is
``` math
\frac{i_{n,t}(j)!}{(d!)^{\lfloor i_{n,t}(j)/d\rfloor}}.
```
This is the literal augmented factorial-grid channel/moment matrix. Let $`c_{n,t}`$ be its Cramer vector, and
``` math
N_d(n,t)=
 \det\!\bigl(A_{n,t}\text{ with its moment row replaced by the $d$-channel row}\bigr).
```
The determinant identities give
``` math
\mathcal R_{n,t}
 =\sum_{d>n+2}\frac{N_d(n,t)}{d!-1}
 =\det(A_{n,t})S+K_{n,t},
 \qquad K_{n,t}\in\mathbb{Z},
\tag{9.9}\label{eq:cramer-residual68}
```
and $`N_d(n,t)=\det(A_{n,t})\ne0`$ after the largest support index. The finite intermediate block crosses floor discontinuities and has genuine sign changes.

<div id="prob:cramer68" class="problem">

**Problem 10** (Cramer residual nonintegrality). Construct an unbounded family $`(n,t)`$ for which
``` math
\mathcal R_{n,t}\notin\mathbb{Z},
```
preferably by an exact certificate
``` math
0<
 \left|\mathcal R_{n,t}
   -\operatorname{round}(\mathcal R_{n,t})\right|
 \le\frac12,
```
or by the integral cofactor inequality
``` math
0<|N(I,D)|<\Delta(I,D),
\tag{9.10}\label{eq:cramer-minors68}
```
where $`\Delta(I,D)`$ is the gcd of the maximal minors.

</div>

A termwise sign assertion is not admissible: adjacent signs already change. Nor does simply asking for $`\det(A_{n,t})S\notin\mathbb{Z}`$ add information to the original scalar problem. A solution must use an exact determinant or finite-difference identity, a valuation or parity obstruction, a cancellation bound, or a gcd-of-minors argument controlling the finite oscillatory block.

Erdős #68 remains open. No statement above proves irrationality or excludes every rational value. The finite checked consequence is nevertheless unconditional: every rational representation with positive denominator has $`q\ge300000`$.

<a id="statements-and-declarations"></a>

# Statements and declarations

<a id="declaration-of-generative-ai-use."></a>

#### Declaration of generative AI use.

Every word of this manuscript was generated by agents based on large language models operating within Will Cook’s private research system for artificial intelligence. The formal proofs and repository software were likewise drafted and revised by the agents through that system under Cook’s direction. Cook set the objectives and acceptance criteria, selected and reviewed the public claims, and approved the published version. Cook assumes responsibility for the accuracy, interpretation, and presentation of the work. Generative systems are production tools, not authors, and supply no independent authority.

Lean does not authorise the exposition, the citation choices, or the interpretation, for which the author remains responsible. This manuscript is authored exposition, not Lean proof authority. The checked core is the canonical factorial digit kernel, the finite defect automaton algebra, floor-factorial channel arithmetic, the channel congruence and its integral normal form, the two-term prime corrector, weighted projection rigidity, the factor-split projection reduction, the fixed-index factorial-base absorption no-go, the rational-grid plateau and first-exit results, the first-crossing denominator bounds, and the literal-prefix prime obstruction through the exact $`p=11`$ instance, strengthened by the all-index eventual-unit-carry theorem and the exact reductions at $`m=60,64,67`$, the bound $`q\ge67`$, and the finite geometric peeling identity. It also checks the normalized strict-successor step and its finite factorial-series expansion in the carry defects $`1-b_m`$, the convergence $`Z_m/m!\to S`$, and the exact equivalence between irrationality and cofinally many non-unit carries. The exact GMP carry certificate through $`m=300000`$ is separately regenerated and hash-bound; combined with the checked carry theorem it gives $`q\ge300000`$, but it is not itself a Lean evaluation. The converse direction of the digit–rationality equivalence, the weighted primitive support decomposition, and the determinant-quotient reduction are returned derivations that have not been kernel-checked here, and are labelled as such wherever they appear. The factorial-gap lcm growth bound is derived here from the exact factorial-congruence multiplicity theorem of Garaev–Luca–Shparlinski \[garaev-luca-shparlinski, arXiv v1, Thm. 12, p. 16\]; it is source-verified, not a verbatim theorem of that paper, not kernel-checked here, and load-bearing for nothing above. The finite computations are finite.

<a id="app:sources"></a>

# Guide to the formal sources

The public `ErdosProblems.Erdos68` package contains the checked source for this note. The release snapshot contains twelve cited modules: `CanonicalFactorialDigits`, `ChannelBreakpointRigidity`, `ChannelIntegralCongruence`, `DivisorFactorialCentre`, `EndpointWeightedPrivateSupport`, `FactorialCarry`, `FactorialChannelCertificate`, `FactorialZeroPlateau`, `FiniteDefectAutomaton`, `PrimeUnitTranslator`, `PrimeZeroBranch`, and `StrictSuccessorArithmetic`. Only these public modules belong to the manuscript source surface; no private auxiliary digit-rigidity file is cited or projected. The release root imports every cited module. The declaration table below is pinned to the shared formal-source commit used throughout this problem-note series.

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L1090)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L953)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L6099)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L4766)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/PrimeUnitTranslator.lean#L1559)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L32)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L37)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L42)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L47)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L50)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L58)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L72)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L99)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L116)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L140)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L149)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L158)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L25)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L39)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L43)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L51)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L55)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L59)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L65)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L101)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L105)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L109)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L112)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L119)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L126)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L133)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L140)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L151)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/8c455842bcc5d17e861816391ec75e85e76a57d3/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L156)

<div class="thebibliography">

9

P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). T. F. Bloom, *Erdős Problem \#68*. <https://www.erdosproblems.com/68>, accessed 28 July 2026. M. Z. Garaev, F. Luca, and I. E. Shparlinski, *Character sums and congruences with $`n!`$*, Trans. Amer. Math. Soc. **356** (2004), no. 12, 5089–5102. <https://doi.org/10.1090/S0002-9947-04-03612-8>; arXiv:[math/0403422v1](https://arxiv.org/abs/math/0403422). C. L. Stewart, *On the greatest and least prime factors of $`n!+1`$, II*, Publ. Math. Debrecen **65** (2004), no. 3–4, 461–480. <https://publi.math.unideb.hu/paper/989/download/10_5486_PMD_2004_3190.pdf>. W. Koepf and D. Schmersau, *Irrationality of certain infinite series II*, Analysis **31** (2011), 117–124. <https://doi.org/10.1524/anly.2011.1094>. D. Duverney, *Irrationality of fast converging series of rational numbers*, J. Math. Sci. Univ. Tokyo **8** (2001), 275–316. <https://www.ms.u-tokyo.ac.jp/journal/pdf/jms080206.pdf>. J. Hančl and R. Tijdeman, *On the irrationality of factorial series*, Acta Arith. **118** (2005), no. 4, 383–401. <https://www.impan.pl/shop/en/publication/transaction/download/product/83588>. K. Barreto, J. Kang, S.-h. Kim, V. Kovač, and S. Zhang, *Irrationality of rapidly converging series: a problem of Erdős and Graham*, arXiv:[2601.21442v3](https://arxiv.org/abs/2601.21442v3), 2026.

</div>
