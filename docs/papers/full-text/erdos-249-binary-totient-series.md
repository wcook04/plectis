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
is a $`\mathbb{Q}`$-basis for the span of the $`2`$-kernel of Euler’s totient. Thus the dyadic sections through level $`e`$ have rank exactly $`2^e+1`$ for every $`e\ge1`$, and two elementary identities generate all their rational linear relations. The basis and finite-rank statements are locally proved with novelty unassessed; the resulting infinite-dimensionality is also implied by Coons’s non-$`2`$-regularity theorem.

A second unconditional theorem determines the positive rank-one Möbius–Mersenne cone exactly. Its quotient has the unique minimizer $`(e,Y)=(1,5)`$; every admissible quotient and every nonempty finite positive mixture exceeds $`\Theta_2=S-1/2`$ by more than $`21/320`$. This rules out the complete positive rank-one and positive direct-sum mechanism, but not signed cancellation or genuinely coupled higher-rank approximants.

These structural theorems do not settle Erdős Problem #249, which asks whether
``` math
S=\sum_{n\ge1}\frac{\varphi(n)}{2^n}
```
is irrational. For $`H_a=\operatorname{lcm}(1,\ldots,2^a)`$ and $`R_a=\operatorname{totientTail}(2H_a)-\operatorname{totientTail}(H_a)`$, we prove the exact criterion
``` math
S\notin\mathbb{Q}
  \quad\Longleftrightarrow\quad
  \forall a_0\ \exists a\ge a_0, R_a\notin\mathbb{Z}
```
Canonical Mersenne-residue and full-depth forms sharpen this equivalence, but none supplies the needed nonintegral seed. Two quantitative routes also remain conditional: one separates the actual LCM orbit from the integers; the other controls four terms in a first-harmonic decomposition. Their cofinal hypotheses are unproved. The exact open boundary is therefore arithmetic control of the actual tail, not the finite-rank structure of the totient’s dyadic sections.

<div class="center">

<div class="minipage">

------------------------------------------------------------------------

**What is proved here**

**Unconditional structure.** The displayed family is a rational basis for the $`2`$-kernel of Euler’s totient, so the sections through level $`e`$ have rank exactly $`2^e+1`$. The positive rank-one Möbius–Mersenne cone also has an exact unique minimizer and a uniform gap. **Series reduction.** Irrationality is equivalent to nonintegrality of the actual LCM-tail differences cofinally. **Open boundary.** The basis theorem and cone obstruction do not supply even one required nonintegral seed.

</div>

</div>

<a id="sec:results"></a>

# Introduction and main results

Erdős Problem #249 asks whether
``` math
S=\sum_{n\ge1}\frac{\varphi(n)}{2^n}
```
is irrational; see Erdős and Graham \[erdosgraham1980, p. 61\] and Erdős \[erdos1988, p. 102\]. Bloom’s current catalogue record reproduces this question and labels it open, while explicitly warning that the status is the website owner’s present assessment and may omit relevant literature \[erdosproblems\]. We therefore use the catalogue for numbering and current reported status only; the two original sources carry the problem statement.

The principal unconditional result is structural: the two zero-residue sections $`\varphi_{0,0}`$ and $`\varphi_{1,0}`$, together with the odd-residue sections, form a rational basis, and the two reduction identities below generate every rational relation among the sections. It gives exact finite-level rank but no rationality-to-finite-rank bridge. The positive rank-one Möbius–Mersenne cone is also determined sharply: one unique minimizer, the uniform $`21/320`$ floor, the $`1/16`$ versus $`1/15`$ boundary, and closure under arbitrary finite positive mixing.

The closest results concerning the open series are exact reformulations and conditional criteria. The actual power-two LCM orbit gives a cofinal nonintegrality equivalence; the canonical Mersenne formulation removes the remote basepoint; and the full-depth theorem shows that one seed gives eventual $`2`$-syndeticity on its ray. The independent first-harmonic argument turns four explicit fibre bounds into a $`9X/10`$ window estimate, but irrationality requires their unproved cofinal form. The example $`38=2\cdot19`$ rules out the simplest global-isolation argument. The remaining inventory records finite Farey and diagonal certificates, Lambert and gcd-moment identities, and explicit limits of fixed-precision methods. None supplies the required cofinal input.

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.

Each *Checked* line below links the relevant declarations at commit `99f4bf47422a`. The bracketed tags reproduce the public status recorded by the claim registry; where no registry row owns the cited declarations, the text says so rather than assigning a neighbouring status.

Throughout $`\mathbb{N}=\{0,1,2,\ldots\}`$ and $`\varphi(0)=0`$. Thus $`\varphi_{j,r}(n)=\varphi(2^jn+r)`$, for $`j\ge0`$ and $`0\le r<2^j`$, is the $`(j,r)`$ *dyadic section* of Euler’s totient, a vector in $`\mathbb{Q}^{\mathbb{N}}`$, and $`j`$ is its *level*; the family of all of them is the $`2`$-kernel $`\mathcal K_2(\varphi)`$ in the sense of Allouche and Shallit \[allouche-shallit\]. Two elementary identities relate them: the *reductions* $`\varphi_{j+1,0}=2^{j}\varphi_{1,0}`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L160)) and $`\varphi_{j,\,2^{t+1}s}=2^{t}\varphi_{j-t-1,\,s}`$ for $`s`$ odd with $`2^{t+1}s<2^j`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L169)). At level $`3`$, for instance, they give $`\varphi_{3,0}=4\varphi_{1,0}`$, $`\varphi_{3,2}=\varphi_{2,1}`$, $`\varphi_{3,4}=2\varphi_{1,1}`$ and $`\varphi_{3,6}=\varphi_{2,3}`$, while the four odd residues $`r=1,3,5,7`$ are reduced by neither; numerically $`\varphi_{3,4}(1)=\varphi(12)=4=2\varphi(3)=2\varphi_{1,1}(1)`$. So beyond $`\varphi_{0,0}`$ and $`\varphi_{1,0}`$ each level contributes only its odd residues, and the count through level $`e`$ is $`2+\sum_{j=1}^{e}2^{j-1}=2^e+1`$; <a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a> says that count is the exact dimension.

