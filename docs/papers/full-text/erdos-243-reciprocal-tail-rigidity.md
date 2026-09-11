<a id="erdos-243-reciprocal-tail-rigidity"></a>

# Excluding the Bounded Negative Part

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Let $`a_1<a_2<\cdots`$ be positive integers with $`a_{n+1}/a_n^2\to1`$ and rational reciprocal sum, and put $`P_n=\prod_{j<n}a_j`$. We prove that
``` math
\limsup_{n\to\infty}\frac{P_n}{a_n}
 \left(\frac{a_n^2}{a_{n+1}}-1\right)<+\infty
```
forces $`a_{n+1}=a_n^2-a_n+1`$ eventually. In the integral tail state, bounded negative error caps upward increments, while normalised vanishing forces a nonterminal numerator to infinity. Stabilising the common divisor then supplies a Chinese remainder block that those increments cannot cross. An LCM formulation gives a weighted record criterion and the corresponding LCM-prefactor consequence. The required bound or record budget remains unproved for the unrestricted problem.

<a id="sec:problem"></a>

# Introduction

<div id="res:originalbounded" class="corollary">

**Corollary 1** (original-coordinate bounded defect). *Let $`a_1<a_2<\cdots`$ be positive integers, $`a_{n+1}/a_n^2\to1`$, and $`\sum_{n\ge1}1/a_n\in\mathbb{Q}`$. Put $`P_n=\prod_{j<n}a_j`$. If
``` math
\limsup_{n\to\infty}\frac{P_n}{a_n}
 \left(\frac{a_n^2}{a_{n+1}}-1\right)<+\infty,
```
then $`a_{n+1}=a_n^2-a_n+1`$ for all sufficiently large $`n`$.*

</div>

The statement is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos243/PaperCompleteR7/ProductDefect.lean#L211).

<a id="the-obstruction."></a>

#### The obstruction.

The equation $`C_{n+1}=C_n-E_n`$ translates a bound on negative error into a bound on upward increments. At negative indices the common divisor of $`C_n,D_n`$ divides the bounded magnitude. Once this divisor stabilises, reduction makes the later numerators coprime to the old multipliers. The Chinese remainder theorem places consecutive forbidden heights beyond any fixed prefix. A first crossing then gives the contradiction. Section <a href="#sec:lcmrecords" data-reference-type="ref" data-reference="sec:lcmrecords">6</a> uses the same divisibility at record sources, so that only record excess is charged.

<div class="samepage">

Write $`\operatorname{ctr}(a,D,C)=D-(a-1)C`$. The following integer-state theorem implies Corollary <a href="#res:originalbounded" data-reference-type="ref" data-reference="res:originalbounded">1</a>; the ordinary tail transfer is proved in Section <a href="#sec:transfer" data-reference-type="ref" data-reference="sec:transfer">4</a>. Its centring hypothesis is redundant under normalised vanishing and is retained to match the source statement.

<div id="res:bounded" class="theorem">

**Theorem 2** (bounded negative part). *Let $`a,C,D:\mathbb{N}\to\mathbb{N}`$ and $`E:\mathbb{N}\to\mathbb{Z}`$ satisfy*

1.  *$`a_n>1`$ and $`C_n>0`$ for every $`n`$;*

2.  *the exact dynamics $`C_{n+1}+D_n=a_nC_n`$ and $`D_{n+1}=a_nD_n`$;*

3.  *$`E_n=\operatorname{ctr}(a_n,D_n,C_n)`$ for every $`n`$;*

4.  **eventual strict centring*: $`|E_n|<C_n`$ for all large $`n`$;*

5.  **eventually bounded negative part*: $`-B\le E_n`$ for all large $`n`$, for some $`B`$;*

6.  **normalised vanishing*: for every $`K`$ there is an $`N`$ with $`K\,|E_n|<C_n`$ for all $`n\ge N`$.*

*Then $`E_n=0`$ for all sufficiently large $`n`$.*

</div>

</div>

<div id="res:problem" class="problem">

