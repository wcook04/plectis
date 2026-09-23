<a id="optimal-sparse-perturbations"></a>

# Reading Eight Erdős Problems Together

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Let $`c>0`$ and let $`d\ge1`$ be an integer. For entire functions $`f(z)=\sum_{n\ge1}e_nz^n/n!`$ with nonnegative integer coefficients $`e_n\le n^c`$ eventually, each eventually divisible by every fixed integer, the vectors $`(f(1),\ldots,f^{(d-1)}(1))`$ have Hausdorff dimension $`\min(c,d)`$. They contain an open set exactly when $`c>d`$; at $`c=d`$ they are full-dimensional, null and meagre. A nonpolynomial such function with all these derivatives rational exists exactly when $`c>d`$. Multiplication and division by powers of $`z-1`$ give the matching construction and obstruction. We also study series values under restrictions on supports and congruences, using questions from seven irrationality problems of Erdős. Let $`Q_n`$ be positive integers with $`Q_n\mid Q_{n+1}`$ and $`Q_{n+1}\ge2Q_n`$, and let integer allowances $`F_n\ge0`$ satisfy $`\sum F_n/Q_n<\infty`$. Nonnegative integer digits bounded by $`F_n`$ eventually and eventually divisible by each fixed integer represent every nonnegative real exactly when $`Q_N\sum_{n>N}F_n/Q_n\to\infty`$; otherwise their values form a null meagre set. The positive construction also imposes eventual divisibility of cumulative digit sums. For factorial denominators and allowances $`n^c`$, with $`c>0`$, on a fixed infinite support, interval filling requires successive gaps to be eventually strictly smaller than $`c`$. For coprime $`a>b\ge1`$ with $`a^2>b^3`$, we prove irrationality of $`\sum_{n\in S}((a/b)^n-1)^{-1}`$ on every infinite divisibility chain $`S`$; eventually doubling chains give transcendence at every rational base greater than one. In contrast, every rational base between one and two admits rational values on infinite supports. At base two, a fixed-depth rational count and an exact late rejection separate finite survival from membership. Full proofs, method obstructions and the unsuccessful approaches are included. The main arguments are ordinary proofs, with formal ingredients and external results identified separately; no original Erdős problem is settled here.

<a id="sec:map"></a>

# From individual problems to reusable questions

Seven of the eight programmes ask whether a series is irrational: $`\sum(n!-1)^{-1}`$ in \#68, reciprocal sums of near-Sylvester sequences in \#243, $`\sum\varphi(n)2^{-n}`$ in \#249, $`\sum p_n2^{-n}`$ in \#251, $`\sum_{n\in S}(2^n-1)^{-1}`$ in \#257, reciprocal running least common multiples in \#269, and $`\sum(t^n-1)^{-1}`$ at rational $`t`$ in \#1049 \[erdosgraham1980; erdos1988\]. The eighth, \#1041, concerns polynomial lemniscates. It supplies no premise for the series arguments below.

What can the freedom to choose digits preserve, and when does arithmetic remove that freedom? Sparse corrections in the \#251 paper motivate the capacity criterion of Section <a href="#capacity:sec:criterion" data-reference-type="ref" data-reference="capacity:sec:criterion">3</a>. Its proof makes one interval of possible continuations work for every cumulative residue. The factorial examples show that the arithmetic restrictions change a sharp support-gap threshold. Factorial denominators $`n!`$ in this construction are not the denominators $`n!-1`$ in \#68.

Section <a href="#capacity:sec:jets-intro" data-reference-type="ref" data-reference="capacity:sec:jets-intro">2</a> asks whether a single factorial digit sequence can prescribe several derivatives independently. Theorems <a href="#capacity:thm:jets" data-reference-type="ref" data-reference="capacity:thm:jets">1</a> and <a href="#capacity:thm:rational-jets" data-reference-type="ref" data-reference="capacity:thm:rational-jets">2</a> give the sharp threshold and the dimension of the attainable vectors. The proof uses the scalar capacity theorem first, then a carry that preserves lower derivatives; Sections <a href="#capacity:sec:jets-proof" data-reference-type="ref" data-reference="capacity:sec:jets-proof">4</a> and <a href="#capacity:sec:rational-jets" data-reference-type="ref" data-reference="capacity:sec:rational-jets">5</a> give the argument and the rationality obstruction.

The common Lambert series in \#257 and \#1049 gives a second comparison in Section <a href="#sec:results" data-reference-type="ref" data-reference="sec:results">6</a>: a base below two permits rational subsums, while nested denominators force irrationality on certain thin supports. Neither interval filling nor a measure estimate decides whether one specified rational is a subsum at base two. Sections <a href="#sec:base2" data-reference-type="ref" data-reference="sec:base2">6.3</a> and <a href="#sec:misread" data-reference-type="ref" data-reference="sec:misread">8</a> explain that obstruction, including the exact computation that disproved a proposed stopping rule. Section <a href="#sec:second" data-reference-type="ref" data-reference="sec:second">7</a> retains the other method limits without claiming that they have one common cause.

The proofs presented here are ordinary mathematical arguments. Cited Lean results establish specified ingredients and quoted results, not the complete capacity classification or Lambert-chain theorem. The sources and originating review are credited in Section <a href="#capacity:sec:sources" data-reference-type="ref" data-reference="capacity:sec:sources">11</a>. Historical novelty and independent expert review are not established.

<a id="capacity:sec:jets-intro"></a>

# Prescribing a value and its derivatives

An integer factorial expansion can represent a real number while its digits eventually vanish modulo every fixed integer. Can the same digits prescribe several real quantities independently? Consider their exponential generating function. Its derivatives at $`1`$ are different weighted sums of the same digits, so this is simultaneous prescription, not several independent expansions.

For $`c>0`$, let $`\mathcal H_c`$ consist of the entire functions
``` math
\begin{gathered}
 f(z)=\sum_{n\ge1}e_n\frac{z^n}{n!},\qquad e_n\in\mathbb{Z}_{\ge0},\\
 e_n\le n^c\ \hbox{eventually},\qquad
 (\forall q\ge1)\ q\mid e_n\ \hbox{eventually}.
 \end{gathered}
```
Polynomial coefficient growth implies locally uniform convergence of every derivative. Put $`J_d(f)=(f(1),f'(1),\ldots,f^{(d-1)}(1))`$ and $`\mathcal J_{d,c}=\{J_d(f):f\in\mathcal H_c\}\subseteq\mathbb{R}^d`$. These are Hurwitz functions: all derivatives at $`0`$ are integers. Our restrictions concern those integers; the prescribed derivatives are at $`1`$.

<div id="capacity:thm:jets" class="theorem">

**Theorem 1** (Dimension and the sharp interpolation threshold). *For every $`c>0`$ and integer $`d\ge1`$,
``` math
\dim_{\mathrm H}\mathcal J_{d,c}=\min(c,d).
```
If $`c>d`$, this set contains a nonempty open subset of $`\mathbb{R}^d`$. If $`c\le d`$, it has $`d`$-dimensional Lebesgue measure zero and is meagre; these conclusions already follow from eventual evenness of the coefficients. The dimension lower bound and the open-set conclusion can both be realised with $`e_n\le n^c`$ at every position, an arbitrarily long initial zero segment, and congruence cutoffs common to the constructed family. The open set can be realised using only functions with eventually positive coefficients.*

</div>

<div id="capacity:thm:rational-jets" class="theorem">

**Theorem 2** (Rational derivatives force polynomiality). *Let $`d\ge1`$, and let
``` math
f(z)=\sum_{n\ge0}a_n\frac{z^n}{n!},\qquad a_n\in\mathbb{Z},\quad |a_n|=O(n^d).
```
Assume that, for each $`q\ge1`$, $`q\mid a_n`$ eventually. If $`f(1),f'(1),\ldots,f^{(d-1)}(1)`$ are all rational, then $`f`$ is a polynomial. Consequently, a nonpolynomial member of $`\mathcal H_c`$ with all these derivatives rational exists if and only if $`c>d`$.*

</div>

Thus if a nonpolynomial $`f\in\mathcal H_2`$ has rational $`f(1)`$, its derivative $`f'(1)`$ is irrational. Increasing the allowance to $`n^{2+\varepsilon}`$ permits both to be rational, for every $`\varepsilon>0`$. At $`c=2`$, the attainable pairs nevertheless form a full-dimensional null set. We do not assert that every vector is attained: nonnegative coefficients impose inequalities such as $`f'(1)\ge f(1)`$.

The identity behind the construction is
``` math
(z-1)\sum_{n\ge0}b_n\frac{z^n}{n!}
 =-b_0+\sum_{n\ge1}(n b_{n-1}-b_n)\frac{z^n}{n!}.
 \tag{J}\label{capacity:eq:jet-carry}
```
Adding the left-hand side to a function leaves its value at $`1`$ unchanged and changes its derivative there by $`\sum b_n/n!`$. Multiplication by $`(z-1)^k`$ leaves the first $`k`$ entries of the derivative vector unchanged, at a cost of $`k`$ powers of $`n`$ in the coefficient allowance. The scalar construction of Theorem <a href="#capacity:thm:capacity" data-reference-type="ref" data-reference="capacity:thm:capacity">3</a> supplies the free quantity. For necessity, eventual evenness reduces the number of prefixes by an exponential factor, which forces measure zero even at $`c=d`$. Section <a href="#capacity:sec:jets-proof" data-reference-type="ref" data-reference="capacity:sec:jets-proof">4</a> proves the theorem, including its dimension statement at the critical exponent. In the reverse direction, division by $`(z-1)^d`$ converts vanishing derivatives into bounded integer coefficients. Eventual divisibility then forces them to vanish; this proves Theorem <a href="#capacity:thm:rational-jets" data-reference-type="ref" data-reference="capacity:thm:rational-jets">2</a> in Section <a href="#capacity:sec:rational-jets" data-reference-type="ref" data-reference="capacity:sec:rational-jets">5</a>.

<a id="capacity:sec:criterion"></a>

# An exact capacity criterion

A factorial expansion usually permits a digit of size about $`n`$ at position $`n`$. If more digits are allowed, can most positions be discarded? What changes if each fixed integer must eventually divide every digit?

Let $`Q_n`$ be positive integers, $`n\ge1`$, such that $`Q_n\mid Q_{n+1}`$ and $`Q_{n+1}\ge2Q_n`$. Let $`F_n\in\mathbb{Z}_{\ge0}`$ satisfy $`\sum_nF_n/Q_n<\infty`$, and put
``` math
U_N=Q_N\sum_{n>N}\frac{F_n}{Q_n}.
 \tag{C}\label{capacity:eq:capacity}
```
Define $`E_Q(F)`$ to be the set of sums $`\sum_{n\ge1}e_n/Q_n`$, allowing nonnegative integer digits $`e_n\le F_n`$ eventually and requiring, for each fixed $`q\ge1`$, that $`q\mid e_n`$ eventually. The cutoffs and finite initial digits may depend on the represented value.

<div id="capacity:thm:capacity" class="theorem">

**Theorem 3**. *If $`U_N\to\infty`$, then $`E_Q(F)=[0,\infty)`$; otherwise $`E_Q(F)`$ is null and meagre. In particular interval filling is equivalent to $`U_N\to\infty`$. In the positive case, every nonnegative target may be represented with $`e_n=0`$ before any prescribed cutoff, at most one exception to $`e_n\le F_n`$, and
``` math
q\mid e_n,\qquad q\mid\sum_{k<n}e_k
 \quad\text{for all sufficiently large }n,
```
with congruence cutoffs depending on $`q`$ but independent of the target. If the allowance must hold at every position, a nondegenerate interval is still represented with both congruences and a common cutoff for each $`q`$.*

</div>

The criterion compares *all* future capacity with the prefix lattice. It requires no monotonicity, regular variation or gap bound on the allowances, and no upper bound on the denominator ratios. It does not require the $`Q_n`$ to clear every rational denominator. Section <a href="#capacity:sec:capacity-proof" data-reference-type="ref" data-reference="capacity:sec:capacity-proof">3.2</a> proves the theorem using the same residue-feedback mechanism already present in the public Lean repository. The capacity estimates and complete criterion are ordinary proofs; the abstract feedback endpoint is kernel-checked separately. Both geometric and factorial denominators satisfy the hypotheses.

<a id="the-sharp-support-threshold"></a>

## The sharp support threshold

Let $`S\subseteq\mathbb{N}_{\!>0}`$ and $`c>0`$. Define $`E(S,c)`$ to be the set of sums
``` math
x=\sum_{n\ge1}\frac{e_n}{n!},\qquad e_n\in\mathbb{Z}_{\ge0},\quad
 e_n=0\ (n\notin S),\quad e_n\le n^c\text{ eventually},
 \tag{1}\label{capacity:eq:class}
```
subject to
``` math
\text{for every }q\ge1,\qquad q\mid e_n\text{ for all sufficiently large }n.
 \tag{2}\label{capacity:eq:congruence}
```
The cutoffs and the finite initial digits in this definition may depend on $`x`$. All series converge, since finitely many unrestricted digits do not affect convergence. A permitted position need not carry a nonzero digit.

