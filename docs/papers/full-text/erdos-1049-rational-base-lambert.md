<a id="erdos-1049-rational-base-lambert"></a>

# Arithmetic Boundaries at Base 3/2

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Let $`F(t)=\sum_{n\ge1}(t^{n}-1)^{-1}`$. Problem #1049 asks whether $`F(t)`$ is irrational for every rational $`t>1`$; it remains open, and we prove no irrationality result. At the rational base $`3/2`$ we instead prove two scoped arithmetic obstructions. The first concerns a common-width integer-linear-form approach. Integer scalar multiplication changes the analytic error and the exterior determinant by the same factors, including determinant height, so scalar content alone gives no local-to-Archimedean gain. Homogeneous specialisation at $`(3,2)`$ detects the constant endpoint modulo $`3`$ and the top endpoint modulo $`2`$; under unit-endpoint hypotheses, neither prime can divide both specialised evaluations. Thus an argument using this particular local-divisibility strategy must obtain its $`2`$- and $`3`$-primary gain after primitive normalisation. These results exclude only those mechanisms; they neither prove that local gain is necessary nor rule out polynomial factors before specialisation, cross-row arithmetic, or another proof architecture. We also give a finite-group collision lemma: for positive bottom depth $`R`$, any $`M\ge4R+2S`$ coefficient pairs admit a nonzero selector difference cancelling four prescribed endpoint residues, that is, both endpoint jets in both sequences. This constructs only the signed relation; it does not ensure that the resulting polynomial pair or analytic remainder is nonzero.

Second, we isolate a six-condition coordinatewise clearing scheme at a rational base $`r/s`$. Its hypotheses force $`s^{N+K+1}<r(N+K)`$, which is impossible at $`3/2`$ when the shift and cleared window are nonempty. The associated cleared-tail recurrence $`U_{N+1}=rU_N-Bc(N+1)s^{N+1}`$ is recorded as an explanatory identity; its forcing term satisfies $`2^{N+1}\le Bc(N+1)s^{N+1}`$ for $`s\ge2`$ and positive data, whereas at $`s=1`$ that term is $`Bc(N+1)`$. The recurrence is not derived from rationality and does not exclude other clearing or linear-form constructions.

For comparison, Bundschuh and Väänänen’s published theorem settles a restricted family containing $`7/2`$; Lean checks only the elementary height inequality required by that 1994 criterion \[bv1994\], leaving its analytic irrationality argument external. Polynomial denominator-exponent bounds for a homogenised Padé construction likewise leave the analytic remainder untreated. We also verify elementary membership and exclusion statements for the logarithmic region $`\log b/\log a<81/200`$, but cite no analytic irrationality theorem for that cutoff. Problem #1049 remains open: nothing here proves rationality or irrationality at $`3/2`$, or supplies a method-wide obstruction.

<a id="sec:problem"></a>

# Introduction

Let $`t>1`$ be a rational number and let $`\tau(n)`$ count the divisors of $`n`$. Erdős Problem #1049 asks whether
``` math
F(t)=\sum_{n\ge1}\frac{1}{t^{n}-1}=\sum_{n\ge1}\frac{\tau(n)}{t^{n}}
```
is irrational \[erdos1988, p. 102\]. The two forms agree by expanding $`(t^{n}-1)^{-1}=\sum_{k\ge1}t^{-nk}`$ and collecting the terms with the same exponent, the coefficient of $`t^{-m}`$ being the number of divisors of $`m`$. The question is a conjecture of Chowla; Erdős proved it for every integer $`t\ge2`$ \[erdos1948\]. Bloom’s current catalogue record reproduces the displayed rational-$`t`$ question, labels it *open*, attributes it to Chowla, and points to Erdős’s 1988 statement on p. 102 and the 1948 integer-base theorem \[erdosproblems\]. The same record warns that its status is the website owner’s current assessment and asks readers to cite the original Erdős sources. Accordingly, the catalogue is used here for numbering and current reported status, while the two original publications carry the mathematical claims. The universal conjecture over all rational $`t>1`$ remains open; individual non-integral rational bases are known, including $`7/2`$ below.

Write $`t=r/s`$ in lowest terms with $`r>s\ge1`$, so that $`s=1`$ is exactly the integer case Erdős settled. The resistant explicit base of least naive height $`H(r/s)=\max(r,s)`$ is $`t=3/2`$. A published height criterion of Bundschuh and Väänänen \[bv1994, Thm. 2, p. 177; hypotheses pp. 175–176\] settles a family of rational bases restricted by a height condition; that family contains $`7/2`$ and does not contain $`3/2`$. Between the two lies the question this note is about: what exactly stops the integer-base argument from running at $`3/2`$?

<a id="relation-to-prior-work."></a>

#### Relation to prior work.

The *Formal Conjectures* file for Problem #1049 contains the conjecture and integer-base theorem as `sorry` placeholders, but it also proves the Lambert identity between the two displayed series for rational $`t`$ \[formalconjectures1049\]. In the present $`t>1`$ regime its `lambert_convergent` branch is an ordinary convergent-series proof; the same file’s $`|t|\le1`$ branch instead uses Lean’s convention that the `tsum` of a nonsummable series is zero. Thus it supplies genuine checked prior art for the identity, but no irrationality theorem. The present note formalises propositions about the clearing argument and likewise does not answer the conjecture. Erdős’s positive-integer theorem of 1948 \[erdos1948\] sits inside a larger integer-base literature. At the level of functions, Rivin proves that if a sequence $`\gamma`$ and its divisor-sum sequence are both eventually linearly recurrent, then $`\gamma`$ is finitely supported \[rivin2026, Theorem 1.1, p. 2; proof pp. 6–7\]. His periodic-coefficient corollary therefore shows that
``` math
\sum_{n\ge1}\frac{z^n}{1-z^n}
```
is not a rational function \[rivin2026, Corollary 6.4, p. 9\]. This is an exact structural statement about the function underlying Problem #1049, but it gives no irrationality statement for a special value at $`z=1/t`$: a nonrational function may take rational values at particular rational points. In 1991 Borwein proved the irrationality of shifted series $`\sum_{n\ge1}(t^{n}+w)^{-1}`$ at integer bases $`t\ge2`$, for every nonzero rational $`w`$ with $`w\ne-t^m`$ for all $`m\ge1`$, by Padé approximation rather than by digit clearing; his estimates also show that these values are not Liouville numbers \[borwein1991, Thm. 4, pp. 257–258\]. In 2001 Van Assche recovered the integer-base irrationality and the bound $`\mu(F(p))\le 2\pi^2/(\pi^2-2)=2.50828\ldots`$ using little $`q`$-Legendre Padé approximants  \[vanassche2001, Thm. 1, p. 10; proof pp. 10–11\]. His more general Theorem 3 proves irrationality of $`\sum_{k\ge1}(cp^k-1)^{-1}`$ for an integer $`p>1`$ and fixed rational $`c`$ away from the poles \[vanassche2001, Thm. 3, p. 14\]; it does not cover a rational noninteger base $`t`$ in $`F(t)`$, because the multiplier needed to write $`t^k`$ over an integer base varies with $`k`$. In 2013 Vandehey proved that $`\sum_{n\ge1}d(n)a_n/b^n`$ is irrational whenever $`b>1`$ is an integer and $`(a_n)`$ ranges in a finite integer alphabet excluding zero; taking $`a_n=(-1)^n`$ completes the elementary digit method for integer bases $`b\le-2`$ \[vandehey2013, Thm. 1.2, p. 2\]. His companion theorem permits a finite alphabet of nonnegative integers containing zero, provided the coefficient sequence is not eventually zero \[vandehey2013, Thm. 1.1, p. 2\]. All three retain an integer base. In 2004 Zudilin obtained the uniform bound $`\mu(F(p))\le2.46497868\ldots`$ for every integer $`p\notin\{0,\pm1\}`$, by way of Heine’s basic transform and a permutation group \[zudilin2004, Thm. 1, p. 154; Secs. 4–5, pp. 159–162\]. The ordinary-hypergeometric antecedent is Rhin and Viola’s $`S_5`$ action and twelve-coset denominator reduction for rational forms in $`\zeta(2)`$ \[rhinviola1996, Sec. 3, pp. 38–42; Sec. 4, pp. 46–51\]. Those sources motivate the permutation, denominator and polynomial- specialisation architecture of Section <a href="#sec:endpoints" data-reference-type="ref" data-reference="sec:endpoints">3</a>; the endpoint lemmas there are abstract and are not yet applied to either source’s actual coefficient family. The neighbouring problem of Lambert subseries $`\sum_{n\in A}(t^{n}-1)^{-1}`$ over a restricted index set $`A`$ is treated by Kovač and Tao \[kovactao2024\]. The rational non-integer progress relevant here is instead the height criterion of Bundschuh and Väänänen \[bv1994\]. No claim of priority is made for anything below, which concerns the formal status of an argument rather than a new theorem about $`F(t)`$.

<a id="erdőss-integer-base-argument-in-outline."></a>

#### Erdős’s integer-base argument, in outline.

