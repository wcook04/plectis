<a id="erdos-1041-lemniscate-newton-flow"></a>

# Newton Flow and Critical-Value Ray Separation

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Let $`f(z)=\prod_{i}(z-z_i)`$ be monic with every root in the open unit disc. Erdős, Herzog, and Piranian asked whether two roots can always be joined by a curve of length less than $`2`$ contained in the open lemniscate $`\{|f|<1\}`$. The problem is open. A manuscript posted in March 2026 claims the result for all such $`f`$; its Proposition 12 is a load-bearing spanning-tree decomposition whose printed proof contains an invalid local saddle block. At an interior Morse saddle a sufficiently small chart lies wholly in the open component and contains all four sectors, so the asserted one-lower/two-upper three-ended neighbourhood does not follow. The proposition itself is not refuted and may admit a cut-annulus or four-pronged repair. An independent June 2026 preprint proves the degree-four case. This note isolates and checks a dynamical input that could support an alternative decomposition.

Along a trajectory of the complex Newton field $`-f/f'`$ the polynomial value satisfies $`w'=-w`$, so $`f(z(t))=e^{-t}f(z(0))`$ and $`e^{t}f(z(t))`$ is a first integral. Both are checked by the Lean kernel. The consequence is a separation criterion: the endpoints of any finite Newton-flow connection lie on one oriented ray from the origin, so critical values on distinct rays admit no saddle-to-saddle connection. The criterion is sharper than the one the manuscript uses. Distinct critical values, and even distinct critical-value moduli, do not exclude saddle connections; distinct critical-value *arguments* do. The obstruction to arranging distinct arguments by perturbation is also made explicit: for each pair of critical values the set of common translations causing a ray collision is a one-real-parameter locus, given in closed form.

What remains is the planar topology and the length bookkeeping. Neither is proved here, and Erdős \#1041 is not settled.