Two objects built from $`S`$ recur below. The *scaled tail* $`R_N=\sum_{m\ge1}\varphi(N+m)/2^m`$ is $`2^N`$ times the part of the series beyond index $`N`$; since $`2^NS=\Phi_N+R_N`$ with $`\Phi_N=\sum_{1\le n\le N}\varphi(n)2^{N-n}`$ an integer ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailPeriodKiller.lean#L150)), $`R_N`$ and $`2^NS`$ differ by an integer. For $`h,N,L\in\mathbb{N}`$, put
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
([definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailPeriodKiller.lean#L72)). It exists to make a statement about an infinite tail decidable by a finite computation, and it is faithful: some depth $`L`$ certifies $`(h,N)`$ if and only if $`R_{N+h}-R_N\notin\mathbb{Z}`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmConeFlatness.lean#L316)). For example,
``` math
D_{1,12,16}=-143140,\qquad
  \rho_{1,12,16}=53468,\qquad N+h+L+2=31,
```
so $`(1,12,16)`$ is a certificate. More generally, the test succeeds at $`(h,12,16)`$ for every $`h`$ with $`1\le h\le8`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailPeriodKiller.lean#L404)), so none of $`R_{13}-R_{12},\dots,R_{20}-R_{12}`$ is an integer ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailPeriodKiller.lean#L407)).

A third recurring object is an *integral scaled-tail sequence with multiplier $`v`$*. For a coefficient sequence $`c:\mathbb{N}\to\mathbb{N}`$ and an integer $`v\ge1`$, this is an integer sequence $`u`$ satisfying
``` math
u(N+1)=2u(N)-v\,c(N+1)\quad\hbox{for every }N,
  \qquad
  \frac{u(N)}{2^N}\longrightarrow0
```
([definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GenericTailOrbitRigidity.lean#L67)); for $`c=\varphi`$ such a pair $`(v,u)`$ with $`v\ge1`$ exists exactly when $`S`$ is rational (Section <a href="#sec:carry-rank" data-reference-type="ref" data-reference="sec:carry-rank">4</a>).

1.  <span id="res:canonicalmersenne" label="res:canonicalmersenne"></span> <span class="smallcaps">\[formalised here\]</span> **Canonical Mersenne arithmetic frontier.** Let
    ``` math
    B_{H,N}=\sum_{j=0}^{H-1}\varphi(N+1+j)2^{H-1-j},\qquad
     \rho_{H,N,M}=(-B_{H,N})\bmod M.
    ```
    For every $`c,v\in\mathbb{N}`$ with $`v>0`$ and $`\gcd(2,v)=1`$, the statement that there are $`H,M\in\mathbb{N}`$ with
    ``` math
    H>0,\qquad \varphi(v)\mid H,\qquad vM=2^H-1,
     \qquad c+H+1<\rho_{H,c,M}<M-(c+H+1)
    ```
    is equivalent, after quantifying over $`c,v`$, to irrationality of $`S`$. The basepoint is exactly $`c`$, the dyadic valuation of a prospective rational denominator; the older centred-residue condition searched for a remote $`N\ge\max(c,N_0)`$. The canonical statement implies that older condition by feeding $`\max(c,N_0)`$ into its $`c`$-slot. Moreover, whenever $`M\mid2^H-1`$, the finite residue obeys the exact recurrence
    ``` math
    \rho_{H,N+1,M}
     =\bigl(2\rho_{H,N,M}-(\varphi(N+H+1)-\varphi(N+1))\bigr)\bmod M.
    ```
    This removes analytic tails, carry trajectories, and remote-basepoint search from the equivalent residual, but it does not prove the required central gap. *Checked:* [residue recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L2322), [dominance over the remote condition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L3132), [exact equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L3165).

2.  <span id="res:fulldepth" label="res:fulldepth"></span> <span class="smallcaps">\[formalised here\]</span> **Full-depth ray amplification and exactness.** Fix $`d>0`$ and $`N`$. If $`(d,N,L)`$ is a finite tail-difference certificate at any depth $`L`$, then there is $`T>0`$ such that every pair $`\{t,t+1\}`$ with $`t\ge T`$ contains a multiplier $`m`$ for which $`(md,N,md)`$ is a certificate. Thus one seed forces an eventually $`2`$-syndetic family whose depth equals its period. Pointwise,
    ``` math
    \exists t>0:\ (td,N,td)\text{ is certified}
     \quad\Longleftrightarrow\quad R_{N+d}-R_N\notin\mathbb{Z}.
    ```
    Consequently the predicate demanding such a full-depth certificate for every $`d>0,N`$ is equivalent to irrationality of $`S`$. Its cofinal-in-$`N`$ version is equivalent both to the older arbitrary-depth period-multiple condition and to irrationality. Thus requiring full depth loses no strength; it does not produce the first non-integral shift or seed. *Checked:* [eventual two-syndeticity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L364), [pointwise equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L388), [global equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L406), [cofinal depth deletion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L421), [cofinal endpoint](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L438).

3.  <span id="res:basis" label="res:basis"></span> <span class="smallcaps">\[unconditional progress\]</span> **Basis theorem.** The family $`\mathcal B=\{\varphi_{0,0},\varphi_{1,0}\}\cup\{\varphi_{j,r}:j\ge1,\ r\ \text{odd},\
    0<r<2^j\}`$ is linearly independent over $`\mathbb{Q}`$ and spans the same $`\mathbb{Q}`$-subspace of $`\mathbb{Q}^{\mathbb{N}}`$ as $`\mathcal K_2(\varphi)`$; so $`\mathcal B`$ is a basis of that span, which is therefore infinite-dimensional. Since the reductions make every remaining section a rational multiple of a member of $`\mathcal B`$, the $`\mathbb{Q}`$-linear relations among dyadic sections of $`\varphi`$ are exactly those the reductions generate — a one-line consequence of the checked statements, not a further one. *Checked:* [independence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L1265), [span equality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L1380), [basis](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L1392). *Registry:* `dyadic_totient_basis`.

4.  <span id="res:rank" label="res:rank"></span> <span class="smallcaps">\[unconditional progress\]</span> **Exact finite-level rank.** For every $`e\ge0`$ the $`2^e+1`$ sections $`\varphi_{0,0}`$, $`\varphi_{1,0}`$ and $`\varphi_{j,r}`$ with $`1\le j\le e`$, $`r`$ odd, $`0<r<2^j`$ are linearly independent over $`\mathbb{Q}`$, so their span has dimension exactly $`2^e+1=2+\sum_{j=1}^{e}2^{j-1}`$: exact, not an estimate, because the even residues are already dependent by the reductions. Read instead as a truncation of the kernel, $`V_e=\operatorname{span}_{\mathbb{Q}}\{\varphi_{j,r}:0\le j\le
    e\}`$ has $`\dim V_e=2^e+1`$ for every $`e\ge1`$, and $`\dim V_0=1`$: the counted family carries $`\varphi_{1,0}`$, which is a level-one section, so the two readings agree from $`e=1`$ on and differ only at $`e=0`$. At $`e=1`$ both readings say that $`\varphi(n)`$, $`\varphi(2n)`$ and $`\varphi(2n+1)`$ are linearly independent over $`\mathbb{Q}`$. The independence half of <a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a> follows by finite character; the span equality needs the reductions as well. *Checked:* [independence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L935), [dimension](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L989), [the exact finite-truncation rank](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L1084); the latter is the complete truncation wrapper, with its explicit hypothesis $`e\ge1`$, while the canonical-family rank is the intermediary because even residues reduce to the odd-core family. [infinite-dimensionality directly](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L1145).

5.  <span id="res:rankonefloor" label="res:rankonefloor"></span> <span class="smallcaps">\[unconditional progress\]</span> **Sharp positive rank-one and direct-sum floor.** Put
    ``` math
    \Theta_2=\sum_{d\ge1}\frac{\mu(d)}{(2^d-1)^2}=S-\frac12,
     \qquad
     Q(e,Y)=
     \frac{\bigl(\sum_{d=1}^{Y}\mu(d)/(2^d-1)^{e+2}\bigr)^2}
          {\sum_{d=1}^{Y}\mu(d)/(2^d-1)^{2e+2}}.
    ```
    For every $`e\ge1`$ and $`Y\ge4`$, the quotient $`Q(e,Y)`$ is uniquely minimized at $`(1,5)`$ and satisfies $`Q(e,Y)-\Theta_2>21/320>1/16`$. The stronger unit-fraction floor $`1/15`$ fails already at $`(1,5)`$. Every nonempty finite positive weighted average of admissible $`Q(e,Y)`$ has the same strict $`21/320`$ separation. In rational-linear-form language, if $`Q(e,Y)=p/q`$ with $`p\in\mathbb{Z}`$ and $`q\ge1`$, then $`|q\Theta_2-p|>21q/320`$. Hence neither adding atoms nor taking positive direct sums can repair this rank-one approximation mechanism; signed cancellation and genuinely coupled higher-rank kernels remain outside the theorem. *Checked:* [unique minimizer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L534), [uniform $`21/320`$ floor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L624), [$`1/16`$ floor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L634), [$`1/15`$ failure](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L645), [positive direct sums](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L655), [rational linear-form obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/RankOneSharpFloor.lean#L693).

6.  <span id="res:index" label="res:index"></span> <span class="smallcaps">\[formalised here\]</span> **Canonical all-base index and unique coordinates.** For every integer $`k\ge2`$ and level $`e`$, the two zero-residue channels are followed at level $`j+1`$ by the unique coordinates $`r=kq+(d+1)`$ with $`q<k^j`$ and $`d<k-1`$. Equivalently, every integer $`1\le r<k^{j+1}`$ with $`k\nmid r`$ has one and only one such representation. The level block therefore has $`k^{j+1}-k^j`$ coordinates, and the complete finite index has exactly $`2+\sum_{j<e}k^j(k-1)=k^e+1`$ elements. This is the concrete quotient and nonzero-last-digit mechanism behind the all-base rank statement: it counts the canonical candidates and proves the reduction coordinates, but it does not prove their linear independence. *Checked:* [coordinate specification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelIndex.lean#L124), [unique representation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelIndex.lean#L213), [level count](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelIndex.lean#L241), [full index count](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelIndex.lean#L277).

7.  <span id="res:denominator" label="res:denominator"></span> <span class="smallcaps">\[formalised here\]</span> **Denominator exclusion, sharp for its window.** If $`S=a/q`$ with $`a\in\mathbb{Z}`$ and $`q\ge1`$ then $`q>79\,639\,646\,646\,701\,375\,323\,355\,774\,875\,831\,053\approx7.96\times10^{34}`$. The constant is optimal for the window that produces it — the window here is the pair $`(N,K)=(1,240)`$, meaning $`240`$ committed binary digits of the series shifted by one — in the sense that the next integer up is the exact first denominator at which that window’s certificate fails. The method is the classical Farey mediant argument (Section <a href="#sec:denominator" data-reference-type="ref" data-reference="sec:denominator">5</a>). *Checked:* [exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18371), [reduced-denominator form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18384), [first failure](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GapFareyBound.lean#L225). *Registry:* the row owns the reduced-denominator form only.

8.  <span id="res:carryrank" label="res:carryrank"></span> <span class="smallcaps">\[formalised here\]</span> **Rank lower bound for a rational scaled-tail sequence.** If $`S`$ were rational then some integral scaled-tail sequence $`u`$ for the coefficients $`\varphi`$, with positive multiplier, would have for *every* $`e`$ dyadic sections through level $`e`$ — formed from $`u`$ exactly as the $`\varphi_{j,r}`$ are formed from $`\varphi`$ — spanning a space of dimension at least $`2^e-1`$. The same lower bound holds for every positive-multiplier integral scaled-tail sequence. This statement is specific to that binary scaled-tail representation; it does not constrain arguments formulated only through the Lambert weight, the coprimality identity, or tail differences. It is not an irrationality criterion, because no finite-rank upper bound is proved for the scaled-tail sequences supplied by rationality. *Checked:* [the barrier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientCarryKernelRigidity.lean#L300), [rank transport from <a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a>](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientCarryKernelRigidity.lean#L211).

    The orbit-level form sharpens this rank barrier without closing it: under the same non-irrationality hypothesis, the same carry also has uniformly eventual dyadic-section periodicity modulo $`v`$, as recorded by [the modular-period/rank frontier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailCarryPeriod.lean#L224). This does not turn quotient periodicity into a finite-$`\mathbb Q`$-rank bound. Indeed, if $`p\mid v`$, the totient forcing disappears modulo $`p`$ and the carry is the homogeneous geometric orbit $`u_N\equiv2^N u_0`$ modulo $`p`$ ([forcing vanishing](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailCarryPeriod.lean#L126); [geometric reduction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailCarryPeriod.lean#L140)). This is the natural obstruction to extracting the missing finite-rank upper bound, so the irrationality of $`S`$ remains open.

9.  <span id="res:weight" label="res:weight"></span> <span class="smallcaps">\[checked; no registry row\]</span> **The \#249 weight.** $`S=\sum_{d\ge1}A(d)/(2^d-1)`$ with $`A=\varphi*\mu`$, the Dirichlet convolution $`A(n)=\sum_{d\mid n}\varphi(d)\mu(n/d)`$; here $`A\ge0`$, $`A(p)=p-2`$, $`A(p^k)=\varphi(p^k)-\varphi(p^{k-1})`$, and $`A`$ is unbounded. Its values at $`n=1,\dots,10`$ are $`1,0,1,1,3,0,5,2,4,0`$. *Checked:* [identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18445), [sign](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MersenneLambertLadder.lean#L370), [primes](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MersenneLambertLadder.lean#L297), [prime powers](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MersenneLambertLadder.lean#L272), [unboundedness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MersenneLambertLadder.lean#L321). *Registry:* the Lambert-ladder row owns the neighbouring rungs, not these five declarations; see the formal source notes below.

10. <span id="res:gcdmoment" label="res:gcdmoment"></span> <span class="smallcaps">\[proved here\]</span> **Squared Lambert layers expose a first gcd moment.** The two exact identities
    ``` math
    \sum_{d\ge1}\frac{1}{(2^d-1)^2}
        =\sum_{n\ge1}(\sigma(n)-\tau(n))2^{-n},
      \qquad
      \sum_{d\ge1}\frac{\varphi(d)}{(2^d-1)^2}
        =\sum_{n\ge1}(\mathsf P(n)-n)2^{-n},
    ```
    where $`\mathsf P(n)=\sum_{e\mid n}\varphi(e)(n/e)`$, are checked in the source. For the independent fair-coin geometric waiting times used below, the second left-hand side is $`\mathbb E[\gcd(X,Y)]`$: the factor $`(2^d-1)^{-2}`$ is the mass of the event $`d\mid X`$ and $`d\mid Y`$, and $`\sum_{d\mid g}\varphi(d)=g`$. This exact first-moment identity does not imply irrationality of $`S`$; no novelty claim is made for the divisor algebra. *Checked:* [divisor-count layer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GcdMomentCalculus.lean#L216), [first gcd moment](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GcdMomentCalculus.lean#L235).

11. <span id="res:squareenclosure" label="res:squareenclosure"></span> <span class="smallcaps">\[proved here\]</span> **A sharp squared-Mersenne diagonal enclosure.** For the diagonal tail difference $`R_{2H}-R_H`$, let
    ``` math
    C_{H,D}=Z_H+2^H(2^H-1)\left(\frac12+
       \sum_{1\le d\le D}\frac{\mu(d)}{(2^d-1)^2}\right),
     \qquad Z_H=\Phi_H-\Phi_{2H}.
    ```
    The exact decomposition is
    ``` math
    R_{2H}-R_H-C_{H,D}
     =2^H(2^H-1)\sum_{d>D}\frac{\mu(d)}{(2^d-1)^2},
    ```
    and the signed remainder has the sharp elementary bound
    ``` math
    \left|R_{2H}-R_H-C_{H,D}\right|
     \le \frac{4\,2^H(2^H-1)}{3(2^{D+1}-1)^2}.
    ```
    Consequently, if this radius is smaller than the distance from $`C_{H,D}`$ to every integer, the diagonal cannot be integral. The centre is rational and its denominator is explicitly reduced by the gcd with $`2^H(2^H-1)`$; the separation hypothesis is the remaining arithmetic input. This finite criterion gives neither an unbounded separation family nor irrationality of $`S`$. *Checked:* [exact centre decomposition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquaredMersenneDiagonalEnclosure.lean#L138), [sharp enclosure](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquaredMersenneDiagonalEnclosure.lean#L408), [separation criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquaredMersenneDiagonalEnclosure.lean#L426); [target equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FullTargetPrimeAdjunctionNoGo.lean#L139).

12. <span id="res:freshprimedeficit" label="res:freshprimedeficit"></span> <span class="smallcaps">\[proved here\]</span> **Fresh-prime support is an explicit endpoint deficit.** For $`H>0`$, put $`g_H(s)=\gcd(\operatorname{rad}(H),s)`$ and
    ``` math
    M_H(k,s)=\frac{kH+s}{g_H(s)}\varphi(g_H(s)),
     \qquad F_H(k,s)=M_H(k,s)-\varphi(kH+s).
    ```
    The old-prime mass $`M_H(k,s)`$ dominates the actual totient, so $`F_H(k,s)\ge0`$. If $`\Delta_H(s)=\varphi(2H+s)-\varphi(H+s)`$, then
    ``` math
    \Delta_H(s)=\Delta_H^{\rm old}(s)+F_H(1,s)-F_H(2,s),
    ```
    and the literal foreign channel is exactly the same lower-minus-upper deficit. The second-difference and five-point curvature operators preserve this decomposition; the latter is bounded below by the old-prime branch minus
    ``` math
    8F_H(1,s)+4F_H(2,s+1)+2F_H(2,s+2)+F_H(2,s+3)+F_H(2,s+4).
    ```
    This isolates the hard issue: new prime support has a known sign, but no cofinal bound on its adverse placement is proved. In particular, this is a finite curvature-loss budget, not an irrationality proof. *Checked:* [endpoint nonnegativity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FreshPrimeDeficitDecomposition.lean#L91), [foreign-channel identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FreshPrimeDeficitDecomposition.lean#L184), [five-point loss bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FreshPrimeDeficitDecomposition.lean#L269).

13. <span id="res:squarecrt" label="res:squarecrt"></span> <span class="smallcaps">\[proved here\]</span> **Finite square-CRT correction suppression.** Let $`E`$ be a finite family of distinct primes $`p_i`$, with anchors $`A_i`$, and let $`J<p_i`$ for every $`i\in E`$. A common square-CRT base $`n`$ can be chosen with
    ``` math
    n<\left(\prod_{i\in E}p_i^2\right)(\sup_{i\in E}A_i+2),
     \qquad n=A_i+p_i^2t_i
    ```
    for suitable $`t_i`$. Therefore every $`1\le h\le J`$ obeys
    ``` math
    \varphi(n+p_i h-A_i)=(p_i-1)\varphi(p_i t_i+h).
    ```
    The congruence removes the $`p_i`$-divisibility correction on the whole finite horizon, simultaneously across the family. Checked regression witnesses show why this is not already a separation theorem: one clean block has both displayed coefficients zero (at base $`52`$), while another clean block has a displayed coefficient $`-4`$ (at base $`27`$). Thus the CRT mechanism controls a finite local error term but supplies neither a cofinal gap nor an irrationality criterion. *Checked:* [simultaneous finite family](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L297), [finite horizon](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L327), [vanishing block](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L459), [nonzero block](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L477).

14. <span id="res:slackcriterion" label="res:slackcriterion"></span> <span class="smallcaps">\[conditional reduction\]</span> **Canonical strict-jump slack reduction.** Put
    ``` math
    \begin{aligned}
     m_t&=\operatorname{canonicalAdjacentSuffixDepth}(t),\\
     d_t&=\operatorname{diagonalAdjacentSuffixResidue}(t,0,m_t),
     \end{aligned}
    ```
    and define the integer slack
    ``` math
    \lambda_t=\min\!\left(d_t-2^{m_t-5},
           (2^{m_t}-2^{m_t-5})-d_t\right).
    ```
    The two-sided central-band test at $`t`$ is equivalent to $`\lambda_t\ge0`$. Moreover, the existence, beyond every threshold, of a strict LCM jump $`H_t<H_{t+1}`$ with $`\lambda_t\ge0`$ is equivalent to the corresponding central-band condition; either cofinal condition implies that $`S`$ is irrational. This exposes one integer observable for exact computation and recurrence arguments, but the cofinal sign assertion itself remains open. *Checked:* [centrality equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalFreshLossBridge.lean#L2667), [equivalence of the two conditions](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalFreshLossBridge.lean#L2757), [conditional irrationality theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalFreshLossBridge.lean#L2932).

15. <span id="res:foreignresidue" label="res:foreignresidue"></span> <span class="smallcaps">\[conditional reduction\]</span> **Finite foreign-residue projection.** For $`H,D\in\mathbb{N}`$, split the finite Möbius-residue diagonal into the channels whose indices divide $`H`$ and those that do not. The checked identity is
    ``` math
    \begin{aligned}
     \operatorname{finiteResidueDiagonal}(H,D)
       &=\operatorname{projectedForeignDefect}(H,D)\\
       &\quad+\operatorname{projectedDivisorChannels}(H,D).
     \end{aligned}
    ```
    When $`H\le D`$, the divisor term is exactly the explicit radical Möbius shadow. If $`2H\le D`$, every finite omitted window is bounded by
    ``` math
    B_{H,D}=\operatorname{diagonalCoefficient}(H)\left(
           \frac{2}{2^D}+\frac{4}{3\,4^D}\right).
    ```
    Thus a controlled comparison of the limiting foreign defect with $`B_{H,D}`$, together with separation of the projected state from every integer, forces a full-target miss. The analytic comparison and an unbounded supply of separated projections remain unproved; this is a conditional reduction, not an irrationality theorem. *Checked:* [finite complement bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/ActualForeignResidueProjection.lean#L276), [exact channel split](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/ActualForeignResidueProjection.lean#L308), [conditional target-miss theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/ActualForeignResidueProjection.lean#L414).

16. <span id="res:actualorbit" label="res:actualorbit"></span> <span class="smallcaps">\[exact reformulation\]</span> **Actual LCM orbit frontier.** Let $`H_a=\operatorname{lcm}(1,\ldots,2^a)`$ and $`R_a=\operatorname{totientTail}(2H_a)-\operatorname{totientTail}(H_a)`$. Then $`S`$ is irrational if and only if, beyond every threshold $`a_0`$, some $`a\ge a_0`$ has $`R_a\notin\mathbb{Z}`$. This is an exact cofinal nonintegrality criterion for the actual LCM diagonal, not a quantitative separation estimate and not a proof that such indices occur. *Checked:* [exact frontier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitNonintegrality.lean#L37), [forward implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitNonintegrality.lean#L53).

17. <span id="res:actualsign" label="res:actualsign"></span> <span class="smallcaps">\[unconditional progress\]</span> **Positive LCM corridor and top-edge boundary.** For $`a\ge8`$ and $`J+(a+6)<2\cdot2^a`$, the true translated orbit difference $`\operatorname{totientTail}(2H_a+J)-\operatorname{totientTail}(H_a+J)`$ is strictly positive. If it is represented by an integer and the dyadic modulus has room for the directed endpoint strip, the carry survivor is strictly negative and the discrepancy residue is exactly the top-edge representative $`2^K-\text{carry}_K`$, lying strictly between the strip’s lower edge and $`2^K`$. Thus the positive corridor eliminates the nonnegative true survivor but does not itself produce a central-band contradiction; an independent arithmetic exclusion of the top boundary is still required. *Checked:* [positive corridor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSign.lean#L39), [negative survivor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSign.lean#L172), [top-edge residue](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSign.lean#L211).

18. <span id="res:factorideal" label="res:factorideal"></span> <span class="smallcaps">\[unconditional progress\]</span> **LCM factor-ideal shift-algebra no-go.** For every $`t\ge3`$, with $`H=\operatorname{lcm}(1,\ldots,t)`$, there is a nonzero synthetic dyadic coboundary whose forcing letters reproduce the actual totient differences at $`t-2`$ prescribed indices and lie in the ideal generated by $`\varphi(H)`$. Every finite integer shift polynomial preserves the exact coboundary cancellation, the $`H`$-factor ideal and all lower factor ideals, together with uniform state and letter bounds. A sparse-anchor variant also preserves every prescribed whole-ray anchor. Hence factor ideals, finite shift-algebra closure and these bounds cannot by themselves force a contradiction. The witness is synthetic: its letters are not claimed to be actual totient differences, nonlinear combinations are outside the theorem, and no cofinal family of certificates follows. *Checked:* [finite shift-algebra no-go](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmFactorIdealPulseObstruction.lean#L798), [sparse-anchor no-go](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmFactorIdealPulseObstruction.lean#L866).

19. <span id="res:periodic" label="res:periodic"></span> <span class="smallcaps">\[unconditional progress\]</span> **Eventually periodic weights are settled.** For every integer base $`b\ge2`$, if $`\gamma\colon\mathbb{N}\to\mathbb{Q}`$ is eventually periodic, nonnegative and positive at some positive index of its periodic part, then $`\sum_{a\ge1}\gamma(a)/(b^a-1)`$ is irrational. Theorem A in Luca and Tachiya’s 2017 open-access RIMS paper restates their earlier signed theorem in the exact purely-periodic integer case: every nonzero purely periodic integer sequence gives an irrational Lambert value at every integer base $`|q|>1`$ \[lucatachiya2017, Theorem A, p. 139\]. Their Theorem 1 strengthens the nonnegative case to linear independence of each finite divisor-convolution ladder \[lucatachiya2017, Theorem 1, p. 139; proof pp. 149–150\]. Clearing the common denominator of a rational period and subtracting the finite rational prefix shows that Theorem 1 already proves the eventual nonnegative rational claim above; the checked theorem gives an independent formal proof. By <a href="#res:weight" data-reference-type="ref" data-reference="res:weight">[res:weight]</a> the weight $`A`$ is unbounded, hence not eventually periodic, so \#249 is outside this class. *Checked:* [the periodic theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L12811).

20. <span id="res:primindex" label="res:primindex"></span> <span class="smallcaps">\[proved here\]</span> **No fixed common denominator clears the normalised weight.** For every integer $`D\ge1`$ some $`n\ge1`$ has $`D\cdot A(n)/n\notin\mathbb{Z}`$ — for $`D=6`$ at the prime $`n=7`$, where $`A(7)/7=5/7`$ — and any $`D`$ clearing every coordinate up to a horizon $`N\ge4`$ is divisible by an explicit two-tier primorial ($`4`$ at $`p=2`$, $`p^2`$ when $`p^2\le N`$, else $`p`$). No argument that clears the coordinates $`A(n)/n`$ by a single positive integer valid at all $`n`$ can therefore succeed. This obstruction is caused by the normalisation: the unnormalised weights $`A(n)`$ are integers. Arguments whose common denominator grows with the horizon, arguments using the integral weights directly, and arguments that never clear these coordinates are untouched. *Checked:* [no fixed index](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/PrimitiveDeterminantLift.lean#L169), [the primorial divisibility](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/PrimitiveDeterminantLift.lean#L148).

21. <span id="res:equivalences" label="res:equivalences"></span> <span class="smallcaps">\[proved here\]</span> **Four exact characterisations of irrationality.** Irrationality of $`S`$ is equivalent to each of: non-integrality of the tail difference $`R_{N+h}-R_N`$ at every $`N`$ and every shift $`h\ge1`$, equivalently a certificate at every such pair; a certificate at every $`h\ge1`$ and at arbitrarily large $`N`$; and the same at the scales $`N=h=\operatorname{lcm}(1,\dots,t)`$, for arbitrarily large $`t`$. A fourth equivalence, independent of the certificate language, is a counted anti-concentration condition on window phases. These characterisations identify the unbounded input exactly; they retain the full difficulty of \#249 and do not prove that input. *Checked:* [pointwise](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmConeFlatness.lean#L399), [cofinal at each shift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmConeFlatness.lean#L412), [$`\operatorname{lcm}`$ diagonal](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmConeFlatness.lean#L426), [window-separated pairs](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/PivotAntiReconstruction.lean#L1765).

22. <span id="res:supply" label="res:supply"></span> <span class="smallcaps">\[conditional reduction\]</span> **A denominator-indexed gap-certificate hypothesis.** Suppose that for each denominator $`q`$ there is a truncation window $`(N,K)`$ whose totient residue avoids a band of width $`q(N{+}K{+}2)`$ out of $`2^K`$. This hypothesis *implies* irrationality. It concerns a second certificate family, not the one of <a href="#res:equivalences" data-reference-type="ref" data-reference="res:equivalences">[res:equivalences]</a>: the band scales with $`q`$, and the family is indexed by denominators rather than by shifts. The converse is not proved and is not claimed. *Checked:* [the conditional implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L16025). *Registry:* no row currently owns this declaration.

23. <span id="res:open" label="res:open"></span> <span class="smallcaps">\[open\]</span> **Erdős #249.** Whether $`S`$ is irrational. Not proved here.

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
| $`\tau`$ | $`1.6066951\ldots=E`$ | $`g\equiv1`$ | The Erdős–Borwein constant; irrational \[erdos1948, theorem on p. 63\]; formalised here in the Lambert form $`\sum_{d\ge1}(2^d-1)^{-1}`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L8335)) |
| $`\omega`$ | $`0.5169428\ldots`$ | $`g=\mathbf 1_{\text{primes}}`$ | Irrational at base $`2`$: Tao–Teräväinen, Thm. 1.3, p. 4; proof pp. 44–56 \[taoteravainen2025\] |
| $`\Omega`$ | $`0.5895032\ldots`$ | $`g=\mathbf 1_{\text{prime powers}}`$ | Asserted *ibid.* by a similar argument, with the details left to the reader; not a proved theorem there |
| $`\varphi`$ | $`1.3676308\ldots=S`$ | $`g=A=\varphi*\mu`$ | **Open** (Erdős \#249) |

The first three weights are bounded, taking only the values $`0`$ and $`1`$ (for $`\tau`$ the weight is the constant $`1`$). The fourth is unbounded, by <a href="#res:weight" data-reference-type="ref" data-reference="res:weight">[res:weight]</a>. That difference is the one used in <a href="#res:periodic" data-reference-type="ref" data-reference="res:periodic">[res:periodic]</a>, and we do not claim it is the only difference: $`A`$ also vanishes on $`n\equiv2\pmod4`$, while $`\mathbf 1_{\text{primes}}`$ is bounded but no more eventually periodic than $`A`$ is, so the settled $`\omega`$ row is not an instance of <a href="#res:periodic" data-reference-type="ref" data-reference="res:periodic">[res:periodic]</a> either. It was settled by a different method, discussed in Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">9.5</a>.

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

Several neighbouring Dirichlet-convolution identities are rational and exactly computable. Writing $`L(g):=\sum_{d\ge1}g(d)/(2^d-1)`$, we have $`\sum_{d\ge1}\mu(d)/(2^d-1)=\tfrac12`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18434)) and $`\sum_{d\ge1}\varphi(d)/(2^d-1)=2`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18429)). These belong to two distinct one-step Möbius-convolution chains:
``` math
L(\mathbf 1)=E\ \longmapsto\ L(\mu)=\tfrac12,
  \qquad
  L(\varphi)=2 \ \longmapsto\ L(\varphi*\mu)=S.
```
Thus $`S`$ is one convolution step from the rational value $`L(\varphi)=2`$, not from $`E`$; the parallel chains show that this transformation need not preserve rationality. The squared-denominator representation $`S=\tfrac12+\sum_{d\ge1}\mu(d)/(2^d-1)^2`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18454)) converges fast enough to recompute the decimal above.

There is also an exact probabilistic reading, and it is more than a gloss. Let $`X`$ and $`Y`$ be independent fair-coin geometric waiting times on $`\mathbb{N}_{>0}`$. Then
``` math
S=\tfrac12+\Pr[\gcd(X,Y)=1]
```
([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18557)), the probability being the visible-coprime-pair series $`\sum_{\gcd(m,n)=1}2^{-(m+n)}`$. That probability is related to a distribution over the Stern–Brocot tree in a completely explicit way. For positive coprime $`(a,b)`$ put $`w_{a,b}=1/(2^{a+b}-1)`$. These reduced-slope masses sum to exactly $`1`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GcdMomentCalculus.lean#L349)), and at each node $`(a,b)`$ the cylinder mass $`1/((2^a-1)(2^b-1))`$ splits exactly into its stop mass and the masses of its two children ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GcdMomentCalculus.lean#L474)). The coprimality probability is not that total mass; rather,
``` math
S-\tfrac12
  =\sum_{\substack{a,b\ge1\\(a,b)=1}}2^{-(a+b)}
  =\sum_{\substack{a,b\ge1\\(a,b)=1}}
     \bigl(1-2^{-(a+b)}\bigr)w_{a,b}.
```
It is therefore the expectation of the conditional primitive-pair factor $`1-2^{-(a+b)}`$ under the self-similar reduced-slope probability law. What is missing is not structure; it is an arithmetic consequence of the structure.

The squared layer gives a different, genuinely moment-level view of the same fair-coin model. Since
``` math
\Pr[d\mid X\text{ and }d\mid Y]=\frac{1}{(2^d-1)^2},
```
the checked identity
``` math
\sum_{d\ge1}\frac{\varphi(d)}{(2^d-1)^2}
    =\sum_{n\ge1}(\mathsf P(n)-n)2^{-n},
  \qquad \mathsf P(n)=\sum_{e\mid n}\varphi(e)(n/e),
```
is exactly the divisor expansion of $`\mathbb E[\gcd(X,Y)]`$. The companion constant-weight identity replaces $`\varphi`$ by $`1`$ and yields $`\sum_{n\ge1}(\sigma(n)-\tau(n))2^{-n}`$, the corresponding divisor-count layer. These statements are useful because they turn the squared Lambert denominators into observables of the same random gcd, but they do not convert the first moment into an irrationality certificate for $`S`$; the missing arithmetic consequence remains the open endpoint. *Checked:* [divisor-count layer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GcdMomentCalculus.lean#L216), [first gcd moment](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GcdMomentCalculus.lean#L235).

<a id="sec:rank"></a>

# Proof of the dyadic-section basis theorem

<a id="prior-work"></a>

## Prior work

For an integer $`k\ge2`$, the *$`k`$-kernel* of a sequence $`c`$ is $`\{n\mapsto c(k^jn+r):j\ge0,\ 0\le r<k^j\}`$, and $`c`$ is *$`k`$-regular* when the module generated by its $`k`$-kernel is finitely generated; both notions are due to Allouche and Shallit (\[allouche-shallit, Defs. 1.1 and 2.1, author-preprint pp. 2–3\]). Their Theorem 2.2 gives equivalent finite-kernel and matrix characterisations, and Theorem 3.1 proves closure under convolution  \[allouche-shallit, pp. 3–4 and 10–11\]; neither result controls the finite-level rank of a sequence that is not $`k`$-regular. Coons proved that $`\varphi`$ is not $`k`$-regular for any $`k\ge2`$ (\[coons\], Theorem 3.2, pp. 348–349, in the published version; Theorem 3.3, pp. 8–9, in the preprint, which numbers its results on a single running counter). Bell and Smertnig reach a further negative conclusion, by a different argument rather than by strengthening that one: their Theorem 1.3 shows that a $`k`$-Mahler series with multiplicative coefficients has a $`k`$-regular coefficient sequence in an explicit closed form, and that the totient generating series is not $`k`$-Mahler for any $`k\ge2`$ follows directly from the closed form \[bell-smertnig\].

A separate line of work settles linear independence of totient values along affine progressions, and settles it more strongly than anything proved here. Martin \[martin-phi-inequalities\] assumes only that $`a_1,\dots,a_m`$ are positive integers and that $`a_ib_j\neq a_jb_i`$ for $`i\neq j`$, and proves in his Theorem 1 that for every constant $`C>0`$ the simultaneous ratio gaps
``` math
\frac{\varphi(a_1n+b_1)}{\varphi(a_2n+b_2)}>C,\quad\dots,\quad
 \frac{\varphi(a_{m-1}n+b_{m-1})}{\varphi(a_mn+b_m)}>C
```
hold on a set of positive lower density; he also notes that the hypotheses are symmetric in the forms, so every one of the $`m!`$ orderings occurs on such a set.

Taking $`C>\bigl(\sum_{i\neq t}|c_i|\bigr)/|c_t|`$ after moving a channel with $`c_t\neq0`$ to the front shows at once that
``` math
\bigl\{n\mapsto\varphi(a_in+b_i)\bigr\}_{i=1}^m
```
is linearly independent over $`\mathbb{R}`$, hence over $`\mathbb{Q}`$. His Corollary 4 carries Theorem 1 and its corollaries to $`\sigma`$. Every affine-totient independence statement used below is therefore a consequence of Martin’s theorem, and no originality is claimed for it.

Martin does not state the exact finite-level rank, the explicit basis, or the complete relation normal form; the present section derives them by combining his theorem with the reductions below. Coons and Bell–Smertnig likewise do not state those finite-level conclusions.

Coons’s statement is about the union over all levels: no finite set of sections generates the rest. Bell and Smertnig’s is about a functional equation.

One consequence of Coons’s theorem should be recorded explicitly, because it bounds what the present section may claim. For a subgroup $`M\subseteq\mathbb{Z}^{\mathbb{N}}`$ of integer-valued sequences, finite generation over $`\mathbb{Z}`$ is *equivalent* to finite dimension of its $`\mathbb{Q}`$-span. One direction is immediate. For the other, choose $`\mathbb{Q}`$-independent $`m_1,\dots,m_d\in M`$ and evaluation points $`n_1,\dots,n_d`$ with $`D:=\det[m_i(n_j)]\neq0`$, necessarily a nonzero integer; for $`x\in M`$ Cramer’s rule applied to the integer system $`x(n_j)=\sum_i a_im_i(n_j)`$ places every $`a_i`$ in $`\tfrac1D\mathbb{Z}`$, so $`M\subseteq\tfrac1D\bigl(\mathbb{Z}m_1+\dots+\mathbb{Z}m_d\bigr)`$, and over the principal ideal domain $`\mathbb{Z}`$ a submodule of a finitely generated module is finitely generated. (The familiar obstruction, that $`\mathbb{Z}[\tfrac12]`$ has rank one without being finitely generated, cannot occur here: an integer-valued sequence bounds its own denominators through its values at small indices.)

Hence *infinite-dimensionality of the full totient kernel is not an independent contribution of this note*: it is equivalent to Coons’s non-$`k`$-regularity and follows from it. Only the finite-level statements are additional. Knowing that a span is not finitely generated says nothing about its dimension at a given truncation, nor about which relations hold there; what is added here is that the dimension through level $`e`$ is exactly $`2^e+1`$, that an explicit family is a basis, and that the two elementary reductions generate every relation. We found no prior source giving any of those three for $`\varphi`$; that is the outcome of a search, not a proof of non-existence, and no priority is claimed.

The next subsection gives an independent, constructive proof of the same linear independence.

<a id="parity-separated-evaluation-matrices"></a>

## Parity-separated evaluation matrices

<a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a> is proved by exhibiting a square matrix of values of the sections whose determinant is nonzero, and the linear algebra at its centre is simpler than the arithmetic construction that feeds it. We give the linear algebra first, then the arithmetic input it consumes.

Evaluate the sections at one point apiece to get a square matrix $`M`$, and suppose each column $`j`$ admits a fixed power $`2^{d_j}`$ dividing every entry of that column such that, after dividing the column through by it, the diagonal entry is odd and every off-diagonal entry is even; call such an $`M`$ a *parity-separated evaluation matrix*. The normalised matrix is then the identity modulo $`2`$; its determinant is odd, hence nonzero, and the sections are independent ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L823)).

Producing evaluation points with exactly that parity pattern is what the arithmetic input is for, and it is the harder half. The Chinese remainder theorem together with Dirichlet’s theorem on primes in arithmetic progressions makes one of the evaluated affine values prime, which fixes the exact power of $`2`$ dividing the diagonal entry, while every other value receives a fresh prime divisor congruent to $`1`$ modulo a large power of two, which supplies the one extra factor of two that the off-diagonal entries need ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L882)). Even residues never enter, because the second reduction has already carried them to odd residues at lower levels ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientMahlerDefect.lean#L169)).

<a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a> then needs only two further steps, and both are short. Linear independence is a property of finite subfamilies, so the level-$`e`$ statement, applied with $`e`$ above the largest level occurring in a given finite subset, already gives independence of the whole infinite family $`\mathcal B`$. And the two reductions carry every remaining section onto a rational multiple of a member of $`\mathcal B`$, so the spans agree. That the assembly is short is the point: the level-$`e`$ theorem was always the whole content, and stating its consequence as infinite-dimensionality understated it. The sharp form is a basis.

<div class="remark">

*Remark 1*. <a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a> and <a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a> concern $`\varphi`$. Their complete proofs are independent of the arithmetic status of $`S`$. The single proved transport to \#249 is <a href="#res:carryrank" data-reference-type="ref" data-reference="res:carryrank">[res:carryrank]</a>.

</div>

<a id="sec:carry-rank"></a>

# Carry-rank consequences of rationality

Multiplying successive scaled tails by $`2`$ turns a hypothetical rational value into an integral recurrence. For coefficients $`c:\mathbb{N}\to\mathbb{N}`$ satisfying $`c(n)\le n`$, and in particular for $`c=\varphi`$ since $`\varphi(n)\le n`$, the series $`\sum c(n)/2^n`$ is rational exactly when an integral scaled-tail sequence exists, that is, an integer sequence $`u`$ with $`u(N+1)=2u(N)-v\,c(N+1)`$ for every $`N`$ and $`u(N)/2^N\to0`$, for some integer $`v\ge1`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GenericTailOrbitRigidity.lean#L426)). Transporting <a href="#res:rank" data-reference-type="ref" data-reference="res:rank">[res:rank]</a> through that recurrence gives <a href="#res:carryrank" data-reference-type="ref" data-reference="res:carryrank">[res:carryrank]</a>. The complementary finite-rank upper bound, which would make this a proof of irrationality, is not available.

<a id="sec:denominator"></a>

# A Farey-mediant denominator exclusion

<a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a> is a Farey exclusion, and we say so before saying anything else about it. The argument is the classical mediant one. The Lean lemma commits the first $`240`$ binary digits of the shifted series as a single residue over the totient carry window $`(N,K)=(1,240)`$; a rational $`a/q`$ can equal $`S`$ only if it falls into a resulting bad interval of width $`243/2^{240}`$; that interval is bracketed by two explicit unimodular fractions $`a_1/b<c_1/d`$ with $`bc_1-a_1d=1`$; and the mediant lemma ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GapFareyBound.lean#L51)) forces any rational strictly between unimodular neighbours to have denominator at least $`b+d`$. The excluded range is therefore $`q\le b+d-1`$, which is the printed constant ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GapFareyBound.lean#L176)), and the transport to the series is a tail estimate ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L15986)). *The method is standard, and we claim no novelty for it.*

Two things should be read off correctly. First, the scale. A window of $`K`$ computed binary digits yields a mediant bound of order $`2^{K/2}`$: the same calculation gives $`2.49\times10^{17}`$ at $`K=120`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GapFareyBound.lean#L88)) and $`7.96\times10^{34}`$ at $`K=240`$. The constant is a function of how many digits were committed, not a measure of how much the problem has moved. Second, the sharpness. Within its window the bound cannot be improved at all: $`b+d`$ itself fails the certificate, so $`b+d-1`$ is exactly the last denominator excluded. A reader who regards an explicit Farey exclusion as routine is not in disagreement with this note. <a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a>, not <a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a>, is where we would ask a sceptical reader to look.

The bound transfers to the coprimality form of Section <a href="#sec:family" data-reference-type="ref" data-reference="sec:family">2</a> with the constant halved: the visible-coprime-pair series has no representation $`a/d`$ with $`d\le39\,819\,823\,323\,350\,687\,661\,677\,887\,437\,915\,526`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L18572)), that number being $`(q_0-1)/2`$ for the constant $`q_0`$ of <a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a>.

<a id="sec:fresh-prime"></a>

# Fresh-prime losses in the diagonal probes

The finite diagonal and curvature probes have a useful decomposition that keeps the effect of new prime support visible. Fix $`H>0`$ and an offset $`s\in\mathbb{N}`$, and write
``` math
g_H(s)=\gcd(\operatorname{rad}(H),s),
 \qquad
 M_H(k,s)=\frac{kH+s}{g_H(s)}\varphi(g_H(s)).
```
Here $`\operatorname{rad}(H)`$ is the squarefree kernel of $`H`$. Since $`g_H(s)`$ divides both $`H`$ and $`s`$, it divides $`kH+s`$. The quantity $`M_H(k,s)`$ is the endpoint mass predicted by retaining only the prime support already present in $`H`$. Adding the remaining prime support can only lower the totient density, so the integer deficit
``` math
F_H(k,s)=M_H(k,s)-\varphi(kH+s)
```
is nonnegative. This sign is the key input: the new primes are not an uncontrolled error, even though their placement between endpoints is not favourable by default.

Let
``` math
\Delta_H(s)=\varphi(2H+s)-\varphi(H+s),
 \qquad
 \Delta_H^{\rm old}(s)=M_H(2,s)-M_H(1,s).
```
The checked endpoint calculation gives the exact identity
``` math
\Delta_H(s)=\Delta_H^{\rm old}(s)+F_H(1,s)-F_H(2,s),
```
and the literal foreign channel is precisely the lower-endpoint deficit minus the upper-endpoint deficit. Thus the old-prime model is affine in the multiplier $`k`$, while the actual diagonal departs from it only through a signed difference of two nonnegative quantities.

For the offset second difference $`\delta f(s)=f(s+1)-2f(s)+f(s+2)`$ and the five-point branch $`Wf(s)=4\delta f(s)+\delta f(s+2)`$, the same split remains exact. Dropping the favourable terms using $`F_H(k,s)\ge0`$ gives the concrete lower bound
``` math
W\Delta_H(s)\ge W\Delta_H^{\rm old}(s)-\mathcal A_H(s),
```
where
``` math
\mathcal A_H(s)=8F_H(1,s)+4F_H(2,s+1)+2F_H(2,s+2)
                  +F_H(2,s+3)+F_H(2,s+4).
```
This is the hard mechanism behind the finite curvature margins: a future cofinal argument must control the adverse budget $`\mathcal A_H(s)`$. Control of the old-prime margin alone is insufficient. The current formal result supplies no such cofinal bound, so this decomposition is a finite estimate, not an irrationality proof. *Checked:* [endpoint nonnegativity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FreshPrimeDeficitDecomposition.lean#L91), [diagonal split](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FreshPrimeDeficitDecomposition.lean#L171), [foreign-channel identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FreshPrimeDeficitDecomposition.lean#L184), [five-point loss bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FreshPrimeDeficitDecomposition.lean#L269).

<a id="finite-square-crt-correction-suppression."></a>

#### Finite square-CRT correction suppression.

Let $`E`$ be a finite family of distinct primes $`p_i`$, with anchors $`A_i`$, and let $`J<p_i`$ for every $`i\in E`$. The checked square-CRT construction produces a common base $`n`$, with
``` math
n<\left(\prod_{i\in E}p_i^2\right)(\sup_{i\in E}A_i+2),
 \qquad n=A_i+p_i^2t_i
```
for suitable $`t_i`$ at each index. Therefore every $`1\le h\le J`$ obeys
``` math
\varphi(n+p_i h-A_i)=(p_i-1)\varphi(p_i t_i+h).
```
The congruence has removed the $`p_i`$-divisibility correction on the whole finite horizon, simultaneously across the family. The formal regression witnesses show why this is not already a separation theorem: one clean block has both displayed coefficients zero (at base $`52`$), while another clean block has a displayed coefficient $`-4`$ (at base $`27`$). Thus the CRT mechanism controls a finite local error term but supplies neither a cofinal gap nor an irrationality criterion. *Checked:* [simultaneous finite family](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L297), [finite horizon](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L327), [vanishing block](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L459), [nonzero block](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SquareCRTCube.lean#L477).

<a id="canonical-strict-jump-slack."></a>

#### Canonical strict-jump slack.

At $`t`$, let $`m_t`$ be the checked canonical suffix depth and let $`d_t`$ be its residue at offset $`0`$. The scalar
``` math
\lambda_t=\min\!\left(d_t-2^{m_t-5},
       (2^{m_t}-2^{m_t-5})-d_t\right)
```
is the signed distance from that residue to the nearer edge of the central band. The two central inequalities therefore collapse exactly to $`\lambda_t\ge0`$. The formal equivalence says that asking for this sign at arbitrarily large strict LCM jumps is neither weaker nor stronger than asking for the original two-sided central band there. The same source then deduces irrationality of $`S`$ from the scalar condition. The hard step has only moved: no cofinal nonnegative-slack supply is proved, so this section records a one-integer target for future arithmetic or computational work, not a closure of Problem #249. *Checked:* [centrality equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalFreshLossBridge.lean#L2667), [equivalence of the two conditions](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalFreshLossBridge.lean#L2757), [conditional irrationality theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalFreshLossBridge.lean#L2932).

<a id="finite-foreign-residue-projection."></a>

#### Finite foreign-residue projection.

For a diagonal height $`H`$ and cutoff $`D`$, retain separately the residue channels with $`d\nmid H`$ and those with $`d\mid H`$. The formal finite state splits exactly as
``` math
\begin{aligned}
 \operatorname{finiteResidueDiagonal}(H,D)
   &=\operatorname{projectedForeignDefect}(H,D)\\
   &\quad+\operatorname{projectedDivisorChannels}(H,D).
 \end{aligned}
```
Once $`H\le D`$, the second summand is the explicit divisor shadow. In the stable range $`2H\le D`$, the omitted foreign window has the closed bound
``` math
\left|\operatorname{foreignTailWindow}(H,D,L)\right|
 \le \operatorname{diagonalCoefficient}(H)\left(
       \frac{2}{2^D}+\frac{4}{3\,4^D}\right).
```
The criterion is now transparent: if the limiting foreign defect is controlled by this budget, and the finite projected state is farther from every integer than the budget, the full target cannot be hit. The first comparison and a cofinal supply of separated projections are the remaining analytic and arithmetic obligations. No unbounded family is proved here. *Checked:* [finite complement bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/ActualForeignResidueProjection.lean#L276), [exact channel split](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/ActualForeignResidueProjection.lean#L308), [conditional target-miss theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/ActualForeignResidueProjection.lean#L414).

<a id="the-actual-lcm-orbit-exact-frontier-and-sign-trap."></a>

#### The actual LCM orbit: exact frontier and sign trap.

For the actual diagonal, set $`H_a=\operatorname{lcm}(1,\ldots,2^a)`$ and $`R_a=\operatorname{totientTail}(2H_a)-\operatorname{totientTail}(H_a)`$. The formal criterion [is exact](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitNonintegrality.lean#L37) says that irrationality is equivalent to finding $`R_a\notin\mathbb{Z}`$ cofinally in $`a`$. This is the sharp endpoint reformulation: it does not ask the orbit to stay a fixed distance from the integers, but it also supplies no such $`a`$.

There is nonetheless an unconditional geometric constraint on any attempted certificate. For $`a\ge8`$ and $`J+(a+6)<2\cdot2^a`$, the first lookahead letter in the short LCM window is positive and large enough to dominate the directed infinite remainder; the whole translated difference is therefore positive. The checked argument uses the arithmetic positivity of the LCM-ray letters and the directed tail bound, not an assumption about the sign of a finite residue. In an integral orbit this positivity is transported by the carry recurrence: the true survivor is negative, and, once the dyadic modulus exceeds the endpoint strip, the window residue is forced to the top edge rather than the central arc [by the exact top-edge theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSign.lean#L211). The sign corridor therefore removes one branch but exposes the remaining arithmetic task. A proof must exclude this persistent top boundary (or find cofinal non-integrality); a sign-only modular kill is not available.

<a id="a-quantitative-separation-criterion."></a>

#### A quantitative separation criterion.

The adjacent arithmetic theorem makes the finite evidence at the actual LCM heights explicit rather than treating it as a numerical table: [the $`t=2^4`$, length-$`23`$ kill](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmShortKill.lean#L18) and [the $`t=2^6`$, length-$`93`$ kill](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmShortKill.lean#L27) give [actual-orbit non-integrality at both heights](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmShortKill.lean#L35). The same file records the latter witness as a short arithmetic result through exponent six [but explicitly stops at that finite prefix](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmShortKill.lean#L54); it does not supply the missing cofinal quantifier.

A stronger unbounded approach asks for a quantitative anti-concentration bound. A sign alone gives too little information. At odd rank $`2q+1`$, the exact raw LCM block approximates the actual orbit with the elementary error bound [recorded here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSeparation.lean#L141); the raw block itself is an integer half-word divided by $`4^q`$ [by the normalization identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSeparation.lean#L179). Separation of that raw value from every integer by $`1/32`$ forces the half-word band [through the exact threshold lemma](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSeparation.lean#L208). The formal cofinal hypothesis strengthens this to $`1/32`$ plus the orbit error. This condition is [the cofinal separation hypothesis](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSeparation.lean#L254), and it yields irrationality by [the conditional endpoint theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmOrbitSeparation.lean#L305). Thus the hard step is an actual cofinal anti-concentration estimate; finite separation, the sign corridor, and the exact endpoint reduction do not imply it.

There is also a precise no-go for a tempting substitute. In the positive short LCM window, a terminal dyadic staircase would force the complete discrepancy word to vanish modulo its terminal power of two, but the last positive arithmetic letter is strictly smaller than that modulus, so [the staircase is impossible under the stated room hypothesis](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmTopEdgeStaircase.lean#L251). The companion [terminal-remainder identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientActualLcmTopEdgeStaircase.lean#L297) shows what survives: only the final letters control that residue. This prunes total dyadic annihilation, not every top-edge pattern; the remaining endpoint problem is still to prove a nonzero cofinal residue gap.

<a id="sec:nogo"></a>

# Obstructions for fixed-coordinate methods

<a href="#res:primindex" data-reference-type="ref" data-reference="res:primindex">[res:primindex]</a> has a one-line proof. Take a prime $`p>\max(D,2)`$; then $`A(p)=p-2`$ by <a href="#res:weight" data-reference-type="ref" data-reference="res:weight">[res:weight]</a>, and $`p\nmid D(p-2)`$, so $`D\cdot A(p)/p\notin\mathbb{Z}`$.

Two further checked results delimit narrower abstract hypothesis classes.

A fixed-precision transport theorem ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TropicalCurvatureCarry.lean#L137)) gives an unconditional reusable negative for a whole local escape strategy: at every fixed positive precision, every finite odd-unit valuation word admits a prefix-locked centred completion. The hard step is one-step modular recentering: the compatible carry is chosen by reducing the shifted state into an interval-sized power-of-two window, with an unrestricted quotient. Induction then centres every letter of the finite word, whatever the incoming carry. Consequently, no contradiction can be extracted from a finite local valuation-unit signature read at a precision fixed in advance; this retires that fixed-positive-precision local strategy for good. The theorem is synthetic and finite-word only: its valuation/unit symbols and unrestricted high quotients do not encode the actual totient differences, so it mentions neither $`\varphi`$ nor $`S`$. It does not provide a growing-precision or global correlation bridge, nonlinear arithmetic, or a genuinely fresh divisor channel, and it does not settle the \#249 endpoint or irrationality.

The factor-ideal no-go of <a href="#res:factorideal" data-reference-type="ref" data-reference="res:factorideal">[res:factorideal]</a> ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmFactorIdealPulseObstruction.lean#L798), with a sparse-anchor companion at [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmFactorIdealPulseObstruction.lean#L866)) exhibits, for each $`t\ge3`$ with $`H=\operatorname{lcm}(1,\dots,t)`$, a nonzero integer carry whose forcing letters lie in the ideal generated by $`\varphi(H)`$, which reproduces the true totient differences at $`t-2`$ prescribed indices, and which every finite integer shift polynomial carries to a pair with the same coboundary form, the same ideal memberships and an $`\ell^1`$-weight bound. It does close that hypothesis class. Two limits. The witness is a spike — its state is $`-\varphi(H)`$ at $`t-2`$ points and zero elsewhere, so it stays uniformly bounded while the strip bounds it respects grow, and the construction is cheap for that reason. And the shifted pairs are not asserted to be nonzero, so an argument that additionally demanded non-vanishing after the shift is not excluded. The theorem contains no whole-ray anchor condition, diagonal bound, or strict-survivor condition.

<a id="sec:conditional-criteria"></a>

# Conditional criteria

The criteria below do not enter the proofs of the unconditional results. Each states its unproved hypotheses explicitly.

<a id="a-prime-orbit-sufficient-condition."></a>

#### A prime-orbit sufficient condition.

The hypothesis [asks](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L157) for cofinally many primes $`p`$ at which the first tail-orbit exponential has real part strictly below $`9/10`$. Granting it, [a positive adaptive truncation budget](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L485) follows, and then [$`S`$ is irrational](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L524). The $`9/10`$ hypothesis is weaker than the earlier $`4/5`$ hypothesis, but no instance of this cofinal hypothesis is proved.

The companion block branch is recorded in the same family: a nonpositive phase-density predicate [density hypothesis](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L35) implies the uniform block-gap predicate [block-gap hypothesis](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L25) by the checked bridge [density-to-gap implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L45). Both questions reduce to one exact phase dynamics: if $`\zeta_{h,M}=\operatorname{tailOrbitFirstExp}(h,M)`$, then
``` math
\zeta_{h,M+1}=\zeta_{h,M}^{\,2}
```
because the integer increment in the tail-difference recurrence disappears after exponentiation [exact squaring recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L167). Iteration gives the closed form
``` math
\zeta_{h,M+k}=\zeta_{h,M}^{\,2^k},
  \qquad \zeta_{h,N}=\zeta_{h,0}^{\,2^N},
```
and the formal prime-gap predicate is exactly the same $`9/10`$ test on these initial-phase iterates along the shifted primes [iterate formula](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L191), [initial-phase normal form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L201), [initial-phase equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L278).

The same dynamics gives a sharp obstruction: if an iterate is a dyadic root of unity, repeated squaring reaches the absorbing phase $`1`$, so the cofinal strict gap is impossible [dyadic-root obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L322). There is also a precise conditional bridge from phase information to the prime-index hypothesis: cofinally many nonpositive phases at shifted prime indices imply the strict prime-orbit gap [prime-alignment implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L465). The bridge does not supply those prime-aligned visits. These are classification and obstruction statements for one conditional family, not a classification of the actual initial phase. This identifies the missing input as phase-density or prime-index supply for that squaring orbit, not another finite certificate theorem. The identity and its root obstruction supply neither anti-concentration, density, nor a cofinal prime gap, so no irrationality conclusion follows. Section <a href="#sec:frontier" data-reference-type="ref" data-reference="sec:frontier">9</a> states the sharper form in which this hypothesis is now available.

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
at [$`s=1`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L28) and [$`s=2`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L36). On the prime-power divisor-sum row,
``` math
\sigma_p(1)-2\sigma_p(0)=p-1
```
([first difference](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L44)), and for every $`e\ge0`$,
``` math
\sigma_p(e+2)-2\sigma_p(e+1)+\sigma_p(e)
    =p^{e+1}(p-1)
```
([second difference](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FiniteEulerSieve.lean#L51)). For example, at $`p=3`$ the values $`\sigma_3(0),\ldots,\sigma_3(3)=1,4,13,40`$ give $`4-2=2`$ and $`40-2\cdot13+4=18=3^2(3-1)`$. Thus convolution with $`\mu\ast\mu`$ converts the prime-power divisor-sum row into the corresponding totient row at every finite stage. These are finite algebraic identities; no transcendence conclusion is attached to them.

<a id="mixed-differences-of-cyclotomic-layers."></a>

#### Mixed differences of cyclotomic layers.

For a function $`F:\{0,1\}^2\to\mathbb{Z}`$, define
``` math
\Delta F=F(1,1)-F(1,0)-F(0,1)+F(0,0)
```
([mixed difference](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L22)). If $`F(i,j)=u(i)+v(j)`$, then $`\Delta F=0`$ ([separable case](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L26)). Conversely, among integer linear combinations of the four values of $`F`$ whose coefficients sum to zero along each row and each column, the pattern $`(1,-1,-1,1)`$ is forced up to scale ([fixed-stencil uniqueness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L32)). For example, the table
``` math
\begin{array}{c|cc}
 &0&1\\ \hline
0&9&13\\
1&12&16
\end{array}
```
has mixed difference $`16-12-13+9=0`$; increasing only the lower-right entry by $`5`$ changes the mixed difference to $`5`$. The uniqueness statement is internal to this fixed $`2\times2`$ stencil. It does not assert invariance under larger stencils, nonlinear functionals, or another representation.

The formal development also records [a four-point divisor-layer identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L45) and [a centred representative for a residue class modulo an even modulus](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L62). The two unproved hypotheses and their target conclusion are as follows. For $`C:\mathbb{N}\to\mathbb{N}`$ and $`m,d\in\mathbb{N}`$, put
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
These are the linked predicates [Layer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L95), [BoundedOrder](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L102), and [FinitePrimeEscape](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L151). The bounded-order condition does not assert an exact multiplicative order; it asserts only the displayed divisibility for some $`k\le d`$.

The implication from bounded order to finite-prime escape is a size argument in the paper. If $`m=0`$, the bounded-order condition forces $`C(0)=1`$. If $`m>0`$, the assertion is immediate for $`S=\varnothing`$; otherwise choose $`Q_0`$ so that $`mQ_0>\max_{p\in S}(p^d-1)`$. For every prime $`q\ge Q_0`$, a divisor $`p\in S`$ of $`C(mq)`$ would give $`mq\mid p^k-1`$ for some $`k\le d`$, hence $`mq\le p^k-1\le p^d-1`$, a contradiction. The layer hypothesis separately ensures that the layers are nontrivial and coprime to their indices. Neither hypothesis is proved here; polynomial-resultant realisability and Archimedean growth are also not established.

<a id="sec:frontier"></a>

# Open problems

Write $`H_t=\operatorname{lcm}(1,\dots,t)`$ ([definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CarrySurvivorExtinction.lean#L515)), so that $`H_1=1`$, $`H_2=2`$, $`H_3=6`$, $`H_4=12`$, $`H_5=H_6=60`$ and $`H_7=420`$; and recall from Section <a href="#sec:results" data-reference-type="ref" data-reference="sec:results">1</a> the tail $`R_N=\sum_{m\ge1}\varphi(N+m)/2^{m}`$, which differs from $`2^NS`$ by an integer ([definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientTailPeriodKiller.lean#L57)).

<a id="exact-equivalent-formulations"></a>

## Exact equivalent formulations

<div id="prob:diagonal" class="equivform">

*Equivalent formulation 1* (lcm-diagonal escape). For every $`t_0`$ there is a $`t\ge t_0`$ with $`R_{2H_t}-R_{H_t}\notin\mathbb{Z}`$.

</div>

By <a href="#res:equivalences" data-reference-type="ref" data-reference="res:equivalences">[res:equivalences]</a>, formulation <a href="#prob:diagonal" data-reference-type="ref" data-reference="prob:diagonal">1</a> is equivalent to irrationality of $`S`$. It identifies an exact decidable witness family, but is not claimed to reduce the difficulty of Erdős \#249. A finite list of successful certificates establishes the predicate only on its tested scales. Conversely, one pair $`h>0`$, $`N`$ with $`R_{N+h}-R_N\in\mathbb{Z}`$ already makes $`S`$ rational ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/LcmConeFlatness.lean#L357)).

The certificate is decidable at each $`t`$, and is kernel-checked at the $`28`$ listed scales between $`t=1`$ and $`t=64`$ ([list](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalPincerCertificatesT64.lean#L1933), [verification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/DiagonalPincerCertificatesT64.lean#L1967)). The current pinned source strengthens that historical list to every $`t\le82`$, with no gaps ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Skip/LadderT67.lean#L71264)). The theorem through $`t=82`$ supplies no instance at $`t=83`$ and does not discharge the cofinal quantifier.

The cyclotomic form exposes more arithmetic structure. Write $`C(n)=|\Phi_n(2)|`$.

<div id="prob:cyclotomic" class="equivform">

*Equivalent formulation 2* (cyclotomic-anchored phase escape). For every $`h\ge1`$ and every $`N_0`$, there exist primes $`q,p`$ and $`L\in\mathbb{N}`$ such that
``` math
\gcd(p,hq)=1,\qquad p\mid C(hq),\qquad hq\mid p-1,
 \qquad p-1\ge N_0,
```
and $`(hq,p-1,L)`$ is a finite tail-difference certificate.

</div>

This is [CyclotomicAnchoredKillSupply](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L3231). For the binary layers, clean anchors satisfying every condition before the certificate are already supplied, and [the checked equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L3327) identifies formulation <a href="#prob:cyclotomic" data-reference-type="ref" data-reference="prob:cyclotomic">2</a> with irrationality of $`S`$. The unknown is phase escape of the totient discrepancy modulo $`2^L`$, not large prime divisors or multiplicative order. The checked $`p=331`$ instances are finite models of this exact predicate; unbounded support alone does not imply it.

The [checked conditional support/period no-go](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L1706) makes that limitation exact. If $`S`$ were rational, its eventual integral tail-period law would supply some $`h>0`$, while [unbounded prime divisors](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L158) would persist on the same $`h`$-ray for the actual binary cyclotomic layers, by [the checked binary-layer theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean#L1693). Consequently, unbounded support cannot be the missing contradiction unless an additional carry- or phase-escape theorem relates that support to the period law. This is a necessary-state theorem under hypothetical rationality: it neither constructs a rational example nor proves that the rationality hypothesis is consistent, and Erdős \#249 remains open.

<a id="exact-full-depth-reduction-and-a-stronger-sufficient-condition"></a>

## Exact full-depth reduction and a stronger sufficient condition

The earlier condition [ApFullDepthEscape](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/PeriodMultipleEscape.lean#L441) asks, for every $`d\ge1`$ and $`N`$, for a $`t\ge1`$ such that $`(td,N,td)`$ is a finite tail-difference certificate. It was originally recorded only as a sufficient condition because the certificate depth is forced to equal its period. The full-depth theorem removes that asymmetry completely. For fixed $`d,N`$, one certificate $`(d,N,L)`$ at any depth yields a threshold $`T>0`$ beyond which every adjacent pair of multipliers contains an $`m`$ with a full-depth certificate $`(md,N,md)`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L364)). Together with finite-certificate faithfulness, this gives the pointwise equivalence
``` math
\exists t>0:\ (td,N,td)\text{ is certified}
 \quad\Longleftrightarrow\quad R_{N+d}-R_N\notin\mathbb{Z}
```
([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L388)). Therefore $`\operatorname{ApFullDepthEscape}`$ is equivalent to irrationality ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L406)). The cofinal full-depth supply is likewise equivalent to the arbitrary-depth period-multiple supply and hence to irrationality ([depth deletion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L421); [endpoint equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos249/FullDepthRayAmplifier.lean#L438)). What remains open is the initial nonintegrality: the theorem converts one non-integral shift, equivalently one seed, into a dense ray of full-depth certificates but does not furnish that seed.

<div id="prob:firstharmonic" class="problem">

**Problem 3** (first-harmonic anti-concentration on supplier fibres). For each $`h\ge1`$, do there exist $`s\ge1`$ and $`0<\eta<1`$ such that, for every $`X_0`$, there are $`X,L`$ with
``` math
\max(X_0,1)\le X,\qquad h\le L-s,\qquad
 16(2X+h+L+2)\le2^L,
```
for which the four bounds below hold?

</div>

This four-term decomposition is one way to prove a fixed-full-block first-harmonic gap. The underlying question is whether the first additive character of the totient-window discrepancy has a constant saving. Failure of this particular decomposition would not decide that question, still less Erdős Problem #249.

To make the question self-contained, put
``` math
\omega_N=\exp\!\left(2\pi i\,
   \frac{D_{h,N,L}\bmod 2^L}{2^L}\right),\qquad X\le N<2X.
```
At the pivot argument $`N+L-s+1`$, call $`N`$ a supplier when this integer factors as $`mp`$, where $`p`$ is its largest prime factor, $`0<m\le\sqrt X/2`$, and $`p>2\sqrt X`$. Suppliers are good when $`\eta m\le\varphi(m)`$ and bad otherwise; non-suppliers form the remaining set. Writing $`t=L-s+1`$, the canonical fibre with cofactor $`m`$ is exactly the image of the primes in
``` math
X+t\le mp<2X+t
```
under the injective map $`p\mapsto mp-t`$ ([membership](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L299), [injectivity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L367), [image equality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L384)). This exact bijection does not imply that the supplier prime is isolated from every other argument in the window. At $`X=16`$, $`L=20`$, $`s=1`$, $`m=2`$, and $`N=18`$, the pivot is $`38=2\cdot19`$, while the same prime $`19`$ divides the distinct argument $`N+1=19`$ ([checked counterexample](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L394)).

For a supplier write $`z_N`$ for its explicit totient pivot phase, $`w_N=\omega_N/z_N`$, and $`\bar z_m`$ for the mean of $`z_N`$ on the fibre with cofactor $`m`$. Define
``` math
\begin{aligned}
 \mathcal C&=\sum_{N\ {\mathrm{good}}}w_N(z_N-\bar z_m),&
 \mathcal M&=\sum_{N\ {\mathrm{good}}}w_N\bar z_m,\\
 \mathcal B&=\sum_{N\ {\mathrm{bad}}}\omega_N,&
 \mathcal U&=\sum_{N\ {\mathrm{nonsupplier}}}\omega_N.
\end{aligned}
```
The exact identity is $`\sum_{X\le N<2X}\omega_N=\mathcal C+\mathcal M+\mathcal B+\mathcal U`$, and Problem <a href="#prob:firstharmonic" data-reference-type="ref" data-reference="prob:firstharmonic">3</a> asks precisely for
``` math
\operatorname{Re}\mathcal C\le\frac{14}{25}X,\qquad
 |\mathcal M|\le\frac1{100}X,\qquad
 |\mathcal B|\le\frac1{100}X,\qquad
 |\mathcal U|\le\frac8{25}X.
```
The decomposition is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L514), and the four budgets imply irrationality by [the conditional irrationality theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L577).

More precisely, these four inequalities are the source predicate [the budget condition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L543), and its checked consequence [the first-harmonic gap](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/FirstHarmonicPivot.lean#L549) is the explicit estimate
``` math
\sum_{X\le N<2X}\cos\!\left(2\pi
   \frac{D_{h,N,L}\bmod 2^L}{2^L}\right)\le\frac9{10}X.
```
The hard missing step is therefore cofinal centred-correlation and error bounds, not the formal addition of the four terms. In particular, the exact supplier-fibre bijection above does not provide global prime isolation; the $`38=2\cdot19`$ witness is the natural friction that the correlation estimate must overcome. We claim neither the budget predicate nor the resulting gap without those cofinal bounds. An obstruction showing that available first- and second-moment information cannot force this modulo-$`2^L`$ small-ball estimate would also decisively close this harmonic argument.

<a id="structural-and-diophantine-routes"></a>

## Structural and Diophantine routes

<div id="prob:carryrank" class="problem">

**Problem 4** (totient carry-rank compression). Suppose $`v\ge1`$ and $`u:\mathbb{N}\to\mathbb{Z}`$ satisfy
``` math
u(N+1)=2u(N)-v\varphi(N+1),\qquad \frac{u(N)}{2^N}\longrightarrow0.
```
Must the span of the level-$`e`$ dyadic sections of $`u`$ have dimension less than $`2^e-1`$ for some $`e`$?

</div>

Rationality of $`S`$ would produce exactly such an integral tempered orbit, while the checked transport theorem forces its rank to be at least $`2^e-1`$ at every level. Thus a positive answer proves irrationality. A negative answer should ideally construct a control recurrence with the same integrality and decay architecture and near-maximal dyadic rank; infinite dimension of the totient $`2`$-kernel alone is not enough.

For a separate denominator-compression argument, define the Möbius–Mersenne ladder
``` math
\Theta_r=\sum_{d\ge1}\frac{\mu(d)}{(2^d-1)^r},
 \qquad \Theta_2=S-\frac12.
```
Result <a href="#res:rankonefloor" data-reference-type="ref" data-reference="res:rankonefloor">[res:rankonefloor]</a> excludes the positive rank-one family by an exact extremal calculation, not a coarse interval screen. The unique minimum is $`(e,Y)=(1,5)`$, and every admissible quotient, hence every nonempty finite positive normalized average of them, satisfies
``` math
Q(e,Y)-\Theta_2>\frac{21}{320}>\frac1{16}.
```
The stronger unit-fraction floor $`1/15`$ fails already at the minimizer. Thus adding atoms or positive rank-one blocks cannot create a small linear form; any remaining argument must use signed cancellation, off-diagonal coupling, or genuinely higher rank.

<div id="prob:hankel" class="problem">

**Problem 5** (genuinely coupled denominator compression). Construct integers $`P_n`$ and $`Q_n>0`$ from a genuinely off-diagonal, vector-valued, or signed-cancellation Hankel–Schur–Padé kernel such that
``` math
0<Q_n\left|\Theta_2-\frac{P_n}{Q_n}\right|\longrightarrow0.
```
Alternatively, prove a structural no-go theorem for a clearly defined larger class of bounded-width coupled kernels.

</div>

Ordinary convergence of rational approximants is insufficient; the scaled error is the Diophantine quantity. The words “genuinely coupled” exclude the positive rank-one and positive direct-sum mechanisms already separated from $`\Theta_2`$ by the uniform gap.

<a id="independent-extension"></a>

## Independent extension

This subsection previously posed the odd-prime kernel dimension as an open problem. It is now a theorem, and for every integer base rather than for odd primes only. The statement below combines Lean-checked arithmetic, spanning, and conditional-rank layers with a paper-level independence argument. Lean proves the zero-residue relation ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelReduction.lean#L60)) and the exact division-free composite-base reduction ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TotientKernelReduction.lean#L117)). It also proves unique quotient/nonzero-digit coordinates for each admissible fixed-level residue and that the resulting finite index has cardinality $`k^e+1`$. The new conditional layer proves that the canonical family spans the complete truncation and that its linear independence implies exact rank $`k^e+1`$. These are respectively `span_allBaseTotientKernelThroughLevelFamily_eq_canonical` and `finrank_allBaseTotientKernelThroughLevelFamily_eq_of_linearIndependent` in `Erdos249257/TotientKernelConditional.lean`; their immutable source links are added after the module lands in the paper’s pinned snapshot. The antecedent of the second statement is explicit and is not discharged in Lean. The paper obtains it from Martin’s external positive-density theorem through the elementary linear-independence consequence recorded above.

<div id="thm:kkernelrank" class="theorem">

**Theorem 6** (exact rank of every totient $`k`$-kernel truncation). *Let $`k\ge2`$ and $`e\ge1`$ be integers, write $`F^{(k)}_{j,r}(n)=\varphi(k^jn+r)`$, and put
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

The checked composite-base statement is deliberately cross-multiplied by $`\varphi(\gcd(k,u))`$; the displayed scalar is the equivalent paper-level normalisation after exact division. Lean also checks that this scalar is nonzero and gives the exact one-step functional reduction `allBaseTotientKernelSeq_mul_residue_step` in `Erdos249257/TotientKernelConditional.lean`. Thus the zero channel, arithmetic reduction, finite-index/cardinality, spanning, and conditional-rank layers have kernel receipts. Martin remains the external authority for the linear-independence input and hence for the unconditional basis and rank conclusion of Theorem <a href="#thm:kkernelrank" data-reference-type="ref" data-reference="thm:kkernelrank">6</a>.

The selection condition is $`k\nmid r`$, not $`\gcd(k,r)=1`$; for composite $`k`$ a basis residue may share prime factors with $`k`$. Independence is obtained by restricting to $`n=km+1`$, where the surviving channels become the affine forms $`L_0(m)=km+1`$ and $`L_{j,r}(m)=k^{j+1}m+(k^j+r)`$ with $`k\nmid r`$. These have positive slopes and satisfy $`a_ib_j\neq a_jb_i`$, so Martin’s Theorem 1 \[martin-phi-inequalities\] applies through the linear-independence consequence recorded in the prior-work subsection. The two zero-residue channels are proportional on that progression and are separated afterwards by evaluating at $`n=k`$, using $`\varphi(k^2)=k\varphi(k)`$ and $`\varphi(k)<k`$.

At $`k=2`$ this recovers the dyadic rank theorem of Section <a href="#sec:rank" data-reference-type="ref" data-reference="sec:rank">3</a>; at $`k=\ell`$ an odd prime it gives the case first posed here. Neither Coons’s non-$`k`$-regularity theorem nor the Bell–Smertnig Mahler classification supplies a finite-level rank, a basis, or the relations, so Theorem <a href="#thm:kkernelrank" data-reference-type="ref" data-reference="thm:kkernelrank">6</a> is not a consequence of either. A targeted literature search located no source stating the exact rank, the basis, or the normal form; that is a search result and not a novelty claim, and the statement remains subject to specialist review.

<div class="remark">

*Remark 2* (excluded generic mechanisms). Unbounded prime support, exact multiplicative order, natural-boundary information, ordinary Hankel nonvanishing, and positive rank-one averaging do not supply the missing binary phase or denominator compression. The finite Euler-factor and $`2\times2`$ mixed-difference identities of Section <a href="#sec:conditional-criteria" data-reference-type="ref" data-reference="sec:conditional-criteria">8</a> are tools rather than open endpoints; no growing-level Diophantine conclusion is claimed for them here.

</div>

A proof of formulation <a href="#prob:diagonal" data-reference-type="ref" data-reference="prob:diagonal">1</a> gives irrationality of $`S`$ by <a href="#res:equivalences" data-reference-type="ref" data-reference="res:equivalences">[res:equivalences]</a>. Its negation settles \#249 in the opposite direction: it supplies a positive-shift integral tail difference, which forces rationality. By contrast, failure of the sufficient bounds would rule out only those particular arguments.

<a id="the-independent-denominator-exclusion."></a>

#### The independent denominator exclusion.

The constant $`7.96\times10^{34}`$ of <a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a> is the classical Farey mediant bound applied to a window with a free parameter $`K`$; it has order $`2^{K/2}`$, and raising it needs only more committed binary digits, which is a computation rather than an idea. It is not one of the open items of Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">9.5</a>.

<a id="sec:open"></a>

## Logical status and analytic input

1.  Irrationality of $`S`$ (<a href="#res:open" data-reference-type="ref" data-reference="res:open">[res:open]</a>). No proof is claimed.

2.  The lcm-diagonal and clean cyclotomic-anchor statements are exact equivalent formulations of <a href="#res:equivalences" data-reference-type="ref" data-reference="res:equivalences">[res:equivalences]</a>: they convert irrationality into the existence of an unbounded family of finite tail-difference certificates. Finite instances are checked — every $`t\le82`$, including the historical $`28`$-scale bank of Section <a href="#sec:frontier" data-reference-type="ref" data-reference="sec:frontier">9</a> — and the unbounded family is not. The equivalences fix the exact missing quantifier but do not make that quantifier easier to prove. <a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a> is a finite instance of a *different* family, the gap certificates of <a href="#res:supply" data-reference-type="ref" data-reference="res:supply">[res:supply]</a>, which reach irrationality by a one-way implication; the two families should not be counted together.

3.  Full-depth period-multiple escape and the four first-harmonic pivot bounds are stronger sufficient conditions; they, and the prime-orbit gap the pivot bounds refine, are unproved. Failure of either would refute only that argument.

4.  Carry-rank compression and genuinely coupled denominator compression are separate contradiction targets. No required upper bound or coupled approximant family is proved.

5.  The $`k`$-kernel rank statement of Theorem <a href="#thm:kkernelrank" data-reference-type="ref" data-reference="thm:kkernelrank">6</a> is independent of the irrationality problem and settles nothing about it. Its zero-residue, composite-base arithmetic, finite-index/cardinality, and spanning layers are Lean-checked. Lean also checks the exact-rank theorem under an explicit linear-independence hypothesis. That hypothesis remains a paper deduction from Martin’s Theorem 1; Martin’s theorem is not formalised. No source was located for the rank, basis, or normal form themselves; that search result is not a priority verdict.

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

<a id="claim-status."></a>

#### Claim status.

Two of the items above are checked propositions that no row of the claim registry currently owns: the three declarations of <a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a>, and the five of <a href="#res:weight" data-reference-type="ref" data-reference="res:weight">[res:weight]</a>; the supply implication of <a href="#res:supply" data-reference-type="ref" data-reference="res:supply">[res:supply]</a> is likewise unowned, and <a href="#res:denominator" data-reference-type="ref" data-reference="res:denominator">[res:denominator]</a> cites three declarations of which the registry’s row owns one. Under this project’s own division of authority the registry, not a manuscript, owns public status, so the honest tag on those items is that they are kernel-checked and not yet registered. We print that rather than borrowing a neighbouring row’s status. The gap is a defect in the record, not in the proofs, and closing it is a review action rather than a mathematical one.

This manuscript is authored exposition, not proof authority. The linked Lean snapshot is authoritative only for its exact propositions, and kernel checking establishes that a proposition was proved, not that it is interesting, novel, or sufficient. The consequence drawn in the last sentence of <a href="#res:basis" data-reference-type="ref" data-reference="res:basis">[res:basis]</a>, the deduction in <a href="#res:periodic" data-reference-type="ref" data-reference="res:periodic">[res:periodic]</a> that an unbounded weight is not eventually periodic, the mechanism sentence in Section <a href="#sec:nogo" data-reference-type="ref" data-reference="sec:nogo">7</a>, and the size argument in Section <a href="#sec:conditional-criteria" data-reference-type="ref" data-reference="sec:conditional-criteria">8</a> are one-line arguments in the prose, marked as such; the first three are drawn from checked statements, and the last assumes the unproved bounded-order condition.

The small numerical instances printed above — the level-three reductions, the certificate at $`(1,12,16)`$, the first values of $`A`$, the $`p=3`$ Euler-factor calculation, the mixed-difference table, and the values of $`H_t`$ — are computations from the definitions and checked identities beside them, and are not separate checked propositions. Source theorems attributed to Allouche and Shallit, Martin, Coons, Bell and Smertnig, Kaneko–Suzuki–Tachiya, Luca–Tachiya, and Tao–Teräväinen are cited from the literature. This development does not formalise Martin’s positive-density theorem or Coons’s non-regularity theorem.

It does kernel-check an independent dyadic basis/rank proof and a full-kernel infinite-dimensionality consequence that Coons already implies. For every base it also kernel-checks the arithmetic reduction, unconditional canonical spanning, and the exact-rank conclusion conditional on an explicit linear-independence hypothesis; it does not prove that hypothesis. The assessment that no prior source gives an explicit basis, an exact finite-level dimension formula, or a relation normal form for the totient $`2`$-kernel is the outcome of a literature search and is not a proof of non-existence.

Erdős Problem #249 remains open.

<div class="thebibliography">

10 J.-P. Allouche and J. Shallit, [*The ring of $`k`$-regular sequences*](https://cs.uwaterloo.ca/~shallit/Papers/as0.pdf), Theoret. Comput. Sci. **98** (1992), no. 2, 163–197, doi:[10.1016/0304-3975(92)90001-V](https://doi.org/10.1016/0304-3975(92)90001-V). Definitions 1.1 and 2.1 are on pp. 2–3 of the linked author preprint, which differs slightly from the published version; the cited definitions are unaffected. M. Coons, *(Non)Automaticity of number theoretic functions*, J. Théor. Nombres Bordeaux 22 (2010), no. 2, 339–352; [doi:10.5802/jtnb.718](https://doi.org/10.5802/jtnb.718); [arXiv:0810.3709](https://arxiv.org/abs/0810.3709). Theorem 3.2, pp. 348–349, in the published version (Theorem 3.3, pp. 8–9, in the preprint): $`\varphi`$ is not $`k`$-regular for any $`k\ge2`$. G. Martin, *Simultaneous inequalities among values of the Euler phi-function*, 2 March 2006, [arXiv:math/0603053](https://arxiv.org/abs/math/0603053); [doi:10.48550/arXiv.math/0603053](https://doi.org/10.48550/arXiv.math/0603053). Theorem 1: for positive integers $`a_1,\dots,a_k`$ and integers $`b_1,\dots,b_k`$ with $`a_ib_j\neq a_jb_i`$, and every $`C>0`$, the simultaneous ratio gaps $`\varphi(a_1n+b_1)/\varphi(a_2n+b_2)>C,\dots`$ hold on a set of positive lower density; Corollary 4 carries this to $`\sigma`$. Cited here as a public preprint: a separate journal publication was not located. J. Bell and D. Smertnig, *Mahler series with multiplicative coefficient sequences*, 2026, [arXiv:2603.23456](https://doi.org/10.48550/arXiv.2603.23456). The totient generating series is not $`k`$-Mahler for any $`k\ge2`$, a consequence of their Theorem 1.3 recorded in the introduction. H. Kaneko, Y. Suzuki and Y. Tachiya, [*Refinements of Erdős’s irrationality criterion for certain sparse infinite series*](https://arxiv.org/abs/2601.20743), arXiv:2601.20743v1, 2026. Corollary 3 is on pp. 5–6 and proves irrationality for the $`\sigma(n)`$- and $`\varphi(n)`$-in-the-exponent families; its proof is on pp. 18–19. T. Tao and J. Teräväinen, *Quantitative correlations and some problems on prime factors of consecutive integers*, arXiv:2512.01739 (submitted December 2025, revised April 2026). Theorem 1.3 proves irrationality of $`\sum_{n\ge1}\omega(n)/2^n`$ at base $`2`$; the extension to every integer base and the $`\Omega`$ analogue are stated as remarks, with the modifications left to the reader. The theorem is on p. 4 and its proof is Section 5, pp. 44–56, in arXiv v2. R. Balasubramanian, S. Giri and P. Srivastav, *On correlations of certain multiplicative functions*, J. Number Theory 174 (2017), 221–238, [DOI](https://doi.org/10.1016/j.jnt.2016.10.001); [arXiv:1511.02221](https://arxiv.org/abs/1511.02221). The arXiv version’s Theorem 2.2 and Remark 2.4 give the uniform shifted divisor-convolution correlation and Euler product used above; the required fixed-shift weighted partial-summation formula follows Corollary 2.8. F. Luca and Y. Tachiya, [*Linear independence results for the values of divisor functions series*](https://www.kurims.kyoto-u.ac.jp/~kyodo/kokyuroku/contents/pdf/2014-14.pdf), RIMS Kôkyûroku No. 2014 (2017), 138–150. Theorem A on p. 139 explicitly restates their earlier Theorem 1.1 for nonzero purely periodic integer weights. Theorem 1 is on p. 139, its examples are on p. 140, and its proof is on pp. 149–150. P. Erdős, [*On arithmetical properties of Lambert series*](https://users.renyi.hu/~p_erdos/1948-04.pdf), J. Indian Math. Soc. (N.S.) **12** (1948), 63–66. The integer-base full-support theorem is on p. 63; the proof is on pp. 63–66, and the closing totient-series remark is on p. 66. P. Erdős and R. L. Graham, *Old and New Problems and Results in Combinatorial Number Theory*, 1980, p. 61. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). T. F. Bloom, [*Erdős Problem \#249*](https://www.erdosproblems.com/249), `erdosproblems.com/249`, accessed 28 July 2026 (page displays “last edited 28 September 2025”). The current record labels the problem open, cites `[ErGr80, p. 61]` and `[Er88c, p. 102]`, and explicitly describes its status as the website owner’s present assessment rather than a literature-completeness guarantee.

</div>