<div id="capacity:thm:main" class="theorem">

**Theorem 4**. *If $`S`$ is finite, $`E(S,c)`$ is countable. If $`S`$ is infinite, enumerate it as $`n_0<n_1<\cdots`$.*

1.  *For $`0<c\le1`$, $`E(S,c)`$ is null and meagre.*

2.  *For $`c>1`$, $`E(S,c)`$ contains a nondegenerate interval if and only if
    ``` math
    n_j-n_{j-1}<c\qquad\text{for all sufficiently large }j.
     \tag{3}\label{capacity:eq:gaps}
    ```
    If this condition fails, $`E(S,c)`$ is null and meagre.*

*When <a href="#capacity:eq:gaps" data-reference-type="eqref" data-reference="capacity:eq:gaps">[capacity:eq:gaps]</a> holds, one may require $`e_n=0`$ before any prescribed cutoff and impose both
``` math
q\mid e_n,\qquad q\mid\sum_{k<n}e_k
 \tag{4}\label{capacity:eq:both}
```
for all sufficiently large $`n`$, with cutoffs depending on $`q`$ but independent of $`x`$ throughout the constructed interval.*

</div>

The theorem is an ordinary mathematical proof. The associated formal sources check the general digit-feedback construction and, separately, the common-divisor carry obstruction of Section <a href="#capacity:sec:carry" data-reference-type="ref" data-reference="capacity:sec:carry">3.6</a>; they do not formalise this gap classification or its measure argument. The source and attribution account is in Section <a href="#capacity:sec:sources" data-reference-type="ref" data-reference="capacity:sec:sources">11</a>.

For example, with allowance $`n^2`$, every second position suffices without congruences. Under <a href="#capacity:eq:congruence" data-reference-type="eqref" data-reference="capacity:eq:congruence">[capacity:eq:congruence]</a>, infinitely many omitted positions already force a null set. With allowance $`n^{2.01}`$, every second position again suffices, even under <a href="#capacity:eq:both" data-reference-type="eqref" data-reference="capacity:eq:both">[capacity:eq:both]</a>. Thus the strict inequality in <a href="#capacity:eq:gaps" data-reference-type="eqref" data-reference="capacity:eq:gaps">[capacity:eq:gaps]</a> is essential.

<div id="capacity:cor:density" class="corollary">

**Corollary 5**. *For $`c>1`$, the least possible asymptotic density of a fixed permitted support that fills an interval under <a href="#capacity:eq:congruence" data-reference-type="eqref" data-reference="capacity:eq:congruence">[capacity:eq:congruence]</a> is $`1/(\lceil c\rceil-1)`$. Every such support has lower density at least this value, and an arithmetic progression attains it. A density bound alone is not sufficient: even rare gaps of length $`\lceil c\rceil`$ prevent interval filling if they occur infinitely often.*

</div>

<div class="proof">

*Proof.* Put $`d=\lceil c\rceil-1`$. Eventual gaps at most $`d`$ give $`\liminf_{N\to\infty}|S\cap[1,N]|/N\ge1/d`$. An arithmetic progression of step $`d`$ satisfies the theorem. ◻

</div>

<a id="capacity:sec:capacity-proof"></a>

## Proof of the capacity criterion

The necessity and sufficiency use different parts of the expansion. Prefixes supply an arithmetic obstruction; a common interval of possible future remainders makes the residue choices compatible with exact representation.

<a id="bounded-capacity-along-a-subsequence"></a>

### Bounded capacity along a subsequence

If $`U_N`$ does not tend to infinity, there are a constant $`B>0`$ and arbitrarily large $`N`$ with $`U_N\le B`$. Choose one integer $`q>B`$. Fix a cutoff $`K`$ after which the allowance and divisibility by $`q`$ hold, and fix the finite prefix, of value $`y_0`$. The set $`V`$ of resulting sums is compact by summability and the finite choices at each remaining position. For every such $`N>K`$,
``` math
V\subseteq y_0+\frac q{Q_N}\mathbb{Z}+[0,B/Q_N].
```
Indeed the scaled prefix after $`K`$ is a multiple of $`q`$ and the remaining tail is at most $`U_N/Q_N`$. These grids leave holes inside every fixed open interval for all sufficiently large selected $`N`$, so $`V`$ is nowhere dense. For a bounded interval $`J`$ they also give $`|V\cap J|\le(B/q)|J|+2B/Q_N`$. Passing to the subsequence and covering $`V`$ by finitely many intervals with total length at most $`|V|+\varepsilon`$ gives $`|V|\le(B/q)(|V|+\varepsilon)`$, hence $`|V|=0`$. A countable union over the cutoffs and integer prefixes covers $`E_Q(F)`$.

<a id="one-continuation-interval-for-every-cumulative-residue"></a>

### One continuation interval for every cumulative residue

Suppose $`U_N\to\infty`$ and put $`h_N=\inf_{k\ge N}U_k`$. For sufficiently large $`n`$, let $`M_n`$ be the largest factorial at most $`\min\{n,\sqrt{h_{\lfloor n/2\rfloor}}\}`$, and set the finitely many earlier moduli equal to one. These positive integers are nested under divisibility, tend to infinity, and are eventually divisible by each fixed integer. The delayed lower envelope controls the whole future cost of rounding, even when the denominator ratios are unbounded. Indeed, $`Q_N/Q_k\le2^{N-k}`$, so for sufficiently large $`N`$,
``` math
\begin{aligned}
 C_N:=Q_N\sum_{k>N}\frac{M_k}{Q_k}
 &\le\sqrt{h_N}\sum_{k=N+1}^{2N}2^{N-k}
       +\sum_{k>2N}k\,2^{N-k}\\
 &\le\sqrt{h_N}+(2N+2)2^{-N}.
 \end{aligned}
```
The first bound uses $`\lfloor k/2\rfloor\le N`$ when $`k\le2N`$; the second uses $`M_k\le k`$. Since $`U_N\ge h_N\to\infty`$ and $`M_N\le\sqrt{h_N}`$, this proves $`U_N-2C_N\ge M_N`$ for every sufficiently large $`N`$. Start beyond this point and any prescribed cutoff.

Keep only the active positions $`S=\{n:F_n\ge2M_n\}`$ after this cutoff. Define two common tail bounds
``` math
\alpha_N=\sum_{\substack{n>N\\n\in S}}\frac{M_n}{Q_n},\qquad
 \beta_N=\sum_{\substack{n>N\\n\in S}}\frac{F_n-M_n}{Q_n}.
```
Both are nonnegative and tend to zero. Discarding an inactive position loses less than $`2M_n`$; reserving both margins at an active position loses exactly $`2M_n`$. Thus the preceding estimate gives the decisive overlap inequality
``` math
Q_N(\beta_N-\alpha_N)\ge U_N-2C_N\ge M_N.
 \tag{O}\label{capacity:eq:overlap}
```
In particular the active set is infinite and each continuation interval has positive width.

Choose a target in $`[\alpha_{N_0},\beta_{N_0}]`$ and set all preceding digits to zero. Suppose the current unweighted cumulative sum is $`C`$ and the remaining target before position $`n`$ lies in $`[\alpha_{n-1},\beta_{n-1}]`$. At an inactive position choose zero. At an active position, the permitted digits in the residue class $`e\equiv-C\pmod{M_n}`$, $`0\le e\le F_n`$, form a nonempty arithmetic progression of step $`M_n`$. Its least digit is less than $`M_n`$ and its greatest digit exceeds $`F_n-M_n`$. By (O), the intervals
``` math
\frac e{Q_n}+[\alpha_n,\beta_n]
```
for these digits overlap. Their union contains
``` math
\left[\frac{M_n}{Q_n}+\alpha_n,
       \frac{F_n-M_n}{Q_n}+\beta_n\right]
   =[\alpha_{n-1},\beta_{n-1}].
```
Choose a digit whose interval contains the remaining target. The next remainder stays between $`\alpha_n`$ and $`\beta_n`$, and these bounds tend to zero, proving exact representation. This is precisely the common-interval feedback construction; no target-independent ordinary block sum is required.

After an active position $`n`$, the cumulative sum is divisible by $`M_n`$. Each later active digit is divisible by the previous active modulus, because both adjacent cumulative sums are; the moduli are nested. For a fixed $`q`$, take one active position with $`q\mid M_n`$. After that position, all individual digits and all preceding cumulative sums are divisible by $`q`$. This cutoff is common to all targets in the interval.

<a id="from-one-interval-to-every-nonnegative-target"></a>

### From one interval to every nonnegative target

The finite-exception convention in $`E_Q(F)`$ strengthens the conclusion. Given $`y>0`$, choose $`N`$ arbitrarily late with $`\alpha_N<y`$ and put
``` math
p=M_N\left\lfloor\frac{Q_N(y-\alpha_N)}{M_N}\right\rfloor.
```
Then $`p\ge0`$, $`M_N\mid p`$, and (O) gives $`y-p/Q_N\in[\alpha_N,\beta_N]`$. Set $`e_N=p`$ and all earlier digits to zero. Run the same continuation construction after $`N`$, with initial cumulative sum $`C=p`$; its interval covering worked for every $`C`$. All later digits obey their allowances. The zero target uses zero digits.

The congruence cutoffs can also be common to all $`y`$. For fixed $`q`$, choose an active position $`j`$ with $`q\mid M_j`$. If the target’s exceptional index $`N`$ precedes $`j`$, the repair at $`j`$ gives the required divisibilities after $`j`$. If $`N\ge j`$, all preceding digits are zero, $`q\mid M_N\mid p`$, and all subsequent repairs preserve divisibility by $`q`$. Thus $`j+1`$ is a valid cutoff for every target. The allowance-exception index itself may depend on the target. This completes Theorem <a href="#capacity:thm:capacity" data-reference-type="ref" data-reference="capacity:thm:capacity">3</a>.

The growth hypothesis has content. If repeated denominators are allowed, take $`Q_n=2^{\lfloor\sqrt n\rfloor}`$ and $`F_n=1`$. The allowance series converges, while $`U_N\ge\lfloor\sqrt N\rfloor`$ by counting the next complete denominator block. Yet eventual divisibility by two forces all sufficiently late digits to vanish, so the attainable set is countable. Imposing all cumulative congruences as well leaves only zero. Thus nestedness alone does not justify the criterion.

<a id="capacity:sec:negative"></a>

## Why a large gap prevents interval filling

The decisive obstruction is local. At a position $`N`$, the whole preceding factorial sum lies on a lattice of spacing $`1/N!`$. Eventual divisibility widens that spacing to $`q/N!`$, up to a fixed translation. After a sufficiently long gap, all remaining permitted digits reach only a bounded multiple of $`1/N!`$. Choosing one fixed $`q`$ larger than that bound leaves holes at arbitrarily small scales.

Here are the details, including the target-dependent cutoffs in (1)–(2). Put $`r=\lceil c\rceil`$. Suppose infinitely many successive $`S`$-gaps have length at least $`r`$, and let $`N`$ run through the positions immediately before these gaps. For large $`k`$,
``` math
\frac{(k+1)^c/(k+1)!}{k^c/k!}
 =\frac{(1+1/k)^c}{k+1}\le\frac12.
```
Consequently, for sufficiently large such $`N`$,
``` math
\begin{align}
 N!\sum_{\substack{k>N\\k\in S}}\frac{k^c}{k!}
 &\le 2N!\frac{(N+r)^c}{(N+r)!}\\
 &\le 2^{c+1}N^{c-r}\le B,\qquad B=2^{c+1}.
 \tag{5}\label{capacity:eq:tailbound}
\end{align}
```
In the second inequality we used $`N\ge r`$ and $`(N+1)\cdots(N+r)\ge N^r`$.

The bounded capacity along this subsequence invokes the necessity argument of Theorem <a href="#capacity:thm:capacity" data-reference-type="ref" data-reference="capacity:thm:capacity">3</a>, with allowances $`F_n=\lfloor n^c\rfloor`$ on $`S`$ and zero elsewhere. It gives nullity and meagreness even with target-dependent congruence and allowance cutoffs.

If $`c\le1`$, every support gap is at least $`r=1`$, so this proves the first part of Theorem <a href="#capacity:thm:main" data-reference-type="ref" data-reference="capacity:thm:main">4</a>. If $`c>1`$ and (3) fails, it proves the negative part. Notice that infrequent large gaps are enough; average digit counts do not detect this obstruction.

<a id="a-digit-that-also-corrects-the-cumulative-residue"></a>

## A digit that also corrects the cumulative residue

The following construction supplies the positive direction. It is useful beyond factorial weights.

<div id="capacity:lem:feedback" class="lemma">