For an integer $`b\ge2`$, Erdős rewrites $`F(b)=\sum_{n\ge1}\tau(n)b^{-n}`$. A Chinese-remainder construction forces arbitrarily long blocks in which the divisor coefficients have the powers of $`b`$ needed to make the corresponding base-$`b`$ digits zero. Explicit bounds control the middle and far tails, while positivity proves that the expansion does not terminate. The resulting base-$`b`$ expansion has arbitrarily long zero blocks without being eventually zero and is therefore irrational  \[erdos1948, pp. 63–66\].

<a id="the-direct-cut-and-clear-attempt-studied-here."></a>

#### The direct cut-and-clear attempt studied here.

A more naive route is to suppose $`F(b)=p/q`$, cut at $`N`$, and multiply the remaining identity by $`qb^N`$. This does not by itself trap a positive integer below $`1`$: the first uncleared tail contribution is $`q\tau(N+1)/b`$. The sections below isolate additional corridor hypotheses under which a bounded-window version of this route would work, and then show why those hypotheses fail at $`3/2`$.

Write $`\beta=r/s`$ for the base and $`c(n)`$ for the coefficient of $`\beta^{-n}`$, so that $`c=\tau`$ in the case at hand. The term $`c(n)\beta^{-n}`$ is $`c(n)s^{n}/r^{n}`$. Clearing the power of $`r`$ leaves the numerator factor $`s^{n}`$ in place. That factor is invisible when $`s=1`$ and grows geometrically when $`s\ge2`$. At $`3/2`$ it is $`2^{n}`$.

<a id="terminology."></a>

#### Terminology.

The linear-form route uses polynomial pairs before specialisation and integer pairs afterwards. We reserve *row* for an integer pair $`(U,V)`$. Its *integer scalar content* is $`\gcd(|U|,|V|)`$; a row is *primitive* when this number is $`1`$, and dividing by it is *primitive normalisation*. A polynomial pair may instead have a polynomial common factor in $`\mathbb{Z}[X]`$; that is a different operation and is not called row content here. The *exterior determinant* of two integer rows is $`U_{n}V_{m}-U_{m}V_{n}`$, the determinant of the $`2\times2`$ matrix they form. Two quantities attached to that determinant are compared throughout: an integer dividing it, which is a local gain, and its absolute value, which is an Archimedean cost; we call that comparison the *local-to-Archimedean balance*. The *endpoints* of a coefficient polynomial, taken relative to the declared width $`W`$ of Section <a href="#sec:endpoints" data-reference-type="ref" data-reference="sec:endpoints">3</a>, are its constant coefficient and its coefficient at $`W`$; we call these the *constant endpoint* and the *top endpoint*, so the top endpoint is the coefficient at $`W`$ and not the leading coefficient unless the two agree. A *unit* endpoint is one equal to $`\pm1`$, the units of $`\mathbb{Z}`$; Theorem <a href="#res:endpoints" data-reference-type="ref" data-reference="res:endpoints">3</a> is the reason only these two coefficients decide divisibility by $`3`$ and by $`2`$ after specialisation at $`(3,2)`$. A *jet* is a residue of a specialised coefficient modulo a prime power: the bottom jet is its residue modulo $`3^{R}`$ and the top jet its residue modulo $`2^{S}`$, and $`R`$ and $`S`$ are the bottom and top *depths*. A jet vanishes exactly when the prime power in question divides the specialised coefficient.

<a id="the-shortfall-at-32."></a>

#### The shortfall at $`3/2`$.

The elementary route and the linear-form route are both examined below. For the coordinatewise clearing scheme the leftover at each step is the forcing term of an exact recurrence, of size at least $`2^{N+1}`$ whenever $`s\ge2`$ and the scaling constant $`B`$ and the coefficient $`c(N+1)`$ are at least $`1`$ (Theorem <a href="#res:forcing" data-reference-type="ref" data-reference="res:forcing">17</a>), and the scheme itself is excluded at $`3/2`$ for every shift $`N\ge1`$ and every cleared window of width $`K\ge1`$ (Theorem <a href="#res:nocorridor" data-reference-type="ref" data-reference="res:nocorridor">15</a>). For the linear-form constructions we examine two possible sources of $`2`$-adic and $`3`$-adic gain. Integer scalar content is exactly neutral, since it scales the exterior determinant and its absolute height by the same factor (Theorem <a href="#res:content" data-reference-type="ref" data-reference="res:content">1</a>), while unit endpoints keep both $`2`$ and $`3`$ out of any common divisor of the two specialised evaluations (Theorem <a href="#res:endpoints" data-reference-type="ref" data-reference="res:endpoints">3</a> and Proposition <a href="#res:commonmult" data-reference-type="ref" data-reference="res:commonmult">5</a>). Corollary <a href="#res:nomult" data-reference-type="ref" data-reference="res:nomult">7</a> states the two scoped exclusions together; neither is claimed to be necessary for every linear-form proof. Separately, the scalar parameter margin is negative under the assumed source inequality (Theorem <a href="#res:scalar" data-reference-type="ref" data-reference="res:scalar">10</a>). One candidate pursued here is additive: an integer relation among rows that cancels the endpoint jets. Theorem <a href="#res:jetkernel" data-reference-type="ref" data-reference="res:jetkernel">8</a> shows that a nonzero relation with coefficients in $`\{-1,0,1\}`$ cancelling all four jets exists whenever the bottom depth is positive and the number of coefficient pairs is at least $`4R+2S`$. It does not show that the resulting combination has a nonzero polynomial pair or a nonzero remainder. Problem <a href="#prob:kernel" data-reference-type="ref" data-reference="prob:kernel">22</a> gives a precise sufficient specification for that particular candidate architecture, not a necessary condition for solving Problem #1049. Sections <a href="#sec:sevenhalves" data-reference-type="ref" data-reference="sec:sevenhalves">6</a> and <a href="#sec:pade" data-reference-type="ref" data-reference="sec:pade">7</a> record two external routes and what each leaves unproved at $`3/2`$.

<a id="sharpness."></a>

#### Sharpness.

Two questions of scope are worth isolating. The corridor bound of Theorem <a href="#res:corridorbound" data-reference-type="ref" data-reference="res:corridorbound">12</a> is exponential on the left and linear on the right, so for a fixed numerator and any $`s\ge2`$ a corridor can survive only for bounded $`N+K`$; the base $`3/2`$ is the case in which the crossing has already happened at the smallest admissible window, which is why the exclusion there holds for all $`N\ge1`$ and $`K\ge1`$ with no further restriction. The height criterion of \[bv1994\] is restricted by a height condition satisfied at $`7/2`$ and not at $`3/2`$, so the two bases are separated by that criterion rather than by anything proved here.

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

| Statement | Status | Treatment here |
|:---|:---|:---|
| Irrationality of $`F(3/2)`$ | Open | Not proved; the results below exclude only named proof architectures and imply no arithmetic property of this value. |
| Irrationality at some rational non-integer base | Proved elsewhere | The height criterion of \[bv1994\]; cited, not formalised. |
| Nonrationality of the Lambert function $`\sum_{n\ge1}z^n/(1-z^n)`$ | Proved elsewhere | Rivin’s Corollary 6.4 \[rivin2026, p. 9\]; a functional statement, not a special-value theorem. |
| Integer scalar content is neutral for the local-to-Archimedean balance | Proved here | Theorem <a href="#res:content" data-reference-type="ref" data-reference="res:content">1</a>, including the absolute determinant height. |
| Homogeneous endpoint residues at $`(3,2)`$ | Proved here | Theorem <a href="#res:endpoints" data-reference-type="ref" data-reference="res:endpoints">3</a>. |
| Common divisor of the two specialised evaluations avoids $`2`$ and $`3`$ | Proved here | Proposition <a href="#res:commonmult" data-reference-type="ref" data-reference="res:commonmult">5</a>; under unit endpoint hypotheses. |
| No gain from integer scalar content or from the stated common divisor at $`3/2`$ | Deduced here | Corollary <a href="#res:nomult" data-reference-type="ref" data-reference="res:nomult">7</a>; an ordinary deduction from the two preceding rows, not separately formalised. |
| Four-jet collision at $`M\ge4R+2S`$ coefficient pairs | Proved here | Theorem <a href="#res:jetkernel" data-reference-type="ref" data-reference="res:jetkernel">8</a>; sufficient, at positive bottom depth. |
| Scalar margin on Zudilin’s parameter cone | Negative under source input | Theorem <a href="#res:scalar" data-reference-type="ref" data-reference="res:scalar">10</a>; the source inequality is assumed. |
| Corridor forces $`s^{N+K+1}<r(N+K)`$ | Proved here | Theorem <a href="#res:corridorbound" data-reference-type="ref" data-reference="res:corridorbound">12</a>. |
| No corridor at base $`3/2`$ | Proved here | Theorem <a href="#res:nocorridor" data-reference-type="ref" data-reference="res:nocorridor">15</a>; a statement about the clearing scheme. |
| Cleared-tail recurrence | Proved here | Theorem <a href="#res:tailrec" data-reference-type="ref" data-reference="res:tailrec">16</a>, an exact identity. |
| Forcing term at least $`2^{N+1}`$ for $`s\ge2`$ | Proved here | Theorem <a href="#res:forcing" data-reference-type="ref" data-reference="res:forcing">17</a>; at $`s=1`$ the term is $`Bc(N+1)`$. |
| The elementary $`7/2`$ height condition | Proved here | Theorem <a href="#res:sevenhalves" data-reference-type="ref" data-reference="res:sevenhalves">19</a>; the analytic theorem of \[bv1994\] remains external. |
| Membership of $`31/4`$ and its powers in the $`81/200`$ logarithmic region | Proved here | Exact elementary inequalities; no analytic irrationality theorem is inferred. |
| Exclusion of $`3/2`$ from both recorded height regions | Proved here | $`3^{81}<2^{200}`$ gives $`81/200<\log2/\log3`$. |
| Explicit rectangular exponent-model threshold does not improve the classical margin | Proved here | Algebraic statement about the displayed exponent formulas, with equality only at the classical endpoint. |
| Padé denominator-exponent bounds | Proved here | Section <a href="#sec:pade" data-reference-type="ref" data-reference="sec:pade">7</a>; exponent arithmetic only. |
| Padé remainder positivity and decay | Not treated | Section <a href="#sec:pade" data-reference-type="ref" data-reference="sec:pade">7</a>. |
| Common-width simultaneous endpoint-jet construction | Candidate sufficient route | Problem <a href="#prob:kernel" data-reference-type="ref" data-reference="prob:kernel">22</a>; not necessary for every proof and not supplied by the collision theorem alone. |

