<a id="erdos-249-binary-totient-series"></a>

# A Basis for the 2-Kernel of Euler’s Totient

<div id="prob:firstharmonic" class="problem">

**Problem 1** (first-harmonic anti-concentration on supplier fibres). For each $`h\ge1`$, do there exist $`s\ge1`$ and $`0<\eta<1`$ such that, for every $`X_0`$, there are $`X,L`$ with
``` math
\max(X_0,1)\le X,\qquad h\le L-s,\qquad
 16(2X+h+L+2)\le2^L,
```
for which the four bounds below hold?

</div>

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

For every $`e\ge1`$, the dyadic sections of Euler’s totient through level $`e`$ have rational rank $`2^e+1`$. The two zero-residue sections and the odd-residue sections form a basis, and two families of scalar reductions generate every relation. Divisibility makes an evaluation matrix diagonal modulo a prime, with nonzero diagonal entries. The construction gives rank $`k^e+1`$ in every base $`k\ge2`$ and an integral normal form. Separately, $`\sum_{n\ge1}(\varphi(n)\bmod m)2^{-n}`$ is irrational for every $`m\ge3`$, with a complete rationality classification at dyadic moduli. For $`S=\sum_{n\ge1}\varphi(n)2^{-n}`$, one nonintegral tail shift forces full-depth certificates in every sufficiently late pair of multipliers. Irrationality is equivalent to an explicit central-residue gap for every prospective denominator; its arithmetic supply remains open.

<a id="sec:results"></a>

# A basis and all its relations

Set $`\varphi(0)=0`$. For $`k\ge2`$, the $`k`$-kernel consists of the sequences $`n\mapsto\varphi(k^jn+r)`$ with $`j\ge0`$ and $`0\le r<k^j`$. The following theorem gives a unique coordinate system at every finite level.

<div id="thm:kkernelrank" class="theorem">

**Theorem 2** (exact rank of every totient $`k`$-kernel truncation). *Let $`k\ge2`$ and $`e\ge1`$ be integers, write $`F^{(k)}_{j,r}(n)=\varphi(k^jn+r)`$, and put
``` math
V_{k,e}=\operatorname{span}_{\mathbb{Q}}
 \{\,F^{(k)}_{j,r}:0\le j\le e,\ 0\le r<k^j\,\}.
```
Then $`\dim_{\mathbb{Q}}V_{k,e}=k^e+1`$, and
``` math
\mathcal B_{k,e}
 =\{F^{(k)}_{0,0},F^{(k)}_{1,0}\}
 \cup\{\,F^{(k)}_{j,r}:1\le j\le e,\ 1\le r<k^j,\ k\nmid r\,\}
```
is a basis. Every omitted section reduces to a basis element by an explicit scalar: $`F^{(k)}_{j,0}=k^{j-1}F^{(k)}_{1,0}`$ for $`j\ge1`$, and if $`r=k^tu`$ with $`t=\max\{s:k^s\mid r\}\ge1`$ and $`k\nmid u`$, then
``` math
F^{(k)}_{j,r}=C_k(t,u)\,F^{(k)}_{j-t,u},
 \qquad
 C_k(t,u)=k^t\prod_{\substack{p\mid k\\ p\nmid u}}\Bigl(1-\tfrac1p\Bigr).
```*

</div>

1.  <span id="res:rank" label="res:rank"></span> <span class="smallcaps">\[unconditional progress\]</span> **Exact finite-level rank.** Theorem <a href="#thm:kkernelrank" data-reference-type="ref" data-reference="thm:kkernelrank">2</a> is the coordinate statement: every totient $`k`$-kernel truncation has rank $`k^e+1`$.

The retained condition is $`k\nmid r`$. At $`k=6`$, for example, the residue $`r=2`$ is retained. At base $`2`$ and level $`3`$, the fifteen sections have nine coordinates; the omitted positive-residue sections satisfy
``` math
\varphi(8n+2)=\varphi(4n+1),\qquad
 \varphi(8n+4)=2\varphi(2n+1),\qquad
 \varphi(8n+6)=\varphi(4n+3).
```

<a id="sec:rank"></a>

## The evaluation matrix

The two ingredients are scalar reduction and arithmetic independence. The local formula for $`\varphi`$ gives the displayed reductions. For a prime $`p\mid k`$ that does not divide $`u`$, the argument $`k^{j-t}n+u`$ is a $`p`$-adic unit, so multiplication by $`k^t`$ contributes its power of $`p`$ and one factor $`1-1/p`$. When $`p\mid u`$, the argument already contains $`p`$, and only its power contributes. This gives $`C_k(t,u)`$.