**Lemma 6**. *Let $`w_j>0`$, let positive integers $`M_j`$ satisfy $`M_{j-1}\mid M_j`$, and let $`F_j\ge0`$. Suppose $`M_jw_j\to0`$ and, for $`j\ge1`$,
``` math
2M_j\le M_{j-1}\frac{w_{j-1}}{w_j},\qquad
 2M_{j-1}\frac{w_{j-1}}{w_j}\le F_j.
 \tag{7}\label{capacity:eq:step}
```
Every $`y\in[M_0w_0,2M_0w_0]`$ has a representation $`y=\sum_{j\ge1}b_jw_j`$ with integers $`0\le b_j\le F_j`$ such that
``` math
M_j\mid\sum_{i\le j}b_i,\qquad M_{j-1}\mid b_j.
```*

</div>

<div class="proof">

*Proof.* Start with residual $`R_0=y`$ and cumulative sum $`C_0=0`$. Suppose $`M_{j-1}w_{j-1}\le R_{j-1}\le2M_{j-1}w_{j-1}`$ and $`M_{j-1}\mid C_{j-1}`$. Put $`u=R_{j-1}/w_j`$ and let $`v`$ be the least nonnegative residue of $`-C_{j-1}`$ modulo $`M_j`$. Choose
``` math
b_j=v+M_j\left\lfloor\frac{u-M_j-v}{M_j}\right\rfloor.
 \tag{8}\label{capacity:eq:selector}
```
Since $`u\ge2M_j`$ and $`0\le v<M_j`$, this integer is nonnegative. The floor identity gives $`M_j\le u-b_j<2M_j`$; also $`b_j\le u\le F_j`$. Thus $`R_j=R_{j-1}-b_jw_j`$ lies in $`[M_jw_j,2M_jw_j)`$, while $`C_j=C_{j-1}+b_j`$ is divisible by $`M_j`$. The incoming modulus divides both $`C_{j-1}`$ and $`M_j`$, hence also $`b_j`$. Finally $`R_j\to0`$, so the partial sums converge to $`y`$. ◻

</div>

The residue in (8) may depend on $`y`$. Only the schedule of moduli needs to be common to all targets. Requiring target-independent ordinary block sums would impose an unnecessary restriction on the construction.

<a id="the-positive-direction-and-the-arithmetic-cost"></a>

## The positive direction and the arithmetic cost

Suppose $`c>1`$ and the support gaps are eventually at most $`d=\lceil c\rceil-1`$. Discard a finite prefix and write
``` math
r_j=\frac{n_j!}{n_{j-1}!},\qquad F_j=n_j^c,\qquad w_j=\frac1{n_j!}.
```
Then $`r_j\ge n_j\to\infty`$, while $`r_j\le n_j^d`$ and therefore $`F_j/r_j\ge n_j^{c-d}\to\infty`$. Define
``` math
h_j=\inf_{k\ge j}\min\left\{\frac{\sqrt{r_k}}2,
                                  \frac{F_k}{2r_k}\right\}.
```
This lower envelope is nondecreasing and tends to infinity. Begin sufficiently late that $`h_1\ge1`$, set $`M_0=1`$, and let $`M_j`$ be the largest factorial at most $`h_j`$. These moduli are nested and eventually divisible by every fixed integer. Moreover,
``` math
2M_j\le\sqrt{r_j}\le r_jM_{j-1},\qquad
 2r_jM_{j-1}\le F_j.
```
The second inequality uses $`M_{j-1}\le h_j`$, also valid for $`j=1`$. Finally, $`M_j/n_j!\le\sqrt{r_j}/(2n_j!)\le1/(2\sqrt{n_j!})\to0`$. Lemma <a href="#capacity:lem:feedback" data-reference-type="ref" data-reference="capacity:lem:feedback">6</a> fills $`[1/n_0!,2/n_0!]`$ using the positions $`n_j`$, $`j\ge1`$. Put zero digits elsewhere. Once $`q\mid M_J`$, all later digits and cumulative sums at the original integer indices have the divisibilities in (4). This proves the positive direction, including common cutoffs.

For comparison, remove condition (2) and call the resulting attainable set $`E_0(S,c)`$.

<div id="capacity:prop:unrestricted" class="proposition">

**Proposition 7**. *For an infinite support and $`c\ge1`$, $`E_0(S,c)`$ contains an interval exactly when its successive gaps are eventually at most $`\lfloor c\rfloor`$. Otherwise it is null and meagre. For $`0<c<1`$ it is always null and meagre.*

</div>

<div class="proof">

*Proof.* For necessity repeat Section <a href="#capacity:sec:negative" data-reference-type="ref" data-reference="capacity:sec:negative">3.3</a> with $`r=\lfloor c\rfloor+1`$. The bound in (5) now tends to zero. With lattice spacing $`1/N!`$, it is eventually bounded by $`1/(2N!)`$, so the same compact-set argument applies with $`q=1`$, $`B=1/2`$. For sufficiency, $`r_j\le n_j^c`$ along the support. The ordinary mixed-radix expansion using digits $`0\le b_j<r_j`$ fills $`[0,1/n_0!]`$. To see this directly, the maximum tail after $`n_j`$ is $`1/n_j!`$, since $`(r_k-1)/n_k!=1/n_{k-1}!-1/n_k!`$. The adjacent digit intervals therefore meet, and their lengths tend to zero. ◻

</div>

Thus the difference between the two gap thresholds occurs exactly at integer $`c`$. At $`c=m\ge2`$, imposing eventual congruences raises the least support density from $`1/m`$ to $`1/(m-1)`$. At $`c=1`$ it destroys interval filling entirely. With quadratic allowances, deleting only the positions $`2^k`$ destroys interval filling, although the permitted support still has density one. This is the simplest example of why support density loses decisive information. These statements concern intervals of values on a common permitted support; they are not lower bounds for representing one specially chosen value.

<a id="capacity:sec:carry"></a>

## A common-divisor test for irrationality

The distinction between small and large allowances also appears directly in rationality. Let $`b_n\ge2`$ be integers, put $`Q_0=1`$ and $`Q_n=b_1\cdots b_n`$, and consider a Cantor series.

<div id="capacity:thm:gcd" class="theorem">

**Theorem 8**. *Suppose $`0\le a_n\le A`$ and $`e_n\ge0`$ are integers, $`e_n\le Cb_n`$ eventually, and $`a_n+e_n`$ is nonzero infinitely often. If
``` math
\limsup_{n\to\infty}\gcd(b_n,e_n)=\infty,
```
then $`\sum_{n\ge1}(a_n+e_n)/Q_n`$ is irrational.*

</div>

<div class="proof">

*Proof.* For large $`n`$, the scaled tail satisfies
``` math
0<Q_n\sum_{k>n}\frac{a_k+e_k}{Q_k}\le A+2C.
```
Indeed, the bounded $`a_k`$ contribute at most $`A\sum_{j\ge1}2^{-j}=A`$, and $`e_k\le Cb_k`$ contributes at most $`C\sum_{j\ge1}2^{-(j-1)}=2C`$. If the total were $`p/D`$, the numbers
``` math
T_n=DQ_n\left(\frac pD-\sum_{k\le n}\frac{a_k+e_k}{Q_k}\right)
```
would be positive integers eventually bounded by $`D(A+2C)`$. No hypothesis that $`D\mid Q_n`$ is needed: the extra factor $`D`$ clears it. The recurrence
``` math
b_nT_{n-1}=D(a_n+e_n)+T_n
```
implies $`\gcd(b_n,e_n)\mid Da_n+T_n`$. The integer on the right is positive and eventually at most $`D(2A+2C)`$, contradicting the unbounded gcd. ◻

</div>

For factorial denominators, $`b_n=n`$, and eventual divisibility of $`e_n`$ by each fixed integer makes $`\gcd(n,e_n)`$ arbitrarily large arbitrarily late: choose a late multiple of that integer. Hence bounded nonnegative digits that are nonzero infinitely often cannot be rationalised by nonnegative $`O(n)`$ corrections satisfying (2). Conversely any allowance $`F(n)`$ with $`F(n)/n\to\infty`$ permits interval filling under (4): apply the positive construction with $`r_n=n`$, replacing $`n^c`$ by $`F(n)`$.

The arithmetic hypothesis cannot be replaced by $`b_n\to\infty`$, even if both congruences (4) are retained. Set $`a_n=1`$, $`e_1=2`$, and $`e_n=(n+1)!-n!`$ for $`n\ge2`$, and let $`b_n=e_n+2`$. Then $`\sum_{k\le n}e_k=(n+1)!`$, so (4) holds, and $`e_n<b_n`$. Nevertheless
``` math
\sum_{n\ge1}\frac{a_n+e_n}{Q_n}
 =\sum_{n\ge1}\frac{b_n-1}{Q_n}=1.
```
Here $`\gcd(b_n,e_n)\le2`$. This example separates rapid denominator growth from the arithmetic obstruction used in Theorem <a href="#capacity:thm:gcd" data-reference-type="ref" data-reference="capacity:thm:gcd">8</a>.

<a id="why-a-small-allowance-along-a-subsequence-is-insufficient"></a>

## Why a small allowance along a subsequence is insufficient

Without eventual congruences, the allowance $`F(n)=n-1`$ for $`n\ge2`$ gives the full interval $`[0,1]`$, whereas $`F(n)=o(n)`$ as $`n\to\infty`$ gives a null attainable set. The latter conclusion does not follow from small allowances merely along a subsequence, as the example below shows.

For the nullity assertion, eventually $`F(n)+1\le n/2`$ and $`F(n)\le n`$. Thus the number of prefixes through $`N`$ is at most $`C2^{-N}N!`$ for a fixed $`C`$, while the capacity after $`N`$ is at most $`\sum_{n>N}n/n!\le2/N!`$. The covering bound of Theorem <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a>(i), allowing zero-capacity levels to be omitted, tends to zero.

For the subsequence counterexample put $`F(2k)=0`$ and $`F(2k+1)=(2k)(2k+1)-1`$ for $`k\ge1`$, with $`F(1)=0`$. Then
``` math
\frac{F(2k+1)}{(2k+1)!}
 =\frac1{(2k-1)!}-\frac1{(2k+1)!}.
```
The total capacity is $`1`$, and the capacity after each permitted index $`2k+1`$ is exactly $`1/(2k+1)!`$, equal to the spacing between its choices. The interval criterion therefore gives every value in $`[0,1]`$, even though $`F(n)/n=0`$ at every even index. The exact telescoping identities and sample greedy expansions are reproduced by the script cited in Section <a href="#sec:misread" data-reference-type="ref" data-reference="sec:misread">8</a>; the interval conclusion follows from this argument, not from the samples.

<a id="capacity:sec:jets-proof"></a>

# Proof of the derivative interpolation theorem

Write $`(n)_r=n(n-1)\cdots(n-r+1)`$, with $`(n)_0=1`$ and $`(n)_r=0`$ for $`r>n`$. Then $`f^{(r)}(1)=\sum_n(n)_r e_n/n!`$.

<a id="nullity-at-and-below-the-critical-exponent"></a>

## Nullity at and below the critical exponent

Here only eventual evenness is needed. Fix a cutoff $`K`$ and a prefix before $`K`$, and allow every continuation with $`0\le e_n\le n^c`$ and $`2\mid e_n`$ for $`n\ge K`$. The derivative vectors form a compact set $`V`$. For all sufficiently large $`n`$, there are at most
``` math
\lfloor n^c/2\rfloor+1\le(3/4)n^c
```
choices at position $`n`$. Thus the number of prefixes through $`N`$ is at most $`C(3/4)^N(N!)^c`$. Every remaining derivative tail has norm at most $`C_{c,d}N^{c+d-1}/(N+1)!`$, by comparison with its first term. Balls of this radius, one for each prefix, cover $`V`$ with total $`d`$-dimensional volume at most
``` math
C'(3/4)^N(N!)^{c-d}N^{d(c+d-1)}.
```
For $`c\le d`$ this tends to zero. Hence $`V`$ is null and, being compact, nowhere dense. Countably many cutoffs and integer prefixes cover the attainable set. This proves both conclusions, including the critical case.

<a id="lifting-a-scalar-interval-to-an-open-set"></a>

## Lifting a scalar interval to an open set

First allow signed integer coefficients. For every $`\eta>0`$ and cutoff $`N\ge1`$, consider series supported on $`n\ge N`$ with $`|e_n|\le\eta n^c`$ and the same eventual divisibilities. We prove by induction on $`d`$ that their derivative vectors contain an open set whenever $`c>d`$. For $`d=1`$, apply Theorem <a href="#capacity:thm:capacity" data-reference-type="ref" data-reference="capacity:thm:capacity">3</a> to $`F_n=\lfloor\eta n^c\rfloor`$ and $`Q_n=n!`$, starting after $`N`$. The first tail term makes $`U_N\to\infty`$ when $`c>1`$; the all-position version gives an interval with common congruence cutoffs.