<a id="structure."></a>

#### Structure.

Section <a href="#sec:primitive" data-reference-type="ref" data-reference="sec:primitive">2</a> proves that integer scalar content is neutral for the local-to-Archimedean balance. Section <a href="#sec:endpoints" data-reference-type="ref" data-reference="sec:endpoints">3</a> proves the endpoint congruences at $`(3,2)`$, deduces from them and from Section <a href="#sec:primitive" data-reference-type="ref" data-reference="sec:primitive">2</a> that neither integer scalar content nor a common divisor of the two specialised evaluations supplies the targeted endpoint gain, gives the four-jet collision count, and records one further exclusion on Zudilin’s scalar parameters. Sections <a href="#sec:corridor" data-reference-type="ref" data-reference="sec:corridor">4</a> and <a href="#sec:tail" data-reference-type="ref" data-reference="sec:tail">5</a> return to the elementary clearing scheme and record what the residue $`s^{n}`$ costs there, first as an exclusion and then as an exact recurrence with a lower bound on the surviving term. Sections <a href="#sec:sevenhalves" data-reference-type="ref" data-reference="sec:sevenhalves">6</a> and <a href="#sec:pade" data-reference-type="ref" data-reference="sec:pade">7</a> record what is and is not formalised of two external routes, together with the separate $`81/200`$ logarithmic comparison. Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">8</a> separates kernel escape from asymptotic adequacy and states the remaining obligations. Linked phrases open the corresponding Lean declaration at the pinned source revision 76b5b0a7ed5d.

**Keywords.** irrationality; Lambert series; rational base; Padé approximation; Lean 4. **MSC 2020.** 11J72 (primary); 11J82, 68V20 (secondary).

<a id="sec:primitive"></a>

# Integer scalar content is neutral

An irrationality argument by linear forms replaces the clearing scheme by explicit rational approximation: one constructs integer linear forms in $`1`$ and $`F(\beta)`$ whose analytic decay outruns the height of their common denominator. For an integer coefficient pair $`(U,V)`$ and a real target $`S`$, put
``` math
L_S(U,V)=US-V,
 \qquad
 \Delta\bigl((U_n,V_n),(U_m,V_m)\bigr)=U_nV_m-U_mV_n.
```
We call $`L_S(U,V)`$ the *error* of the row at $`S`$; a good approximation is one that makes it small. The second expression is the exterior determinant of the two rows, and it eliminates $`S`$ exactly:
``` math
\Delta=U_mL_S(U_n,V_n)-U_nL_S(U_m,V_m).
```
This identity is what makes the determinant useful. Since $`\Delta`$ is an integer, if it does not vanish then
``` math
1\le|\Delta|
  \le|U_m|\,\bigl|L_S(U_n,V_n)\bigr|+|U_n|\,\bigl|L_S(U_m,V_m)\bigr|,
```
and the two errors cannot both be smaller than $`1/(|U_n|+|U_m|)`$. The determinant therefore carries two competing quantities at once, an integer that divides it and its own absolute value, and the theorem below is about how a rescaling moves them.

<div id="res:content" class="theorem">

**Theorem 1** (integer-scalar-content no-go). *Let $`S`$ be real, let $`(U_n,V_n)`$ and $`(U_m,V_m)`$ be pairs of integers, and let $`c_n,c_m`$ be integers. Then
``` math
L_S(c_nU_n,c_nV_n)=c_nL_S(U_n,V_n),
```
``` math
\Delta\bigl(c_n(U_n,V_n),c_m(U_m,V_m)\bigr)
 =c_nc_m\Delta\bigl((U_n,V_n),(U_m,V_m)\bigr),
```
and consequently
``` math
\left|\Delta\bigl(c_n(U_n,V_n),c_m(U_m,V_m)\bigr)\right|
 =|c_n|\,|c_m|\,
   \left|\Delta\bigl((U_n,V_n),(U_m,V_m)\bigr)\right|.
```
In particular $`c_nc_m`$ divides the scaled determinant. Hence a local divisor supplied only by the two integer scalar factors is paid for by exactly the same factor in the Archimedean determinant height.*

</div>

<div class="proof">

*Proof.* All three identities are routine expansions in $`\mathbb{Z}`$ or $`\mathbb{R}`$; the divisibility statement uses the primitive determinant as its witness. ◻

</div>

Informally, Theorem <a href="#res:content" data-reference-type="ref" data-reference="res:content">1</a> says that multiplying specialised integer rows by scalar factors moves the local gain and the Archimedean cost by exactly the same amount. Within an argument whose only extra divisor is integer scalar content, primitive normalisation therefore loses no net gain. This says nothing about polynomial factors before specialisation, cross-row common factors, determinant-specific arithmetic, or additive combinations.

<div id="ex:content" class="example">

**Example 2**. Take $`(U_n,V_n)=(1,2)`$ and $`(U_m,V_m)=(3,5)`$, so that $`\Delta=1\cdot5-3\cdot2=-1`$. Multiplying the first row by $`c_n=6`$ and the second by $`c_m=10`$ gives the rows $`(6,12)`$ and $`(30,50)`$, whose determinant is $`6\cdot50-30\cdot12=-60`$. That determinant is now divisible by $`60`$, which looks like a local gain of $`60`$; and its absolute value has risen from $`1`$ to $`60`$, which is a cost of exactly the same size.

</div>

Lean checks the error identity in [error scaling](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L84), the determinant identity in [content factorisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L94), the exact absolute-height identity in [absolute determinant scaling](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L104), and the divisor statement in [content-product divisibility](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L116). The elimination identity is the checked [exterior determinant identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L124).

The key point is that the two scalings are the same scaling. Each identity on its own is a one-line expansion, and the interest of the theorem is not in any one of them. Taken together they say that the factor $`c_nc_m`$ which a rescaling introduces into the determinant reappears undiminished, as $`|c_n|\,|c_m|`$, in the absolute value of that determinant. The third identity is displayed with absolute values for exactly that reason: it is what makes the statement one about the Archimedean height and not about divisibility alone. Whatever $`c_n`$ and $`c_m`$ are, a rescaling therefore leaves the balance between the local divisor and that height where it was.

The theorem does not construct primitive Padé rows, estimate their remainders, or prove that their exterior determinant is nonzero. It removes one source of apparent gain: multiplying a useful row by a large common integer cannot improve the local-to-Archimedean balance. Within a construction whose proposed gain comes only from those integer scalars, the rows may be primitive-normalised without a net loss. This does not say that every candidate family must use such a normalisation or that every proof needs separate $`2`$-adic and $`3`$-adic gain. The theorem quantifies over arbitrary integer pairs, so it applies whenever a construction has reached that specialised-row stage.

<a id="sec:endpoints"></a>

# Endpoint residues at $`(3,2)`$ and the four-jet kernel

Zudilin’s treatment of $`q`$-harmonic series \[zudilin2004\] builds linear forms of the shape used in Section <a href="#sec:primitive" data-reference-type="ref" data-reference="sec:primitive">2</a> out of Heine’s basic transform. The generic endpoint and jet lemmas below concern arbitrary integral coefficient pairs of this shape; they do not construct or instantiate Zudilin’s actual polynomial family. Each lemma uses no property beyond integrality and quantifies over arbitrary elements of $`\mathbb{Z}[X]`$. The exception is Theorem <a href="#res:scalar" data-reference-type="ref" data-reference="res:scalar">10</a> at the end of the section, which concerns the scalar parameters of Zudilin’s cone rather than the coefficient polynomials.

Substituting $`X=3/2`$ into an integer polynomial produces a rational number, and multiplying by a power of $`2`$ clears its denominator. The following evaluation records that cleared numerator, so that all the arithmetic below stays inside $`\mathbb{Z}`$. For $`P(X)=\sum_i p_iX^i\in\mathbb{Z}[X]`$ and a declared width $`W\ge0`$, put
``` math
H_W(P)=\sum_{i=0}^{W}p_i\,3^i2^{W-i}.
```
This is the [homogeneous endpoint evaluation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L96). It is homogeneous in the sense that $`X^{i}`$ is replaced by $`3^{i}2^{W-i}`$, so the numerator and the denominator of the base are carried symmetrically. When $`W\ge\deg P`$ it is exactly the cleared numerator, since
``` math
\sum_{i=0}^{W}p_i\,3^i2^{W-i}=2^{W}\sum_{i=0}^{W}p_i\left(\tfrac32\right)^{i}
 =2^{W}P\!\left(\tfrac32\right).
```

