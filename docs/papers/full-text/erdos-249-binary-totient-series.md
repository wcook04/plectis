<a id="erdos-249-binary-totient-series"></a>

# A Basis for the 2-Kernel of Euler’s Totient

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

For $`j\ge0`$ and $`0\le r<2^j`$, write $`\varphi_{j,r}(n)=\varphi(2^jn+r)`$. We prove that
``` math
\{\varphi_{0,0},\varphi_{1,0}\}
  \cup
  \{\varphi_{j,r}:j\ge1,\ 0<r<2^j,\ r\ {\rm odd}\}
```
is a $`\mathbb{Q}`$-basis for the span of the $`2`$-kernel of Euler’s totient. Consequently, the span of the dyadic sections through level $`e`$ has dimension exactly $`2^e+1`$ for every $`e\ge1`$, and the two elementary reduction identities generate every $`\mathbb{Q}`$-linear relation among the sections. This determines the entire dyadic-section span; it does not decide the irrationality question below.

Let $`S=\sum_{n\ge1}\varphi(n)/2^n`$. A rational value would induce a tempered integral tail orbit whose dyadic sections through level $`e`$ have rank at least $`2^e-1`$; no conflicting upper bound is proved. Independently, every rational representation $`S=a/q`$ must satisfy
``` math
q>79\,639\,646\,646\,701\,375\,323\,355\,774\,875\,831\,053,
```
the sharp exclusion for the chosen $`240`$-binary-digit Farey window. The current repository also verifies a diagonal tail certificate at every natural scale $`t\le82`$. This aggregate is finite: it supplies neither an instance at $`t=83`$ nor an unbounded family.

We also record exact equivalences between irrationality of $`S`$ and cofinal tail-nonintegrality or certificate supplies. These are lossless reformulations of the open problem, not evidence for the missing cofinal producer. Erdős Problem #249 remains open; formalisation alone is not presented as a novelty claim.

<a id="sec:results"></a>

# Introduction and main results

Erdős Problem #249 asks whether
``` math
S=\sum_{n\ge1}\frac{\varphi(n)}{2^n}
```
is irrational; see Erdős and Graham \[erdosgraham1980, p. 61\] and Erdős \[erdos1988, p. 102\]. Bloom’s current catalogue record reproduces this question and labels it open, while explicitly warning that the status is the website owner’s present assessment and may omit relevant literature \[erdosproblems\]. We therefore use the catalogue for numbering and current reported status only; the two original sources carry the problem statement.

The principal result determines the dyadic sections of Euler’s totient at every finite level: the two zero-residue sections $`\varphi_{0,0}`$ and $`\varphi_{1,0}`$, together with the odd-residue sections, form a rational basis, and the two reduction identities below generate every rational relation among the sections. Its connection with Erdős Problem #249 is through the integral scaled-tail recurrence displayed below. The basis theorem gives a lower bound for the dyadic-section rank of every such recurrence supplied by a hypothetical rational value of $`S`$, but no corresponding upper bound is known.

The other unconditional statements are a finite Farey denominator exclusion, finite diagonal certificates at every $`t\le82`$, identities for the Lambert coefficient sequence $`A=\varphi*\mu`$, and a theorem that no fixed common denominator clears every $`A(n)/n`$. The certificate equivalences have a different logical status: <a href="#res:equivalences" data-reference-type="ref" data-reference="res:equivalences">[res:equivalences]</a> gives exact characterisations of irrationality, while <a href="#res:supply" data-reference-type="ref" data-reference="res:supply">[res:supply]</a> gives a sufficient criterion. Their unbounded hypotheses are not proved, so the finite certificate band is not progress on the cofinal obligation.

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

Each *Checked* line below links the relevant declarations at commit `599f7e50a15b`. The bracketed tags reproduce the public status recorded by the claim registry; where no registry row owns the cited declarations, the text says so rather than assigning a neighbouring status.

Throughout $`\mathbb{N}=\{0,1,2,\ldots\}`$ and $`\varphi(0)=0`$. Thus $`\varphi_{j,r}(n)=\varphi(2^jn+r)`$, for $`j\ge0`$ and $`0\le r<2^j`$, is the $`(j,r)`$ *dyadic section* of Euler’s totient, a vector in $`\mathbb{Q}^{\mathbb{N}}`$, and $`j`$ is its *level*; the family of all of them is the $`2`$-kernel $`\mathcal K_2(\varphi)`$ in the sense of Allouche and Shallit \[allouche-shallit\]. Two elementary identities relate them: the *reductions* $`\varphi_{j+1,0}=2^{j}\varphi_{1,0}`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientMahlerDefect.lean#L150)) and $`\varphi_{j,\,2^{t+1}s}=2^{t}\varphi_{j-t-1,\,s}`$ for $`s`$ odd with $`2^{t+1}s<2^j`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientMahlerDefect.lean#L159)). At level $`3`$, for instance, they give $`\varphi_{3,0}=4\varphi_{1,0}`$, $`\varphi_{3,2}=\varphi_{2,1}`$, $`\varphi_{3,4}=2\varphi_{1,1}`$ and $`\varphi_{3,6}=\varphi_{2,3}`$, while the four odd residues $`r=1,3,5,7`$ are reduced by neither; numerically $`\varphi_{3,4}(1)=\varphi(12)=4=2\varphi(3)=2\varphi_{1,1}(1)`$. So beyond $`\varphi_{0,0}`$ and $`\varphi_{1,0}`$ each level contributes only its odd residues, and the count through level $`e`$ is $`2+\sum_{j=1}^{e}2^{j-1}=2^e+1`$; <a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a> says that count is the exact dimension.

