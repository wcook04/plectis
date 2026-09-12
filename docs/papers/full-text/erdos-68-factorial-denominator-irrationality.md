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

Every rational representation $`S=a/q`$, $`q>0`$, of $`S=\sum_{n\ge2}(n!-1)^{-1}`$ satisfies
``` math
q\nmid299999!,\qquad q\ge2^{39990}>10^{12038}.
```
The first exclusion follows from an exact strict-successor carry test; the second from continued fractions. An integral divisor basis determines the cancelling vectors and their attainable factorial moments. At fixed moment, every correction translates the full residual by an integer. Actual prime-power cancellations explain why common-denominator growth alone does not control reduced prefixes. The companion constant $`S-e+2`$ gives an exact factorial-orbit criterion; the remaining assertion is a [cofinal miss of the strict factorial successor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L1090).

<a id="sec:problem"></a>

# The denominator exclusions

Let $`S=\sum_{n\ge2}(n!-1)^{-1}`$ and
``` math
H_m=\sum_{n=2}^m\frac1{n!-1},\qquad
Z_m=\lfloor m!H_m\rfloor+1,\qquad
b_m=mZ_{m-1}+1-Z_m.
```
The divisibility exclusion in the abstract rests on the implication
``` math
\begin{equation}
S=a/q,\quad q\mid(m-1)!,\quad m\ge3
\quad\Longrightarrow\quad b_m=1.\label{eq:finite-denominator-consumer}
\end{equation}
```
Indeed, $`0<m!(S-H_m)<1`$, by comparison with the telescoping series $`\sum_{n>m}(n-1)/n!=1/m!`$. Thus $`m!S`$ is the unique integer strictly above $`m!H_m`$. The same argument at $`m-1`$ gives $`Z_m=m!S=mZ_{m-1}`$, proving <a href="#eq:finite-denominator-consumer" data-reference-type="eqref" data-reference="eq:finite-denominator-consumer">[eq:finite-denominator-consumer]</a>. For example, $`H_2=1`$ and $`H_3=6/5`$, so $`Z_2=3`$, $`Z_3=8`$, and $`b_3=3Z_2+1-Z_3=2`$. Thus the first test already excludes a rational denominator dividing $`2!`$; the computation at $`m=300000`$ is the same exact obstruction at a much stronger scale. A non-unit carry at index $`m`$ therefore forces [every rational denominator to be at least $`m`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L876), since any smaller positive $`q`$ would divide $`(m-1)!`$. The exact value $`b_{300000}\ne1`$ therefore excludes every divisor of $`299999!`$ as a denominator of $`S`$.

The independent continued-fraction exclusion bounds the denominator’s size. Neither restriction implies the other: a prime between $`299999`$ and $`599998`$ satisfies the divisibility restriction and fails the size restriction, whereas $`299999!`$ does the reverse. Both conclusions are finite; they do not decide the irrationality question posed by Erdős \[erdos1988; bloom\]. Their computational certificates are specified in §<a href="#sec:finite" data-reference-type="ref" data-reference="sec:finite">8</a>.

[Adjacent factorial differences affect exactly their divisor channels](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L65). Integral triangular elimination therefore solves the channel equations. The support restriction determines which factorial moments occur, while at a fixed moment every correction changes the residual by an integer. The argument separates coefficient feasibility from the real separation needed for irrationality.

<a id="sec:companion-orbit"></a>

# The fixed companion orbit

The termwise identity
``` math
\frac1{n!-1}=\frac1{n!}+\frac1{n!(n!-1)}
```
replaces the changing prefixes by the factorial orbit of one fixed number,
``` math
C=\sum_{n\ge2}\frac1{n!(n!-1)}.
```
Absolute convergence gives
``` math
\begin{equation}
C+(e-2)=S.\label{eq:companion-decomposition}
\end{equation}
```
The endpoint of the exponential prefix contributes residue $`1`$ modulo $`m`$; its positive tail removes another unit on taking the floor. This accounts for the distinguished residue $`-2`$ in the following theorem.

<div id="res:companion-orbit-rationality-boundary" class="theorem">

**Theorem 2** (fixed companion-orbit rationality boundary). *The following statements are equivalent:*

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