<div id="res:endpoints" class="theorem">

**Theorem 3** (endpoint residues). *Let $`P=\sum_ip_iX^i\in\mathbb{Z}[X]`$ and let $`W\ge0`$. Then
``` math
H_W(P)\equiv p_0\,2^W\pmod 3,\qquad
 H_W(P)\equiv p_W\,3^W\pmod 2.
```
Consequently a unit constant coefficient prevents divisibility by $`3`$, and a unit coefficient at the declared width $`W`$ prevents divisibility by $`2`$.*

</div>

<div class="proof">

*Proof.* Modulo $`3`$, every summand with $`i>0`$ vanishes; modulo $`2`$, every summand with $`i<W`$ vanishes. The remaining powers are units in the corresponding residue fields. ◻

</div>

Since $`2^{W}`$ is invertible modulo $`3`$ and $`3^{W}`$ is invertible modulo $`2`$, the two congruences say more than the stated consequence: divisibility of $`H_W(P)`$ by $`3`$ is decided by $`p_0`$ alone, and divisibility by $`2`$ by $`p_W`$ alone. The rest of the coefficient vector is invisible to both primes. The coefficient $`p_W`$ is the top coefficient of $`P`$ exactly when $`\deg P=W`$, and is zero when $`\deg P<W`$; the identity $`H_W(P)=2^{W}P(3/2)`$ likewise holds only for $`\deg P\le W`$.

<div id="ex:endpoints" class="example">

**Example 4**. Take $`W=2`$. The three polynomials below differ only at an endpoint.

<div class="center">

| $`P`$      | $`H_2(P)`$                     | $`3\mid H_2(P)`$ | $`2\mid H_2(P)`$ |
|:-----------|:-------------------------------|:----------------:|:----------------:|
| $`X^2+1`$  | $`1\cdot4+0\cdot6+1\cdot9=13`$ |        no        |        no        |
| $`X^2+3`$  | $`3\cdot4+0\cdot6+1\cdot9=21`$ |       yes        |        no        |
| $`2X^2+1`$ | $`1\cdot4+0\cdot6+2\cdot9=22`$ |        no        |       yes        |

</div>

The first has both endpoints equal to $`1`$ and its evaluation, $`13`$, is divisible by neither prime; as a check, $`2^{2}\bigl((3/2)^2+1\bigr)=13`$. The second and third show that each hypothesis is used: spoiling the constant endpoint admits $`3`$, and spoiling the top endpoint admits $`2`$.

</div>

The congruences are the [bottom-endpoint identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L201) and [top-endpoint identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L215); the unit consequences are the [constant-endpoint obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L233) and [top-endpoint obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L251).

The proof is two lines, but the shape of the statement is not incidental. The difficulty lies in the fact that the specialisation sees a different endpoint at each of the two primes: modulo $`3`$ only the constant coefficient survives, and modulo $`2`$ only the top one does. The two exclusions are therefore conditions at opposite ends of the coefficient vector, and the statement below imposes one at each end, on the two entries of a single coefficient pair.

<div id="res:commonmult" class="proposition">

**Proposition 5** (common divisor). *Let $`U,V\in\mathbb{Z}[X]`$ and let $`W\ge0`$. If $`U`$ has unit top endpoint, $`V`$ has unit constant endpoint, and an integer $`c`$ divides both $`H_W(U)`$ and $`H_W(V)`$, then
``` math
2\nmid c\qquad\text{and}\qquad 3\nmid c.
```*

</div>

This is the checked [common-divisor exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L293). The proposition does not say that the two evaluations are coprime; it says that whatever they share misses both of the primes that matter at $`3/2`$.

<div id="ex:commonmult" class="example">

**Example 6**. Take $`W=2`$, $`U=X^2+3`$ and $`V=5X^2+1`$. The top endpoint of $`U`$ and the constant endpoint of $`V`$ are both $`1`$, and
``` math
H_2(U)=3\cdot4+1\cdot9=21,\qquad H_2(V)=1\cdot4+5\cdot9=49 .
```
Here $`\gcd(21,49)=7`$, so a common divisor does exist and is not small; it is simply coprime to $`6`$.

</div>

<div id="res:nomult" class="corollary">

**Corollary 7** (no gain from integer scalar content or the stated common divisor at $`3/2`$). *Under the endpoint hypotheses of Proposition <a href="#res:commonmult" data-reference-type="ref" data-reference="res:commonmult">5</a>, neither integer scalar content of specialised rows nor a common divisor of the two specialised evaluations $`H_W(U)`$ and $`H_W(V)`$ can supply factors $`2`$ and $`3`$ by those mechanisms in the common-width endpoint architecture studied here.*

</div>

<div class="proof">

*Proof.* By Theorem <a href="#res:content" data-reference-type="ref" data-reference="res:content">1</a> integer scalar content multiplies the analytic error and the exterior determinant, including the absolute determinant height, by exactly the factors it introduces, so a divisor obtained that way is paid for by the same factor in that height. By Proposition <a href="#res:commonmult" data-reference-type="ref" data-reference="res:commonmult">5</a> an integer dividing both specialised evaluations is divisible by neither $`2`$ nor $`3`$. ◻

</div>

Both ingredients are Lean-checked; the combination is an ordinary deduction and is not separately formalised. The corollary excludes two ways of producing the targeted gain. It does not show that a gain of that kind is necessary for a proof by linear forms at $`3/2`$.

Corollary <a href="#res:nomult" data-reference-type="ref" data-reference="res:nomult">7</a> excludes the two multiplicative mechanisms above, and one candidate pursued in the rest of this section is additive: rather than multiplying one row by a scalar, take an integer combination of several rows and ask that the combination be divisible where the individual rows are not. The endpoint congruences are the first case of a divisibility condition that can be imposed to any depth, and it is that condition, read additively, which is counted below.

We first raise the two congruences to prime powers. Fix depths $`R,S\ge0`$. For $`P\in\mathbb{Z}[X]`$ the *bottom jet* $`J_{3,R}(P)`$ is the residue of $`H_W(P)`$ modulo $`3^R`$, and the *top jet* $`J_{2,S}(P)`$ is its residue modulo $`2^S`$; Theorem <a href="#res:endpoints" data-reference-type="ref" data-reference="res:endpoints">3</a> computes them at $`R=S=1`$. Their vanishing is exactly the requested divisibility:
``` math
J_{3,R}(P)=0\iff 3^R\mid H_W(P),\qquad
 J_{2,S}(P)=0\iff 2^S\mid H_W(P).
```
These are the checked [bottom-jet divisibility criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L189) and [top-jet divisibility criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L195). The *four-jet signature* of a coefficient pair $`(U,V)`$ is then the quadruple
``` math
\bigl(J_{3,R}(U),J_{3,R}(V),J_{2,S}(U),J_{2,S}(V)\bigr)
 \in(\mathbb{Z}/3^R\mathbb{Z})^2\times(\mathbb{Z}/2^S\mathbb{Z})^2 ,
```
two residues for each of the two primes, one from each entry of the pair. By the displayed criteria it vanishes exactly when $`3^R`$ divides both specialised entries and $`2^S`$ divides both.

For this candidate architecture, this turns the targeted local divisor into an additive congruence-kernel problem: what is sought is no longer a common divisor of the two evaluations, but a vector of small integer coefficients on which four residues vanish at once. Since $`H_W`$ is linear in the coefficients of $`P`$, the four-jet signature of a combination is the corresponding combination of signatures, which is what makes the following count possible.

<div id="res:jetkernel" class="theorem">

**Theorem 8** (binary four-jet collision). *Fix a width $`W`$ and depths $`R,S`$, and let $`(U_j,V_j)_{j<M}`$ be any $`M`$ pairs of integral polynomials. Call a subset of $`\{0,\dots,M-1\}`$, equivalently a vector of $`\{0,1\}^M`$, a *binary selector*. If the $`2^M`$ binary selectors outnumber the finite four-jet target
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
which proves the stated sufficient threshold. ◻

</div>

The target count is the checked [four-jet target cardinality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L129); the abstract collision is the checked [four-jet pigeonhole kernel](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L140), and the linear sufficient condition is the checked [rank–depth collision threshold](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L159). The count is a routine pigeonhole; the reformulation above is what makes it relevant. Pigeonhole cancellation itself requires no independence. Additional information about the input family is needed to ensure that the resulting nonzero selector difference has a nonzero combined polynomial pair and analytic remainder. None of the statements proved here supplies such a family or proves either nonvanishing conclusion.

<div id="ex:jetcount" class="example">

**Example 9**. At depths $`R=S=1`$ the four-jet target is $`(\mathbb{Z}/3\mathbb{Z})^2\times(\mathbb{Z}/2\mathbb{Z})^2`$, of cardinality $`9\cdot4=36`$, and the threshold reads $`M\ge4\cdot1+2\cdot1=6`$. With six pairs there are $`2^{6}=64`$ binary selectors against $`36`$ targets, so two of them collide and their difference is a vector in $`\{-1,0,1\}^{6}`$, not identically zero, killing all four jets.