Two objects built from $`S`$ recur below. The *scaled tail* $`R_N=\sum_{m\ge1}\varphi(N+m)/2^m`$ is $`2^N`$ times the part of the series beyond index $`N`$; since $`2^NS=\Phi_N+R_N`$ with $`\Phi_N=\sum_{1\le n\le N}\varphi(n)2^{N-n}`$ an integer ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientTailPeriodKiller.lean#L150)), $`R_N`$ and $`2^NS`$ differ by an integer. For $`h,N,L\in\mathbb{N}`$, put
``` math
D_{h,N,L}
  =
  \sum_{j=0}^{L-1}
  \bigl(\varphi(N+h+1+j)-\varphi(N+1+j)\bigr)2^{L-1-j},
```
and let $`\rho_{h,N,L}\in\{0,\dots,2^L-1\}`$ be its residue modulo $`2^L`$. A *finite tail-difference certificate* at $`(h,N,L)`$ is the pair of strict inequalities
``` math
N+h+L+2<\rho_{h,N,L}<2^L-(N+h+L+2)
```
([definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientTailPeriodKiller.lean#L72)). It exists to make a statement about an infinite tail decidable by a finite computation, and it is faithful: some depth $`L`$ certifies $`(h,N)`$ if and only if $`R_{N+h}-R_N\notin\mathbb{Z}`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/LcmConeFlatness.lean#L316)). For example,
``` math
D_{1,12,16}=-143140,\qquad
  \rho_{1,12,16}=53468,\qquad N+h+L+2=31,
```
so $`(1,12,16)`$ is a certificate. More generally, the test succeeds at $`(h,12,16)`$ for every $`h`$ with $`1\le h\le8`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientTailPeriodKiller.lean#L404)), so none of $`R_{13}-R_{12},\dots,R_{20}-R_{12}`$ is an integer ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientTailPeriodKiller.lean#L407)).

A third recurring object is an *integral scaled-tail sequence with multiplier $`v`$*. For a coefficient sequence $`c:\mathbb{N}\to\mathbb{N}`$ and an integer $`v\ge1`$, this is an integer sequence $`u`$ satisfying
``` math
u(N+1)=2u(N)-v\,c(N+1)\quad\hbox{for every }N,
  \qquad
  \frac{u(N)}{2^N}\longrightarrow0
```
([definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/GenericTailOrbitRigidity.lean#L67)); for $`c=\varphi`$ such a pair $`(v,u)`$ with $`v\ge1`$ exists exactly when $`S`$ is rational (Section <a href="#sec:carry-rank" data-reference-type="ref" data-reference="sec:carry-rank">4</a>).

1.  <span id="res:basis" label="res:basis"></span> <span class="smallcaps">\[checked; no registry row\]</span> **Basis theorem.** The family $`\mathcal B=\{\varphi_{0,0},\varphi_{1,0}\}\cup\{\varphi_{j,r}:j\ge1,\ r\ \text{odd},\
    0<r<2^j\}`$ is linearly independent over $`\mathbb{Q}`$ and spans the same $`\mathbb{Q}`$-subspace of $`\mathbb{Q}^{\mathbb{N}}`$ as $`\mathcal K_2(\varphi)`$; so $`\mathcal B`$ is a basis of that span, which is therefore infinite-dimensional. Since the reductions make every remaining section a rational multiple of a member of $`\mathcal B`$, the $`\mathbb{Q}`$-linear relations among dyadic sections of $`\varphi`$ are exactly those the reductions generate — a one-line consequence of the checked statements, not a further one. *Checked:* [independence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientMahlerDefect.lean#L1133), [span equality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientMahlerDefect.lean#L1248), [basis](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientMahlerDefect.lean#L1260). *Registry:* none of these three declarations is currently owned by a row of the claim registry; see the formal source notes below.

2.  <span id="res:rank" label="res:rank"></span> <span class="smallcaps">\[unconditional progress\]</span> **Exact finite-level rank.** For every $`e\ge0`$ the $`2^e+1`$ sections $`\varphi_{0,0}`$, $`\varphi_{1,0}`$ and $`\varphi_{j,r}`$ with $`1\le j\le e`$, $`r`$ odd, $`0<r<2^j`$ are linearly independent over $`\mathbb{Q}`$, so their span has dimension exactly $`2^e+1=2+\sum_{j=1}^{e}2^{j-1}`$: exact, not an estimate, because the even residues are already dependent by the reductions. Read instead as a truncation of the kernel, $`V_e=\operatorname{span}_{\mathbb{Q}}\{\varphi_{j,r}:0\le j\le
    e\}`$ has $`\dim V_e=2^e+1`$ for every $`e\ge1`$, and $`\dim V_0=1`$: the counted family carries $`\varphi_{1,0}`$, which is a level-one section, so the two readings agree from $`e=1`$ on and differ only at $`e=0`$. At $`e=1`$ both readings say that $`\varphi(n)`$, $`\varphi(2n)`$ and $`\varphi(2n+1)`$ are linearly independent over $`\mathbb{Q}`$. The independence half of <a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a> follows by finite character; the span equality needs the reductions as well. *Checked:* [independence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientMahlerDefect.lean#L900), [dimension](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientMahlerDefect.lean#L954), [infinite-dimensionality directly](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientMahlerDefect.lean#L1014).

3.  <span id="res:denominator" label="res:denominator"></span> <span class="smallcaps">\[formalised here\]</span> **Denominator exclusion, sharp for its window.** If $`S=a/q`$ with $`a\in\mathbb{Z}`$ and $`q\ge1`$ then $`q>79\,639\,646\,646\,701\,375\,323\,355\,774\,875\,831\,053\approx7.96\times10^{34}`$. The constant is optimal for the window that produces it — the window here is the pair $`(N,K)=(1,240)`$, meaning $`240`$ committed binary digits of the series shifted by one — in the sense that the next integer up is the exact first denominator at which that window’s certificate fails. The method is the classical Farey mediant argument (Section <a href="#sec:denominator" data-reference-type="ref" data-reference="sec:denominator">5</a>). *Checked:* [exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L18043), [reduced-denominator form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L18056), [first failure](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/GapFareyBound.lean#L225). *Registry:* the row owns the reduced-denominator form only.

4.  <span id="res:carryrank" label="res:carryrank"></span> <span class="smallcaps">\[formalised here\]</span> **Rank lower bound for a rational scaled-tail sequence.** If $`S`$ were rational then some integral scaled-tail sequence $`u`$ for the coefficients $`\varphi`$, with positive multiplier, would have for *every* $`e`$ dyadic sections through level $`e`$ — formed from $`u`$ exactly as the $`\varphi_{j,r}`$ are formed from $`\varphi`$ — spanning a space of dimension at least $`2^e-1`$. The same lower bound holds for every positive-multiplier integral scaled-tail sequence. This statement is specific to that binary scaled-tail representation; it does not constrain arguments formulated only through the Lambert weight, the coprimality identity, or tail differences. It is not an irrationality criterion, because no finite-rank upper bound is proved for the scaled-tail sequences supplied by rationality. *Checked:* [the barrier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientCarryKernelRigidity.lean#L284), [rank transport from <a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a>](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientCarryKernelRigidity.lean#L211).

5.  <span id="res:weight" label="res:weight"></span> <span class="smallcaps">\[checked; no registry row\]</span> **The \#249 weight.** $`S=\sum_{d\ge1}A(d)/(2^d-1)`$ with $`A=\varphi*\mu`$, the Dirichlet convolution $`A(n)=\sum_{d\mid n}\varphi(d)\mu(n/d)`$; here $`A\ge0`$, $`A(p)=p-2`$, $`A(p^k)=\varphi(p^k)-\varphi(p^{k-1})`$, and $`A`$ is unbounded. Its values at $`n=1,\dots,10`$ are $`1,0,1,1,3,0,5,2,4,0`$. *Checked:* [identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L18117), [sign](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/MersenneLambertLadder.lean#L370), [primes](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/MersenneLambertLadder.lean#L297), [prime powers](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/MersenneLambertLadder.lean#L272), [unboundedness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/MersenneLambertLadder.lean#L321). *Registry:* the Lambert-ladder row owns the neighbouring rungs, not these five declarations; see the formal source notes below.

6.  <span id="res:periodic" label="res:periodic"></span> <span class="smallcaps">\[unconditional progress\]</span> **Eventually periodic weights are settled.** For every integer base $`b\ge2`$, if $`\gamma\colon\mathbb{N}\to\mathbb{Q}`$ is eventually periodic, nonnegative and positive at some positive index of its periodic part, then $`\sum_{a\ge1}\gamma(a)/(b^a-1)`$ is irrational. Theorem A in Luca and Tachiya’s 2017 open-access RIMS paper restates their earlier signed theorem in the exact purely-periodic integer case: every nonzero purely periodic integer sequence gives an irrational Lambert value at every integer base $`|q|>1`$ \[lucatachiya2017, Theorem A, p. 139\]. Their Theorem 1 strengthens the nonnegative case to linear independence of each finite divisor-convolution ladder \[lucatachiya2017, Theorem 1, p. 139; proof pp. 149–150\]. Clearing the common denominator of a rational period and subtracting the finite rational prefix shows that Theorem 1 already proves the eventual nonnegative rational claim above; the checked theorem gives an independent formal proof. By <a href="#res:weight" data-reference-type="ref" data-reference="res:weight">[res:weight]</a> the weight $`A`$ is unbounded, hence not eventually periodic, so \#249 is outside this class. *Checked:* [the periodic theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L12483).

7.  <span id="res:primindex" label="res:primindex"></span> <span class="smallcaps">\[proved here\]</span> **No fixed common denominator clears the normalised weight.** For every integer $`D\ge1`$ some $`n\ge1`$ has $`D\cdot A(n)/n\notin\mathbb{Z}`$ — for $`D=6`$ at the prime $`n=7`$, where $`A(7)/7=5/7`$ — and any $`D`$ clearing every coordinate up to a horizon $`N\ge4`$ is divisible by an explicit two-tier primorial ($`4`$ at $`p=2`$, $`p^2`$ when $`p^2\le N`$, else $`p`$). No argument that clears the coordinates $`A(n)/n`$ by a single positive integer valid at all $`n`$ can therefore succeed. This obstruction is caused by the normalisation: the unnormalised weights $`A(n)`$ are integers. Arguments whose common denominator grows with the horizon, arguments using the integral weights directly, and arguments that never clear these coordinates are untouched. *Checked:* [no fixed index](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/PrimitiveDeterminantLift.lean#L169), [the primorial divisibility](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/PrimitiveDeterminantLift.lean#L148).

8.  <span id="res:equivalences" label="res:equivalences"></span> <span class="smallcaps">\[proved here\]</span> **Four exact characterisations of irrationality.** Irrationality of $`S`$ is equivalent to each of: non-integrality of the tail difference $`R_{N+h}-R_N`$ at every $`N`$ and every shift $`h\ge1`$, equivalently a certificate at every such pair; a certificate at every $`h\ge1`$ and at arbitrarily large $`N`$; and the same at the scales $`N=h=\operatorname{lcm}(1,\dots,t)`$, for arbitrarily large $`t`$. A fourth equivalence, independent of the certificate language, is a counted anti-concentration condition on window phases. These characterisations identify the unbounded input exactly; they retain the full difficulty of \#249 and do not supply that input. *Checked:* [pointwise](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/LcmConeFlatness.lean#L399), [cofinal at each shift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/LcmConeFlatness.lean#L412), [$`\operatorname{lcm}`$ diagonal](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/LcmConeFlatness.lean#L426), [window-separated pairs](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/PivotAntiReconstruction.lean#L1775).

9.  <span id="res:supply" label="res:supply"></span> <span class="smallcaps">\[conditional reduction\]</span> **A denominator-indexed gap-certificate hypothesis.** Suppose that for each denominator $`q`$ there is a truncation window $`(N,K)`$ whose totient residue avoids a band of width $`q(N{+}K{+}2)`$ out of $`2^K`$. This hypothesis *implies* irrationality. It concerns a second certificate family, not the one of <a href="#res:equivalences" data-reference-type="ref" data-reference="res:equivalences">[res:equivalences]</a>: the band scales with $`q`$, and the family is indexed by denominators rather than by shifts. The converse is not proved and is not claimed. *Checked:* [the supply implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L15697). *Registry:* no row currently owns this declaration.

10. <span id="res:open" label="res:open"></span> <span class="smallcaps">\[open\]</span> **Erdős #249.** Whether $`S`$ is irrational. Not proved here.

<a id="sec:family"></a>

# The Lambert-series form of Problem \#249

If $`f=g*\mathbf 1`$, that is $`f(n)=\sum_{d\mid n}g(d)`$, and $`\sum_{d\ge1}|g(d)|/(2^d-1)<\infty`$, then absolute convergence justifies interchanging the two sums and gives
``` math
\sum_{n\ge1}\frac{f(n)}{2^n}
  \;=\;\sum_{d\ge1}\frac{g(d)}{2^d-1}.
  \tag{1}\label{eq:lambert}
```
whose right-hand side is a Lambert series with coefficients $`g`$. Four classical coefficient sequences have this shape. The table records the constant, the weight $`g=f*\mu`$, and its status.

| $`f`$ | $`\sum f(n)/2^n`$ | weight $`g=f*\mu`$ | status |
|:---|:---|:---|:---|
| $`\tau`$ | $`1.6066951\ldots=E`$ | $`g\equiv1`$ | The Erdős–Borwein constant; irrational \[erdos1948, theorem on p. 63\]; formalised here in the Lambert form $`\sum_{d\ge1}(2^d-1)^{-1}`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L8007)) |
| $`\omega`$ | $`0.5169428\ldots`$ | $`g=\mathbf 1_{\text{primes}}`$ | Irrational at base $`2`$: Tao–Teräväinen, Thm. 1.3, p. 4; proof pp. 44–56 \[taoteravainen2025\] |
| $`\Omega`$ | $`0.5895032\ldots`$ | $`g=\mathbf 1_{\text{prime powers}}`$ | Asserted *ibid.* by a similar argument, with the details left to the reader; not a proved theorem there |
| $`\varphi`$ | $`1.3676308\ldots=S`$ | $`g=A=\varphi*\mu`$ | **Open** (Erdős \#249) |

The first three weights are bounded, taking only the values $`0`$ and $`1`$ (for $`\tau`$ the weight is the constant $`1`$). The fourth is unbounded, by <a href="#res:weight" data-reference-type="ref" data-reference="res:weight">[res:weight]</a>. That difference is the one that matters for the route in <a href="#res:periodic" data-reference-type="ref" data-reference="res:periodic">[res:periodic]</a>, and we do not claim it is the only difference: $`A`$ also vanishes on $`n\equiv2\pmod4`$, while $`\mathbf 1_{\text{primes}}`$ is bounded but no more eventually periodic than $`A`$ is, so the settled $`\omega`$ row is not an instance of <a href="#res:periodic" data-reference-type="ref" data-reference="res:periodic">[res:periodic]</a> either. It was settled by a different method, discussed in Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">8.5</a>.

Luca and Tachiya’s result is stronger than the single $`\tau`$ row: Example 1 makes $`1`$ and every finite ladder of generalized-divisor-function values linearly independent  \[lucatachiya2017, Example 1, p. 140; proof pp. 149–150\]. Their Example 2 applies the period-two odd-support indicator and proves joint linear independence of its Lambert value with every finite higher divisor-convolution ladder, for integer bases $`q`$ of either sign with $`|q|>1`$ \[lucatachiya2017, Example 2, p. 140\]. Thus the cited theorem strictly strengthens the isolated odd-support irrationality row. Historically, Erdős already singled out the totient series itself as a difficult analogue at the end of his 1948 paper \[erdos1948, p. 66\]; that remark supplies lineage, not a modern status proof.

<a id="a-nearby-2026-totient-theorem-has-different-coordinates."></a>

#### A nearby 2026 totient theorem has different coordinates.

Kaneko, Suzuki and Tachiya prove that if $`f(n)`$ is a nonnegative integer sequence of infinite support with $`\sum_{n\le x}f(n)=O(x(\log x)^\delta)`$, then, for every integer $`t\ge2`$, both
``` math
\sum_{n\ge1}\frac{f(n)}{t^{\sigma(n)}}
  \qquad\text{and}\qquad
  \sum_{n\ge1}\frac{f(n)}{t^{\varphi(n)}}
```
are irrational \[kanekosuzukitachiya2026, Corollary 3, pp. 5–6; proof pp. 18–19\]. This includes substantial families of totient-related series, but $`\varphi(n)`$ occurs in the *exponent*. Problem #249 instead places $`\varphi(n)`$ in the coefficient of $`2^{-n}`$. The theorem therefore supplies a genuine adjacent result and a useful warning against a tempting misidentification; it does not settle or reduce the displayed problem.

<a id="exact-identities-and-representations."></a>

#### Exact identities and representations.

Several neighbouring Dirichlet-convolution identities are rational and exactly computable. Writing $`L(g):=\sum_{d\ge1}g(d)/(2^d-1)`$, we have $`\sum_{d\ge1}\mu(d)/(2^d-1)=\tfrac12`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L18106)) and $`\sum_{d\ge1}\varphi(d)/(2^d-1)=2`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L18101)). These belong to two distinct one-step Möbius-convolution chains:
``` math
L(\mathbf 1)=E\ \longmapsto\ L(\mu)=\tfrac12,
  \qquad
  L(\varphi)=2 \ \longmapsto\ L(\varphi*\mu)=S.
```
Thus $`S`$ is one convolution step from the rational value $`L(\varphi)=2`$, not from $`E`$; the parallel chains show that this transformation need not preserve rationality. The squared-denominator representation $`S=\tfrac12+\sum_{d\ge1}\mu(d)/(2^d-1)^2`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L18126)) converges fast enough to recompute the decimal above.

There is also an exact probabilistic reading, and it is more than a gloss. Let $`X`$ and $`Y`$ be independent fair-coin geometric waiting times on $`\mathbb{N}_{>0}`$. Then
``` math
S=\tfrac12+\Pr[\gcd(X,Y)=1]
```
([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L18229)), the probability being the visible-coprime-pair series $`\sum_{\gcd(m,n)=1}2^{-(m+n)}`$. That probability is related to a distribution over the Stern–Brocot tree in a completely explicit way. For positive coprime $`(a,b)`$ put $`w_{a,b}=1/(2^{a+b}-1)`$. These reduced-slope masses sum to exactly $`1`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/GcdMomentCalculus.lean#L349)), and at each node $`(a,b)`$ the cylinder mass $`1/((2^a-1)(2^b-1))`$ splits exactly into its stop mass and the masses of its two children ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/GcdMomentCalculus.lean#L474)). The coprimality probability is not that total mass; rather,
``` math
S-\tfrac12
  =\sum_{\substack{a,b\ge1\\(a,b)=1}}2^{-(a+b)}
  =\sum_{\substack{a,b\ge1\\(a,b)=1}}
     \bigl(1-2^{-(a+b)}\bigr)w_{a,b}.
```
It is therefore the expectation of the conditional primitive-pair factor $`1-2^{-(a+b)}`$ under the self-similar reduced-slope probability law. What is missing is not structure; it is an arithmetic consequence of the structure.

<a id="sec:rank"></a>

# Proof of the dyadic-section basis theorem

<a id="prior-work"></a>

## Prior work

For an integer $`k\ge2`$, the *$`k`$-kernel* of a sequence $`c`$ is $`\{n\mapsto c(k^jn+r):j\ge0,\ 0\le r<k^j\}`$, and $`c`$ is *$`k`$-regular* when the module generated by its $`k`$-kernel is finitely generated; both notions are due to Allouche and Shallit (\[allouche-shallit, Defs. 1.1 and 2.1, author-preprint pp. 2–3\]). Their Theorem 2.2 gives equivalent finite-kernel and matrix characterisations, and Theorem 3.1 proves closure under convolution  \[allouche-shallit, pp. 3–4 and 10–11\]; neither result controls the finite-level rank of a sequence that is not $`k`$-regular. Coons proved that $`\varphi`$ is not $`k`$-regular for any $`k\ge2`$ (\[coons\], Theorem 3.2, pp. 348–349, in the published version; Theorem 3.3, pp. 8–9, in the preprint, which numbers its results on a single running counter). Bell and Smertnig reach a further negative conclusion, and by a different route rather than by strengthening that one: their Theorem 1.3 shows that a $`k`$-Mahler series with multiplicative coefficients has a $`k`$-regular coefficient sequence in an explicit closed form, and that the totient generating series is not $`k`$-Mahler for any $`k\ge2`$ follows directly from the closed form \[bell-smertnig\].

Coons’s statement is about the union over all levels: no finite set of sections generates the rest. Bell and Smertnig’s is about a functional equation. <a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a> and <a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a> are complementary positive statements at each finite level, and are consistent with both precisely because the rank is unbounded in $`e`$. Knowing that a span is not finitely generated says nothing about its dimension at a given truncation, nor about which relations hold there; what is added here is that the dimension through level $`e`$ is exactly $`2^e+1`$, that an explicit family is a basis, and that the two elementary reductions generate every relation. We found no prior source giving any of those three for $`\varphi`$; that is the outcome of a search, not a proof of non-existence, and no priority is claimed.

<a id="parity-separated-evaluation-matrices"></a>

## Parity-separated evaluation matrices

<a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a> is proved by exhibiting a square matrix of values of the sections whose determinant is nonzero, and the linear algebra at its centre is simpler than the arithmetic construction that feeds it. We give the linear algebra first, then the arithmetic input it consumes.

Evaluate the sections at one point apiece to get a square matrix $`M`$, and suppose each column $`j`$ admits a fixed power $`2^{d_j}`$ dividing every entry of that column such that, after dividing the column through by it, the diagonal entry is odd and every off-diagonal entry is even; call such an $`M`$ a *parity-separated evaluation matrix*. The normalised matrix is then the identity modulo $`2`$; its determinant is odd, hence nonzero, and the sections are independent ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientMahlerDefect.lean#L788)). Producing evaluation points with exactly that parity pattern is what the arithmetic input is for, and it is the harder half. The Chinese remainder theorem together with Dirichlet’s theorem on primes in arithmetic progressions makes one of the evaluated affine values prime, which fixes the exact power of $`2`$ dividing the diagonal entry, while every other value receives a fresh prime divisor congruent to $`1`$ modulo a large power of two, which supplies the one extra factor of two that the off-diagonal entries need ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientMahlerDefect.lean#L847)). Even residues never enter, because the second reduction has already carried them to odd residues at lower levels ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientMahlerDefect.lean#L159)).

<a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a> then needs only two further steps, and both are short. Linear independence is a property of finite subfamilies, so the level-$`e`$ statement, applied with $`e`$ above the largest level occurring in a given finite subset, already gives independence of the whole infinite family $`\mathcal B`$. And the two reductions carry every remaining section onto a rational multiple of a member of $`\mathcal B`$, so the spans agree. That the assembly is short is the point: the level-$`e`$ theorem was always the whole content, and stating its consequence as infinite-dimensionality understated it. The sharp form is a basis.

<div class="remark">

*Remark 1*. <a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a> and <a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a> are statements about $`\varphi`$, not about $`S`$; they are true, and their proofs are complete, whether or not $`S`$ is irrational. Their connection to \#249 is not thematic but a single proved transport, and it is <a href="#res:carryrank" data-reference-type="ref" data-reference="res:carryrank">[res:carryrank]</a>.

</div>

<a id="sec:carry-rank"></a>

# Carry-rank consequences of rationality

Multiplying successive scaled tails by $`2`$ turns a hypothetical rational value into an integral recurrence. For coefficients $`c:\mathbb{N}\to\mathbb{N}`$ satisfying $`c(n)\le n`$, and in particular for $`c=\varphi`$ since $`\varphi(n)\le n`$, the series $`\sum c(n)/2^n`$ is rational exactly when an integral scaled-tail sequence exists, that is, an integer sequence $`u`$ with $`u(N+1)=2u(N)-v\,c(N+1)`$ for every $`N`$ and $`u(N)/2^N\to0`$, for some integer $`v\ge1`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/GenericTailOrbitRigidity.lean#L426)). Transporting <a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a> through that recurrence gives <a href="#res:carryrank" data-reference-type="ref" data-reference="res:carryrank">[res:carryrank]</a>. The complementary finite-rank upper bound, which would make this a proof of irrationality, is not available.

<a id="sec:denominator"></a>

# A Farey-mediant denominator exclusion

<a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a> is a Farey exclusion, and we say so before saying anything else about it. The argument is the classical mediant one. The Lean lemma commits the first $`240`$ binary digits of the shifted series as a single residue over the totient carry window $`(N,K)=(1,240)`$; a rational $`a/q`$ can equal $`S`$ only if it falls into a resulting bad interval of width $`243/2^{240}`$; that interval is bracketed by two explicit unimodular fractions $`a_1/b<c_1/d`$ with $`bc_1-a_1d=1`$; and the mediant lemma ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/GapFareyBound.lean#L51)) forces any rational strictly between unimodular neighbours to have denominator at least $`b+d`$. The excluded range is therefore $`q\le b+d-1`$, which is the printed constant ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/GapFareyBound.lean#L176)), and the transport to the series is a tail estimate ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L15658)). *The method is standard, and we claim no novelty for it.*

Two things should be read off correctly. First, the scale. A window of $`K`$ computed binary digits yields a mediant bound of order $`2^{K/2}`$: the same pipeline gives $`2.49\times10^{17}`$ at $`K=120`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/GapFareyBound.lean#L88)) and $`7.96\times10^{34}`$ at $`K=240`$. The constant is a function of how many digits were committed, not a measure of how much the problem has moved. Second, the sharpness. Within its window the bound cannot be improved at all: $`b+d`$ itself fails the certificate, so $`b+d-1`$ is exactly the last denominator excluded. A reader who regards an explicit Farey exclusion as routine is not in disagreement with this note. <a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a>, not <a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a>, is where we would ask a sceptical reader to look.

The bound transfers to the coprimality form of Section <a href="#sec:family" data-reference-type="ref" data-reference="sec:family">2</a> with the constant halved: the visible-coprime-pair series has no representation $`a/d`$ with $`d\le39\,819\,823\,323\,350\,687\,661\,677\,887\,437\,915\,526`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CertificateKernel.lean#L18244)), that number being $`(q_0-1)/2`$ for the constant $`q_0`$ of <a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a>.

<a id="sec:nogo"></a>

# Obstructions for fixed-coordinate methods

<a href="#res:primindex" data-reference-type="ref" data-reference="res:primindex">[res:primindex]</a> has a one-line proof. Take a prime $`p>\max(D,2)`$; then $`A(p)=p-2`$ by <a href="#res:weight" data-reference-type="ref" data-reference="res:weight">[res:weight]</a>, and $`p\nmid D(p-2)`$, so $`D\cdot A(p)/p\notin\mathbb{Z}`$.

Two further checked results delimit narrower abstract hypothesis classes.

A fixed-precision transport result ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TropicalCurvatureCarry.lean#L137)) says that at every fixed positive precision, each finite compatible valuation-unit word admits a prefix-locked centred completion. Its statement quantifies over abstract pairs of a two-adic valuation and an odd unit; it mentions neither $`\varphi`$ nor $`S`$, its content is that a congruence class meets any interval of the corresponding length, and it is a restatement of a lemma printed immediately above it. The class of arguments it closes — deriving a contradiction from a local signature read at a precision fixed in advance, along a finite word — is not one anybody has proposed for \#249.

A factor-ideal result ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/LcmFactorIdealPulseObstruction.lean#L798), with a sparse-anchor companion at [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/LcmFactorIdealPulseObstruction.lean#L866)) exhibits, for each $`t\ge3`$ with $`H=\operatorname{lcm}(1,\dots,t)`$, a nonzero integer carry whose forcing letters lie in the ideal generated by $`\varphi(H)`$, which reproduces the true totient differences at $`t-2`$ prescribed indices, and which every finite integer shift polynomial carries to a pair with the same coboundary form, the same ideal memberships and an $`\ell^1`$-weight bound. It does close that hypothesis class. Two limits. The witness is a spike — its state is $`-\varphi(H)`$ at $`t-2`$ points and zero elsewhere, so it stays uniformly bounded while the strip bounds it respects grow, and the construction is cheap for that reason. And the shifted pairs are not asserted to be nonzero, so an argument that additionally demanded non-vanishing after the shift is not excluded. The theorem contains no whole-ray anchor condition, diagonal bound, or strict-survivor condition.

<a id="sec:programmes"></a>

# Further conditional criteria

The criteria below do not enter the proofs of the unconditional results. Each states its unproved hypotheses explicitly.

<a id="a-prime-orbit-sufficient-condition."></a>

#### A prime-orbit sufficient condition.

The hypothesis [asks](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L18) for cofinally many primes $`p`$ at which the first tail-orbit exponential has real part strictly below $`9/10`$. Granting it, [a positive adaptive truncation budget](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L27) follows, and then [$`S`$ is irrational](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L66). The $`9/10`$ hypothesis is weaker than the earlier $`4/5`$ hypothesis, but no instance of this cofinal hypothesis is proved. Section <a href="#sec:frontier" data-reference-type="ref" data-reference="sec:frontier">8</a> states the sharper form in which this hypothesis is now available.

<a id="finite-euler-factor-identities."></a>

#### Finite Euler-factor identities.

The local coefficients are
``` math
\eta(0)=1,\qquad \eta(1)=-2,\qquad \eta(2)=1,\qquad
  \eta(e)=0\quad(e\ge3),
```
the coefficients of $`(1-X)^2`$. For a prime $`p`$ and $`e\ge0`$, write $`\sigma_p(e)=1+p+\cdots+p^e`$. The two local Euler factors are
``` math
1-\frac2p+\frac1{p^2}=\left(1-\frac1p\right)^2,
  \qquad
  1-\frac2{p^2}+\frac1{p^4}
      =\left(1-\frac1{p^2}\right)^2
```
at [$`s=1`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L28) and [$`s=2`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L36). On the prime-power divisor-sum row,
``` math
\sigma_p(1)-2\sigma_p(0)=p-1
```
([first difference](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L44)), and for every $`e\ge0`$,
``` math
\sigma_p(e+2)-2\sigma_p(e+1)+\sigma_p(e)
    =p^{e+1}(p-1)
```
([second difference](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L51)). For example, at $`p=3`$ the values $`\sigma_3(0),\ldots,\sigma_3(3)=1,4,13,40`$ give $`4-2=2`$ and $`40-2\cdot13+4=18=3^2(3-1)`$. Thus convolution with $`\mu\ast\mu`$ converts the prime-power divisor-sum row into the corresponding totient row at every finite stage. These are finite algebraic identities; no transcendence conclusion is attached to them.

<a id="mixed-differences-of-cyclotomic-layers."></a>

#### Mixed differences of cyclotomic layers.

For a function $`F:\{0,1\}^2\to\mathbb{Z}`$, define
``` math
\Delta F=F(1,1)-F(1,0)-F(0,1)+F(0,0)
```
([mixed difference](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L15)). If $`F(i,j)=u(i)+v(j)`$, then $`\Delta F=0`$ ([separable case](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L19)). Conversely, among integer linear combinations of the four values of $`F`$ whose coefficients sum to zero along each row and each column, the pattern $`(1,-1,-1,1)`$ is forced up to scale ([fixed-stencil uniqueness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L25)). For example, the table
``` math
\begin{array}{c|cc}
 &0&1\\ \hline
0&9&13\\
1&12&16
\end{array}
```
has mixed difference $`16-12-13+9=0`$; increasing only the lower-right entry by $`5`$ changes the mixed difference to $`5`$. The uniqueness statement is internal to this fixed $`2\times2`$ stencil. It does not assert invariance under larger stencils, nonlinear functionals, or another representation.

The formal development also records [a four-point divisor-layer identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L38) and [a centred representative for a residue class modulo an even modulus](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L55). The two unproved hypotheses and their target conclusion are as follows. For $`C:\mathbb{N}\to\mathbb{N}`$ and $`m,d\in\mathbb{N}`$, put
``` math
\begin{aligned}
\operatorname{Layer}(C,m)\quad\Longleftrightarrow\quad&
\exists Q_0\ \forall q\ge Q_0,\quad q\ {\rm prime}\Longrightarrow\\[-2pt]
&\hspace{5em}1<C(mq)\ \hbox{ and }\ \gcd(C(mq),mq)=1.
\end{aligned}
```
``` math
\begin{aligned}
\operatorname{BoundedOrder}(C,m,d)\quad\Longleftrightarrow\quad&
\forall q,p,\quad q,p\ {\rm prime},\ p\mid C(mq)\Longrightarrow\\[-2pt]
&\hspace{3em}\exists k,\quad 1\le k\le d\ \hbox{ and }\ mq\mid p^k-1.
\end{aligned}
```
``` math
\begin{aligned}
\operatorname{FinitePrimeEscape}(C,m)\quad\Longleftrightarrow\quad&
\forall\text{ finite sets }S\text{ of primes},\ \exists Q_0\
\ \forall q\ge Q_0,\\[-2pt]
&\hspace{3em}q\ {\rm prime}\Longrightarrow
\forall p\in S,\quad p\nmid C(mq).
\end{aligned}
```
These are the linked predicates [Layer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L88), [BoundedOrder](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L95), and [FinitePrimeEscape](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L102). The bounded-order condition does not assert an exact multiplicative order; it asserts only the displayed divisibility for some $`k\le d`$.

The implication from bounded order to finite-prime escape is a size argument in the paper. If $`m=0`$, the bounded-order condition forces $`C(0)=1`$. If $`m>0`$, the assertion is immediate for $`S=\varnothing`$; otherwise choose $`Q_0`$ so that $`mQ_0>\max_{p\in S}(p^d-1)`$. For every prime $`q\ge Q_0`$, a divisor $`p\in S`$ of $`C(mq)`$ would give $`mq\mid p^k-1`$ for some $`k\le d`$, hence $`mq\le p^k-1\le p^d-1`$, a contradiction. The layer hypothesis separately ensures that the layers are nontrivial and coprime to their indices. Neither hypothesis is proved here; polynomial-resultant realisability and Archimedean growth are also not established.

<a id="sec:frontier"></a>

# Open problems

Write $`H_t=\operatorname{lcm}(1,\dots,t)`$ ([definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/CarrySurvivorExtinction.lean#L515)), so that $`H_1=1`$, $`H_2=2`$, $`H_3=6`$, $`H_4=12`$, $`H_5=H_6=60`$ and $`H_7=420`$; and recall from Section <a href="#sec:results" data-reference-type="ref" data-reference="sec:results">1</a> the tail $`R_N=\sum_{m\ge1}\varphi(N+m)/2^{m}`$, which differs from $`2^NS`$ by an integer ([definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/TotientTailPeriodKiller.lean#L57)).

<a id="exact-equivalent-formulations"></a>

## Exact equivalent formulations

<div id="prob:diagonal" class="equivform">

*Equivalent formulation 1* (lcm-diagonal escape). For every $`t_0`$ there is a $`t\ge t_0`$ with $`R_{2H_t}-R_{H_t}\notin\mathbb{Z}`$.

</div>

By <a href="#res:equivalences" data-reference-type="ref" data-reference="res:equivalences">[res:equivalences]</a>, formulation <a href="#prob:diagonal" data-reference-type="ref" data-reference="prob:diagonal">1</a> is equivalent to irrationality of $`S`$. It identifies an exact decidable witness family, but is not claimed to reduce the difficulty of Erdős \#249. A finite list of successful certificates establishes the predicate only on its tested scales. Conversely, one pair $`h>0`$, $`N`$ with $`R_{N+h}-R_N\in\mathbb{Z}`$ already makes $`S`$ rational ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/LcmConeFlatness.lean#L357)).

The certificate is decidable at each $`t`$, and is kernel-checked at the $`28`$ listed scales between $`t=1`$ and $`t=64`$ ([list](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/DiagonalPincerCertificatesT64.lean#L1933), [verification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/DiagonalPincerCertificatesT64.lean#L1967)). The current pinned source strengthens that historical list to every $`t\le82`$, with no gaps ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Skip/LadderT67.lean#L71264)). The theorem through $`t=82`$ supplies no instance at $`t=83`$ and does not discharge the cofinal quantifier.

The cyclotomic form exposes more arithmetic structure. Write $`C(n)=|\Phi_n(2)|`$.

<div id="prob:cyclotomic" class="equivform">

*Equivalent formulation 2* (cyclotomic-anchored phase escape). For every $`h\ge1`$ and every $`N_0`$, there exist primes $`q,p`$ and $`L\in\mathbb{N}`$ such that
``` math
\gcd(p,hq)=1,\qquad p\mid C(hq),\qquad hq\mid p-1,
 \qquad p-1\ge N_0,
```
and $`(hq,p-1,L)`$ is a finite tail-difference certificate.

</div>

This is [CyclotomicAnchoredKillSupply](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L3042). For the binary layers, clean anchors satisfying every condition before the certificate are already supplied, and [the checked equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L3138) identifies formulation <a href="#prob:cyclotomic" data-reference-type="ref" data-reference="prob:cyclotomic">2</a> with irrationality of $`S`$. The unknown is phase escape of the totient discrepancy modulo $`2^L`$, not large prime divisors or multiplicative order. The checked $`p=331`$ instances are finite models of this exact predicate; unbounded support alone does not imply it.

<a id="stronger-sufficient-producer-problems"></a>

## Stronger sufficient producer problems

<div id="prob:fulldepth" class="problem">

**Problem 3** (full-depth period-multiple escape). For every $`d\ge1`$ and every $`N\in\mathbb{N}`$, is there a $`t\ge1`$ such that $`(td,N,td)`$ is a finite tail-difference certificate?

</div>

This is the depth-locked predicate [ApFullDepthEscape](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/PeriodMultipleEscape.lean#L162). It is stronger than the exact period-multiple characterisation because the certificate depth is forced to equal the period. A positive answer proves irrationality through [the checked consumer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/PeriodMultipleEscape.lean#L171); a negative answer eliminates this route only.

<div id="prob:firstharmonic" class="problem">

**Problem 4** (first-harmonic anti-concentration on supplier fibres). For each $`h\ge1`$, do there exist $`s\ge1`$ and $`0<\eta<1`$ such that, for every $`X_0`$, there are $`X,L`$ with
``` math
\max(X_0,1)\le X,\qquad h\le L-s,\qquad
 16(2X+h+L+2)\le2^L,
```
for which the four bounds below hold?

</div>

To make the question self-contained, put
``` math
\omega_N=\exp\!\left(2\pi i\,
   \frac{D_{h,N,L}\bmod 2^L}{2^L}\right),\qquad X\le N<2X.
```
At the pivot argument $`N+L-s+1`$, call $`N`$ a supplier when this integer factors as $`mp`$, where $`p`$ is its largest prime factor, $`0<m\le\sqrt X/2`$, and $`p>2\sqrt X`$. Suppliers are good when $`\eta m\le\varphi(m)`$ and bad otherwise; non-suppliers form the remaining set. For a supplier write $`z_N`$ for its explicit totient pivot phase, $`w_N=\omega_N/z_N`$, and $`\bar z_m`$ for the mean of $`z_N`$ on the fibre with cofactor $`m`$. Define
``` math
\begin{aligned}
 \mathcal C&=\sum_{N\ {\mathrm{good}}}w_N(z_N-\bar z_m),&
 \mathcal M&=\sum_{N\ {\mathrm{good}}}w_N\bar z_m,\\
 \mathcal B&=\sum_{N\ {\mathrm{bad}}}\omega_N,&
 \mathcal U&=\sum_{N\ {\mathrm{nonsupplier}}}\omega_N.
\end{aligned}
```
The exact identity is $`\sum_{X\le N<2X}\omega_N=\mathcal C+\mathcal M+\mathcal B+\mathcal U`$, and Problem <a href="#prob:firstharmonic" data-reference-type="ref" data-reference="prob:firstharmonic">4</a> asks precisely for
``` math
\operatorname{Re}\mathcal C\le\frac{14}{25}X,\qquad
 |\mathcal M|\le\frac1{100}X,\qquad
 |\mathcal B|\le\frac1{100}X,\qquad
 |\mathcal U|\le\frac8{25}X.
```
The decomposition is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/FirstHarmonicPivot.lean#L342), and the four budgets imply irrationality by [the checked consumer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/Erdos249257/FirstHarmonicPivot.lean#L405). An obstruction showing that available first- and second-moment information cannot force this modulo-$`2^L`$ small-ball estimate would also decisively close the present harmonic route.

<a id="structural-and-diophantine-routes"></a>

## Structural and Diophantine routes

<div id="prob:carryrank" class="problem">

**Problem 5** (totient carry-rank compression). Suppose $`v\ge1`$ and $`u:\mathbb{N}\to\mathbb{Z}`$ satisfy
``` math
u(N+1)=2u(N)-v\varphi(N+1),\qquad \frac{u(N)}{2^N}\longrightarrow0.
```
Must the span of the level-$`e`$ dyadic sections of $`u`$ have dimension less than $`2^e-1`$ for some $`e`$?

</div>

Rationality of $`S`$ would produce exactly such an integral tempered orbit, while the checked transport theorem forces its rank to be at least $`2^e-1`$ at every level. Thus a positive answer proves irrationality. A negative answer should ideally construct a control recurrence with the same integrality and decay architecture and near-maximal dyadic rank; infinite dimension of the totient $`2`$-kernel alone is not enough.

For a separate denominator-compression route, define the Möbius–Mersenne ladder
``` math
\Theta_r=\sum_{d\ge1}\frac{\mu(d)}{(2^d-1)^r},
 \qquad \Theta_2=S-\frac12.
```
The positive rank-one family has already been excluded at a quantitative scale: every admissible monomial quotient, and every positive finite average of them, exceeds $`\Theta_2`$ by more than $`1/480`$ ([rank-one gap](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/RankOneSubrankObstruction.lean#L238), [positive-sum gap](https://github.com/wcook04/plectis-lean-erdos249-257/blob/599f7e50a15b288f27f9b57ece16fdd396cb6d76/ErdosProblems/Erdos249/RankOneSubrankObstruction.lean#L300)).

<div id="prob:hankel" class="problem">

**Problem 6** (genuinely coupled denominator compression). Construct integers $`P_n`$ and $`Q_n>0`$ from a genuinely off-diagonal, vector-valued, or signed-cancellation Hankel–Schur–Padé kernel such that
``` math
0<Q_n\left|\Theta_2-\frac{P_n}{Q_n}\right|\longrightarrow0.
```
Alternatively, prove a structural no-go theorem for a clearly defined larger class of bounded-width coupled kernels.

</div>

Ordinary convergence of rational approximants is insufficient; the scaled error is the Diophantine quantity. The words “genuinely coupled” exclude the positive rank-one and positive direct-sum mechanisms already separated from $`\Theta_2`$ by the uniform gap.

<a id="independent-extension"></a>

## Independent extension

<div id="prob:oddprime" class="problem">

**Problem 7** (odd-prime totient kernels). For a fixed odd prime $`\ell`$, determine for every $`e`$ the exact dimension
``` math
\dim_{\mathbb{Q}}\operatorname{span}_{\mathbb{Q}}
 \{\,n\mapsto\varphi(\ell^j n+r):0\le j\le e,
       \ 0\le r<\ell^j\,\},
```
and give an explicit basis and a complete normal form for all rational relations. The first concrete case is $`\ell=3`$.

</div>

<div class="remark">

*Remark 2* (excluded generic mechanisms). Unbounded prime support, exact multiplicative order, natural-boundary information, ordinary Hankel nonvanishing, and positive rank-one averaging do not supply the missing binary phase or denominator compression. The finite Euler-factor and $`2\times2`$ mixed-difference identities of Section <a href="#sec:programmes" data-reference-type="ref" data-reference="sec:programmes">7</a> are tools rather than open endpoints; no growing-level Diophantine conclusion is claimed for them here.

</div>

A proof of formulation <a href="#prob:diagonal" data-reference-type="ref" data-reference="prob:diagonal">1</a> gives irrationality of $`S`$ by <a href="#res:equivalences" data-reference-type="ref" data-reference="res:equivalences">[res:equivalences]</a>. Its negation settles \#249 in the opposite direction: it supplies a positive-shift integral tail difference, which forces rationality. By contrast, failure of the sufficient producer bounds would rule out only their respective routes.

<a id="the-independent-denominator-exclusion."></a>

#### The independent denominator exclusion.

The constant $`7.96\times10^{34}`$ of <a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a> is the classical Farey mediant bound applied to a window with a free parameter $`K`$; it has order $`2^{K/2}`$, and raising it needs only more committed binary digits, which is a computation rather than an idea. It is not one of the open items of Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">8.5</a>.

<a id="sec:open"></a>

## Logical status and analytic input

1.  Irrationality of $`S`$ (<a href="#res:open" data-reference-type="ref" data-reference="res:open">[res:open]</a>). No proof is claimed.

2.  The lcm-diagonal and clean cyclotomic-anchor statements are exact equivalent formulations of <a href="#res:equivalences" data-reference-type="ref" data-reference="res:equivalences">[res:equivalences]</a>: they convert irrationality into the existence of an unbounded family of finite tail-difference certificates. Finite instances are checked — every $`t\le82`$, including the historical $`28`$-scale bank of Section <a href="#sec:frontier" data-reference-type="ref" data-reference="sec:frontier">8</a> — and the unbounded family is not. The equivalences fix the exact missing quantifier but do not make that quantifier easier to prove. <a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a> is a finite instance of a *different* family, the gap certificates of <a href="#res:supply" data-reference-type="ref" data-reference="res:supply">[res:supply]</a>, which reach irrationality by a one-way implication; the two families should not be counted together.

3.  Full-depth period-multiple escape and the four first-harmonic pivot bounds are stronger sufficient producers; they, and the prime-orbit gap the pivot bounds refine, are unproved. Failure of either would refute only that route.

4.  Carry-rank compression and genuinely coupled denominator compression are separate contradiction targets. No required upper bound or coupled approximant family is proved.

5.  The odd-prime kernel question is independent of the irrationality problem and carries no claimed answer or prior-art verdict.

The correlation source that fits the normalised totient most directly is Balasubramanian–Giri–Srivastav \[bgs2017\], not a direct transfer of the Tao–Teräväinen method. Write
``` math
g(n)=\frac{\varphi(n)}n
      =\sum_{d\mid n}\frac{\mu(d)}d=(f*1)(n),
  \qquad f(d)=\frac{\mu(d)}d\in\mathcal A_1 ,
```
the class $`\mathcal A_1`$ being the coefficient class in which the theorem cited next is stated. Theorem 2.2 of the arXiv version of \[bgs2017\] gives, uniformly for $`|h|\le x/2`$, an explicit asymptotic for $`\sum g(n)g(n-h)`$ with error $`O(\log^2x)`$; Remark 2.4 gives its Euler product, For each fixed $`h`$, the weighted partial-summation formula immediately following Corollary 2.8 permits $`Q(n)=n(n-h)`$, restoring the two linear factors needed to return from $`g(n)g(n-h)`$ to $`\varphi(n)\varphi(n-h)`$ with an explicitly propagated error. That displayed weighted formula is not itself stated uniformly in $`h`$ and starts its main integral at $`1`$, not $`H`$; retaining uniformity and the lower endpoint would require applying partial summation directly to Theorem 2.2. No later claim here relies on an unproved uniform weighted version.

Tao–Teräväinen’s quantitative correlation theorem (\[taoteravainen2025\], Theorem 3.1) assumes either quantitative equidistribution together with an exact small-prime condition, or non-pretentiousness. Here $`g(p)=1-1/p`$, so the stated small-prime condition does not hold, while $`\sum_p(1-g(p))/p=\sum_p1/p^2<\infty`$, so $`g`$ is pretentious to the constant function. Their theorem therefore does not apply unchanged. The Balasubramanian–Giri–Srivastav theorem supplies the missing first- and second-moment input in the correct divisor-convolution class, but it does *not* supply the residue small-ball or phase anti-concentration estimate needed to turn those moments into a certificate. That modulo-$`2^L`$ step is the precise remaining analytic gap; no irrationality conclusion is drawn from the correlation asymptotic alone.

<a id="formal-source-notes"></a>

# Formal source notes

<a id="registry-coverage."></a>

#### Registry coverage.

Two of the items above are checked propositions that no row of the claim registry currently owns: the three declarations of <a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a>, and the five of <a href="#res:weight" data-reference-type="ref" data-reference="res:weight">[res:weight]</a>; the supply implication of <a href="#res:supply" data-reference-type="ref" data-reference="res:supply">[res:supply]</a> is likewise unowned, and <a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a> cites three declarations of which the registry’s row owns one. Under this project’s own division of authority the registry, not a manuscript, owns public status, so the honest tag on those items is that they are kernel-checked and not yet registered. We print that rather than borrowing a neighbouring row’s status. The gap is a defect in the record, not in the proofs, and closing it is a review action rather than a mathematical one.

This manuscript is authored exposition, not proof authority. The linked Lean snapshot is authoritative only for its exact propositions, and kernel checking establishes that a proposition was proved, not that it is interesting, novel, or sufficient. The consequence drawn in the last sentence of <a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a>, the deduction in <a href="#res:periodic" data-reference-type="ref" data-reference="res:periodic">[res:periodic]</a> that an unbounded weight is not eventually periodic, the mechanism sentence in Section <a href="#sec:nogo" data-reference-type="ref" data-reference="sec:nogo">6</a>, and the size argument in Section <a href="#sec:programmes" data-reference-type="ref" data-reference="sec:programmes">7</a> are one-line arguments in the prose, marked as such; the first three are drawn from checked statements, and the last assumes the unproved bounded-order condition. The small numerical instances printed above — the level-three reductions, the certificate at $`(1,12,16)`$, the first values of $`A`$, the $`p=3`$ Euler-factor calculation, the mixed-difference table, and the values of $`H_t`$ — are computations from the definitions and checked identities beside them, and are not separate checked propositions. Results attributed to Allouche and Shallit, to Coons, to Bell and Smertnig, to Kaneko, Suzuki and Tachiya, to Luca and Tachiya, and to Tao and Teräväinen are cited from the literature and are not formalised here; the assessment that no prior source gives an explicit basis, an exact finite-level dimension formula, or a relation normal form for the totient $`2`$-kernel is the outcome of a literature search and is not a proof of non-existence.

*Scope of the AI declaration.* Large-language-model agents assisted throughout, drafting and revising this exposition, the Lean developments it links to, and the repository software that checks them. Will Cook set the objectives, selected and reviewed the public claims, checked the cited literature, and authorised this manuscript, and is responsible for its contents. Formal authority is the pinned kernel’s acceptance of an exact proposition; no model output carries any, and neither does this sentence.

Erdős Problem #249 remains open.

<div class="thebibliography">

10 J.-P. Allouche and J. Shallit, [*The ring of $`k`$-regular sequences*](https://cs.uwaterloo.ca/~shallit/Papers/as0.pdf), Theoret. Comput. Sci. **98** (1992), no. 2, 163–197, doi:[10.1016/0304-3975(92)90001-V](https://doi.org/10.1016/0304-3975(92)90001-V). Definitions 1.1 and 2.1 are on pp. 2–3 of the linked author preprint, which differs slightly from the published version; the cited definitions are unaffected. M. Coons, *(Non)Automaticity of number theoretic functions*, J. Théor. Nombres Bordeaux 22 (2010), no. 2, 339–352; [doi:10.5802/jtnb.718](https://doi.org/10.5802/jtnb.718); [arXiv:0810.3709](https://arxiv.org/abs/0810.3709). Theorem 3.2, pp. 348–349, in the published version (Theorem 3.3, pp. 8–9, in the preprint): $`\varphi`$ is not $`k`$-regular for any $`k\ge2`$. J. Bell and D. Smertnig, *Mahler series with multiplicative coefficient sequences*, 2026, [arXiv:2603.23456](https://doi.org/10.48550/arXiv.2603.23456). The totient generating series is not $`k`$-Mahler for any $`k\ge2`$, a consequence of their Theorem 1.3 recorded in the introduction. H. Kaneko, Y. Suzuki and Y. Tachiya, [*Refinements of Erdős’s irrationality criterion for certain sparse infinite series*](https://arxiv.org/abs/2601.20743), arXiv:2601.20743v1, 2026. Corollary 3 is on pp. 5–6 and proves irrationality for the $`\sigma(n)`$- and $`\varphi(n)`$-in-the-exponent families; its proof is on pp. 18–19. T. Tao and J. Teräväinen, *Quantitative correlations and some problems on prime factors of consecutive integers*, arXiv:2512.01739 (submitted December 2025, revised April 2026). Theorem 1.3 proves irrationality of $`\sum_{n\ge1}\omega(n)/2^n`$ at base $`2`$; the extension to every integer base and the $`\Omega`$ analogue are stated as remarks, with the modifications left to the reader. The theorem is on p. 4 and its proof is Section 5, pp. 44–56, in arXiv v2. R. Balasubramanian, S. Giri and P. Srivastav, *On correlations of certain multiplicative functions*, J. Number Theory 174 (2017), 221–238, [DOI](https://doi.org/10.1016/j.jnt.2016.10.001); [arXiv:1511.02221](https://arxiv.org/abs/1511.02221). The arXiv version’s Theorem 2.2 and Remark 2.4 give the uniform shifted divisor-convolution correlation and Euler product used above; the required fixed-shift weighted partial-summation formula follows Corollary 2.8. F. Luca and Y. Tachiya, [*Linear independence results for the values of divisor functions series*](https://www.kurims.kyoto-u.ac.jp/~kyodo/kokyuroku/contents/pdf/2014-14.pdf), RIMS Kôkyûroku No. 2014 (2017), 138–150. Theorem A on p. 139 explicitly restates their earlier Theorem 1.1 for nonzero purely periodic integer weights. Theorem 1 is on p. 139, its examples are on p. 140, and its proof is on pp. 149–150. P. Erdős, [*On arithmetical properties of Lambert series*](https://users.renyi.hu/~p_erdos/1948-04.pdf), J. Indian Math. Soc. (N.S.) **12** (1948), 63–66. The integer-base full-support theorem is on p. 63; the proof is on pp. 63–66, and the closing totient-series remark is on p. 66. P. Erdős and R. L. Graham, *Old and New Problems and Results in Combinatorial Number Theory*, 1980, p. 61. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). T. F. Bloom, [*Erdős Problem \#249*](https://www.erdosproblems.com/249), `erdosproblems.com/249`, accessed 28 July 2026 (page displays “last edited 28 September 2025”). The current record labels the problem open, cites `[ErGr80, p. 61]` and `[Er88c, p. 102]`, and explicitly describes its status as the website owner’s present assessment rather than a literature-completeness guarantee.

</div>