For the induction step, use dimension $`d-1`$ and exponent $`c-1`$ for $`B(z)=\sum b_nz^n/n!`$ with $`|b_n|\le(\eta/4)n^{c-1}`$ and $`b_n=0`$ before $`N`$. The higher derivative coordinates of $`(z-1)B`$ form an open set $`W\subseteq\mathbb{R}^{d-1}`$, because
``` math
((z-1)B)^{(r)}(1)=rB^{(r-1)}(1),\qquad r\ge1.
```
Choose $`y_0+[-2\rho,2\rho]^{d-1}\subset W`$. Choose a later cutoff $`M`$ so that every $`A`$ supported on $`n\ge M`$ with $`0\le a_n\le(\eta/2)n^c`$ has $`|A^{(r)}(1)|<\rho`$ for $`1\le r<d`$. This follows uniformly from the convergent derivative tails. The scalar theorem gives a nondegenerate interval $`I`$ of values $`A(1)`$. For each $`x\in I`$ choose one such $`A`$. For every $`y\in y_0+(-\rho,\rho)^{d-1}`$, a suitable $`B`$ cancels the higher coordinates of $`A`$ and gives $`y`$. Hence the attainable vectors contain
``` math
I^\circ\times\bigl(y_0+(-\rho,\rho)^{d-1}\bigr).
```
No continuous choice of $`A`$ is assumed: uniform smallness of all its higher derivatives makes the same cube work for every $`x`$. The coefficients of $`A+(z-1)B`$ obey the bound, since $`n|b_{n-1}|+|b_n|\le(\eta/2)n^c`$; divisibility holds term by term. The finitely many families in the induction have common cutoffs for each $`q`$.

To restore nonnegativity, choose nested positive integers $`m_n\to\infty`$ such that every fixed integer eventually divides $`m_n`$ and $`\log m_n=o(\log n)`$. One choice is the largest factorial at most $`\log(n+3)`$. For large $`n`$,
``` math
h_n=m_n\left\lfloor\frac{n^c}{2m_n}\right\rfloor,
 \qquad n^c/3\le h_n\le n^c/2.
```
Set earlier $`h_n`$ to zero and start the signed construction after that point. Take $`\eta=1/4`$. Adding $`\sum h_nz^n/n!`$ translates the open set and puts every sufficiently late coefficient between $`n^c/12`$ and $`3n^c/4`$. All coefficients lie between $`0`$ and $`n^c`$, and each function is nonpolynomial.

<a id="the-upper-bound-for-hausdorff-dimension"></a>

## The upper bound for Hausdorff dimension

Fix a finite prefix and an allowance cutoff. Through index $`N`$ there are at most $`\prod_{n\le N}(\lfloor n^c\rfloor+1)`$ continuations, whose logarithm is $`c\log(N!)+O(N)`$. Each derivative tail has norm at most $`O_{c,d}(N^{c+d-1}/(N+1)!)`$. For any $`s>c`$, the sum of the $`s`$-th powers of the diameters of these covering balls tends to zero. Countably many prefixes and cutoffs preserve this bound; the ambient bound is $`d`$.

<a id="a-separated-construction-attaining-the-dimension"></a>

## A separated construction attaining the dimension

For $`0\le k<d`$ with $`k<c`$, set $`\alpha_k=\min(1,c-k)`$. Use only these indices. Their sum is $`s=\min(c,d)`$. Let $`\varepsilon=2^{-d-6}`$ and use the same $`m_n`$. Independently for every $`n`$ and $`k`$, choose
``` math
b_n^{(k)}\in\left\{0,m_n,2m_n,\ldots,
 m_n\left\lfloor\frac{\varepsilon n^{\alpha_k}}{m_n}\right\rfloor\right\}.
 \tag{D}\label{capacity:eq:jet-digits}
```
All digits vanish before a large cutoff. Put
``` math
f(z)=\sum_n h_n\frac{z^n}{n!}
       +\sum_k(z-1)^k\sum_n b_n^{(k)}\frac{z^n}{n!}.
 \tag{F}\label{capacity:eq:jet-code}
```
The coefficient added at position $`n`$ is
``` math
\sum_k\sum_{j=0}^k(-1)^{k-j}\binom{k}{j}(n)_j b_{n-j}^{(k)},
```
with negative indices interpreted as zero. Its absolute value is at most $`\varepsilon\sum_{k<d}2^k n^c<n^c/4`$, since $`j+\alpha_k\le c`$. Thus $`f\in\mathcal H_c`$, with the allowance everywhere and common congruence cutoffs. Local uniform convergence makes the image of this product of finite digit sets compact.

The crucial step is to rule out cancellation between different codes. Suppose two codes first differ at index $`n`$, and let $`g`$ be their difference. For $`0\le r<d`$, take the Taylor coefficients of $`z^{-n}g(z)`$ at $`1`$:
``` math
[u^r](1+u)^{-n}g(1+u)
 =\frac{\Delta b_n^{(r)}}{n!}
   +\sum_{m>n}\sum_{k\le r}
       \frac{\Delta b_m^{(k)}}{m!}\binom{m-n}{r-k}.
 \tag{T}\label{capacity:eq:moving-taylor}
```
Unused coordinates are zero. The binomial coefficient now depends on $`m-n`$, not on $`m`$. Since $`|\Delta b_m^{(k)}|\le\varepsilon m`$, the absolute tail, multiplied by $`n!`$, is at most
``` math
\varepsilon\sum_{t\ge1}\frac{2^t}{(t-1)!}
 =2e^2\varepsilon<18\varepsilon<\frac12.
```
Here $`n!/(n+t-1)!\le1/(t-1)!`$ and $`\sum_{k\le r}\binom{t}{r-k}\le2^t`$. Some $`\Delta b_n^{(r)}`$ is a nonzero integer. Therefore one coordinate on the left of <a href="#capacity:eq:moving-taylor" data-reference-type="eqref" data-reference="capacity:eq:moving-taylor">[capacity:eq:moving-taylor]</a> has absolute value at least $`1/(2n!)`$. The linear map from $`J_d(g)`$ to those coordinates has norm at most $`C_dn^{d-1}`$: its entries are $`(-1)^j\binom{n+j-1}{j}/(r-j)!`$, $`0\le j\le r<d`$. Distinct codes first differing at $`n`$ consequently have separation at least
``` math
\delta_n=\frac{1}{2C_dn^{d-1}n!}
 \tag{S}\label{capacity:eq:jet-separation}
```
in the supremum norm of $`\mathbb{R}^d`$.

Give all choices in <a href="#capacity:eq:jet-digits" data-reference-type="eqref" data-reference="capacity:eq:jet-digits">[capacity:eq:jet-digits]</a> uniform independent probabilities. If $`A_N`$ counts prefixes through $`N`$, then
``` math
\log A_N=s\log(N!)+o(N\log N),
```
because $`\log m_n=o(\log n)`$ and each used $`\alpha_k`$ is positive. The separation makes the coding injective. A ball of radius less than $`\delta_N/2`$ meets at most one length-$`N`$ cylinder and has measure at most $`A_N^{-1}`$. For a small radius $`r`$, choose $`N`$ with $`\delta_{N+1}/2\le r<\delta_N/2`$. Since $`\log(1/\delta_{N+1})/\log(N!)\to1`$, for every $`t<s`$ this implies $`\mu(B(x,r))\le C_t r^t`$. Summing this inequality over any ball cover gives positive $`t`$-dimensional Hausdorff content. The dimension is at least $`s`$, completing Theorem <a href="#capacity:thm:jets" data-reference-type="ref" data-reference="capacity:thm:jets">1</a>.

<a id="capacity:sec:rational-jets"></a>

# The arithmetic threshold for rational derivatives

We prove Theorem <a href="#capacity:thm:rational-jets" data-reference-type="ref" data-reference="capacity:thm:rational-jets">2</a>. The coefficient estimate and the divisibilities are both needed, including at the critical exponent.

Suppose the first $`d`$ derivatives at $`1`$, starting with the value, are rational. Subtract their Taylor polynomial
``` math
P(z)=\sum_{r=0}^{d-1}\frac{f^{(r)}(1)}{r!}(z-1)^r
```
and choose a positive integer $`D`$ clearing its coefficient denominators. Then $`g=D(f-P)=\sum_{k\ge0}g_kz^k/k!`$ has integer coefficients, $`|g_k|=O(k^d)`$, and the same eventual divisibilities. Moreover $`g^{(r)}(1)=0`$ for $`0\le r<d`$. Thus $`B(z)=g(z)/(z-1)^d`$ is entire. Expansion at zero gives
``` math
B(z)=\sum_{n\ge0}b_n\frac{z^n}{n!},\qquad
 b_n=(-1)^d\sum_{k=0}^n\binom{n-k+d-1}{d-1}\frac{n!}{k!}g_k.
 \tag{Q}\label{capacity:eq:quotient-prefix}
```
In particular $`b_n`$ is an integer. Fix $`q`$, and choose $`K`$ so that $`q\mid g_k`$ for $`k\ge K`$. Those terms in <a href="#capacity:eq:quotient-prefix" data-reference-type="eqref" data-reference="capacity:eq:quotient-prefix">[capacity:eq:quotient-prefix]</a> are divisible by $`q`$. For each of the finitely many $`k<K`$, the factor $`n!/k!`$ is divisible by $`q`$ once $`n`$ is sufficiently large. Hence $`q\mid b_n`$ eventually as well.

The vanishing derivatives imply $`\sum_{k\ge0}R(k)g_k/k!=0`$ for every polynomial $`R`$ of degree less than $`d`$, because the falling factorials of orders $`0,\ldots,d-1`$ form a basis. Apply this to $`R(k)=\binom{n-k+d-1}{d-1}`$, interpreted as a polynomial. Its values at $`k=n+1,\ldots,n+d-1`$ vanish, and at $`k=n+j`$, $`j\ge d`$, they equal $`(-1)^{d-1}\binom{j-1}{d-1}`$. The complementary tail of <a href="#capacity:eq:quotient-prefix" data-reference-type="eqref" data-reference="capacity:eq:quotient-prefix">[capacity:eq:quotient-prefix]</a> therefore gives
``` math
b_n=n!\sum_{j\ge d}\binom{j-1}{d-1}\frac{g_{n+j}}{(n+j)!}.
 \tag{R}\label{capacity:eq:quotient-tail}
```
All series here converge absolutely. For large $`n`$, the absolute value is bounded by $`C`$ times the sum of
``` math
v_j=\binom{j-1}{d-1}\frac{n!(n+j)^d}{(n+j)!},\qquad j\ge d.
```
Their successive ratios satisfy
``` math
\frac{v_{j+1}}{v_j}
 =\frac{j}{j-d+1}\left(\frac{n+j+1}{n+j}\right)^d\frac1{n+j+1}
 \le\frac{d2^d}{n+1}.
```
For sufficiently large $`n`$ this is at most $`1/2`$, whereas $`v_d=n!(n+d)^d/(n+d)!`$ is bounded. Thus $`(b_n)`$ is bounded. Choose an integer $`q`$ larger than its eventual absolute bound. Eventual divisibility by this $`q`$ forces $`b_n=0`$ eventually. It follows that $`B`$, $`g`$ and $`f`$ are polynomials.

For the converse, when $`c>d`$, Theorem <a href="#capacity:thm:jets" data-reference-type="ref" data-reference="capacity:thm:jets">1</a> gives an open set of vectors realised by nonpolynomial members of $`\mathcal H_c`$. Every nonempty open subset of $`\mathbb{R}^d`$ meets $`\mathbb Q^d`$. This completes the proof of the sharp threshold.

<div class="remark">

*Remark 1* (Why the congruences cannot be omitted). The function $`(z-1)^de^z`$ has its first $`d`$ derivatives zero at $`1`$. Its integer factorial coefficients are
``` math
p_d(n)=\sum_{j=0}^d(-1)^{d-j}\binom dj(n)_j
       =n^d-\frac{d(d+1)}2n^{d-1}+O_d(n^{d-2})
```
for $`d\ge2`$; for $`d=1`$ they are $`n-1`$. Thus $`0\le p_d(n)\le n^d`$ eventually. Replacing the finitely many earlier coefficients, including the constant coefficient, by zero adds a rational polynomial. The resulting nonpolynomial function has nonnegative integer coefficients bounded by $`n^d`$ everywhere and all the specified derivatives rational. It fails the eventual divisibility assumption. Full dimension and even the growth bound alone therefore do not supply the arithmetic conclusion.

</div>

<a id="sec:results"></a>

# Lambert subsums across bases

For real $`t>1`$ and a set $`S`$ of positive integers put
``` math
X_S(t)=\sum_{n\in S}\frac{1}{t^n-1},\qquad
 w_n=\frac{1}{t^n-1},\qquad R_N=\sum_{n>N}w_n .
```
Problem \#257 asks whether $`X_S(t)`$ is irrational for every infinite $`S`$ at every integer $`t\ge2`$ \[erdosgraham1980, p. 62\]; Problem \#1049 asks about $`X_{\mathbb{N}_{>0}}(t)`$ at rational $`t`$.

The comparison behind everything is stated for weights with multiplicities. Let $`u_n>0`$ and integers $`D_n\ge1`$ satisfy $`\sum_nD_nu_n<\infty`$, and put
``` math
V=\Bigl\{\sum_{n\ge1}\varepsilon_nu_n:\ \varepsilon_n\in\{0,1,\dots,D_n\}\Bigr\},
 \qquad C_N=\sum_{n>N}D_nu_n .
```