For independence, consider finitely many forms $`L_i(n)=a_in+b_i`$ with positive slopes and $`a_ib_j\ne a_jb_i`$ for $`i\ne j`$. A finite shift makes the intercepts positive. Write $`L_i=g_iA_i`$, where $`A_i`$ is primitive. Choose an odd prime $`\ell`$ avoiding the slopes, all $`g_i\varphi(g_i)`$, and the nonzero cross determinants. In row $`i`$, choose distinct primes $`q_{ij}\equiv1\pmod\ell`$ for $`j\ne i`$, outside the same finite exceptional set, and impose
``` math
L_j(n)\equiv0\pmod{q_{ij}},\qquad A_i(n)\equiv2\pmod\ell.
```
The Chinese remainder theorem combines these congruences. The resulting progression for $`A_i(n)`$ is reduced: a prime $`q_{ij}`$ dividing $`A_i(n)`$ would also divide the nonzero cross determinant; $`\ell`$ is excluded by the chosen residue; and primitivity excludes the primes of the slope. Dirichlet’s theorem supplies arbitrarily large primes $`p=A_i(n)`$ with $`p\nmid g_i`$. Only the selected affine form is made prime in this row. The diagonal value is $`\varphi(g_i)(p-1)\not\equiv0\pmod\ell`$. Each off-diagonal value is divisible by $`\ell`$, since $`q_{ij}-1`$ divides the corresponding totient. One evaluation per row gives
``` math
\bigl(\varphi(L_j(n_i))\bigr)_{i,j}
 \equiv\operatorname{diag}(u_1,\ldots,u_s)\pmod\ell,
 \qquad u_i\ne0.
```
The determinant is nonzero over $`\mathbb{Q}`$.

Apply this construction after restricting a relation among the retained sections to $`n=km+1`$. The positive-residue sections give pairwise nonproportional forms
``` math
k^{j+1}m+(k^j+r),\qquad k\nmid r,
```
and the remaining form is $`km+1`$. Equality between two affine fractions would make the residue at the larger level divisible by $`k`$. The matrix therefore eliminates every positive-residue coefficient. If $`A,B`$ are the two zero-residue coefficients, the restriction gives $`A+B\varphi(k)=0`$. Evaluation at $`n=k`$ gives $`A+Bk=0`$, since $`\varphi(k^2)=k\varphi(k)`$. As $`\varphi(k)<k`$, both coefficients vanish. The reductions give spanning and the count is
``` math
2+\sum_{j=1}^e(k^j-k^{j-1})=k^e+1.
```
This proves Theorem <a href="#thm:kkernelrank" data-reference-type="ref" data-reference="thm:kkernelrank">2</a>. The scalar reduction at level $`j-t`$, with the Euler product written out, is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos249/PaperCompleteR7/KernelIntegral.lean#L226).

<div id="res:basis" class="corollary">

**Corollary 3** (Dyadic basis). *The family
``` math
\{\varphi_{0,0},\varphi_{1,0}\}
 \cup\{\varphi_{j,r}:j\ge1,\ 0<r<2^j,\ r\text{ odd}\},
 \qquad \varphi_{j,r}(n)=\varphi(2^jn+r),
```
is a basis for the rational span of the full dyadic kernel. Every rational relation is generated by the scalar reductions. The complete level-zero truncation has dimension one.*

</div>

<div class="proof">

*Proof.* Every finite subfamily lies in a sufficiently high truncation. The theorem gives its independence; the reductions give equality of the full spans. The level-zero clause is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos249/PaperCompleteR7/ArithmeticAssemblies.lean#L112). ◻

</div>

<div id="cor:integral-normal-form" class="corollary">

**Corollary 4** (Integral normal form). *Let $`k\ge2`$ and $`e\ge1`$. The canonical family is a $`\mathbb{Z}`$-basis of the module generated by the sections through level $`e`$. For each omitted channel $`F_i`$, write its canonical reduction as $`F_i=a_iF_{j(i)}`$, where $`j(i)`$ is retained and $`a_i`$ is a nonnegative integer. In the free abelian group on all the channels, the vectors
``` math
R_i=E_i-a_iE_{j(i)}\qquad(i\text{ omitted})
```
form a $`\mathbb{Z}`$-basis of the kernel of evaluation $`E_i\mapsto F_i`$. In particular, every integral relation has a unique integral expression in these elementary relations, and their rank is $`\sum_{j=1}^{e-1}k^j`$.*

</div>

<div class="proof">

*Proof.* The denominator $`\prod_{p\mid k,\,p\nmid u}p`$ in $`C_k(t,u)`$ divides $`k`$, so the successive channel reductions have integer scalars. They give integral coordinates in the retained family; its rational independence makes these coordinates unique over $`\mathbb{Z}`$ as well.

