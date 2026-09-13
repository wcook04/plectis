<a id="erdos-1041-lemniscate-newton-flow"></a>

# Sharp Solved Families and Constant-Factor Paths in Polynomial Lemniscates

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Every monic trinomial $`z^n+az^m+b`$, $`1\le m<n`$, whose roots lie in the open unit disc has every root-to-origin segment inside $`\{|f|<1\}`$; any two roots are joined through the origin with length less than $`2`$. The root equation reduces the radial image to a convex combination of two controlled values. For arbitrary squarefree monic polynomials, the condition $`\mu=\min_{f'(c)=0}|f(c)|\le13/25`$ also gives a connection shorter than $`2`$. Rescaling gives a path shorter than $`(5/2)\mu^{1/n}`$ in $`\{|f|<(25/13)\mu\}`$, with no root-location restriction. If $`f`$ is monic of degree $`n\ge3`$, $`c`$ is a simple critical point, $`v=f(c)`$ satisfies $`0<|v|<1`$, and some $`w_0\in[0,1]`$ satisfies $`|f(d)/v-w_0|\ge4/3`$ at every other critical point $`d`$, a two-sheeted square-root uniformisation, the Bergman segment inequality and a capacity bound give a root connector shorter than $`2`$. Independently, if the roots of a monic polynomial of degree $`n\ge2`$ lie in a closed disc of radius $`R`$ and $`c_1,\ldots,c_{n-1}`$ are its critical points counted with multiplicity, a Poisson identity gives the sharp mean $`\sum_j|f(c_j)|^{2/(n-1)}\le(n-1)R^{2n/(n-1)}`$; this mean alone does not control a connector. Exact counterexamples isolate the geometric information these estimates leave undetermined. These results do not settle the unrestricted problem.

<a id="sec:trinomial"></a>

# Monic trinomials, in every degree

<div id="res:trinomial-all-degree" class="theorem">

**Theorem 1** (all-degree monic trinomials). *Let $`1\le m<n`$ and
``` math
f(z)=z^n+az^m+b,
```
with every zero in the open unit disc. For any zero $`\zeta`$, the entire segment $`[0,\zeta]`$ lies in $`\{|f|<1\}`$. Distinct zeros $`\zeta_1,\zeta_2`$ are therefore joined by the broken line $`\zeta_1\to0\to\zeta_2`$ of length $`\|\zeta_1\|+\|\zeta_2\|<2`$ inside the open unit lemniscate.*

</div>

<div class="proof">

