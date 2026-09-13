<a id="erdos-1049-rational-base-lambert"></a>

# Irrationality of F(31/4) and the Exact Normalized Hankel Order

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

For coprime integers $`a>b\ge1`$, the Lambert value $`F(a/b)=\sum_{n\ge1}((a/b)^n-1)^{-1}`$ is irrational whenever $`\log b/\log a<\theta^*`$, where the explicit constant below satisfies $`\theta^*\approx0.4056830213840605`$. In particular, $`F((31/4)^r)`$ is irrational for every integer $`r\ge1`$. The same forms bound its irrationality exponent uniformly in $`r`$. This is an ordinary proof: it uses the polynomial conclusion of Zudilin’s Lemma 7 before the source’s integer-specialisation step; Lean checks finite subclaims, not the irrationality theorem. Cyclotomic factors are cancelled before the rational-base denominator is cleared; the degree of the resulting polynomial pair determines the cost. The argument does not cover $`3/2`$. For the normalised Hankel determinant in the second construction we prove
``` math
\operatorname{ord}_qV_N^*=\frac{N(N-1)(2N-1)}6,
 \qquad [q^{\operatorname{ord}_qV_N^*}]V_N^*
       =\frac{(N!)^2(N+1)!}{2^N}.
```
The exponent and coefficient come from a unique least-order tuple in a formal moment expansion. A quantitative selector criterion separates local divisibility from the additional estimates needed for a small nonzero real remainder.

<a id="sec:problem"></a>

# Introduction

For $`t>1`$, expansion of each geometric series gives
``` math
F(t)=\sum_{n\ge1}\frac1{t^n-1}
     =\sum_{n\ge1}\frac{\tau(n)}{t^n},
```
where $`\tau(n)`$ is the number of positive divisors of $`n`$. Erdős Problem #1049 asks for irrationality at every rational $`t>1`$ \[erdos1988, p. 102\]. The theorem below proves an explicit sufficient region and settles the power family in the title.

Cyclotomic cancellation produces positive forms $`\Lambda_n=U_nF-V_n`$ with integral coefficient polynomials of degree at most $`W_n`$, and
``` math
\log\!\bigl(b^{W_n}\Lambda_n(a/b)\bigr)
 =\bigl(C_1\log b-C_0\log a\bigr)n^2+o(n^2).
```
A negative exponent yields positive integral linear forms tending to zero.

The order of these operations explains the region. At a rational base $`a/b`$, each remaining polynomial degree costs a power of $`b`$ when denominators are cleared. Cancelling a common cyclotomic factor first reduces that degree. The proof must then compare the actual cancelled degree with the decay of the positive remainder; divisibility alone gives neither estimate.

The Hankel argument concerns a different family. Its moment expansion makes one increasing index tuple responsible for the first coefficient. The final sections explain what local cancellation can establish at $`3/2`$ and specify the real estimate that would complete that approach. The complete catalogue of other constructions and their failure witnesses is retained in the long record.

<a id="sec:rational-base-irrationality"></a>

# A rational base at which $`F`$ is irrational

Write $`\psi_1(u)=\sum_{k\ge0}(k+u)^{-2}`$. Let $`\mathcal I`$ be the thirteen intervals listed in the proof and put
``` math
C_1=\frac{1091}{2},\qquad
 J=\sum_{[u,v)\in\mathcal I}\bigl(\psi_1(u)-\psi_1(v)\bigr),\qquad
 C_0=266-\frac3{\pi^2}(225-J).
```
Thus $`\theta^*=C_0/C_1`$ and $`\mu=C_1/C_0`$ are defined exactly.

<div id="res:rational-base-threshold" class="theorem">

**Theorem 1** (rational-base region). *Let $`a>b\ge1`$ be coprime integers with
``` math
\begin{gathered}
 b^{\mu}<a,\qquad\text{equivalently}\qquad
 \frac{\log b}{\log a}<\theta^*,\\
 \theta^*=\frac{C_0}{C_1}=0.4056830213840605\ldots,\\
 \mu=\frac{C_1}{C_0}=2.4649786835749750\ldots.
\end{gathered}
```
Then $`F(a/b)`$ is irrational.*

</div>

The cancellation is performed before homogenisation, so the clearing degree is the degree of the cancelled pair. The value $`3/2`$ is outside this sufficient region: $`J\le\psi_1(1/14)-\psi_1(1)<196`$ gives $`\theta^*<266/(1091/2)<1/2<\log2/\log3`$.

<div class="proof">