Now let $`x=\sum_i x_iE_i`$ evaluate to zero. For each omitted index $`i`$, subtract $`x_iR_i`$. The result is supported on retained indices and still evaluates to zero, so independence forces it to vanish. Thus the $`R_i`$ generate the integral relation module. Conversely, the coefficient at an omitted index $`i`$ in $`\sum_h c_hR_h`$ is exactly $`c_i`$: each relation has coefficient one at its own omitted coordinate and zero at all the others. This proves independence and uniqueness without dividing by any integer. There are
``` math
(1+k+\cdots+k^e)-(k^e+1)=\sum_{j=1}^{e-1}k^j
```
omitted channels. The formal statement combines the integral coordinate basis, these two-term relation vectors, and their exact rank. This complete integral normal form is [kernel-checked in Lean](https://github.com/wcook04/plectis-erdos/blob/25ef6245d15a47548c6926369ae8f1a0f0a14a80/ErdosProblems/Erdos249/PaperCompleteR8/KernelRelationBasis.lean#L398). ◻

</div>

For example, at base $`2`$ and depth $`2`$, retain $`F_{0,0},F_{1,0},F_{1,1},F_{2,1},F_{2,3}`$. The two omitted channels satisfy $`F_{2,0}=2F_{1,0}`$ and $`F_{2,2}=F_{1,1}`$, so
``` math
E_{2,0}-2E_{1,0},\qquad E_{2,2}-E_{1,1}
```
are an integral basis of all relations among the seven channels. The rank calculation alone would give two; the basis also identifies every relation and its unique coefficients.

The module here is the one generated by the channels. It is not saturated in the group of all integer-valued sequences: at base $`2`$ and $`e\ge2`$, $`\varphi(4n+3)/2`$ is integer-valued but has canonical coefficient $`1/2`$.

<a id="a-reusable-consequence"></a>

## A reusable consequence

<div id="cor:periodic-freezing" class="corollary">

**Corollary 5** (Freezing periodic coefficients). *If $`L_i`$ are pairwise nonproportional positive-slope affine forms and $`w_i`$ are rational-valued periodic sequences, then
``` math
\sum_i w_i(n)\varphi(L_i(n))=0\quad\text{for all sufficiently large }n
 \quad\Longrightarrow\quad w_i(n)=0\quad\text{for every }i,n.
```*

</div>

<div class="proof">

*Proof.* Choose a common period $`Q`$. On each progression $`n=a+Qt`$, the coefficients are constant and the cross determinants become $`Q(a_ib_j-a_jb_i)\ne0`$. Shift beyond the threshold and apply the affine independence just proved. The statement is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos249/PaperCompleteR7/PeriodicAndPulse.lean#L64), with a separate period for each coefficient. ◻

</div>

The same argument preserves the basis after deletion of a finite prefix. For the two zero channels, large $`n\equiv1\pmod k`$ and large powers of $`k`$ replace the two evaluations used above.

<a id="sec:family"></a>

# Bounded residues and rationality

The residue theorem uses the same separation principle: force neighbouring coefficients to vanish while retaining one central value.

<div id="res:residueseries" class="theorem">

**Theorem 6**. *For every $`m\ge3`$,
``` math
A_m=\sum_{n\ge1}\frac{\varphi(n)\bmod m}{2^n}\notin\mathbb{Q}.
```
For $`k\ge1`$ and $`f:\mathbb{Z}/2^k\mathbb{Z}\to\mathbb{Q}`$, the series $`\sum_{n\ge1}f(\varphi(n)\bmod2^k)2^{-n}`$ is rational exactly when $`f`$ is constant on the even residue classes. If that constant is $`c`$, its value is $`3f(1)/4+c/4`$.*

</div>

<div id="lem:bounded-pulse" class="lemma">

**Lemma 7** (A bounded isolated pulse). *Let $`a_n\in\mathbb{Z}`$ satisfy $`|a_n|\le C`$. Suppose that for arbitrarily large $`L`$ there is $`N>L`$ such that $`a_N\ne0`$ and $`a_{N+t}=0`$ for $`0<|t|\le L`$. Then $`\sum_{n\ge1}a_n2^{-n}`$ is irrational.*

</div>

<div class="proof">

*Proof.* If the sum has denominator $`q`$, every scaled tail $`T_j=\sum_{t\ge1}a_{j+t}2^{-t}`$ belongs to $`q^{-1}\mathbb{Z}`$. Choose $`L`$ so large that $`C2^{-L}<1/q`$. The right zero block gives $`|T_N|\le C2^{-L}<1/q`$, hence $`T_N=0`$. The left zero block now gives $`T_{N-L-1}=a_N2^{-L-1}`$, a nonzero element of $`q^{-1}\mathbb{Z}`$ with absolute value less than $`1/q`$, a contradiction. The statement is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos249/PaperCompleteR7/PeriodicAndPulse.lean#L106). ◻

</div>

<div class="proof">

*Proof of Theorem <a href="#res:residueseries" data-reference-type="ref" data-reference="res:residueseries">6</a>.* Fix a unit $`s\pmod m`$ and a block length $`L`$. For each nonzero $`t\in[-L,L]`$, choose a distinct prime $`q_t\equiv1\pmod m`$ larger than $`L`$ and outside the prime divisors of $`m`$. Prescribe
``` math
p\equiv s\pmod m,\qquad p\equiv-t\pmod{q_t}.
```
This is a reduced progression, because each $`q_t>|t|`$. Dirichlet supplies arbitrarily large primes $`p`$ in it. Then $`m\mid\varphi(p+t)`$ for every $`0<|t|\le L`$, whereas $`\varphi(p)\equiv s-1\pmod m`$.

Subtract $`f(0)`$ from the observable and clear its denominators. Whenever $`f(s-1)\ne f(0)`$, the preceding construction gives arbitrarily long bounded isolated pulses, so Lemma <a href="#lem:bounded-pulse" data-reference-type="ref" data-reference="lem:bounded-pulse">7</a> applies. For the least-residue map choose $`s=-1`$: its central residue is $`m-2\ne0`$ when $`m\ge3`$. For $`m=2^k`$, every even residue $`r`$ has $`r+1`$ a unit, so a nonconstant restriction to the even residues supplies such a pulse. Conversely, $`\varphi(n)`$ is even for every $`n\ge3`$. Constancy on the even classes therefore makes all terms after $`n=2`$ constant, giving the stated rational value. This converse requires no recurrent-support theorem. The three clauses together are [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos249/PaperCompleteR7/RationalObservableClassification.lean#L277). ◻

</div>

The bounded-pulse proof fixes its coefficient bound before choosing the block. For $`S`$, the termwise condition $`2^L\mid\varphi(N+L)`$, with $`N+L>1`$, forces $`2^L\le\varphi(N+L)\le N+L-1`$. Hence the tail envelope $`(N+L+2)2^{-L}>1`$ cannot exclude any positive denominator. The following criterion instead measures cancellation in a weighted prefix.

<a id="sec:carry-rank"></a>

# The actual series and the remaining residue gap

Write
``` math
S=\sum_{n\ge1}\varphi(n)2^{-n},\qquad
 R_N=\sum_{j\ge1}\varphi(N+j)2^{-j},\qquad
 \Delta_h(N)=R_{N+h}-R_N.
```
The prefix identity $`2^NS=\Phi_N+R_N`$, with $`\Phi_N=\sum_{n=1}^N\varphi(n)2^{N-n}\in\mathbb{Z}`$, gives
``` math
\begin{equation}
\label{eq:tail-phase}
 \Delta_h(N)\equiv2^N(2^h-1)S\pmod\mathbb{Z}.
\end{equation}
```
In particular a nonintegral tail difference is a precise arithmetic statement about $`S`$.

<a id="one-seed-removes-the-full-depth-restriction"></a>

## One seed removes the full-depth restriction

For $`h,N,L\in\mathbb{N}`$, let
``` math
D_{h,N,L}=\sum_{j=0}^{L-1}
   \bigl(\varphi(N+h+1+j)-\varphi(N+1+j)\bigr)2^{L-1-j},
 \qquad B=N+h+L+2.
```
Write $`K(h,N,L)`$ for
``` math
B<D_{h,N,L}\bmod2^L<2^L-B.
```
The exact truncation and $`\varphi(n)\le n`$ give
``` math
\begin{equation}
\label{eq:tail-error}
 |2^L\Delta_h(N)-D_{h,N,L}|\le B.
\end{equation}
```
Thus some $`L`$ satisfies $`K(h,N,L)`$ exactly when $`\Delta_h(N)\notin\mathbb{Z}`$: necessity follows from the strict inequalities; sufficiency follows by choosing $`L`$ with $`2^L\|\Delta_h(N)\|_{\mathbb{R}/\mathbb{Z}}>2B`$.

<div id="res:fulldepth" class="theorem">

**Theorem 8** (Full-depth amplification). *Fix $`d\ge1`$ and $`N\ge0`$. If $`\Delta_d(N)\notin\mathbb{Z}`$, then every sufficiently late pair $`\{t,t+1\}`$ contains an $`m`$ such that $`K(md,N,md)`$ holds. Consequently
``` math
\exists t\ge1:\ K(td,N,td)
 \quad\Longleftrightarrow\quad\Delta_d(N)\notin\mathbb{Z}.
```
Requiring this for every $`d\ge1,N\ge0`$ is equivalent to $`S\notin\mathbb{Q}`$.*

</div>

<div class="proof">

*Proof.* Set $`F_t=\Delta_{td}(N)`$. Equation <a href="#eq:tail-phase" data-reference-type="eqref" data-reference="eq:tail-phase">[eq:tail-phase]</a> yields $`F_{t+1}\equiv2^dF_t+F_1\pmod\mathbb{Z}`$. If $`K(td,N,td)`$ fails, <a href="#eq:tail-error" data-reference-type="eqref" data-reference="eq:tail-error">[eq:tail-error]</a> gives
``` math
\|F_t\|_{\mathbb{R}/\mathbb{Z}}\le\epsilon_t,
 \qquad \epsilon_t=2(N+2td+2)2^{-td}.
```
Two adjacent failures would imply $`\|F_1\|\le2^d\epsilon_t+\epsilon_{t+1}`$, impossible for all sufficiently large $`t`$ because the left side is positive and the right side tends to zero. Conversely, if $`F_1`$ is integral, then every $`F_t`$ is integral by the same recurrence, so no certificate exists. Finally, <a href="#eq:tail-phase" data-reference-type="eqref" data-reference="eq:tail-phase">[eq:tail-phase]</a> is nonintegral for every $`d,N`$ when $`S`$ is irrational. If $`S=a/(2^cv)`$ with $`v`$ odd, take $`N=c`$ and $`d=\varphi(v)`$ to make it integral. ◻

</div>

For instance $`D_{1,12,16}=-143140`$, with residue $`53468`$ modulo $`2^{16}`$ and $`B=31`$, supplies a seed. The amplifier produces infinitely many full-depth certificates from this finite fact; it does not provide seeds for all $`d,N`$.

<a id="sec:frontier"></a>

## A single canonical endpoint

For $`c\ge0`$, odd $`v\ge1`$ and a positive multiple $`H`$ of $`\varphi(v)`$, put
``` math
M=\frac{2^H-1}{v},\qquad
 B_{H,c}=\sum_{j=0}^{H-1}\varphi(c+1+j)2^{H-1-j},\qquad K=c+H+1.
```
Euler’s theorem makes $`M`$ integral.

<div id="res:canonicalmersenne" class="equivform">

*Equivalent formulation 9* (Canonical Mersenne gap). The series $`S`$ is irrational if and only if, for every $`c\ge0`$ and odd $`v\ge1`$, some positive multiple $`H`$ of $`\varphi(v)`$ satisfies
``` math
\begin{equation}
\label{eq:canonical-gap}
 K<(-B_{H,c})\bmod M<M-K.
\end{equation}
```

</div>

<div class="proof">

*Proof.* The identity
``` math
B_{H,c}=2^HR_c-R_{c+H}=M(vR_c)-\Delta_H(c)
```
is exact. For $`H\ge1`$, $`|\Delta_H(c)|<c+H+1=K`$. Indeed $`R_N\le N+1`$ for $`N\ge1`$ and $`0<R_0\le3/2`$; the strict inequalities follow by subtracting a positive tail. If $`S=a/(2^cv)`$, then $`vR_c\in\mathbb{Z}`$ and $`\Delta_H(c)\in\mathbb{Z}`$. The residue of $`-B_{H,c}`$ is therefore within distance less than $`K`$ of $`0\pmod M`$, so <a href="#eq:canonical-gap" data-reference-type="eqref" data-reference="eq:canonical-gap">[eq:canonical-gap]</a> fails.

If $`S`$ is irrational, fix $`c,v`$. Then $`vR_c`$ is nonintegral. As $`H`$ tends to infinity through positive multiples of $`\varphi(v)`$, $`\Delta_H(c)/M\to0`$ and $`K/M\to0`$. Hence the fractional part of $`-B_{H,c}/M=-vR_c+\Delta_H(c)/M`$ stays away from both endpoints of $`[0,1]`$, which gives <a href="#eq:canonical-gap" data-reference-type="eqref" data-reference="eq:canonical-gap">[eq:canonical-gap]</a> for all sufficiently large such $`H`$. ◻

</div>

This proof identifies the equivalent missing quantifier. It does not supply $`H`$ arithmetically without assuming the desired irrationality. The equivalence, with the modulus written as the natural quotient $`(2^H-1)/v`$ and $`v`$ odd, is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos249/PaperCompleteR7/ArithmeticAssemblies.lean#L156). The finite residues also satisfy
``` math
\rho_{H,N+1,M}=
 \bigl(2\rho_{H,N,M}-\varphi(N+H+1)+\varphi(N+1)\bigr)\bmod M,
 \quad \rho_{H,N,M}=(-B_{H,N})\bmod M,
```
which is an exact recurrence for searches directed at <a href="#eq:canonical-gap" data-reference-type="eqref" data-reference="eq:canonical-gap">[eq:canonical-gap]</a>.

<a id="sec:nogo"></a>

# Information that does not force the gap

1.  <span id="res:actualorbit" label="res:actualorbit"></span> <span class="smallcaps">\[exact reformulation\]</span> **Actual LCM orbit frontier.** Let $`H_a=\operatorname{lcm}(1,\ldots,2^a)`$ and $`R_a=\operatorname{totientTail}(2H_a)-\operatorname{totientTail}(H_a)`$. Then $`S`$ is irrational if and only if, beyond every threshold $`a_0`$, some $`a\ge a_0`$ has $`R_a\notin\mathbb{Z}`$. This is an exact cofinal nonintegrality criterion for the actual LCM diagonal, not a quantitative separation estimate and not a proof that such indices occur. *Checked:* [exact frontier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitNonintegrality.lean#L37), [forward implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitNonintegrality.lean#L53).

2.  <span id="res:actualsign" label="res:actualsign"></span> <span class="smallcaps">\[unconditional progress\]</span> **Positive LCM corridor and top-edge boundary.** For $`a\ge8`$ and $`J+(a+6)<2\cdot2^a`$, the true translated orbit difference $`\operatorname{totientTail}(2H_a+J)-\operatorname{totientTail}(H_a+J)`$ is strictly positive. If it is represented by an integer and the dyadic modulus has room for the directed endpoint strip, the carry survivor is strictly negative and the discrepancy residue is exactly the top-edge representative $`2^K-\mathrm{carry}_K`$, lying strictly between the strip’s lower edge and $`2^K`$. Thus the positive corridor eliminates the nonnegative true survivor but does not itself produce a central-band contradiction; an independent arithmetic exclusion of the top boundary is still required. *Checked:* [positive corridor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSign.lean#L39), [negative survivor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSign.lean#L172), [top-edge residue](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSign.lean#L211).

3.  <span id="res:factorideal" label="res:factorideal"></span> <span class="smallcaps">\[unconditional progress\]</span> **LCM factor-ideal shift-algebra no-go.** For every $`t\ge3`$, with $`H=\operatorname{lcm}(1,\ldots,t)`$, there is a nonzero synthetic dyadic coboundary whose forcing letters reproduce the actual totient differences at $`t-2`$ prescribed indices and lie in the ideal generated by $`\varphi(H)`$. Every finite integer shift polynomial preserves the exact coboundary cancellation, the $`H`$-factor ideal and all lower factor ideals, together with uniform state and letter bounds. A sparse-anchor variant also preserves every prescribed whole-ray anchor. Hence factor ideals, finite shift-algebra closure and these bounds cannot by themselves force a contradiction. The witness is synthetic: its letters are not claimed to be actual totient differences, nonlinear combinations are outside the theorem, and no cofinal family of certificates follows. *Checked:* [finite shift-algebra no-go](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmFactorIdealPulseObstruction.lean#L798).

The long record supplies a rational control with $`c(n)=\varphi(n)`$ for odd $`n`$, $`|c(n)-\varphi(n)|\le2`$ for even $`n`$, $`0\le c(n)\le n`$, and
``` math
\sum_{n\ge1}c(n)2^{-n}=\frac54.
```
It has an integral tempered carry with dyadic rank at least $`2^e-1`$ at every level. Thus the same lower bound for a hypothetical totient carry is compatible with rationality. For one fixed prime $`p`$, the exact laws $`g(pn)=p g(n)`$ when $`p\mid n`$ and $`g(pn)=(p-1)g(n)`$ otherwise, together with $`g-\varphi=o(n)`$, force $`g=\varphi`$: a nonzero defect keeps a nonzero ratio to the argument along $`p^j n`$. The control fails these laws; its full coefficient rank is asserted only at measured finite depths.

A different obstruction concerns rational approximation. Put
``` math
\Theta_2=\sum_{d\ge1}\frac{\mu(d)}{(2^d-1)^2}=S-\frac12,
 \qquad
 Q(e,Y)=\frac{\bigl(\sum_{d=1}^{Y}\mu(d)/(2^d-1)^{e+2}\bigr)^2}
 {\sum_{d=1}^{Y}\mu(d)/(2^d-1)^{2e+2}}.
```
The divisor-convolution identity gives the displayed value of $`\Theta_2`$, as recorded by Fan \[fan2026totient\]. The following exact extremum is stated in the long record as Theorem `thm:rankonefloor`; its proof is [the sharp-floor argument](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L534) in the linked source.

<div id="res:rankonefloor" class="theorem">

**Theorem 10** (Positive rank-one floor). *For $`e\ge1`$ and $`Y\ge4`$, the denominator of $`Q(e,Y)`$ is positive, and the unique minimiser is $`(e,Y)=(1,5)`$. Every admissible quotient and every nonempty finite positive weighted average of such quotients satisfies
``` math
Q-\Theta_2>\frac{21}{320}.
```
The uniform bound $`Q-\Theta_2>1/15`$ is false already at $`(1,5)`$.*

</div>

This theorem treats averages after the quotients are formed. Signed coefficients, coupling before the quotient, and higher-rank kernels require separate arguments. For any proposed rational approximants $`p_j/q_j`$ in lowest terms, a sufficient arithmetic target is
``` math
0<q_j\left|\Theta_2-p_j/q_j\right|\longrightarrow0.
```
Ordinary convergence and Hankel nonvanishing do not contain this denominator estimate. The canonical gap <a href="#eq:canonical-gap" data-reference-type="eqref" data-reference="eq:canonical-gap">[eq:canonical-gap]</a> remains the equivalent endpoint; the approximation estimate is one stronger sufficient route.

<a id="sec:open"></a>

# Antecedents and proof record

Allouche and Shallit introduced $`k`$-regular sequences \[allouche-shallit\]. Coons proved that $`\varphi`$ is not $`k`$-regular \[coons\]; Martin’s stronger affine ordering theorem implies the independence in Section <a href="#sec:rank" data-reference-type="ref" data-reference="sec:rank">1.1</a> \[martin-phi-inequalities\]. The basis theorem gives the exact finite-level normal form. Wong \[wong2015\] proved least-residue irrationality when the denominator base equals the modulus; Section <a href="#sec:family" data-reference-type="ref" data-reference="sec:family">2</a> fixes base two and classifies dyadic observables. The original question appears in Erdős and Graham \[erdosgraham1980, p. 61\].

The exact all-base basis and rank, residue-series irrationality, full-depth amplification, canonical equivalence and positive rank-one floor have proofs in the supplied Lean source snapshot: [amplification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L364), [canonical gap](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L3165), and [rank-one floor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L624). The historical source links retain `99f4bf47422a`; the all-base module requires a matching public source supplement. The integral normal form has its ordinary proof above. The periodic transport lemma is checked in `PeriodicTotientIndependence.lean`; the eventual version follows by the displayed threshold shift. The rational control and the termwise-window and prime-dilation boundaries are proved in `ParityPerturbedRationalControl.lean` and `PrefixValuationAndControlRigidity.lean`, respectively. Finite evaluation ranks and the all-level carry lower bound remain distinct. The long record retains the separate continued-fraction bounds $`q\ge2^{39989}`$ and $`q>10^{12038}`$ under rationality, alongside the Lean-checked Farey exclusion. Neither implies the universal gap.

<a id="app:sources"></a>

# Guide to the formal sources

The public snapshot used by this note is recorded by the following source links.

[checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L160), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L169), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailPeriodKiller.lean#L150), [definition](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailPeriodKiller.lean#L72), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmConeFlatness.lean#L316), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailPeriodKiller.lean#L404), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailPeriodKiller.lean#L407), [definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GenericTailOrbitRigidity.lean#L67), [residue recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L2322), [dominance over the remote condition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L3132), [exact equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L3165), [eventual two-syndeticity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L364), [pointwise equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L388), [global equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L406), [cofinal depth deletion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L421), [cofinal endpoint](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L438), [independence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L1265), [span equality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L1380), [basis](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L1392), [independence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L935), [dimension](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L989), [the exact finite-truncation rank](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L1084), [infinite-dimensionality directly](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L1145), [unique minimizer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L534), [uniform $`21/320`$ floor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L624), [$`1/16`$ floor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L634), [$`1/15`$ failure](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L645), [positive direct sums](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L655), [rational linear-form obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L693), [coordinate specification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelIndex.lean#L124), [unique representation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelIndex.lean#L213), [level count](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelIndex.lean#L241), [full index count](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelIndex.lean#L277), [exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18371), [reduced-denominator form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18384), [first failure](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GapFareyBound.lean#L225), [the barrier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientCarryKernelRigidity.lean#L300), [rank transport from <a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a>](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientCarryKernelRigidity.lean#L211), [the modular-period/rank frontier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailCarryPeriod.lean#L224), [forcing vanishing](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailCarryPeriod.lean#L126), [geometric reduction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailCarryPeriod.lean#L140), [identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18445), [sign](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MersenneLambertLadder.lean#L370), [primes](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MersenneLambertLadder.lean#L297), [prime powers](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MersenneLambertLadder.lean#L272), [unboundedness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MersenneLambertLadder.lean#L321), [divisor-count layer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GcdMomentCalculus.lean#L216), [first gcd moment](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GcdMomentCalculus.lean#L235), [exact centre decomposition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquaredMersenneDiagonalEnclosure.lean#L138), [sharp enclosure](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquaredMersenneDiagonalEnclosure.lean#L408), [separation criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquaredMersenneDiagonalEnclosure.lean#L426), [target equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FullTargetPrimeAdjunctionNoGo.lean#L139), [endpoint nonnegativity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FreshPrimeDeficitDecomposition.lean#L91), [foreign-channel identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FreshPrimeDeficitDecomposition.lean#L184), [five-point loss bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FreshPrimeDeficitDecomposition.lean#L269), [simultaneous finite family](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L297), [finite horizon](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L327), [vanishing block](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L459), [nonzero block](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L477), [centrality equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalFreshLossBridge.lean#L2667), [equivalence of the two conditions](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalFreshLossBridge.lean#L2757), [conditional irrationality theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalFreshLossBridge.lean#L2932), [finite complement bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/ActualForeignResidueProjection.lean#L276), [exact channel split](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/ActualForeignResidueProjection.lean#L308), [conditional target-miss theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/ActualForeignResidueProjection.lean#L414), [exact frontier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitNonintegrality.lean#L37), [forward implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitNonintegrality.lean#L53), [positive corridor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSign.lean#L39), [negative survivor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSign.lean#L172), [top-edge residue](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSign.lean#L211), [finite shift-algebra no-go](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmFactorIdealPulseObstruction.lean#L798), [sparse-anchor no-go](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmFactorIdealPulseObstruction.lean#L866), [the periodic theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L12811), [no fixed index](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/PrimitiveDeterminantLift.lean#L169), [the primorial divisibility](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/PrimitiveDeterminantLift.lean#L148), [pointwise](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmConeFlatness.lean#L399), [cofinal at each shift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmConeFlatness.lean#L412), [$`\operatorname{lcm}`$ diagonal](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmConeFlatness.lean#L426), [window-separated pairs](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/PivotAntiReconstruction.lean#L1765), [the conditional implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L16025), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L8335), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18434), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18429), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18454), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18557), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GcdMomentCalculus.lean#L349), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GcdMomentCalculus.lean#L474), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L823), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L882), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GenericTailOrbitRigidity.lean#L426), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GapFareyBound.lean#L51), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GapFareyBound.lean#L176), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L15986), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GapFareyBound.lean#L88), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18572), [diagonal split](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FreshPrimeDeficitDecomposition.lean#L171), [the $`t=2^4`$, length-$`23`$ kill](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmShortKill.lean#L18), [the $`t=2^6`$, length-$`93`$ kill](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmShortKill.lean#L27), [actual-orbit non-integrality at both heights](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmShortKill.lean#L35), [but explicitly stops at that finite prefix](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmShortKill.lean#L54), [recorded here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSeparation.lean#L141), [by the normalization identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSeparation.lean#L179), [through the exact threshold lemma](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSeparation.lean#L208), [the cofinal separation hypothesis](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSeparation.lean#L254), [the conditional endpoint theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSeparation.lean#L305), [the staircase is impossible under the stated room hypothesis](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmTopEdgeStaircase.lean#L251), [terminal-remainder identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmTopEdgeStaircase.lean#L297), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TropicalCurvatureCarry.lean#L137), [asks](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L157), [a positive adaptive truncation budget](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L485), [$`S`$ is irrational](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L524), [density hypothesis](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L35), [block-gap hypothesis](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L25), [density-to-gap implication](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L45), [exact squaring recurrence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L167), [iterate formula](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L191), [initial-phase normal form](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L201), [initial-phase equivalence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L278), [dyadic-root obstruction](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L322), [prime-alignment implication](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L465), [$`s=1`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L28), [$`s=2`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L36), [first difference](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L44), [second difference](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L51), [mixed difference](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L22), [separable case](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L26), [fixed-stencil uniqueness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L32), [a four-point divisor-layer identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L45), [a centred representative for a residue class modulo an even modulus](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L62), [Layer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L95), [BoundedOrder](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L102), [FinitePrimeEscape](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L151), [definition](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CarrySurvivorExtinction.lean#L515), [definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailPeriodKiller.lean#L57), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmConeFlatness.lean#L357), [list](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalPincerCertificatesT64.lean#L1933), [verification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalPincerCertificatesT64.lean#L1967), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Skip/LadderT67.lean#L71264), [CyclotomicAnchoredKillSupply](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L3231), [the checked equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L3327), [checked conditional support/period no-go](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L1706), [unbounded prime divisors](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L158), [the checked binary-layer theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L1693), [ApFullDepthEscape](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PeriodMultipleEscape.lean#L441), [membership](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L299), [injectivity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L367), [image equality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L384), [checked counterexample](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L394), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L514), [the conditional irrationality theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L577), [the budget condition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L543), [the first-harmonic gap](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L549), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelReduction.lean#L60), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelReduction.lean#L117).

<div class="thebibliography">

9 J.-P. Allouche and J. Shallit, *The ring of $`k`$-regular sequences*, Theoret. Comput. Sci. **98** (1992), 163–197. doi:10.1016/0304-3975(92)90001-V. M. Coons, *(Non)Automaticity of number theoretic functions*, J. Théor. Nombres Bordeaux **22** (2010), 339–352, Theorem 3.2. doi:10.5802/jtnb.718. G. Martin, *Simultaneous inequalities among values of the Euler phi-function*, 2006, arXiv:math/0603053, Theorem 1 and Corollary 4. E. Wong, answer to [question 1210886](https://math.stackexchange.com/questions/1210886), Mathematics Stack Exchange, 29 March 2015. P. Erdős and R. L. Graham, *Old and New Problems and Results in Combinatorial Number Theory*, 1980, p. 61. S. Fan, comment on Erdős Problem \#249, 16 May 2026, 19:01, [Erdős Problems discussion thread](https://www.erdosproblems.com/forum/thread/249).

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