</div>

Informally, the theorem says only this: once there are at least $`4R+2S`$ pairs and the bottom depth $`R`$ is positive, some coefficient vector in $`\{-1,0,1\}^M`$, not identically zero, kills all four jets of the corresponding combination. It does not say that the combination is nonzero as a pair of polynomials, and it does not say that its remainder is nonzero. Those are the two obligations Problem <a href="#prob:kernel" data-reference-type="ref" data-reference="prob:kernel">22</a> carries.

One further exclusion is recorded here. It concerns the scalar parameters of Zudilin’s cone rather than the coefficient polynomials.

<div id="res:scalar" class="theorem">

**Theorem 10** (scalar margin no-go). *Let $`C_1>0`$. If $`C_0\le0`$ or $`2C_0\le C_1`$, then
``` math
C_0\log 3-C_1\log 2<0.
```*

</div>

Written multiplicatively, the conclusion is $`3^{C_0}<2^{C_1}`$. The inequality is immediate from $`\log3<2\log2`$ and $`C_1>0`$, and is the checked [three-halves scalar margin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L323). The interest is in the fence around it. The primary Zudilin theorem \[zudilin2004, Theorem 1, p. 154; Sec. 5, pp. 161–162\] supplies an integer-base irrationality-exponent estimate on its parameter cone, and the elementary inequality $`\mu\ge2`$ then forces $`2C_0\le C_1`$ whenever $`C_0>0`$; Lean checks that implication separately. The primary theorem assumes an integer base $`p=1/q`$. It does not state a rational $`p=3/2`$ theorem, so the all-scale coefficient construction and rational specialisation remain external to the checked result, which is the scalar parameter margin alone.

<a id="sec:corridor"></a>

# Failure of coordinatewise clearing at $`3/2`$

This section and the next return to the elementary route and record what the residue $`s^{n}`$ costs there. We first isolate the arithmetic that the clearing scheme leaves behind, in a form that does not mention the series. The point of doing so is that the clearing argument asks for two things at once, that a power of the numerator divide what has been accumulated and that what survives be small, and these are easier to play off against each other once the series has been discarded and only six natural numbers remain.

<div id="def:corridor" class="definition">

**Definition 11** (coordinatewise corridor). Let $`a,b,N,K,Q,D`$ be natural numbers. Say that $`(a,b,N,K,Q,D)`$ is a *coordinatewise corridor* when
``` math
a>0,\qquad Q>0,\qquad D>0,\qquad D\le N+K,\qquad
 a^{K}\mid QD,\qquad Q\,b^{\,N+K+1}<a^{\,K+1}.
```

</div>

The reading is: $`a`$ and $`b`$ are the numerator and denominator of the base, playing the roles of $`r`$ and $`s`$ in the introduction, so that $`(a,b)=(3,2)`$ is the case of interest; $`N`$ is the shift, $`K`$ is the width of the cleared window, $`Q`$ is the accumulated clearing factor, and $`D`$ is the final coefficient being cleared. The bound $`D\le N+K`$ is the only property of the coefficient used; for the divisor-counting coefficient it holds because $`\tau(n)\le n`$. The divisibility $`a^{K}\mid QD`$ is the requirement that clearing succeeded coordinatewise, and the last inequality is the tail estimate that makes the trapped integer smaller than $`1`$. The name records the shape of the constraint: the divisibility bounds $`a^{K}`$ from above by $`Q(N+K)`$, the tail estimate bounds $`a^{K+1}`$ from below by $`Q\,b^{\,N+K+1}`$, and admissible parameters must fit in the band between them. The definition is the [corridor predicate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L113).

<div id="res:corridorbound" class="theorem">

**Theorem 12** (corridor bound). *If $`(a,b,N,K,Q,D)`$ is a coordinatewise corridor, then
``` math
b^{\,N+K+1}<a\,(N+K).
```*

</div>

<div class="proof">

*Proof.* A routine divisibility computation. Since $`QD>0`$ and $`a^{K}\mid QD`$, we have $`a^{K}\le QD`$, and $`D\le N+K`$ gives $`a^{K}\le Q(N+K)`$. Hence
``` math
Q\,b^{\,N+K+1}<a^{\,K+1}=a^{K}\cdot a\le Q(N+K)\cdot a,
```
and cancelling the positive factor $`Q`$ gives the claim. ◻

</div>

Formalised as the [power-versus-linear consequence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L121).

The inequality of Theorem <a href="#res:corridorbound" data-reference-type="ref" data-reference="res:corridorbound">12</a> is where the integer and rational cases part. At $`b=1`$ it reads $`1<a(N+K)`$, which holds for every $`a\ge2`$ and every nonempty window; this necessary inequality imposes no obstruction. The other corridor hypotheses remain in force. At $`b\ge2`$ the left side is exponential in $`N+K`$ and the right side is linear, so the corridor can survive only for small $`N+K`$. At $`(a,b)=(3,2)`$ the crossing has already happened at the smallest admissible window.

<div id="ex:corridor" class="example">

**Example 13**. Take the smallest window, $`N=K=1`$, and numerator $`a=3`$. At $`b=1`$ the tuple $`(3,1,1,1,3,1)`$ is a corridor: $`D=1\le2`$, the divisibility reads $`3\mid3`$, and the tail estimate reads $`3\cdot1^{3}=3<3^{2}=9`$. At $`b=2`$ no choice works. The tail estimate becomes $`Q\cdot2^{3}<3^{2}`$, which forces $`Q=1`$; the divisibility then reads $`3\mid D`$, and the only candidates are $`D=1`$ and $`D=2`$, neither divisible by $`3`$. This is the proof of Theorem <a href="#res:corridorbound" data-reference-type="ref" data-reference="res:corridorbound">12</a> in miniature: it derives $`a^{K}\le Q(N+K)`$, here $`3\le2`$.

</div>

<div id="res:exp" class="proposition">

**Proposition 14**. *For every natural number $`x\ge2`$ we have $`3x<2^{\,x+1}`$.*

</div>

<div class="proof">

*Proof.* A routine induction from $`x=2`$, where $`6<8`$. For the step, $`2^{x+1}\ge2^{2}>3`$ when $`x\ge1`$, so $`3(x+1)=3x+3<2^{x+1}+2^{x+1}=2^{x+2}`$. ◻

</div>

Formalised as the [exponential comparison](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L142).

<div id="res:nocorridor" class="theorem">

**Theorem 15** (no corridor at base $`3/2`$). *For all $`N\ge1`$ and $`K\ge1`$ and all natural $`Q,D`$, the tuple $`(3,2,N,K,Q,D)`$ is not a coordinatewise corridor.*

</div>

<div class="proof">

*Proof.* A corridor would give $`2^{\,N+K+1}<3(N+K)`$ by Theorem <a href="#res:corridorbound" data-reference-type="ref" data-reference="res:corridorbound">12</a>, contradicting Proposition <a href="#res:exp" data-reference-type="ref" data-reference="res:exp">14</a> applied to $`x=N+K\ge2`$. ◻

</div>

Formalised as the [corridor exclusion at three halves](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L155).

Theorem <a href="#res:nocorridor" data-reference-type="ref" data-reference="res:nocorridor">15</a> excludes the coordinatewise clearing scheme at $`3/2`$, and nothing else: it does not bound the denominator of $`F(3/2)`$, it does not show that $`F(3/2)`$ is irrational, and it does not show that $`F(3/2)`$ is rational. It also does not cover a clearing scheme of a different shape, since the corridor fixes one divisibility pattern and one tail inequality.

<a id="sec:tail"></a>

# The cleared-tail recurrence and the size of the forcing term

Theorem <a href="#res:nocorridor" data-reference-type="ref" data-reference="res:nocorridor">15</a> says that one scheme fails. This section identifies the quantity responsible, as an exact recurrence.

Let $`r,s,B,F`$ be rationals with $`r\ne0`$ and let $`c:\mathbb{N}\to\mathbb{Q}`$ be arbitrary. Define the prefix and the cleared tail state by
``` math
P_N=\sum_{m=0}^{N-1}\frac{c(m+1)\,s^{\,m+1}}{r^{\,m+1}},
 \qquad
 U_N=B\,r^{N}\bigl(F-P_N\bigr).
\tag{$\ast$}\label{eq:tailstate}
```
Thus $`P_N`$ is the partial sum of $`\sum_{n\ge1}c(n)(s/r)^{n}`$ through level $`N`$, and $`U_N`$ is the tail of a putative value $`F`$ after that level, scaled by $`Br^{N}`$. These are the [rational-base prefix](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L168) and the [cleared tail state](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L181).

<div id="res:tailrec" class="theorem">

**Theorem 16** (cleared-tail recurrence). *Let $`r,s,B,F\in\mathbb{Q}`$ with $`r\ne0`$, let $`c:\mathbb{N}\to\mathbb{Q}`$, and let $`P_N`$ and $`U_N`$ be as in <a href="#eq:tailstate" data-reference-type="eqref" data-reference="eq:tailstate">[eq:tailstate]</a>. Then for every $`N`$,
``` math
U_{N+1}=r\,U_N-B\,c(N+1)\,s^{\,N+1}.
```*

</div>