The equivalence and its cofinal form are [companion orbit boundary](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteExisting.lean#L29).

<div class="proof">

*Proof.* First suppose $`S=a/q`$ with $`q>0`$, and take $`m`$ so large that $`q\mid(m-1)!`$. Write
``` math
E_m=m!\sum_{2\le n\le m}\frac1{n!},
 \qquad
 \varepsilon_m=m!\sum_{n>m}\frac1{n!}.
```
Then $`E_m`$ is an integer, $`0<\varepsilon_m<1`$, and $`m!S`$ is an integer divisible by $`m`$. Multiplying <a href="#eq:companion-decomposition" data-reference-type="eqref" data-reference="eq:companion-decomposition">[eq:companion-decomposition]</a> by $`m!`$ therefore gives
``` math
\lfloor m!C\rfloor=m!S-E_m-1.
```
Every summand of $`E_m`$ except the endpoint $`m!/m!=1`$ is divisible by $`m`$. Thus $`E_m\equiv1\pmod m`$ and $`\lfloor m!C\rfloor\equiv-2\pmod m`$.

Conversely, assume the displayed congruence from some index onward. Let $`d_m(C)=\lfloor m!C\rfloor-m\lfloor(m-1)!C\rfloor`$ be the canonical factorial digit. Since $`0\le d_m(C)<m`$, for $`m\ge3`$ the congruence is equivalent to
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

*Remark 1*. The remaining assertion is cofinal escape of this actual factorial orbit from $`-2`$. The theorem identifies the required event without supplying it.

</div>

<a id="sec:digits"></a>

## The carry and its wrap correction

The canonical factorial digit is $`d_m(C)=\lfloor m!C\rfloor-m\lfloor(m-1)!C\rfloor`$. For $`C_m=\sum_{n=2}^m1/(n!(n!-1))`$, put
``` math
\delta_m=m!(C-C_m),\qquad
\sigma_m=\mathbf1_{\{\{m!C\}<\delta_m\}}.
```
The positive tail satisfies $`0<\delta_m<1/((m+1)!-1)`$. Subtracting it crosses an integer exactly when $`\sigma_m=1`$, so for $`m\ge3`$
``` math
\begin{equation}
b_m=m-1-d_m(C)+\sigma_m-m\sigma_{m-1}.
\label{eq:companion-wrap}
\end{equation}
```
This identity is unconditional. A floor-stability hypothesis is required only to discard the two wrap terms. Equality in the defining comparison is the no-wrap case. Canonical factorial expansions and their rationality criterion are classical \[cantor1869; galambos1976\].

<div id="res:carry-characterization" class="theorem">

**Theorem 3** (exact carry characterisation). *<span id="res:strict-successor-complete-characterization" label="res:strict-successor-complete-characterization"></span> The following conditions are equivalent:
``` math
S\notin\mathbb Q,\qquad
(\forall B)(\exists m>B)\ b_m\ne1,\qquad
(\forall B)(\exists m>B)\ m\nmid Z_m.
```
In particular, [cofinal non-unit carries imply irrationality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L953); equivalently, the original problem is the [strict-successor criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L1090).*

</div>

The pair of equivalences is [carry characterisation](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteExisting.lean#L47).

<div class="proof">

*Proof.* Rationality forces eventual unit carries by <a href="#eq:finite-denominator-consumer" data-reference-type="eqref" data-reference="eq:finite-denominator-consumer">[eq:finite-denominator-consumer]</a>. Conversely, if $`b_m=1`$ eventually, then $`Z_m/m!`$ is eventually constant. Since
``` math
H_m<Z_m/m!\le H_m+1/m!,
```
that rational constant is $`S`$. Finally writing $`x=(m-1)!H_{m-1}`$ gives $`b_m=m-1-\lfloor m\{x\}+1/(m!-1)\rfloor`$, hence $`-1\le b_m\le m-1`$. For $`m\ge3`$, these bounds together with $`Z_m=mZ_{m-1}+1-b_m`$, imply $`m\mid Z_m`$ exactly when $`b_m=1`$. ◻

</div>

<a id="sec:channels"></a>

# An integral basis for factorial channels

For a finite integer vector $`\lambda`$, define
``` math
W_{d,n}=\frac{n!}{(d!)^{\lfloor n/d\rfloor}},\qquad
M(\lambda)=\sum_n\lambda_n n!,\qquad
V_d(\lambda)=\sum_n\lambda_nW_{d,n}.
```
The [weights are integers](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L25). We first allow the auxiliary coordinate $`e_1`$, then impose the manuscript support $`n\ge2`$. This coefficient convention introduces no term $`1/(1!-1)`$ into $`S`$.

<div id="res:divisor-channel-coordinates" class="theorem">

**Theorem 4** (divisor-channel coordinates). *Set
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

The observables, the unique expansion and the coefficient formula are [divisor channel coordinates](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteDivisorCoordinates.lean#L260).

<div class="proof">

*Proof.* The moment of $`T_n`$ is zero. The floor in $`W_{d,n}`$ changes between $`n-1`$ and $`n`$ precisely when $`d\mid n`$, so
``` math
V_d(T_n)=(d!-1)W_{d,n}\mathbf1_{d\mid n}.
```
The recursion cancels the proper divisor channels, proving the two identities by induction. The vectors $`e_1,T_2,\ldots,T_N`$ form an integral triangular basis with final coefficients $`1,-1,\ldots,-1`$. The change from $`T_n`$ to $`U_n`$ is integral triangular with unit diagonal. Hence $`e_1,U_2,\ldots,U_N`$ is also an integral basis. Applying $`M`$ and each $`V_d`$ identifies its coefficients as in <a href="#eq:channel-basis-expansion" data-reference-type="eqref" data-reference="eq:channel-basis-expansion">[eq:channel-basis-expansion]</a>. For $`d`$ beyond the support, $`V_d=M`$, so no infinite sum is required. ◻

</div>

The prime translator is the case $`U_p=T_p`$ for a prime $`p\ge3`$. The recursion also isolates composite channels; for example
``` math
\begin{equation}
U_9=9e_8-e_9-5040e_2+1680e_3.
\label{res:translator}
\end{equation}
```
It has moment zero and only channel $`9`$ is nonzero. Thus each channel can be adjusted separately by a multiple of its own denominator. The expansion is [composite translator nine](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteSupplementary.lean#L17) and the observable profile is [composite translator nine profile](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteSupplementary.lean#L45).

<a id="the-support-restriction-and-the-residual"></a>

## The support restriction and the residual

Write
``` math
L_D=\operatorname{lcm}_{2\le d\le D}(d!-1),\qquad
K_D=L_De_1-\sum_{d=2}^D\frac{L_D}{d!-1}U_d.
```
Equation <a href="#eq:channel-basis-expansion" data-reference-type="eqref" data-reference="eq:channel-basis-expansion">[eq:channel-basis-expansion]</a> implies both the channel congruence
``` math
\begin{equation}
V_d(\lambda)\equiv M(\lambda)\pmod{d!-1}
\label{res:congruence}
\end{equation}
```
in the equivalent integer-divisibility form [supported channel congruence](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteSupplementary.lean#L53), and the unique description of every low-channel kernel:
``` math
\begin{equation}
V_2=\cdots=V_D=0
\quad\Longleftrightarrow\quad
\lambda=tK_D+\sum_{n>D}z_nU_n,\qquad M=tL_D.
\label{eq:low-channel-classification}
\end{equation}
```
For the full residual
``` math
\mathcal R(\lambda)=\sum_{d\ge2}\frac{V_d(\lambda)}{d!-1},
```
we have $`\mathcal R(e_1)=S`$ and $`\mathcal R(U_n)=1`$. Therefore
``` math
\begin{equation}
\mathcal R\left(tK_D+\sum_{n>D}z_nU_n\right)
=tL_D(S-H_D)+\sum_{n>D}z_n.
\label{eq:residual-transparency}
\end{equation}
```
The series converges because $`V_d=M`$ beyond the support. This equation identifies the limit of channel adjustment: every zero-moment correction changes the residual by an integer. A further fractional cancellation coordinate does not arise from these corrections.

Only finitely many $`z_n`$ are nonzero. Put $`a_D=[e_1]K_D`$ and $`u_n=[e_1]U_n`$. Admissibility on $`n\ge2`$ becomes the single integer equation
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
Indeed, finite integer combinations of the $`u_n`$ form $`g_D\mathbb Z`$. The resulting positive generator is attained, and an attaining vector is primitive. Odd $`u_n`$ vanish by induction. For a prime $`p`$, the sole nonzero proper-divisor contribution at $`2p`$ gives $`u_{2p}=-2(2p)!/2^p\ne0`$. Every tail thus contains a nonzero coefficient, so $`g_D>0`$.

<a id="a-finite-certificate-for-the-infinite-moment-ideal."></a>

#### A finite certificate for the infinite moment ideal.

The scalar recurrence is
``` math
u_2=2,\qquad
u_n=-\sum_{\substack{d\mid n\\2\le d<n}}W_{d,n}u_d\quad(n>2).
```
Once a divisor $`g`$ controls the computed tail, only the terms with $`d\le D`$ can supply a nonzero residue to a later coefficient. Those finitely many sources have a factorial cutoff:
``` math
k!\mid W_{d,dk}=\frac{(dk)!}{(d!)^k}.
```
The quotient by $`k!`$ counts partitions into $`k`$ unordered blocks of size $`d`$.

<div id="res:finite-channel-moment-certificate" class="theorem">

**Theorem 5** (finite determination of the moment ideal). *Choose a prime $`\ell`$ with $`D/2<\ell\le D`$ and put $`H=D(2\ell-1)`$. Then
``` math
g_D=\gcd(u_{D+1},\ldots,u_H),\qquad H<2D^2.
```*

</div>

The statement is [finite channel moment certificate](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteMomentHorizon.lean#L252).

<div class="proof">

*Proof.* The finite gcd $`g`$ divides the nonzero term $`u_{2\ell}=-(2\ell)!/2^{\ell-1}`$, so $`g\mid(2\ell)!`$. For $`n>H`$ and a divisor $`d\le D`$, the integer $`n/d`$ is at least $`2\ell`$. Hence $`g\mid(n/d)!\mid W_{d,n}`$. Every early source is divisible by $`g`$. Strong induction handles the remaining divisors $`D<d<n`$, whose coefficients are already divisible by $`g`$. Thus $`g`$ divides the entire tail. Bertrand’s postulate supplies $`\ell`$ for $`D\ge3`$; take $`\ell=2`$ for $`D=2`$. Finally $`H\le D(2D-1)<2D^2`$. ◻

</div>

<div id="res:bandbreakpoint" class="theorem">

**Theorem 6** (quotient-band breakpoint). *Under the band hypothesis,
``` math
M=(d!)^k C_d.
```
In particular, in the first band $`d\le i_j<2d`$, channel cancellation $`C_d=0`$ forces $`M=0`$. If all indices are at least $`d`$, channel cancellation and $`M\ne0`$ therefore force at least one index $`i_j\ge2d`$.*

</div>

The exact factorisation is checked for every quotient band at [the band identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L71), and its zero-channel consequence is [band cancellation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L91). The first-band form is explicit at [first-band factorisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L101); the final breakpoint alternative is [breakpoint witness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L130).

The earlier envelope $`\Lambda_n=\operatorname{lcm}(1,\ldots,n)\mid u_n`$ <span id="eq:channel-lcm-envelope" label="eq:channel-lcm-envelope"></span> remains useful for other certificates. Finite-source checks can end sooner because only the sum of the sources has to vanish modulo $`g`$. The even-coefficient sign pattern supplies a nonzero term in every tail. Together with <a href="#eq:attainable-moment-ideal" data-reference-type="eqref" data-reference="eq:attainable-moment-ideal">[eq:attainable-moment-ideal]</a> this determines the unrestricted minimum positive moment for every fixed depth. For example, $`L_4=115`$, $`a_4=-55`$, $`u_6=-180`$, $`u_8=-4200`$ and $`23u_6-u_8=60\mid\Lambda_9`$ give minimum moment $`1380`$, attained by $`12K_4+253U_6-11U_8`$. On support through $`6`$ the minimum is instead $`4140`$. Minimum moment and minimum upper support are different objectives. Neither computation supplies a cofinal real-residual gap, and neither alters the two finite denominator exclusions.

<a id="sec:translator"></a>

# The moment cost and the choice of support

On the actual support $`n\ge2`$, one has the stronger congruence $`12\mid M-2V_2`$. For $`n=2,3`$, $`n!=2W_{2,n}`$. For $`n\ge4`$, both $`n!`$ and $`2W_{2,n}`$ are divisible by 12: writing $`n=2k`$ or $`2k+1`$, $`W_{2,2k}=k!\prod_{j=1}^k(2j-1)`$ is divisible by 6 for $`k\ge2`$. Since every $`d!-1`$ is coprime to 6, low-channel annihilation implies
``` math
\begin{equation}
12L_D\mid M.\label{eq:twelve-lcm}
\end{equation}
```
The factor 12 is sharp at $`D=2`$ and $`D=3`$, witnessed respectively by $`-6e_2+e_4`$ and $`-6e_2-8e_3+5e_4`$.

<a id="growth-of-the-compulsory-factor"></a>

## Growth of the compulsory factor

The following elementary estimate quantifies this cost:
``` math
\begin{equation}
\liminf_{N\to\infty}\frac{\log L_N}{N^{3/2}\log N}
\ge\frac{2\sqrt2}{3}.\label{res:lcm-growth}
\end{equation}
```
The LCM asymptotic is proved here by an ordinary mathematical argument. The linked asymptotic Lean files are proof candidates and are not being cited as kernel verification. The finite-block inequality has a separate Lean source, [finite terminal-block inequality](https://github.com/wcook04/plectis-erdos/blob/d788dd4b8c59f2246000f2ed98fffb8a5e8ac72e/lean/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L524-L529). For a terminal block of $`k`$ terms, the product–lcm–gcd inequality and $`\gcd(i!-1,j!-1)\mid j!/i!-1`$ give
``` math
\log L_N\ge\sum_{n=N-k+1}^N\log(n!-1)
-\binom{k+1}{3}\log N.
```
Taking $`k=\lfloor\alpha\sqrt N\rfloor`$ gives leading coefficient $`\alpha-\alpha^3/6`$, maximised by $`\alpha=\sqrt2`$. For a fixed $`P\in\mathbb Z[X]\setminus\{0\}`$, the same ordinary argument gives this bound for $`\operatorname{lcm}_{n_0\le n\le N}(n!+P(n))`$, where $`n_0`$ is sufficiently large that all factors are positive and the collision differences below are nonzero, as in Lai’s Lemma 2.1 \[lai\]. The lower cutoff matters: $`P=-2`$ makes the factor at $`n=2`$ vanish. The argument uses
``` math
\gcd(i!+P(i),j!+P(j))\mid P(j)-(j!/i!)P(i);
```
the additional $`O_P(k^2\log N)`$ loss is lower order. The subtraction identity is recorded by Lai \[lai, (2.5)\]. For $`P=0`$, the lcm is only $`N!`$. These are common-denominator estimates. Consecutive denominators $`(N-1)!-1`$ and $`N!-1`$ are already coprime for $`N\ge3`$, so the qualitative failure of common-denominator clearing follows from two terms; the estimate above is the quantitative growth statement. In particular, $`L_N(S-H_N)\to\infty`$, so multiplying the prefix by its full lcm cannot make its positive tail small.

<a id="sec:compressed-kernel"></a>

## Remote primitive kernels

Support location imposes a different requirement from low moment. Let $`D,r\ge2`$ and let $`L`$ be a positive multiple of $`2,\ldots,D`$. Put
``` math
i_j=r+jL\ (0\le j<D),\quad N=r+(D-1)L,\quad
\alpha_d=(d!)^{L/d},
```
``` math
H(X)=\prod_{d=2}^D(\alpha_dX-1)=\sum_{j=0}^{D-1}h_jX^j,
\qquad A=\prod_{d=2}^D\alpha_d.
```
The primitive kernel on this grid is
``` math
\lambda_j^*=\frac{N!h_j}{A i_j!},\qquad
M=N!\prod_{d=2}^D(1-1/\alpha_d)>0.
```
Its final coefficient is 1. The channel equations are polynomial vanishing at the distinct points $`\alpha_d^{-1}`$. Integrality follows by expanding $`h_j/A`$ into products of reciprocal $`\alpha_d`$: each product divides the factorial quotient $`N!/i_j!`$. The minimum step is $`L=\operatorname{lcm}(2,\ldots,D)`$.

The stronger divisibility
``` math
r!\prod_{d=2}^D(L/d)!\prod_{d=2}^D(\alpha_d-1)\mid M
```
follows by counting partitions into the specified equal-sized blocks. In particular $`\lfloor\sqrt N/2\rfloor!\mid M`$: if $`v=\max(r,L/2)`$, then $`N<4v^2`$ and $`v!\mid M`$. Thus these moments absorb every fixed denominator as $`N\to\infty`$. On the factorial-grid Cramer vector the residual differs from a nonzero determinant times $`S`$ by an integer: this is the [Cramer residual identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/PrimeUnitTranslator.lean#L1559). Cofinal residual nonintegrality on this family is sufficient for irrationality; the construction does not establish that nonintegrality.

<a id="sec:prime-pole"></a>

# Cancellation in a reduced prefix

A common-denominator bound does not determine the denominator after addition. Put $`L_M=\operatorname{lcm}_{2\le n\le M}(n!-1)`$ and $`A_M=\sum_{n=2}^M L_M/(n!-1)`$. For a prime $`q`$ with attained maximum $`e=\max_{2\le n\le M}v_q(n!-1)>0`$, set
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
The equivalence, with the maximum and its attainment taken from the actual prefix lcm, is [maximal prime power survival](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompletePrimePole.lean#L118). This first-layer test is a consequence of the general reciprocal-sum valuation formula of Louwsma and Martino \[louwsma-martino, Lemma 4.1\].

The actual factorial-gap examples show why the weights matter. At $`M=138`$, the maximal $`139`$-hits are $`69,122,137`$, with cofactor residues $`6,49,73`$, and
``` math
6^{-1}+49^{-1}+73^{-1}=0\pmod{139}.
```
At $`M=2592`$, the maximal $`2593`$-hits are $`349,2243,2591`$, with residues $`1508,1566,1678`$ and reciprocal sum zero. All these attained exponents are one, so the respective prime disappears completely from the reduced prefix. Singleton maximal support cannot cancel, whereas a hit-count bound alone cannot determine a weighted sum. Even survival must subsequently be coupled to a real strict-successor inequality.

<a id="sec:projection"></a>

# One joint collision and residue estimate

The whole-prefix construction separates the common collision factor from prime-power layers with a unique maximal owner. For a natural parameter $`p\ge3`$, write $`d_n=n!-1`$ and put
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
Every prime dividing $`R_p`$ has a unique denominator attaining its maximal valuation. Reducing $`T_p`$ modulo that prime leaves one unit term, giving $`\gcd(T_p,R_p)=1`$. Thus $`0<\rho_p<R_p`$ whenever $`R_p>1`$.

<div id="res:global-complementary-criterion" class="proposition">

**Proposition 7** (global complementary-residue criterion). *If arbitrarily large natural parameters $`p\ge3`$ satisfy
``` math
\begin{equation}
R_p>1,\qquad
(2p+1)L_p^{\rm blk}<2p^2(2p-1)!\rho_p,
\label{eq:global-complementary-target}
\end{equation}
```
then $`S`$ is irrational.*

</div>

The criterion at natural parameters is [global complementary criterion nat](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteExisting.lean#L156).

<div class="proof">

*Proof.* Suppose $`S=a/q`$. For large $`p`$, $`q\mid F_p\mid C_p`$, so $`L_p^{\rm blk}S`$ is an integer multiple of $`R_p`$. Therefore
``` math
A=L_p^{\rm blk}(S-H_{2p-1})
```
is a positive integer congruent to $`-T_p`$ modulo $`R_p`$, and $`A\ge\rho_p`$. The positive tail bound
``` math
S-H_{2p-1}<\frac{2p+1}{2p^2(2p-1)!}
```
and <a href="#eq:global-complementary-target" data-reference-type="eqref" data-reference="eq:global-complementary-target">[eq:global-complementary-target]</a> give $`A<\rho_p`$, a contradiction. ◻

</div>

Let $`\widetilde C_p=C_p/F_p`$ and $`\eta_p=\rho_p/R_p`$. The inequality is exactly
``` math
\begin{equation}
\log\widetilde C_p-\log\eta_p
<\log\frac{2p^2(2p-1)!}{(2p+1)(p-1)!}.
\label{eq:joint-loss-budget}
\end{equation}
```
The right side is $`p\log p+(2\log2-1)p+O(\log p)`$. The modulus $`R_p`$ cancels: increasing private support alone does not improve this comparison. Coprimality permits $`\rho_p=1`$, so the complementary gap needs its own quantitative control. Both losses must be controlled at the same parameters. The [unit-factor pair floor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L4766) splits that scale test into the complementary-residue inequality and a local collision-core cap. A joint mean bound below $`(1-\varepsilon)p\log p`$ on the same nonempty sets in $`[X,2X]`$ would suffice; two unrelated cofinal sets can be disjoint.

<a id="sec:open"></a>

# The remaining real comparison

<span id="sec:plateau" label="sec:plateau"></span>

The exact target remains the [strict-successor criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L1090):
``` math
\begin{equation}
(\forall B)(\exists m>B)\ m\nmid Z_m.
\label{eq:canonical-open-target}
\end{equation}
```
Two sufficient approaches now have explicit, different missing estimates. For the compressed primitive grids, the moments already absorb every fixed denominator. With positive moment $`M`$ and upper support $`N`$, write
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
It puts the residual below the next integer and above $`A_N`$. Proving this on an unbounded grid family would suffice. The finite signed block $`A_N`$ is essential. The second approach asks for the simultaneous collision and complementary-gap estimate <a href="#eq:joint-loss-budget" data-reference-type="eqref" data-reference="eq:joint-loss-budget">[eq:joint-loss-budget]</a>. Neither estimate is established cofinally here.

<a id="sec:nogo"></a>

#### The limit of short supports.

<span id="sec:adjacent-unit-no-go" label="sec:adjacent-unit-no-go"></span> The shortest-support kernels cannot meet <a href="#eq:signed-block-gap" data-reference-type="eqref" data-reference="eq:signed-block-gap">[eq:signed-block-gap]</a>. For $`N=D+O(1)`$, the compulsory divisibility $`L_D\mid M`$ and <a href="#res:lcm-growth" data-reference-type="eqref" data-reference="res:lcm-growth">[res:lcm-growth]</a> give
``` math
\frac{2|M|}{(N+1)!-1}\longrightarrow\infty,
```
whereas the right side of <a href="#eq:signed-block-gap" data-reference-type="eqref" data-reference="eq:signed-block-gap">[eq:signed-block-gap]</a> is at most one. A useful family must therefore allow a larger upper support and still control its finite signed block.

Large denominator valuations alone also leave the real gap uncontrolled: the model fractions $`1/q^e`$ tend to zero. The exact [zero-branch / lower-endpoint cylinder](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L6099) and doubled-prime tests require joint numerator or predecessor information. Their thresholds, the [adjacent-window collapse](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L148), fixed-owner absorption, and the strongest countermodels are retained in the long reasoning record.

<a id="sec:finite"></a>

# The finite evidence

An exact non-unit carry at the prime index $`67`$ already forces [every rational denominator to be at least $`67`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L940). The exact GMP carry certificate covers $`3\le m\le300000`$. Its unit carries occur at
``` math
52,\ 591,\ 1030,\ 1407,\ 1438,\ 2164,\ 4258,\ 10991,\ 21236.
```
In particular $`b_{300000}\ne1`$, yielding $`q\nmid299999!`$ by <a href="#eq:finite-denominator-consumer" data-reference-type="eqref" data-reference="eq:finite-denominator-consumer">[eq:finite-denominator-consumer]</a>. This excludes every divisor of that factorial, including large divisors. It does not exclude all integers with small prime factors, since their multiplicities can be too large.

The separate $`80000`$-bit exact rational enclosure forces $`23449`$ common continued-fraction partial quotients. Its best-approximation certificate gives $`q\ge2^{39990}>10^{12038}`$. The open-versus-closed complete-quotient endpoint convention matters for a sharper extraction; no stronger numerical floor is asserted here. The exact sources, enclosure and integer-computation receipts are retained with the long record. Neither finite calculation supplies <a href="#eq:canonical-open-target" data-reference-type="eqref" data-reference="eq:canonical-open-target">[eq:canonical-open-target]</a>.

<a id="app:sources"></a>

# Statements and declarations

The finite divisor-event identities, isolated-channel recursion, vanishing moment, individual channel values, and the factor $`12`$ are checked in [divisor channel basis](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/DivisorChannelBasis.lean). The unique integral basis expansion, attainable-moment formula and compressed primitive-grid construction are ordinary proofs, described in [divisor channel basis](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/DivisorChannelBasis.md) and, for the grid construction, in [compressed primitive channel kernel](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompressedPrimitiveChannelKernel.md). The quadratic stopping theorem is checked in [complete moment horizon](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteMomentHorizon.lean), together with the scalar recurrence, the equal-block divisibility and the prime anchor it uses. The earlier lcm-envelope certificate and depth-$`4`$ moment $`1380`$ are ordinary proofs with exact checks in [check moment saturation](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/scripts/check_moment_saturation.py). The finite-source checks are in [check finite source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/scripts/check_finite_source.py). The inherited generic lemmas in [tail ideal certificate](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/TailIdealCertificate.lean) assume the lcm envelope; they do not formalise the factorial arithmetic. The growth liminf is the ordinary asymptotic consequence of the finite terminal-block inequality cited above. The associated [asymptotic](https://github.com/wcook04/plectis-erdos/blob/d788dd4b8c59f2246000f2ed98fffb8a5e8ac72e/lean/ErdosProblems/Erdos68/PaperCompleteAsymptotics.lean) and [liminf](https://github.com/wcook04/plectis-erdos/blob/d788dd4b8c59f2246000f2ed98fffb8a5e8ac72e/lean/ErdosProblems/Erdos68/PaperCompleteLiminf.lean) Lean files are proof candidates and are not being cited as kernel verification.

The Comparator isolation pin for the carry equivalences is [factorial gap plateau core](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/FactorialGapPlateauCore.lean). [factorial zero plateau](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/FactorialZeroPlateau.lean) is the default-root duplicate of that family and is not the isolation source. Companion-orbit rationality is in [companion orbit rationality](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompanionOrbitRationality.lean); the unconditional correction <a href="#eq:companion-wrap" data-reference-type="eqref" data-reference="eq:companion-wrap">[eq:companion-wrap]</a> is in [companion constant carry law](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompanionConstantCarryLaw.lean). The pole-residue identity and the two displayed reciprocal equalities are in [prime pole criterion](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PrimePoleCriterion.lean). The complete maximal-hit data come from the separate exact modular scan. The carry census and continued-fraction certificate use exact integer computation outside Lean.

The inherited public source pin is `99f4bf47422a`. Source-current additions and that public snapshot must be reconciled at one immutable release before its links are represented as a replay of the whole note. Formal proof checking does not assess external novelty or the significance of the remaining hypothesis. The complete source register, receipts and failed-route calculations belong to the long record.

<a id="app:sources"></a>

# Guide to the formal sources

The public `ErdosProblems.Erdos68` package contains the checked source for this note. The pinned snapshot contains fifteen cited modules: `AdjacentUnitCarryWindow`, `CanonicalFactorialDigits`, `ChannelBreakpointRigidity`, `ChannelIntegralCongruence`, `DivisorFactorialCentre`, `EndpointWeightedPrivateSupport`, `FactorialCarry`, `FactorialChannelCertificate`, `FactorialGapPlateauCore` (isolation pin; `FactorialZeroPlateau` is the default-root duplicate), `FiniteDefectAutomaton`, `GapScalarNormalForm`, `PrimeThresholdParity`, `PrimeUnitTranslator`, `PrimeZeroBranch`, and `StrictSuccessorArithmetic`. Only these public modules belong to the manuscript source surface; no private auxiliary digit-rigidity file is cited or projected. The public root imports every cited module. The declaration table below is pinned to the shared formal-source commit used throughout this problem-note series.

- [adjacent-window collapse](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L148)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L215)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L243)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L337)

- [denominator at least the carry index](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L876)

- [denominator at least $`67`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L940)

- [strict-successor criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L1090)

- [cofinal non-unit carries imply irrationality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L953)

- [zero-branch / lower-endpoint cylinder](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L6099)

- [unit-factor pair floor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L4766)

- [Cramer residual identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/PrimeUnitTranslator.lean#L1559)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L34)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L39)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L44)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L49)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L80)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L88)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L102)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L129)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L146)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L170)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L179)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/DivisorFactorialCentre.lean#L188)

- [weights are integers](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L25)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L39)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L43)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L51)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L55)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L59)

- [adjacent differences affect only divisor channels](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L65)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L101)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L105)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L109)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L112)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L119)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L126)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L133)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L140)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L151)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L156)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L868)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L885)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L905)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L1084)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L1103)