*Proof of Theorem <a href="#res:rational-base-threshold" data-reference-type="ref" data-reference="res:rational-base-threshold">1</a>.* Set
``` math
a_0=14n+1,\quad a_1=12n+1,\quad a_2=14n+1,\quad\beta=27n+2,
 \qquad N=15n.
```
Use the coefficient pair $`A_n,B_n`$ of the source identities \[zudilin2004, (8)–(11)\], with $`H_n=A_nF-B_n`$. Put $`D_N(X)=\prod_{\ell=1}^{N}\Phi_\ell(X)`$, $`M_n=266n^2+34n+1`$, and
``` math
\Omega_n(X)=\prod_{\ell=2}^{N}\Phi_\ell(X)^{\nu_\ell},
 \qquad \nu_\ell=\omega(n/\ell),
```
where the periodic function
``` math
\begin{split}
\omega(x)=\max\{0,&\ \lfloor14x\rfloor+\lfloor13x\rfloor
                  -\lfloor12x\rfloor-\lfloor15x\rfloor,\\
                &\ 2\lfloor14x\rfloor-\lfloor13x\rfloor
                  -\lfloor15x\rfloor\}
\end{split}
```
is zero or one. Its support in $`[0,1)`$ consists of
``` math
\begin{gathered}
\,[1/14,1/12),\ [1/7,1/6),\ [3/14,1/4),\ [2/7,1/3),\\
[5/14,2/5),\ [3/7,7/15),\ [1/2,8/15),\ [4/7,3/5),\\
[9/14,2/3),\ [5/7,11/15),\ [11/14,4/5),\\
[6/7,13/15),\ [13/14,14/15).
\end{gathered}
```
These are the intervals $`\mathcal I`$ used to define $`J`$. The zero-one values and this thirteen-interval support are [omega indicator](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperOmegaIndicatorR7.lean#L1297).

#### Integral polynomials and their degrees.

The source’s polynomial inclusion is Lemma 7, display (23). Its parameter vector is $`n(13,14,12,14,15,13)`$, its maximum is $`15n`$, and $`\beta-a_1-a_2=n>0`$. Its hypotheses therefore hold for every $`n\ge1`$. It gives
``` math
\Lambda_n(X)=X^{-M_n}\frac{D_N(X)}{\Omega_n(X)}H_n(X)
            =U_n(X)F(X)-V_n(X),\qquad U_n,V_n\in\mathbb Z[X].
```
This is the polynomial conclusion before the source’s subsequent integer-specialisation step in display (24). The coefficientwise interpretation also follows by comparing the source rational coefficients: $`F`$ is not a rational function, since $`F(e^h)=h^{-1}\log(1/h)+O(h^{-1})`$ as $`h\downarrow0`$. For this estimate split the original sum at $`n=1/h`$; the remaining geometric tail is $`O(h^{-1})`$.

In the source expression for $`A_n`$, the degree of the $`k`$th summand is
``` math
d_k=a_0k+E_k+(a_1-1)(k-a_1)+(\beta-k-1)(k-a_2),
```
where
``` math
E_k=\frac{a_1(a_1-1)-(\beta-a_2)(\beta-a_2-1)
                   +(\beta-k)(\beta-k-1)}2.
```
For $`a_2\le k\le\beta-2`$, one has $`d_{k+1}-d_k=40n+1-k>0`$. There is therefore a unique highest-degree summand, and
``` math
K_n:=\deg A_n=\frac{1091n^2+81n+2}{2},\qquad
 W_n:=\deg U_n=K_n-M_n+\sum_{\ell\le15n}(1-\nu_\ell)\varphi(\ell).
```
For fixed $`n`$, the positive representation below gives $`H_n(x)=O(1)`$ as $`x\to\infty`$. Hence $`\Lambda_n(x)=O(x^{W_n-K_n})`$. Since $`F(x)=O(x^{-1})`$ and $`K_n\ge1`$, the identity $`V_n=U_nF-\Lambda_n`$ gives $`\deg V_n\le W_n-1`$. Thus $`W_n`$ clears both coordinates.

#### The limiting degree cost.

The elementary summatory estimate $`\sum_{\ell\le y}\varphi(\ell)=3y^2/\pi^2+O(y\log y)`$ gives
``` math
\frac1{n^2}\sum_{\ell\le15n}\varphi(\ell)\longrightarrow\frac{675}{\pi^2}.
```
For $`[u,v)\in\mathcal I`$, the condition $`\{n/\ell\}\in[u,v)`$ is the disjoint union of intervals $`n/(k+v)<\ell\le n/(k+u)`$ for $`k\ge0`$. For finitely many $`k`$ the same summatory estimate applies term by term. The remaining terms have total normalised mass $`O(1/K^2)`$ after truncation at $`k=K`$, since they involve only $`\ell\le n/(K+u)`$. Letting first $`n`$ and then $`K`$ tend to infinity proves
``` math
\frac1{n^2}\sum_{\ell\le15n}\nu_\ell\varphi(\ell)
 \longrightarrow\frac3{\pi^2}
 \sum_{[u,v)\in\mathcal I}\sum_{k\ge0}
 \left(\frac1{(k+u)^2}-\frac1{(k+v)^2}\right)=\frac{3J}{\pi^2}.
```
Here no contributing index exceeds $`14n`$, since $`u\ge1/14`$. Consequently
``` math
K_n/n^2\longrightarrow C_1,\qquad
 (K_n-W_n)/n^2\longrightarrow C_0.
```

#### A positive remainder at every fixed real base.

For $`x>1`$ and $`q=1/x`$, the source identity has the positive representation
``` math
H_n(x)=\sum_{t\ge0}q^{a_0t}
 \frac{(q^{t+1};q)_{a_1-1}}{(q;q)_{a_1-1}}
 \frac{(q;q)_{\beta-a_2-1}}{(q^{a_2+t};q)_{\beta-a_2}}.
```
The last denominator has length $`\beta-a_2`$, as required by the source’s gamma expression (7) and residues (8). The shorter length in one unnumbered product on printed p. 156 is an indexing discrepancy. Every finite product lies between $`P=(q;q)_\infty>0`$ and $`1`$, so
``` math
P^2\le H_n(x)\le\frac{P^{-2}}{1-q^{a_0}}.
```
In particular $`\log H_n(x)=O_x(1)`$ and $`\Lambda_n(x)>0`$.

For fixed $`x>1`$, the cyclotomic identity
``` math
\log\Phi_\ell(x)-\varphi(\ell)\log x
 =\sum_{d\mid\ell}\mu(d)\log(1-x^{-\ell/d})
```
has total absolute error $`O_x(n)`$ over $`\ell\le15n`$. Indeed, it is at most $`15n B(x)`$, where
``` math
B(x)=\sum_{d\ge1}\frac{-\log(1-x^{-d})}{d}<\infty.
```
Since $`0\le1-\nu_\ell\le1`$, it follows that
``` math
\log\Lambda_n(x)=-(K_n-W_n)\log x+O_x(n).
```

#### Homogenisation.

Because $`U_n,V_n`$ are integral polynomials of degree at most $`W_n`$, $`b^{W_n}U_n(a/b)`$ and $`b^{W_n}V_n(a/b)`$ are integers. That integrality and the cleared linear-form identity it produces are [cleared linear form identity](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperHomogenisationR7.lean#L61). Moreover
``` math
\begin{split}
 \log\bigl(b^{W_n}\Lambda_n(a/b)\bigr)
 &=K_n\log b-(K_n-W_n)\log a+O_{a/b}(n)\\
 &=\bigl(C_1\log b-C_0\log a\bigr)n^2+o(n^2).
\end{split}
```
The coefficient is negative under the theorem’s hypothesis. Thus positive integral linear forms in $`F(a/b)`$ tend to zero. If $`F(a/b)=r/s`$ were rational, every such form would have absolute value at least $`1/|s|`$, a contradiction. The separation bound for a nonzero integral form at a rational target is [rational integer linear form gap](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/TwoSelectorRemainderEscape.lean#L128). ◻

</div>

<div id="res:thirtyone-four" class="corollary">

**Corollary 2**. *$`F\bigl((31/4)^r\bigr)`$ is irrational for every integer $`r\ge1`$.*

</div>

<div class="proof">

*Proof.* The exact inequalities $`31^2<4^5`$ and $`4^{200}<31^{81}`$ give $`2/5<\log4/\log31<81/200`$. The first term of each trigamma difference yields
``` math
J\ge J_0:=\sum_{[u,v)\in\mathcal I}(u^{-2}-v^{-2})
   =\frac{2015640690251}{25971865920}.
```
Using $`\pi>157/50`$ gives the rational lower bound
``` math
\theta^*>\frac{2359630009523263}{5820307922172744}
           >\frac{81}{200}.
```
Finally, the logarithmic ratio and coprimality are preserved by a common positive integer power. ◻

</div>

<div id="cor:rational-base-measure" class="corollary">

**Corollary 3** (an irrationality measure uniform over powers). *For coprime $`a>b\ge1`$ with $`\theta=\log b/\log a<\theta^*`$ and every integer $`r\ge1`$,
``` math
\mu_{\rm irr}\!\left(F((a/b)^r)\right)
 \le\frac{1-\theta}{\theta^*-\theta}.
```
Here $`\mu_{\rm irr}(\xi)`$ is the supremum of the exponents $`\nu`$ for which $`|\xi-p/q|<q^{-\nu}`$ has infinitely many reduced rational solutions. In particular, $`\mu_{\rm irr}(F((31/4)^r))<301`$ for every $`r\ge1`$.*

</div>

<div class="proof">

*Proof.* The raw source coefficient is a sum of $`O(n)`$ Laurent monomials times two Gaussian polynomials, each of coefficient sum at most $`2^{27n+2}`$. Its coefficient norm is $`\exp(O(n))`$, and every exponent is at most $`K_n`$. The same normalising multiplier used above therefore gives
``` math
|U_n(x)|\le x^{W_n}\exp(O_x(n))\qquad(x>1\text{ fixed}).
```
Set $`\xi=F(a/b)`$, $`Q_n=b^{W_n}U_n(a/b)`$ and $`P_n=b^{W_n}V_n(a/b)`$. With
``` math
\alpha=(C_1-C_0)\log a,\qquad
 \tau=C_0\log a-C_1\log b>0,
```
we have $`\log(Q_n\xi-P_n)=-\tau n^2+o(n^2)`$ and $`|Q_n|\le\exp(\alpha n^2+o(n^2))`$.

For integers $`A,B,p,q`$ with $`q>0`$, if $`L=A\xi-B`$ and $`2q|L|\le1`$, then
``` math
|L|\le |A|\,|\xi-p/q|.
```
When $`Ap-Bq=0`$ this is equality. Otherwise the nonzero integer $`Ap-Bq`$ gives $`1/q\le |L|+|A|\,|\xi-p/q|`$, which proves the inequality. For a fixed $`\eta\in(0,\tau)`$ choose $`n=\lceil\sqrt{\log(2q)/(\tau-\eta)}\rceil`$ and apply it to $`(Q_n,P_n)`$. The two-sided remainder estimate yields
``` math
|\xi-p/q|\ge
 q^{-(\alpha+\tau+2\eta)/(\tau-\eta)-o(1)}.
```
Let $`\eta\downarrow0`$. The resulting bound is $`1+\alpha/\tau=(1-\theta)/(\theta^*-\theta)`$. Taking a common power multiplies $`\alpha,\tau`$ by $`r`$, leaving this quotient unchanged; the constants in the approximation inequality may depend on $`r`$. For $`31/4`$, sixteen terms of each trigamma difference and $`\pi>314159/100000`$ give $`\theta^*>0.40568`$. The logarithm series gives $`\log4/\log31<0.4036982`$. Thus the bound is less than $`2981509/9909<301`$. ◻

</div>

<a id="comparison-and-scope."></a>

#### Comparison and scope.

Bundschuh and Väänänen’s Theorem 2 at $`\alpha=-1`$ \[bv1994, p. 177\] gives $`\log b/\log a<\theta_{\rm BV}:=1/2-1/\pi^2`$. Since $`\pi^2<10`$, one has $`\theta_{\rm BV}<2/5<\log4/\log31`$. The displayed sufficient regions therefore differ on $`[\theta_{\rm BV},\theta^*)`$. The direction $`(14,12,14;27)`$, its thirteen intervals and the constant $`\mu\approx2.46497868`$ are inherited from \[zudilin2004, p. 162\], where $`\mu`$ bounds an integer-base irrationality exponent. The rational-base extension announced in \[zudilin2016, Section 2\] has the same shape with an unspecified computable constant. Here the polynomial specialisation identifies $`\mu`$ as admissible for $`F`$; no priority claim is attached.

<div id="res:sevenhalves" class="theorem">

**Theorem 4** (the $`7/2`$ height condition). *The [integer power certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L32) $`2^{18}<7^7`$ yields the [Archimedean height condition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L83)
``` math
\frac{\log 7}{\log(7/2)}
 <
 \left(\frac12+\frac1{\pi^2}\right)^{-1}.
```*

</div>

This is the elementary parameter check at $`q=7/2`$ in Bundschuh and Väänänen’s Theorem 2 ($`\alpha=-1`$). Their analytic irrationality theorem is not a Lean result here.

Negative bases are not treated.

<a id="the-base-uniform-degree-restriction"></a>

## The base-uniform degree restriction

The preceding construction uses degree and decay estimates valid at every fixed real base greater than one. Such uniformity itself imposes a limit.

<div id="res:archimedean-cap" class="theorem">

**Theorem 5** (Archimedean cap on base-uniform rank-two families). *Let $`(U_n,V_n)`$ be pairs in $`\mathbb Z[X]^2`$ satisfying $`\Lambda_n(x)=U_n(x)F(x)-V_n(x)\ne0`$, $`\deg U_n,\deg V_n\le\delta n^2(1+o(1))`$, $`\log\max(H(U_n),H(V_n))\le h n^2(1+o(1))`$ with $`H`$ the $`\ell^1`$ coefficient norm, and $`\log|\Lambda_n(x)|=-\sigma n^2\log x\,(1+o(1))`$ for every real $`x>1`$, with $`\sigma,\delta>0`$ and $`h\ge0`$ independent of $`x`$. Then with $`d_n=\max(\deg U_n,\deg V_n)`$, the homogenised forms $`b^{d_n}\Lambda_n(a/b)`$ tend to zero whenever $`\log b/\log a<\sigma/(\sigma+\delta)`$, and $`\sigma/(\sigma+\delta)\le1/2`$.*

</div>

<div class="proof">

*Proof.* Write $`H_n=\max(H(U_n),H(V_n))`$. Then $`|U_n(x)|,|V_n(x)|\le H_n x^{d_n}`$ for real $`x>1`$. Suppose $`\sigma>\delta`$ and choose an integer $`p\ge2`$ with $`(\sigma-\delta)\log p>h`$. Set $`a_n=U_n(p)`$, $`b_n=V_n(p)`$ and $`L_n=a_n F(p)-b_n`$. Hypotheses on height and degree give $`|a_n|\le\exp((h+\delta\log p)n^2+o(n^2))`$, while $`|L_n|=\exp(-\sigma\log p\,n^2+o(n^2))`$. The adjacent integer
``` math
a_nb_{n+1}-a_{n+1}b_n=a_{n+1}L_n-a_n L_{n+1}
```
is then $`o(1)`$, hence eventually zero. Also $`a_n\ne0`$ for large $`n`$: otherwise the nonzero integer $`L_n=-b_n`$ would have absolute value less than $`1`$. Thus $`b_n/a_n`$ is eventually a fixed rational $`r`$. If $`F(p)\ne r`$ then $`|L_n|\ge|F(p)-r|`$; if $`F(p)=r`$ then $`L_n=0`$. Both contradict the hypotheses, so $`\sigma\le\delta`$. The integer argument of this paragraph, from the two cross-product limits to the contradiction, is [no small forms of cross product limits](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperRankTwoCapR7.lean#L123). The homogenised logarithm satisfies
``` math
\limsup_{n\to\infty} n^{-2}\log\bigl|b^{d_n}\Lambda_n(a/b)\bigr|
 \le \delta\log b-\sigma\log(a/b),
```
which is negative on the stated sufficient region. The arithmetic form of that region is [logarithmic region iff negative balance](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperRankTwoCapR7.lean#L144), and the final numerical clause is [half cap iff](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperRankTwoCapR7.lean#L155). The conclusion bounds the sufficient cutoff furnished by the displayed degree estimate. An exclusion for a particular family requires its actual degree and remainder asymptotics. ◻

</div>

<a id="sec:hankel-order"></a>

# Exact normalized-Hankel order in Zudilin’s construction

Here the problem is cancellation inside a determinant. Entrywise orders give only a lower bound because terms of that order may cancel. The moment expansion below resolves this by finding one uniquely least-order index tuple, whose coefficient is nonzero. This is a formal-power-series argument; fixed-base estimates are a separate question addressed after the proof.

At $`x=z=1`$, Zudilin’s normalized moments are
``` math
v_m^*=\sum_{t\ge0}q^{(m+1)t}
 \frac{(q;q)_m^3(q^{t+1};q)_m}{(q^{m+1+t};q)_{m+1}},
 \qquad
 V_N^*=\det_{0\le i,j<N}(v_{i+j}^*).
```
His row transformation proves
``` math
\operatorname{ord}_q V_N^*\ge
 \frac{N(N-1)(2N-1)}6
```
for every $`N\ge1`$ \[zudilin2016, Section 4\]. A formal moment expansion identifies the unique least-order term and shows that this estimate is always sharp.

<div id="res:zudilin-sharp-qorder" class="theorem">

**Theorem 6** (sharp normalized Hankel order). *For every $`N\ge1`$,
``` math
\operatorname{ord}_q V_N^*=\frac{N(N-1)(2N-1)}6,
```
and the coefficient of the first nonzero monomial is
``` math
[q^{N(N-1)(2N-1)/6}]V_N^*
   =\frac{(N!)^2(N+1)!}{2^N}.
```*

</div>

<div class="proof">

*Proof.* Write $`P=(q;q)_\infty`$ and introduce the coefficientwise formal series
``` math
G_q(w)=\frac1{(w;q)_\infty^3}
 \sum_{t\ge0}\frac{w^t}{(q;q)_t}
       \frac{(q^tw^2;q)_\infty}{(q^tw;q)_\infty^2},
 \qquad a_k(q)=[w^k]P^4G_q(w).
```
For fixed $`w`$-degree, all operations define power series in $`q`$. The product identities $`(q;q)_m=P/(q^{m+1};q)_\infty`$ and $`(q^a;q)_m=(q^a;q)_\infty/(q^{a+m};q)_\infty`$ give the exact formal identity
``` math
v_m^*=P^4G_q(q^{m+1})
      =\sum_{k\ge0}a_k(q)q^{(m+1)k}.
```
At $`q=0`$, the term $`t=0`$ in $`G_q`$ is $`(1-w^2)/(1-w)^5`$ and the terms $`t\ge1`$ sum to $`w/(1-w)^4`$. Consequently
``` math
G_0(w)=\frac{1+2w}{(1-w)^4},\qquad
 a_k(0)=\frac{(k+1)^2(k+2)}2=:c_k>0.
```

Apply Cauchy–Binet to a finite truncation of the moment sum and then pass coefficientwise to the limit. This is legitimate because only finitely many increasing index tuples contribute to any fixed $`q`$-degree. It gives
``` math
V_N^*=\sum_{k_0<\cdots<k_{N-1}}
 \left(\prod_{i=0}^{N-1}a_{k_i}(q)q^{k_i}\right)
 \prod_{0\le i<j<N}(q^{k_i}-q^{k_j})^2.
```
The summand indexed by $`(k_i)`$ has order
``` math
\sum_{i=0}^{N-1}(2N-1-2i)k_i.
```
Every weight is positive and $`k_i\ge i`$. Equality with the least possible order occurs uniquely when $`k_i=i`$ for every $`i`$. That tuple contributes
``` math
\sum_{i=0}^{N-1}(2N-1-2i)i=\frac{N(N-1)(2N-1)}6
```
and leading coefficient
``` math
\prod_{i=0}^{N-1}c_i=\frac{(N!)^2(N+1)!}{2^N}.
```
No other tuple can cancel this coefficient. ◻

</div>

<a id="formal-order-and-fixed-base-size."></a>

#### Formal order and fixed-base size.

The theorem identifies the first formal term. Formal order alone would not control a fixed-$`q`$ residual: multiplying by $`(1-q)^{N^3}`$ preserves that first term and changes the logarithm by a cubic quantity at fixed $`0<q<1`$. The separate positive-measure argument for these same moments proves $`V_N^*(q)>0`$ and $`\log(V_N^*(q)/(C_Nq^{B_N}))=O_q(N)`$, where $`B_N=N(N-1)(2N-1)/6`$ and $`C_N=(N!)^2(N+1)!/2^N`$. Its complete ordinary proof is in `ZudilinHankelPositiveMeasure.md` and the long record. Neither fact supplies a denominator factor for the 2004 polynomial forms.

<a id="sec:open"></a>

# Local cancellation and the remaining real estimate

<div id="res:nocorridor" class="theorem">

**Theorem 7** (no corridor at base $`3/2`$). *For all $`N\ge1`$ and $`K\ge1`$ and all natural $`Q,D`$, the tuple $`(3,2,N,K,Q,D)`$ is not a [coordinatewise corridor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L155).*

</div>

<div id="res:tailrec" class="theorem">

**Theorem 8** (cleared-tail recurrence). *Let $`r,s,B,F\in\mathbb{Q}`$ with $`r\ne0`$, let $`c:\mathbb{N}\to\mathbb{Q}`$, and let $`P_N`$ and $`U_N`$ be the cleared tail state. Then for every $`N`$ the [cleared-tail recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L187) is
``` math
U_{N+1}=r\,U_N-B\,c(N+1)\,s^{\,N+1}.
```*

</div>

<div id="res:forcing" class="theorem">

**Theorem 9** (the forcing term). *Let $`s,B`$ be natural numbers and $`c:\mathbb{N}\to\mathbb{N}`$, and put $`G_N=B\,c(N+1)\,s^{\,N+1}`$.*

1.  *If $`s\ge2`$, $`B\ge1`$ and $`c(N+1)\ge1`$, then $`2^{\,N+1}\le G_N`$.*

2.  *If $`s=1`$, then $`G_N=B\,c(N+1)`$.*

</div>

Fix a common width $`W`$. For $`P\in\mathbb{Z}[X]`$ of degree at most $`W`$, write
``` math
H_W(P)=2^WP(3/2)=\sum_{i=0}^W[P]_i3^i2^{W-i}.
```
A specialised row is primitive when its two integer coordinates have gcd one. This normalisation is different from removing the common polynomial coefficient content, and must precede the local count. For depths $`R,S\ge0`$, define
``` math
J_{3,R}(P)=H_W(P)\pmod{3^R},\qquad
 J_{2,S}(P)=H_W(P)\pmod{2^S}.
```

<div id="res:bottomjet" class="lemma">

**Lemma 10** (bottom-jet divisibility). *Vanishing of the [bottom jet](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L191) is exactly divisibility by the corresponding power of three: $`J_{3,R}(P)=0`$ if and only if $`3^R\mid H_W(P)`$.*

</div>

All four jets of $`(U,V)`$ vanish precisely when $`D=3^R2^S`$ divides both specialised coordinates. The dependence on the declared width remains fixed when rows are added.

<div id="res:jetkernel" class="theorem">

**Theorem 11** (binary four-jet collision). *Fix a width $`W`$ and depths $`R,S`$, and let $`(U_j,V_j)_{j<M}`$ be any $`M`$ pairs of integral polynomials. Call a subset of $`\{0,\dots,M-1\}`$, equivalently a vector of $`\{0,1\}^M`$, a *binary selector*. If the $`2^M`$ binary selectors outnumber the finite four-jet target
``` math
(\mathbb{Z}/3^R\mathbb{Z})^2\times(\mathbb{Z}/2^S\mathbb{Z})^2,
```
then two distinct subsets have the same four-jet sum. Subtracting their indicator vectors gives a nonzero coefficient vector in $`\{-1,0,1\}^M`$ cancelling all four jets. The target has exact cardinality
``` math
(3^R)^2(2^S)^2.
```
In particular, if $`R>0`$ and $`4R+2S\le M`$, such a collision exists.*

</div>

<div class="proof">

*Proof.* Send each binary selector to the sum of the four-jet signatures it selects. The claimed cardinal inequality and the pigeonhole principle give two distinct selectors in the same fibre. The cardinality formula is the product of the four cyclic-modulus cardinalities. For $`R>0`$,
``` math
(3^R)^2(2^S)^2<(4^R)^2(2^S)^2=2^{4R+2S}\le2^M,
```
which proves the stated sufficient threshold. The cardinality formula, the collision, the signed $`\{-1,0,1\}`$ vector and the sufficient width are together [four jet paper statement](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperFiniteAssembliesR7.lean#L248). ◻

</div>

The ambient count does not use relations between the two residue coordinates. Vanishing minors can reduce that cost to one coordinate.

<div id="res:plucker-collapse" class="theorem">

**Theorem 12** (Bézout–Plücker tail collapse). *Let $`R_0`$ be a commutative ring and let $`w_n=(A_n,B_n)\in R_0^2`$. Suppose that every row is unimodular ($`u_n A_n+v_n B_n=1`$ for some $`u_n,v_n`$) and every adjacent minor vanishes:
``` math
A_nB_{n+1}-B_nA_{n+1}=0\qquad(n\ge0).
```
Then every pairwise minor $`A_iB_j-B_iA_j`$ vanishes. In particular, take $`R_0=\mathbb{Z}/(2^S3^R)\mathbb{Z}`$ with $`R>0`$. If $`S+2R\le k`$, there are two distinct binary selectors $`s,t\in\{0,1\}^{k}`$ such that
``` math
\sum_{i<k}s_iw_i=\sum_{i<k}t_iw_i.
```
Thus the sufficient width is $`S+2R`$, rather than the ambient two-coordinate width $`2S+4R`$.*

</div>

<div class="proof">

*Proof.* A Bézout identity makes each row a unimodular anchor; a unit coordinate is the special case already recorded. Vanishing of the next minor therefore writes the next row as a scalar multiple of the current one; induction places the entire tail on the line through $`w_0`$ and proves the pairwise-minor assertion. A determinant-one Bézout shear sends $`w_0`$ to $`(1,0)`$, so all selector sums have only one free residue coordinate and occupy at most $`2^S3^R`$ values. Finally
``` math
2^S3^R<2^S4^R=2^{S+2R}\le2^k,
```
and pigeonhole gives the two selectors. The ring-generic minor collapse and the modular selector collision are together [plucker paper statement](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperFiniteAssembliesR7.lean#L269). ◻

</div>

Primitive integer rows are unimodular modulo every modulus. A particular coordinate need not be a unit: $`(2,3)`$ modulo $`6`$ is an example. The minor-vanishing hypothesis remains a separate condition on the source rows.

<a id="one-minor-gcd-controls-two-different-costs"></a>

## One minor gcd controls two different costs

<div id="res:pade" class="proposition">

**Proposition 13** (Padé summand bound and exact gap). *Let $`\widetilde{E}_n=3n^{2}-n`$ and put
``` math
\widetilde{P}(n,k)=2\bigl(k(n-k)+nk\bigr)+k(k-1),
```
``` math
\widetilde{Q}(n,m)=2(n^{2}-n)+j^{2}+2jm+j-m^{2}+3m,
 \qquad j=n-m-1 .
```
Then, for integers $`n,k,m`$:*

1.  *if $`0\le k\le n`$, the [summand exponent bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L30) is $`\widetilde{P}(n,k)\le\widetilde{E}_n`$, and the gap factors as $`\widetilde{E}_n-\widetilde{P}(n,k)=(n-k)(3n-k-1)`$;*

2.  *the [exact gap identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L52) is $`\widetilde{E}_n-\widetilde{Q}(n,m)=2\bigl(n+m(m-1)\bigr)`$.*

</div>

<div id="res:content" class="proposition">

**Proposition 14** (row-content determinant scaling). *Rowwise integer contents scale the [exterior determinant](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L124) by the same factors: the [content factorisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L94) and the [absolute determinant scaling](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L104) identify the local divisor with the Archimedean height cost.*

</div>

Let a rank-two lattice $`\Lambda\subset\mathbb{Z}^2`$ be generated by primitive rows, and let $`g>0`$ be the gcd of their $`2\times2`$ minors. Its Smith invariants are $`1,g`$. Therefore
``` math
\bigl|\operatorname{im}(\Lambda\bmod D)\bigr|
       =\frac{D^2}{\gcd(g,D)},\qquad
 \left[\mathbb{Z}^2:\frac{\Lambda\cap D\mathbb{Z}^2}{D}\right]
       =\frac{g}{\gcd(g,D)}.
```
To verify the formulas, make a unimodular change of coordinates sending $`\Lambda`$ to $`\mathbb{Z}\oplus g\mathbb{Z}`$; that change preserves $`D\mathbb{Z}^2`$. The first quotient counts the modular signatures. The second is the index remaining after dividing a successful collision by $`D`$. Once $`D\mid g`$, the modular count is $`D`$, while the remaining index is $`g/D`$.

If two independent divided rows $`(A_i,B_i)`$ have $`|A_i|\le H`$ and $`|A_i\xi-B_i|\le\varepsilon`$, their determinant gives
``` math
2H\varepsilon\ge \frac{g}{\gcd(g,D)}.
```
This is a restriction on two independent forms in the divided lattice. For one nonzero integral form tending to zero, no additional product $`H\varepsilon\to0`$ is required.

<a id="a-collision-must-have-a-small-nonzero-real-remainder"></a>

## A collision must have a small nonzero real remainder

A real bin records the analytic requirement alongside the modular signature. The multiplicity to control is the number of equal real values within one modular fibre.

<div id="res:boundedfibre" class="theorem">

**Theorem 15** (quantitative bounded-fibre escape). *Let $`A,B,J`$ be finite sets and let $`f:A\to B`$, $`g:A\to\mathbb R`$ and $`\iota:A\to J`$. Suppose that each simultaneous fibre of $`(f,g)`$ has at most $`k`$ elements and that, for some $`\delta>0`$,
``` math
\iota(x)=\iota(y)\quad\Longrightarrow\quad |g(x)-g(y)|<\delta.
```
If $`|B||J|k<|A|`$, then some distinct $`x,y\in A`$ satisfy
``` math
f(x)=f(y),\qquad 0<|g(x)-g(y)|<\delta.
```*

</div>

<div class="proof">

*Proof.* Partition $`A`$ by $`(f,\iota)`$. Some cell has more than $`k`$ elements, so its $`g`$-values cannot all agree. Two unequal values in that cell have the same modular signature and differ by less than $`\delta`$. ◻

</div>

For primitive integer rows $`(A_j,B_j)`$, put $`e_j=A_jF(3/2)-B_j`$ and apply the theorem to binary selectors, with
``` math
f(\varepsilon)=\sum_j\varepsilon_j(A_j,B_j)\pmod D,
 \qquad g(\varepsilon)=\sum_j\varepsilon_j e_j.
```
Let $`Q`$ be the number of attained modular signatures and let $`k`$ bound the simultaneous $`(f,g)`$ fibres. All selector remainders lie in an interval of length $`T=\sum_j|e_j|`$. Dividing that interval into half-open bins of width $`D/n`$ gives the sufficient inequality
``` math
\begin{equation}
\label{eq:quantitative-selector-budget}
 2^M>Qk\left(\left\lfloor\frac{nT}{D}\right\rfloor+1\right).
\end{equation}
```
Its conclusion is a signed row sum divisible coordinatewise by $`D`$, with a nonzero divided real remainder of absolute value less than $`1/n`$. More precisely, if modular fibre $`b`$ has its own real span $`T_b`$ and exact value multiplicity $`k_b`$, it suffices that
``` math
2^M>\sum_b k_b\left(\left\lfloor\frac{nT_b}{D}\right\rfloor+1\right).
```
These are estimates for the primitive real remainders of the declared source family. Bounded unnormalised hypergeometric remainders cannot replace them. A nonzero function need not be nonzero at $`3/2`$, as the factor $`2X-3`$ shows; positive individual remainders need not remain positive after subtraction.

<a id="the-source-specific-endpoint-question"></a>

## The source-specific endpoint question

The following sufficient construction keeps source membership, primitive scaling, local cancellation and the real estimate together. Without source and height restrictions, arbitrary polynomial lifts of small rational approximations would simply restate irrationality.

<div id="prob:kernel" class="problem">

**Problem 16** (common-width simultaneous endpoint-jet construction). Exhibit an integer constant $`C\ge1`$ and, for every sufficiently large positive integer $`n`$, positive integers $`W_n,R_n,S_n,M_n`$ such that
``` math
n^2\le W_n,R_n,S_n\le Cn^2,
 \qquad 4R_n+2S_n\le M_n\le Cn^2,
```
together with polynomial pairs coming from a named source family with an explicit coefficient-height bound after primitive normalisation, $`(U_{n,j},V_{n,j})\in\mathbb{Z}[X]^2`$ for $`0\le j<M_n`$, each of degree at most the common declared width $`W_n`$, whose specialised integer rows are primitive:
``` math
\gcd\!\bigl(H_{W_n}(U_{n,j}),H_{W_n}(V_{n,j})\bigr)=1.
```
Find a nonzero vector $`\lambda^{(n)}\in\{-1,0,1\}^{M_n}`$ for which, on putting
``` math
U_n=\sum_{j<M_n}\lambda^{(n)}_jU_{n,j},
 \qquad V_n=\sum_{j<M_n}\lambda^{(n)}_jV_{n,j},
```
the pair $`(U_n,V_n)`$ is not $`(0,0)`$, all four common-width jets vanish,
``` math
J_{3,R_n}(U_n)=J_{3,R_n}(V_n)=0,
 \qquad J_{2,S_n}(U_n)=J_{2,S_n}(V_n)=0,
```
where every jet in this display is formed using the declared width $`W_n`$, and the resulting divided integer linear form
``` math
A_n=\frac{H_{W_n}(U_n)}{3^{R_n}2^{S_n}},
 \qquad
 B_n=\frac{H_{W_n}(V_n)}{3^{R_n}2^{S_n}},
 \qquad
 \rho_n=A_nF(3/2)-B_n
```
satisfies the explicit analytic condition
``` math
0<|\rho_n|<\frac1n.
```

</div>

The jet equations make $`A_n,B_n`$ integers. If $`F(3/2)=a/b`$ were rational, a nonzero $`\rho_n`$ would have absolute value at least $`1/|b|`$, contradicting $`|\rho_n|<1/n`$ for large $`n`$. The required analytic inequality is exactly the displayed scalar condition. For irrationality it suffices to obtain such forms along any unbounded sequence of $`n`$; the all-sufficiently-large-$`n`$ formulation is a stronger construction requirement. Height estimates become relevant when a specific construction uses them to obtain this scalar inequality, or when an independent-row determinant is invoked.

For the literal two-parameter source deformations, the long record keeps the rowwise primitive normalisation, the two local minor valuations and the remaining real-error minimum together. The narrow regular-scale family has an ordinary determinant obstruction to bounded divided errors; that obstruction does not exclude sparse scales or the wider deformation. Thus the next estimate must concern the real remainders of the chosen family. Increasing the number of modular collisions alone does not establish it.

<a id="functional-equations."></a>

#### Functional equations.

The classification of Bell and Smertnig implies that $`L(z)=\sum_{n\ge1}\tau(n)z^n`$ is not $`k`$-Mahler for any $`k\ge2`$ \[bellsmertnig2026, Introduction\]. The earlier simultaneous-$`2`$/$`3`$ obstruction is consequently subsumed by this known single-base result. A construction using additional functions or functional relations must specify those functions and its closure conditions; the single-base statement is not an obstruction to every approximation method.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The [pinned formal-source revision](https://github.com/wcook04/plectis-lean-erdos249-257/tree/99f4bf47422abbd8757cbb22b50ba079d764d3a7) contains the Lean sources, the fixed toolchain, and the library manifest used in the verification. The ordinary proofs used here are printed with their hypotheses.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

The problem numbering and status follow the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\].

<a id="app:index"></a>

# Guide to the formal sources

The seven modules named below are linked at the pinned source revision 99f4bf47422a. Additional declarations in the body of the note are linked at a second immutable revision, `f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a`. These are separate snapshots, not one checked revision of the whole library. Each hyperlink opens the named declaration at the commit recorded in its URL.

The declarations linked at 99f4bf47422a live in seven modules: `RationalBaseLambert`, `QAperyDiagonalNonEquivalence`, `RationalPadeArithmetic`, `ZudilinConeArithmetic`, `ZudilinHeightRegion`, `HermitePadeNoGo`, and `BezoutPluckerJets`. The first contains the corridor, cleared-tail recurrence, and elementary $`7/2`$ certificate; the second checks the finite $`n=0`$ diagonal residual; the remaining four separate the Padé exponent arithmetic, endpoint arithmetic, logarithmic comparisons, rectangular exponent model, and Bézout–Plücker tail collapse. The link coordinates for those seven modules are validated against that pinned revision, so they remain correct as later work moves lines in the working tree.

<div class="thebibliography">

99

P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). P. Bundschuh and K. Väänänen, [*Arithmetical investigations of a certain infinite product*](https://numdam.org/item/CM_1994__91_2_175_0.pdf), Compositio Math. **91** (1994), no. 2, 175–199. W. Zudilin, [*Heine’s basic transform and a permutation group for $`q`$-harmonic series*](https://geodesic.mathdoc.fr/articles/10.4064/aa111-2-4/), Acta Arith. **111** (2004), no. 2, 153–164, doi:10.4064/aa111-2-4. W. Zudilin, [*On the irrationality of generalized $`q`$-logarithm*](https://arxiv.org/abs/1601.02688), arXiv:1601.02688; Res. Number Theory **2** (2016), doi:[10.1007/s40993-016-0042-x](https://doi.org/10.1007/s40993-016-0042-x). The remark that the results extend to non-integer $`p=r/s`$, $`|p|>1`$, under an assumption $`\log|r|>c\log|s|`$ for a computable $`c>0`$, is at the end of Section 2; no value of $`c`$ is computed there, and the remark is made for the generalized $`q`$-logarithm of that paper. T. F. Bloom, [*Erdős Problem \#1049*](https://www.erdosproblems.com/1049), `erdosproblems.com/1049`, accessed 28 July 2026 (page displays “last edited 28 September 2025”). The current record labels the problem open, cites <span class="upright">\[Er88c, p. 102\]</span> and <span class="upright">\[Er48\]</span>, and explicitly describes its status as the website owner’s present assessment rather than a literature-completeness guarantee. J. Bell and D. Smertnig, [*Mahler series with multiplicative coefficient sequences*](https://arxiv.org/abs/2603.23456), arXiv:2603.23456v1, 24 March 2026. The introduction explicitly includes the divisor and totient functions among the examples which are not $`k`$-Mahler for any $`k\ge2`$.

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
