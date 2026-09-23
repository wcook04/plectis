<a id="erdos-1049-rational-base-lambert"></a>

# Zudilin’s Forms at Rational Bases and the Exact Normalised Hankel Order

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

For coprime integers $`a>b\ge1`$, we prove that $`F(a/b)=\sum_{n\ge1}((a/b)^n-1)^{-1}`$ is irrational when $`\log b/\log a<0.4056830213840605\ldots`$, with the cutoff defined exactly below. This includes every positive integral power of $`31/4`$, with irrationality exponent less than $`301`$. We use Zudilin’s 2004 forms and constants, cancel common cyclotomic factors before rational evaluation, and compute the remaining denominator cost.

For the distinct normalised Hankel determinants $`V_N^*`$ in his 2016 construction, with auxiliary parameters $`x=z=1`$, we prove
``` math
\operatorname{ord}_q V_N^*=\frac{N(N-1)(2N-1)}6,
 \qquad [q^{\operatorname{ord}_q V_N^*}]V_N^*
       =\frac{(N!)^2(N+1)!}{2^N}.
```
The order is the least exponent with nonzero coefficient; a unique least-order term in the moment expansion gives both formulas. For fixed $`0<q<1`$ we prove that, as $`N\to\infty`$, $`V_N^*(q)\sim K(q)C_Nq^{B_N}(q;q)_\infty^{2N}N^{-8F(1/q)}`$, where $`B_N`$ and $`C_N`$ are the order and coefficient above and $`K(q)>0`$ is given by a convergent product. We also factor the moment weights into two finite $`q`$-multinomial sums. The rational-base criterion does not include $`3/2`$; neither the order, the asymptotic nor the factorisation settles irrationality at that base.

<a id="sec:problem"></a>

# Introduction

For $`t>1`$, expansion of each geometric series gives
``` math
F(t)=\sum_{n\ge1}\frac1{t^n-1}
     =\sum_{n\ge1}\frac{\tau(n)}{t^n},
```
where $`\tau(n)`$ is the number of positive divisors of $`n`$. With $`q=1/t`$, this is the $`q`$-harmonic series $`\sum_{n\ge1}q^n/(1-q^n)`$. The rearrangement is justified by nonnegativity, and the resulting series converges since $`\tau(n)\le n`$ and $`\sum_{n\ge1}nt^{-n}<\infty`$.

Chowla conjectured that $`F(t)`$ is irrational for every rational $`t>1`$, as Erdős records \[erdos1988, p. 102\]; this is Erdős Problem #1049. The conjecture remains open. We prove a sufficient condition on the numerator and denominator of $`t`$, using Zudilin’s 2004 construction \[zudilin2004\]. The condition includes $`31/4`$ and every positive integral power of $`31/4`$, but not $`3/2`$.

The extra difficulty at a rational base is the denominator. If $`U,V\in\mathbb{Z}[X]`$ have degree at most $`W`$, then $`b^WU(a/b)`$ and $`b^WV(a/b)`$ are integers. To prove irrationality by these forms, their positive remainders $`U(a/b)F(a/b)-V(a/b)`$ must remain small after multiplication by $`b^W`$.

A small example shows why cancellation should come first. At $`3/2`$, the pair $`(X+1)(X+2),(X+1)(X+3)`$, cleared with degree bound $`2`$, gives $`(35,45)`$. Cancelling $`X+1`$ in the polynomial ring and then using degree bound $`1`$ gives $`(7,9)`$. The example is not an approximation to $`F`$; it illustrates how a common polynomial factor changes the required power of the denominator. For Zudilin’s polynomials the corresponding factors are cyclotomic, and their degrees determine the cutoff below.

For the cancelled polynomials $`U_n,V_n`$ used here, put $`\Lambda_n=U_nF-V_n`$ and $`W_n=\deg U_n`$. We prove $`\deg V_n=W_n-1`$ and
``` math
\log\!\bigl(b^{W_n}\Lambda_n(a/b)\bigr)
 =\bigl(C_1\log b-C_0\log a\bigr)n^2+o(n^2),
```
where $`C_0,C_1`$ are defined below. If the coefficient of $`n^2`$ is negative, the forms have integer coefficients and positive values tending to zero. If $`F(a/b)`$ were rational, multiplying by its fixed denominator would give positive integers tending to zero, a contradiction.

The proof of the rational-base result occupies Section <a href="#sec:rational-base-irrationality" data-reference-type="ref" data-reference="sec:rational-base-irrationality">2</a>. The independent argument in Section <a href="#sec:hankel-order" data-reference-type="ref" data-reference="sec:hankel-order">3</a> computes the first nonzero term of a Hankel determinant from the 2016 construction. Neither proof uses Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">4</a>, which records supplementary tests for congruence-based arguments at $`3/2`$. The companion *Zudilin’s Forms at Rational Bases: Proofs and Research Record*, called the long record below, gives the additional moment calculations, source comparisons and computational certificates.

Throughout, logarithms are natural. Empty products and determinants have value $`1`$, and a subscripted constant in $`O_x(\cdot)`$ may depend on the fixed base $`x`$. Other notation is introduced where it is used.

<a id="sec:rational-base-irrationality"></a>

# A region of rational bases at which $`F`$ is irrational

The parameter choice, thirteen intervals and constants $`C_1,C_0`$ below come from Zudilin’s construction \[zudilin2004, §5, pp. 161–162\]; there $`C_1/C_0=2.46497868\ldots`$ is his bound for the irrationality exponent at integer bases \[zudilin2004, Thm. 1, p. 154\]. Write $`\psi_1(u)=\sum_{k\ge0}(k+u)^{-2}`$ for the trigamma function on $`u>0`$. Let $`\mathcal I`$ be the thirteen intervals listed in the proof and put
``` math
C_1=\frac{1091}{2},\qquad
 J=\sum_{[u,v)\in\mathcal I}\bigl(\psi_1(u)-\psi_1(v)\bigr),\qquad
 C_0=266-\frac3{\pi^2}(225-J).
```
The intervals are disjoint and lie in $`[1/14,1)`$, so $`0\le J\le\psi_1(1/14)-\psi_1(1)<196`$. Together with $`\pi>3`$, these bounds give $`0<C_0<266<C_1/2`$. Thus $`\theta^*=C_0/C_1`$ and $`\mu=C_1/C_0`$ are positive reciprocal constants. The notation $`\mu_{\rm irr}(\xi)`$ instead denotes the irrationality exponent of a value. The cutoff is sufficient, not asserted optimal.

<div id="res:rational-base-threshold" class="theorem">

**Theorem 1** (rational-base region for Zudilin’s forms). *Let $`a>b\ge1`$ be coprime integers with
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