<div class="proof">

*Proof.* An immediate computation. Expanding $`P_{N+1}=P_N+c(N+1)s^{N+1}/r^{N+1}`$ and $`r^{N+1}=r^{N}\cdot r`$ in the definition of $`U_{N+1}`$ and clearing the denominator $`r^{N+1}`$, which is nonzero, gives the identity. ◻

</div>

Formalised as the [cleared-tail recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L187).

The recurrence has a linear part $`rU_N`$ and a forcing term $`Bc(N+1)s^{N+1}`$, the inhomogeneous term the state receives at each step. The direct-clearing route studied here works only if the state remains in a bounded window, and the forcing term is what that window must absorb. Its size is what separates the two denominator regimes.

<div id="res:forcing" class="theorem">

**Theorem 17** (the forcing term). *Let $`s,B`$ be natural numbers and $`c:\mathbb{N}\to\mathbb{N}`$, and put $`G_N=B\,c(N+1)\,s^{\,N+1}`$.*

1.  *If $`s\ge2`$, $`B\ge1`$ and $`c(N+1)\ge1`$, then $`2^{\,N+1}\le G_N`$.*

2.  *If $`s=1`$, then $`G_N=B\,c(N+1)`$.*

</div>

<div class="proof">

*Proof.* Both parts are routine. For the first, $`2^{N+1}\le s^{N+1}=1\cdot s^{N+1}\le Bc(N+1)s^{N+1}`$, using $`B\,c(N+1)\ge1`$. The second part is the definition with $`s=1`$. ◻

</div>

Formalised as the [exponential lower bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L204) and the [integer-base collapse](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L218).

At $`s=1`$ the forcing term is $`Bc(N+1)`$, so it grows only as fast as the coefficient; for the divisor function that is $`O(N^{\varepsilon})`$ for every $`\varepsilon>0`$, and a bounded-state argument has room. At $`s\ge2`$ the same term is at least $`2^{N+1}`$ whenever the coefficient is nonzero.

<div id="ex:forcing" class="example">

**Example 18**. Take $`B=1`$, $`c=\tau`$ and $`N=9`$, so that the coefficient is $`\tau(10)=4`$. At $`s=1`$ the forcing term is $`4`$. At $`s=2`$ it is $`4\cdot2^{10}=4096`$, and part (1) of Theorem <a href="#res:forcing" data-reference-type="ref" data-reference="res:forcing">17</a> already guarantees at least $`2^{10}=1024`$ without knowing the coefficient at all.

</div>

This is an exact lower bound on one quantity, and it is all that is proved. It is not a proof that no bounded-state argument exists at $`s\ge2`$; the theorem that one particular scheme fails is Theorem <a href="#res:nocorridor" data-reference-type="ref" data-reference="res:nocorridor">15</a>, and the bound here records the size of the term that scheme would have to absorb.

<a id="sec:sevenhalves"></a>

# The height criterion at $`7/2`$

In 1994 Bundschuh and Väänänen proved an irrationality criterion for a family of rational bases cut out by a height condition \[bv1994, Theorem 2, p. 177; hypotheses pp. 175–176\]. We keep their notation: $`q`$ is the base, and $`\alpha`$ and $`\lambda`$ are the parameters of the criterion. In its special case $`\alpha=-1`$, the printed hypothesis is
``` math
\lambda<\left(\frac12+\frac1{\pi^2}\right)^{-1}.
```
At $`q=7/2`$ the Archimedean parameter is $`\lambda=\log 7/\log(7/2)`$. The criterion therefore applies once the following strict inequality is checked.

<div id="res:sevenhalves" class="theorem">

**Theorem 19** (the $`7/2`$ height condition).
*``` math
\frac{\log 7}{\log(7/2)}
 <
 \left(\frac12+\frac1{\pi^2}\right)^{-1}.
```*

</div>

Numerically the two sides are $`1.5533\ldots`$ and $`1.6630\ldots`$, so the condition holds with a margin of about $`0.11`$. The Lean proof factors the estimate through the explicit [height-region predicate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L44) and the [integer certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L32) $`2^{18}<7^7`$, the resulting [logarithmic ratio bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L48) $`\log2/\log7<7/18`$, the [$`\pi`$-bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L64) $`1/\pi^2<1/9`$, and the [strict margin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L73)
``` math
\frac{\log2}{\log7}<\frac12-\frac1{\pi^2}.
```
The [final height inequality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L83) then rewrites $`\log(7/2)=\log7-\log2`$ and closes the displayed condition.

This formalises the complete elementary parameter check at $`q=7/2`$; it does not formalise Bundschuh and Väänänen’s analytic irrationality theorem, whose proof occupies pp. 189–193 of the source. The conclusion that $`F(7/2)`$ is irrational is consequently cited from that theorem, not claimed as a Lean theorem here.

The criterion does not cover $`3/2`$, and the results of Sections <a href="#sec:corridor" data-reference-type="ref" data-reference="sec:corridor">4</a> and <a href="#sec:tail" data-reference-type="ref" data-reference="sec:tail">5</a> give no evidence either way about whether $`F(3/2)`$ is irrational.

<a id="the-81200-logarithmic-region"></a>

## The $`81/200`$ logarithmic region

Consider the rational-height region
``` math
\frac{\log b}{\log a}<\frac{81}{200}
 \qquad(a>b>0).
```
No bibliographic source for an analytic irrationality theorem at this cutoff is asserted here. The Lean module instead treats the displayed inequality as a definition and proves elementary memberships and exclusions. In particular,
``` math
\frac25
 <\frac{\log4}{\log31}
 <\frac{81}{200}
 <\frac{\log2}{\log3}.
```
The first two comparisons come respectively from $`31^2<4^5`$ and $`4^{200}<31^{81}`$; the last comes from $`3^{81}<2^{200}`$. The lower bound is the checked theorem [two-fifths lower bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L67). Consequently $`31/4`$, and every positive power $`(31/4)^r`$, lies in the enlarged region ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L45), [power family](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L62)). The same base lies strictly outside the earlier Bundschuh–Väänänen region ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L94)), so the $`81/200`$ inequality defines a strict set-theoretic enlargement of the earlier recorded logarithmic region. Membership alone supplies no irrationality theorem for $`31/4`$.

It still does not approach $`3/2`$. The exact comparison
``` math
3^{81}<2^{200}
 \quad\Longrightarrow\quad
 \frac{81}{200}<\frac{\log2}{\log3}
```
is Lean-checked, as is the conclusion that $`3/2`$ belongs to neither height region ([boundary](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L108), [exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L125)). Thus $`81/200`$ is the larger of the two explicitly defined cutoffs used below, while a cutoff that includes $`3/2`$ must be strictly larger than $`\log2/\log3\approx0.6309`$.

<a id="sec:pade"></a>

# Denominator exponents for a homogenised Padé construction

A second external route builds the linear forms of Section <a href="#sec:primitive" data-reference-type="ref" data-reference="sec:primitive">2</a> by Padé approximation. Such a construction produces its coefficients as sums of rational summands, and to obtain integer rows one multiplies through by a single common denominator. The bookkeeping obligation is then to check that no summand needs a larger denominator than the one proposed, which is a comparison between the exponents alone. This section does that comparison, and only that.

No source construction is named here for the exponent expressions below, and they are checked as displayed polynomial identities rather than derived. Giving them Padé-theoretic force would additionally require deriving the expressions from a stated homogenised coefficient formula, proving integrality of the coefficients after multiplication by the proposed common denominator, and establishing nonvanishing and decay of the associated remainder. None of those three is claimed here.

For a homogenised construction over integer parameters the proposed common denominator exponent is $`E_n=(3n^{2}-n)/2`$. Since only doubled exponents occur below, every statement lives over $`\mathbb{Z}`$ and no parity bookkeeping is needed; we write $`\widetilde{E}_n=2E_n=3n^{2}-n`$.

<div id="res:pade" class="proposition">

**Proposition 20** (summand bound and exact gap). *Let $`\widetilde{E}_n=3n^{2}-n`$ and put
``` math
\widetilde{P}(n,k)=2\bigl(k(n-k)+nk\bigr)+k(k-1),
```
``` math
\widetilde{Q}(n,m)=2(n^{2}-n)+j^{2}+2jm+j-m^{2}+3m,
 \qquad j=n-m-1 .
```
Then, for integers $`n,k,m`$:*

1.  *if $`0\le k\le n`$, then $`\widetilde{P}(n,k)\le\widetilde{E}_n`$, and the gap factors as $`\widetilde{E}_n-\widetilde{P}(n,k)=(n-k)(3n-k-1)`$;*

2.  *$`\widetilde{E}_n-\widetilde{Q}(n,m)=2\bigl(n+m(m-1)\bigr)`$ identically;*

3.  *if $`n\ge0`$ and $`m\ge1`$, then $`\widetilde{Q}(n,m)\le\widetilde{E}_n`$.*

</div>

Part (1) is the [summand exponent bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L30), part (2) the [exact gap identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L52), and part (3) the [maximal exponent bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L60). The gap in (2) is an identity in $`\mathbb{Z}[n,m]`$, so (3) follows from $`m(m-1)\ge0`$ and $`n\ge0`$; the hypothesis $`m\ge1`$ names the range in which the corresponding summand does not vanish, and it is not the sharpest hypothesis under which the inequality holds.

