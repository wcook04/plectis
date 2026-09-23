<a id="erdos-1041-lemniscate-newton-flow"></a>

# Paths in Polynomial Lemniscates: Trinomials and Critical-Value Bounds

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

A degree-seven counterexample due to the erdosproblems.com contributor [`ani`](https://www.erdosproblems.com/forum/thread/1041#post-8861), formalised in Lean here, refutes the universal total-variation formulation: every continuous path inside the strict unit lemniscate joining two distinct roots has total variation greater than $`2`$. Its correspondence with the historical curve-length question has not received independent human review. For a monic trinomial $`f(z)=z^n+az^m+b`$, $`1\le m<n`$, with roots in the open unit disc, the root equation controls $`f`$ on every root-to-origin segment. Any two distinct roots are consequently joined inside $`\{|f|<1\}`$ by an explicit two-segment path of length less than $`2`$. Abel summation explains the role of the missing coefficients, and a sextic example shows why root locations alone do not control these segments. We compare this construction with an area-growth criterion: a squarefree monic polynomial has a contained path of length less than $`2`$ when its least critical-value modulus is at most $`13/25`$, without a root-location hypothesis. Its scale-free consequence and proof outline complete the main note. Independent estimates and limitations of other constructions are collected in the supplementary sections.

<a id="sec:trinomial"></a>

# Monic trinomials, in every degree

The root equation will eliminate the middle coefficient and control the polynomial on an entire segment, not just at its endpoints.

<div id="res:trinomial-all-degree" class="theorem">

**Theorem 1** (all-degree monic trinomials). *Let $`1\le m<n`$ and
``` math
f(z)=z^n+az^m+b,
```
with every zero in the open unit disc. For any zero $`\zeta`$, the entire segment $`[0,\zeta]`$ lies in $`\{|f|<1\}`$. Distinct zeros $`\zeta_1,\zeta_2`$ are therefore joined by the broken line $`\zeta_1\to0\to\zeta_2`$ of length $`\|\zeta_1\|+\|\zeta_2\|<2`$ inside the open unit lemniscate.*

</div>

Lean: [all degree monic trinomials whole](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperTrinomialWholeR21.lean#L23).

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

<a id="abel-summation-along-a-segment."></a>

#### Abel summation along a segment.

The same argument can be stated using partial sums. This explains both why trinomials work and what extra information a polynomial with more terms would require. For $`f(z)=\sum_{k=0}^n a_kz^k`$ and $`f(\zeta)=0`$, put $`S_j=\sum_{k=0}^j a_k\zeta^k`$. Abel summation gives
``` math
f(t\zeta)=\sum_{j=0}^{n-1}(t^j-t^{j+1})S_j.
```
For $`0\le t<1`$, the normalised value $`f(t\zeta)/(1-t^n)`$ lies in the convex hull of $`S_0,\ldots,S_{n-1}`$. A bound for each partial sum therefore gives a bound at every point of the segment. For a trinomial every partial sum equals either $`b`$ or $`-\zeta^n`$, both strictly inside the unit disc. This is a condition on the missing coefficients, not just on the root locations. For example, $`z^n-b`$ with $`0<|b|<1`$ is covered, whereas a general polynomial with four nonzero coefficients is not. The next example shows why the additional partial sums cannot simply be ignored.

<div id="res:sextic-spoke" class="proposition">

**Proposition 2** (failure of a prescribed radial segment). *There exist $`r\in(0,1)`$ for which every zero of
``` math
f_r(z)=z^6+\tfrac15 r^2 z^4-\tfrac15 r^4 z^2-r^6
```
lies in the open unit disc, yet the radial spoke from the origin to the zero $`r`$ leaves $`\{|f_r|<1\}`$.*

</div>

Lean: [sextic spoke counterexample whole](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/SexticSpokeWhole.lean#L9).

Indeed, after $`z=rw`$, the polynomial factors as $`r^6(w^2-1)(w^4+\tfrac65 w^2+1)`$, so all six roots have modulus $`r`$. However $`f_r(r/2)=-(327/320)r^6`$. Any $`r`$ with $`320/327<r^6<1`$ proves the assertion. This calculation rules out the segment $`[0,r]`$, not paths through a different root or a different joining point. The corresponding radial evaluation is checked in [the sextic evaluation](https://github.com/wcook04/plectis-erdos/blob/0ba585f632fbbbb43af2ee9532d4e83752af3f67/ErdosProblems/Erdos1041/AbelControlPolygon.lean#L555). The factorisation above explains the root locations.

<a id="sec:problem"></a>

# The historical question and the path estimates

<div id="res:problem" class="problem">

**Problem 3** (Erdős \#1041). Let $`f(z)=\prod_{i=1}^{n}(z-z_i)`$ be monic with $`n\ge2`$ and all $`z_i`$ in the open unit disc. Must two root occurrences be joined by a curve of length less than $`2`$ inside $`\{|f|<1\}`$?

</div>

Repeated roots give a constant path between two listed occurrences, so the geometric question concerns squarefree polynomials. The original question is Problem 5 of Erdős–Herzog–Piranian \[ehp1958, Problem 5, p. 139\], listed as Problem 1041 in Bloom’s catalogue \[bloom\]. Pendyala \[june2026, Theorem 1 and Lemma 1, pp. 1–3\] proves the complete degree-four case by a close-pair chord or two radial segments through the centre of a smallest enclosing disc. That centre need not be a critical point. The results here concern specified polynomial families and sufficient conditions; no priority claim is made.

<span id="res:ani-degree-seven-counterexample" label="res:ani-degree-seven-counterexample"></span> A degree-seven counterexample due to the [erdosproblems.com contributor `ani`](https://www.erdosproblems.com/forum/thread/1041#post-8861) makes the unrestricted total-variation assertion false. For one explicit monic polynomial of degree seven whose roots are distinct and lie in the open unit disc, every continuous path in the strict unit lemniscate joining two distinct roots has total variation greater than $`2`$.[^1] Thus this polynomial has no continuous root-to-root parametrisation of total variation less than $`2`$.

The trinomial proof prescribes a path for every pair of distinct roots. The area-growth argument in Section <a href="#sec:constant-factor" data-reference-type="ref" data-reference="sec:constant-factor">3</a> has a different conclusion: it selects some pair of roots, but requires no coefficient pattern or root-location hypothesis. The next section gives this criterion and its scaling consequence. The [supplementary sections](#supplementary-results) retain the other estimates and the obstructions to prescribed constructions; none is an input to the trinomial proof.

<a id="sec:constant-factor"></a>

# Low critical values and a uniform path bound

For $`t\ge0`$, the set $`\{|f|\le t\}`$ grows from the roots as $`t`$ increases. For a squarefree polynomial, the first merger of two root components occurs at the smallest modulus of a critical value. We use the notation
``` math
K_t=\{z:|f(z)|\le t\},\qquad
 \mu=\min_{f'(c)=0}|f(c)|,\qquad \rho=\mu^{1/n}.
```
Here $`\mu>0`$ for a squarefree polynomial. A positive level $`t`$ is regular when no critical value has modulus $`t`$. The quantity $`\rho`$ scales like a distance: for $`s>0`$, replacing $`f(z)`$ by $`s^{-n}f(sz)`$ divides $`\rho`$ by $`s`$.

<div id="res:low-critical-thirteen-twentyfifths" class="theorem">

**Theorem 4** (a small critical value). *Let $`f`$ be squarefree and monic of degree $`n\ge2`$, and let $`\mu`$ be its least critical-value modulus. If $`\mu\le13/25`$, then two distinct roots are joined inside $`\{|f|<1\}`$ by a rectifiable curve of length strictly less than $`2`$.*

</div>

Not formalised: the degree-two case and the exact rational arithmetic of the stopping-time comparison are checked, and the analytic argument in higher degrees is not. See the [coverage section of the companion record](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=coverage).

The condition $`\mu\le13/25`$ is sufficient, not necessary. For $`f(z)=z^n-b`$ with $`0<|b|<1`$, one has $`\mu=|b|`$, so this criterion covers $`|b|\le13/25`$ and excludes $`13/25<|b|<1`$, even though the trinomial argument gives the required path throughout that family. Unlike that argument, the present criterion imposes no coefficient pattern and no root-location assumption. For example, $`(z-3)^n-1/2`$ has $`\mu=1/2`$ for every $`n\ge2`$, yet all its roots satisfy $`|z|>2`$. The conclusion concerns $`|f(z)|<1`$, not containment in $`|z|<1`$.

<div id="res:scaled-low-critical" class="corollary">

**Corollary 5** (scale-free connection). *Every squarefree monic polynomial of degree $`n\ge2`$ has two distinct roots joined in $`\{|f|<(25/13)\mu\}`$ by a curve of length less than
``` math
2\bigl((25/13)\mu\bigr)^{1/n}.
```
In every degree the length can be chosen less than $`(5/2)\mu^{1/n}`$.*

</div>

Lean: [scaled low critical of low critical](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/LowCriticalScaleTransport.lean#L460), [scaled low critical five halves of low critical](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/LowCriticalScaleTransport.lean#L491). Conditional on Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a> as stated; see the [coverage section of the companion record](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=coverage).

<div class="proof">

*Proof.* Put $`s=((25/13)\mu)^{1/n}`$ and $`g(z)=s^{-n}f(sz)`$. Then $`g`$ is monic and its least critical-value modulus is $`13/25`$. Apply the theorem and scale the curve back by $`s`$. For $`n\ge3`$, $`(25/13)^{1/n}\le(25/13)^{1/3}<5/4`$. For $`n=2`$, the segment between the roots has length $`2\sqrt\mu`$ and lies in $`K_\mu`$. ◻

</div>

<a id="proof-outline-for-the-1325-criterion."></a>

#### Proof outline for the $`13/25`$ criterion.

The contradiction has two steps. Failure of a short path forces roots to be separated in a conformal disc. Packing then forces enough roots in a component to make its area grow faster than Pólya’s inequality allows. [Section 3 of the companion record](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=section.3) gives the complete analytic estimates and the rational comparison; we describe their dependence here.

Suppose no curve of length less than $`2`$ joins two roots below level $`1`$. For a regular level $`\mu<t<1`$, let $`C_t`$ be the component of the open set $`\{|f|<t\}`$ containing a pair that first joins at level $`\mu`$, and put $`a=\operatorname{Area}(C_t)/\pi`$. An inverse-map length estimate turns the failure assumption into pairwise hyperbolic separation of the roots in a Riemann disc. We use the normalisation $`d_{\mathrm{hyp}}(0,s)=2\operatorname{artanh}s`$. The map can be centred at a point $`h`$ on the two inverse arcs to the merging critical point whose intrinsic distance from every root is at least $`1`$. Otherwise the disjoint intrinsic open balls of radius $`1`$ about the roots would cover a connected set containing two roots. Here intrinsic distance means the infimum of lengths of curves in $`C_t`$. In particular $`|f(h)|\le\mu`$.

If $`d_1,\ldots,d_k`$ are the hyperbolic distances of the mapped roots from the origin, the Blaschke product identity gives
``` math
\sum_{j=1}^k-\log\tanh(d_j/2)
 =\log\frac{t}{|f(h)|}\ge x,\qquad x=\log(t/\mu).
```
Pairwise separation gives disjoint hyperbolic balls about the mapped roots. On each circle centred at the origin, their intersections occupy a total angle at most $`2\pi`$. Combining these simultaneous angular constraints with the displayed sum gives a lower bound for $`k`$. The [supplementary packing calculation](#circle-packing-inputs) states the finite inequality and explains why it must be certified at every permitted radial distance, not just on a sampled grid.

A second averaging argument converts the root count into area growth. Lift a common value ray from each root to the boundary and join adjacent endpoints by boundary arcs. Under the failure assumption, each of the $`k`$ resulting paths has length at least $`2`$; their total length counts every lift twice and the boundary once. Coarea therefore gives a lower bound on area growth. The comparison combines the circle intersections with three other root-count bounds, derived in the companion, and exceeds $`\operatorname{Area}(C_t)\le\pi t^{2/n}`$ before $`t=1`$. The circle-intersection bound alone does not yield the stated cutoff.

The rational comparison reaches this contradiction when $`\mu\le13/25`$. Its recorded stopping time also supports $`\mu\le529/1000`$; the [supplement](#certificate-stopping-time) gives that calculation. The certificate has not been rerun for this revision, and no optimality of either cutoff is asserted.

<div id="supplementary-results">

</div>

<a id="supplementary-results"></a>

# Supplementary results

The main note ends with the preceding criterion and its scale-free corollary. The remaining results can be read independently of the trinomial argument. They distinguish control of a chosen component, control of critical values, and control of a prescribed curve. The companion record supplies the full area, separation and Poisson calculations at the locations specified below. The theorem numbering continues from the main note.

<a id="the-finite-packing-input."></a>

#### The finite packing input.

<div id="circle-packing-inputs">

</div>

This supplies the inequality used in the preceding proof outline, with $`a`$, $`x`$ and $`d_j`$ as defined there. It is part of the area-growth proof; the later supplementary constructions are independent of that proof.

To retain both angular and radial information, take disjoint open balls about those roots, each of radius half the guaranteed pairwise separation. Intersect them with a hyperbolic circle of radius $`r>0`$ centred at the origin. Their angular measures add to at most $`2\pi`$. If $`w(d,r)`$ denotes the half-angle of such an intersection, then $`\sum_j w(d_j,r)\le\pi`$. Thus any nonnegative weights $`\sigma_i`$ and uniform majorant
``` math
-\log\tanh(d/2)\le U+\sum_i\sigma_iw(d,r_i),\qquad U>0,
```
valid for every $`d\ge2\operatorname{artanh}\sqrt{1-e^{-1/a}}`$, give
``` math
k\ge\frac{x-\pi\sum_i\sigma_i}{U}.
```
The [recorded finite-sum lemma](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/PaperFiniteDual.lean#L68) assumes the packing bound and boundedness; it records this last implication, not the preceding hyperbolic geometry. Projecting whole balls onto the circle of directions would not suffice: projections of balls at different radii can overlap. Nor does checking the majorant at finitely many radial distances prove its uniform validity.

<a id="the-recorded-stopping-time."></a>

#### The recorded stopping time.

<div id="certificate-stopping-time">

</div>

The [complete area-growth argument and rational certificate](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/AngularBudgetLowCriticalClosure.md) records a terminal time $`X=635762889599/10^{12}`$. The differential inequality supplies its starting area bound; no positive starting area is assumed. The contradiction applies whenever $`\mu e^X<1`$. The companion’s rational exponential estimate gives
``` math
(529/1000)e^X<0.998996547<1,
```
so the same recorded output also covers $`\mu\le529/1000`$; $`13/25`$ is the simpler stated constant. The certificate has not been rerun for this revision, and no optimality of either cutoff is asserted.

<a id="an-independent-area-proof."></a>

#### An independent area proof.

The next theorem gives a weaker numerical bound through an argument that needs no circle-slice certificate. It makes the area allocation explicit.

<div id="res:constant-factor-path" class="theorem">

**Theorem 6** (a uniform path bound at level $`2\mu`$). *For every monic polynomial $`f`$ of degree $`n\ge2`$, two zero occurrences are joined by a possibly degenerate path of length at most
``` math
\frac{71}{10}\,\rho
```
inside $`K_{2\mu}`$. If $`f`$ is squarefree, their locations are distinct. If $`\mu\le1/2`$, the construction may be chosen inside $`\{|f|<1\}`$ with length at most $`5.7`$.*

</div>

Lean: [cfa constant factor path](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L677), [cfa bracket two three twentieths lt](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L355), [cfa bracket five point seven](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L393), [cfa degenerate](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L313), and 3 further declarations. Conditional on the level and direction averaging construction that this proof produces; see the [coverage section of the companion record](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=coverage).

The constant is the rationally certified specialization of a two-parameter bound. If the selected component contains $`k\ge2`$ roots, then for every $`r\in(0,1)`$ and $`\lambda>1`$ the proof constructs a path in $`K_{\lambda\mu}`$ whose length is at most
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

*Proof using the area estimates in the companion, Section 4.* A repeated root gives a constant path, and degree two gives the root segment of length $`2\rho`$ in $`K_\mu`$. Assume $`n\ge3`$ and $`f`$ squarefree. Put $`T=\lambda\mu`$. Coarea, Cauchy–Schwarz and Pólya’s inequality \[crane, Theorem 1\] select a regular level $`\mu<t<T`$ in the component containing a first merger. Let $`k\ge2`$ be its root count. Lift a common value ray from its roots to the boundary, splitting each lift at modulus $`r\mu`$. The estimates proved in the companion are
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
The low estimate holds in every direction by Koebe distortion; the high estimate holds in a direction selected from its mean. The boundary estimate uses the level already chosen. In cyclic order, the $`k`$ adjacent-root paths count each lift twice and the boundary once. One complete path is therefore no longer than their average, which gives (CF). Choosing only a short boundary arc would not control its two lifts. For $`\mu\le1/2`$, substitution of $`r=3/20`$ and $`\lambda=2`$ gives
``` math
\operatorname{length}\le
 \frac{60\sqrt2}{289}+\sqrt{\log(40/3)}
 +\frac{\pi}{\sqrt{\log2}}<5.7.
```
The selected level satisfies $`t<2\mu\le1`$, so containment is open even at $`\mu=1/2`$. ◻

</div>

Refinements using the number of roots, logarithmic capacity, or a range of levels during which a component still has two roots are given in [the detailed area argument](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/UnconditionalConstantFactorBound.md) and [the two-root component argument](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/MinimalHubWindowJoin.md). Their length-$`2`$ conclusions under $`\mu\le1/2`$ already follow from Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a>; their additional content is control of a specified component or a specified descent arc. A simple critical point need not be the unique point at the least critical level. The two-root component argument keeps these assumptions separate, since another merger can occur at the same level.

<a id="sec:critical-proximity"></a>

# Critical proximity and straight-path obstructions

A critical point gives a different way to select two nearby roots, without assuming a sparse coefficient pattern. The logarithmic-derivative balance prevents one root from being arbitrarily closer to the critical point than all the others. This yields a bound on the sum of two distances. To turn that bound into a path theorem, both connecting segments would also have to stay inside the lemniscate; the examples below show why that extra step cannot be assumed.

<div id="res:critical-proximity" class="theorem">

**Theorem 7** (a geometric-mean bound for distances to a critical point). *Let $`n\ge2`$, let $`z_1,\ldots,z_n,c\in\mathbb C`$ with $`c\ne z_k`$ for every $`k`$, and suppose
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

Lean: [exists two roots dist sum le two mul geom mean](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/CriticalTwoRootProximity.lean#L291).

The proof chooses the two smallest distances $`d_i\le d_j`$. The reciprocal balance gives $`d_j\le(n-1)d_i`$, while minimality and the geometric-mean identity give $`d_i d_j^{\,n-1}\le r^n`$. To use the reciprocal identity, set $`t=d_j/d_i`$: it restricts $`t`$ to $`[1,n-1]`$, where
``` math
1+t\le2t^{(n-1)/n}.
```
Indeed, $`\log(2t^{(n-1)/n}/(1+t))`$ vanishes at $`t=1`$ and has derivative $`(n-1-t)/(nt(1+t))\ge0`$ on that interval. Consequently $`d_i+d_j\le2(d_i d_j^{\,n-1})^{1/n}\le2r`$. Without the reciprocal balance, the required restriction on $`t`$ would be missing. The complete complex theorem, including the choice of two indices and both inequalities, is checked as [the bound for the sum of two root distances](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/CriticalTwoRootProximity.lean#L289).

<div class="corollary">

**Corollary 8** (two nearest roots). *If the roots lie in the open unit disc and $`c`$ is a non-root critical point, the two nearest roots to $`c`$ have total distance strictly below $`2`$.*

</div>

Lean: [two nearest roots of polynomial critical](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/TwoNearestPolynomial.lean#L9), [exists two nearest roots of polynomial critical](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/TwoNearestPolynomial.lean#L31).

<div class="proof">

*Proof.* For roots in the closed unit disc, rotate so that $`c=t\ge0`$ and order $`0<d_1\le\cdots\le d_n`$. The root-disc inequalities and $`\sum_j(z_j-c)^{-1}=0`$ give
``` math
n\le(1-t^2)\sum_jd_j^{-2},\qquad
 d_1\le1,\qquad d_2\le(n-1)d_1.
```
If $`d_1+d_2>2`$, the additional bound $`d_2\le1+t`$ gives $`1-t^2<d_1d_2`$, and therefore
``` math
n<d_2/d_1+(n-1)d_1/d_2\le n.
```
The last inequality follows from $`(x-1)(x-(n-1))\le0`$ for $`x=d_2/d_1\in[1,n-1]`$. Scaling by a containing radius $`0<R<1`$ gives the strict bound $`2R<2`$. The [companion’s full distance argument](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=two-nearest-root-distance) derives the two displayed estimates without assuming $`|f(c)|\le1`$. The source is [the proof for the two nearest roots](https://github.com/wcook04/plectis-erdos/blob/a729f05c40398663fd586c9da487ad874d898639/research_corpus/Erdos1041/GlobalCriticalTwoNearestBudget.md); Lean now checks the [strict distance bound from the critical polynomial](https://github.com/wcook04/plectis-erdos/blob/52d6c45ad203ba619cb5fe6ba485c0b5400519ea/lean/ErdosProblems/Erdos1041/PaperCompleteR20/TwoNearestPolynomial.lean#L31), including the root-disc reduction and the choice of the two nearest indices. ◻

</div>

The distance estimate alone does not prove containment of either segment. The next proposition gives counterexamples to both natural straight-line constructions.

<div id="res:straight-no-go" class="proposition">

**Proposition 9** (two counterexamples to straight-path assertions). *There is a monic quintic with all roots in the open unit disc and a non-root critical point $`c`$ whose unique nearest root has a point on the straight spoke to $`c`$ outside $`\{|f|<1\}`$. There is also a monic cubic with all roots in the open unit disc such that the midpoint of every pair of distinct roots lies outside $`\{|f|<1\}`$.*

</div>

Lean: [complete straight path obstructions](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperStraightObstructions.lean#L178).

<div class="proof">

*Proof.* For the quintic, put $`p=999/1000`$ and $`a=(901/902)p`$, and take
``` math
Q(z)=(z-a)(z^2+p^2)
       \left(z^2+\frac{902}{901}pz+p^2\right).
```
Its roots are
``` math
a,\quad ip,\quad-ip,\quad
 p\frac{-451+780i}{901},\quad p\frac{-451-780i}{901}.
```
Since $`451^2+780^2=901^2`$, the last four roots have modulus $`p<1`$, while $`0<a<p`$. Also $`Q'(0)=0`$ and $`Q(0)=-ap^4\ne0`$. Thus $`a`$ is the uniquely nearest root to the non-root critical point $`0`$. At one tenth of that segment, exact rational arithmetic gives
``` math
|Q(a/10)|=
 \frac{9a}{10}\left(\frac{a^2}{100}+p^2\right)
 \left(\frac{a^2}{100}+\frac{11p^2}{10}\right)>1.
```
For the cubic, take $`g(z)=z^3-(99/100)^3`$. If $`z,w`$ are distinct roots, then $`z+w`$ is the negative of the third root, so
``` math
g\!\left(\frac{z+w}{2}\right)
 =-\frac98\left(\frac{99}{100}\right)^3,
 \qquad \frac98\left(\frac{99}{100}\right)^3
 =\frac{8732691}{8000000}>1.
```
All three roots have modulus $`99/100`$. ◻

</div>

Uniqueness in the quintic rules out repairing that example by breaking a tie differently. The cubic excludes every direct root-to-root segment, not a curved path. The two exact evaluations are checked as [escape along the segment to a uniquely nearest root](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/CriticalTwoRootProximity.lean#L438) and [escape at all three root-pair midpoints](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/CriticalTwoRootProximity.lean#L569). [The complete straight-path statement](https://github.com/wcook04/plectis-erdos/blob/0b500c7cf8e8bb7ae343484378df02f277fb8194/lean/ErdosProblems/Erdos1041/PaperStraightObstructions.lean#L178) also includes the polynomial, root-disc, critical-point and unique-nearest-root assertions, rather than only the two evaluations.

<a id="sec:solved-families"></a>

# Solved polynomial families

The following families allow containment to be proved along the whole path. Their assumptions are structural: rotational symmetry, two missing quintic coefficients, or collinearity. In each case the proof must do more than find nearby roots: it must bound the polynomial at every point of the chosen segments.

<a id="a-cubic-composed-with-a-power-map"></a>

## A cubic composed with a power map

The expression $`P((z-h)^q)`$ forces the roots to occur in regular $`q`$-point sets about $`h`$. This exact symmetry is the useful hypothesis; a generic perturbation of the coefficients destroys it. The point $`h`$ need not be the origin. Averaging over a complete set of rotated roots will show why the hypothesis on the roots of $`f`$ also controls the roots of the cubic $`P`$.

<div id="res:cubic-fibres" class="theorem">

**Theorem 10** (a cubic composed with a power map). *Let $`q\ge2`$, $`h\in\mathbb C`$, and let $`P`$ be a monic cubic. Put
``` math
f(z)=P((z-h)^q).
```
If all zeros of $`f`$ lie in the open unit disc and $`f`$ has at least two distinct zeros, then two distinct zeros of $`f`$ are joined by a two-segment path of length strictly less than $`2`$ contained in $`\{|f|<1\}`$.*

</div>

Lean: [complete translated cubic quotient fibres](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCubicFibres.lean#L240).

<div class="proof">

*Proof.* First check that the roots of $`P`$ lie in the open unit disc. Let $`r`$ be a root of $`P`$, choose $`y`$ with $`y^q=r`$, and put $`\omega=e^{2\pi i/q}`$. All $`q`$ points $`h+y\omega^k`$ are roots of $`f`$. Since $`q\ge2`$, their squared moduli satisfy
``` math
\frac1q\sum_{k=0}^{q-1}|h+y\omega^k|^2=|h|^2+|y|^2<1.
```
Thus $`|r|=|y|^q<1`$, as required for the cubic argument.

Write $`P(w)=(w-r)(w-s)(w-v)`$. The three numbers $`\Re(r\overline{s+v})`$, $`\Re(s\overline{r+v})`$ and $`\Re(v\overline{r+s})`$ sum to $`|r+s+v|^2-|r|^2-|s|^2-|v|^2>-3`$. At least one, say the first, exceeds $`-1`$. For $`0\le t\le1`$,
``` math
\frac{|tr-s|^2+|tr-v|^2}{2}
 =t^2|r|^2+\frac{|s|^2+|v|^2}{2}
   -t\Re(r\overline{s+v})<1+t+t^2.
```
AM–GM therefore gives $`|tr-s|\,|tr-v|<1+t+t^2`$. Together with $`|tr-r|=(1-t)|r|`$, this proves $`|P(tr)|<1`$ for $`0\le t<1`$; at $`t=1`$ the value is zero. Lean checks [the cubic segment inequality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/CubicQuotientFiberCase.lean#L161).

A nonzero root $`r`$ with this property gives two distinct roots $`h+y`$ and $`h+y\omega`$ of $`f`$. Their segments to $`h`$ are contained because $`f(h+ty\omega^k)=P(t^qr)`$, and their total length is $`2|y|<2`$. If the selected cubic root is zero, choose a nonzero one, say $`s`$. Then $`P(w)=w(w-s)(w-v)`$ and $`|P(ts)|<2t(1-t)\le1/2`$ for $`0<t<1`$, with zero endpoint values. A nonzero cubic root exists because $`f`$ has at least two distinct zeros. This proves the theorem in all cases. ◻

</div>

The root-of-unity identity, nonzero-root choice and construction of the rectifiable path are formalised in [the complete translated cubic fibre theorem](https://github.com/wcook04/plectis-erdos/blob/27c2fc5fe3c55fe547feaeb4c9bb68b3cf63a5bf/lean/ErdosProblems/Erdos1041/PaperCubicFibres.lean#L240). The corresponding source files occur in the compiled dependency closure recorded by [the build and axiom-audit record](https://github.com/wcook04/plectis-erdos/blob/27c2fc5fe3c55fe547feaeb4c9bb68b3cf63a5bf/verification/erdos1041-returned-r18-v5-full-audit-evidence.json).

<a id="quintics-with-two-missing-coefficients"></a>

## Quintics with two missing coefficients

The coefficients of $`z^3`$ and $`z^2`$ must vanish in the coordinates used below. There is no separate smallness condition on the three remaining coefficients, but a general quintic is not covered. The two missing coefficients give the moment identities used to select two roots.

<div id="res:primitive-quintic" class="theorem">

**Theorem 11** (quintics with two missing coefficients). *Let
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

Lean: [complete primitive quintic](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperPrimitiveCompletionR10.lean#L237).

The selection argument first allows roots on the closed disc, where the two bounds may be non-strict. If $`a\ne0`$, both selected bounds are strict. If $`a=0`$, the root equation gives $`|bw+c|=|w|^5`$ at each root $`w`$, so every root in the open disc gives a strict bound. The missing coefficients give the first three Newton identities. A cubic polynomial in the real parts of the roots combines these identities to rule out four failures of $`|bw+c|<1`$. For roots off the unit circle, its harmonic extension gives the same conclusion: a root with $`|bw+c|\ge1`$ contributes at most $`2/31`$ to that comparison. The full comparison polynomial and its inequalities are displayed in the long record. Once a root $`w`$ satisfies $`|bw+c|<1`$, its whole segment is controlled by the identity
``` math
p(tw)=(1-t)c+(t-t^4)(bw+c)-t^4(1-t)w^5.
```
For $`0\le t<1`$, the three nonnegative weights sum to $`1-t^5`$. Vieta’s formula gives $`|c|<1`$, and $`|w|<1`$, so every term being averaged has modulus below one. The value at $`t=1`$ is zero. Two selected segments have total length $`|w_i|+|w_j|<2`$; coincident occurrences instead give the constant path. Lean checks [the selection for roots on the unit circle](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/PrimitiveQuinticBoundaryTail.lean#L200) and [the selection for roots in the closed disc](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/PrimitiveQuinticInteriorTail.lean#L272). The source snapshot also contains [the complete sparse-quintic path theorem](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperPrimitiveCompletionR10.lean#L235). The recorded build includes this complete open-disc path theorem, not just the two selection inequalities. It does not by itself verify every equality clause of the closed-disc statement in the long paper.

<a id="bdry:solved-polynomial-families"></a>

## Sharp collinear roots

The complete all-degree collinear theorem appears in Section <a href="#sec:collinear" data-reference-type="ref" data-reference="sec:collinear">14</a>. It gives the sharp maximum modulus on a suitable root segment, as well as a bound on that segment’s length. Collinearity supplies a real ordering that is absent for a general complex root configuration. Lean checks [the comparison of alternating values](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/SharpCollinearAlternation.lean#L158) and [the resulting Chebyshev bound](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/SharpCollinearChebyshev.lean#L133); affine normalisation, root-gap selection, and transport back to the original line are ordinary.

<a id="sec:separation"></a>

# Critical-value separation in every degree

Instead of restricting coefficients or root positions, we isolate one simple critical value $`v=f(c)`$. A disc containing $`[0,1]`$ and no other normalised critical value $`f(d)/v`$ permits the two inverse branches meeting at $`c`$ to be followed to roots.

<div id="res:critical-value-separation" class="theorem">

**Theorem 12** (separation of one simple critical value). *Let $`f`$ be monic of degree $`n\ge3`$, let $`c`$ be a simple critical point, and put $`v=f(c)\ne0`$. Fix $`w_0\in[0,1]`$ and $`S>\max(w_0,1-w_0)`$. Suppose every other critical point $`d`$ satisfies
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

Lean: [disc sep separation short](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L534), [disc sep normalise spec](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L410), [disc sep transport](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L475), [disc sep squared length le](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L305), and 1 further declaration. Conditional on the connector and area construction that this proof produces; see the [coverage section of the companion record](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=coverage).

This isolation can be checked directly in familiar examples. For $`f(z)=z^3-3a^2z`$ with $`0<a<1/\sqrt3`$, choose $`c=a`$, so $`v=-2a^3`$. The other normalised critical value is $`-1`$, at distance $`2`$ from the centre $`w_0=1`$, so $`S=4/3`$ is allowed. The roots $`0,\pm\sqrt3a`$ lie in the open unit disc. The hypothesis excludes a multiple selected critical point and can fail when two distinct critical values are close together. Thus it is not a consequence of the root-disc assumption.

<div id="res:critical-value-thresholds" class="corollary">

**Corollary 13** (uniform radius $`4/3`$). *Let $`f`$ be monic of degree $`n\ge3`$ with all roots in the open unit disc. If $`c`$ is a simple critical point with $`0<|f(c)|<1`$ and, for some $`w_0\in[0,1]`$, every other critical point $`d`$ satisfies
``` math
\left|\frac{f(d)}{f(c)}-w_0\right|\ge\frac43,
```
then two roots are joined inside $`\{|f|<1\}`$ by a curve of length strictly below $`2`$. In degree three the branch-centred choice $`w_0=1`$ already works with $`4/3`$ replaced by $`6/5`$.*

</div>

Lean: [disc sep uniform radius](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L702), [disc sep cubic six fifths](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L738), [disc sep coefficient lt two](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L645), [disc sep coefficient three six fifths](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L677). Conditional on the connector and area construction in the proof of Theorem <a href="#res:critical-value-separation" data-reference-type="ref" data-reference="res:critical-value-separation">12</a>; see the [coverage section of the companion record](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=coverage).

<div id="res:separation-parent" class="corollary">

**Corollary 14** (a sufficient condition for a length-$`2`$ path). *Let $`f`$ be monic of degree $`n\ge3`$ with all roots in the open unit disc, and let $`c`$ be a simple critical point with $`v=f(c)`$ and $`0<|v|<1`$. If some real centre $`w_0\in[0,1]`$ admits a radius $`S\ge4/3`$ such that $`|f(d)/v-w_0|\ge S`$ for every other critical point $`d`$, then Erdős Problem #1041 holds for $`f`$.*

</div>

Lean: [separation parent](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/SeparationParent.lean#L162), [separation coefficient lt two](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/SeparationParent.lean#L98), [squared bound lt four](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/SeparationParent.lean#L123), [connected below of connected at most](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/SeparationParent.lean#L144). Conditional on Theorem <a href="#res:critical-value-separation" data-reference-type="ref" data-reference="res:critical-value-separation">12</a> as stated; see the [coverage section of the companion record](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=coverage).

The hypothesis $`|v|<1`$ is required: normalised separation controls a connector in $`\{|f|\le|v|\}`$, which lies in the unit lemniscate only when $`|v|<1`$. The critical-value mean in Section <a href="#sec:freepoint" data-reference-type="ref" data-reference="sec:freepoint">15</a> gives $`|v|<1`$ when $`v`$ has minimum modulus and the roots lie in the open unit disc. An arbitrary selected critical value need not satisfy this bound. The hypothesis is sufficient, not necessary: it does not assert that some critical value always admits such a disk. The cubic $`z^3+(3/100)z-3/4`$ shows in particular that the older separation-two condition does not cover all polynomials.

<div class="proof">

*Proof of the separation estimate.* Normalise by $`P(w)=f(c+|v|^{1/n}w)/v`$. Then $`P(0)=1`$, its leading coefficient has modulus one, and $`0`$ is a simple critical point. The component $`U`$ of $`P^{-1}(D(w_0,S))`$ containing $`0`$ has just that one simple ramification point. At regular inner radii $`1-w_0<S'<S`$, the component count in the proof of \[eks2010, Proposition 2.1\] gives degree two; exhaustion gives the same degree on $`U`$ even if its outer level is critical. Taking a square root of $`1-P`$ resolves the branching and identifies $`U`$ with $`\{\xi:|\xi^2-(1-w_0)|<S\}`$. Its inverse sends $`[-1,1]`$ to a path between the two distinct points over $`P=0`$.

The explicit disc map in [Section 6 of the companion](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=section.6) takes that interval to $`[-q,q]`$, where
``` math
q^2=\frac{S}{S^2+p}<1,
 \qquad S^2-S+p=(S-w_0)(S-(1-w_0))>0.
```
This is where the lower bound on $`S`$ enters the length estimate. The Bergman segment inequality proved there gives
``` math
\operatorname{length}^2
 \le\frac2\pi\log\frac{1+q^2}{1-q^2}\operatorname{Area}(U)
```
in the normalised coordinates. It uses the disc kernel $`\pi^{-1}(1-z\overline w)^{-2}`$; the companion evaluates its double integral on $`[-q,q]^2`$.

The area estimate must concern this two-sheeted component, not merely the whole preimage. For $`1-w_0<S'<S`$, its regular inner components $`U'`$ contain two zeros of $`P-w_0`$. The estimate proved in [Theorem 2 and Corollary 3 of the component-capacity proof](https://github.com/wcook04/plectis-erdos/blob/8efbccc235df64a38d83f5dc7b1949e2ad18270d/research_corpus/Erdos1041/problem/ExteriorBlaschkeFibreCapacityGap.md) gives $`\operatorname{cap}(\overline{U'})^n/S'<1/(n-1)`$. Pólya’s area–capacity inequality \[polya1928, printed pp. 280–282\], in the form \[crane, Theorem 6\], and exhaustion as $`S'\uparrow S`$ then give $`\operatorname{Area}(U)\le\pi(S/(n-1))^{2/n}`$. Substitute this bound and restore the length scale $`|v|^{1/n}`$ to obtain <a href="#eq:disk-family-length" data-reference-type="eqref" data-reference="eq:disk-family-length">[eq:disk-family-length]</a>. The companion proves both the component-capacity estimate and the exhaustion step. Dubinin’s relative area inequality \[dubinin, Theorem 1\] has an additional full-covering hypothesis and is not used in place of this absolute area estimate. ◻

</div>

For the uniform corollary, any separation radius $`S\ge4/3`$ may first be replaced by $`4/3`$: shrinking the disc preserves the exclusion of other critical values. For $`4/3\le S\le2`$ and $`p\ge0`$,
``` math
\frac{S^2+S+p}{S^2-S+p}\le\frac{S+1}{S-1}\le7,
 \qquad \frac{S}{n-1}\le1,
```
and $`\log7<2`$. Thus <a href="#eq:disk-family-length" data-reference-type="eqref" data-reference="eq:disk-family-length">[eq:disk-family-length]</a> is strictly below $`4|v|^{2/n}<4`$ under the corollary’s hypotheses. The cubic constant follows from $`(3/5)^{2/3}\log11<2`$.

<a id="bdry:critical-value-separation"></a>

#### Formalisation.

The analytic proof above is ordinary mathematics. Its pinned source is the [proof of the critical-value separation theorem](https://github.com/wcook04/plectis-erdos/blob/8efbccc235df64a38d83f5dc7b1949e2ad18270d/research_corpus/Erdos1041/problem/DiskFamilyCriticalValueSeparation.md). The separate [formal numerical inequalities](https://github.com/wcook04/plectis-erdos/blob/f36e325c8b05fe5c3ce8a2ca32a699f6dc6336b9/ErdosProblems/Erdos1041/DiskFamilyCriticalValueSeparation.lean) check the coefficient bound for $`n\ge3`$, $`4/3\le S\le2`$, the cubic $`S=6/5`$ inequality, and the implication from the squared bound to length below $`2`$. These checks do not formalise the analytic hypotheses producing <a href="#eq:disk-family-length" data-reference-type="eqref" data-reference="eq:disk-family-length">[eq:disk-family-length]</a>; the adjacent axiom-audit source audits those numerical declarations rather than the ordinary analytic theorem. Only the chosen critical point must be simple; other critical points may be multiple and their values may cluster outside the isolating disc. Existence of such an isolated value is not asserted.

Pendyala’s degree-four theorem \[june2026, Thm. 1\] has no critical-value separation hypothesis. The present separation criterion applies in every degree $`n\ge3`$ and supplies an explicit inverse-map length estimate.

<a id="sec:exact-obstructions"></a>

# Three limits of the sufficient conditions

These examples do not refute the root-to-root assertion. They show why particular sufficient conditions cannot be assumed for every polynomial. The rational calculations are given in [the formal calculations](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/RevisionR2ExactCores.lean); the ordinary arguments are in [the accompanying proofs](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/ExactObstructionsR2.md).

<div id="res:sep-or-false" class="proposition">

**Proposition 15** (failure of two critical-value criteria to cover all polynomials). *Let $`f(z)=z^3+(3/100)z-3/4`$. Every root lies in the open unit disc, both critical points are simple, the critical values lie on distinct positive rays, $`\mu>13/25`$, and
``` math
\bigl|1-f(c_-)/f(c_+)\bigr|<2/375<2.
```*

</div>

Lean: [complete sep or counterexample](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperSeparationCounterexample.lean#L189).

The whole proposition, including the least-modulus assertion rather than a supplied minimum, is checked in Lean as [the complete separation counterexample](https://github.com/wcook04/plectis-erdos/blob/0b500c7cf8e8bb7ae343484378df02f277fb8194/lean/ErdosProblems/Erdos1041/PaperSeparationCounterexample.lean#L189); this is a cubic example, distinct from the quartic example discussed in the long record.

<div id="res:one-root-gamma-false" class="proposition">

**Proposition 16** (a counterexample to the proposed one-root perimeter bound). *Let $`p(z)=z^8-(3/2)z`$ and let $`C`$ be the component of $`\{|p|\le1\}`$ containing the origin. Then $`C`$ contains exactly one zero and a neighbourhood of the closed disc of radius $`5/8`$, so $`\mathcal H^1(\partial C)>5\pi/4`$. The constant $`\Gamma(1/4)^2/(2\sqrt{\pi})`$ is at most $`(\pi/2)(1+\sqrt2)<5\pi/4`$.*

</div>

Lean: [one root gamma false unconditional](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/LobeUnconditional.lean#L41).

This example also lies below every critical-value modulus: its critical points satisfy $`c^7=3/16`$ and $`p(c)=-(21/16)c`$, so $`\mu^7=3\cdot21^7/16^8>1`$. Thus the level $`1`$ is globally subcritical.

The addendum \[revision2026, Proposition 2\] reports a Runge construction of monic level-one components with one zero and arbitrarily long analytic boundaries, without a root-disc restriction; its proof was unavailable. The displayed example refutes the Gamma constant, not every uniform bound. Suppose one constant $`\beta`$ works for all squarefree monic $`f`$ of degree $`n\ge2`$, bounding every inverse branch $`f(\phi(w))=\sigma w`$ by $`\int_0^{2\pi}|\phi'(e^{it})|\,dt\le\beta\sigma^{1/n}`$ at each $`0<\sigma<\mu(f)`$, where all branches are unramified. The [companion’s geometric proof](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=perimeter-to-path) then joins two distinct roots in $`K_\mu`$ with length at most $`\beta\mu^{1/n}`$, using half of each of two component perimeters. Existence of such a $`\beta`$ is not proved here. Necessarily $`\beta\ge2\pi`$, by $`z^N-az`$ with fixed $`a>1`$ and $`N\to\infty`$, then $`a\downarrow1`$; $`z^N-z`$ at level $`1`$ does not give an isolated component. Neither general path theorem uses the rejected arbitrary-component bound.

The next example concerns successive mergers of sublevel components; the roots themselves do not move. A component containing two roots just after the first merger can acquire a third root before level $`2\mu`$. Consider the component at that later level containing the first pair. For this monic cubic, its normalised capacity is its logarithmic capacity divided by $`(2\mu)^{1/3}`$. The whole filled lemniscate has capacity $`(2\mu)^{1/3}`$, so a normalised value of $`1`$ gives no improvement over the whole set.

<div id="res:arity-not-capacity" class="proposition">

**Proposition 17** (root count does not force a capacity gap). *Let $`g(z)=z^3-(3/400)z-3/32`$. All roots lie in the open unit disc and $`\mu=187/2000\le1/2`$. The first merger joins two root components, so $`k_0=2`$, but the component at level $`2\mu`$ containing that pair has normalised capacity $`1`$.*

</div>

Not formalised: the pinned library has no logarithmic capacity of a compact plane set and no notion of the level at which two sublevel components merge, so neither remaining clause can yet be stated. See the [coverage section of the companion record](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=coverage).

<a id="sec:newton"></a>

# The Newton value equation

The Newton equation is
``` math
z'(t)=-\frac{f(z(t))}{f'(z(t))}.
```
It is defined only while the curve avoids critical points. Its usefulness here is that applying $`f`$ turns it into a scalar equation, even though the curve in the $`z`$-plane need not be straight. Kozen and Stefánsson record the following identity as a lemma of Shub, Tischler and Williams \[kozen-stefansson1997, Lemma 2.1\].

<div id="res:value" class="theorem">

**Theorem 18** (value equation). *For a polynomial $`f`$ and a differentiable curve $`z:I\to\mathbb C`$ on an interval $`I`$, assume $`f'(z(t))\ne0`$ and $`z'(t)=-f(z(t))/f'(z(t))`$ throughout $`I`$. Then $`w=f\circ z`$ satisfies $`w'=-w`$, and
``` math
f(z(t))=e^{-(t-t_0)}f(z(t_0))\qquad(t,t_0\in I).
```*

</div>

Lean: [newton real value whole](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/NewtonRealTime.lean#L52).

The local computation is one line: $`w'=f'(z)z'=-f(z)=-w`$. Multiplication by $`e^t`$ and integration on $`I`$ give the displayed identity. Lean checks the local complex-parameter chain rule as [the Newton-flow value equation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L50) and its scaled zero-derivative form as [vanishing of the exponentially scaled value](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L64). The integrated real-time assertion above is an ordinary consequence.

For an existing trajectory with nonzero initial value, the value moves inward on one positive ray. A zero value remains zero and has no argument. Thus a trajectory starting in $`\{|f|<1\}`$ stays there at later times in its interval of existence. The equation neither constructs a global trajectory nor identifies a whole ray preimage with one flow line.

The time parameter matters when comparing this equation with gradient-flow theory. On $`\{f\ne0\}`$, the Euclidean gradient of $`u=-\log|f|`$ is $`\nabla u=-\overline{f'/f}`$. Where $`f'\ne0`$, it is the positive multiple $`|f'/f|^2(-f/f')`$ of the Newton field, so their nonstationary trajectories have the same orientation. At a simple critical point with nonzero value, the gradient extends smoothly as a hyperbolic saddle, whereas $`-f/f'`$ is undefined. The exponential value equation uses Newton time; it is not unchanged by this reparametrisation.

<div id="res:ray" class="corollary">

**Corollary 19** (ray separation). *Let $`a<b`$, let $`z:[a,b]\to\mathbb C`$ be continuous, and suppose $`z`$ is differentiable on $`(a,b)`$ with $`f'(z(t))\ne0`$ and $`z'(t)=-f(z(t))/f'(z(t))`$ there. Then
``` math
f(z(b))=e^{a-b}f(z(a)).
```
If the endpoint values are nonzero, they lie on the same positive ray. In particular, critical points whose values lie on distinct positive rays cannot be the endpoints of such a finite connection.*

</div>

Lean: [newton real endpoint whole](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/NewtonRealTime.lean#L69).

Apply the value equation inside $`(a,b)`$ and pass to the endpoints by continuity. This does not evaluate $`-f/f'`$ at a critical endpoint. Lean checks the algebraic contradiction from an assumed exponential endpoint relation in [the distinct-ray endpoint implication](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L315). Kozen and Stefánsson draw the same consequence for the Newtonian graph: under $`f`$, every edge maps onto a segment of a ray through the origin whose endpoints are $`0`$ or critical values \[kozen-stefansson1997, §2\]. The endpoint behaviour of nonstationary maximal trajectories is classified there as well \[kozen-stefansson1997, Lemma 2.2\].

The Newtonian graph should not be confused with the quotient by whole trajectories. For $`f(z)=z^2-1/4`$, the smooth-gradient flow on $`\{\log2\le-\log|f|\le\log8\}`$ has a real separatrix whose closure contains the saddle $`0`$ as a different, stationary orbit. Its orbit class is not closed, so the orbit quotient is not Hausdorff, despite there being only one simple saddle and no saddle-to-saddle connection. A Hausdorff parameter space for cut strips must refer to the actual cut-open surface and its specified boundary identifications.

<a id="sec:arguments"></a>

# Arguments, not moduli

Two different nonzero numbers need not have different arguments: $`1`$ and $`2`$ have different moduli but lie on the same positive ray. By Corollary <a href="#res:ray" data-reference-type="ref" data-reference="res:ray">19</a>, different arguments of the endpoint values rule out a finite Newton connection. Distinct moduli, or merely distinct values, do not provide this obstruction.

For a polynomial whose critical values are already distinct, adding a constant translates all those values while leaving the critical points unchanged. The next formula identifies the translations to avoid. Its assumption $`a\ne b`$ matters: a common translation can never separate two initially equal values.

<div id="res:locus" class="theorem">

**Theorem 20** (ray-collision locus). *Let $`a\ne b`$ be complex. Every common translation $`\beta`$ for which $`a+\beta`$ and $`b+\beta`$ lie on the same positive ray has the form
``` math
\beta=\frac{ra-b}{1-r},
  \qquad r\in\mathbb{R}_{>0},\ r\ne1 .
```*

</div>

Lean: [translated same positive ray parameterization](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L107).

Indeed, write $`b+\beta=r(a+\beta)`$ with $`r>0`$. Since $`a\ne b`$, one has $`r\ne1`$, and solving for $`\beta`$ gives the displayed formula. Equivalently, $`\beta=-a+(a-b)/(1-r)`$, so the forbidden translations lie on the real affine line through $`-a`$ and $`-b`$.

Each pair of critical values contributes such a forbidden subset, as checked in [the ray-collision parameterization](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L107). These loci lie on finitely many real lines. Excluding those lines and the finitely many translations that make a value zero still leaves a point in every open disc. Accordingly, [an arbitrarily small translation separates the arguments](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L197). Under an explicit margin, [a small constant perturbation keeps the roots in the unit disc](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L287). For a constant shift there is also an elementary sharper estimate: if $`f(z)=\prod_{j=1}^n(z-a_j)`$ has degree $`n\ge1`$ and $`(f+\beta)(z)=0`$, then $`\prod_j|z-a_j|=|\beta|`$, so $`\min_j|z-a_j|\le|\beta|^{1/n}`$. Thus $`\max_j|a_j|+|\beta|^{1/n}<1`$ suffices for root retention. This estimate does not assert a matching of labelled roots or control of a selected path. If a closed-level length bound holds on a dense class of polynomials, the fixed-degree lower semicontinuity in Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">17</a> extends that bound to its closure. Quantitative forward transport of a selected curve requires additional control, but is not a premise of that existence argument.

The distinct-value premise can be arranged first by a small linear perturbation: its local critical-value branches satisfy $`v_j'(\lambda)=c_j(\lambda)`$, so coincidences are isolated when the critical points are simple. Item 4 in Section 13 of the companion proves this qualitative statement, the subsequent choice of translation and root retention by Rouché’s theorem. It does not give quantitative control of a protected region or of the cost of transferring a selected path.

<a id="sec:reciprocal"></a>

# Local polynomial expansions

For $`f(z)=\prod_j(z-a_j)`$ with $`a_j\ne0`$, put $`r=\min_j|a_j|`$ and $`p_m=\sum_j a_j^{-m}`$. On $`|z|<r`$, the exact expansion
``` math
\log|f(z)|=\log|f(0)|-\Re\sum_{m\ge1}\frac{p_m}{m}z^m
```
expresses the local level geometry through the reciprocal power sums. If $`q=|z|/r<1`$, the tail after $`N`$ has modulus at most $`nq^{N+1}/((N+1)(1-q))`$; differentiated geometric series give the corresponding first and second derivative bounds. The linked derivation gives recurrences for these reciprocal power sums and tests based on the first two derivatives for a locally contained piecewise path: [the reciprocal-root expansion](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/ReciprocalNewtonExpansion.md). The assumption $`|z|<r`$ is essential: this disc contains no zero of $`f`$, so a logarithm exists there. The expansion does not continue through a root and does not select a pair of roots to join. A proposed local path must still satisfy the containment inequalities.

<a id="sec:gap"></a>

# Why the proposed spanning-tree estimate fails

The March manuscript’s Proposition 12 claims the following estimate. For $`u=-\log|f|`$, a connected component $`V`$ of $`\{u>c\}`$ carrying $`m\ge2`$ simple zeros, and the regularity and Morse hypotheses in that proposition, it constructs, for every $`\varepsilon>0`$, an embedded spanning tree $`G_\varepsilon\subset V`$ with
``` math
\operatorname{len}(G_\varepsilon)
 \le\frac1{2\pi}\int_{2\alpha}^{\infty}P_V(t)\,dt+\varepsilon.
\tag{5.1}\label{eq:prop12-bound}
```
Here $`P_V(t)=\mathcal H^1(V\cap\{u=t\})`$ is the length of the level set in $`V`$, and $`\alpha>0`$ is the truncation parameter in the proposed estimate. The final theorem depends on this bound. An unattributed local revision repeats the same estimate as Proposition 7; that repetition supplies no independent proof.

The estimate itself is false. Take the Cassini polynomial $`f_a(z)=z^2-a^2`$ at $`a=9/10`$, with $`2\alpha=-\log a`$ and $`0<c<\alpha/2`$. Its component contains the two roots at distance $`9/5`$ and has a single nondegenerate saddle. Parametrising the level curves by $`z=\pm\sqrt{a^2+re^{i\theta}}`$, where $`r=e^{-t}`$, and bounding the angular integral gives the upper majorant
``` math
4\bigl(\sqrt{a^2+a}-a\bigr)<\frac{41}{25}
```
for the right side of <a href="#eq:prop12-bound" data-reference-type="eqref" data-reference="eq:prop12-bound">[eq:prop12-bound]</a> before $`\varepsilon`$, whereas every connected set containing both roots has length at least $`9/5`$. Since $`9/5-41/25=4/25`$, choosing a smaller positive $`\varepsilon`$ contradicts the assertion. Thus neither a different local saddle neighbourhood nor a perfect topological decomposition can recover the printed coefficient $`1/(2\pi)`$. Lean checks the exact finite inequality and the contradiction it gives for the proposed tree-length bound. The level-length majorant remains an ordinary analytic calculation, not a kernel-checked integral evaluation. The long record gives the parametrisation, angular bound and radial integral explicitly. The source namespace is recorded in Appendix <a href="#app:sources" data-reference-type="ref" data-reference="app:sources">19</a>.

At an interior index-one critical point $`p`$, the proof invokes a Morse chart
``` math
u=u(p)+x^2-y^2
```
and replaces the saddle by a three-ended neighbourhood having one connected lower cross-section and two connected upper cross-sections. That local model is false as written. Because $`p\in V`$ and $`V`$ is open, a sufficiently small closed disc around $`p`$ lies entirely in $`V`$. In that disc the full Morse chart has four sectors: two components of $`u>u(p)`$ and two components of $`u<u(p)`$. The level set $`\{u=u(p)\}`$ is a lemniscate graph with a vertex of degree four at $`p`$ \[bishop-eremenko-lazebnik, Definition 1.2 and Proposition 2.4\]. A global component argument cannot delete one local sector from a disc already contained in $`V`$.

This independently diagnoses a proof step, but the Cassini witness above also refutes the proposition’s statement. A different route might cut an adjoining regular annulus along a separatrix or regular flow arc before forming the block, retain a four-pronged saddle neighbourhood and change the assembly, or replace the local construction by the ray-cut decomposition proposed below. But no repair can retain <a href="#eq:prop12-bound" data-reference-type="eqref" data-reference="eq:prop12-bound">[eq:prop12-bound]</a>; it must pay a positive attachment cost, select only one short pair instead of spanning every root, or use a different global metric inequality. The shorter descriptions of the same three-ended block do not repair the four-sector topology.

Within a component, distinct critical-value arguments exclude finite Newton connections between its saddles by Corollary <a href="#res:ray" data-reference-type="ref" data-reference="res:ray">19</a>. The [companion’s inverse-sheet theorem](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=inverse-sheet-component) supplies the corresponding component-wise construction. Its topology does not provide the missing length estimate or quantitative gluing.

<a id="sec:finite"></a>

# Computational searches

The reported grid searches found candidate paths for sampled root configurations through degree ten. They supply no degree-wise upper bound. A raster path becomes a continuous certificate only after every connecting segment and its length have been enclosed. The sample counts, grid distances, and search parameters are retained in the long record. Useful diagnostics for further searches are clustered critical values, shrinking attachment windows, component mergers, and distance to the unit level.

<a id="sec:binomial"></a>

# Two chord constructions for binomials

The trinomial theorem already gives a path through the origin for a binomial. The following construction asks a more precise question: when does the chord between adjacent roots stay inside, and how can it be replaced when it does not? Let $`f(z)=z^n-a`$, where $`n\ge2`$ and $`0<|a|<1`$. After rotation write $`a=r^n>0`$, put $`\omega=e^{2\pi i/n}`$ and $`c=\cos(\pi/n)`$, and set
``` math
r_*=(1+c^n)^{-1/n},\qquad
 \varepsilon=(1-r^n)^{1/n}.
```

<div class="theorem">

**Theorem 21** (complementary binomial chords). *Two adjacent zeros of $`z^n-a`$ can be joined by an explicit polygonal path inside $`\{|z^n-a|<1\}`$ of length strictly below $`2`$. For $`r<r_*`$ the adjacent-root chord itself works. For $`r\ge r_*`$, two radial legs and an inner adjacent crossing chord work after an arbitrarily small radial contraction. These two constructions meet at $`r=r_*`$, where the outer chord attains $`|f|=1`$ at its midpoint and therefore lies only in the closed lemniscate. Open containment at and above the switch uses the inner chord after a radial contraction.*

</div>

Lean: [binomial chords path](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/BinomialChords.lean#L1084), [binomial chords below threshold](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/BinomialChords.lean#L1094), [binomial chords above threshold](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/BinomialChords.lean#L1104), [binomial chords at threshold](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/BinomialChords.lean#L1118), and 3 further declarations in the [coverage section of the companion record](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=coverage).

The central chord calculation is exact. On the chord between adjacent roots,
``` math
\max |z^n-r^n|=r^n(1+c^n),
```
with the maximum at the midpoint; hence the first construction has precisely the threshold $`r_*`$. For $`r\ge r_*`$, which forces $`n\ge3`$ because $`r_*=1`$ when $`n=2`$, put $`t=\varepsilon/c`$. The path from $`r`$ to $`t`$ to $`t\omega`$ to $`r\omega`$ has its crossing chord in the closed lemniscate, and its length is
``` math
2r-2\varepsilon\tan\!\left(\frac\pi4-\frac\pi{2n}\right)<2r<2.
```
The radius $`t`$ is maximal: a larger crossing chord already escapes at its midpoint. Contracting that chord to radius $`\lambda t`$ with $`0<\lambda<1`$ makes the containment strict while keeping the two radial connections and the strict length bound. For $`n=2`$, the adjacent-root diameter is already a strict path of length $`2r<2`$.

The [companion’s binomial chord calculation](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=binomial-chord-calculation) proves, for every $`0<s\le r`$,
``` math
\max_{z\in[s,s\omega]}|z^n-r^n|=r^n+(sc)^n.
```
Its decisive step is $`1+\cos(n\theta)\le2\cos^n\theta`$ on $`|\theta|\le\pi/n`$, obtained from concavity of $`\log\cos`$. This one estimate gives the outer threshold, the inner crossing and strict containment after contraction.

The outer chord has length $`2r\sin(\pi/n)\le2r<2`$. This ordinary argument distinguishes two prescribed polygonal constructions; it is not a shortest-path result, a new Lean theorem or a claim of priority. Its hypotheses concern binomials, not the unrestricted historical question.

<a id="sec:collinear"></a>

# The sharp Chebyshev bound for collinear roots

When all roots lie on one line, consecutive roots have an unambiguous order. Alternation against a Chebyshev polynomial then bounds the largest value on one of the intervening segments. The result covers every real-rooted polynomial after rotation and translation, but excludes any root set containing three noncollinear points. Put
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

Lean: [sharp collinear root diameter](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L367), [sharp collinear root diameter monic](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L967), [exists collinear factorisation](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L928), [exists gap le comparison bound](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L212), and 5 further declarations in the [coverage section of the companion record](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=coverage).

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
It vanishes at $`\pm1`$ and has $`|q_*|\le C_n`$ on $`[-1,1]`$. Choose a point $`c_i`$ of maximum $`|q|`$ in each adjacent gap. Each maximum is attained in the interior, since $`q`$ vanishes at the endpoints and not in the gap. Its signs at the $`n-1`$ chosen points alternate because the roots are simple. If every gap maximum exceeded $`C_n`$, then $`h=q-q_*`$ would have those same nonzero signs at the $`c_i`$. The intermediate value theorem would give $`n-2`$ distinct zeros between consecutive chosen points, in addition to the zeros at $`-1`$ and $`1`$. This is impossible for the nonzero polynomial $`h`$, whose leading terms cancel and whose degree is at most $`n-1`$. Thus one selected gap has $`|q|\le C_n`$ throughout, and scaling back proves the bound.

For sharpness take the roots of $`q_*`$, namely
``` math
\frac{\cos((2k-1)\pi/(2n))}{r_n},\qquad 1\le k\le n.
```
Their extreme roots are $`\pm1`$, and every adjacent gap reaches $`C_n`$ at a Chebyshev extremum. ◻

</div>

Erdős, Herzog and Piranian already give a contained root segment in the collinear case \[ehp1958, Theorem 1, p. 126\]: if the zeros of a monic polynomial of degree $`n`$ are real, lie in $`[-1,1]`$ and have centroid in $`[0,1]`$, then $`\{|f|<1\}\cap\mathbb R`$ contains an interval holding at least $`n/2`$ of the zeros. Apply it to $`q`$, replacing $`q(w)`$ by $`(-1)^nq(-w)`$ if the centroid is negative; the factor preserves monicity. For $`n\ge3`$ this gives two consecutive zeros joined by a segment of length at most $`D`$ inside $`\{|f|<(D/2)^n\}`$. Theorem <a href="#res:sharp-collinear-root-diameter" data-reference-type="ref" data-reference="res:sharp-collinear-root-diameter">22</a> adds the sharp level $`C_n(D/2)^n`$ and its equality configurations.

The chosen gap maxima are the moduli of the ordered critical sequence $`(q(c_1),\ldots,q(c_{n-1}))`$, with $`c_1<\cdots<c_{n-1}`$. That sequence determines a real-rooted polynomial up to an increasing affine change \[eremenko-yuditskii, Theorem 1\]; the proof here needs only alternation. The comparison $`q_*`$ is the monic minimax polynomial on $`[-1/r_n,1/r_n]`$ \[eremenko-yuditskii, §1\], and all its critical values have modulus $`C_n`$.

The [companion’s collinear discussion](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=collinear-source-comparison) gives the full comparison with critical points on an extremal level curve \[eremenko-hayman, Lemma 5\] and with the derivative bound on connected lemniscates \[eremenko-lempert, Theorem 1\], including its equality family \[eremenko-markov, Theorem A\]. Those theorems optimise boundary length or derivative size, not the internal root-to-root path considered here.

If $`D<2`$, the displayed level is below one and this segment lies in the open lemniscate. For $`n\ge3`$, the same strict level holds already at $`D=2`$; degree two is the exact boundary case. Lean checks the alternation count and the Chebyshev comparison; the change of variables and its application to the polynomial remain ordinary steps. Bounded computational tests do not replace those steps. The result does not say that every adjacent gap lies in the lemniscate, and the proof gives no noncollinear analogue: its sign changes depend on the order of the real roots.

<a id="sec:freepoint"></a>

# A Poisson identity for critical-value means

We first prove an inequality for arbitrary points of the closed disc, then compare it with polynomial critical values. For one point it reads $`(1-|c|^2)^2\le1`$. Mixed factors can exceed one, as the pair $`r,-r`$ shows through $`|1-(-r)r|=1+r^2`$, so a factorwise bound will not suffice. The proof instead uses each $`c_j`$ both in $`1-\overline{c_j}z`$ and as a Poisson-kernel centre; the logarithmic derivative connects the two uses.

The points may repeat or lie on the boundary. Positive weights are needed for the stated equality case: allowing zero weights would constrain only points of positive weight. Signed weights are not covered by the Poisson argument. The quadratic identity also yields a fourth-power refinement, explained after the proof.

<div id="res:fp-weighted-all-degree" class="theorem">

**Theorem 23** (a weighted inequality for points in a disc). *Let $`c_1,\ldots,c_m\in\overline{\mathbb D}`$ and let $`w_j>0`$ satisfy $`\sum_j w_j=1`$. Set
``` math
G(z)=\prod_k |1-\overline{c_k}z|^{w_k}.
```
Then
``` math
\sum_j w_j G(c_j)^2\le 1,
```
with equality if and only if every $`c_j=0`$. Equal weights therefore give $`\sum_j(\prod_k|1-\overline{c_k}c_j|)^{1/m}\le m`$ for every $`m`$.*

</div>

Lean: [paper weighted free point](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperWeightedRefinementsR10.lean#L17), [geometric row mean closed disc le](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperWeightedRefinementsR10.lean#L155).

<div class="proof">

*Proof.* For interior points, choose analytic logarithms zero at the origin and put
``` math
g(z)=\exp\sum_jw_j\log(1-\overline{c_j}z)
     =1+\sum_{\nu\ge1}a_\nu z^\nu.
```
Then $`|g|=G`$. On the unit circle, with normalised arclength $`dm`$, the weighted Poisson kernel is
``` math
P=\sum_jw_j\frac{1-|c_j|^2}{|\zeta-c_j|^2}
   =1-2\Re\frac{\zeta g'}g.
```
Poisson majorisation of $`|g|^2`$ at the $`c_j`$, followed by orthogonality of circle powers, gives
``` math
\sum_jw_jG(c_j)^2\le\int |g|^2P\,dm
 =1-\sum_{\nu\ge1}(2\nu-1)|a_\nu|^2\le1.
```
For boundary points, replace $`c_j`$ by $`rc_j`$. The coefficient of degree $`\nu`$ becomes $`r^\nu a_\nu`$. Retain any finite nonnegative coefficient sum and let $`r\uparrow1`$; continuity gives the same bound at the boundary. Equality forces all $`a_\nu=0`$, so $`\sum_jw_j\overline{c_j}/(1-\overline{c_j}z)=0`$ near zero. Grouping repeated points, any nonzero point gives a pole of nonzero positive total weight, a contradiction. All points zero give equality. Finally apply Cauchy–Schwarz and take equal weights for the linear consequence. The companion’s [weighted Poisson proof](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=weighted-poisson-proof) gives the termwise integration and boundary passage, including zero weights. ◻

</div>

The coefficient $`a_1=-\overline{\sum_jw_jc_j}`$ gives the immediate refinement
``` math
\sum_jw_jG(c_j)^2\le1-\left|\sum_jw_jc_j\right|^2.
```
Thus the proof records a quantitative loss when the weighted centroid is nonzero. The long record also explains the four-point consequence and a separate proof for points in a smaller concentric disc. Theorem <a href="#res:fp-weighted-all-degree" data-reference-type="ref" data-reference="res:fp-weighted-all-degree">23</a> does not need either restriction.

<a id="the-fourth-power-refinement."></a>

#### The fourth-power refinement.

The quadratic exponent is not the limit of this Poisson argument. In the same notation, put $`H=g^2=1+\sum_{\nu\ge1}b_\nu z^\nu`$. This choice makes $`|H|^2=G^4`$, while the kernel identity becomes $`P=1-\Re(\zeta H'/H)`$. For interior points the preceding calculation gives
``` math
\sum_jw_jG(c_j)^4
 \le\int |H|^2P\,dm
 =1-\sum_{\nu\ge1}(\nu-1)|b_\nu|^2\le1.
```
All coefficient weights are nonnegative, including the zero weight at $`\nu=1`$. The same radial contraction, applied first to finite coefficient sums, proves the inequality for closed-disc points. This is the $`p=4`$ case of the ordinary [power-parameter Poisson identity](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/SharpPowerDiscProducts.md). The long record proves its extension under vanishing complex power sums and handles equality at this endpoint. Unlike the quadratic theorem, this analytic refinement is not part of the cited complete Lean result.

<a id="relation-to-classical-critical-value-products."></a>

#### Relation to classical critical-value products.

For a monic polynomial with all zeros in the unit disc, Dubinin \[dubinin2006critical, Theorem 2 and its proof, pp. 1172–1173\] proves the sharp geometric-mean inequality $`\bigl(\prod_{j=1}^{n-1}|f(c_j)|\bigr)^{1/(n-1)}\le1`$. The proof uses the resultant identity (9), the maximum-modulus principle and Schur’s unit-circle Vandermonde inequality, not the dissymmetrisation argument of his Theorem 1. The positive-moment inequality below implies that product bound by AM–GM. For a list with at least two entries, a product bound alone does not control a positive moment; in degree two there is only one critical value, so the two bounds are equivalent. This comparison identifies an antecedent, not a priority claim for the stronger moment statement.

<div id="res:fp-to-s" class="theorem">

**Theorem 24** (critical-value mean in every degree). *Let $`f`$ be monic of degree $`n\ge2`$, with roots in a closed disc of radius $`R`$, and let $`c_1,\ldots,c_{n-1}`$ be its critical points with multiplicity. Then
``` math
\sum_{j=1}^{n-1}|f(c_j)|^{2/(n-1)}
 \le(n-1)R^{2n/(n-1)}.
```
In particular, $`\sum_j|f(c_j)|^{1/n}\le(n-1)R`$ in every degree.*

</div>

Lean: [paper critical value mean](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCriticalValueMeanR10.lean#L101).

<div class="proof">

*Proof.* For $`R>0`$, translate and scale to the unit disc; $`R=0`$ is immediate. Write $`q=f'/n=\prod_j(z-c_j)`$ and $`q^\#(z)=\prod_j(1-\overline{c_j}z)`$. The numerator $`f-zq=(nf-zf')/n`$ agrees with $`f`$ at critical points and is the polar derivative at zero divided by $`n`$. For roots strictly inside the disc,
``` math
\Re\frac{\zeta f'(\zeta)}{f(\zeta)}>\frac n2
 \quad(|\zeta|=1)
 \quad\Longrightarrow\quad
 |f(\zeta)-\zeta q(\zeta)|<|q(\zeta)|=|q^\#(\zeta)|.
```
Gauss–Lucas makes $`q^\#`$ nonvanishing on the closed disc. The maximum-modulus principle applied to $`(f-zq)/q^\#`$ therefore gives
``` math
|f(c_j)|\le\prod_k|1-\overline{c_k}c_j|.
```
The equal-weight quadratic inequality proves the claim. Radial contraction treats closed-disc roots; power means give the lower exponent; scaling restores $`R`$. The reflected-derivative lemma in Section 8 of the companion supplies the displayed modulus comparison and the contraction argument explicitly. ◻

</div>

The same pointwise comparison transfers the fourth-power Poisson bound. With $`m=n-1`$ and equal weights, on the unit disc
``` math
\frac1m\sum_j|f(c_j)|^{4/m}
 \le\frac1m\sum_jG(c_j)^4\le1.
```
Consequently, for the same hypotheses as Theorem <a href="#res:fp-to-s" data-reference-type="ref" data-reference="res:fp-to-s">24</a>,
``` math
\sum_j|f(c_j)|^{4/(n-1)}\le(n-1)R^{4n/(n-1)}.
```
For $`R>0`$, this follows by applying the unit-disc estimate to $`R^{-n}f(h+Rz)`$, where $`h`$ is the containing-disc centre; for $`R=0`$ all critical values are zero. The constant is attained by $`f(z)=(z-h)^n-\lambda`$ with $`|\lambda|=R^n`$. Theorem <a href="#res:fp-to-s" data-reference-type="ref" data-reference="res:fp-to-s">24</a> states the quadratic specialisation that is recorded in Lean; the displayed fourth-power consequence has the ordinary analytic proof just given.

If a zero is fixed at the disc centre, Dubinin’s Theorem 3 \[dubinin2006critical, p. 1174\] gives the sharper product estimate $`\bigl(\prod_j|f(c_j)|\bigr)^{1/(n-1)}
\le(n-1)(|f'(0)|^2/n^n)^{1/(n-1)}`$ in the unit-disc normalisation. Dubinin explicitly records the preceding contribution of Tischler \[tischler1989, p. 444, as discussed by Dubinin\]. Neither the product estimate nor its equality family settles the marked-zero positive-moment question in the research addendum \[revision2026\].

For a fixed containing disc $`\overline D(h,R)`$ with $`R>0`$, the equality cases in Theorem <a href="#res:fp-to-s" data-reference-type="ref" data-reference="res:fp-to-s">24</a> are exactly $`f(z)=(z-h)^n-\lambda`$ with $`|\lambda|=R^n`$. Indeed, after normalising this disc, equality in the critical-value bound forces equality in the equal-weight Poisson inequality. All critical points are then $`0`$, so $`f'=nz^{n-1}`$ and $`f=z^n-\lambda`$; equality forces $`|\lambda|=1`$. Scaling back gives the stated family. The same argument covers equality in the lower-exponent consequence, since equality in the chain of power-mean bounds forces equality in the quadratic bound. This equality classification is an ordinary consequence of the proof. The formal-source index records [the complete critical-value mean](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperCriticalValueMeanR10.lean#L101) and the complete weighted inequality in its recorded checked build. That critical-value endpoint has exponent $`2/(n-1)`$ and includes arbitrary centre, $`R=0`$, and critical points counted with multiplicity. It does not formally establish the exponent-$`4/(n-1)`$ refinement. Section <a href="#sec:evidence-ledger" data-reference-type="ref" data-reference="sec:evidence-ledger">18</a> distinguishes the recorded build evidence from a new verification. A bound on the critical values alone gives neither a curve nor a length estimate.

<a id="sec:orlicz"></a>

# A nonlinear integral for component mergers

Consider a component containing $`k`$ roots that later joins a larger component as the level of $`|f|`$ increases. If $`r\in(0,1]`$ is the ratio of these two merger scales, one logarithmic contribution assigned to each of its roots is $`k^{-1}\log(1/r)`$. An earlier length estimate instead involves the integral
``` math
I_k(r)=\int_r^1
 \frac{dq}{q\log\bigl((1+q^{2/k})/(1-q^{2/k})\bigr)}.
```
For nearby merger scales, $`r`$ is close to $`1`$. The integral is then much smaller than $`k^{-1}\log(1/r)`$. The following change of variables proves that no fixed positive multiple of this logarithmic contribution is a uniform lower bound.

<div id="res:orlicz-currency" class="theorem">

**Theorem 25** (the relation between two merger-scale integrals). *Define
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
In particular, no positive universal constant bounds $`I_k(r)`$ below by that constant times $`k^{-1}\log(1/r)`$.*

</div>

Lean: [orlicz currency](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/MergerScaleOrlicz.lean#L374), [orlicz kernel continuous](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/MergerScaleOrlicz.lean#L115), [orlicz kernel tendsto zero](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/MergerScaleOrlicz.lean#L163), [merger integral eq mul phi](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/MergerScaleOrlicz.lean#L278), and 4 further declarations in the [coverage section of the companion record](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=coverage).

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

As $`r`$ approaches $`1`$, two successive merger scales approach each other. The integral can then be arbitrarily small relative to the logarithmic contribution, even for fixed $`k`$. Any estimate along a chain of mergers must retain this nonlinear dependence. Related weighted Jensen estimates and a lemma selecting two roots with small total logarithmic contribution are given in [the proof and related integral inequalities](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/AttachmentAgeLifetimeOrlicz.md). Those inequalities do not by themselves construct pieces of a contained path that meet one another.

<a id="sec:open"></a>

# What a universal path estimate would require

Fix $`n\ge2`$, and let $`\mathcal K_n`$ be the compact coefficient class of monic degree-$`n`$ polynomials with roots in the closed unit disc. Define
``` math
\Lambda(f)=\inf_\gamma\operatorname{length}(\gamma),
```
where $`\gamma\subset\{|f|\le1\}`$ joins two different listed root occurrences. A repeated root permits a constant curve; an empty set of competitors has infimum $`+\infty`$.

<a id="passing-a-length-bound-to-a-limit."></a>

#### Passing a length bound to a limit.

The function $`\Lambda`$ is lower semicontinuous, and a finite infimum is attained. Indeed, near-minimising curves of bounded length can be parametrised on $`[0,1]`$ with a common Lipschitz bound. Arzelà–Ascoli, convergence of root multisets and lower semicontinuity of length give a contained limiting curve, even if the two endpoint occurrences coalesce. [The fixed-degree limits subsection of the companion](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=closed-class-limits) gives the full argument, also recorded in [the compactness proof](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/GenericSufficiencyClosure.md).

Thus a bound $`\Lambda\le2`$ on a dense class would extend to its closure. For an open-disc polynomial, rescaling a containing radius $`R<1`$ would give length at most $`2R<2`$ in $`\{|f|\le R^n\}\subset\{|f|<1\}`$. The binomial $`z^n-1`$ has $`\Lambda=2`$: its root sectors meet only at zero, and the radial paths attain this length. These facts explain the historical reduction; they do not prove the required dense-class bound. A counterexample to the original question would refute the universal bound on the closed class as well. The reduction remains available on separately specified polynomial classes.

<a id="the-particular-curves-used-in-the-earlier-approach."></a>

#### The particular curves used in the earlier approach.

For polynomials whose critical points are simple and whose critical values are nonzero, with pairwise distinct arguments and moduli, cutting the value plane along critical rays gives the finite inverse-sheet construction recorded in [the decomposition into inverse sheets](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/AttachmentAwareReeb.md). The underlying inverse-sheet construction is classical: Dubinin \[dubinin2006critical, §1, pp. 1169–1170\] cuts outward from the critical values and describes the resulting sheet adjacency tree; \[dubinin2006capacity, §2, pp. 34–35\] uses a related network in a capacity argument. The latter assumes critical values bounded by one and controls logarithmic capacity, not Euclidean length. Here the task is to specify admissible descent arcs and estimate their metric cost. Let $`L_f(c)`$ be the length of the curve formed by the two inverse lifts of $`[0,f(c)]`$ meeting at a critical point $`c`$. This length is finite under the stated hypotheses: the inverse derivative has an integrable inverse-square-root singularity at the simple critical endpoint and is regular at the root endpoint. Its halves are Newton-flow trajectories from $`c`$ to roots, that is, edges of the Newtonian graph \[kozen-stefansson1997, Definition 2.1\]. These curves lie in $`\{|f|\le1\}`$ precisely when $`|f(c)|\le1`$. A sufficient length bound is
``` math
\min_{\substack{f'(c)=0\\|f(c)|\le1}}L_f(c)\le2.
```
Since $`\Lambda`$ minimises over all curves, the minimum over these inverse-ray curves is an upper bound for $`\Lambda`$. Equality between the two minimisations is not assumed. In a unit-sublevel component, the sheets and tree use only that component’s critical points; equal values in another component do not invalidate this local construction. These ordinary topological steps are not formalised here and supply no length estimate.

<a id="the-attachment-obstruction-is-quantitative."></a>

#### The attachment obstruction is quantitative.

For $`f(z)=z^n-r^n`$ with $`r>0`$, consider the value ray $`\{s e^{i\theta}:s\ge0\}`$. Along any of its inverse lifts, $`|z|^n=|r^n+s e^{i\theta}|`$. The minimum over $`s\ge0`$ is $`r^n`$ when $`\cos\theta\ge0`$, and $`r^n|\sin\theta|`$ otherwise. Thus a lift meets $`B(0,\varepsilon)`$, with $`0<\varepsilon<r`$, precisely when
``` math
\cos\theta<0,\qquad
 |\sin\theta|<(\varepsilon/r)^n.
```
The permitted directions therefore form an interval about $`\pi`$ of width $`2\arcsin((\varepsilon/r)^n)`$. A bound averaged over all directions need not hold on this shrinking interval. An argument that must join its paths near the critical point needs control there, or must leave the joining point free. The binomial itself is solved by radial segments.

<a id="which-information-is-insufficient."></a>

#### Which information is insufficient.

The sextic of Proposition <a href="#res:sextic-spoke" data-reference-type="ref" data-reference="res:sextic-spoke">2</a> excludes automatic control of every prescribed root-to-origin segment once further partial sums occur. The exact Cassini example in Section <a href="#sec:gap" data-reference-type="ref" data-reference="sec:gap">11</a> excludes the historical global tree-length estimate even after the local saddle model is corrected. The examples in Section <a href="#sec:exact-obstructions" data-reference-type="ref" data-reference="sec:exact-obstructions">7</a> show that the least critical modulus and the separation test with radius $`2`$ do not cover all polynomials, and that the number of roots at the first merger does not control capacity after subsequent mergers. The critical-value inequalities bound sums of powers of the moduli; they do not choose inverse branches that join to form the required path. The ordinary [note on powers of Blaschke products](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/BlaschkePowerCriticalSpectra.md) gives fixed-degree tests of these limitations and separate asymptotic results for the shortest contained path. The family, certificate scope, centroid restriction and two distinct parameter regimes are given in [the Blaschke-product subsection of the companion](../mirror/erdos1041-lemniscate-reasoning-surface.pdf#nameddest=blaschke-product-examples), after the compactness functional is defined. Neither a failed sufficient condition nor a fixed-degree certificate settles an asymptotic path estimate.

The earlier note gives a near-regular-pentagon family for which *all* origin segments escape \[revision2026, Proposition A of the preserved earlier note\]. The long record gives the two-scale proof along the five segments, including the open-disc contraction. The addendum reports a stronger failure for every critical joining point, but its proof was not supplied or available for checking in this revision. Failure at the origin, which is not a critical point of this family, does not establish that stronger assertion. Neither straight-segment claim excludes a different vertex, curved inverse-ray arms or an arbitrary contained connector.

Outside the cases covered by the structural results, the separation criterion and the recorded certificate consequence $`\mu\le529/1000`$, these arguments give no general conclusion. In particular, exceeding a sufficient cutoff is not evidence for or against the unrestricted assertion. On any class where a stronger positive result is sought, the same selected pair must satisfy both containment and a length estimate. The long record gives the examples showing why root distances and critical-value means do not ensure this.

<a id="sec:evidence-ledger"></a>

# Proof boundaries

The formal-source index records complete formal results for the quadratic weighted inequality, the exponent-$`2/(n-1)`$ critical-value mean, the translated cubic family, and the sparse quintic in its checked build. The fourth-power and higher-moment refinements above have ordinary analytic proofs, not the same recorded formal status. The degree-three path is also implemented, including a release-source theorem under monicity, degree three and the open-disc root hypothesis, but that endpoint is not in this recorded checked-build category. The guide below distinguishes the two source snapshots. The older source links below are retained at their original commits; they are not replaced by links to the current development branch.

The trinomial inequalities and finite selection lemmas have the narrower statements cited beside them. They do not automatically certify the ordinary geometric steps in a path proof. In particular, the $`13/25`$ theorem uses analysis and a rational certificate; the independent $`71/10`$ argument, the inverse-map construction, and the decomposition into sheets also contain ordinary, unformalised analysis. The accompanying research addendum is unreviewed, and its rational checks are distinct from its analytic arguments. No fresh Lean build or independent mathematical review was performed for this exposition revision.

Lower semicontinuity explains how an established dense-class length bound would extend to the closed class. It does not establish that bound. Likewise, the lengths of the particular inverse-ray curves need not equal the infimum over all contained curves. The reported grid searches prove neither estimate.

<a id="sec:1041-sources"></a>

## Sources and adjacent results

The original root-to-root problem is \[ehp1958, Problem 5, p. 139\]. Pendyala’s degree-four theorem \[june2026, Theorem 1\] is directly comparable. Erdős Problem #1120, treated by Pendyala \[pendyala2026shortest, Definition 1.1 and Theorem 1.2\], asks for a path from $`0`$ to the unit circle inside $`\{|z|\le1,\ |f(z)|\le1\}`$. Its admissible region includes the unit-disc restriction, and its endpoints are not a chosen pair of roots. It does not imply the root-pair conclusion. The exact Cassini obstruction in Section <a href="#sec:gap" data-reference-type="ref" data-reference="sec:gap">11</a> concerns the metric assertion of \[march2026, Prop. 12\]. Eremenko and Hayman prove the global boundary estimate $`\operatorname{length}\{z:|p(z)|=1\}<9.173\deg p`$ and show that an extremal level set is connected \[eremenko-hayman, Thm. 1 and the lemma on connectedness\]. Their metric is the total length of a level curve, so this does not supply the short internal root-to-root connector asked for here.

The Newton value identity of Section <a href="#sec:newton" data-reference-type="ref" data-reference="sec:newton">8</a> is a lemma of Shub, Tischler and Williams, and the ray-segment description of Newton-flow edges belongs to their Newtonian graph; we use both in the form recorded by Kozen and Stefánsson \[kozen-stefansson1997, Lemmas 2.1–2.2 and §2\]. The area arguments use Pólya’s inequality and the area–capacity inequality in the formulations \[crane, Theorems 1 and 6\]; the square-root uniformisation uses the component-wise Riemann–Hurwitz count in the proof of \[eks2010, Proposition 2.1\]. Existence of a contained root segment for collinear zeros already follows from \[ehp1958, Theorem 1\]; Section <a href="#sec:collinear" data-reference-type="ref" data-reference="sec:collinear">14</a> adds the sharp constant. Crane’s Smale mean-value argument \[crane2007smale, Lemma 2.1, Theorem 2.2 and §§3–4\] combines inverse branches, radial slits and capacity, but concerns a derivative-normalised mean-value ratio rather than our absolute monic critical values. Dubinin’s four-point theorem \[dubinin2013fourpoint, Theorem 1 and Corollary 4\] assumes a bound on *all* critical values and concerns distortion; its normalisation does not supply our root-disc moment or path estimate. Kuznetsova and Tkachev \[kuznetsova2003, Theorems 1–2\] study length functions on regular lemniscate levels. Their log-convexity is useful context, not a uniform one-root perimeter bound at a critical endpoint. The long record gives further source comparisons and the history of the withdrawn argument. No uniqueness or priority claim is inferred from this comparison.

<a id="acknowledgements"></a>

# Acknowledgements

I thank Wouter van Doorn for advice on mathematical exposition, in particular on explaining restrictive hypotheses, avoiding private terminology and introducing notation only when it helps the reader. His remarks concerned another note; this acknowledgement does not imply that he reviewed or endorsed the mathematics of the present paper.

<a id="app:sources"></a>

# Guide to the formal sources

The rescaling step, transporting both the level and the extended variation of an arbitrary curve under $`z\mapsto h+cz`$, is [the affine rescaling of a rectifiable path](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/PaperMetricScaling.lean#L40). The formal-source index places that implementation outside its checked build; the analytic theorem used before rescaling is not fully formalised.

The finite Cassini inequalities are in the namespace `ErdosProblems.Erdos1041.CassiniTreeBudget`.

The formal-source index describes sources at snapshot `6b78209ab63a`. The links below retain their earlier commits and line numbers. The index distinguishes complete statements in its recorded checked build from implementations present outside that build.

- Complete statements recorded in the supplied checked build: [critical-value mean with exponent $`2/(n-1)`$](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperCriticalValueMeanR10.lean#L101), [the quadratic weighted inequality for points in a disc](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperWeightedRefinementsR10.lean#L17), and [translated cubic-fibre path](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperCubicFibres.lean#L240).

- Complete implementations recorded outside that build: [degree-three path](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperCubicCompletion.lean#L297). The supplied release snapshot additionally contains [the cubic theorem under monicity, degree three and the open-disc hypothesis](https://github.com/wcook04/plectis-erdos-lean/blob/52f29ad173b04e3bac941b3663f2b9aebe5de0bb/ErdosProblems/Erdos1041/PaperCubicMonic.lean#L32), with an actual proof and an expanded solution statement. Its recorded status is `release_only`; it is not promoted to the checked-build category here.

- Also recorded in the supplied checked build: [the sparse-quintic path](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperPrimitiveCompletionR10.lean#L235).

- The index also distinguishes finite inequalities, declarations supplied only in the release sources, and ordinary analytic arguments. None of these categories is interchangeable with a complete formal path theorem.

A snapshot link is not a build receipt. The original paper-wide commit macro is retained for legacy links; newer target links name their own snapshot explicitly.

<a id="sec:pinned-lean-sources"></a>

# Pinned Lean sources

These links retain the original source files and line numbers at the commit fixed for this paper. Their text describes the mathematics; the Lean declaration names remain in the link targets.

- [the Newton vector field](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L34)

- [cancellation of the derivative in the Newton equation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L38)

- [the positive-ray relation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L77)

- [reflexivity of the positive-ray relation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L80)

- [symmetry of the positive-ray relation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L84)

- [transitivity of the positive-ray relation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L92)

- [real affine lines in the complex plane](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L127)

- [agreement with the affine-span definition](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L130)

- [closedness of a real affine line](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L147)

- [density of its complement](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L152)

- [a small perturbation avoiding finitely many real lines](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L162)

- [the line containing forbidden translations](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L179)

- [retention of the unit-disc margin near a root](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L230)

- [root displacement under a constant perturbation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L257)

- [positive-ray invariance under exponential decay](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L306)

<div class="thebibliography">

99 T. F. Bloom, *Erdős Problems*, problem 1041. <https://www.erdosproblems.com/1041> P. Erdős, F. Herzog, and G. Piranian, *Metric properties of polynomials*, J. Analyse Math. **6** (1958), 125–148, doi:[10.1007/BF02790232](https://doi.org/10.1007/BF02790232). `shtuka`, *A Short Path Joining Two Zeros Inside a Polynomial Lemniscate*, manuscript posted 24 March 2026, 48 pp. <https://shtuka123.github.io/1041/main.pdf> V. S. Pendyala, *A Degree-Four Lemniscate Path Theorem*, arXiv:[2606.24875v1](https://arxiv.org/abs/2606.24875v1) (2026), doi:[10.48550/arXiv.2606.24875](https://doi.org/10.48550/arXiv.2606.24875). V. S. Pendyala, *Shortest paths in polynomial lemniscate sublevel sets and a problem of Erdős*, arXiv:[2606.19178v1](https://arxiv.org/abs/2606.19178v1) (2026), doi:[10.48550/arXiv.2606.19178](https://doi.org/10.48550/arXiv.2606.19178). D. Kozen and K. Stefánsson, *Computing the Newtonian graph*, J. Symbolic Comput. **24** (1997), no. 2, 125–136, doi:[10.1006/jsco.1997.0118](https://doi.org/10.1006/jsco.1997.0118); authors’ copy <https://www.cs.cornell.edu/kozen/Papers/newton.pdf>. E. Crane, *The areas of polynomial images and pre-images*, Bull. London Math. Soc. **36** (2004), no. 6, 786–792, doi:[10.1112/S0024609304003509](https://doi.org/10.1112/S0024609304003509); preprint arXiv:[math/0302189v1](https://arxiv.org/abs/math/0302189v1), whose statement numbers are cited. P. Ebenfelt, D. Khavinson, and H. S. Shapiro, *Two-dimensional shapes and lemniscates*, in *Complex Analysis and Dynamical Systems IV, Part 1*, Contemp. Math. **553**, Amer. Math. Soc., Providence, RI, 2011, 45–59, doi:[10.1090/conm/553/10931](https://doi.org/10.1090/conm/553/10931); preprint arXiv:[1003.4567v1](https://arxiv.org/abs/1003.4567v1), whose statement numbers are cited. A. Eremenko and W. Hayman, *On the length of lemniscates*, Michigan Math. J. **46** (1999), no. 2, 409–415, doi:[10.1307/mmj/1030132418](https://doi.org/10.1307/mmj/1030132418); preprint arXiv:[0805.2295](https://arxiv.org/abs/0805.2295). A. Eremenko and P. Yuditskii, *Comb functions*, Contemp. Math. **578** (2012), 99–118, doi:[10.1090/conm/578/11472](https://doi.org/10.1090/conm/578/11472); preprint arXiv:[1109.1464v1](https://arxiv.org/abs/1109.1464v1). A. Eremenko and L. Lempert, *An extremal problem for polynomials*, Proc. Amer. Math. Soc. **122** (1994), no. 1, 191–193, doi:[10.1090/S0002-9939-1994-1207536-1](https://doi.org/10.1090/S0002-9939-1994-1207536-1). A. Eremenko, *A Markov-type inequality for arbitrary plane continua*, Proc. Amer. Math. Soc. **135** (2007), no. 5, 1505–1510, doi:[10.1090/S0002-9939-06-08640-0](https://doi.org/10.1090/S0002-9939-06-08640-0); preprint arXiv:[math/0606745v1](https://arxiv.org/abs/math/0606745v1). C. J. Bishop, A. Eremenko, and K. Lazebnik, *On the shapes of rational lemniscates*, Geom. Funct. Anal. **35** (2025), no. 2, 359–407, doi:[10.1007/s00039-025-00704-2](https://doi.org/10.1007/s00039-025-00704-2); preprint arXiv:[2407.14610v1](https://arxiv.org/abs/2407.14610v1). V. N. Dubinin, *Some inequalities for polynomials and rational functions associated with lemniscates*, Zap. Nauchn. Sem. POMI **404** (2012), 83–99; English translation, J. Math. Sci. **193** (2013), no. 1, 45–54, doi:[10.1007/s10958-013-1432-4](https://doi.org/10.1007/s10958-013-1432-4). G. Pólya, *Beitrag zur Verallgemeinerung des Verzerrungssatzes auf mehrfach zusammenhängende Gebiete*, Sitzungsberichte der Preussischen Akademie der Wissenschaften, Physikalisch-Mathematische Klasse (1928), printed pp. 228–232 and 280–282. <https://archive.org/details/sitzungsbericht1928preu>. V. N. Dubinin, *Inequalities for critical values of polynomials*, Sb. Math. **197** (2006), no. 8, 1167–1176, doi:[10.1070/SM2006v197n08ABEH003793](https://doi.org/10.1070/SM2006v197n08ABEH003793). E. Crane, *A bound for Smale’s mean value conjecture for complex polynomials*, Bull. London Math. Soc. **39** (2007), no. 5, 781–791, doi:[10.1112/blms/bdm063](https://doi.org/10.1112/blms/bdm063); author preprint <https://people.maths.bris.ac.uk/~maetc/SMVCbound.pdf>. V. N. Dubinin, *Four-point distortion theorem for complex polynomials*, arXiv:[1301.3985v1](https://arxiv.org/abs/1301.3985v1) (2013). O. S. Kuznetsova and V. G. Tkachev, *Length functions of lemniscates*, Manuscripta Math. **112** (2003), 519–538, doi:[10.1007/s00229-003-0411-3](https://doi.org/10.1007/s00229-003-0411-3); preprint arXiv:[math/0306327](https://arxiv.org/abs/math/0306327). D. Tischler, *Critical points and values of complex polynomials*, J. Complexity **5** (1989), no. 4, 438–456. W. Cook / Plectis, *Three refinements for the lemniscate-path programme*, 16 September 2026, accompanying unreviewed research note, Sections 1–3, with the earlier *Structural obstructions* note preserved in the same revision bundle. V. N. Dubinin, *Lemniscates and inequalities for the logarithmic capacities of continua*, Mat. Zametki **80** (2006), no. 1, 33–37; English translation, Math. Notes **80** (2006), no. 1, 31–35, doi:[10.1007/s11006-006-0105-8](https://doi.org/10.1007/s11006-006-0105-8).

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.

[^1]: Lean checks this instance in [`erdos1041_ani_degree_seven`](https://github.com/wcook04/plectis-erdos/blob/f70679d47178bf1174309cb29f5b31748609cc04/lean/ErdosProblems/Erdos1041/Counterexample/CatalogueAdapter.lean#L25). The formal result concerns one polynomial; it does not formalise the reported small-parameter family or a Hausdorff-measure comparison, and its correspondence with the historical formulation has not received independent human review.
