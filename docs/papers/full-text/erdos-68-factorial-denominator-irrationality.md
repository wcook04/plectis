<a id="erdos-68-factorial-denominator-irrationality"></a>

# Two Incomparable Denominator Exclusions for \sum\_{n\ge2}(n!-1)^{-1}

<div id="res:problem" class="problem">

**Problem 1** (Erdős \#68). Is
``` math
S=\sum_{n\ge2}\frac1{n!-1}
```
irrational?

</div>

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Any expression of $`S=\sum_{n\ge2}(n!-1)^{-1}`$ as $`a/q`$, with integers $`a`$ and $`q>0`$, must satisfy
``` math
q\nmid299999!,\qquad q\ge2^{39990}>10^{12038},
```
according to the exact finite calculations described here. The first exclusion uses the next integer above a factorial-scaled partial sum; the second uses a rational enclosure and continued fractions. Neither restriction implies the other.

A separate coefficient construction gives remainders of the form $`MS+k`$, with integers $`M,k`$. We classify the vectors that cancel prescribed initial weighted sums and determine their possible $`M`$. At fixed $`M`$, all remainders have the same fractional part. To prove irrationality by this approach, each positive integer must divide a moment whose remainder is shown to lie strictly between consecutive integers.

<a id="sec:problem"></a>

# The denominator exclusions

<a id="the-factorial-divisibility-exclusion."></a>

#### The factorial-divisibility exclusion.

For $`m\ge2`$, put
``` math
H_m=\sum_{n=2}^m\frac1{n!-1},\qquad
Z_m=\lfloor m!H_m\rfloor+1,
```
and for $`m\ge3`$ define the carry
``` math
b_m=mZ_{m-1}+1-Z_m.
```
Here $`Z_m`$ is the least integer strictly greater than $`m!H_m`$, even when $`m!H_m`$ is itself an integer; it is not always $`\lceil m!H_m\rceil`$. Thus $`b_m=1`$ means that the next integers scale exactly by the factor $`m`$: $`Z_m=mZ_{m-1}`$. The exclusion rests on the implication, for integers $`a`$ and $`q>0`$,
``` math
\begin{equation}
S=a/q,\quad q\mid(m-1)!,\quad m\ge3
\quad\Longrightarrow\quad b_m=1.\label{eq:finite-denominator-consumer}
\end{equation}
```
For $`n\ge3`$, we have $`1/(n!-1)<(n-1)/n!`$ and $`\sum_{n>m}(n-1)/n!=1/m!`$, so $`0<m!(S-H_m)<1`$. Under the divisibility hypothesis, $`m!S`$ is integral, so this bound identifies it as $`Z_m`$. The same argument at $`m-1`$ gives $`Z_m=m!S=mZ_{m-1}`$, proving <a href="#eq:finite-denominator-consumer" data-reference-type="eqref" data-reference="eq:finite-denominator-consumer">[eq:finite-denominator-consumer]</a>. Thus $`b_m\ne1`$ forces [every rational denominator to be at least $`m`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L876), since any smaller positive $`q`$ would divide $`(m-1)!`$. The recorded exact value $`b_{300000}\ne1`$ therefore excludes every divisor of $`299999!`$ as a denominator of $`S`$. This does not exclude every $`299999`$-smooth denominator: sufficiently high powers of a small prime need not divide $`299999!`$. Section <a href="#sec:finite" data-reference-type="ref" data-reference="sec:finite">7</a> distinguishes this reported full run from the smaller computation repeated in the rewrite notes.

<a id="the-size-exclusion."></a>

#### The size exclusion.

For the continued-fraction calculation, put $`B=2^{80000}`$ and let $`N`$ be the first integer with $`N!-1>B`$. Define
``` math
\ell=\sum_{n=2}^{N-1}\left\lfloor\frac B{n!-1}\right\rfloor,
 \qquad
 u=\ell+(N-2)+\left\lfloor\frac{2B}{N!-1}\right\rfloor+1.
```
Rounding the $`N-2`$ prefix terms down loses less than $`N-2`$. Successive terms in the omitted tail have ratio less than $`1/(N+1)`$, so their sum is less than $`(N+1)/(N(N!-1))<2/(N!-1)`$. Thus $`\ell/B<S<u/B`$. Exact integer computation gives $`N=7054`$ and $`u-\ell=7053`$.

Apply the continued-fraction algorithm to both endpoints. Retain a common integer part only while both remainders are nonzero, then invert and reverse the endpoint order. The computation gives $`23449`$ common partial quotients $`a_0,\ldots,a_{23448}`$. Their convergent denominators satisfy
``` math
Q_{-2}=1,\qquad Q_{-1}=0,\qquad
 Q_j=a_jQ_{j-1}+Q_{j-2},\qquad Q_{23448}\ge2^{39990}.
```
Every rational in the open enclosure has this initial segment. To see why it gives a denominator bound, write $`P_j/Q_j`$ for the last common convergent, with $`j=23448`$. A continuation with complete quotient $`x/y>1`$, where $`x,y`$ are coprime positive integers, has reduced denominator $`Q_jx+Q_{j-1}y\ge Q_j`$; if the expansion terminates at this convergent, its denominator is $`Q_j`$. Reducedness follows from the determinant identity $`P_jQ_{j-1}-P_{j-1}Q_j=\pm1`$ \[nist-dlmf, §1.12(ii), (1.12.5)–(1.12.7), (1.12.20)–(1.12.21)\]. The integer comparison $`2^{39990}>10^{12038}`$ completes the second exclusion. A non-reduced representation has a denominator at least as large as the reduced one, so the bound applies to every $`q`$ in $`S=a/q`$. The long record gives the immutable program and receipt links.

Neither restriction implies the other: the prime $`300007`$ satisfies the divisibility restriction and fails the size restriction, whereas $`299999!`$ does the reverse. Both conclusions are finite; they do not decide the irrationality question posed by Erdős \[erdos1988, p. 102\] and listed in Bloom’s catalogue \[bloom\]. Their computational certificates are specified in §<a href="#sec:finite" data-reference-type="ref" data-reference="sec:finite">7</a>.

<a id="the-corresponding-rationality-criterion."></a>

#### The corresponding rationality criterion.

A finite non-unit carry excludes particular denominators. Non-unit carries at arbitrarily large indices are equivalent to irrationality.

<div id="res:carry-characterization" class="theorem">

**Theorem 2** (exact carry characterisation). *<span id="res:strict-successor-complete-characterization" label="res:strict-successor-complete-characterization"></span> The following conditions are equivalent:
``` math
S\notin\mathbb Q,\qquad
(\forall B)(\exists m>B)\ b_m\ne1,\qquad
(\forall B)(\exists m>B)\ m\nmid Z_m.
```
In particular, [cofinal non-unit carries imply irrationality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L953); equivalently, the original problem is the [criterion using the next integer](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L1090).*

</div>

Lean: [carry characterisation](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos68/PaperCompleteExisting.lean#L45).

<div class="proof">

*Proof.* Rationality forces eventual unit carries by <a href="#eq:finite-denominator-consumer" data-reference-type="eqref" data-reference="eq:finite-denominator-consumer">[eq:finite-denominator-consumer]</a>. Conversely, if $`b_m=1`$ eventually, then $`Z_m/m!`$ is eventually constant. Since
``` math
H_m<Z_m/m!\le H_m+1/m!,
```
that rational constant is $`S`$. Finally writing $`x=(m-1)!H_{m-1}`$ gives $`b_m=m-1-\lfloor m\{x\}+1/(m!-1)\rfloor`$, hence $`-1\le b_m\le m-1`$. For $`m\ge3`$, these bounds together with $`Z_m=mZ_{m-1}+1-b_m`$ imply $`m\mid Z_m`$ exactly when $`b_m=1`$. ◻

</div>

For $`e`$, multiplication by $`m!`$ clears every denominator of the partial sum; here $`\gcd(m!,m!-1)=1`$ prevents even the last summand from being cleared when $`m\ge3`$. For the tail arguments below, the issue is the gap to an integer after scaling, not just the size of the unscaled tail. The remaining sections study that gap and the exact coefficient equations. Appendix <a href="#sec:companion-orbit" data-reference-type="ref" data-reference="sec:companion-orbit">8</a> gives a factorial-digit formulation and the floor correction relating the two sequences. Secondary constructions are proved in the long companion paper, *Denominators and Rationality Criteria*.

<a id="sec:channels"></a>

# Integer vectors for cancelling weighted sums

For a chosen integer $`D\ge2`$, we seek integer coefficients whose contributions at denominators $`2!-1,\ldots,D!-1`$ vanish, removing the first few terms of a remainder. To construct such coefficients, we remove powers of $`d!`$ from $`n!`$. For example, at $`d=3`$ and $`n=4`$, removing the factor $`3!=6`$ leaves $`4`$, and $`24/5-4/5=4`$: the fractional part is unchanged. For a finitely supported integer vector $`\lambda=(\lambda_n)_{n\ge1}`$ and an integer $`d\ge2`$, define
``` math
W_{d,n}=\frac{n!}{(d!)^{\lfloor n/d\rfloor}},\qquad
M(\lambda)=\sum_n\lambda_n n!,\qquad
V_d(\lambda)=\sum_n\lambda_nW_{d,n}.
```
The [weights are integers](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L25). Indeed, write $`n=kd+r`$ with $`0\le r<d`$. The quotient $`n!/((d!)^k r!)`$ is a multinomial coefficient, and $`W_{d,n}`$ is $`r!`$ times that integer. Since $`n!=(d!)^{\lfloor n/d\rfloor}W_{d,n}`$ and $`d!\equiv1\pmod{d!-1}`$, the difference $`(n!-W_{d,n})/(d!-1)`$ is an integer. Thus the same fractional-part calculation holds for every $`d\ge2`$ and $`n\ge1`$. Write $`e_n`$ for the vector with coefficient $`1`$ at index $`n`$ and $`0`$ elsewhere. We temporarily allow index $`1`$ to simplify the basis calculation; we later require its coefficient to vanish. This does not add the undefined term $`1/(1!-1)`$ to $`S`$.

The exponent $`\lfloor n/d\rfloor`$ is chosen for its changes at multiples of $`d`$, not to remove the largest power of $`d!`$ dividing $`n!`$. Consequently, the adjacent differences below affect only sums with $`d\mid n`$. Call $`M(\lambda)`$ the moment, without assuming it positive. The remainder
``` math
\mathcal R(\lambda)=\sum_{d\ge2}\frac{V_d(\lambda)}{d!-1}
```
converges absolutely: beyond the support, $`V_d=M`$. For any $`N\ge2`$ at least as large as every supported index, the congruences just proved give
``` math
\mathcal R(\lambda)-M(\lambda)S
=\sum_{d=2}^N\frac{V_d(\lambda)-M(\lambda)}{d!-1}\in\mathbb Z.
```
Thus the weights retain an integer linear form in $`1`$ and $`S`$ while allowing $`V_2,\ldots,V_D`$ to be set to zero. We now solve those equations.

For example, $`4e_3-e_4`$ has moment zero, $`V_2=6`$ and $`V_4=23`$, with all other $`V_d`$ zero. The vector $`2e_1-e_2`$ has moment zero and only $`V_2=1`$ nonzero. Subtracting six copies of the latter therefore removes the unwanted $`V_2`$ without changing $`V_4`$. The following recursion performs this elimination at the proper divisors of each index.

<div id="res:divisor-channel-coordinates" class="theorem">

**Theorem 3** (an integer basis with prescribed weighted sums). *Set
``` math
T_n=ne_{n-1}-e_n,\qquad
U_n=T_n-\sum_{\substack{d\mid n\\2\le d<n}}W_{d,n}U_d
\quad(n\ge2).
```
Then
``` math
M(U_n)=0,\qquad V_d(U_n)=(d!-1)\mathbf1_{d=n}.
```
The vectors $`e_1,U_2,U_3,\ldots`$ form an integral basis. Every finite vector has the unique finite expansion
``` math
\begin{equation}
\lambda=M(\lambda)e_1+
\sum_{d\ge2}\frac{V_d(\lambda)-M(\lambda)}{d!-1}U_d.
\label{eq:channel-basis-expansion}
\end{equation}
```*

</div>

Lean: [divisor channel coordinates](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos68/PaperCompleteDivisorCoordinates.lean#L260).

<div class="proof">

*Proof.* The moment of $`T_n`$ is zero. The floor in $`W_{d,n}`$ changes between $`n-1`$ and $`n`$ precisely when $`d\mid n`$. Accordingly, [the $`d`$th weighted sum of $`T_n`$ vanishes unless $`d`$ divides $`n`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L65), and in full
``` math
V_d(T_n)=(d!-1)W_{d,n}\mathbf1_{d\mid n}.
```
The recursion cancels the weighted sums indexed by proper divisors, proving the two identities by induction. The columns $`e_1,T_2,\ldots,T_N`$ form a triangular integer matrix with diagonal entries $`1,-1,\ldots,-1`$. Its determinant is $`\pm1`$, so it is unimodular and its columns form a $`\mathbb Z`$-basis. The change from $`T_n`$ to $`U_n`$ is also triangular over $`\mathbb Z`$, with diagonal entries $`1`$. Thus $`e_1,U_2,\ldots,U_N`$ is a $`\mathbb Z`$-basis as well. Applying $`M`$ and each $`V_d`$ identifies its coefficients as in <a href="#eq:channel-basis-expansion" data-reference-type="eqref" data-reference="eq:channel-basis-expansion">[eq:channel-basis-expansion]</a>. For $`d`$ beyond the support, $`V_d=M`$, so no infinite sum is required. ◻

</div>

For a prime $`p\ge3`$, the recursion gives $`U_p=T_p`$: adding $`U_p`$ changes $`V_p`$ by $`p!-1`$, leaves every other $`V_d`$ unchanged, and leaves $`M`$ unchanged. The same construction works at composite indices. For example,
``` math
\begin{equation}
U_9=9e_8-e_9-5040e_2+1680e_3.
\label{res:translator}
\end{equation}
```
It has moment zero and only $`V_9`$ is nonzero. These individual adjustments need not preserve support on $`n\ge2`$: the earlier $`U_4`$ has coefficient $`-12`$ at index $`1`$. We now impose that restriction.

<a id="the-support-restriction-and-the-remainder"></a>

## The support restriction and the remainder

Fix $`D\ge2`$ and write
``` math
L_D=\operatorname{lcm}_{2\le d\le D}(d!-1),\qquad
K_D=L_De_1-\sum_{d=2}^D\frac{L_D}{d!-1}U_d.
```
The coefficients in <a href="#eq:channel-basis-expansion" data-reference-type="eqref" data-reference="eq:channel-basis-expansion">[eq:channel-basis-expansion]</a> are integers, so
``` math
\begin{equation}
V_d(\lambda)\equiv M(\lambda)\pmod{d!-1}.
\label{res:congruence}
\end{equation}
```
When $`V_2=\cdots=V_D=0`$, these congruences force $`L_D\mid M`$. Substituting $`M=tL_D`$ gives every such solution, with finitely many nonzero $`z_n`$:
``` math
\begin{equation}
V_2=\cdots=V_D=0
\quad\Longleftrightarrow\quad
\lambda=tK_D+\sum_{n>D}z_nU_n,\qquad M=tL_D.
\label{eq:low-channel-classification}
\end{equation}
```
The basis identities give $`\mathcal R(e_1)=S`$ and $`\mathcal R(U_n)=1`$. By linearity,
``` math
\begin{equation}
\mathcal R\left(tK_D+\sum_{n>D}z_nU_n\right)
=tL_D(S-H_D)+\sum_{n>D}z_n.
\label{eq:residual-transparency}
\end{equation}
```
The finite integer-difference identity shows that changing coefficients at fixed moment preserves the fractional part. A nonintegral remainder rules out $`S=a/q`$ when $`q\mid M`$. To exclude every denominator this way, each positive integer $`q`$ must divide the moment of some nonintegral remainder in the family; unbounded moments alone do not guarantee this.

Let $`a_D`$ and $`u_n`$ be the coefficients at index $`1`$ of $`K_D`$ and $`U_n`$, respectively. Requiring that coefficient to vanish gives
``` math
\begin{equation}
t a_D+\sum_{n>D}z_nu_n=0.\label{eq:support-equation}
\end{equation}
```
Consequently the attainable moments are
``` math
\begin{equation}
L_D\frac{g_D}{\gcd(g_D,a_D)}\mathbb Z,
\qquad g_D=\gcd\{u_n:n>D\}.
\label{eq:attainable-moment-ideal}
\end{equation}
```
Indeed, finite integer combinations of the $`u_n`$ form $`g_D\mathbb Z`$. The positive generator is attained because a gcd of any integer family is a finite integer combination of its members. An attaining vector is primitive: division by a common coefficient factor greater than one would preserve all zero weighted sums and produce a smaller positive moment. For odd $`n`$, $`u_n=0`$ by induction. For a prime $`p`$, the sole nonzero proper-divisor contribution at $`2p`$ gives $`u_{2p}=-2(2p)!/2^p\ne0`$. Every tail thus contains a nonzero coefficient, so $`g_D>0`$.

<a id="computing-the-gcd-from-finitely-many-coefficients."></a>

#### Computing the gcd from finitely many coefficients.

The scalar recurrence is
``` math
u_2=2,\qquad
u_n=-\sum_{\substack{d\mid n\\2\le d<n}}W_{d,n}u_d\quad(n>2).
```
To prove that an integer $`g`$ divides every $`u_n`$ with $`n>D`$, use induction in this recurrence. Once the terms with $`D<d<n`$ are divisible by $`g`$, only $`d\le D`$ need further consideration. For these terms we use
``` math
k!\mid W_{d,dk}=\frac{(dk)!}{(d!)^k}.
```
The quotient by $`k!`$ counts partitions into $`k`$ unordered blocks of size $`d`$.

<div id="res:finite-channel-moment-certificate" class="theorem">

**Theorem 4** (a finite formula for the gcd). *Choose a prime $`\ell`$ with $`D/2<\ell\le D`$ and put $`H=D(2\ell-1)`$. Then
``` math
g_D=\gcd(u_{D+1},\ldots,u_H),\qquad H<2D^2.
```*

</div>

Lean: [finite channel moment certificate](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos68/PaperCompleteMomentHorizon.lean#L252), [finite channel moment certificate eq](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos68/PaperCompleteMomentHorizon.lean#L260).

<div class="proof">

*Proof.* Since $`D<2\ell\le D(2\ell-1)=H`$, the finite interval includes the nonzero term $`u_{2\ell}=-(2\ell)!/2^{\ell-1}`$. Thus its gcd $`g`$ is positive and $`g\mid(2\ell)!`$. For $`n>H`$ and a divisor $`d\le D`$, the integer $`n/d`$ is at least $`2\ell`$. The equal-block divisibility above gives $`g\mid(n/d)!\mid W_{d,n}`$. Every term of the recurrence with $`d\le D`$ is therefore divisible by $`g`$. Strong induction handles the remaining divisors $`D<d<n`$, whose coefficients are already divisible by $`g`$. Thus $`g`$ divides the entire tail. Finally $`H\le D(2D-1)<2D^2`$.

This does not justify replacing $`H`$ by $`2D`$. ◻

</div>

Bertrand’s postulate supplies $`\ell`$ for every $`D\ge3`$, and $`\ell=2`$ works for $`D=2`$. This finite calculation determines allowable moments, not the nonintegrality of their remainders.

<div id="res:bandbreakpoint" class="theorem">

**Theorem 5** (constant values of the floor in the weights). *Let $`\lambda`$ be a finitely supported integer vector, let $`d\ge2`$ and $`k\ge0`$ be integers, and suppose each index $`n`$ in its support satisfies $`kd\le n<(k+1)d`$. Then
``` math
M(\lambda)=(d!)^k V_d(\lambda).
```
In particular, support in $`[d,2d)`$ and $`V_d(\lambda)=0`$ force $`M(\lambda)=0`$. If all supported indices are at least $`d`$, $`V_d(\lambda)=0`$ and $`M(\lambda)\ne0`$, some supported index is at least $`2d`$.*

</div>

Lean: [supported quotient band](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos68/PaperCompleteSupportedBands.lean#L24), [supported first band cancellation](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos68/PaperCompleteSupportedBands.lean#L42), [supported breakpoint escape](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos68/PaperCompleteSupportedBands.lean#L51).

<div class="proof">

*Proof.* On the stated interval $`\lfloor n/d\rfloor=k`$, so $`n!=(d!)^kW_{d,n}`$. Sum against $`\lambda_n`$; the final assertion follows by contraposition from the case $`k=1`$. ◻

</div>

For example, at $`D=4`$ the minimum moment is $`1380`$, attained by $`12K_4+253U_6-11U_8`$. The inputs to <a href="#eq:attainable-moment-ideal" data-reference-type="eqref" data-reference="eq:attainable-moment-ideal">[eq:attainable-moment-ideal]</a> are $`L_4=115`$, $`a_4=-55`$ and $`g_4=60`$. The last equality uses the full-tail divisibility $`\operatorname{lcm}(1,\ldots,n)\mid u_n`$ together with $`23u_6-u_8=60`$. <span id="eq:channel-lcm-envelope" label="eq:channel-lcm-envelope"></span> The long record, §5.1, proves that divisibility by Legendre’s formula, checks the attaining vector, and gives the different minimum $`4140`$ when support is restricted to $`n\le6`$.

<a id="sec:translator"></a>

# How cancellation forces a large moment

On the actual support $`n\ge2`$, one has the stronger congruence $`12\mid M-2V_2`$. For $`n=2,3`$, $`n!=2W_{2,n}`$. For $`n\ge4`$, both $`n!`$ and $`2W_{2,n}`$ are divisible by 12: writing $`n=2k`$ or $`2k+1`$, $`W_{2,2k}=k!\prod_{j=1}^k(2j-1)`$ is divisible by 6 for $`k\ge2`$. Since every $`d!-1`$ is coprime to 6, vanishing of $`V_2,\ldots,V_D`$ implies
``` math
\begin{equation}
12L_D\mid M.\label{eq:twelve-lcm}
\end{equation}
```
This is a necessary divisor, not the minimum: the long record, §5.1, gives examples attaining $`12L_D`$ at $`D=2,3`$ but proves that the minimum at $`D=6`$ is $`24L_6`$. It does not by itself cover every fixed denominator either: $`L_D`$ is coprime to $`3`$, so $`9\nmid12L_D`$ for every $`D`$.

<a id="growth-of-the-compulsory-factor"></a>

## Growth of the compulsory factor

The divisibility $`L_D\mid M`$ forces any nonzero moment with $`V_2=\cdots=V_D=0`$ to be large. To estimate it, take a block of denominators near $`N`$: their product is large, and pairwise gcds bound how much can be lost on passing to the lcm. This gives
``` math
\begin{equation}
\liminf_{N\to\infty}\frac{\log L_N}{N^{3/2}\log N}
\ge\frac{2\sqrt2}{3}.\label{res:lcm-growth}
\end{equation}
```
This bounds a common denominator before reduction, not a denominator of $`S`$. Multiplying $`i!-1`$ by $`j!/i!`$ and subtracting $`j!-1`$ gives $`\gcd(i!-1,j!-1)\mid j!/i!-1`$. For positive integers $`x_i`$, the divisibility $`\prod_i x_i\mid\operatorname{lcm}(x_i)\prod_{i<j}\gcd(x_i,x_j)`$ follows prime by prime: after ordering valuations, each except the maximum occurs at least once among the pairwise minima. On a terminal block of $`k`$ terms, this inequality and $`\gcd(i!-1,j!-1)\mid j!/i!-1`$ give
``` math
\log L_N\ge\sum_{n=N-k+1}^N\log(n!-1)
-\binom{k+1}{3}\log N.
```
The product contributes about $`kN\log N`$, whereas the gcd loss is of order $`k^3\log N`$. Balancing them suggests $`k`$ of order $`\sqrt N`$. Fix $`\alpha>0`$ and take $`k=\lfloor\alpha\sqrt N\rfloor`$. Dividing the inequality by $`N^{3/2}\log N`$ and letting $`N\to\infty`$ gives $`\liminf \log L_N/(N^{3/2}\log N)\ge\alpha-\alpha^3/6`$. The choice $`\alpha=\sqrt2`$ proves <a href="#res:lcm-growth" data-reference-type="eqref" data-reference="res:lcm-growth">[res:lcm-growth]</a>; the error estimates are given in the long record, §2.

This lower bound does not provide a small positive scaled tail. For $`N\ge3`$, any common divisor of $`(N-1)!-1`$ and $`N!-1`$ divides $`N-1`$ by subtraction, and is coprime to $`N-1`$ because $`N-1\mid(N-1)!`$. Thus the two denominators are coprime. Since $`S-H_N>1/((N+1)!-1)`$,
``` math
L_N(S-H_N)>
 \frac{((N-1)!-1)(N!-1)}{(N+1)!-1}\longrightarrow\infty.
```
Even two terms therefore obstruct clearing by the full common denominator; <a href="#res:lcm-growth" data-reference-type="eqref" data-reference="res:lcm-growth">[res:lcm-growth]</a> gives the stronger quantitative cost.

<a id="sec:compressed-kernel"></a>

## Solutions supported on an arithmetic progression

For $`D,r\ge2`$ and a positive multiple $`\ell`$ of $`2,\ldots,D`$, there is a primitive integer vector supported on $`r,r+\ell,\ldots,r+(D-1)\ell`$. With $`N=r+(D-1)\ell`$, it satisfies
``` math
V_2=\cdots=V_D=0,\qquad
 M=N!\prod_{d=2}^D\bigl(1-(d!)^{-\ell/d}\bigr)>0,
 \qquad (\lfloor\sqrt N/2\rfloor+1)!\mid M.
```
The long record, §5, paragraph “A primitive solution on an arithmetic progression”, constructs the coefficients from a polynomial with prescribed roots and proves integrality and primitivity by a multinomial count. Thus $`N\ge4(q-1)^2`$ guarantees $`q\mid M`$ for each positive integer $`q`$, including for denominators increasing with $`N`$. What remains unproved is nonintegrality of the corresponding remainders; the divisibility and the successful comparison must concern the same vector.

<a id="sec:prime-pole"></a>

# Cancellation in a reduced prefix

A large common denominator can shrink on addition: $`1/3+1/15=2/5`$ removes the prime $`3`$, whereas $`1/9+1/45=2/15`$ only lowers its exponent. Write $`v_q(a)`$ for the exponent of the prime $`q`$ in a positive integer $`a`$, and $`\operatorname{den}(x)`$ for a rational number’s positive reduced denominator.

Louwsma and Martino give a valuation formula for an elementary symmetric sum \[louwsma-martino, Lemma 4.1, p. 10\]. Dividing that sum by the product of its arguments gives the reciprocal-sum test below; we prove it directly for $`n!-1`$. Put $`L_M=\operatorname{lcm}_{2\le n\le M}(n!-1)`$ and $`A_M=\sum_{n=2}^M L_M/(n!-1)`$. For a prime $`q`$ with attained maximum $`e=\max_{2\le n\le M}v_q(n!-1)>0`$, set
``` math
I_{q,e}(M)=\{n\in[2,M]:v_q(n!-1)=e\},\qquad
R_{q,e}(M)=\sum_{n\in I_{q,e}(M)}
\left(\frac{n!-1}{q^e}\right)^{-1}\pmod q.
```
After multiplication by $`L_M`$, all lower-valuation terms vanish modulo $`q`$. Hence
``` math
A_M\equiv (L_M/q^e)R_{q,e}(M)\pmod q,
```
and $`L_M/q^e`$ is a unit. Consequently
``` math
\begin{equation}
v_q(\operatorname{den}H_M)=e
\quad\Longleftrightarrow\quad R_{q,e}(M)\ne0\pmod q.
\label{eq:prime-pole-survival}
\end{equation}
```
The equivalence, with the maximum and its attainment taken from the actual prefix lcm, is [maximal prime power survival](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompletePrimePole.lean#L118).

Reduction of $`H_M=A_M/L_M`$ gives $`v_q(\operatorname{den}H_M)=\max\{0,e-v_q(A_M)\}`$. A zero residue in <a href="#eq:prime-pole-survival" data-reference-type="eqref" data-reference="eq:prime-pole-survival">[eq:prime-pole-survival]</a> therefore lowers the exponent; complete cancellation requires $`v_q(A_M)\ge e`$. For $`e=1`$ these conditions coincide, but for $`e>1`$ they need not.

A unique maximal exponent survives because its residue sum has one nonzero term. For repeated maxima, cancellation does occur in the actual sequence. At $`M=138`$, the maximal $`139`$-exponent occurs at $`69,122,137`$, with cofactor residues $`6,49,73`$. The exact modular scan gives
``` math
6^{-1}+49^{-1}+73^{-1}=0\pmod{139}.
```
The scan for $`2593`$ also gives a zero reciprocal sum; its indices and cofactor residues are recorded in the long paper, §1. All attained exponents in these two examples are one, so each prime disappears completely. The cancellations already hold at indices $`137`$ and $`2591`$, respectively, and persist thereafter. For a prime $`q\ge3`$, Wilson’s theorem gives $`(q-1)!-1\equiv-2\pmod q`$, and $`n!-1\equiv-1\pmod q`$ for $`n\ge q`$. Thus no summand after index $`q-2`$ can change the prime’s exponent in the reduced denominator; the general proof is in the long record, §1. This concerns partial sums, not a hypothetical denominator of $`S`$. Survival still needs to be combined with a bound for the real tail.

<a id="sec:projection"></a>

# Comparing the tail with the distance to an integer

We return to the integer-gap argument of §<a href="#sec:problem" data-reference-type="ref" data-reference="sec:problem">1</a>, now choosing a scale that clears every prime-power level shared by two summand denominators. Each remaining prime then occurs in just one scaled denominator and cannot cancel. This sufficient choice may exceed what cancellation in the sum requires. Including $`(p-1)!`$ ensures that the scale eventually absorbs each fixed rational denominator. For an integer parameter $`p\ge3`$, not necessarily prime, write $`d_n=n!-1`$ and put
``` math
F_p=(p-1)!,\quad
D_p=\operatorname{lcm}_{2\le i<j\le2p-1}\gcd(d_i,d_j),
```
``` math
C_p=\operatorname{lcm}(F_p,D_p),\quad
L_p^{\rm blk}=\operatorname{lcm}(F_p,d_2,\ldots,d_{2p-1}),
```
``` math
R_p=L_p^{\rm blk}/C_p,\quad
T_p=\sum_{n=2}^{2p-1}L_p^{\rm blk}/d_n,\quad
\rho_p=(-T_p)\bmod R_p.
```
For a prime dividing $`R_p`$, the largest exponent among the $`d_n`$ exceeds both the second-largest exponent and the exponent in $`F_p`$. It is attained at exactly one index. Reducing $`T_p`$ modulo that prime leaves only the term at that index, which is a unit. Thus $`\gcd(T_p,R_p)=1`$ and $`0<\rho_p<R_p`$ whenever $`R_p>1`$.

Thus $`R_p=\operatorname{den}(C_pH_{2p-1})`$: it is the reduced denominator of the scaled prefix, not generally of $`H_{2p-1}`$. No coprimality of $`C_p`$ and $`R_p`$ is required. For $`R_p>1`$, the gap from $`T_p/R_p`$ to the next integer is $`\rho_p/R_p`$. For $`R_p=1`$, the prefix is integral and that strict gap is $`1`$, although $`\rho_p=0`$.

For $`p=3`$, the denominators $`1,5,23,119`$ are pairwise coprime, so $`D_3=1`$ and $`C_3=2`$. Direct calculation gives
``` math
C_3H_5=\frac{34264}{13685},\qquad
\frac{\rho_3}{R_3}=\frac{6791}{13685}.
```
The tail bound used below gives $`C_3(S-H_5)<7/1080<6791/13685`$, so this block satisfies the required comparison. One block is not enough: the argument needs arbitrarily large $`p`$ to ensure that any fixed rational denominator eventually divides $`F_p`$.

<div id="res:global-complementary-criterion" class="proposition">

**Proposition 6** (a sufficient tail inequality). *If arbitrarily large natural parameters $`p\ge3`$ satisfy
``` math
\begin{equation}
R_p>1,\qquad
(2p+1)L_p^{\rm blk}<2p^2(2p-1)!\rho_p,
\label{eq:global-complementary-target}
\end{equation}
```
then $`S`$ is irrational.*

</div>

Lean: [global complementary criterion nat](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos68/PaperCompleteExisting.lean#L154).

<div class="proof">

*Proof.* Suppose $`S=a/q`$ with $`q>0`$, and choose a parameter in the hypothesis with $`p>q`$. Then $`q\mid F_p\mid C_p`$, so $`C_pS`$ is an integer strictly above $`C_pH_{2p-1}`$. Hence
``` math
C_p(S-H_{2p-1})\ge\frac{\rho_p}{R_p}.
```
But $`1/(n!-1)<2/n!`$ for $`n\ge2p`$ and the geometric majorant with ratio $`1/(2p+1)`$ give
``` math
C_p(S-H_{2p-1})
 <\frac{(2p+1)C_p}{2p^2(2p-1)!}
 <\frac{\rho_p}{R_p},
```
where the last inequality follows by rearranging <a href="#eq:global-complementary-target" data-reference-type="eqref" data-reference="eq:global-complementary-target">[eq:global-complementary-target]</a> and using $`L_p^{\rm blk}=C_pR_p`$. This is a contradiction. ◻

</div>

Under $`R_p>1`$ we have $`\rho_p>0`$, so logarithms are defined. Dividing the strict inequality by $`R_p`$ and by $`F_p=(p-1)!`$ gives the equivalent logarithmic comparison
``` math
\begin{equation}
\log\frac{C_p}{(p-1)!}-\log\frac{\rho_p}{R_p}
<\log\frac{2p^2(2p-1)!}{(2p+1)(p-1)!}.
\label{eq:joint-loss-budget}
\end{equation}
```
The right side is $`p\log p+(2\log2-1)p+O(\log p)`$.

The hypothesis compares a scaled positive tail with the actual gap to the next integer. If $`\rho_p/R_p\ge1/2`$, the logarithmic cost of that gap is at most $`\log2`$. If $`\rho_p=1`$, the gap is only $`1/R_p`$ and the cost is $`\log R_p`$. Coprimality permits both cases: it proves positivity, not a uniform lower bound. No unbounded family satisfying the displayed comparison is established here. The factor $`C_p/(p-1)!`$ and the gap $`\rho_p/R_p`$ must be controlled at the same indices. Selected-prime and joint-mean variants are recorded in the appendix and proved in the long paper, §§4 and 7; neither is needed for this proposition.

<a id="sec:open"></a>

# The remaining real comparison

<span id="sec:plateau" label="sec:plateau"></span>

The exact target remains the [criterion using the next integer](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L1090):
``` math
\begin{equation}
(\forall B)(\exists m>B)\ m\nmid Z_m.
\label{eq:canonical-open-target}
\end{equation}
```
For a vector $`\lambda`$ with $`V_2=\cdots=V_D=0`$ and $`M>0`$, choose a cutoff $`N\ge D`$ at least as large as every supported index. Write
``` math
A_N=\sum_{d=D+1}^N\frac{V_d(\lambda)}{d!-1},\qquad
\mathcal R(\lambda)=A_N+M\sum_{d>N}\frac1{d!-1}.
```
The sufficient strict comparison is
``` math
\begin{equation}
\frac{2M}{(N+1)!-1}<\lfloor A_N\rfloor+1-A_N.
\label{eq:signed-block-gap}
\end{equation}
```
It puts the remainder strictly between $`A_N`$ and the next integer. The finite integer-difference identity proved in §<a href="#sec:channels" data-reference-type="ref" data-reference="sec:channels">2</a> then excludes $`S=a/q`$ for every $`q\mid M`$. For the progression vectors of §<a href="#sec:compressed-kernel" data-reference-type="ref" data-reference="sec:compressed-kernel">3.2</a>, every fixed $`q`$ divides $`M`$ once their support endpoint is large enough. Their moment formula also gives $`0<M<N!`$, so at that endpoint
``` math
0<M(S-H_N)<\frac{2M}{(N+1)!-1}<\frac2N.
```
Thus the tested upper bound already tends to zero along this family. The missing step is comparison with the gap on the right of <a href="#eq:signed-block-gap" data-reference-type="eqref" data-reference="eq:signed-block-gap">[eq:signed-block-gap]</a>, which may also tend to zero. Smallness of the omitted tail alone does not prove the strict comparison. The finite signed sum $`A_N`$ cannot be omitted. An integral $`A_N`$, even a negative one, leaves a gap of $`1`$; a value just below an integer leaves a much smaller gap. Positivity is required of $`M`$, not of $`A_N`$.

The cutoff need not be the largest supported index. For the vector $`-6e_2+e_4`$, with $`D=2`$ and moment $`12`$, the comparison fails at $`N=4`$: its gap is $`9/115`$, smaller than $`24/119`$. At $`N=5`$, the gap is $`13376/13685`$, larger than the new bound $`24/719`$, so the same vector succeeds. This illustrates a choice of truncation, not an improvement of either denominator exclusion.

For a fixed vector, <a href="#eq:signed-block-gap" data-reference-type="eqref" data-reference="eq:signed-block-gap">[eq:signed-block-gap]</a> holds at every sufficiently large cutoff exactly when $`\mathcal R(\lambda)`$ is nonintegral. In that case $`A_N\uparrow\mathcal R(\lambda)`$ and its gap is eventually bounded below by $`\lfloor\mathcal R(\lambda)\rfloor+1-\mathcal R(\lambda)>0`$. For an integral remainder the eventual gap is instead the omitted tail itself, smaller than the tested upper bound. Increasing $`N`$ changes neither $`M`$ nor denominator coverage. The long record, §5.1, gives the full endpoint argument; its further numerical examples are in Appendix B.6.

<a id="sec:nogo"></a>

#### The limit of short truncations.

<span id="sec:adjacent-unit-no-go" label="sec:adjacent-unit-no-go"></span> As $`D\to\infty`$, the comparison <a href="#eq:signed-block-gap" data-reference-type="eqref" data-reference="eq:signed-block-gap">[eq:signed-block-gap]</a> cannot hold at cutoffs $`N=D+O(1)`$ for vectors with $`M>0`$ and $`V_2=\cdots=V_D=0`$. Indeed, the compulsory divisibility $`L_D\mid M`$ and <a href="#res:lcm-growth" data-reference-type="eqref" data-reference="res:lcm-growth">[res:lcm-growth]</a> give
``` math
\frac{2|M|}{(N+1)!-1}\longrightarrow\infty,
```
whereas the right side of <a href="#eq:signed-block-gap" data-reference-type="eqref" data-reference="eq:signed-block-gap">[eq:signed-block-gap]</a> is at most one. Thus the comparison requires larger cutoffs. This is a support restriction only when the cutoff must equal the largest supported index; it does not exclude a vector with narrower support evaluated later.

Large denominator valuations alone also leave the gap to the next integer uncontrolled. For a fixed prime $`q`$, the reduced fractions $`1-1/q^e`$ have denominator $`q^e`$, but their gaps to the next integer are $`1/q^e\to0`$.

<a id="sec:finite"></a>

# Computation records

An exact non-unit carry at the prime index $`67`$ already forces [every rational denominator to be at least $`67`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L940). The exact GMP carry certificate covers $`3\le m\le300000`$. Its unit carries occur at
``` math
52,\ 591,\ 1030,\ 1407,\ 1438,\ 2164,\ 4258,\ 10991,\ 21236.
```
In particular $`b_{300000}\ne1`$, giving the exclusion proved in <a href="#eq:finite-denominator-consumer" data-reference-type="eqref" data-reference="eq:finite-denominator-consumer">[eq:finite-denominator-consumer]</a>. This is a reported exact computation outside Lean. The long record, §6, transcribes its driver, backend and payload digests and distinguishes the smaller replay through $`4000`$. The original packet supplies the report, not the full GMP executable and payload; this prose revision neither authenticates those files nor repeats the full run.

The continued-fraction enclosure and its denominator implication are proved in §<a href="#sec:problem" data-reference-type="ref" data-reference="sec:problem">1</a>. The exact replay gives $`N=7054`$, enclosure width $`7053`$ at scale $`2^{80000}`$, and $`23449`$ common partial quotients. Its integer algorithm and receipt are recorded in the long paper, §6. These two finite calculations are distinct from an unbounded family of non-unit carries or successful remainder comparisons.

<a id="sec:companion-orbit"></a>

# A criterion using the factorial digits of $`S-e+2`$

The termwise identity
``` math
\frac1{n!-1}=\frac1{n!}+\frac1{n!(n!-1)}
```
separates the familiar factorial series for $`e-2`$ from the number
``` math
C=\sum_{n\ge2}\frac1{n!(n!-1)}.
```
Absolute convergence gives
``` math
\begin{equation}
C+(e-2)=S.\label{eq:companion-decomposition}
\end{equation}
```
For $`m\ge2`$, define the canonical factorial digit
``` math
d_m(C)=\lfloor m!C\rfloor-m\lfloor(m-1)!C\rfloor,
 \qquad 0\le d_m(C)<m.
```
For $`m\ge3`$, the congruence in the next theorem says exactly that $`d_m(C)=m-2`$.

The floor convention excludes the alternative expansion with an eventually maximal tail. For example,
``` math
\frac12=\frac1{2!}=\sum_{m\ge3}\frac{m-1}{m!},
```
but the canonical digits of $`1/2`$ are $`d_2=1`$ and $`d_m=0`$ for $`m\ge3`$. With this convention, Cantor’s factorial expansion \[cantor1869\] represents a rational number exactly when its digits eventually vanish. For $`C=S-e+2`$, the following criterion instead requires eventual digit $`m-2`$: adding back $`e-2`$ supplies the missing $`1/m!`$ at each index.

<div id="res:companion-orbit-rationality-boundary" class="theorem">

**Theorem 7** (rationality and factorial residues). *The following statements are equivalent:*

1.  *$`S\in\mathbb Q`$;*

2.  *$`(\lfloor m!C\rfloor+2)\bmod m=0`$ for every sufficiently large $`m`$.*

*Consequently,
``` math
\begin{equation}
 S\notin\mathbb Q
 \quad\Longleftrightarrow\quad
 (\forall B)(\exists m>B)\;
   (\lfloor m!C\rfloor+2)\bmod m\ne0 .
 \label{eq:companion-cofinal}
\end{equation}
```*

</div>

Lean: [companion orbit boundary](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos68/PaperCompleteExisting.lean#L27).

<div class="proof">

*Proof.* First suppose $`S=a/q`$ with $`q>0`$, and take $`m`$ so large that $`q\mid(m-1)!`$. Write
``` math
E_m=m!\sum_{2\le n\le m}\frac1{n!}.
```
Then $`E_m`$ is an integer and the omitted scaled tail satisfies $`0<m!\sum_{n>m}1/n!<1`$. Also, $`m!S`$ is an integer divisible by $`m`$. Multiplying <a href="#eq:companion-decomposition" data-reference-type="eqref" data-reference="eq:companion-decomposition">[eq:companion-decomposition]</a> by $`m!`$ therefore gives
``` math
\lfloor m!C\rfloor=m!S-E_m-1.
```
Every summand of $`E_m`$ except the endpoint $`m!/m!=1`$ is divisible by $`m`$. Thus $`E_m\equiv1\pmod m`$ and $`\lfloor m!C\rfloor\equiv-2\pmod m`$.

Conversely, assume the displayed congruence from some index onward. Since $`0\le d_m(C)<m`$, for $`m\ge3`$ it is equivalent to
``` math
d_m(C)=m-2.
```
Choose $`N`$ beyond the exceptional indices. The canonical factorial expansion of $`C`$ then has the form
``` math
C=\lfloor C\rfloor+
   \sum_{m=2}^{N}\frac{d_m(C)}{m!}+
   \sum_{m>N}\frac{m-2}{m!}.
```
Adding $`e-2=\sum_{m\ge2}1/m!`$ and using the telescoping identity
``` math
\sum_{m>N}\frac{m-1}{m!}
 =\sum_{m>N}\left(\frac1{(m-1)!}-\frac1{m!}\right)
 =\frac1{N!}
```
gives
``` math
S=\lfloor C\rfloor+
   \sum_{m=2}^{N}\frac{d_m(C)+1}{m!}+\frac1{N!},
```
which is rational. Negating the eventual statement yields the cofinal formulation above. ◻

</div>

<div id="bdry:companion-orbit-nonconcentration" class="remark">

*Remark 1*. It remains to prove that the displayed congruence fails at arbitrarily large indices for this particular $`C`$. Any one finite list of failures, however long, is not enough. The theorem is an equivalence, not an estimate for the distribution of these residues.

</div>

<a id="sec:digits"></a>

## When subtracting the tail changes a floor

The digit uses $`C`$, but the carry uses a partial sum. Their floors can differ when the omitted tail crosses an integer. Write $`\{x\}=x-\lfloor
x\rfloor`$ for the fractional part and $`\mathbf1`$ for an indicator, and put
``` math
\delta_m=m!\sum_{n>m}\frac1{n!(n!-1)},\qquad
\sigma_m=\mathbf1_{\{\{m!C\}<\delta_m\}}.
```
Since $`0<\delta_m<1/((m+1)!-1)<1`$ by comparison with $`m!\sum_{n>m}1/n!<1`$, subtracting this tail lowers a floor by exactly $`\sigma_m`$. Hence
``` math
Z_m=m!\sum_{n=2}^m\frac1{n!}+\lfloor m!C\rfloor+1-\sigma_m.
```
The first term is an integer, and its difference from $`m`$ times the preceding one is $`1`$. Substitution in the definition of $`b_m`$ therefore gives, for $`m\ge3`$,
``` math
\begin{equation}
b_m=m-1-d_m(C)+\sigma_m-m\sigma_{m-1}.
\label{eq:companion-wrap}
\end{equation}
```
Equality $`\{m!C\}=\delta_m`$ leaves an integral prefix and gives no correction. A fractional part smaller than the tail crosses an integer, however small the tail is; neither indicator can simply be omitted.

<a id="app:sources"></a>

# Guide to the formal sources

The proofs above can be read without following the Lean links. Each link retains the commit and path cited in the original manuscript; the links do not assert that all the modules were compiled together.

The source packet for this revision contains the public snapshot `6b78209ab63a8c643281115f8628a3be79ff7ec7` and the separate release `52f29ad173b04e3bac941b3663f2b9aebe5de0bb`. Its declaration index distinguishes recorded checked declarations, source files outside the recorded build, and release-only declarations. In particular, `PaperCompleteExisting` is present but outside the recorded checked build, as is the candidate finite-size certificate. Source presence is not a proof-checking receipt.

The packet’s build receipt points back to a successful Lean build at an earlier commit; the Lean build step at the supplied public pin was skipped. No Lean build or axiom audit was run for this prose revision. Statements below described as checked refer to the supplied source and build records, not to a new compilation. Likewise, the large carry census is a recorded integer computation, not a Lean theorem established by this revision. The continued-fraction enclosure and the small numerical examples can be checked independently with integer arithmetic; the rewrite notes record which such checks were repeated.

<a id="source-counterparts-of-the-main-statements."></a>

#### Source counterparts of the main statements.

The following links identify the declarations corresponding to the numbered results and selected formulas. The source and build qualifications above apply to every entry.

Theorem <a href="#res:companion-orbit-rationality-boundary" data-reference-type="ref" data-reference="res:companion-orbit-rationality-boundary">7</a>. The formal statement of the equivalence is [the factorial-residue equivalence](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteExisting.lean#L29).

Theorem <a href="#res:carry-characterization" data-reference-type="ref" data-reference="res:carry-characterization">2</a>. A single source declaration records [both carry equivalences](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteExisting.lean#L47). The equivalent condition [$`m\nmid Z_m`$ at arbitrarily large indices](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L1090) has the same unbounded quantifier.

Theorem <a href="#res:divisor-channel-coordinates" data-reference-type="ref" data-reference="res:divisor-channel-coordinates">3</a>. The corresponding Lean statement gives [the integer basis and its coefficient formula](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteDivisorCoordinates.lean#L260).

Equation <a href="#res:translator" data-reference-type="eqref" data-reference="res:translator">[res:translator]</a>. The source records [the explicit vector $`U_9`$](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteSupplementary.lean#L17) and [its weighted sums](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteSupplementary.lean#L45).

Congruence <a href="#res:congruence" data-reference-type="eqref" data-reference="res:congruence">[res:congruence]</a>. The source states this as [divisibility of $`V_d(\lambda)-M(\lambda)`$ by $`d!-1`$](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteSupplementary.lean#L53).

Theorem <a href="#res:finite-channel-moment-certificate" data-reference-type="ref" data-reference="res:finite-channel-moment-certificate">4</a>. The linked Lean statement gives [the finite formula for the gcd](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteMomentHorizon.lean#L252).

Theorem <a href="#res:bandbreakpoint" data-reference-type="ref" data-reference="res:bandbreakpoint">5</a>. The linked sources give [the factorisation for $`k\ge 0`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L71), [its zero-moment consequence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L91), [the case $`d\le n<2d`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L101), and [the support conclusion](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L130).

Proposition <a href="#res:global-complementary-criterion" data-reference-type="ref" data-reference="res:global-complementary-criterion">6</a>. The [formal counterpart](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteExisting.lean#L156) states the same implication for natural-number parameters.

<a id="what-the-source-records-establish."></a>

#### What the source records establish.

The identities for adjacent coefficient differences, the recursion that isolates one weighted sum, the vanishing moment, the individual values $`V_d`$, and the factor $`12`$ have formal proofs in [the integer basis for the weighted sums](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/DivisorChannelBasis.lean). The unique integral basis expansion, attainable-moment formula and construction on an arithmetic progression are ordinary proofs, described in [the integer basis for the weighted sums](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/DivisorChannelBasis.md) and, for the grid construction, in [the primitive vector on an arithmetic progression](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompressedPrimitiveChannelKernel.md). The quadratic stopping theorem is checked in [the quadratic stopping bound for the gcd](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteMomentHorizon.lean), together with the scalar recurrence, the equal-block divisibility and the explicit coefficient at twice a prime used in its proof. The divisibility $`\operatorname{lcm}(1,\ldots,n)\mid u_n`$ and the depth-$`4`$ moment $`1380`$ have ordinary proofs with exact checks in [exact checks of the moment divisibility](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/scripts/check_moment_saturation.py). Checks for the finite gcd calculation are in [the finite gcd verification script](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/scripts/check_finite_source.py). The inherited generic lemmas in [gcd lemmas with an assumed divisibility](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/TailIdealCertificate.lean) assume that divisibility; they do not prove it for the factorial coefficients. The growth liminf is the ordinary asymptotic consequence of the finite terminal-block inequality cited above, and Lean checks it as [the liminf bound for the common denominator](https://github.com/wcook04/plectis-erdos/blob/0b500c7cf8e8bb7ae343484378df02f277fb8194/lean/ErdosProblems/Erdos68/PaperCompleteLiminf.lean#L42). The checked counterpart of the growth liminf in the public Lean release `wcook04/plectis-erdos-lean` at commit `52f29ad1` is identified in the next source paragraph for <a href="#res:lcm-growth" data-reference-type="eqref" data-reference="res:lcm-growth">[res:lcm-growth]</a>.

Formal proof checking does not assess external novelty or the significance of the remaining hypothesis. The complete source register, receipts and failed-route calculations belong to the long record.

<a id="formal-sources-for-the-common-denominator-bound."></a>

#### Formal sources for the common-denominator bound.

The formal sources for <a href="#res:lcm-growth" data-reference-type="eqref" data-reference="res:lcm-growth">[res:lcm-growth]</a> include [the liminf bound for the common denominator](https://github.com/wcook04/plectis-erdos/blob/0b500c7cf8e8bb7ae343484378df02f277fb8194/lean/ErdosProblems/Erdos68/PaperCompleteLiminf.lean#L42). The separate public Lean release `wcook04/plectis-erdos-lean` at commit `52f29ad1` states the bound <a href="#res:lcm-growth" data-reference-type="eqref" data-reference="res:lcm-growth">[res:lcm-growth]</a>, with the least common multiple of $`n!-1`$ over $`2\le n\le N`$ as the common denominator, as `common_denominator_growth` and in extended real form as `common_denominator_growth_liminf`. The statements are in the Comparator challenge file [`PalomarCorpus/E68/Challenge.lean`](https://github.com/wcook04/plectis-erdos-lean/blob/52f29ad173b04e3bac941b3663f2b9aebe5de0bb/PalomarCorpus/E68/Challenge.lean#L249), where the proofs are left as `sorry`. The solution file [`Solutions/PalomarCorpus/E68/CommonDenominatorGrowth.lean`](https://github.com/wcook04/plectis-erdos-lean/blob/52f29ad173b04e3bac941b3663f2b9aebe5de0bb/Solutions/PalomarCorpus/E68/CommonDenominatorGrowth.lean#L17) closes both by transfer from `common_denominator_growth` in `ErdosProblems/Erdos68/PaperCompleteAsymptotics.lean` and `common_denominator_growth_liminf` in `ErdosProblems/Erdos68/PaperCompleteLiminf.lean` of the same release. The supplied release record reports that a Linux replay of Palomar’s Comparator stage accepted the entry with the Lean kernel and with NanoDa ([run 34782407633](https://github.com/wcook04/plectis-erdos-lean/actions/runs/34782407633)). This bound concerns a common denominator of the partial sums. It is not a lower bound for the denominator of the series under a rationality assumption. The finite-block inequality has a separate Lean source, [the inequality for a terminal block](https://github.com/wcook04/plectis-erdos/blob/d788dd4b8c59f2246000f2ed98fffb8a5e8ac72e/lean/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L524-L529).

<a id="links-to-individual-statements."></a>

#### Links to individual statements.

The links below are grouped by the calculation they support. Their original commit, file, line and declaration targets are unchanged; the separate build qualifications above still apply.

*Successive partial sums and carries:* [the condition for two consecutive unit carries](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L148); [the two denominator-reduction factors telescope](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L215); [the denominator after two steps](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L243); [the offset equals the later numerator times the reduction factors](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L337); [denominator at least the carry index](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L876); [denominator at least $`67`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L940); [criterion using the next integer](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L1090); [cofinal non-unit carries imply irrationality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L953); [the interval condition at the lower endpoint](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L6099).

*Selected factors and determinant remainders:* [comparison using the factors $`1`$ and a selected prime](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L4766); [the remainder equals a determinant times $`S`$, up to an integer](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/PrimeUnitTranslator.lean#L1559).

*Finite factorial-weighted sums:* [the summand $`W_{n,m}/(n!-1)`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L34); [the weight $`W_{n,m}`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L39); [the finite sum $`\sum_{n=2}^{m}W_{n,m}/(n!-1)`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L44); [the divisor sum $`\sum_{2\le n\le m,\,n\mid m}W_{n,m}`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L49); [the factorial recurrence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L80); [the quotient when the divisor does not divide the index](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L88); [the quotient when the divisor divides the index](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L102); [the term when the divisor does not divide the index](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L129); [the term when the divisor divides the index](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L146); [the term at its own index](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L170); [the coefficient at its own index](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L179); [the recurrence for this finite sum](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L188).

*Coefficient identities:* [weights are integers](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L25); [the integer factorial weights](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L39); [the denominator-times-weight identity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L43); [the weighted sum](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L51); [the factorial-weighted moment](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L55); [the change in a weighted sum at one index](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L59); [adjacent differences affect only divisor weighted sums](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L65).

*The two-term vector:* [the vector $`2e_3-e_4`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L101); [the coefficient at index three](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L105); [the coefficient at index four](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L109); [the vanishing second weighted sum](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L112); [the moment of the two-term example](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L119); [the third weighted sum of the example](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L126); [the fourth weighted sum of the example](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L133); [the later weighted sums of the example](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L140); [the remainder expressed in terms of the tail](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L151); [the strict rational bounds for the example remainder](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L156).

*Conditional support bounds:* [a cubic lower bound for the support parameter](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L868); [exclusion of the stated eventual cubic upper bound](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L885); [the support parameter is not little-o of the cubic scale](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L905); [the finite lower bound with constant three halves](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L1084); [exclusion of an eventual upper bound with constant three halves](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L1103).

<a id="related-denominator-estimates."></a>

#### Related denominator estimates.

Shared prime-power divisibility was used to control the spacing of factorial indices by Erdős and Stewart \[erdos-stewart1976, §3, pp. 516–517\]. The subtraction in the proof of <a href="#res:lcm-growth" data-reference-type="eqref" data-reference="res:lcm-growth">[res:lcm-growth]</a> is the case $`P=-1`$ of Luca and Shparlinski’s polynomial-shift argument \[luca-shparlinski, proof of Lemma 5, p. 811\], also used by Lai \[lai, proof of Lemma 2.4, display (2.5)\]. These sources supply that subtraction, not the lcm asymptotic stated here. The extension to a fixed nonzero polynomial shift $`n!+P(n)`$ uses an eventual cutoff for positivity and nonvanishing \[lai, Lemma 2.1\], attributed there to Luca and Shparlinski \[luca-shparlinski\]. Its proof, including the uniform choice of cutoff and the lower-order gcd loss, is in the long record, §2. The non-polynomial shift $`n!+2^n-1`$ uses a different, three-index elimination \[luca-shparlinski-exp, Lemmas 2.1–2.3\]; it is not an instance of that extension. Spacing methods for factorial congruences \[stewart2004, Lemma 2\] and the fixed-value multiplicity bound \[garaev-luca-shparlinski, arXiv v1, Theorem 12, p. 16\] are relevant comparisons, not ingredients of this proof.

<a id="comparison-with-denominator-savings-in-p-adic-linear-forms."></a>

#### Comparison with denominator savings in $`p`$-adic linear forms.

A related denominator-saving argument occurs in work of Lai, Lupu and Sprang on linear forms in $`p`$-adic zeta values. Here $`p\ge5`$ is a fixed prime and $`n`$ indexes the forms. They save a product $`\Phi_n`$ of prime powers from coefficient-denominator bounds built from $`\operatorname{lcm}(1,\ldots,n)`$ \[lai-lupu-sprang, §5\]. Its growth rate \[lai-lupu-sprang, Lemma 7.3\] enters their inequality \[lai-lupu-sprang, (8.1)\] and irrationality criterion \[lai-lupu-sprang, Lemma 2.1, p. 3\], quoted from Lai \[lai-2adic, Lemma 2.1, p. 4\]. On the same unbounded subsequence, nonzero forms with integer coefficients must have their $`p`$-adic absolute values, multiplied by the largest ordinary absolute value of a coefficient, tending to zero. For $`H_M`$, the analogous saving is $`L_M/\operatorname{den}(H_M)`$, whose required asymptotic size is not established here. This is a comparison of denominator control; no $`p`$-adic theorem is applied to $`S`$.

<a id="factorial-series-comparisons."></a>

#### Factorial-series comparisons.

Galambos treats the rationality of Cantor series in \[galambos1976, Ch. II, §2.1, pp. 21–22\]. Koepf and Schmersau prove irrationality for nonterminating factorial expansions whose digits are not eventually maximal \[koepf-schmersau, Example 3.2, p. 121\]. Appendix <a href="#sec:companion-orbit" data-reference-type="ref" data-reference="sec:companion-orbit">8</a> specifies the canonical convention and proves the criterion for $`C=S-e+2`$ directly.

The argument in §<a href="#sec:problem" data-reference-type="ref" data-reference="sec:problem">1</a> identifies the next integer above a scaled partial sum. This differs from the factorial-tail integrality lemma of Hančl and Tijdeman \[hancl-tijdeman, Lemma 2.1 and the following remark, p. 385\]: $`m!H_m`$ need not be integral; under the denominator-divisibility hypothesis, it is $`m!S`$ that is integral. The exclusion can also be expressed by saying that the least positive $`r`$ with $`q\mid r!`$ is at least $`300000`$. Sondow uses this factorial index for $`e`$ \[sondow2006, §3, Theorem 1\]; his approximation bound is not applied to $`S`$.

For integer-coefficient factorial series, Hančl and Tijdeman prove integrality of normalised rational tails \[hancl-tijdeman, Lemma 2.1 and the following remark, p. 385\], and classify the polynomial-coefficient case \[hancl-tijdeman, Theorem 3.1 and Corollary 3.1, pp. 390–391\]. The long record, Appendix B.2, explains the direct application after rewriting $`S`$ as a factorial series with integer carry-defect coefficients. These results do not remove the indicators in <a href="#eq:companion-wrap" data-reference-type="eqref" data-reference="eq:companion-wrap">[eq:companion-wrap]</a>.

<a id="selected-prime-and-mean-comparisons."></a>

#### Selected-prime and mean comparisons.

The [test with an additional selected prime](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L4766) adds $`(2p+1)C_pq<2p^2(2p-1)!`$ for a prime $`q\mid R_p`$ to <a href="#eq:global-complementary-target" data-reference-type="eqref" data-reference="eq:global-complementary-target">[eq:global-complementary-target]</a>. The long paper, §4, constructs blocks with $`q\mid R_p`$ and proves the equivalence with the two inequalities. This is an additional restriction, not an equivalent criterion for irrationality. Its §7 gives a sufficient joint mean bound for <a href="#eq:joint-loss-budget" data-reference-type="eqref" data-reference="eq:joint-loss-budget">[eq:joint-loss-budget]</a>, on the same sets of parameters for both summands; separate estimates on unrelated sets do not suffice.

<a id="additional-proofs-and-comparison-files."></a>

#### Additional proofs and comparison files.

A related cofactor construction gives [a remainder equal to a determinant times $`S`$, up to an integer](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/PrimeUnitTranslator.lean#L1559). For a positive starting parameter, its primitive normalization is the progression vector of §<a href="#sec:compressed-kernel" data-reference-type="ref" data-reference="sec:compressed-kernel">3.2</a>, up to sign; the long record, §7, proves this identification. Nonintegrality along the family with least support index tending to infinity is equivalent to irrationality, not a condition established by the construction.

The [interval condition at the lower endpoint](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L6099) and the test for $`p^2\mid Z_{2p}`$ combine quantities at the same index. Non-unit carries at arbitrarily large $`2p`$, with $`p`$ an odd prime, already suffice without that test. These comparisons, [the condition for two consecutive unit carries](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L148), and an example distinguishing the integer recurrence from its defining floor relation are given in the long record. It also explains why any fixed collection of denominator factors eventually divides the factorial being removed.

The standalone formal source for the carry equivalences is [the isolated source for the next-integer criterion](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/FactorialGapPlateauCore.lean). [The module on factorial-scaled partial sums and the next integer](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/FactorialZeroPlateau.lean) duplicates this development; it is not the standalone source. Formal proofs of the rationality equivalence are given in [rationality and factorial residues](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompanionOrbitRationality.lean). Its statements corresponding to the paper are [eventual residue congruence under rationality](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompanionOrbitRationality.lean) and [arbitrarily late failures of the residue congruence](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompanionOrbitRationality.lean). The combined statement [the full factorial-residue equivalence](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompanionOrbitRationality.lean) corresponds to Theorem <a href="#res:companion-orbit-rationality-boundary" data-reference-type="ref" data-reference="res:companion-orbit-rationality-boundary">7</a> and the following [remark](#bdry:companion-orbit-nonconcentration). The long record also gives the two simultaneous inequalities for a selected prime, the shared-factor bound for the selected factors, and the eventual absorption of fixed denominator indices. The separate public Lean release `wcook04/plectis-erdos-lean` at commit `52f29ad1` selects those three endpoints as `movingPrivateFactorScaleSplit_implies_irrational`, `splitFactorNormalizedCollision_implies_irrational` and `fixedOwnerPair_eventually_absorbed` in `PalomarCorpus/E68/Challenge.lean`. These three release statements are separate from the historical public links above. The supplied release record reports acceptance of the `E68` entry at commit `52f29ad1` by the Linux replay of Palomar’s Comparator stage (run 34782407633, cited earlier in this appendix). That report does not establish a new compilation of every source linked by this manuscript. The unconditional correction <a href="#eq:companion-wrap" data-reference-type="eqref" data-reference="eq:companion-wrap">[eq:companion-wrap]</a> is checked in [the exact floor correction for the companion series](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompanionConstantCarryLaw.lean), and the pole-residue identity and the two displayed reciprocal equalities are checked in [the prime-power noncancellation criterion](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PrimePoleCriterion.lean). The complete maximal-hit data come from the separate exact modular scan; the carry census and continued-fraction certificate use exact integer computation outside Lean. The inherited macro-generated links use public source pin `99f4bf47422a`. Their targets are retained for traceability, not retargeted to the newer attached snapshot.

<a id="acknowledgements"></a>

# Acknowledgements

The author thanks Wouter van Doorn for advice on exposition: explaining notation when it first appears, avoiding private terminology, and saying how restrictive a conditional hypothesis is. His advice concerned the writing of another note; he has not reviewed the mathematics of this paper.

<div class="thebibliography">

99

Paul Erdős. [On the irrationality of certain series: problems and results](https://doi.org/10.1017/CBO9780511897184.009). In Alan Baker (ed.), *New Advances in Transcendence Theory*, Cambridge University Press (1988), pp. 102–109.

Thomas F. Bloom. [Erdős Problem \#68](https://www.erdosproblems.com/68). Online resource (2026). Historical access: 28 July 2026; present-page status not reverified.

Georg Cantor. Über die einfachen Zahlensysteme. *Zeitschrift für Mathematik und Physik* **14** (1869), 121–128.

János Galambos. [Representations of Real Numbers by Infinite Series](https://doi.org/10.1007/BFb0081642). Lecture Notes in Mathematics 502, Springer (1976).

Wolfram Koepf and Dieter Schmersau. [Irrationality of certain infinite series II](https://doi.org/10.1524/anly.2011.1094). *Analysis* **31** (2011), 117–124.

Jaroslav Hančl and Robert Tijdeman. [On the irrationality of factorial series](https://doi.org/10.4064/aa118-4-5). *Acta Arithmetica* **118** (4) (2005), 383–401.

Joel Louwsma and Joseph Martino. [Rational numbers with odd greedy expansion of fixed length](https://arxiv.org/abs/2309.07280v1). Preprint (2023). arXiv:2309.07280.

Li Lai. [On the largest prime divisor of $`n!+1`$](https://doi.org/10.1017/S0004972725100543). *Bulletin of the Australian Mathematical Society* **113** (3) (2026), 390–403. arXiv:2103.14894.

Florian Luca and Igor E. Shparlinski. [Prime divisors of shifted factorials](https://doi.org/10.1112/S0024609305004923). *Bulletin of the London Mathematical Society* **37** (6) (2005), 809–817.

Li Lai, Cezar Lupu and Johannes Sprang. [On the irrationality of certain $`p`$-adic zeta values](https://doi.org/10.1007/s40687-025-00559-x). *Research in the Mathematical Sciences* **12** (4) (2025), article 77. arXiv:2505.23088.

Li Lai. [On the irrationality of certain $`2`$-adic zeta values](https://doi.org/10.1142/S1793042125500113). *International Journal of Number Theory* **21** (1) (2025), 207–235. arXiv:2304.00816.

NIST Digital Library of Mathematical Functions. [Continued fractions: convergents](https://dlmf.nist.gov/1.12). Online resource (2026).

Paul Erdős and Cameron L. Stewart. [On the greatest and least prime factors of $`n!+1`$](https://doi.org/10.1112/jlms/s2-13.3.513). *Journal of the London Mathematical Society* **13** (3) (1976), 513–519.

Florian Luca and Igor E. Shparlinski. [On the largest prime factor of $`n!+2^n-1`$](https://doi.org/10.5802/jtnb.524). *Journal de Théorie des Nombres de Bordeaux* **17** (3) (2005), 859–870.

Jonathan Sondow. [A geometric proof that $`e`$ is irrational and a new measure of its irrationality](https://arxiv.org/abs/0704.1282v2). *American Mathematical Monthly* **113** (7) (2006), 637–641. arXiv:0704.1282. Addendum: *Amer. Math. Monthly* **114** (2007), 659; reading copy v2.

Cameron L. Stewart. [On the greatest and least prime factors of $`n!+1`$, II](https://doi.org/10.5486/PMD.2004.3190). *Publicationes Mathematicae Debrecen* **65** (3–4) (2004), 461–480.

Moubariz Z. Garaev, Florian Luca and Igor E. Shparlinski. [Character sums and congruences with $`n!`$](https://doi.org/10.1090/S0002-9947-04-03612-8). *Transactions of the American Mathematical Society* **356** (12) (2004), 5089–5102. arXiv:math/0403422.

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