<div id="ex:pade" class="example">

**Example 21**. At $`n=2`$ the proposed doubled exponent is $`\widetilde{E}_2=10`$, and $`\widetilde{P}(2,k)`$ takes the values $`0,6,10`$ at $`k=0,1,2`$. The three gaps are $`10,4,0`$, matching the factorisation $`(2-k)(5-k)`$ of part (1); the summand at $`k=2`$ is the one that saturates the proposed denominator. For part (2), at $`m=1`$ we have $`j=0`$ and $`\widetilde{Q}(2,1)=6`$, with gap $`4=2\bigl(2+1\cdot0\bigr)`$.

</div>

These are routine inequalities between polynomials in the exponents. They establish that the proposed exponent $`\widetilde{E}_n`$ dominates the two displayed summand exponent expressions, and nothing further. Positivity of the remainder, its rate of decay, and the comparison of that rate against the denominator height are the analytic obligations, and none of them is treated here, so nothing in this section is an irrationality measure.

<a id="sec:open"></a>

# Complements and further questions

Problem #1049 remains open. Theorem <a href="#res:jetkernel" data-reference-type="ref" data-reference="res:jetkernel">8</a> suggests the following precise sufficient subproblem for one common-width additive architecture. It is not asserted to be necessary for every proof of irrationality.

<div id="prob:kernel" class="problem">

**Problem 22** (common-width simultaneous endpoint-jet construction). Exhibit an integer constant $`C\ge1`$ and, for every sufficiently large positive integer $`n`$, positive integers $`W_n,R_n,S_n,M_n`$ such that
``` math
n^2\le W_n,R_n,S_n\le Cn^2,
 \qquad 4R_n+2S_n\le M_n\le Cn^2,
```
together with polynomial pairs $`(U_{n,j},V_{n,j})\in\mathbb{Z}[X]^2`$ for $`0\le j<M_n`$, each of degree at most the common declared width $`W_n`$, whose specialised integer rows are primitive:
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

The jet equations make $`A_n,B_n`$ integers. A solution would prove irrationality: if $`F(3/2)=a/b`$ in lowest terms, every nonzero $`\rho_n`$ has absolute value at least $`1/b`$, contradicting the displayed bound for $`n>b`$. Theorem <a href="#res:jetkernel" data-reference-type="ref" data-reference="res:jetkernel">8</a> supplies only a nonzero signed relation with the four jet equations once the pairs and size inequality are present; it does not supply primitive input rows, a nonzero combined polynomial pair, or the nonvanishing and decay of $`\rho_n`$.

Integer rescaling and a common divisor of the two specialised evaluations are the two mechanisms excluded by Corollary <a href="#res:nomult" data-reference-type="ref" data-reference="res:nomult">7</a>. Polynomial factors before specialisation, cross-row or determinant-specific arithmetic, cyclotomic factors, other additive constructions, and entirely different architectures remain outside that corollary and are not decided either way.

The remaining linear-form programme therefore has two independent gates: first find a four-jet collision that does not collapse algebraically or analytically; only then ask whether its divisibility and decay beat its height. We state those gates separately below.

<a id="exact-kernel-escape"></a>

## Exact kernel escape

Fix, for each $`n`$, a declared width $`W_n`$ and a specified family
``` math
(U_{n,j},V_{n,j},\mathcal R_{n,j})_{j<M_n},
```
where $`U_{n,j},V_{n,j}\in\mathbb{Z}[X]`$ and $`\mathcal R_{n,j}`$ is the corresponding remainder function. Normalisation must be fixed before the jet map is formed. Call the family *polynomially primitive* when the common coefficient content of the pair in $`\mathbb{Z}[X]^2`$ is divided out before specialisation; as the Terminology paragraph records, that is a different operation from primitive normalisation of a specialised integer row, which is what Problem <a href="#prob:kernel" data-reference-type="ref" data-reference="prob:kernel">22</a> imposes. The specialised row content
``` math
g^{\mathrm{spec}}_{n,j}
 =\gcd\!\bigl(H_{W_n}(U_{n,j}),H_{W_n}(V_{n,j})\bigr)
```
and the content of a final additive combination are separate quantities; they are not silently divided out. If either is divided out later, both the height and the remainder below are measured after that same division. Under the unit endpoint hypotheses, $`g^{\mathrm{spec}}_{n,j}`$ is coprime to $`6`$, so such division does not manufacture or destroy the $`2`$- and $`3`$-primary jet vanishing.

For target depths $`R_n,S_n`$, let $`J_n(\lambda)`$ be the four-jet signature of the pair $`\sum_j\lambda_j(U_{n,j},V_{n,j})`$, and define
``` math
\mathcal C_n=
 \{\lambda\in\{-1,0,1\}^{M_n}\mathbin{\backslash}\{0\}:J_n(\lambda)=0\},
```
``` math
\begin{aligned}
 K_n^{\mathrm{poly}}
   &=\left\{\lambda\in\{-1,0,1\}^{M_n}:
       \sum_j\lambda_jU_{n,j}=0,\ \sum_j\lambda_jV_{n,j}=0\right\},\\
 K_n^{\mathrm{rem}}
   &=\left\{\lambda\in\{-1,0,1\}^{M_n}:
       \sum_j\lambda_j\mathcal R_{n,j}(3/2)=0\right\}.
\end{aligned}
```
The second nullspace concerns the value at $`3/2`$; an identically zero remainder function is a still stronger collapse and is automatically bad.

The exact pigeonhole condition is
``` math
2^{M_n}>3^{2R_n}2^{2S_n},
 \qquad\text{equivalently}\qquad
 M_n>2R_n\log_2 3+2S_n.
\tag{8.1}\label{eq:exact-jet-threshold}
```
Thus the least admissible integer rank is
``` math
M_{\min}(R,S)=
 \left\lfloor2R\log_2 3+2S\right\rfloor+1.
```
The checked condition $`M\ge4R+2S`$ for $`R>0`$ is a convenient sufficient corollary, not the exact threshold. Moreover, with $`N=2^{M_n}`$ and $`Q=3^{2R_n}2^{2S_n}`$, convexity of the fibre sizes gives at least
``` math
\frac12\left(\frac{N^2}{Q}-N\right)
\tag{8.2}\label{eq:collision-count}
```
unordered equal-signature selector pairs. A normality estimate can therefore win by showing that fewer than this many collision pairs land in the two bad nullspaces.

<div id="prob:escape" class="problem">

**Problem 23** (four-jet kernel escape). For one literal polynomially primitive family satisfying <a href="#eq:exact-jet-threshold" data-reference-type="eqref" data-reference="eq:exact-jet-threshold">[eq:exact-jet-threshold]</a>, prove, preferably by comparing the lower bound <a href="#eq:collision-count" data-reference-type="eqref" data-reference="eq:collision-count">[eq:collision-count]</a> with the bad-pair multiplicities, that
``` math
\mathcal C_n\mathbin{\backslash}
 \bigl(K_n^{\mathrm{poly}}\cup K_n^{\mathrm{rem}}\bigr)
 \ne\varnothing
```
for all sufficiently large $`n`$.

</div>

Theorem <a href="#res:jetkernel" data-reference-type="ref" data-reference="res:jetkernel">8</a> supplies only $`\mathcal C_n\ne\varnothing`$. It gives a nonzero selector difference, but it gives neither polynomial-pair nonvanishing nor remainder nonvanishing. Problem <a href="#prob:escape" data-reference-type="ref" data-reference="prob:escape">23</a> is finite algebra and normality; it makes no asymptotic product-formula claim. It is the first of the two gates in Problem <a href="#prob:kernel" data-reference-type="ref" data-reference="prob:kernel">22</a>: it asks for the two nonvanishing conclusions, and not for the analytic condition stated there.

<a id="the-first-falsifiable-families"></a>

## The first falsifiable families

An exploratory calculation suggests a contiguous $`a_0`$-shift determinant at $`r_n=13n+2`$, after apparent failure of lower ranks $`r\le13n+1`$. These computations are not Lean theorems. More importantly, no literal definition of the matrix $`A_{n,r}`$ is given here, so writing merely “$`\det A_{n,13n+2}\ne0`$” would not yet be a public mathematical question.

<div class="problem">

**Problem 24** (the first saturated determinant). Give the entrywise formula for the contiguous $`a_0`$-shift matrix $`A_{n,r}`$, the exact relation $`M_n=M(n,r)`$ between its size and the number of coefficient pairs, and the declared width $`W_n`$. Then determine whether
``` math
\det A_{n,13n+2}\ne0
```
for every sufficiently large $`n`$. At the first computable scales, report the rank, determinant, coefficient-pair contents, specialised row contents, four endpoint jets, and the first nonzero remainder coefficient. A negative answer must identify a systematic rank relation or the first exact failing $`n`$.

</div>

This formulation makes the matrix definition part of the problem statement rather than relying on undeclared notation.

<div class="problem">

**Problem 25** (minimal non-$`a_0`$ deformation). If the saturated contiguous family collapses, enlarge it by exactly one $`a_1`$-shift while retaining the same source cone and widths. Does this one-direction extension increase the polynomial-pair rank and produce a collision outside $`K_n^{\mathrm{poly}}\cup K_n^{\mathrm{rem}}`$? If every such one-shift extension collapses, prove that class-wide obstruction before adding a second new direction.