*Proof.* If $`\zeta^n+a\zeta^m+b=0`$, then
``` math
f(t\zeta)=b(1-t^m)+\zeta^n(t^n-t^m).
```
Vieta gives $`|b|<1`$. For $`0\le t<1`$, the weights $`1-t^m`$ and $`t^m-t^n`$ are nonnegative, so
``` math
|f(t\zeta)|\le |b|(1-t^m)+|\zeta|^n(t^m-t^n)
 <1-t^n\le1.
```
At $`t=1`$ the value is zero. Concatenating the two segments gives length $`|\zeta_1|+|\zeta_2|<2`$. Lean checks [the trinomial radial inequalities and radius budget](https://github.com/wcook04/plectis-erdos/blob/0ba585f632fbbbb43af2ee9532d4e83752af3f67/ErdosProblems/Erdos1041/AbelControlPolygon.lean#L330), including the constant-term bound from the root-disc hypothesis. The conversion of those two segment inequalities and their radius-sum bound into the single rectifiable path stated here is an ordinary geometric step. ◻

</div>

<a id="a-finite-convex-certificate."></a>

#### A finite convex certificate.

For $`f(z)=\sum_{k=0}^n a_kz^k`$ and $`f(\zeta)=0`$, put $`S_j=\sum_{k=0}^j a_k\zeta^k`$. Abel summation gives
``` math
f(t\zeta)=\sum_{j=0}^{n-1}(t^j-t^{j+1})S_j.
```
For $`0\le t<1`$, the normalised value $`f(t\zeta)/(1-t^n)`$ lies in the convex hull of $`S_0,\ldots,S_{n-1}`$. Bounds on these finitely many values therefore certify a whole segment. In the trinomial case the distinct control values are $`b`$ and $`-\zeta^n`$, both strictly inside the unit disc. With more terms, the additional partial sums need their own bounds.

<div id="res:sextic-spoke" class="proposition">

**Proposition 2** (prescribed-spoke guardrail). *There exist $`r\in(0,1)`$ for which every zero of
``` math
f_r(z)=z^6+\tfrac15 r^2 z^4-\tfrac15 r^4 z^2-r^6
```
lies in the open unit disc, yet the radial spoke from the origin to the zero $`r`$ leaves $`\{|f_r|<1\}`$.*

</div>

Indeed, after $`z=rw`$, the polynomial factors as $`r^6(w^2-1)(w^4+\tfrac65 w^2+1)`$, so all six roots have modulus $`r`$. However $`f_r(r/2)=-(327/320)r^6`$. Any $`r`$ with $`320/327<r^6<1`$ proves the assertion. Only this prescribed spoke is excluded; other connectors remain available. The corresponding radial evaluation is checked in [the sextic guardrail](https://github.com/wcook04/plectis-erdos/blob/0ba585f632fbbbb43af2ee9532d4e83752af3f67/ErdosProblems/Erdos1041/AbelControlPolygon.lean#L555). The factorisation above explains the root locations.

<a id="sec:problem"></a>

# The problem and the general regimes

<div id="res:problem" class="problem">

**Problem 3** (Erdős \#1041). Let $`f(z)=\prod_{i=1}^{n}(z-z_i)`$ be monic with $`n\ge2`$ and all $`z_i`$ in the open unit disc. Must two root occurrences be joined by a curve of length less than $`2`$ inside $`\{|f|<1\}`$?

</div>

Repeated roots give a constant path between two listed occurrences, so the geometric question concerns squarefree polynomials. The original question is Problem 5 of Erdős–Herzog–Piranian \[ehp1958, p. 139\]. Pendyala \[june2026, Thm. 1\] proves the complete degree-four case. A separate degree-seven counterexample has been announced on the [problem’s discussion page](https://www.erdosproblems.com/1041). That external claim is not assessed in this note; the results below concern the stated polynomial families and sufficient conditions.

Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a> treats arbitrary geometry when $`\mu\le13/25`$, without a root-location assumption. Its scaling corollary gives length less than $`(5/2)\mu^{1/n}`$ in the open level $`(25/13)\mu`$ for every squarefree monic polynomial. The independent $`71/10`$ argument below exhibits how inverse lifts and boundary arcs spend area. The disk-family theorem gives a different sufficient condition, using a simple critical value $`v`$ with $`0<|v|<1`$ and normalised separation radius $`4/3`$. The collinear and sparse families retain the target length $`2`$.

Two constructions organise the general estimates. Averaging inverse lifts and boundary arcs converts area into a freely selected connector. Resolving a simple saddle gives a holomorphic inverse whose Dirichlet energy controls its diameter trace. The weighted free-point theorem isolates a complementary critical-value estimate. Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">17</a> states the remaining selection question and the examples showing which information is insufficient.

<a id="sec:constant-factor"></a>

# Low critical values and a uniform path bound

The least critical value is the natural scale for the first merger of root components. A theorem at one fixed critical level therefore supplies a scale-invariant theorem for arbitrary monic polynomials. For a monic degree-$`n`$ polynomial put
``` math
K_t=\{z:|f(z)|\le t\},\qquad
 \mu=\min_{f'(c)=0}|f(c)|,\qquad \rho=\mu^{1/n}.
```

<div id="res:low-critical-thirteen-twentyfifths" class="theorem">

**Theorem 4** (low-critical parent regime). *Let $`f`$ be squarefree and monic of degree $`n\ge2`$, and let $`\mu`$ be its least critical-value modulus. If $`\mu\le13/25`$, then two distinct roots are joined inside $`\{|f|<1\}`$ by a rectifiable curve of length strictly less than $`2`$.*

</div>

<div id="res:scaled-low-critical" class="corollary">

**Corollary 5** (scale-free connection). *Every squarefree monic polynomial of degree $`n\ge2`$ has two distinct roots joined in $`\{|f|<(25/13)\mu\}`$ by a curve of length less than
``` math
2\bigl((25/13)\mu\bigr)^{1/n}.
```
In every degree the length can be chosen less than $`(5/2)\mu^{1/n}`$.*

</div>

<div class="proof">

*Proof.* Put $`s=((25/13)\mu)^{1/n}`$ and $`g(z)=s^{-n}f(sz)`$. Then $`g`$ is monic and its least critical-value modulus is $`13/25`$. Apply the theorem and scale the curve back by $`s`$. The rescaling step, transporting both the level and the extended variation of an arbitrary curve under $`z\mapsto h+cz`$, is [the affine transport of a contained rectifiable connector](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/PaperMetricScaling.lean#L40); the low-critical input remains ordinary. For $`n\ge3`$, $`(25/13)^{1/n}\le(25/13)^{1/3}<5/4`$. For $`n=2`$, the segment between the roots has length $`2\sqrt\mu`$ and lies in $`K_\mu`$. ◻

</div>

<a id="the-geometric-step-behind-1325."></a>

#### The geometric step behind $`13/25`$.

Suppose no curve of length less than $`2`$ joins two roots below level $`1`$. Conformal normalisation of an ancestor component gives points $`b_1,\ldots,b_k`$ in the hyperbolic disc with pairwise distance at least $`D`$. Write $`d_j=d_{\mathrm{hyp}}(0,b_j)`$. The inverse-map estimates also give a lower radius $`d_*>0`$ and
``` math
d_j\ge d_*,\qquad
 \sum_j\ell(d_j)\ge x:=\log(t/\mu),\qquad
 \ell(d)=-\log\tanh(d/2).
```
The difficulty is to use the pairwise separation without discarding the radial positions of the points. Projecting all the balls onto the circle of directions loses this information: balls at different radii can have overlapping projections. Instead, the open balls of radius $`D/2`$ around the $`b_j`$ are intersected with the same hyperbolic circle of radius $`r`$. Their intersections are disjoint, possibly empty, arcs. The hyperbolic cosine law gives their angular half-widths
``` math
w(d,r)=\arccos\!\left[\frac{\cosh d\cosh r-\cosh(D/2)}
                              {\sinh d\sinh r}\right]_{-1}^{1},
 \qquad \sum_j w(d_j,r)\le\pi,
```
where brackets denote truncation to $`[-1,1]`$. Choose radii $`r_i`$ and weights $`\sigma_i\ge0`$. If
``` math
\ell(d)\le U+\sum_i\sigma_iw(d,r_i)\quad(d\ge d_*),\qquad U>0,
```
then summing over the roots proves the finite dual bound
``` math
\boxed{\quad k\ge\frac{x-\pi\sum_i\sigma_i}{U}.\quad}
```
The summation and supremum step from the majorant and the slice bounds to the boxed inequality is [the finite dual arity floor, with the packing bound and the boundedness of the dual values as premises](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/PaperFiniteDual.lean#L68); the hyperbolic supplier of those premises is ordinary. The nonnegative weights combine valid bounds from several radii; the summation is elementary once the uniform majorant has been proved. Establishing that majorant and the geometric separation estimates is the substantive input. The resulting lower bound for $`k`$ enters the length–area comparison until a short boundary connection is forced. The complete comparison proof and rational certificate are in [the angular budget low critical closure](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/AngularBudgetLowCriticalClosure.md). The certified terminal time is $`635762889599/10^{12}`$, and $`(13/25)\exp(635762889599/10^{12})<1`$.

<a id="an-independent-area-proof."></a>

#### An independent area proof.

The next theorem gives a weaker numerical bound through an argument that needs no circle-slice certificate. It makes the area allocation explicit.

<div id="res:constant-factor-path" class="theorem">

**Theorem 6** (unconditional constant-factor path). *For every monic polynomial $`f`$ of degree $`n\ge2`$, two zero occurrences are joined by a possibly degenerate path of length at most
``` math
\frac{71}{10}\,\rho
```
inside $`K_{2\mu}`$. If $`f`$ is squarefree, their locations are distinct. If $`\mu\le1/2`$, the construction may be chosen inside $`\{|f|<1\}`$ with length at most $`5.7`$.*

</div>

The constant is the rationally certified specialization of a two-parameter bound. If the selected working component contains $`k\ge2`$ roots, then for every $`r\in(0,1)`$ and $`\lambda>1`$ the proof constructs a path in $`K_{\lambda\mu}`$ whose length is at most
``` math
\sqrt{\frac2k}\left(
   \frac{\sqrt2\,r}{(1-r)^2}
   +\lambda^{1/n}\left(
      \sqrt{\log(\lambda/r)}+
      \frac{\pi}{\sqrt{\log\lambda}}
    \right)
 \right)\rho.                                      \tag{CF}
```
For $`n\ge3`$, the choice $`\lambda=2`$, $`r=3/20`$ makes the bracket less than $`71/10`$; degree two has the exact root-segment bound $`2\rho`$.

<div class="proof">

*Proof.* A repeated zero gives a constant path of length zero, so assume $`f`$ is squarefree; then $`\mu>0`$. Write $`K_t=\{|f|\le t\}`$, $`C_T`$ for the component of $`K_T`$ containing a minimising critical point, and $`A(\sigma)=\operatorname{Area}(K_\sigma\cap C_T)`$. Degree two is the root segment of length $`2\rho`$ inside $`K_\mu`$; assume $`n\ge3`$.

If a regular component $`C'`$ of $`K_\sigma\cap C_T`$ holds $`k'`$ roots, then $`|dz|=\sigma\,d\varphi/|f'|`$ on $`\partial C'`$ and $`\int d\varphi=2\pi k'`$. Cauchy–Schwarz and coarea give
``` math
\mathcal H^1(\partial C')^2
 \le2\pi k'\,\sigma A'(\sigma).                     \tag{CF1}
```
Pólya’s inequality $`A(T)\le\pi T^{2/n}`$ and the change of measure $`d\sigma/\sigma`$ on $`[\mu,T]`$, $`T=\lambda\mu`$, produce a non-critical level $`t\in[\mu,T]`$ with $`t A'(t)\le\pi T^{2/n}/\log\lambda`$. The component $`C_t\subseteq C_T`$ still holds $`k\ge2`$ roots, and
``` math
\mathcal H^1(\partial C_t)
 \le\pi\sqrt{2k/\log\lambda}\,T^{1/n}.
```
The level $`t`$ is chosen from the mean of $`\sigma A'(\sigma)`$ *before* any path is assembled. That is the only device that removes the logarithmic divergence of $`A'`$ at a critical level.

For arguments avoiding the finitely many critical-value rays, each root in $`C_t`$ lifts along a value-ray to $`\partial C_t`$. Split every lift at level $`r\mu`$. On a one-root lobe the inverse of $`f/\mu`$ is univalent, so Koebe distortion bounds the low pieces pointwise; the precritical identity
``` math
\sum_i\frac{\mu^2}{|f'(z_i)|^2}\le\rho^2          \tag{CF2}
```
then aggregates them by Cauchy–Schwarz, paying $`\sqrt{2/k}`$ rather than once per root. Coarea and (CF1) bound the high pieces only after averaging in the argument. Choose one argument realising that average, order the lift endpoints cyclically on $`\partial C_t`$, and hop along the shortest adjacent boundary arc. Averaging the two lifts and the $`k`$ arcs over adjacent pairs gives (CF). Explicitly, the three contributions to that pair average satisfy
``` math
\begin{aligned}
 \frac2k\sum_i\ell_i^{\rm low}
 &\le\frac{2r\rho}{\sqrt{k}(1-r)^2},\\
 \frac2k\sum_i\ell_i^{\rm high}
 &\le\sqrt{\frac2k}\sqrt{\log(\lambda/r)}\,T^{1/n},\\
 \frac{\mathcal H^1(\partial C_t)}k
 &\le\sqrt{\frac2k}\frac{\pi T^{1/n}}{\sqrt{\log\lambda}}.
\end{aligned}
```
The low estimate is pointwise in the ray; the high estimate holds for the single ray chosen from its mean. The boundary estimate uses the level already selected. Thus these estimates apply together, and $`T^{1/n}=\lambda^{1/n}\rho`$ gives the three terms in (CF). For the final assertion, the repeated-zero case is already a constant path, and in degree two the root segment has length $`2\rho=2\sqrt\mu\le\sqrt2`$. For $`n\ge3`$, take $`\lambda=2`$ and $`r=3/20`$. Since $`k\ge2`$ and $`\mu\le1/2`$, (CF) gives
``` math
\begin{aligned}
 \operatorname{length}
 &\le \frac{60\sqrt2}{289}\mu^{1/n}
 +(2\mu)^{1/n}\left(
   \sqrt{\log(40/3)}+\frac{\pi}{\sqrt{\log2}}
 \right)\\
 &\le \frac{60\sqrt2}{289}+\sqrt{\log(40/3)}
      +\frac{\pi}{\sqrt{\log2}}\\
 &=5.676476\ldots<5.7.
 \end{aligned}
```
Here $`2\mu\le1`$, and the mean-value choice may be taken at a regular level strictly below the top of its positive-measure window. Thus the entire path lies in $`\{|f|<1\}`$. ◻

</div>

The component-arity, capacity and two-root persistence-window refinements are retained with their complete hypotheses in [unconditional constant factor bound](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/UnconditionalConstantFactorBound.md) and [minimal hub window join](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/MinimalHubWindowJoin.md). Their parent conclusions under $`\mu\le1/2`$ are already covered by Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a>; their additional content is control of a specified component or a specified descent arc. The exact distinction between a simple minimum and a unique minimum is preserved with the persistence-window argument.

<a id="sec:critical-proximity"></a>

# Critical proximity and straight-path obstructions

A critical point gives a different way to select two nearby roots, without assuming a sparse coefficient pattern. The logarithmic-derivative balance prevents one root from being arbitrarily closer to the critical point than all the others. This yields a bound on the sum of two distances. To turn that bound into a path theorem, both connecting segments would also have to stay inside the lemniscate; the examples below show why that extra step cannot be assumed.

<div id="res:critical-proximity" class="theorem">

**Theorem 7** (critical geometric-mean proximity). *Let $`n\ge2`$, let $`z_1,\ldots,z_n,c\in\mathbb C`$ with $`c\ne z_k`$ for every $`k`$, and suppose
``` math
\sum_{k=1}^n\frac1{c-z_k}=0.
```
If $`r>0`$ is determined by
``` math
r^n=\prod_{k=1}^n|c-z_k|,
```
then there are distinct indices $`i,j`$ such that
``` math
|c-z_i|+|c-z_j|\le2r.
```*

</div>

The proof chooses the two smallest distances $`d_i\le d_j`$. The reciprocal balance gives $`d_j\le(n-1)d_i`$, while minimality and the geometric-mean identity give $`d_i d_j^{\,n-1}\le r^n`$. The role of the balance is visible on setting $`t=d_j/d_i`$: it restricts $`t`$ to $`[1,n-1]`$, where
``` math
1+t\le2t^{(n-1)/n}.
```
Indeed, $`\log(2t^{(n-1)/n}/(1+t))`$ vanishes at $`t=1`$ and has derivative $`(n-1-t)/(nt(1+t))\ge0`$ on that interval. Consequently $`d_i+d_j\le2(d_i d_j^{\,n-1})^{1/n}\le2r`$. Without the reciprocal balance, the required restriction on $`t`$ would be missing. The complete complex theorem, including the selector and both inequalities, is checked as [the critical geometric-mean proximity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/CriticalTwoRootProximity.lean#L289).

<div class="corollary">

**Corollary 8** (two nearest roots). *If the roots lie in the open unit disc and $`c`$ is a non-root critical point, the two nearest roots to $`c`$ have total distance strictly below $`2`$.*

</div>

<div class="proof">

*Proof.* Apply the closed-disc two-nearest-root inequality after scaling by any radius $`R<1`$ containing all the roots. The ordinary reduction is recorded in the [global two-nearest-root budget](https://github.com/wcook04/plectis-erdos/blob/a729f05c40398663fd586c9da487ad874d898639/research_corpus/Erdos1041/GlobalCriticalTwoNearestBudget.md); Lean checks its algebraic core as . ◻

</div>

This is not silently promoted to a path theorem. The same source module checks two exact barriers to the most tempting completions.

<div id="res:straight-no-go" class="proposition">

**Proposition 9** (two straight-path no-go families). *There is a monic quintic with all roots in the open unit disc and a non-root critical point $`c`$ whose unique nearest root has a point on the straight spoke to $`c`$ outside $`\{|f|<1\}`$. There is also a monic cubic with all roots in the open unit disc such that the midpoint of every pair of distinct roots lies outside $`\{|f|<1\}`$.*

</div>

The certificates are exact rational-algebraic computations, checked as the [unique nearest-spoke escape](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/CriticalTwoRootProximity.lean#L438) and the [cubic all-straight midpoint obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/CriticalTwoRootProximity.lean#L569), and the displayed proposition itself, with both quintic and cubic exhibited as polynomials and the nearest-root condition quantified over every zero, records those same two evaluations. `PaperStraightObstructions.lean` is not in this checkout. The first defeats a tie-breaking escape hatch; the second defeats every straight root-pair segment. Together with Theorem <a href="#res:critical-proximity" data-reference-type="ref" data-reference="res:critical-proximity">7</a>, they isolate the real gap: critical-point proximity selects a short metric pair, but universal containment requires curved or topological geometry.

<a id="sec:solved-families"></a>

# Solved polynomial families

The following families cross that containment gap by controlling entire spokes or segments. The translated cubic fibre theorem has a complete rectifiable-path formalisation. For the other two families, the displayed proofs identify the checked kernels and the ordinary geometric steps.

<a id="translated-cubic-quotient-fibres"></a>

## Translated cubic quotient fibres

<div id="res:cubic-fibres" class="theorem">

**Theorem 10** (translated cubic quotient fibres). *Let $`q\ge2`$, $`h\in\mathbb C`$, and let $`P`$ be a monic cubic. Put
``` math
f(z)=P((z-h)^q).
```
If all zeros of $`f`$ lie in the open unit disc and $`f`$ has at least two distinct zeros, then two distinct zeros of $`f`$ are joined by a two-segment path of length strictly less than $`2`$ contained in $`\{|f|<1\}`$.*

</div>

For cubic roots $`r,s,v`$, the real charges $`\Re(r\overline{s+v})`$ sum to more than $`-3`$, so one is greater than $`-1`$. For that root, AM–GM and the exact cyclotomic cancellation $`(1-t)(1+t+t^2)=1-t^3`$ prove that its complete origin spoke is safe. Lean checks [the safe cubic root-spoke fan-in](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/CubicQuotientFiberCase.lean#L161). Pulling the spoke back under $`y\mapsto y^q`$ gives $`q`$ safe spokes from $`h`$; two different fibre points are joined through $`h`$ with length $`2|y|<2`$. The finite root-of-unity mean-square argument and fibre assembly are also formalised in [the complete translated cubic fibre theorem](https://github.com/wcook04/plectis-erdos/blob/27c2fc5fe3c55fe547feaeb4c9bb68b3cf63a5bf/lean/ErdosProblems/Erdos1041/PaperCubicFibres.lean#L240). Its conclusion constructs the explicit continuous rectifiable two-segment path with strict containment and variation below $`2`$. The exact source files occur in the successful compiled dependency closure of [the source-bound Lean build and axiom-audit record](https://github.com/wcook04/plectis-erdos/blob/27c2fc5fe3c55fe547feaeb4c9bb68b3cf63a5bf/verification/erdos1041-returned-r18-v5-full-audit-evidence.json).

<a id="primitive-sparse-quintics"></a>

## Primitive sparse quintics

<div id="res:primitive-quintic" class="theorem">

**Theorem 11** (primitive sparse quintics). *Let
``` math
p(z)=z^5+az^4+bz+c
```
be monic with all five root occurrences in the open unit disc. Then two distinct root occurrences $`w_i,w_j`$ satisfy
``` math
|bw_i+c|<1,
  \qquad
  |bw_j+c|<1,
```
and the corresponding two radial spokes join them through the origin inside $`\{|p|<1\}`$ with total length strictly below $`2`$. If the two occurrences coincide, the associated root-to-root path is degenerate.*

</div>

The stronger closed-disc selector has non-strict tails; if $`a\ne0`$ the selected tails are strict, while for $`a=0`$ strictness is exactly the interior-root condition. The phase-sensitive boundary theorem uses the first three Newton moments and a cubic separator. Its harmonic extension controls mixed interior/boundary configurations and shows that an unsafe interior tail contributes at most $`2/31`$. Lean checks the finite selectors [two boundary tail energies below one](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/PrimitiveQuinticBoundaryTail.lean#L200) and [two interior tail energies below one](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/PrimitiveQuinticInteriorTail.lean#L272); the rotation, moment identification, Abel path estimate, and two-spoke assembly are ordinary mathematics.

<a id="bdry:solved-polynomial-families"></a>

## Sharp collinear roots

The complete all-degree collinear theorem appears in Section <a href="#sec:collinear" data-reference-type="ref" data-reference="sec:collinear">14</a>. It gives the sharp Chebyshev constant, not merely an existence bound, and therefore belongs to the solved-family layer rather than the frontier layer. Lean checks [the constrained monic-comparison alternation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/SharpCollinearAlternation.lean#L158) and [its Chebyshev comparison-bound consumer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/SharpCollinearChebyshev.lean#L133); affine normalisation, root-gap selection, and transport back to the original line are ordinary.

<a id="sec:separation"></a>

# Critical-value separation in every degree

The solved families of Section <a href="#sec:solved-families" data-reference-type="ref" data-reference="sec:solved-families">5</a> are unconditional and complete, and each is confined to a shape of root configuration. This section gives a hypothesis that is not a shape at all. It constrains only the critical spectrum, it holds in every degree above an exact cutoff, and where it holds it gives the target constant $`2`$ rather than a constant multiple of it.

<div id="res:critical-value-separation" class="theorem">

**Theorem 12** (disk-family critical-value separation). *Let $`f`$ be monic of degree $`n\ge3`$, let $`c`$ be a simple critical point, and put $`v=f(c)\ne0`$. Fix $`w_0\in[0,1]`$ and $`S>\max(w_0,1-w_0)`$. Suppose every other critical point $`d`$ satisfies
``` math
\left|\frac{f(d)}v-w_0\right|\ge S .
```
Put $`p=w_0(1-w_0)`$. Then two distinct roots are joined inside $`\{|f|\le|v|\}`$ by a curve $`\Gamma`$ satisfying
``` math
\begin{equation}
\label{eq:disk-family-length}
 \operatorname{length}(\Gamma)^2
 \le 2|v|^{2/n}\Bigl(\frac{S}{n-1}\Bigr)^{2/n}
 \log\!\frac{S^2+S+p}{S^2-S+p}.
\end{equation}
```*

</div>

<div id="res:critical-value-thresholds" class="corollary">

**Corollary 13** (uniform radius $`4/3`$). *Let $`f`$ be monic of degree $`n\ge3`$ with all roots in the open unit disc. If $`c`$ is a simple critical point with $`0<|f(c)|<1`$ and, for some $`w_0\in[0,1]`$, every other critical point $`d`$ satisfies
``` math
\left|\frac{f(d)}{f(c)}-w_0\right|\ge\frac43,
```
then two roots are joined inside $`\{|f|<1\}`$ by a curve of length strictly below $`2`$. In degree three the branch-centred choice $`w_0=1`$ already works with $`4/3`$ replaced by $`6/5`$.*

</div>

<div id="res:separation-parent" class="corollary">

**Corollary 14** (a parent-problem regime). *Let $`f`$ be monic of degree $`n\ge3`$ with all roots in the open unit disc, and let $`c`$ be a simple critical point with $`v=f(c)`$ and $`0<|v|<1`$. If some real centre $`w_0\in[0,1]`$ admits a radius $`S\ge4/3`$ such that $`|f(d)/v-w_0|\ge S`$ for every other critical point $`d`$, then Erdős Problem #1041 holds for $`f`$.*

</div>

The hypothesis $`|v|<1`$ is required: normalised separation controls a connector in $`\{|f|\le|v|\}`$, which lies in the unit lemniscate only when $`|v|<1`$. The Fekete chain supplies $`|v|<1`$ at a minimum-modulus critical point, but an arbitrary selected critical value need not. The hypothesis is sufficient, not necessary: it does not assert that some critical value always admits such a disk. The cubic $`z^3+(3/100)z-3/4`$ shows in particular that the older separation-two condition does not cover all polynomials.

<div class="proof">

*Proof of Theorem <a href="#res:critical-value-separation" data-reference-type="ref" data-reference="res:critical-value-separation">12</a>.* Set $`\rho=|v|^{1/n}`$ and
``` math
P(w)=\frac{f(c+\rho w)}v.
```
Then $`P(0)=1`$, $`P'(0)=0`$, $`P''(0)\ne0`$, and its leading coefficient is $`|v|/v`$, of modulus one. This is the normalization used below; lengths scale back by $`\rho`$.

Let $`Q=D(w_0,S)`$ and let $`U`$ be the component of $`P^{-1}(Q)`$ containing $`0`$. The hypotheses put both $`0,1`$ and the segment $`[0,1]`$ in $`Q`$, while $`0`$ is the only critical point in $`U`$. The restriction $`P:U\to Q`$ is proper. Riemann–Hurwitz, with one simple ramification point, makes it a degree-two map and makes $`U`$ simply connected. Thus $`1-P`$ has only its double zero at $`0`$ on $`U`$ and admits a single-valued square root $`\xi^2=1-P`$. This map is proper and locally injective onto
``` math
\widetilde Q=\{\xi:|\xi^2-(1-w_0)|<S\},
```
the connected simply connected double cover of $`Q`$. It is therefore a conformal bijection. Its inverse $`Z`$ is the global resolved branch, and $`Z([-1,1])`$ joins the two distinct points over $`P=0`$ inside $`\{|P|\le1\}`$. This component argument is what prevents the local inverse germ from changing sheets or escaping during continuation.

Put $`a=1-w_0`$. The conformal map
``` math
\zeta(\xi)=\xi\sqrt{\frac{S}{S^2+a\xi^2-a^2}}
       :\widetilde Q\longrightarrow\mathbb D
```
sends $`[-1,1]`$ to $`[-q,q]`$, where $`q^2=S/(S^2+p)`$. Applying the Bergman segment inequality to $`Z\circ\zeta^{-1}`$ gives
``` math
\operatorname{length}(Z([-1,1]))^2
 \le\frac2\pi\log\!\frac{S^2+S+p}{S^2-S+p}
       \operatorname{Area}(U).                       \tag{*}
```

The area estimate concerns this particular two-sheeted component. For $`1-w_0<S'<S`$, let $`U'`$ be the component of $`\{|P-w_0|<S'\}`$ containing $`0`$. It is a proper regular component containing exactly two zeros of $`P-w_0`$, counted with multiplicity. The exterior-fibre capacity gap gives
``` math
\frac{\operatorname{cap}(\overline{U'})^n}{S'}<\frac1{n-1}.
```
Pólya’s area–capacity inequality \[polya1928, printed pp. 280–282\] then gives $`\operatorname{Area}(U')<\pi(S'/(n-1))^{2/n}`$. The components $`U'`$ exhaust $`U`$ as $`S'\nearrow S`$, so $`\operatorname{Area}(U)\le\pi(S/(n-1))^{2/n}`$. Substitute this in (\*) and scale lengths by $`\rho`$ to obtain <a href="#eq:disk-family-length" data-reference-type="eqref" data-reference="eq:disk-family-length">[eq:disk-family-length]</a>. No relative area inequality is used here; the disposition of Dubinin’s Theorem 1 is recorded in the bibliography entry \[dubinin\]. That theorem has a full covering hypothesis; neither that hypothesis nor its relative-area conclusion is used in this proof. ◻

</div>

For $`4/3\le S\le2`$ and $`p\ge0`$,
``` math
\frac{S^2+S+p}{S^2-S+p}\le\frac{S+1}{S-1}\le7,
 \qquad \frac{S}{n-1}\le1,
```
and $`\log7<2`$. Thus <a href="#eq:disk-family-length" data-reference-type="eqref" data-reference="eq:disk-family-length">[eq:disk-family-length]</a> is strictly below $`4|v|^{2/n}<4`$ under the corollary’s hypotheses. The cubic constant follows from $`(3/5)^{2/3}\log11<2`$.

<a id="bdry:critical-value-separation"></a>

#### Boundary.

The two-sheeted component, its square-root uniformisation, the Bergman segment inequality, the exterior-fibre capacity gap, Pólya’s inequality and the exhaustion are ordinary mathematics. Their complete immutable source is the [disk-family critical-value separation record](https://github.com/wcook04/plectis-erdos/blob/8efbccc235df64a38d83f5dc7b1949e2ad18270d/research_corpus/Erdos1041/problem/DiskFamilyCriticalValueSeparation.md). The separate [Lean numerical kernel](https://github.com/wcook04/plectis-erdos/blob/f36e325c8b05fe5c3ce8a2ca32a699f6dc6336b9/ErdosProblems/Erdos1041/DiskFamilyCriticalValueSeparation.lean) checks the coefficient bound for $`n\ge3`$, $`4/3\le S\le2`$, the cubic $`S=6/5`$ inequality, and the implication from the squared bound to length below $`2`$. It does not formalise the analytic hypotheses producing <a href="#eq:disk-family-length" data-reference-type="eqref" data-reference="eq:disk-family-length">[eq:disk-family-length]</a>; the adjacent axiom-audit source audits those numerical declarations rather than the ordinary analytic theorem. Nothing in this section asserts a separated disk always exists, covers the near-tie or multiple-saddle strata, or proves the unrestricted problem. The argument uses Pólya’s absolute area–capacity inequality, not the relative covering inequality in Dubinin’s Theorem 1 \[dubinin\].

Pendyala’s degree-four theorem \[june2026, Thm. 1\] has no critical-spectrum hypothesis. The present separation criterion applies in every degree $`n\ge3`$ and supplies an explicit inverse-map length estimate.

<a id="sec:exact-obstructions"></a>

# Three exact covering obstructions

None of the following is a counterexample to Erdős #1041. Each kills a covering reading of a sufficient regime. Rational cores are checked in [revision r2 exact cores](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/RevisionR2ExactCores.lean); the ordinary arguments are in [exact obstructions r2](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/ExactObstructionsR2.md).

<div id="res:sep-or-false" class="proposition">

**Proposition 15** (no separation-or covering). *Let $`f(z)=z^3+(3/100)z-3/4`$. Every root lies in the open unit disc, both critical points are simple, the critical values lie on distinct positive rays, $`\mu>13/25`$, and
``` math
\bigl|1-f(c_-)/f(c_+)\bigr|<2/375<2.
```*

</div>

The whole proposition, including the least-modulus assertion rather than a supplied minimum, is ordinary in this note. `PaperSeparationCounterexample.lean` is not in this checkout; the distinct quartic file `SeparationCounterexampleR13.lean` is not this cubic example.

<div id="res:one-root-gamma-false" class="proposition">

**Proposition 16** (one-root gamma bound is false). *Let $`p(z)=z^8-(3/2)z`$ and let $`C`$ be the component of $`\{|p|\le1\}`$ containing the origin. Then $`C`$ contains exactly one zero and a neighbourhood of the closed disc of radius $`5/8`$, so $`\mathcal H^1(\partial C)>5\pi/4`$. The constant $`\Gamma(1/4)^2/(2\sqrt{\pi})`$ is at most $`(\pi/2)(1+\sqrt2)<5\pi/4`$.*

</div>

A degree-uniform one-root perimeter constant, if one exists, must be at least $`2\pi`$. For each fixed $`a>1`$, the one-root component of $`\{|z^N-az|\le1\}`$ contains every disc of radius $`r<1/a`$ for all sufficiently large $`N`$. A circle of radius between $`1/a`$ and $`1`$ isolates that component by Rouché’s theorem. Its perimeter is therefore at least $`2\pi/a`$ in the limit; now let $`a\downarrow1`$. The family $`z^N-z`$ at level $`1`$ does not supply a one-root component. Neither general path theorem uses the rejected perimeter bound.

<div id="res:arity-not-capacity" class="proposition">

**Proposition 17** (arity does not force a capacity gap). *Let $`g(z)=z^3-(3/400)z-3/32`$. All roots lie in the open unit disc, $`\mu=187/2000\le1/2`$, the first-merge arity is $`k_0=2`$, and the ancestor component at level $`2\mu`$ has normalised capacity $`1`$.*

</div>

<a id="sec:newton"></a>

# The Newton value equation

Away from the critical set, define the complex Newton field
``` math
N(z)=-\frac{f(z)}{f'(z)} .
```
Let $`I\subseteq\mathbb R`$ be an interval on which a differentiable curve $`z`$ satisfies $`f'(z(t))\ne0`$ and $`z'(t)=N(z(t))`$. Put $`w(t)=f(z(t))`$.

<div id="res:value" class="theorem">

**Theorem 18** (value equation). *For a polynomial $`f`$ and a differentiable curve $`z:I\to\mathbb C`$ on an interval $`I`$, assume $`f'(z(t))\ne0`$ and $`z'(t)=-f(z(t))/f'(z(t))`$ throughout $`I`$. Then $`w=f\circ z`$ satisfies $`w'=-w`$, and
``` math
f(z(t))=e^{-(t-t_0)}f(z(t_0))\qquad(t,t_0\in I).
```*

</div>

The local computation is one line: $`w'=f'(z)z'=-f(z)=-w`$. Multiplication by $`e^t`$ and integration on $`I`$ give the displayed identity. Lean checks the local complex-parameter chain rule as [the Newton-flow value equation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L50) and its scaled zero-derivative form as [vanishing of the exponentially scaled value](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L64). The integrated real-time assertion above is an ordinary consequence.

For an existing trajectory with nonzero initial value, the value moves inward on one positive ray. A zero value remains zero and has no argument. Thus a trajectory starting in $`\{|f|<1\}`$ stays there at later times in its interval of existence. The equation neither constructs a global trajectory nor identifies a whole ray preimage with one flow line.

<div id="res:ray" class="corollary">

**Corollary 19** (ray separation). *Let $`a<b`$, let $`z:[a,b]\to\mathbb C`$ be continuous, and suppose $`z`$ is differentiable on $`(a,b)`$ with $`f'(z(t))\ne0`$ and $`z'(t)=-f(z(t))/f'(z(t))`$ there. Then
``` math
f(z(b))=e^{a-b}f(z(a)).
```
If the endpoint values are nonzero, they lie on the same positive ray. In particular, critical points whose values lie on distinct positive rays cannot be the endpoints of such a finite connection.*

</div>

Apply the value equation inside $`(a,b)`$ and pass to the endpoints by continuity. This does not evaluate $`-f/f'`$ at a critical endpoint. Lean checks the algebraic contradiction from an assumed exponential endpoint relation in [the distinct-ray endpoint implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L315); the existence and endpoint behaviour of trajectories are additional geometric questions.

<a id="sec:arguments"></a>

# Arguments, not moduli

It is tempting to arrange a generic perturbation so that the critical values are pairwise distinct, or that their moduli are pairwise distinct, and to conclude that saddle connections are excluded. Neither is enough.

Two distinct critical values can lie on one ray, and two critical values with distinct moduli certainly can: the ray records the argument, and the modulus is exactly the coordinate the flow contracts. By Corollary <a href="#res:ray" data-reference-type="ref" data-reference="res:ray">19</a> the invariant that excludes connections is the argument. What a perturbation must therefore achieve is pairwise distinct critical-value *arguments*, which is a condition on $`n-1`$ points modulo the circle rather than on their positions in the plane.

The cost of that condition is also checked, and it is small.

<div id="res:locus" class="theorem">

**Theorem 20** (ray-collision locus). *Let $`a\ne b`$ be complex. Every common translation $`\beta`$ for which $`a+\beta`$ and $`b+\beta`$ lie on the same positive ray has the form
``` math
\beta=\frac{ra-b}{1-r},
  \qquad r\in\mathbb{R}_{>0},\ r\ne1 .
```*

</div>

So each pair of critical values contributes a one-real-parameter forbidden locus in the translation plane, given in closed form ([the ray-collision parameterization](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L107)). A finite union of such loci has empty interior, so [an arbitrarily small translation separates the arguments](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L197). Under an explicit margin, [a small constant perturbation keeps the roots in the unit disc](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L287). Fixed-degree lower semicontinuity in Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">17</a> passes a dense-generic closed-level length bound to the whole coefficient class. Quantitative forward transport of a selected curve requires additional control, but is not a premise of that existence argument.

<a id="sec:reciprocal"></a>

# Local coordinates for perturbative competitors

For $`f(z)=\prod_j(z-a_j)`$ with $`a_j\ne0`$, put $`r=\min_j|a_j|`$ and $`p_m=\sum_j a_j^{-m}`$. On $`|z|<r`$, the exact expansion
``` math
\log|f(z)|=\log|f(0)|-\Re\sum_{m\ge1}\frac{p_m}{m}z^m
```
keeps the nonlinear terms as coefficient coordinates. If $`q=|z|/r<1`$, the tail after $`N`$ has modulus at most $`nq^{N+1}/((N+1)(1-q))`$; differentiated geometric series give the corresponding first and second derivative bounds. The complete reciprocal recurrences, zero-margin staple construction, and quadratic contact test are proved in the long record and [reciprocal newton expansion](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/ReciprocalNewtonExpansion.md). Their use requires a compatible local contact; the expansion alone supplies no global root-pair selection.

<a id="sec:gap"></a>

# A proof gap in the unrestricted argument

The March manuscript’s Proposition 12 claims the following load-bearing statement. For $`u=-\log|f|`$, a connected component $`V`$ of $`\{u>c\}`$ carrying $`m\ge2`$ simple zeros, and the stated regularity and Morse hypotheses, it constructs, for every $`\varepsilon>0`$, an embedded spanning tree $`G_\varepsilon\subset V`$ with
``` math
\operatorname{len}(G_\varepsilon)
 \le\frac1{2\pi}\int_{2\alpha}^{\infty}P_V(t)\,dt+\varepsilon.
\tag{5.1}\label{eq:prop12-bound}
```
The final theorem uses this estimate, so the issue below cannot be bypassed by calling the proposition auxiliary. Proposition 7 of the unattributed local revision repeats the same estimate.

The estimate itself is false. Take the Cassini polynomial $`f_a(z)=z^2-a^2`$ at $`a=9/10`$. Its component contains the two roots at distance $`9/5`$ and satisfies the relevant Morse and critical-value hypotheses. Direct level-length calculation gives the upper majorant
``` math
4\bigl(\sqrt{a^2+a}-a\bigr)<\frac{41}{25}
```
for the right side of <a href="#eq:prop12-bound" data-reference-type="eqref" data-reference="eq:prop12-bound">[eq:prop12-bound]</a> before $`\varepsilon`$, whereas every connected set containing both roots has length at least $`9/5`$. Since $`9/5-41/25=4/25`$, choosing a smaller positive $`\varepsilon`$ contradicts the assertion. Thus neither a different local saddle neighbourhood nor a perfect topological decomposition can recover the printed coefficient $`1/(2\pi)`$. The exact inequality and its abstract tree-budget contradiction are checked in `ErdosProblems.Erdos1041.CassiniTreeBudget`; the level-length majorant is an explicit analytic input, not a kernel-checked integral evaluation.

At an interior index-one critical point $`p`$, the proof invokes a Morse chart
``` math
u=\mu+x^2-y^2
```
and replaces the saddle by a three-ended neighbourhood having one connected lower cross-section and two connected upper cross-sections. That local model is false as written. Because $`p\in V`$ and $`V`$ is open, a sufficiently small closed disc around $`p`$ lies entirely in $`V`$. In that disc the full Morse chart has four sectors: two components of $`u>\mu`$ and two components of $`u<\mu`$. A global component argument cannot delete one local sector from a disc already contained in $`V`$.

This independently diagnoses a proof step, but the Cassini witness above also refutes the proposition’s statement. A different route might cut an adjoining regular annulus along a separatrix or regular flow arc before forming the block, retain a four-pronged saddle neighbourhood and change the assembly, or replace the local construction by the ray-cut decomposition proposed below. But no repair can retain <a href="#eq:prop12-bound" data-reference-type="eqref" data-reference="eq:prop12-bound">[eq:prop12-bound]</a>; it must pay a positive attachment cost, select only one short pair instead of spanning every root, or use a different global metric inequality. The shorter descriptions of the same three-ended block do not repair the four-sector topology.

Corollary <a href="#res:ray" data-reference-type="ref" data-reference="res:ray">19</a> supplies one independent input for a different route: distinct critical-value arguments exclude saddle-to-saddle Newton connections. It does not itself prove the compact planar decomposition, classify all orbit endpoints or provide the metric gluing estimate. Those are separate problems below.

<a id="sec:finite"></a>

# Computational searches

Raster searches over sampled root configurations supplied candidate paths through degree ten. They supply no degree-wise upper bound. A raster path becomes a continuous certificate only after every connecting segment and its length have been enclosed. The sample counts, grid distances, and search parameters are retained in the long record. Further searches should track named obstructions: clustered critical values, shrinking attachment windows, component mergers, and distance to the unit level.

<a id="sec:binomial"></a>

# Exact symmetric benchmark: complementary chords for every binomial degree

There is a complete all-degree model family which isolates the metric geometry without pretending to select paths for arbitrary polynomials. Let $`f(z)=z^n-a`$, where $`n\ge2`$ and $`0<|a|<1`$. After rotation write $`a=r^n>0`$, put $`c=\cos(\pi/n)`$, and set
``` math
r_*=(1+c^n)^{-1/n},\qquad
 \varepsilon=(1-r^n)^{1/n}.
```

<div class="theorem">

**Theorem 21** (complementary binomial chords). *Two adjacent zeros of $`z^n-a`$ can be joined by an explicit polygonal path inside $`\{|z^n-a|<1\}`$ of length strictly below $`2`$. For $`r\le r_*`$ the adjacent-root chord itself works. For $`r\ge r_*`$, two radial legs and an inner adjacent crossing chord work after an arbitrarily small radial contraction. These two constructions meet at $`r=r_*`$, where the outer chord attains $`|f|=1`$ at its midpoint: equality is closed containment, not the open lemniscate. Open containment at and above the switch uses the inner chord after a radial contraction.*

</div>

The central chord calculation is exact. On the chord between adjacent roots,
``` math
\max |z^n-r^n|=r^n(1+c^n),
```
with the maximum at the midpoint; hence the first construction has precisely the threshold $`r_*`$. Above it, put $`t=\varepsilon/c`$. The path from $`r`$ to $`t`$ to $`t\omega`$ to $`r\omega`$ has its crossing chord in the closed lemniscate, and its length is
``` math
2r-2\varepsilon\tan\!\left(\frac\pi4-\frac\pi{2n}\right)<2r<2.
```
The radius $`t`$ is maximal: a larger crossing chord already escapes at its midpoint. Contracting that chord to radius $`\lambda t`$ with $`0<\lambda<1`$ makes the containment strict while keeping the two radial connections and the strict length bound. For $`n=2`$, the adjacent-root diameter is already a strict path of length $`2r<2`$.

The proof uses the sharp inequality
``` math
1+\cos(n\theta)\le2\cos^n\theta
  \qquad (|\theta|\le\pi/n),
```
followed by elementary chord geometry and the disk inequality that justifies the contraction. It is an authored ordinary all-degree proof with bounded numerical replay, not a Lean theorem or a priority claim. Its role is a symmetric benchmark: the exact transition says why a direct outer chord fails and why the complementary inner chord repairs it. It gives no path optimality, no theorem for arbitrary monic polynomials, and no solution of Erdős Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">3</a>.

<a id="sec:collinear"></a>

# The sharp collinear theorem: order buys an exact Chebyshev extremal

Collinearity supplies the global ordering that arbitrary complex root sets lack, and it yields a sharp all-degree solved subcase. Put
``` math
C_n=\frac{1}{2^{n-1}\cos^n(\pi/(2n))}.
```

<div id="res:sharp-collinear-root-diameter" class="theorem">

**Theorem 22** (sharp collinear root-diameter bound). *Let $`f`$ be monic of degree $`n\ge2`$, with collinear zero occurrences of diameter $`D`$. Then some two zero occurrences are joined by their straight segment, of length at most $`D`$, on which
``` math
|f|\le C_n\left(\frac D2\right)^n.
```
The constant is sharp: equality is attained by the affine images of the scaled Chebyshev root configuration with extreme roots at distance $`D`$.*

</div>

<div class="proof">

*Proof.* Repeated zeros give the constant path, so suppose the zeros are distinct. Translation, rotation, and scaling by $`R=D/2`$ reduce to a monic real-rooted polynomial $`q`$ with roots
``` math
-1=y_1<\cdots<y_n=1,
 \qquad |f|=R^n|q|\ \text{on the root line}.
```
Set $`r_n=\cos(\pi/(2n))`$ and compare $`q`$ with the monic polynomial
``` math
q_*(x)=\frac{T_n(r_nx)}{2^{n-1}r_n^n}.
```
It vanishes at $`\pm1`$ and has $`|q_*|\le C_n`$ on $`[-1,1]`$. Choose a point $`c_i`$ of maximum $`|q|`$ in each adjacent gap. If every gap maximum exceeded $`C_n`$, then $`h=q-q_*`$ would have the alternating signs of $`q(c_i)`$ at the $`c_i`$, hence a zero between each consecutive pair, as well as zeros at $`-1`$ and $`1`$. These are $`n`$ distinct zeros, whereas the leading terms cancel and $`\deg h\le n-1`$, a contradiction. Thus one selected gap has $`|q|\le C_n`$ throughout, and scaling back proves the bound.

For sharpness take the roots of $`q_*`$, namely
``` math
\frac{\cos((2k-1)\pi/(2n))}{r_n},\qquad 1\le k\le n.
```
Their extreme roots are $`\pm1`$, and every adjacent gap reaches $`C_n`$ at a Chebyshev extremum. ◻

</div>

If $`D<2`$, the displayed level is below one and this segment lies in the open lemniscate. For $`n\ge3`$, the same strict level holds already at $`D=2`$; degree two is the exact boundary case. The proof is a complete authored ordinary argument. Two load-bearing alternation and Chebyshev-comparator kernels are Lean checked, while the affine normalization and transport remain ordinary; bounded replay is regression evidence only. This proves neither that every adjacent gap is safe nor any non-collinear analogue: the real order used in the alternation count is precisely what the general problem lacks.

<a id="sec:freepoint"></a>

# A Poisson identity for critical-value means

Write $`\mathrm{FP}_m`$ for the equal-weight inequality $`\sum_j(\prod_k|1-\overline{c_k}c_j|)^{1/m}\le m`$.

The same points can define both an analytic geometric mean and a positive Poisson mixture. Their logarithmic-derivative relation converts the desired nonlinear estimate into a diagonal Taylor-coefficient inequality.

<div id="res:fp-weighted-all-degree" class="theorem">

**Theorem 23** (weighted free-point inequality in every degree). *Let $`c_1,\ldots,c_m\in\overline{\mathbb D}`$ and let $`w_j>0`$ satisfy $`\sum_j w_j=1`$. Set
``` math
G(z)=\prod_k |1-\overline{c_k}z|^{w_k}.
```
Then
``` math
\sum_j w_j G(c_j)^2\le 1,
```
with equality if and only if every $`c_j=0`$. Equal weights therefore give $`\mathrm{FP}_m`$ for every $`m`$.*

</div>

<div class="proof">

*Proof.* First assume $`|c_j|<1`$ and choose analytic logarithms zero at the origin. Put
``` math
g(z)=\exp\sum_jw_j\log(1-\overline{c_j}z)
      =1+\sum_{\nu\ge1}a_\nu z^\nu,
 \qquad P=\sum_jw_jP_{c_j},
```
where $`P_c(\zeta)=(1-|c|^2)/|\zeta-c|^2`$ and $`dm`$ denotes normalised arclength. On the unit circle,
``` math
P=1-2\Re\frac{\zeta g'}g.
```
Subharmonicity and Taylor orthogonality therefore give
``` math
\begin{align*}
 \sum_jw_jG(c_j)^2
 &\le\int |g|^2P\,dm\\
 &=\int\bigl(|g|^2-2\Re(\zeta g'\overline g)\bigr)\,dm\\
 &=1-\sum_{\nu\ge1}(2\nu-1)|a_\nu|^2.
\end{align*}
```
All series converge on a neighbourhood of the closed disc in this case. For boundary points, replace $`c_j`$ by $`rc_j`$ and let $`r\uparrow1`$. The finite left sum and every fixed Taylor coefficient converge; passing first with a finite coefficient sum proves the same inequality in the limit. Equality forces $`g=1`$. The rational function $`\sum_jw_j\overline{c_j}/(1-\overline{c_j}z)`$ then vanishes identically. A nonzero point would give a pole with nonzero total positive weight, so all points are zero. Weighted Cauchy–Schwarz gives the equal-weight linear inequality. ◻

</div>

The coefficient $`a_1=-\overline{\sum_jw_jc_j}`$ gives the immediate refinement
``` math
\sum_jw_jG(c_j)^2\le1-\left|\sum_jw_jc_j\right|^2.
```
Thus the proof records a quantitative loss when the point centroid is nonzero. The specialised four-point and central-radius proofs are retained in the long record; the all-degree inequality above removes their cardinality restriction.

<div id="res:fp-to-s" class="theorem">

**Theorem 24** (critical-value mean in every degree). *Let $`f`$ be monic of degree $`n\ge2`$, with roots in a closed disc of radius $`R`$, and let $`c_1,\ldots,c_{n-1}`$ be its critical points with multiplicity. Then
``` math
\sum_{j=1}^{n-1}|f(c_j)|^{2/(n-1)}
 \le(n-1)R^{2n/(n-1)}.
```
In particular $`(S)_n`$, the inequality $`\sum_j|f(c_j)|^{1/n}\le(n-1)R`$, holds in every degree.*

</div>

<div class="proof">

*Proof.* Translation and scaling reduce to $`R=1`$; the case $`R=0`$ is immediate. Write $`q=f'/n=\prod_j(z-c_j)`$ and $`q^\#(z)=\prod_j(1-\overline{c_j}z)`$. For roots strictly inside the unit disc, on $`|\zeta|=1`$,
``` math
\Re\frac{\zeta f'(\zeta)}{f(\zeta)}
 =\sum_i\Re\frac{\zeta}{\zeta-z_i}>\frac n2.
```
Hence $`|f-\zeta q|<|q|=|q^\#|`$ there. Gauss–Lucas makes $`q^\#`$ zero-free on the closed disc, so the maximum principle gives $`|(f-zq)/q^\#|<1`$ inside. At a critical point,
``` math
|f(c_j)|\le\prod_k|1-\overline{c_k}c_j|.
```
The equal-weight quadratic theorem proves the required bound. Contracting a closed-disc root configuration and taking a limit treats its boundary. Power means give $`(S)_n`$, and scaling restores $`R`$. ◻

</div>

The constant is attained by $`f(z)=(z-h)^n-\lambda`$ with $`|\lambda|=R^n`$. These ordinary analytic proofs are recorded in [free point quadratic all degrees](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/FreePointQuadraticAllDegrees.md) and [centred circle quadrinomial connector](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/CentredCircleQuadrinomialConnector.md). Lean checks [the complete critical-value mean](https://github.com/wcook04/plectis-erdos/blob/27c2fc5fe3c55fe547feaeb4c9bb68b3cf63a5bf/lean/ErdosProblems/Erdos1041/PaperCriticalValueMeanR10.lean#L101), with the complete all-degree conclusion, arbitrary centre, $`R=0`$, and critical points counted with multiplicity. The exact source bytes and its directly audited target alias are recorded in [the source-bound Lean build and axiom-audit record](https://github.com/wcook04/plectis-erdos/blob/27c2fc5fe3c55fe547feaeb4c9bb68b3cf63a5bf/verification/erdos1041-returned-r18-v5-full-audit-evidence.json). The argument above explains that statement; the earlier candidate status in the source header predates the successful audit. A critical-value mean supplies no attachment or path-length estimate by itself.

<a id="sec:orlicz"></a>

# The exact nonlinear lifetime currency

The merge-tree route has its own exact theorem. For each nontrivial child component $`u`$, let $`k_u`$ be its number of roots and let $`r_u=\beta_u/\beta_{\operatorname{parent}(u)}\in(0,1]`$ be its merge-scale ratio. Its contribution to the attachment age of each descendant root is
``` math
x_u=\frac1{k_u}\log\frac1{r_u}.
```
The edge lifetime is written
``` math
\lambda_k(q)=\log\frac{1+q^{2/k}}{1-q^{2/k}},
 \qquad
 I_k(r)=\int_r^1\frac{dq}{q\lambda_k(q)}.
```

<div id="res:orlicz-currency" class="theorem">

**Theorem 25** (exact attachment-age/lifetime currency). *Define
``` math
\Phi(x)=\int_0^x\frac{dt}{\log(\coth t)}\qquad(x\ge0).
```
At $`t=0`$ the integrand is understood by its continuous limiting value $`0`$ (equivalently, the integral is improper at that endpoint). For every integer $`k\ge1`$ and $`0<r\le1`$, with $`x=k^{-1}\log(1/r)`$,
``` math
I_k(r)=k\Phi(x).                                      \tag{O1}
```
The function $`\Phi`$ is increasing and strictly convex on $`(0,\infty)`$, and
``` math
\frac{\Phi(x)}x\longrightarrow0\qquad(x\downarrow0). \tag{O2}
```
Consequently, for every fixed $`k\ge1`$ and every $`c>0`$, some $`0<r<1`$ satisfies
``` math
I_k(r)<c\,\frac1k\log\frac1r.                        \tag{O3}
```
In particular, there is no positive universal linear conversion from attachment age to lifetime.*

</div>

<div class="proof">

*Proof.* Set $`q=e^{-kt}`$. Then $`dq/q=-k\,dt`$, the endpoints $`q=1,r`$ become $`t=0,x`$, and
``` math
\frac{1+e^{-2t}}{1-e^{-2t}}=\coth t,
```
which proves (O1). Since $`\coth t`$, and hence $`\log(\coth t)`$, is strictly decreasing, the positive integrand $`1/\log(\coth t)`$ is strictly increasing. This proves monotonicity and strict convexity. Moreover
``` math
0\le\frac{\Phi(x)}x\le\frac1{\log(\coth x)}\longrightarrow0,
```
which gives (O2); taking $`r=e^{-kx}`$ gives (O3). ◻

</div>

The identity explains why a linear charge per attachment age loses the behaviour of very young edges. Chain allocation must retain the distribution of ages and the convex function $`\Phi`$. The weighted Jensen bounds and the two-young-root selector are retained in [attachment age lifetime orlicz](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/AttachmentAgeLifetimeOrlicz.md). They still require a geometric compatibility estimate before they produce a contained connector.

<a id="sec:open"></a>

# The remaining geometric selection problem

Let $`\mathcal K_n`$ be the compact coefficient class of monic degree-$`n`$ polynomials with roots in the closed unit disc. Define
``` math
\Lambda(f)=\inf_\gamma\operatorname{length}(\gamma),
```
where $`\gamma\subset\{|f|\le1\}`$ joins two different listed root occurrences. A repeated root permits a constant curve.

<a id="a-dense-generic-class-suffices."></a>

#### A dense generic class suffices.

The functional $`\Lambda`$ is lower semicontinuous. Indeed, bounded-length competitors have uniformly bounded images and admit constant-speed parametrisations with uniformly bounded Lipschitz constants. Arzelà–Ascoli, convergence of root multisets, and uniform convergence of the polynomials on compact sets produce a limiting competitor. Its length is no larger than the lower limit of the approximating lengths, and closed sublevel containment passes to the limit. Thus a dense generic bound $`\Lambda\le2`$ proves that bound on all of $`\mathcal K_n`$. For an open-disc polynomial, enclosing its roots in a disc of radius $`R<1`$ and scaling gives a path with length at most $`2R<2`$ in $`\{|f|\le R^n\}\subset\{|f|<1\}`$.

For $`f(z)=z^n-1`$, the punctured unit sublevel has separate root sectors. Every path between distinct roots passes through zero, and the two radial segments attain length $`2`$. The exact closed-class question is therefore
``` math
\boxed{\Lambda(f)\le\Lambda(z^n-1)=2\qquad(f\in\mathcal K_n).}
```
The lower-semicontinuity argument is proved in [generic sufficiency closure](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/GenericSufficiencyClosure.md).

<a id="a-sufficient-canonical-arc-estimate."></a>

#### A sufficient canonical-arc estimate.

On the generic simple-critical, ray-separated class, cutting the value plane along critical rays gives the finite inverse-sheet construction recorded in [attachment aware reeb](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/AttachmentAwareReeb.md). Let $`L_f(c)`$ be the length of the canonical two-root descent arc through a critical point $`c`$. Only critical points with $`|f(c)|\le1`$ give admissible unit-level candidates. The sufficient metric target is
``` math
\min_{\substack{f'(c)=0\\|f(c)|\le1}}L_f(c)\le2.
```
Since $`\Lambda`$ minimises over all curves, this canonical minimum is an upper bound for $`\Lambda`$. Equality between the two minimisations is not assumed. The ordinary slit-sheet construction closes its stated generic topology problem; formalising that construction remains a separate task.

<a id="the-attachment-obstruction-is-quantitative."></a>

#### The attachment obstruction is quantitative.

For $`f(z)=z^n-r^n`$, the inverse image of the positive value ray with argument $`\theta`$ approaches the saddle at zero only if its value-plane direction approaches $`\pi`$. A lift meets $`B(0,\varepsilon)`$, with $`0<\varepsilon<r`$, precisely when
``` math
\cos\theta<0,\qquad
 |\sin\theta|<(\varepsilon/r)^n.
```
The total angular window is $`2\arcsin((\varepsilon/r)^n)`$. An angular mean length bound therefore gives no uniform control at the shrinking set of attachable directions. A successful fixed-attachment estimate needs this angular concentration or a construction free to choose its attachment. The binomial itself is solved by radial segments.

<a id="which-information-is-insufficient."></a>

#### Which information is insufficient.

The sextic of Proposition <a href="#res:sextic-spoke" data-reference-type="ref" data-reference="res:sextic-spoke">2</a> excludes automatic control of every prescribed root spoke once further partial sums occur. The exact Cassini example in Section <a href="#sec:gap" data-reference-type="ref" data-reference="sec:gap">11</a> excludes the historical global strip-tree budget even after a local saddle model is corrected. The examples in Section <a href="#sec:exact-obstructions" data-reference-type="ref" data-reference="sec:exact-obstructions">7</a> show that the least critical modulus and a separation-two test do not cover all polynomials, and that initial merge arity does not control capacity after subsequent mergers. The all-degree critical-value inequality controls a marginal distribution; it does not identify compatible inverse branches. The ordinary note [blaschke power critical spectra](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/BlaschkePowerCriticalSpectra.md) records Blaschke-power polynomials $`F_N=A^N-D^N`$ that realise the sharp critical-value moment numerator $`4s`$ inside the polynomial class, including a high-critical nonseparated regime with exact rational certificates. The same family has ordinary short connectors of length $`O(1/N)`$ and an exact degree-dependent degeneration of $`\Lambda`$. These statements are not parent proofs, are not Lean-checked as analytic theorems, and do not replace the trinomial flagship.

The remaining parent regime has $`\mu>13/25`$ and lies outside the solved families and the applicable separation conditions. Further progress requires a contained pair selected with its geometric cost, a quantitative attachment estimate, or a different competitor for $`\Lambda`$. The failed scalar implications and their exact witnesses are preserved in the long record.

<a id="sec:evidence-ledger"></a>

# Proof boundaries

The trinomial radial inequalities and length budget, the two-root proximity selector, the exact spoke counterexamples, and the specified finite kernels are checked in Lean at their linked source revisions. Their geometric assemblies are identified separately in the corresponding proofs.

The $`13/25`$ theorem is ordinary analysis with an exact rational certificate. The $`71/10`$ theorem, the analytic inverse-map construction, the all-degree Poisson argument, and the generic slit-sheet construction are ordinary proofs. The finite coefficient identity and the polar circle comparison have checked kernels; neither substitutes for Poisson integration or the maximum principle. The complete declaration-to-claim map is retained in the long record and the formal-source guide below.

Fixed-degree lower semicontinuity reduces the closed class to a dense generic metric bound. The admissible canonical-arc length estimate remains open. Raster searches supply candidate paths for finite samples; their meaning is separate from the exact rational certificates used in proved inequalities. No independent human review or resolution of the general problem is claimed.

<a id="sec:1041-sources"></a>

## Sources and adjacent results

The original root-to-root problem is \[ehp1958, p. 139, Problem 5\]. Pendyala’s degree-four theorem \[june2026, Thm. 1\] is directly comparable. His separate Erdős Problem #1120 \[pendyala2026shortest\] asks for a path from the origin to the unit circle inside a filled sublevel set; its endpoints differ, and it does not imply the root-pair conclusion. The exact Cassini obstruction in Section <a href="#sec:gap" data-reference-type="ref" data-reference="sec:gap">11</a> concerns the metric assertion of \[march2026, Prop. 12\]. Eremenko and Hayman prove the global boundary estimate $`\operatorname{length}\{z:|p(z)|=1\}<9.173\deg p`$ and show that an extremal level set is connected \[eremenko-hayman, Thm. 1 and the lemma on connectedness\]. Their metric is the total length of a level curve, so this does not supply the short internal root-to-root connector asked for here. Downloaded-source digests, precise locators, and withdrawal history are retained in the long record. No uniqueness or priority claim is inferred from this comparison.

<a id="app:sources"></a>

# Guide to the formal sources

The public `ErdosProblems.Erdos1041.NewtonFlowRaySeparation` module contains the checked source for this note. The search of §<a href="#sec:finite" data-reference-type="ref" data-reference="sec:finite">12</a> is `scripts/search_counterexample.py` in the source package. The declaration table below is pinned to the shared formal-source commit used throughout this problem-note series.

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L34)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L38)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L50)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L64)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L77)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L80)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L84)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L92)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L107)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L127)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L130)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L147)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L152)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L162)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L179)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L197)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L230)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L257)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L287)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L306)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L315)