<div id="thm:dichotomy" class="theorem">

**Theorem 9** (choices against contraction). *<span class="upright">(i)</span> For every $`N`$, the Lebesgue measure of $`V`$ is at most $`C_N\prod_{n\le N}(D_n+1)`$. If $`\liminf_NC_N\prod_{n\le N}(D_n+1)=0`$ then $`V`$ is null.*

*<span class="upright">(ii)</span> If $`u_n\le C_n`$ for every $`n>N_0`$, then for each choice of $`\varepsilon_1,\dots,\varepsilon_{N_0}`$ the set $`V`$ contains the interval $`[\mu,\mu+C_{N_0}]`$, where $`\mu=\sum_{n\le N_0}\varepsilon_nu_n`$.*

*<span class="upright">(iii)</span> For $`u_n=\beta^{-n}`$ with real $`\beta>1`$ and $`D_n=D`$, the bound in <span class="upright">(i)</span> tends to $`0`$ exactly when $`D+1<\beta`$, and the hypothesis of <span class="upright">(ii)</span> holds exactly when $`D+1\ge\beta`$.*

</div>

Part (ii) is Kakeya’s covering argument and part (i) is the standard covering bound; both are classical \[hornich1941; nitecki2013; fridy1966\], and Kovač and Tao give a scalar reciprocal-choice covering lemma \[kovactao2024, Lemma 5.1\]; their higher-dimensional approximation lemma is Lemma 7.2 of the same paper. We claim no novelty for Theorem <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a>. Its use here is to say which side each problem lies on.

<div id="thm:bases" class="theorem">

**Theorem 10** (the subseries across bases). *Let $`t>1`$ be real.*

*<span class="upright">(a)</span> If $`t<2`$, let $`N_0\ge0`$ be least with $`t^{-n}\le2-t`$ for all $`n>N_0`$. Then the set of values $`X_S(t)`$ is the union of the intervals $`[X_F(t),X_F(t)+R_{N_0}]`$ over $`F\subseteq\{1,\dots,N_0\}`$, where $`X_F(t)=\sum_{n\in F}w_n`$; in particular it contains $`[0,R_{N_0}]`$. If moreover $`t=a/b`$ in lowest terms, then every rational in $`[0,R_{N_0}]`$ whose reduced denominator shares a prime factor with $`ab`$ equals $`X_S(t)`$ for some $`S`$, and every such $`S`$ is infinite. There is an infinite $`S\subseteq\{2,3,\dots\}`$ with $`X_S(3/2)=1/2`$.*

*<span class="upright">(b)</span> If $`t=2`$, every value has exactly one $`S`$, and the set of values is a Cantor set of Lebesgue measure $`1`$ inside $`[0,E]`$, where $`E=\sum_{n\ge1}(2^n-1)^{-1}=1.6066951524\ldots`$.*

*<span class="upright">(c)</span> If $`t>2`$, the set of values is null.*

</div>

Part (b) is proved in the companion note on \#257, Section 7, from Hornich’s theorem as proved by Nitecki \[plectis257; hornich1941; nitecki2013\]; Kovač and Tao record the strict inequality $`w_N>R_N`$ and the Cantor-set conclusion for every fixed base $`t\ge2`$ \[kovactao2024, Remark 4.1\]. Parts (a) and (c) follow from Theorem <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a> in a few lines. We have not found part (a) stated for non-integer bases and it may be known. It shows that the statement asked in \#257 is false at every rational base below $`2`$, so any proof at base $`2`$ must use more than the shape of the series.

<div id="thm:chains" class="theorem">

**Theorem 11** (divisibility chains). *Let $`t=a/b>1`$ in lowest terms and let $`S=\{n_1<n_2<\cdots\}`$ be infinite with $`n_j\mid n_{j+1}`$ for every $`j`$.*

*<span class="upright">(a)</span> If $`a^2>b^3`$, then $`X_S(t)`$ is irrational.*

*<span class="upright">(b)</span> If $`n_{j+1}=2n_j`$ for all large $`j`$, then $`X_S(t)`$ is transcendental, with no condition on $`a`$ and $`b`$.*

</div>

The hypothesis $`a^2>b^3`$ says $`\log b/\log a<2/3`$. It holds for every integer base, for $`3/2`$, $`5/2`$ and $`7/3`$, and fails for $`4/3`$ and $`5/4`$. At integer bases part (a) is contained in the theorem of Erdős on supports with $`\sum_{n\in S}1/n<\infty`$ \[erdos1968\], proved in full in \[plectis257, Theorem 2\]. At base $`3/2`$ it sits inside the regime of Theorem <a href="#thm:bases" data-reference-type="ref" data-reference="thm:bases">10</a>(a): rational values occur there, and exact divisibility still forces irrationality. For comparison, the companion note on \#1049 proves the irrationality of the full sum $`X_{\mathbb{N}_{>0}}(a/b)`$ when $`\log b/\log a<0.4056830213840605\ldots`$, using Zudilin’s linear forms \[plectis1049, Theorem 1\], \[zudilin2004\], and proves that the sufficient cutoff supplied by one integer-polynomial family with common leading degree, coefficient-height and decay bounds at every fixed real base $`x>1`$ is at most $`1/2`$ \[plectis1049, Theorem 5\]. This restriction does not exclude stronger estimates at a particular base or a different choice of family there. Thin supports reach further than the full sum because the denominators divide one another.

At base $`2`$ the greedy rule characterises membership and supplies finite certificates of nonmembership: starting from $`r_0=x`$, take index $`n`$ when $`r_{n-1}\ge w_n`$ and subtract. Since $`w_n>R_n`$, a real $`x\in[0,E]`$ is a subsum if and only if no remainder falls strictly between $`R_n`$ and $`w_n`$; we say $`x`$ is *rejected at step $`n`$* when that happens first at index $`n`$.

<div id="thm:forced" class="theorem">

**Theorem 12** (the fixed-depth rational count). *Fix $`N\ge1`$. Among the reduced fractions $`p/q\in(0,E]`$ with $`q\le Q`$, the proportion not rejected in the first $`N`$ steps tends to $`2^NR_N/E`$ as $`Q\to\infty`$, with error $`O(2^N\log Q/Q)`$. Consequently the upper limit of the proportion that are subsums is at most $`1/E=0.62239\ldots`$.*

</div>

The limit $`2^NR_N/E`$ does not depend on whether \#257 is true. Agreement with this fixed-depth limiting proportion therefore does not establish membership. An exact computation in \[plectisinvestigation\] first read a surviving share near $`62\%`$ as evidence that most such fractions are subsums; Theorem <a href="#thm:forced" data-reference-type="ref" data-reference="thm:forced">12</a> is the correction. Section <a href="#sec:base2" data-reference-type="ref" data-reference="sec:base2">6.3</a> states what remains.

<a id="evidence."></a>

#### Evidence.

The proofs of Theorems <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a>–<a href="#thm:forced" data-reference-type="ref" data-reference="thm:forced">12</a> are ordinary proofs. Theorem <a href="#thm:chains" data-reference-type="ref" data-reference="thm:chains">11</a> uses Nishioka’s theorem for Mahler systems as an external premise in the eventually doubling case, hence in both parts. Results quoted from the problem papers retain the evidence class given at each use.

<a id="sec:dichotomy"></a>

## Choices against contraction

<div class="proof">

*Proof of Theorem <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a>.* (i) A choice of $`\varepsilon_1,\dots,\varepsilon_N`$ fixes $`\sum_{n\le N}\varepsilon_nu_n`$, and the rest of the sum lies in $`[0,C_N]`$. So $`V`$ is covered by at most $`\prod_{n\le N}(D_n+1)`$ intervals of length $`C_N`$.

\(ii\) Subtracting $`\mu`$, it suffices to reach every $`y\in[0,C_{N_0}]`$ with the levels $`n>N_0`$. Put $`y_{N_0}=y`$ and, for $`n>N_0`$, let $`\varepsilon_n=\min(D_n,\lfloor y_{n-1}/u_n\rfloor)`$ and $`y_n=y_{n-1}-\varepsilon_nu_n`$. If $`0\le y_{n-1}\le C_{n-1}=D_nu_n+C_n`$ then $`0\le y_n\le C_n`$: when $`\varepsilon_n=D_n`$ this is a subtraction, and when $`\varepsilon_n<D_n`$ it holds because $`y_n<u_n\le C_n`$. Since $`C_n\to0`$, the sum of the $`\varepsilon_nu_n`$ is $`y`$.

\(iii\) Here $`C_n=D\beta^{-n}/(\beta-1)`$. The product in (i) is a constant multiple of $`((D+1)/\beta)^N`$, and $`u_n\le C_n`$ says $`\beta-1\le D`$. ◻

</div>

The reading that matters for irrationality is immediate. Suppose a family of series has values $`x_0+\sum\varepsilon_nu_n`$ with the $`\varepsilon_n`$ free as in (ii). The values then fill an interval, which contains rationals and irrationals, so a property that all members of the family share implies neither. A proof of irrationality for one member has to use something that distinguishes it inside the family. Two constructions in the companion notes are families of this kind.

*Problem \#251.* Proposition 1 of \[plectis251\] (ordinary proof), applied in its Corollary 2 to the prime gaps, changes the gaps on a set of upper Banach density zero, by nonnegative integers below any prescribed function tending to infinity, keeping every congruence modulo every fixed $`q`$ from some point on, and reaches every real in an interval. The resulting positions $`P_n`$ satisfy $`P_n\sim n\log n`$ and are not asserted to be prime. In the notation above the $`j`$-th block has $`u_j=M_j2^{-n_j-2}`$ and $`D_j=2^{s_j}-1`$, and the inequality verified there is $`u_j\le C_j`$. The lemma is credited there to \[fridy1966\], \[crmarickovac2025, Lemma 4\] and \[kovactao2024, Lemma 5.1\]. The note also proves that a bounded allowance is impossible under the stated congruences. Thus every allowance tending to infinity suffices, while no bounded allowance does. The specified growth, eventual fixed-modulus congruences and empirical distributions of unnormalised blocks therefore do not suffice to prove $`\sum p_n2^{-n}`$ irrational; neither primality nor every quantitative correlation is preserved.

*Problem \#249.* Section 5 of \[plectis249\] gives an integer sequence $`c`$ with $`c(n)=\varphi(n)`$ for odd $`n`$, $`|c(n)-\varphi(n)|\le2`$ for even $`n`$, $`0\le c(n)\le n`$ and $`\sum c(n)2^{-n}=5/4`$ (Lean-checked there). Changing even indices by at most $`2`$ is the case $`u_n=2^{-n}`$ for even $`n`$, $`D_n=4`$, where $`C_n\ge\tfrac43 2^{-n}>u_n`$.

The same comparison appears in Kovač and Tao’s theorem that for integers $`2\le t_1<\dots<t_m`$ with $`\sum1/(t_k-1)>1`$ there are sets $`S_k`$, one of them infinite, with $`\sum_kX_{S_k}(t_k)`$ rational \[kovactao2024, Theorem 2.3\]: merging the weights of the $`m`$ bases, the sum of all weights below a given weight $`u`$ is at least $`(1-O(u))\,u\sum1/(t_k-1)`$, which exceeds $`u`$ once $`u`$ is small.

<a id="sec:bases"></a>

## The subseries across bases

<div class="proof">

*Proof of Theorem <a href="#thm:bases" data-reference-type="ref" data-reference="thm:bases">10</a>.* (a) Since $`R_n\ge\sum_{k>n}t^{-k}=t^{-n}/(t-1)`$ and $`w_n=t^{-n}/(1-t^{-n})`$, the inequality $`w_n\le R_n`$ holds as soon as $`t^{-n}\le2-t`$. Theorem <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a>(ii) with $`D_n=1`$ gives, for each $`F\subseteq\{1,\dots,N_0\}`$, the interval $`[X_F(t),X_F(t)+R_{N_0}]`$, and every value $`X_S(t)`$ lies in the one with $`F=S\cap[1,N_0]`$. For $`t=a/b`$ a finite subsum is $`\sum_{n\in F}b^n/(a^n-b^n)`$, whose denominator divides $`\prod(a^n-b^n)`$ and is coprime to $`ab`$. A rational whose denominator is not coprime to $`ab`$ is therefore never a finite subsum, and inside the interval it is a subsum. At $`t=3/2`$ the inequality $`t^{-n}\le1/2`$ holds for $`n\ge2`$ and $`R_1>1/2`$.

\(c\) For $`t>2`$, $`2^NR_N\le2^Nt^{-N}/((t-1)(1-t^{-1}))\to0`$, and Theorem <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a>(i) applies. ◻

</div>

<div class="proof">