**Problem 3** (Erdős \#243). Let $`1\le a_1<a_2<\cdots`$ be a sequence of integers with
``` math
\lim_{n\to\infty}\frac{a_n}{a_{n-1}^{2}}=1
 \qquad\text{and}\qquad
 \sum\frac{1}{a_n}\in\mathbb{Q}.
```
Then $`a_n=a_{n-1}^{2}-a_{n-1}+1`$ for all sufficiently large $`n`$.

</div>

The additional hypothesis in Theorem <a href="#res:bounded" data-reference-type="ref" data-reference="res:bounded">2</a> is the lower bound on $`E_n`$. The growth and rationality assumptions already supply the other state hypotheses after a finite shift. Koizumi’s nonnegative-error case is integer descent \[koizumi2025, Proposition 1(2)\]; the theorem allows arbitrary sign changes with bounded negative depth. Bado’s author-posted preprint assumes two-sided bounded errors \[bado2026, Theorem 5.1\]. The comparisons concern these stated hypotheses and make no priority claim.

<a id="sec:bounded"></a>

# Proof of bounded-negative rigidity

The arithmetic ingredients are proved immediately afterwards. Normalised vanishing and integrality give $`C_n\to\infty`$ on a nonzero tail, while the lower error bound gives $`C_{n+1}\le C_n+B`$.

<div class="proof">

*Proof of Theorem <a href="#res:bounded" data-reference-type="ref" data-reference="res:bounded">2</a>.* Suppose not. We first remove every late zero: by Theorem <a href="#res:absorb" data-reference-type="ref" data-reference="res:absorb">6</a> and its contrapositive form, $`E`$ is nowhere zero beyond the centring threshold. Two cases remain. If $`E`$ is negative cofinally, then (5) bounds those magnitudes, so Proposition <a href="#res:gcdstab" data-reference-type="ref" data-reference="res:gcdstab">11</a> makes the tail gcd stabilise and the orbit may be taken reduced past that point. Hypothesis (5) with Proposition <a href="#res:update" data-reference-type="ref" data-reference="res:update">5</a> gives $`C_{n+1}\le C_n+B`$, a bounded rise; hypothesis (6) with $`E`$ nowhere zero gives $`C_n\to\infty`$. A reduced exact tail with a divergent numerator and bounded rise is excluded by Theorem <a href="#res:barrier" data-reference-type="ref" data-reference="res:barrier">9</a>. It remains to treat the case that $`E`$ is eventually positive, and there the descent of Theorem <a href="#res:descent" data-reference-type="ref" data-reference="res:descent">[res:descent]</a> applies and forces $`E`$ to vanish, contradicting nowhere-vanishing. ◻

</div>

<div id="res:cor" class="corollary">

**Corollary 4**. *Under Theorem <a href="#res:bounded" data-reference-type="ref" data-reference="res:bounded">2</a>, the multipliers satisfy $`a_{n+1}=a_n^2-a_n+1`$ eventually.*

</div>

<div class="proof">

*Proof.* Apply the two-zero implication in Corollary <a href="#res:eventual" data-reference-type="ref" data-reference="res:eventual">[res:eventual]</a> below. ◻

</div>

<a id="sec:state"></a>

# The arithmetic ingredients

<a id="sec:defect"></a>

## Error, absorption and descent

<span id="sec:descent" label="sec:descent"></span> Write $`\Delta_n=a_{n+1}-(a_n^2-a_n+1)`$.

<div id="res:update" class="proposition">

**Proposition 5** (error identities). *<span id="res:defect" label="res:defect"></span> For an exact integer state,
``` math
C_{n+1}=C_n-E_n,\qquad
 \Delta_n C_{n+1}=a_n^2E_n-E_{n+1}.
```*

</div>

<div class="proof">

*Proof.* Substitute $`E_n=D_n-(a_n-1)C_n`$ and use $`D_{n+1}=a_nD_n`$, $`C_{n+1}=a_nC_n-D_n`$. ◻

</div>

Both identities are [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos243/PaperCompleteR7/Arithmetic.lean#L21).

<div id="res:absorb" class="theorem">

**Theorem 6** (absorption and descent). *<span id="res:descent" label="res:descent"></span> For a positive exact state with strict centring, $`E_n=0`$ implies $`E_{n+1}=0`$. For any positive integer state with $`C_{n+1}=C_n-E_n`$, eventual nonnegativity of $`E_n`$ implies its eventual vanishing.*

</div>

<div class="proof">

*Proof.* When $`E_n=0`$, the second identity makes $`E_{n+1}`$ a multiple of $`C_{n+1}`$; strict centring forces that multiple to be zero. In the second assertion, $`C_n`$ is eventually a nonincreasing sequence of positive integers, so it stabilises. ◻

</div>

Both assertions are [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos243/PaperCompleteR7/Arithmetic.lean#L120).

<div id="res:step" class="corollary">

**Corollary 7** (two zero errors). *<span id="res:eventual" label="res:eventual"></span> If $`E_n=E_{n+1}=0`$ and $`C_{n+1}\ne0`$, then $`a_{n+1}=a_n^2-a_n+1`$. Thus eventual zero error in a positive exact state implies the eventual Sylvester recurrence.*

</div>

<div class="proof">

*Proof.* The second error identity has nonzero factor $`C_{n+1}`$. ◻

</div>

The local and eventual forms are [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos243/PaperCompleteR7/Arithmetic.lean#L138).

Absorption holds after any eventual centring threshold. On a nonterminal tail it removes all subsequent zeros. Then $`|E_n|\ge1`$, so normalised vanishing gives $`C_n\to\infty`$.

<a id="sec:barrier"></a>

## The first-crossing obstruction

<div id="res:crt" class="lemma">

**Lemma 8** (consecutive multiples). *For pairwise coprime integers $`m_0,\ldots,m_{B-1}\ge2`$ and every lower bound, there is a larger $`t`$ such that $`m_i\mid t+i`$ for each $`i<B`$.*

</div>

<div class="proof">

*Proof.* Solve $`t\equiv-i\pmod{m_i}`$ by the Chinese remainder theorem, then add multiples of $`\prod_i m_i`$. ◻

</div>

<div id="res:barrier" class="theorem">

**Theorem 9** (bounded-rise obstruction). *Let $`u_n\in\mathbb{N}`$ tend to infinity with $`u_{n+1}\le u_n+B`$, for a fixed integer $`B>0`$. There is no infinite pairwise coprime family $`m_i\ge2`$ with $`\gcd(m_i,u_t)=1`$ whenever $`i<t`$.*

</div>

<div class="proof">

*Proof.* Choose $`B`$ old moduli and take a CRT block $`[t,t+B)`$ beyond every numerator in the prefix before they become old. At the first crossing of $`t`$, the new numerator lies in that block, so it is divisible by an old modulus. This contradicts coprimality. No monotonicity of $`u`$ is used. ◻

</div>

<a id="reduction-and-stabilisation"></a>

## Reduction and stabilisation

A reduced exact tail has positive $`u_n`$, integer $`v_n\ge0`$, $`\gcd(u_n,v_n)=1`$, and
``` math
u_{n+1}=a_nu_n-v_n,\qquad v_{n+1}=a_nv_n.
```

<div id="res:reduced" class="proposition">

**Proposition 10** (persistent coprimality). *In a reduced exact tail, $`\gcd(a_n,v_n)=1`$. Distinct multipliers are pairwise coprime, and every earlier multiplier is coprime to every later numerator.*

</div>

<div class="proof">

*Proof.* A common prime divisor of $`a_n,v_n`$ would divide both $`u_{n+1}`$ and $`v_{n+1}`$. Also, $`a_i\mid v_t`$ for $`i<t`$, so reducedness gives $`\gcd(a_i,u_t)=1`$, and $`\gcd(a_t,v_t)=1`$ gives $`\gcd(a_i,a_t)=1`$. ◻

</div>

All three conclusions are [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos243/PaperCompleteR7/Reduction.lean#L16).

<div id="res:gcdstab" class="proposition">

**Proposition 11** (gcd stabilisation). *For a positive exact state, if negative errors have bounded magnitudes along a cofinal set of indices, then $`G_n=\gcd(C_n,D_n)`$ eventually stabilises. Division by its stable value gives a reduced exact tail.*

</div>

<div class="proof">

*Proof.* Both updates preserve common divisors, so $`G_n\mid G_{n+1}`$. Moreover $`G_n\mid E_n`$, hence $`G_n\le -E_n`$ at a negative index. The positive divisibility chain is bounded along a cofinal set and therefore bounded everywhere; it eventually stabilises. Division by the stable value preserves both exact updates and leaves the states coprime. ◻

</div>

The stable gcd and the reduced exact tail are [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos243/PaperCompleteR7/Reduction.lean#L103).

In the main proof, division by the stable gcd preserves divergence and a bounded upward increment. Theorem <a href="#res:barrier" data-reference-type="ref" data-reference="res:barrier">9</a> therefore applies to the reduced numerator. Sparse changes of the gcd without eventual stabilisation are a different statement; the supporting record retains that distinction and its finite-block consequences.

<a id="sec:transfer"></a>

# Transfer to a reciprocal series

Let $`x_n=\sum_{k\ge n}1/a_k`$, suppose $`x_1=p/q`$ with $`q>0`$, and put
``` math
P_n=\prod_{j<n}a_j,\qquad D_n=qP_n,\qquad C_n=D_nx_n.
```
Each $`C_n`$ is a positive integer, since $`D_n`$ clears the rational sum and every term of the preceding finite prefix. The tail relation $`x_n=1/a_n+x_{n+1}`$ gives the exact state updates.

Quadratic growth gives $`a_n\ge\exp(c2^n)`$ eventually for some $`c>0`$ and
``` math
x_n=\frac1{a_n}+\frac1{a_{n+1}}+O(a_{n+1}^{-2}).
```
Consequently
``` math
\frac{C_{n+1}}{C_n}
 =\frac{a_nx_{n+1}}{x_n}
 =\frac{a_n^2}{a_{n+1}}+O(1/a_n)\longrightarrow1,
 \qquad \frac{E_n}{C_n}\longrightarrow0.
```
Thus strict centring also holds eventually. These are the ordinary canonical-tail implications of Koizumi’s Corollary 3 and Lemma 4 \[koizumi2025\].

<div class="proof">

*Proof of Corollary <a href="#res:originalbounded" data-reference-type="ref" data-reference="res:originalbounded">1</a>.* Put $`\gamma_n=a_n^2/a_{n+1}-1`$. Since
``` math
\frac{P_{n+1}/a_{n+1}}{P_n/a_n}=1+\gamma_n\longrightarrow1,
 \qquad P_n/a_n=\exp(o(n)),
```
the two-term estimate gives
``` math
\begin{equation}
\label{eq:canonical-dictionary}
 E_n+q\frac{P_n}{a_n}\gamma_n
 =\frac{qP_n}{a_{n+1}}+
 O\!\left(\frac{qP_na_n}{a_{n+1}^2}\right)=o(1).
\end{equation}
```
The assumed upper bound therefore gives an eventual lower bound on the integer $`E_n`$. After deleting a finite prefix, all hypotheses of Theorem <a href="#res:bounded" data-reference-type="ref" data-reference="res:bounded">2</a> hold. Apply Corollary <a href="#res:cor" data-reference-type="ref" data-reference="res:cor">4</a>. ◻

</div>

The same calculation is valid with $`qP_n`$ replaced by any positive clearance $`H_n\le qP_n`$: if $`W_n=H_nx_n`$ and $`Z_n=H_n-(a_n-1)W_n`$, then
``` math
\begin{equation}
\label{eq:general-clearance-dictionary}
 Z_n+\frac{H_n}{a_n}\gamma_n=o(1).
\end{equation}
```
This will supply the LCM-prefactor consequence below.

<a id="sec:mass"></a>

# A scalar finite-mass criterion

<div id="res:massscalar" class="theorem">

**Theorem 12** (finite negative relative mass). *<span id="res:mass" label="res:mass"></span> Let $`C_n`$ be positive integers and $`E_n`$ integers satisfying $`C_{n+1}=C_n-E_n`$. If
``` math
\sum_n\frac{(-E_n)_+}{C_n}<\infty,
```
then $`E_n=0`$ eventually. No denominator dynamics or normalised vanishing is required.*

</div>

<div class="proof">

*Proof.* Set $`\delta_n=(-E_n)_+/C_n`$. Then
``` math
C_N\le C_0\prod_{n<N}(1+\delta_n)
 \le C_0\exp\!\left(\sum_n\delta_n\right).
```
Choose an integer upper bound $`K`$ for $`C_n`$. Each strict rise contributes at least $`1/K`$ to $`\sum\delta_n`$, so there are only finitely many rises. The remaining positive integer sequence is nonincreasing and stabilises. ◻

</div>

The product argument is the [summable relative growth](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/SparseResetRecovery.lean#L423); its specialisation to negative mass is the [vanishing from finite negative mass](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/SparseResetRecovery.lean#L488), and the statement giving the recurrence directly is the [Sylvester recurrence from summable negative mass](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/SparseResetRecovery.lean#L510). The elementary growth comparison is [tail growth](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/SparseResetRecovery.lean#L378).

On an exact reciprocal-tail orbit the conclusion gives the Sylvester recurrence. The scalar criterion and bounded negative error are distinct quantities to estimate; on the common exact-orbit class with normalised vanishing they are each equivalent to the same endpoint.

<a id="sec:lcmrecords"></a>

# Weighted first crossings of LCM records

Only steps setting an LCM numerator record need contribute. The first-crossing argument permits subtraction of a fixed baseline and any decreasing weight with divergent integral. The theorem in this section has an ordinary proof.

Set
``` math
L_n=\operatorname{lcm}(q,a_0,\ldots,a_{n-1}),\quad
 M_n=D_n/L_n,\quad U_n=C_n/M_n,\quad V_n=E_n/M_n.
```
The rational tail has denominator dividing $`L_n`$, so $`U_n`$ and $`V_n`$ are integers. With $`\rho_n=\gcd(L_n,a_n)`$, the exact updates are
``` math
M_{n+1}=M_n\rho_n,\qquad
 \rho_nU_{n+1}=U_n-V_n,\qquad V_n=L_n-(a_n-1)U_n.
```
Write $`R_n=\max_{j\le n}U_j`$ and $`\mathcal R=\{n:U_{n+1}>R_n\}`$. Centring implies that every sufficiently late strict rise has $`\rho_n=1`$: otherwise $`U_{n+1}\le3U_n/4`$. Its actual jump is therefore $`d_n=U_{n+1}-U_n=-V_n`$.

<div id="res:weightedrecord" class="theorem">

**Theorem 13** (weighted record excess). *Assume the growth and rationality hypotheses of Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">3</a>. Let $`f:[1,\infty)\to[0,\infty)`$ be finite and nonincreasing, with $`\int_1^\infty f(t)\,dt=\infty`$. Then the sequence is eventually Sylvester if and only if, for some integer $`B\ge0`$,
``` math
\sum_{n\in\mathcal R}(-V_n-B)_+f(U_n)<\infty.
```*

</div>

<div class="proof">

*Proof.* Suppose the sequence is not eventually Sylvester. Absorption and integrality give $`1/U_n\le |V_n|/U_n=|E_n|/C_n\to0`$, so there are infinitely many record steps. Every sufficiently late record is fresh. Their digits are pairwise coprime: an earlier digit divides the later $`L_n`$, while the digit at a fresh record is coprime to $`L_n`$. For any fixed $`B\ge1`$, choose $`B`$ such digits $`m_0,\ldots,m_{B-1}>B`$ and take $`T`$ after their indices.

Put $`P=\prod_i m_i`$ and choose $`x`$ by the Chinese remainder theorem with $`m_i\mid x+i`$. Consider all translates $`\tau=x+B+kP>R_T`$, $`k\in\mathbb{Z}`$; the first is at most $`R_T+P`$. A first crossing $`U_n\le R_n<\tau\le U_n+d_n`$ is a record step. If $`d_n\le B`$, then $`U_n\in[\tau-B,\tau)`$, so some $`m_i`$ divides $`U_n`$. It also divides $`L_n`$, hence divides $`d_n=(a_n-1)U_n-L_n`$, contradicting $`0<d_n\le B<m_i`$.

If the step first crosses $`h\ge1`$ such heights, their spacing gives $`(h-1)P<d_n`$. With $`r=d_n-B\ge1`$ and $`P\ge B+1`$, we have $`d_n=B+r\le Pr`$, whence $`h\le r`$. Monotonicity of $`f`$ now gives
``` math
\sum_{\substack{\tau\text{ first crossed}\\\text{at step }n}}f(\tau)
 \le(d_n-B)f(U_n).
```
Each height above $`R_T`$ has one first crossing. Summing, and comparing each interval of length $`P`$ with its left endpoint, yields the finite bound
``` math
\begin{equation}
\label{eq:weightedcrossing}
 \sum_{\substack{T\le n<N\\n\in\mathcal R}}(-V_n-B)_+f(U_n)
 \ge\frac1P\int_{R_T+P}^{R_N} f(t)\,dt.
\end{equation}
```
Since $`R_n\to\infty`$, the right side diverges for every $`B\ge1`$; $`B=0`$ follows by domination. Conversely a Sylvester tail telescopes to $`x_n=1/(a_n-1)`$, so $`V_n=0`$ eventually. ◻

</div>

For example, $`f(t)=1/[t\log(et)]`$ gives the sufficient condition
``` math
\sum_{n\in\mathcal R}\frac{(-V_n-B)_+}{U_n\log(eU_n)}<\infty.
```
Its finite lower bound in <a href="#eq:weightedcrossing" data-reference-type="eqref" data-reference="eq:weightedcrossing">[eq:weightedcrossing]</a> is $`P^{-1}\log\bigl(\log(eR_N)/\log(e(R_T+P))\bigr)`$. Further fixed iterated logarithmic factors are allowed whenever the integral still diverges. These are specialisations of one crossing theorem.

The criterion also has an exact expression in the original growth defect. Put $`\gamma_n=a_n^2/a_{n+1}-1`$ and $`\theta_n=E_n/C_n`$. The defect identity gives
``` math
\gamma_n+\theta_n=
 \frac{(1-\theta_n)(a_n-1+\theta_{n+1})}{a_{n+1}},
 \qquad 0<\gamma_n+\theta_n<3/a_n
```
eventually. Thus the two nonnegative summands $`U_nf(U_n)(\gamma_n-B/U_n)_+`$ and $`(-V_n-B)_+f(U_n)`$ differ by at most $`3U_nf(U_n)/a_n`$. This is summable because $`U_n\le C_n=\exp(o(n))`$, $`f(U_n)\le f(1)`$, and $`a_n\ge\exp(c2^n)`$ eventually for some $`c>0`$. Consequently Theorem <a href="#res:weightedrecord" data-reference-type="ref" data-reference="res:weightedrecord">13</a> is equivalent to finiteness of
``` math
\begin{equation}
\label{eq:weightedgrowth}
 \sum_{n\in\mathcal R}U_nf(U_n)
 \left(\frac{a_n^2}{a_{n+1}}-1-\frac B{U_n}\right)_+
\end{equation}
```
for some $`B`$. The original hypotheses do not currently supply this finiteness. In particular, termwise convergence to zero is insufficient. Also, $`d_n`$ is the actual jump, including any recovery from a drawdown; it must not be replaced by $`R_{n+1}-R_n`$ in the crossing proof.

<div id="res:lcmbounded" class="corollary">

**Corollary 14** (LCM-weighted bounded defect). *Assume the hypotheses of Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">3</a>. Write $`A_n=\operatorname{lcm}(a_1,\ldots,a_{n-1})`$ with $`A_1=1`$ and
``` math
Z_n=\frac{A_n}{a_n}\Bigl(\frac{a_n^2}{a_{n+1}}-1\Bigr).
```
If $`\limsup Z_n<\infty`$, then the sequence is eventually Sylvester.*

</div>

<div class="proof">

*Proof.* Put $`t_n=L_n/A_n=q/\gcd(q,A_n)`$, so $`1\le t_n\le q`$. Equation <a href="#eq:general-clearance-dictionary" data-reference-type="eqref" data-reference="eq:general-clearance-dictionary">[eq:general-clearance-dictionary]</a>, with $`H_n=L_n`$, gives $`V_n+t_nZ_n=o(1)`$. A finite upper bound on $`Z_n`$ therefore bounds the negative part of $`V_n`$. The record series vanishes after a finite prefix for a sufficiently large baseline, so Theorem <a href="#res:weightedrecord" data-reference-type="ref" data-reference="res:weightedrecord">13</a> applies. ◻

</div>

Erdős–Straus Theorem 3 uses a nonpositive limsup in the corresponding next-index LCM expression \[erdosstraus1964\]. Here any finite upper bound suffices under the quadratic-limit assumption. Since $`A_n\mid P_n`$, this also implies Corollary <a href="#res:originalbounded" data-reference-type="ref" data-reference="res:originalbounded">1</a>: multiplication by a factor in $`(0,1]`$ preserves an upper bound, including at negative values.

The divisor constraint also survives integral numerator coefficients: $`d=(a_n-1)U_n-b_nL_n`$ is divisible by every divisor of both $`U_n,L_n`$. The already-proved coefficient-uniform variant gives bounded LCM height from a bounded negative part; normalised vanishing is used afterwards for stationarity. Its proof and exact bounded-height counterexamples are in the [coefficient proof supplement](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/CoefficientUniformBoundedHeight.md).

<a id="sec:secondaryrate"></a>

# Further consequences

<div id="res:cubicrate" class="theorem">

**Theorem 15** (cubic-rate irrationality). *A strictly increasing sequence of positive integers with
``` math
a_n^2/a_{n+1}=1+\frac3n+o(n^{-3})
```
has irrational reciprocal sum.*

</div>

<div class="proof">

*Proof by the polynomial exclusion.* Under rationality, the canonical estimate gives $`C_{n+1}/C_n=1+3/n+o(n^{-3})`$. Integer finite differences force $`C_n=An(n+1)(n+2)+B`$ eventually. The fixed-cubic exclusion rules this out. The complete ordinary polynomial and number-field argument is retained in [the proof supplement, Section 8](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/WeightedRecordOctupleCriteria.md#8-rising-factorial-cubic-profiles-and-the-cubic-rate-irrationality-r08); finite congruence checks alone are insufficient for that implication. ◻

</div>

The same finite-difference extraction excludes every nonintegral $`\lambda>1`$ under the rate $`a_n^2/a_{n+1}=1+\lambda/n+o(n^{-\lambda})`$: eventual polynomial growth would force its degree to equal $`\lambda`$. These rates lie outside Koizumi’s $`1+o(1/n)`$ hypothesis \[koizumi2025, Remark 3\].

There is also an admitted quantitative extension. Under the hypotheses of Theorem <a href="#res:bounded" data-reference-type="ref" data-reference="res:bounded">2</a> other than (5), put $`\operatorname{LL}(x)=\log_2\log_2\max(4,x)`$. Each fixed $`\delta\in(0,1)`$ gives
``` math
(-E_n)_+\le(1-\delta)\operatorname{LL}(C_n)
 \quad\text{eventually}\quad\Longrightarrow\quad E_n=0\text{ eventually}.
```
The LCM version needs the corresponding bound only at late record steps. The proofs use a CRT block in $`[P,2P)`$ and the canonical multiplier scale; they are retained in [the slow-negative proof](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/SlowNegativePartRigidity.md) and [the record-only extension](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/LcmRecordExcess.md#5-record-only-subcritical-log-log-bound). These are ordinary results with stated rate hypotheses; neither establishes the general record budget.

<a id="sec:open"></a>

# The remaining arithmetic estimate

<div id="res:frontier" class="proposition">

**Proposition 16** (necessary profile). *The canonical state of a counterexample has $`E_n\ne0`$ eventually, $`|E_n|/C_n\to0`$, unbounded negative magnitudes along negative indices, and
``` math
\sum_n\frac{(-E_n)_+}{C_n}=\infty.
```*

</div>

<div class="proof">

*Proof.* Absorption excludes late zeros, descent excludes an eventually nonnegative error, and Theorems <a href="#res:bounded" data-reference-type="ref" data-reference="res:bounded">2</a> and <a href="#res:massscalar" data-reference-type="ref" data-reference="res:massscalar">12</a> exclude the two finiteness conditions. ◻

</div>

<div id="res:lcmheight" class="problem">

**Problem 17** (global overlap-height growth). For every nonterminal canonical orbit satisfying Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">3</a>, must
``` math
\limsup_{n\to\infty}\frac{\log M_n}{n}>0?
```
Equivalently, must there be a $`K\ge1`$ for which
``` math
2^n\le M_n^K
```
at infinitely many indices?

</div>

The canonical necessary profile is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos243/PaperCompleteR7/Frontier.lean#L151).

For $`B\ge0`$ put
``` math
F_B(X)=\sum_{\substack{n\in\mathcal R\\U_n\le X}}(-V_n-B)_+.
```
The remaining equivalent estimate is
``` math
\begin{equation}
\label{eq:remaining-record-budget}
 \exists B\in\mathbb{N}:\qquad\liminf_{X\to\infty}\frac{F_B(X)}X=0.
\end{equation}
```
On a nonterminal orbit first crossings instead give $`F_B(X)\ge X/P_B-O_B(1)`$, with an orbit-dependent CRT modulus $`P_B`$. The missing step is to derive <a href="#eq:remaining-record-budget" data-reference-type="eqref" data-reference="eq:remaining-record-budget">[eq:remaining-record-budget]</a> from the canonical dynamics. The equivalence with the existence of an admissible summable weight is proved in the [record-budget supplement](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/LcmDefectCriterionReduction.md); it does not establish the estimate.

The obstruction is the exact unit-numerator feedback at the record sources. The scalar sequence $`C_n=n^2+1`$, $`E_n=-(2n+1)`$ has normalised vanishing, subexponential height and finite square mass, but is not an exact reciprocal-tail orbit: its numerator word $`0,0,2\pmod5`$ violates the persistent-zero transport of the exact equations. Likewise, small rises and avoidance of an arbitrary sparse coprime family do not control the canonical timing and size of the available divisors. The supporting record keeps those falsifying examples with the exact hypotheses each preserves.

<a id="formal-scope-and-supporting-record."></a>

#### Formal scope and supporting record.

The bounded-negative state theorem is checked in Lean 4 against Mathlib at the stated source checkpoint: [eventual bounded-negative rigidity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/ReciprocalTailRigidity.lean#L2352). The canonical analytic transfer and the global weighted, polynomial and slow-negative arguments are ordinary proofs; the scalar finite-mass proof is printed in full above. The auxiliary source guide, constant and periodic exclusions, primitive feedback, finite certificates and unsuccessful global extensions belong to the accompanying reasoning record. Their stronger global producer hypotheses remain explicit.

<a id="declarations."></a>

#### Declarations.

The authorship and AI-use statement on the first page applies to this manuscript. Code and mathematical source are available at the repository checkpoint `99f4bf47422a`. A source declaration establishes only its own statement; the ordinary transfer and the unresolved estimate above are separately identified.

<a id="app:index"></a>

# Guide to the formal sources

Each linked phrase opens its Lean declaration at the pinned source revision 99f4bf47422a. The state system, the exclusions, the barrier, and the bounded-negative-part theorem are in `ReciprocalTailRigidity.lean`; the finite-negative-mass theorem is in `SparseResetRecovery.lean`; and the repair-entropy inequalities are in `RepairEntropy.lean`. The residue reduction of Appendix <a href="#app:residue" data-reference-type="ref" data-reference="app:residue">10</a> is in `FiniteHorizonResidue.lean`. Three distinctions are worth carrying into the source. The identification of any of these modules with reciprocal tails is the exposition of Section <a href="#sec:state" data-reference-type="ref" data-reference="sec:state">3</a> and is not a checked statement. The periodic exclusion assumes the regime $`e_n<a_n`$. And the final Lean declaration lists strict centring and normalised vanishing as hypotheses; the former follows eventually from the latter with $`K=1`$, while the formal source derives neither from the original analytic problem. For the external bridge supplying them, see Sections <a href="#sec:problem" data-reference-type="ref" data-reference="sec:problem">1</a> and <a href="#sec:bounded" data-reference-type="ref" data-reference="sec:bounded">2</a>.

<a id="app:residue"></a>

# A factorial residue reduction for forced orbits

In the case $`m=c=1`$ of Section <a href="#sec:constant" data-reference-type="ref" data-reference="sec:constant">[sec:constant]</a>, where the shape equation <a href="#eq:shape" data-reference-type="eqref" data-reference="eq:shape">[eq:shape]</a> reads $`D_n+1=(a_n-1)(n+1)`$, each multiplier is determined by its predecessor; we call such an orbit *forced*. At index $`n`$ the numerator of the next multiplier is
``` math
\operatorname{num}(n,a)=(n+1)a^{2}-(n+2)a+(n+3),
```
the [forced numerator](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/FiniteHorizonResidue.lean#L22), and the divisor is $`n+2`$. The orbit survives a step when that division is exact, giving a survival predicate, the [survival predicate](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/FiniteHorizonResidue.lean#L75). Example <a href="#ex:shape" data-reference-type="ref" data-reference="ex:shape">[ex:shape]</a> is the forced orbit from $`a=3`$ read this way: $`\operatorname{num}(0,3)=6`$ is divisible by $`2`$ and gives $`a_1=3`$, while $`\operatorname{num}(1,3)=13`$ is not divisible by $`3`$, so the orbit stops there. Deciding survival by iteration is expensive because the orbit grows doubly exponentially, and it is unnecessary: survival over a finite horizon depends on the initial value only through a factorial residue.

<div id="res:residue" class="theorem">

**Theorem 18** (factorial residue reduction). *For all $`h`$ and all integers $`a\equiv b \pmod{(h+1)!}`$, the orbit from $`a`$ survives $`h`$ forced updates exactly when the orbit from $`b`$ does.*

</div>

<div class="proof">

*Proof.* Let $`M(0,i)=1`$ and $`M(h+1,i)=(i+2)M(h,i+1)`$, an ascending factorial with $`M(h,0)=(h+1)!`$. The numerator is a polynomial with integer coefficients, so congruences transfer; reducing the modulus gives divisibility by $`i+2`$ for one exactly when for the other, and cancelling that common factor from both values and modulus leaves the inductive hypothesis at $`M(h,i+1)`$. ◻

</div>

Formalised as the [factorial residue reduction](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/FiniteHorizonResidue.lean#L134), over the [shrinking-modulus transport](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/FiniteHorizonResidue.lean#L97), the [polynomial congruence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/FiniteHorizonResidue.lean#L26), and the [exact-division cancellation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/FiniteHorizonResidue.lean#L41); the modulus identifications are the [ascending-factorial form](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/FiniteHorizonResidue.lean#L59) and the [factorial value at the initial index](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos243/FiniteHorizonResidue.lean#L69).

At $`h=1`$ the modulus is $`2!=2`$, and surviving one update means $`2\mid a^{2}-2a+3`$, which holds exactly for odd $`a`$: for instance $`\operatorname{num}(0,3)=6`$ but $`\operatorname{num}(0,4)=11`$. So one step of survival is decided by the parity of $`a`$ alone, which is Theorem <a href="#res:residue" data-reference-type="ref" data-reference="res:residue">18</a> at its smallest nontrivial horizon.

The search this supported is superseded. Running it over initial states below $`5000`$ produced forced prefixes of length $`17`$ and no longer, which was evidence and not a proof; Theorem <a href="#res:constant" data-reference-type="ref" data-reference="res:constant">[res:constant]</a> now excludes the constant-negative case outright, for every seed and at every scale. The reduction is retained because it is exact, and because the shrinking-modulus technique transfers to any forced orbit whose step is a polynomial division.

<div class="thebibliography">

9

P. Erdős and E. G. Straus, [*On the irrationality of certain Ahmes series*](https://users.renyi.hu/~p_erdos/1964-19.pdf), J. Indian Math. Soc. (N.S.) **27** (1964), 129–133. MR 175848. D. Duverney, [*Irrationality of fast converging series of rational numbers*](https://www.ms.u-tokyo.ac.jp/journal/pdf/jms080206.pdf), J. Math. Sci. Univ. Tokyo **8** (2001), 275–316. MR 1837165. C. Badea, [*A theorem on irrationality of infinite series and applications*](https://matwbn.icm.edu.pl/ksiazki/aa/aa63/aa6342.pdf), Acta Arith. **63** (1993), no. 4, 313–323. P. Erdős and R. L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory*](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf), Monogr. Enseign. Math. 28, Geneva, 1980, p. 64. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). V. Kovač and T. Tao, [*On several irrationality problems for Ahmes series*](https://arxiv.org/abs/2406.17593), Acta Math. Hungar. **175** (2025), 572–608; preprint arXiv:2406.17593v4. I. O. Bado, *Prime-Support Rigidity and Primitive Pseudo-Greedy Dynamics: Partial Progress on Erdős Problem #243*, author-posted preprint, September 2026, doi:[10.13140/RG.2.2.36612.08325](https://doi.org/10.13140/RG.2.2.36612.08325). Not independently validated here. J. Koizumi, [*Irrationality of the reciprocal sum of doubly exponential sequences*](https://math.colgate.edu/~integers/aa28/aa28.pdf), Integers **26** (2026), Paper No. A28, 17 pp., doi:[10.5281/zenodo.18714404](https://doi.org/10.5281/zenodo.18714404); preprint arXiv:2504.05933v1. T. F. Bloom, [*Erdős Problem \#243*](https://www.erdosproblems.com/243), `erdosproblems.com/243`.

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