Lean: [printed contour short](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperCompleteR21/PrintedContourConstants.lean#L440), [printed mu](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperCompleteR21/PrintedContourConstants.lean#L461), [zudilin j enclosure](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperCompleteR21/PrintedContourConstants.lean#L334), [zudilin c0 enclosure](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperCompleteR21/PrintedContourConstants.lean#L383), and 7 further declarations in the [coverage section of the companion record](../mirror/erdos1049-rational-base-lambert-reasoning-surface.pdf#nameddest=coverage).

The condition holds for every integer base, since $`b=1`$ gives $`\log b/\log a=0`$. For a fixed denominator $`b>1`$, it requires $`a>b^{2.46497868\ldots}`$, much more than $`a>b`$; nevertheless it gives infinitely many reduced noninteger rational bases for each such $`b`$. The base $`31/4`$ satisfies the condition, and taking a common positive integer power of the numerator and denominator leaves their logarithmic ratio unchanged. The base $`3/2`$ is excluded since $`\theta^*<1/2<\log2/\log3`$. At equality $`\log b/\log a=\theta^*`$ the quadratic exponent vanishes, so the estimates below give no conclusion.

<div class="proof">

*Proof of Theorem <a href="#res:rational-base-threshold" data-reference-type="ref" data-reference="res:rational-base-threshold">1</a>.* We construct positive forms, cancel their common factors, and compare the remaining degree with their decay. Fix $`n\ge1`$ and set
``` math
a_0=14n+1,\quad a_1=12n+1,\quad a_2=14n+1,\quad\beta=27n+2,
 \qquad N=15n.
```
In this proof $`N`$ is a cyclotomic cutoff, not a Hankel rank. Use the coefficient pair $`A_n,B_n`$ of the source identities \[zudilin2004, (8)–(11), pp. 156–157\], with $`H_n=A_nF-B_n`$. Let $`\Phi_\ell`$ be the cyclotomic polynomial whose roots are the primitive $`\ell`$th roots of unity. Put $`D_N(X)=\prod_{\ell=1}^{N}\Phi_\ell(X)`$, $`M_n=266n^2+34n+1`$, and
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
has period $`1`$: the coefficients of the floor arguments in each difference have equal sums, $`14+13=12+15`$ and $`2\cdot14=13+15`$. On $`[0,1)`$ it is zero or one, with support
``` math
\begin{gathered}
\,[1/14,1/12),\ [1/7,1/6),\ [3/14,1/4),\ [2/7,1/3),\\
[5/14,2/5),\ [3/7,7/15),\ [1/2,8/15),\ [4/7,3/5),\\
[9/14,2/3),\ [5/7,11/15),\ [11/14,4/5),\\
[6/7,13/15),\ [13/14,14/15).
\end{gathered}
```
These are the intervals $`\mathcal I`$ used to define $`J`$. The function $`\omega`$, these thirteen intervals and the exponents $`\nu_\ell=\omega(n/\ell)`$ of the source’s (22) are printed at \[zudilin2004, pp. 161–162\]. The zero-one values and the interval decomposition are checked in [interval formula for $`\omega`$](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperOmegaIndicatorR7.lean#L1297).

#### The positive source expression.

For $`x>1`$, put $`q=1/x`$. The $`q`$-Pochhammer symbol, also called the shifted $`q`$-factorial, is $`(z;q)_m=\prod_{j=0}^{m-1}(1-zq^j)`$. The source identity (9) on p. 156 gives the positive representation
``` math
H_n(x)=\sum_{t\ge0}q^{a_0t}
 \frac{(q^{t+1};q)_{a_1-1}}{(q;q)_{a_1-1}}
 \frac{(q;q)_{\beta-a_2-1}}{(q^{a_2+t};q)_{\beta-a_2}}.
```
The denominator length is $`\beta-a_2`$, as in the gamma expression (7) and residues (8) of \[zudilin2004, p. 156\]; the unnumbered display of $`R(T)`$ on that page has length $`\beta-a_2-1`$ instead. Each of the four finite products displayed above lies between $`P=(q;q)_\infty>0`$ and $`1`$, so
``` math
P^2\le H_n(x)\le\frac{P^{-2}}{1-q^{a_0}}.
```
In particular $`H_n(x)>0`$ and $`\log H_n(x)=O_x(1)`$.

#### Integral polynomials and their degrees.

The source’s polynomial inclusion is Lemma 7, display (23) \[zudilin2004, p. 161\]. Its parameter vector is $`n(13,14,12,14,15,13)`$, its maximum is $`15n`$, and $`\beta-a_1-a_2=n>0`$, which is the positivity condition $`s>0`$ of the lemma. The conditions (14) of \[zudilin2004, p. 157\], $`a_1\le a_2`$ and $`a_1+a_2\le\beta\le a_0+a_2`$, hold as well, so the exponent in (23) is the integer (16), which equals $`M_n`$. Lemma 7 therefore gives, for every $`n\ge1`$,
``` math
\Lambda_n(X)=X^{-M_n}\frac{D_N(X)}{\Omega_n(X)}H_n(X)
            =U_n(X)F(X)-V_n(X),\qquad U_n,V_n\in\mathbb Z[X].
```
This is the polynomial conclusion before integer specialisation in the source’s (24), p. 162. The coefficients are the cancelled source coefficients:
``` math
U_n=X^{-M_n}(D_N/\Omega_n)A_n,\qquad
 V_n=X^{-M_n}(D_N/\Omega_n)B_n.
```
Indeed, coefficients of $`F`$ and $`1`$ over $`\mathbb{Q}(X)`$ are unique because $`F`$ is not a rational function. For completeness, as $`h\downarrow0`$, split $`F(e^h)`$ into $`m\le1/h`$ and $`m>1/h`$. The first part is $`h^{-1}\sum_{m\le1/h}m^{-1}+O(h^{-1})`$, using $`y^{-1}-1\le(e^y-1)^{-1}\le y^{-1}`$ for $`0<y\le1`$; the geometric tail is $`O(h^{-1})`$. Thus $`F(e^h)=h^{-1}\log(1/h)+O(h^{-1})`$, which has no rational-function pole order at $`X=1`$. The cancelled remainder is positive for $`x>1`$, since $`D_N/\Omega_n`$ is a product of cyclotomic polynomials positive there.

The Gaussian binomial polynomial $`\genfrac{[}{]}{0pt}{}{m}{k}_X=\prod_{j=1}^k(1-X^{m-k+j})/(1-X^j)`$ is monic of degree $`k(m-k)`$ for integers $`0\le k\le m`$. The source’s (8) and (10) on p. 156 give the coefficient whose degree we need:
``` math
A_n(X)=\sum_{k=a_2}^{\beta-1}(-1)^{a_1+a_2+k+1}
 X^{a_0k+\binom{a_1}{2}-\binom{\beta-a_2}{2}+\binom{\beta-k}{2}}
 \genfrac{[}{]}{0pt}{}{k-1}{a_1-1}_X
 \genfrac{[}{]}{0pt}{}{\beta-a_2-1}{\beta-k-1}_X.
```
The degree increases by $`40n+1-k>0`$ from summand $`k`$ to summand $`k+1`$ for $`a_2\le k\le\beta-2`$. Thus the last summand alone determines the leading term, and
``` math
K_n:=\deg A_n=\frac{1091n^2+81n+2}{2},\qquad
 W_n:=\deg U_n=K_n-M_n+\sum_{\ell\le15n}(1-\nu_\ell)\varphi(\ell).
```
Here $`\varphi(\ell)=\deg\Phi_\ell`$ is Euler’s totient function, and $`\nu_1=\omega(n)=0`$. The bounds for $`H_n`$ are uniform for $`x\ge2`$: then $`P\ge\prod_{j\ge1}(1-2^{-j})>0`$ and $`(1-x^{-a_0})^{-1}\le2`$. For fixed $`n`$, therefore, $`H_n(x)=O(1)`$ and $`\Lambda_n(x)=O(x^{W_n-K_n})`$ as $`x\to\infty`$. The unique top summand of $`A_n`$ has leading coefficient $`(-1)^{a_1+a_2+\beta}=(-1)^n`$. Since the Gaussian factors and $`D_N/\Omega_n`$ are monic, $`U_n`$ has that leading coefficient too. Moreover $`F(x)=x^{-1}+O(x^{-2})`$ and $`K_n\ge2`$, so
``` math
V_n(x)=U_n(x)F(x)-\Lambda_n(x)
       =(-1)^n x^{W_n-1}+O(x^{W_n-2}).
```
Here $`W_n\ge K_n-M_n=(559n^2+13n)/2>0`$. Thus $`\deg V_n=W_n-1`$, with the same unit leading coefficient as $`U_n`$. For every prime $`p\mid b`$, reduction of the cleared first coordinate gives
``` math
b^{W_n}U_n(a/b)\equiv(-1)^n a^{W_n}\not\equiv0\pmod p.
```
Thus $`U_n(a/b)`$ has reduced denominator exactly $`b^{W_n}`$, the least common clearing denominator for this pair. Any common integer divisor of the cleared row is coprime to $`b`$; other common factors, or savings from different rows, require separate analysis.

This degree calculation fixes $`n`$ and lets $`x\to\infty`$; the decay calculation below fixes $`x`$ and lets $`n\to\infty`$.

#### The limiting degree cost.

The limits below are the cyclotomic limits of \[zudilin2004, Lemmas 1–2, p. 155\]. The proof uses the argument through reciprocal intervals, the summatory totient estimate and the trigamma function from the proof of \[zudilin2002, Lemma 1, p. 466\], with an explicit truncation of the block sum. The elementary summatory estimate $`\sum_{\ell\le y}\varphi(\ell)=3y^2/\pi^2+O(y\log y)`$ gives
``` math
\frac1{n^2}\sum_{\ell\le15n}\varphi(\ell)\longrightarrow\frac{675}{\pi^2}.
```
For $`[u,v)\in\mathcal I`$, the condition $`\{n/\ell\}\in[u,v)`$ is the disjoint union of intervals $`n/(k+v)<\ell\le n/(k+u)`$ for $`k\ge0`$. For finitely many $`k`$ the same summatory estimate applies term by term. For $`K\ge1`$, the omitted blocks have $`\ell\le n/(K+u)`$. The elementary bound $`\sum_{\ell\le y}\varphi(\ell)\le y^2`$ for $`y\ge0`$ bounds their total normalised contribution by
``` math
\frac1{n^2}\sum_{\ell\le n/(K+u)}\varphi(\ell)
 \le\frac1{(K+u)^2}.
```
Indeed, for $`y\ge1`$ one can bound $`\varphi(\ell)`$ by $`\ell`$ and sum; for $`0\le y<1`$ the sum is empty. This bound is uniform in $`n`$. Letting first $`n`$ and then $`K`$ tend to infinity proves
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

#### The size after cancellation.

Let $`\mu_{\rm Mob}`$ denote the Möbius function. For fixed $`x>1`$, the cyclotomic identity
``` math
\log\Phi_\ell(x)-\varphi(\ell)\log x
 =\sum_{d\mid\ell}\mu_{\rm Mob}(d)\log(1-x^{-\ell/d})
```
has total absolute error $`O_x(n)`$ over $`\ell\le15n`$. Indeed, it is at most
``` math
15n\sum_{d\ge1}\frac{-\log(1-x^{-d})}{d},
```
The series converges because $`-\log(1-x^{-d})\le x^{-d}/(1-x^{-1})`$. Since $`0\le1-\nu_\ell\le1`$, it follows that
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
The coefficient is negative under the theorem’s hypothesis. The positive values of these integer-coefficient forms therefore tend to zero. If $`F(a/b)=r/s`$ with integers $`r,s`$ and $`s\ne0`$, every nonzero value would have absolute value at least $`1/|s|`$, a contradiction. The separation bound for a nonzero integral form at a rational target is [rational integer linear form gap](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/TwoSelectorRemainderEscape.lean#L128). ◻

</div>

<div id="res:thirtyone-four" class="corollary">

**Corollary 2**. *$`F\bigl((31/4)^r\bigr)`$ is irrational for every integer $`r\ge1`$.*

</div>

Lean: [thirtyone four powers](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperR17/SourceConsumers.lean#L117).

<div class="proof">

*Proof.* The exact inequalities $`31^2<4^5`$ and $`4^{200}<31^{81}`$ give $`2/5<\log4/\log31<81/200`$. The first term of each trigamma difference yields
``` math
J\ge\sum_{[u,v)\in\mathcal I}(u^{-2}-v^{-2})
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

Lean: [rational base measure uniform](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperCompleteR21/RationalBaseThreshold.lean#L194), [thirtyone four power measure lt 301](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperCompleteR21/RationalBaseThreshold.lean#L205), [rational base power measure](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperR17/SourceConsumers.lean#L167), [thirtyone four power measure lt 301](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperR17/SourceConsumers.lean#L176).

<div class="proof">

*Proof.* The passage from the forms to an exponent bound is the standard one that Zudilin uses at integer bases \[zudilin2004, p. 162\]; the estimates below give an exponent bound independent of $`r`$, although the estimates are applied separately at each fixed base $`(a/b)^r`$. Use the polynomials $`U_n,V_n`$ constructed in the proof of Theorem <a href="#res:rational-base-threshold" data-reference-type="ref" data-reference="res:rational-base-threshold">1</a>, with $`W_n=\deg U_n`$. In that construction the coefficient of $`F`$ before cancellation is a sum of $`O(n)`$ Laurent monomials times two Gaussian binomial polynomials. Each Gaussian polynomial has nonnegative coefficients summing to at most $`2^{27n+2}`$. Thus the sum of the absolute coefficients is $`\exp(O(n))`$. Its largest exponent is $`K_n=(1091n^2+81n+2)/2`$, so its absolute value at a fixed $`x>1`$ is at most $`x^{K_n}\exp(O(n))`$. The cyclotomic estimate in the same proof bounds the normalising multiplier by $`x^{W_n-K_n}\exp(O_x(n))`$. Multiplication gives
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
When $`Ap-Bq=0`$ this is equality. Otherwise the nonzero integer $`Ap-Bq`$ gives $`1/q\le |L|+|A|\,|\xi-p/q|`$, which proves the inequality. Fix $`0<\eta<\tau`$. For all sufficiently large $`n`$, the estimates above give
``` math
e^{-(\tau+\eta)n^2}\le Q_n\xi-P_n\le e^{-(\tau-\eta)n^2},
 \qquad |Q_n|\le e^{(\alpha+\eta)n^2}.
```
For every sufficiently large denominator $`q`$, choose $`n=\lceil\sqrt{\log(2q)/(\tau-\eta)}\rceil`$. Then $`2q(Q_n\xi-P_n)\le1`$, so the preceding integer argument applies to $`(A,B)=(Q_n,P_n)`$ for every numerator $`p`$. Also $`Q_n\ne0`$: otherwise $`Q_n\xi-P_n`$ would be an integer strictly between $`0`$ and $`1`$. It follows that
``` math
|\xi-p/q|\ge e^{-(\alpha+\tau+2\eta)n^2}
             =q^{-(\alpha+\tau+2\eta)/(\tau-\eta)-o(1)},
```
since $`n^2=\log(2q)/(\tau-\eta)+O_\eta(\sqrt{\log q}+1)`$.

Let $`\eta\downarrow0`$. The resulting bound is $`1+\alpha/\tau=(1-\theta)/(\theta^*-\theta)`$. Taking a common power multiplies $`\alpha,\tau`$ by $`r`$, leaving this quotient unchanged; the constants in the approximation inequality may depend on $`r`$. For $`31/4`$, the exact interval bounds in the long record, Section 2.5, give $`\theta<0.4036982`$ and $`\theta^*>0.40568`$. The quotient increases with $`\theta`$ and decreases with $`\theta^*`$ in this range, so
``` math
\frac{1-\theta}{\theta^*-\theta}
 <\frac{1-0.4036982}{0.40568-0.4036982}
 =\frac{2981509}{9909}<301.
```
Long Section 2.5 supplies the sharper numerical enclosures, their series and tail bounds, and the cutoff-digit certificate. These are exact computations, not additional Lean declarations. ◻

</div>

<a id="formal-sources."></a>

#### Formal sources.

The linked Lean sources prove Theorem <a href="#res:rational-base-threshold" data-reference-type="ref" data-reference="res:rational-base-threshold">1</a> as [the rational-base region](https://github.com/wcook04/plectis-erdos/blob/f4e61ed8a6941571310049e22dc239baa1b04e12/lean/ErdosProblems/Erdos1049/PaperR17/SourceConsumers.lean#L113), and Corollary <a href="#res:thirtyone-four" data-reference-type="ref" data-reference="res:thirtyone-four">2</a> as [the powers of $`31/4`$](https://github.com/wcook04/plectis-erdos/blob/f4e61ed8a6941571310049e22dc239baa1b04e12/lean/ErdosProblems/Erdos1049/PaperR17/SourceConsumers.lean#L117), with [the base $`31/4`$](https://github.com/wcook04/plectis-erdos/blob/f4e61ed8a6941571310049e22dc239baa1b04e12/lean/ErdosProblems/Erdos1049/PaperR17/SourceConsumers.lean#L121) as the case $`r=1`$. They construct the coefficient polynomials and prove the remainder estimates rather than assuming them. Of Zudilin’s two constructions \[zudilin2004; zudilin2016\], the argument here uses the 2004 forms; Section <a href="#sec:hankel-order" data-reference-type="ref" data-reference="sec:hankel-order">3</a> uses the 2016 sequence.

<a id="comparison-and-scope."></a>

#### Comparison and scope.

Bundschuh and Väänänen’s Theorem 2 at $`\alpha=-1`$ \[bv1994, p. 177\] gives irrationality for $`\log b/\log a<\theta_{\rm BV}:=1/2-1/\pi^2`$. Their $`q`$ is the base $`a/b>1`$, not its reciprocal. Their logarithmic derivative is $`L_q(z)=\sum_{j\ge1}(q^j+z)^{-1}`$, so the value at $`z=\alpha=-1`$ is exactly $`F(a/b)`$. The rational height is $`h(q)=a`$, and their parameter $`\lambda=\log h(q)/\log q`$ is $`1/(1-\log b/\log a)`$, which gives the displayed cutoff. Since $`\pi^2<10`$, one has $`\theta_{\rm BV}<2/5<\log4/\log31`$, so $`31/4`$ lies outside that sufficient region. The two sufficient regions differ on $`[\theta_{\rm BV},\theta^*)`$. Zudilin also notes an extension to noninteger rational bases $`p=r/s`$ for the generalized $`q`$-logarithm when $`\log|r|>c\log|s|`$, with $`c>0`$ computable but unspecified \[zudilin2016, Sec. 2, p. 4\]. For $`F`$, the specialisation above gives $`c=\mu`$, the exponent bound of \[zudilin2004, p. 162\].

<div id="res:sevenhalves" class="theorem">

**Theorem 4** (the $`7/2`$ height condition). *The [integer power certificate](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L32) $`2^{18}<7^7`$ yields the [Archimedean height condition](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L83)
``` math
\frac{\log 7}{\log(7/2)}
 <
 \left(\frac12+\frac1{\pi^2}\right)^{-1}.
```*

</div>

<div class="proof">

*Proof.* The power comparison gives $`\log2/\log7<7/18`$, whereas $`\pi>3`$ gives $`1/2+1/\pi^2<11/18`$. Taking reciprocals of positive quantities,
``` math
\frac{\log7}{\log(7/2)}
 =\frac1{1-\log2/\log7}<\frac{18}{11}
 <\left(\frac12+\frac1{\pi^2}\right)^{-1}.
```
 ◻

</div>

This is the elementary parameter check at $`q=7/2`$ in Bundschuh and Väänänen’s Theorem 2 ($`\alpha=-1`$). Their analytic irrationality theorem is not a Lean result here.

Negative bases are not treated: the positive-remainder estimates used here assume $`x>1`$. The boundary $`x=1`$ is excluded because the Lambert series diverges there.

<a id="why-the-same-estimates-at-every-base-impose-a-restriction"></a>

## Why the same estimates at every base impose a restriction

The next restriction requires one polynomial family and common leading degree, height and decay constants at every fixed real base $`x>1`$. The error terms may depend on $`x`$. Here $`H`$ is the sum of the absolute coefficients, and $`a>b\ge1`$ are integers. Reducing $`a/b`$ avoids an unnecessary clearing factor, but coprimality is not needed for this estimate.

<div id="res:archimedean-cap" class="theorem">

**Theorem 5** (a degree restriction for estimates valid at every base). *Let $`(U_n,V_n)`$ be pairs in $`\mathbb Z[X]^2`$ satisfying $`\Lambda_n(x)=U_n(x)F(x)-V_n(x)\ne0`$, $`\deg U_n,\deg V_n\le\delta n^2(1+o(1))`$, $`\log\max(H(U_n),H(V_n))\le h n^2(1+o(1))`$ with $`H`$ the $`\ell^1`$ coefficient norm, and $`\log|\Lambda_n(x)|=-\sigma n^2\log x\,(1+o(1))`$ for every real $`x>1`$, with $`\sigma,\delta>0`$ and $`h\ge0`$ independent of $`x`$. Then with $`d_n=\max(\deg U_n,\deg V_n)`$, the homogenised forms $`b^{d_n}\Lambda_n(a/b)`$ tend to zero whenever $`\log b/\log a<\sigma/(\sigma+\delta)`$, and $`\sigma/(\sigma+\delta)\le1/2`$.*

</div>

Lean: [short note archimedean cap](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperShortCapR9.lean#L162).

<div class="proof">

*Proof.* For real $`x>1`$, the sum of the absolute values of the coefficients gives $`|U_n(x)|,|V_n(x)|\le\max(H(U_n),H(V_n))x^{d_n}`$. Suppose $`\sigma>\delta`$ and choose an integer $`p\ge2`$ with $`(\sigma-\delta)\log p>h`$. Set $`a_n=U_n(p)`$, $`b_n=V_n(p)`$ and $`L_n=a_n F(p)-b_n`$. Hypotheses on height and degree give $`|a_n|\le\exp((h+\delta\log p)n^2+o(n^2))`$, while $`|L_n|=\exp(-\sigma\log p\,n^2+o(n^2))`$. The adjacent integer
``` math
a_nb_{n+1}-a_{n+1}b_n=a_{n+1}L_n-a_n L_{n+1}
```
is then $`o(1)`$, hence eventually zero. Also $`a_n\ne0`$ for large $`n`$: otherwise the nonzero integer $`L_n=-b_n`$ would have absolute value less than $`1`$. Thus $`b_n/a_n`$ is eventually a fixed rational $`r`$. If $`F(p)\ne r`$ then $`|L_n|\ge|F(p)-r|`$; if $`F(p)=r`$ then $`L_n=0`$. Both contradict the hypotheses, so $`\sigma\le\delta`$. The deduction of a contradiction from the two cross-product limits is formalised in [the integer linear-form argument](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperRankTwoCapR7.lean#L123). The homogenised logarithm satisfies
``` math
\limsup_{n\to\infty} n^{-2}\log\bigl|b^{d_n}\Lambda_n(a/b)\bigr|
 \le \delta\log b-\sigma\log(a/b),
```
which is negative on the stated sufficient region. The equivalence with the stated logarithmic condition is checked in [the logarithmic comparison](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperRankTwoCapR7.lean#L144), and the final bound in [the comparison with $`1/2`$](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperRankTwoCapR7.lean#L155). The conclusion bounds the sufficient cutoff furnished by the displayed degree estimate. An exclusion for a particular family requires its actual degree and remainder asymptotics. ◻

</div>

A general irrationality-exponent estimate retains the coefficient-height term. The stronger evaluated bound in Corollary <a href="#cor:rational-base-measure" data-reference-type="ref" data-reference="cor:rational-base-measure">3</a> removes it for Zudilin’s family, not for every family in this theorem. Long Section 2.6 gives the general formula and explains why, at $`h=0`$, the permitted additive bound $`hn^2+o(n^2)`$ is weaker than the literal $`hn^2(1+o(1))`$.

Estimates proved only at $`3/2`$, or for a different family at each base, do not verify the all-base hypotheses. The theorem also does not treat forms in several independent target values. For example, Postelmans and Van Assche prove the $`\mathbb{Q}`$-linear independence of $`1,\zeta_q(1),\zeta_q(2)`$ for $`q=1/p`$ with integer $`p\ge2`$ \[postelmansvanassche2007, Thm. 1.3, p. 3; Sec. 6\]. That simultaneous construction is not an instance of the theorem.

<a id="sec:hankel-order"></a>

# The first nonzero term of Zudilin’s Hankel determinant

The order of a nonzero formal series is its least exponent with nonzero coefficient. Matrix-entry orders alone give only a lower bound for the determinant, because terms can cancel. Here a moment expansion has a unique least-order term. We work in formal power series; values at a fixed real $`q`$ require a separate estimate.

Here $`N`$ denotes the Hankel rank and $`q`$ is a formal variable. At $`x=z=1`$, Zudilin’s normalised moments \[zudilin2016, (6), pp. 6–7\] are
``` math
v_m^*=\sum_{t\ge0}q^{(m+1)t}
 \frac{(q;q)_m^3(q^{t+1};q)_m}{(q^{m+1+t};q)_{m+1}},
 \qquad
 V_N^*=\det_{0\le i,j<N}(v_{i+j}^*).
```
The source uses $`\ell_p(x,z)=x\sum_{r\ge1}z^r/(p^r-x)`$, with $`p=q^{-1}`$, so $`\ell_p(1,1)=F(p)`$. Here $`x`$ is an auxiliary parameter, not the real base of the preceding section. These series are well defined coefficientwise: the $`t`$th summand has order $`(m+1)t`$, and every product in its denominator has constant term $`1`$. His row transformation proves
``` math
\operatorname{ord}_q V_N^*\ge
 \frac{N(N-1)(2N-1)}6
```
for every $`N\ge1`$ \[zudilin2016, Sec. 4, Lemma 1, pp. 6–7\]. A formal moment expansion identifies the unique least-order term and shows that this estimate is always sharp.

<div id="res:zudilin-sharp-qorder" class="theorem">

**Theorem 6** (the first nonzero term of the Hankel determinant). *For every $`N\ge1`$,
``` math
\operatorname{ord}_q V_N^*=\frac{N(N-1)(2N-1)}6,
```
and the coefficient of the first nonzero monomial is
``` math
[q^{N(N-1)(2N-1)/6}]V_N^*
   =\frac{(N!)^2(N+1)!}{2^N}.
```*

</div>

Lean: [order zudilin normalized hankel det all](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/AllRow/Producer.lean#L173), [coeff zudilin normalized hankel det all rat](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/AllRow/Producer.lean#L199).

<div class="proof">

*Proof.* To obtain moments at the nodes $`q^k`$, collect the dependence on $`m`$ into $`w=q^{m+1}`$. Write $`P=(q;q)_\infty`$ and set
``` math
G_q(w)=\frac1{(w;q)_\infty^3}
 \sum_{t\ge0}\frac{w^t}{(q;q)_t}
       \frac{(q^tw^2;q)_\infty}{(q^tw;q)_\infty^2},
 \qquad a_k(q)=[w^k]P^4G_q(w).
```
The expression belongs to $`\mathbb{Z}[[q,w]]`$: only finitely many $`t`$ contribute to each $`w`$-coefficient, and the remaining products define power series in $`q`$. The product identities $`(q;q)_m=P/(q^{m+1};q)_\infty`$ and $`(q^a;q)_m=(q^a;q)_\infty/(q^{a+m};q)_\infty`$ give the exact formal identity
``` math
v_m^*=P^4G_q(q^{m+1})
      =\sum_{k\ge0}a_k(q)q^{(m+1)k}.
```
At $`q=0`$, the $`t=0`$ term is $`(1-w^2)/(1-w)^5`$, while the remaining terms sum to $`w/(1-w)^4`$. Hence
``` math
G_0(w)=\frac{1+2w}{(1-w)^4},\qquad
 a_k(0)=\frac{(k+1)^2(k+2)}2=:c_k>0.
```

The expansion below is Heine’s formula for a Hankel determinant of moments as a sum of squared Vandermonde products; Zudilin uses its integral form and reproduces its proof in \[zudilin2017det, Sec. 2, (2)–(5), pp. 2–3\]. To compute modulo $`q^{M+1}`$, truncate each moment sum at $`k=M`$. Every omitted term is divisible by $`q^{M+1}`$, so multilinearity shows that the determinant is unchanged modulo $`q^{M+1}`$. Finite Cauchy–Binet then gives, coefficient by coefficient,
``` math
V_N^*=\sum_{k_0<\cdots<k_{N-1}}
 \left(\prod_{i=0}^{N-1}a_{k_i}(q)q^{k_i}\right)
 \prod_{0\le i<j<N}(q^{k_i}-q^{k_j})^2.
```
At rank two, the pair $`(k_0,k_1)=(0,1)`$ contributes $`6q+O(q^2)`$. Every other increasing pair has order at least two: its order is $`3k_0+k_1`$. This already gives $`V_2^*=6q+O(q^2)`$. At general rank, the summand indexed by $`(k_i)`$ has order
``` math
\sum_{i=0}^{N-1}(2N-1-2i)k_i.
```
Each $`a_k(q)`$ has $`q`$-order zero with positive initial coefficient $`c_k`$, and $`k_i\ge i`$. Equality with the least possible order occurs uniquely when $`k_i=i`$ for every $`i`$. That tuple contributes
``` math
\sum_{i=0}^{N-1}(2N-1-2i)i=\frac{N(N-1)(2N-1)}6
```
and leading coefficient
``` math
\prod_{i=0}^{N-1}c_i=\frac{(N!)^2(N+1)!}{2^N}.
```
No other tuple can cancel this coefficient. ◻

</div>

The Lean proof uses transformed rows rather than the moment expansion above. It checks both identities at every rank as [the exact order](https://github.com/wcook04/plectis-erdos/blob/0b500c7cf8e8bb7ae343484378df02f277fb8194/lean/ErdosProblems/Erdos1049/AllRow/Producer.lean#L173) and [the leading coefficient](https://github.com/wcook04/plectis-erdos/blob/0b500c7cf8e8bb7ae343484378df02f277fb8194/lean/ErdosProblems/Erdos1049/AllRow/Producer.lean#L199).

<a id="from-formal-order-to-size-at-a-fixed-base."></a>

#### From formal order to size at a fixed base.

Formal order alone does not bound the value at a fixed $`q`$: multiplication by $`(1-q)^{N^3}`$ leaves the first term unchanged but changes its logarithm by a cubic quantity. The long record, Section 3.1, proves separately that $`V_N^*(q)>0`$ and that $`\log(V_N^*(q)/(C_Nq^{B_N}))=O_q(N)`$ for fixed $`0<q<1`$. The same positive-measure argument, carried further, settles the size within that band. The first of the two facts about the moment weights used in the proof below, their exact factorisation with the bounds it gives, is a [Lean theorem](https://github.com/wcook04/plectis-erdos/blob/168bf6727758f918a430ef056a1c93d3160b53a6/lean/ErdosProblems/Erdos1049/PaperCompleteR21/RogersFactorisationAnalytic.lean#L1312). The theorem itself and the rest of its proof are ordinary mathematics, with no Lean statement.

<div id="res:sharp-fixed-base" class="theorem">

**Theorem 7** (the size of $`V_N^*`$ at a fixed base). *Fix $`0<q<1`$ and write $`P=(q;q)_\infty`$, $`B_N=N(N-1)(2N-1)/6`$ and $`C_N=(N!)^2(N+1)!/2^N`$. There is a $`K(q)>0`$ with
``` math
V_N^*(q)\sim K(q)\,C_Nq^{B_N}P^{2N}N^{-8F(1/q)}
 \qquad(N\to\infty).
```*

</div>

<div class="proof">

*Outline; the full proof is in the long record.* Collecting the moment dependence in $`w=q^{m+1}`$ as above writes $`v_m^*=\sum_{k\ge0}a_kq^{(m+1)k}`$ with $`a_k=[w^k]P^4G_q(w)`$. Two facts about these weights suffice. First, they factor exactly as
``` math
a_k=P^4\frac{R_k^{(2)}R_k^{(3)}}{(q;q)_k},
 \qquad
 R_k^{(r)}=\sum_{n_1+\cdots+n_r=k}\frac{(q;q)_k}{\prod_j(q;q)_{n_j}},
```
which gives $`P^5c_k\le a_k\le P^{-1}c_k`$ and a polynomial bound on the ratios $`a_{k+h}/a_k`$. Second, $`P^4(1-w)^4G_q(w)`$ is analytic past the unit circle with value $`3`$ and derivative $`2+8F(1/q)`$ at $`w=1`$, so $`a_k/c_k=1-8F(1/q)/(k+1)+O_q((k+1)^{-2})`$ and $`\prod_{k<N}a_k\sim\mathcal A(q)C_NN^{-8F(1/q)}`$ for a convergent product $`\mathcal A(q)`$.

In Heine’s expansion of the determinant, write each increasing tuple as $`k_i=i+\lambda_i`$ and reverse the shifts to obtain a partition. The least tuple contributes $`q^{B_N}\prod_{k<N}a_k`$ times its own Vandermonde product $`\Delta_N=\prod_{d<N}(1-q^d)^{2(N-d)}`$; the first bound on the weights majorises every other tuple by a summand that is summable over partitions and independent of $`N`$. Dominated convergence then reduces the normalised sum to the case $`a_k\equiv1`$, where Cauchy’s determinant evaluates it, and that sum tends to $`\mathcal M(q)=\prod_{d\ge1}(1-q^d)^{-d}`$. Separately $`\Delta_N/P^{2N}\to\mathcal M(q)^2`$. Writing $`\mathcal A(q)`$ for the convergent product above, the constant is $`K(q)=\mathcal A(q)\mathcal M(q)^3`$. ◻

</div>

One of those three factors of $`\mathcal M(q)`$ comes from the tuples other than the least one, and is therefore invisible to the order calculation; the other two come from comparing the least tuple’s own Vandermonde product with $`P^{2N}`$. The long record proves both ingredients in full, including the degree $`\lfloor k^2/4\rfloor+\lfloor k^2/3\rfloor`$ and coefficient sum $`6^k`$ of the product $`R_k^{(2)}R_k^{(3)}`$.

<a id="what-neither-calculation-implies."></a>

#### What neither calculation implies.

Theorem <a href="#res:sharp-fixed-base" data-reference-type="ref" data-reference="res:sharp-fixed-base">7</a> replaces that band by explicit linear and logarithmic terms and a constant. It changes no cubic coefficient and no prime-power valuation, so it supplies no divisor for the 2004 polynomial forms. Against the two proposed degree savings of long Section 3, the shortfall at $`3/2`$ is exactly $`N(74N^2-117N+41)/41>0`$ for $`N\ge2`$, and the new estimate closes no part of it. Neither assertion supplies the cyclotomic divisibility proved for a different recurrence in \[krvz2009, Prop. 4, pp. 14–15\]. The separate coefficient and content calculations are in long Section 3.3; Appendix <a href="#app:index" data-reference-type="ref" data-reference="app:index">5</a> records their sources and finite scope.

<a id="sec:open"></a>

# Supplementary arithmetic at $`3/2`$

The principal proofs are complete. The question here is whether combinations of evaluated rows can be divided by a common integer without losing nonvanishing or smallness of the remainder. This is a different operation from the polynomial cancellation in Section <a href="#sec:rational-base-irrationality" data-reference-type="ref" data-reference="sec:rational-base-irrationality">2</a>. The results below give necessary tests and conditional counting arguments, not such a family.

For natural $`a,b,N,K,Q,D`$, consider the clearing conditions
``` math
a,Q,D>0,\quad D\le N+K,\quad a^K\mid QD,
 \quad Qb^{N+K+1}<a^{K+1}.
```
Since $`QD>0`$, divisibility gives $`a^K\le QD\le Q(N+K)`$. Combining this with the last inequality and cancelling $`Q>0`$ yields $`b^{N+K+1}<a(N+K)`$. At $`(a,b)=(3,2)`$ this contradicts $`3x<2^{x+1}`$ for $`x=N+K\ge2`$. The last inequality tests only a lower bound for the omitted tail: for $`a>b\ge1`$,
``` math
Q a^N\sum_{m\ge N+K+1}\tau(m)(b/a)^m
 >\frac{Qb^{N+K+1}}{a^{K+1}}.
```
Thus it is necessary for the scaled tail to be less than $`1`$, not sufficient. The long record, Section 6, gives counterexamples to the converse and to clearing all coordinates from the last-coordinate test. The following theorem excludes these stated conditions at $`3/2`$, not every rational approximation argument.

<div id="res:nocorridor" class="theorem">

**Theorem 8** (failure of the stated clearing conditions at $`3/2`$). *For all $`N\ge1`$ and $`K\ge1`$ and all natural $`Q,D`$, the tuple $`(3,2,N,K,Q,D)`$ does not satisfy the [clearing conditions above](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L155).*

</div>

For $`r,s,B,\xi\in\mathbb{Q}`$ with $`r\ne0`$ and $`c:\mathbb{N}\to\mathbb{Q}`$, put
``` math
U_N=Br^N\left(\xi-\sum_{m=0}^{N-1}
 c(m+1)\frac{s^{m+1}}{r^{m+1}}\right).
```
The rational $`\xi`$ is arbitrary; in an irrationality argument it would be a hypothetical value of the series.

<div id="res:tailrec" class="theorem">

**Theorem 9** (recurrence for the scaled remainder). *Let $`r,s,B,\xi\in\mathbb{Q}`$ with $`r\ne0`$, let $`c:\mathbb{N}\to\mathbb{Q}`$, and define $`U_N`$ as above. Then for every $`N`$ the [recurrence for the scaled remainder](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L187) is
``` math
U_{N+1}=r\,U_N-B\,c(N+1)\,s^{\,N+1}.
```*

</div>

Subtracting successive partial sums proves the identity. Neither convergence nor equality of $`\xi`$ with the infinite series is assumed.

<div id="res:forcing" class="theorem">

**Theorem 10** (the forcing term). *Let $`s,B`$ be natural numbers and $`c:\mathbb{N}\to\mathbb{N}`$.*

1.  *If $`s\ge2`$, $`B\ge1`$ and $`c(N+1)\ge1`$, then $`2^{\,N+1}\le B\,c(N+1)\,s^{\,N+1}`$.*

2.  *If $`s=1`$, then $`B\,c(N+1)\,s^{\,N+1}=B\,c(N+1)`$.*

</div>

Lean: [forcing term](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperFiniteAssembliesR7.lean#L186).

<div class="proof">

*Proof.* In the first case, $`2^{N+1}\le s^{N+1}\le Bc(N+1)s^{N+1}`$. The second case follows by substituting $`s=1`$. ◻

</div>

For fixed $`r`$, the recurrence gives $`\max(|U_N|,|U_{N+1}|)\ge2^{N+1}/(1+|r|)`$ under the first case’s hypotheses. It excludes a bounded full sequence when those hypotheses hold for every $`N`$, not a bounded subsequence. The long record, Section 7, gives the triangle-inequality proof and a cancellation example.

Fix $`W\ge0`$. For any $`P\in\mathbb{Z}[X]`$, let $`[P]_i`$ denote its coefficient of $`X^i`$ and define
``` math
H_W(P)=\sum_{i=0}^W[P]_i3^i2^{W-i}.
```
This is $`2^WP(3/2)`$ when $`\deg P\le W`$ and a truncated evaluation otherwise. The congruence counts use either interpretation; statements about the actual remainder require the degree bound. Primitivity means that the two evaluated coordinates have gcd one, not that the polynomial coefficients do: at $`W=1`$, $`(X,3)`$ has coefficient content one but gives $`(3,6)`$. The counts below require neither normalisation. Any division must be applied to both the rows and their remainders before the residue map is formed. For depths $`R,S\ge0`$, define
``` math
J_{3,R}(P)=H_W(P)\pmod{3^R},\qquad
 J_{2,S}(P)=H_W(P)\pmod{2^S}.
```

<div id="res:bottomjet" class="lemma">

**Lemma 11** (a residue and divisibility by $`3^R`$). *Vanishing of the [residue modulo $`3^R`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L191) is exactly divisibility by the corresponding power of three: $`J_{3,R}(P)=0`$ if and only if $`3^R\mid H_W(P)`$.*

</div>

All four residues of $`(U,V)`$ vanish precisely when $`D=3^R2^S`$ divides both integers $`H_W(U)`$ and $`H_W(V)`$. Use the same $`W`$ for all rows: even when $`W`$ bounds every degree, replacing it by $`W+1`$ doubles the cleared values and changes their $`2`$-adic divisibility. The general truncation identity and endpoint congruences are given in long Section 5.

<div id="res:jetkernel" class="theorem">

**Theorem 12** (equal residues for two subset sums). *Fix a truncation index $`W`$ and depths $`R,S`$, and let $`(U_j,V_j)_{j<M}`$ be any $`M`$ pairs of integral polynomials. Represent each subset of $`\{0,\dots,M-1\}`$ by its indicator vector in $`\{0,1\}^M`$. If the $`2^M`$ subsets outnumber the possible residue vectors in
``` math
(\mathbb{Z}/3^R\mathbb{Z})^2\times(\mathbb{Z}/2^S\mathbb{Z})^2,
```
then two distinct subsets have the same residue vector. Subtracting their indicator vectors gives a nonzero coefficient vector in $`\{-1,0,1\}^M`$ cancelling all four residues. The target has exact cardinality
``` math
(3^R)^2(2^S)^2.
```
In particular, if $`R>0`$ and $`4R+2S\le M`$, such a collision exists.*

</div>

Lean: [four jet paper statement](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperFiniteAssembliesR7.lean#L248).

<div class="proof">

*Proof.* Send each subset to the sum of the residue vectors of its members. The pigeonhole principle gives two distinct subsets with the same image. The target size is the product of its four moduli. For $`R>0`$,
``` math
(3^R)^2(2^S)^2<(4^R)^2(2^S)^2=2^{4R+2S}\le2^M,
```
which proves the stated sufficient threshold. The cardinality formula, the collision, the signed $`\{-1,0,1\}`$ vector and the sufficient number of rows are formalised together in [the residue-count statement](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperFiniteAssembliesR7.lean#L248). ◻

</div>

The ambient count does not use relations between the two residue coordinates. Vanishing minors can reduce that cost to one coordinate.

<div id="res:plucker-collapse" class="theorem">

**Theorem 13** (vanishing minors and a residue count). *Let $`R_0`$ be a commutative ring and let $`w_n=(A_n,B_n)\in R_0^2`$. Suppose that every row is unimodular ($`u_n A_n+v_n B_n=1`$ for some $`u_n,v_n`$) and every adjacent minor vanishes:
``` math
A_nB_{n+1}-B_nA_{n+1}=0\qquad(n\ge0).
```
Then every pairwise minor $`A_iB_j-B_iA_j`$ vanishes. In particular, take $`R_0=\mathbb{Z}/(2^S3^R)\mathbb{Z}`$ with $`R>0`$. If $`S+2R\le k`$, there are two distinct binary selectors $`s,t\in\{0,1\}^{k}`$ such that
``` math
\sum_{i<k}s_iw_i=\sum_{i<k}t_iw_i.
```
Thus $`S+2R`$ rows suffice, in place of the sufficient bound $`2S+4R`$ from the ambient two-coordinate count.*

</div>

Lean: [plucker paper statement](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperFiniteAssembliesR7.lean#L269).

<div class="proof">

*Proof.* If $`uA+vB=1`$ and $`AB'-BA'=0`$, then $`(A',B')=(uA'+vB')(A,B)`$. Applying this identity to consecutive rows and then inducting shows that every row is a multiple of $`w_0`$. This proves that every pairwise minor is zero. Right multiplication by
``` math
\begin{pmatrix}u_0&-B_0\\v_0&A_0\end{pmatrix}
```
has determinant $`u_0A_0+v_0B_0=1`$ and sends $`w_0`$ to $`(1,0)`$. Consequently all transformed subset sums have second coordinate zero and take at most $`2^S3^R`$ values. Finally
``` math
2^S3^R<2^S4^R=2^{S+2R}\le2^k,
```
and pigeonhole gives the two selectors. The special cases requiring an invertible second coordinate are formalised together in [the vanishing-minor and residue-count statement](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1049/PaperFiniteAssembliesR7.lean#L269). ◻

</div>

Primitive integer rows are unimodular modulo every modulus: for $`(2,3)`$ modulo $`6`$, neither coordinate is a unit, but $`-2+3=1`$. Vanishing minors is an extra assumption. It is imposed in the quotient ring, not in $`\mathbb{Z}`$: the rows $`(1,0),(1,6)`$ below have determinant $`6`$ and coincide modulo $`6`$. Arbitrary primitive rows need not satisfy it; $`(1,0),(0,1)`$ have determinant $`1`$. No such approximation family is constructed here.

<a id="an-exponent-model-and-row-normalisation"></a>

## An exponent model and row normalisation

The next proposition checks an exponent model, not an approximation construction: no coefficient polynomials producing these exponents are specified.

<div id="res:pade" class="proposition">

**Proposition 14** (exponent model: summand bound and exact gap). *Let $`\widetilde{E}_n=3n^{2}-n`$ and put
``` math
\widetilde{P}(n,k)=2\bigl(k(n-k)+nk\bigr)+k(k-1),
```
``` math
\widetilde{Q}(n,m)=2(n^{2}-n)+j^{2}+2jm+j-m^{2}+3m,
 \qquad j=n-m-1 .
```
Then, for integers $`n,k,m`$:*

1.  *if $`0\le k\le n`$, the [summand exponent bound](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L30) is $`\widetilde{P}(n,k)\le\widetilde{E}_n`$, and the gap factors as $`\widetilde{E}_n-\widetilde{P}(n,k)=(n-k)(3n-k-1)`$;*

2.  *the [exact gap identity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L52) is $`\widetilde{E}_n-\widetilde{Q}(n,m)=2\bigl(n+m(m-1)\bigr)`$.*

</div>

Lean: [pade summand bound and gap](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperFiniteAssembliesR7.lean#L201).

For the first inequality the gap is zero at $`n=k=0`$; otherwise both factors are nonnegative. Substituting $`j=n-m-1`$ gives the second identity for every integer $`m`$.

<div id="res:content" class="proposition">

**Proposition 15** (rescaling two integer rows). *Multiplying two integer rows by $`c_1`$ and $`c_2`$ multiplies their [determinant](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L124) by $`c_1c_2`$. The [integer identity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L94) and its [absolute-value form](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L104) show that the added divisibility is accompanied by exactly the same factor in the real absolute value.*

</div>

Lean: [integer scalar content](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/PaperFiniteAssembliesR7.lean#L59).

For nonzero row contents $`c_1,c_2`$, write $`r_i=c_ir_i^{\rm prim}`$. Then $`\det(r_1,r_2)=c_1c_2\det(r_1^{\rm prim},r_2^{\rm prim})`$ and $`r_i\cdot(\xi,-1)=c_i r_i^{\rm prim}\cdot(\xi,-1)`$. These identities concern multiplication or division of whole integer rows, not cancellation of a polynomial factor before specialisation. Nor does dividing different rows by different contents preserve a fixed residue relation: $`(1,1)+(5,5)`$ is zero modulo $`6`$, but the sum of the primitive rows is $`(2,2)`$. Even contents coprime to the modulus require the residue map to be formed again after row-by-row normalisation.

<a id="residue-counts-and-the-index-after-division"></a>

## Residue counts and the index after division

The primitive rows $`(1,0),(1,6)`$ generate $`\mathbb{Z}\oplus6\mathbb{Z}`$. Modulo $`2`$ this lattice has only two residue vectors, but dividing its even vectors by $`2`$ gives $`\mathbb{Z}\oplus3\mathbb{Z}`$, which still has index $`3`$ in $`\mathbb{Z}^2`$. Thus a small residue space need not become the full integer lattice after division. Smith normal form gives both quantities in general.

Let a rank-two lattice $`\Lambda\subset\mathbb{Z}^2`$ be generated by primitive rows, and let $`g>0`$ be the gcd of their $`2\times2`$ minors. By the description of Smith invariants through gcds of minors \[stanley2016, Thms. 2.3–2.4, p. 3\], its Smith invariants are $`1,g`$. For $`D\ge1`$, therefore
``` math
\bigl|\operatorname{im}(\Lambda\bmod D)\bigr|
       =\frac{D^2}{\gcd(g,D)},\qquad
 \left[\mathbb{Z}^2:\frac{\Lambda\cap D\mathbb{Z}^2}{D}\right]
       =\frac{g}{\gcd(g,D)}.
```
A unimodular change of coordinates preserves $`D\mathbb{Z}^2`$ and reduces both calculations to $`\mathbb{Z}\oplus g\mathbb{Z}`$. Thus, when $`D\mid g`$, there are only $`D`$ residues, but the divided lattice still has index $`g/D`$. The general formulas without primitive generators are in the long record, Section 10.1.

If two independent divided rows $`(A_i,B_i)`$ have $`|A_i|\le H`$ and $`|A_i\xi-B_i|\le\varepsilon`$, their determinant gives
``` math
2H\varepsilon\ge \frac{g}{\gcd(g,D)}.
```
This is a restriction on two independent forms in the divided lattice. For one nonzero integral form tending to zero, no additional product $`H\varepsilon\to0`$ is required.

<a id="a-collision-must-have-a-small-nonzero-real-remainder"></a>

## A collision must have a small nonzero real remainder

Counting residues within short intervals gives small differences. To keep a difference nonzero, one must also bound the number of selectors with the same residues and the same real value.

<div id="res:boundedfibre" class="theorem">

**Theorem 16** (equal residues with close, distinct values). *Let $`A,B,J`$ be finite sets and let $`f:A\to B`$, $`g:A\to\mathbb R`$ and $`\iota:A\to J`$. Suppose that each simultaneous fibre of $`(f,g)`$ has at most $`k`$ elements and that, for some $`\delta>0`$,
``` math
\iota(x)=\iota(y)\quad\Longrightarrow\quad |g(x)-g(y)|<\delta.
```
If $`|B||J|k<|A|`$, then some distinct $`x,y\in A`$ satisfy
``` math
f(x)=f(y),\qquad 0<|g(x)-g(y)|<\delta.
```*

</div>

Lean: [exists small real escape of conditional multiplicity](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1049/QuantitativeSelectorEscape.lean#L79).

<div class="proof">

*Proof.* Partition $`A`$ by $`(f,\iota)`$. Some cell has more than $`k`$ elements, so its $`g`$-values cannot all agree. Two unequal values in that cell have the same residue vector and differ by less than $`\delta`$. ◻

</div>

Primitivity gives no useful bound on $`k`$: repeated rows $`(1,0)`$ produce the same sum and remainder for every subset of a given size. The application below therefore needs a separate multiplicity estimate.

Fix positive integers $`n,D`$ and $`M`$ primitive integer rows $`(A_j,B_j)`$, indexed by $`0\le j<M`$. Put $`e_j=A_jF(3/2)-B_j`$ and apply Theorem <a href="#res:boundedfibre" data-reference-type="ref" data-reference="res:boundedfibre">16</a> to binary selectors, with
``` math
f(\varepsilon)=\sum_j\varepsilon_j(A_j,B_j)\pmod D,
 \qquad g(\varepsilon)=\sum_j\varepsilon_j e_j.
```
Let $`Q`$ be the number of attained residue vectors and let $`k`$ bound the simultaneous $`(f,g)`$ fibres. For a rank-two lattice generated by these rows, the preceding Smith formula gives $`Q\le D^2/\gcd(g_0,D)`$, where $`g_0`$ is the gcd of the minors; it gives no bound on $`k`$. The selector remainders span an interval of length $`T=\sum_j|e_j|`$. Subtract its minimum, multiply by $`n/D`$, and take floors. The resulting indices range from $`0`$ to $`\lfloor nT/D\rfloor`$, and two remainders with the same index differ by less than $`D/n`$. Thus a sufficient inequality is
``` math
\begin{equation}
\label{eq:quantitative-selector-budget}
 2^M>Qk\left(\left\lfloor\frac{nT}{D}\right\rfloor+1\right).
\end{equation}
```
It yields a signed row sum divisible coordinatewise by $`D`$, whose divided real remainder has absolute value strictly between $`0`$ and $`1/n`$. The residue-specific version is in the long record, Section 10.1. The multiplicity bound is what prevents a zero remainder; polynomial nonvanishing does not.

<a id="the-remaining-construction-problem"></a>

## The remaining construction problem

The next question specifies the required integer forms, not an approximation family. Unrestricted, it is equivalent to irrationality of $`F(3/2)`$; the long record, Section 10, proves the converse even with the stated index bounds and coefficient height $`\exp(O(n^2))`$. A method-specific problem must additionally fix its coefficient formulas, parameter set and permitted normalisations.

<div id="prob:kernel" class="problem">

**Problem 17** (a divided linear form with small nonzero remainder). Exhibit an integer constant $`C\ge1`$ and, for every sufficiently large positive integer $`n`$, positive integers $`W_n,R_n,S_n,M_n`$ such that
``` math
n^2\le W_n,R_n,S_n\le Cn^2,
 \qquad 4R_n+2S_n\le M_n\le Cn^2,
```
together with polynomial pairs $`(U_{n,j},V_{n,j})\in\mathbb{Z}[X]^2`$ for $`0\le j<M_n`$, each of degree at most the common degree bound $`W_n`$, whose specialised integer rows are primitive:
``` math
\gcd\!\bigl(H_{W_n}(U_{n,j}),H_{W_n}(V_{n,j})\bigr)=1.
```
Find a nonzero vector $`\lambda^{(n)}\in\{-1,0,1\}^{M_n}`$ for which, on putting
``` math
U_n=\sum_{j<M_n}\lambda^{(n)}_jU_{n,j},
 \qquad V_n=\sum_{j<M_n}\lambda^{(n)}_jV_{n,j},
```
the pair $`(U_n,V_n)`$ is not $`(0,0)`$, all four residues vanish,
``` math
J_{3,R_n}(U_n)=J_{3,R_n}(V_n)=0,
 \qquad J_{2,S_n}(U_n)=J_{2,S_n}(V_n)=0,
```
where every residue in this display is formed using the common degree bound $`W_n`$, and the resulting divided integer linear form
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

The residues make $`A_n,B_n`$ integers. If $`F(3/2)=a/b`$, then $`|\rho_n|\ge1/|b|`$ whenever $`\rho_n\ne0`$, contradicting the bound for arbitrarily large indices $`n`$. Such indices suffice; see long Section 10.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The [pinned formal-source revision](https://github.com/wcook04/plectis-erdos/tree/99f4bf47422abbd8757cbb22b50ba079d764d3a7) contains the Lean sources, the fixed toolchain, and the library manifest used in the verification. The ordinary proofs used here are printed with their hypotheses.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

The problem numbering and status follow the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\]. I thank Wouter van Doorn for advice on writing for a first-time reader, using fewer names and symbols, and explaining the force of a theorem’s hypotheses. His advice was given on another note and does not constitute mathematical review or endorsement of the results here.

<a id="app:index"></a>

# Source comparisons and formal verification

<a id="integer-base-methods."></a>

#### Integer-base methods.

Vandehey treats signed coefficients in the digit argument \[vandehey2013, Thms. 1.1–1.2, p. 2\]; Duverney and Tachiya prove linear-independence refinements \[duverneytachiya2019, Thms. 1.1–1.2 and Cor. 1.1, pp. 2–3\]. Van Assche gives a little $`q`$-Legendre construction \[vanassche2001, (4), (9), (16), pp. 3–4\]. These integer-base methods are compared in the long record’s related-work section; they are not inputs to the rational specialisation in Section 2.

<a id="coefficient-moments."></a>

#### Coefficient moments.

The coefficient polynomials in \[zudilin2016, Sec. 3, p. 5\] give a moment problem different from the remainder moments in Section 3. Long Section 3.3 checks the two leading Hankel families through rank eight, not the all-rank criterion in \[wangzhu2016, Lemma 2.1, p. 4\]. For the unshifted family, positivity through rank eight at every real $`p\ge1`$ is also a [Lean theorem](https://github.com/wcook04/plectis-erdos/blob/168bf6727758f918a430ef056a1c93d3160b53a6/lean/ErdosProblems/Erdos1049/PaperR20/HankelKroneckerCertificate.lean#L458). So is the consequence the long record draws from it: at each rank up to eight, the roots of a determinant polynomial built from Zudilin’s coefficients are real and lie below $`F(p)`$ for every real $`p>1`$ ([finite coefficient positivity and pencil roots](https://github.com/wcook04/plectis-erdos/blob/168bf6727758f918a430ef056a1c93d3160b53a6/lean/ErdosProblems/Erdos1049/PaperR20/FinitePencilProposition.lean#L43)). Long Section 3.3 also proves a finite moment representation and discusses $`(m!)^3`$ at the endpoint \[berg2007, Thm. 5.1\], formal continued fractions and finite quadrature \[sw2024; golubwelsch1969\]. It also gives complete polynomial contents through rank five and specified cyclotomic residue tests through rank eight. These finite results do not assert all-rank coefficient positivity or divisibility.

<a id="functional-equations."></a>

#### Functional equations.

Bell and Smertnig’s classification \[bellsmertnig2026, Thm. 1.3 and the consequences on p. 3\] excludes $`k`$-Mahler equations for $`L(z)=\sum_{n\ge1}\tau(n)z^n`$ when $`k\ge2`$: there is no polynomial-coefficient relation among $`L(z),L(z^k),\ldots,L(z^{k^d})`$ with a nonzero coefficient of $`L(z)`$. The single-base exclusion is also a Lean theorem, in the form that for every $`k\ge2`$ no finite-dimensional $`\mathbb{Q}(z)`$-subspace of $`\mathbb{Q}((z))`$ containing $`L`$ is stable under $`z\mapsto z^k`$ ([single-base statement](https://github.com/wcook04/plectis-erdos/blob/168bf6727758f918a430ef056a1c93d3160b53a6/lean/ErdosProblems/Erdos1049/PaperCompleteR21/SimultaneousMahlerSystemUnconditional.lean#L263)). Long Section 10.3 explains this functional obstruction; it gives no irrationality statement for $`L(2/3)=F(3/2)`$.

<a id="formal-sources-and-finite-computations."></a>

#### Formal sources and finite computations.

In the supplied snapshot, `PaperR17/SourceConsumers.lean` constructs the cancelled forms and proves the irrationality and measure results; `AllRow/Producer.lean` constructs the transformed rows and proves the all-rank determinant formulas.

The index distinguishes reported public, parallel-release and unbuilt material; no new Lean run is claimed for the indexed material. The linked invertible-coordinate theorem is weaker than the ordinary unimodular-row theorem. Apart from the rank-eight positivity of the unshifted family, the finite computations described above are not Lean proofs; their certificates and reproduction scripts are in the long record. Historical links retain their original revisions and line numbers, which have not been revalidated. Long Appendix A records the snapshot identifiers and gives the full source guide.

<a id="sec:pinned-lean-sources"></a>

# Additional formal statements

Each link below retains its original revision and line number. Appendix <a href="#app:index" data-reference-type="ref" data-reference="app:index">5</a> explains the supplied snapshot and verification scope.

<a id="comparison-of-the-two-diagonals"></a>

#### Comparison of the two diagonals

[initial values of Van Assche’s diagonal](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/QAperyDiagonalNonEquivalence.lean#L33); [residual of the other diagonal’s recurrence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/QAperyDiagonalNonEquivalence.lean#L67); [nonzero residual for $`p>1`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/QAperyDiagonalNonEquivalence.lean#L94).

<a id="clearing-partial-sums-and-their-remainders"></a>

#### Clearing partial sums and their remainders

[six conditions for clearing a window](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L113); [necessary power-versus-linear inequality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L121); [$`3x<2^{x+1}`$ for $`x\ge 2`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L142); [rational-base partial sum](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L168); [one-term extension of the partial sum](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L173); [scaled remainder](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L181); [subtracted term in the recurrence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L198); [exponential lower bound for that term](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L204); [integer-base special case](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L218); [rational comparison for $`7/2`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L36).

<a id="proposed-denominator-exponents-and-scalar-rescaling"></a>

#### Proposed denominator exponents and scalar rescaling

[doubled proposed denominator exponent](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L19); [first summand exponent](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L24); [second summand exponent](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L46); [bound for the second exponent](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L60); [linear-form error under scalar rescaling](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L84); [divisor introduced by rescaling rows](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L116).

<a id="residues-at-32"></a>

#### Residues at $`3/2`$

[denominator-cleared evaluation at $`3/2`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L98); [number of possible residue vectors](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L131); [equal residues for two subsets](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L142); [sufficient row count for equal residues](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L161); [divisibility by $`2^S`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L197); [evaluation modulo $`3`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L203).

<a id="evaluation-at-a-general-rational-base"></a>

#### Evaluation at a general rational base

[homogeneous evaluation at a rational base](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L221); [reduction modulo the numerator](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L226); [reduction modulo the denominator](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L238); [coprimality with the numerator from the constant coefficient](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L254); [coprimality with the denominator from the top coefficient](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L270); [combined coprimality criterion](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L286); [coprimality of homogeneous cyclotomic values](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L302).

<a id="restrictions-on-common-divisors"></a>

#### Restrictions on common divisors

[evaluation modulo $`2`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L320); [exclusion of the factor $`3`$ by the constant coefficient](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L338); [exclusion of the factor $`2`$ by the coefficient of $`X^W`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L356); [restriction on a common evaluated divisor](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L398).

<a id="sufficient-regions-and-comparison-bounds"></a>

#### Sufficient regions and comparison bounds

[comparison $`2C_0\le C_1`$ from exponent bounds](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L416); [sign of the scalar exponent at $`3/2`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L428); [$`31/4`$ satisfies the $`81/200`$ condition](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L45); [the same condition for positive powers of $`31/4`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L59); [$`31/4`$ lies outside the earlier region](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L91); [$`81/200<\log 2/\log 3`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L105); [$`3/2`$ fails the $`81/200`$ condition](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L122); [bound for the rectangular exponent expression](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L103); [equality case for that bound](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L126).

<div class="thebibliography">

99

P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). P. Bundschuh and K. Väänänen, [*Arithmetical investigations of a certain infinite product*](https://numdam.org/item/CM_1994__91_2_175_0.pdf), Compositio Math. **91** (1994), no. 2, 175–199. W. Zudilin, *Remarks on irrationality of $`q`$-harmonic series*, Manuscripta Math. **107** (2002), no. 4, 463–477, doi:[10.1007/s002290200249](https://doi.org/10.1007/s002290200249). W. Zudilin, [*Heine’s basic transform and a permutation group for $`q`$-harmonic series*](https://geodesic.mathdoc.fr/articles/10.4064/aa111-2-4/), Acta Arith. **111** (2004), no. 2, 153–164, doi:[10.4064/aa111-2-4](https://doi.org/10.4064/aa111-2-4). Page references are to the printed journal pages. W. Zudilin, [*On the irrationality of generalized $`q`$-logarithm*](https://arxiv.org/abs/1601.02688v2), arXiv:1601.02688; Res. Number Theory **2** (2016), Art. 15, doi:[10.1007/s40993-016-0042-x](https://doi.org/10.1007/s40993-016-0042-x). Page references are to arXiv:1601.02688v2. The remark that the results extend to non-integer $`p=r/s`$, $`|p|>1`$, under an assumption $`\log|r|>c\log|s|`$ for a computable $`c>0`$, is in Section 2, p. 4, in the paragraph beginning “Finally, we remark”; no value of $`c`$ is computed there, and the remark is made for the generalized $`q`$-logarithm of that paper. R. P. Stanley, *Smith normal form in combinatorics*, J. Combin. Theory Ser. A **144** (2016), 476–495, doi:[10.1016/j.jcta.2016.06.013](https://doi.org/10.1016/j.jcta.2016.06.013); arXiv:[1602.00166v1](https://arxiv.org/abs/1602.00166v1). Page references are to arXiv:1602.00166v1. W. Zudilin, *A determinantal approach to irrationality*, Constr. Approx. **45** (2017), no. 2, 301–310, doi:[10.1007/s00365-016-9333-7](https://doi.org/10.1007/s00365-016-9333-7); arXiv:[1507.05697v1](https://arxiv.org/abs/1507.05697v1). Page and equation references are to arXiv:1507.05697v1. T. F. Bloom, [*Erdős Problem \#1049*](https://www.erdosproblems.com/1049), `erdosproblems.com/1049`. Historical snapshot cited in the supplied manuscript: accessed 28 July 2026, displaying “last edited 28 September 2025”. J. Bell and D. Smertnig, [*Mahler series with multiplicative coefficient sequences*](https://arxiv.org/abs/2603.23456v1), arXiv:2603.23456v1, 24 March 2026. Theorem 1.3 is on pp. 2–3; its stated consequences on p. 3 include that the divisor and totient generating series are not $`k`$-Mahler for any $`k\ge2`$. J. Vandehey, [*On an incomplete argument of Erdős on the irrationality of Lambert series*](https://arxiv.org/abs/1206.0340v1), Integers **13** (2013), Paper A58. Page references are to arXiv:1206.0340v1 (2012). D. Duverney and Y. Tachiya, *Refinement of the Chowla–Erdős method and linear independence of certain Lambert series*, Forum Math. **31** (2019), no. 6, 1557–1566, doi:[10.1515/forum-2018-0299](https://doi.org/10.1515/forum-2018-0299). Page references are to the [authors’ version](https://danielduverney.fr/documents/theorie-des-nombres/DuverneyTachiya190522.pdf). W. Van Assche, [*Little $`q`$-Legendre polynomials and irrationality of certain Lambert series*](https://arxiv.org/abs/math/0101187v1), Ramanujan J. **5** (2001), no. 3, 295–310, doi:[10.1023/A:1012930828917](https://doi.org/10.1023/A:1012930828917). Page references are to arXiv:math/0101187v1. K. Postelmans and W. Van Assche, [*Irrationality of $`\zeta_q(1)`$ and $`\zeta_q(2)`$*](https://arxiv.org/abs/math/0604312v1), J. Number Theory **126** (2007), no. 1, 119–154, doi:[10.1016/j.jnt.2006.11.011](https://doi.org/10.1016/j.jnt.2006.11.011). Page references are to arXiv:math/0604312v1 (2006). C. Krattenthaler, I. Rochev, K. Väänänen and W. Zudilin, *On the non-quadraticity of values of the $`q`$-exponential function and related $`q`$-series*, Acta Arith. **136** (2009), no. 3, 243–269, doi:[10.4064/aa136-3-4](https://doi.org/10.4064/aa136-3-4); arXiv:[0812.2921v1](https://arxiv.org/abs/0812.2921v1). Page references are to arXiv:0812.2921v1. Y. Wang and B.-X. Zhu, [*Log-convex and Stieltjes moment sequences*](https://arxiv.org/abs/1612.04114v1), Adv. Appl. Math. **81** (2016), 115–127, doi:[10.1016/j.aam.2016.06.008](https://doi.org/10.1016/j.aam.2016.06.008). Page references are to arXiv:1612.04114v1. C. Berg, *On powers of Stieltjes moment sequences, II*, J. Comput. Appl. Math. **199** (2007), 23–38; arXiv:[math/0412340v1](https://arxiv.org/abs/math/0412340v1). Theorem references use the preprint; Theorem 5.1 treats factorial powers. A. D. Sokal and J. Walrad, *Continued-fraction characterization of Stieltjes moment sequences with support in $`[\xi,\infty)`$*, [arXiv:2404.12131v1](https://arxiv.org/abs/2404.12131v1), 2024. The classical Stieltjes criterion is recalled on pp. 1–2. G. H. Golub and J. H. Welsch, *Calculation of Gauss Quadrature Rules*, Math. Comp. **23** (1969), no. 106, 221–230, doi:[10.1090/S0025-5718-69-99647-1](https://doi.org/10.1090/S0025-5718-69-99647-1).

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