*Proof of Theorem <a href="#thm:chains" data-reference-type="ref" data-reference="thm:chains">11</a>.* Write $`\rho=b/a`$, $`D_j=a^{n_j}-b^{n_j}`$ and $`S_j=\sum_{i\le j}b^{n_i}/(a^{n_i}-b^{n_i})`$. Because $`n_i\mid n_j`$ for $`i\le j`$, each $`a^{n_i}-b^{n_i}`$ divides $`D_j`$, so $`D_jS_j`$ is an integer. The tail satisfies
``` math
0<X_S(t)-S_j\le\sum_{n\ge n_{j+1}}\frac{\rho^n}{1-\rho^n}
 \le\frac{\rho^{\,n_{j+1}}}{(1-\rho)^2}.
```
Each ratio $`n_{j+1}/n_j`$ is an integer at least $`2`$.

Suppose the ratio is at least $`3`$ for infinitely many $`j`$. For those $`j`$,
``` math
0<D_j\bigl(X_S(t)-S_j\bigr)\le\frac{a^{n_j}\rho^{3n_j}}{(1-\rho)^2}
 =\frac{1}{(1-\rho)^2}\Bigl(\frac{b^3}{a^2}\Bigr)^{n_j}\longrightarrow0
```
when $`a^2>b^3`$. If $`X_S(t)=p/q`$, then $`qD_j(X_S(t)-S_j)`$ is a positive integer for every $`j`$, a contradiction.

Otherwise the ratio is $`2`$ from some index on, which is the case of part (b), and $`S`$ is a finite set together with $`\{d,2d,4d,\dots\}`$. With $`z=t^{-d}`$ the infinite part contributes $`g(z)`$, where
``` math
g(z)=\sum_{k\ge0}\frac{z^{2^k}}{1-z^{2^k}},\qquad
 g(z^2)=g(z)-\frac{z}{1-z}.
```
We use Nishioka’s value theorem for Mahler systems \[nishioka1996\], in the precise form quoted by Adamczewski and Faverjon \[adamczewskifaverjon2016, Theorem 1.1, p. 3\]. At an algebraic regular point it equates the transcendence degree of the function values with that of the functions over $`\overline{\mathbb{Q}}(z)`$. Here the system is
``` math
\begin{pmatrix}g(z)\\1\end{pmatrix}
 =\begin{pmatrix}1&z/(1-z)\\0&1\end{pmatrix}
  \begin{pmatrix}g(z^2)\\1\end{pmatrix}.
```
The matrix and its inverse have no poles at any iterate $`\rho^{\,d2^k}\in(0,1)`$, so $`\rho^d`$ is regular. The function $`g`$ is transcendental: at a root of unity $`\zeta`$ of order $`2^j`$ the terms with $`k\ge j`$ are positive on the ray $`r\zeta`$ and diverge as $`r\to1`$, while the earlier terms stay bounded, so $`g`$ has infinitely many singularities on the unit circle. An algebraic function over $`\mathbb{C}(z)`$ has only finitely many singular points, so $`g`$ is transcendental over $`\mathbb{C}(z)`$. Hence $`g(\rho^{\,d})`$ is transcendental, and adding the rational finite part proves (b) and completes (a). ◻

</div>

We do not know whether $`a^2>b^3`$ is necessary in (a). The first open case is base $`4/3`$ with a chain whose ratios are $`2`$ except for infinitely many $`3`$s.

<a id="sec:base2"></a>

## Base two

<a id="sec:lemmas"></a>

### Removed intervals and finite translations

For the remainder of this subsection, take $`t=2`$: $`w_n=(2^n-1)^{-1}`$, $`R_N=\sum_{n>N}w_n`$, $`g_n=w_n-R_n>0`$, $`X_F=\sum_{n\in F}w_n`$ for finite $`F`$, and $`\mathcal A`$ is the set of all subsums.

<div id="lem:gaps" class="lemma">

**Lemma 13** (the removed intervals). *$`[0,E]\smallsetminus\mathcal A`$ is the disjoint union, over finite nonempty $`F`$, of the open intervals $`(X_F-g_{\max F},\,X_F)`$. Their total length is $`\sum_n2^{n-1}g_n=E-1`$, and $`g_n=\sum_{j\ge2}\frac{2^j-2}{2^j-1}2^{-jn}=\tfrac23 4^{-n}+\tfrac67 8^{-n}+\cdots`$.*

</div>

<div class="proof">

*Proof.* Fix the digits $`\varepsilon_1,\dots,\varepsilon_{n-1}`$ and let $`s=\sum_{i<n}\varepsilon_iw_i`$. The values with these digits lie in $`[s,s+R_{n-1}]`$, and they split into $`[s,s+R_n]`$ and $`[s+w_n,s+w_n+R_n]`$. The interval between them is $`(s+R_n,s+w_n)`$. Its right end is $`X_F`$ with $`F=\{i<n:\varepsilon_i=1\}\cup\{n\}`$ and its length is $`g_n`$. Every finite nonempty $`F`$ arises once. The total length is $`E`$ minus the measure of $`\mathcal A`$, which is $`1`$ \[plectis257, Section 7\]. The series for $`g_n`$ follows from $`w_n=\sum_{j\ge1}2^{-jn}`$ and $`R_n=\sum_{j\ge1}2^{-jn}/(2^j-1)`$. ◻

</div>

<div id="lem:translate" class="lemma">

**Lemma 14** (translation by a finite subsum). *Let $`F`$ be finite with largest element $`n`$ and let $`0\le x\le R_n`$. The greedy rule applied to $`X_F+x`$ selects exactly $`F`$ among the indices up to $`n`$ and then agrees with the greedy rule applied to $`x`$. In particular $`X_F+x\in\mathcal A`$ if and only if $`x\in\mathcal A`$, and $`X_F+x`$ is rejected at a step $`m>n`$ exactly when $`x`$ is.*

</div>

<div class="proof">

*Proof.* At an index $`i\le n`$ the remainder is $`X_{F\cap[i,n]}+x`$. If $`i\in F`$ it is at least $`w_i`$ and the index is taken. If $`i\notin F`$ it is at most $`R_i-R_n+x\le R_i<w_i`$, so the index is skipped and nothing is rejected. After index $`n`$ the remainder is $`x`$. ◻

</div>

Two consequences. The map $`x\mapsto x+1`$ preserves reduced denominators, so at every step $`n\ge2`$ the number of fractions of height at most $`Q`$ rejected at that step is even; every saved table has this property. The condition is $`x\le R_{\max F}`$. It is not enough that $`X_F+x\le E`$: $`x=1/2`$ is not rejected through step $`160`$, while $`1/2+1/3=5/6`$ lies in $`(R_1,1)`$ and is rejected at step $`1`$. Counts of rejections should therefore be taken modulo these translations. At height $`200`$ the four fractions rejected at step $`12`$ are $`46/183`$ and its translates by $`1/3`$, $`1`$ and $`4/3`$, one event.

A finite subsum has odd denominator, since $`\prod_{n\in F}(2^n-1)`$ is odd. So a rational with even denominator is never a finite subsum, and if it is a subsum at all its set $`S`$ is infinite.

<a id="fixed-depth-rational-counts"></a>

### Fixed-depth rational counts

<div class="proof">

*Proof of Theorem <a href="#thm:forced" data-reference-type="ref" data-reference="thm:forced">12</a>.* Fixing the first $`N`$ digits gives $`2^N`$ closed intervals of length $`R_N`$. They are pairwise disjoint because $`w_n>R_n`$, and a real in $`[0,E]`$ is not rejected in the first $`N`$ steps exactly when it lies in their union $`K_N`$, which has measure $`2^NR_N`$. For an interval $`I`$ of length $`\ell`$, the number of integers $`p`$ coprime to $`q`$ with $`p/q\in I`$ is $`\varphi(q)\ell+O(2^{\omega(q)})`$ by inclusion and exclusion. Summing over $`q\le Q`$ with $`\sum_{q\le Q}\varphi(q)=3Q^2/\pi^2+O(Q\log Q)`$ and $`\sum_{q\le Q}2^{\omega(q)}=O(Q\log Q)`$ gives $`3Q^2\ell/\pi^2+O(Q\log Q)`$. Apply this to the $`2^N`$ intervals of $`K_N`$ and to $`(0,E]`$ and divide. The second statement follows because every subsum lies in every $`K_N`$ and $`2^NR_N\to1`$. ◻

</div>

The intervals removed at step $`n`$ are explicit. Put $`g_n=w_n-R_n`$, so that $`g_n=\tfrac23 4^{-n}+O(8^{-n})`$. For a finite nonempty $`F`$ with largest element $`n`$, the interval $`(X_F(2)-g_n,\,X_F(2))`$ is removed at step $`n`$, and
``` math
[0,E]\smallsetminus\mathcal A=\bigsqcup_{F\ne\varnothing}\bigl(X_F(2)-g_{\max F},\,X_F(2)\bigr),
 \qquad\sum_{n\ge1}2^{n-1}g_n=E-1,
```
where $`\mathcal A`$ is the set of subsums. By Theorem <a href="#thm:bases" data-reference-type="ref" data-reference="thm:bases">10</a>(b) a rational with an infinite $`S`$ is exactly a counterexample to \#257 at base $`2`$. So \#257 at base $`2`$ holds if and only if every rational in $`[0,E]`$ that is not a finite subsum lies strictly between $`X_F(2)-g_{\max F}`$ and $`X_F(2)`$ for some finite nonempty $`F`$. This is a one-sided question of approximation by the countable set of finite subsums, with an error that shrinks like $`4^{-\max F}`$.

Under \#257 the only fractions of height at most $`Q`$ that are subsums are the finite subsums, $`40`$ of the $`19{,}653`$ fractions with $`2\le q\le200`$. A model that treats later remainders as equidistributed gives the opposite extreme, a proportion tending to $`1/E`$, because the shares $`2^{n-1}g_n/E`$ of the removed intervals are summable. That model asserts that \#257 fails for a positive proportion of all rationals. The fixed-depth limiting proportion does not distinguish this claim from its negation. An arithmetic argument, or a count with separately justified estimates as both depth and height grow, is needed. Measure does not decide either. Boes, Darst and Erdős construct symmetric Cantor sets of every measure in $`[0,1)`$ that contain essentially no rationals \[boesdarsterdos1981\].

The exact computation in \[plectisinvestigation\] agrees with Theorem <a href="#thm:forced" data-reference-type="ref" data-reference="thm:forced">12</a> step by step. Among the $`19{,}653`$ reduced fractions with $`2\le q\le200`$, the numbers rejected at steps $`1`$, $`2`$ and $`7`$ are $`4809`$, $`1470`$ and $`32`$, against $`4811`$, $`1467`$ and $`32`$ from the measures of the removed intervals. The measure-based main term for the number rejected at step $`n`$ is $`2^{n-1}g_n\sum_{2\le q\le Q}\varphi(q)`$, asymptotically $`(3Q^2/\pi^2)2^{n-1}g_n`$, which falls below $`1`$ near $`n=2\log_2Q-2\log_2\pi`$. This is not a deterministic cutoff: the error in Theorem <a href="#thm:forced" data-reference-type="ref" data-reference="thm:forced">12</a> does not justify such an extrapolation. For example, $`189/388`$ is first rejected at step $`17`$, beyond this scale for $`Q=388`$. Its selected indices before rejection are $`F=\{2,3,7,9,10,14,15,16\}`$, and exact arithmetic gives
``` math
R_{17}\le\frac{196609}{25769803776}
 <\frac{189}{388}-X_F(2)
 =\frac{9291822600689}{1217890317075045460}
 <\frac1{131071}=w_{17}.
```
Section <a href="#sec:misread" data-reference-type="ref" data-reference="sec:misread">8</a> supplies the earlier-step checks. Deeper computation can therefore produce new exclusion certificates; absence of a later rejection still does not prove membership. No rational is known to have an infinite $`S`$ at base $`2`$.

<div id="prob:membership" class="problem">

**Problem 15**. Decide whether $`1/2`$ is a subsum of $`\sum(2^n-1)^{-1}`$. By \[plectis257, Theorem 7\] this holds if and only if the integer remainders of the greedy rule fail to increase at infinitely many steps.

</div>

The rational-point counting papers examined here concern null Cantor sets such as the middle-third set \[rstw2019; chowvarjuyu2024\]. We did not locate a theorem settling the present positive-measure subsum problem. Problem <a href="#prob:membership" data-reference-type="ref" data-reference="prob:membership">15</a> asks about one explicit rational point.

<a id="sec:second"></a>

# Limits on methods

<span id="sec:inventory" label="sec:inventory"></span>

Status is as stated in each note: L for checked in Lean there, O for an ordinary proof there, C for cited there.

