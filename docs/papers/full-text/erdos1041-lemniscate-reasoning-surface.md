<a id="erdos1041-lemniscate-reasoning-surface"></a>

# Paths in Polynomial Lemniscates: Proofs and Examples

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

For one degree-seven polynomial constructed by the erdosproblems.com contributor [`ani`](https://www.erdosproblems.com/forum/thread/1041#post-8861), Lean proves that every preconnected subset of its strict unit lemniscate containing two distinct roots has one-dimensional Hausdorff measure greater than $`2`$. This refutes the exact path-image-length formulation in Formal Conjectures, as well as the total-variation formulation. Independent human review of correspondence with the 1958 curve-length wording is not recorded. For a monic trinomial with roots in the open unit disc, the root equation bounds the polynomial along every root-to-origin segment. Any two distinct roots are therefore joined inside $`\{|f|<1\}`$ by a path of length less than $`2`$. For any squarefree monic polynomial $`f`$ of degree $`n\ge2`$, an area-growth argument gives such a path when its least critical-value modulus $`\mu`$ is at most $`13/25`$, without a root-location hypothesis. Scaling gives length less than $`(5/2)\mu^{1/n}`$ inside $`\{|f|<(25/13)\mu\}`$. We develop this argument, an independent inverse-ray averaging estimate, and a construction using an isolated simple critical value. We also prove results for collinear roots and several coefficient families. A weighted Poisson identity gives the mean bound, with sharp constant, $`\sum_{j=1}^{n-1}|f(c_j)|^{4/(n-1)}\le(n-1)R^{4n/(n-1)}`$ for roots in a closed disc of radius $`R`$, with critical points counted with multiplicity. Examples distinguish this bound from path-length control. The final sections examine inverse-sheet topology and refute an earlier spanning-tree estimate. The positive results retain their stated hypotheses and do not repair the refuted universal formulation.

The [short note](../mirror/erdos-1041-lemniscate-newton-flow.pdf) centres on the trinomial identity in Section <a href="#sec:trinomials" data-reference-type="ref" data-reference="sec:trinomials">2</a>. That proof does not use Newton flow. The area-growth comparison is proved here in Section <a href="#sec:low-critical-closure" data-reference-type="ref" data-reference="sec:low-critical-closure">3</a>. The other constructions are independent of that proof. This record provides their derivations and keeps failed estimates beside the witnesses that refute them.

<div class="center">

| Short-note passage | Argument in this record |
|:---|:---|
| Section 3: small critical value | Section <a href="#sec:low-critical-closure" data-reference-type="ref" data-reference="sec:low-critical-closure">3</a>: inverse-map lengths, packing, area growth and the rational certificate. |
| Supplement after Section 3: area estimate | Section <a href="#sec:constant-factor" data-reference-type="ref" data-reference="sec:constant-factor">4</a>: regular-level selection, low and high lifts, and the adjacent-pair average. |
| Section 6: isolated critical value | Section <a href="#sec:critical-value-separation" data-reference-type="ref" data-reference="sec:critical-value-separation">6</a>: the two-sheeted component, square-root map, Bergman segment bound and capacity estimate. |
| Sections 13–14: chords and collinear roots | Section <a href="#sec:frontier" data-reference-type="ref" data-reference="sec:frontier">8</a>: the [exact binomial chord calculation](#binomial-chord-calculation); Section <a href="#subsec:sharp-collinear-chebyshev" data-reference-type="ref" data-reference="subsec:sharp-collinear-chebyshev">7.1</a>: Chebyshev comparison and [related extremal problems](#collinear-source-comparison). |
| Section 15: critical-value means | Section <a href="#sec:frontier" data-reference-type="ref" data-reference="sec:frontier">8</a>: the reflected derivative, weighted Poisson identity, boundary passage and equality cases. |
| Section 17: limits and examples | Section <a href="#sec:frontier" data-reference-type="ref" data-reference="sec:frontier">8</a>, subsections [Limits of contained paths at fixed degree](#closed-class-limits) and [Blaschke-product examples and limits in varying degree](#blaschke-product-examples). |

</div>

<a id="sec:problem"></a>

# The historical question

<div id="res:problem" class="problem">

**Problem 1** (Erdős \#1041). Let $`f(z)=\prod_{i=1}^{n}(z-z_i)`$ be monic of degree $`n\ge2`$, with $`z_i\in\mathbb{D}`$, the open unit disc. Must two of the roots be joined by a curve of length less than $`2`$ lying in the open lemniscate $`\{z\in\mathbb{C}:|f(z)|<1\}`$?

</div>

The open-disc hypothesis is essential for this formulation. For $`f(z)=z^2-1`$, whose roots lie on the unit circle, every continuous path from $`-1`$ to $`1`$ meets the imaginary axis. There $`|f(iy)|=1+y^2\ge1`$, so no such path lies in the open unit lemniscate. Repeated roots, counted as distinct occurrences, give a constant path; the substantive case is therefore squarefree.

The problem numbering follows Bloom’s Erdős problem catalogue \[bloom\]. <span id="res:ani-degree-seven-counterexample-long" label="res:ani-degree-seven-counterexample-long"></span> The degree-seven polynomial constructed by [erdosproblems.com contributor `ani`](https://www.erdosproblems.com/forum/thread/1041#post-8861) has distinct roots in the open unit disc. Lean proves that every preconnected subset of its strict unit lemniscate containing two distinct roots has one-dimensional Hausdorff measure greater than $`2`$. Hence the image of every continuous root-to-root path has Hausdorff length greater than $`2`$, and the exact Formal Conjectures statement is false.[^1] The new Hausdorff bound uses a bottleneck: a preconnected set joining the two roots must cross radial circles in two disjoint sheets near a critical point. The distance coordinate is one-Lipschitz on each sheet, and the resulting lower bounds for their disjoint portions add to more than $`2`$. This is stronger than a bound only on the variation of a parametrisation. The original source is Problem 5 on printed p. 139 of Erdős–Herzog–Piranian \[ehp1958, Problem 5, p. 139\]; the preceding paragraph records the known input that one component of the lemniscate contains at least two zeros.

The main constructions use different kinds of information. The trinomial identity controls a prescribed path directly. The area argument instead uses the number of roots in a sublevel component. Source comparisons for component counts and lemniscate topology accompany the inverse-sheet discussion in Section <a href="#sec:gap" data-reference-type="ref" data-reference="sec:gap">11</a>; the Newton-flow terminology is introduced in Section <a href="#sec:newton" data-reference-type="ref" data-reference="sec:newton">9</a>.

Two recent manuscripts are relevant. The 48-page manuscript posted by `shtuka` on 24 March 2026 \[march2026, Theorem 1, p. 1\] claims the unrestricted statement. Its Proposition 12 (p. 16, with proof continuing through p. 30) supplies the spanning-tree decomposition used in the final proof. The defect was located publicly in the problem’s discussion thread: on 25 March 2026 Tao observed that the invocation of Lemma 8 there is unjustified and that the flow lines need not organise into connected trees, and on 26 March 2026 the manuscript’s author agreed that the statement of Proposition 12 itself, not only its printed proof, is incorrect, and set the strategy aside. Section <a href="#sec:gap" data-reference-type="ref" data-reference="sec:gap">11</a> records an independent diagnosis of the same local saddle defect, together with the Cassini obstruction to the printed global tree-length bound. That obstruction refutes the metric estimate used in the final proof, not Erdős \#1041. Pendyala’s independent June 2026 preprint \[june2026, Thm. 1, p. 1\] proves the degree-four case through a finite four-point radial lemma and a short polygonal connector. That is the degree-four result directly comparable to the root-pair problem. Together with the cubic theorem established here, it settles these two degrees; it does not supply the general-degree conclusion. The all-degree estimates below either impose a bound on the least critical-value modulus or allow a larger length constant and containment level. They address different hypotheses from the quartic theorem.

<a id="what-the-formal-links-establish."></a>

#### What the formal links establish.

An ordinary mathematical argument is distinct from a proof checked by Lean. A linked declaration may prove a finite inequality without constructing the curve used here. Moreover, a declaration may be present in the versioned sources but absent from their recorded checked build. We distinguish these cases where the declarations are used. Neither a successful build nor an exact finite calculation establishes an unformalised analytic step.

<a id="sec:trinomials"></a>

# Trinomials

Write $`E_f=\{z\in\mathbb C:|f(z)|<1\}`$. The first theorem gives a prescribed path between every pair of zeros of a trinomial, in every degree.

<div id="res:trinomial-all-degree" class="theorem">

**Theorem 2** (trinomial root connections). *Let $`n,m`$ be integers with $`1\le m<n`$, and let $`f(z)=z^n+az^m+b`$ have every zero in $`\mathbb{D}`$. For every zero $`\zeta`$, the segment $`[0,\zeta]`$ lies in $`E_f`$. Consequently any two zeros $`\zeta_1,\zeta_2`$ are joined in $`E_f`$ by the broken line $`\zeta_1\to0\to\zeta_2`$, of length $`|\zeta_1|+|\zeta_2|<2`$.*

</div>

Lean: [all spokes](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperTrinomial.lean#L26), [complete trinomial](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperTrinomial.lean#L38).

<div class="proof">

*Proof.* Vieta’s formula gives $`|b|<1`$. At a zero $`\zeta`$ the root equation $`\zeta^n+a\zeta^m+b=0`$ eliminates the middle coefficient:
``` math
\begin{equation}
\label{eq:trinomial-cancellation}
 f(t\zeta)=b(1-t^m)+\zeta^n(t^n-t^m).
\end{equation}
```
For $`0\le t<1`$ the two scalar weights $`1-t^m`$ and $`t^m-t^n`$ are nonnegative and sum to $`1-t^n`$, so
``` math
|f(t\zeta)|\le|b|(1-t^m)+|\zeta|^n(t^m-t^n)<1-t^n\le1 .
```
At $`t=1`$ the value is zero. Concatenating two such segments gives the length assertion. ◻

</div>

The coefficient $`a`$ carries no hypothesis; the root equation removes it before absolute values are taken. The conclusion concerns segments to zeros and makes no assertion that $`E_f`$ is star-shaped.

<a id="subsec:abel-mechanism"></a>

#### The cancellation mechanism.

For $`f(z)=\sum_{k=0}^nc_kz^k`$ and a zero $`\zeta`$, put $`S_j=\sum_{k=0}^jc_k\zeta^k`$. Finite summation by parts gives
``` math
\begin{equation}
\label{eq:abel-control-polygon}
 f(t\zeta)=\sum_{j=0}^{n-1}(t^j-t^{j+1})S_j\qquad(0\le t\le1),
\end{equation}
```
since the coefficient of $`c_k\zeta^k`$ on the right is $`t^k-t^n`$ and $`\sum_{k<n}c_k\zeta^k=-c_n\zeta^n`$. The weights in <a href="#eq:abel-control-polygon" data-reference-type="eqref" data-reference="eq:abel-control-polygon">[eq:abel-control-polygon]</a> are nonnegative and sum to $`1-t^n`$, so the whole radial segment lies in the closed unit sublevel set whenever every partial sum lies in the closed unit disc. For a trinomial, $`S_j=b`$ for $`j<m`$ and $`S_j=-\zeta^n`$ for $`m\le j<n`$; these two values may coincide. This is exactly the estimate above. With two intermediate coefficients, the root-disc hypothesis need not put every partial sum in the unit disc. The next example shows that a prescribed radial segment can then escape.

<div id="ex:sextic-spoke" class="example">

**Example 3** (an escaping root spoke). Let $`0<r<1`$ satisfy $`r^6>320/327`$, and set
``` math
f_r(z)=z^6+\tfrac15r^2z^4-\tfrac15r^4z^2-r^6
       =(z^2-r^2)\bigl(z^4+\tfrac65r^2z^2+r^4\bigr).
```
Every zero has modulus $`r`$: for the quartic factor put $`z=rw`$, so that the squared roots solve $`v^2+(6/5)v+1=0`$, whose two roots are complex conjugates of product one. Nevertheless
``` math
f_r(r/2)=-\frac{327}{320}\,r^6,
```
so the segment $`[0,r]`$ leaves $`E_{f_r}`$. This rules out a universal assertion about every origin-to-zero segment. It exhibits no counterexample to the existence of some short connection.

</div>

<a id="bdry:trinomial"></a>

#### Sources and scope.

The identity <a href="#eq:abel-control-polygon" data-reference-type="eqref" data-reference="eq:abel-control-polygon">[eq:abel-control-polygon]</a> is checked as [the Abel summation identity](https://github.com/wcook04/plectis-erdos/blob/0ba585f632fbbbb43af2ee9532d4e83752af3f67/ErdosProblems/Erdos1041/AbelControlPolygon.lean#L123), the constant-term bound as [the constant-term estimate from the root-disc hypothesis](https://github.com/wcook04/plectis-erdos/blob/0ba585f632fbbbb43af2ee9532d4e83752af3f67/ErdosProblems/Erdos1041/AbelControlPolygon.lean#L258), the radial estimate as [containment along a trinomial root segment](https://github.com/wcook04/plectis-erdos/blob/0ba585f632fbbbb43af2ee9532d4e83752af3f67/ErdosProblems/Erdos1041/AbelControlPolygon.lean#L219), and their combination with the length bound as [the two segment inequalities and their length bound](https://github.com/wcook04/plectis-erdos/blob/0ba585f632fbbbb43af2ee9532d4e83752af3f67/ErdosProblems/Erdos1041/AbelControlPolygon.lean#L330). Example <a href="#ex:sextic-spoke" data-reference-type="ref" data-reference="ex:sextic-spoke">3</a> is checked as [the sextic evaluation](https://github.com/wcook04/plectis-erdos/blob/0ba585f632fbbbb43af2ee9532d4e83752af3f67/ErdosProblems/Erdos1041/AbelControlPolygon.lean#L555). What the kernel proves is the pair of radial inequalities and the bound $`|\zeta_1|+|\zeta_2|<2`$ on the sum of the two radii. Assembling those into a single rectifiable path object, and the passage to the one-dimensional Hausdorff measure used by the original formulation of the problem, are ordinary steps taken here. No novelty claim is made for this elementary trinomial argument.

<a id="sec:low-critical-closure"></a>

# A small least critical value

The next criterion restricts the smallest critical-value modulus, but places no condition on the coefficients or the root locations. Throughout this section
``` math
\mu=\min_{f'(c)=0}|f(c)|
```
is the least critical-value modulus.

<div id="res:low-critical-thirteen-twentyfifths" class="theorem">

**Theorem 4** (a small least critical value forces a short connector). *Let $`f`$ be squarefree and monic of degree $`n\ge2`$ with $`\mu\le13/25`$. Then two distinct roots of $`f`$ are joined inside $`\{|f|<1\}`$ by a rectifiable curve of length strictly below $`2`$. No hypothesis is placed on the locations of the roots, on the number of roots in any component, or on the capacity of any component.*

</div>

Not formalised: the degree-two case and the exact rational arithmetic of the stopping-time comparison are checked, and the analytic argument in higher degrees is not. See the [coverage section](#sec:coverage).

For $`f(z)=z^n-b`$ with $`0<|b|<1`$, the only critical point is $`0`$ and $`\mu=|b|`$. Thus this criterion includes $`|b|\le13/25`$ but excludes $`13/25<|b|<1`$, although the trinomial theorem gives the required path in both ranges. Its value is that it also applies to polynomials with arbitrary coefficient patterns, including roots outside the unit disc. For example, $`(z-3)^n-1/2`$, $`n\ge2`$, has $`\mu=1/2`$ and all its roots satisfy $`|z|>2`$. The required containment is $`|f(z)|<1`$, not $`|z|<1`$.

<div id="res:low-critical-scale-free" class="corollary">

**Corollary 5** (scale-free form). *Every squarefree monic $`f`$ of degree $`n\ge2`$ has two distinct roots joined inside $`\{|f|<(25/13)\mu\}`$ by a curve of length below $`2\bigl((25/13)\mu\bigr)^{1/n}`$.*

</div>

Lean: [scaled low critical of low critical](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/LowCriticalScaleTransport.lean#L460). Conditional on Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a> as stated; see the [coverage section](#sec:coverage).

<div class="proof">

*Proof.* Apply Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a> to $`s^{-n}f(sz)`$ with $`s=\bigl((25/13)\mu\bigr)^{1/n}`$, whose least critical-value modulus is $`13/25`$, and scale back. Squarefreeness gives $`\mu>0`$, so the scaling factor is positive. ◻

</div>

The proof has two steps. Failure of the length bound first forces the roots to be far apart in the hyperbolic metric of a sublevel component. Packing those roots gives a lower bound for their number. Averaging paths between adjacent boundary points then converts that root count into an area-growth inequality. The rational certificate shows that this growth would exceed Pólya’s area bound before the value level reaches $`1`$.

<a id="consequences-of-having-no-short-path."></a>

#### Consequences of having no short path.

Assume no two distinct roots are joined inside $`\{|f|<1\}`$ by a curve of length below $`2`$. Choose a critical point at level $`\mu`$ and two descending inverse arcs into distinct one-root components of $`\{|f|<\mu\}`$; below $`\mu`$ each component maps conformally onto the value disc, and distinct local inverse arcs at the first critical point enter distinct components, since two inverse images of a nearby regular value in one component would contradict its degree one. Their union is a compact connected set containing two roots. Fix a level $`t\in(\mu,1)`$ at which no critical value has modulus $`t`$, so that the level is regular. Let $`C_t`$ be the component of $`\{|f|<t\}`$ containing that set, let $`k\ge2`$ be its root count, and put $`x=\log(t/\mu)`$ and $`a=\operatorname{Area}(C_t)/\pi`$; Pólya’s inequality \[crane, Theorem 1\] gives $`a\le t^{2/n}<1`$. The component is a Jordan domain. List its roots as $`\zeta_1,\ldots,\zeta_k`$, choose a Riemann map $`\varphi:\mathbb D\to C_t`$, and write $`b_j=\varphi^{-1}(\zeta_j)`$. The component-wise form of \[eks2010, (2.2)\] is
``` math
\frac{f(\varphi(z))}{t}
 =e^{i\theta}\prod_{j=1}^k\frac{z-b_j}{1-\overline{b_j}z}.
```
Indeed, regularity extends $`\varphi`$ across the Jordan boundary. The quotient of the two sides without the phase has no zero or pole on the closed disc and has boundary modulus one. The maximum principle, applied to that quotient and its reciprocal, makes it a unimodular constant. The product has degree $`k`$, the root count of this component, not necessarily the full degree $`n`$. Distances between the $`b_j`$ below are hyperbolic distances in $`\mathbb D`$, normalised by $`d(0,s)=2\operatorname{artanh}s`$ for $`0\le s<1`$. Intrinsic distances in $`C_t`$ are infima of Euclidean lengths of curves in that component.

The length estimate converts area into a bound for the image of a compact real interval $`I\subset(-1,1)`$. Here is the coefficient calculation underlying the Bergman-kernel argument. Write $`\varphi'(z)=\sum_{\ell\ge0}\alpha_\ell z^\ell`$. Injectivity and the area formula give $`\sum_{\ell\ge0}|\alpha_\ell|^2/(\ell+1)=a`$. To express length as a linear integral, choose $`\omega(x)=\overline{\varphi'(x)}/|\varphi'(x)|`$ on $`I`$; the denominator is nonzero because $`\varphi`$ is conformal. Cauchy–Schwarz gives
``` math
\operatorname{length}(\varphi(I))^2
 =\left|\sum_{\ell\ge0}\alpha_\ell\int_I\omega(x)x^\ell\,dx\right|^2
 \le a\sum_{\ell\ge0}(\ell+1)
       \left|\int_I\omega(x)x^\ell\,dx\right|^2.
```
Compactness of $`I`$ permits termwise integration of the series. Since $`\sum_{\ell\ge0}(\ell+1)(xy)^\ell=(1-xy)^{-2}>0`$ for real $`x,y\in I`$, taking absolute values in the resulting double integral yields
``` math
\operatorname{length}(\varphi(I))^2
 \le a\int_I\!\int_I\frac{dx\,dy}{(1-xy)^2}.
```
This is precisely the positivity of the disc Bergman kernel $`K(z,w)=\pi^{-1}(1-z\overline w)^{-2}`$ on the real diameter. For $`I=[u,v]\subset(-1,1)`$, direct integration gives
``` math
\int_u^v\!\int_u^v\frac{dx\,dy}{(1-xy)^2}
 =\log\frac{(1-uv)^2}{(1-u^2)(1-v^2)}.
```
Thus $`I=[0,r]`$ gives $`\operatorname{length}(\varphi([0,r]))^2\le a\log(1/(1-r^2))`$. Moving two preimages to $`\pm s`$ and taking $`I=[-s,s]`$ instead gives
``` math
\operatorname{length}(\varphi([-s,s]))^2\le4a\operatorname{artanh}(s^2).
```
A pair of roots at hyperbolic distance $`d`$ may be placed at $`\pm\tanh(d/4)`$, so a connector shorter than $`2`$ exists as soon as $`\operatorname{artanh}(\tanh^2(d/4))<1/a`$. Failure therefore gives
``` math
\begin{equation}
\label{eq:lc-separation}
 d(b_i,b_j)\ \ge\ D:=4\operatorname{artanh}\sqrt{\tanh(1/a)},
 \qquad \cosh(D/2)=e^{2/a}.
\end{equation}
```

There is also a point $`h`$ in the chosen compact connected set whose intrinsic distance in $`C_t`$ from every root is at least $`1`$. Otherwise the open intrinsic balls of radius $`1`$ about the roots would cover that set. Two balls with distinct centres cannot meet: paths from their centres to a common point would concatenate to length below $`2`$. But a connected set containing two distinct roots cannot be covered by these disjoint open sets. This contradiction proves the assertion. Now choose the Riemann map with $`\varphi(0)=h`$, and continue to write $`b_j=\varphi^{-1}(\zeta_j)`$. Put $`d_j=d(0,b_j)`$ and $`\lambda(d)=-\log\tanh(d/2)`$. The one-root estimate at $`h`$ gives $`\tanh(d_j/2)\ge\sqrt{1-e^{-1/a}}`$. The centre $`h`$ lies on the chosen inverse arcs, so $`0<|f(h)|\le\mu`$; it is not a root because its intrinsic distance from every root is at least $`1`$. The Blaschke identity at $`0`$ gives $`|f(h)|/t=\prod_j|b_j|`$, hence $`\sum_j\lambda(d_j)=\log(t/|f(h)|)\ge\log(t/\mu)=x`$. Together these estimates give
``` math
\begin{equation}
\label{eq:lc-radius-and-budget}
 \lambda(d_j)\le\frac{\delta(a)}2,\quad
 \delta(a)=-\log\bigl(1-e^{-1/a}\bigr),
 \qquad
 \sum_{j=1}^{k}\lambda(d_j)\ \ge\ x .
\end{equation}
```

<a id="a-lower-bound-for-the-number-of-roots."></a>

#### A lower bound for the number of roots.

Testing only consecutive pairs in angular order loses essential information. For $`k=2m`$, put $`m`$ points at hyperbolic radius $`d_{\mathrm{low}}`$ and $`m`$ at radius $`d_{\mathrm{low}}+D`$, alternating in cyclic order. The reverse triangle inequality separates every consecutive pair by at least $`D`$, regardless of the angular gaps, whereas
``` math
\sum_j\lambda(d_j)
 =m\bigl(\lambda(d_{\mathrm{low}})+\lambda(d_{\mathrm{low}}+D)\bigr)
 \longrightarrow\infty\qquad(m\to\infty).
```
The even number of points is needed for cyclic alternation. These point configurations test only the consecutive-pair constraints; they need not satisfy separation for nonconsecutive pairs or arise from a polynomial component. To use the missing pairwise information, we impose the packing bound on every circle centred at the origin.

<div id="res:circle-slice-packing" class="lemma">

**Lemma 6** (circle-slice packing). *Under <a href="#eq:lc-separation" data-reference-type="eqref" data-reference="eq:lc-separation">[eq:lc-separation]</a>, for every $`r>0`$,
``` math
\sum_{j=1}^{k}w(d_j,r)\le\pi,\qquad
 w(d,r)=\arccos\Bigl(\operatorname{clamp}
   \frac{\cosh d\cosh r-\cosh(D/2)}{\sinh d\sinh r}\Bigr),
```
where $`\operatorname{clamp}`$ truncates its argument to $`[-1,1]`$.*

</div>

Lean: [circle slice packing](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L563), [cosh dist polar](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L141), [dist polar i](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L166), [exists polar](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L177), and 2 further declarations in the [coverage section](#sec:coverage).

<div class="proof">

*Proof.* The open balls $`B_j=B_{\mathrm{hyp}}(b_j,D/2)`$ are pairwise disjoint, since a common point would force $`d(b_i,b_j)<D`$. Fix $`r>0`$. By the hyperbolic law of cosines the point of the hyperbolic circle of radius $`r`$ at angle $`\theta`$ lies in $`B_j`$ exactly when $`\cosh d_j\cosh r-\sinh d_j\sinh r\cos(\theta-\theta_j)<\cosh(D/2)`$. The set of angles satisfying this inequality has measure $`2w(d_j,r)`$: clamping gives measure zero for an empty intersection and $`2\pi`$ for a full circle, with tangent endpoint sets of measure zero. The intersections of the balls with this circle are disjoint, so their angular measures sum to at most $`2\pi`$. ◻

</div>

<div id="res:dual-arity-floor" class="theorem">

**Theorem 7** (a lower bound for the number of roots). *Fix radii $`r_1,\ldots,r_p>0`$ and weights $`\sigma_1,\ldots,\sigma_p\ge0`$, put $`\Sigma=\sum_i\sigma_i`$ and
``` math
U=\sup_{d\ge d_{\mathrm{low}}(a)}
   \Bigl[\lambda(d)-\sum_i\sigma_i\,w(d,r_i)\Bigr],
 \qquad
 \lambda\bigl(d_{\mathrm{low}}(a)\bigr)=\frac{\delta(a)}2 .
```
If $`U>0`$, then failure forces $`k\ge(x-\pi\Sigma)/U`$.*

</div>

Lean: [dual arity floor sup](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L594), [dual arity floor](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L579), [le of lam le](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L506), [cosh dist polar](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L141), and 1 further declaration. Conditional on the radius and budget bound that this proof derives from the standing failure hypothesis; see the [coverage section](#sec:coverage).

<div class="proof">

*Proof.* By <a href="#eq:lc-radius-and-budget" data-reference-type="eqref" data-reference="eq:lc-radius-and-budget">[eq:lc-radius-and-budget]</a>, Lemma <a href="#res:circle-slice-packing" data-reference-type="ref" data-reference="res:circle-slice-packing">6</a> and the radius bound,
``` math
x\le\sum_j\lambda(d_j)
  =\sum_j\Bigl[\lambda(d_j)-\sum_i\sigma_i w(d_j,r_i)\Bigr]
    +\sum_i\sigma_i\sum_j w(d_j,r_i)
  \le kU+\pi\Sigma. \qedhere
```
 ◻

</div>

The weighted sum of circle-slice inequalities is a dual certificate: it bounds the contribution of every permitted root configuration without having to optimise over all configurations directly. The weights give a usable bound only when $`\Sigma`$ and the supremum $`U`$ have rigorous bounds. In particular, checking the expression on a finite grid does not bound the supremum between grid points. Zero weights recover only the individual bound $`k\ge2x/\delta(a)`$; nonzero weights incorporate the circle-packing information and can improve the result. A certificate at area $`a'\ge a`$ also applies at $`a`$. Indeed, $`d_{\mathrm{low}}(a)\ge d_{\mathrm{low}}(a')`$, so the admissible range of $`d`$ only shrinks. Also $`D(a)\ge D(a')`$, which enlarges every slice angle $`w(d,r_i)`$ at fixed $`d,r_i`$. Since the weights are nonnegative, the expression defining $`U`$ can only decrease. Thus the same certified pair $`(\Sigma,U)`$ remains valid. The numerical comparison also uses two bounds that do not involve chosen weights. They are useful where the circle-slice certificate is weaker. We derive them here so that every root-count input to the comparison is visible.

<a id="two-further-root-count-bounds."></a>

#### Two further root-count bounds.

Order the distances as $`d_1\le\cdots\le d_k`$. The triangle inequality gives $`d_j\ge D-d_1`$ for $`j\ge2`$. The function $`\lambda`$ is decreasing and convex, since $`\lambda'(d)=-1/\sinh d`$ and $`\lambda''(d)=\cosh d/\sinh^2d>0`$. On $`[d_{\mathrm{low}},D/2]`$, the convex function $`\lambda(d)+(k-1)\lambda(D-d)`$ takes its maximum at an endpoint. If $`d_1\ge D/2`$, each summand is at most $`\lambda(D/2)`$ instead. (The definitions give $`d_{\mathrm{low}}<D/2`$.) Thus
``` math
x\le\sum_j\lambda(d_j)
 \le\max\left\{
  \frac{\delta(a)}2+(k-1)\lambda(D-d_{\mathrm{low}}),\;
  k\lambda(D/2)\right\},
```
and consequently
``` math
k\ge\min\left\{
  1+\frac{x-\delta(a)/2}{\lambda(D-d_{\mathrm{low}})},\;
  \frac{x}{\lambda(D/2)}\right\}.
```
The minimum is essential: the two expressions arise from alternative positions of the nearest root, not from simultaneous restrictions.

For the second bound, integrate over the disjoint hyperbolic balls of radius $`D/2`$. Put $`E=e^{2/a}-1`$, so each ball has hyperbolic area $`2\pi E`$. At most one contains the origin; its contribution to $`\sum_j\lambda(d_j)`$ is at most $`\delta(a)/2`$. On every other ball, $`-\log|z|`$ is harmonic. To average it, first move the ball’s centre to $`0`$ by a disc automorphism. Hyperbolic area is invariant under this change of coordinates and has radial density $`4/(1-|z|^2)^2`$ there. The ordinary mean-value property on each centred Euclidean circle therefore gives hyperbolic area mean $`\lambda(d_j)`$. If the original ball has $`0`$ on its boundary, use increasing smaller concentric balls and monotone convergence.

There are $`m=k-1`$ nonexceptional balls if one contains the origin, and $`m=k`$ otherwise. Their union has area $`2\pi mE`$. Each superlevel set of $`-\log|z|`$ is a centred ball, so its intersection with any set of this area has area at most the smaller of the two areas. The centred ball of area $`2\pi mE`$ attains that upper bound at every superlevel. Integrating these intersection areas over the superlevel parameter therefore bounds the integral over the union by the integral over that centred ball. Its radius $`R`$ satisfies $`\cosh R=1+mE`$. With $`v=\cosh r-1`$, the identity $`-\log\tanh(r/2)=\tfrac12\log(1+2/v)`$ reduces the radial integral to $`(2E)^{-1}\int_0^{mE}\log(1+2/v)\,dv`$. Evaluating it gives
``` math
\frac1{2\pi E}\int_{B_{\mathrm{hyp}}(0,R)}-\log|z|\,dA_{\mathrm{hyp}}
 =\frac{\frac{mE}{2}\log(1+2/(mE))+\log(1+mE/2)}{E}
 \le\frac{1+\log(1+mE/2)}{E},
```
where the improper integral is finite because $`v\log v\to0`$ as $`v\downarrow0`$, and the last inequality uses $`\log(1+u)\le u`$ for $`u>0`$. Adding the possible exceptional contribution and inverting each case yields
``` math
k\ge\min\left\{
  1+\frac2E\bigl(e^{E(x-\delta(a)/2)-1}-1\bigr),\;
  \frac2E\bigl(e^{Ex-1}-1\bigr)\right\}.
```
Again the minimum accounts for the two possible cases. This estimate uses area rearrangement, whereas the preceding one uses only ordered distances; neither replaces the circle-slice inequalities.

The comparison takes the maximum of $`2`$, $`2x/\delta(a)`$, these two bounds, and the certified circle-slice bounds. Each may first be rounded up because $`k`$ is an integer. Any of these estimates derived with an upper bound for $`a`$ remains valid at the actual smaller area: the root configuration still satisfies the weaker separation and radius conditions at that upper bound.

<a id="from-the-root-count-to-an-area-contradiction."></a>

#### From the root count to an area contradiction.

At a direction avoiding the finitely many critical-value arguments, lift the value radius from $`0`$ to $`te^{i\theta}`$ from each of the $`k`$ roots in $`C_t`$ and split each lift at level $`\mu`$. Put $`A_0=\operatorname{Area}(C_t\cap\{|f|<\mu\})`$. This is the sum of the areas of the $`k`$ one-root components inside $`C_t`$, not of all the root components of $`f`$; in particular, $`0\le A_0\le\pi a`$. On each of these components $`f/\mu`$ is conformal, since it is a proper map with no critical point onto a simply connected disc. Take $`\psi(z)=\sum_{\ell\ge0}\gamma_\ell z^\ell`$ to be its inverse, so $`f(\psi(z))=\mu z`$ and $`\psi(0)`$ is the selected root. The radial curves in this coordinate therefore trace exactly the required value-ray lifts. Cauchy–Schwarz in the radial variable and Parseval give
``` math
\operatorname{mean}_\theta
   \Bigl(\int_0^1|\psi'(re^{i\theta})|\,dr\Bigr)^2
 \le\sum_{\ell\ge1}\frac{\ell^2|\gamma_\ell|^2}{2\ell-1}
 \le\sum_{\ell\ge1}\ell|\gamma_\ell|^2
 =\frac{\operatorname{Area}(\text{component})}\pi.
```
First stop the radial integrals short of the unit circle, then pass to the endpoint by monotone convergence. Thus no smoothness of the boundary at level $`\mu`$ is assumed. Summing the $`k`$ square-root area bounds gives a mean total low lift length at most $`\sqrt{kA_0/\pi}`$. At a regular intermediate level $`u`$, let $`A_C(u)`$ be the area of $`C_t\cap\{|f|<u\}`$ and $`P_C(u)`$ its total boundary length. The argument principle and the coarea formula give
``` math
\begin{equation}
\label{eq:lc-perimeter}
 P_C(u)^2\le2\pi k\,u\,A_C'(u),
\end{equation}
```
because $`|dz|=u\,d(\arg f)/|f'|`$ on the level curve, its total argument variation is $`2\pi k`$, and Cauchy–Schwarz applies. Integrating $`P_C(u)/(2\pi u)`$ from $`\mu`$ to $`t`$ bounds the mean high lift length by $`\sqrt{kx(\pi a-A_0)/(2\pi)}`$. Cauchy–Schwarz combines the low and high bounds as
``` math
\sqrt{\frac{kA_0}{\pi}}+
 \sqrt{\frac{kx(\pi a-A_0)}{2\pi}}
 \le\sqrt{ka(1+x/2)}.
```
Choose a direction whose total lift length is at most $`\sqrt{ka(x+2)/2}`$. Order its $`k`$ boundary endpoints cyclically and join each adjacent pair using the two lifts and the intervening boundary arc. Each path lies in $`\overline{C_t}\subset\{|f|<1\}`$ and, under failure, has length at least $`2`$. Each lift occurs twice in the sum of these lengths, while the boundary occurs once. Therefore
``` math
2k\le\sqrt{2ka(x+2)}+P_C(t).
```
Now let $`t=\mu e^x`$ vary, and write $`a(x)=\operatorname{Area}(C_{\mu e^x})/\pi`$ for the component containing the chosen first pair; its root count $`k`$ may increase at later mergers. On a regular interval, $`a'(x)=tA_C'(t)/\pi`$. Applying <a href="#eq:lc-perimeter" data-reference-type="eqref" data-reference="eq:lc-perimeter">[eq:lc-perimeter]</a> at the outer level and rearranging therefore gives
``` math
\begin{equation}
\label{eq:lc-area-growth}
 a'(x)\ \ge\ \frac1{2\pi^2}
 \Bigl[\,2\sqrt k-\sqrt{2a(x)(x+2)}\,\Bigr]_{+}^{2}
\end{equation}
```
on each regular interval for the component containing the selected pair, using the largest of the root-count bounds just derived. At merger levels this component only gains area, which strengthens the integrated comparison. Pólya’s inequality caps $`a`$ at $`1`$ until the level reaches $`1`$, so a trajectory forced past that cap before $`t=1`$ contradicts the assumption.

No positive initial area has to be assumed. While $`a\le1`$, for $`0<x\le3/10^5`$ the bound $`k\ge2`$ alone gives
``` math
a'(x)\ge\frac1{2\pi^2}
 \left(2\sqrt2-\sqrt{2(2+3/10^5)}\right)^2>\frac1{30}
```
at regular levels. For example, the last inequality follows using $`\pi<22/7`$, $`\sqrt2>140/99`$ and $`\sqrt{2(2+3/10^5)}<20001/10000`$. Integration, including the nonnegative merger jumps, gives $`a(3/10^5)>10^{-6}`$. This is the universal starting bound used by the certificate.

The comparison is integrated cell by cell without assuming that the independently certified lower bounds increase with the table index. On a cell $`[x_\ell,x_r]`$, suppose $`a(x_\ell)\ge a_\iota`$ and choose a trial upper bound $`m`$ for the area. Let $`g`$ be a certified lower bound for the right side of <a href="#eq:lc-area-growth" data-reference-type="eqref" data-reference="eq:lc-area-growth">[eq:lc-area-growth]</a> throughout that cell under the trial assumption $`a\le m`$. If $`m<a_\iota+(x_r-x_\ell)g`$, then $`a(x_r)>m`$. Indeed, the contrary assumption $`a(x_r)\le m`$ would imply $`a\le m`$ throughout the cell by monotonicity. Integrating the differential inequality, with the nonnegative merger jumps, would then give $`a(x_r)>m`$, a contradiction.

<a id="certificate."></a>

#### Certificate.

The comparison gives an upper bound $`X`$ on the logarithmic time needed for the forced area to exceed $`1`$. It therefore gives a contradiction whenever $`\mu e^X<1`$. The stated constant $`13/25`$ is a convenient rational choice with room to spare, not an optimality claim. The companion program [`check_erdos1041_angular_budget_closure.py`](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/scripts/check_erdos1041_angular_budget_closure.py) evaluates every accepted inequality in exact rational arithmetic, with directed rounding on the transcendental evaluations. Its fixed rational brackets for $`\pi`$ and $`\log2`$ have different elementary checks: Machin’s identity $`\pi=16\arctan(1/5)-4\arctan(1/239)`$ for the former, and $`\log2=2\sum_{j\ge0}3^{-(2j+1)}/(2j+1)`$ for the latter. Alternating-series bounds and a geometric tail bound, respectively, suffice to verify them. The full replay uses $`18`$ area-table levels, $`14`$ radii in each weighted bound, $`126`$ attempted choices of weights, maximum step $`1/400`$, and the initial lower area $`10^{-6}`$ at $`x=3/10^5`$. Only accepted rational certificates enter the comparison; its early steps may be shorter than $`1/400`$. The recorded full replay certifies
``` math
X=\frac{635762889599}{1000000000000}<0.6357629,
 \qquad \frac{13}{25}e^{X}<1,
```
which gives Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a>. The recorded quick-mode replay gives $`X=664373027131/1000000000000`$ and the weaker threshold $`51/100`$. The floating optimiser proposes weights but supplies no proof. The argument uses only the subsequently certified rational bounds on their sum and on the supremum $`U`$. Each accepted pair supplies a weight sum $`\Sigma`$ and a certified upper bound for the supremum $`U`$ in Theorem <a href="#res:dual-arity-floor" data-reference-type="ref" data-reference="res:dual-arity-floor">7</a>. For orientation, the recorded quick-mode pairs at $`a=1`$, rounded to six decimal places, are $`(0.085674,0.045865)`$, $`(0.126361,0.021829)`$, $`(0.163157,0.010513)`$ and $`(0.208928,0.004318)`$, giving $`kU+\pi\Sigma`$ approximately $`0.4526`$, $`0.5716`$, $`0.6808`$ and $`0.7945`$ at $`k=4,8,16,32`$, respectively. These rounded pairs do not themselves certify an inequality; the comparison uses the unrounded rational values and their directed bounds. To bound the supremum over $`d`$, the checker subdivides intervals and bounds each term in the direction needed for an upper bound. The function $`\lambda`$ is decreasing. For fixed $`r`$, the slice angle $`w(d,r)`$ has no strict interior minimum. Indeed, before clipping the angle to $`0`$ or $`\pi`$, its cosine is
``` math
H(d)=\frac{\cosh d\cosh r-\cosh(D/2)}{\sinh d\sinh r},\qquad
 H'(d)=\frac{\cosh(D/2)\cosh d-\cosh r}{\sinh^2d\sinh r}.
```
The numerator of $`H'`$ is increasing. Thus $`H`$ has at most one interior minimum, and $`w=\arccos H`$ has at most one interior maximum; clipping preserves the endpoint-minimum property. On an interval $`[d_-,d_+]`$, therefore,
``` math
\lambda(d)-\sum_i\sigma_iw(d,r_i)
 \le\lambda(d_-)-\sum_i\sigma_i
       \min\{w(d_-,r_i),w(d_+,r_i)\}.
```
Beyond $`d=\max_i r_i+D/2`$, all the slice angles vanish, so only the decreasing function $`\lambda`$ remains. These are interval bounds, not values sampled on a grid. The closing inequality is independently checkable: with $`X=635762889599/10^{12}`$ and $`e^X\le\sum_{j\le14}X^j/j!+(X^{15}/15!)/(1-X/16)`$, rational arithmetic gives $`(13/25)e^X<0.982000386<1`$. The same majorant also gives
``` math
\frac{529}{1000}e^X<0.998996547<1.
```
Thus the recorded full certificate in fact gives the path conclusion for $`\mu\le529/1000`$, without changing the geometric argument or its hypotheses. This is an arithmetic consequence of the recorded stopping time, not a new certificate replay. We retain $`13/25`$ in the theorem and its scaling corollaries as the simpler constant.

<a id="bdry:low-critical-closure"></a>

#### Sources and scope.

The analytic chain above is ordinary mathematics. Its general inputs are the Riemann mapping theorem, the Bergman kernel, the argument principle, the coarea formula, and Pólya’s area inequality $`\operatorname{Area}\{|f|\le t\}\le\pi t^{2/n}`$ \[polya1928, printed pp. 280–282\], \[crane, Theorem 1\]. The exact rational certificate is checked by a separate exact-arithmetic program, not by the Lean kernel. The two additional root-count bounds above are the ordered-distance estimate in [the earlier distance comparison](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/ClusterSeparationLowCriticalClosure.md) and the area-rearrangement estimate in [the hyperbolic packing argument](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/HyperbolicPackingArityFloor.md). Their derivations above are part of the analytic proof. No complete Lean proof or independent review of this theorem is claimed. The finite summation implication identified in the companion paper assumes the geometric inequalities; it does not formalise the analytic chain or the certificate replay. Prior art for the assembled statement is unassessed. No novelty is claimed for the slice inequality, which follows directly from disjointness of the balls and the hyperbolic law of cosines. The public source of record is [`AngularBudgetLowCriticalClosure.md`](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/AngularBudgetLowCriticalClosure.md), which carries the full analytic argument, the table of certified weighted bounds and the instructions for replaying the certificate. The stopping-time test requires $`\mu<e^{-X}`$; the stated $`13/25`$ theorem and the $`529/1000`$ consequence are two rational cutoffs within that range. Other theorems apply to some polynomials outside it, so failure of this numerical test does not identify the class left untreated by all the results. Fixed-degree arguments remain stronger at $`n=4`$ and $`n=5`$, where the corresponding thresholds are $`61/100`$ and $`139/250`$; from $`n=6`$ on the all-degree constant $`13/25`$ is the better statement. These threshold arguments do not settle the unrestricted root-connector conclusion.

<div id="res:scaled-low-critical-path" class="corollary">

**Corollary 8** (scaled low-critical connection). *Every squarefree monic polynomial $`f`$ of degree $`n\ge2`$ has two distinct zeros joined by a rectifiable curve of length less than $`(5/2)\mu^{1/n}`$ in $`\{|f|<(25/13)\mu\}`$, where $`\mu=\min_{f'(c)=0}|f(c)|`$.*

</div>

Lean: [scaled low critical five halves of low critical](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/LowCriticalScaleTransport.lean#L491). Conditional on Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a> as stated, and only in degrees above two; see the [coverage section](#sec:coverage).

<div class="proof">

*Proof.* For $`n\ge3`$, apply Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a> to $`g(z)=s^{-n}f(sz)`$ with $`s=((25/13)\mu)^{1/n}`$. Its least critical modulus is $`13/25`$; rescaling gives length less than $`2(25/13)^{1/n}\mu^{1/n}<(5/2)\mu^{1/n}`$, since $`25/13<(5/4)^3`$. For $`n=2`$, write $`f(z)=(z-h)^2-d^2`$. The two radial segments through $`h`$ have total length $`2|d|=2\mu^{1/2}`$ and lie in the closed level $`\mu`$, which is inside the stated open level. ◻

</div>

The next section gives a different construction whose estimates retain the root count and capacity of the chosen component.

<a id="sec:constant-factor"></a>

# A path estimate from area and boundary length

Corollary <a href="#res:scaled-low-critical-path" data-reference-type="ref" data-reference="res:scaled-low-critical-path">8</a> has both a smaller length constant and a smaller containment level than the next theorem: $`5/2<71/10`$ and $`25/13<2`$. The independent area argument below is useful for a different reason: it keeps the root count and component capacity in the length estimate. Its $`\mu\le1/2`$ corollaries illustrate that geometric dependence; their ranges are already covered by Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a>. For a monic degree-$`n`$ polynomial put
``` math
K_t=\{z:|f(z)|\le t\},\qquad
 \mu=\min_{f'(c)=0}|f(c)|,\qquad \rho=\mu^{1/n}.
```

<div id="res:constant-factor-path" class="theorem">

**Theorem 9** (a uniform path bound at level $`2\mu`$). *For every monic polynomial $`f`$ of degree $`n\ge2`$, two zero occurrences are joined by a possibly degenerate path of length at most
``` math
\frac{71}{10}\,\rho
```
inside $`K_{2\mu}`$. If $`f`$ is squarefree, their locations are distinct. If $`\mu\le1/2`$, the construction may be chosen inside $`\{|f|<1\}`$ with length at most $`5.7`$.*

</div>

Lean: [cfa constant factor path](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L677), [cfa bracket two three twentieths lt](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L355), [cfa bracket five point seven](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L393), [cfa degenerate](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L313), and 3 further declarations. Conditional on the level and direction averaging construction that this proof produces; see the [coverage section](#sec:coverage).

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
For $`n\ge3`$, the choice $`\lambda=2`$, $`r=3/20`$ makes the bracket less than $`71/10`$: the largest case is $`n=3`$, where exact rational bounds give $`66517563/9392500<71/10`$. Degree two has the exact root-segment bound $`2\rho`$.

<div class="proof">

*Proof.* A repeated zero gives the constant path, so assume $`f`$ is squarefree and $`\mu>0`$. Degree two is the segment of length $`2\rho`$ in $`K_\mu`$; assume $`n\ge3`$. Put $`T=\lambda\mu`$, let $`C_T`$ be the component of $`K_T`$ containing a critical point at level $`\mu`$, and write $`A(\sigma)=\operatorname{Area}(K_\sigma\cap C_T)`$. We will first choose a regular level $`t`$, then a direction in the value plane, and finally an adjacent pair of roots. This order ensures that the three estimates below apply to the same path.

At a regular level $`\sigma`$, a component $`C'`$ containing $`k'`$ roots has $`|dz|=\sigma\,d\varphi/|f'|`$ on its boundary and total argument variation $`2\pi k'`$. Cauchy–Schwarz, followed by the coarea formula, gives
``` math
\mathcal H^1(\partial C')^2\le2\pi k'\,\sigma A'(\sigma).
                                                        \tag{CF1}
```
Here $`A'`$ sums the area derivatives of all the components in $`C_T`$, so it bounds the contribution from $`C'`$. Pólya’s inequality $`A(T)\le\pi T^{2/n}`$ \[crane, Theorem 1\] and averaging with respect to $`d\sigma/\sigma`$ on $`(\mu,T)`$ give a regular level $`t`$ such that $`tA'(t)\le\pi T^{2/n}/\log\lambda`$. The component $`C_t`$ containing the chosen first merger has $`k\ge2`$ roots and
``` math
\mathcal H^1(\partial C_t)
 \le\pi\sqrt{2k/\log\lambda}\,T^{1/n}.
```
Averaging over levels avoids estimating the area derivative at the critical level itself.

Choose a direction avoiding all critical-value arguments. Lift its radial segment from each of the $`k`$ roots to $`\partial C_t`$, splitting each lift at value modulus $`r\mu`$. Below $`\mu`$, the inverse branches of $`f/\mu`$ are univalent. Their derivatives at $`0`$ are $`\mu/f'(z_i)`$, where $`z_i`$ ranges over the roots. The area formula for their disjoint images gives
``` math
\sum_i\frac{\mu^2}{|f'(z_i)|^2}\le\rho^2.        \tag{CF2}
```
Indeed, the squared derivative at the centre is at most the image area divided by $`\pi`$, and the total image area is at most $`\pi\mu^{2/n}`$. Koebe distortion and Cauchy–Schwarz therefore bound the sum of the lengths below $`r\mu`$, uniformly in the direction. Write $`\ell_i^{\rm high}(\theta)`$ for the length of the $`i`$th piece above $`r\mu`$ in direction $`\theta`$. At an intermediate regular level, apply (CF1) to all the lower components contained in $`C_t`$; their root counts sum to $`k`$. Integrating their total perimeter with measure $`d\sigma/(2\pi\sigma)`$ gives the mean of $`\sum_i\ell_i^{\rm high}`$. Cauchy–Schwarz in $`\sigma`$, using an area increment at most $`\operatorname{Area}(C_t)\le\pi T^{2/n}`$, gives
``` math
\frac1{2\pi}\int_0^{2\pi}\sum_i\ell_i^{\rm high}(\theta)\,d\theta
 \le\sqrt{\frac{k\operatorname{Area}(C_t)}{2\pi}
                   \log\frac{t}{r\mu}}
 \le\sqrt{\frac k2}\,T^{1/n}\sqrt{\log(\lambda/r)}.
```
Choose a direction avoiding the critical-value arguments at which the sum is at most this bound. The excluded directions form a finite set and hence have measure zero.

Order its $`k`$ endpoints cyclically on $`\partial C_t`$. Each adjacent pair of endpoints gives a path consisting of two lifted segments and the intervening boundary arc. In the sum over these $`k`$ paths, every lifted segment occurs twice and the boundary arcs partition $`\partial C_t`$. Thus some pair has length at most the sum of the following three bounds:
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
The first holds in every direction, the second in the direction just chosen, and the third at the previously selected level. Substituting $`T^{1/n}=\lambda^{1/n}\rho`$ proves (CF). For the final assertion, the repeated-zero case is already a constant path, and in degree two the root segment has length $`2\rho=2\sqrt\mu\le\sqrt2`$. For $`n\ge3`$, take $`\lambda=2`$ and $`r=3/20`$. Since $`k\ge2`$ and $`\mu\le1/2`$, (CF) gives
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

The bracket (CF) retains two quantities that the constant $`71/10`$ discards, namely the root count $`k`$ of the selected component through the factor $`\sqrt{2/k}`$, and the capacity of that component through the area input. Keeping either one turns the constant-factor theorem into the target conclusion on an explicit region.

The number of roots in the first merged component can be much smaller than the degree. At a first merger caused by one simple critical point it is $`2`$, so the following thresholds do not apply. For $`z^n-b`$, however, all $`n`$ roots merge at the same level, giving $`k_0=n`$. For example, $`n\ge17`$ and $`0<|b|\le1/2`$ satisfy the first pair of hypotheses. These conditions illustrate what the area argument gains from simultaneous mergers; the preceding $`13/25`$ theorem already covers these three ranges without requiring a large root count.

<div id="res:constant-factor-arity" class="corollary">

**Corollary 10** (a criterion using the number of roots at the first merger). *Let $`f`$ be monic with every root in the open unit disc, let $`c_*`$ be a critical point with $`|f(c_*)|=\mu`$, and let $`k_0`$ be the number of roots, counted with multiplicity, in the component of $`K_\mu`$ containing $`c_*`$. Then Erdős #1041 holds for $`f`$ in each of the three cases
``` math
\mu\le\tfrac12\ \text{and}\ k_0\ge17,\qquad
 \mu\le\tfrac14\ \text{and}\ k_0\ge12,\qquad
 \mu\le\tfrac18\ \text{and}\ k_0\ge10 .
```*

</div>

Lean: [cfa arity criterion](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L765), [cfa arity bracket case one](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L440), [cfa arity bracket case two](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L455), [cfa arity bracket case three](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L470), and 2 further declarations. Conditional on the level and direction averaging construction in the proof of Theorem <a href="#res:constant-factor-path" data-reference-type="ref" data-reference="res:constant-factor-path">9</a>; see the [coverage section](#sec:coverage).

<div class="proof">

*Proof.* If $`\mu=0`$, a repeated zero gives the constant path. Assume henceforth $`\mu>0`$. Every selected component $`C_t`$ in the proof of Theorem <a href="#res:constant-factor-path" data-reference-type="ref" data-reference="res:constant-factor-path">9</a> contains the first-merge component, so $`k\ge k_0`$. For the first case take $`\lambda=2`$, $`r=13/100`$; then $`(2\mu)^{1/n}\le1`$ and $`\rho\le1`$, and the exact bounds $`\sqrt2<283/200`$, $`\sqrt{\log(200/13)}<5/3`$ and $`\pi/\sqrt{\log2}<(22/7)/(104/125)=1375/364`$ make the bracket in (CF) at most $`15668813/2755116`$, whose square is $`34-12570881068535/7590664173456<34`$. Hence $`k_0\ge17`$ gives squared length below $`(2/17)\cdot34=4`$. For the second case take $`\lambda=4`$, $`r=3/25`$: the bracket is below $`6075221/1273888`$, whose square is $`24-2038665078215/1622790636544<24`$, and $`2/k_0\le1/6`$ gives squared length below $`4`$. For the third take $`\lambda=8`$, $`r=11/100`$: the bracket is below $`55629121/12475575`$, whose square is $`20-18200328379859/155639971580625<20`$, and $`2/k_0\le1/5`$ again gives squared length below $`4`$. In each case $`\lambda\mu\le1`$, so the freedom in the choice of the regular level $`t`$ keeps $`t<1`$ and the containment strict. ◻

</div>

The next criterion uses logarithmic capacity, a measure of the size of a compact set that scales linearly under dilation. It compares the size of one component with that of the entire polynomial sublevel set. If that sublevel set is connected, the ratio $`\kappa`$ below is $`1`$; a cutoff such as $`\kappa\le1/3`$ therefore requires a genuinely smaller component. This is additional geometric information, not a consequence of a small number of roots in the component. The ratio requires $`\mu>0`$. When $`\mu=0`$, $`f`$ has a repeated zero and the constant path already gives the conclusion; there is no capacity ratio to evaluate.

<div id="res:constant-factor-capacity" class="corollary">

**Corollary 11** (a criterion using component capacity). *Keep the hypotheses of Corollary <a href="#res:constant-factor-arity" data-reference-type="ref" data-reference="res:constant-factor-arity">10</a> with $`0<\mu\le1/2`$, let $`C`$ be the component of $`\{|f|<2\mu\}`$ containing $`c_*`$, and put $`\kappa=\operatorname{cap}(\overline C)/(2\mu)^{1/n}`$. If $`\kappa\le\tau_{k_0}`$, where
``` math
\tau_k=\frac{\sqrt{2k}-A}{B},\qquad
 A=\frac{283}{3610},\qquad B=\frac{52029}{9100},
```
then Erdős #1041 holds for $`f`$. In particular $`\kappa\le1/3`$ suffices for every root count $`k_0\ge2`$, and the rational cutoffs $`2/5,\,12/25,\,1/2,\,7/12,\,16/25,\,2/3,\,7/10`$ suffice at $`k_0=3,\ldots,9`$, rising to $`39/40`$ at $`k_0=16`$.*

</div>

Lean: [cfa capacity criterion](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L538), [cfa tau third](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L583), [cfa tau cutoffs](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L591), [cfa tau ge of sq](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/ConstantFactorAreaCriteria.lean#L572), and 2 further declarations. Conditional on the level and direction averaging construction in the proof of Theorem <a href="#res:constant-factor-path" data-reference-type="ref" data-reference="res:constant-factor-path">9</a>, together with the area-capacity inequality; see the [coverage section](#sec:coverage).

<div class="proof">

*Proof.* Repeat the averaging proof of Theorem <a href="#res:constant-factor-path" data-reference-type="ref" data-reference="res:constant-factor-path">9</a> with $`A(\sigma)=\operatorname{Area}(K_\sigma\cap C)`$ for $`\sigma<2\mu`$. This keeps the chosen paths in the open component $`C`$, even if distinct components have touching boundaries at level $`2\mu`$. Replace the global area input by the component form $`\operatorname{Area}(C)\le\pi\operatorname{cap}(\overline C)^2
 =\pi\kappa^2(2\mu)^{2/n}`$ of the area–capacity inequality \[crane, Theorem 6\]. Only the high-lift and boundary terms acquire the factor $`\kappa`$; the low-lift term (CF2) is unchanged. Taking $`\lambda=2`$, $`r=1/20`$, and the exact bounds above together with $`\log40<12641/3402<(97/50)^2`$, gives $`\operatorname{length}<\sqrt{2/k_0}\,(A+B\kappa)`$. The definition of $`\tau_{k_0}`$ makes the right side at most $`2`$, and for each displayed rational $`q_k`$ integer arithmetic gives $`(A+Bq_k)^2<2k`$. Discarding $`\sqrt{2/k_0}\le1`$ altogether gives the uniform cutoff $`\kappa\le1/3`$. ◻

</div>

By the component-capacity formula, $`\kappa=e^{-\Sigma/n}`$ with $`\Sigma`$ the sum of exterior Green function values at the roots excluded from $`C`$. Indeed, let $`\Omega`$ be the unbounded component of $`\widehat{\mathbb C}\mathbin{\backslash}\overline C`$, let $`G`$ be its Green function with pole at infinity, extended by zero off $`\Omega`$, and let $`g(\cdot,a)`$ be its Green function with pole at $`a\in\Omega`$. The function $`\frac1n\log\frac{|f|}{2\mu}-G+\frac1n\sum_a g(\cdot,a)`$, summed over the roots $`a\in\Omega`$ with multiplicity, extends harmonically to $`\Omega`$, is bounded, and vanishes on $`\partial\Omega\subseteq\partial C`$, so it vanishes identically; its value at infinity is $`\log\kappa+\frac1n\sum_aG(a)`$ by the symmetry $`g(\infty,a)=G(a)`$. Failure of these component-sensitive criteria alone, in the range $`\mu\le1/2`$, forces $`k_0\le16`$ and exterior Green sum $`\Sigma<n\log(40/39)`$ when $`k_0=16`$. This is a limitation of the area-based criteria. The low-critical theorem already excludes an actual counterexample throughout that range.

The proof of Theorem <a href="#res:constant-factor-path" data-reference-type="ref" data-reference="res:constant-factor-path">9</a> averages over levels in $`[\mu,\lambda\mu]`$. To keep the path at the first critical level instead, one would need a perimeter estimate of the following kind. The regular-level argument (CF1) gives no finite pointwise bound at the critical level: even at a simple critical point, the area derivative diverges logarithmically.

The addendum \[revision2026, Proposition 2\] reports a Runge-approximation construction of monic level-one components with one simple zero and arbitrarily long analytic boundaries. It imposes neither a unit root disc nor a global lower bound on critical-value moduli. That proof was not supplied or available for checking in this revision; the report is not an input to the path estimates here. The question below requires a stronger hypothesis than the existence of one unramified component: the level must lie below every critical-value modulus of the polynomial. A construction without that global condition cannot by itself answer the question.

<div id="prob:conjecture-p" class="problem">

**Problem 12** (perimeter below the smallest critical-value modulus). Let $`f`$ be squarefree and monic of degree $`n\ge2`$, and put $`\mu=\min_{f'(c)=0}|f(c)|`$. Is there a constant $`\beta`$, independent of $`n,f`$ and $`0<\sigma<\mu`$, such that every component $`C`$ of $`\{|f|\le\sigma\}`$ satisfies
``` math
\mathcal H^1(\partial C)\le\beta\sigma^{1/n}?
```
Equivalently, for each univalent inverse branch defined on $`\mathbb D`$ by $`f(\phi_j(w))=\sigma w`$, is
``` math
\int_0^{2\pi}|\phi_j'(e^{it})|\,dt\le\beta\sigma^{1/n}
 \qquad(1\le j\le n)?
```
There is no root-location hypothesis. If such constants exist, write $`\beta_*`$ for their infimum.

</div>

All these components contain one zero. The condition $`\sigma<\mu`$ controls all inverse branches at once; it is stronger than requiring only the selected component to contain one zero. The examples below compare particular constants, not the necessity of this global hypothesis for every possible perimeter bound. For $`1<R<\mu/\sigma`$, the area estimate gives
``` math
\frac{1}{2\pi}\int_0^{2\pi}|\phi_j'(e^{it})|\,dt
 \le \frac{(\sigma R)^{1/n}}{\sqrt{R^2-1}}.
```
Indeed, circular means of $`|\phi_j'|^2`$ increase, the image of the annulus $`1<|w|<R`$ has area at least $`\pi(R^2-1)`$ times the mean at $`1`$, and Pólya’s preimage-area bound \[crane, Theorem 1\] bounds that area by $`\pi(\sigma R)^{2/n}`$. The loss as $`R\downarrow1`$ belongs to this argument and does not prove an endpoint divergence.

For $`d>0`$ and $`f(z)=z^2-d^2`$, one has $`\mu=d^2`$ and $`\rho=d`$. For $`\sigma<d^2`$ the component of $`\{|f|\le\sigma\}`$ around $`d`$ contains one root. Its parametrisations $`d\sqrt{1+(\sigma/d^2)e^{i\theta}}`$ converge uniformly, as $`\sigma\uparrow d^2`$, to one loop of Bernoulli’s lemniscate $`|z^2-d^2|=d^2`$, of length $`d\,\Gamma(1/4)^2/(2\sqrt\pi)`$ by the substitution $`\varphi(w)=d\sqrt{1+w}`$ and $`\Gamma(1/4)\Gamma(3/4)=\pi\sqrt2`$. At $`\sigma=d^2`$ the two loops meet at the critical point, and the closed sublevel set is a single component containing both roots. Lower semicontinuity of length under the stated uniform convergence gives $`\beta_*\ge\Gamma(1/4)^2/(2\sqrt\pi)=3.70814935\ldots`$; convergence of the lengths themselves is not required. For $`z^n-r^n`$, polar parametrisation of one limiting loop gives its length divided by $`r`$ as
``` math
\frac{2^{1/n}}{n}\int_{-\pi/2}^{\pi/2}
     (\cos\theta)^{1/n-1}\,d\theta
 =\frac{2^{1/n}}{n}\sqrt\pi\,
     \frac{\Gamma(1/(2n))}{\Gamma(1/(2n)+1/2)}.
```
The evaluation is Euler’s beta integral [(5.12.1)](https://dlmf.nist.gov/5.12.E1), in its [trigonometric form (5.12.2)](https://dlmf.nist.gov/5.12.E2). To verify the claimed decrease with $`n`$, put $`p=1/n`$. The expression is $`2^{p+1}\sqrt\pi\,\Gamma(1+p/2)/\Gamma((1+p)/2)`$; its logarithmic derivative is
``` math
\log2+\tfrac12\left(
    \frac{\Gamma'(1+p/2)}{\Gamma(1+p/2)}-
    \frac{\Gamma'((1+p)/2)}{\Gamma((1+p)/2)}\right)>0.
```
Here $`\Gamma'/\Gamma`$ is increasing on the positive real axis, by the positive trigamma series [(5.15.1)](https://dlmf.nist.gov/5.15.E1). The expression therefore decreases with $`n`$ and tends to $`2`$.

The comparison with the next example also has an elementary bound, independent of rounded gamma values. One loop of $`z^2-d^2`$ has parametrisation
``` math
z(s)=\sqrt2\,d\,
   \frac{\cos s(1+i\sin s)}{1+\sin^2s},
 \qquad -\pi/2\le s\le\pi/2,
```
whose speed is $`\sqrt2\,d/\sqrt{1+\sin^2s}`$. Convexity puts $`(1+x)^{-1/2}`$ below its secant on $`[0,1]`$. Integrating that secant at $`x=\sin^2s`$ bounds the loop length divided by $`d`$ by $`(\pi/2)(1+\sqrt2)`$, as used below.

The quadratic loop is exceeded in degree eight, even with the global subcritical hypothesis. For $`p(z)=z^8-(3/2)z`$, every critical point $`c`$ satisfies $`c^7=3/16`$ and $`p(c)=-(21/16)c`$. Hence
``` math
\mu=\frac{21}{16}\left(\frac3{16}\right)^{1/7}>1,
 \qquad \mu^7=\frac{3\cdot21^7}{16^8}>1.
```
Thus $`\sigma=1`$ is below every critical-value modulus, not merely a regular level for the selected component. The component $`C`$ of $`\{|p|\le1\}`$ containing the origin lies in $`\{|z|<4/5\}`$, because $`|p(z)|\ge6/5-(4/5)^8>1`$ on $`|z|=4/5`$, and it contains a neighbourhood of the closed disc of radius $`5/8`$, because $`|p(z)|\le(5/8)^8+15/16<1`$ on that disc. The other roots satisfy $`|z|^7=3/2`$, so $`C`$ contains exactly one root, and $`\mathcal H^1(\partial C)>5\pi/4>(\pi/2)(1+\sqrt2)\ge\Gamma(1/4)^2/(2\sqrt\pi)`$. Moreover, for fixed $`a>1`$ and all sufficiently large $`N`$, the one-root component of $`\{|z^N-az|\le1\}`$ contains every disc of radius $`r<1/a`$, and a circle of radius between $`1/a`$ and $`1`$ isolates it by Rouché’s theorem; letting $`a\downarrow1`$ shows that every admissible $`\beta`$ is at least $`2\pi`$. For the latter family all critical values have modulus $`(1-1/N)a(a/N)^{1/(N-1)}\to a>1`$, so it also gives the necessary bound $`\beta_*\ge2\pi`$ under the corrected global subcritical hypothesis. Kuznetsova–Tkachev \[kuznetsova2003, Theorems 1–2\] establish Laplace-transform and log-convexity properties for regular level-length functions. Those results do not provide a uniform bound at the first critical level. Total lemniscate length and one-branch endpoint length are different extremal quantities.

The preceding examples do not establish a universal perimeter bound. The implication below applies to an individual polynomial; a constant $`\beta`$ independent of the polynomial and degree would give a uniform path bound. The construction uses two components meeting at a first critical point and joins each root to that point at a cost of at most half its component’s perimeter. It does not give the constant $`2`$ of the historical question.

<div id="res:conjecture-p-consumer" class="theorem">

**Theorem 13** (a path from a subcritical perimeter bound). *Let $`f`$ be squarefree and monic of degree $`n\ge2`$, and put $`\mu=\min_{f'(c)=0}|f(c)|>0`$. Suppose $`\beta>0`$ satisfies
``` math
\mathcal H^1(\partial C)\le\beta\sigma^{1/n}
```
for every $`0<\sigma<\mu`$ and every component $`C`$ of $`\{|f|\le\sigma\}`$. Then two distinct roots of $`f`$ are joined inside $`K_\mu=\{|f|\le\mu\}`$ by a rectifiable path of length at most $`\beta\mu^{1/n}`$.*

</div>

Lean: [subcritical perimeter path paper](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/SubcriticalPerimeterPath.lean#L265), [subcritical perimeter path](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/SubcriticalPerimeterPath.lean#L245), [connected at most half perimeter](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/SubcriticalPerimeterPath.lean#L203), [half perimeter join of jordan arc datum](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/SubcriticalPerimeterPath.lean#L216), and 4 further declarations. Conditional on the two-component split at the first critical level that this proof constructs; see the [coverage section](#sec:coverage).

<div class="proof">

*Proof.*

<div id="perimeter-to-path">

</div>

Put $`\rho=\mu^{1/n}`$. On each component of $`\{|f|<\mu\}`$, $`f`$ is a proper unramified covering of the disc $`\{|w|<\mu\}`$, hence univalent. Equivalently, exhaust by regular levels below $`\mu`$ and apply the component count \[eks2010, proof of Proposition 2.1\]. At a critical point $`c_*`$ with $`|f(c_*)|=\mu`$, the local degree $`d\ge2`$ gives $`d`$ nearby preimages of an inward radial value. Univalence places them in different one-root components. Choose two such components $`U_a,U_b`$, containing roots $`a,b`$ and with $`c_*`$ in both closures; simplicity of $`c_*`$ is unnecessary. For the boundary passage, take $`f(\phi(w))=\mu w`$ on $`\mathbb D`$. Fix $`|w_0|=1`$. The finitely many preimages of $`\mu w_0`$ have disjoint neighbourhoods. Properness of $`f`$ and connectedness of a sufficiently small disc cap force $`\phi`$ to stay in one of them as $`w\to w_0`$. At its preimage $`c`$, write
``` math
f(z)-f(c)=(z-c)^d h(z),\qquad h(c)\ne0.
```
A local analytic $`d`$th root of $`h`$ makes $`(z-c)h(z)^{1/d}`$ a conformal coordinate. In each inverse sector, $`\phi`$ is therefore an analytic function of $`(w-w_0)^{1/d}`$ and extends continuously to $`c`$. The finitely many critical boundary values are the only exceptional points; at every other boundary value the ordinary inverse function theorem applies. Moreover, near $`e^{i\theta_0}=w_0`$ the boundary speed is $`O(|\theta-\theta_0|^{1/d-1})`$, which is integrable even when $`d>2`$. Thus the extension is continuous on the closed disc and its boundary curve is rectifiable. The identity $`f(\phi(e^{i\theta}))=\mu e^{i\theta}`$ makes the boundary values injective, so the curve is Jordan.

As $`r\uparrow1`$, the curves $`\phi(re^{i\theta})`$ converge uniformly to that boundary and have length at most $`\beta(\mu r)^{1/n}`$ by the hypothesis. Lower semicontinuity of length gives boundary length at most $`\beta\rho`$ for each component.

A bounded rectifiable Jordan domain $`U`$ has the following elementary property: any $`a\in U`$ can be joined to any $`c\in\partial U`$ in $`\overline U`$ with length at most $`\mathcal H^1(\partial U)/2`$. Choose a line through $`a`$ but not $`c`$, and let $`[u,v]`$ be the closure of the connected interval in its intersection with $`U`$ containing $`a`$. Of the two boundary arcs from $`u`$ to $`v`$, write $`A`$ for the one containing $`c`$ and $`A'`$ for the other. The paths from $`a`$ through $`u`$ or $`v`$ and then along $`A`$ to $`c`$ have total length
``` math
|a-u|+|a-v|+\operatorname{length}(A)
 =|u-v|+\operatorname{length}(A)
 \le\mathcal H^1(\partial U),
```
because $`|u-v|\le\operatorname{length}(A')`$. One path is at most half this sum. The connected interval ensures containment of the straight parts even when $`U`$ is not convex.

Apply this property in $`U_a,U_b`$ with common boundary point $`c_*`$. Concatenating the two paths gives length at most $`\tfrac12(\mathcal H^1(\partial U_a)+\mathcal H^1(\partial U_b))
\le\beta\rho`$, as required. Only these two component perimeters are used; the subcritical hypothesis bounds them by the limiting argument above. Boundary arcs are allowed, so containment is in $`K_\mu`$, not the open sublevel. ◻

</div>

<a id="bdry:constant-factor"></a>

#### Sources and scope.

Theorem <a href="#res:constant-factor-path" data-reference-type="ref" data-reference="res:constant-factor-path">9</a> is ordinary mathematics. Its degenerate case $`\mu=0`$, its degree-two case and every numerical constant in its statement are checked in Lean; the analytic construction for degree at least three is used there as a hypothesis (Section <a href="#sec:coverage" data-reference-type="ref" data-reference="sec:coverage">[sec:coverage]</a>). The inputs of that construction are the capacity identity for polynomial preimages \[crane, §2\], Pólya’s area inequality \[crane, Theorem 1\], Cauchy–Schwarz, the Koebe distortion theorem for univalent maps, and averaging over adjacent boundary endpoints. The public source of record is [the full area and boundary-length argument](https://github.com/wcook04/plectis-erdos/blob/f214a6b45528dc5eefe20ffadc35f2e981627d4c/research_corpus/Erdos1041/UnconditionalConstantFactorBound.md), which carries every rational verification quoted above. Its Section 10 gives a weaker conditional bound involving an auxiliary parameter and a logarithm; Theorem <a href="#res:conjecture-p-consumer" data-reference-type="ref" data-reference="res:conjecture-p-consumer">13</a> states the stronger $`\beta\rho`$ consequence proved here. That section’s proposed numerical perimeter constant is refuted by the degree-eight example above and is not assumed in the theorem. The unconditional construction retains level $`2\mu`$ and constant $`71/10`$. The scaled low-critical corollary has both a smaller constant and a smaller level. The proof retained here is ordinary, with component-sensitive consequences on their stated regions; its rational cutoffs are exact integer inequalities. The earlier perimeter samples concerned only a selected component. They do not test the stronger condition that the level lie below every critical value. The sharp root-connector conclusion is not established for the unrestricted class by the arguments in this record. The adjacent classical literature on lemniscate length concerns the arclength of the level curve $`\{|p|=1\}`$, which is Erdős #114. Fryntov and Nazarov recall its history \[fryntovnazarov2008, Introduction\]: Dolzhenko’s bound $`4\pi n`$, Pommerenke’s bound $`74n^2`$ of 1961, and Borwein’s bound $`8\pi en`$ \[borwein1995\]. Eremenko and Hayman proved $`9.173n`$ \[eremenkohayman1999, Theorem 1\], Fryntov and Nazarov the asymptotically sharp $`2n+o(n)`$ \[fryntovnazarov2008\], and Tao resolved the problem for large $`n`$ \[tao2025\]. These results bound the length of a level curve, not the least internal root-pair path. This distinction identifies the quantity being estimated; no claim of novelty follows from the scope or outcome of a literature search.

<a id="sec:degree-three"></a>

# Degree three

<div id="res:degree-three" class="theorem">

**Theorem 14** (the cubic case). *Let $`f(z)=\prod_{j=1}^{3}(z-z_j)`$ with $`|z_j|<1`$, the roots listed with multiplicity. Then two listed root occurrences are joined inside $`\{|f|<1\}`$ by a polygonal path of length strictly below $`2`$. If $`f`$ is squarefree the two are distinct.*

</div>

Lean: [cubic paper complete](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCubicCompletion.lean#L297).

<div class="proof">

*Proof.* Multiple roots give a constant path, so assume $`f`$ squarefree. The Erdős–Herzog–Piranian component lemma \[ehp1958, remark before Problem 5, p. 139\] gives a component of $`\{|f|<1\}`$ containing two roots. Join them by a compact path in that open component, and choose a regular value modulus $`t<1`$ larger than $`\max|f|`$ on the path. The component of $`\{|f|<t\}`$ containing it has $`k\ge2`$ roots and hence $`k-1\ge1`$ critical points, by the component-wise Riemann–Hurwitz count in the proof of \[eks2010, Proposition 2.1\]. One of these critical points has value of modulus below $`t<1`$. This choice of $`t`$ avoids assuming that the level $`|f|=1`$ is regular.

Suppose first that $`f'`$ has two distinct zeros. Choose a critical point $`c`$ minimising $`|f(c)|`$, write the other one as $`c+\delta`$, and put $`v=f(c)`$, so $`0<|v|<1`$. Monicity gives the exact expansion $`f(c+d)=d^3-\tfrac32\delta d^2+v`$. Choose $`\alpha`$ with $`\alpha^3=v`$ and set $`b=\delta/\alpha`$; dividing by $`v`$ gives $`f(c+\alpha w)/v=P_b(w)`$ with
``` math
P_b(w)=w^3-\tfrac32bw^2+1 .
```
At the other critical point $`f(c+\delta)=v(1-b^3/2)`$, so minimality of $`|v|`$ is exactly the hypothesis $`|1-b^3/2|\ge1`$.

Under that hypothesis $`P_b`$ has at least two zeros, with multiplicity, in the closed unit disc. In the strict region a unit-circle zero $`w`$ would give $`b=\tfrac23(w+w^{-2})`$. Write $`w^3=e^{2iu}`$; substitution gives
``` math
|1-b^3/2|^2
 =1+\frac{64}{729}\cos^4u\,(16\cos^2u-27)\le1.
```
Since $`16\cos^2u-27<0`$, equality requires $`\cos u=0`$, which gives $`b=0`$. Thus the strict region has no unit-circle zero. The radial deformation $`b\mapsto sb`$, $`s\ge1`$, stays in the strict region, since $`z=b^3/2`$ and $`|1-z|^2>1`$ give $`|1-s^3z|^2-1=s^3(s^3|z|^2-2\Re z)>0`$. For large $`s`$, Rouché’s theorem on $`|w|=1`$ compares $`P_{sb}`$ with $`-\tfrac32sbw^2`$, whose modulus $`\tfrac32s|b|`$ exceeds $`2\ge|w^3+1|`$, so $`P_{sb}`$ has exactly two zeros in the open unit disc; no zero crosses the circle along the deformation. For the equality case with $`b\ne0`$, the same radial deformation lies in the strict region for every $`s>1`$, and continuity of the root multiset allows $`s\downarrow1`$. If $`b=0`$, then $`P_b(w)=w^3+1`$ and all three roots lie on the unit circle.

If $`P_b(w)=0`$ and $`0\le t\le1`$, then $`P_b(tw)=1-t^2-t^2(1-t)w^3`$, so $`|w|\le1`$ gives $`|P_b(tw)|\le(1-t^2)+t^2(1-t)|w|^3\le1-t^3\le1`$. The whole segment from $`0`$ to $`w`$ therefore lies in the closed unit sublevel set. Selecting two normalized roots $`w_1,w_2`$ with $`|w_i|\le1`$, the two segments from $`c`$ to $`c+\alpha w_i`$ lie in $`\{|f|\le|v|\}\subset\{|f|<1\}`$ and have combined length at most $`2|\alpha|=2|v|^{1/3}<2`$.

If instead $`f'`$ has a double zero $`c`$, then $`f(c+d)=d^3+v`$. With $`\alpha^3=-v`$ and $`\omega=e^{2\pi i/3}`$, its roots are $`c+\alpha`$, $`c+\alpha\omega`$, $`c+\alpha\omega^2`$. Averaging their squared moduli gives $`|c|^2+|\alpha|^2<1`$, so $`|\alpha|<1`$; any two radial spokes have total length $`2|\alpha|<2`$, and along either spoke the value has modulus $`|v|(1-t^3)<1`$ away from the root endpoint. ◻

</div>

The unit level need not be regular, even when all roots lie in the open unit disc. For example, $`Q(z)=(z-1)(z+1)(z+9/10)`$ has $`Q(1/3)=-148/135<-1`$. Its minimum $`v`$ on $`[-9/10,1]`$ occurs at an interior critical point and satisfies $`v<-1`$. Set $`r=|v|^{-1/3}<1`$. The monic cubic $`r^3Q(z/r)`$ has the three distinct roots $`-r,-9r/10,r`$ in the open unit disc and a critical value equal to $`-1`$. Its unit level is therefore singular, although the cubic path theorem applies.

[A formal-source implementation includes the polygonal path, strict variation bound and repeated-root case; its recorded build status is stated below.](https://github.com/wcook04/plectis-erdos/blob/bb4e24651b37cd096d3749ef299c3317930b3a3b/ErdosProblems/Erdos1041/PaperCubicCompletion.lean#L297)

<a id="bdry:degree-three"></a>

#### Sources and scope.

The source snapshot contains [the complete degree-three path implementation](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperCubicCompletion.lean#L297) and its supporting cubic source. This earlier implementation lies outside the main repository’s recorded checked build. The supplied release snapshot also contains [the cubic theorem under monicity, degree three and the open-disc hypothesis](https://github.com/wcook04/plectis-erdos-lean/blob/52f29ad173b04e3bac941b3663f2b9aebe5de0bb/ErdosProblems/Erdos1041/PaperCubicMonic.lean#L32) and [its expanded solution statement](https://github.com/wcook04/plectis-erdos-lean/blob/52f29ad173b04e3bac941b3663f2b9aebe5de0bb/Solutions/ExternalVerification1041CubicPath.lean#L38). The release proof obtains a root enumeration from monicity and degree; it does not assume an additional analytic path supplier. It constructs a continuous polygonal curve with bounded variation, values strictly below one and length strictly below two. Its endpoints are distinct when the polynomial is squarefree; repeated root occurrences are handled by the enumerated version. The supplied index classifies these release declarations as `release_only`, not `ci_checked`. The solution source contains a proof rather than the placeholder in the corresponding challenge file. This identifies the full formal target. The kernel checks and axioms stated in the coverage subsection of Appendix <a href="#app:sources" data-reference-type="ref" data-reference="app:sources">14</a> belong to the revisions named there. The proof above remains an ordinary mathematical argument. Pendyala \[june2026, Theorem 1, pp. 1–3\] proves the separate quartic case; no historical priority for the cubic theorem is asserted here.

<a id="sec:critical-value-separation"></a>

# An all-degree critical-value separation theorem

The next theorem applies when one simple critical value is separated from all the others by a disc in the value plane. After a change of variables, the chosen critical point is $`0`$ and its value is $`1`$. The hypothesis below then says that the disc of centre $`w_0`$ and radius $`S`$ contains no other critical value. It is a condition to check, not an isolation property guaranteed for every polynomial.

The simplicity assumption means that the chosen critical point is a simple zero of the derivative, so two inverse branches meet there. A multiple chosen critical point is excluded; the other critical points need not be simple. Also, separation of roots in the $`z`$-plane is not enough: different critical points can have nearly equal values. An exact quartic example below makes this distinction explicit. For a positive example, take $`f(z)=z^3-3a^2z`$ with $`0<a<1/\sqrt3`$. Its roots $`0,\pm\sqrt3a`$ lie in the unit disc. At $`c=a`$ the critical value is $`v=-2a^3`$, and the other normalised critical value is $`-1`$. Thus the disc centred at $`1`$ with radius $`4/3`$ contains $`0`$ and $`1`$ but excludes the other critical value. Radius $`2`$ is allowed as well: the other critical value then lies on the boundary. The proof must therefore allow a nonregular outer level.

<div id="res:critical-value-separation" class="theorem">

**Theorem 15** (separation of one simple critical value). *Let $`P`$ be a polynomial of degree $`n\ge3`$ whose leading coefficient has modulus one, with
``` math
P(0)=1,\qquad P'(0)=0,\qquad P''(0)\ne0.
```
Fix $`w_0\in[0,1]`$ and $`S>\max(w_0,1-w_0)`$. Suppose every other critical point $`d\ne0`$ satisfies
``` math
|P(d)-w_0|\ge S.                                      \tag{4}
```
Put $`p=w_0(1-w_0)`$. The two local solutions of $`P(Z(\xi))=1-\xi^2`$, $`Z(0)=0`$, continue along the real segment to one injective root-to-root connector $`\Gamma`$. Its endpoints are distinct roots, $`\Gamma\subseteq\{|P|\le1\}`$, and
``` math
\begin{equation*}
\label{eq:disk-family-length}
 \operatorname{length}(\Gamma)^2
 \le 2\Bigl(\frac{S}{n-1}\Bigr)^{2/n}
 \log\!\frac{S^2+S+p}{S^2-S+p}.                       \tag{5}
\end{equation*}
```
Consequently the connector is shorter than $`2`$ whenever
``` math
\begin{equation*}
\label{eq:disk-family-coefficient}
 \Bigl(\frac{S}{n-1}\Bigr)^{2/n}
 \log\!\frac{S^2+S+p}{S^2-S+p}<2.                    \tag{6}
\end{equation*}
```*

</div>

Lean: [disc sep separation long](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L344), [disc sep squared length le](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L305), [disc sep length lt two](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L334), [disc sep bergman factor](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L179), and 2 further declarations. Conditional on the connector and area construction that this proof produces; see the [coverage section](#sec:coverage).

<div class="proof">

*Proof.* Let $`Q=D(w_0,S)`$ and let $`U`$ be the component of $`P^{-1}(Q)`$ containing $`0`$. Both $`0`$ and $`1`$ lie in $`Q`$, and (4) says that $`0`$ is the only critical point in $`U`$. A component of a polynomial sublevel set is simply connected: on any Jordan curve in the component, the maximum principle bounds the same polynomial throughout its interior, which must therefore remain in the component. Condition (4) permits critical values on $`\partial Q`$, so we must not assume that $`\partial U`$ is regular. For $`1-w_0<S'<S`$, let $`U'`$ be the component of $`\{|P-w_0|<S'\}`$ containing $`0`$. This level is regular, and $`0`$ contributes its only unit of ramification. The component count in the proof of \[eks2010, Proposition 2.1\] therefore gives $`\deg(P|_{U'})=2`$.

These nested components exhaust $`U`$. Indeed, a point of $`U`$ can be joined to $`0`$ by a compact path in $`U`$; the maximum of $`|P-w_0|`$ on that path is strictly below $`S`$, so the path eventually lies in $`U'`$. For any fixed regular value in $`Q`$, all its finitely many preimages in $`U`$ therefore lie in one such $`U'`$ once $`S'`$ is sufficiently large. The proper map $`P:U\to Q`$ consequently also has degree two. This establishes the count without a smoothness assumption at the outer level.

Set $`a=1-w_0`$. On $`U`$, the function $`1-P`$ has only its double zero at $`0`$, so it has a single-valued square root
``` math
\xi(z)^2=1-P(z).
```
Taking this square root removes the double branching at $`0`$. The map $`\xi`$ is proper into
``` math
\widetilde Q=\{\xi:|\xi^2-a|<S\}.
```
Away from $`0`$, the identity $`2\xi\xi'=-P'`$ gives $`\xi'\ne0`$; at $`0`$, $`(\xi'(0))^2=-P''(0)/2\ne0`$. The target is star-shaped about $`0`$: because $`S>a`$, the convex disc $`D(a,S)`$ contains $`0`$, so $`t^2\xi^2\in D(a,S)`$ whenever $`\xi\in\widetilde Q`$ and $`0\le t\le1`$. It is therefore connected and simply connected. A proper local biholomorphism has open and closed image, hence is a covering of this target. Since $`U`$ is connected, it is a conformal bijection. Its inverse $`Z`$ continues both local inverse branches through the critical point. Since $`[-1,1]\subset\widetilde Q`$, the curve $`Z([-1,1])`$ joins the two distinct points over $`P=0`$, and $`P(Z(\xi))=1-\xi^2\in[0,1]`$ gives its containment.

We next map the parameter domain to the unit disc so that the curve becomes a straight interval. This allows its length to be estimated by the area of $`U`$, without replacing the domain by a larger disc. Squaring sends $`\widetilde Q`$ onto $`D(a,S)`$. To map this disc to $`\mathbb D`$ while fixing $`0`$, compose $`w\mapsto(w-a)/S`$ with the disc automorphism taking $`-a/S`$ to $`0`$. The result is the Möbius map
``` math
w\longmapsto\frac{Sw}{S^2+aw-a^2}.
```
Taking its square root after substituting $`w=\xi^2`$ gives the conformal bijection
``` math
\zeta(\xi)=\xi\sqrt{\frac{S}{S^2+a\xi^2-a^2}}
     :\widetilde Q\longrightarrow\mathbb D,
```
where the square-root factor is chosen positive at $`0`$. It sends $`[-1,1]`$ to $`[-q,q]`$, with
``` math
q^2=\frac{S}{S^2+p},\qquad
 S^2-S+p=(S-w_0)(S-(1-w_0))>0.
```
The last inequality is exactly where $`S>\max(w_0,1-w_0)`$ ensures $`0<q<1`$, as required by the length estimate below. For $`\Phi=Z\circ\zeta^{-1}:\mathbb D\to U`$, the Bergman segment inequality, proved by the kernel estimate of Section <a href="#sec:low-critical-closure" data-reference-type="ref" data-reference="sec:low-critical-closure">3</a> with the double integral taken over $`[-q,q]^2`$, gives
``` math
\begin{align*}
 \operatorname{length}(\Gamma)^2
 &\le \frac2\pi\log\frac{1+q^2}{1-q^2}
       \operatorname{Area}(U)\\
 &=\frac2\pi\log\frac{S^2+S+p}{S^2-S+p}
       \operatorname{Area}(U).                       \tag{7}
\end{align*}
```

It remains to bound the area of this component. The factor $`n-1`$ comes from the roots outside it, rather than from Pólya’s inequality alone. The auxiliary capacity estimate is as follows: for a monic degree-$`n`$ polynomial $`F`$, a regular value $`t>0`$ of $`|F|`$, and a component $`V`$ of $`\{|F|<t\}`$ containing $`k<n`$ zeros counted with multiplicity,
``` math
\frac{\operatorname{cap}(\overline V)^n}{t}<\frac{k}{2n-k}.
```
Multiplying $`F`$ by a unimodular constant leaves the estimate unchanged. This is a separate component estimate, not part of the Riemann–Hurwitz statement cited above. We give the harmonic-measure argument behind it, following [Theorem 2 and Corollary 3 of the component-capacity proof](https://github.com/wcook04/plectis-erdos/blob/8efbccc235df64a38d83f5dc7b1949e2ad18270d/research_corpus/Erdos1041/problem/ExteriorBlaschkeFibreCapacityGap.md).

Let $`m=n-k`$ and let $`\psi`$ map $`|\zeta|>1`$ conformally onto the exterior of $`\overline V`$, with positive leading coefficient $`\operatorname{cap}(\overline V)`$. The $`m`$ excluded roots have preimages $`\xi_j`$ with $`|\xi_j|>1`$. Put $`b_j=1/\overline{\xi_j}`$ and form
``` math
B(z)=\prod_{j=1}^m\frac{z-b_j}{1-\overline{b_j}z}.
```
Reflection in the unit circle shows that $`F(\psi(\zeta))/t`$ equals $`\zeta^n\overline{B(1/\overline\zeta)}`$ up to a constant of modulus one: their zeros and pole at infinity agree, and both have modulus one on the boundary. Comparing leading coefficients gives
``` math
|B(0)|=\frac{\operatorname{cap}(\overline V)^n}{t}.
```
Regularity of the level permits analytic continuation of $`\psi`$ across the boundary. On the unit circle,
``` math
\frac{d}{d\theta}\arg F(\psi(e^{i\theta}))
 =n-|B'(e^{i\theta})|>0.
```
Positivity follows because a regular polynomial level is mapped locally in the positive boundary direction. Thus $`|B'|<n`$ there.

The boundary-fibre identity used next is Lemma 1 of the same component-capacity proof. Here is its harmonic-measure argument. For a continuous real function $`h`$ on the unit circle, let $`H`$ be its harmonic extension to the disc. Since $`H\circ B`$ is harmonic, the mean value property and the Poisson formula give
``` math
\frac1{2\pi}\int_0^{2\pi}h(B(e^{i\theta}))\,d\theta
 =H(B(0))
 =\frac1{2\pi}\int_0^{2\pi}h(e^{i\phi})
   \frac{1-|B(0)|^2}{|e^{i\phi}-B(0)|^2}\,d\phi.
```
Differentiating the factors gives the positive angular derivative
``` math
\frac{d}{d\theta}\arg B(e^{i\theta})
 =|B'(e^{i\theta})|
 =\sum_{j=1}^m\frac{1-|b_j|^2}{|e^{i\theta}-b_j|^2}>0.
```
Changing variables through the $`m`$ boundary inverse branches in the first integral and comparing the continuous densities therefore yields
``` math
\sum_{B(\zeta)=w}\frac1{|B'(\zeta)|}
 =\frac{1-|B(0)|^2}{|w-B(0)|^2}\qquad(|w|=1).
```
In particular each boundary fibre consists of $`m`$ distinct points. Choosing $`w=-B(0)/|B(0)|`$ yields
``` math
\frac mn<\frac{1-|B(0)|}{1+|B(0)|},
 \qquad |B(0)|<\frac{n-m}{n+m}=\frac{k}{2n-k}.
```
Here $`B(0)\ne0`$ because every excluded-root preimage is finite. This proves the component estimate and explains how the excluded roots enter it.

For the regular inner components $`U'`$ above, the degree-two count gives exactly two zeros of $`P-w_0`$, counted with multiplicity. Since $`2<n`$, the preceding estimate applies with $`k=2`$ and gives
``` math
\frac{\operatorname{cap}(\overline{U'})^n}{S'}
 <\frac{k}{2n-k}=\frac1{n-1}.
```
Pólya’s area–capacity inequality $`\operatorname{Area}(K)\le\pi\operatorname{cap}(K)^2`$ \[crane, Theorem 6\] then yields $`\operatorname{Area}(U')<\pi(S'/(n-1))^{2/n}`$. The exhaustion proved at the start and continuity of area from below give, without assuming regularity of the limiting boundary,
``` math
\operatorname{Area}(U)\le\pi\Bigl(\frac{S}{n-1}\Bigr)^{2/n}.
```
Substitution into (7) proves (5), and (6) makes its right side strictly less than $`4`$. ◻

</div>

<div id="res:critical-value-thresholds" class="corollary">

**Corollary 16** (uniform radius $`4/3`$). *Inequality <a href="#eq:disk-family-coefficient" data-reference-type="eqref" data-reference="eq:disk-family-coefficient">[eq:disk-family-coefficient]</a> holds for every $`n\ge3`$, every $`w_0\in[0,1]`$, and every $`4/3\le S\le2`$. Thus, if $`f`$ is monic with roots in the open unit disc, $`c`$ is a simple critical point with $`v=f(c)\ne0`$ and $`|v|<1`$, and
``` math
\left|\frac{f(d)}v-w_0\right|\ge\frac43
```
for every other critical point $`d`$, then two roots of $`f`$ are joined inside $`\{|f|<1\}`$ by a curve of length strictly below $`2`$.*

</div>

Lean: [disc sep coefficient lt two](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L645), [disc sep uniform radius](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L702), [disc sep ratio le branch](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L629), [disc sep branch le seven](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CriticalValueSeparationTransport.lean#L637). Conditional on the connector and area construction in the proof of Theorem <a href="#res:critical-value-separation" data-reference-type="ref" data-reference="res:critical-value-separation">15</a>; see the [coverage section](#sec:coverage).

<div class="proof">

*Proof.* For $`S\ge4/3`$ and $`p\ge0`$,
``` math
\frac{S^2+S+p}{S^2-S+p}\le\frac{S+1}{S-1}\le7.
```
Also $`S/(n-1)\le1`$ when $`S\le2`$ and $`n\ge3`$, while $`\log7<2`$. This proves <a href="#eq:disk-family-coefficient" data-reference-type="eqref" data-reference="eq:disk-family-coefficient">[eq:disk-family-coefficient]</a>. For the unnormalised polynomial, set $`z=c+|v|^{1/n}w`$. Then $`P(w)=f(z)/v`$ has leading coefficient $`|v|/v`$, of modulus one. Scaling the connector multiplies its length by $`|v|^{1/n}<1`$ and takes $`\{|P|\le1\}`$ to $`\{|f|\le|v|\}\subset\{|f|<1\}`$. The selected value $`v`$ need not attain the minimum defining $`\mu`$. ◻

</div>

Taking $`w_0=1`$ and $`S=2`$ gives the earlier criterion $`|1-f(d)/v|\ge2`$ in every degree $`n\ge3`$. If $`c`$ attains the minimum modulus among *all* critical values and $`v\ne0`$, the Fekete–resultant bound gives $`|v|\le R^n<1`$ when all roots lie in a disc of radius $`R<1`$. Deleting zero critical values before taking the minimum would invalidate that inference. For example, $`(z-R)^2(z+R)`$ with $`0<R<1`$ has critical values $`0`$ and $`32R^3/27`$, so its least nonzero critical-value modulus exceeds $`R^3`$. The repeated root already gives a constant path, but it does not give this nonzero value the required bound. For a critical point chosen in another way, $`|v|<1`$ must remain an explicit hypothesis. In degree three the choice $`w_0=1`$ already works at $`S=6/5`$, since
``` math
\Bigl(\frac35\Bigr)^{2/3}\log 11<2.
```
This sharper cubic constant is part of the numerical Lean kernel cited below.

The separation hypothesis of Theorem <a href="#res:critical-value-separation" data-reference-type="ref" data-reference="res:critical-value-separation">15</a> is a condition on values, not on the positions of roots or critical points. To distinguish these conditions, consider the family
``` math
g_\varepsilon(z)=z^4-\varepsilon z^3-2z^2+3\varepsilon z+\tfrac12,
 \qquad 0<\varepsilon\le\tfrac1{32}.
```
Its derivative and two critical values are
``` math
g_\varepsilon'(z)=(z^2-1)(4z-3\varepsilon),\qquad
 g_\varepsilon(\pm1)=-\tfrac12\pm2\varepsilon.
```
At the endpoints of each of the intervals $`(-3/2,-5/4)`$, $`(-3/4,-1/2)`$, $`(1/2,3/4)`$ and $`(5/4,3/2)`$, the values of $`g_\varepsilon`$ have opposite signs throughout this parameter range. Each interval therefore contains exactly one root. Together with the critical points $`-1,3\varepsilon/4,1`$, these give seven points at pairwise distances greater than $`1/4`$, uniformly in $`\varepsilon`$. Nevertheless the two displayed critical values differ by $`4\varepsilon\to0`$. The earlier numerical choice is the exact member $`\varepsilon=1/262144`$:
``` math
g(z)=z^4-\frac{z^3}{262144}-2z^2+\frac{3z}{262144}+\frac12,
 \qquad
 g'(z)=4(z+1)(z-3/1048576)(z-1),
```
for which that difference is $`1/65536`$. The monic polynomial $`2^{-4}g_\varepsilon(2z)`$ puts every root inside $`|z|<3/4`$ and retains a spatial separation greater than $`1/8`$. For the critical points $`\pm1/2`$ of the scaled polynomial, the ratio of the two values is unchanged and obeys
``` math
\frac{g_\varepsilon(-1)}{g_\varepsilon(1)}
 =\frac{1+4\varepsilon}{1-4\varepsilon}\le\frac97<\frac43.
```
The reciprocal ratio lies between $`0`$ and $`1`$. Hence, for any centre $`w_0\in[0,1]`$, neither selected value satisfies the theorem’s radius-$`4/3`$ isolation condition: the other normalised value is less than $`4/3`$ away. This does not exclude a suitable isolated value at a *different* critical point.

<a id="bdry:critical-value-separation"></a>

#### Sources and scope.

The two-sheeted component, its square-root uniformisation, the Bergman segment inequality, the component-capacity estimate, Pólya’s area–capacity inequality and the exhaustion are ordinary arguments. They are collected in [the proof using an isolated critical value](https://github.com/wcook04/plectis-erdos/blob/8efbccc235df64a38d83f5dc7b1949e2ad18270d/research_corpus/Erdos1041/problem/DiskFamilyCriticalValueSeparation.md), whose capacity step is cited separately above. The separate [Lean numerical kernel](https://github.com/wcook04/plectis-erdos/blob/f36e325c8b05fe5c3ce8a2ca32a699f6dc6336b9/ErdosProblems/Erdos1041/DiskFamilyCriticalValueSeparation.lean) checks the coefficient bound for $`n\ge3`$, $`4/3\le S\le2`$ and $`p\ge0`$, and the implication from the squared length bound to length below $`2`$. It does not formalise the analytic hypotheses producing <a href="#eq:disk-family-length" data-reference-type="eqref" data-reference="eq:disk-family-length">[eq:disk-family-length]</a>. The adjacent axiom-audit source names those numerical declarations; it is not an axiom audit of the ordinary analytic theorem.

The proof requires both a simple critical point and a disc centred on $`[0,1]`$ that isolates its normalised value. For example, the trinomial $`z^n-b`$ with $`n>2`$ and $`0<|b|<1`$ has a short path by Theorem <a href="#res:trinomial-all-degree" data-reference-type="ref" data-reference="res:trinomial-all-degree">2</a>, but its only critical point is not simple, so this method does not apply. The restriction is on the chosen critical point and on the distance of the other critical values from the chosen disc. The other critical points may be multiple, and their values need not be separated from one another. No sharpness is claimed for $`S=4/3`$, and no assertion is made that every polynomial has a suitable isolated simple value. In particular, this is not a proof of the unrestricted assertion of Erdős #1041.

A related area comparison is Dubinin’s Theorem 1. The source is \[dubinin\], Theorem 1 on printed page 85 of the POMI original. It concerns a holomorphic function that gives a full $`n`$-fold covering of an annulus $`t_1<|w|<t_2`$, and, in the notation of that theorem, with $`E`$ its explicitly defined complementary set, it states
``` math
\Bigl(\frac{t_2}{t_1}\Bigr)^{2/n}\le\frac{m(E\cup D)}{m(E)}.
```
The full covering and the explicit complementary set are hypotheses of the theorem. Tao cited it on the Erdős Problem #1041 discussion page on 25 March 2026 for the relative scaling factor $`s^{2/n}`$ between the areas of two nested sublevel sets, which is the reading of the displayed inequality in which $`E`$ and $`E\cup D`$ are those two sublevel sets and the covering hypothesis holds. No step of this note uses that relative inequality. The disk-family theorem instead uses Pólya’s absolute area–capacity inequality on a component containing fewer than $`n`$ roots, after the component-capacity estimate supplies its strict capacity gap. The absolute sublevel inequality $`\operatorname{Area}\{|P|<T\}\le\pi T^{2/n}`$ remains the area input to Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a> and to Theorem <a href="#res:constant-factor-path" data-reference-type="ref" data-reference="res:constant-factor-path">9</a>. Dubinin’s theorem is a neighbouring result under a full covering hypothesis and supplies no root connector.

<a id="sec:solved-polynomial-families"></a>

# Collinear roots and two sparse polynomial families

The following results impose concrete restrictions: roots on one line, a quintic with two missing coefficients, or a polynomial of the form $`P((z-h)^q)`$ with $`P`$ cubic. None covers a general polynomial with roots in the unit disc. We first state the finite inequalities used in their proofs, then explain how the inequalities produce contained paths. The formal links distinguish these two steps.

<a id="subsec:sharp-collinear-chebyshev"></a>

## Collinear roots and Chebyshev comparison

The extreme zeros of $`T_n`$ are $`\pm\cos(\pi/(2n))`$. Scaling them to $`\pm1`$ makes the comparison polynomial have the same endpoint zeros as the polynomial under study; dividing by its leading coefficient makes both polynomials monic. Their difference then has smaller degree. Accordingly, put
``` math
r_n=\cos\frac{\pi}{2n},
 \qquad C_n=\frac{1}{2^{n-1}r_n^n}.
```

<div id="prop:sharp-collinear-chebyshev-comparator" class="theorem">

**Theorem 17** (Chebyshev comparison). *Let $`m\ge0`$, let $`p\in\mathbb R[X]`$ be monic of degree $`m+2`$, and let
``` math
-1<c_0<\cdots<c_m<1,\qquad |c_i|\le1.
```
Suppose $`p(-1)=p(1)=0`$ and $`p(c_i)p(c_{i+1})<0`$ for $`0\le i<m`$. Then
``` math
\min_{0\le i\le m}|p(c_i)|\le C_{m+2}.
```*

</div>

Lean: [exists peak le comparison bound](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/SharpCollinearChebyshev.lean#L133).

This is exactly the statement selected as [the formal Chebyshev endpoint](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/verification/ExternalVerification1041SolvedFamilies/Solution.lean#L74). It proves the finite alternation inequality; it does not yet construct the segment between two roots.

All real-rooted polynomials, and their images under rotations and translations, satisfy the collinearity hypothesis. Three noncollinear roots already fall outside it. The gain is an explicit sharp bound for the modulus along one adjacent-root segment, not a bound obtained by assuming that segment is contained.

<div id="thm:sharp-collinear-diameter" class="theorem">

**Theorem 18** (a sharp bound for collinear roots). *Let $`f`$ be a monic polynomial of degree $`n\ge2`$ whose zero occurrences are collinear, and let $`D`$ be their diameter. Some two adjacent zero occurrences are joined by a segment of length at most $`D`$ on which
``` math
|f(z)|\le
 \frac{(D/2)^n}{2^{n-1}\cos^n(\pi/(2n))}.          \tag{9}
```
The constant in *(9)* is best possible in every degree. Equality is attained by affine images of the zeros of $`T_n`$ whose extreme zeros have distance $`D`$.*

</div>

Lean: [sharp collinear root diameter](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L367), [sharp collinear root diameter monic](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L967), [exists collinear factorisation](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L928), [exists gap le comparison bound](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L212), and 5 further declarations in the [coverage section](#sec:coverage).

<div class="proof">

*Proof.* A repeated zero gives the constant path, so assume the zero values are distinct. Let $`m`$ be the midpoint of the two extreme zeros, and choose $`\theta\in\mathbb R`$ so that their line is $`m+e^{i\theta}\mathbb R`$. Put $`R=D/2`$. Translation by $`m`$, rotation by $`e^{i\theta}`$ and scaling by $`R`$ give the polynomial
``` math
q(w)=R^{-n}e^{-in\theta}f(m+Re^{i\theta}w),
```
which is monic with real zeros $`-1=y_1<\cdots<y_n=1`$, and $`|f(m+Re^{i\theta}w)|=R^n|q(w)|`$.

Compare $`q`$ with the monic endpoint-normalized Chebyshev polynomial
``` math
q_*(x)=\frac{T_n(r_nx)}{2^{n-1}r_n^n}.
```
Both $`q`$ and $`q_*`$ vanish at $`\pm1`$, and $`|q_*|\le C_n`$ on $`[-1,1]`$. For each gap $`[y_i,y_{i+1}]`$, choose $`c_i`$ at which $`|q|`$ is maximal. The maximum lies in the interior: $`q`$ vanishes at the endpoints and nowhere inside the gap. Since every root is simple, the signs at the $`n-1`$ chosen points alternate. If every gap maximum were larger than $`C_n`$, then $`q-q_*`$ would have the same nonzero signs there. The intermediate value theorem would give $`n-2`$ zeros between consecutive $`c_i`$, in addition to the two zeros at $`\pm1`$. These $`n`$ zeros are distinct, but $`q-q_*`$ is nonzero and has degree at most $`n-1`$ because its leading terms cancel. This contradiction selects a gap on which $`|q|\le C_n`$. Scaling back proves *(9)*.

For sharpness, take
``` math
y_k=\frac{\cos((2k-1)\pi/(2n))}{r_n},
 \qquad 1\le k\le n.
```
These are the zeros of $`q_*`$, have extremes $`\pm1`$, and every adjacent gap contains a scaled Chebyshev extremum where $`|q_*|=C_n`$. No smaller universal constant can work. ◻

</div>

<div id="cor:collinear-erdos-1041" class="corollary">

**Corollary 19** (collinear Erdős case). *If the zero occurrences of a monic polynomial of degree $`n\ge2`$ lie on one line in the open unit disc, two of them are joined by a curve of length strictly below $`2`$ inside $`\{|f|<1\}`$.*

</div>

Lean: [collinear erdos 1041](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L515), [collinear erdos 1041 monic](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L984), [exists collinear factorisation](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L928), [sharp collinear root diameter](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L367).

<div class="proof">

*Proof.* A repeated zero gives the constant path, so assume the zeros are distinct. Their diameter satisfies $`0<D<2`$. Since $`\cos(\pi/(2n))\ge1/\sqrt2`$, the defining formula gives $`C_n\le2^{1-n/2}\le1`$, with equality possible only at $`n=2`$. Thus *(9)* is strictly below one, and the selected segment has length at most $`D<2`$. ◻

</div>

Corollary <a href="#cor:collinear-erdos-1041" data-reference-type="ref" data-reference="cor:collinear-erdos-1041">19</a> already follows from a theorem of Erdős, Herzog and Piranian \[ehp1958, Theorem 1, p. 126\]: if the zeros of a monic polynomial of degree $`n`$ are real, lie in $`[-1,1]`$ and have centroid in $`[0,1]`$, then $`\{|f|<1\}\cap\mathbb R`$ contains an interval holding at least $`n/2`$ of the zeros. Apply it to the normalized polynomial $`q`$, replacing it by the monic polynomial $`(-1)^nq(-w)`$ if its centroid is negative. This reverses the root line without changing modulus bounds. For $`n\ge3`$ two consecutive zeros in that interval are joined by a segment of length at most $`D`$ inside $`\{|f|<(D/2)^n\}`$, and for $`n=2`$ the segment between the zeros lies in $`\{|f|\le(D/2)^2\}`$. Theorem <a href="#thm:sharp-collinear-diameter" data-reference-type="ref" data-reference="thm:sharp-collinear-diameter">18</a> adds the sharp level and its equality configurations.

<a id="critical-sequences-and-the-extremal-configuration."></a>

#### Critical sequences and the extremal configuration.

<div id="collinear-source-comparison">

</div>

For distinct real zeros, each gap between consecutive zeros contains exactly one zero of $`q'`$, and $`|q|`$ attains its maximum over the gap only there. The points $`c_i`$ chosen in the proof of Theorem <a href="#thm:sharp-collinear-diameter" data-reference-type="ref" data-reference="thm:sharp-collinear-diameter">18</a> are therefore the critical points of $`q`$, and the gap maxima are the moduli of its ordered critical sequence $`(q(c_1),\ldots,q(c_{n-1}))`$, with $`c_1<\cdots<c_{n-1}`$. In this distinct-root setting, the ordered sequence determines the real polynomial up to an increasing real affine change of variable \[eremenkoyuditskii2012, Theorem 1\]. The proof above uses only the alternation count, not this classification theorem. In this language, *(9)* says that a real polynomial of degree $`n`$ with $`n`$ distinct real zeros, leading coefficient $`a`$ and zero diameter $`D`$ has a critical value of modulus at most $`C_n|a|(D/2)^n`$.

The comparison polynomial $`q_*`$ is the monic polynomial of least deviation from zero on $`[-1/r_n,1/r_n]`$, characterised by the equioscillation conditions recalled in \[eremenkoyuditskii2012, §1\]. All $`n-1`$ of its critical values have modulus $`C_n`$, so every critical point of $`q_*`$ lies on the level curve $`\{|q_*|=C_n\}`$. Extremals with this property also occur in the level-curve length problem, where some extremal polynomial has all its critical points on $`\{|p|=1\}`$ \[eremenkohayman1999, Lemma 5\], and in the sharp bound for $`|f'|`$ on a connected sublevel set $`\{|f|\le1\}`$ of a monic polynomial, proved by Eremenko and Lempert \[eremenkolempert1994, Theorem 1\], whose equality cases are $`e^{-in\theta}T_n(2^{1/n-1}e^{i\theta}z+b)`$ with $`\theta`$ real \[eremenko2007, Theorem A\].

<a id="rem:sharp-collinear-formal-boundary"></a>

#### Formal scope.

Lean checks sign preservation, the alternating root-count mechanism, the scaled Chebyshev endpoint and uniform bound, and Theorem <a href="#prop:sharp-collinear-chebyshev-comparator" data-reference-type="ref" data-reference="prop:sharp-collinear-chebyshev-comparator">17</a>. It does not check the rigid normalization, the existence of the gap maxima, transport back to the root line, or the equality-node locations used in Theorem <a href="#thm:sharp-collinear-diameter" data-reference-type="ref" data-reference="thm:sharp-collinear-diameter">18</a>. These are ordinary steps. The sharpness assertion concerns the maximum of $`|f|`$ on the selected adjacent-root segment, and the displayed configurations attain it; no claim is made that they exhaust the equality cases, and no claim is made that the selected segment is a shortest path in $`\{|f|<1\}`$.

<a id="subsec:primitive-sparse-quintic"></a>

## Quintics with two missing coefficients

The next inequality selects two indices from five real pairs. Its three moment identities will come from the missing cubic and quadratic terms of $`z^5+az^4+bz+c`$. For $`0<r<2`$ and $`0\le s_i\le1`$, $`x_i^2\le s_i`$, put
``` math
E_i=s_i^4(s_i+r^2+2rx_i).
```

<div id="prop:primitive-quintic-two-tail-energy-selector" class="theorem">

**Theorem 20** (a consequence of three moment identities). *Suppose
``` math
\sum_{i=0}^4x_i=-r,\qquad
 \sum_{i=0}^4(2x_i^2-s_i)=r^2,\qquad
 \sum_{i=0}^4(4x_i^3-3s_ix_i)=-r^3.              \tag{10}
```
Then at least one of the ten pairs $`0\le i<j\le4`$ satisfies $`E_i<1`$ and $`E_j<1`$.*

</div>

Lean: [primitive interior exists two tail energy lt one](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PrimitiveQuinticInteriorTail.lean#L272).

This is the exact finite conclusion selected as [the formal two-index inequality](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/verification/ExternalVerification1041SolvedFamilies/Solution.lean#L24). It selects two distinct indices. It does not assert that the corresponding complex root values are distinct.

The polynomial must have no $`z^3`$ or $`z^2`$ term in the coordinates used here. For example, $`z^5+bz+c`$ is included, but a general quintic with all coefficients nonzero is not. The root-location assumption alone does not imply the three moment identities. Those identities are precisely what lets the finite inequality find two radial segments.

<div id="thm:primitive-quintic-two-tail" class="theorem">

**Theorem 21** (a quintic with two missing coefficients). *Let
``` math
p(z)=z^5+az^4+bz+c
```
and suppose its five zero occurrences $`w_0,\ldots,w_4`$ lie in the closed unit disc. At least two distinct indices satisfy
``` math
|bw_i+c|\le1.                                    \tag{11}
```
If $`a\ne0`$, two indices can be chosen with strict inequalities. If $`a=0`$, every index satisfies *(11)*, and equality holds exactly when $`|w_i|=1`$.*

*For open-disc zeros, two zero occurrences are joined inside $`\{|p|<1\}`$ by a curve of length below $`2`$: use the two radial spokes through $`0`$ when their values are distinct, and the constant path when the selected occurrences have the same value.*

</div>

Lean: [primitive quintic two tail](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/PrimitiveQuinticClosedDisc.lean#L260), [primitive quintic two tail of polynomial](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/PrimitiveQuinticClosedDisc.lean#L313), [two tails closed disc of ne zero](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/PrimitiveQuinticClosedDisc.lean#L93), [tail le one and eq iff of leading zero](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/PrimitiveQuinticClosedDisc.lean#L199), and 1 further declaration in the [coverage section](#sec:coverage).

<div class="proof">

*Proof.* If $`a=0`$, the root equation gives $`|bw_i+c|=|w_i|^5`$ for every index, proving *(11)* and its equality clause. For $`a\ne0`$, write $`a=re^{i\phi}`$ with $`r>0`$ and set $`z_i=e^{-i\phi}w_i`$. The missing $`z^3`$ and $`z^2`$ coefficients and Newton’s identities give
``` math
\sum z_i=-r,\qquad \sum z_i^2=r^2,\qquad
 \sum z_i^3=-r^3.                                 \tag{12}
```
At a zero,
``` math
|bw_i+c|=|w_i|^4|w_i+a|.
```
Thus, for $`x_i=\Re z_i`$ and $`s_i=|z_i|^2`$, the squared modulus $`|bw_i+c|^2`$ is exactly $`E_i`$ and *(12)* becomes *(10)*. The third moment gives $`r^3=|\sum_i z_i^3|\le5<8`$, so $`0<r<2`$ as required by the finite inequality.

We need to rule out four indices with squared modulus at least $`1`$. The three known power sums determine the sum of any real harmonic polynomial of degree at most three over the roots. On the unit circle, $`s^4(s+r^2+2rx)\ge1`$ reduces to $`x\ge-r/2`$. We therefore use the harmonic extension of $`(-r/2-x)(1-x)^2`$, which is nonpositive on that part of the circle. In the variables $`x=\Re z`$ and $`s=|z|^2`$, this extension is
``` math
H_r(x,s)=(-r/2-x)(1-x)^2
 +(1-s)\left(1-\frac r4-\frac{3x}{4}\right).
```
The useful feature of this choice is the expansion
``` math
H_r(\Re z,|z|^2)
 =1-\frac{3r}{4}+
 \Re\!\left[\left(r-\frac74\right)z+
             \left(1-\frac r4\right)z^2-\frac{z^3}{4}\right].
```
It is harmonic, and summing this expression with the three moments in *(12)* gives
``` math
\sum_{i=0}^4H_r(x_i,s_i)=5-2r.                  \tag{13}
```
On the unit circle its value is $`(-r/2-x)(1-x)^2`$, and
``` math
4-2r-(-r/2-x)(1-x)^2
 =(x+1)\left(\frac{(2-r)(3-x)}2+(1-x)^2\right)\ge0.
```
The maximum principle therefore gives $`H_r\le4-2r`$ throughout the disc. For an index with $`s^4(s+r^2+2rx)\ge1`$, one has $`s>0`$ and $`s^{-4}\ge1+4(1-s)`$ by convexity on $`(0,1]`$. Consequently
``` math
2r(x+r/2)\ge s^{-4}-s\ge5(1-s).
```
Put $`d=x+r/2`$, $`u=1-x`$, $`A=1-r/4-3x/4`$, and $`P=-u^2+(2r/5)A`$. The assumption $`s^4(s+r^2+2rx)\ge1`$ gives $`0\le d<2`$. Since $`H_r=-du^2+(1-s)A`$, it is nonpositive when $`A\le0`$; when $`A>0`$, the preceding bound gives $`H_r\le dP`$. The remaining estimate is the exact sum-of-squares identity
``` math
\frac1{31}-P
 =\frac25\left(d-\frac{38}{31}
               +\frac14(u-\frac3{31})\right)^2
  +\frac{31}{40}\left(u-\frac3{31}\right)^2\ge0,
```
which gives $`P\le1/31`$, and hence $`H_r(x,s)\le2/31`$ whether $`P`$ is positive or nonpositive. Thus $`H_r\le2/31`$ whenever the squared modulus is at least $`1`$. If four indices had squared modulus at least $`1`$, *(13)* would give
``` math
5-2r\le4-2r+\frac8{31}<5-2r,
```
a contradiction. This proves the two-index conclusion when $`a\ne0`$.

For either value of $`a`$, at a zero $`w`$,
``` math
p(tw)=(1-t)c+(t-t^4)(bw+c)-t^4(1-t)w^5.
```
For $`0\le t\le1`$ the three nonnegative weights sum to $`1-t^5`$. The tail bound, $`|w|\le1`$, and $`|c|\le1`$ therefore keep each selected radial segment in $`\{|p|\le1\}`$. Under the open-disc hypothesis, $`|c|<1`$. Its coefficient $`1-t`$ is positive for $`0\le t<1`$, so
``` math
|p(tw)|<(1-t)+(t-t^4)+t^4(1-t)=1-t^5\le1.
```
At $`t=1`$ the value is zero. Thus both segments lie in $`\{|p|<1\}`$, and their total length is $`|w_i|+|w_j|<2`$. ◻

</div>

<a id="rem:primitive-quintic-formal-boundary"></a>

#### Formal scope.

The moment identities and the inequality selecting two indices have formal proofs. The source snapshot additionally contains [a complete implementation of the open-disc sparse-quintic path conclusion](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperPrimitiveCompletionR10.lean#L235), including the geometric assembly. The formal-source index places the complete *open-disc path conclusion* in its checked build. That declaration does not by itself assert every closed-disc equality clause of the longer theorem above. That is supplied build evidence, not a new compilation performed for this prose revision. The ordinary argument above is retained, and the source link remains at its original commit.

<a id="subsec:translated-cubic-quotient-fibres"></a>

## Polynomials obtained from a cubic by a power substitution

For $`f(z)=P((z-h)^q)`$, the roots associated with a nonzero root of $`P`$ form a regular $`q`$-gon centred at $`h`$. This rotational symmetry is a substantial restriction: a generic polynomial of degree $`3q`$ does not have it. It lets one contained segment for the cubic give two segments in the original variable. The first theorem supplies that segment.

<div id="lem:cubic-safe-root-spoke" class="theorem">

**Theorem 22** (a contained radial segment for a cubic). *If $`r,s,v\in\mathbb C`$ have modulus below one, at least one $`u\in\{r,s,v\}`$ satisfies
``` math
\left|(tu-r)(tu-s)(tu-v)\right|\le1
 \qquad(0\le t\le1).
```*

</div>

Lean: [cubic has safe root spoke](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/CubicQuotientFiberCase.lean#L161).

This is exactly [the formal cubic segment inequality](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/verification/ExternalVerification1041SolvedFamilies/Solution.lean#L14).

<div id="thm:translated-cubic-quotient-fibres" class="theorem">

**Theorem 23** (a cubic composed with a power map). *Let $`q\ge2`$, $`h\in\mathbb C`$, $`P`$ be monic cubic, and
``` math
f(z)=P((z-h)^q).
```
If every zero of $`f`$ lies in the open unit disc and $`f`$ has at least two distinct zero values, then two zeros are joined through $`h`$ by a two-segment path of length below $`2`$ inside $`\{|f|<1\}`$. Equivalently this closes the coefficient family
``` math
(z-h)^{3q}+A(z-h)^{2q}+B(z-h)^q+C
```
in every degree $`3q\ge6`$.*

</div>

Lean: [complete translated cubic quotient fibres](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCubicFibres.lean#L240).

<div class="proof">

*Proof.* Fix a $`q`$th root $`y`$ of a quotient root and a primitive $`q`$th root of unity $`\zeta`$. The full fibre consists of $`h+y\zeta^k`$. Since every fibre point lies in the open unit disc,
``` math
\frac1q\sum_{k=0}^{q-1}|h+y\zeta^k|^2
   =|h|^2+|y|^2<1.                                \tag{14}
```
Thus $`|y|<1`$, and the corresponding quotient root has modulus $`|y|^q<1`$. This verifies the open-disc hypothesis for all quotient roots before selecting a radial segment for the cubic. The identity retains more information than these separate bounds: $`|h|<1`$ and every fibre radius is strictly below $`\sqrt{1-|h|^2}`$. Consequently, any two contained fibre segments constructed below have total length strictly less than $`2\sqrt{1-|h|^2}`$. The position of the symmetry centre therefore improves the length bound; replacing it by $`2`$ discards this information.

Write $`P(w)=(w-r)(w-s)(w-v)`$ and associate to $`r`$ the real number $`A_r=\Re(r\overline{s+v})`$, cyclically. The exact sum is
``` math
A_r+A_s+A_v=|r+s+v|^2-(|r|^2+|s|^2+|v|^2)>-3,
```
so one of these numbers, say $`A_r`$, exceeds $`-1`$. For $`0\le t\le1`$,
``` math
\frac{|tr-s|^2+|tr-v|^2}{2}
 =t^2|r|^2+\frac{|s|^2+|v|^2}{2}-tA_r<1+t+t^2.
```
AM–GM now gives $`|tr-s|\,|tr-v|<1+t+t^2`$. Consequently, for $`0\le t<1`$,
``` math
|P(tr)|<(1-t)(1+t+t^2)=1-t^3\le1.              \tag{15}
```
At $`t=1`$ the polynomial vanishes. The entire spoke is therefore strictly contained, including its origin endpoint.

For a nonzero quotient root satisfying the segment bound from *(15)*, two distinct fibre points satisfy
``` math
f(h+ty\zeta^k)=P(t^qr),
```
and their two spokes through $`h`$ have total length $`2|y|<2\sqrt{1-|h|^2}\le2`$. If the selected quotient root is zero, choose a nonzero quotient root $`s`$ and write $`P(w)=w(w-s)(w-v)`$. For $`0<t<1`$,
``` math
|P(ts)|=t(1-t)|s|^2|ts-v|<2t(1-t)\le\frac12.
```
The values at both endpoints are zero, so this nonzero root supplies two distinct fibre points. If no nonzero quotient root exists, $`f`$ has only one distinct zero value, contrary to the hypothesis. ◻

</div>

<a id="rem:cubic-quotient-formal-boundary"></a>

#### Formal scope.

Lean checks the identity for these three real numbers, the choice of a contained cubic segment, and the quartic counterexample, and also [the complete translated cubic fibre theorem](https://github.com/wcook04/plectis-erdos/blob/27c2fc5fe3c55fe547feaeb4c9bb68b3cf63a5bf/lean/ErdosProblems/Erdos1041/PaperCubicFibres.lean#L240). The latter supplies the finite set of roots in each fibre, root-of-unity average, nonzero-root selection, pullback and explicit rectifiable path through the centre under the hypotheses displayed above. Its exact source occurs in the successfully compiled dependency closure of [the source-bound Lean build and axiom-audit record](https://github.com/wcook04/plectis-erdos/blob/27c2fc5fe3c55fe547feaeb4c9bb68b3cf63a5bf/verification/erdos1041-returned-r18-v5-full-audit-evidence.json). The theorem gives length below $`2`$; the sharper $`2\sqrt{1-|h|^2}`$ reading in the proof is recorded here as an ordinary consequence of the mean-square identity, not as a separately audited endpoint.

<a id="bdry:solved-polynomial-families"></a>

#### Scope of the formal results.

The finite declarations prove the Chebyshev comparison, the two-index quintic inequality and the cubic segment estimate. The formal-source index also records complete path theorems for the sparse quintic and the translated cubic family in its checked build. These are stronger than the finite inequalities alone. The sharper bound $`2\sqrt{1-|h|^2}`$ and the quartic lifting arguments below retain the ordinary proof status stated beside them. A formal declaration must still be compared with the exact hypotheses and conclusion of the paper statement; a similar name is not enough.

<a id="sec:frontier"></a>

# Further families and counterexamples to proposed proof steps

The following sections collect additional sufficient conditions and counterexamples to particular path constructions. They are not a programme for proving the unrestricted historical assertion. The underlying research notes are retained at commit [`f214a6b4`](https://github.com/wcook04/plectis-erdos/tree/f214a6b45528dc5eefe20ffadc35f2e981627d4c/research_corpus/Erdos1041) and summarised in [the dated overview of these arguments](https://github.com/wcook04/plectis-erdos/blob/f214a6b45528dc5eefe20ffadc35f2e981627d4c/research_corpus/Erdos1041/FRONTIER.md). Where a claim is based on a computation rather than a proof, that restriction is stated explicitly.

<a id="roots-close-to-a-regular-polygon"></a>

## Roots close to a regular polygon

Let $`f(z)=\prod_{i=1}^n(z-a_i)`$, $`n\ge2`$, with all $`|a_i|\le1`$. Put $`\rho_i=|a_i|`$ and $`D=|\operatorname{disc}(f)|/n^n`$. The [Vandermonde determinant estimate](https://github.com/wcook04/plectis-erdos/blob/f214a6b45528dc5eefe20ffadc35f2e981627d4c/research_corpus/Erdos1041/NearFeketeRadialAngularSplit.md) says that, when $`D\ge1-\eta`$ and $`0\le\eta\le1/(80n^2)`$,
``` math
1-\rho_i^2\le \frac{n\eta}{n-1},\qquad
  |a_i-a_j|\ge \frac{2-2\sqrt\eta-n\eta}{n-1},
```
where the second inequality is for $`i\ne j`$. Moreover, the roots lie within $`7\sqrt\eta`$ of a rotated regular $`n`$-gon, after a bijection. These estimates come from near equality in Hadamard’s determinant inequality, as follows.

Take the Vandermonde matrix $`V_{im}=a_i^m`$, $`0\le m<n`$, and let $`G=VV^*`$, $`s_i=G_{ii}=\sum_{m=0}^{n-1}\rho_i^{2m}`$ and $`H=\operatorname{diag}(s_i^{-1/2})G\operatorname{diag}(s_i^{-1/2})`$. The normalisation makes $`H`$ positive semidefinite with diagonal entries one, and
``` math
D=\det H\prod_i\frac{s_i}{n}.
```
Every factor is at most one by Hadamard’s inequality, so $`D\ge1-\eta`$ forces each factor to be at least $`1-\eta`$. In particular,
``` math
(n-1)(1-\rho_i^2)\le n-s_i\le n\eta.
```
Hadamard–Fischer applied to the $`\{i,j\}`$ principal block gives $`\det H\le1-|H_{ij}|^2`$, hence $`|G_{ij}|\le n\sqrt\eta`$. For $`t=a_i\overline{a_j}`$, the finite geometric sum then gives
``` math
n\sqrt\eta\ge\left|\sum_{m=0}^{n-1}t^m\right|
 \ge n-\frac{n(n-1)}2|1-t|.
```
Together with $`1-t=1-\rho_j^2+\overline{a_j}(a_j-a_i)`$, this proves the displayed separation bound. These two bounds need only $`0\le\eta<1`$; the smaller range is used for the matching with a regular polygon.

For that matching, put $`\kappa=n^2\eta/(n-1)\le1/80`$ and $`u_i=a_i/\rho_i`$. The radial bound gives $`\rho_i^{2n}\ge1-\kappa`$, while $`(1-t)G_{ij}=1-t^n`$ gives $`|1-a_i^n\overline{a_j^n}|\le2n\sqrt\eta`$ for $`i\ne j`$. Using $`|1-be^{i\theta}|^2=(1-b)^2+b|1-e^{i\theta}|^2`$ with $`b=\rho_i^n\rho_1^n\ge1-\kappa`$, we obtain
``` math
|u_i^n-u_1^n|\le\frac{2n\sqrt\eta}{\sqrt{1-\kappa}}.
```
Choose the nearest $`n`$th-root phase to $`u_i`$ among $`u_1e^{2\pi i j/n}`$. The inequality $`|e^{i\theta}-1|\ge2|\theta|/\pi`$ for $`|\theta|\le\pi`$ shows that its distance from $`a_i`$ is at most
``` math
\frac{n\eta}{n-1}+\frac{\pi\sqrt\eta}{\sqrt{1-\kappa}}
 \le7\sqrt\eta.
```
The separation bound exceeds $`14\sqrt\eta`$ in the stated range, so two roots cannot be assigned the same phase. There are $`n`$ roots and $`n`$ phases, giving the required bijection. This is an ordinary argument from standard determinant inequalities, not a new Lean declaration or a claim of priority for the stability estimate.

The hypothesis $`D\ge1-\eta`$ with $`\eta\le1/(80n^2)`$ is a strong quantitative assumption, not merely a requirement that roots lie near the unit circle. The regular $`n`$-gon has $`D=1`$, whereas a configuration with a repeated root has $`D=0`$. In particular, radial information alone cannot supply this discriminant bound.

The comparison with unit-modulus roots is pointwise on a specified segment, not an ordering of complex polynomial values. Write $`a_k=\rho_k u_k`$, with $`|u_k|=1`$. Under $`D\ge1-\eta`$ and $`0\le\eta\le1/(10n^4)`$, the same source proves
``` math
|f(su_i)|\le\prod_k|su_i-u_k|
 \qquad(0\le s\le\rho_i).
```
The elementary step is
``` math
|su_i-\rho_ku_k|^2-|su_i-u_k|^2
 =(1-\rho_k)\bigl(2s\Re(u_i\overline{u_k})-1-\rho_k\bigr).
```
Here is where the discriminant hypothesis enters. The two bounds just proved imply
``` math
|a_i-a_k|>\frac1{n-1}\ (i\ne k),\qquad
 1-\rho_k\le\frac{n\eta}{n-1}<\frac1{(n-1)^2}.
```
For $`k=i`$, the required inequality is $`2s\le1+\rho_i`$, which follows from $`s\le\rho_i\le1`$. For $`k\ne i`$, it is immediate if $`\Re(u_i\overline{u_k})\le0`$. Otherwise $`s\le\rho_i`$ gives
``` math
\begin{split}
 \rho_k\bigl(2s\Re(u_i\overline{u_k})-1-\rho_k\bigr)
 &\le\rho_i^2-\rho_k-|a_i-a_k|^2\\
 &\le1-\rho_k-|a_i-a_k|^2<0.
\end{split}
```
Multiplying the factorwise inequalities proves the comparison. This argument uses the two elementary bounds, not the polygon-matching range; it therefore also covers $`n=2`$, when $`1/(10n^4)>1/(80n^2)`$. Moving the roots inward reduces this modulus bound, but does not select the angular directions of two contained segments.

For exact regular-polygon directions, write $`a_i=\rho_i\omega\zeta^i`$, with $`|\omega|=1`$ and $`\zeta=e^{2\pi i/n}`$. In any degree $`n\ge2`$, the sufficient condition
``` math
0<\rho_k\le1,\qquad \rho_k\ge2\cos(2\pi/n)-1\quad\hbox{for every }k
```
makes the same factorwise comparison hold. Indeed, for $`k\ne i`$ with positive cosine, $`s\le1`$ gives $`2s\Re(\zeta^{i-k})\le2\cos(2\pi/n)\le1+\rho_k`$; nonpositive cosines and $`k=i`$ are handled as above. Since $`\prod_k(z-\omega\zeta^k)=z^n-\omega^n`$, we obtain
``` math
|f(s\,\omega\zeta^i)|\le1-s^n
 \quad(0\le s\le\rho_i).
```
Every root-to-origin segment is therefore contained in $`\{|f|\le1\}`$. If all $`\rho_i<1`$, containment is strict: the displayed bound is below $`1`$ for $`s>0`$, and $`|f(0)|=\prod_i\rho_i<1`$. Any two roots can then be joined through the origin with length $`\rho_i+\rho_j<2`$. For $`2\le n\le6`$ the lower bound on $`\rho_k`$ is nonpositive, so every choice of positive radii at most one is allowed. For $`n\ge7`$ the argument instead requires each radius to be at least $`2\cos(2\pi/n)-1`$. This is a sufficient condition for the factorwise comparison, not a claimed necessary condition for a contained path. The favourable index in the general unit-circle averaging identity may move with $`s`$, however; an existence statement at one level does not supply a fixed pair of roots.

<a id="the-exact-binomial-chord-calculation"></a>

## The exact binomial chord calculation

<div id="binomial-chord-calculation">

</div>

For $`f(z)=z^n-r^n`$, $`0<r<1`$ and $`n\ge2`$, the construction in Section 13 of the short note depends on the maximum over an entire chord. The endpoint values alone do not give that maximum. Put $`\omega=e^{2\pi i/n}`$ and $`c=\cos(\pi/n)`$. When $`n\ge3`$, define $`r_*=(1+c^n)^{-1/n}`$ and $`\varepsilon=(1-r^n)^{1/n}`$; in the inner-chord case $`r\ge r_*`$, set $`t=\varepsilon/c\le r`$.

Here is the chord estimate, including the smaller radii used in the second construction. For $`n\ge3`$, let $`0<s\le r`$. A point on the chord from $`s`$ to $`s\omega`$ can be written
``` math
z=\frac{sc}{\cos\theta}e^{i(\pi/n+\theta)},
 \qquad |\theta|\le\pi/n.
```
Concavity of $`\log\cos x`$ on $`[0,\pi/2)`$ gives $`\cos(n\theta/2)\le\cos^{n/2}\theta`$ for $`0\le\theta<\pi/n`$. By symmetry and continuity,
``` math
1+\cos(n\theta)\le2\cos^n\theta
 \qquad (|\theta|\le\pi/n).
```
Set $`u=\cos^{-n}\theta\ge1`$. Since $`z^n=-(sc)^nu e^{in\theta}`$, this inequality gives
``` math
\begin{split}
 |z^n-r^n|^2-\bigl(r^n+(sc)^n\bigr)^2
 &\le (u-1)(sc)^n\bigl((sc)^n(u+1)-2r^n\bigr)\le0.
 \end{split}
```
The last step uses $`(sc)^nu\le s^n\le r^n`$ and $`(sc)^n\le r^n`$. Equality holds at the midpoint, where $`\theta=0`$. Consequently the maximum on every such chord is exactly $`r^n+(sc)^n`$. Taking $`s=r`$ proves the outer threshold; taking $`s=t=\varepsilon/c\le r`$ proves the inner bound, and taking $`s=\lambda t<t`$ makes it strict. Every radial leg between $`s`$ and $`r`$ has modulus $`r^n-|z|^n<1`$. Its two legs and crossing chord have length $`2r-2s(1-\sin(\pi/n))<2r`$, which proves the stated length formula and shows that contraction preserves the strict length bound.

For $`n=2`$, the chord is a diameter and its maximum is $`r^2<1`$; its length is $`2r<2`$. For $`n\ge3`$, the outer chord works exactly when $`r<r_*`$, and its length is $`2r\sin(\pi/n)`$. At $`r=r_*`$ it reaches level one at its midpoint. If $`r\ge r_*`$, the two radial legs and inner crossing have length
``` math
2r-2\varepsilon\tan\left(\frac\pi4-\frac\pi{2n}\right)<2r<2.
```
Contracting the crossing radius makes the level bound strict, as proved above. The argument compares these constructions, not their lengths with all admissible paths.

<a id="a-bounded-radius-concyclic-class"></a>

## A bounded-radius concyclic class

A different argument gives a chord when all roots lie on a circle of sufficiently small radius. Let $`f`$ be monic of degree $`n\ge3`$ with distinct zeros on a circle of radius $`\rho`$. If $`2\rho^n\le1`$, two adjacent zeros are joined by their straight chord, whose length is at most $`2\rho\sin(\pi/n)<2`$, and the chord lies in $`\{|f|<1\}`$. (If a zero is repeated, the short-connection conclusion is immediate; the distinct case is the substantive one.)

For each fixed degree $`n`$, the radius condition is $`\rho\le2^{-1/n}`$. It allows arbitrary spacing on that circle, but does not cover every radius $`\rho<1`$. No restriction on the circle’s centre is imposed.

After translating and scaling, let $`g`$ be the monic polynomial with roots $`w_1,\ldots,w_n`$ on the unit circle. Such a polynomial is *self-inversive*: $`z^n\overline{g(1/\overline z)}`$ is a constant multiple of $`g(z)`$, with the constant of modulus one. Equivalently, $`e^{-in\theta/2}g(e^{i\theta})`$ is real up to a fixed phase. Choose
``` math
c=(-1)^{n+1}\prod_j w_j,\qquad q(z)=z^n-c.
```
Then $`g`$ and $`q`$ have the same leading and constant coefficients, and their boundary values have a common real phase. If every root gap contained a point with $`|g|>|q|`$, the real boundary function of $`g-q`$ would have alternating signs at these points. Advancing the angle by $`2\pi`$ multiplies that function by $`(-1)^n`$, so the alternation also holds across the final gap. The intermediate value theorem would give $`n`$ distinct unit-circle zeros of $`g-q`$. This is impossible: its degree is at most $`n-1`$, and $`g=q`$ cannot satisfy the assumed strict inequalities. Thus some adjacent-root arc satisfies $`|g|\le|q|\le2`$. The interior of that arc contains no zero of $`q`$, since $`g`$ is nonzero there. As consecutive zeros of $`q`$ are separated by angle $`2\pi/n`$, the selected arc has angular width at most $`2\pi/n`$. This explains why the same selected pair also has the required short chord. To pass from this arc to its chord $`[a,b]`$, let $`\nu`$ be the unit normal pointing into the circular segment bounded by them. On the open chord, logarithmic differentiation gives
``` math
\partial_\nu\log|g(z)|
 =\sum_{w_j\notin\{a,b\}}
   \frac{\operatorname{Re}\bigl(\nu\overline{z-w_j}\bigr)}{|z-w_j|^2}>0.
```
The endpoint terms vanish because their directions are tangent to the chord. Every remaining numerator is positive because the other roots lie strictly on the far side of its line; $`n\ge3`$ ensures at least one such term. The harmonic function $`\log|g|`$ has no interior maximum and tends to $`-\infty`$ at $`a,b`$. A maximum cannot lie on the open chord either, since moving into the circular segment increases the function. It is therefore attained on the arc, and the maximum on the chord is strictly smaller. Scaling back gives $`|f|<2\rho^n\le1`$ throughout the chord, with $`f=0`$ at its endpoints. These are the arguments of [Theorem C and Lemma S, Sections 3–4 of the concyclic note](https://github.com/wcook04/plectis-erdos/blob/f214a6b45528dc5eefe20ffadc35f2e981627d4c/research_corpus/Erdos1041/ConcyclicAlternation.md).

The argument is an ordinary proof outside Lean. The [exact-rational checker](https://github.com/wcook04/plectis-erdos/blob/f214a6b45528dc5eefe20ffadc35f2e981627d4c/research_corpus/Erdos1041/scripts/check_erdos1041_concyclic_exact_witness.py) checks finitely many identities used in the proof and configurations, while the [numerical checker](https://github.com/wcook04/plectis-erdos/blob/f214a6b45528dc5eefe20ffadc35f2e981627d4c/research_corpus/Erdos1041/scripts/check_erdos1041_concyclic_alternation.py) is regression and stress-test evidence. The arc constant $`2`$ is attained by the regular $`n`$-gon. Thus the bound obtained by passing through the arc is $`\rho\le2^{-1/n}`$, although this cutoff tends to $`1`$ as $`n\to\infty`$. This does not assert optimality of the chord bound or exclude another contained path at a larger radius. Nor does arc sharpness make the pair of radial segments shortest. For example, for $`g(z)=z^3-1/8`$ the chord between $`1/2`$ and $`e^{2\pi i/3}/2`$ has length $`\sqrt3/2<1`$, whereas the two radii have total length $`1`$. The binomial calculation above gives a maximum of $`9/64<1`$ on that chord. The length-$`2`$ equality at $`z^n-1`$, proved below, concerns the uncontracted closed-level problem.

<a id="power-substitutions-in-trinomials"></a>

## Power substitutions in trinomials

The radial-segment identity and strict bound are formalized in [cancellation along a trinomial root segment](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/CyclicTrinomialFiberCase.lean#L46) and [containment of a trinomial root segment](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/CyclicTrinomialFiberCase.lean#L103).

The trinomial identity also applies after a power substitution. Fix integers $`1\le r<m`$ and $`q\ge1`$, and consider the translated monic polynomial
``` math
f(z)=(z-h)^{qm}+a(z-h)^{qr}+c.
```
The strict exponent inequality keeps the leading monomial separate. The algebraic identity below also holds when $`r=m`$, but then the two leading terms merge and the displayed polynomial need not be monic or have degree $`qm`$. Writing $`w=(z-h)^q`$ reduces the root equation to $`w^m+aw^r+c=0`$. At such a quotient root the middle coefficient can be eliminated exactly: for $`0\le u\le1`$,
``` math
u^mw^m+au^rw^r+c
   =(1-u^r)c-(u^r-u^m)w^m.
```
This is a nonnegative combination of $`c`$ and $`-w^m`$, with weights $`1-u^r`$ and $`u^r-u^m`$ summing to $`1-u^m`$. The [formal radial-segment estimate](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/CyclicTrinomialFiberCase.lean#L103) gives strict containment when $`|w|<1`$ and $`|c|<1`$.

For $`q\ge2`$ and a nonzero quotient root satisfying these bounds, choose two distinct solutions $`y_1,y_2`$ of $`y^q=w`$. Their common modulus is $`|w|^{1/q}<1`$. To lift a quotient radial segment, set $`u=t^q`$:
``` math
|f(h+ty_i)|
 \le (1-t^{qm})\max\{|c|,|w|^m\}<1
 \qquad(0\le t\le1).
```
Thus the two lifted segments join $`h+y_1`$ to $`h+y_2`$ through $`h`$ with length $`2|w|^{1/q}<2`$. The construction uses any quotient root with the stated modulus bound; it does not prove that such a root exists without an additional hypothesis. A zero quotient root instead gives a root of multiplicity at least $`q`$ at $`h`$ and hence a constant path between two occurrences. The formal source checks the factorization, radial-segment estimate and finite length inequality. It does not establish the existence of a suitable quotient root or formalise the selection and lifting just described. Thus its scope is the segment inequality and finite length calculation, not the complete path construction or unrestricted Erdős #1041.

<a id="a-coefficient-condition-for-four-term-polynomials"></a>

## A coefficient condition for four-term polynomials

With one additional monomial, Abel summation gives a sufficient condition involving the two lower coefficients. Let
``` math
g(w)=w^m+aw^r+bw^s+c,\qquad m>r>s\ge1,
```
assume all roots of $`g`$ lie in the open unit disk, and let $`w_1,w_2`$ be roots of the two smallest moduli. If
``` math
|c|+|b|\,|w_2|^s<1,
```
then the complete radial spokes from $`w_1`$ and $`w_2`$ to the origin lie in $`\{|g|<1\}`$, and their broken line has length strictly below $`2`$. The simpler coefficient condition
``` math
|b|+|c|\le1
```
makes every root-to-origin segment contained; the coefficient $`a`$ has no additional restriction beyond the assumed root locations. This coefficient condition includes $`b=0`$ and $`|c|\le1`$, but is not automatic for all four-term polynomials with roots in the disc.

The mechanism is visible in one identity. At a root $`w`$ and for $`0\le u\le1`$,
``` math
\begin{split}
 g(uw)={}&(1-u^s)c
  +(u^s-u^r)(c+bw^s)
  +(u^r-u^m)(-w^m).
\end{split}
```
Here the root equation has eliminated $`aw^r`$ before taking absolute values. The three weights are nonnegative and sum to $`1-u^m`$. The controlled terms are $`c`$, $`c+bw^s`$ and $`-w^m`$; their moduli are strictly below one under the root-dependent condition. The same identity explains why no bound on $`a`$ is needed. Lean checks the [factorization](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/CyclicTetranomialCoefficientCase.lean#L27) and the resulting [strict spoke theorem](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/CyclicTetranomialCoefficientCase.lean#L145) under the exact weak exponent hypotheses $`1\le s\le r\le m`$; it also checks the coefficient-only corollary above. Its weak bound $`|b|+|c|\le1`$ still gives strict containment: the root-disc hypothesis implies $`|c|<1`$, and, if $`b\ne0`$, $`|w|^s<1`$ gives $`|c|+|b||w|^s<|c|+|b|\le1`$. If $`b=0`$, the required bound is simply $`|c|<1`$.

An alternative criterion uses a complex power sum to select two indices. Let $`S`$ index a finite family of roots, $`N=|S|\ge2`$, and
``` math
M=\sum_{i\in S}w_i^s.
```
The [squared-modulus identity](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/TetranomialL2Selector.lean#L33) gives
``` math
\sum_{i\in S}|c+bw_i^s|^2
 =N|c|^2+|b|^2\sum_{i\in S}|w_i^s|^2
   +2\mathop{\rm Re}(\overline c\,bM).
```
Consequently, if every $`|w_i|<1`$, $`|c|<1`$, and
``` math
N\bigl(|b|^2+|c|^2\bigr)
   +2\mathop{\rm Re}(\overline c\,bM)<N-1,
```
then two distinct indices $`i,j\in S`$ satisfy $`|c+bw_i^s|<1`$ and $`|c+bw_j^s|<1`$. Indeed, the displayed identity bounds the sum of squared moduli strictly below $`N-1`$. If at most one index had modulus below one, the other $`N-1`$ terms would each contribute at least one. This explains both the threshold $`N-1`$ and why the criterion selects two indices. Applying the [resulting contained-segment theorem](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/TetranomialL2Selector.lean#L208) to these inequalities proves that both root segments lie strictly in $`\{|g|<1\}`$. Retaining the signed cross term permits the inequality to hold for configurations outside the coefficient-only triangle $`|b|+|c|\le1`$. The formal hypotheses do not require $`i\mapsto w_i`$ to be injective, so distinct indices need not denote distinct root values. For the polynomial consequence, the family must be a submultiset of the zeros, respecting their algebraic multiplicities. A repeated zero then already gives a constant path between two occurrences. Repeating a simple zero in an arbitrary indexed family cannot supply a second occurrence. The two sufficient conditions are not ordered by strength. For example, $`g(w)=w^5+19/20`$ has all roots in the open unit disc and satisfies the coefficient condition with $`b=0`$. For its full five-root list, however, the left side of the power-sum condition is $`5(19/20)^2=361/80>4=N-1`$, so that condition fails. Its benefit is the use of cancellation in the cross term, not inclusion of every case covered by the coefficient condition. Conversely,
``` math
g(w)=(w^2-1/2)(w^3+4/5)
     =w^5-\tfrac12w^3+\tfrac45w^2-\tfrac25
```
has all roots of modulus $`1/\sqrt2`$ or $`(4/5)^{1/3}`$, hence below one, but $`|b|+|c|=6/5>1`$. Its full root list has $`M=\sum_iw_i^2=1`$: the two quadratic roots contribute $`1`$, and the three cubic roots contribute $`0`$. The power-sum left side is $`5(16/25+4/25)-16/25=84/25<4`$. Thus this criterion does cover root-disc polynomials excluded by the coefficient condition.

For $`q\ge2`$ and $`f(z)=g((z-h)^q)`$, assume also that all roots of $`f`$ lie in the open unit disc. If $`y^q=w`$ and $`\omega=e^{2\pi i/q}`$, the roots $`h+\omega^j y`$ satisfy
``` math
\frac1q\sum_{j=0}^{q-1}|h+\omega^j y|^2=|h|^2+|y|^2<1.
```
Thus every quotient root has $`|w|=|y|^q<1`$, which supplies the root-disc hypothesis used above, and every lifted spoke has length $`|y|<1`$. Two selected spokes join through $`h`$ with total length below $`2`$; repeated root occurrences instead permit the constant path. The Lean theorem assumes the finite root family, its complex power sum $`M`$, and the displayed inequality. It neither derives that inequality from arbitrary coefficients nor verifies the family’s polynomial multiplicities, the cyclic lifting, or the final path construction. Completeness of the root list is not required for the selection argument: a submultiset respecting multiplicity suffices. Without one of the power-sum, root-dependent, or coefficient-only inequalities, the tetranomial case is not covered by this argument; this family does not solve unrestricted Erdős #1041.

<a id="sec:translated-quartic-quotient-fibres"></a>

## A quartic composed with a power map

Pendyala’s degree-four theorem \[june2026, Theorem 1\], with his four-point radial lemma \[june2026, Lemma 1\], can also be lifted through every nontrivial cyclic power. Let $`P`$ be a monic quartic, let $`q\ge2`$ be an integer, and set
``` math
f(z)=P((z-h)^q).
```
Assume that every root of $`f`$ lies in the open unit disc. A repeated root of $`f`$ gives the constant path, so suppose $`f`$ is squarefree. Then the roots of $`P`$ are distinct and nonzero. For a root $`w=y^q`$ of $`P`$, all points $`h+\zeta^j y`$, with $`\zeta=e^{2\pi i/q}`$, are roots of $`f`$. Hence the open-disc hypothesis gives
``` math
\frac1q\sum_{j=0}^{q-1}|h+\zeta^jy|^2=|h|^2+|y|^2<1.
```
In particular $`|w|^{1/q}=|y|<1`$, which is the bound needed for the lifted length, and also $`|w|<1`$. Pendyala’s chord-or-radial argument supplies the quotient geometry in two cases. If two quotient roots satisfy $`|w_i-w_j|<1`$, every point $`w`$ of the chord $`[w_i,w_j]`$ lies in the unit disc; the two endpoint factors of $`|P(w)|`$ have product at most $`|w_i-w_j|^2/4`$ and the other two factors are below $`2`$, so $`|P(w)|\le|w_i-w_j|^2<1`$. Otherwise the quotient roots are pairwise at distance at least $`1`$. Choosing $`R`$ with $`\max_k|w_k|<R<1`$ and applying the four-point radial lemma to the points $`w_k/R`$ gives distinct $`i,j`$ with $`|P(tw_i)|\le R^4`$ and $`|P(tw_j)|\le R^4`$ for $`0\le t\le1`$, so the radial segments $`[0,w_i]`$ and $`[0,w_j]`$ lie in $`\{|P|<1\}`$. The extra issue is metric: a short chord in the $`w`$-plane need not lift isometrically through $`y\mapsto y^q`$.

Put $`\alpha=1/q`$. On a chord avoiding $`0`$, choose a continuous argument and hence a root lift $`y`$ with $`y^q=w`$. Differentiation gives $`|dy|=\alpha|w|^{\alpha-1}|dw|`$, independently of the chosen root. If the supporting line has distance $`d`$ from $`0`$, and $`x`$ is distance along that line from the perpendicular foot, then
``` math
\bigl(\sqrt{d^2+x^2}\bigr)^{\alpha-1}
    \le x^{\alpha-1}\qquad(x>0).
```
The negative exponent is why replacing $`|w|`$ by $`x`$ gives an upper length bound. Lean checks [the integral of the power-map derivative](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/research_corpus/Erdos1041/QuarticQuotientFiberCase.lean#L37)
``` math
\alpha\int_0^A x^{\alpha-1}\,dx=A^\alpha.
```
If the foot lies on the chord, split there: the two integrals are bounded by the $`\alpha`$-powers of the distances from the foot to the endpoints, hence by $`|a|^\alpha+|b|^\alpha`$. If the foot lies outside the chord, integrate on one side of it; extending the interval to the foot bounds the result by the $`\alpha`$-power of the farther endpoint’s modulus. When the chord passes through $`0`$, choose a continuous root on each half and join the lifts at $`0`$; the integral is finite because $`\alpha>0`$. This proves the chord-lift estimate
``` math
\operatorname{length}(\widetilde{[a,b]})
    \le |a|^{1/q}+|b|^{1/q}.
```
The [strict endpoint-length estimate](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/research_corpus/Erdos1041/QuarticQuotientFiberCase.lean#L59) also proves that if $`0\le a,b<1`$, $`\alpha>0`$, and a candidate length $`L`$ is at most $`a^\alpha+b^\alpha`$, then $`L<2`$. The close-pair chord therefore has a lift of length below $`2`$. In the other case the quotient arms meet at $`0`$, so their lifts are radial segments meeting at $`h`$, with total length $`|w_i|^{1/q}+|w_j|^{1/q}<2`$. In both cases $`f=P\circ((z-h)^q)`$ transfers containment from the quotient curve. Distinct quotient endpoints give distinct roots of $`f`$. This proves the path assertion in every degree $`4q\ge8`$. The fibre average gives a little more: $`|h|<1`$ and $`|w_k|^{1/q}<\sqrt{1-|h|^2}`$ for every quotient root. Consequently the same constructed path has length
``` math
\operatorname{length}<2\sqrt{1-|h|^2}\le2.
```
This refinement concerns the translated power-substitution family, not arbitrary degree-$`4q`$ polynomials.

Pendyala proves the quartic geometric theorem and its four-point radial lemma. The local Lean module checks the antitone density inequality, its integral, the strict powered endpoint-length bound, and the final length estimate. It does not formalize Pendyala’s geometric lemma, the continuous covering-space construction of the root lift, or the ordinary chord/radial case assembly. This is a family defined by a power substitution, not a proof of unrestricted Erdős #1041.

<a id="the-joining-point-in-the-quartic-construction."></a>

#### The joining point in the quartic construction.

Pendyala’s proof of \[june2026, Theorem 1, pp. 2–3\] uses a smallest enclosing disc and joins the selected roots through its centre. For the power substitution we instead apply \[june2026, Lemma 1\] to the centred disc $`|w|\le R`$. That lemma requires only the disc and pairwise-distance hypotheses, not minimality of the disc. Keeping the joining point at $`0`$ is what makes the radial lift above valid. The endpoint-length bound for a single chord would not justify lifting an arbitrary broken line through a nonzero quotient vertex.

<a id="a-mean-bound-for-critical-values-in-every-degree"></a>

## A mean bound for critical values in every degree

The next theorem gives the quadratic case of a Poisson argument for critical-value moments. It allows a disc of any centre and radius, repeated roots, and repeated critical points. After proving this case, we derive the stronger exponent $`4/(n-1)`$ and explain how vanishing complex power sums permit still larger exponents. None of these moment bounds controls the lengths of inverse paths ending at the critical points.

Dubinin \[dubinin2006critical, Theorem 2, (9), pp. 1172–1173\] proves the sharp unit-disc critical-value product inequality using the resultant identity, the maximum-modulus principle and Schur’s Vandermonde inequality. The positive-moment estimate below implies his product bound by AM–GM. When $`n\ge3`$, the product estimate alone cannot control a positive moment: a list $`T,T^{-1},1,\ldots,1`$ has product one, but its sum of $`p`$th powers is unbounded as $`T\to\infty`$ for every $`p>0`$. This compares the information in two inequalities for nonnegative lists; it does not claim that these lists occur as critical values of polynomials in the theorem. In degree two there is just one critical value, and the product and positive-moment bounds are equivalent. For a zero prescribed at the origin, his Theorem 3 (p. 1174) gives
``` math
\left(\prod_j|f(c_j)|\right)^{1/(n-1)}
 \le(n-1)\left(\frac{|f'(0)|^2}{n^n}\right)^{1/(n-1)}.
```
Dubinin explicitly identifies Tischler’s earlier contribution \[tischler1989, p. 444, as reported in Dubinin\]. His Theorem 1 uses dissymmetrisation; that is not the proof mechanism of Theorem 2. Schur’s original paper \[schur1918\] is the historical antecedent cited there, not a separately re-proved source in this record. A sharp marked-zero positive-moment bound remains a separate question. The addendum \[revision2026, Section 3\] reports a reduction to boundary-root configurations, without solving the resulting angular optimisation. That unavailable addendum is not a proof dependency of the critical-value theorem below.

<div id="res:critical-value-budget" class="theorem">

**Theorem 24** (a mean bound for critical values). *Let $`f`$ be monic of degree $`n\ge2`$, with roots in a closed disc of radius $`R\ge0`$. If $`c_1,\ldots,c_{n-1}`$ are its critical points counted with multiplicity, then
``` math
\begin{equation}
\label{eq:critical-value-quadratic-budget}
 \sum_{j=1}^{n-1}|f(c_j)|^{2/(n-1)}
 \le(n-1)R^{2n/(n-1)}.
\end{equation}
```
Consequently the lower exponents used elsewhere in the record satisfy
``` math
\begin{equation}
\label{eq:critical-value-power-budget}
 \sum_{j=1}^{n-1}|f(c_j)|^{1/(n-1)}
 \le(n-1)R^{n/(n-1)}
\end{equation}
```
and
``` math
\sum_{j=1}^{n-1}|f(c_j)|^{1/n}\le(n-1)R.
```
The constant is attained by $`f(z)=(z-\tau)^n-\lambda`$ with enclosing disk centred at $`\tau`$ and radius $`R=|\lambda|^{1/n}`$.*

</div>

Lean: [critical value three budgets](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/CriticalMeanWhole.lean#L14), [critical value three budgets sharp](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/CriticalMeanWhole.lean#L36).

The finite inequality behind the theorem concerns arbitrary points of the disk, without asking them to arise as critical points. Its quadratic form is
``` math
\sum_{j=1}^m\left(\prod_{k=1}^m
       |1-\overline{c_j}c_k|\right)^{2/m}\le m,
 \qquad |c_j|\le1.
```
The following pointwise bound explains why these finite inequalities control critical values in every degree.

<div id="res:reflected-critical-value" class="lemma">

**Lemma 25** (reflected-derivative bound). *If $`f`$ is monic of degree $`n\ge2`$ with roots in the closed unit disk, and $`c_1,\ldots,c_{n-1}`$ list its critical points with multiplicity, then
``` math
\begin{equation}
\label{eq:critical-reflected-product}
 |f(c_j)|\le\prod_{k=1}^{n-1}|1-\overline{c_j}c_k|.
\end{equation}
```*

</div>

Lean: [reflected critical value](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperReflectedCompletion.lean#L254).

[The reflected-derivative inequality is checked in Lean, including closed-disc roots and critical-point multiplicities.](https://github.com/wcook04/plectis-erdos/blob/bb4e24651b37cd096d3749ef299c3317930b3a3b/ErdosProblems/Erdos1041/PaperReflectedCompletion.lean#L254)

<div class="proof">

*Proof.* First put all roots $`a_i`$ strictly inside the disk. We want a numerator that equals $`nf`$ at the critical points and can be compared with $`f'`$ on the circle. Set
``` math
N(z)=nf(z)-zf'(z),\qquad
 G(z)=n\prod_k(1-\overline{c_k}z).
```
The numerator is the polar derivative at $`0`$: the conventional polar derivative at $`\alpha`$ is $`nf(z)+(\alpha-z)f'(z)`$; see [Rather–Gulzar, Section 1](https://arxiv.org/abs/1303.0068v1) for this notation. Its leading term cancels, and $`N(c_j)=nf(c_j)`$. Reflection gives $`|G|=|f'|`$ on the circle. Gauss–Lucas puts every $`c_k`$ inside the disc, so $`G`$ has no zero on its closure. Thus $`N/G`$ is a holomorphic quotient to which the maximum-modulus principle applies. On $`|\zeta|=1`$,
``` math
\operatorname{Re}\frac{\zeta f'(\zeta)}{f(\zeta)}
 =\sum_i\left(\frac12+
       \frac{1-|a_i|^2}{2|1-a_i\bar\zeta|^2}\right)\ge\frac n2.
```
Writing the logarithmic derivative as $`w`$, the identity $`|n-w|^2-|w|^2=n^2-2n\operatorname{Re}w\le0`$ gives $`|N|\le|G|`$ on the circle. The maximum-modulus principle applied to $`N/G`$ gives the same comparison inside. At $`c_j`$, $`N(c_j)=nf(c_j)`$; dividing by $`n`$ and conjugating each factor proves <a href="#eq:critical-reflected-product" data-reference-type="eqref" data-reference="eq:critical-reflected-product">[eq:critical-reflected-product]</a>. For closed-disk roots apply this result to $`f_r(z)=r^nf(z/r)`$, $`0<r<1`$, whose critical points are $`rc_k`$:
``` math
r^n|f(c_j)|\le\prod_k|1-r^2\overline{c_j}c_k|.
```
Let $`r\uparrow1`$. This also handles boundary critical points and all multiplicities without selecting local branches. ◻

</div>

Set $`m=n-1`$. The weighted Poisson proof below gives the quadratic finite inequality for every $`m\ge1`$. Gauss–Lucas and Lemma <a href="#res:reflected-critical-value" data-reference-type="ref" data-reference="res:reflected-critical-value">25</a> then give $`\sum_j|f(c_j)|^{2/m}\le m`$ on the unit disc. Applying this to $`R^{-n}f(h+Rz)`$ and scaling back proves <a href="#eq:critical-value-quadratic-budget" data-reference-type="eqref" data-reference="eq:critical-value-quadratic-budget">[eq:critical-value-quadratic-budget]</a> for $`R>0`$; if $`R=0`$, all critical values vanish.

The two displayed consequences are the lower power means of the same nonnegative $`m`$-tuple. Equivalently, after unit-disc normalization, apply the monotonicity of normalized $`L^p`$ means from exponent $`2/m`$ first to $`1/m`$ and then to $`1/(m+1)=1/n`$. Scaling back contributes respectively $`R^{n/m}`$ and $`R`$. These are consequences of the quadratic case; the higher-power argument below strengthens that case without changing these lower-exponent applications.

The quadratic mean and both lower-exponent consequences are recorded as checked in [the complete critical-value mean](https://github.com/wcook04/plectis-erdos/blob/27c2fc5fe3c55fe547feaeb4c9bb68b3cf63a5bf/lean/ErdosProblems/Erdos1041/PaperCriticalValueMeanR10.lean#L101). This includes arbitrary centre, zero radius, and critical points counted with multiplicity. The source version and formal target are identified in [the source-bound Lean build and axiom-audit record](https://github.com/wcook04/plectis-erdos/blob/27c2fc5fe3c55fe547feaeb4c9bb68b3cf63a5bf/verification/erdos1041-returned-r18-v5-full-audit-evidence.json). The earlier candidate description in the source header predates that run.

The quadratic moment controls the number of large critical values. For $`R>0`$, write $`r_j=|f(c_j)|^{1/n}`$. Then
``` math
\sum_j(r_j/R)^{2n/(n-1)}\le n-1,\qquad
 \#\{j:r_j\ge tR\}\le\frac{n-1}{t^{2n/(n-1)}}\quad(t>0).
```
The counting bound follows by retaining just the indicated summands. The fourth-power refinement proved below replaces the exponent $`2n/(n-1)`$ here by $`4n/(n-1)`$, improving the count for $`t>1`$. For $`0<t\le1`$ the trivial bound $`n-1`$ is at least as good. The binomial equality family has every $`r_j=R`$, but these distributional bounds still leave the geometry of the joining paths to be supplied.

<a id="the-weighted-poisson-inequality-and-its-equality-case."></a>

#### The weighted Poisson inequality and its equality case.

<div id="weighted-poisson-proof">

</div>

For one point $`c`$ of weight $`1`$, the quantity to bound is $`(1-|c|^2)^2\le1`$; equality holds only at $`c=0`$. For two points $`c,-c`$ of equal weight, it is $`1-|c|^4\le1`$. These examples suggest why a nonzero configuration should lose from equality. Now let $`w_j\ge0`$, $`\sum_jw_j=1`$, and $`|c_j|\le1`$, with repetitions allowed. Write $`G(z)=\prod_k|1-\overline{c_k}z|^{w_k}`$, taking a factor of exponent zero to be one. We seek an analytic function with modulus $`G`$: its logarithmic derivative will express the weighted Poisson kernel, and its Taylor coefficients will measure the loss from equality. For $`|c|<1`$ and $`|\zeta|=1`$, let $`P_c(\zeta)=(1-|c|^2)/|\zeta-c|^2`$, and write $`dm=dt/(2\pi)`$ on $`\zeta=e^{it}`$. When every centre is strictly inside the disc, choose analytic logarithms zero at the origin and put
``` math
g(z)=\exp\sum_jw_j\log(1-\overline{c_j}z)
     =1+\sum_{\nu\ge1}a_\nu z^\nu,\qquad
 P=\sum_jw_jP_{c_j}.
```
On the unit circle $`P=1-2\Re(\zeta g'/g)`$, by logarithmic differentiation. The Poisson formula reproduces $`g(c)`$ from its boundary values and gives $`\int P_c\,dm=1`$ for $`|c|<1`$. Expanding a square therefore yields
``` math
\int |g|^2P_c\,dm-|g(c)|^2
   =\int |g-g(c)|^2P_c\,dm\ge0.
```
This explains why the same kernel bounds the value at each centre. Take $`c=c_j`$, multiply by $`w_j`$ and sum to obtain
``` math
\sum_jw_jG(c_j)^2\le\int |g|^2P\,dm
 =1-\sum_{\nu\ge1}(2\nu-1)|a_\nu|^2.
```
To see the last equality, expand $`|g|^2`$ and $`\zeta g'\overline g`$ and integrate on the circle. Orthogonality leaves $`1+\sum_{\nu\ge1}|a_\nu|^2`$ and $`\sum_{\nu\ge1}\nu|a_\nu|^2`$, respectively. The analytic function $`g`$ extends to a neighbourhood of the closed disc in this interior case, which justifies the termwise integrations. For closed-disc centres replace $`c_j`$ by $`rc_j`$, $`0<r<1`$. The actual coefficient of degree $`\nu`$ becomes $`r^\nu a_\nu`$, where the fixed coefficients are defined from the analytic function near zero. Pass to $`r\uparrow1`$ first with an arbitrary finite coefficient sum. Nonnegative finite deficits then give summability and the infinite inequality; no boundary holomorphic logarithm is required. Lean checks the [exact radial transport of each Cauchy coefficient](https://github.com/wcook04/plectis-erdos/blob/1d70482583cc9c662cd3b86f66d75c54bb405aa6/lean/ErdosProblems/Erdos1041/WeightedCauchyTransportR10.lean#L66), the [finite boundary-deficit inequality](https://github.com/wcook04/plectis-erdos/blob/1d70482583cc9c662cd3b86f66d75c54bb405aa6/lean/ErdosProblems/Erdos1041/WeightedBoundaryDeficitR10.lean#L108), and the [summable full boundary deficit](https://github.com/wcook04/plectis-erdos/blob/1d70482583cc9c662cd3b86f66d75c54bb405aa6/lean/ErdosProblems/Erdos1041/WeightedBoundaryDeficitR10.lean#L153).

If equality holds, all positive-degree coefficients vanish, so $`g=1`$ near zero and $`\sum_jw_j\overline{c_j}/(1-\overline{c_j}z)=0`$ there. Group equal centres before clearing denominators. A nonzero centre of positive total weight gives a nonzero pole coefficient, which is impossible. Thus equality is equivalent to $`c_j=0`$ on positive support. In particular, strictly positive weights force all centres zero. A point of weight zero is unconstrained: weight one at $`0`$ and weight zero at $`1`$ still give equality. Grouping equal centres is necessary: an argument that assumed they were distinct would not prove the stated equality case.

Equal weights in $`\sum_jw_jG(c_j)^2\le1`$ give the quadratic finite inequality above for every $`m\ge1`$, with equality only at the zero configuration. The linear inequality follows separately. For $`M=\sum_jw_jG(c_j)`$, the variance identity
``` math
M^2+\sum_jw_j(G(c_j)-M)^2=\sum_jw_jG(c_j)^2
```
gives $`M\le1`$. Equality in this Cauchy–Schwarz step means that the values $`G(c_j)`$ are constant at all indices of positive weight; equality in the final bound also requires equality in the quadratic inequality. The three-point and four-point specialisations follow with their equality cases. The formal-source index records the complete weighted theorem in its checked build. The hypotheses permit repeated centres and zero weights; the equality condition refers only to centres of positive weight.

This equality condition also identifies all equality cases of Theorem <a href="#res:critical-value-budget" data-reference-type="ref" data-reference="res:critical-value-budget">24</a> for a fixed containing disc $`\overline D(h,R)`$ with $`R>0`$. Equality in the critical-value bound forces equality in the quadratic finite inequality after normalisation, so every critical point is $`0`$. Thus the normalised derivative is $`nz^{n-1}`$ and the polynomial is $`z^n-\lambda`$, with $`|\lambda|=1`$ forced by equality. Restoring the centre and radius gives exactly $`f(z)=(z-h)^n-\lambda`$ with $`|\lambda|=R^n`$. Equality in either lower-power consequence also forces equality in the quadratic bound, so it has the same family. For $`R=0`$ the only possible polynomial is $`(z-h)^n`$. This classification follows from the ordinary proof; it is not an additional assertion about the cited Lean endpoints.

The earlier three-point Hölder argument and four-point matching argument are not used here. Their scalar identities do not justify the omitted inequalities; the proof is the weighted Poisson calculation above.

<a id="higher-powers-and-vanishing-complex-power-sums."></a>

#### Higher powers and vanishing complex power sums.

The quadratic inequality is the formally recorded case, not the full range of the analytic argument. To estimate $`G^p`$ for $`p>0`$, we need an analytic function whose squared modulus is $`G^p`$. Using the same logarithms as above, define
``` math
H_p=g^{p/2}=1+\sum_{\nu\ge1}b_\nu z^\nu.
```
For interior centres, logarithmic differentiation and the Poisson majorant give
``` math
\begin{align*}
 P&=1-\frac4p\Re\frac{\zeta H_p'}{H_p},\\
 \sum_jw_jG(c_j)^p
 &\le\int |H_p|^2P\,dm
 =1-\sum_{\nu\ge1}\left(\frac{4\nu}{p}-1\right)|b_\nu|^2.
\end{align*}
```
The identity follows from the same two orthogonality calculations used for $`g`$; only the coefficient of the derivative term changes. For $`0<p\le4`$ every displayed coefficient is nonnegative. Hence
``` math
\sum_jw_jG(c_j)^p\le1\qquad(0<p\le4).
```
Boundary centres follow by replacing $`c_j`$ by $`rc_j`$: the degree-$`\nu`$ coefficient becomes $`r^\nu b_\nu`$, and the values on the left are $`G_r(rc_j)=\prod_k|1-r^2\overline{c_k}c_j|^{w_k}`$. First retain finitely many nonnegative terms, then let $`r\uparrow1`$. Zero weights can be omitted throughout. This proves the closed-disc inequality without differentiating a boundary logarithm. The argument is the ordinary [power-parameter Poisson identity](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/SharpPowerDiscProducts.md), not an additional conclusion of the cited complete Lean theorem.

In particular, equal weights and Lemma <a href="#res:reflected-critical-value" data-reference-type="ref" data-reference="res:reflected-critical-value">25</a> give, with $`m=n-1`$,
``` math
\frac1m\sum_j|f(c_j)|^{4/m}\le\frac1m\sum_jG(c_j)^4\le1
```
on the unit disc. For roots in $`\overline D(h,R)`$ this becomes
``` math
\sum_j|f(c_j)|^{4/(n-1)}\le(n-1)R^{4n/(n-1)}.
```
As before, $`R>0`$ is handled by $`R^{-n}f(h+Rz)`$, and $`R=0`$ by the vanishing of all critical values. The constant is attained by $`(z-h)^n-\lambda`$ with $`|\lambda|=R^n`$. This proves sharpness of the constant, not optimality of the exponent for each fixed degree.

At $`p=4`$ the coefficient of $`|b_1|^2`$ vanishes, so the previous quadratic equality proof cannot simply be reused. If equality holds, the finite-deficit bounds imply $`H_4=1+b_1z`$. If $`b_1\ne0`$, the rational identity $`H_4'/H_4=2g'/g`$ shows, by comparing poles and their residues, that all nonzero centres coincide at $`a=-\overline{b_1}`$ and have total weight $`1/2`$. The other half of the weight is at zero. Their fourth-power average is
``` math
\tfrac12\bigl(1+(1-|a|^2)^2\bigr)
 =1-|a|^2+\tfrac12|a|^4<1\qquad(0<|a|\le1),
```
a contradiction. Thus $`H_4=1`$, and the pole argument already used for $`g`$ forces every centre of positive weight to be zero. Conversely that configuration gives equality. It follows that the fourth-power critical-value estimate has the same equality family as the quadratic one for a fixed containing disc.

For $`p>4`$, the coefficient $`4/p-1`$ is negative, so the nonnegative-deficit argument no longer applies. To extend its range we can force the first Taylor coefficients to vanish. Let $`s\ge1`$ be an integer and suppose
``` math
\sum_jw_jc_j^k=0\qquad(1\le k<s).
```
The expansion
``` math
\log H_p(z)=-\frac p2\sum_{k\ge1}
       \frac{\overline{\sum_jw_jc_j^k}}{k}z^k
```
then has no terms of degree below $`s`$, so $`b_1=\cdots=b_{s-1}=0`$. All remaining coefficient weights are nonnegative for $`0<p\le4s`$. The same proof therefore gives $`\sum_jw_jG(c_j)^p\le1`$ throughout that range. For a monic polynomial with roots in $`\overline D(h,R)`$, $`R>0`$, the resulting endpoint is
``` math
\sum_j|f(c_j)|^{4s/(n-1)}\le(n-1)R^{4sn/(n-1)},
 \qquad \sum_j(c_j-h)^k=0\quad(1\le k<s).
```
There is no cancellation hypothesis when $`s=1`$. For $`s=2`$, the condition says that the critical-point centroid is the disc centre. Comparing the coefficients of $`f`$ and $`f'`$ shows
``` math
\frac1{n-1}\sum_jc_j=\frac1n\sum_{i=1}^n z_i,
```
so this is also the root centroid. Recentring can increase the required radius: for $`0<r<1`$, the roots of $`(z-r)^2(z+r)`$ lie in $`\overline D(0,r)`$, but their centroid is $`r/3`$, and a disc centred there needs radius $`4r/3`$ to contain the root $`-r`$. Thus the exponent-$`8/(n-1)`$ statement cannot be applied at the old centre with the old radius. These are exact cancellations, not merely bounds on the moments. All higher-power conclusions in this paragraph are ordinary analytic results; the linked complete Lean moment endpoint has exponent $`2/(n-1)`$.

<a id="formal-scope-of-the-poisson-and-integration-steps."></a>

#### Formal scope of the Poisson and integration steps.

The square-expansion proof above applies whenever $`g`$ is holomorphic on the disc and continuous on its closure, with $`|c|<1`$. The linked [norm-square majorization](https://github.com/wcook04/plectis-erdos/blob/d4fed71423840f70f10edf27b9ad27c22fc4f49a/ErdosProblems/Erdos1041/PoissonNormSquare.lean#L114) uses the Poisson formula for a real part and the nonnegativity of a square. The [weighted kernel identity](https://github.com/wcook04/plectis-erdos/blob/d4fed71423840f70f10edf27b9ad27c22fc4f49a/ErdosProblems/Erdos1041/PoissonKernelBridge.lean#L27) identifies the pointwise Poisson mixture. Separately, [absolute series transport](https://github.com/wcook04/plectis-erdos/blob/d4fed71423840f70f10edf27b9ad27c22fc4f49a/ErdosProblems/Erdos1041/CircleSeriesTransport.lean#L49) justifies termwise circle integration when the terms are circle integrable and admit a summable uniform norm bound; its Taylor double-product form assumes absolute summability of both coefficient sequences. The complete weighted and critical-value targets are indexed in the recorded checked dependency closure. Their exact statements, dependencies and status are recorded in the accompanying formal-scope map. Historical totals of named axiom prints are not an additional proof of a paper statement. The kernel checks and axioms stated in the coverage subsection of Appendix <a href="#app:sources" data-reference-type="ref" data-reference="app:sources">14</a> belong to the revisions named there.

<a id="a-uniform-central-region-in-every-degree."></a>

#### A uniform central region in every degree.

For every $`m\ge1`$, the [inequality for points in a smaller disc](https://github.com/wcook04/plectis-erdos/blob/3be82b1a7340284aea72e9a5c8493cb020843921/ErdosProblems/Erdos1041/FreePointCentralCompletion.lean#L39) proves
``` math
|c_j|\le\sqrt{1-e^{-2}}\quad(1\le j\le m)
 \quad\Longrightarrow\quad
 \sum_{j=1}^m\left(\prod_{k=1}^m|1-\overline c_jc_k|\right)^{1/m}\le m.
```
To see the mechanism, set $`h_j=m^{-1}\sum_k\log|1-\overline c_jc_k|`$ and $`D_j=-\log(1-|c_j|^2)`$. Write $`M_\nu=m^{-1}\sum_k c_k^\nu`$ for the normalised complex power sums used in this calculation. The absolutely convergent series for $`\log(1-z)`$ gives
``` math
h_j=-\Re\sum_{\nu\ge1}\frac{\overline c_j^{\,\nu}M_\nu}{\nu},
 \qquad
 -\frac1m\sum_jh_j=\sum_{\nu\ge1}\frac{|M_\nu|^2}{\nu}.
```
In particular, $`\sum_jh_j\le0`$. Cauchy–Schwarz applied to the first series, using $`\sum_{\nu\ge1}|c_j|^{2\nu}/\nu=D_j`$, gives $`h_j^2\le(-m^{-1}\sum_i h_i)D_j`$. The radius bound gives $`D_j\le2`$. Put $`r=\sqrt{-m^{-1}\sum_i h_i}`$. If $`r=0`$, every $`h_j`$ vanishes. For $`r>0`$, convexity bounds $`e^h`$ by the chord of its graph over $`[-\sqrt2r,\sqrt2r]`$. Averaging and using $`m^{-1}\sum_jh_j=-r^2`$ gives
``` math
\frac1m\sum_j e^{h_j}
 \le\cosh(\sqrt2r)-\frac r{\sqrt2}\sinh(\sqrt2r)\le1.
```
For the last inequality, the function $`\cosh u-(u/2)\sinh u`$ equals $`1`$ at $`u=0`$ and has derivative $`(\sinh u-u\cosh u)/2\le0`$ for $`u\ge0`$. Thus the radius bound supplies the estimates needed for the geometric-mean inequality; no further series hypotheses are imposed. This alternative proof includes the all-zero configuration but requires the smaller radius $`\sqrt{1-e^{-2}}`$. The weighted theorem above covers the whole closed unit disc. The next logarithmic argument imposes a different sufficient radius condition; neither restriction belongs to the weighted theorem.

For $`m\ge1`$, let $`|c_i|^2\le a<1`$, with $`a\ge0`$, and put $`L=-\log(1-a)`$. The [uniform-radius theorem](https://github.com/wcook04/plectis-erdos/blob/457e0c74b2666f7fb2d825c967e49e439a600b23/ErdosProblems/Erdos1041/FreePointUniformRadius.lean#L84) gives the geometric-mean inequality
``` math
e^L\le1+2L\quad\Longrightarrow\quad
 \sum_{i=1}^m\left(\prod_{j=1}^m|1-\overline c_i c_j|\right)^{1/m}\le m.
```
For $`a=1/2`$ the scalar hypothesis holds, since $`2\le1+2\log2`$; for $`a=3/4`$ it fails, since $`4>1+2\log4`$. Thus it supplies a sufficient restriction on the squared radii, not a necessary condition for the geometric-mean inequality.

The proof uses point-dependent logarithmic bounds. Write $`H_i=m^{-1}\sum_j\log|1-\overline c_i c_j|`$ and $`D_i=-\log(1-|c_i|^2)`$. The preceding logarithmic calculation gives $`\sum_iH_i\le0`$ and $`H_i^2\le-(D_i/m)\sum_jH_j`$. For nonnegative upper bounds $`M_i\ge H_i`$, Taylor’s formula with integral remainder gives
``` math
e^{H_i}\le1+H_i+\Phi(M_i)H_i^2,
 \qquad \Phi(t)=\int_0^1(1-s)e^{st}\,ds.
```
Since $`\Phi(M_i)\ge0`$, summing and using the quadratic bounds yields
``` math
\sum_i e^{H_i}
 \le m+\left(1-\frac1m\sum_i\Phi(M_i)D_i\right)\sum_jH_j
 \le m
```
whenever $`\sum_i\Phi(M_i)D_i\le m`$. This is the sufficient condition in the [formal inequality with individual upper bounds](https://github.com/wcook04/plectis-erdos/blob/0d34630e1cc9d2b1ac6edfa7cfdba83b31bdc8fe/ErdosProblems/Erdos1041/LogKernelCentralCertificate.lean#L99). Taking $`M_i=L`$ gives $`\Phi(L)L\le1`$ as a sufficient condition, since $`H_i,D_i\le L`$. For $`L>0`$, integration gives $`\Phi(L)=(e^L-1-L)/L^2`$; hence this condition is exactly $`e^L\le1+2L`$. At $`L=0`$ all centres vanish, so the conclusion is immediate.

<a id="four-points-without-a-matching-or-numerical-split."></a>

#### Four points without a matching or numerical split.

The preceding weighted proof with $`m=4`$ and $`w_j=1/4`$ gives
``` math
\sum_{j=1}^4\left(\prod_{k=1}^4|1-\overline{c_k}c_j|\right)^{1/4}\le4,
 \qquad |c_j|\le1,
```
with equality if and only if all four centres vanish. The checked four-point theorem includes this equality case. In particular, the inequality is strict as soon as one centre is nonzero, even with repeated centres or centres on the unit circle.

This four-point consequence needs neither the former $`21/25`$ split nor a perfect-matching Hölder step. The scalar stationary-point inequalities from that approach are not a proof of its missing steps. The two restricted arguments above remain independent alternatives. The recorded compilation and axiom checks concern the weighted proof and its three- and four-point consequences.

The mean inequality gives $`\mu\le R^n`$. In the unit-disc normalisation $`R=1`$, this does not force the smaller quintic threshold $`\mu<1/M_5`$ below. For $`f(z)=z^n-1`$, every critical value has modulus one, so no uniformly smaller bound holds on the closed-disc class. These are bounds for moduli, not inverse-ray lengths; a path selection or a metric comparison is still needed.

<a id="a-sufficient-critical-value-threshold-in-degree-five"></a>

## A sufficient critical-value threshold in degree five

<a id="the-distance-bound-for-the-two-nearest-roots."></a>

#### The distance bound for the two nearest roots.

<div id="two-nearest-root-distance">

</div>

Let $`f`$ have degree $`n\ge2`$ and all roots in the closed unit disc, and let $`c`$ be a critical point with $`f(c)\ne0`$. List roots with multiplicity. Its two nearest roots have total distance at most $`2`$. The root-disc hypothesis, rather than a bound on $`|f(c)|`$, is what gives this estimate.

Rotate so that $`c=t\ge0`$, and order the distances as $`0<d_1\le d_2\le\cdots\le d_n`$. Logarithmic differentiation gives $`\sum_j(z_j-c)^{-1}=-f'(c)/f(c)=0`$. Dividing $`|z_j-c|^2+2t\Re(z_j-c)\le1-t^2`$ by $`d_j^2`$, then summing and using the reciprocal balance, gives
``` math
n\le(1-t^2)\sum_jd_j^{-2}.
```
Thus $`t<1`$ and $`d_1\le\sqrt{1-t^2}\le1`$. The same reciprocal balance, with the nearest term isolated, gives $`d_2\le(n-1)d_1`$.

Suppose $`d_1+d_2>2`$. Since $`d_2\le1+t`$, we have $`d_1>1-t`$, and hence
``` math
1-t^2<d_1(2-d_1)<d_1d_2.
```
The first strict inequality uses that $`x(2-x)`$ is increasing on $`[0,1]`$. It follows that
``` math
n\le(1-t^2)\bigl(d_1^{-2}+(n-1)d_2^{-2}\bigr)
 <\frac{d_2}{d_1}+(n-1)\frac{d_1}{d_2}\le n.
```
For the last step, put $`x=d_2/d_1\in[1,n-1]`$ and expand $`(x-1)(x-(n-1))\le0`$. This contradiction proves the closed-disc bound. For roots in the open unit disc, scaling by a containing radius $`0<R<1`$ gives $`d_1+d_2\le2R<2`$. This is the argument in [the proof for the two nearest roots](https://github.com/wcook04/plectis-erdos/blob/a729f05c40398663fd586c9da487ad874d898639/research_corpus/Erdos1041/GlobalCriticalTwoNearestBudget.md); Lean now checks the [strict distance bound from the critical polynomial](https://github.com/wcook04/plectis-erdos/blob/52d6c45ad203ba619cb5fe6ba485c0b5400519ea/lean/ErdosProblems/Erdos1041/PaperCompleteR20/TwoNearestPolynomial.lean#L31), including the root-disc reduction and the choice of the two nearest indices.

This argument selects the two nearest roots but does not put their segments inside a polynomial sublevel set. The next calculation supplies that separate containment estimate under a bound on $`|f(c)|`$.

<a id="containment-of-the-two-selected-segments."></a>

#### Containment of the two selected segments.

Let $`f`$ be monic of degree $`n\ge3`$ with roots in the closed unit disc. The following estimate controls the segments from a critical point to its two nearest roots. To specify the constant, put
``` math
\begin{split}
 M_n^2=\max_{\substack{0\le t\le1\\4-n\le y\le n}}
 &(1-t)^2\bigl((1-t)^2+2ty+n(n-2)t^2\bigr)\\
 &\hspace{8mm}\cdot
 \left((1-t)^2+\frac{2t(n-y)}{n-2}\right)^{n-2}.
\end{split}
```
Here $`t`$ parametrises the segment. The product estimates below use $`f'(c)=0`$ and the ordering of distances, not the root-disc hypothesis; the latter enters when bounding the combined segment length. To explain the other parameter and the coefficient $`n(n-2)`$, suppose $`f(c)\ne0`$, order the roots $`a_1,\ldots,a_n`$ by distance from $`c`$, and set $`v_j=(a_2-c)/(a_j-c)`$. Then $`v_2=1`$, $`|v_j|\le1`$ for $`j\ge2`$, and $`\sum_jv_j=0`$ by $`f'(c)=0`$. With $`y=1-\Re v_1`$, this gives
``` math
y=2+\sum_{j=3}^n\Re v_j\in[4-n,n],\qquad |v_1|\le n-1.
```
Consequently
``` math
\begin{split}
 |1-tv_1|^2&\le(1-t)^2+2ty+n(n-2)t^2,\\
 \frac1{n-2}\sum_{j=3}^n|1-tv_j|^2
 &\le(1-t)^2+\frac{2t(n-y)}{n-2}.
\end{split}
```
The factor $`v_2=1`$ contributes $`(1-t)^2`$. Applying AM–GM to the remaining $`n-2`$ squared factors in $`f(c+t(a_2-c))/f(c)=\prod_j(1-tv_j)`$ gives the defining expression for $`M_n^2`$. Thus the maximisation is an explicit bound for the second segment, not an additional optimisation hypothesis about the roots.

For the nearer segment, put $`x_j=(a_1-c)/(a_j-c)`$. Now $`x_1=1`$, $`|x_j|\le1`$ for every $`j`$, and $`\sum_jx_j=0`$. Hence
``` math
\sum_{j=2}^n|1-tx_j|^2
 \le (n-1)(1+t^2)+2t,
```
so AM–GM gives
``` math
\left|\frac{f(c+t(a_1-c))}{f(c)}\right|^2
 \le(1-t)^2\left((1-t)^2+\frac{2tn}{n-1}\right)^{n-1}.
```
This bound is at most $`M_n^2`$ for every $`n\ge3`$, not just for numerically tested degrees. Indeed, set $`y=n/(n-1)`$ in the defining maximum. This value is admissible because $`n/(n-1)-(4-n)=(n-2)^2/(n-1)\ge0`$. The last factor then has base $`(1-t)^2+2tn/(n-1)`$, and the preceding factor has this same base plus $`n(n-2)t^2\ge0`$. Their product therefore dominates the displayed nearer-segment bound. Thus $`|f(z)|\le M_n|f(c)|`$ on both segments, so $`0<|f(c)|\le1/M_n`$ gives containment in $`\{|f|\le1\}`$; the critical-point distance estimate gives total length at most $`2`$. If $`f(c)=0`$, two root occurrences already coincide at $`c`$. The quadratic case is the direct root segment treated earlier. For degree five the maximum evaluates to
``` math
M_5=(1-t_*)(1+t_*)^3\sqrt{16t_*^2-4t_*+1},
 \qquad
 t_*=\frac{5}{16}+\frac{3\sqrt{105}}{80},
 \qquad
 \frac{1}{M_5}=0.2760461\ldots.
```
The breakpoint comes from the constraint on $`y`$, not from a numerical search. For fixed $`0<t<1`$, write the two bases in the definition of $`M_5`$ as
``` math
A=(1-t)^2+2ty+15t^2,\qquad
 B=(1-t)^2+\frac{2t(5-y)}3.
```
They are positive for $`-1\le y\le5`$, and $`\partial_y\log(AB^3)=2t(B-A)/(AB)`$. Thus the unconstrained maximum occurs at $`A=B`$, or $`y=5/4-45t/8`$. This reaches the lower endpoint $`-1`$ at $`t=2/5`$; thereafter the maximum is at $`y=-1`$. For $`0\le t\le2/5`$ the resulting expression is $`(1-t)(1+t/2+19t^2/4)^2`$, whose derivative is
``` math
\frac{5t(14-19t)(19t^2+2t+4)}{16}\ge0.
```
For $`2/5\le t\le1`$, the square of the resulting expression is $`(1-t)^2(1+t)^6(16t^2-4t+1)`$, whose derivative is
``` math
-4t(1-t)(1+t)^5(40t^2-25t-2).
```
The quadratic changes sign once on this interval, at $`t_*`$, so the second branch increases from the common breakpoint to $`t_*`$ and then decreases to zero. Since the first branch increases to that breakpoint, $`t_*`$ gives the global maximum. This proves the displayed value without sampling either optimisation variable. As an existence criterion this is weaker than the $`13/25`$ theorem. Its different content is the control of the two straight segments from the specified critical point, rather than a curve selected by area averaging. For $`z^5-b`$ it requires $`|b|\le1/M_5`$, so it excludes part of a binomial family already covered by the trinomial theorem. No claim is made that every quintic has a critical value below this level.

A near-regular pentagon illustrates why a prescribed joining point is restrictive. For sufficiently small $`\epsilon>0`$, set
``` math
P_\epsilon(z)=z^5+\epsilon^5z^4+\epsilon^3z^3
              -\epsilon^3z^2-\epsilon^5z-1,
 \quad F_\epsilon(z)=r^5P_\epsilon(z/r),\quad r=1-\epsilon^9.
```
All five roots of $`F_\epsilon`$ lie in the open unit disc, approach a regular pentagon, and have escaping segments from the origin. Here is a proof of that assertion, including the effect of the radial contraction.

The roots of $`P_\epsilon`$ are simple perturbations $`\zeta_\epsilon=\zeta_0+O(\epsilon^3)`$ of the fifth roots of unity. The identity
``` math
z^5\overline{P_\epsilon(1/\overline z)}=-P_\epsilon(z)
```
makes the roots invariant under conjugate inversion. Uniqueness of the root near each $`\zeta_0`$ therefore forces $`|\zeta_\epsilon|=1`$. The roots $`r\zeta_\epsilon`$ of $`F_\epsilon`$ consequently have modulus $`r<1`$. The displacement estimate follows from the implicit function theorem at each simple root of $`z^5-1`$, since the first coefficient perturbations have order $`\epsilon^3`$.

For $`\zeta_0=1,e^{4\pi i/5},e^{-4\pi i/5}`$, take $`t=\epsilon/4`$. Substitution into the polynomial gives
``` math
|F_\epsilon(rt\zeta_\epsilon)|^2
 =1+\left(\frac{\Re\zeta_0^2}{8}-\frac1{512}\right)\epsilon^5
       +O(\epsilon^6).
```
The coefficient is positive, since $`\Re\zeta_0^2\ge(\sqrt5-1)/4`$. For the remaining roots, with $`\zeta_0=e^{2\pi i/5}`$ or $`e^{-2\pi i/5}`$, take $`t=\epsilon^2/4`$ instead. Then
``` math
|F_\epsilon(rt\zeta_\epsilon)|^2
 =1+\frac{3\sqrt5-5}{32}\epsilon^7+O(\epsilon^9)>1
```
for sufficiently small $`\epsilon`$. The two scales are needed because $`\Re\zeta_0^2`$ is negative for this second pair; its positive linear contribution dominates at the smaller scale. Multiplication by $`r^{10}=1+O(\epsilon^9)`$ cannot remove either positive leading term. The remainders are uniform over the five root branches, so one sufficiently small $`\epsilon`$ works for every segment. This is an ordinary asymptotic proof; it gives no numerical upper bound for the permitted $`\epsilon`$.

The addendum \[revision2026, Proposition 1\] reports the stronger assertion that no critical point of this family supplies two contained straight arms of total length at most $`2`$. That proof is not supplied with this record and was not available for checking in this revision. The origin calculation above does not prove it: $`P_\epsilon'(0)=-\epsilon^5`$ shows that the origin is not a critical point. The stronger reported assertion is not used in any theorem here. Neither the proved failure at the origin nor the reported critical-point obstruction excludes curved inverse images of rays or a different joining point.

A different local question allows a freely chosen, noncritical vertex: for some $`\delta>0`$, does every monic quintic with open-disc roots within $`\delta`$ of a rotated regular pentagon admit two contained straight arms through some $`h\in\mathbb C`$ of total length below $`2`$? Neither the origin nor a critical point is prescribed in this question. The sufficient low-critical threshold preceding this paragraph is unchanged.

<a id="area-of-a-connected-sublevel-set."></a>

#### Area of a connected sublevel set.

The following calculation applies in every degree $`n\ge2`$, independently of the degree-five segment criterion. Let $`f`$ be monic of degree $`n`$ and let $`t>0`$ with $`K_t=\{|f|\le t\}`$ connected. Translate its root centroid to $`0`$, so $`f(z)=z^n+c_{n-2}z^{n-2}+\cdots`$, and let $`\psi`$ be the exterior map normalised at infinity with positive leading coefficient. For a regular connected lemniscate, the identity $`f(\psi(\zeta))=t\zeta^n`$ is \[eks2010, (2.3)\] after scaling the value level. The following argument also permits critical boundary points. The exterior Green functions $`(\log|f|-\log t)/n`$ and $`\log|\psi^{-1}|`$ agree: both vanish at the boundary and have a logarithmic pole of coefficient one at infinity. Comparison there gives the leading coefficient $`t^{1/n}`$ for $`\psi`$. The quotient $`f(\psi(\zeta))/(t\zeta^n)`$ has constant modulus one and limit one at infinity, proving the polynomial identity. Its $`\zeta^{n-1}`$ coefficient forces the constant Laurent coefficient of $`\psi`$ to vanish. Thus
``` math
\psi(\zeta)=t^{1/n}\zeta+\sum_{k\ge1}a_k\zeta^{-k}.
```

Grönwall’s area identity takes the form
``` math
\operatorname{Area}(K_t)=\pi\left(t^{2/n}-
 \sum_{k\ge1}k|a_k|^2\right).
```
One can obtain it directly without assuming that level $`t`$ is regular. For $`r>1`$, Green’s area formula on the analytic Jordan curve $`\psi(re^{i\theta})`$ gives the enclosed area $`\pi(t^{2/n}r^2-\sum_{k\ge1}k|a_k|^2r^{-2k})`$. These enclosed compact sets decrease to $`K_t`$ as $`r\downarrow1`$; continuity of area from above and monotone convergence of the series give the identity. Comparing the coefficient of $`\zeta^{n-2}`$ in the exterior identity now gives
``` math
nt^{(n-1)/n}a_1+c_{n-2}t^{(n-2)/n}=0,
 \qquad a_1=-\frac{c_{n-2}}{n\,t^{1/n}}.
```
The nonnegative coefficient sum quantifies the loss from Pólya’s upper bound. It does not by itself control an internal path length. No analogous coefficient formula for an individual component of a disconnected sublevel set is established here. The degree-five statements and their evidence classes are recorded in [the degree-five estimates and their proofs](https://github.com/wcook04/plectis-erdos/blob/f214a6b45528dc5eefe20ffadc35f2e981627d4c/research_corpus/Erdos1041/Degree5AssemblyAndSharpenedCuts.md).

<a id="numerical-tests-of-selection-by-the-smallest-critical-value"></a>

## Numerical tests of selection by the smallest critical value

Three examples distinguish critical-value bounds from path-length bounds. For a critical point $`c`$ whose two inverse arms over $`[0,f(c)]`$ reach roots, write $`L_f(c)`$ for their total length. The first computation tests the rule of choosing the critical point with uniquely smallest value modulus. The source gives an unnormalised quintic $`f_0`$, a selected critical point $`c_0`$, and the numerical values
``` math
L_{f_0}(c_0)\approx2.057343275393654508,
 \qquad R\approx1.021393477405696164,
```
where $`R`$ is the radius of a smallest disc containing the roots of $`f_0`$. The first number is not the length after normalisation to the unit disc. If $`h`$ is the centre of that disc, set
``` math
F(z)=R^{-5}f_0(h+Rz).
```
This preserves monicity, sends the roots into the closed unit disc, and divides every corresponding curve length by $`R`$. The reported normalised values are therefore
``` math
L_F\!\left(\frac{c_0-h}{R}\right)\approx2.01425143287505,
 \qquad
 \left|F\!\left(\frac{c_0-h}{R}\right)\right|
 \approx0.899569245.
```
A further contraction uses $`F_s(z)=s^5F(z/s)`$, with $`0<s<1`$: roots and curve lengths are multiplied by $`s`$, and critical values by $`s^5`$. Thus the reported excess would persist for $`s`$ sufficiently close to $`1`$, with roots in the open unit disc.

These are numerical observations, not a certified counterexample. A small residual at a computed fibre root does not enclose that root or establish its membership in the tracked inverse branch. The inscribed-polyline comparison needs both facts before it gives a rigorous lower bound for the intended arms. Another critical point supplies a shorter pair in the reported computation; this is evidence at that configuration, not a universal selection theorem.

Second, the linked record reports numerical violations of $`\sum_cL_f(c)\le2(n-1)R`$ in degrees four and five. Here $`R`$ is the radius of a smallest disc containing the roots. The quartic computation gives $`\sum_cL_f(c)=6.006352157\ldots`$ against the proposed bound $`6`$. Several differential-equation solvers agree, and an inscribed-polyline calculation using numerically computed fibre roots gives a similar excess. These checks do not provide rigorous enclosures for those roots, their branch assignment or the resulting length lower bound. They are evidence against the aggregate inequality, not a certified refutation or a proof that an open set of polynomials violates it. Its algebraic factor
``` math
\sum_{k=1}^{n-1}|f(c_k)|^{1/n}\le(n-1)R
```
is proved for every $`n\ge2`$ in Theorem <a href="#res:critical-value-budget" data-reference-type="ref" data-reference="res:critical-value-budget">24</a>. The value estimate alone supplies no bound for the associated path-length sum. The algebraic theorem therefore remains useful independently of how the numerical aggregate examples are resolved. The two computational records, to be read with the evidence limitations just stated, are [the numerical test of selection by the smallest critical value](https://github.com/wcook04/plectis-erdos/blob/f214a6b45528dc5eefe20ffadc35f2e981627d4c/research_corpus/Erdos1041/MinimalHubArmBudgetRefutation.md) and [the comparison between sums of critical values and path lengths](https://github.com/wcook04/plectis-erdos/blob/f214a6b45528dc5eefe20ffadc35f2e981627d4c/research_corpus/Erdos1041/SeparatrixAggregateReduction.md).

Third, all five origin segments can escape even when the roots are arbitrarily close to a regular pentagon. The two-scale calculation above proves this for the family $`F_\epsilon`$ attributed to the earlier note \[revision2026, Proposition A of the preserved earlier note\]; an isolated numerical example would not prove the assertion for arbitrarily small defects. Failure for every critical joining point is a different, stronger claim, reported in the addendum but not established by the origin calculation. No conclusion about curved inverse-ray paths or an arbitrary connector follows from either straight-segment assertion.

<a id="limits-of-contained-paths-at-fixed-degree"></a>

## Limits of contained paths at fixed degree

<div id="closed-class-limits">

</div>

The compactness argument used in Section 17 of the short note is given here in full. It concerns arbitrary contained curves, not a prescribed pair of inverse rays.

Fix $`n\ge2`$, and let $`\mathcal K_n`$ be the compact coefficient class of monic degree-$`n`$ polynomials with roots in the closed unit disc. Define
``` math
\Lambda(f)=\inf_\gamma\operatorname{length}(\gamma),
```
where $`\gamma\subset\{|f|\le1\}`$ joins two different listed root occurrences. A repeated root permits a constant curve; an empty set of competitors has infimum $`+\infty`$.

<a id="passing-a-length-bound-to-a-limit."></a>

#### Passing a length bound to a limit.

Let $`f_j\to f`$ in $`\mathcal K_n`$. If the lower limit of $`\Lambda(f_j)`$ is finite, pass to a subsequence on which these infima converge to it and choose rectifiable curves $`\gamma_j`$ with lengths at most $`\Lambda(f_j)+1/j`$. Every closed unit sublevel lies in $`|z|\le2`$: for $`|z|>2`$, the root factorization gives $`|f_j(z)|\ge(|z|-1)^n>1`$. Constant-speed parametrisation on $`[0,1]`$ therefore gives uniformly bounded images and Lipschitz constants. Arzelà–Ascoli supplies a uniformly convergent subsequence.

To retain the endpoints with their multiplicities, list the two chosen occurrences first among the roots of $`f_j`$, and list the remaining roots arbitrarily. Compactness of the product of $`n`$ closed unit discs gives a further subsequence on which this entire list converges. The limiting factorization is $`f`$, so its first two entries remain two occurrences, even if their locations coincide. Uniform convergence of the curves and of the polynomials on $`|z|\le2`$ gives $`|f|\le1`$ on the limiting curve $`\gamma`$. For any partition $`0=t_0<\cdots<t_M=1`$,
``` math
\sum_{\ell=1}^M|\gamma(t_\ell)-\gamma(t_{\ell-1})|
 =\lim_j\sum_{\ell=1}^M|\gamma_j(t_\ell)-\gamma_j(t_{\ell-1})|
 \le\liminf_j\operatorname{length}(\gamma_j).
```
Taking the supremum over partitions proves the required lower semicontinuity of length and hence $`\Lambda(f)\le\liminf_j\Lambda(f_j)`$. An infinite lower limit needs no argument. With $`f`$ fixed, the same compactness proof shows that a finite infimum is attained. Thus a bound $`\Lambda\le2`$ on a dense class gives an actual path of length at most $`2`$ throughout $`\mathcal K_n`$. For an open-disc polynomial, choose a containing disc of radius $`0<R<1`$ and scale: the resulting path has length at most $`2R<2`$ and lies in $`\{|f|\le R^n\}\subset\{|f|<1\}`$.

For $`f(z)=z^n-1`$, the inequality $`|z^n-1|\le1`$ implies $`2\Re(z^n)\ge|z|^{2n}>0`$ whenever $`z\ne0`$. Thus the punctured sublevel lies in $`n`$ disjoint angular sectors, one per root. A path between different roots must pass through zero and has length at least $`2`$ by the triangle inequality. The two radial segments attain that length. The corresponding historical assertion on the closed class is
``` math
\boxed{\Lambda(f)\le\Lambda(z^n-1)=2\qquad(f\in\mathcal K_n).}
```
The lower-semicontinuity argument is proved in [the compactness proof](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/GenericSufficiencyClosure.md).

The displayed universal inequality is recorded to explain the earlier reduction, not proposed here as a remaining open assertion. A counterexample to the original problem would also refute this inequality and, by the same compactness argument, any dense-class estimate implying it. The reduction can still be used for separately specified polynomial classes.

<a id="blaschke-product-examples-and-limits-in-varying-degree"></a>

## Blaschke-product examples and limits in varying degree

<div id="blaschke-product-examples">

</div>

The following family separates the limitations of the sufficient conditions from bounds for the actual shortest contained path.

The ordinary [note on powers of Blaschke products](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/BlaschkePowerCriticalSpectra.md) uses the degree-$`2N`$ polynomials
``` math
F_N(z)=[z(z+b)]^N-(1+bz)^N,\qquad N\ge1,\quad 0<b<1,
```
and their radial contractions. Its finite rational certificates and its asymptotic proofs have different roles. The degree-eight certificate excludes an unconditional critical-value exponent $`8/7`$. It does not contradict the ordinary exponent $`4/7`$ proved by the Poisson argument above, or the smaller exponent $`2/7`$ in the cited Lean theorem. For $`N\ge2`$, the root centroid of $`F_N`$ is $`-b/2`$, as its $`z^{2N-1}`$ coefficient is $`Nb`$. A radial contraction by $`r>0`$ changes this to $`-rb/2`$, not zero. Thus the degree-eight example does not satisfy the additional centroid condition that permits numerator $`8`$ above. The degree-twenty-four certificate gives critical values in $`|v+1|<1/12`$, so $`\mu>11/12`$ while every radius-$`4/3`$ separation test fails. These fixed-degree examples do not establish optimality uniformly in degree. That conclusion uses the limiting measures in Sections 2–3 of the linked full proof.

For $`b=\lambda/N`$ with fixed $`0<\lambda\le1`$, Section 4 constructs connectors of length at most $`[\log(2/\lambda)+\pi+o(1)]/N`$. The two radial pieces reduce the oscillatory term; a short circular arc then joins them in a sector where the remaining factor has modulus below one. The unspecified starting degree depends on $`\lambda`$. For $`b=e^{-\alpha N}/N`$ with fixed $`\alpha>0`$, the same section instead proves $`\Lambda(F_N)\to2(1-e^{-\alpha/2})`$ for the uncontracted polynomials $`F_N`$ displayed above and the closed-level functional defined earlier. The second assertion is a separate argument, not a substitution of a varying parameter into the first. Both are ordinary asymptotic arguments, not consequences of the finite certificates or formally checked analytic theorems. They concern varying degree and do not contradict fixed-degree compactness or prove the unrestricted assertion.

<a id="what-the-earlier-inverse-ray-approach-would-have-required"></a>

## What the earlier inverse-ray approach would have required

The earlier proposed sufficient condition concerned *curved* inverse images of rays, not straight segments. On a generic ray-separated class let $`L_f(c)`$ be the length of the two-root descent arc at an admissible critical point, where $`|f(c)|\le1`$. Then
``` math
\min_{c\ \mathrm{admissible}}L_f(c)\le2
```
would imply the root-connector conclusion by the stated compactness argument. The unrestricted infimum over all contained curves can be smaller; equality of these two optimisation problems is not assumed. The obstruction to two straight segments through a critical point does not by itself prove or disprove this curved-arc estimate. Examples in which another critical point gives a shorter curve do not prove the estimate universally. The critical value bound, containment and length bound must hold for the same curve. The displayed universal inequality is recorded as a historical sufficient condition, not proposed as an open assertion: a counterexample to the original question would refute it as well. The reduction remains useful on separately specified polynomial classes.

<a id="sec:newton"></a>

# The Newton value equation

Sutherland uses the term Newton flow for $`\dot z=-f(z)/f'(z)`$ and notes that its solution curves map under $`f`$ to radial lines \[sutherland1992, p. 42\]. The value equation \[kozen-stefansson1997, Lemma 2.1\] determines their orientation and time parametrisation. The global Newtonian graph \[kozen-stefansson1997, §2\], described with its endpoint conventions below, is a separate input to the inverse-sheet discussion in Section <a href="#sec:gap" data-reference-type="ref" data-reference="sec:gap">11</a>.

A Newton trajectory is a differentiable curve satisfying
``` math
z'(t)=-\frac{f(z(t))}{f'(z(t))}
```
where $`f'(z(t))\ne0`$. Let $`I\subseteq\mathbb R`$ be an interval on which these assumptions hold; put $`w(t)=f(z(t))`$. Kozen and Stefánsson record the following identity as a lemma of Shub, Tischler and Williams \[kozen-stefansson1997, Lemma 2.1\].

<div id="res:value" class="theorem">

**Theorem 26** (value equation). *Let $`f`$ be a polynomial and $`z:I\to\mathbb C`$ a differentiable curve on an interval $`I`$, with $`f'(z(t))\ne0`$ and $`z'(t)=-f(z(t))/f'(z(t))`$ throughout $`I`$. For $`w=f\circ z`$, one has $`w'(t)=-w(t)`$ on $`I`$.*

</div>

Lean: [newton real value whole](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/NewtonRealTime.lean#L52).

The computation is one line: $`w'=f'(z)\,z'=f'(z)\cdot(-f(z)/f'(z))=-f(z)=-w`$. The kernel checks the local complex-parameter chain rule as [the derivative of the polynomial value along a Newton trajectory](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L50), together with the differential form of the first integral, [the derivative of the exponentially rescaled value](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L64):
``` math
\frac{d}{dt}\Bigl(e^{t}f(z(t))\Bigr)=0.
```
Equivalently,
``` math
f(z(t))=e^{-(t-t_0)}f(z(t_0)),\qquad t_0\le t,\quad t_0,t\in I .
```
Integration on the real interval gives the last identity as an ordinary consequence of the differential equation. For an existing trajectory with nonzero initial value, its value moves inward on one positive ray; a zero value has no argument and remains zero. Thus $`|f|<1`$ is preserved for later times in that trajectory’s existing interval. No global existence or description of a whole ray preimage follows from this scalar equation. The real-time candidate endpoint is [the real-time value equation](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/NewtonFlowTrajectory.lean) in [the real-time trajectory source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/NewtonFlowTrajectory.lean).

<div id="res:ray" class="corollary">

**Corollary 27** (ray separation). *Let $`a<b`$ and let the value trajectory $`t\mapsto f(z(t))`$ be continuous on $`[a,b]`$. Assume the Newton equation and $`f'(z(t))\ne0`$ on $`(a,b)`$ only. Then
``` math
f(z(b))=e^{a-b}f(z(a)).
```
If these endpoint values are nonzero, they lie on one positive ray. Therefore critical points with values on distinct positive rays cannot be endpoints of such a finite connection. The trajectory in the $`z`$ plane need not be radial.*

</div>

Lean: [newton real endpoint whole](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/NewtonRealTime.lean#L69).

The interior identity passes to the endpoints by continuity, not by evaluating $`-f/f'`$ at a critical endpoint. The candidate declarations [value decay at continuous endpoints](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/PaperNewtonEndpoints.lean) and [no finite connection of distinct value rays](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/PaperNewtonEndpoints.lean) in [the trajectory endpoint source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos1041/PaperNewtonEndpoints.lean) make these premises explicit. Their compilation and axiom checks are not reported here. They construct no trajectories and supply no global monodromy theorem. Kozen and Stefánsson draw the same ray consequence for the Newtonian graph: under $`f`$, every edge maps onto a segment of a ray through the origin whose endpoints are $`0`$ or critical values \[kozen-stefansson1997, §2\].

<a id="sec:arguments"></a>

# Arguments, not moduli

It is tempting to arrange a generic perturbation so that the critical values are pairwise distinct, or that their moduli are pairwise distinct, and to conclude that saddle connections are excluded. Neither is enough.

Along a Newton trajectory the argument of $`f`$ stays constant while its modulus decreases. By Corollary <a href="#res:ray" data-reference-type="ref" data-reference="res:ray">27</a>, arranging pairwise distinct arguments of the nonzero critical values is therefore a sufficient way to exclude finite connections between critical points. It is not asserted to be necessary. This condition imposes no lower bound on the distances between critical values and no upper bound on their moduli.

The weaker conditions really can coexist with a connection, even when all roots lie in the open unit disc. Take
``` math
f(z)=z^3-\frac3{16}z+\frac3{64}.
```
On $`|z|=1`$, the lower terms have total modulus at most $`15/64<1`$, so Rouché’s theorem places all three roots inside. The critical points are $`-1/4`$ and $`1/4`$, with distinct positive values $`5/64`$ and $`1/64`$. On the intervening real interval $`f`$ is positive and strictly decreasing. The equation
``` math
f(x(t))=\frac5{64}e^{-t},\qquad 0<t<\log5,
```
therefore defines a differentiable path with $`x'(t)=-f(x(t))/f'(x(t))`$. Its endpoint limits are $`-1/4`$ and $`1/4`$. It is an actual critical-to-critical Newton trajectory, not merely a pair of values on one ray. The time convention is that of the value equation \[kozen-stefansson1997, Lemma 2.1\]; the singular field is not evaluated at the endpoints.

A common translation of distinct values can separate their arguments. The next calculation describes the translations to avoid.

<div id="res:locus" class="theorem">

**Theorem 28** (ray-collision locus). *Let $`a\ne b`$ be complex. Every common translation $`\beta`$ for which $`a+\beta`$ and $`b+\beta`$ lie on the same positive ray has the form
``` math
\beta=\frac{ra-b}{1-r},
  \qquad r\in\mathbb{R}_{>0},\ r\ne1 .
```*

</div>

Lean: [translated same positive ray parameterization](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L107).

Indeed, write $`b+\beta=r(a+\beta)`$ with $`r>0`$. Since $`a\ne b`$, one has $`r\ne1`$, and solving for $`\beta`$ gives the displayed formula. Equivalently, $`\beta=-a+(a-b)/(1-r)`$, so the forbidden translations lie on the real affine line through $`-a`$ and $`-b`$.

The formula is checked as [translations that put two values on one ray](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L107). A finite union of these loci has empty interior. Adding a constant to $`f`$ translates all critical values by that constant and leaves the critical points unchanged. Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">13</a> records the formal avoidance and root-retention estimates. A constant cannot separate equal critical values; coefficient perturbation and control of the remaining geometric margins are separate requirements.

<a id="sec:gap"></a>

# Why the proposed spanning-tree estimate fails

Recent work on polynomial lemniscates separates component counts from metric path questions. Ghosh and Ramachandran record that the open set $`\{|f|<1\}`$ has $`1+\#\{j:|f(c_j)|\ge1\}`$ components, where $`c_1,\ldots,c_{n-1}`$ are the critical points listed with multiplicity \[ghosh2023, Lemma 2.5\]; the underlying component-wise Riemann–Hurwitz count appears in the proof of \[eks2010, Proposition 2.1\]. For the binomial family $`z^n-a`$, the condition $`|a|<1`$ therefore puts the filled unit lemniscate in the connected regime. Connectedness alone gives no path-length bound. Bishop, Eremenko and Lazebnik describe the possible shapes: every rational lemniscate is a lemniscate graph whose vertices are the critical points on the level set, each of even degree at least four \[bishoperemenkolazebnik2025, Definition 1.2 and Proposition 2.4\], and a lemniscate graph is realised by a polynomial lemniscate up to a homeomorphism of the plane exactly when it is the boundary of its unbounded face \[bishoperemenkolazebnik2025, Corollary 1.6\]. This topological description also gives no path-length bound.

The March manuscript’s Proposition 12 claims the following estimate. For $`u=-\log|f|`$, a connected component $`V`$ of $`\{u>c\}`$ carrying $`m\ge2`$ simple zeros, and the regularity and Morse hypotheses in that proposition, it constructs, for every $`\varepsilon>0`$, an embedded spanning tree $`G_\varepsilon\subset V`$ with
``` math
\operatorname{len}(G_\varepsilon)
 \le\frac1{2\pi}\int_{2\alpha}^{\infty}P_V(t)\,dt+\varepsilon.
\tag{5.1}\label{eq:prop12-bound}
```
Here $`P_V(t)=\mathcal H^1(V\cap\{u=t\})`$ is the length of the level set in $`V`$, and $`\alpha>0`$ is the truncation parameter in the proposed estimate. The final theorem depends on this bound.

The estimate itself is false. Take $`f_a(z)=z^2-a^2`$ with $`a=9/10`$ and choose $`2\alpha=-\log a`$. For $`0<c<\alpha/2`$, the component $`V`$ of $`\{-\log|f_a|>c\}`$ contains $`\{|f_a|\le a\}`$ and both roots. The only critical point is a nondegenerate saddle at $`0`$; distinctness of critical values is vacuous.

Here the level-length integral can be bounded directly. Put $`r=e^{-t}`$. On a regular level the inverse parametrisations $`z=\pm\sqrt{a^2+re^{i\theta}}`$ give
``` math
P_V(t)=r\int_0^{2\pi}|a^2+re^{i\theta}|^{-1/2}\,d\theta.
```
The elementary identity
``` math
|a^2+re^{i\theta}|^2
 =(a^2+r)^2\cos^2(\theta/2)+(a^2-r)^2\sin^2(\theta/2)
```
implies
``` math
|a^2+re^{i\theta}|^{-1/2}
 \le(a^2+r)^{-1/2}|\cos(\theta/2)|^{-1/2}.
```
The angular factor has mean at most $`2`$. Indeed, symmetry reduces its integral to $`4\int_0^{\pi/2}(\cos s)^{-1/2}\,ds`$, and $`\cos s\ge1-2s/\pi`$ bounds the latter integral by $`4\pi`$. Changing variables from $`t`$ to $`r`$ therefore gives
``` math
\frac1{2\pi}\int_{2\alpha}^{\infty}P_V(t)\,dt
 \le2\int_0^a\frac{dr}{\sqrt{a^2+r}}
 =4\bigl(\sqrt{a^2+a}-a\bigr)<\frac{41}{25}.
```
The isolated critical level is handled by the corresponding improper integral. Every connected set containing both roots has length at least $`2a=9/5`$. Since $`9/5-41/25=4/25`$, any $`0<\varepsilon<4/25`$ contradicts <a href="#eq:prop12-bound" data-reference-type="eqref" data-reference="eq:prop12-bound">[eq:prop12-bound]</a>. Thus neither a different local saddle neighbourhood nor a perfect topological decomposition can recover the printed coefficient $`1/(2\pi)`$. Lean checks the exact numerical inequality and the resulting contradiction for a tree-length bound. The level-length majorant remains an explicit analytic input; the integral evaluation is not checked by that formal proof.

At an interior index-one critical point $`p`$, the proof invokes a Morse chart
``` math
u=u(p)+x^2-y^2
```
and replaces the saddle by a three-ended neighbourhood having one connected lower cross-section and two connected upper cross-sections. That local model is false as written. Because $`p\in V`$ and $`V`$ is open, a sufficiently small closed disc around $`p`$ lies entirely in $`V`$. In that disc the full Morse chart has four sectors: two components of $`u>u(p)`$ and two components of $`u<u(p)`$. The level set $`\{u=u(p)\}`$ is a lemniscate graph with a vertex of degree four at $`p`$ \[bishoperemenkolazebnik2025, Definition 1.2 and Proposition 2.4\]. A global component argument cannot delete one local sector from a disc already contained in $`V`$.

This independently diagnoses a proof step, but the Cassini witness above also refutes the proposition’s printed metric statement. A different route might cut an adjoining regular annulus along a separatrix or regular flow arc before forming the block, retain a four-pronged saddle neighbourhood and change the assembly, or replace the local construction by the ray-cut decomposition proposed below. But no repair can retain <a href="#eq:prop12-bound" data-reference-type="eqref" data-reference="eq:prop12-bound">[eq:prop12-bound]</a>; it must pay a positive attachment cost, select only one short pair instead of spanning every root, or use a different global metric inequality. The shorter descriptions of the same three-ended block do not repair the four-sector topology.

There is an ordinary topological theorem when the critical values have pairwise distinct arguments and moduli, and the critical points are simple. Its ingredients are classical: the Newtonian graph of Shub, Tischler and Williams \[kozen-stefansson1997, §2\], the component-wise Riemann–Hurwitz count in the proof of \[eks2010, Proposition 2.1\], and the division of the Riemann surface of the inverse function into sheets by outward critical-value slits. Dubinin describes the sheet adjacency tree directly in \[dubinin2006critical, §1, pp. 1169–1170\] and uses a related network for capacity in \[dubinin2006capacity, §2, pp. 34–35\]. The latter paper assumes bounded critical values and controls capacity; it does not supply a Euclidean tree-length bound. The theorem below specifies the sheets, critical transpositions and descent arcs for the stated component.

The assumptions exclude a component containing a multiple critical point or two critical values on the same ray. For $`z^n-b`$ with $`n>2`$ and $`0<|b|<1`$, the component containing the origin fails the first condition. They hold, for example, for $`f(z)=z^3-(3/25)z+1/500`$: its critical points are $`\pm1/5`$ and its critical values are $`-7/500`$ and $`9/500`$. On the unit circle the two lower terms have total modulus at most $`61/500<1`$, so all three roots lie in the open unit disc by Rouché’s theorem. In the statement, “excellent” means that the critical levels of the Morse function are pairwise distinct. This regularity permits a decomposition into sheets; it does not bound the total length of the resulting tree.

<div id="inverse-sheet-component">

</div>

<div id="res:attachment-aware-reeb" class="theorem">

**Theorem 29** (inverse sheets with distinct critical-value arguments). *Let $`f`$ be monic, and let $`U`$ be a component of $`\{|f|<1\}`$ containing $`k\ge2`$ roots, counted with multiplicity. Suppose every critical point of $`f`$ in $`U`$ is simple, its critical value is nonzero, and these critical values have pairwise distinct arguments and pairwise distinct moduli. All preimages and sheets below are taken inside $`U`$, and only critical points in $`U`$ determine the cuts. Then:*

1.  *$`-\log|f|:U\mathbin{\backslash}f^{-1}(0)\to(0,\infty)`$ is a proper excellent Morse function, with exactly $`k-1`$ nondegenerate saddles;*

2.  *cutting $`\mathbb D\smallsetminus\{0\}`$ along the critical-value rays decomposes its preimage in $`U`$ into conformal strips;*

3.  *cutting each ray only from its critical value to the unit circle gives $`k`$ conformal sheets, one per root, whose critical transpositions form a tree;*

4.  *for each critical point $`c\in U`$, the two inverse lifts of $`[0,f(c)]`$ join two roots through $`c`$ inside $`U\cap\{|f|\le|f(c)|\}`$, and the union of these arcs is an embedded geometric realisation of that tree.*

*Small neighbourhoods of the saddles can be chosen with diameter $`O(\sqrt\delta)`$ at value radius $`\delta`$.*

</div>

Not formalised: the ray-disjointness, level-separation and saddle-scale steps of the proof are checked, and the Morse, monodromy and strip statements are not. See the [coverage section](#sec:coverage).

<div class="proof">

*Proof.* The map $`f:U\to\mathbb D`$ is proper of degree $`k`$, and $`U`$ is simply connected. To apply the count from the proof of \[eks2010, Proposition 2.1\] only at a regular level, join all roots and critical points in $`U`$ by finitely many compact paths in $`U`$. Choose a regular $`t<1`$ above the maximum of $`|f|`$ on their union. One component of $`\{|f|<t\}`$ then contains exactly the roots and critical points of $`U`$; Riemann–Hurwitz there gives $`k-1`$ simple critical points. No regularity of the level-one boundary is needed. The holomorphic Morse lemma makes these points nondegenerate saddles of $`-\log|f|`$, and their distinct moduli separate the critical levels. A compact range in $`(0,\infty)`$ stays away from both the level-one boundary and the deleted roots, proving properness of the Morse function.

Remove $`0`$ and the rays determined by these $`k-1`$ values. Each remaining sector is simply connected and contains no branch value of $`f:U\to\mathbb D`$, even if it contains critical values coming from outside $`U`$. Each component of its preimage in $`U`$ maps biholomorphically to the sector. If the sector has angular range $`(\theta_1,\theta_2)`$, the holomorphic coordinate $`-\log f`$ maps this component onto the semi-infinite strip
``` math
\{x+iy:x>0,\ -\theta_2<y<-\theta_1\}.
```
Thus its real coordinate is $`-\log|f|`$, while its imaginary coordinate is $`-\arg f`$. The minus sign in both coordinates is needed for a holomorphic map; keeping $`+\arg f`$ would reverse orientation.

For the sheet tree, remove only the outward slits $`\{tf(c):1\le t<1/|f(c)|\}`$, for critical points $`c\in U`$. The remaining value domain is star-shaped about $`0`$, hence simply connected, and its preimage in $`U`$ splits into $`k`$ sheets labelled by the roots. Local monodromy at each slit endpoint is a transposition of two of these sheets. Deleting the finitely many fibres over the branch values from $`U`$ leaves a connected domain, so the monodromy action is transitive. The $`k-1`$ transpositions therefore give a connected graph with $`k`$ vertices, which is a tree.

For $`c\in U`$, the inward segment from $`f(c)`$ to $`0`$ contains no other branch value of $`f:U\to\mathbb D`$, by the distinct-argument hypothesis. Distinct moduli were needed only to separate the Morse levels. Its two inverse lifts converge to $`c`$ by the holomorphic Morse coordinate and start at the two root labels exchanged by its transposition. These labels are distinct, as are the roots, because a root in $`U`$ cannot also be a critical point under the nonzero-critical-value hypothesis. Lifts belonging to different critical points cannot cross away from roots, since an intersection would give one nonzero value on two critical rays. Their union is therefore an embedded tree. Each edge is rectifiable: at a simple critical endpoint, parametrising the value segment by its distance $`s`$ from the critical value gives speed $`O(s^{-1/2})`$, which is integrable. The root endpoint is regular, and the derivative is bounded on compact subsegments between the endpoints. This proves finiteness of each length, not a uniform bound for it. The same local Morse coordinate identifies a value disc of radius $`\delta`$ with a spatial neighbourhood of diameter $`O(\sqrt\delta)`$. The constant and the permitted range of $`\delta`$ depend on $`f`$ and the chosen saddle. Indeed, in the coordinate $`f(z)-f(c)=u^2`$, the inverse map has derivative of modulus $`\sqrt{2/|f''(c)|}`$ at $`u=0`$. No bound uniform over degenerating critical points is asserted. For a fixed polynomial there are finitely many saddles, so their individual constants have a finite maximum. ◻

</div>

The complete ordinary argument is recorded in [the proof of the decomposition into inverse sheets](https://github.com/wcook04/plectis-erdos/blob/a729f05c40398663fd586c9da487ad874d898639/research_corpus/Erdos1041/AttachmentAwareReeb.md). Its Lean companion checks the ray-distance, averaging and finite-tree kernels; it explicitly does not formalise Riemann–Hurwitz, monodromy, the strip diffeomorphisms or the geometric assembly. The theorem supplies topology, not a useful length sum: the canonical inverse-ray tree can already have the Cassini deficit discussed above.

The component restriction cannot be dropped. For example, take
``` math
f(z)=(z^2-4)^2-\tfrac14.
```
Its critical points are $`0,\pm2`$, with values $`63/4,-1/4,-1/4`$. The positive roots $`\sqrt{7/2}`$ and $`\sqrt{9/2}`$ lie in one component $`U`$: on the intervening real interval, $`-1/4\le f\le0`$. But $`f(iy)=(y^2+4)^2-1/4>1`$ for real $`y`$, so this component cannot contain the negative roots or $`-2`$. Its only critical point is the simple point $`2`$. Thus the theorem applies in $`U`$, although the other component has the same critical value. This example concerns component topology; no root-unit-disc hypothesis is imposed here.

Corollary <a href="#res:ray" data-reference-type="ref" data-reference="res:ray">27</a> also excludes finite saddle-to-saddle Newton connections inside $`U`$. The theorem does not treat coincident arguments, simultaneous critical levels or multiple saddles in that component. Nor does it identify a slit domain with the quotient by all trajectories: the quadratic example following Problem <a href="#prob:globalflow1041" data-reference-type="ref" data-reference="prob:globalflow1041">34</a> satisfies its hypotheses but has a non-Hausdorff orbit quotient. Boundary tangencies and quantitative strip attachment remain separate questions. The embedded tree supplies no length bound for the historical question.

<a id="sec:finite"></a>

# Numerical path searches

A search was run over random monic polynomials with roots in the unit disc. For each sample the region $`\{|f|<1\}`$ was rasterised and shortest grid paths were computed between every pair of roots. The reported grid distances were
``` math
\begin{array}{lrr}
    \text{degree } 5, & 500 \text{ trials}: & 1.1052648928\\
    \text{degree } 6, & 1500 \text{ trials}: & 0.8450414343\\
    \text{degree } 8, & 1500 \text{ trials}: & 0.6203916714\\
    \text{degree } 10, & 1500 \text{ trials}: & 0.4303640486 .
  \end{array}
```
No counterexample candidate was found, and the measured values sit well below the threshold $`2`$. These are numerical candidate connectors. A polygon whose vertices satisfy $`|f|<1`$ need not lie in the open lemniscate, since an edge can cross the boundary between two safe vertices, and root snapping adds further edges of the same kind. Turning a candidate into a proof needs a continuous certificate on every edge, for instance strict positivity of the real polynomial $`1-|f(z(t))|^2`$ on $`[0,1]`$ for each straight edge $`z(t)=u+t(v-u)`$, established by exact coefficients or outward-rounded interval arithmetic with subdivision, together with exact root enclosures. No such certificate is attached to the numbers above. They are grid distances for the sampled configurations, and the apparent decrease with degree is a property of the sample, from which we draw no conjecture. Even a finite collection of proved instances would not establish the universal statement. These searches do not test `ani`’s degree-seven counterexample. Useful stress tests for particular path constructions include near-degenerate saddles, thin necks, boundary-critical configurations, and almost-connected separatrices. They should report those diagnostics. Raster paths remain candidate finders, never continuous certificates.

<a id="sec:open"></a>

# Further questions about topology, length and perturbation

The questions below separate topological, metric and perturbative steps of earlier arguments. They are retained for their own content, not as a claim that completing them must prove the unrestricted historical assertion. A counterexample or a necessary additional hypothesis can be as informative as a positive theorem.

<a id="local-saddle-geometry-and-the-refuted-tree-estimate"></a>

## 1. Local saddle geometry and the refuted tree estimate

<div id="prob:saddle1041" class="problem">

**Problem 30** (corrected local saddle assembly). The printed $`1/(2\pi)`$ spanning-tree estimate of Proposition 12 is false: the Cassini polynomial $`z^2-a^2`$ at $`a=9/10`$ makes the proposed tree budget strictly shorter than the distance between its roots. Any later argument must pay a positive attachment cost, select only one short pair instead of spanning every root, or use a different global metric inequality. A four-pronged or cut-annulus local model may still be useful for another estimate, but it cannot recover <a href="#eq:prop12-bound" data-reference-type="eqref" data-reference="eq:prop12-bound">[eq:prop12-bound]</a>.

</div>

The full-disc model $`x^2-y^2`$, an annulus in which lower branches rejoin, two saddles joined by a separatrix and simultaneous saddle levels are mandatory tests. Repeating the one-lower/two-upper assertion does not answer the problem.

<a id="cutting-a-compact-region-into-flow-strips"></a>

## 2. Cutting a compact region into flow strips

Let $`p`$ be a polynomial with simple roots and simple critical points, and set $`u=-\log|p|`$ away from the roots. Simplicity of the roots makes every critical value nonzero; critical points themselves may lie at $`0`$. For regular values $`c<T`$, let $`V`$ be a component of $`\{u>c\}`$ and assume that $`\overline{V\cap\{c<u<T\}}`$ is a compact genus-zero surface, its lower boundary is one smooth Jordan curve, its upper boundary consists of $`m`$ smooth level curves each enclosing one root, all interior critical points are nondegenerate index-one saddles, the normalised gradient field, defined away from the saddles,
``` math
X=\frac{\nabla u}{|\nabla u|^2}=-\frac{p}{p'},
```
is transverse to the level boundaries, and no maximal $`X`$-trajectory has two saddle endpoints. The equality uses the identification of a planar vector with a complex number: $`\nabla u=-\overline{p'/p}`$. In particular, $`du(X)=1`$ wherever $`X`$ is defined.

<div id="prob:reeb1041" class="problem">

**Problem 31** (finite strip decomposition after ray cuts). For every $`\eta>0`$, construct disjoint Morse neighbourhoods $`N_j`$ with $`\sum_j\operatorname{diam}N_j<\eta`$ and a finite set of complete separatrix or regular-flow cuts so that the closure of each remaining component in the cut-open surface is flow-diffeomorphic to a rectangle
``` math
[a_S,b_S]\times[0,1],\qquad u=t,
```
with connected level sections and no uncut annular component. Give an explicit finite bound for the number of strips in terms of the number $`s`$ of saddles and the number $`m`$ of upper boundary curves, or exhibit the minimal missing hypothesis or a counterexample.

</div>

No particular formula such as $`2s+1`$ is presumed. Boundary tangencies, simultaneous levels and branch reunion through an annulus require explicit cuts. The closure is taken in the cut-open surface, with its separate boundary copies, not after regluing them in the plane. The quadratic example following Problem <a href="#prob:globalflow1041" data-reference-type="ref" data-reference="prob:globalflow1041">34</a> explains why replacing this construction by the ordinary orbit quotient would fail.

<a id="length-estimates-for-joining-flow-strips"></a>

## 3. Length estimates for joining flow strips

For a strip $`S`$, write
``` math
\Gamma_t^S=S\cap\{u=t\},\qquad
 P_S(t)=\mathcal H^1(\Gamma_t^S),
```
and write
``` math
\Phi_S(t)=\int_{\Gamma_t^S}|\nabla u|\,ds
```
for its transverse flux. On a regular sub-band, $`u`$ is harmonic and the side boundaries are flow lines. The divergence theorem therefore makes $`\Phi_S(t)`$ independent of $`t`$. Normalise the transverse measure by
``` math
d\mu_{t_0}(x)=\frac{|\nabla u(x)|}{\Phi_S(t_0)}\,ds(x).
```
The choice of measure is determined by the length calculation. Since $`u=t`$ along the normalised flow, its Euclidean speed is $`1/|\nabla u|`$. Transporting the flux measure to level $`t`$ therefore gives
``` math
\begin{aligned}
 \int_{\Gamma_{t_0}^S}\operatorname{len}(\gamma_x)\,d\mu_{t_0}(x)
 &=\int_{a_S}^{b_S}\int_{\Gamma_t^S}
    \frac1{|\nabla u|}\frac{|\nabla u|}{\Phi_S(t_0)}\,ds\,dt\\
 &=\frac1{\Phi_S(t_0)}\int_{a_S}^{b_S}P_S(t)\,dt .
 \end{aligned}
```
Here $`0<\Phi_S(t_0)<\infty`$ for a nonempty regular strip. Tonelli’s theorem applies to the nonnegative integrand. At a critical endpoint level, exhaustion through regular sub-bands gives the same identity, allowing the common value to be infinite. A finite right side gives a trajectory of length at most that mean; an identity with both sides infinite gives no length estimate. A strip flux need not be an integer multiple of $`2\pi`$. For $`f(z)=z`$ and $`u=-\log|z|`$, take an annular sector of angular width $`\theta`$. On a circular level arc, $`|\nabla u|=1/r`$ and $`ds=r\,d\phi`$, so its flux is $`\Phi_S=\theta`$. For $`f(z)=z^n`$, the same calculation gives $`\Phi_S=n\theta`$. A closed regular level curve enclosing $`k`$ roots has flux $`2\pi k`$ by the argument principle. Restricting it to a strip replaces that full winding by the strip’s share of the flux. The averaging measure therefore depends on the width of the strip. Summing separate strip estimates cannot replace those widths by the winding number of a closed level curve. They do not reopen <a href="#eq:prop12-bound" data-reference-type="eqref" data-reference="eq:prop12-bound">[eq:prop12-bound]</a>. Cassini already excludes the printed coefficient $`1/(2\pi)`$ for any embedded tree that contains all $`m`$ roots: Problem <a href="#prob:saddle1041" data-reference-type="ref" data-reference="prob:saddle1041">30</a> records that no later gluing argument can retain that estimate.

<div id="prob:metric1041" class="problem">

**Problem 32** (strip gluing after the printed coefficient). Assuming Problem <a href="#prob:reeb1041" data-reference-type="ref" data-reference="prob:reeb1041">31</a>, do one of the following, for every $`\eta>0`$.

1.  Produce an embedded tree $`G`$ containing all $`m`$ roots whose length obeys
    ``` math
    \begin{equation*}
     \operatorname{len}(G)
     \le C\int_{2\alpha}^{\infty}P_V(t)\,dt+\eta
    \tag{6.1}\label{eq:metric-fanin1041}
    \end{equation*}
    ```
    for an explicit constant $`C>1/(2\pi)`$, uniform over a stated class of polynomials and an explicitly restricted range of truncations $`\alpha`$. The restrictions must account for attachment cost and for a valid allocation of the strip fluxes $`\Phi_S`$.

2.  Connect only one pair of distinct roots, rather than spanning every root.

3.  Give a different global metric inequality that is not <a href="#eq:prop12-bound" data-reference-type="eqref" data-reference="eq:prop12-bound">[eq:prop12-bound]</a>.

The printed coefficient $`1/(2\pi)`$ is not an open target. Better additive control of saddle, annular-cut and root-cap cost cannot recover <a href="#eq:prop12-bound" data-reference-type="eqref" data-reference="eq:prop12-bound">[eq:prop12-bound]</a>.

</div>

The restriction on $`\alpha`$ is essential in the first alternative. For a fixed $`f(z)=z^2-a^2`$, with $`0<a<1`$, choose $`0<c<-2\log a`$ and let $`V`$ be the component of $`\{-\log|f|>c\}`$ containing both roots. At sufficiently deep levels, the Cassini parametrisation used above gives
``` math
P_V(t)\le\frac{2\pi e^{-t}}{\sqrt{a^2-e^{-t}}}.
```
Consequently $`\int_{2\alpha}^\infty P_V(t)\,dt\to0`$ as $`\alpha\to\infty`$, whereas every spanning tree has length at least $`2a`$. No fixed $`C`$ can cover arbitrary truncations. This is a limitation of the unrestricted formulation of (6.1), separate from the earlier counterexample to the particular coefficient $`1/(2\pi)`$.

The printed collar slack
``` math
q=\frac1{2\pi}\int_{\alpha}^{2\alpha}P_V(t)\,dt>0
```
used the same excluded coefficient. It is not an unused error allowance in an otherwise complete spanning-tree estimate. Independently choosing a shortest trajectory in each strip is not enough unless the attachment mismatch is controlled, and controlling that mismatch does not restore the printed $`1/(2\pi)`$ tree bound.

<a id="coefficient-perturbation-and-stability"></a>

## 4. Coefficient perturbation and stability

The constant-translation stage is no longer open. Once a finite critical-value family is injective, Lean proves an arbitrarily small translation making every value nonzero and pairwise positive-ray separated ([a small translation separating the arguments](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L197)). It also proves the explicit root-retention estimate: for a monic polynomial $`f`$ of degree $`n\ge1`$, a constant shift of modulus below $`\varepsilon>0`$ keeps all roots in the unit disc provided
``` math
((n+1)\varepsilon)^{1/n}+\max_{f(b)=0}|b|<1
```
([the root-retention estimate for the unit disc](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L287)). Adding a constant leaves the difference of two critical values unchanged, so it cannot separate values that were equal to begin with.

For a constant shift alone, factorisation gives the sharper elementary bound
``` math
(f+\beta)(z)=0\quad\Longrightarrow\quad
 \prod_{f(b)=0}|z-b|=|\beta|
 \quad\Longrightarrow\quad
 \min_{f(b)=0}|z-b|\le|\beta|^{1/n},
```
where the product counts roots with multiplicity. Hence $`\max_{f(b)=0}|b|+|\beta|^{1/n}<1`$ already ensures retention in the open unit disc. The factor $`n+1`$ in the recorded Lean estimate is not needed for this ordinary constant-shift argument. The coefficient one in the displacement bound is optimal, as $`f(z)=z^n`$ shows. The estimate does not match labelled root lists or bound the cost of transporting an existing curve.

Qualitatively, a small linear perturbation also supplies distinct critical values as well as simple critical points. For $`\deg f\ge2`$, a multiple critical point of $`f+\lambda z`$ must satisfy $`f''(c)=0`$ and $`\lambda=-f'(c)`$; only finitely many parameters are excluded. Near any other parameter, label the distinct critical points by holomorphic functions $`c_j(\lambda)`$. Their values
``` math
v_j(\lambda)=f(c_j(\lambda))+\lambda c_j(\lambda)
 \quad\hbox{satisfy}\quad v_j'(\lambda)=c_j(\lambda).
```
Thus $`v_i-v_j`$ cannot vanish identically for $`i\ne j`$, and its zeros are isolated. Avoiding the finitely many pairs in a sufficiently small parameter neighbourhood gives simple critical points with distinct values. The neighbourhood can be chosen inside any prescribed disc about $`\lambda=0`$, proving the required arbitrarily small choice.

If distinct moduli are also needed for the excellent Morse function, the translation $`\beta`$ can avoid them at the same time as the ray collisions. For each distinct pair $`v_i,v_j`$, the equality $`|v_i+\beta|=|v_j+\beta|`$ is the real affine line
``` math
2\Re\bigl((v_i-v_j)\overline\beta\bigr)=|v_j|^2-|v_i|^2.
```
For ray separation it is enough to avoid, for each pair, the real line through $`-v_i`$ and $`-v_j`$: the ray-collision formula puts every forbidden translation on that line. Avoid also the finitely many points $`-v_j`$ to keep the translated values nonzero. Thus the full excluded set is contained in two real affine lines per pair of critical values, together with finitely many points. Its complement meets every open disc, so imposing distinct moduli costs no lower bound on the size of the perturbation. Root retention is also qualitative: choose a circle $`|z|=R<1`$ enclosing the original open-disc roots. If $`|\lambda|R+|\beta|<\min_{|z|=R}|f(z)|`$, Rouché’s theorem keeps all roots of $`f+\lambda z+\beta`$ inside that circle. These ordinary arguments establish genericity and root retention; they do not estimate the collar or the cost of transferring a selected curve. The first two requirements below therefore have qualitative proofs, while their simultaneous quantitative use is the remaining task.

For the next problem, fix a specified valid replacement for the refuted metric inequality. Its slack is the difference between the permitted length and the bound supplied by that replacement. The symbols $`q`$ and $`q_g`$ refer to this same specified quantity for $`f`$ and $`g`$, respectively; they are not the historical collar integral with coefficient $`1/(2\pi)`$. Without a choice of replacement inequality, the requirement $`q_g>q/2`$ has no defined geometric content.

<div id="prob:perturb1041" class="problem">

**Problem 33** (two-stage generic perturbation with slack). For fixed root discs, compact collar $`K`$, regular levels $`\alpha/2,\alpha,2\alpha,5\alpha/2`$, and a specified valid replacement metric inequality with slack $`q>0`$ at $`f`$, prove that an arbitrarily small
``` math
g_{\lambda,\beta}(z)=f(z)+\lambda z+\beta
```
can be chosen so that:

1.  $`f+\lambda z`$ has simple relevant critical points and injective complex critical values;

2.  the checked constant translation $`\beta`$ makes those values nonzero and pairwise ray-separated;

3.  no critical point enters the protected collar or truncation boundary;

4.  the relevant component remains in $`K`$, contains exactly the corresponding perturbed roots and has slack $`q_g>q/2`$; and

5.  root displacement and straight-line transfer back to the original roots consume less than a prescribed fraction of $`q/m`$.

If the one-coefficient perturbation $`\lambda z`$ cannot ensure all five properties, give the smallest additional lower-coefficient direction that can, or an explicit obstruction.

</div>

The cited declarations supply finite planar avoidance and the constant translation. The ordinary argument above additionally supplies a linear perturbation with simple critical points and distinct critical values. What remains for the stated problem is simultaneous control of the protected collar, the component, the quantitative slack and the root-to-root transfer cost. No formalisation of the new genericity argument or solution of those stability requirements is claimed.

<a id="newton-flow-on-a-compact-region-between-regular-levels"></a>

## 5. Newton flow on a compact region between regular levels

Classical Newton-flow theory describes maximal trajectories and the graph they form. Away from the roots and critical points, every orbit satisfies
``` math
p(z(t))=e^{-(t-t_0)}p(z(t_0)),\qquad
 u(z(t))=u(z(t_0))+t-t_0,\qquad u=-\log|p|,
```
by the lemma of Shub, Tischler and Williams \[kozen-stefansson1997, Lemma 2.1\]. For an initial point that is neither a root nor a critical point, the maximal Newton trajectory has one of four endpoint patterns: each finite-time end is a critical point, an infinite forward end is a root, and an infinite backward end is the point at infinity \[kozen-stefansson1997, Lemma 2.2\]. Stationary trajectories at simple roots are not part of this classification. The maximal nonconstant trajectories with endpoints among the roots and critical points form a connected Newtonian graph with finitely many edges \[kozen-stefansson1997, Definition 2.1 and §2\]. Critical-to-critical edges are included; pairwise distinct arguments exclude them by the value equation, not by the definition of the graph.

The smooth field needed for Morse theory is not $`-p/p'`$, which is undefined at a critical point with nonzero value. On the root-free band the Euclidean gradient satisfies
``` math
\nabla u=-\overline{p'/p}
   =\frac{|p'|^2}{|p|^2}\left(-\frac{p}{p'}\right)
 \qquad(p'\ne0).
```
It has the same oriented nonstationary trajectories as the Newton field, with a different time parameter. At a simple critical point $`c`$, its derivative is the real Hessian of $`u`$, whose eigenvalues are $`\pm|p''(c)/p(c)|`$. Thus it extends as a hyperbolic saddle there. A finite critical endpoint in Newton time is not a finite arrival at an equilibrium of the smooth field. These two parametrisations must be distinguished in a statement about a Morse–Smale flow.

<div id="prob:globalflow1041" class="problem">

**Problem 34** (relative global Newton-flow theorem). Let $`p`$ be a nonconstant polynomial, let $`a<b`$ be finite regular values of $`u=-\log|p|`$, and suppose every critical point in the compact band
``` math
\{z:a\le u(z)\le b\}
```
is simple, with the critical values in the band on pairwise distinct positive rays. Describe the maximal trajectories of the smooth gradient field $`\nabla u`$ relative to the lower and upper level boundaries, each of which may have several components. Construct a cut-open model by regular flow strips, specifying the separate copies of cut boundaries and the equivalence relation used for its trajectory parameter space. Prove that this parameter space is Hausdorff, or identify the obstruction to the proposed identifications. The ordinary orbit quotient of the uncut band is not required to be Hausdorff. State the boundary convention and the comparison with Newton trajectories through the positive change of time above, without evaluating $`-p/p'`$ at its singular points.

</div>

The endpoint classification on this band follows from the cited Newton classification and the time change. Each nonconstant trajectory runs from the lower boundary to the upper boundary, from the lower boundary to a saddle, or from a saddle to the upper boundary. Indeed, Newton time equals the change in $`u`$, so the part of a Newton trajectory in the band has bounded Newton-time interval. At either end it must meet a regular boundary or tend to a critical point. Ray separation excludes two different critical endpoints, and strict increase of $`u`$ excludes two ends at the same critical point. In smooth-gradient time, regular boundary crossings occur in finite time, whereas convergence to a saddle takes infinite time by uniqueness for the smooth differential equation. The remaining trajectories are the stationary saddles. This is an ordinary consequence of the classical classification, not an additional checked Lean theorem.

The planar transversality condition also follows from the hypotheses. Along a nonstationary gradient trajectory, the value of $`p`$ has constant argument, so a trajectory between two different saddles would contradict ray separation. A homoclinic trajectory is excluded by the strict increase of $`u`$. The stable-manifold theorem gives local stable and unstable curves tangent to the Hessian eigenspaces. Their global branches for different saddles therefore do not meet; at one saddle they meet transversely, since their tangent lines are the two distinct Hessian eigenspaces. The regular lower boundary is an entrance and the regular upper boundary an exit. With this boundary convention, the gradient satisfies the Morse–Smale transversality condition. This does not make the quotient by entire trajectories Hausdorff.

For an explicit obstruction, take $`p(z)=z^2-1/4`$ and the compact band
``` math
\log2\le-\log|p(z)|\le\log8.
```
Its only critical point is the simple saddle at $`0`$, whose value is $`-1/4`$; both boundary levels are regular and ray separation is vacuous. The positive real separatrix, including its upper-boundary endpoint, is
``` math
\bigl(0,1/(2\sqrt2)\bigr],\qquad
 \frac{dx}{d\tau}=\frac{2x}{1/4-x^2}.
```
Integration gives $`\tau-\tau_0=\tfrac18\log(x/x_0)-(x^2-x_0^2)/4`$, so this trajectory tends to $`0`$ as smooth-gradient time $`\tau\to-\infty`$. Thus this orbit is not closed in the band: its closure also contains the stationary orbit $`\{0\}`$. In the quotient topology its image is a nonclosed singleton, so the orbit quotient is not even $`T_1`$, hence not Hausdorff. Reparametrising the nonstationary trajectories leaves this quotient unchanged.

On an actual cut-open flow rectangle, by contrast, collapsing the trajectories gives the transverse interval. Identifying boundary copies is a further quotient and requires a separate separation argument. The [Reeb graph](https://arxiv.org/abs/1902.08841v5) uses yet another equivalence relation: it identifies connected components of level sets, not complete trajectories. Neither that graph nor the embedded Newtonian graph can be substituted for the orbit quotient without specifying a new equivalence relation.

The recorded checked algebra gives the pointwise value equation and excludes distinct endpoint rays once the exponential endpoint relation is assumed. The ordinary value-equation proof derives that relation for an existing real-time trajectory, using continuity at critical endpoints; the separate endpoint candidate has no reported compilation here. Global solution theory and the finite graph are the classical results cited above. The relative endpoint classification and transversality are proved above. They do not construct the required finite cut-open space, justify its boundary identifications or control the length needed to join the pieces. The quadratic example settles the uncut-orbit-space question negatively; it does not obstruct a construction that retains the required separate boundary copies.

This record does not establish the unrestricted conclusion of Erdős #1041. Its sufficient conditions have different hypotheses and containment levels: low critical value, separated simple critical value, and the individually proved polynomial families are not a cover of the remaining class. In particular, the scaled $`(5/2)\mu^{1/n}`$ bound is at level $`(25/13)\mu`$, which is smaller than $`2\mu`$; it therefore improves both the constant and the level of the $`71/10`$ construction. The latter is retained for its independent proof and component-sensitive estimates. The critical-value moment does not choose a contained pair. The ordinary generic slit-sheet topology has classical antecedents; the earlier proposed sufficient estimate concerned the lengths of particular inverse-ray curves. Their minimum need not equal the infimum over all contained curves. The degree-seven counterexample above rules out the corresponding universal estimate for these particular curves too, without invalidating conditional estimates on smaller classes.

<a id="adjacent-inverse-map-methods."></a>

#### Adjacent inverse-map methods.

Crane \[crane2007smale, Lemma 2.1, Theorem 2.2 and §§3–4\] uses inverse-branch hyperbolic geometry, Dubinin’s radial-slit input and capacity for a derivative-normalised Smale ratio. Dubinin’s four-point result \[dubinin2013fourpoint, Theorem 1 and Corollary 4\] assumes bounded critical values and estimates distortion. These are relevant methods, not direct sources of the present positive moment or connector constant, and their normalisations are not interchangeable with a root-disc hypothesis.

<a id="statements-and-declarations"></a>

# Statements and declarations

Lean checks exact formal statements, not citation choices or mathematical priority. The formal-source index records the complete quadratic weighted inequality, the exponent-$`2/(n-1)`$ critical-value mean, the translated cubic family and the open-disc sparse-quintic path conclusion in its checked build. The fourth-power and higher-moment refinements proved here remain ordinary analytic results. The complete degree-three path also has a release-source proof under monicity, degree three and the open-disc root hypothesis, distinct from the earlier implementation outside that build; its release status is explained above. Finite inequalities do not replace a comparison of the full geometric statements. The analytic path arguments and the research addendum retain the ordinary proof status stated locally. No fresh Lean build or independent mathematical review was performed for this revision.

<a id="acknowledgements"></a>

# Acknowledgements

I thank Wouter van Doorn for advice on mathematical exposition, in particular on explaining restrictive hypotheses, avoiding private terminology and introducing notation only when it helps the reader. His remarks concerned another note; this acknowledgement does not imply that he reviewed or endorsed the mathematics of the present paper.

<a id="app:sources"></a>

# Guide to the formal sources

The formal-source index describes sources at snapshot `6b78209ab63a`. The links below retain their earlier commits and line numbers. The index distinguishes complete statements in its recorded checked build from implementations present outside that build.

- Complete statements recorded in the supplied checked build: [critical-value mean with exponent $`2/(n-1)`$](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperCriticalValueMeanR10.lean#L101), [the quadratic weighted inequality for points in a disc](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperWeightedRefinementsR10.lean#L17), and [translated cubic-fibre path](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperCubicFibres.lean#L240).

- Complete implementations recorded outside that build: [degree-three path](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperCubicCompletion.lean#L297). The supplied release snapshot additionally contains [the cubic theorem under monicity, degree three and the open-disc hypothesis](https://github.com/wcook04/plectis-erdos-lean/blob/52f29ad173b04e3bac941b3663f2b9aebe5de0bb/ErdosProblems/Erdos1041/PaperCubicMonic.lean#L32), with an actual proof and an expanded solution statement. Its recorded status is `release_only`; it is not promoted to the checked-build category here.

- Also recorded in the supplied checked build: [the sparse-quintic path](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos1041/PaperPrimitiveCompletionR10.lean#L235).

- The index also distinguishes finite inequalities, declarations supplied only in the release sources, and ordinary analytic arguments. None of these categories is interchangeable with a complete formal path theorem.

A snapshot link is not a build receipt; the kernel checks and axioms stated in the coverage subsection below belong to the revisions named there. The original paper-wide commit macro is retained for legacy links; newer target links name their own snapshot explicitly.

<a id="sec:coverage"></a>

## Formalisation coverage and remaining dependencies

<div id="coverage">

</div>

Every theorem, lemma, proposition and corollary of this record other than those listed below has a Lean statement of the same assertion, with the same hypotheses, checked by the Lean kernel using only the axioms `propext`, `Classical.choice` and `Quot.sound`, in the development at revision `181078b6b009`. This includes Lemma <a href="#res:circle-slice-packing" data-reference-type="ref" data-reference="res:circle-slice-packing">6</a>.

Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a> is checked in degree two, with no hypothesis on the positions of the roots, and the exact rational arithmetic of its stopping-time comparison is checked. The analytic argument in higher degrees is not yet formalised. Corollary <a href="#res:low-critical-scale-free" data-reference-type="ref" data-reference="res:low-critical-scale-free">5</a> and Corollary <a href="#res:scaled-low-critical-path" data-reference-type="ref" data-reference="res:scaled-low-critical-path">8</a> are verified as reductions to that theorem, which is itself in this list; the degree-two case of the second corollary is checked with no input at all.

Theorem <a href="#res:critical-value-separation" data-reference-type="ref" data-reference="res:critical-value-separation">15</a> and Corollary <a href="#res:critical-value-thresholds" data-reference-type="ref" data-reference="res:critical-value-thresholds">16</a> are verified as reductions to a single named statement, which is what the analytic construction in the proof of Theorem <a href="#res:critical-value-separation" data-reference-type="ref" data-reference="res:critical-value-separation">15</a> produces: for every normalised separation datum, a square-root connector of a given length together with a component area satisfying the two displayed bounds. That construction is not formalised. It uses the conformal bijection supplied by the Riemann mapping theorem, the Bergman segment inequality, the exterior Blaschke capacity gap and Pólya’s area–capacity inequality \[crane, Theorem 6\]. The first clause of Corollary <a href="#res:critical-value-thresholds" data-reference-type="ref" data-reference="res:critical-value-thresholds">16</a>, inequality <a href="#eq:disk-family-coefficient" data-reference-type="eqref" data-reference="eq:disk-family-coefficient">[eq:disk-family-coefficient]</a> for every $`n\ge3`$, every $`w_0\in[0,1]`$ and every $`4/3\le S\le2`$, is unconditional, and so is every numerical inequality entering the second clause.

Theorem <a href="#res:constant-factor-path" data-reference-type="ref" data-reference="res:constant-factor-path">9</a>, Corollary <a href="#res:constant-factor-arity" data-reference-type="ref" data-reference="res:constant-factor-arity">10</a> and Corollary <a href="#res:constant-factor-capacity" data-reference-type="ref" data-reference="res:constant-factor-capacity">11</a> are verified as reductions to named statements, each of which is what the level and direction averaging in their own proofs produces. That construction is not formalised; its ingredients are Pólya’s area inequality \[crane, Theorem 1\], the Koebe distortion theorem and the coarea formula. The degenerate case $`\mu=0`$, the degree-two case and every numerical constant are checked. Theorem <a href="#res:conjecture-p-consumer" data-reference-type="ref" data-reference="res:conjecture-p-consumer">13</a> is verified as a reduction to the two-component split at the first critical level, which its own proof constructs and which is not formalised; its ingredients are the component count in the proof of \[eks2010, Proposition 2.1\], the boundary extension of the inverse branch and the Jordan curve theorem. The half-perimeter selection lemma is checked. Theorem <a href="#res:dual-arity-floor" data-reference-type="ref" data-reference="res:dual-arity-floor">7</a> is verified as a reduction to <a href="#eq:lc-radius-and-budget" data-reference-type="eqref" data-reference="eq:lc-radius-and-budget">[eq:lc-radius-and-budget]</a>, which its own proof derives from the standing failure hypothesis by the Blaschke factorisation of a Riemann map and Pólya’s area inequality; that derivation is not formalised. The hyperbolic law of cosines it uses is proved in the development. For Theorem <a href="#res:attachment-aware-reeb" data-reference-type="ref" data-reference="res:attachment-aware-reeb">29</a> the development checks the ray-disjointness, level-separation and saddle-scale steps of its proof, and the Morse, monodromy and strip statements themselves are not yet formalised.

Formal proofs of the named inputs are not included in the verified development, so the endpoints that carry one remain conditional on it. Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a> and Theorem <a href="#res:attachment-aware-reeb" data-reference-type="ref" data-reference="res:attachment-aware-reeb">29</a> carry no such input; for each of them part of the argument is formalised and the rest is not. A theorem whose own statement is conditional is formalised exactly as stated; the results listed here are asserted unconditionally.

The concordance below is pinned to an earlier checkpoint and records the total-variation version of the degree-seven counterexample. The stronger Hausdorff-measure theorem and the exact Formal Conjectures negation are linked in Section <a href="#sec:problem" data-reference-type="ref" data-reference="sec:problem">1</a>; the earlier Comparator receipt does not review those later declarations.

<a id="concordance-of-statements-and-lean-declarations."></a>

#### Concordance of statements and Lean declarations.

Each result of this record that has a kernel-checked Lean statement of the same assertion is listed below with the declarations that jointly state it. Each name links to the source revision in its URL. Where the Lean statement is stronger than the printed one and implies it by an immediate specialisation, the entry says so. An entry marked *compared* was also checked independently: a restatement of the same declarations against Mathlib alone, together with its proof, was verified by Comparator (`leanprover/comparator`) in a clean continuous integration environment, in the run named by its number. Comparator trusts the restated statement, so the correspondence between the printed result and that statement is the one this concordance records.

The statement at <a href="#res:ani-degree-seven-counterexample-long" data-reference-type="ref" data-reference="res:ani-degree-seven-counterexample-long">[res:ani-degree-seven-counterexample-long]</a>: [`erdos1041_counterexample_hausdorff`](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/Counterexample/HausdorffLength.lean#L283), [`erdos1041_hausdorff_negation`](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/Counterexample/HausdorffLength.lean#L407), [`erdos1041_hausdorff_answer_false`](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/Counterexample/HausdorffLength.lean#L449). *Comparator replay pending; Palomar entry pending.*

Theorem <a href="#res:trinomial-all-degree" data-reference-type="ref" data-reference="res:trinomial-all-degree">2</a> (the Lean statement is stronger): [`all_spokes`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperTrinomial.lean#L26), [`complete_trinomial`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperTrinomial.lean#L38). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

Lemma <a href="#res:circle-slice-packing" data-reference-type="ref" data-reference="res:circle-slice-packing">6</a> (the Lean statement is stronger): [`circle_slice_packing`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L563), [`cosh_dist_polar`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L141), [`dist_polar_I`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L166), [`exists_polar`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L177), [`polar_zero_zero`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L162), [`circle_slice_packing_abstract`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/HyperbolicLawOfCosines.lean#L315).

Theorem <a href="#res:degree-three" data-reference-type="ref" data-reference="res:degree-three">14</a> (the Lean statement is stronger): [`cubic_paper_complete`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCubicCompletion.lean#L297). *Compared*, run [`35544127144`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35544127144).

Theorem <a href="#prop:sharp-collinear-chebyshev-comparator" data-reference-type="ref" data-reference="prop:sharp-collinear-chebyshev-comparator">17</a>: [`exists_peak_le_comparisonBound`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/SharpCollinearChebyshev.lean#L133). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

Theorem <a href="#thm:sharp-collinear-diameter" data-reference-type="ref" data-reference="thm:sharp-collinear-diameter">18</a>: [`sharp_collinear_root_diameter`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L367), [`sharp_collinear_root_diameter_monic`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L967), [`exists_collinear_factorisation`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L928), [`exists_gap_le_comparisonBound`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L212), [`sharp_collinear_equality_attained`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L836), [`chebyshev_configuration_attains`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L769), [`monicScaledChebyshev_eq_prod`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L684), [`collinearDiameterBound_sharpConstant`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L871), [`sharpConstant_le_of_collinearDiameterBound`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L878). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

Corollary <a href="#cor:collinear-erdos-1041" data-reference-type="ref" data-reference="cor:collinear-erdos-1041">19</a>: [`collinear_erdos_1041`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L515), [`collinear_erdos_1041_monic`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L984), [`exists_collinear_factorisation`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L928), [`sharp_collinear_root_diameter`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/CollinearDiameterWhole.lean#L367). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

Theorem <a href="#prop:primitive-quintic-two-tail-energy-selector" data-reference-type="ref" data-reference="prop:primitive-quintic-two-tail-energy-selector">20</a>: [`primitiveInterior_exists_two_tailEnergy_lt_one`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PrimitiveQuinticInteriorTail.lean#L272). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

Theorem <a href="#thm:primitive-quintic-two-tail" data-reference-type="ref" data-reference="thm:primitive-quintic-two-tail">21</a>: [`primitive_quintic_two_tail`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/PrimitiveQuinticClosedDisc.lean#L260), [`primitive_quintic_two_tail_of_polynomial`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/PrimitiveQuinticClosedDisc.lean#L313), [`two_tails_closedDisc_of_ne_zero`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/PrimitiveQuinticClosedDisc.lean#L93), [`tail_le_one_and_eq_iff_of_leading_zero`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/PrimitiveQuinticClosedDisc.lean#L199), [`tail_norm_of_leading_zero`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR21/PrimitiveQuinticClosedDisc.lean#L82). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

Theorem <a href="#lem:cubic-safe-root-spoke" data-reference-type="ref" data-reference="lem:cubic-safe-root-spoke">22</a>: [`cubic_has_safe_root_spoke`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/CubicQuotientFiberCase.lean#L161). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

Theorem <a href="#thm:translated-cubic-quotient-fibres" data-reference-type="ref" data-reference="thm:translated-cubic-quotient-fibres">23</a>: [`complete_translated_cubic_quotient_fibres`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCubicFibres.lean#L240). *Compared*, run [`35544127144`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35544127144).

Theorem <a href="#res:critical-value-budget" data-reference-type="ref" data-reference="res:critical-value-budget">24</a> (the Lean statement is stronger): [`critical_value_three_budgets`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/CriticalMeanWhole.lean#L14), [`critical_value_three_budgets_sharp`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/CriticalMeanWhole.lean#L36). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

Lemma <a href="#res:reflected-critical-value" data-reference-type="ref" data-reference="res:reflected-critical-value">25</a>: [`reflected_critical_value`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperReflectedCompletion.lean#L254). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

Theorem <a href="#res:value" data-reference-type="ref" data-reference="res:value">26</a> (the Lean statement is stronger): [`newton_real_value_whole`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/NewtonRealTime.lean#L52). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

Corollary <a href="#res:ray" data-reference-type="ref" data-reference="res:ray">27</a> (the Lean statement is stronger): [`newton_real_endpoint_whole`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/PaperCompleteR20/NewtonRealTime.lean#L69). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

Theorem <a href="#res:locus" data-reference-type="ref" data-reference="res:locus">28</a>: [`translated_samePositiveRay_parameterization`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L107). *Compared*, run [`35643815458`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35643815458).

<a id="sec:record-circle-slice"></a>

# Numerical estimates for the packing inequality

This appendix records numerical estimates for the packing argument in Theorem <a href="#res:low-critical-thirteen-twentyfifths" data-reference-type="ref" data-reference="res:low-critical-thirteen-twentyfifths">4</a>. The short paper does not depend on the floating-point comparisons below. Those comparisons are not certified upper bounds; the separate table of certified lower root counts is identified as such. The computations indicate where particular relaxations lose strength in the displayed range $`13/25<\mu<1`$. This is not an uncovered interval: the rigorous comparison above also covers $`\mu\le529/1000`$. The floating-point comparisons neither enlarge that certified range nor assert the historical path bound throughout the rest of the interval.

At $`a=1`$ the constants of the failure inequalities have the rounded values $`\delta\approx0.4586751`$, $`D\approx5.3770730`$, and $`d_{\mathrm{low}}\approx2.1700770`$; the identity $`\cosh(D/2)=e^{2}`$ is exact. The quantity being estimated is $`\sum_j\lambda(d_j)`$ for $`k`$ roots at this fixed area, not a Euclidean path length. The four columns compare the earlier bound
``` math
\max\!\left\{\frac\delta2+(k-1)\lambda(D-d_{\mathrm{low}}),
                  k\operatorname{artanh}(e^{-2})\right\},
```
where $`\lambda(d)=-\log\tanh(d/2)`$ as in Section <a href="#sec:low-critical-closure" data-reference-type="ref" data-reference="sec:low-critical-closure">3</a>; the hyperbolic packing bound used for the earlier threshold $`2/5`$; the linear-programming value $`M_{\mathrm{circ}}`$ of the relaxation of Lemma <a href="#res:circle-slice-packing" data-reference-type="ref" data-reference="res:circle-slice-packing">6</a>; and the largest reported objective value at a numerically constructed configuration. The last column is a search result, not a certified feasible value or a proved optimum.

<div class="center">

| $`k`$ | earlier bound | packing | $`M_{\mathrm{circ}}`$ | search |
|------:|--------------:|--------:|----------------------:|-------:|
|     2 |        0.3103 |  0.5899 |                0.3102 | 0.3103 |
|     3 |        0.4085 |  0.6878 |                0.3893 | 0.3784 |
|     4 |        0.5447 |  0.7475 |                0.4450 | 0.4306 |
|     5 |        0.6809 |  0.7906 |                0.4846 | 0.4694 |
|     6 |        0.8170 |  0.8244 |                0.5155 | 0.4986 |
|     7 |        0.9532 |  0.8521 |                0.5408 | 0.5208 |
|     8 |        1.0894 |  0.8757 |                0.5622 | 0.5413 |
|    10 |        1.3617 |  0.9142 |                0.5972 | 0.5759 |
|    14 |        1.9064 |  0.9710 |                0.6487 | 0.6228 |
|    20 |        2.7234 |  1.0298 |                0.7022 | 0.6717 |
|    30 |        4.0851 |  1.0955 |                0.7624 | 0.7283 |
|   100 |        13.617 |  1.2871 |                0.9428 |    n/a |

</div>

Both right-hand columns come from floating-point searches. In addition, $`M_{\mathrm{circ}}`$ uses a $`2600`$-point $`d`$-grid and a $`1400`$-point $`r`$-grid. Restricting the allowed $`d`$ values and checking only finitely many circle constraints have opposite effects on the feasible set. Without a separate continuous feasibility or dual certificate, the computed value is not a proved lower or upper bound for the continuous relaxation. At $`k=2`$, the grid value $`0.31018`$ differs from the analytic value, approximately $`0.310338`$. Their proximity supplies no rigorous bracket.

The certified lower bounds for $`k`$, rounded up to integers, are as follows at $`a=1`$.

<div class="center">

| $`x`$              | 0.40 | 0.45 | 0.50 | 0.55 | 0.60 | 0.63 | 0.65 | 0.70 |
|:-------------------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| earlier bound      |    3 |    4 |    4 |    5 |    5 |    5 |    5 |    6 |
| packing bound      |    2 |    2 |    2 |    2 |    2 |    3 |    3 |    4 |
| circle-slice bound |    3 |    4 |    6 |    8 |   10 |   12 |   14 |   18 |

</div>

In one explicit-Euler floating replica with step $`10^{-3}`$ and a geometric grid of $`40`$ initial areas from $`10^{-6}`$ to $`1`$, the largest computed time to reach the area cap falls from $`0.89703`$ with the earlier packing lower bound for $`k`$ to $`0.65503`$ with the certified circle-slice bounds, and to $`0.63003`$ if the relaxation’s linear-programming value replaces those bounds. Shrinking the relaxation by the worst measured slack factor $`1.045`$ moves it only to $`0.60703`$. These computations suggest that this particular relaxation may stop near $`e^{-0.607}=0.545`$; they do not prove that it does, and they exclude neither a stronger lower bound on the root count nor a larger certified range.

The search uses only ten or fourteen radii in its two settings and a coarse $`a`$-grid with upward rounding. The reported loss from the first restriction at $`a=1`$, $`k=8`$ is about one per cent; the reported rounding loss is comparable. These are empirical estimates, not certified error bounds relative to the unrestricted continuous optimum.

The continuous optimisation remains unevaluated: maximise $`\sum_j\lambda(d_j)`$ subject to $`d_j\ge d_{\mathrm{low}}`$ and $`\sum_jw(d_j,r)\le\pi`$ for every $`r>0`$, allowing the relaxed radial distributions used in the computation. The numerical optimiser spreads mass over several radii and suggests logarithmic growth in $`k`$. Neither that growth law nor its coefficient is proved. Evaluating the relaxation would clarify this packing argument; its effect on the final path threshold would still need to be established.

<a id="sec:erdos-1041-complete-family-map"></a>

# Guide to the results

The table distinguishes the main conclusions and their limitations. Each theorem retains its own hypotheses; the scope of formal verification is recorded separately.

<div class="center">

| Family or mechanism | Conclusion and limitations |
|:---|:---|
| Trinomials | The root equation controls every root-to-origin segment. |
| Low critical values | Area growth and a finite certificate give the stated cutoff $`13/25`$; the recorded certificate also covers $`\mu\le529/1000`$. The scaled consequence uses level $`(25/13)\mu`$. |
| Separated simple value | A square root removes local branching; Bergman and capacity estimates bound length. The chosen critical point must be simple and its value isolated. |
| Collinear and sparse families | Segment constructions for roots on a line or specified coefficients, not for arbitrary sparse polynomials. |
| Critical-value means | An unconditional exponent $`4/(n-1)`$ with sharp constant; higher exponents require specified complex power-sum cancellations. No choice of a short contained path follows. |
| Counterexamples and conditional reductions | The Cassini example refutes the stated spanning-tree coefficient. The degree-eight example refutes the proposed Gamma-function perimeter constant, not every uniform perimeter bound. An assumed uniform subcritical perimeter bound $`\beta\sigma^{1/n}`$ gives length at most $`\beta\rho`$ in $`K_\mu`$. Prescribed straight-segment rules also fail; the inverse-ray bound remains a historical sufficient condition. |

</div>

A critical-value mean, a contained segment and a formally checked finite inequality do not supply the same conclusion.

<div class="thebibliography">

99 G. Pólya, *Beitrag zur Verallgemeinerung des Verzerrungssatzes auf mehrfach zusammenhängende Gebiete*, Sitzungsberichte der Preussischen Akademie der Wissenschaften, Physikalisch-Mathematische Klasse (1928), printed pp. 228–232 and 280–282. <https://archive.org/details/sitzungsbericht1928preu>. E. Crane, *The areas of polynomial images and pre-images*, Bull. London Math. Soc. **36** (2004), no. 6, 786–792, doi:[10.1112/S0024609304003509](https://doi.org/10.1112/S0024609304003509); preprint arXiv:[math/0302189v1](https://arxiv.org/abs/math/0302189v1), whose statement numbers are cited. T. F. Bloom, *Erdős Problems*, problem 1041. <https://www.erdosproblems.com/1041> P. Erdős, F. Herzog, and G. Piranian, *Metric properties of polynomials*, J. Analyse Math. **6** (1958), 125–148, doi:[10.1007/BF02790232](https://doi.org/10.1007/BF02790232). S. Ghosh and K. Ramachandran, *Number of Components of Polynomial Lemniscates: A Problem of Erdős, Herzog, and Piranian*, J. Math. Anal. Appl. **540** (2024), no. 1, 128571, doi:[10.1016/j.jmaa.2024.128571](https://doi.org/10.1016/j.jmaa.2024.128571); preprint arXiv:[2312.13673v1](https://arxiv.org/abs/2312.13673v1), whose statement numbers are cited. S. Sutherland, *Bad Polynomials for Newton’s Method*, in B. Bielefeld and M. Lyubich (eds.), *Conformal Dynamics Problem List*, Stony Brook IMS preprint (1992), 42–44. <https://www.math.stonybrook.edu/preprints/ims92-7.pdf> D. Kozen and K. Stefánsson, *Computing the Newtonian graph*, J. Symbolic Comput. **24** (1997), no. 2, 125–136, doi:[10.1006/jsco.1997.0118](https://doi.org/10.1006/jsco.1997.0118); authors’ copy <https://www.cs.cornell.edu/kozen/Papers/newton.pdf>. P. Ebenfelt, D. Khavinson, and H. S. Shapiro, *Two-dimensional shapes and lemniscates*, in *Complex Analysis and Dynamical Systems IV, Part 1*, Contemp. Math. **553**, Amer. Math. Soc., Providence, RI, 2011, 45–59, doi:[10.1090/conm/553/10931](https://doi.org/10.1090/conm/553/10931); preprint arXiv:[1003.4567v1](https://arxiv.org/abs/1003.4567v1), whose statement numbers are cited. V. N. Dubinin, *Lemniscates and inequalities for the logarithmic capacities of continua*, Mat. Zametki **80** (2006), no. 1, 33–37, doi:[10.4213/mzm2777](https://doi.org/10.4213/mzm2777); English translation, Math. Notes **80** (2006), no. 1, 31–35, doi:[10.1007/s11006-006-0105-8](https://doi.org/10.1007/s11006-006-0105-8). `shtuka`, *A Short Path Joining Two Zeros Inside a Polynomial Lemniscate*, manuscript posted 24 March 2026, 48 pp. <https://shtuka123.github.io/1041/main.pdf>. The file at this URL has since been replaced by a shorter partial version that no longer contains Proposition 12; the durable public record of the March version, its defect, and the author’s 26 March 2026 concession is the discussion thread at <https://www.erdosproblems.com/forum/thread/1041>. V. S. Pendyala, *A Degree-Four Lemniscate Path Theorem*, arXiv:[2606.24875v1](https://arxiv.org/abs/2606.24875v1) (2026), doi:[10.48550/arXiv.2606.24875](https://doi.org/10.48550/arXiv.2606.24875). V. N. Dubinin, *Some inequalities for polynomials and rational functions associated with lemniscates*, Zap. Nauchn. Sem. POMI **404** (2012), 83–99; English translation, J. Math. Sci. **193** (2013), no. 1, 45–54, doi:[10.1007/s10958-013-1432-4](https://doi.org/10.1007/s10958-013-1432-4). P. Borwein, *The arc length of the lemniscate $`\{|p(z)|=1\}`$*, Proc. Amer. Math. Soc. **123** (1995), no. 3, 797–799, doi:[10.1090/S0002-9939-1995-1223265-3](https://doi.org/10.1090/S0002-9939-1995-1223265-3). A. Eremenko and W. Hayman, *On the length of lemniscates*, Michigan Math. J. **46** (1999), no. 2, 409–415, doi:[10.1307/mmj/1030132418](https://doi.org/10.1307/mmj/1030132418); preprint arXiv:[0805.2295](https://arxiv.org/abs/0805.2295). A. Fryntov and F. Nazarov, *New estimates for the length of the Erdős–Herzog–Piranian lemniscate*, in *Linear and Complex Analysis*, Amer. Math. Soc. Transl. Ser. 2 **226**, Amer. Math. Soc., Providence, RI, 2009, 49–60, doi:[10.1090/trans2/226/05](https://doi.org/10.1090/trans2/226/05); preprint arXiv:[0808.0717v1](https://arxiv.org/abs/0808.0717v1). T. Tao, *The maximal length of the Erdős–Herzog–Piranian lemniscate in high degree*, arXiv:[2512.12455v1](https://arxiv.org/abs/2512.12455v1) (2025). A. Eremenko and P. Yuditskii, *Comb functions*, Contemp. Math. **578** (2012), 99–118, doi:[10.1090/conm/578/11472](https://doi.org/10.1090/conm/578/11472); preprint arXiv:[1109.1464v1](https://arxiv.org/abs/1109.1464v1). A. Eremenko and L. Lempert, *An extremal problem for polynomials*, Proc. Amer. Math. Soc. **122** (1994), no. 1, 191–193, doi:[10.1090/S0002-9939-1994-1207536-1](https://doi.org/10.1090/S0002-9939-1994-1207536-1). A. Eremenko, *A Markov-type inequality for arbitrary plane continua*, Proc. Amer. Math. Soc. **135** (2007), no. 5, 1505–1510, doi:[10.1090/S0002-9939-06-08640-0](https://doi.org/10.1090/S0002-9939-06-08640-0); preprint arXiv:[math/0606745v1](https://arxiv.org/abs/math/0606745v1). C. J. Bishop, A. Eremenko, and K. Lazebnik, *On the shapes of rational lemniscates*, Geom. Funct. Anal. **35** (2025), no. 2, 359–407, doi:[10.1007/s00039-025-00704-2](https://doi.org/10.1007/s00039-025-00704-2); preprint arXiv:[2407.14610v1](https://arxiv.org/abs/2407.14610v1). V. N. Dubinin, *Inequalities for critical values of polynomials*, Sb. Math. **197** (2006), no. 8, 1167–1176, doi:[10.1070/SM2006v197n08ABEH003793](https://doi.org/10.1070/SM2006v197n08ABEH003793). E. Crane, *A bound for Smale’s mean value conjecture for complex polynomials*, Bull. London Math. Soc. **39** (2007), no. 5, 781–791, doi:[10.1112/blms/bdm063](https://doi.org/10.1112/blms/bdm063); author preprint <https://people.maths.bris.ac.uk/~maetc/SMVCbound.pdf>. V. N. Dubinin, *Four-point distortion theorem for complex polynomials*, arXiv:[1301.3985v1](https://arxiv.org/abs/1301.3985v1) (2013). O. S. Kuznetsova and V. G. Tkachev, *Length functions of lemniscates*, Manuscripta Math. **112** (2003), 519–538, doi:[10.1007/s00229-003-0411-3](https://doi.org/10.1007/s00229-003-0411-3); preprint arXiv:[math/0306327](https://arxiv.org/abs/math/0306327). D. Tischler, *Critical points and values of complex polynomials*, J. Complexity **5** (1989), no. 4, 438–456. W. Cook / Plectis, *Three refinements for the lemniscate-path programme*, 16 September 2026, accompanying unreviewed research note, Sections 1–3, with the earlier *Structural obstructions* note preserved in the same revision bundle. I. Schur, *Über die Verteilung der Wurzeln bei gewissen algebraischen Gleichungen mit ganzzahligen Koeffizienten*, Math. Z. **1** (1918), no. 4, 377–402.

</div>

[^1]: The checked [preconnected-set theorem](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/Counterexample/HausdorffLength.lean#L283) yields the [negation](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/Counterexample/HausdorffLength.lean#L407) and [`answer(False)`](https://github.com/wcook04/plectis-erdos/blob/7380b7871687b6bcc41ca0143c61f232e8af6500/lean/ErdosProblems/Erdos1041/Counterexample/HausdorffLength.lean#L449) forms of the Formal Conjectures proposition. This formalises one polynomial, not ani’s reported small-parameter family. Independent human review has not adjudicated correspondence with the 1958 wording.