> **Contribution.** The paper checks exponential Newton-value decay, parameterises positive-ray collisions, constructs arbitrarily small translations avoiding all collisions in a finite family, and proves root retention under a quantified constant perturbation.
>
> **Relation to the open problem.** These are dynamical and perturbative inputs. They do not repair the global topology and metric gluing needed for a curve of length less than $`2`$, so Problem #1041 remains open.
>
> **Executable review object.** Comparator selects the finite-family small-translation theorem and the quantified root-retention theorem. The literature diagnosis and finite computation remain separate evidence classes. The repository’s external-verification job compares these exact Lean propositions with separately declared challenge statements and an axiom budget, then asks Lean’s kernel to check the submitted proofs. The [formalisation manifest](https://github.com/wcook04/plectis-lean-erdos249-257/blob/main/formalization.yaml) and the commit-bound CI receipt record that check; they do not assess novelty, significance, or whether the original problem is solved.

<a id="sec:problem"></a>

# The problem

<div id="res:problem" class="problem">

**Problem 1** (Erdős \#1041). Let $`f(z)=\prod_{i=1}^{n}(z-z_i)`$ be monic with $`z_i\in\mathbb{D}`$, the open unit disc. Show that two of the roots can be joined by a curve of length less than $`2`$ lying in the open lemniscate $`E=\{z\in\mathbb{C}:|f(z)|<1\}`$.

</div>

Numbering and current status follow Bloom’s Erdős problem catalogue \[bloom\]. The problem is open. The original source is Problem 5 on printed p. 139 of Erdős–Herzog–Piranian \[ehp1958, p. 139\]; the preceding paragraph records the known input that one component of the lemniscate contains at least two zeros.

Two recent manuscripts are relevant. The 48-page manuscript posted by `shtuka` on 24 March 2026 \[march2026, Theorem 1, p. 1\] claims the unrestricted statement. Its Proposition 12 (p. 16, with proof continuing through p. 30) supplies the spanning-tree decomposition used in the final proof. The defect was located publicly in the problem’s discussion thread: on 25 March 2026 Tao observed that the invocation of Lemma 8 there is unjustified and that the flow lines need not organise into connected trees, and on 26 March 2026 the manuscript’s author agreed that the statement of Proposition 12 itself, not only its printed proof, is incorrect, and set the strategy aside. Section <a href="#sec:gap" data-reference-type="ref" data-reference="sec:gap">4</a> records an independent diagnosis of the same failure through the local three-ended saddle model, together with possible repairs. No counterexample to the proposition is exhibited there. Pendyala’s independent June 2026 preprint \[june2026, Thm. 1, p. 1\] proves the degree-four case. The quartic theorem does not close the problem.

The object we work with is not the lemniscate directly but the flow that foliates it.

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

| Statement | Status | Exact boundary |
|:---|:---|:---|
| Erdős \#1041 | Open | No proof is claimed. |
| Newton value equation $`w'=-w`$ | Checked | Away from critical points, along any trajectory tangent to $`-f/f'`$. |
| Exponential first integral | Checked | $`\tfrac{d}{dt}\bigl(e^{t}f(z(t))\bigr)=0`$. |
| Ray separation of critical values | Checked (consumer form) | Endpoints of a finite connection share one oriented ray; distinct rays exclude a connection. |
| Ray-collision locus | Checked | $`\beta=(ra-b)/(1-r)`$, $`r>0`$, $`r\ne1`$: one real parameter per pair. |
| Quartic case | Cited | Proved in \[june2026, Thm. 1, p. 1\]; does not extend to general degree. |
| Unrestricted proof of \[march2026, Theorem 1, p. 1\] | Proof gap | Proposition 12 uses a false three-ended local saddle block; located publicly by Tao (25 March 2026), conceded by the author at statement level (26 March 2026). No counterexample is exhibited. |
| Constant-translation ray separation and root retention | Checked | After critical-value injectivity, arbitrary small ray avoidance and an explicit unit-disc margin. |
| Coefficient perturbation and slack stability | Open | Must first create injective critical values and preserve the component, collars and length budget. |
| Reeb decomposition and length fan-in | Open | The two surviving producers. |
| Random search to degree $`10`$ | Verified finite instances | Upper bounds for sampled configurations only. |

<a id="sec:newton"></a>

# The Newton value equation

Away from the critical set, define the complex Newton field
``` math
N(z)=-\frac{f(z)}{f'(z)} .
```
Let $`z(t)`$ be differentiable with $`z'(t)=N(z(t))`$, and put $`w(t)=f(z(t))`$.

<div id="res:value" class="theorem">

**Theorem 2** (value equation). *$`w'(t)=-w(t)`$.*

</div>

The computation is one line: $`w'=f'(z)\,z'=f'(z)\cdot(-f(z)/f'(z))=-f(z)=-w`$. The kernel checks it as *newton flow value has deriv at*, together with the differential form of the first integral, *newton flow scaled value has deriv at zero*:
``` math
\frac{d}{dt}\Bigl(e^{t}f(z(t))\Bigr)=0,
  \qquad\text{equivalently}\qquad
  f(z(t))=e^{-t}f(z(0)) .
```
Observe what this says about the geometry. The value moves radially inward at exponential rate and never changes argument. The lemniscate $`\{|f|<1\}`$ is therefore forward-invariant, and the flow lines are exactly the preimages of rays from the origin.

<div id="res:ray" class="corollary">

**Corollary 3** (ray separation). *The endpoints of any finite Newton-flow connection lie on the same oriented ray from $`0`$. Consequently, if two critical values lie on distinct positive rays, no Newton-flow saddle connection joins the corresponding critical points.*

</div>

This is checked in consumer form: the kernel accepts the implication from the hypothesis of distinct rays to the absence of a connection. It is the statement the topology needs, and it is a genuine sharpening of the criterion used in the literature.

<a id="sec:arguments"></a>

# Arguments, not moduli

It is tempting to arrange a generic perturbation so that the critical values are pairwise distinct, or that their moduli are pairwise distinct, and to conclude that saddle connections are excluded. Neither is enough.

Two distinct critical values can lie on one ray, and two critical values with distinct moduli certainly can: the ray records the argument, and the modulus is exactly the coordinate the flow contracts. By Corollary <a href="#res:ray" data-reference-type="ref" data-reference="res:ray">3</a> the invariant that excludes connections is the argument. What a perturbation must therefore achieve is pairwise distinct critical-value *arguments*, which is a condition on $`n-1`$ points modulo the circle rather than on their positions in the plane.

The cost of that condition is also checked, and it is small.

<div id="res:locus" class="theorem">

**Theorem 4** (ray-collision locus). *Let $`a\ne b`$ be complex. Every common translation $`\beta`$ for which $`a+\beta`$ and $`b+\beta`$ lie on the same positive ray has the form
``` math
\beta=\frac{ra-b}{1-r},
  \qquad r\in\mathbb{R}_{>0},\ r\ne1 .
```*

</div>

So each pair of critical values contributes a one-real-parameter forbidden locus in the translation plane, given in closed form (*translated same positive ray parameterization*). A finite union of such loci has empty interior, which is the shape one wants for an avoidance argument. Turning that into a perturbation of $`f`$ is not immediate: the translation model must be replaced by an actual perturbation of the roots that keeps them inside $`\mathbb{D}`$ and preserves the length slack. That is the first open producer of §<a href="#sec:open" data-reference-type="ref" data-reference="sec:open">6</a>.

<a id="sec:gap"></a>

# A proof gap in the unrestricted argument

The March manuscript’s Proposition 12 claims the following load-bearing statement. For $`u=-\log|f|`$, a connected component $`V`$ of $`\{u>c\}`$ carrying $`m\ge2`$ simple zeros, and the stated regularity and Morse hypotheses, it constructs, for every $`\varepsilon>0`$, an embedded spanning tree $`G_\varepsilon\subset V`$ with
``` math
\operatorname{len}(G_\varepsilon)
 \le\frac1{2\pi}\int_{2\alpha}^{\infty}P_V(t)\,dt+\varepsilon.
\tag{5.1}\label{eq:prop12-bound}
```
The final theorem uses this estimate, so the issue below cannot be bypassed by calling the proposition auxiliary.

At an interior index-one critical point $`p`$, the proof invokes a Morse chart
``` math
u=\mu+x^2-y^2
```
and replaces the saddle by a three-ended neighbourhood having one connected lower cross-section and two connected upper cross-sections. That local model is false as written. Because $`p\in V`$ and $`V`$ is open, a sufficiently small closed disc around $`p`$ lies entirely in $`V`$. In that disc the full Morse chart has four sectors: two components of $`u>\mu`$ and two components of $`u<\mu`$. A global component argument cannot delete one local sector from a disc already contained in $`V`$.

This diagnoses a proof step, not the proposition’s statement. A repair might cut an adjoining regular annulus along a separatrix or regular flow arc before forming the block, retain a four-pronged saddle neighbourhood and change the assembly, or replace the local construction by the ray-cut decomposition proposed below. Any repair must prove that its connector cost can be made arbitrarily small uniformly in the attachment points and that the repaired blocks still assemble to an embedded tree satisfying <a href="#eq:prop12-bound" data-reference-type="eqref" data-reference="eq:prop12-bound">[eq:prop12-bound]</a>. The shorter descriptions of the same three-ended block do not repair the four-sector topology.

Corollary <a href="#res:ray" data-reference-type="ref" data-reference="res:ray">3</a> supplies one independent input for a different route: distinct critical-value arguments exclude saddle-to-saddle Newton connections. It does not itself prove the compact planar decomposition, classify all orbit endpoints or provide the metric gluing estimate. Those are separate problems below.

<a id="sec:finite"></a>

# Finite evidence

A search was run over random monic polynomials with roots in the unit disc. For each sample the region $`\{|f|<1\}`$ was rasterised and shortest grid paths were computed between every pair of roots. The best upper bounds obtained were
``` math
\begin{array}{lrr}
    \text{degree } 5, & 500 \text{ trials}: & 1.1052648928\\
    \text{degree } 6, & 1500 \text{ trials}: & 0.8450414343\\
    \text{degree } 8, & 1500 \text{ trials}: & 0.6203916714\\
    \text{degree } 10, & 1500 \text{ trials}: & 0.4303640486 .
  \end{array}
```
No counterexample candidate was found, and the measured values sit well below the threshold $`2`$. These are grid distances for the sampled configurations: upper bounds on those samples, not bounds over the family. The apparent decrease with degree is a property of the sample, and we draw no conjecture from it. Future searches should target named failure modes—near-degenerate saddles, thin necks, boundary-critical configurations and almost-connected separatrices—and report those diagnostics. Raster paths remain candidate finders, never continuous certificates.

<a id="sec:open"></a>

# Complements and further questions

The dependency chain has five separate gates. A proof, a minimally corrected hypothesis set, or an explicit polynomial or planar counterexample is a decisive answer to any one of them.

<a id="repair-or-refute-the-saddle-block"></a>

## 1. Repair or refute the saddle block

<div id="prob:saddle1041" class="problem">

**Problem 5** (corrected local saddle assembly). Under the hypotheses of Proposition 12, replace the invalid three-ended local model by a four-pronged block or by a block formed after a specified annular cut. Prove that for every $`\eta>0`$ its connector has total Euclidean length below $`\eta`$, uniformly over the selected attachment points, and that the corrected blocks assemble to an embedded tree satisfying
``` math
\operatorname{len}(G_\varepsilon)
 \le\frac1{2\pi}\int_{2\alpha}^{\infty}P_V(t)\,dt+\varepsilon;
```
or give a polynomial or harmonic planar counterexample to that statement.

</div>

The full-disc model $`x^2-y^2`$, an annulus in which lower branches rejoin, two saddles joined by a separatrix and simultaneous saddle levels are mandatory tests. Repeating the one-lower/two-upper assertion does not answer the problem.

<a id="the-compact-ray-cut-decomposition"></a>

## 2. The compact ray-cut decomposition

Let $`p`$ have simple roots, simple nonzero critical points and let $`u=-\log|p|`$. For regular values $`c<T`$, take
``` math
M_{c,T}=\overline{V\cap\{c<u<T\}},
```
and assume explicitly that this is a compact genus-zero surface, its lower boundary is one smooth Jordan curve, its upper boundary consists of $`m`$ smooth root curves, all interior critical points are nondegenerate index-one saddles, the normalised gradient field
``` math
X=\frac{\nabla u}{|\nabla u|^2}=-\frac{p}{p'}
```
is transverse to the level boundaries, and no maximal $`X`$-trajectory has two saddle endpoints.

<div id="prob:reeb1041" class="problem">

**Problem 6** (finite strip decomposition after ray cuts). For every $`\eta>0`$, construct disjoint Morse neighbourhoods $`N_j`$ with $`\sum_j\operatorname{diam}N_j<\eta`$ and a finite set of complete separatrix or regular-flow cuts so that every component of the complement is flow-diffeomorphic to a rectangle
``` math
[a_S,b_S]\times[0,1],\qquad u(\Phi_S(t,s))=t,
```
with connected level sections and no uncut annular component. Give an explicit finite bound $`E(s,m)`$ for the number of strips, or exhibit the minimal missing hypothesis or a counterexample.

</div>

No particular formula such as $`2s+1`$ is presumed. Boundary tangencies, simultaneous levels, branch reunion through an annulus and non-Hausdorff orbit spaces must be handled rather than suppressed.

<a id="metric-fan-in-without-losing-the-coefficient"></a>

## 3. Metric fan-in without losing the coefficient

For a strip $`S`$, write
``` math
\Gamma_t^S=S\cap\{u=t\},\qquad
 P_S(t)=\mathcal H^1(\Gamma_t^S),
```
and let $`k_S`$ be its number of root ends. The flux identity
``` math
\int_{\Gamma_t^S}|\nabla u|\,ds=2\pi k_S
```
gives the average trajectory estimate
``` math
\int_{\Gamma_{t_0}^S}\operatorname{len}(\gamma_x)\,d\mu_{t_0}(x)
 =
 \frac1{2\pi k_S}\int_{a_S}^{b_S}P_S(t)\,dt.
```

<div id="prob:metric1041" class="problem">

**Problem 7** (additive-error strip gluing). Assuming Problem <a href="#prob:reeb1041" data-reference-type="ref" data-reference="prob:reeb1041">6</a>, select trajectories in all strips and connect them through the saddle and root neighbourhoods so that, for every $`\eta>0`$, the resulting embedded tree contains all $`m`$ roots and obeys
``` math
\operatorname{len}(G)
 \le\frac1{2\pi}\int_{2\alpha}^{\infty}P_V(t)\,dt+\eta.
\tag{6.1}\label{eq:metric-fanin1041}
```
The total saddle, annular-cut and root-cap cost must be below $`\eta`$ without a multiplicative loss in $`1/(2\pi)`$.

</div>

For the final strict inequality, use the actual collar slack
``` math
q=\frac1{2\pi}\int_{\alpha}^{2\alpha}P_V(t)\,dt>0
```
and give budgets that keep the perturbation, tree error and transfer cost below fixed fractions of $`q`$. Independently choosing a shortest trajectory in each strip is not enough unless the attachment mismatch is controlled.

<a id="coefficient-perturbation-and-stability"></a>

## 4. Coefficient perturbation and stability

The constant-translation stage is no longer open. Once a finite critical-value family is injective, Lean proves an arbitrarily small translation making every value nonzero and pairwise positive-ray separated (*exists small translation separating arguments*). It also proves the explicit root-retention estimate; a shift below $`\varepsilon`$ keeps all roots in the unit disc when
``` math
((n+1)\varepsilon)^{1/n}+\rho<1
```
(*constant perturbation roots in unit disk*). A constant translation cannot separate initially equal critical values.

<div id="prob:perturb1041" class="problem">

**Problem 8** (two-stage generic perturbation with slack). For fixed root discs, compact collar $`K`$, regular levels $`\alpha/2,\alpha,2\alpha,5\alpha/2`$ and collar slack $`q>0`$, prove that an arbitrarily small
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

Finite planar avoidance and the subsequent constant translation must not be relisted as missing; coefficient genericity, component stability and slack stability are the open content.

<a id="the-global-newton-flow-claim-ceiling"></a>

## 5. The global Newton-flow claim ceiling

<div id="prob:globalflow1041" class="problem">

**Problem 9** (relative global Newton-flow theorem). On a compact regular band
``` math
M_{a,b}=\{z:a\le-\log|p(z)|\le b\},
```
prove real-time existence and the identities
``` math
p(z(t))=e^{-(t-t_0)}p(z(t_0)),\qquad
 u(z(t))=u(z(t_0))+t-t_0
```
throughout every maximal orbit; classify both limiting endpoints among the regular boundary, root ends and finite saddle set; and exclude recurrent, accumulating and non-Hausdorff orbit phenomena. Under pairwise ray separation of the critical values, decide whether the flow is Morse–Smale relative to the boundary or whether the strongest valid conclusion is only absence of saddle-to-saddle connections.

</div>

The checked algebra proves the pointwise value equation and the endpoint-ray consumer. It does not supply global solution theory or an orbit-space graph. A positive stronger theorem must give the graph and a finite edge bound; a negative answer should exhibit the simplest ray-separated polynomial carrying the remaining pathology.

Erdős #1041 remains open. The source now publicly verifies the Newton kernel, finite ray avoidance and quantitative constant-translation root control; the coefficient perturbation, corrected planar decomposition and metric gluing remain the exact unresolved producers.

<a id="statements-and-declarations"></a>

# Statements and declarations

This manuscript is authored exposition, not Lean proof authority. The checked core is the Newton value equation, the exponential first integral, the consumer form of ray separation, the finite planar-avoidance theorem, quantitative constant-translation root retention, and the ray-collision parameterisation. The decomposition and length statements of §<a href="#sec:open" data-reference-type="ref" data-reference="sec:open">6</a> are not proved. The diagnosis of Proposition 12 in §<a href="#sec:gap" data-reference-type="ref" data-reference="sec:gap">4</a> concerns its printed local saddle construction; it does not refute the proposition’s statement. The search results of §<a href="#sec:finite" data-reference-type="ref" data-reference="sec:finite">5</a> are computations.

<a id="app:sources"></a>

# Guide to the formal sources

The public `ErdosProblems.Erdos1041.NewtonFlowRaySeparation` module contains the checked source for this note. The search of §<a href="#sec:finite" data-reference-type="ref" data-reference="sec:finite">5</a> is `scripts/search_counterexample.py` in the source package. The declaration table below is pinned to the shared formal-source commit used throughout this problem-note series.

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L34)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L38)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L50)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L64)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L77)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L80)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L84)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L92)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L107)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L127)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L130)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L147)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L152)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L162)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L179)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L197)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L230)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L257)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L287)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L306)

- [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean#L315)

<div class="thebibliography">

9 T. F. Bloom, *Erdős Problems*, problem 1041. <https://www.erdosproblems.com/1041> P. Erdős, F. Herzog, and G. Piranian, *Metric properties of polynomials*, J. Analyse Math. **6** (1958), 125–148. <https://doi.org/10.1007/BF02790232> `shtuka`, *A Short Path Joining Two Zeros Inside a Polynomial Lemniscate*, manuscript posted 24 March 2026, 48 pp. <https://shtuka123.github.io/1041/main.pdf>. The file at this URL has since been replaced by a shorter partial version that no longer contains Proposition 12; the durable public record of the March version, its defect, and the author’s 26 March 2026 concession is the discussion thread at <https://www.erdosproblems.com/forum/thread/1041>. V. S. Pendyala, *A Degree-Four Lemniscate Path Theorem*, arXiv:2606.24875v1 (2026). <https://arxiv.org/abs/2606.24875>, doi:[10.48550/arXiv.2606.24875](https://doi.org/10.48550/arXiv.2606.24875).

</div>