| Note | Location | Statement |  |
|:---|:---|:---|:---|
| \#68 \[plectis68\] | Section 6 | Under the displayed cancellation hypotheses, the integer-gap comparison fails at cutoffs $`N=D+O(1)`$ as the cancellation cutoff $`D\to\infty`$. Small tails alone do not give the strict comparison. | O |
| \#243 \[plectis243\] | Proposition 17 | A counterexample has errors that are eventually nonzero, relatively small, with unbounded negative parts. This necessary profile is formalised; the comparison with scalar profiles and the need for denominator compatibility are ordinary discussion. | L, O |
| \#249 \[plectis249\] | Section 5 | A rational series with the totient’s values at odd indices, within $`2`$ at even indices, and sum $`5/4`$. Positive tail differences need not be nonintegral. | L |
| \#249 \[plectis249\] | Theorem 9 | Every admissible rank-one quotient stays more than $`21/320`$ from its target. | L |
| \#251 \[plectis251\] | Proposition 1, Corollary 2 | For every allowance $`f(n)\to\infty`$, sparse nonnegative corrections reach every real in an interval while every fixed modulus eventually divides both the corrections and their cumulative sums. A bounded allowance is impossible under these congruences. Sources: \[fridy1966\], \[crmarickovac2025, Lemma 4\], \[kovactao2024, Lemma 5.1\], \[vandoornkovac2025\]. | O |
| \#257 \[plectis257\] | Section 6 | The small-displacement quantity stays above $`1/2`$ at full support, where the value is irrational \[erdos1948\]. No proof covering full support can rest on it. | L, O |
| \#257 \[plectis257\] | Section 3 | Every positive divisor cover costs at least $`e`$ times the mean of $`\log^+`$ of its multiplicity. The averaging method cannot reach the prime support, where irrationality is known at base $`2`$ \[taoteravainen2025\]. | O |
| \#269 \[plectis269\] | Theorem 1 | Nonsingular minors of every order: no finite sum of products separates one exponent from the other two. Fan posted the two-prime separation \[fan2026comment\]; the three-prime statement is the note’s. | L |
| \#1049 \[plectis1049\] | Theorem 5 | One family of nonzero integer-polynomial linear forms with common leading degree, coefficient-height and decay bounds at every fixed real $`x>1`$ has $`\sigma\le\delta`$; the sufficient cutoff $`\sigma/(\sigma+\delta)`$ supplied by those estimates is at most $`1/2`$. Ordinary proof, with the contradiction step and the comparison with $`1/2`$ checked in Lean. | O, L |
| \#1049 \[plectis1049\] | Theorem 7 | The stated clearing conditions cannot be met at base $`3/2`$. | L |

Theorem <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a>(ii) explains interval filling in the \#251 construction. The \#249 countermodel is a separate explicit construction with its own preserved identities. The \#1049 restriction does not exclude stronger base-specific estimates, different families at different bases, or forms involving several target values. The others bound a method. We tried to state one inequality that covers \#1049 Theorem 5 and the cover cost of \#257, a cost of clearing denominators against the decay gained, and did not find a formulation that survives both sets of hypotheses. We do not claim the rows share a cause.

<a id="sec:misread"></a>

# The computation and its limits

The computation \[plectisinvestigation\] runs the greedy rule in exact arithmetic on every reduced fraction in $`(0,E]`$ with $`2\le q\le Q`$.

*First reading.* At $`Q=36`$, $`382`$ of $`633`$ fractions are not rejected through step $`160`$ and $`14`$ are finite subsums, a share $`(382+14)/633=0.6256`$ close to $`1/E=0.6224`$. This was read as evidence that about $`62\%`$ of rationals are subsums, hence that \#257 is false. The reading is wrong. By Theorem <a href="#thm:forced" data-reference-type="ref" data-reference="thm:forced">12</a> above the share at any fixed depth tends to $`2^NR_N/E`$ whatever the truth of \#257, because fractions equidistribute over the $`2^N`$ intervals that survive $`N`$ steps.

*An incorrect stopping rule.* A subsequent interpretation went too far in the opposite direction, asserting that survival after about $`2\log_2Q-3.3`$ steps was forced. The measure-based main term for the number rejected at step $`n`$ is $`2^{n-1}g_n\sum_{2\le q\le Q}\varphi(q)`$, asymptotically $`(3Q^2/\pi^2)2^{n-1}g_n`$, which is below $`1`$ for $`n>2\log_2Q-2\log_2\pi`$, about step $`12`$ at $`Q=200`$. A main term below $`1`$ does not make the actual count zero. Theorem <a href="#thm:forced" data-reference-type="ref" data-reference="thm:forced">12</a> is a fixed-depth asymptotic, and its error $`O(2^N\log Q/Q)`$ does not justify an extrapolation to $`N\sim2\log_2Q`$. Late rejections remain exact nonmembership certificates; the $`12{,}218`$ fractions not rejected through step $`60`$ have only that finite-depth status. At $`N=12`$ the observed share is $`0.62372`$ against $`2^{12}R_{12}/E=0.62245`$.

*An exact rejection at step $`17`$.* The witness $`189/388`$, recorded in the earlier investigation’s Desk B report, contradicts the proposed stopping rule: $`2\log_2 388-2\log_2\pi`$ is about $`13.9`$. The selected indices through step $`16`$ are $`F=\{2,3,7,9,10,14,15,16\}`$. At each skipped earlier index $`n`$, exact rational arithmetic gives a remainder at most $`2^{-n}<R_n`$, so no rejection has yet occurred. The remaining value is
``` math
r=\frac{189}{388}-X_F
  =\frac{9291822600689}{1217890317075045460}.
```
Since $`1/(2^k-1)=2^{-k}+4^{-k}/(1-2^{-k})`$ and $`1/(1-2^{-k})\le2`$ for $`k\ge1`$, summing gives
``` math
R_n\le2^{-n}+\frac{2}{3\cdot4^n}.
```
At $`n=17`$, the exact comparison is
``` math
R_{17}\le\frac{196609}{25769803776}<r<\frac1{131071}=w_{17}.
```
The same rejection occurs for $`577/388=1+189/388`$ by Lemma <a href="#lem:translate" data-reference-type="ref" data-reference="lem:translate">14</a>. The independent reproduction, including every earlier skipped step, is in `research/experiments/sparse_interpolation/late_rejection.py`. This certificate shows that deeper computation can add exclusions. It does not convert survival to any finite depth into a membership certificate.

What survives is the agreement itself. At $`Q=200`$ the counts at steps $`1`$ to $`9`$ are $`4809`$, $`1470`$, $`600`$, $`268`$, $`132`$, $`66`$, $`32`$, $`8`$, $`6`$, against $`4811`$, $`1467`$, $`604`$, $`277`$, $`133`$, $`65`$, $`32`$, $`16`$, $`8`$ from the measures of Lemma <a href="#lem:gaps" data-reference-type="ref" data-reference="lem:gaps">13</a>; steps $`10`$ and $`11`$ have none against $`4`$ and $`2`$, and step $`12`$ has $`4`$ against $`1`$. The late counts fluctuate more than independent events would, because rejections arrive in the families of Lemma <a href="#lem:translate" data-reference-type="ref" data-reference="lem:translate">14</a>.

<a id="sec:eliminated"></a>

# Eliminated ideas

1.  *If the reachable values form a null set, no rational value is reachable.* False. Take the binary series with digit $`1`$ everywhere except digit $`0`$ at positions $`n_1<n_2<\cdots`$, and allow each of those digits to be changed to $`1`$. The reachable values form a null set when the positions are sparse, by Theorem <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a>(i), yet changing all of them gives $`\sum2^{-n}=1`$. So no count of choices against contraction, and no depth depending only on sparsity, excludes a particular rational.

2.  *Every infinite subset of a host with null subsum set has an irrational sum.* A host is a set $`B`$ of allowed indices, and its subsum set is $`\{X_S(2):S\subseteq B\}`$. For hosts chosen without reference to the target this is open and is a form of \#257 itself. As a universal statement it cannot be a route: the support of any rational subsum with infinite $`S`$ would be such a host. The subsum set of a host $`B`$ has positive measure exactly when the complement of $`B`$ is finite, by Theorem <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a>(i) and the measure at full support.

3.  *The share of surviving fractions as evidence.* Section <a href="#sec:misread" data-reference-type="ref" data-reference="sec:misread">8</a>.

4.  *A wrong locator.* A draft of Theorem <a href="#thm:chains" data-reference-type="ref" data-reference="thm:chains">11</a>(b) cited Theorem <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a> of \[adamczewskifaverjon2026\] as Nishioka’s theorem. That theorem says a value of a Mahler function at an algebraic point is rational or transcendental, which cannot prove irrationality. The proof in Section <a href="#sec:bases" data-reference-type="ref" data-reference="sec:bases">6.2</a> uses Nishioka’s value theorem as quoted in \[adamczewskifaverjon2016, Theorem 1.1, p. 3\], applied there to the two-dimensional system for $`(g,1)`$ with regular points in $`(0,1)`$.

5.  *Algebraic independence for \#1049.* With $`g`$ as in Section <a href="#sec:bases" data-reference-type="ref" data-reference="sec:bases">6.2</a>, $`\sum_{n\ge1}(t^n-1)^{-1}=\sum_{m\ \mathrm{odd}}g(t^{-m})`$, and each $`g(t^{-m})`$ is transcendental for rational $`t>1`$. This gives nothing for the infinite sum: limits of transcendental numbers take every value. No applicable value theorem for this decomposition is supplied here.

<a id="sec:known"></a>

# What was already known

- The covering argument of Theorem <a href="#thm:dichotomy" data-reference-type="ref" data-reference="thm:dichotomy">9</a>(ii) goes back to Kakeya; see \[hornich1941; nitecki2013; fridy1966\]. Its use to build rational series inside a class defined by soft data is the method of Kovač and Tao \[kovactao2024\], of Crmarić and Kovač \[crmarickovac2025\] and of van Doorn and Kovač \[vandoornkovac2025\].

- That the subsums of $`\sum(t^n-1)^{-1}`$ form a Cantor set at fixed $`t\ge2`$ is \[kovactao2024, Remark 4.1\].

- A closed set of positive measure can contain essentially no rationals \[boesdarsterdos1981\], so the heuristic of Section <a href="#sec:base2" data-reference-type="ref" data-reference="sec:base2">6.3</a> cannot be a consequence of measure.

- The rational-point counting papers examined here concern null Cantor sets \[rstw2019; chowvarjuyu2024\]. We did not locate a theorem settling the present positive-measure subsum problem. The searches were made on 20 September 2026 and are listed in the repository record.

- One identity with a consequence. Since $`\sum_{n\ge1}\mu(n)/(b^n-1)=1/b`$, the sums of $`(b^n-1)^{-1}`$ over squarefree $`n`$ with an even, respectively odd, number of prime factors are $`\tfrac12(X_{\mathrm{sf}}(b)\pm1/b)`$. Duverney and Tachiya prove that $`X_{\mathrm{sf}}(2^j)`$ is irrational \[duverneytachiya, Corollary 1.2 and Example 1.1\], as quoted in \[plectis257, Section 6\], so both sums are irrational at every base $`2^j`$. Both supports have divergent reciprocal sums. The identity at base $`2`$ is derived in \[plectis249, Section 5\]; the corollary may be known.

<a id="capacity:sec:sources"></a>

# Sources and formal correspondence

The starting point is the sparse perturbation construction accompanying Erdős Problem \#251 in this repository, especially its [short paper](../mirror/erdos-251-prime-gap-dyadic-series.pdf) and [`ResidueFeedbackCore.lean`](https://github.com/wcook04/plectis-erdos/blob/8d6596fbde2c4aacf946adec4b0226ba1a97545d/lean/ErdosProblems/Erdos251/ResidueFeedbackCore.lean). The latter already proves residue-dependent selection and an abstract infinite sum endpoint. An operator-supplied review supplied the form of Lemma <a href="#capacity:lem:feedback" data-reference-type="ref" data-reference="capacity:lem:feedback">6</a>, the sharp exponential support constants, and the linear/superlinear factorial contrast. Those ingredients are credited to that review, not presented as discoveries of this paper. The extensions developed here are the exact capacity criterion on arbitrary strict integer divisibility chains, the factorial support classification and its integer-exponent comparison, the common-divisor formulation, and the derivative dimension and rationality thresholds proved above.

The derivative theorem combines residue feedback from \#251 with the treatment of factorial carries in \#68. Identity <a href="#capacity:eq:jet-carry" data-reference-type="eqref" data-reference="capacity:eq:jet-carry">[capacity:eq:jet-carry]</a> interprets a carry as multiplication by a polynomial vanishing at the evaluation point. This produces the independent higher derivative instead of assuming its availability. The moving coordinates in <a href="#capacity:eq:moving-taylor" data-reference-type="eqref" data-reference="capacity:eq:moving-taylor">[capacity:eq:moving-taylor]</a> make the full-dimensional critical construction possible; the counting obstruction proves its measure is zero. Conversely, division by the same vanishing polynomial preserves integer factorial coefficients and eventual divisibility. The complementary tail formula then proves rational-derivative rigidity at precisely the same threshold. These are explicit transfers between representations, not evidence for a general improvement in automated discovery. The other programmes motivated comparison of rank, arithmetic and analytic obstructions; their endpoints are not premises here.