<a id="source-current-companion-orbit-and-comparator-routes."></a>

#### Source-current companion orbit and Comparator routes.

The complete infinite rationality boundary is checked in [companion orbit rationality](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompanionOrbitRationality.lean). Its paper-facing endpoints are [not irrational factorial gap series iff eventually companion floor $`-2`$](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompanionOrbitRationality.lean) and [irrational factorial gap series iff cofinal companion floor misses](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompanionOrbitRationality.lean). The coherent Comparator composite [companion-orbit complete characterisation](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/CompanionOrbitRationality.lean) routes to Theorem <a href="#res:companion-orbit-rationality-boundary" data-reference-type="ref" data-reference="res:companion-orbit-rationality-boundary">2</a> and Remark <a href="#bdry:companion-orbit-nonconcentration" data-reference-type="ref" data-reference="bdry:companion-orbit-nonconcentration">1</a>. The moving-factor Comparator endpoints are recorded in the long reasoning record as the moving-factor scale split, the split-factor normalised collision, and the fixed-owner absorption boundary. These source-current modules, Comparator packages, and this manuscript stage require one common immutable public checkpoint before terminal external replay or Palomar readiness is claimed.

<div class="thebibliography">

9

P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). T. F. Bloom, *Erdős Problem \#68*. <https://www.erdosproblems.com/68>, accessed 28 July 2026. G. Cantor, *Über die einfachen Zahlensysteme*, Z. Math. Phys. **14** (1869), 121–128. J. Galambos, *Representations of Real Numbers by Infinite Series*, Lecture Notes in Math. **502**, Springer, 1976, Chapter 1. J. Louwsma and J. Martino, *Rational numbers with odd greedy expansion of fixed length*, arXiv:[2309.07280v1](https://arxiv.org/abs/2309.07280), 2023, Lemma 4.1, p. 10. L. Lai, *On the largest prime divisor of $`n!+1`$*, arXiv:[2103.14894v1](https://arxiv.org/abs/2103.14894), 2021, proof of Lemma 2.4, (2.5).

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