<div class="thebibliography">

10 T. F. Bloom, *Erdős Problems*, problem 1041. <https://www.erdosproblems.com/1041> P. Erdős, F. Herzog, and G. Piranian, *Metric properties of polynomials*, J. Analyse Math. **6** (1958), 125–148. <https://doi.org/10.1007/BF02790232> `shtuka`, *A Short Path Joining Two Zeros Inside a Polynomial Lemniscate*, manuscript posted 24 March 2026, 48 pp. <https://shtuka123.github.io/1041/main.pdf> V. S. Pendyala, *A Degree-Four Lemniscate Path Theorem*, arXiv:2606.24875v1 (2026). <https://arxiv.org/abs/2606.24875>, doi:[10.48550/arXiv.2606.24875](https://doi.org/10.48550/arXiv.2606.24875). V. S. Pendyala, *Shortest paths in polynomial lemniscate sublevel sets and a problem of Erdős*, arXiv:2606.19178v1 (2026), Erdős Problem #1120, Theorem 1.2 and introductory discussion, pp. 2–3. <https://arxiv.org/abs/2606.19178>, doi:[10.48550/arXiv.2606.19178](https://doi.org/10.48550/arXiv.2606.19178). A. Eremenko and W. Hayman, *On the length of lemniscates*, Michigan Math. J. **46** (1999), 409–415. <https://arxiv.org/abs/0805.2295>. V. N. Dubinin, *Some inequalities for polynomials and rational functions associated with a lemniscate*, Zap. Nauchn. Sem. POMI **404** (2012), 83–99; English translation, J. Math. Sci. **193** (2013), no. 1, 45–54, doi:[10.1007/s10958-013-1432-4](https://doi.org/10.1007/s10958-013-1432-4). This neighbouring covering theorem is discussed in the long record; the area input used here is the absolute Pólya inequality \[polya1928\]. G. Pólya, *Beitrag zur Verallgemeinerung des Verzerrungssatzes auf mehrfach zusammenhängende Gebiete*, Sitzungsberichte der Preussischen Akademie der Wissenschaften, Physikalisch-Mathematische Klasse (1928), printed pp. 228–232 and 280–282. <https://archive.org/details/sitzungsbericht1928preu>.

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