Hurwitz functions and interpolation by vanishing polynomials are classical. Waldschmidt’s survey \[waldschmidt2022, Sections 2–3\] describes growth and multipoint derivative questions. Here we fix a polynomial bound on the integer Taylor coefficients and study the dimension and interior of a finite real derivative image, as well as rationality of finitely many derivatives under eventual coefficient divisibility. This last hypothesis is restrictive: it is not an unrestricted rational-value theorem for Hurwitz functions. For the classical scalar dimension formula, see Wegmann \[wegmann1968, Satz 4, p. 625\], who credits Šalát. Our additional task is to separate a joint derivative image after several carry constructions have been added. Neither the definition of a Hurwitz function nor the mass-distribution argument is new. The precise dimension formula and the two sharp thresholds are proved here; historical priority remains unestablished.

Airey, Mance and Vandehey already use digit sets eventually divisible by every fixed integer while retaining asymptotically full digit entropy \[amv2015, Section 6, p. 1321\]. Their theorem concerns normality and Hausdorff dimension for chosen Cantor bases. Here a fixed divisibility chain and arbitrary summable allowances are given, and the conclusion distinguishes interval filling from nullity and meagreness. These are elementary arguments in the classical theory of Cantor series and achievement sets; historical novelty of the exact classification is not established. Classical interval covering is background, rather than a contribution claimed here. A literature comparison and the reproducible checks are recorded in [the accompanying research record](https://github.com/wcook04/plectis-erdos/blob/8d6596fbde2c4aacf946adec4b0226ba1a97545d/research/experiments/sparse_interpolation/README.md). The work was developed with AI assistance and mathematical cross-checking by separate agent passes; that does not constitute independent expert review.

The formal module [`CongruenceInterpolation.lean`](https://github.com/wcook04/plectis-erdos/blob/8d6596fbde2c4aacf946adec4b0226ba1a97545d/lean/ErdosProblems/Synthesis/CongruenceInterpolation.lean) uses the existing feedback module and states the common-divisor obstruction for a real carry recurrence. The analytic identification of that recurrence with the Cantor series, and the capacity and support classifications, are the ordinary proofs above. The module [`FeedbackContinuation.lean`](https://github.com/wcook04/plectis-erdos/blob/8d6596fbde2c4aacf946adec4b0226ba1a97545d/lean/ErdosProblems/Synthesis/FeedbackContinuation.lean) reuses the existing interval-feedback endpoint and proves eventual individual and cumulative divisibility from nested cofinal moduli; choosing the moduli and continuation intervals remains part of the ordinary proof. See the research record for the exact build status and source revision. No claim about any of the eight Erdős programmes changes; in particular factorial denominators $`n!`$ here are not $`n!-1`$ from \#68.

The accompanying module [`FactorialJet.lean`](https://github.com/wcook04/plectis-erdos/blob/2bd14835b940b3c695a9cc8828c7e2967d65c053/lean/ErdosProblems/Synthesis/FactorialJet.lean) checks the finite factorial-carry identity and its first weighted version, including endpoint terms, and preservation of divisibility. It does not formalise Theorems <a href="#capacity:thm:jets" data-reference-type="ref" data-reference="capacity:thm:jets">1</a> and <a href="#capacity:thm:rational-jets" data-reference-type="ref" data-reference="capacity:thm:rational-jets">2</a>, their limits or dimension proof. The exact-arithmetic script `jets.py` checks the formulas at specified finite degrees, both quotient formulas, and independently checks the uniform tail majorant in <a href="#capacity:eq:moving-taylor" data-reference-type="eqref" data-reference="capacity:eq:moving-taylor">[capacity:eq:moving-taylor]</a>. These finite degree tests are not the proof for every $`d`$.

The capacity criterion already covers non-power and oscillating allowances.

<a id="sec:questions"></a>

# Further questions

1.  Is $`1/2`$ a subsum of $`\sum(2^n-1)^{-1}`$? The exact obligation is in \[plectis257, Theorem 7\]. By Lemma <a href="#lem:gaps" data-reference-type="ref" data-reference="lem:gaps">13</a> the general question is one-sided approximation of a rational by finite subsums $`X_F`$ to within $`g_{\max F}`$.

2.  Does the count of fractions of height at most $`Q`$ rejected at step $`n`$ stay close to $`(3Q^2/\pi^2)2^{n-1}g_n`$ in the joint range $`n\le(2-\varepsilon)\log_2Q`$, counted modulo the translations of Lemma <a href="#lem:translate" data-reference-type="ref" data-reference="lem:translate">14</a>? A persistent excess would be the first sign of an arithmetic mechanism for \#257.

3.  Is $`a^2>b^3`$ necessary in Theorem <a href="#thm:chains" data-reference-type="ref" data-reference="thm:chains">11</a>(a)? First case: base $`4/3`$, a chain with ratios $`2`$ and infinitely many ratios $`3`$.

4.  Is there one inequality behind \#1049 Theorem 5 and the cover cost of \#257?

The capacity criterion already covers non-power and oscillating allowances. For factorial gaps of fixed length $`m`$, a bounded multiple of $`n^m`$ still gives the lattice obstruction, whereas $`n^mL(n)`$ with $`L(n)\to\infty`$ permits interval filling. A further question concerns the null case: what finer tail data determine its Hausdorff dimension? The criterion itself does not separate dimension zero from full-dimensional null sets. Outside integer divisibility chains the prefix lattice changes, so no corresponding necessity is asserted here.

<div class="thebibliography">

99 P. Erdős and R. L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory*](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf), Monogr. Enseign. Math. 28, Geneva, 1980.

P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009).

P. Erdős, [*On the irrationality of certain series*](https://users.renyi.hu/~p_erdos/1969-09.pdf), Math. Student 36 (1968), 222–226 (issued 1969).

H. Hornich, *Über beliebige Teilsummen absolut konvergenter Reihen*, Monatshefte für Mathematik und Physik **49** (1941), 316–320. [doi:10.1007/BF01707309](https://doi.org/10.1007/BF01707309).

Z. Nitecki, [*Subsum sets: intervals, Cantor sets, and Cantorvals*](https://arxiv.org/abs/1106.3779v2), arXiv:1106.3779v2 (2013).

John A. Fridy, [*Generalized bases for the real numbers*](https://www.fq.math.ca/Scanned/4-3/fridy.pdf). The Fibonacci Quarterly **4** (1966), no. 3, 193–201.

T. Crmarić and V. Kovač, [*On the irrationality of certain super-polynomially decaying series*](https://arxiv.org/abs/2504.18712v1), Colloq. Math. **179** (2025), 55–68, doi:[10.4064/cm9628-5-2025](https://doi.org/10.4064/cm9628-5-2025). Theorem locators follow arXiv:2504.18712v1.

Vjekoslav Kovač and Terence Tao, [*On several irrationality problems for Ahmes series*](https://arxiv.org/abs/2406.17593v4). Acta Mathematica Hungarica **175** (2025), 572–608, doi:[10.1007/s10474-025-01528-0](https://doi.org/10.1007/s10474-025-01528-0); arXiv:[2406.17593v4](https://arxiv.org/abs/2406.17593v4). Statement and section numbers refer to arXiv version 4.

W. Zudilin, [*Heine’s basic transform and a permutation group for $`q`$-harmonic series*](https://geodesic.mathdoc.fr/articles/10.4064/aa111-2-4/), Acta Arith. **111** (2004), no. 2, 153–164, doi:[10.4064/aa111-2-4](https://doi.org/10.4064/aa111-2-4).

T. Tao and J. Teräväinen, [*Quantitative correlations and some problems on prime factors of consecutive integers*](https://arxiv.org/abs/2512.01739v2), arXiv:2512.01739v2 (submitted December 2025, revised April 2026).

Steve Fan, *Comment on Erdős Problem \#269, thread 269, post 7218* (2026), [source](https://www.erdosproblems.com/forum/thread/269#post-7218). 26 June 2026.

K. Mahler, *Arithmetische Eigenschaften der Lösungen einer Klasse von Funktionalgleichungen*, Math. Ann. **101** (1929), 342–367.

B. Adamczewski and C. Faverjon, [*Méthode de Mahler : relations linéaires, transcendance et applications aux nombres automatiques*](https://arxiv.org/abs/1508.07158v2), arXiv:1508.07158v2 (2016), Theorem 1.1, p. 3.

Ku. Nishioka, *Mahler Functions and Transcendence*, Lecture Notes in Math. 1631, Springer, Berlin, 1996.

D. Boes, R. Darst and P. Erdős, [*Fat, symmetric, irrational Cantor sets*](https://www.tandfonline.com/doi/abs/10.1080/00029890.1981.11995266), Amer. Math. Monthly **88** (1981), 340–341.

A. Rahm, N. Solomon, T. Trauthwein and B. Weiss, [*The distribution of rational numbers on Cantor’s middle thirds set*](https://arxiv.org/abs/1909.01198), arXiv:1909.01198.

S. Chow, P. Varjú and H. Yu, [*Counting rationals and diophantine approximation in missing-digit Cantor sets*](https://arxiv.org/abs/2402.18395), arXiv:2402.18395.

W. Cook, [*Two incomparable denominator exclusions for $`\sum_{n\ge2}(n!-1)^{-1}`$*](../mirror/erdos-68-factorial-denominator-irrationality.pdf), Erdős Problem Notes, 2026.

W. Cook, [*Bounded increments and rational reciprocal sums*](../mirror/erdos-243-reciprocal-tail-rigidity.pdf), Erdős Problem Notes, 2026.

W. Cook, [*Bases and integral relations for the $`k`$-kernel of Euler’s totient*](../mirror/erdos-249-binary-totient-series.pdf), Erdős Problem Notes, 2026.

W. Cook, [*Sparse congruence-preserving perturbations of dyadic series*](../mirror/erdos-251-prime-gap-dyadic-series.pdf), Erdős Problem Notes, 2026.

W. Cook, [*Weighted support criteria for reciprocal Mersenne subseries*](../mirror/erdos-257-mersenne-support-subseries.pdf), Erdős Problem Notes, 2026.

W. Cook, [*No finite separable representation at three prime generators*](../mirror/erdos-269-three-prime-running-lcm.pdf), Erdős Problem Notes, 2026.

W. Cook, [*Zudilin’s forms at rational bases and the exact normalised Hankel order*](../mirror/erdos-1049-rational-base-lambert.pdf), Erdős Problem Notes, 2026.

W. Cook, *Choices, contraction and rational membership*, exact computation with saved outputs in `research/experiments/choices_contraction/` of the repository, 2026.

P. Erdős, *On arithmetical properties of Lambert series*, J. Indian Math. Soc. 12 (1948), 63–66.

Wouter van Doorn and Vjekoslav Kovač, [*Lacunary sequences whose reciprocal sums represent all rational numbers in an interval*](https://arxiv.org/abs/2509.24971v3). Acta Arithmetica **223** (2026), 275–295, doi:[10.4064/aa251001-13-1](https://doi.org/10.4064/aa251001-13-1); arXiv:[2509.24971v3](https://arxiv.org/abs/2509.24971v3). Statement numbers refer to arXiv version 3.

D. Duverney and Y. Tachiya, [*Refinement of the Chowla–Erdős method and linear independence of certain Lambert series*](https://danielduverney.fr/documents/theorie-des-nombres/DuverneyTachiya190522.pdf), Forum Math. 31 (2019), no. 6, 1557–1566, [DOI](https://doi.org/10.1515/forum-2018-0299). Page numbers refer to the linked author preprint.

Boris Adamczewski and Colin Faverjon, *Mahler’s method in several variables and finite automata*, Annals of Mathematics **204**, no. 2 (2026), 455–533, [doi:`10.4007/annals.2026.204.2.1`](https://doi.org/10.4007/annals.2026.204.2.1). Locators refer to the [68-page author manuscript](https://faverjon.perso.math.cnrs.fr/AdamczewskiFaverjon_MahlerFiniteAutomata.pdf).

D. Airey, B. Mance and J. Vandehey, *Normality preserving operations for Cantor series expansions and associated fractals. II*, New York J. Math. **21** (2015), 1311–1326. <https://nyjm.albany.edu/j/2015/21-60v.pdf>. M. Waldschmidt, *Integer-valued functions, Hurwitz functions, and related topics: a survey*, in K. Kurşungöz and A. Zeytin (eds.), *Number Theory: Proceedings of the Journées Arithmétiques 2019*, De Gruyter, 2022, pp. 61–82. <https://doi.org/10.1515/9783110761115-005>. H. Wegmann, *Die Hausdorffsche Dimension von Mengen reeller Zahlen, die durch Zifferneigenschaften einer Cantorentwicklung charakterisiert sind*, Czechoslovak Math. J. **18** (1968), 622–632. <https://dml.cz/handle/10338.dmlcz/100861>.

</div>

<a id="declaration-of-generative-ai-use"></a>

# Declaration of generative AI use

The mathematics and text were developed with large language model agents under Will Cook’s direction. The first-page disclosure states his review boundary. The earlier synthesis record reports separate agent proof checks, independent reruns of the exact computations, and source checks on 20 September 2026; the failed citation is retained in Section <a href="#sec:eliminated" data-reference-type="ref" data-reference="sec:eliminated">9</a>. This consolidation preserves those arguments and their evidence classes. It is not an independent mathematical review.