</div>

This is the smallest specified deformation beyond the contiguous family; it replaces the unbounded request for a “genuinely independent deformation.”

<a id="asymptotic-adequacy-after-kernel-escape"></a>

## Asymptotic adequacy after kernel escape

Suppose a good collision has been found. Let $`D_n=3^{R_n}2^{S_n}`$ be the certified local divisor (or replace it by the exact determinant-specific divisor), let $`H_n`$ be the coefficient or exterior height after precisely the normalisation just declared, and let $`L_n\ne0`$ be the resulting analytic form or exterior remainder.

<div class="problem">

**Problem 26** (negative normalised product-formula margin). Prove the explicit estimate
``` math
\limsup_{n\to\infty}
 \frac{\log H_n+\log|L_n|-R_n\log3-S_n\log2}{n^2}<0.
\tag{8.3}\label{eq:negative-margin}
```
Every denominator, row content and final-combination content must already be included in $`H_n`$ and $`L_n`$.

</div>

Nonvanishing alone does not address <a href="#eq:negative-margin" data-reference-type="eqref" data-reference="eq:negative-margin">[eq:negative-margin]</a>. Conversely, excellent formal decay is irrelevant if every jet collision lies in a bad nullspace. The exploratory adjacent-exterior calculation leaves a positive normalised exponent of about $`110.850\,n^2`$; this is not a checked theorem. Any proposed improvement must remove this explicit deficit rather than merely exhibit some extra divisibility.

<a id="one-exact-alternative-criterion-test"></a>

## One exact alternative-criterion test

A separate possible route is Mahler’s method. Its first applicability test is the following.

<div class="problem">

**Problem 27** (finite Mahler-system test). For
``` math
\mathcal L(z)=\sum_{n\ge1}\frac{z^n}{1-z^n},
```
determine whether $`\mathcal L`$ belongs to a finite-dimensional $`\mathbb{Q}(z)`$-vector space stable under both $`z\mapsto z^2`$ and $`z\mapsto z^3`$, with a regular functional system at $`z=2/3`$ to which a stated special-value theorem applies. Supply the literal system and verify its hypotheses, or prove that no such finite-dimensional regular system exists.

</div>

This question has a concrete positive and negative outcome. It does not infer a special-value theorem from the already known fact that $`\mathcal L`$ is not a rational function.

<a id="the-quantitative-height-frontier"></a>

## The quantitative height frontier

The module `HermitePadeNoGo` defines an explicit rectangular two-parameter exponent model. Writing $`\sigma=1+\rho+u`$, its denominator-cleared gap has the exact expansion
``` math
-\pi^2\rho^2-\pi^2\rho u-2\pi^2\rho-2\rho^2-10\rho u
 -4\rho-6u^2-8u.
```
Thus for $`\rho\ge0`$ and $`\sigma\ge1+\rho`$ the cleared gap is nonpositive, and it vanishes exactly when $`\rho=0`$ and $`\sigma=1`$ ([exact expansion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L43), [nonpositivity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L53), [equality case](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L70)). Equivalently, within that model the displayed threshold never exceeds the classical one-function margin, with equality only at the classical endpoint ([bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L99), [equality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L121)). This is an algebraic theorem about the four defined exponent expressions and only that explicit rectangular model. It does not construct polynomials, remainders, integrality, a determinant, or asymptotics, and it is not a method-universal no-go theorem. The separate $`81/200`$ cutoff of the preceding section satisfies
``` math
\frac{81}{200}<\frac{\log2}{\log3}.
```
Thus “improve the height theorem” has a precise numerical target.

<div class="problem">

**Problem 28** (optimal admissible height threshold). Specify a concrete class $`\mathcal A`$ of primitive, noncollapsed constructions, excluding scalar row rescaling, proportional permutation-orbit forms, pure row-content gain, and constructions governed by the rectangular exponent model above. For that class define
``` math
\theta_*=\sup_{\alpha\in\mathcal A}
   \frac{C_0(\alpha)}{C_1(\alpha)}.
```
Prove one of the following: $`\theta_*>81/200`$ by an explicit construction; an exact value for $`\theta_*`$; a converse $`\theta_*<\log2/\log3`$; or a class theorem showing that every member reduces to one of the checked scalar or rectangular no-go mechanisms.

</div>

Reaching $`3/2`$ requires a threshold strictly beyond $`\log2/\log3\approx0.6309`$, not merely an improvement over $`81/200=0.405`$. The unrestricted question of which rational bases give irrational values remains open and is not reduced to any one of these problems.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The [pinned formal-source revision](https://github.com/wcook04/plectis-lean-erdos249-257/tree/76b5b0a7ed5da7ebf3b9ed3bfd2fb480b6c38ee0) contains the Lean sources, the fixed toolchain, and the library manifest used in the verification. This manuscript provides navigation rather than proof authority.

<a id="declaration-of-generative-ai-use."></a>

#### Declaration of generative AI use.

Large-language-model agents were used throughout development to draft and revise prose, formal proofs, and software. The author set the objectives and acceptance criteria, selected and reviewed the claims, and approved the published version. The author assumes responsibility for the accuracy, interpretation, and presentation of the work. Generative systems are production tools; they are not authors and supply no independent authority. Lean checks each proof term against the fixed library version, and the sources linked here contain no proof placeholders and no project-defined axioms; Lean does not authorise the exposition, the citation choices, or the interpretation, for which the author remains responsible.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

The problem numbering and status follow the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\].

<a id="app:index"></a>

# Guide to the formal sources

Each linked phrase opens its Lean declaration at the pinned source revision 76b5b0a7ed5d. The declarations of this note live in five modules: `RationalBaseLambert`, `RationalPadeArithmetic`, `ZudilinConeArithmetic`, `ZudilinHeightRegion`, and `HermitePadeNoGo`. The first contains the corridor, cleared-tail recurrence, and elementary $`7/2`$ certificate; the remaining four separate the Padé exponent arithmetic, endpoint arithmetic, logarithmic comparisons, and rectangular exponent model. The link coordinates are validated against that pinned revision, so they remain correct as later work moves lines in the working tree.

<div class="thebibliography">

99

P. Erdős, [*On arithmetical properties of Lambert series*](https://users.renyi.hu/~p_erdos/1948-04.pdf), J. Indian Math. Soc. (N.S.) **12** (1948), 63–66. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). P. B. Borwein, *On the irrationality of $`\sum1/(q^{n}+r)`$*, J. Number Theory **37** (1991), no. 3, 253–259, doi:[10.1016/S0022-314X(05)80041-1](https://doi.org/10.1016/S0022-314X(05)80041-1). P. Bundschuh and K. Väänänen, [*Arithmetical investigations of a certain infinite product*](https://numdam.org/item/CM_1994__91_2_175_0.pdf), Compositio Math. **91** (1994), no. 2, 175–199. W. Zudilin, [*Heine’s basic transform and a permutation group for $`q`$-harmonic series*](https://www.impan.pl/shop/en/publication/transaction/download/product/82435), Acta Arith. **111** (2004), no. 2, 153–164, doi:[10.4064/aa111-2-4](https://doi.org/10.4064/aa111-2-4). G. Rhin and C. Viola, *On a permutation group related to $`\zeta(2)`$*, Acta Arith. **77** (1996), no. 1, 23–56, doi:[10.4064/aa-77-1-23-56](https://doi.org/10.4064/aa-77-1-23-56). W. Van Assche, [*Little $`q`$-Legendre polynomials and irrationality of certain Lambert series*](https://arxiv.org/abs/math/0101187), Ramanujan J. **5** (2001), no. 3, 295–310, doi:[10.1023/A:1012930828917](https://doi.org/10.1023/A:1012930828917). J. Vandehey, [*On an incomplete argument of Erdős on the irrationality of Lambert series*](https://arxiv.org/abs/1206.0340), Integers **13** (2013), Paper A58. I. Rivin, [*Zero Coefficients of Rational Power Series and Rational Lambert Series*](https://arxiv.org/abs/2604.25151), arXiv:2604.25151v1, 2026. Theorem 1.1 is on p. 2 and proved on pp. 6–7; the periodic-coefficient Corollary 6.4 is on p. 9. V. Kovač and T. Tao, [*On several irrationality problems for Ahmes series*](https://arxiv.org/abs/2406.17593), Acta Math. Hungar. **175** (2025), 572–608; arXiv:2406.17593, 2024. T. F. Bloom, [*Erdős Problem \#1049*](https://www.erdosproblems.com/1049), `erdosproblems.com/1049`, accessed 28 July 2026 (page displays “last edited 28 September 2025”). The current record labels the problem open, cites <span class="upright">\[Er88c, p. 102\]</span> and <span class="upright">\[Er48\]</span>, and explicitly describes its status as the website owner’s present assessment rather than a literature-completeness guarantee. The Formal Conjectures Authors, [*FormalConjectures.ErdosProblems.`1049`*](https://github.com/google-deepmind/formal-conjectures/blob/f776d2f2039351b00737ffcafb9d7d7666e1d9af/FormalConjectures/ErdosProblems/1049.lean), Lean source at commit `f776d2f`, 2026, accessed 28 July 2026. The irrationality declarations are unproved; the Lambert-series identity is proved.

</div>
