<a id="erdos249-totient-reasoning-surface"></a>

# The Binary Totient Series

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

This paper gives a claim-bounded map of the current formal attack on Erdős Problem 249, which asks whether $`S=\sum_{n\ge1}\varphi(n)/2^n`$ is irrational. The problem remains open. The unconditional headline results are an explicit rational basis for the full dyadic totient kernel, exact rank $`2^e+1`$ through every level $`e\ge1`$, a denominator exclusion through approximately $`7.96\times10^{34}`$, and finite lcm-diagonal certificates for every $`t\le82`$. The full kernel is therefore infinite-dimensional. The paper also records exact equivalences between irrationality and several cofinal certificate or tail-nonintegrality supplies. Those equivalences re-express rather than solve the problem: no certificate at $`t=83`$, unbounded certificate family, or irrationality proof is obtained. The contribution is the audited organization of checked results, coordinate-specific obstructions, and open implications—not a solution, an exhaustive reproduction of every repository theorem, or a priority claim for every formalisation.

<a id="how-to-read-this-document"></a>

# How to read this document

This is a reasoning surface, not an exhaustive corpus export or a literature survey. It is designed to expose the principal premises, obstructions, and open interfaces before work begins. The machine-readable corpus remains the current inventory when later theorem waves outrun this exposition. Three conventions carry the paper’s claim boundary.

*Evidence bands.* Every statement is tagged. <span class="sans-serif">\[Lean\]</span> means a proof term was checked by the pinned Lean kernel. <span class="sans-serif">\[Cert\]</span> means an exact finite computation, with no floating-point decision anywhere in it. <span class="sans-serif">\[Math\]</span> means proved in ordinary mathematics in the sources but not formalised. <span class="sans-serif">\[Cited\]</span> means established in the published literature. <span class="sans-serif">\[Open\]</span> means not proved. These are never blurred, and a statement carrying one band is never described in language belonging to another.

*Scale.* Every parameter-indexed statement is tagged <span class="sans-serif">scale:fixed</span> (proved at specific listed values), <span class="sans-serif">scale:bounded</span> (proved below an explicit bound), <span class="sans-serif">scale:cofinal</span> (proved for arbitrarily large parameters), or <span class="sans-serif">scale:uniform</span> (proved for all parameters). The corpus contains theorems at all four scales; the unresolved endpoint depends on a particular cofinal certificate producer that is not among them. Sorting by scale keeps that distinction visible.

*Coordinates.* Every statement records the representation it is expressed in. An obstruction is a fact about a coordinate, not about the object, and a wall measured in one representation may simply not exist in another; the atlas section gives the transport maps, so any obstruction recorded here can be re-measured elsewhere.

*Frontier terminology.* The catalogue uses *producer* for an unproved hypothesis that would supply a missing step, *consumer* for a proved implication that uses such a hypothesis, *converter* for an exact identity or reduction, and *socket* for the precise place where the missing hypothesis enters. These are local navigation terms, not additional mathematical objects or evidence classes.

Erdős Problem 249 is open. No section of this document claims otherwise, and a reduction of the problem to another statement is recorded as a reduction, never as progress toward a solution.

<a id="the-problem-and-what-is-actually-known"></a>

# The problem, and what is actually known

Let $`\varphi`$ be Euler’s totient function and put
``` math
S \;:=\; \sum_{n \ge 1} \frac{\varphi(n)}{2^{n}}
  \;=\; \tfrac12 + \tfrac14 + \tfrac{2}{8} + \tfrac{2}{16} + \tfrac{4}{32} + \cdots
  \;=\; 1.3676308019850223\ldots
```
The series converges absolutely because $`\varphi(n) \le n`$. Erdős Problem \#249 asks whether $`S`$ is irrational. *It is open.* Nothing in this document decides it, no route recorded here is a proof, and no result here should be read as an approach that is close to working. What this document does is different in kind: it assembles every recorded failure, obstruction, countermodel and dead route the programme has produced against \#249, and classifies each one by the exact class of argument it eliminates. The claim being made is that those failures are not independent — they are repeated measurements of a single obstruction, and that obstruction has a shape which can be stated.

<div class="rem">

*Remark 1* (Literature coordinates). The nearby literature serves three distinct roles. Kovač–Tao’s [Ahmes-series paper](https://arxiv.org/abs/2406.17593v4) maps a broader Lambert-subseries landscape, but does not treat the coefficient series $`S`$. Merca’s [Lambert-series factorization theorem](https://doi.org/10.1007/s11139-016-9856-3) and the [Merca–Schmidt](https://doi.org/10.55016/ojs/cdm.v14i1.62425) factor-pair formalism provide transform background for the Möbius–Mersenne coordinate. Finally, [Balasubramanian–Giri–Srivastav, Theorem 2.2](https://arxiv.org/abs/1511.02221) gives uniform shifted-correlation estimates for the relevant divisor-convolution class. It does not supply the dyadic residue small-ball or phase anti-concentration required by $`\mathrm{Sep}`$. These are contextual or method sources, not proofs of the open certificate supply. <span class="sans-serif">\[Cited\]</span>

</div>

The open question has a sharp equivalent inside the corpus, and it is the statement everything below is measured against. Write $`2^{N} S = \Phi_N + R_N`$ with $`\Phi_N := \sum_{n \le N} \varphi(n) 2^{N-n} \in \mathbb{N}`$ and $`R_N := \sum_{j \ge 0} \varphi(N+1+j)/2^{j+1} \in [0,\infty)`$ (, ). If $`S \in \mathbb{Q}`$ then, applying Euler’s theorem to the odd part of its denominator, there are $`h > 0`$ and $`N_0`$ with $`R_{N+h} - R_N \in \mathbb{Z}`$ for every $`N \ge N_0`$ (, explicit witnesses $`h = \varphi(\mathrm{oddPart}(r.\mathrm{den}))`$, $`N_0 = v_2(r.\mathrm{den})`$).

So it suffices to refute integrality cofinally on every period ray. The finite device that refutes it is a residue certificate:
``` math
\mathrm{windowDiscrepancy}(h,N,L)
  \;:=\; \sum_{j<L}\bigl(\varphi(N{+}h{+}1{+}j) - \varphi(N{+}1{+}j)\bigr)\,2^{\,L-1-j} \in \mathbb{Z},
```
the depth-$`L`$ truncation of $`2^{L}(R_{N+h} - R_N)`$, and
``` math
\mathrm{certifiedKill}(h,N,L)
  \;:\Longleftrightarrow\;
  (N{+}h{+}L{+}2) \;<\; \mathrm{windowDiscrepancy}(h,N,L) \bmod 2^{L}
  \;<\; 2^{L} - (N{+}h{+}L{+}2),
```
a decidable condition (, ).

The radius $`N{+}h{+}L{+}2`$ is exactly the crude tail bound coming from $`\varphi(m) \le m`$, so a certificate is sound: it forces $`R_{N+h} - R_N \notin \mathbb{Z}`$, and in fact certificates are *complete* for non-integrality (). The entire \#249 side of the programme therefore reduces to one obligation.

<div id="defn:sep" class="defn">

**Definition 2** (The supply obligation $`\mathrm{Sep}`$ — the exact open target).
``` math
\mathrm{Sep}
  \;:\Longleftrightarrow\;
  \forall h \ge 1\ \forall N_0\ \exists N \ge N_0\ \exists L,\;
  \mathrm{certifiedKill}(h,N,L).
```
$`\mathrm{Sep} \Rightarrow \mathrm{Irrational}(S)`$ (). `coord:binary-digit` <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span>

</div>

Two features of $`\mathrm{Sep}`$ govern everything that follows. First, the quantifier shape is $`\forall\forall\exists\exists`$: the corpus can and does verify individual instances, but an instance is not the obligation. Second, depth cannot stay bounded: from $`\mathrm{certifiedKill}(h,N,L)`$ one gets $`2(N{+}h{+}L{+}2) < 2^{L}`$ immediately (, <span class="sans-serif">\[Lean\]</span>), so $`L \gtrsim \log_2(N{+}h)`$. A certificate is a demand that a weighted accumulation over a window of length $`\approx \log_2 N`$ lands near the centre of its dyadic arc, at full arithmetic resolution.

<a id="the-unconditional-record"></a>

## The unconditional record

The following hold with no irrationality hypothesis. They are the results a specialist should know before reading further; each is stated at the scale at which it is actually proved.

<div id="thm:denom" class="thm">

**Theorem 3** (Denominator exclusion — the headline unconditional fact). *If $`S \in \mathbb{Q}`$ then its reduced denominator exceeds $`Q_0 := 79\,639\,646\,646\,701\,375\,323\,355\,774\,875\,831\,053 \approx 7.96 \times 10^{34}`$. Equivalently, $`S \ne p`$ for every $`p \in \mathbb{Q}`$ with $`p.\mathrm{den} \le Q_0`$. The bound is sharp for the method: $`q = Q_0 + 1`$ is the exact first failing denominator, exhibited as the mediant of two explicit unimodular Farey neighbours. `coord:farey` <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span>*

</div>

This is obtained from a classical Stern–Brocot gap lemma () applied at window $`K = 240`$, the last rung of the ladder $`4838 \to 2^{22} \to 2.49\times10^{17} \to Q_0`$. It is logically independent of $`\mathrm{Sep}`$: it uses no certificate and no period apparatus. Its own open continuation is whether $`\sup_K (b+d)(K) = \infty`$; that would close \#249 through this theorem’s consumer. <span class="sans-serif">\[Open\]</span>

<div id="prop:deposits" class="prop">

**Proposition 4** (Finite certificate deposits). *$`\mathrm{certifiedKill}`$ has been verified at: the $`28`$ diagonal instances of the LCM pincer through $`t = 64`$ (, endpoint ); all shifts $`h \in [1,16]`$ simultaneously at $`(N,L) = (14,9)`$, by `decide` (); and eight further period deposits at $`N = 300`$. Every deposit fires within a small additive constant of the minimum depth permitted by $`\mathrm{certifiedKill\_depth\_floor}`$. Note the quantifier order: this deposit proves $`\exists N \exists L\, \forall h \le 16`$, whereas $`\mathrm{Sep}`$ needs $`\forall h\, \forall N_0\, \exists N \exists L`$. `coord:binary-digit` <span class="sans-serif">scale:fixed</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="prop:sign" class="prop">

**Proposition 5** (Cofinal positivity, and why it is exactly half a certificate). *The true actual-LCM tail difference is strictly positive for every $`a \ge 8`$, with no irrationality hypothesis (, ). In the same coordinate, integrality of the orbit forces the residue to the *top edge*, exactly $`2^{K} - e`$ (). Positivity does not exclude the top edge. So the strongest cofinal fact the corpus owns about the actual object supplies one of the two inequalities a certificate needs and provably cannot supply the other. `coord:actual-lcm` <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="prop:rank" class="prop">

**Proposition 6** (Rationality forces unbounded carry rank). *If $`S`$ is rational then, for every $`e`$, the dyadic carry-kernel family at level $`e`$ has $`\mathbb{Q}`$-rank at least $`2^{e}-1`$ (). The scale side is complete and uniform in $`e`$: the canonical family of $`2^{e}+1`$ dyadic totient-kernel channels is linearly independent over $`\mathbb{Q}`$ at every depth, via CRT plus Dirichlet (), so the full family spans an infinite-dimensional space (). `coord:carry-rank` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="prop:period-not-rank" class="prop">

**Proposition 7** (What rationality actually buys, and what it does not). *Rationality gives uniform eventual periodicity of the carry’s dyadic sections modulo $`v`$; that periodicity provably does *not* promote to any $`\mathbb{Q}`$-rank bound on the carry family (). `coord:carry-rank` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="prop:iffs" class="prop">

**Proposition 8** (Exact reformulations that do not move the truth value). *Several re-encodings are proved *equivalent* to $`\mathrm{Irrational}(S)`$, not merely sufficient for it: the period-multiple kill supply (), the base certificate supply and its lcm-diagonal normal form (; ), the directed-certificate supply and its LCM specialisation (), and the window-separated-pairs predicate (). `coord:binary-digit` <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="prop:parity" class="prop">

**Proposition 9** (A rational sequence indistinguishable from $`\varphi`$ by every coarse invariant). *There is $`c : \mathbb{N}\to \mathbb{N}`$ with $`c(n) \le 6`$ and $`c(n) \le n`$ for all $`n`$, $`c(n) \equiv \varphi(n) \pmod 2`$ for *every* $`n`$, and $`c`$ not eventually periodic — indeed for every $`N, G, K`$ there are $`K`$ explicit carry pulses beyond $`N`$, pairwise separated by more than $`G`$ — and yet $`\sum_n c(n)/2^{n} = 3/2 \in \mathbb{Q}`$ (; sum at `:359`, aperiodicity at `:487`, parity match at `:194`; `#print axioms` clean). `coord:coefficient-word` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span>*

</div>

Propositions <a href="#prop:sign" data-reference-type="ref" data-reference="prop:sign">5</a>–<a href="#prop:parity" data-reference-type="ref" data-reference="prop:parity">9</a> are the four facts a reader should carry into the next section: the corpus’s best cofinal information is half a certificate, its best rank information runs the wrong way, its reformulations are equivalences rather than reductions, and every purely qualitative property of the coefficient word is satisfied by a rational countermodel.

<a id="sec:wall"></a>

# The wall

This programme has produced many exact reformulations of \#249 and no proof. That is the honest summary, and the rest of this section is an argument that it is also the wrong way to read the record. The reformulations do not fail independently. They fail in a small number of recurring ways, and when each failure is stated as a claim about *which class of argument it eliminates* rather than as a report that something did not work, the classes fit together into one obstruction with a describable shape. A hundred reformulations that all die are not a hundred failures; they are a hundred measurements of one wall, taken from different angles. The measurements are below.

The thesis, in one sentence: *every barrier in the record is a bound, and the quantity a certificate measures is invariant under exactly the bounds that make an argument finite.*

<a id="the-plane-the-barriers-live-on"></a>

## The plane the barriers live on

Fix two axes for a hypothetical proof of $`\mathrm{Sep}`$ (Definition <a href="#defn:sep" data-reference-type="ref" data-reference="defn:sep">2</a>): the *range* of indices at which it consults $`\varphi`$, and the *resolution* at which it consults them. Two derived axes matter as well: the size of the proof’s internal bookkeeping (carry state, $`\mathbb{Q}`$-rank, shift-polynomial degree), and whether the target is asserted *pointwise* at a chosen index or as an *average* over a block.

- The quadrant \[full resolution $`\times`$ bounded range\] is closed by Theorem <a href="#thm:gamma" data-reference-type="ref" data-reference="thm:gamma">13</a> (B1): $`\varphi`$ may be pinned exactly on $`[1,B]`$ and the series can still be rational.

- The complementary quadrant \[coarse resolution $`\times`$ unbounded range\] is closed by Proposition <a href="#prop:parity" data-reference-type="ref" data-reference="prop:parity">9</a> (B7): $`\varphi`$’s parity may be pinned at *every* index, together with boundedness, $`c(n) \le n`$, and arbitrarily strong aperiodicity, and the series can still be $`3/2`$.

- The remaining quadrant is closed *whenever the proof compresses*: B5 (no bounded carry state, no fixed-precision signature) and B6 (four independent finite truncations of the totient kernel, all with trivial kernel).

- B4 closes the one construction that tried to reach the good quadrant by *prescribing* values: residue engineering pays for amplitude in position, and position enters the certificate radius.

- B2 closes the escape of retargeting; B3 records that no bounded result in the corpus has ever promoted.

The corpus’s own results partition along these axes perfectly, which is the first evidence that the axes are the right ones. Every unconditional *finite* deposit (Proposition <a href="#prop:deposits" data-reference-type="ref" data-reference="prop:deposits">4</a>, the $`K=240`$ Farey rung of Theorem <a href="#thm:denom" data-reference-type="ref" data-reference="thm:denom">3</a>, the actual-LCM orbits at $`a = 4`$ and $`a = 6`$) sits at full resolution and bounded range, so B1 says extending them is evidence forever and proof never. Every unconditional *cofinal* theorem (letterwise positivity for all $`a \ge 8`$, the tail bounds from $`\varphi(m) \le m`$, unbounded Mersenne-shadow denominator growth) sits at coarse resolution and unbounded range, and Proposition <a href="#prop:sign" data-reference-type="ref" data-reference="prop:sign">5</a> proves in the corpus’s own coordinate that this is exactly half a certificate.

<a id="b1-the-finite-inspection-barrier-as-a-theorem"></a>

## B1: the finite-inspection barrier, as a theorem

B1 is the one barrier that is a genuine no-go theorem about proof method, so it is stated and proved as one. The generic vocabulary is needed first. For $`c : \mathbb{N}\to \mathbb{N}`$ with $`c(n) \le n`$, write $`T_c := \sum_{n \ge 1} c(n)/2^{n}`$, $`R^{c}_{N} := \sum_{j \ge 0} c(N{+}1{+}j)/2^{\,j+1}`$, $`A_c(h,N,L) := \sum_{j<L}(c(N{+}h{+}1{+}j) - c(N{+}1{+}j))2^{\,L-1-j}`$, and let $`\mathrm{Kill}_c(h,N,L)`$ and $`\mathrm{Sep}_c`$ be $`\mathrm{certifiedKill}`$ and $`\mathrm{Sep}`$ with $`A_c`$ in place of $`\mathrm{windowDiscrepancy}`$. For $`c = \varphi`$ these are the objects of Definition <a href="#defn:sep" data-reference-type="ref" data-reference="defn:sep">2</a>.

<div id="lem:gsound" class="lem">

**Lemma 10** (Generic soundness). *$`\mathrm{Kill}_c(h,N,L) \Rightarrow R^{c}_{N+h} - R^{c}_{N} \notin \mathbb{Z}`$. `coord:binary-digit` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Math\]</span>*

</div>

<div class="proof">

*Proof.* From $`c(n) \le n`$ one gets $`\lvert 2^{L}(R^{c}_{N+h} - R^{c}_{N}) - A_c(h,N,L)\rvert < N{+}h{+}L{+}2`$; this is the crude tail estimate, formalised for $`\varphi`$ at and used there to prove . If $`R^{c}_{N+h} - R^{c}_{N} = k \in \mathbb{Z}`$ then $`2^{L}k \equiv 0 \pmod{2^{L}}`$ and $`A_c`$ lies within $`N{+}h{+}L{+}2`$ of $`2^{L}k`$, so $`A_c \bmod 2^{L}`$ lies within $`N{+}h{+}L{+}2`$ of $`0`$ or of $`2^{L}`$, contradicting $`\mathrm{Kill}_c`$. ◻

</div>

<div id="lem:gperiod" class="lem">

**Lemma 11** (Generic tail-period law). *If $`T_c = p/(2^{e}m)`$ with $`m`$ positive and odd, and if $`h\ge1`$ satisfies $`m\mid 2^h-1`$, then $`R^{c}_{N+h} - R^{c}_{N} \in \mathbb{Z}`$ for every $`N \ge e`$. `coord:binary-digit` <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Math\]</span>*

</div>

<div class="proof">

*Proof.* $`R^{c}_{N} = 2^{N}T_c - \Phi^{c}_{N}`$ with $`\Phi^{c}_{N} \in \mathbb{Z}`$, so $`R^{c}_{N+h} - R^{c}_{N} = 2^{N}(2^{h}-1)T_c - (\Phi^{c}_{N+h} - \Phi^{c}_{N})`$, and $`2^{N}(2^{h}-1)p/(2^{e}m) \in \mathbb{Z}`$ because $`2^{e} \mid 2^{N}`$ and $`m \mid 2^{h}-1`$. ◻

</div>

<div class="rem">

*Remark 12*. Lemmas <a href="#lem:gsound" data-reference-type="ref" data-reference="lem:gsound">10</a> and <a href="#lem:gperiod" data-reference-type="ref" data-reference="lem:gperiod">11</a> are elementary and are stated here in ordinary mathematics. Their $`\varphi`$-instances are Lean theorems (, ), and the generic tail-period direction exists on disk inside ; a generic *named* theorem of the form of Lemma <a href="#lem:gperiod" data-reference-type="ref" data-reference="lem:gperiod">11</a> does not exist in either tree. The composition below is mechanical but unformalised, and is flagged <span class="sans-serif">\[Math\]</span> throughout for that reason.

</div>

<div id="thm:gamma" class="thm">

**Theorem 13** (B1, the $`\gamma`$-splice: finite inspection cannot certify the supply). *Let $`B \ge 1`$ and let $`P > B`$. Define $`\gamma : \mathbb{N}\to \mathbb{N}`$ by
``` math
\gamma(n) := \varphi(n) \ \ (n \le B), \qquad
  \gamma(n) := \begin{cases} n-1, & P \mid n \\ n, & P \nmid n \end{cases}
  \ \ (n > B).
```
Then:*

1.  *$`\gamma(n) \le n`$ for all $`n`$, so $`\gamma`$ lies in the same coefficient class as $`\varphi`$;*

2.  *$`\gamma(n) = \varphi(n)`$ for every $`n \le B`$, and consequently $`A_\gamma(h,N,L) = A_\varphi(h,N,L)`$ for every $`(h,N,L)`$ with $`N + h + L \le B`$;*

3.  *$`T_\gamma = D - 1/(2^{P}-1) \in \mathbb{Q}`$, where $`D = 2 - \sum_{n \le B}(n - \varphi(n))/2^{n}`$, and the odd part of the reduced denominator of $`T_\gamma`$ is *exactly* $`2^{P}-1`$;*

4.  *$`\mathrm{Sep}_\gamma`$ is false — indeed it fails already at $`h = P`$.*

*Hence for every $`B`$ there is a coefficient sequence in the same class, agreeing with $`\varphi`$ on all of $`[1,B]`$, whose supply obligation is false. `coord:binary-digit` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Math\]</span>*

</div>

<div class="proof">

*Proof.* (i) is immediate; (ii) holds because $`A_\varphi(h,N,L)`$ reads $`\varphi`$ only at indices $`\le N{+}h{+}L`$. For (iii), since $`P > B`$ every multiple of $`P`$ exceeds $`B`$, so
``` math
T_\gamma
  = \sum_{n\ge1}\frac{n}{2^{n}} - \sum_{n \le B}\frac{n - \varphi(n)}{2^{n}}
    - \sum_{k \ge 1} 2^{-kP}
  = 2 - \sum_{n \le B}\frac{n-\varphi(n)}{2^{n}} - \frac{1}{2^{P}-1}.
```
Write $`D = A/2^{B}`$ with $`A = 2^{B+1} - \sum_{n \le B}(n-\varphi(n))2^{\,B-n} \in \mathbb{Z}`$. Then $`T_\gamma = \bigl(A(2^{P}-1) - 2^{B}\bigr)/\bigl(2^{B}(2^{P}-1)\bigr)`$, and $`\gcd\bigl(A(2^{P}-1) - 2^{B},\, 2^{P}-1\bigr) = \gcd(2^{B}, 2^{P}-1) = 1`$ because $`2^{P}-1`$ is odd. So no factor of $`2^{P}-1`$ cancels, and the odd part of the reduced denominator is exactly $`2^{P}-1`$. For (iv), the odd part of the denominator is $`m = 2^{P}-1`$ and $`\mathrm{ord}_m(2) = P`$, while $`v_2(\mathrm{den}) \le B`$. By Lemma <a href="#lem:gperiod" data-reference-type="ref" data-reference="lem:gperiod">11</a>, $`R^{\gamma}_{N+P} - R^{\gamma}_{N} \in \mathbb{Z}`$ for every $`N \ge B`$, so by Lemma <a href="#lem:gsound" data-reference-type="ref" data-reference="lem:gsound">10</a> no $`\mathrm{Kill}_\gamma(P,N,L)`$ holds for any $`N \ge B`$ and any $`L`$. Taking $`N_0 = B`$ refutes the inner existential of $`\mathrm{Sep}_\gamma`$ at $`h = P`$. ◻

</div>

<div id="cor:b1" class="cor">

**Corollary 14** (What B1 rules out). *No proof rule that is uniform over all coefficient sequences $`c(n)\le n`$ can establish $`\mathrm{Sep}`$ from a single fixed prefix $`\{c(n):n\le B\}`$: Theorem <a href="#thm:gamma" data-reference-type="ref" data-reference="thm:gamma">13</a> supplies a rational countermodel with that same prefix. This does *not* invalidate an argument that uses the fixed arithmetic sequence $`\varphi`$ together with compatible information at arbitrarily large horizons; the theorem gives a different $`\gamma_B`$ for each $`B`$, not one sequence agreeing with $`\varphi`$ at every $`B`$.*

</div>

<div id="rem:b1-scope" class="rem">

*Remark 15* (Scope discipline — what B1 does *not* say). Theorem <a href="#thm:gamma" data-reference-type="ref" data-reference="thm:gamma">13</a> is a statement about proof method, not about $`\varphi`$. It does not touch $`S`$, and it does not suggest that $`\varphi`$ is such a $`\gamma`$; it says only that no fixed-horizon check can tell them apart. It also does *not* kill bounded-parameter certificates in general. “Bounded parameter” splits into four independent bounds with four different killers: bounded index range (this theorem), bounded certificate depth $`L`$ (killed separately, and by a Lean theorem — $`\mathrm{certifiedKill\_depth\_floor}`$ forces $`2(N{+}h{+}L{+}2) < 2^{L}`$), bounded proof state (B5), and bounded rank (B6). Conflating them would overstate B1.

</div>

The Lean-formalised sibling of the same mechanism — a lacunary zero-valued coboundary splice — is Proposition <a href="#prop:parity" data-reference-type="ref" data-reference="prop:parity">9</a>, which is B7. B1 and B7 are the two object-level witnesses of the wall, one along each axis.

<a id="b2b7"></a>

## B2–B7

Each barrier below is stated as a claim about a class of arguments, with its status never blurred. *Proved* means there is a theorem (Lean or ordinary mathematics, as marked) whose content is the elimination. *Observed pattern* means an audit over the corpus: real evidence, not a theorem, and it is never used as a premise elsewhere in this document.

<div id="prop:b2" class="prop">

**Proposition 16** (B2, route-collapse: intermediate targets are not waypoints). ***Status: proved** (Lean, three independent mechanisms).*

1.  **Certificate completeness.* Every certificate vocabulary is an *iff* with the underlying non-integrality, so every re-encoding of $`\mathrm{Sep}`$ is equivalent to $`\mathrm{Sep}`$ (, forward at `:132`, converse at `:143`).*

2.  **Sample choice.* Any weakening in which the prover may *choose* which indices to test collapses to $`\mathrm{Irrational}(S)`$ outright, because irrationality plus doubling expansivity already supplies a two-point sample with the required separation (). The mechanism is visible in the converse proof (`windowSeparatedPairsAt_of_cofinally_scaled_adjacent_chord`, `PivotAntiReconstruction.lean:1663`): it selects $`T = \{N, N+1\}`$ and two ordered pairs, and the counted-energy threshold $`2\lvert T\rvert^{2}/5 = 8/5 \le 2\delta^{2}`$ is met by $`\delta = 9/10`$.*

3.  **Multi-point enrichment.* Adding vertices, higher-order differences, or finite shift-polynomial combinations on the same ray buys nothing, because integrality transports affinely along every ray $`H \mapsto kH`$: the four-hit diamond $`\mathrm{Hit}(H) \wedge \mathrm{Hit}(pH) \wedge \mathrm{Hit}(qH)
      \wedge \mathrm{Hit}(pqH)`$ is equivalent to $`\mathrm{Hit}(H)`$ alone, with no primality used ().*

***Rules out:** “find an easier waypoint” as a strategy class. **Does not rule out:** targets over a *fixed full block* with no sample choice, and targets demanding a *uniform quantitative margin* that irrationality does not supply. These two exemptions are read off the collapse proofs themselves and are exactly what the surviving routes in §<a href="#sec:survivors" data-reference-type="ref" data-reference="sec:survivors">3</a> exploit. `coord:binary-digit` <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div class="rem">

*Remark 17*. A corroborating instance: rank-$`2`$ second-difference certificates are sound but measurably *not* shallower than rank-$`1`$ — at $`(h,N) = (1,8)`$ rank-$`1`$ fires at depth $`8`$ and no rank-$`2`$ certificate exists at depth $`\le 8`$ (`totient_tail_rank_two_kill_sound_but_not_shallower_cell`, `CertificateKernel.lean:18762`, <span class="sans-serif">\[Lean\]</span>). Separately, the claim sometimes made that the Farey growth law $`\sup_K(b+d) = \infty`$ is “equivalent in difficulty to \#249” is an argument, not an *iff*: the bound produced is the convergent denominator of the underlying constant, which stalls at $`q_0`$ precisely if $`S = a/q_0`$. It should not be cited as an equivalence. <span class="sans-serif">\[Math\]</span>

</div>

<div id="prop:b3" class="prop">

**Proposition 18** (B3, no free promotion). ***Status: observed pattern (an audit, not a theorem).** Across the corpus’s proved results, no bounded or partial result has a proof uniform enough to be promoted to cofinal scale by routine strengthening — raising a bound, widening a hypothesis, or reindexing a quantifier. Method: $`56`$ near-miss rows were catalogued against the four open obligations; $`18`$ were flagged promotable on a statement-level read; all $`18`$ proof *bodies* were then opened. Verdict: $`16`$ conclusively not promotable with a named blocker each, and $`2`$ promotable with no new mathematics but both pure restatements that widen a target family without supplying arithmetic content. Blocker taxonomy: hypothesis strength $`\times 6`$, scale-only $`\times 5`$, coordinate-only $`\times 4`$, multiple $`\times 3`$. Rows with an outright quantifier-order mismatch were judged unpromotable before the body audit and excluded, so the audited $`18`$ are the *most favourable* subset. `coord:audit` <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Cert\]</span>*

</div>

<div id="obs:pointwise" class="obs">

*Observation 19* (The sharpest signal in the audit). Every not-promotable \#249-supply row asks for a *pointwise* fact at a specially chosen index: one large $`a`$ with a top-edge residue gap, one $`q`$ with a terminal-dominance inequality, one exponent past $`a = 6`$, one $`t`$ past $`64`$, one sign at one LCM jump, one prime per LCM height, one $`K`$ past $`240`$. Not one such index has ever been located unconditionally beyond the finite census. The single audited row whose missing input is not of that shape is the first-harmonic gap — an *average* over a block. This contrast is what selects the leading survivor in §<a href="#sec:survivors" data-reference-type="ref" data-reference="sec:survivors">3</a>. It is evidence, not proof.

</div>

<div id="prop:b4" class="prop">

**Proposition 20** (B4, amplitude versus radius: residue engineering is self-defeating). ***Status: proved** (Lean construction plus an unconditional arithmetic margin). A certificate demands that the window residue sit at distance $`> N{+}h{+}L{+}2`$ from both $`0`$ and $`2^{L}`$ modulo $`2^{L}`$, and the depth floor forces $`2^{L} > 2(N{+}h{+}L{+}2)`$, so the required amplitude is comparable to the modulus. Any producer that *buys* that amplitude by prescribing totient values at engineered positions pays for the prescription in position, and position enters the radius. The corpus’s strongest such construction proves the trade is exactly self-cancelling, unconditionally and at every depth: a two-adic pulse block lands the residue at the arc *centre* $`2^{K-1} \bmod 2^{K}`$ — the ideal target — and still cannot fire, because its own defining congruence $`p \equiv 1 + 2^{K-1} \pmod{2^{K}}`$ forces $`p \ge 1 + 2^{K-1}`$, so with $`N = p-K`$, $`h = H`$, $`L = K`$ the radius $`p+H+2`$ exceeds $`2^{K-1}`$ for every prime $`p`$ and every $`K`$. `coord:two-adic-pulse` <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="rem:b4" class="rem">

*Remark 21* (B4’s own recorded repair, and its scope). Two further Lean facts show that prescribing *letters* is exhausted: the full terminal dyadic staircase is unconditionally impossible — its terminal letter would have to be positive, strictly below a wider modulus, and divisible by it, hence $`0`$ (); and the surviving *punctured* staircase pins its penultimate letter to exactly $`2^{m-1}`$ with $`2^{m} < 2(2H{+}J{+}K{+}2)`$, i.e. no slack at all (`puncturedDyadicStaircase_penultimate_eq_half`, `TotientActualLcmTopEdgeStaircase.lean:1187`). The repair the barrier permits is explicit: impose the half-turn on the *word* rather than on one delta, i.e. ask for cofinally many $`(h,N,L)`$ with $`\mathrm{windowDiscrepancy}(h,N,L) \equiv 2^{L-1} \pmod{2^{L}}`$ and $`2^{L-1} > N{+}h{+}L{+}2`$. What is *proved* is the failure of the Dirichlet/CRT residue-engineering family by an explicit exponential margin. The broader reading — that only carry accumulation across the weighted word can produce the required amplitude, since one letter obeys $`\lvert \varphi(n{+}h) - \varphi(n) \rvert < n{+}h`$ while the weighted word can reach $`2^{L}`$ — is an inference from the proved instance plus the linear growth bound, not itself a theorem on disk. <span class="sans-serif">\[Math\]</span>

</div>

<div id="prop:b5" class="prop">

**Proposition 22** (B5, bounded state and local signatures). ***Status: proved** (three Lean theorems, all problem-agnostic).*

1.  *No bounded or autonomous carry state summarising the history before position $`m`$ determines the tail after $`m`$: for a balanced-pulse family whose predecessor state is constant, no $`\mathrm{decode}`$ recovers the radius parameter, and any finite state type needs cardinality $`\ge \lfloor m/2 \rfloor + 2`$, unbounded in $`m`$ ().*

2.  *Long common suffixes erase predecessor information *exactly*: two affine binary orbits with different seeds satisfy $`\mathrm{orbit}_u(L) - \mathrm{orbit}_v(L) = 2^{L}(u_0 - v_0)`$, so the endpoint residue mod $`2^{L}`$ is independent of the initial carry ().*

3.  *Bounded local $`2`$-adic valuation-unit data at fixed precision excludes nothing: for any finite word of odd-unit symbols at fixed precision and any starting carry, a compatible orbit exists with every intermediate state centred inside its symbol’s dyadic radius ().*

***Rules out:** the finite-automaton-computes-the-expansion family outright; any hope of distinguishing two carry histories after a long common suffix; and any contradiction derived from a fixed-precision valuation-unit signature. Growing precision is mandatory, not optional. None of the three mentions $`\varphi`$, so all three bind \#257 identically. `coord:carry-orbit` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="prop:b6" class="prop">

**Proposition 23** (B6, no finite linear compression). ***Status: proved for four independent truncations** (Lean), with the honest limit stated below. Every natural finite truncation of the totient kernel has trivial kernel:*

1.  **Dyadic.* The canonical family of $`2^{e}+1`$ dyadic channels is linearly independent over $`\mathbb{Q}`$ at every depth (Proposition <a href="#prop:rank" data-reference-type="ref" data-reference="prop:rank">6</a>), and the natural repair — a bounded compressed-adjoint certificate — is impossible (, structure at `:1039`).*

2.  **Möbius incidence.* $`U_N(i,j) = \mu((i{+}1)/(j{+}1))`$ when $`(j{+}1) \mid (i{+}1)`$ and $`0`$ otherwise is lower triangular with unit diagonal, so $`\det U_N = 1`$ for every $`N`$ and the jet map is injective: no finite incidence-quotient relation exists at any horizon (, `mobiusCompanionJetMap_injective` at `:77`).*

3.  **Adjugate reconstruction.* Any finite rational row exactly isolating one totient value has crude two-tail cost $`\ge 3`$, hence never $`< 1`$, at any finite grid height, using only $`\varphi(x) \le x`$ (, closure at `:307`).*

4.  **Shift-polynomial.* An explicit nonzero all-horizon countermodel agrees with every exact whole-ray anchor and survives every finite commensurate LCM-cube shift polynomial, at every finite rank (`LcmFactorIdealPulseObstruction.lean`; module docstring, theorem bodies not individually re-verified in this pass, and the construction is explicitly synthetic — it does not claim its compensation letters occur as actual totient differences).*

*Additionally, every strict-subrank monomial quotient in the Möbius–Mersenne ladder overshoots its target by more than $`1/480`$, *uniformly* — every rung $`r \ge 3`$ lies in $`[1429/1512, 1)`$ and every prefix after four atoms is within $`1/3584`$ of its rung, so this is a uniform no-go rather than a census (). **Honest limit:** this is four checked truncations, not a proof that no finite-linear shortcut exists. Its correct reading is the one the source module gives: any winning finite-linear shortcut must live in a genuinely different coordinate or use a growing-parameter construction. The reason the barrier bites is Proposition <a href="#prop:period-not-rank" data-reference-type="ref" data-reference="prop:period-not-rank">7</a>: what rationality actually buys is periodicity, and periodicity provably does not promote to a rank bound. `coord:carry-rank` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="prop:b7" class="prop">

**Proposition 24** (B7, the coarse-invariant barrier). ***Status: proved** (Lean, `#print axioms` clean). This is Proposition <a href="#prop:parity" data-reference-type="ref" data-reference="prop:parity">9</a> read as an elimination. **Rules out:** any proof of \#249 whose hypothesis set on the coefficient word lies inside {uniform boundedness, $`c(n) \le n`$, agreement with $`\varphi`$ mod $`2`$ at every index, failure of eventual periodicity in any strength up to arbitrarily long, arbitrarily separated blocks}. The witness satisfies every one of those and is rational. **Does not rule out:** arguments using actual quantitative totient size or residue information. That complement is precisely why the corpus’s standing lesson is that only a quantitative argument in the actual-LCM or fixed-rank style can close \#249. Any future sufficient condition stated purely in terms of coefficient-word properties must be checked against this fixture before being trusted, for either problem. `coord:coefficient-word` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<a id="the-shape"></a>

## The shape

Put together, the barriers say something more specific than “the problem is hard”. The certificate residue is a weighted accumulation over an unboundedly long window at full arithmetic resolution, and *every device that makes an argument finite destroys precisely the quantity being measured*: bounding the window (B1), coarsening the values (B7), compressing the state (B5), truncating the rank (B6), or letting the prover pick the sample (B2). B4 closes the remaining escape — buying the amplitude by construction — with an explicit exponential margin, and B3 records that in practice nothing bounded has ever promoted.

There is exactly one known way to hold unbounded range and full resolution at once without a finite bookkeeping device: stop naming an index and assert an average instead. That is what an exponential-sum bound is. It is why the surviving routes of §<a href="#sec:survivors" data-reference-type="ref" data-reference="sec:survivors">3</a> are, with the honest exceptions noted there, the ones that never name a good index.

<a id="sec:survivors"></a>

# What the wall does not block

An elimination is only worth the paper it is written on if it leaves somewhere to stand. This section is that payoff. Five routes survive the classification of §<a href="#sec:wall" data-reference-type="ref" data-reference="sec:wall">2</a>; for each we state the exact statement it needs, which barrier it evades, and *why* the evasion is structural rather than accidental. Two of the five are demoted explicitly, because they evade every *proved* barrier while sitting squarely inside the class that the strongest *observed* pattern (Observation <a href="#obs:pointwise" data-reference-type="ref" data-reference="obs:pointwise">19</a>) indicts. None of the five is a proof, and none is close to one; what has changed is that the space of things to try is no longer large.

<a id="survivor-1-the-first-harmonic-block-cancellation-bound"></a>

## Survivor 1: the first-harmonic block cancellation bound

<div id="defn:fh" class="defn">

**Definition 25** (The open analytic obligation). Write $`e(x) := \exp(2\pi i x)`$ and $`\mathrm{windowFirstExp}(h,N,L) := e\bigl((\mathrm{windowDiscrepancy}(h,N,L) \bmod 2^{L})/2^{L}\bigr)`$. $`\mathrm{DTWFirstHarmonicNormGap}`$ is the statement
``` math
\forall h \ge 1\ \forall X_0\ \exists X, L : \quad
  \max(X_0,1) \le X, \quad
  16(2X + h + L + 2) \le 2^{L}, \quad
  \Bigl\lVert \sum_{N \in [X,\,2X)} \mathrm{windowFirstExp}(h,N,L) \Bigr\rVert
  \le \tfrac{21}{25}X .
```
It implies $`\mathrm{Irrational}(S)`$. `coord:first-harmonic` <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span>

</div>

The real-part form suffices and is strictly weaker: it is enough that $`\sum_{N \in [X,2X)} \mathrm{windowFirstCos}(h,N,L) \le \tfrac{9}{10}X`$ (, the elementary unconditional engine; the $`21/25 \to 9/10`$ bridge is ). Unpacked, the required object is a constant-saving cancellation estimate for the dyadically weighted totient-difference exponential sum
``` math
\sum_{X \le N < 2X}
  e\!\left(\frac{\sum_{j<L}\bigl(\varphi(N{+}h{+}1{+}j)-\varphi(N{+}1{+}j)\bigr)2^{\,L-1-j}}{2^{L}}\right),
  \qquad L \approx \log_2 X + O(1).
```
**Not one instance of this bound is proved anywhere, at any $`X`$, $`h`$ or $`L`$.** Both trees were searched for a theorem supplying it; only consumers exist. <span class="sans-serif">\[Open\]</span>

<a id="why-it-evades-the-wall."></a>

#### Why it evades the wall.

This is the only route in the corpus that evades all seven barrier classes, and the reasons are structural.

- **B1.** $`X`$ is a free unbounded parameter and the room condition $`16(2X{+}h{+}L{+}2) \le 2^{L}`$ forces $`L \gtrsim \log_2 X + 5`$, so the estimate reads $`\varphi`$ at every index in $`[X{+}1,\,2X{+}h{+}L]`$ with both position and window length growing. No $`\gamma`$ agreeing with $`\varphi`$ only on $`[1,B]`$ constrains it.

- **B2 — the decisive point.** The proved collapse $`\mathrm{DTWWindowSeparatedPairs} \Leftrightarrow \mathrm{Irrational}(S)`$ works *because the prover may choose the sample*: the converse proof selects $`T = \{N, N{+}1\}`$ and meets the threshold with $`\delta = 9/10`$ supplied by irrationality plus doubling expansivity (Proposition <a href="#prop:b2" data-reference-type="ref" data-reference="prop:b2">16</a>(b)). Definition <a href="#defn:fh" data-reference-type="ref" data-reference="defn:fh">25</a> admits no sample choice: the sum ranges over all of $`[X,2X)`$ at one common depth $`L`$. Since $`\neg\,\mathrm{certifiedKill}(h,N,L)`$ forces $`\mathrm{windowFirstCos}(h,N,L) > 9/10`$ (), the gap demands that a *positive proportion* of basepoints in the block carry certificates at a *single* depth. Irrationality supplies only one certificate per $`(h,N_0)`$, at a depth that may vary with $`N`$. The collapse mechanism therefore has no purchase. **Honest limit:** no theorem proves $`\mathrm{DTWFirstHarmonicNormGap}`$ inequivalent to $`\mathrm{Irrational}(S)`$. What is asserted is that the one proved collapse mechanism in this lane demonstrably requires sample choice, which this predicate denies. Note also that the *subset* form () does permit sample choice and is therefore the collapse-exposed variant. Attack the full-block form.

- **B4.** The statistic is the first additive character of the *accumulated* weighted word, never an individual letter. Nothing is prescribed at any position, so the self-defeating cost that kills Dirichlet residue engineering does not arise. B4’s own recorded repair (Remark <a href="#rem:b4" data-reference-type="ref" data-reference="rem:b4">21</a>) is to impose the structure on the word rather than on one delta, which is exactly what a block exponential-sum bound does.

- **B5, B6, B7.** No carry state is summarised and no fixed precision is used; the estimate is on the true residue mod $`2^{L}`$ with $`L \to \infty`$. A cancellation bound is not a rank statement and seeks no finite-dimensional relation. And the estimate uses the actual real residue, not parity, boundedness or aperiodicity, so neither countermodel touches it — both differ from $`\varphi`$ at exactly the large indices where this sum lives.

- **B3.** The audit’s own verdict on this row is that the consumer side is *finished* and already at the obligation’s exact quantifier shape: $`X`$ is free, so applying the bound at $`X \ge N_0`$ gives $`\exists N \ge N_0 \exists L`$ directly. The missing piece is one named arithmetic fact, not a strengthening of anything on disk. The constants $`9/10`$, $`\pi/8`$ and $`16`$ are absolute and do not degrade with $`X`$, $`h`$ or $`L`$; there is no case analysis and no table.

<div id="rem:b1-not-selector" class="rem">

*Remark 26* (Does B1 *select* this route? No.). It is tempting to say the finite-inspection theorem points at analysis. It does not. B1 says any proof must use $`\varphi`$ at unbounded indices — a necessary condition satisfied by *every* open route here (the LCM diagonal as $`t \to \infty`$, the actual-LCM supply for $`a \ge 8`$, the Farey growth law as $`K \to \infty`$, the rank bound for all $`e`$). B1 does not discriminate.

What selects this route is a sharper pair: (1) B4, proved, kills the only mechanism the corpus ever found for reaching full resolution at unbounded range by *prescribing* values, and its own stated repair is accumulation over the word — which is what an exponential sum measures; and (2) Observation <a href="#obs:pointwise" data-reference-type="ref" data-reference="obs:pointwise">19</a>, an observed pattern and not a theorem, shows that every single-index producer has failed to be supplied at even one large index, while this route’s missing input is a block average and therefore never requires naming a good index.

B1’s real contribution is narrower but still load-bearing: it proves that the finite deposits can never be extended into a proof, so the gap between the census and the obligation is a gap in kind, not in degree. That is a genuine no-go about method, of the same species as a relativization barrier. It is not a selector.

</div>

<div class="rem">

*Remark 27* (Evidence in both directions). Weak supporting evidence, observed and not proof: every landed diagonal certificate through $`t = 64`$ fires within a small additive constant of the minimum depth forced by $`\mathrm{certifiedKill\_depth\_floor}`$, which is the profile a doubling-orbit equidistribution argument would produce. Countervailing evidence, also observed: the strict-LCM-jump census records a closest central margin of $`\approx 0.000221`$ of the modulus at $`t = 100`$, so these residues are not robustly central and any equidistribution claim will be delicate. <span class="sans-serif">\[Cert\]</span>

</div>

<a id="survivor-2-the-four-term-pivot-budget"></a>

## Survivor 2: the four-term pivot budget

Same lane as Survivor 1, with the analytic burden repackaged. Split the block sum at a largest-prime pivot into centred correlation, fibre-mean, bad-cofactor and non-supplier contributions and bound the four separately.

<div id="defn:pivot" class="defn">

**Definition 28** ($`\mathrm{DTWPivotResidualDecorrelation}`$). For every $`h > 0`$ there are $`s > 0`$ and $`\eta \in (0,1)`$ such that for every $`X_0`$ there are $`X, L`$ with $`\max(X_0,1) \le X`$, $`h \le L - s`$, $`16(2X{+}h{+}L{+}2) \le 2^{L}`$, and all four of
``` math
\mathrm{Re}\,\mathrm{pivotCenteredCorrelation} \le \tfrac{14}{25}X, \quad
  \lVert \mathrm{pivotFiberMean} \rVert \le \tfrac{1}{100}X, \quad
  \lVert \mathrm{pivotBad} \rVert \le \tfrac{1}{100}X, \quad
  \lVert \mathrm{pivotNonSupplier} \rVert \le \tfrac{8}{25}X .
```
It implies $`\mathrm{Irrational}(S)`$. `coord:first-harmonic` <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span>

</div>

It inherits Survivor 1’s evasions of B1, B4, B5, B6 and B7 verbatim: the four terms are exact finite sums over canonical largest-prime supplier fibres of the same accumulated-word phases, with no sample choice and nothing prescribed. Its specific advantages are three.

The decomposition is an *exact identity*, proved unconditionally with `#print axioms` clean (, budget consumer ). The one-sided budget lowers the hard requirement from a norm bound $`\lVert \cdot \rVert \le X/2`$ to a real-part bound $`\le 14X/25`$. And the pivot rests on genuine arithmetic rather than a sampled surrogate: on the canonical fibre $`m = 1`$, $`s = L-h`$ the supplier set is *literally* the shifted dyadic interval of primes, proved as a membership equality (), with the totient factorisation at the pivot the honest $`\varphi(mp) = \varphi(m)(p-1)`$ and the non-divisibility discharged by size.

Three of the four terms are then counting bookkeeping; only the first needs a genuine correlation estimate, and only in real part.

**What it must respect.** B6 has a residual-gauge instance: a residual-blind determinant or conditioning test cannot certify that genuine phase reconstruction rather than a locked degenerate configuration has occurred (). So this route must couple rows by an extra arithmetic identity, not merely gauge-normalise columns. **Honest status:** strictly a repackaging of Survivor 1’s burden; it is listed separately only because three quarters of it are already exact identities on disk. The module asserts no prime-distribution or decorrelation estimate — the socket is deliberately empty. <span class="sans-serif">\[Open\]</span>

<a id="survivor-3-uniform-quantitative-escape-at-cofinally-many-primes"></a>

## Survivor 3: uniform quantitative escape at cofinally many primes

<div id="defn:primegap" class="defn">

**Definition 29** ($`\mathrm{DTWNaturalPrimeTailOrbitStrictGap}`$). For every $`h \ge 1`$ and every $`N_0`$ there is a prime $`p`$ with $`\max(N_0{+}h{+}1,\, h{+}5) \le p`$ and $`\mathrm{Re}\,\mathrm{tailOrbitFirstExp}(h,\,p{-}h{-}1) < \tfrac{9}{10}`$, where $`\mathrm{tailOrbitFirstExp}(h,N) = e(R_{N+h} - R_N)`$. Equivalently: cofinally many primes $`p`$ at which the totient tail difference across the shift $`h`$ stays a *fixed* distance $`\ge \arccos(9/10)/2\pi \approx 0.0718`$ from every integer. It implies $`\mathrm{Irrational}(S)`$. `coord:prime-pivot` <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span>

</div>

It evades B1, B4, B5, B6 and B7 for the reasons given for Survivor 1: a statement about the true real tail difference at unbounded prime positions, with no letters prescribed, no bounded state, no rank, no coarse coefficient-word invariant. It evades B2 by the *second* of the two exemptions in Proposition <a href="#prop:b2" data-reference-type="ref" data-reference="prop:b2">16</a> — not by denying sample choice, but by demanding a *uniform margin*. Irrationality gives non-integrality of every tail difference and supplies no lower bound whatever on distance to $`\mathbb{Z}`$; certificate completeness therefore cannot manufacture this predicate.

**Honest demotion.** This is a *pointwise* producer: it requires naming a good prime, and Observation <a href="#obs:pointwise" data-reference-type="ref" data-reference="obs:pointwise">19</a> records that no pointwise producer in this corpus has ever been supplied at even one large index, across seven independent attempts. It evades every proved barrier while sitting inside the class the strongest observed pattern indicts. Nothing on disk proves it at a single prime for a single $`h`$. It ranks below Survivor 1. <span class="sans-serif">\[Open\]</span>

<a id="survivor-4-depth-locked-full-depth-escape"></a>

## Survivor 4: depth-locked full-depth escape

<div id="defn:apfde" class="defn">

**Definition 30** ($`\mathrm{ApFullDepthEscape}`$). For every $`d \ge 1`$ and every $`N`$ there is $`t \ge 1`$ with $`\mathrm{certifiedKill}(td,\,N,\,td)`$; unpacked,
``` math
N + 2td + 2 \;<\; \mathrm{windowDiscrepancy}(td,N,td) \bmod 2^{td}
  \;<\; 2^{td} - (N + 2td + 2).
```
It implies $`\mathrm{Irrational}(S)`$. `coord:period-ray` <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span>

</div>

This is the shortest fully stated open inequality the programme has produced. Its evasion of B2 is recorded on disk rather than argued: its ambient parent $`\mathrm{PeriodMultipleKillSupply}`$ is *proved* equivalent to $`\mathrm{Irrational}(S)`$ and $`\mathrm{ApFullDepthEscape}`$ implies it (), so it is at least as strong, and possibly strictly stronger — the file’s own docstring records “sufficient for irrationality; not known necessary”. Being possibly strictly stronger, certificate completeness cannot collapse it back. It evades B1 (both $`N`$ and $`t`$ unbounded), B4 (locking depth to the period means the entire word accumulates and no letter is prescribed), B5 and B6 (no state, no rank). Its substance is pure anti-concentration: via , the difference of two adjacent period blocks must have central residue mod $`2^{h}`$ at some multiple period $`h = td`$, and the room condition is automatic once $`h`$ is large, so nothing but the residue’s position is at stake.

**Honest demotion,** identical to Survivor 3: it is a pointwise producer and names an index. It is listed because it is the cleanest target for computational exploration — with Theorem <a href="#thm:gamma" data-reference-type="ref" data-reference="thm:gamma">13</a> as the standing reminder that no amount of such exploration becomes a proof. <span class="sans-serif">\[Open\]</span>

<a id="survivor-5-the-rationality-side-rank-upper-bound"></a>

## Survivor 5: the rationality-side rank upper bound

<div id="defn:rankupper" class="defn">

**Definition 31** (The coordinate-disjoint obligation). Either: there is $`C`$ such that for every $`c : \mathbb{N}\to \mathbb{N}`$ with $`c(n) \le n`$ and $`T_c \notin`$ the irrationals, every $`v > 0`$ and every tempered binary orbit $`u`$ for $`(c,v)`$, and every $`e`$, $`\dim_{\mathbb{Q}} \mathrm{span}_{\mathbb{Q}}\bigl(\mathrm{canonicalCarryKernelFamily}(u,e)\bigr) \le C`$; or the same with any $`g(e)`$ growing strictly slower than $`2^{e}-1`$ in place of $`C`$. Either version contradicts the proved floor of Proposition <a href="#prop:rank" data-reference-type="ref" data-reference="prop:rank">6</a> and closes \#249. `coord:carry-rank` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Open\]</span>

</div>

This is the only surviving obligation that is not a residue or certificate statement at all, so B2’s certificate completeness cannot reach it — it is not a reformulation of $`\mathrm{Sep}`$ in any vocabulary. It evades B1 and B4 entirely (no window, no letters, no prescribed residues) and B5 (linear algebra over the whole orbit, not a bounded-state summary). The scale side is finished and uniform in $`e`$ (Proposition <a href="#prop:rank" data-reference-type="ref" data-reference="prop:rank">6</a>).

**Honest flag, and it is severe.** B6 partly indicts this route from inside. The most natural approach to the upper bound is dead (), and what rationality actually buys — uniform eventual periodicity of the carry’s dyadic sections mod $`v`$ — provably does not promote to a $`\mathbb{Q}`$-rank bound (Proposition <a href="#prop:period-not-rank" data-reference-type="ref" data-reference="prop:period-not-rank">7</a>). So this survivor is genuinely coordinate-disjoint from everything else, which is its whole value, but its obvious approach is closed and the missing input is a rigidity theorem nobody has stated.

<a id="reading-the-detailed-record"></a>

# Reading the detailed record

The opening note has already defined the evidence bands, scale tags, coordinates, and catalogue terminology. This section therefore gives only the order of dependence needed for the longer reference material.

<a id="scale-and-coordinate-discipline."></a>

#### Scale and coordinate discipline.

Every direct certificate deposit for $`\mathrm{Sep}`$ is fixed or bounded, although the corpus also contains uniform and cofinal structural theorems. Those stronger-scale results do not produce $`\mathrm{Sep}`$, and Theorem <a href="#thm:gamma" data-reference-type="ref" data-reference="thm:gamma">13</a> shows why extending bounded verification does not establish the cofinal statement. The coordinate tags are equally literal: the $`\gamma`$-splice concerns `coord:binary-digit`, the rank floor `coord:carry-rank`, positivity `coord:actual-lcm`, and the Farey exclusion `coord:farey`. An obstruction in one coordinate does not transfer without a proved map.

<a id="order-of-dependence."></a>

#### Order of dependence.

Read the wall in §<a href="#sec:wall" data-reference-type="ref" data-reference="sec:wall">2</a> before selecting an attack. In particular, B4 governs prescribed totient values, B5 bounded carry states, and B2 purportedly weaker certificate conditions. The mathematical-ingredient catalogue that follows may then be entered by coordinate: it records hypotheses, evidence band, scale, and Lean declaration. The later tables give the exact implication graph, the near misses at each open obligation, and the promotion audit summarised as B3. These tables are reference material; the wall and the surviving-route argument are intended to be read linearly.

<a id="the-object-the-target-and-the-exact-record"></a>

# The object, the target, and the exact record

This part fixes the object of Erdős Problem \#249, states exactly what is open about it, and records every unconditional numeral, identity and Lean-checked bound the corpus currently holds. Nothing in this part decides irrationality. Every result below is either an identity (no hypothesis, holds unconditionally), a finite computation (holds up to an explicitly stated bound), or is flagged <span class="sans-serif">\[Cited\]</span>/<span class="sans-serif">\[Open\]</span> where that is the honest status.

<a id="the-object"></a>

## The object

<div id="defn:S" class="defn">

**Definition 32** (The Erdős–249 constant). Let $`\varphi`$ denote Euler’s totient function. Define
``` math
S \;:=\; \sum_{n \ge 1} \frac{\varphi(n)}{2^{n}} \;=\; \sum_{n : \mathbb{N}} \frac{\varphi(n)}{2^{n}},
```
the two forms coinciding because $`\varphi(0)=0`$; the second, $`\mathbb{N}`$-indexed form is the one carried in the Lean source. The series converges absolutely since $`\varphi(n) = O(n)`$. *Erdős \#249 asks whether $`S`$ is irrational. This is OPEN.* Nothing in this paper decides it; every claim below is either an unconditional identity, a finite computation with an explicitly stated range, or is marked <span class="sans-serif">\[Cited\]</span>/<span class="sans-serif">\[Open\]</span>.

</div>

<div class="rem">

*Remark 33* (Status). No proof or disproof of $`\mathrm{Irrational}(S)`$ exists anywhere in the corpus, formal or informal. What exists is: one large unconditional finite denominator exclusion (§<a href="#ssec:farey" data-reference-type="ref" data-reference="ssec:farey">5.3</a>), several exact reformulations of $`S`$ that relocate the same open question onto different coordinates without touching its truth value (§<a href="#ssec:coprime" data-reference-type="ref" data-reference="ssec:coprime">5.4</a>–§<a href="#ssec:lambert" data-reference-type="ref" data-reference="ssec:lambert">5.6</a>), and a certificate apparatus whose cofinal supply obligation is the precise open target (recorded in full in Part 1 of this paper; only its finite, checked instances are catalogued here, §<a href="#ssec:certtable" data-reference-type="ref" data-reference="ssec:certtable">5.7</a>).

</div>

<a id="the-binary-digit-reduction"></a>

## The binary-digit reduction

<div id="prop:shift" class="prop">

**Proposition 34** (Digit-shift identity). *For every $`N : \mathbb{N}`$,
``` math
2^{N} \cdot S \;=\; \Phi_N + R_N,
```
where $`\Phi_N := \sum_{n \le N} \varphi(n) \cdot 2^{N-n} \in \mathbb{N}`$ (the integer prefix) and $`R_N := \sum_{j \ge 0} \varphi(N+1+j)/2^{j+1}`$ (the fractional tail, `totientTail` in Lean). `coord:binary-digit` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div class="proof">

*Consequence.* Rationality and eventual periodicity of the base-2 expansion of $`S`$ is *exactly* a statement about the tail $`R_N`$: $`S \in \mathbb{Q}`$ forces (by Euler’s theorem applied to the odd part of the denominator) a period $`h>0`$ and pre-period $`N_0`$ with $`R_{N+h}-R_N \in \mathbb{Z}`$ for all $`N \ge N_0`$ (`eventual_period_of_not_irrational`, , <span class="sans-serif">\[Lean\]</span>, explicit witness $`h=\varphi(\mathrm{oddPart}(r.\mathrm{den}))`$, $`N_0=v_2(r.\mathrm{den})`$). Nothing in the corpus supplies the converse cofinally; this is the certificate wall documented in full in Part 1 and is not restated here beyond this pointer. ◻

</div>

<a id="ssec:farey"></a>

## The unconditional denominator floor

The strongest *unconditional* fact the corpus holds about $`S`$ is a lower bound on its denominator should it happen to be rational. It is obtained by a completely elementary Farey/mediant argument, entirely free of any certificate or period apparatus, and is therefore logically independent of the open certificate-supply obligation.

<div id="lem:farey" class="lem">

**Lemma 35** (Farey gap, fully general). *For integers $`a,b,c,d,r,s`$ with $`b>0`$, $`d>0`$, $`bc-ad=1`$ (i.e. $`a/b`$ and $`c/d`$ are unimodular Farey neighbours), and $`as < rb`$, $`rd < cs`$ (i.e. $`r/s`$ lies strictly between them): $`b+d \le s`$. `coord:farey` <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span>*

</div>

This lemma is a classical Stern–Brocot fact with zero totient or Mersenne content; it is the generic engine underneath every Farey-gap bound in the corpus, for either open problem.

<div id="prop:gapwindow" class="prop">

**Proposition 36** (The wave-17 gap certificate at window $`K=240`$). *Let $`V`$ be the explicit committed totient residue for window $`(N,K)=(1,240)`$. For every $`q : \mathbb{N}`$ with
``` math
0 < q \;\le\; Q_0 := 79\,639\,646\,646\,701\,375\,323\,355\,774\,875\,831\,053 \;\;(\approx 7.96\times 10^{34}),
```
``` math
(q \cdot V) \bmod 2^{240} \;+\; 243\,q \;<\; 2^{240}.
```
This bound is *sharp*: $`q = Q_0+1 = 79\,639\,646\,646\,701\,375\,323\,355\,774\,875\,831\,054`$ is the exact first failing denominator, exhibited as the mediant of two explicit unimodular Farey neighbours. `coord:farey` <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="thm:denom-record" class="thm">

**Theorem 37** (Erdős \#249 denominator exclusion — the headline unconditional result). *For every $`p \in \mathbb{Q}`$ with reduced denominator $`p.\mathrm{den} \le Q_0`$,
``` math
S \;\neq\; p.
```
Equivalently: *if $`S`$ is rational, its reduced denominator exceeds* $`Q_0 \approx 7.96 \times 10^{34}`$. `coord:farey` <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div class="rem">

*Remark 38* (What this does and does not say). Theorem <a href="#thm:denom-record" data-reference-type="ref" data-reference="thm:denom-record">37</a> is a complete, unconditional finite fact: no rational of small denominator equals $`S`$. It says nothing about arbitrarily large denominators and is not itself a route to irrationality. The docstring behind Proposition <a href="#prop:gapwindow" data-reference-type="ref" data-reference="prop:gapwindow">36</a> states the honest open question this leaves: whether $`\sup_K (b+d)(K)`$ (the growing analogue of $`Q_0`$ as the window $`K`$ grows) is unbounded as $`K \to \infty`$ — which would close \#249 through this theorem’s consumer, entirely independently of the certificate-supply obligation of Proposition <a href="#prop:shift" data-reference-type="ref" data-reference="prop:shift">34</a>. <span class="sans-serif">\[Open\]</span>; not claimed or proved anywhere in the corpus.

</div>

<div class="rem">

*Remark 39* (Ladder of prior rungs). $`Q_0`$ is the current end of an explicit sequence of increasingly wide Farey windows computed by the same mechanism: $`4838 \to 2^{22} \to 2.49\times10^{17}`$ (window $`K=120`$) $`\to Q_0`$ (window $`K=240`$). Each rung is a finite, independently checked instance of Lemma <a href="#lem:farey" data-reference-type="ref" data-reference="lem:farey">35</a> and Proposition <a href="#prop:gapwindow" data-reference-type="ref" data-reference="prop:gapwindow">36</a>’s pattern at a larger $`K`$; none is claimed to extrapolate.

</div>

<a id="ssec:coprime"></a>

## The same record, transported: the Möbius-square and coprimality-probability forms

The exact finite Farey record behind Theorem <a href="#thm:denom-record" data-reference-type="ref" data-reference="thm:denom-record">37</a> is not tied to the $`\varphi(n)/2^n`$ presentation of $`S`$; it transfers verbatim to two other exact reformulations of the same constant, at exactly half the bound.

<div id="prop:coprime" class="prop">

**Proposition 40** (Fair-coin coprimality form). *Let $`X,Y`$ be independent random variables with $`\Pr(X=n)=\Pr(Y=n)=2^{-n}`$ for $`n \ge 1`$ (independent fair-coin waiting times). Then
``` math
S \;=\; \tfrac12 \;+\; \Pr\bigl(\gcd(X,Y)=1\bigr)
\;=\; \tfrac12 \;+\; \sum_{\substack{a,b\ge 1\\ \gcd(a,b)=1}} 2^{-(a+b)}.
```
Equivalently, on the visible lattice: summing $`2^{-(a+b)}`$ over the half-open coprime pairs ($`a\ge1`$, $`b\ge0`$, $`\gcd(a,b)=1`$) recovers $`\sum_n \varphi(n)/2^n`$ exactly, with no boundary correction, because the visible-point count on the half-open antidiagonal at height $`n`$ equals $`\varphi(n)`$ for every $`n`$, including $`n=0,1`$. `coord:probability` <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="prop:gcdlayer" class="prop">

**Proposition 41** (The gcd-layer normalisation). *For independent fair-coin waiting times as above, $`\sum_{g\ge1}\Pr(\gcd(X,Y)=g)=1`$ exactly; and for every $`d>0`$, $`\Pr(d\mid X \wedge d\mid Y) = 1/(2^d-1)^2`$. `coord:probability` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="thm:denomcoprime" class="thm">

**Theorem 42** (Denominator exclusion for the coprimality-probability form). *Let
``` math
Q_1 := \left\lfloor \frac{Q_0}{2} \right\rfloor = 39\,819\,823\,323\,350\,687\,661\,677\,887\,437\,915\,526.
```
For every $`a\in\mathbb{Z}`$, $`d\in\mathbb{N}`$ with $`0<d\le Q_1`$: the visible coprime-pair probability $`\Pr(\gcd(X,Y)=1)`$ is not equal to $`a/d`$. `coord:farey` <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div id="thm:denommobsq" class="thm">

**Theorem 43** (Denominator exclusion for the Möbius-square form). *With $`Q_1`$ as in Theorem <a href="#thm:denomcoprime" data-reference-type="ref" data-reference="thm:denomcoprime">42</a>: for every $`a\in\mathbb{Z}`$, $`d\in\mathbb{N}`$ with $`0<d\le Q_1`$, the signed series $`T := \sum_{d\ge1} \mu(d)/(2^d-1)^2 = S - \tfrac12`$ (see §<a href="#ssec:mobius" data-reference-type="ref" data-reference="ssec:mobius">5.5</a>) is not equal to $`a/d`$. `coord:farey` <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div class="rem">

*Remark 44* (Why the bound halves, and why this is not new information). $`Q_1 = \lfloor Q_0/2 \rfloor`$ arithmetically: $`Q_0`$ is odd ($`Q_0 = 79\,639\,646\,646\,701\,375\,323\,355\,774\,875\,831\,053`$), so $`Q_0/2 = 39\,819\,823\,323\,350\,687\,661\,677\,887\,437\,915\,526.5`$ and $`Q_1`$ is its floor. The halving is the cost of transporting the known bound through the affine shift $`S = \tfrac12 + T`$ (resp. $`S = \tfrac12 + \Pr(\gcd(X,Y)=1)`$) on a denominator-exclusion statement: excluding all denominators $`\le Q_1`$ for $`T`$ follows from excluding all denominators $`\le Q_0`$ for $`S`$ (a denominator-$`d`$ value of $`T`$ with $`d\le Q_1`$ yields a denominator dividing $`2d\le Q_0`$ for $`S`$). Theorems <a href="#thm:denomcoprime" data-reference-type="ref" data-reference="thm:denomcoprime">42</a> and <a href="#thm:denommobsq" data-reference-type="ref" data-reference="thm:denommobsq">43</a> are therefore the *same* finite Farey record as Theorem <a href="#thm:denom-record" data-reference-type="ref" data-reference="thm:denom-record">37</a>, transported through Proposition <a href="#prop:coprime" data-reference-type="ref" data-reference="prop:coprime">40</a> and Proposition <a href="#prop:mobsq" data-reference-type="ref" data-reference="prop:mobsq">45</a> respectively — not independent evidence. The converse finite implication is not asserted: subtracting $`1/2`$ can double a denominator, so the $`Q_1`$ exclusion for $`T`$ alone need not recover the full $`Q_0`$ exclusion for $`S`$.

</div>

<a id="ssec:mobius"></a>

## The Möbius–Mersenne identity and why bounded coefficients matter

<div id="prop:mobsq" class="prop">

**Proposition 45** (Möbius-square reduction).
*``` math
S \;=\; \sum_{n\ge1}\frac{\varphi(n)}{2^n} \;=\; \frac12 \;+\; \sum_{d\ge1}\frac{\mu(d)}{(2^d-1)^2},
```
where $`\mu`$ is the Möbius function, so $`\mu(d)\in\{-1,0,1\}`$ for every $`d`$. Consequently *Erdős \#249 $`\iff`$ $`T:=\sum_{d\ge1}\mu(d)/(2^d-1)^2 \notin \mathbb{Q}`$*, the single reduced target every other result in this subsection and §<a href="#ssec:lambert" data-reference-type="ref" data-reference="ssec:lambert">5.6</a> feeds. `coord:mobius-mersenne` <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span>*

</div>

<div class="rem">

*Remark 46* (Why the bounded coefficients matter — the Erdős-1948 regime). The identity of Proposition <a href="#prop:mobsq" data-reference-type="ref" data-reference="prop:mobsq">45</a> rewrites $`S`$ (equivalently $`T`$) as a *Möbius-twisted Lambert-squared series*: the numerator weight $`\mu(d)`$ is bounded, $`|\mu(d)|\le1`$ for every $`d`$, uniformly in $`d`$. This places $`T`$ in exactly the coefficient regime of the classical Erdős (1948) near-integer irrationality criterion and of the level-1 sibling identity $`L(\mu):=\sum_d \mu(d)/(2^d-1) = \tfrac12`$ (rational, trivially) alongside $`L(1) = \sum_d 1/(2^d-1) = E`$, the Erdős–Borwein constant, which *is* proved irrational in this same kernel (, <span class="sans-serif">\[Lean\]</span>).

This is the opposite regime from Proposition <a href="#prop:shift" data-reference-type="ref" data-reference="prop:shift">34</a>’s **binary-digit coordinate**, where the corresponding weight satisfies $`0\le\varphi(n)\le n`$ and is unbounded. The function $`\varphi`$ has average order $`6n/\pi^2`$, equivalently $`\sum_{k\le x}\varphi(k)\sim 3x^2/\pi^2`$, but there is no pointwise estimate $`\varphi(n)=\Theta(n)`$. A near-integer/Dirichlet-approximation argument of Erdős-1948 shape (formalised generically as and its base-power specialisation , both <span class="sans-serif">\[Lean\]</span>, `coord:n/a`, fully coordinate-free) has a genuine chance of transferring to $`T`$ precisely because its weight is bounded, in a way it does not have a chance of transferring directly to the raw $`\varphi(n)/2^n`$ series.

No such transfer is proved; §<a href="#ssec:mobius" data-reference-type="ref" data-reference="ssec:mobius">5.5</a> below (cross-referenced here, developed in Part 2 of this paper) records exactly why the transfer has so far failed (the “$`\mu`$-pollution” obstruction) rather than merely asserting the analogy.

</div>

<a id="ssec:lambert"></a>

## The squared-Lambert gcd-moment identities

<div id="prop:lambertengine" class="prop">

**Proposition 47** (Squared-Lambert transfer engine). *For $`w:\mathbb{N}\to\mathbb{R}`$ with $`|w(d)|\le d`$ for all $`d>0`$, and $`0\le r<1`$:
``` math
\sum_{d\ge1} w(d)\left(\frac{r^d}{1-r^d}\right)^2 \;=\; \sum_{n\ge1}\left(\sum_{e\mid n} w(e)\Bigl(\tfrac{n}{e}-1\Bigr)\right) r^n.
```
`coord:mobius-mersenne` <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span>*

</div>

This one identity, at $`r=1/2`$, specialises to every squared-Lambert rung the corpus computes; two instances are exact and directly relevant to \#249’s weight structure:

<div id="prop:zetaq" class="prop">

**Proposition 48** (The known $`\zeta_q`$-rung).
*``` math
\sum_{d\ge1} \frac{1}{(2^d-1)^2} \;=\; \sum_{n\ge1} \frac{\sigma(n)-\tau(n)}{2^n} \;=\; \zeta_q(2)-\zeta_q(1) \text{ at } q=\tfrac12,
```
where $`\sigma`$ is the sum-of-divisors function and $`\tau`$ the number-of-divisors function. The *identity* is machine-checked (<span class="sans-serif">\[Lean\]</span>); irrationality of the *value* $`\zeta_q(2)-\zeta_q(1)`$ is <span class="sans-serif">\[Cited\]</span> (Postelmans–Van Assche $`q`$-Padé), *not* formalised in this corpus. `coord:mobius-mersenne` <span class="sans-serif">scale:n/a</span>*

</div>

<div id="prop:pillai" class="prop">

**Proposition 49** (The Pillai/gcd-moment rung).
*``` math
\sum_{d\ge1} \frac{\varphi(d)}{(2^d-1)^2} \;=\; \sum_{n\ge1} \bigl(P(n)-n\bigr)\cdot 2^{-n} \;=\; \mathbb{E}[\gcd(X,Y)],
```
where $`P(n) := \sum_{e\mid n}\varphi(e)\cdot(n/e) = (\varphi * \mathrm{Id})(n)`$ is Pillai’s gcd-sum function and $`X,Y`$ are the independent fair-coin waiting times of Proposition <a href="#prop:coprime" data-reference-type="ref" data-reference="prop:coprime">40</a>. The identity itself is machine-checked (<span class="sans-serif">\[Lean\]</span>); the value $`\mathbb{E}[\gcd(X,Y)]`$ is <span class="sans-serif">\[Open\]</span> — a cousin rung to \#249, not \#249 itself. `coord:mobius-mersenne` <span class="sans-serif">scale:n/a</span>*

</div>

<div class="rem">

*Remark 50* (The level mirror). Writing $`L(f):=\sum_d f(d)/(2^d-1)`$ (level 1) and $`L_2(f):=\sum_d f(d)/(2^d-1)^2`$ (level 2): $`L(\mu)=\tfrac12`$ (rational, trivial), $`L(1)=E`$ (Erdős–Borwein, irrational, <span class="sans-serif">\[Lean\]</span>), $`L(\varphi)=2`$ (rational); $`L_2(\mu)=S-\tfrac12`$ (<span class="sans-serif">\[Open\]</span>, this is \#249), $`L_2(1)=\zeta_q(2)-\zeta_q(1)`$ (<span class="sans-serif">\[Cited\]</span> irrational, Proposition <a href="#prop:zetaq" data-reference-type="ref" data-reference="prop:zetaq">48</a>), $`L_2(\varphi)=\mathbb{E}[\gcd(X,Y)]`$ (<span class="sans-serif">\[Open\]</span>, Proposition <a href="#prop:pillai" data-reference-type="ref" data-reference="prop:pillai">49</a>). At level 1 the Möbius rung is trivial and the $`\zeta`$-rung is the hard classical case; at level 2 the $`\zeta`$-rung is known and the Möbius rung *is* \#249. Möbius projection is the one wall repeated at both levels of the ladder.

</div>

<a id="ssec:certtable"></a>

## The exact certificate record: the contiguous band through $`t\le82`$

The certificate apparatus itself (the predicate `certifiedKill`, its soundness/completeness theorems, and the cofinal supply obligation that is the actual open target) is developed in full in Part 1 of this paper. What is recorded here is a representative historical set of machine-checked anchors, together with the current aggregate theorem closing every scale $`t\le82`$. The declaration inventory, rather than this table, is authoritative for all individual certificate shards; no extrapolation beyond the stated band is implied.

<a id="certificate-object."></a>

#### Certificate object.

For $`h,N,L : \mathbb{N}`$, define the window discrepancy $`\Delta_{h,N,L} := \sum_{j<L} (\varphi(N+h+1+j)-\varphi(N+1+j))\cdot 2^{L-1-j} \in \mathbb{Z}`$ (, <span class="sans-serif">\[Lean\]</span>), and
``` math
\mathrm{Sep}(h,N,L) \;:\equiv\; (N+h+L+2) < \Delta_{h,N,L} \bmod 2^{L} < 2^{L}-(N+h+L+2),
```
(, <span class="sans-serif">\[Lean\]</span>, decidable). By completeness (, <span class="sans-serif">\[Lean\]</span>), $`(\exists L,\ \mathrm{Sep}(h,N,L)) \iff R_{N+h}-R_N \notin \mathbb{Z}`$ for every $`h,N`$: an unbounded (cofinal, over $`h`$ and $`N`$) supply of $`\mathrm{Sep}`$ is exactly equivalent to $`\mathrm{Irrational}(S)`$. The table below records the principal $`(h,N,L)`$-shaped and $`t`$-shaped anchors; none of them is cofinal, and none is presented as deciding \#249.

| **Anchor** | **Exact statement of what was checked** | **Scale** | **Site** |
|:---|:---|:---|:---|
| Fixed-window deposit, depth 16 | $`\mathrm{Sep}(h,12,16)`$ holds for every $`h \in \{1,\dots,8\}`$ (by `decide`, $`256`$ totient values below $`37`$); consequently $`S \ne r`$ for every $`r\in\mathbb{Q}`$ with $`1\le h\le 8`$ and $`r.\mathrm{den} \mid 2^{12}(2^h-1)`$. | <span class="sans-serif">scale:fixed</span> |  |
| Fixed-window deposit, depth 9, wider net | $`\mathrm{Sep}(h,14,9)`$ holds for every $`h\in\{1,\dots,16\}`$: $`S \ne r`$ for every $`r\in\mathbb{Q}`$ with $`1\le h\le16`$ and $`r.\mathrm{den}\mid 2^{14}(2^h-1)`$. | <span class="sans-serif">scale:fixed</span> |  |
| Diagonal-pincer certificates, base 12 scales | $`\mathrm{Sep}\bigl(H_t, H_t, D(t)\bigr)`$, $`H_t := \mathrm{lcm}(1,\dots,t)`$, holds (by explicit `decide`/`norm_num` on checked `Nat.totient` values, via factored prime-power blocks with Lucas-primality certificates) for $`t \in \{1,2,3,4,5,7,8,9,11,13,16,17\}`$ with certificate depths $`D(t) \in \{6,5,7,7,9,14,15,14,21,22,23,26\}`$ respectively (in the same order). | <span class="sans-serif">scale:fixed</span> |  |
| Diagonal-pincer certificates, extended scales through $`t=64`$ | The same predicate $`\mathrm{Sep}(H_t,H_t,D(t))`$ is additionally checked, one sibling module per scale, at $`t \in \{19,\allowbreak23,\allowbreak25,\allowbreak27,\allowbreak29,\allowbreak31,
\allowbreak32,\allowbreak37,\allowbreak41,\allowbreak43,\allowbreak47,\allowbreak49,
\allowbreak53,\allowbreak59,\allowbreak61,\allowbreak64\}`$ (16 further explicit values). Together with the base 12 scales above this is **28 explicit values of $`t`$ in total**, the complete list being $`\{1,\allowbreak2,\allowbreak3,\allowbreak4,\allowbreak5,\allowbreak7,
\allowbreak8,\allowbreak9,\allowbreak11,\allowbreak13,\allowbreak16,\allowbreak17,
\allowbreak19,\allowbreak23,\allowbreak25,\allowbreak27,\allowbreak29,\allowbreak31,
\allowbreak32,\allowbreak37,\allowbreak41,\allowbreak43,\allowbreak47,\allowbreak49,
\allowbreak53,\allowbreak59,\allowbreak61,\allowbreak64\}`$. This does *not* establish $`\mathrm{Sep}(H_t,H_t,\cdot)`$ for infinitely many $`t`$; these 28 deposits are a historical strict subset of the contiguous band in the next row. | <span class="sans-serif">scale:fixed</span> | Per-scale Lean modules; endpoint |
| Contiguous lcm-diagonal band through $`t\le82`$ | For every natural $`t\le82`$ there exists a depth $`L`$ with $`\mathrm{Sep}(H_t,H_t,L)`$. This closes every scale in the finite interval, including plateau transfers, with no holes. The next lcm jump is at the prime $`83`$; no certificate at $`t=83`$ is claimed, and any such certificate must have depth at least $`125`$. | <span class="sans-serif">scale:bounded</span> |  |
| Farey denominator floor | Every $`q\in\mathbb{N}`$ with $`0<q\le Q_0=79\,639\,646\,646\,701\,375\,323\,355\,774\,875\,831\,053`$ satisfies the window-$`(N,K)=(1,240)`$ gap certificate; $`q=Q_0+1`$ is the exact first failure. | <span class="sans-serif">scale:bounded</span> |  |
| Coprimality-probability / Möbius-square Farey floor | Every $`d\in\mathbb{N}`$ with $`0<d\le Q_1=39\,819\,823\,323\,350\,687\,661\,677\,887\,437\,915\,526`$ (exactly $`\lfloor Q_0/2\rfloor`$) is excluded as a denominator of $`\Pr(\gcd(X,Y)=1)`$ and, separately, of $`T=\sum_d\mu(d)/(2^d-1)^2`$. | <span class="sans-serif">scale:bounded</span> |  |

<div class="rem">

*Remark 51* (What this table is not). No row above is cofinal in its indexing parameter ($`h`$, $`t`$, or the denominator bound), and no row is claimed to extrapolate. The historical diagonal-pincer depths are irregular and nonmonotone ($`6,5,7,7,9,14,15,14,21,22,23,26,\dots`$); no closed-form growth rate for $`D(t)`$ is proved or conjectured in the corpus. This table records the historical 28-scale bank through $`t=64`$; the later aggregate theorem for every $`t\le82`$ is stated above and is not itemised row by row here. Neither bounded record supplies the cofinal obligation developed in Part 1.

</div>

<a id="catalogue-of-mathematical-ingredients"></a>

# Catalogue of mathematical ingredients

This catalogue renders every producer and converter/identity result found for Erdős \#249 ($`S = \sum_{n\ge1}\varphi(n)/2^n`$) in the certificate-kernel lane (`TotientTailPeriodKiller.lean`, `CertificateKernel.lean`, and the lcm/diagonal/cone reduction family) and the Möbius–Mersenne / squared-Lambert lane (`GcdMomentCalculus.lean`, `RepunitMobiusNumerator.lean` through `PrimePowerJumpDynamics.lean`, `MersenneLambertLadder.lean`). Each entry is a self-contained premise: exact hypotheses, exact conclusion, the coordinate it was proved in, and the Lean site. **\#249 is OPEN**; nothing below decides it. Entries labelled `consumer`-shaped (an implication whose hypothesis is an unsupplied cofinal predicate) are marked explicitly as conditional — the hypothesis itself carries <span class="sans-serif">\[Open\]</span> and is never claimed as proved. Lean site paths are relative to the public `Erdos249257/` source tree.

<a id="open-hypotheses-and-candidate-inputs"></a>

## Open hypotheses and candidate inputs

Producers conclude an existence or a supply: a witnessed object, a witnessed finite family, or an unconditional dimension/growth lower bound obtained by exhibiting witnesses (CRT, Dirichlet primes in AP, Bertrand’s postulate, explicit `decide` computation). Sorted by scale: uniform, then bounded, then fixed; no producer in this lane is cofinal (the cofinal-scale reduction theorems are consumer-shaped and are catalogued as converters below, since each moves a cofinal hypothesis across a coordinate boundary to the target conclusion).

<div class="thm">

**Theorem 52** (cert:a9 — `eventual_period_of_not_irrational`, THE TAIL-PERIOD LAW). *If $`S`$ is rational then a period exists: $`\neg\mathrm{Irrational}(S) \to \exists h:\mathbb{N},\, 0<h \wedge \exists N_0:\mathbb{N},\, \forall N\ge N_0,\ \mathrm{totientTail}(N+h) - \mathrm{totientTail}(N) \in \mathrm{range}((\uparrow):\mathbb{Z}\to\mathbb{R})`$. The witness is explicit: $`h = \varphi(\mathrm{oddPart}(r.\mathrm{den}))`$, $`N_0 = v_2(r.\mathrm{den})`$, from Euler’s theorem applied to the odd part of the hypothetical denominator.*

*<span class="sans-serif">scale:uniform</span> `coord:binary-digit`*

</div>

<div class="thm">

**Theorem 53** (cert:d5 — `not_irrational_totientSeries_implies_unbounded_carryRank_unconditional`). *$`\neg\mathrm{Irrational}(S) \to \exists v>0,\, \exists u:\mathbb{N}\to\mathbb{Z},\, \mathrm{IsTemperedBinaryOrbit}\,\varphi\,v\,u \wedge \forall e,\ 2^e-1 \le \mathrm{finrank}_{\mathbb{Q}}(\mathrm{span}(\mathrm{range}(\mathrm{canonicalCarryKernelFamily}\,u\,e)))`$. Rationality of $`S`$ forces its associated tempered integral binary-carry orbit to have unboundedly rich dyadic-section rank; this is a second, coordinate-independent necessary condition on rationality, parallel to cert:a9 but in the carry-kernel-rank coordinate rather than the binary-digit-periodicity coordinate. It is not by itself an irrationality proof. In particular, the later countermodels rule out treating generic finite-rank shift-polynomial or compressed-adjoint observations as the missing opposite inequality; an actual-totient-specific upper bound would be a genuinely new theorem, not a surviving consequence of the present rank machinery.*

*<span class="sans-serif">scale:uniform</span> `coord:other:carry-kernel-rank`*

</div>

<div class="thm">

**Theorem 54** (cert:d4 — `linearIndependent_canonicalTotientKernelFamily`). *For every $`e:\mathbb{N}`$, the canonical dyadic totient-kernel family $`\mathrm{canonicalTotientKernelFamily}(e) : \mathrm{TotientCanonicalIndex}(e) \to \mathbb{N}\to\mathbb{Q}`$, which has exactly $`2^e+1`$ channels, is linearly independent over $`\mathbb{Q}`$. Proved unconditionally by constructing, via CRT and Dirichlet’s theorem on primes in arithmetic progression (`PrimesCongruentOne`/`PrimesInAP` from Mathlib), an explicit evaluation point at which one channel becomes prime and every other channel picks up a fresh prime $`\equiv 1`$ modulo a large power of $`2`$ — a genuine witnessed producer, not merely a dimension count. Consequently $`\neg\mathrm{FiniteDimensional}\,\mathbb{Q}\,(\mathrm{span}\,\mathbb{Q}\,(\mathrm{range}\,\mathrm{fullTotientKernelFamily}))`$. Self-flagged: this shows the dyadic-kernel side is infinite-rank; it is not itself an irrationality proof.*

*<span class="sans-serif">scale:uniform</span> `coord:other:dyadic-kernel-rank`*

</div>

<div class="prop">

**Proposition 55** (cert:a8 — `tail_diff_int_of_den_dvd`). *If $`S = (r:\mathbb{R})`$ for $`r:\mathbb{Q}`$ and $`r.\mathrm{den} \mid 2^N\cdot(2^h-1)`$, then $`\mathrm{totientTail}(N+h) - \mathrm{totientTail}(N) \in \mathrm{range}((\uparrow):\mathbb{Z}\to\mathbb{R})`$: a rational value of $`S`$ with a denominator of this shape forces the shifted tail difference to be an integer. The sharp contrapositive engine underlying cert:a9 and cert:a6.*

*<span class="sans-serif">scale:uniform</span> `coord:binary-digit`*

</div>

<div class="prop">

**Proposition 56** (mob:b5 — top fibre survives, T3, `mobiusNumerator_gcd_cyclotomicValue`). *For $`r`$ squarefree: $`\gcd(|\mathrm{mobiusNumerator}(r)|,\ \mathrm{cyclotomicValue}(r)) = 1`$, hence $`\mathrm{cyclotomicValue}(r) \mid \mathrm{baseMobiusShadow}(r).\mathrm{den}`$. The top cyclotomic channel $`|\Phi_r(2)|`$ is produced as a survivor: it can never cancel from the numerator and is exhibited as an unconditional divisor of the reduced denominator at every squarefree $`r`$.*

*<span class="sans-serif">scale:uniform</span> `coord:cyclotomic`*

</div>

<div class="prop">

**Proposition 57** (mob:b6 — upper-half prime channel survival, T4). *For a scale coprime to $`C = \prod_{p \in \mathrm{upperHalfPrimes}(t)} \mathrm{mersenne}(p)`$ (or with prime support $`\le t`$), the whole finite product $`C`$ over the explicit upper-half prime set $`\mathrm{upperHalfPrimes}(t) = \{p \text{ prime} : t/2 < p \le t\}`$ divides the reduced denominator of the scaled Möbius shadow at LCM height $`t`$, unscaled. A genuine finite family of surviving Mersenne-prime channels is exhibited explicitly at every $`t`$, not merely bounded below.*

*<span class="sans-serif">scale:uniform</span> `coord:cyclotomic`*

</div>

<div class="prop">

**Proposition 58** (mob:b7a — denominator growth lower bound). *For $`t \ge 5`$ (Bertrand’s postulate supplies nonemptiness of $`\mathrm{upperHalfPrimes}(t)`$): $`2^{t/2} \le \prod_{p \in \mathrm{upperHalfPrimes}(t)} \mathrm{mersenne}(p) \le \big(\mathrm{lcmHeight}(t)\cdot\mathrm{numericMobiusShadow}(\mathrm{lcmHeight}(t))\big).\mathrm{den}`$. An exponential-in-$`t/2`$ growth lower bound for the reduced denominator at every LCM height, produced from mob:b6’s explicit surviving channel product. Denominator-only: does not by itself rule out cancellation by a foreign-defect term, hence does not by itself prove \#249.*

*<span class="sans-serif">scale:uniform</span> `coord:mobius-mersenne`*

</div>

<div class="prop">

**Proposition 59** (mob:b7b — exact denominator value). *For every $`t`$ (no lower bound on $`t`$ needed for this direction): $`\big(\mathrm{lcmHeight}(t)\cdot\mathrm{numericMobiusShadow}(\mathrm{lcmHeight}(t))\big).\mathrm{den} = \mathrm{mersenne}(\mathrm{lcmRadical}(t)) / \gcd\big(\mathrm{mersenne}(\mathrm{lcmRadical}(t)),\ \mathrm{lcmScale}(t)\cdot|\mathrm{oddJordanScalar}(\mathrm{lcmRadical}(t))|\big)`$. A fully closed form for the reduced denominator at every scale, produced (not merely bounded) as an explicit rational function of $`t`$.*

*<span class="sans-serif">scale:uniform</span> `coord:mobius-mersenne`*

</div>

<div class="prop">

**Proposition 60** (mob:d3 — signed dyadic sum nonvanishing, `scaled_dyadic_sum_ne_zero`). *If a finite signed sum $`\sum_{i \in s} u(i)\cdot 2^{e(m)-e(i)}`$ (clearing dyadic denominators to a common exponent $`e(m)`$) has one index $`m \in s`$ with strictly maximal exponent $`e(m)`$ and odd coefficient $`u(m)`$, while every other index has strictly smaller exponent, then the cleared sum is $`\equiv 1 \pmod 2`$, hence nonzero. A positive finite-nonvanishing engine, produced via a rectangular Cauchy–Binet determinant expansion (`det_mul_rectangular`) applied to the signed-Hankel/$`q`$-moment construction (`hankelDet`, `truncatedMoment`); the underlying arithmetic is a $`q=1/2`$ Hankel-determinant framework for a possible Padé route to \#249. No supply theorem is proved that such a unique-terminal configuration exists cofinally — this is a per-instance producer, not a cofinal producer.*

*<span class="sans-serif">scale:bounded</span> `coord:p-adic`*

</div>

<div class="prop">

**Proposition 61** (cert:a11 — `certifiedKill_all_small`). *$`\forall h \in [1,8],\ \mathrm{certifiedKill}\ h\ 12\ 16`$ — a finite, fully unconditional `decide`-checked family of 8 certificate witnesses at the fixed point $`N=12`$, $`L=16`$ (256 explicit totient values below 37 evaluated). Consequence, via cert:a6: $`\forall r:\mathbb{Q},\ 1\le h\le 8,\ r.\mathrm{den}\mid 2^{12}\cdot(2^h-1) \to S \ne r`$.*

*<span class="sans-serif">scale:fixed</span> `coord:other:binary-window`*

</div>

<div class="prop">

**Proposition 62** (cert:a12 — upto-sixteen deposit). *$`\forall h \in [1,16]`$, $`\mathrm{certifiedKill}\ h\ 14\ 9`$: a wider, fully unconditional `decide`-checked family of certificate witnesses. The basepoint $`N=14`$ yields the denominator factor $`2^{14}`$; the certificate depth is $`L=9`$. Consequence: $`\forall r:\mathbb{Q},\ 1\le h\le 16,\ r.\mathrm{den}\mid
2^{14}\cdot(2^h-1) \to S \ne r`$.*

*<span class="sans-serif">scale:fixed</span> `coord:other:binary-window`*

</div>

<div class="prop">

**Proposition 63** (cert:b11 — diagonal pincer finite deposits, historical bank and current band). *Let $`H_t=\operatorname{lcm}(1,\ldots,t)`$ and let
``` math
P(t)\quad:\Longleftrightarrow\quad \exists L,\ \mathrm{certifiedKill}(H_t,H_t,L).
```
The checked certificate bank proves $`P(t)`$ at 28 explicit indices, ending at $`t=64`$. For the initial indices
``` math
t=1,2,3,4,5,7,8,9,11,13,16,17,\ldots,
```
the corresponding depths begin $`6,5,7,7,9,14,15,14,21,22,23,26,\ldots`$. Each entry is a finite kernel computation on explicit totient values. The factorisations use checked prime-power blocks and Lucas primality certificates. Thus the bank proves a finite list of instances of $`P(t)`$; it does not prove that $`P(t)`$ holds for infinitely many $`t`$.*

*<span class="sans-serif">scale:fixed</span> `coord:other:lcm-diagonal`*

*The historical 28 deposits are now a strict subset of the aggregate theorem $`\forall t\le82,\ P(t)`$. That theorem closes the finite interval without holes but supplies neither $`P(83)`$ nor a cofinal family.*

*<span class="sans-serif">scale:bounded</span> `coord:other:lcm-diagonal`*

</div>

<a id="exact-identities-and-reductions"></a>

## Exact identities and reductions

Converters and identities move a statement between coordinates without changing its truth value: definitions, exact algebraic identities, iff-characterisations, and the implication theorems that convert a supply hypothesis in one coordinate into the target conclusion $`\mathrm{Irrational}(S)`$. This subsection carries the certificate-kernel core (the `Sep`(h,N,L) predicate, its completeness iff, and every known reformulation of the open supply obligation) and the Möbius–Mersenne / squared-Lambert identity family, including the Mersenne–Lambert five-row status ladder. Sorted by scale: foundational (n/a) definitions and identities first, then uniform, then cofinal, then bounded, then fixed.

<a id="foundational-definitions-and-identities-scale-na"></a>

### Foundational definitions and identities (scale n/a)

<div class="defn">

**Definition 64** (cert:a1 — `totientTail`). $`\mathrm{totientTail}(N) := \sum_{j\ge0}' \varphi(N+1+j)/2^{j+1}`$, the fractional layer of $`2^N\cdot S`$; well-defined for every $`N`$.

<span class="sans-serif">scale:n/a</span> `coord:binary-digit`

</div>

<div class="defn">

**Definition 65** (cert:a3 — `windowDiscrepancy`). $`\mathrm{windowDiscrepancy}(h,N,L) := \sum_{j<L} \big(\varphi(N+h+1+j) - \varphi(N+1+j)\big)\cdot 2^{L-1-j} \in \mathbb{Z}`$, the depth-$`L`$ truncation of $`2^L\cdot(\mathrm{totientTail}(N+h) - \mathrm{totientTail}(N))`$; computable and decidable given $`h,N,L`$.

<span class="sans-serif">scale:n/a</span> `coord:other:binary-window`

</div>

<div class="defn">

**Definition 66** (cert:a4 — `certifiedKill`, THE Sep(h,N,L) PREDICATE). $`\mathrm{certifiedKill}(h,N,L) := (N+h+L+2:\mathbb{Z}) < \mathrm{windowDiscrepancy}(h,N,L) \bmod 2^L < 2^L - (N+h+L+2)`$ — the residue of the window discrepancy modulo $`2^L`$ avoids the shrinking radius-$`(N+h+L+2)`$ neighbourhood of $`0`$. This is exactly the object named $`\mathrm{Sep}(h,N,L)`$: purely finite arithmetic, decidable, with no analytic hypothesis. This is the certificate kernel’s core object; every theorem below is either a hypothesis-shape wrapping it or an unconditional finite instance of it.

<span class="sans-serif">scale:n/a</span> `coord:other:binary-window`

</div>

<div class="prop">

**Proposition 67** (cert:a2 — shift identity, `two_pow_mul_totient_series_eq`). *$`2^N \cdot \Big(\sum_{n\ge0}' \varphi(n)/2^n\Big) = \mathrm{totientPrefix}(N) + \mathrm{totientTail}(N)`$, where $`\mathrm{totientPrefix}(N) = \sum_{n\le N}\varphi(n)\cdot 2^{N-n} \in \mathbb{N}`$ is an exact integer. Rationality/periodicity of $`S`$’s binary expansion reduces exactly to a statement about $`\mathrm{totientTail}`$. Template shape (constant $`\cdot`$ prefix + tail split) reusable for any $`\sum f(n)/2^n`$.*

*<span class="sans-serif">scale:uniform</span> `coord:binary-digit`*

</div>

<div class="lem">

**Lemma 68** (cert:a5 — certificate depth floor, `certifiedKill_depth_floor`). *$`\mathrm{certifiedKill}(h,N,L) \to 2\cdot(N+h+L+2) < 2^L`$. A structural corollary of the kernel definition: the certificate depth $`L`$ cannot stay bounded while $`N+h \to \infty`$; $`L`$ must grow at least logarithmically with $`N+h`$. Necessary context for reading every fixed/bounded-scale kernel instance below.*

*<span class="sans-serif">scale:uniform</span> `coord:other:binary-window`*

</div>

<div class="prop">

**Proposition 69** (cert:a6 — certificate soundness, the kernel’s converter direction, `tail_diff_notMem_int_of_certifiedKill`). *$`\mathrm{certifiedKill}(h,N,L) \to \mathrm{totientTail}(N+h) - \mathrm{totientTail}(N) \notin \mathrm{range}((\uparrow):\mathbb{Z}\to\mathbb{R})`$. This is the kernel’s soundness converter: it moves a finite, decidable, binary-window fact into a real-analytic non-integrality fact. Composes with cert:a9 (tail-period law) by contradiction to kill a hypothetical rational’s period.*

*<span class="sans-serif">scale:uniform</span> `coord:other:binary-window`*

</div>

<div class="thm">

**Theorem 70** (cert:a7 — certificate completeness, `exists_certifiedKill_iff_tail_diff_notMem_int`). *$`(\exists L,\ \mathrm{certifiedKill}(h,N,L)) \iff \mathrm{totientTail}(N+h) - \mathrm{totientTail}(N) \notin \mathrm{range}((\uparrow):\mathbb{Z}\to\mathbb{R})`$, for all $`h,N`$. Certificates are *complete* receipts of non-integrality, not merely sufficient: the certificate vocabulary is dispensable, and the real target of the whole kernel is exactly the right-hand real-analytic statement. Converts the open \#249 obligation freely between "supply of certificates" language and "supply of non-integral tail differences at arbitrarily large scale" language (cert:b8 below uses the latter form). Any independent non-integrality proof from any coordinate automatically yields a certificate by this iff, and vice versa.*

*<span class="sans-serif">scale:uniform</span> `coord:other:binary-window`*

</div>

<div class="defn">

**Definition 71** (cert:b1 — `periodLcm`, the universal period ray). $`\mathrm{periodLcm}(0) = 1`$, $`\mathrm{periodLcm}(t+1) = \mathrm{lcm}(\mathrm{periodLcm}(t), t+1)`$, i.e. $`\mathrm{periodLcm}(t) = \mathrm{lcm}(1,\dots,t)`$; $`t \le \mathrm{periodLcm}(t)`$; every primitive period $`h_0 \le t`$ divides $`\mathrm{periodLcm}(t)`$. Pure number theory about $`\mathrm{lcm}(1..t)`$, zero totient content; directly reusable for \#257 or any period-search problem — "stand on the universal-period ray to remove one free parameter" is a general reduction technique.

<span class="sans-serif">scale:n/a</span> `coord:other:lcm-period-ray`

</div>

<div class="prop">

**Proposition 72** (cert:c1 — `farey_gap`, the mediant lemma). *For $`a,b,c,d,r,s:\mathbb{Z}`$ with $`b>0`$, $`d>0`$, unimodular neighbours $`bc-ad=1`$, and $`r`$ strictly between $`a/b`$ and $`c/d`$ ($`a\cdot s < r\cdot b`$, $`r\cdot d < c\cdot s`$): $`b+d \le s`$. Any rational strictly between two unimodular Farey neighbours has denominator at least the sum of the neighbours’ denominators. Fully problem-agnostic — pure Stern–Brocot/Farey fact, zero totient content, directly reusable for \#257.*

*<span class="sans-serif">scale:n/a</span> `coord:farey`*

</div>

<div class="prop">

**Proposition 73** (cert:d1 — `irrational_of_den_mul_abs_sub_tendsto_zero`, generic Dirichlet-gap criterion). *If $`u:\mathbb{N}\to\mathbb{Q}`$ is eventually never equal to $`x:\mathbb{R}`$, and $`\mathrm{den}(u(k))\cdot|x - u(k)| \to 0`$, then $`\mathrm{Irrational}(x)`$. Classical Dirichlet-approximation irrationality criterion, zero totient/Mersenne content, already reused in this corpus to prove full-support Erdős–Borwein irrationality (#257-shaped). Apply to any explicit sequence of convergents to $`S`$ with a provable denominator$`\cdot`$gap $`\to 0`$ bound.*

*<span class="sans-serif">scale:n/a</span> `coord:n/a`*

</div>

<div class="prop">

**Proposition 74** (cert:d2 — `irrational_of_int_mul_near_int`, classical near-integer criterion). *If $`\forall q>0,\ \exists m,z:\mathbb{Z},\ 0 < |m\cdot\xi - z| < 1/q`$, then $`\mathrm{Irrational}(\xi)`$. The classical Erdős-1948-shape criterion behind digit/carry irrationality proofs. Base-power specialisation $`\mathrm{irrational\_of\_pow\_mul\_near\_int}`$ (witnesses of form $`b^n\cdot\xi`$) directly matches a digit/carry construction in any base $`b`$, hence directly usable for \#257’s $`b^n-1`$ denominators. Together with cert:d1 these are the only two general-purpose irrationality criteria in the whole kernel; everything else exists to supply or substitute for their hypotheses.*

*<span class="sans-serif">scale:n/a</span> `coord:n/a`*

</div>

<div class="prop">

**Proposition 75** (cert:d3 — `SeparatedMinorCertificate`, linear independence from a nonzero minor). *For an indexed family $`\mathrm{family}: \iota\to\mathbb{N}\to\mathbb{Q}`$: a $`\mathrm{SeparatedMinorCertificate}`$ (an explicit finite evaluation-point assignment $`\mathrm{rowIndex}:\iota\to\mathbb{N}`$ with $`\det(\mathrm{family}(j)(\mathrm{rowIndex}(i)))_{i,j} \ne 0`$) implies $`\mathrm{LinearIndependent}\ \mathbb{Q}\ \mathrm{family}`$. Fully generic finite-dimensional linear algebra; $`\mathrm{family}`$ is a free variable, nothing here mentions totient or Mersenne structure. Reusable for any finite-rank/linear-independence obstruction in either open problem.*

*<span class="sans-serif">scale:n/a</span> `coord:n/a`*

</div>

<div class="prop">

**Proposition 76** (cert:d9 — `positive_rational_difference_lower_bound`). *For $`\mathrm{pfx} < \mathrm{whole}:\mathbb{Q}`$ (strict): $`1/(\mathrm{whole.den}\cdot\mathrm{pfx.den}) \le (\mathrm{whole}:\mathbb{R}) - (\mathrm{pfx}:\mathbb{R})`$. A positive rational difference is bounded below by the reciprocal of the product of the two *actual* reduced denominators, not a displayed/guessed one. Fully general; feeds `prefixDenominator_shell_power_bound_of_rational_difference` and `nextSupport_power_bound_of_rational_difference`, converting any analytic upper bound on a rational gap into a denominator-growth lower bound — plug in any tail estimate from either open problem’s coordinate.*

*<span class="sans-serif">scale:n/a</span> `coord:n/a`*

</div>

<div class="prop">

**Proposition 77** (mob:a1a — the Möbius–squared-Mersenne identity). *$`S = \sum_{n\ge1} \varphi(n)/2^n = \sum_{d\ge1}' \mu(d)\cdot 2^d/(2^d-1)^2 = \tfrac12 + \sum_{d\ge1}' \mu(d)/(2^d-1)^2`$. Unconditional identity of convergent real series; this is the reduced target every Möbius–Mersenne-lane result in this catalogue feeds.*

*<span class="sans-serif">scale:n/a</span> `coord:mobius-mersenne`*

</div>

<div class="cor">

**Corollary 78** (mob:a1b — \#249 restated in the squared-Lambert coordinate). *Immediate from mob:a1a: $`\mathrm{Irrational}(S) \iff \sum_{d\ge1}' \mu(d)/(2^d-1)^2 \notin \mathbb{Q}`$. Denote the right-hand series $`L_2(\mu) := S - 1/2`$ (mob:a3 below). Every subsequent Möbius-coordinate obstruction or identity in this catalogue is measured against this exact restatement, not the original totient series.*

*<span class="sans-serif">scale:n/a</span> `coord:mobius-mersenne`*

</div>

<div class="prop">

**Proposition 79** (mob:a2 — squared-Lambert transfer engine, `tsum_lambert_linear_weight_sq_pure`). *For $`w:\mathbb{N}\to\mathbb{R}`$ with $`|w(d)| \le d`$ for $`d>0`$, and $`0 \le r < 1`$: $`\sum_{d:\mathbb{N}^+}' w(d)\cdot(r^d/(1-r^d))^2 = \sum_{n:\mathbb{N}^+}' \Big(\sum_{e\mid n} w(e)\cdot(n/e-1)\Big)\cdot r^n`$. Converts any linear-growth-bounded squared-Lambert series into a divisor-convolution power series — the single reusable brick for the whole level-2 Möbius–Lambert ladder below. Pure Dirichlet-convolution/Lambert-series algebra, no Mersenne-specific structure; instantiate at $`w = \mu, 1, \varphi`$ to obtain mob:a3–a5, and directly reusable for a weighted or squared variant of \#257’s series.*

*<span class="sans-serif">scale:uniform</span> `coord:mobius-mersenne`*

</div>

<div class="defn">

**Definition 80** (mob:a3 — $`L_2(\mu)`$ is exactly \#249). $`L_2(\mu) := \sum_{d:\mathbb{N}^+}' \mu(d)/(2^d-1)^2 = S - 1/2`$. The open \#249 atom, restated as the Möbius rung of the level-2 (squared) Lambert ladder; consequence of mob:a1a and mob:a2 at $`w=\mu`$.

<span class="sans-serif">scale:n/a</span> `coord:mobius-mersenne`

</div>

<div class="prop">

**Proposition 81** (mob:a4 — $`L_2(1)`$, the known $`q`$-zeta anchor rung, `tsum_one_div_mersenne_sq_eq_sigma_sub_tau_series`). *$`\sum_{d:\mathbb{N}^+}' 1/(2^d-1)^2 = \sum_{n:\mathbb{N}^+}' \big(\sigma(n)-\tau(n)\big)\cdot(1/2)^n = \zeta_q(2) - \zeta_q(1)`$ at $`q=1/2`$. The level-2 $`\zeta`$-rung, exactly evaluated in Lean. Irrationality of this *value* is cited (Postelmans–Van Assche $`q`$-Padé), *not* formalised — only the identity itself is machine-checked. This is the "known" sibling rung mirroring mob:a3 in the level-mirror table mob:a6.*

*<span class="sans-serif">scale:n/a</span> `coord:mobius-mersenne`*

</div>

<div class="prop">

**Proposition 82** (mob:a5 — $`L_2(\varphi)`$, the Pillai gcd-moment rung, `tsum_totient_div_mersenne_sq_eq_gcd_moment_series`). *$`\sum_{d:\mathbb{N}^+}' \varphi(d)/(2^d-1)^2 = \sum_{n:\mathbb{N}^+}' (P(n)-n)\cdot(1/2)^n`$, where $`P = \varphi * \mathrm{Id}`$ (Pillai’s gcd-sum function). Equals $`\mathbb{E}[\gcd(X,Y)]`$ for independent fair-coin waiting times $`X,Y`$ (probabilistic coordinate, mob:a7–a9). A cousin rung, not \#249 itself; status open.*

*<span class="sans-serif">scale:n/a</span> `coord:mobius-mersenne`*

</div>

<div class="obs">

*Observation 83* (mob:a6 — the level-mirror table). Level 1 ($`L(f) := \sum f(d)/(2^d-1)`$): $`L(\mu) = 1/2`$ (rational, trivial); $`L(1) = \mathcal{E}`$, the Erdős–Borwein constant (irrational, Erdős 1948, machine-checked in this kernel, cert:d7c below); $`L(\varphi) = 2`$ (rational). Level 2 ($`L_2(f) := \sum f(d)/(2^d-1)^2`$): $`L_2(\mu) = S - 1/2`$ (mob:a3, OPEN, $`=`$ \#249); $`L_2(1) = \zeta_q(2)-\zeta_q(1)`$ (mob:a4, irrational, cited); $`L_2(\varphi) = \mathbb{E}[\gcd]`$ (mob:a5, open, Pillai). At level 1 the Möbius rung is trivial and the $`\zeta`$-rung is hard; at level 2 the $`\zeta`$-rung is known and the Möbius rung *is* \#249 — Möbius projection is the single wall at both levels. This mirror-structure phenomenon is a general observation about Dirichlet-convolution ladders, potentially informative for \#257’s Mersenne-shifted sums too.

<span class="sans-serif">scale:n/a</span> `coord:mobius-mersenne`

</div>

<div class="prop">

**Proposition 84** (mob:a7 — gcd-divisibility factorises, `tsum_pos_pair_both_dvd_half_eq_inv_mersenne_sq`). *For independent fair-coin waiting times $`X,Y`$ ($`P(X=n)=2^{-n}`$) and $`d>0`$: $`P(d\mid X \wedge d\mid Y) = 1/(2^d-1)^2`$. The foundation stone for reading $`L_2(f)`$ as $`\mathbb{E}[(f*\zeta)(\gcd(X,Y))]`$. Pure probability/geometric-series fact about independent geometric random variables, zero \#249-specific content; directly reusable for a two-coordinate gcd structure in \#257.*

*<span class="sans-serif">scale:uniform</span> `coord:probability`*

</div>

<div class="prop">

**Proposition 85** (mob:a8 — reduced-direction law, `tsum_pos_coprime_inv_mersenne_eq_one`). *$`\sum_{(a,b):\, a,b\ge1,\, \gcd(a,b)=1}' 1/(2^{a+b}-1) = 1`$: the sum over exact bipartite coprime pairs. Every positive coprime pair carries a slope mass $`1/(2^{a+b}-1)`$, and these mass exactly one — the root cylinder $`M(1,1)=1`$ of the Stern–Brocot tree, mob:a9. Pure coprimality/geometric-series law, applies verbatim to any base-$`b`$ analogue.*

*<span class="sans-serif">scale:n/a</span> `coord:probability`*

</div>

<div class="prop">

**Proposition 86** (mob:a9a — Stern–Brocot cylinder recursion, `cylinderMass_split`). *$`M(a,b) := 1/\big((2^a-1)(2^b-1)\big)`$ satisfies the exact telescoping identity $`M(a,b) = 1/(2^{a+b}-1) + M(a+b,b) + M(a,a+b)`$ for $`a,b:\mathbb{N}^+`$: an exact Markov measure on the Stern–Brocot mediant tree, whose closed form is a product of two independent-coordinate divisor probabilities $`P(a\mid X)\cdot P(b\mid Y)`$ (mob:a7).*

*<span class="sans-serif">scale:uniform</span> `coord:other:stern-brocot`*

</div>

<div class="prop">

**Proposition 87** (mob:a9b — depth-$`d`$ convergence rate, `sternBrocotDepthMass_error` / `tendsto_sternBrocotDepthMass`). *Children of a Stern–Brocot cylinder carry at most $`2/3`$ of the parent’s mass; the depth-$`d`$ finite unfolding of mob:a9a converges to $`M(a,b)`$ at explicit rate $`|M(a,b) - M_d(a,b)| \le (2/3)^d\cdot M(a,b)`$. The "recursion limit $`=`$ subtree mass" identification is explicitly *not* claimed beyond this rate bound (flagged as a wave-21 gap in the source). All-left cusp cylinders $`M(N,1) = 1/(2^N-1)`$ are near-Mersenne-reciprocal, one exponential order closer to the Erdős–Borwein engine than raw $`\varphi(n)`$ coefficients — an advisory bridge candidate to Erdős-1948-style arguments, not a proved route.*

*<span class="sans-serif">scale:uniform</span> `coord:other:stern-brocot`*

</div>

<div class="prop">

**Proposition 88** (mob:b1 — repunit gcd word, T1, `mobiusNumeratorPolynomial_eq_gcdWord`). *For $`r`$ squarefree, the divisor-signed polynomial $`\mathrm{mobiusNumeratorPolynomial}(r) := \sum_{d\mid r} \mu(d)\cdot(r/d)\cdot\mathrm{spacedRepunit}(d,r/d)`$ equals $`\mathrm{gcdWord}(r)`$, whose $`X^k`$ coefficient ($`k<r`$) is $`\mathrm{gcdWordCoeff}(r,k) = (r/\gcd(r,k))\cdot\varphi(\gcd(r,k))`$, strictly positive for $`k<r`$ and zero for $`k\ge r`$. The signed repunit numerator is exactly a positive gcd word; the classical polynomial identity underlying it (signed spaced repunit $`=`$ gcd word) is base-independent, though the application here is Mersenne-specific.*

*<span class="sans-serif">scale:n/a</span> `coord:cyclotomic`*

</div>

<div class="prop">

**Proposition 89** (mob:b2 — evaluation at $`2`$ recovers the integer numerator, `mobiusNumeratorPolynomial_eval_two`). *$`\mathrm{mobiusNumeratorPolynomial}(r).\mathrm{eval}\,2 = \mathrm{mobiusNumerator}(r)`$ for $`r`$ squarefree, where $`\mathrm{mobiusNumerator}(r) := \sum_{s \subseteq \mathrm{primeFactors}(r)} (-1)^{|s|}\cdot(r/d)\cdot(\mathrm{mersenne}(r)/\mathrm{mersenne}(d))`$, $`d = \prod s`$. Bridges the polynomial (mob:b1) world to the integer arithmetic used by every denominator-survival theorem below.*

*<span class="sans-serif">scale:uniform</span> `coord:cyclotomic`*

</div>

<div class="prop">

**Proposition 90** (mob:b3 — radical shadow scale decomposition). *$`\mathrm{baseMobiusShadow}(r) := \mathrm{mobiusNumerator}(r)/(2^r-1)`$ (unscaled); $`\mathrm{numericMobiusShadow}(H) := \mathrm{baseMobiusShadow}(\mathrm{rad}(H))/\mathrm{rad}(H)`$; exactly $`H\cdot\mathrm{numericMobiusShadow}(H) = (H/\mathrm{rad}(H))\cdot\mathrm{baseMobiusShadow}(\mathrm{rad}(H))`$ for $`H>0`$. Reduced-denominator identity for the unscaled shadow: $`\mathrm{baseMobiusShadow}(r).\mathrm{den} = \mathrm{mersenne}(r)/\gcd(|\mathrm{mobiusNumerator}(r)|, \mathrm{mersenne}(r))`$ for $`r>0`$ — exact and generic, no coprimality assumed, no channel-survival hidden.*

*<span class="sans-serif">scale:uniform</span> `coord:mobius-mersenne`*

</div>

<div class="prop">

**Proposition 91** (mob:b4 — cyclotomic congruence, T2, `cyclotomic_dvd_mobiusNumeratorPolynomial_sub`). *For $`r`$ squarefree, $`m \mid r`$: $`\Phi_m \mid \big(\mathrm{mobiusNumeratorPolynomial}(r) - C(\mu(m)\cdot J_2(r/m))\big)`$ in $`\mathbb{Z}[X]`$, where $`J_2 = \mu * \mathrm{id}^2`$ is the Jordan totient. Evaluated: $`\mathrm{cyclotomicEval}(m) \mid \mathrm{mobiusNumerator}(r) - \mu(m)\cdot J_2(r/m)`$. Every cyclotomic fibre $`\Phi_m(2)`$ of the numerator is congruent to an explicit constant depending only on $`\mu(m)`$ and the Jordan totient of the cofactor. Setting $`m=r`$ gives mob:b5 (top fibre survives).*

*<span class="sans-serif">scale:uniform</span> `coord:cyclotomic`*

</div>

<div class="prop">

**Proposition 92** (mob:b8a — prime-power jump recurrence, T5, new fibre). *Adjoining a new prime $`p \nmid r`$: on a genuinely new fibre $`m\cdot p`$ (with $`m \mid r`$), $`\Phi_{mp} \mid \mathrm{mobiusNumeratorPolynomial}(rp) + \mathrm{expand}_p(\mathrm{mobiusNumeratorPolynomial}(r))`$ — the new fibre picks up a sign-flipped $`p`$-expansion of the old numerator. Holds for $`p`$ prime, $`p \nmid r`$, $`m \mid r`$; the underlying recurrence needs no squarefreeness of $`r`$.*

*<span class="sans-serif">scale:uniform</span> `coord:cyclotomic`*

</div>

<div class="prop">

**Proposition 93** (mob:b8b — prime-power jump recurrence, T5, old fibre). *Adjoining a new prime $`p \nmid r`$: on an old fibre $`m`$ (with $`m \mid r`$), $`\Phi_m \mid \mathrm{mobiusNumeratorPolynomial}(rp) - C(p^2-1)\cdot\mathrm{mobiusNumeratorPolynomial}(r)`$ — old fibres scale by exactly $`p^2-1`$. Requires $`r`$ squarefree (needed for the T2 constant-fibre step mob:b4, not for the underlying recurrence itself). An inductive tool for building explicit denominator/numerator values one prime at a time; a candidate base case for an induction proving mob:b7a/b7b’s growth bound tight.*

*<span class="sans-serif">scale:uniform</span> `coord:cyclotomic`*

</div>

<div class="prop">

**Proposition 94** (cert:d7 — the Mersenne–Lambert ladder identities). *Define $`L(f) := \sum_{n\ge1} f(n)/(2^n-1)`$ (level 1, no square). Writing $`A := \varphi*\mu`$ (the primitive Euler weight, $`\alpha`$ in prose): the Dirichlet-convolution identities $`A*\zeta = \varphi`$ and $`\varphi*\zeta = \mathrm{Id}`$ separate five exact values of $`L`$ along one ladder, each obtained by factoring $`L(f)`$ as a divisor-transform $`(f*1)`$ followed by binary evaluation, $`L(f) = \sum_n (f*1)(m)/2^m`$. $`S`$ sits inside this ladder as $`L(A)`$: this is \#249 restated in positive Erdős–Borwein form.*

*<span class="sans-serif">scale:n/a</span> `coord:mobius-mersenne`*

</div>

| Weight $`f`$ | Value $`L(f)`$ | Status |
|:---|:---|:---|
| $`\mu`$ | $`L(\mu) = 1/2`$ | rational, trivial |
| $`\varphi`$ | $`L(\varphi) = 2`$ | rational |
| $`\mathrm{Id}`$ | $`L(\mathrm{Id}) = \sum_m \sigma(m)/2^m`$ | transcendental (Nesterenko 1996, <span class="sans-serif">\[Cited\]</span>, not formalised) |
| $`1`$ | $`L(1) = \mathcal{E}`$, Erdős–Borwein constant | irrational, <span class="sans-serif">\[Lean\]</span> (`irrational_erdosBorwein_series`, |
|  |  | `CertificateKernel.lean:8007`) — matches \#257’s full-support case |
| $`A = \varphi*\mu`$ | $`L(A) = S`$ | **OPEN** — this is \#249 |

The Mersenne–Lambert ladder five-row status table (docstring @ `CertificateKernel.lean:18063--18083`, body `MersenneLambertLadder.lean`).

<div class="rem">

*Remark 95* (cert:d7 — reading the ladder). This is the single clearest bridge placing \#249 inside \#257’s native Mersenne-Lambert coordinate ($`\sum f(n)/(b^n-1)`$, here $`b=2`$): if the \#257 lane’s Mersenne-coordinate machinery (achievement sets, greedy orbits) can say anything about the sign or density structure of $`A = \varphi*\mu`$ specifically, it transfers here for free via this ladder identity. Conversely, any \#249 result about $`L(A)`$ phrased purely in Lambert-series terms (not totient terms) is directly \#257-lane-portable. The ‘evaluated’ identity confirming $`S`$’s $`\mathbb{N}`$-indexed form equals its $`\mathbb{N}^+`$/Lambert-indexed form is the one row here checked directly against source (); the body machinery in `MersenneLambertLadder.lean` establishing the other four rows was read only via this docstring and is flagged <span class="sans-serif">\[Cited\]</span>/<span class="sans-serif">\[Math\]</span> accordingly except where a specific declaration is named above.

</div>

<div class="prop">

**Proposition 96** (mob:e3 — joint-35 cone annihilator, `oldChannel_affine_moment_annihilation` / `joint35_oldChannel_zero`). *The four-vertex affine annihilator $`q(X,Y) = XY-3X-2Y+4`$ ($`q(1,1)=q(3,5)=0`$, $`q(9,25)=152`$) kills every “old” divisor channel exactly at any LCM height: for $`d\mid H`$, $`d>0`$, $`\mathrm{transportResidueKernel}(d,15H) - 3\cdot\mathrm{transportResidueKernel}(d,3H) - 2\cdot\mathrm{transportResidueKernel}(d,5H) + 4\cdot\mathrm{transportResidueKernel}(d,H) = 0`$. General form (`oldChannel_affine_moment_annihilation`): any finite affine annihilator with $`\sum c_i = 0`$, $`\sum c_i\cdot m_i = 0`$ kills every old residue channel, independent of the particular $`(3,5)`$ choice — fully coordinate-free finite linear algebra. Sharp cone radius $`19H+5L+5`$ (`sharpJoint35ConeRadius`). An unbounded certificate supply built from this (not proved) would close \#249 via the same cone-flatness route as mob:e2/cert:b6.*

*<span class="sans-serif">scale:uniform</span> `coord:other:lcm-diagonal`*

</div>

<div class="prop">

**Proposition 97** (mob:f1 — composite dilation defect identity, `supportCoeff_mul_eq_add_defect`). *For an abstract support set $`A\subseteq\mathbb{N}`$, $`\mathrm{supportCoeff}_A(n) := \#\{a\in A: a\mid n\}`$: for $`a\in A`$, $`a>0`$, $`x>0`$, $`\mathrm{supportCoeff}_A(ax) = \mathrm{supportCoeff}_A(x) + [a\nmid x] + \mathrm{compositeDilationDefect}_A(a,x)`$. On prime-only support (every element of $`A`$ prime) the defect is identically zero, recovering the classical $`\mathrm{supportCoeff}_A(px) = \mathrm{supportCoeff}_A(x) + [p\nmid x]`$. Pure divisor combinatorics over an abstract support set, no $`2^n`$-specific structure — a shared \#249/#257 substrate identity: instantiate $`A=\mathbb{N}`$ weighted by $`\varphi`$ for \#249, or $`A`$ the chosen infinite subset for \#257’s $`\sum_{n\in A}1/(2^n-1)`$.*

*<span class="sans-serif">scale:uniform</span> `coord:other:support-divisor-counting`*

</div>

<a id="cofinal-scale-converters-the-certificate-kernel-reduction-ladder"></a>

### Cofinal-scale converters — the certificate-kernel reduction ladder

Every entry in this block exposes a cofinal supply predicate and a checked route to $`\mathrm{Irrational}(S)`$. **None of the supply predicates is established.** Completeness now gives registered iff theorems for the base certificate supply and the lcm-diagonal supply; the older one-directional consumer declarations remain useful proof components but are not the full logical status.

<div class="thm">

**Theorem 98** (cert:a10 — certificate-supply iff, THE WALL). *$`\big(\forall h:\mathbb{N},\ 0<h \to \forall N_0:\mathbb{N},\ \exists N\ge N_0,\ \exists L,\ \mathrm{certifiedKill}(h,N,L)\big) \leftrightarrow \mathrm{Irrational}(S)`$. The supply side is exactly $`\mathrm{Sep}(h,N,L)`$ quantified as $`\forall h\ge1\ \forall N_0\ge0\ \exists N\ge N_0\ \exists L`$. **This supply is nowhere proved in the corpus; the iff is an exact reformulation, not progress.***

*(equivalence proved; supply <span class="sans-serif">\[Open\]</span>) <span class="sans-serif">scale:cofinal</span> `coord:other:binary-window`*

</div>

<div class="thm">

**Theorem 99** (cert:b2 — multiple-period collapse, wave-22, `irrational_totient_series_of_multiple_certificate_supply`). *$`\big(\forall h_0>0,\ \forall N_0,\ \exists m>0,\ \exists N\ge N_0,\ \exists L,\ \mathrm{certifiedKill}(m\cdot h_0, N, L)\big) \to \mathrm{Irrational}(S)`$. Weaker hypothesis than cert:a10: for every primitive period it suffices to certify *some* multiple. Proof idea (`tail_diff_mul`, telescoping an $`m\cdot h`$-difference into a sum of $`m`$ shifted $`h`$-differences) is problem-agnostic; logically equivalent-strength weakening of cert:a10, still open.*

*(implication proved; hypothesis <span class="sans-serif">\[Open\]</span>) <span class="sans-serif">scale:cofinal</span> `coord:other:lcm-period-multiple`*

</div>

<div class="thm">

**Theorem 100** (cert:b3 — lcm-diagonal iff, the canonical single-parameter form). *$`\big(\forall t_0:\mathbb{N},\ \exists t\ge t_0,\ \exists L,\ \mathrm{certifiedKill}(\mathrm{periodLcm}(t), \mathrm{periodLcm}(t), L)\big) \leftrightarrow \mathrm{Irrational}(S)`$. Standing at $`N=h=\mathrm{periodLcm}(t)`$ beats every hypothetical rational simultaneously; conversely, pointwise completeness supplies a diagonal witness already at $`t=t_0`$. **This is an exact restatement with one quantified scale $`t`$**, not progress. The finite floor is every $`t\le82`$, not a cofinal supply.*

*(equivalence proved; supply <span class="sans-serif">\[Open\]</span>) <span class="sans-serif">scale:cofinal</span> `coord:other:lcm-diagonal`*

</div>

<div class="lem">

**Lemma 101** (cert:b4 — lcm-window structure, `eq_prime_pow_of_not_dvd_periodLcm`). *For $`0<j<2t`$: if $`j \nmid \mathrm{periodLcm}(t)`$ then $`\exists`$ prime $`p,k`$ with $`j=p^k \wedge t<j`$ — below $`2t`$, every non-divisor of $`\mathrm{lcm}(1..t)`$ is a bare prime power exceeding $`t`$. Pure elementary number theory about $`\mathrm{lcm}(1..t)`$; structural input for anyone trying to search for a diagonal certificate — narrows where the "noise" in $`\varphi`$ on the window comes from.*

*<span class="sans-serif">scale:uniform</span> `coord:other:lcm-window`*

</div>

<div class="prop">

**Proposition 102** (cert:b5 — lcm-ray window totient factorisation, `totient_periodLcm_ray_split`). *On a clean divisor $`j \mid \mathrm{periodLcm}(t)`$ (every prime factor of $`j`$ still divides $`\mathrm{periodLcm}(t)/j`$): $`\varphi(q\cdot\mathrm{periodLcm}(t)+j) = \varphi(j)\cdot\varphi\big(q\cdot(\mathrm{periodLcm}(t)/j)+1\big)`$. An exact multiplicative split of window totient values into a known local part and a cofactor forced $`\equiv1`$ modulo every exhausted prime — the exact algebraic handle needed to attempt an unconditional supply proof at cert:b3.*

*<span class="sans-serif">scale:uniform</span> `coord:other:lcm-window-multiplicative`*

</div>

<div class="thm">

**Theorem 103** (cert:b6 — lcm-cone flatness law, wave-24, `rational_totient_series_forces_lcm_cone_flatness`). *$`\neg\mathrm{Irrational}(S) \to \exists t_1,\ \forall t\ge t_1,\ \forall q,m:\mathbb{N},\ 0<q \to \mathrm{totientTail}(q\cdot\mathrm{periodLcm}(t) + m\cdot\mathrm{periodLcm}(t)) - \mathrm{totientTail}(q\cdot\mathrm{periodLcm}(t)) \in \mathrm{range}((\uparrow):\mathbb{Z}\to\mathbb{R})`$. Rationality forces one fractional constant on the *entire* lcm cone $`\{k\cdot\mathrm{periodLcm}(t):k\ge1\}`$ at every scale $`t\ge t_1`$, not just the diagonal pair — a strict generalisation of cert:a9’s hypothesis-generating side. Any certificate anywhere on the cone kills \#249 (cert:b7).*

*<span class="sans-serif">scale:uniform</span> `coord:other:lcm-cone`*

</div>

<div class="thm">

**Theorem 104** (cert:b7 — cone collapse, wave-24, annihilator umbrella, `irrational_totient_series_of_lcm_cone_window_kill_supply`). *$`\big(\forall t_0:\mathbb{N},\ \exists t\ge t_0,\ \exists q,m,L:\mathbb{N},\ 0<q \wedge \mathrm{certifiedKill}(m\cdot\mathrm{periodLcm}(t),\, q\cdot\mathrm{periodLcm}(t),\, L)\big) \to \mathrm{Irrational}(S)`$. One certified kill anywhere on the two-multiplier lcm cone, at arbitrarily large $`t`$, suffices. Diagonal (cert:b3) is the cell $`q=m=1`$; $`q`$-ray steps are $`m=1`$; prime-jump pairs are $`(q,m)=(1,p-1)`$. The widest known target still logically equivalent-in-strength to cert:a10.*

*(implication proved; hypothesis <span class="sans-serif">\[Open\]</span>) <span class="sans-serif">scale:cofinal</span> `coord:other:lcm-cone`*

</div>

<div class="cor">

**Corollary 105** (cert:b8 — pure non-integrality frontier forms, no certificate vocabulary). *Diagonal: $`\big(\forall t_0,\ \exists t\ge t_0,\ \mathrm{totientTail}(2\cdot\mathrm{periodLcm}(t)) - \mathrm{totientTail}(\mathrm{periodLcm}(t)) \notin \mathrm{range}((\uparrow):\mathbb{Z}\to\mathbb{R})\big) \to \mathrm{Irrational}(S)`$; cone form is the $`(q,m)`$ generalisation identical in shape. Via cert:a7’s iff these hypotheses are *exactly* equivalent to cert:b3/cert:b7 respectively. **The frontier of \#249 stripped of certificate vocabulary**: does $`\mathrm{totientTail}(2H_t) - \mathrm{totientTail}(H_t) \notin \mathbb{Z}`$ for infinitely many $`t`$, $`H_t = \mathrm{lcm}(1..t)`$?*

*(implication proved; hypothesis <span class="sans-serif">\[Open\]</span>) <span class="sans-serif">scale:cofinal</span> `coord:other:real-analytic-nonintegrality`*

</div>

<div class="prop">

**Proposition 106** (cert:b9a — second-difference certificates, sound but measured not shallower, `second_diff_notMem_int_of_certifiedRank2Kill`). *$`\mathrm{certifiedRank2Kill}(h,N,L) \to \big(\mathrm{totientTail}(N+2h)-\mathrm{totientTail}(N+h)\big) - \big(\mathrm{totientTail}(N+h)-\mathrm{totientTail}(N)\big) \notin \mathrm{range}((\uparrow):\mathbb{Z}\to\mathbb{R})`$. Sound second-difference non-integrality via a doubled band radius. Measured cell $`(h,N)=(1,8)`$: rank-1 fires at depth 8, no rank-2 certificate exists at depth $`\le8`$, rank-2 first fires at depth 9 — a probe over $`t\le20`$ finds rank-1 at least as shallow in 30/40 cells. This route is empirically *not* a shortcut over rank-1; flagged do-not-re-attempt without new information.*

*<span class="sans-serif">scale:uniform</span> `coord:other:binary-window` (measured verdict: )*

</div>

<div class="thm">

**Theorem 107** (cert:b10a — cone non-flatness menu refuter, wave-25, sharper than pairwise, `exists_nonintegral_pair_of_coneNonflatCert`). *For a nonempty menu $`Q`$ of positive vertex multipliers with the one-sided floor $`\forall q\in Q,\ q\cdot H + L + 2 < 2^L`$ (half the pairwise floor of $`\mathrm{certifiedKill}`$): $`\mathrm{coneNonflatCert}(H,L,Q) \to \exists q_i,q_j \in Q,\ \mathrm{totientTail}(q_j\cdot H) - \mathrm{totientTail}(q_i\cdot H) \notin \mathrm{range}((\uparrow):\mathbb{Z}\to\mathbb{R})`$. Proved by an argmin/Helly-avoidance argument over one-sided arcs: if all vertices shared one fractional part, the minimal-deep-tail vertex would be a common left endpoint of every arc, which $`\mathrm{coneNonflatCert}`$ denies. Information-theoretically half the depth floor of pairwise $`\mathrm{certifiedKill}`$; the reusable combinatorial-geometry technique transplants to any modular-residue pincer with more than two points.*

*<span class="sans-serif">scale:uniform</span> `coord:other:lcm-cone-menu`*

</div>

<div class="thm">

**Theorem 108** (cert:b10b — cone non-flat supply, wave-25, `irrational_totient_series_of_lcm_cone_nonflat_supply`). *If $`\mathrm{coneNonflatCert}`$ fires (via cert:b10a) on a menu whose scale is unbounded, then $`\mathrm{Irrational}(S)`$. The sharpest known certificate-depth-reduced restatement of the wall; for $`|Q|\ge3`$ genuinely joint (menu inconsistent while every pair consistent) this is the best-known target for a search-based attempt at supplying cert:a10/cert:b3/cert:b7.*

*(implication proved; supply <span class="sans-serif">\[Open\]</span>) <span class="sans-serif">scale:cofinal</span> `coord:other:lcm-cone-menu`*

</div>

<div class="prop">

**Proposition 109** (cert:b12 — survivorKill, alternative certificate via bounded carry orbit). *$`\mathrm{survivorKill}(h,N,K) := \forall j < 2(N+h+1)+1,\ \exists i\le K,\ \mathrm{carryOrbit}(h,N,j-(N+h+1),i)`$ escapes the strip $`|\cdot|\le N+i+h+2`$. Soundness: $`\mathrm{survivorKill}(h,N,K) \to \mathrm{totientTail}(N+h)-\mathrm{totientTail}(N)\notin\mathrm{range}((\uparrow):\mathbb{Z}\to\mathbb{R})`$ — a bounded-orbit argument, alternative to cert:a4/cert:a6’s residue-window argument, exhausting all $`2(N+h+1)+1`$ integer box candidates and checking each provably escapes within $`K`$ steps. cert:a4 (window) and this (orbit) are two *independently complete* coordinates for the same non-integrality target (via cert:a7’s iff): the "enumerate all integer candidates in a shrinking box, verify each provably diverges" pattern is a general technique for irrationality-by-integer-orbit arguments.*

*<span class="sans-serif">scale:uniform</span> `coord:other:carry-orbit`*

</div>

<div class="thm">

**Theorem 110** (mob:e1 — first-harmonic norm-gap supply, `irrational_totient_series_of_first_harmonic_norm_gap`). *Hypothesis $`\mathrm{DTWFirstHarmonicNormGap} := \forall h>0,\ \forall X_0,\ \exists X\ge\max(X_0,1),\ \exists L,\ 16(2X+h+L+2)\le 2^L \wedge \big\|\sum_{N\in[X,2X)} \mathrm{windowFirstExp}(h,N,L)\big\| \le (21/25)\cdot X`$. If this holds then $`\mathrm{Irrational}(S)`$. A genuinely cofinal first-harmonic exponential-sum (Weyl-sum) cancellation statement is sufficient for \#249; unconditional companion `exists_certifiedKill_of_first_harmonic_gap` shows any constant-saving first-harmonic gap on one dyadic block forces a finite kill certificate (via $`\cos(\pi/8)>9/10`$ and a pigeonhole/averaging argument).*

*(conditional theorem proved; hypothesis <span class="sans-serif">\[Open\]</span>) <span class="sans-serif">scale:cofinal</span> `coord:binary-digit`*

</div>

<div class="thm">

**Theorem 111** (mob:e2 — prime-jump sharp-kill supply, `irrational_totient_series_of_primeJumpSharpKill_supply`). *$`\mathrm{primeJumpTailCommutator}(H,p) := D(pH) - p\cdot D(H)`$, $`D(H) = R_{2H}-R_H`$, has an exact partial/tail split with sharp radius $`3pH + (p+1)(L+2)`$ (tighter than the earlier $`4pH`$ two-cell-disjunction radius). If $`\forall t_0\, \exists t\ge t_0\, \exists p,L>0,\ \mathrm{primeJumpSharpKill}(\mathrm{periodLcm}(t), p, L)`$, then $`\mathrm{Irrational}(S)`$. One concrete deposit is proved unconditionally: $`\mathrm{primeJumpSharpKill}(12,5,15)`$, kernel-`decide`d. Proof strategy: assume $`S`$ rational $`\Rightarrow`$ cone flatness (cert:b6) $`\Rightarrow`$ contradiction via the sharp prime-jump kill.*

*(conditional theorem + <span class="sans-serif">\[Cert\]</span> witness; supply <span class="sans-serif">\[Open\]</span>) <span class="sans-serif">scale:cofinal</span> `coord:other:lcm-diagonal`*

</div>

<a id="consequence-theorems"></a>

## Consequence theorems

This subsection lists every premise in the corpus whose conclusion is *conditional* on an unsupplied hypothesis, with that hypothesis rendered in display maths so an agent can recognise it as a search target. All targets below are logically downstream of the single exact equivalence that defines the open problem:

<div id="prop:NI-01" class="prop">

**Proposition 112** (The exact target: \#249 = cofinal actual-orbit nonintegrality). *Unconditionally,
``` math
\mathrm{Irrational}\Big(\textstyle\sum_n' \varphi(n)/2^n\Big)
\iff
\forall a_0,\ \exists a \ge a_0,\ \mathtt{actualLcmTailOrbit}\ a \notin \mathrm{range}(\mathbb{Z}\to\mathbb{R}).
```
Nothing beyond a supply of the right-hand side is needed in principle; every other proposition in this subsection is a route to it. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:AR-07" class="prop">

**Proposition 113** (Short-window arithmetic-kill supply). *If
``` math
\forall a_0,\ \exists a\ge a_0,\ \exists L< 2\cdot 2^a,\quad \mathtt{LcmDiagonalArithmeticKill}(2^a,L)
```
holds, then \#249 follows (via then Prop. <a href="#prop:NI-01" data-reference-type="ref" data-reference="prop:NI-01">112</a>). The predicate is exactly the residue-band exclusion of Appendix A4/A6: $`\mathtt{lcmDiagonalArithmeticWord}`$ at scale $`2^a`$ escapes a shrinking central arc mod $`2^L`$. Only two instances are proved (Prop. <a href="#prop:SK-02" data-reference-type="ref" data-reference="prop:SK-02">118</a>’s base cases); the cofinal supply is the open trigger of the actual-orbit batch. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Open\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:SEP-03" class="prop">

**Proposition 114** (Diophantine separation supply). *If, at canonically-guarded odd ranks $`q`$, cofinally many $`a`$ satisfy
``` math
\big|\,\mathtt{actualLcmTailOrbit}\ a - z\,\big| > \tfrac{1}{32} + (\text{explicit error radius}) \qquad \forall z\in\mathbb Z,
```
then \#249 follows via the landed signed-margin producer. This restates the target as effective irrationality-measure / anti-concentration for the actual orbit rather than exact residue exclusion, using the explicit approximant of Prop. <a href="#prop:SEP-02-inv" data-reference-type="ref" data-reference="prop:SEP-02-inv">134</a>. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Open\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:TE-04" class="prop">

**Proposition 115** (One-sided top-edge residue-gap supply). *If, for the room bound of Prop. <a href="#prop:SGN-01" data-reference-type="ref" data-reference="prop:SGN-01">135</a> ($`a\ge 8`$, $`J+K+(a+6)<2\cdot2^a`$),
``` math
\mathtt{ActualLcmTopEdgeResidueGap}\ a\ J\ K\ m
\quad:\iff\quad
m\le K \ \wedge\ \big(\text{residue of }\mathtt{windowDiscrepancy}\text{ at scale }m\big)\le 2^m-(\text{room bound})
```
holds cofinally, then \#249 follows (, sufficiency at line 1260), because Prop. <a href="#prop:SGN-01" data-reference-type="ref" data-reference="prop:SGN-01">135</a>/<a href="#prop:SGN-03" data-reference-type="ref" data-reference="prop:SGN-03">136</a> already exclude the negative-side residue independently — only the positive arc needs excluding. This is a strictly *weaker* target than the old symmetric certifiedKill band and is the genuinely easier open target of the whole batch. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Open\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:TE-05" class="prop">

**Proposition 116** (The five-link equivalence chain below the residue-gap target). *Each of the following cofinal supplies is proved *sufficient* for Prop. <a href="#prop:TE-04" data-reference-type="ref" data-reference="prop:TE-04">115</a>’s target, chained in decreasing strength:
``` math
\begin{aligned}
&\mathtt{PowerTwoActualLcmTopEdgeResidueGapSupply}
 \Leftarrow \mathtt{PowerTwoAdjacentSuffixMidbandSupply}\\
&\Leftarrow \mathtt{PowerTwoOddGuardTopEdgeHalfWordBandSupply}
 \iff \mathtt{PowerTwoActualFinalTopEdgeMagnitudeSupply}\\
&\Leftarrow \mathtt{PowerTwoFlexibleActualTopEdgeMagnitudeSupply}
 \Leftarrow \mathtt{PowerTwoFlexibleActualTerminalDominanceSupply}\\
&\Leftarrow \mathtt{PowerTwoFlexibleActualTerminalCarryCorridorEscapeSupply}
\end{aligned}
```
All six named predicates are open; none is proved. Because the chain is implication-only-downward, proving the single *weakest* link (`...TerminalCarryCorridorEscapeSupply`) closes the entire cluster and hence \#249. This is the true minimal remaining target of `TotientActualLcmTopEdgeStaircase`. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Open\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:TE-06" class="prop">

**Proposition 117** (The exact closed-form escape identity). *Under integrality of the actual orbit (representative $`z`$) and the half-cell fit condition $`2(H+q+2)\le 4^q`$ ($`a\ge 8`$, room bound as above),
``` math
2\cdot \mathtt{actualOddHalfCenteredLift}\ a\ q \;=\; \mathtt{diagonalWindowIncrement}(2^a)(2q+2) \;-\; \mathtt{carryOrbit}\ H\ H\ z\ (2q+1)
```
holds *exactly*. Escaping either side of this named open interval (the “terminal/carry corridor”) is both necessary and sufficient for non-integrality at rank $`q`$ (). This is the sharpest fully explicit statement of “what remains to prove” anywhere in the batch. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:SK-02" class="prop">

**Proposition 118** (Extend the short-kill stub past $`a_0=6`$). *Currently proved only for $`a_0\le 6`$:
``` math
\forall a_0\le 6,\ \exists a\ L,\ a_0\le a\ \wedge\ L<2\cdot2^a\ \wedge\ \mathtt{LcmDiagonalArithmeticKill}(2^a)\ L.
```
The module’s own comment states plainly: “the remaining endpoint gap is now precisely the unbounded continuation beyond this finite prefix.” Supplying a single further instance at $`a_0=7`$ or $`a_0=8`$ already extends the stub and is independently interesting evidence toward Prop. <a href="#prop:AR-07" data-reference-type="ref" data-reference="prop:AR-07">113</a>’s full cofinal supply; the two base cases $`a=4,6`$ trace to /. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean (finite prefix only)\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:FR-01" class="prop">

**Proposition 119** (Fixed-rank extremal-ordering supply). *Define $`\mathtt{fixedRankSecondDifference}\ H\ j := \varphi(3H+j)-2\varphi(2H+j)+\varphi(H+j)`$. If, at $`H=\mathtt{periodLcm}(2^a)`$ and some fixed small $`j`$,
``` math
\mathtt{MiddleRankTotientExtremal}\ H\ j
\quad:\iff\quad
\varphi(2H+j)\ \text{is a strict min or max among}\ \{\varphi(H+j),\varphi(2H+j),\varphi(3H+j)\},
```
then $`\mathtt{fixedRankSecondDifference}\ H\ j\ne 0`$, with sign matching the extremum. Notably an *ordering* suffices — no quantitative gap is required. This is a genuinely different coordinate from the sliding LCM window: $`j`$ fixed and small, only three fixed ranks examined. The remaining open step is : does this ordering hold cofinally in $`a`$. <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span> `coord:other:fixed-rank-curvature`\*

</div>

<div id="prop:CP-06" class="prop">

**Proposition 120** (The directed/LCM-specialised certificate supply). *$`\mathtt{directedCertifiedKill}\ h\ N\ L`$ is sound *and complete*:
``` math
(\exists L,\ \mathtt{directedCertifiedKill}\ h\ N\ L) \iff \mathtt{totientTail}(N+h)-\mathtt{totientTail}(N)\notin \mathrm{range}(\mathbb Z\to\mathbb R),
```
exactly, no gap; and $`\mathrm{Irrational}(S)\iff \mathtt{CofinalDirectedLcmCertificateSupply}`$ (the LCM-diagonal specialisation). The asymmetric strip is a genuine finite-depth improvement over the symmetric certificate (kills $`t=3`$ at depth 6, one level earlier than the symmetric one), but the file itself notes the improvement does not turn into an independent sieve theorem: supplying the cofinal predicate is exactly as hard as \#249 itself. <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span> `coord:seam-integer`\*

</div>

<div id="prop:CP-07" class="prop">

**Proposition 121** (Pulse-restricted survivor-search supply). *Given the cofinal mod-4 pulse supply of Prop. <a href="#prop:CP-05-inv" data-reference-type="ref" data-reference="prop:CP-05-inv">142</a>, it suffices to kill only the $`2\bmod 4`$-class candidate states (a fourfold reduction of the initial search strip) at one cofinal arithmetic-pulse prime per putative period, to conclude \#249:
``` math
\mathtt{modFourPulseSurvivorKill} \implies \mathrm{Irrational}(S).
```
The reduction technique (use a cofinal totient-specific pulse to legally restrict the survivor search to one residue class mod a small modulus) transfers wherever an analogous cofinal pulse can be built on the \#257 side. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:A10" class="prop">

**Proposition 122** (The wave-21 wall: certificate supply over all periods).
*``` math
\big(\forall h\ge 1,\ \forall N_0,\ \exists N\ge N_0,\ \exists L,\ \mathtt{certifiedKill}\ h\ N\ L\big)
\iff \mathrm{Irrational}(S).
```
This is exactly the quantifier structure $`\forall h\ge1\ \forall N_0\ \exists N\ge N_0\ \exists L\ \mathrm{Sep}(h,N,L)`$. Nothing in the corpus supplies this predicate; every other reduction in Part B of the certificate bank is a logically equivalent-or-weaker reformulation of this same missing supply, never independent progress on it. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span> (equivalence; supply <span class="sans-serif">\[Open\]</span>) `coord:mobius-mersenne`\*

</div>

<div id="prop:B3" class="prop">

**Proposition 123** (Diagonal collapse — one free parameter).
*``` math
\big(\forall t_0,\ \exists t\ge t_0,\ \exists L,\ \mathtt{certifiedKill}(\mathtt{periodLcm}\,t)(\mathtt{periodLcm}\,t)\ L\big)
\iff \mathrm{Irrational}(S).
```
Standing at $`N=h=\mathtt{periodLcm}\,t`$ beats every hypothetical rational simultaneously (any $`t\ge\max(h_0,N_0)`$ serves both parameters at once), collapsing Prop. <a href="#prop:A10" data-reference-type="ref" data-reference="prop:A10">122</a>’s two unbounded parameters to one. Conversely, pointwise completeness supplies the diagonal witness at $`t=t_0`$. This is the canonical single-scale restatement, not an advance. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span> (equivalence; supply <span class="sans-serif">\[Open\]</span>) `coord:mobius-mersenne`\*

</div>

<div id="prop:B7" class="prop">

**Proposition 124** (Cone collapse — annihilator umbrella).
*``` math
\big(\forall t_0,\ \exists t\ge t_0,\ \exists q\,m\,L,\ 0<q \wedge \mathtt{certifiedKill}(m\cdot\mathtt{periodLcm}\,t)(q\cdot\mathtt{periodLcm}\,t)\ L\big)
\implies \mathrm{Irrational}(S).
```
One certified kill *anywhere* on the two-multiplier LCM cone, at arbitrarily large $`t`$, suffices; the diagonal (Prop. <a href="#prop:B3" data-reference-type="ref" data-reference="prop:B3">123</a>) is the cell $`q=m=1`$. This is the widest known target still logically equivalent-in-strength to Prop. <a href="#prop:A10" data-reference-type="ref" data-reference="prop:A10">122</a>. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Open\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:B10" class="prop">

**Proposition 125** (Menu non-flatness supply — sharper than pairwise). *For a nonempty menu $`Q`$ of positive vertex multipliers with one-sided floor $`\forall q\in Q,\ qH+L+2<2^L`$ (*half* the pairwise floor of `certifiedKill`),
``` math
\mathtt{coneNonflatCert}\ H\ L\ Q \implies \exists\, q_i,q_j\in Q,\ \mathtt{totientTail}(q_jH)-\mathtt{totientTail}(q_iH)\notin \mathrm{range}(\mathbb Z\to\mathbb R).
```
If this fires at unbounded scale over a menu with $`|Q|\ge3`$ genuinely joint (menu inconsistent while every pair is separately consistent), \#249 follows via Prop. <a href="#prop:B7" data-reference-type="ref" data-reference="prop:B7">124</a>. The argmin/Helly-avoidance proof technique is a reusable combinatorial-geometry pattern for any modular-residue pincer with more than two points. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Open\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:C2sup" class="prop">

**Proposition 126** (Unbounded Farey growth — a second independent wall). *The Farey-gap denominator bound at window $`K`$ is currently $`\sim 7.96\times10^{34}`$ at $`K=240`$ (Prop. <a href="#prop:C2-inv" data-reference-type="ref" data-reference="prop:C2-inv">150</a>). If
``` math
\sup_K\, (b+d)(K) = \infty
```
(the bound growing without limit as $`K\to\infty`$), then \#249 follows via the $`C3`$-style denominator-exclusion consumer, logically *independently* of Prop. <a href="#prop:A10" data-reference-type="ref" data-reference="prop:A10">122</a>’s certificate-supply wall. No unboundedness claim is proved or attempted in the corpus. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Open\]</span> `coord:other:farey-gap`\*

</div>

<div id="prop:D5cons" class="prop">

**Proposition 127** (Rank lower bound; the generic compression shortcut is retired). *By Prop. <a href="#prop:D4-inv" data-reference-type="ref" data-reference="prop:D4-inv">149</a>, the canonical dyadic totient-kernel family is unconditionally $`(2^e+1)`$-dimensional at every level $`e`$. Rationality of $`S`$ forces an associated tempered carry orbit with $`\mathbb Q`$-rank $`\ge 2^e-1`$ at every level (Prop. <a href="#prop:CP-02" data-reference-type="ref" data-reference="prop:CP-02">141</a>). Formally, a theorem
``` math
\text{bounding the dyadic-section rank of \emph{every} rationality-supplied tempered carry}
```
would contradict this lower bound and close \#249. The corpus supplies no such theorem or mechanism. More strongly, its compressed-adjoint impossibility result and its explicit all-horizon finite-rank shift-polynomial countermodel retire the generic finite-compression shortcut (Observation <a href="#prop:B4b-kill" data-reference-type="ref" data-reference="prop:B4b-kill">166</a>). Thus the displayed upper bound is only a logically sufficient new input, not a third live frontier and not evidence that existing rank machinery is close to a contradiction. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Open\]</span> `coord:other:carry-kernel-rank`\*

</div>

<div id="prop:B12cons" class="prop">

**Proposition 128** (Alternative coordinate: bounded carry-orbit survivor supply). *$`\mathtt{survivorKill}\ h\ N\ K`$ enumerates all $`2(N+h+1)+1`$ integer box candidates and checks each provably diverges from the strip $`|\cdot|\le N+i+h+2`$ within $`K`$ steps; soundness gives $`\mathtt{survivorKill}\ h\ N\ K \implies \mathtt{totientTail}(N+h)-\mathtt{totientTail}(N)\notin\mathrm{range}(\mathbb Z\to\mathbb R)`$, proving the *same* target as Prop. <a href="#prop:A10" data-reference-type="ref" data-reference="prop:A10">122</a>/<a href="#prop:NI-01" data-reference-type="ref" data-reference="prop:NI-01">112</a> from a different coordinate (bounded dynamics, not residue windows). Per the doctrine “obstructions are coordinate-relative,” a case hard in the window coordinate may be easy here. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:other:carry-orbit-dynamics`\*

</div>

<a id="invariants"></a>

## Invariants

Necessary conditions that any successful (or unsuccessful) approach must be consistent with — facts a solution cannot contradict, whichever way \#249 eventually resolves.

<div id="prop:AR-04-inv" class="prop">

**Proposition 129** (Exact quotient-scale digit closed form, no cleanliness hypothesis).
*``` math
\mathtt{lcmRayArithmeticLetter}\ t\ j \;=\; \mathtt{deltaTotient}(\mathtt{periodLcm}\,t)(\mathtt{periodLcm}\,t + j) \;=\; \mathtt{diagonalWindowIncrement}\ t\ j,
```
valid for *both* divisor and non-divisor offsets $`j`$, with no side condition on which primes of $`j`$ survive in $`H/j`$. Every downstream sign, positivity, or residue statement about the diagonal word must factor through this identity; it generalises the older $`\mathtt{deltaTotient\_periodLcm\_ray\_split}`$, which needed $`j`$’s primes to survive. <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:AR-03-inv" class="prop">

**Proposition 130** (Uniform $`3/4`$-density retained on rough integers). *For $`a\ge8`$, $`t=2^a`$, every prime factor of $`n>0`$ exceeding $`t`$, and $`n<2^{2\cdot2^a}`$: $`n.\mathrm{primeFactors.card} < 2^a/4`$, hence $`(3/4)\cdot n < \varphi(n)`$ over $`\mathbb Q`$. Any argument bounding $`\varphi`$ on the short window below height $`\mathtt{periodLcm}(2^a)^2`$ must respect this floor; the counting mechanism (union-bound-in-product form, then convert via $`\mathtt{Nat.totient\_eq\_mul\_prod\_factors}`$) is reusable for \#257’s Mersenne-rough objects at the analogous height. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:AR-05-inv" class="prop">

**Proposition 131** (Every short-window digit sign is fixed to $`+`$). *For $`a\ge8`$, $`0<j<2\cdot2^a`$: $`0<\mathtt{lcmRayArithmeticLetter}(2^a)\ j`$. Every coefficient of the actual diagonal word in the entire short window is strictly positive — divisor offsets via a quantitative $`H<4jc`$ bound, foreign prime powers via predecessor descent plus Prop. <a href="#prop:AR-03-inv" data-reference-type="ref" data-reference="prop:AR-03-inv">130</a>’s rough-density bracket ($`H/4<c<5H/2`$), exponent-one new primes via $`H/4<c`$. This unconditional fact (no irrationality hypothesis) is what makes every sign theorem in the batch — Prop. <a href="#prop:SGN-01" data-reference-type="ref" data-reference="prop:SGN-01">135</a> and the staircase-impossibility of Prop. <a href="#prop:TE-01-killer" data-reference-type="ref" data-reference="prop:TE-01-killer">158</a> — provable at all. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:AR-06-inv" class="prop">

**Proposition 132** (Window word = truncated discrepancy; kill $`\iff`$ certificate). *$`\mathtt{lcmDiagonalArithmeticWord}\ t\ L = \mathtt{windowDiscrepancy}(\mathtt{periodLcm}\,t)(\mathtt{periodLcm}\,t)\ L`$, and $`\mathtt{LcmDiagonalArithmeticKill}\ t\ L \iff \mathtt{certifiedKill}(\mathtt{periodLcm}\,t)(\mathtt{periodLcm}\,t)\ L`$. Any residue-band existence claim about the actual diagonal word converts directly to a $`\mathtt{certifiedKill}`$/non-integrality fact through this iff — it is the fixed bridge every consumer in this subsection implicitly uses. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:SEP-01-inv" class="prop">

**Proposition 133** (Exact global-to-local bridge).
*``` math
\mathtt{actualLcmTailOrbit}\ a \;=\; 2^H(2^H-1)\Big(\textstyle\sum_n' \varphi(n)/2^n\Big) - \big(\mathtt{totientPrefix}(2H)-\mathtt{totientPrefix}(H)\big),\quad H=\mathtt{periodLcm}(2^a).
```
Every local orbit statement is secretly a statement about the global series value minus a computable finite prefix; any rational-approximation or continued-fraction style separation argument for \#249 must express its target through this exact affine image. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:SEP-02-inv" class="prop">

**Proposition 134** (Explicit computable approximant with explicit error radius). *For all $`a,q`$: $`|\mathtt{actualLcmTailOrbit}\ a - \mathtt{actualLcmRawApprox}\ a\ q| < (2H+2q+3)/2^{2q+1}`$, where $`\mathtt{actualLcmRawApprox}\ a\ q := \mathtt{diagonalAdjacentSuffixRawBlock}(2^a,0,2q{+}1)/2^{2q+1}`$. Any separation-from-integers argument (Prop. <a href="#prop:SEP-03" data-reference-type="ref" data-reference="prop:SEP-03">114</a>) is forced to work with this finite, computable block rather than the infinite tail, at this exact error rate. <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:SGN-01" class="prop">

**Proposition 135** (Unconditional positive-sign corridor — a real theorem, not a supply). *For $`a\ge8`$, $`J+(a+6)<2\cdot2^a`$:
``` math
0 < \mathtt{totientTail}(2H+J) - \mathtt{totientTail}(H+J),\qquad H=\mathtt{periodLcm}(2^a),
```
with no irrationality hypothesis — the true, infinite, real translated tail difference is strictly positive throughout almost the entire short window, proved unconditionally from Prop. <a href="#prop:AR-05-inv" data-reference-type="ref" data-reference="prop:AR-05-inv">131</a> plus a directed one-sided tail bound. Any argument about the sign of the actual orbit (not merely its residue mod $`2^L`$) must agree with this; specialised at $`J=0`$ this gives $`0<\mathtt{actualLcmTailOrbit}\ a`$. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:SGN-03" class="prop">

**Proposition 136** (Integrality forces the exact top-edge residue — names the obstruction). *Under the room bound of Prop. <a href="#prop:SGN-01" data-reference-type="ref" data-reference="prop:SGN-01">135</a> plus $`2H+J+K+2<2^K`$: integrality of the actual orbit forces
``` math
\mathtt{windowDiscrepancy}\ H\ (H{+}J)\ K \bmod 2^K \;=\; 2^K - e
```
(the top-edge representative), provably *outside* the central arc required by $`\mathtt{directedCertifiedKill}`$. This documents precisely why the sign theorem alone cannot close \#249: any contradiction needs an independent exclusion of this specific top-edge boundary band, not a re-derivation of the carry reset. The named residue $`2^K-e`$ ($`e>0`$ small) is exactly what Prop. <a href="#prop:TE-04" data-reference-type="ref" data-reference="prop:TE-04">115</a> sets out to exclude. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:TE-02-inv" class="prop">

**Proposition 137** (Punctured staircase is pinned to the half-turn). *Under the room bound and the punctured-staircase hypothesis (all but the last letter vanish at growing dyadic weight; the last letter retained below the top-edge carry band),
``` math
\mathtt{lcmRayArithmeticLetter}(2^a)(J{+}K{-}1) = 2^{m-1} \quad\text{exactly, and}\quad 2^m < 2(2H+J+K+2).
```
The modulus must be the first dyadic scale above the room bound; any extra bit of modulus makes even the punctured route empty. Any attempt to revive a partial-staircase strategy must land exactly here. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:TE-03-inv" class="prop">

**Proposition 138** (Any certificate reduces to a two-bit test — universal normal form). *Unconditionally, for arbitrary $`h,N`$ (no totient content in the proof):
``` math
(\exists L,\ \mathtt{certifiedKill}\ h\ N\ L) \iff \mathtt{GuardCylinderWitness}\ h\ N,
```
where the witness is a logarithmic-depth socket $`(b{+}1)`$ or a two-bit mixed-guard cylinder at scale $`b=\log_2(N{+}h{+}L{+}2){+}1`$. Any certificate-search algorithm or complexity bound for either problem’s tail differences must respect this compression — an unbounded-depth search is never truly necessary once $`b`$ is fixed. <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span> `coord:seam-integer`\*

</div>

<div id="prop:FR-02-inv" class="prop">

**Proposition 139** (Primitive kernel factor of the fixed-rank curvature). *On the square-root clean window $`j^2\le2^a`$, $`a\ge4`$: $`2\varphi(j) \mid \mathtt{fixedRankSecondDifference}(\mathtt{periodLcm}(2^a))\ j`$. The exact local factor $`2\varphi(j)`$ comes from the affine-rank-3 kernel $`(1,-2,1)`$ combined with the parity of three odd rough cofactors, and is provably tight — Prop. <a href="#prop:FR-03-kill" data-reference-type="ref" data-reference="prop:FR-03-kill">159</a> shows no bare application of the kernel can force one more factor of $`2`$. Any curvature-based attack at fixed rank must land inside this exact divisibility ceiling. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span> `coord:other:fixed-rank-curvature`\*

</div>

<div id="prop:CP-01-inv" class="prop">

**Proposition 140** (Carry displacement $`\iff`$ integral tail difference — central plumbing). *For a positive-multiplier tempered totient carry $`u`$ ($`\mathtt{IsTemperedBinaryOrbit}\ \varphi\ v\ u`$, $`v>0`$):
``` math
(v:\mathbb Z)\mid u(N{+}k)-u(N) \iff \mathtt{totientTail}(N{+}k)-\mathtt{totientTail}(N)\in\mathrm{range}(\mathbb Z\to\mathbb R).
```
Every statement in this batch that converts between “carry orbit divisibility” and “real tail difference is an integer” is an instance of this identity — the underlying machinery ($`\mathtt{IsTemperedBinaryOrbit}`$, $`\mathtt{binaryCoeffTail}`$) is generic over any $`f`$ with $`f(n)\le n`$, so it transfers to \#257’s own coefficient function verbatim. <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span> `coord:seam-integer`\*

</div>

<div id="prop:CP-02" class="prop">

**Proposition 141** (What rationality does and does not buy — the exact frontier). *If $`\neg\mathrm{Irrational}(S)`$, there exist $`v>0`$ and a tempered orbit $`u`$ such that for every level $`e`$, the $`\mathbb Q`$-rank of the canonical carry-kernel-family span is $`\ge 2^e-1`$ (torsion-free rank grows exponentially in level), *yet* $`u`$’s dyadic sections are uniformly eventually periodic modulo $`v`$ ($`\mathtt{CarrySectionsEventuallyPeriodicMod}`$). Rationality buys quotient-mod-$`v`$ periodicity but does *not* buy any bound on $`\mathbb Q`$-rank — this is precisely the boundary any Mersenne-specific residue argument (mod-4 pulse, two-adic pulse) exists to cross. Proposition <a href="#prop:D5cons" data-reference-type="ref" data-reference="prop:D5cons">127</a> records the rank lower bound while explicitly retiring generic finite-rank compression as a live shortcut. <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span> `coord:other:carry-kernel-rank`\*

</div>

<div id="prop:CP-05-inv" class="prop">

**Proposition 142** (Cofinal mod-4 residue pulse — genuinely totient-specific). *For any $`h>0`$ and bound $`B`$, there is a prime $`p>B`$ with $`\mathtt{deltaTotient}(4h)\ p \equiv 2\pmod4`$, constructed via Dirichlet on $`p\equiv(3r-H)\bmod 4r`$ for a fresh prime $`r\equiv1\pmod4`$. Unlike the Mersenne-primitivity killer of Prop. <a href="#prop:CP-03-kill" data-reference-type="ref" data-reference="prop:CP-03-kill">162</a>, this *is* a genuinely totient-specific residue supplied cofinally beyond every threshold — any argument invoking Prop. <a href="#prop:CP-07" data-reference-type="ref" data-reference="prop:CP-07">121</a> inherits this as its forcing mechanism. The fresh-prime CRT template is scaled to arbitrary depth in Prop. <a href="#prop:TA-inv" data-reference-type="ref" data-reference="prop:TA-inv">143</a> below. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span> `coord:other:dirichlet-crt`\*

</div>

<div id="prop:TA-inv" class="prop">

**Proposition 143** (Arbitrary-depth zero-prefix-then-pulse construction, and its transfer). *For $`K\ge2`$, $`H>K`$, $`B`$: cofinally many primes $`p>B`$ satisfy $`p\equiv1+2^{K-1}\pmod{2^K}`$, $`2^K\mid\varphi(p{+}H)`$, and $`2^K\mid\varphi(p{-}j)\wedge2^K\mid\varphi(p{-}j{+}H)`$ for every $`1\le j<K`$ — an entire length-$`(K{-}1)`$ zero prefix followed by a half-turn terminal pulse, at arbitrary two-adic depth (Prop. <a href="#prop:CP-05-inv" data-reference-type="ref" data-reference="prop:CP-05-inv">142</a>’s $`K=2`$ case generalised to every $`K`$, via $`K{-}1`$ fresh Dirichlet primes glued by CRT). This forces
``` math
\mathtt{windowDiscrepancy}\ H\ (p{-}K)\ K \equiv 2^{K-1}\pmod{2^K},
```
and under eventual integrality transfers to $`\exists z,\ (z:\mathbb R)=\mathtt{totientTail}(p{+}H)-\mathtt{totientTail}(p)\wedge z\equiv2^{K-1}\pmod{2^K}`$. Any solution attempt must be consistent with the existence of this pulse family at every depth $`K`$. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Lean\]</span> `coord:p-adic`\*

</div>

<div id="prop:MP-01-inv" class="prop">

**Proposition 144** (Exact Möbius-inversion tail identity). *$`\mathtt{totientTail}\ N = \sum_d' \mu(d)\cdot 2^{d-r_d(N)}\big(q_d(N)/(2^d-1) + 1/(2^d-1)^2\big)`$, with $`r_d(N)=d-N\bmod d`$ (forward shift to the next multiple of $`d`$), $`q_d(N)=\lfloor N/d\rfloor+1`$ — exact, not a definition-by-subtraction from a target. Any Möbius/Lambert-series manipulation of $`\mathtt{totientTail}`$ in this batch or in \#257 factors through this identity and its fully generic regrouping primitive $`\mathtt{tsum\_lambert\_pair\_regroup\_if}`$ (proved for arbitrary weight functions $`|w(d)|\le d`$, $`|v(m)|\le m`$). <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span> `coord:cyclotomic`\*

</div>

<div id="prop:SK-01-inv" class="prop">

**Proposition 145** (The rare unconditional deposits — necessary base cases). *$`\mathtt{LcmDiagonalArithmeticKill}(2^4)\ 23`$ and $`\mathtt{LcmDiagonalArithmeticKill}(2^6)\ 93`$ are proved, routed through pre-existing compressed certificates $`\mathtt{certifiedKill\_diagonal\_t16}/\mathtt{t64}`$, giving $`\mathtt{actualLcmTailOrbit}\ 4,6\notin\mathrm{range}(\mathbb Z\to\mathbb R)`$ — the *only* two unconditional actual-orbit nonintegrality facts currently proved. Any induction or bootstrapping attempt at Prop. <a href="#prop:AR-07" data-reference-type="ref" data-reference="prop:AR-07">113</a> must reproduce these as base cases, and they double as a computational sanity check that the $`\mathtt{lcmRayArithmeticLetter}`$ machinery agrees with the older compressed-certificate route. <span class="sans-serif">scale:fixed</span> <span class="sans-serif">\[Cert\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:A5-inv" class="prop">

**Proposition 146** (Certificate depth floor). *$`\mathtt{certifiedKill}\ h\ N\ L \implies 2(N{+}h{+}L{+}2)<2^L`$. Certificate depth $`L`$ cannot stay bounded while $`N{+}h\to\infty`$: $`L`$ must grow at least logarithmically. Any complexity argument about certificate search inherits this floor, and it is exactly what Prop. <a href="#prop:TE-03-inv" data-reference-type="ref" data-reference="prop:TE-03-inv">138</a> compresses to a two-bit test at the corresponding logarithmic scale. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:seam-integer`\*

</div>

<div id="prop:A9-inv" class="prop">

**Proposition 147** (The tail-period law — necessary consequence of rationality). *$`\neg\mathrm{Irrational}(S) \implies \exists h{:}\mathbb N,\ 0<h \wedge \exists N_0,\ \forall N\ge N_0,\ \mathtt{totientTail}(N{+}h)-\mathtt{totientTail}(N)\in\mathrm{range}(\mathbb Z\to\mathbb R)`$, with explicit witnesses $`h=\varphi(\mathrm{oddPart}(r.\mathrm{den}))`$, $`N_0=v_2(r.\mathrm{den})`$ for $`S=r`$. This is the “only if” half of the master equivalence: any rationality-refutation strategy must eventually contradict *some* period $`h`$ and preperiod $`N_0`$ produced this way. Composes with Prop. <a href="#prop:AR-06-inv" data-reference-type="ref" data-reference="prop:AR-06-inv">132</a>/soundness to give Prop. <a href="#prop:A10" data-reference-type="ref" data-reference="prop:A10">122</a>. <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span> `coord:other:euler-theorem`\*

</div>

<div id="prop:B6-inv" class="prop">

**Proposition 148** (Rationality flattens the whole LCM cone). *$`\neg\mathrm{Irrational}(S) \implies \exists t_1,\ \forall t\ge t_1,\ \forall q\,m{:}\mathbb N,\ 0<q,\ \mathtt{totientTail}(q\cdot\mathtt{periodLcm}\,t + m\cdot\mathtt{periodLcm}\,t)-\mathtt{totientTail}(q\cdot\mathtt{periodLcm}\,t)\in\mathrm{range}(\mathbb Z\to\mathbb R)`$. Rationality forces ONE fractional constant on the entire cone $`\{k\cdot\mathtt{periodLcm}\,t : k\ge1\}`$ at every scale $`t\ge t_1`$, not just the diagonal pair — a strict generalisation of Prop. <a href="#prop:A9-inv" data-reference-type="ref" data-reference="prop:A9-inv">147</a>. Any certificate anywhere on the cone therefore kills \#249 (Prop. <a href="#prop:B7" data-reference-type="ref" data-reference="prop:B7">124</a>). <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:D4-inv" class="prop">

**Proposition 149** (Unconditional $`(2^e{+}1)`$-dimensional dyadic kernel — the rank floor). *The canonical dyadic-kernel family $`\mathtt{canonicalTotientKernelFamily}\ e`$ has exactly $`2^e+1`$ channels, unconditionally linearly independent for every $`e`$ (CRT + Dirichlet: one channel made prime, every other channel gets a fresh prime $`\equiv1\bmod`$ a large power of $`2`$). This is a proved fact, needing no rationality hypothesis at all, and it is the fixed lower bound that Prop. <a href="#prop:D5cons" data-reference-type="ref" data-reference="prop:D5cons">127</a> would have to contradict. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:other:carry-kernel-rank`\*

</div>

<div id="prop:C2-inv" class="prop">

**Proposition 150** (Sharp Farey rung — concrete necessary floor at $`K=240`$). *For all $`q{:}\mathbb N`$, $`0<q\le79639646646701375323355774875831053`$ ($`\sim7.96\times10^{34}`$): $`(qV)\bmod2^{240} + 243q < 2^{240}`$, where $`V`$ is the explicit committed totient residue for window $`(N,K)=(1,240)`$; this is SHARP — $`q=79639646646701375323355774875831054`$ is the exact first failing denominator (an explicit Farey mediant). Any candidate rational value for $`S`$ must have reduced denominator strictly larger than this bound (Prop. <a href="#prop:C3-inv" data-reference-type="ref" data-reference="prop:C3-inv">151</a> below). <span class="sans-serif">scale:fixed</span> <span class="sans-serif">\[Cert\]</span> `coord:other:farey-gap`\*

</div>

<div id="prop:C3-inv" class="prop">

**Proposition 151** (Denominator exclusion — headline unconditional consequence). *$`\forall p{:}\mathbb Q,\ p.\mathrm{den}\le79639646646701375323355774875831053 \implies S\ne(p:\mathbb R)`$. If $`S`$ is rational, its reduced denominator exceeds $`\sim7.96\times10^{34}`$ — an unconditional necessary condition on any hypothetical rational value, logically independent of the certificate-supply wall (Prop. <a href="#prop:A10" data-reference-type="ref" data-reference="prop:A10">122</a>); it excludes small denominators outright, without needing a period at all. <span class="sans-serif">scale:fixed</span> <span class="sans-serif">\[Lean\]</span> `coord:other:farey-gap`\*

</div>

<div id="prop:D1D2-inv" class="prop">

**Proposition 152** (The two foundational irrationality engines). *Two, and only two, general-purpose irrationality criteria exist in the kernel, and any successful proof of \#249 must ultimately instantiate one of them: (i) if $`u{:}\mathbb N\to\mathbb Q`$ is eventually never $`x`$ and $`\mathrm{den}(u_k)\cdot|x-u_k|\to0`$, then $`\mathrm{Irrational}(x)`$; (ii) if $`\forall q>0,\ \exists m,z{:}\mathbb Z,\ 0<|m\xi-z|<1/q`$, then $`\mathrm{Irrational}(\xi)`$ (with a base-power specialisation $`b^n\xi`$ matching any digit/carry construction in base $`b`$). Every certificate, cone, or Farey argument in this catalogue exists either to supply one of these two hypotheses or to substitute for them via the $`\mathtt{certifiedKill}`$ route. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:other:dirichlet-approximation`\*

</div>

<div id="prop:D7-inv" class="prop">

**Proposition 153** (S sits on the Mersenne-Lambert ladder). *Writing $`L(f):=\sum_{n\ge1}f(n)/(2^n-1)`$: $`L(\mu)=1/2`$, $`L(\varphi)=2`$ (exactly rational, machine-checked), $`L(1)=E`$ = the Erdős-Borwein constant, proved **irrational** in this same kernel; $`L(A)=S`$ for $`A=\varphi*\mu`$ is exactly \#249 restated in “positive Erdős-Borwein form,” still open; $`L(\mathrm{Id})=\sum\sigma(m)/2^m`$ is transcendental by Nesterenko 1996 (cited, not formalised). Any proof of \#249 sits on this Dirichlet-convolution ladder next to a proved irrational neighbour ($`L(1)`$) and a proved rational neighbour ($`L(\varphi)`$); this is the clearest bridge into \#257’s native Lambert-series coordinate. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean, Cited\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:D9-inv" class="prop">

**Proposition 154** (Generic rational-gap adapter). *For $`\mathtt{pfx}<\mathtt{whole}{:}\mathbb Q`$: $`1/(\mathtt{whole.den}\cdot\mathtt{pfx.den}) \le \mathtt{whole}-\mathtt{pfx}`$ (as reals). Any analytic upper bound on a totient-tail gap converts, via this lemma, into a denominator-growth lower bound extending Prop. <a href="#prop:C2-inv" data-reference-type="ref" data-reference="prop:C2-inv">150</a>’s Farey rungs without redoing the Farey-neighbour search from scratch — a clean, fully general adapter usable on either problem’s tail estimate. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:other:farey-gap`\*

</div>

<div id="prop:B11-inv" class="prop">

**Proposition 155** (Finite pincer floor — contiguous evidence through $`t\le82`$). *$`\mathtt{certifiedKill\_diagonal\_all\_imported}`$: Prop. <a href="#prop:B3" data-reference-type="ref" data-reference="prop:B3">123</a>’s predicate $`P\,t`$ holds for $`t\in\{1,2,3,4,5,7,8,9,11,13,16,17,\dots\}`$ (28 explicit cases through $`t=64`$), each a finite $`\mathtt{decide}/\mathtt{norm\_num}`$ computation on explicit $`\varphi`$ values via checked prime-power blocks with Lucas-primality certificates. The current aggregate theorem strengthens this historical list to $`\forall t\le82,\ P\,t`$, with no holes. It does *not* establish $`P\,83`$ or infinitely many $`t`$ and hence does not close Props. <a href="#prop:A10" data-reference-type="ref" data-reference="prop:A10">122</a>/<a href="#prop:B3" data-reference-type="ref" data-reference="prop:B3">123</a>/<a href="#prop:B7" data-reference-type="ref" data-reference="prop:B7">124</a>. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Cert\]</span> `coord:mobius-mersenne`\*

</div>

<div id="prop:C1-inv" class="prop">

**Proposition 156** (The fair-coin coprimality reformulation of $`S`$). *$`\#\{(a,b): a{+}b=n,\ a>0,\ \gcd(a,b)=1\}=\varphi(n)`$ for every $`n`$ (uniform, $`\varphi(0)=0`$, $`\varphi(1)=1`$ included automatically). At $`r=1/2`$, for independent fair-coin waiting times $`X,Y`$ ($`P(X{=}n)=2^{-n}`$, $`n\ge1`$): $`P(\gcd(X,Y)=1) = S - 1/2`$. \#249’s constant is, up to the additive constant $`1/2`$, a literal lattice-point probability. Any digit argument for \#249 necessarily also carries a positional meaning about visible lattice points on the addition antidiagonal — a reformulation any proof attempt should keep in view even though it is not itself a route to a proof. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:other:visible-lattice-points`\*

</div>

<a id="obstructions-and-countermodels"></a>

## Obstructions and countermodels

Adversarial constructions and no-go results, kept with the mechanism that closes each route so the machinery outlives the framing. Per the corpus’s own doctrine (project memory `feedback_invent_dont_audit`): obstructions below are coordinate-relative, and each entry names exactly which coordinate or proof-template it excludes, not the underlying object.

<div id="prop:SGN-02" class="obs">

*Observation 157* (Nonnegative-branch elimination for the true survivor). If the translated actual orbit is integral at the start of Prop. <a href="#prop:SGN-01" data-reference-type="ref" data-reference="prop:SGN-01">135</a>’s positive corridor, then for every later depth $`K`$ with room $`J{+}K{+}(a{+}6)<2\cdot2^a`$, the negated carry-orbit trajectory $`-\mathtt{carryOrbit}\ H\ (H{+}J)\ d\ K`$ is negative and is an $`\mathtt{endpointSurvivor}`$ at every depth in the corridor. This eliminates only the nonnegative branch of the true survivor’s sign — it is emphatically *not* a nonintegrality claim; spurious survivors of either sign may still exist. Any strategy hoping to conclude non-integrality purely from this sign fact fails: Prop. <a href="#prop:SGN-03" data-reference-type="ref" data-reference="prop:SGN-03">136</a> names exactly what remains. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\

</div>

<div id="prop:TE-01-killer" class="obs">

*Observation 158* (Total dyadic staircase is impossible — route-pruning). For $`a\ge8`$, room bound, and modulus wide enough ($`2H{+}J{+}K{+}2<2^m`$): $`\mathtt{ActualLcmTerminalDyadicStaircase}\ a\ J\ K\ m`$ is **false** — a terminal window where every one of the last $`m`$ letters is divisible by its own growing power of two ($`2^{r+1}\mid\text{letter}_r`$) cannot occur. The last letter would have to be positive (Prop. <a href="#prop:AR-05-inv" data-reference-type="ref" data-reference="prop:AR-05-inv">131</a>), strictly below the wide modulus, and divisible by it, forcing it to be exactly $`0`$ — contradicting positivity. **Kills outright**: any strategy aiming for total dyadic annihilation of the terminal suffix. The generic mechanism ($`0<e<2^m\wedge2^m\mid e\implies e=0`$) is reusable wherever a positive quantity is asked to vanish mod a wider-than-itself modulus. The surviving route is the *punctured* staircase (Prop. <a href="#prop:TE-02-inv" data-reference-type="ref" data-reference="prop:TE-02-inv">137</a>) or the residue-gap producers (Prop. <a href="#prop:TE-04" data-reference-type="ref" data-reference="prop:TE-04">115</a>). <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\

</div>

<div id="prop:FR-03-kill" class="obs">

*Observation 159* (The bare 3-rank kernel is exactly tight — a sharpness no-go). $`\mathtt{fixedRankSecondDifference}(2^{n+1}\cdot2)(2^{n+1}\cdot3) = -2^{n+1}`$ exactly, for all $`n`$ (a closed-form computed fixture). The two-adic valuation gained by Prop. <a href="#prop:FR-02-inv" data-reference-type="ref" data-reference="prop:FR-02-inv">139</a> is exactly tight — the normalised $`1{\times}1`$ minor is odd at every depth, so the bounded-height primitive kernel alone can **never** force one additional factor of $`2`$. **Kills**: any attempt to squeeze more $`2`$-adic information out of the bare 3-rank curvature kernel; further progress needs new arithmetic input, matching the file’s own open target $`\mathtt{PowerTwoLcmMiddleRankExtremalSupply}`$. <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Cert\]</span> `coord:other:fixed-rank-curvature`\

</div>

<div id="prop:CM-01" class="obs">

*Observation 160* (The parity coboundary countermodel object). $`\mathtt{parityCoboundaryWeight}\ n := \mathtt{parityBaseWeight}\ n + 2\cdot\mathtt{largePowerTwoBit}\ n - 4\cdot\mathtt{largePowerTwoBit}(n{-}1)`$, where $`\mathtt{parityBaseWeight}`$ is the eventually-constant word $`0,1,1,2,4,4,4,\dots`$ and $`\mathtt{largePowerTwoBit}\ n=1`$ iff $`n=2^{k+3}`$ (lacunary spikes starting at $`8`$). This is a hand-built adversary sequence containing *no* $`\varphi`$ in its definition at all except via its parity. The construction technique — add a zero-valued sparse binary coboundary $`2\cdot2^{-m}-4\cdot2^{-(m+1)}=0`$ at lacunary ranks to an eventually-periodic base word, destroying periodicity while preserving the rational sum — is a completely general recipe, directly portable to an analogous \#257 adversary matched to $`1/(2^n-1)`$-parity patterns. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:other:binary-digit`\

</div>

<div id="prop:CM-02" class="obs">

*Observation 161* (What the countermodel refutes — the flagship kill of the batch). There is $`c{:}\mathbb N\to\mathbb N`$ with: (a) arbitrarily many, arbitrarily-separated, cofinal explicit “$`6,0`$” carry pairs (for every $`N,G,K`$ a block of $`K`$ such pairs beyond $`N`$, pairwise separated by $`>G`$); (b) $`\forall n,\ c(n)\le6`$; (c) $`\forall n,\ c(n)\le n`$; (d) $`\forall n,\ c(n)\equiv\varphi(n)\pmod2`$ (exact parity agreement with Euler’s totient); (e) $`c`$ is **not** eventually periodic; yet (f) $`\sum_n' c(n)/2^n = 3/2`$, a *rational* number.

**Kills**: any \#249 proof strategy whose only inputs are uniform boundedness, the trivial growth bound $`c(n)\le n`$, exact $`\varphi`$-parity agreement, and failure of eventual periodicity — *even strengthened* to cofinal, arbitrarily-separated, arbitrarily-long-block non-periodicity. The obstruction is structural, not a shortage of non-periodicity witnesses: a rational coboundary can carry unlimited *visible* aperiodic structure while summing to a fixed rational.

**Doctrine consequence** (matches project memory `feedback_erdos_reductions_rejected_bank_real_results`): only arguments using actual quantitative totient/Mersenne size or residue information (as in the $`\mathtt{TotientActualLcm}\ast`$/$`\mathtt{TotientFixedRank}\ast`$ families) can possibly close \#249; pure symbolic-word arguments cannot. This countermodel is also the ready-made stress-test fixture for any future sufficient-condition candidate stated purely in coefficient-word terms (boundedness/growth/parity/periodicity), on either \#249 or \#257. <span class="sans-serif">scale:cofinal</span> <span class="sans-serif">\[Cert\]</span> `coord:other:binary-digit`\

</div>

<div id="prop:CP-03-kill" class="obs">

*Observation 162* (Primitive Mersenne-prime factors alone force nothing). For the completely-multiplicative control $`c(n)=n`$ (zero totient content: $`\mathtt{binaryCoeffTail}\ \mathrm{id}\ N = N{+}2`$): if $`q>K>0`$ and $`q\mid2^K-1`$ (e.g. $`q`$ a primitive prime factor of the homogeneous Mersenne multiplier), the shift is integral at every $`N`$ (value exactly $`K`$) but $`q\nmid K`$. **Kills**: “a large primitive Mersenne prime factor alone forces a contradiction” as a proof strategy — this is a route-pruning warning applicable *verbatim* to \#257, whose denominators $`2^n-1`$ are literally the object $`q\mid2^K-1`$ tested here. Any successful use of such a factor needs genuinely totient-specific residue/size input beyond bare Mersenne primitivity — contrast with the genuinely totient-specific pulse of Prop. <a href="#prop:CP-05-inv" data-reference-type="ref" data-reference="prop:CP-05-inv">142</a>. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\

</div>

<div id="prop:CP-04-kill" class="obs">

*Observation 163* (Universal no-go for absolute-adjugate coefficient reconstruction). For any finite rational row $`w{:}\iota\to\mathbb Q`$, integer targets $`x{:}\iota\to\mathbb N`$ that *exactly* isolate one totient channel ($`\sum_i w_i\varphi(x_i)=1`$): the crude two-tail cost $`\sum_i|w_i|\cdot(2(x_i{+}1)+(x_i{+}2))`$ is $`\ge3`$, hence never $`<1`$. **Kills**: the strategy of recovering $`\varphi(x)`$ from $`2R_{x-1}-R_x`$ and bounding each tail termwise by $`R_M\le M{+}2`$ — it can *never* reach the strict $`<1`$ tail-error threshold, at any finite grid height, independent of matrix height, row translation, determinant, or target channel. The proof only uses $`\varphi(x)\le x`$, so the same triangle-inequality floor transfers verbatim to any \#257 reformulation with $`c(n)\le n`$. <span class="sans-serif">scale:uniform</span> <span class="sans-serif">\[Lean\]</span> `coord:other:adjugate-linear-algebra`\

</div>

<div id="prop:B9cert-kill" class="obs">

*Observation 164* (Rank-2 second-difference certificates: sound but measured not shallower). $`\mathtt{certifiedRank2Kill}\ h\ N\ L \implies`$ the second difference $`(\mathtt{totientTail}(N{+}2h){-}\mathtt{totientTail}(N{+}h)) - (\mathtt{totientTail}(N{+}h){-}\mathtt{totientTail}\,N) \notin\mathrm{range}(\mathbb Z\to\mathbb R)`$, sound at doubled band radius versus rank 1. Measured at $`(h,N)=(1,8)`$: rank-1 fires at depth 8, no rank-2 certificate exists at depth $`\le8`$, rank-2 first fires at depth 9 — empirically **not** a shortcut over rank-1 (rank-1 at least as shallow in $`30/40`$ probed cells for $`t\le20`$). **Kills**: expecting a depth improvement from moving to second differences. Explicitly flagged as a dead end — do not re-attempt this exact refinement without new information. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Cert\]</span> `coord:mobius-mersenne`\

</div>

<div id="prop:D8cert-kill" class="obs">

*Observation 165* (Unit-gap strengthening rescues at most one lattice point). $`\mathtt{ReducedDenominatorUnitGapCert}\ u\ N\ K := \forall t\in[1,L],\ \neg\mathrm{Coprime}(J{+}t,u)`$ (nonunits-only refinement of the Farey-gap consumer). At a prime-power reduced denominator $`p^e`$: $`\mathtt{ReducedDenominatorUnitGapCert}(p^e)\ N\ K \iff L{=}0 \vee (L{=}1\wedge p\mid(J{+}1))`$ — the unit-gap strengthening can rescue **at most one** additional candidate lattice point beyond the ordinary Farey-gap certificate. **Kills**: expecting this refinement to unboundedly strengthen Prop. <a href="#prop:C2-inv" data-reference-type="ref" data-reference="prop:C2-inv">150</a>/<a href="#prop:C3-inv" data-reference-type="ref" data-reference="prop:C3-inv">151</a>’s Farey rungs — it is self-flagged in its own docstring as “a strict certificate-level strengthening, not a supply theorem.” A known dead end; do not re-attempt expecting more than $`+1`$ lattice point per prime power. <span class="sans-serif">scale:bounded</span> <span class="sans-serif">\[Lean\]</span> `coord:other:farey-gap`\

</div>

<div id="prop:B4b-kill" class="obs">

*Observation 166* (Synthetic all-horizon countermodel to homogeneous-factor-only proof strategies). There is an explicit nonzero “all-horizon countermodel” sequence built from multiples of $`\varphi(\mathtt{periodLcm}\,t)`$ that (i) agrees with every exact whole-ray anchor $`\mathtt{deltaTotient}\ H\ (qH)=\varphi(H)`$ for $`2\le q<t`$; (ii) stays inside the natural diagonal bounds; and (iii) **survives every finite integer shift polynomial** — every commensurate finite-rank LCM cube, via the normal form $`P_m(E_H)\cdot\prod(E_H^n-1)`$. Explicitly flagged synthetic: it does not claim the compensation letters occur as actual totient differences. **Kills**: the strategy of “retain only homogeneous LCM-ray factors” at *every* finite rank, not just rank 2 or 3. This is a representation-level exclusion (a particular factor-ideal projection throws away information that can be adversarially reconstructed), not an exclusion of $`\varphi`$ itself — an actual proof must control the fresh Möbius channel, per $`\mathtt{totient\_eq\_sum\_mobiusTotientChannel}`$ in the same file. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean (docstring-sourced)\]</span> `coord:mobius-mersenne`\
and

</div>

<div id="prop:B5-kill" class="obs">

*Observation 167* (Fixed-precision local valuation-unit signatures never obstruct). For any finite word of odd-valuation-unit symbols at fixed local $`2`$-adic precision $`u>0`$, and any starting carry state $`e`$, there **exists** a compatible carry orbit realising that exact word with every intermediate state centred in its dyadic interval ($`|e'|\le\mathtt{vuRadius}\ u\ \sigma`$). **Kills**: any proof strategy trying to derive a contradiction purely from “the local valuation-unit signature at fixed precision $`u`$ is incompatible with $`X`$” — such signatures are *always* realisable by some carry orbit. Framed against \#249 in the docstring, but the theorem itself carries no totient- or Mersenne-specific content: a proof needs growing precision or extra arithmetic coupling, not a fixed-window local signature. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:p-adic`\

</div>

<div id="prop:B8-kill" class="obs">

*Observation 168* (Square-CRT correction-suppression is independent of nonvanishing). Square-CRT correction suppression (fixing a cofactor mod a prime square to remove a weighted correction term on a finite horizon) is achievable, **but** suppression alone does not force a nonzero coefficient: the smallest returned countermodel has the whole two-step finite block vanish identically, while a separate clean witness shows it can also be nonzero — “clean” (correction-suppressed) is consistent with *both* vanishing and nonvanishing. **Kills**: “achieve a clean square-CRT horizon” as a sufficient condition by itself for a nonvanishing correction term; an additional anti-concentration or residue producer is still needed, exactly as the module’s own docstring states. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean (docstring-sourced)\]</span> `coord:other:square-crt-cocycle`\

</div>

<div id="prop:D6-kill" class="obs">

*Observation 169* (No fixed integer clears every normalised primitive-Euler coordinate). $`\forall D>0,\ \neg\forall n>0,\ \exists z{:}\mathbb Z,\ D\cdot(A(n)/n)=z`$, where $`A=\varphi*\mu`$ is the Mersenne-Lambert primitive weight (so $`S=L(A)`$, Prop. <a href="#prop:D7-inv" data-reference-type="ref" data-reference="prop:D7-inv">153</a>). Any $`D`$ clearing normalised coordinates through horizon $`N`$ must be divisible by every odd prime $`p\le N`$, every $`p^2\le N`$, and by $`4`$ once $`N\ge4`$ — so no fixed $`D`$ works for all $`n`$. **Kills**: any strategy seeking a single fixed integer denominator that simultaneously integralises every primitive-Euler coordinate $`A(n)/n`$ — a finite no-lift theorem in the integral Euler/Witt-coordinate category (weaker than the general Dieudonné-Dwork theorem, and explicitly *not* itself an irrationality proof). An independent-coordinate no-go, orthogonal to the binary-window (Prop. <a href="#prop:A10" data-reference-type="ref" data-reference="prop:A10">122</a>) and carry-rank (Prop. <a href="#prop:D5cons" data-reference-type="ref" data-reference="prop:D5cons">127</a>) obstructions — a third distinct coordinate attacking the same open problem. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean\]</span> `coord:mobius-mersenne`\

</div>

<div id="prop:B11cert-kill" class="obs">

*Observation 170* (Finite certificates only ever prove exclusion, never membership). Certified-death/kill families (finite decidable checks at a given depth) are explicitly **one-sided**: a found certificate proves exclusion, but failure to find one, or survival through any finite probed depth, proves *nothing* about membership or rationality. This is a structural caveat recurring across every certificate family in this catalogue ($`\mathtt{certifiedKill}`$, $`\mathtt{directedCertifiedKill}`$, $`\mathtt{survivorKill}`$, $`\mathtt{LcmDiagonalArithmeticKill}`$): none of them can ever certify membership/rationality by finite search, only non-membership/non-integrality. **Kills**: treating an unsuccessful finite search over any of the certificate families above as evidence toward rationality, or treating a finite prefix of confirmed kills (Prop. <a href="#prop:SK-01-inv" data-reference-type="ref" data-reference="prop:SK-01-inv">145</a>, Prop. <a href="#prop:B11-inv" data-reference-type="ref" data-reference="prop:B11-inv">155</a>) as anything more than a floor to extend. <span class="sans-serif">scale:n/a</span> <span class="sans-serif">\[Lean (structural caveat, cross-problem)\]</span> `coord:n/a`\

</div>

<a id="recently-added-declarations"></a>

## Recently added declarations

This subsection catalogues material that entered the public record after the rest of this paper was drafted: declarations union-merged into modules that were already public (`SignedQMomentObstruction`, `GenericTailOrbitRigidity`, `DiagonalFreshLossBridge`, `SquaredMersenneDiagonalEnclosure`, `ActualForeignResidueProjection`, `DyadicPrefixCompression`, `RepunitMobiusNumerator`, `GeometricCoprimality`, `LcmDiagonalReduction`, `PivotAntiReconstruction`, all in `Erdos249257/`), and the newly published per-problem tree `ErdosProblems/Erdos249/`. Every declaration below was read directly from source; none is inferred from a name. Several of these files contain long chains of “`XSupply` $`\to`$ irrational” implications whose hypothesis is an unproved cofinal predicate. Per the standing rule of this paper, those chains are named as exactly what they are — reductions, not results — and are not restated as if they narrowed the open problem. The module `SquareCRTCube` is deliberately excluded: its private additions did not compile even in the private tree and were reverted, so nothing from it beyond the existing public file is cited here.

<a id="the-möbiusmersenne-ladder-unconditional-log-concavity"></a>

### The Möbius–Mersenne ladder: unconditional log-concavity

`SignedQMomentObstruction` adds an infinite ladder $`\Theta_r := \sum_{n\ge 0} \mu(n+1)/(2^{n+1}-1)^r`$ built from the same Möbius–Mersenne atoms as the rest of the corpus, together with a full unconditional order-two Hankel (log-concavity) theorem for every rung.

<div class="defn">

**Definition 171**. $`\Theta_r := \sum_{n\ge 0}\mu(n+1)/(2^{n+1}-1)^r`$, split exactly into the first two atoms $`\mathrm{TwoAtom}(r) := 1 - 3^{-r}`$ and the tail $`\mathrm{TailAfterTwo}(r) := \sum_{n\ge 0}\mu(n+3)/(2^{n+3}-1)^r`$. `coord:mobius-mersenne`.

</div>

<div class="thm">

**Theorem 172** (Two low rungs are exact rationals tied to \#249). *$`\Theta_1 = 1/2`$, and $`\Theta_2 = \bigl(\sum_{n\ge 1}\varphi(n)2^{-n}\bigr) - 1/2`$ — the second rung is literally $`S - 1/2`$. `coord:mobius-mersenne`.*

</div>

<div class="thm">

**Theorem 173** (Two-atom exact Hankel gap). *$`\mathrm{TwoAtom}(r{+}1)^2 - \mathrm{TwoAtom}(r)\mathrm{TwoAtom}(r{+}2) = 4/3^{r+2}`$, hence the two-atom truncation alone is strictly log-concave at every $`r`$. `coord:mobius-mersenne`.*

</div>

<div class="thm">

**Theorem 174** (Full ladder: unconditional strict log-concavity, every rung). *For every $`r\ge 1`$, $`\Theta_r\,\Theta_{r+2} < \Theta_{r+1}^2`$: the shifted $`2\times 2`$ Hankel determinant of the whole ladder is negative at every rung, not just asymptotically. The proof propagates the exact two-atom gap above against a geometric tail-error budget that contracts by a factor $`1/4`$ per rung against a gap that only contracts by $`1/3`$, giving an inductive floor from rung $`5`$ on (kernel-checked base cases below). `coord:mobius-mersenne`.*

</div>

<div class="obs">

*Observation 175*. This is a genuine unconditional analytic fact about the ladder, but it is not by itself an irrationality obstruction or a step toward one: negative Hankel determinants say the sequence $`(\Theta_r)`$ is not the moment sequence of a positive measure, which is unrelated to whether any single $`\Theta_r`$ (in particular $`\Theta_2 = S - 1/2`$) is rational. It is recorded here as exactly what it is — a structural fact about the ladder — and no stronger claim is made.

</div>

The file also supplies the underlying algebraic infrastructure: a rectangular Cauchy–Binet expansion derived from the Leibniz formula (, <span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:uniform</span>, `coord:other:hankel-determinant`, needed because Mathlib’s pinned determinant API does not expose rectangular Cauchy–Binet directly), and a finite unique-terminal-dyadic-exponent parity lemma showing that clearing a common denominator by its uniquely largest power of two preserves oddness of the numerator (, <span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:uniform</span>, `coord:other:dyadic-parity`).

<a id="generic-tail-orbit-rigidity-a-self-labelled-non-claim"></a>

### Generic tail-orbit rigidity: a self-labelled non-claim

`GenericTailOrbitRigidity` is explicit in its own header that it asserts no novelty and no priority, and contains an explicit `NON_CLAIM` guard against a superseded “positive orbit” route; it is a formal algebra/analysis interface, reproduced here only because it entered the public tree after the earlier parts of this paper were drafted.

<div class="thm">

**Theorem 176** (T7: tempered-orbit equivalence, abstract binary series). *For any $`c:\mathbb{N}\to\mathbb{N}`$ with $`c(n)\le n`$, writing $`X_c := \sum_{n\ge 1} c(n)/2^n`$, $`X_c`$ is rational iff there exist $`v>0`$ and an integer sequence $`u`$ with $`u(N{+}1) = 2u(N) - v\,c(N{+}1)`$ and $`u(N)/2^N \to 0`$; when it exists such an orbit is rigid, $`u(N) = v\cdot T_c(N)`$ for every $`N`$, where $`T_c`$ is the scaled tail. `coord:other:tail-orbit-rigidity`.*

</div>

<div class="prop">

**Proposition 177** (Rigidity engine). *A real sequence $`d`$ with $`d(N{+}1)=2d(N)`$ and $`d(N)=o(2^N)`$ is identically zero. `coord:other:tail-orbit-rigidity`.*

</div>

<div class="obs">

*Observation 178* (Finite-state no-go for successor decoders). For fixed $`m\ge 2`$, the “balanced-pulse” family $`c_{m,r}`$ (mass $`r`$ moved from digit $`m`$ to digit $`m{+}1`$, $`0\le r\le
\lfloor(m{+}1)/2\rfloor`$) has the same value and the same complete pre-$`m`$ history for every $`r`$, yet the parameter $`r`$ is recovered exactly from the first post-pulse digit. Consequently no state that identifies all members of one such family can be decoded by any autonomous map, and the fan-out of any correct decoder is unbounded in $`m`$. `coord:other:tail-orbit-rigidity`. This is a genuine barrier of the class the brief asks for: it rules out exactly the class of arguments that try to predict/decode the exact tail orbit from a state depending only on the pre-pulse history, because the family exhibited is a literal counterexample generator for any such decoder. It says nothing about the totient-specific series itself.

</div>

Two “rational control models” are included as honesty checks, not irrationality statements: the pair-balanced family $`c(2k){=}k{-}a(k)`$, $`c(2k{+}1){=}2a(k)`$ has tempered orbit for every bounded payload $`a`$ and a fixed marked value $`4/9`$ regardless of $`a`$ (, <span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:uniform</span>, `coord:other:tail-orbit-rigidity`); and the identity coefficients $`c(n)=n`$ have the explicit multiplier-one tempered orbit $`u(N)=N+2`$ (, <span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:fixed</span>, `coord:other:tail-orbit-rigidity`).

<a id="squared-mersenne-diagonal-enclosure"></a>

### Squared-Mersenne diagonal enclosure

`SquaredMersenneDiagonalEnclosure` spends the exactly-summable first-order Lambert term of the actual \#249 diagonal exactly, leaving only a squared-Mersenne tail to bound.

<div class="prop">

**Proposition 179** (Exact rational centre, direct). *$`\mathrm{scaleDiagonalTailDifference}(H) - \mathrm{lambertProjectedDiagonal}(H,D)
= C_H \cdot \mathrm{mobiusSquareTail}(D)`$ for every $`H,D`$ — no residue split and no side condition on $`D`$ versus $`H`$. `coord:other:squared-mersenne-tail`.*

</div>

<div class="prop">

**Proposition 180** (Sharp geometric tail bound). *$`|\mathrm{mobiusSquareTail}(D)| \le 4/\bigl(3(2^{D+1}-1)^2\bigr)`$. `coord:other:squared-mersenne-tail`.*

</div>

<div class="obs">

*Observation 181* (Directed vs. symmetric enclosure). When the first nonzero Möbius channel past $`D`$ is known, its sign directs a one-sided interval half the width of the symmetric bound (, <span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:uniform</span>, `coord:other:squared-mersenne-tail`), and either enclosure composes with an integer-lattice separation hypothesis into a consumer theorem (). The separation hypothesis itself is exactly the remaining open content; the enclosure is real but does not supply it.

</div>

<a id="oldforeign-möbius-channel-split-diagonalfreshlossbridge"></a>

### Old/foreign Möbius channel split (DiagonalFreshLossBridge)

The 4243-line addition to `DiagonalFreshLossBridge` isolates, at the level of individual Möbius-totient channels, which channels are “old” (index divides the LCM height $`H`$) and which are “foreign” (index does not), and proves exact identities for both. Most of the file’s bulk beyond what is recorded here is a long ladder of `...Supply`-conditional “$`\Rightarrow`$ irrational” implications at successively more specialised hypotheses; those are reductions and are not restated as results.

<div class="prop">

**Proposition 182** (Exact old-channel value: a positive gcd word, scaled). *For $`H>0`$, the sum of totient forward-differences over exactly the divisor channels of $`H`$ equals $`(H/\mathrm{rad}(H))\cdot\mathrm{gcdWordCoeff}(\mathrm{rad}(H),s)`$, where $`\mathrm{gcdWordCoeff}`$ is the positive gcd-word coefficient of §<a href="#repunit-gcd-word" data-reference-type="ref" data-reference="repunit-gcd-word">6.6.5</a> below. `coord:other:gcd-word`.*

</div>

<div class="prop">

**Proposition 183** (Exact old/foreign split of the diagonal height increment). *$`\mathrm{diagonalHeightIncrement}(H,s) = \mathrm{oldMobiusIncrement}(H,s) +
\mathrm{finiteForeignChannelIncrement}(H,s)`$, a literal finite-sum identity, not an estimate. `coord:other:gcd-word`.*

</div>

<div class="thm">

**Theorem 184** (Exact doubling law for the old-channel increment). *If $`H`$ and $`r`$ are both even, $`\mathrm{diagonalHeightIncrement}(2H,2r) =
2\cdot\mathrm{diagonalHeightIncrement}(H,r)`$; if $`H`$ is even and $`r`$ odd, the same doubled height increment equals $`\mathrm{diagonalHeightIncrement}(H,r)`$ unchanged. `coord:other:gcd-word`.*

</div>

<div class="obs">

*Observation 185* (Every nonzero foreign phase term is squarefree-supported). A “foreign” channel $`d\nmid H`$ contributes a nonzero phase term to the literal increment only if $`d`$ is squarefree and $`d`$ divides exactly one of the two window endpoints $`2H{+}s`$, $`H{+}s`$ (never both, since $`d\nmid H`$ forces the two endpoints incongruent mod $`d`$). `coord:other:gcd-word`. This is a real structural narrowing — it rules out non-squarefree indices and simultaneous double support as sources of foreign contribution — but it narrows a finite bookkeeping decomposition, not the analytic separation obligation itself.

</div>

<div class="prop">

**Proposition 186** (Low/top echo doubling). *If a foreign channel $`d`$ has a lower-endpoint hit at offset $`s`$, its value there is $`-\mu(d)\cdot\lfloor(H{+}s)/d\rfloor`$, and its top-endpoint value at the doubled offset $`2s`$ is exactly twice that quantity in absolute value (with sign flipped): $`\mathrm{foreignChannelPhaseTerm}(d,H,2s) =
2\bigl(\mu(d)\lfloor(H{+}s)/d\rfloor\bigr)`$. `coord:other:gcd-word`.*

</div>

<a id="repunit-gcd-word"></a>

### Repunit Möbius numerator is a positive gcd word (T1)

<div class="thm">

**Theorem 187** (T1). *For squarefree $`r`$, the signed repunit numerator polynomial $`\sum_{d\mid r}\mu(d)(r/d)(1+X^d+\cdots+X^{r-d})`$ equals the “gcd word” whose coefficient at $`X^k`$ ($`k<r`$) is $`(r/\gcd(r,k))\cdot\varphi(\gcd(r,k))`$ — strictly positive for $`k<r`$, zero for $`k\ge r`$. The squarefree hypothesis is kept explicit and is not promoted to arbitrary $`r`$. `coord:other:gcd-word`.*

</div>

<div class="cor">

**Corollary 188**. *Evaluation at $`X=2`$ recovers the integral Möbius–Mersenne numerator already owned by `RadicalMobiusShadow`, on the same squarefree boundary. `coord:other:gcd-word`.*

</div>

<a id="dyadic-prefix-compression-exact-greedy-carry-arithmetic"></a>

### Dyadic prefix compression: exact greedy-carry arithmetic

`DyadicPrefixCompression` adds roughly 3200 lines of exact-arithmetic infrastructure for a greedy half-orbit carry construction (Mersenne-weight achievement sets); the bulk is machinery for a specific producer hypothesis. Two pieces of genuinely reusable exact arithmetic:

<div class="defn">

**Definition 189**. For a displayed residual $`p/(2L)`$, the integer excess numerator above the next dyadic point $`2^{-(n+1)}`$ is $`\mathrm{nextDyadicExcessIntNumerator}(p,n,L) := 2^n p - L`$, chosen so the skipped-branch comparison is an exact Diophantine inequality rather than a real-valued phase estimate; it obeys the exact doubling recurrence $`E(p,n{+}1,L) = 2E(p,n,L) + L`$. `coord:other:dyadic-carry`.

</div>

<div class="prop">

**Proposition 190** (Exact geometric tail bound for the Mersenne-weight remainder). *For $`n\ge 2`$, $`\mathrm{mersenneWeightRemainder}(n) \le (4/3)(1/8)^n`$, and the corresponding infinite tail from depth $`m\ge 1`$ is $`\le (4/21)(1/8)^m`$. `coord:other:dyadic-carry`.*

</div>

<a id="pivot-fibre-anti-reconstruction-an-exact-energy-identity"></a>

### Pivot-fibre anti-reconstruction: an exact energy identity

`PivotAntiReconstruction` adds roughly 1800 lines building a finite-fibre variance/energy machinery around the “first-harmonic” producer hypothesis, ending in another chain of `DTW...Supply` $`\Leftrightarrow`$ irrationality equivalences (again reductions, flagged as such). The exact algebraic core underneath is reusable:

<div class="prop">

**Proposition 191** (Anchor defect is a squared complex distance). *$`\mathrm{firstHarmonicAnchorDefect}(h,L,T) = \sum_{N\in T}\|
\mathrm{windowFirstExp}(h,N,L) - 1\|^2`$, and it equals $`2|T| - 2\sum_{N\in T}\mathrm{windowFirstCos}(h,N,L)`$. `coord:other:pivot-fiber`.*

</div>

<div class="lem">

**Lemma 192** (Separated-pairs energy floor). *For a finite family $`z:T\to\mathbb{C}`$ and any set of pairs $`P\subseteq
T\times T`$ each separated by $`\ge\delta`$, $`|P|\cdot\delta^2 \le
\sum_{i,j\in T}\|z_i-z_j\|^2`$. `coord:other:pivot-fiber`.*

</div>

<a id="actual-foreign-residue-projection"></a>

### Actual foreign-residue projection

`ActualForeignResidueProjection` is explicit that it is “the proof consumer” for a receipt whose analytic kernel identity remains a separate Lean validation lane; it supplies the finite bridge, not the estimate.

<div class="prop">

**Proposition 193** (Explicit shadow is exactly the divisor-channel sum). *For $`H>0`$, $`\mathrm{scaleExplicitShadow}(H) = \sum_{d\mid H}
\mathrm{residueIncrement}(d,H)`$. `coord:other:foreign-residue`.*

</div>

<div class="prop">

**Proposition 194** (Complement-noncancellation consumer). *If a projection’s error against the true foreign defect is controlled by the closed geometric budget $`\mathrm{foreignComplementBound}(H,D)`$, and the finite rational state $`\mathrm{scaleExplicitShadow}(H) +
\mathrm{projectedForeignDefect}(H,D)`$ is farther from every integer than that budget, then $`S\ne \mathrm{fullTargetHit}`$ at scale $`H`$. `coord:other:foreign-residue`. The control and separation hypotheses are exactly the two remaining open obligations; the consumer is a real theorem, not a claim they hold.*

</div>

<a id="geometric-coprimality-a-lattice-coordinate-and-a-classical-identity-beside-it"></a>

### Geometric coprimality: a lattice coordinate, and a classical identity beside it

`GeometricCoprimality` relocates \#249 onto the visible-lattice-point mass of coprime pairs. Beside that bridge it formalises the classical gcd-layering identity for the Lambert-weighted coprime sum. That identity is an elementary rational function of its parameter, so it cannot distinguish rational from irrational inputs; and it carries a different summand weight from $`S`$, so it is not a statement about \#249.

<div class="thm">

**Theorem 195** (Visible-point count is the totient, uniformly). *For every $`n\in\mathbb{N}`$, $`\#\{(a,b): a+b=n,\ 0<a,\ \gcd(a,b)=1\} =
\varphi(n)`$, with no case split at $`n=0,1`$. `coord:other:coprime-lattice`.*

</div>

<div class="prop">

**Proposition 196** (Coprime-pair lattice mass bridges). *For $`0\le r<1`$: $`\sum_{(a,b)\ \mathrm{coprime},\,a\ge 1} r^{a+b} =
\sum_n \varphi(n)r^n`$; over strictly positive coprime pairs the same sum is $`\sum_n\varphi(n)r^n - r`$; and layering by $`\gcd = g`$ recovers the full positive-quadrant mass $`\sum_g[\text{layer }g] = (r/(1-r))^2`$, which equals $`1`$ exactly at $`r=1/2`$ (two independent fair-coin waiting times have a finite gcd almost surely). `coord:other:coprime-lattice`.*

</div>

<div class="thm">

**Theorem 197** (The classical visible-point Lambert identity). *For every $`0\le r<1`$, $`\sum_{(a,b)\ \mathrm{coprime},\, a,b\ge 1}
\dfrac{r^{a+b}}{1-r^{a+b}} = \Bigl(\dfrac{r}{1-r}\Bigr)^2`$, an elementary rational function of $`r`$, hence rational at every rational $`r`$ including $`r=1/2`$. This is the classical visible-point identity, and the Lean declaration is a formalisation of it rather than a new result: writing each pair $`(A,B)`$ of positive integers uniquely as $`g\cdot(a,b)`$ with $`\gcd(a,b)=1`$ converts the quadrant sum $`\sum_{A,B\ge1}r^{A+B}=(r/(1-r))^2`$ into the displayed sum over visible points, which is the $`\gcd`$-layering already recorded in the bridges above. Its summand weight is the Lambert weight $`r^{a+b}/(1-r^{a+b})`$, not the plain weight $`r^{a+b}`$ under which the same index set sums to $`\sum_n\varphi(n)r^n`$; the two sums share an index set and differ in weight, and only the second is $`S`$. `coord:other:coprime-lattice`.*

</div>

<div class="obs">

*Observation 198*. The consequence to draw is narrow, and it is about the Lambert-weighted sum rather than about $`S`$. Coprime-pair restriction, exact Stern–Brocot-type splitting by $`\gcd`$, and geometric cylinder decay of the summand under the map $`n\mapsto r^n/(1-r^n)`$, used together and evaluated at a rational $`r`$, cannot imply irrationality of the resulting sum, because the identical construction is provably rational at *every* rational $`r`$ in $`[0,1)`$ — the mechanism has zero sensitivity to whether $`r`$ itself is rational. This closes one route through the coprime-lattice coordinate; it does not close the coordinate, and it is not evidence about the plain-weight sum that actually equals $`S`$. Any future argument built on this specific route must use some further feature of $`r=1/2`$ beyond coprimality, gcd-layering, and geometric decay.

</div>

<a id="the-lcm-diagonal-collapse-reduced-to-one-mathbbn-indexed-predicate"></a>

### The lcm-diagonal collapse: reduced to one $`\mathbb{N}`$-indexed predicate

`LcmDiagonalReduction` (module `TotientTailPeriodKiller`, “wave 23”) removes the second free parameter from the wave-22 one-parameter reduction, producing a single decidable $`\mathbb{N}`$-indexed statement equivalent to \#249. The module’s own header states plainly that the resulting supply hypothesis “is the open content of \#249 and is NOT claimed”; the equivalence itself is a reduction, reported as such.

<div class="obs">

*Observation 199* (Diagonal collapse — reduction, not a result). $`\mathrm{irrational}(S)`$ follows from: for every $`t_0`$, some $`t\ge t_0`$ admits a certified kill at the diagonal point $`(H_t,H_t)`$, $`H_t :=
\mathrm{lcm}(1,\dots,t)`$. This is proved as an implication only; the antecedent is the unproved open content. (implication proved; antecedent <span class="sans-serif">\[Open\]</span>) `coord:other:lcm-diagonal`.

</div>

<div class="thm">

**Theorem 200** (Window structure of the lcm ray — unconditional). *Below $`2t`$, the only indices $`j`$ that fail to divide $`H_t`$ are bare prime powers exceeding $`t`$; every $`j\le t`$ divides $`H_t`$ outright. On a “clean” divisor $`j\mid H_t`$ (every prime of $`j`$ still divides $`H_t/j`$) the window totient factors exactly: $`\varphi(qH_t+j) = \varphi(j)\cdot\varphi(q(H_t/j)+1)`$. `coord:other:lcm-diagonal`.*

</div>

<div class="obs">

*Observation 201* (Diagonal deposits). The kernel decides $`P(t)`$ (a certified diagonal kill) unconditionally for every $`1\le t\le 8`$ (totient arguments stay $`\le 130`$), at tabulated depths. `coord:other:lcm-diagonal` — a finite floor, not evidence toward the cofinal supply.

</div>

<a id="cyclotomic-anchored-kills-unconditional-prime-support-plus-new-exclusion-certificates"></a>

### Cyclotomic anchored kills: unconditional prime support, plus new exclusion certificates

The newly published `ErdosProblems/Erdos249/CyclotomicAnchoredKill.lean` (3222 lines, namespace `ErdosProblems.Erdos249.CyclotomicAnchoredKill`) discharges the abstract order-consumer producer of §<a href="#prime-ray-curvature" data-reference-type="ref" data-reference="prime-ray-curvature">6.6.12</a> completely for the concrete polynomial $`X-2`$, and separately deposits new kernel-checked denominator exclusions. Its middle $`\approx\!1600`$ lines are a further ladder of `CyclotomicPrime...CarryKillSupply` $`\Leftrightarrow`$ irrationality equivalences; those are reductions and are reported only as architecture, not as narrowing progress.

<div class="thm">

**Theorem 202** (Unconditional unbounded prime support for the Mersenne layer). *Every prime divisor $`p`$ of $`2^q-1`$, for prime $`q`$, satisfies $`q\mid p-1`$ (the order of $`2`$ mod $`p`$ is exactly $`q`$, by Fermat/Lagrange in $`(\mathbb{Z}/p)^\times`$); consequently the prime divisors appearing in the layers $`\{2^n-1\}`$ are unbounded, unconditionally, with no cyclotomic resultant hypothesis left open. `coord:other:cyclotomic-anchor`.*

</div>

<div class="thm">

**Theorem 203** (Unconditional clean cyclotomic anchor existence). *For every period $`h>0`$ and threshold $`N_0`$, there exist a prime $`q`$ and a prime factor $`p`$ of $`|\Phi_{hq}(2)|`$ (the binary cyclotomic layer) with $`p`$ coprime to $`hq`$, $`hq\mid p-1`$, and $`p-1\ge N_0`$. The characteristic-prime exceptional case in the cyclotomic order decomposition is eliminated directly, by choosing $`q>2^h`$ (rules out $`p=q`$) and $`q>h`$ (rules out $`p\mid h`$). `coord:other:cyclotomic-anchor`.*

</div>

<div class="obs">

*Observation 204*. These two theorems are genuine unconditional number theory — an exact-order argument and a Dirichlet-plus-cyclotomic-root existence construction — and they close the abstract producer hypotheses of `PrimeRayCyclotomicCurvature` (§<a href="#prime-ray-curvature" data-reference-type="ref" data-reference="prime-ray-curvature">6.6.12</a>) for the $`X-2`$ layer with no residual conditional. Neither result touches the irrationality question itself; they supply arithmetic support for a *different*, still-open cofinal predicate about certified kills at cyclotomic-anchored periods.

</div>

<div class="obs">

*Observation 205* (New certified exclusions at period 30). The kernel decides two independent certificates at the composite cyclotomic anchor period $`h=30`$ (natural basepoint $`N=300`$, and the prime-anchored basepoint $`N=330`$), yielding a genuine new denominator exclusion: $`S\ne r`$ for every $`r\in\mathbb{Q}`$ with $`r.\mathrm{den}\mid 2^{300}(2^{30}-1)`$. `coord:other:cyclotomic-anchor` — a finite exclusion, not evidence toward the cofinal supply.

</div>

<a id="prime-ray-curvature"></a>

### Prime-ray cyclotomic curvature: the abstract order-consumer producer

<div class="thm">

**Theorem 206** (Bounded-degree order realisability forces unbounded prime support). *If every prime divisor of a layer $`C(mq)`$ has order at most $`d`$ in the relevant residue group (`BoundedDegreeOrderConsumer`), then for every fixed finite set of primes $`S`$, all sufficiently large prime indices $`q`$ avoid $`S`$ entirely on layer $`C(mq)`$; combined with a nontrivial-layer hypothesis this forces arbitrarily large new prime divisors on cofinally many prime indices. `coord:other:cyclotomic-anchor`. This is the abstract producer instantiated unconditionally for $`X-2`$ in §<a href="#prime-ray-curvature" data-reference-type="ref" data-reference="prime-ray-curvature">6.6.12</a>’s sibling result above; polynomial resultant realisability and Archimedean growth for other layers remain explicit upstream obligations, not proved here.*

</div>

<a id="rank-one-subrank"></a>

### Rank-one subrank obstruction: a uniform proved barrier

`RankOneSubrankObstruction` is a uniform proved barrier: it names an entire family of candidate linear-form constructions and proves, uniformly, that none of them can work.

<div class="thm">

**Theorem 207** (Uniform rank-one no-go). *Let $`\Theta_r`$ be the Möbius–Mersenne ladder rung and let $`t(Y,r)`$ be its first $`Y`$ atoms. For every $`e\ge 1`$ and $`Y\ge 4`$,
``` math
t(Y,e{+}2)^2/t(Y,2e{+}2) - \Theta_2 > 1/480.
```
Every rank-one monomial Schur quotient built this way overshoots $`\Theta_2 =
S-1/2`$ by a fixed positive margin, uniformly in $`e`$ and $`Y`$; the bound uses only two interval facts (every rung $`r\ge 3`$ lies in $`[1429/1512,1)`$, and every length-$`\ge\!4`$ prefix is within $`1/3584`$ of its rung). `coord:other:rank-one-subrank`.*

</div>

<div class="prop">

**Proposition 208** (The gap survives positive averaging). *For any nonempty finite positively-weighted family of admissible quotients, the weighted average still overshoots $`\Theta_2`$ by more than $`1/480`$; and every primitive integer linear form $`q\Theta_2 - p`$ realising such a quotient satisfies $`|q\Theta_2 - p| > q/480`$. `coord:other:rank-one-subrank`.*

</div>

<div class="obs">

*Observation 209*. This is a proved barrier stated at the required precision: the class of argument it rules out is exactly “a primitive rational linear form for $`\Theta_2`$ (equivalently for $`S`$) obtained as a rank-one strict-subrank monomial quotient of finite Möbius–Mersenne prefixes,” and the reason is the explicit uniform lower bound above, not an empirical failure report. It does not touch, and is not claimed to touch, linear forms built by any other mechanism.

</div>

<a id="period-multiple-escape-the-nesting-identity-and-eight-new-exclusions"></a>

### Period-multiple escape: the nesting identity and eight new exclusions

`PeriodMultipleEscape` proves the period-multiple kill supply is *exactly equivalent* to irrationality of $`S`$ (both directions, sufficiency by telescoping the tail-period law, necessity by certificate completeness) — reported here as an equivalence-class reduction, not progress — and separately deposits genuinely new denominator exclusions.

<div class="thm">

**Theorem 210** (Nesting: the cyclotomic fan collapses onto the dyadic tower). *$`Q_{a+b,N} = 2^b Q_{a,N} + Q_{b,N+a}`$ (block concatenation), so the order-4 cyclotomic channel at height $`h`$ is literally the order-2 channel at height $`2h`$: the 2–3–4 fan of channels is a nested family along the tower $`h,2h,4h,\dots`$, not three unrelated moduli. `coord:other:lcm-period-multiple`.*

</div>

<div class="obs">

*Observation 211* (Supply $`\Leftrightarrow`$ irrational — reduction, not a result). (equivalence proved; both directions of the underlying predicate are exactly as open as \#249 itself) `coord:other:lcm-period-multiple`. The paper’s current aggregate diagonal bank certifies kills at every $`H_t`$ for $`t\le82`$; this module’s equivalence contributes no new information about $`t=83`$ or any cofinal supply.

</div>

<div class="obs">

*Observation 212* (Eight new certified denominator exclusions past the 64-smooth diagonal bank). The kernel certifies kills, unconditionally, at the eight prime-power periods the diagonal bank could not reach ($`67,81,97,101,121,125,127,128`$, all at basepoint $`N=300`$), each yielding $`S\ne r`$ for every $`r`$ with $`r.\mathrm{den}\mid 2^{300}(2^h-1)`$ — new odd denominator classes, including the Cole factors of $`2^{67}-1`$ and the Mersenne prime $`2^{127}-1`$. One of the eight is certified at its own locked depth $`L=h=67`$, the concrete instance of the sufficient (not known necessary) depth-equals-period form $`\mathrm{ApFullDepthEscape}`$. `coord:other:lcm-period-multiple` — eight finite exclusions, not evidence toward the cofinal supply.

</div>

<a id="strict-prime-orbit-escape-a-sharper-reduction"></a>

### Strict prime-orbit escape: a sharper reduction

`TotientStrictPrimeEscape` sharpens the legacy first-harmonic producer’s threshold from a $`4/5`$ gap to a strict $`9/10`$ gap with an adaptive truncation budget, and proves the sharper predicate still closes \#249 through the existing singleton-certificate endpoint. This is, exactly as its own comment states, a reduction: “the producer itself remains unproved.” (implication proved; antecedent <span class="sans-serif">\[Open\]</span>) `coord:other:first-harmonic`.

<a id="finite-euler-sieve-algebra"></a>

### Finite Euler-sieve algebra

`FiniteEulerSieve` records the elementary finite-stage identities behind the squared-Möbius Euler factor, with no transcendence claim asserted: $`(1-2/p+1/p^2) = (1-1/p)^2`$ and its degree-two analogue, and the second finite difference of $`1+p+\cdots+p^{e}`$ recovering $`p^{e+1}(p-1)`$, the prime-power totient row. `coord:other:euler-sieve`.

<a id="sec:249-scale-ladder"></a>

# The scale ladder

Every statement in the Erdős \#249 corpus that this paper draws on is tagged with a *scale*: <span class="sans-serif">scale:fixed</span> (a finite, explicitly enumerated set of parameter values, typically closed by `decide`/`interval_cases`), <span class="sans-serif">scale:bounded</span> (holds for all parameter values on one side of a threshold, e.g. $`\forall a\ge 8`$, but the proof or the constants inside it do not survive removing the threshold), <span class="sans-serif">scale:uniform</span> (holds unconditionally for every value of every free parameter, with no scale restriction at all), and <span class="sans-serif">scale:cofinal</span> (an existential claim of the shape $`\forall N_0\,\exists N\ge N_0,\ P(N)`$ — infinitely often, arbitrarily far out).

The source tables underlying this ladder also mark a handful of pure identities and converters `n/a` when they are not indexed by any problem-scale parameter at all (they are definitions or unconditional equivalences); for ladder purposes these are folded into <span class="sans-serif">scale:uniform</span>, since an unconditional statement is, if anything, stronger than a uniform one. This convention is applied uniformly below and is stated here once rather than re-flagged on every row.

\#249’s own supply obligation is *exactly* cofinal. The reduction chain (§<a href="#sec:249-scale-ladder" data-reference-type="ref" data-reference="sec:249-scale-ladder">7</a>, and see ) shows
``` math
\mathrm{Irrational}\Bigl(\sum_{n\ge 1}\varphi(n)/2^n\Bigr) \iff \forall a_0\ \exists a\ge a_0,\ \texttt{actualLcmTailOrbit}\ a \notin \mathrm{range}(\mathbb{Z}\to\mathbb{R}),
```
an `cofinal` statement in the exponent $`a`$ that indexes $`H=\mathrm{periodLcm}(2^a)`$. Nothing weaker in scale can close \#249; the entire question is whether the corpus’s uniform, bounded, and fixed machinery can be pushed to cofinal. The table below lists every catalogued \#249 result, grouped by scale, with a horizontal rule separating everything that is *proved* (uniform, bounded, fixed) from the handful of statements that are themselves the *cofinal target* or consumers of it (below the rule). Quantifier prefixes are written out explicitly and exactly as recorded against the Lean source; nothing is compressed to “$`\forall\dots`$” where the source specifies bounds.

<div class="landscape">

<table style="width:94%;">
<caption>The #249 scale ladder. Every row above the rule is proved; every row below it is the cofinal target or a direct consumer of it.</caption>
<colgroup>
<col style="width: 22%" />
<col style="width: 18%" />
<col style="width: 8%" />
<col style="width: 34%" />
<col style="width: 12%" />
</colgroup>
<thead>
<tr>
<th style="text-align: left;"><strong>Result</strong></th>
<th style="text-align: left;"><strong>Lean site</strong></th>
<th style="text-align: left;"><strong>Scale</strong></th>
<th style="text-align: left;"><strong>Quantifier prefix</strong></th>
<th style="text-align: left;"><strong>Coordinate</strong></th>
</tr>
</thead>
<tbody>
<tr>
<td style="text-align: left;"><strong>Result</strong></td>
<td style="text-align: left;"><strong>Lean site</strong></td>
<td style="text-align: left;"><strong>Scale</strong></td>
<td style="text-align: left;"><strong>Quantifier prefix</strong></td>
<td style="text-align: left;"><strong>Coordinate</strong></td>
</tr>
<tr>
<td colspan="5" style="text-align: right;"><em>continued on next page</em></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;">totientTail well-defined</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>N</em></span></td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;"><span class="math inline">2<sup><em>N</em></sup> ⋅ <em>S</em></span> split</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>N</em></span></td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;">windowDiscrepancy (def)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> ∀<em>N</em> ∀<em>L</em></span></td>
<td style="text-align: left;">other-binary-window</td>
</tr>
<tr>
<td style="text-align: left;">certifiedKill Sep<span class="math inline">(<em>h</em>, <em>N</em>, <em>L</em>)</span> (def)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> ∀<em>N</em> ∀<em>L</em></span></td>
<td style="text-align: left;">other-binary-window</td>
</tr>
<tr>
<td style="text-align: left;">certificate depth floor</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> ∀<em>N</em> ∀<em>L</em></span>, given <code>certifiedKill</code><span class="math inline"> <em>h</em> <em>N</em> <em>L</em></span></td>
<td style="text-align: left;">other-binary-window</td>
</tr>
<tr>
<td style="text-align: left;">kill engine soundness</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> ∀<em>N</em> ∀<em>L</em></span>, given <code>certifiedKill</code></td>
<td style="text-align: left;">other-binary-window</td>
</tr>
<tr>
<td style="text-align: left;">certificates are complete receipts</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> ∀<em>N</em></span></td>
<td style="text-align: left;">other-binary-window</td>
</tr>
<tr>
<td style="text-align: left;">forced integrality under den. divisibility</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>N</em> ∀<em>h</em> ∀<em>r</em> : ℚ</span>, given <span class="math inline"><em>S</em> = <em>r</em></span>, <span class="math inline"><em>r</em>.den ∣ 2<sup><em>N</em></sup>(2<sup><em>h</em></sup> − 1)</span></td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;">tail-period law</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">¬Irrational <em>S</em> → ∃<em>h</em> &gt; 0 ∃<em>N</em><sub>0</sub> ∀<em>N</em> ≥ <em>N</em><sub>0</sub></span></td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;">periodLcm basic facts</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em></span></td>
<td style="text-align: left;">other-lcm-period-ray</td>
</tr>
<tr>
<td style="text-align: left;">non-divisor<span class="math inline"> &lt; 2<em>t</em></span> is a bare prime power</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em> ∀<em>j</em> (0 &lt; <em>j</em> &lt; 2<em>t</em>)</span>, given <span class="math inline"><em>j</em> ∤ periodLcm <em>t</em></span></td>
<td style="text-align: left;">other-lcm-window</td>
</tr>
<tr>
<td style="text-align: left;">LCM-ray multiplicative split</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em> ∀<em>j</em> ∀<em>q</em></span>, given <span class="math inline"><em>j</em> ∣ periodLcm <em>t</em></span>, clean-divisor</td>
<td style="text-align: left;">other-lcm-window-multiplicative</td>
</tr>
<tr>
<td style="text-align: left;">rationality flattens the whole LCM cone</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">¬Irrational <em>S</em> → ∃<em>t</em><sub>1</sub> ∀<em>t</em> ≥ <em>t</em><sub>1</sub> ∀<em>q</em> &gt; 0 ∀<em>m</em></span></td>
<td style="text-align: left;">other-lcm-cone</td>
</tr>
<tr>
<td style="text-align: left;">second-difference kill engine</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> ∀<em>N</em> ∀<em>L</em></span>, given <code>certifiedRank2Kill</code></td>
<td style="text-align: left;">other-binary-window</td>
</tr>
<tr>
<td style="text-align: left;">cone-menu nonintegral pair</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>H</em> ∀<em>L</em> ∀<em>Q</em> ≠ ∅</span>, given <code>coneNonflatCert</code></td>
<td style="text-align: left;">other-lcm-cone-menu</td>
</tr>
<tr>
<td style="text-align: left;">survivorKill engine (carry-orbit route)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> ∀<em>N</em> ∀<em>K</em></span>, given <code>survivorKill</code></td>
<td style="text-align: left;">other-carry-orbit</td>
</tr>
<tr>
<td style="text-align: left;">Farey neighbour denominator law</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> <em>b</em> <em>c</em> <em>d</em> <em>r</em> <em>s</em> : ℤ</span>, <span class="math inline"><em>b</em> &gt; 0, <em>d</em> &gt; 0, <em>b</em><em>c</em> − <em>a</em><em>d</em> = 1</span>, unimodular-between</td>
<td style="text-align: left;">farey</td>
</tr>
<tr>
<td style="text-align: left;">Dirichlet near-integer criterion</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>u</em> : ℕ → ℚ ∀<em>x</em> : ℝ</span></td>
<td style="text-align: left;">n/a (generic)</td>
</tr>
<tr>
<td style="text-align: left;">Erdős 1948 near-integer criterion</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>ξ</em> : ℝ</span>, <span class="math inline">∀<em>q</em> &gt; 0 ∃<em>m</em> <em>z</em> 0 &lt; |<em>m</em><em>ξ</em> − <em>z</em>| &lt; 1/<em>q</em></span></td>
<td style="text-align: left;">n/a (generic)</td>
</tr>
<tr>
<td style="text-align: left;">finite-minor <span class="math inline">⇒</span> linear independence</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀ family : <em>ι</em> → ℕ → ℚ</span>, given SeparatedMinorCertificate</td>
<td style="text-align: left;">n/a (generic)</td>
</tr>
<tr>
<td style="text-align: left;">dyadic totient-kernel rank <span class="math inline"> = 2<sup><em>e</em></sup> + 1</span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>e</em></span></td>
<td style="text-align: left;">other-dyadic-kernel-rank</td>
</tr>
<tr>
<td style="text-align: left;">rationality forces unbounded carry-kernel rank</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">¬Irrational <em>S</em> → ∃<em>v</em> &gt; 0 ∃<em>u</em> ∀<em>e</em></span></td>
<td style="text-align: left;">other-carry-kernel-rank</td>
</tr>
<tr>
<td style="text-align: left;">no fixed <span class="math inline"><em>D</em></span> clears all primitive Euler jets</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>D</em> &gt; 0</span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">Mersenne–Lambert ladder value identities</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;">value identities, <span class="math inline">$L(\mu){=}\tfrac12$</span>, <span class="math inline"><em>L</em>(<em>φ</em>) = 2</span>, <span class="math inline"><em>L</em>(1)=</span>Erdős–Borwein</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">prime-power reduced-denom. unit-gap ceiling</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>p</em> prime ∀<em>e</em> &gt; 0</span></td>
<td style="text-align: left;">farey</td>
</tr>
<tr>
<td style="text-align: left;">positive rational-difference lower bound</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀ whole pfx : ℚ, pfx &lt; whole</span></td>
<td style="text-align: left;">n/a (generic)</td>
</tr>
<tr>
<td style="text-align: left;">Möbius-square identity (<span class="math inline">$S=\tfrac12+\Sigma$</span>)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;">unconditional</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">squared-Lambert transfer engine</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>w</em> : ℕ → ℝ (|<em>w</em>(<em>d</em>)| ≤ <em>d</em>) ∀<em>r</em> ∈ [0, 1)</span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;"><span class="math inline">$L_2(\mu)=S-\tfrac12$</span></td>
<td style="text-align: left;">prose:L2_of_mu_is_249</td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;">unconditional</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;"><span class="math inline"><em>L</em><sub>2</sub>(1) = <em>ζ</em><sub><em>q</em></sub>(2) − <em>ζ</em><sub><em>q</em></sub>(1)</span> identity</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;">unconditional</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;"><span class="math inline"><em>L</em><sub>2</sub>(<em>φ</em>)</span> = gcd moment</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;">unconditional</td>
<td style="text-align: left;">mobius-mersenne/probability</td>
</tr>
<tr>
<td style="text-align: left;">level-mirror table</td>
<td style="text-align: left;">prose:level_mirror_table</td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;">unconditional</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">gcd-divisibility factorizes</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>d</em> : ℕ, <em>d</em> &gt; 0</span></td>
<td style="text-align: left;">probability</td>
</tr>
<tr>
<td style="text-align: left;">reduced-direction law <span class="math inline"><em>Σ</em> = 1</span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;">unconditional (sum over all coprime pairs)</td>
<td style="text-align: left;">probability</td>
</tr>
<tr>
<td style="text-align: left;">Stern–Brocot cylinder recursion</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> <em>b</em> : ℕ<sup>+</sup> ∀depth <em>d</em></span></td>
<td style="text-align: left;">other-stern-brocot</td>
</tr>
<tr>
<td style="text-align: left;">repunit gcd-word T1</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>r</em> (Squarefree <em>r</em>) ∀<em>k</em> &lt; <em>r</em></span></td>
<td style="text-align: left;">cyclotomic</td>
</tr>
<tr>
<td style="text-align: left;">eval-at-2 recovers numerator</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>r</em> (Squarefree <em>r</em>)</span></td>
<td style="text-align: left;">cyclotomic</td>
</tr>
<tr>
<td style="text-align: left;">radical-shadow scale decomposition</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>H</em> &gt; 0 ∀<em>r</em> &gt; 0</span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">cyclotomic congruence T2</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>r</em> (Squarefree <em>r</em>) ∀<em>m</em> (<em>m</em> ∣ <em>r</em>)</span></td>
<td style="text-align: left;">cyclotomic</td>
</tr>
<tr>
<td style="text-align: left;">top-fibre survives T3</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>r</em> (Squarefree <em>r</em>)</span></td>
<td style="text-align: left;">cyclotomic</td>
</tr>
<tr>
<td style="text-align: left;">upper-half prime channel survival T4</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em> ∀<em>p</em> prime ∈ (<em>t</em>/2, <em>t</em>]</span>, scale-coprime-to-<span class="math inline"><em>C</em></span></td>
<td style="text-align: left;">cyclotomic</td>
</tr>
<tr>
<td style="text-align: left;">denominator lower bound / exact value</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em></span> (exact-value); <span class="math inline"><em>t</em> ≥ 5</span> (lower bound)</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">prime-power jump recurrence T5</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>p</em> prime (<em>p</em> ∤ <em>r</em>) ∀<em>m</em> (<em>m</em> ∣ <em>r</em>)</span></td>
<td style="text-align: left;">cyclotomic</td>
</tr>
<tr>
<td style="text-align: left;">squared-Mersenne diagonal tail enclosure</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>D</em> : ℕ</span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;"><span class="math inline">(3, 5)</span> joint annihilator</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>d</em> &gt; 0 (<em>d</em> ∣ <em>H</em>)</span>; general: finite affine annihilator</td>
<td style="text-align: left;">other-lcm-diagonal</td>
</tr>
<tr>
<td style="text-align: left;">composite-dilation defect identity</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ∈ <em>A</em> (<em>a</em> &gt; 0) ∀<em>x</em> &gt; 0</span></td>
<td style="text-align: left;">other-divisor-support-coeff</td>
</tr>
<tr>
<td style="text-align: left;">sublogarithmic zero-window T11</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>ε</em> &gt; 0 ∃<em>B</em></span>, given rationality of the base-2 support series</td>
<td style="text-align: left;">other-support-divisor-counting</td>
</tr>
<tr>
<td style="text-align: left;">campbell shift <span class="math inline">↔︎</span> Mersenne endpoint (shared namespace, #257-flavored)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;">iff, no extra parameter</td>
<td style="text-align: left;">other-greedy-mersenne-achievement</td>
</tr>
<tr>
<td style="text-align: left;">totient overlap-factor multiplicativity</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>x</em> &gt; 0</span> (<span class="math inline"><em>j</em></span> fixed)</td>
<td style="text-align: left;">other-totient-arithmetic</td>
</tr>
<tr>
<td style="text-align: left;">totient relative-Euler-product split</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>j</em> <em>x</em> &gt; 0</span></td>
<td style="text-align: left;">other-totient-arithmetic</td>
</tr>
<tr>
<td style="text-align: left;">lcmRayArithmeticLetter <span class="math inline">=</span> deltaTotient <span class="math inline">=</span> diagonalWindowIncrement</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em> ∀<em>j</em></span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">lcmDiagonalArithmeticWord <span class="math inline">=</span> windowDiscrepancy</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em> ∀<em>L</em></span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">#249 <span class="math inline">⇔</span> cofinal actual-orbit nonintegrality</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;">iff</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">actualLcmTailOrbit <span class="math inline">=</span> scaled series <span class="math inline">−</span> prefix</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em></span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">explicit finite-block approximation</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ∀<em>q</em></span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">guard-cylinder normal form</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> <em>N</em>, iff</span></td>
<td style="text-align: left;">seam-integer</td>
</tr>
<tr>
<td style="text-align: left;">fixedRankSecondDifference sign under extremality</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>H</em> <em>j</em></span>, given MiddleRankTotientExtremal</td>
<td style="text-align: left;">other-fixed-rank-curvature</td>
</tr>
<tr>
<td style="text-align: left;">dyadic fixture exactness (kernel-valuation sharpness)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>n</em></span> (closed-form)</td>
<td style="text-align: left;">other-fixed-rank-curvature</td>
</tr>
<tr>
<td style="text-align: left;">parityCoboundaryWeight (def)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>n</em></span> (definition)</td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;">totientTail <span class="math inline">=</span> positive foreign-residue kernel sum</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>N</em></span></td>
<td style="text-align: left;">cyclotomic</td>
</tr>
<tr>
<td style="text-align: left;">totientTail <span class="math inline">=</span> shifted Möbius-pulse sum</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>N</em></span></td>
<td style="text-align: left;">cyclotomic</td>
</tr>
<tr>
<td style="text-align: left;">Lambert double-sum regroup engine</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>w</em> <em>v</em> : ℕ → ℝ (|<em>w</em>(<em>d</em>)| ≤ <em>d</em>, |<em>v</em>(<em>m</em>)| ≤ <em>m</em>)</span></td>
<td style="text-align: left;">cyclotomic</td>
</tr>
<tr>
<td style="text-align: left;">carryShift-integrality iff</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>N</em> <em>k</em></span>, given tempered orbit</td>
<td style="text-align: left;">seam-integer</td>
</tr>
<tr>
<td style="text-align: left;">rationality <span class="math inline">⇒</span> periodicity &amp; unbounded rank</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">¬Irrational <em>S</em> → ∃<em>v</em> <em>u</em> ∀<em>e</em></span></td>
<td style="text-align: left;">seam-integer</td>
</tr>
<tr>
<td style="text-align: left;">adjugate tail-cost floor <span class="math inline"> ≥ 3</span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀ finite <em>w</em> : <em>ι</em> → ℚ <em>x</em> : <em>ι</em> → ℕ</span>, given <span class="math inline">∑<em>w</em><sub><em>i</em></sub><em>φ</em>(<em>x</em><sub><em>i</em></sub>) = 1</span></td>
<td style="text-align: left;">other-adjugate-linear-algebra</td>
</tr>
<tr>
<td style="text-align: left;">directedCertifiedKill exact iff</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> <em>N</em> <em>L</em></span></td>
<td style="text-align: left;">seam-integer</td>
</tr>
<tr>
<td style="text-align: left;">tempered orbit rigidity iff</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>c</em> : ℕ → ℕ (<em>c</em>(<em>n</em>) ≤ <em>n</em>)</span>, iff</td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;">doubling-orbit rigidity</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>d</em> : ℕ → ℝ</span>, doubling <span class="math inline">+</span> tempered <span class="math inline"> → <em>d</em> ≡ 0</span></td>
<td style="text-align: left;">other-abstract-recursion</td>
</tr>
<tr>
<td style="text-align: left;">finite-state no-go (unbounded state)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>m</em> ∀State</span>, collapsing-state <span class="math inline">→</span> no decoder</td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;">fixed-depth affine reset</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> : ℕ → ℤ ∀<em>u</em><sub>0</sub> <em>v</em><sub>0</sub> ∀<em>L</em></span></td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;">signed dichotomy engine (full-block certs)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>b</em> ≥ 2 ∀<em>c</em> ∀<em>q</em></span>, given full-block certificate at <span class="math inline"><em>q</em></span></td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;">Lambert double-sum regroup (dyadic forward-difference calc.)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>f</em>, <em>c</em> : ℕ → ℤ ∀ shift-lists</span></td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;">fair-coin coprimality bridge</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>n</em></span>; <span class="math inline">∀<em>r</em> ∈ [0, 1)</span></td>
<td style="text-align: left;">probability</td>
</tr>
<tr>
<td style="text-align: left;">linear-descender rigidity</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>V</em>, <em>W</em> ∀ev ∀<em>L</em></span>, <span class="math inline">ker (ev) ≤ ker (<em>L</em>)</span></td>
<td style="text-align: left;">p-adic</td>
</tr>
<tr>
<td style="text-align: left;">rational denominator survival law</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>D</em> &gt; 0 ∀<em>m</em> ∣ <em>D</em> ∀<em>a</em></span></td>
<td style="text-align: left;">p-adic</td>
</tr>
<tr>
<td style="text-align: left;">scalar-localization complement-dvd (adelic height tax)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>x</em> : ℚ ∀<em>H</em> (<em>H</em> ∣ <em>x</em>.den) ∀<em>c</em> ((<em>c</em><em>x</em>).den ∣ <em>H</em>)</span></td>
<td style="text-align: left;">p-adic</td>
</tr>
<tr>
<td style="text-align: left;">signed Hankel terminal-parity engine</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∃<em>m</em> ∈ <em>s</em></span> (strictly maximal, odd coeff), <span class="math inline">∀<em>i</em> ≠ <em>m</em> <em>e</em>(<em>i</em>) &lt; <em>e</em>(<em>m</em>)</span></td>
<td style="text-align: left;">p-adic</td>
</tr>
<tr>
<td style="text-align: left;">residual gauge obstruction (locked minors)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>d</em> ∀<em>e</em> : Fin <em>d</em> → ℕ ∀<em>z</em> : Fin <em>d</em> → ℂ</span> (<span class="math inline"><em>z</em></span> nonzero)</td>
<td style="text-align: left;">other-first-harmonic-phase</td>
</tr>
<tr>
<td style="text-align: left;">incidence-quotient no compression</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">uniform</td>
<td style="text-align: left;"><span class="math inline">∀<em>N</em> : ℕ</span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;">Farey window <span class="math inline"><em>K</em> = 240</span> denominator bound</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>q</em> : ℕ, 0 &lt; <em>q</em>≤</span><br />
<span class="math inline">79, 639, 646, 646, 701,</span><br />
<span class="math inline">375, 323, 355, 774, 875, 831, 053</span></td>
<td style="text-align: left;">farey</td>
</tr>
<tr>
<td style="text-align: left;">denominator lower bound <span class="math inline"><em>S</em> ≠ <em>p</em>/<em>q</em></span>, <span class="math inline"><em>q</em> ≤ <em>Q</em><sub>0</sub></span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>p</em> : ℚ, <em>p</em>.den ≤ <em>Q</em><sub>0</sub></span></td>
<td style="text-align: left;">farey</td>
</tr>
<tr>
<td style="text-align: left;">foreign-residue tail-limit converter</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>H</em> <em>D</em></span> with <span class="math inline">2<em>H</em> ≤ <em>D</em></span>, given tail-limit convergence</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">fixed-precision tropical no-go</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>u</em> &gt; 0</span> (fixed precision), <span class="math inline">∀</span> finite carry word</td>
<td style="text-align: left;">p-adic</td>
</tr>
<tr>
<td style="text-align: left;"><span class="math inline"><em>μ</em></span>-clean-Padé feasibility wall</td>
<td style="text-align: left;">prose:mu_pollution_qpade_wall</td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;">claimed <span class="math inline">∀<em>d</em></span>; machine-audited only <span class="math inline"><em>d</em> ≤ 12</span></td>
<td style="text-align: left;">mobius-mersenne (q-Padé)</td>
</tr>
<tr>
<td style="text-align: left;">iterated pullback / bounded-<span class="math inline"><em>Ω</em></span> vanishing</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;">given <span class="math inline"><em>Ω</em>(<em>a</em>) ≤ <em>K</em> ∀<em>a</em> ∈ <em>A</em></span></td>
<td style="text-align: left;">other-support-divisor-counting</td>
</tr>
<tr>
<td style="text-align: left;">rough-density <span class="math inline">⇒</span> totient <span class="math inline">$\ge\tfrac34 n$</span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ≥ 8 ∀<em>n</em> &gt; 0</span> (<span class="math inline"><em>n</em></span> is <span class="math inline"><em>t</em></span>-rough, <span class="math inline"><em>t</em> = 2<sup><em>a</em></sup></span>, <span class="math inline"><em>n</em> &lt; 2<sup>2 ⋅ 2<sup><em>a</em></sup></sup></span>)</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">short-window sign fixed positive</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ≥ 8 ∀<em>j</em> (0 &lt; <em>j</em> &lt; 2 ⋅ 2<sup><em>a</em></sup>)</span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">unconditional lower-half positivity</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded<span class="math inline"><sup>†</sup></span></td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ≥ 8 ∀<em>J</em> (<em>J</em> + (<em>a</em> + 6) &lt; 2 ⋅ 2<sup><em>a</em></sup>)</span>, no rationality hypothesis</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">top-edge residue survivor negative</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ≥ 8 ∀<em>J</em> <em>K</em></span> (room bound)</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">integrality forces top-edge residue</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ≥ 8 ∀<em>J</em> <em>K</em></span> (room, <span class="math inline">2<em>H</em> + <em>J</em> + <em>K</em> + 2 &lt; 2<sup><em>K</em></sup></span>)</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">short-kill supply through <span class="math inline"><em>a</em> ≤ 6</span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em><sub>0</sub> ≤ 6 ∃<em>a</em> <em>L</em></span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">terminal dyadic staircase impossible with room</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ≥ 8 ∀<em>J</em> <em>K</em> <em>m</em></span> (room, modulus-wide)</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">punctured staircase penultimate pin</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ≥ 8 ∀<em>J</em> <em>K</em> <em>m</em></span> (room <span class="math inline">+</span> punctured hyp.)</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">top-edge residue-gap <span class="math inline">⇒</span> nonintegral</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ≥ 8 ∀<em>J</em> <em>K</em> <em>m</em></span> (room, one-sided)</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">odd-rank centred-lift <span class="math inline">=</span> terminal <span class="math inline">−</span> true carry</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ≥ 8 ∀<em>q</em></span> (room, fit bound <span class="math inline">2(<em>H</em> + <em>q</em> + 2) ≤ 4<sup><em>q</em></sup></span>)</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">prime-power kernel valuation floor</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em> ≥ 4 ∀<em>j</em> &gt; 0 (<em>j</em><sup>2</sup> ≤ 2<sup><em>a</em></sup>)</span></td>
<td style="text-align: left;">other-fixed-rank-curvature</td>
</tr>
<tr>
<td style="text-align: left;">finite rational-separation <span class="math inline">⇒</span> <span class="math inline">¬</span> hit (#257-flavored)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>H</em> &gt; 0 ∀<em>D</em> ≥ 2<em>H</em></span>, given finite separation</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">homogeneous Mersenne multiplier does not annihilate</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>K</em>, <em>q</em> (<em>K</em> &gt; 0, <em>K</em> &lt; <em>q</em>, <em>q</em> ∣ 2<sup><em>K</em></sup> − 1)</span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">numerator-gap <span class="math inline">⇒</span> <span class="math inline">¬</span> hit (#257-flavored)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>H</em>, <em>D</em></span> fixed, given uniform numerator-gap bound</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">periodic-weight Lambert dichotomy</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>b</em> ≥ 2 ∀<em>m</em> &gt; 0 ∀<em>w</em></span> (<span class="math inline"><em>w</em>(<em>n</em> + <em>m</em>) = <em>w</em>(<em>n</em>)</span>)</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">non-negative periodic <span class="math inline">⇒</span> irrational (unconditional)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>b</em> ≥ 2 ∀<em>m</em> &gt; 0</span>, <span class="math inline"><em>w</em></span> periodic, <span class="math inline"> ≥ 0</span>, frequently <span class="math inline"> ≠ 0</span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;">all <span class="math inline"><em>h</em> ∈ [1, 8]</span> kill certificate at depth 16, <span class="math inline"><em>N</em> = 12</span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">fixed</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> ∈ [1, 8]</span>, <code>certifiedKill</code> <span class="math inline"><em>h</em></span> 12 16 (by <code>decide</code>)</td>
<td style="text-align: left;">other-binary-window</td>
</tr>
<tr>
<td style="text-align: left;"><span class="math inline"><em>h</em> ∈ [1, 16]</span>, exponent 14 kill table</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">fixed</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> ∈ [1, 16]</span>, denominator exponent 14 (by <code>decide</code>)</td>
<td style="text-align: left;">other-binary-window</td>
</tr>
<tr>
<td style="text-align: left;">rank-2 kill not shallower at <span class="math inline">(<em>h</em>, <em>N</em>) = (1, 8)</span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">fixed</td>
<td style="text-align: left;">measured over <span class="math inline"><em>t</em> ≤ 20</span> (30/40 cells)</td>
<td style="text-align: left;">other-binary-window</td>
</tr>
<tr>
<td style="text-align: left;">28-point diagonal pincer table through <span class="math inline"><em>t</em> = 64</span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">fixed</td>
<td style="text-align: left;"><span class="math inline"><em>t</em> ∈ {1, 2, 3, 4, 5, 7, 8, 9, 11, 13, 16, 17, …}</span> (28 explicit values)</td>
<td style="text-align: left;">other-lcm-diagonal</td>
</tr>
<tr>
<td style="text-align: left;">contiguous diagonal certificate band through <span class="math inline"><em>t</em> ≤ 82</span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">bounded</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em> ≤ 82 ∃<em>L</em></span>; no <span class="math inline"><em>t</em> = 83</span> certificate claimed</td>
<td style="text-align: left;">other-lcm-diagonal</td>
</tr>
<tr>
<td style="text-align: left;">short kill at <span class="math inline"><em>a</em> = 4</span> and <span class="math inline"><em>a</em> = 6</span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">fixed</td>
<td style="text-align: left;"><span class="math inline"><em>a</em> = 4</span>, <span class="math inline"><em>a</em> = 6</span> (concrete, kernel-checked)</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">square-CRT clean block: vanishing / nonvanishing witnesses</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">fixed</td>
<td style="text-align: left;">witness <span class="math inline"><em>n</em> = 52</span> (vanishes); witness <span class="math inline"><em>n</em> = 27</span> (nonzero)</td>
<td style="text-align: left;">other-crt-dyadic-residue</td>
</tr>
<tr>
<td style="text-align: left;">echo-vs-height two-front wall</td>
<td style="text-align: left;">prose:echo_versus_height_two_front_wall</td>
<td style="text-align: left;">fixed</td>
<td style="text-align: left;">empirical over tested families only (not universal)</td>
<td style="text-align: left;">mobius-mersenne (q-Padé, quantitative)</td>
</tr>
<tr>
<td style="text-align: left;">period-4 zeroset escape witness</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">fixed</td>
<td style="text-align: left;"><span class="math inline">∀<em>n</em>, <em>n</em> ≡ 3   (mod  4)</span> (fixed weight <span class="math inline"><em>w</em></span>)</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"></td>
</tr>
<tr>
<td style="text-align: left;"><strong>THE WALL</strong> — certificate supply <span class="math inline">⇒</span> Irrational <span class="math inline"><em>S</em></span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;"><strong>cofinal</strong></td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> ≥ 1 ∀<em>N</em><sub>0</sub> ≥ 0 ∃<em>N</em> ≥ <em>N</em><sub>0</sub> ∃<em>L</em>, <code>certifiedKill</code> <em>h</em> <em>N</em> <em>L</em></span></td>
<td style="text-align: left;">other-binary-window</td>
</tr>
<tr>
<td style="text-align: left;">multiple-certificate supply (weakened)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em><sub>0</sub> &gt; 0 ∀<em>N</em><sub>0</sub> ∃<em>m</em> &gt; 0 ∃<em>N</em> ≥ <em>N</em><sub>0</sub> ∃<em>L</em></span></td>
<td style="text-align: left;">other-lcm-period-multiple</td>
</tr>
<tr>
<td style="text-align: left;">LCM-diagonal one-parameter restatement</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em><sub>0</sub> ∃<em>t</em> ≥ <em>t</em><sub>0</sub> ∃<em>L</em></span></td>
<td style="text-align: left;">other-lcm-diagonal</td>
</tr>
<tr>
<td style="text-align: left;">LCM-cone window-kill supply (widest target)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em><sub>0</sub> ∃<em>t</em> ≥ <em>t</em><sub>0</sub> ∃<em>q</em> &gt; 0 ∃<em>m</em> ∃<em>L</em></span></td>
<td style="text-align: left;">other-lcm-cone</td>
</tr>
<tr>
<td style="text-align: left;">LCM diagonal/cone nonintegrality restatement</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em><sub>0</sub> ∃<em>t</em> ≥ <em>t</em><sub>0</sub></span>, <span class="math inline"><code>totientTail</code>(2<em>H</em><sub><em>t</em></sub>) − <code>totientTail</code>(<em>H</em><sub><em>t</em></sub>) ∉ ℤ</span></td>
<td style="text-align: left;">other-real-analytic-nonintegrality</td>
</tr>
<tr>
<td style="text-align: left;">LCM cone-nonflat supply (sharpest depth-reduced form)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∃</span> unbounded-scale menu <span class="math inline"><em>Q</em></span> with <code>coneNonflatCert</code> firing</td>
<td style="text-align: left;">other-lcm-cone-menu</td>
</tr>
<tr>
<td style="text-align: left;">first-harmonic norm-gap supply</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> &gt; 0 ∀<em>X</em><sub>0</sub> ∃<em>X</em> ≥ max (<em>X</em><sub>0</sub>, 1) ∃<em>L</em></span>, room <span class="math inline">16(2<em>X</em> + <em>h</em> + <em>L</em> + 2) ≤ 2<sup><em>L</em></sup></span></td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;">prime-jump sharp-kill supply</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∀<em>t</em><sub>0</sub> ∃<em>t</em> ≥ <em>t</em><sub>0</sub> ∃<em>p</em>, <em>L</em> &gt; 0</span></td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;"><span class="math inline"><em>a</em></span>-exponent short-arithmetic kill supply (the open trigger)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em><sub>0</sub> ∃<em>a</em> <em>L</em>, <em>a</em><sub>0</sub> ≤ <em>a</em> ∧ <em>L</em> &lt; 2 ⋅ 2<sup><em>a</em></sup></span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">actual-orbit separation supply</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;">cofinal <span class="math inline">1/32+</span>error separation at guarded odd ranks</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">top-edge-residue-gap sufficiency chain (5 links, weakest first)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∀<em>a</em><sub>0</sub> ∃<em>a</em> ≥ <em>a</em><sub>0</sub> ∃⟨supply predicate⟩</span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">rational countermodel refutes {bound,parity,aperiodicity}</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∃<em>c</em> : ℕ → ℕ</span>, <span class="math inline"><em>c</em> ≤ 6</span>, <span class="math inline"><em>c</em> ≤ <em>n</em></span>, <span class="math inline"><em>c</em> ≡ <em>φ</em>   (mod  2)</span>, arbitrarily-separated blocks</td>
<td style="text-align: left;">binary-digit</td>
</tr>
<tr>
<td style="text-align: left;">mod-4 pulse cofinal supply (via CRT+Dirichlet)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∀<em>h</em> &gt; 0 ∀<em>B</em> ∃prime <em>p</em> &gt; <em>B</em></span></td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">mod-4 pulse survivor kill (fourfold reduction)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;">given CP-05’s cofinal supply</td>
<td style="text-align: left;">mobius-mersenne</td>
</tr>
<tr>
<td style="text-align: left;">two-adic pulse at arbitrary depth <span class="math inline"><em>K</em></span></td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∀<em>K</em> ≥ 2 ∀<em>H</em> &gt; <em>K</em> ∀<em>B</em> ∃cofinally many primes <em>p</em> &gt; <em>B</em></span></td>
<td style="text-align: left;">p-adic</td>
</tr>
<tr>
<td style="text-align: left;">two-adic pulse transfer (needs eventual integrality)</td>
<td style="text-align: left;"></td>
<td style="text-align: left;">cofinal</td>
<td style="text-align: left;"><span class="math inline">∀<em>K</em> ≥ 2</span>, given TA-01 pulse <span class="math inline">+</span> eventual integrality</td>
<td style="text-align: left;">p-adic</td>
</tr>
</tbody>
</table>

</div>

$`^\dagger`$ The source normal-form table tags `actualLcmTailDiff_shift_pos` <span class="sans-serif">scale:bounded</span> because the window parameter $`J`$ is finite-range relative to $`2\cdot2^a`$; the exponent $`a`$ itself is completely unbounded ($`\forall a\ge 8`$), and this row’s constants ($`4`$, $`8`$, $`32`$) do not degrade with $`a`$. It is flagged here, not silently re-tagged, because it is exactly the kind of row an automated promotion sweep must not misclassify — see the audit below.

<a id="checked-negative-result-no-free-promotion-from-bounded-to-cofinal"></a>

## Checked negative result: no free promotion from bounded to cofinal

A ladder like the one above invites an obvious question: is any <span class="sans-serif">scale:bounded</span> result actually uniform in disguise, so that removing its threshold is a routine generalisation rather than new mathematics? This was checked directly rather than assumed. An audit read the Lean proof body behind every bounded-scale result in the \#249 corpus — eighteen candidates in total, spanning the near-miss list against the \#249-supply obligation catalogued in the interface index (fourteen rows, each independently checked against the exact cofinal target it is closest to) together with the remaining bounded/fixed rows in the certificate, Möbius–Lambert, and actual-orbit banks above — and found **no** bounded result whose proof is uniform enough in its threshold parameter to promote to cofinal or uniform for free. Every candidate failed for one of three reasons, and the failure mode is worth recording because it is a checked negative result, not an absence of search:

1.  **Finite certificate tables.** Results such as (28 explicit values of $`t`$ through $`t{=}64`$, now a strict subset of the aggregate $`\forall t\le82`$ band), ($`h\in[1,8]`$ at fixed depth 16), and ($`h\in[1,16]`$ at exponent 14) are each a finite *list* of independently verified rows, not a single argument instantiated at a free parameter. There is no uniform proof underneath to strip the bound from; each new row is a fresh finite computation.

2.  **`interval_cases`/`decide` over a bounded range.** Results such as ($`a{\ge}8`$) and the entire /top-edge-staircase family (room conditions of the shape $`J{+}(a{+}6){<}2\cdot2^a`$) are proved by case-splitting a residue or a divisor structure that is only exhaustively enumerable inside the stated range; the mathematical content genuinely narrows as the range widens, so `decide` cannot simply be re-run at a larger bound without an exponential blow-up in the search space it certifies.

3.  **Constants that degrade with the parameter.** The clearest instance is the echo-versus-height wall (prose:echo_versus_height_two_front_wall, §5e–5f of the ambitious-modular-route note): height-optimal ladder families pay quadratic height $`P(1)\sim 2^{K^2/2}`$ matching ’s own growth rate, while height-minimal integer-relation minimizers regrow the echo term $`E_R`$ to match — for every tested family, the two costs cannot both be driven to zero as the scale parameter grows. The interface index records the same phenomenon for `HalfRung`$`(J)`$-shaped truncation rungs: the certificate window $`B(J)`$ is driven by $`L_J=\mathrm{lcm}(2,\dots,J)`$, which grows super-exponentially in $`J`$, so the per-$`J`$ constant degrades with the very parameter the cofinal claim needs to range over — “the hallmark of a proof that does not survive bound removal” (interface index, row `d-3a/d-3b`).

None of the fourteen near-miss rows against the \#249-supply obligation is closed by a scale argument alone either: reading each one’s own recorded `exact_mismatch` shows the residual gap is a missing *arithmetic input* (a constant-saving Weyl-sum bound for `e1-companion`; a one-sided top-edge residue gap for `TE-04`/`TE-05-weakest`), never a generalisable proof technique sitting one `omega` call away from cofinal. The one row where the source tag itself is imprecise — `SGN-01`, marked <span class="sans-serif">scale:bounded</span> even though its underlying exponent $`a`$ is unbounded, see $`^\dagger`$ above — is precisely the kind of false positive the audit was built to catch, and even there what remains open is the *other* half of the certificate band (the top-edge residue), not a scale defect in SGN-01 itself.

<a id="coordinate-atlas-and-transport-maps"></a>

# Coordinate atlas and transport maps

\#249 is not proved or disproved in a single representation. The corpus expresses $`S=\sum_{n\ge1}\varphi(n)/2^n`$ in at least eight distinct coordinates, and the central methodological lesson of the whole programme — flagged repeatedly in the source banks as AP17/AP18, “obstructions are coordinate-relative” — is that a mechanism which kills a proof strategy in one coordinate can be silent, or even actively helpful, in another. This section lists every coordinate used, gives at least one exact transport map out of it into another coordinate with its Lean site, and then makes the coordinate-relativity claim precise for the one pair where it matters most: binary-digit versus Möbius–Mersenne.

<div class="description">

$`S`$ as the literal base-2 expansion object: `totientTail`, `windowDiscrepancy`, `certifiedKill`. *Transport to mobius-mersenne:* the core identity
``` math
S=\sum_{n\ge1}\frac{\varphi(n)}{2^n}=\frac12+\sum_{d\ge1}\frac{\mu(d)}{(2^d-1)^2}
```
proved by (consumed at ) turns every binary-digit statement about $`S`$ into a statement about a squared Möbius–Mersenne Lambert series, and back.

$`S`$ as $`\tfrac12+\sum_d\mu(d)/(2^d-1)^2`$, the Lambert ladder $`L(w)=\sum_n w(n)/(2^n-1)`$ at $`w=\mu,1,\varphi`$, and the whole cyclotomic denominator-survival chain built on it. *Transport to cyclotomic:* evaluating the Möbius-numerator polynomial at $`x=2`$, together with the definition , moves the squared-denominator question into finite cyclotomic-polynomial arithmetic over $`\mathbb{Z}`$.

$`S-\tfrac12=\Pr(\gcd(X,Y)=1)`$ for independent fair-coin waiting times $`X,Y`$. *Transport from mobius-mersenne:* the gcd-divisibility factorisation ($`\Pr(d\mid X\wedge d\mid Y)=1/(2^d-1)^2`$) together with the reduced-direction law converts the squared-Lambert sum into a probability mass, and the independently-built gives the same bridge from the totient generating function directly.

The T1–T6 chain: `mobiusNumeratorPolynomial`, its coefficients (an exact divisor-counting formula, ), cyclotomic-value survival (), and prime-power jump dynamics. *Transport to mobius-mersenne (denominator growth):* the upper-half prime-channel survival theorem feeds directly into the exact denominator-growth formula in the Möbius–Mersenne coordinate.

Fixed and growing 2-adic valuation-unit dynamics: the adelic height/denominator-tax law, the tropical fixed-precision no-go, the signed-Hankel terminal-parity engine, the two-adic pulse-block construction. *Transport to farey:* the scalar-localisation complement-dvd law together with the Mersenne-height corollary ($`2^r\mid|x.\mathrm{num}|\wedge x<2/(2^n-1)\Rightarrow 2^r(2^n-1)<2\cdot x.\mathrm{den}`$) is exactly a denominator lower bound of the same shape the Farey coordinate proves directly.

Unimodular denominator exclusion: and the committed $`K{=}240`$ window certificate giving $`S\ne p/q`$ for every $`q\le Q_0\approx7.96\times10^{34}`$. *Transport to binary-digit:* the window bound is built directly from a committed $`2^{240}`$-scale totient residue $`V`$ for the window $`(N,K)=(1,240)`$ — a binary-digit object — via , which shows the bound is sharp at exactly the mediant $`b_K+d_K`$.

The `periodLcm`/LCM-diagonal/LCM-cone family: , , the multiplicative ray split, and the cone-flatness/cone-nonflat producers. *Transport to binary-digit:* the identity and identifies the LCM-ray letter literally with a `deltaTotient`/`windowDiscrepancy` value, so every LCM-orbit statement is, term for term, a binary-digit statement in disguise.

Weyl-sum block cancellation over the totient window discrepancy: and the unconditional companion at (any constant-saving cancellation, via $`\cos(\pi/8)>9/10`$ plus pigeonhole, forces a finite kill certificate). *Transport to binary-digit:* by construction the exponential sum is literally $`\sum_N \cos\bigl(2\pi\cdot(\texttt{windowDiscrepancy}\ h\ N\ L \bmod 2^L)/2^L\bigr)`$ — a first-harmonic statistic *of* the binary-digit residue, so a norm-gap in this coordinate is definitionally a statement about `windowDiscrepancy`.

</div>

<a id="obstructions-are-coordinate-relative-the-binary-digit-vs.-möbiusmersenne-case"></a>

## Obstructions are coordinate-relative: the binary-digit vs. Möbius–Mersenne case

The clearest instance of coordinate-relative obstruction in the whole \#249 corpus is the fate of the classical Erdős (1948) near-integer digit method. That method needs, in essence, a finite automaton: a bounded amount of state carried forward from one digit block to the next, so that the value of a far-away digit block can be recovered from a bounded summary of everything before it. In the binary-digit coordinate this is exactly what fails, and it fails as a proved Lean theorem, not a heuristic remark: shows that for a balanced-pulse family of radius $`m`$, any finite `State` type collapsing the family to a single autonomous summary must satisfy $`|\mathrm{State}|\ge\lfloor m/2\rfloor+2`$ — unbounded in $`m`$ — so no finite-state decoder can recover the shift $`r`$ from its collapsed state (<span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:uniform</span>, coordinate `binary-digit`).

This is the formal shadow of the elementary facts that $`0\le\varphi(n)\le n`$, that $`\varphi`$ is unbounded, and that $`\varphi`$ has average order $`\tfrac6{\pi^2}n`$, equivalently $`\sum_{k\le x}\varphi(k)\sim\tfrac3{\pi^2}x^2`$ (<span class="sans-serif">\[Math\]</span>), rather than any false pointwise estimate $`\varphi(n)=\Theta(n)`$: the digit-window discrepancy `windowDiscrepancy`$`\,h\,N\,L`$ genuinely needs $`\Omega(m)`$ bits of state to track as $`N`$ grows, which is exactly why \#249’s own binary-digit engine is forced into a *cofinal certificate supply* () rather than a single finite-state argument: the same shape of no-go recurs at (locked gauge defeats residual-blind rank certificates for the first-harmonic pivot) and at (the dyadic totient-kernel span is genuinely infinite-rank, not compressible to any fixed dimension).

The Möbius–Mersenne coordinate does not carry this obstruction, because it is built on a coefficient sequence, $`\mu(d)\in\{-1,0,1\}`$, that is bounded rather than growing with $`d`$. The squared-Lambert transfer engine takes any weight with $`|w(d)|\le d`$ — $`\mu`$ trivially qualifies with room to spare — and converts it into a divisor-convolution power series for free; no finite-state decoder is ever needed because the relevant recursion (the cyclotomic T1–T6 chain: through ) is a finite, exact polynomial identity at every squarefree radical $`r`$, uniform in $`r`$, with no growth-driven state explosion.

This is precisely why the corpus’s strongest *unconditional* denominator result — the exact-value and lower-bound formulas of and — lives entirely in the Möbius–Mersenne coordinate and is scale-`uniform`, while the sharpest *conditional* route in the binary-digit coordinate is scale-`cofinal` and unclosed. The two coordinates are not equivalent representations of the same difficulty: the wall each one hits is a fact about that coordinate’s own state-growth, not about \#249 itself, which is exactly the AP17/AP18 discipline this corpus was built to enforce — before reporting an obstruction, name the coordinate it was measured in, and test whether a re-representation removes it.

<a id="frontier-index-what-stands-between-the-corpus-and-a-proof"></a>

# Frontier index: what stands between the corpus and a proof

This section is the join layer of the paper. Parts I–II inventory what the corpus proves; this part inventories, obligation by obligation, exactly what is *missing* to turn each proved reduction into a proof of Erdős \#249, in a form usable as a premise without opening the Lean tree. Erdős \#249 asks whether $`S = \sum_{n\ge 0} \varphi(n)/2^n`$ is irrational. It is OPEN. Nothing in this section decides it. Every row below either (a) states a proved theorem exactly, or (b) states an unproved but well-posed proposition (an *open producer* or *open supply*) together with the exact proved consumer that would turn it into irrationality of $`S`$.

<a id="reading-this-index"></a>

## Reading this index

Every entry follows the same discipline. **Yields**: the exact statement proved, with quantifiers in their proved order. **Exact mismatch**: precisely where the proved statement falls short of the open obligation it is compared against — never “it doesn’t work,” always the named axis of shortfall. **What would close it**: the exact remaining proposition, stated in full, whose proof (via the cited Lean consumer, already on disk) proves $`\mathrm{Irrational}(S)`$.

Each numbered claim carries three tags. <span class="sans-serif">scale:fixed</span> means proved at finitely many explicit numerals with no argument in the growing parameter; <span class="sans-serif">scale:bounded</span> means proved on a bounded range of a parameter that is itself unbounded elsewhere in the statement; <span class="sans-serif">scale:uniform</span> means proved for *every* value of the relevant parameter (the strongest positive tag short of matching the open target); <span class="sans-serif">scale:cofinal</span> means the statement itself has the shape $`\forall a_0\ \exists a\ge
a_0`$, i.e. it is exactly the quantifier shape the open obligation needs; <span class="sans-serif">scale:n/a</span> applies to structural non-existence results with no growing parameter. The evidence tags are <span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">\[Cert\]</span>, <span class="sans-serif">\[Math\]</span>, <span class="sans-serif">\[Cited\]</span>, <span class="sans-serif">\[Open\]</span>, used exactly as defined in Part I.

The canonical open obligation for \#249, proved in Part II to be sufficient (), is the **249-supply** obligation:
``` math
\forall h \ge 1,\ \forall N_0,\ \exists N \ge N_0,\ \exists L,\ \mathtt{certifiedKill}\ h\ N\ L .
```
Fourteen near-miss rows are catalogued against it below: one headline row (the sharpest reduction in the corpus, given its own subsection) and thirteen further rows, each attacking the same obligation from a different coordinate.

<a id="ssec:headline"></a>

## The headline: \#249 reduces to a single unsupplied exponential-sum bound

The following two definitions, verified against the live Lean tree in this session, are the sharpest statement of the \#249 frontier that the corpus contains.

<div class="defn">

**Definition 213** (Window discrepancy). . For $`h,N,L\in\mathbb N`$,
``` math
A_{h,N,L} \;=\; \sum_{j=0}^{L-1} \bigl(\varphi(N+h+1+j) - \varphi(N+1+j)\bigr)\cdot 2^{\,L-1-j}
  \ \in \mathbb Z .
```
This is the depth-$`L`$ truncation of $`2^L\cdot(R_{N+h}-R_N)`$, where $`R_N = \sum_{j\ge 1}\varphi(N+j)/2^j`$ is the local totient tail ().

</div>

<div class="defn">

**Definition 214** (Certified kill). .
``` math
\mathtt{certifiedKill}\ h\ N\ L \;:\Leftrightarrow\;
  (N{+}h{+}L{+}2) < A_{h,N,L}\bmod 2^L < 2^L - (N{+}h{+}L{+}2).
```
That is: the residue of $`A_{h,N,L}`$ modulo $`2^L`$ avoids the radius-$`(N{+}h{+}L{+}2)`$ neighbourhood of $`0`$. records the necessary room condition this forces: $`2(N{+}h{+}L{+}2) < 2^L`$.

</div>

<div class="defn">

**Definition 215** (First-harmonic real and complex characters). and :
``` math
\mathtt{windowFirstCos}\ h\ N\ L = \cos\!\Bigl(2\pi\,\tfrac{A_{h,N,L}\bmod 2^L}{2^L}\Bigr),\qquad
  \mathtt{windowFirstExp}\ h\ N\ L = \exp\!\Bigl(i\,2\pi\,\tfrac{A_{h,N,L}\bmod 2^L}{2^L}\Bigr).
```
records $`\mathrm{Re}(\mathtt{windowFirstExp})
= \mathtt{windowFirstCos}`$ and that $`\|\mathtt{windowFirstExp}\,h\,N\,L\| = 1`$: this is literally the first additive character of the endpoint discrepancy modulo $`2^L`$, a standard exponential-sum object.

</div>

<div id="thm:hgap-real" class="thm">

**Theorem 216** (Real-part certificate consumer). *. <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span>. `coord:first-harmonic`. For all $`h,X,L`$ with $`0<X`$ and the room condition $`16(2X{+}h{+}L{+}2)\le 2^L`$, if
``` math
\sum_{N=X}^{2X-1} \mathtt{windowFirstCos}\ h\ N\ L \;\le\; \tfrac{9}{10}\,X ,
```
then $`\exists N\in[X,2X)`$ with $`\mathtt{certifiedKill}\ h\ N\ L`$.*

</div>

<div id="thm:hgap-subset" class="thm">

**Theorem 217** (Subset consumer — no density or partition hypothesis). *. <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span>. `coord:first-harmonic`. For any nonempty finite $`T\subseteq\mathbb N`$ with $`T\subset[0,2X)`$ and the same room condition, if
``` math
\sum_{N\in T} \mathtt{windowFirstCos}\ h\ N\ L \;\le\; \tfrac{9}{10}\,|T| ,
```
then $`\exists N\in T`$ with $`\mathtt{certifiedKill}\ h\ N\ L`$. This is strictly stronger than Theorem <a href="#thm:hgap-real" data-reference-type="ref" data-reference="thm:hgap-real">216</a>: $`T`$ can be *any* explicitly chosen nonempty finite subset of the dyadic block, not the whole block, and the proof (an averaging pigeonhole, §below) never uses that $`T`$ has positive density or comes from a partition.*

</div>

<div id="thm:hgap-norm" class="thm">

**Theorem 218** (Complex norm consumer and the open producer). *and . <span class="sans-serif">\[Lean\]</span> for both implications; the hypothesis $`DTWFirstHarmonicNormGap`$ is <span class="sans-serif">\[Open\]</span>. The complex norm bound is strictly stronger than the real-part bound ($`|z|\ge\mathrm{Re}(z)`$, and $`21/25 < 9/10`$ absorbs the slack), so it composes through Theorem <a href="#thm:hgap-real" data-reference-type="ref" data-reference="thm:hgap-real">216</a> to the same certificate. Define
``` math
\mathtt{DTWFirstHarmonicNormGap} :\Leftrightarrow\;
  \forall h{>}0\ \forall X_0\ \exists X, L,\ \max(X_0,1)\le X\ \wedge\ 16(2X{+}h{+}L{+}2)\le 2^L\ \wedge
```
``` math
\Bigl\|\ \sum_{N=X}^{2X-1}\mathtt{windowFirstExp}\ h\ N\ L\ \Bigr\| \;\le\; \tfrac{21}{25}\,X .
```
`coord:first-harmonic`. <span class="sans-serif">scale:cofinal</span> (this is the open target itself). Then
``` math
\mathtt{DTWFirstHarmonicNormGap} \;\Longrightarrow\; \mathrm{Irrational}\Bigl(\sum_{n\ge 0}
  \tfrac{\varphi(n)}{2^n}\Bigr),
```
proved in full, with no further gap, by chaining Theorem <a href="#thm:hgap-norm" data-reference-type="ref" data-reference="thm:hgap-norm">218</a>$`\to`$Theorem <a href="#thm:hgap-real" data-reference-type="ref" data-reference="thm:hgap-real">216</a>$`\to`$ .*

</div>

<div id="obs:no-instance" class="obs">

*Observation 219* (The exact negative). No instance of $`\mathtt{DTWFirstHarmonicNormGap}`$’s hypothesis, nor of $`hgap`$ in Theorems <a href="#thm:hgap-real" data-reference-type="ref" data-reference="thm:hgap-real">216</a>–<a href="#thm:hgap-subset" data-reference-type="ref" data-reference="thm:hgap-subset">217</a>, is proved anywhere in the corpus, at any $`h`$, $`X`$, $`L`$. <span class="sans-serif">\[Open\]</span> is exact, not conservative rounding. The two consumer theorems that *use* the subset form (Theorem <a href="#thm:hgap-subset" data-reference-type="ref" data-reference="thm:hgap-subset">217</a>) are conditional consumers, not a supply: instantiates $`T`$ as the explicit two-element set $`\{N,M\}`$ (`apply exists_certifiedKill_of_first_harmonic_gap_subset ({N, M} : Finset Nat)`). The two call sites in and use, respectively, an arbitrary supplied finite set $`T`$ and the explicit singleton $`\{N\}`$; neither call site supplies such a set or discharges its harmonic-gap hypothesis. There is no theorem anywhere in the corpus that discharges $`hgap`$ at a single instance, let alone cofinally.

</div>

<div class="rem">

*Remark 220* (Why this is the sharpest reduction, and why it is tractable). This reduction converts the open producer for \#249 from certificate-supply language — “exhibit a certified kill $`(N,L)`$” — into a *constant-saving cancellation estimate for the first additive character of the totient window discrepancy over a dyadic block*: exactly the shape of a classical exponential-sum bound in analytic number theory (a Weyl-type estimate for $`\sum_N e(\theta_N)`$). Three features make this genuinely the narrowest gap in the corpus.

First, the saving required is a *constant*, not $`o(X)`$: $`21/25`$ (complex norm) or $`9/10`$ (real part), fixed independent of $`h`$, $`X`$, $`L`$. Any nontrivial cancellation estimate — even one far weaker than square-root cancellation — would suffice; this is not asking for GRH-strength input.

Second, the room condition $`16(2X{+}h{+}L{+}2)\le 2^L`$ forces only $`L \gtrsim \log_2 X + 5`$, which is satisfiable for every $`X`$ by simply taking $`L`$ large enough (the depth floor grows logarithmically in $`X`$, not polynomially); no scale obstruction of the kind documented elsewhere in this paper (e.g. the $`\sqrt{2\log_2 N}`$ silent-position defect for \#257, Part I) stands in the way of the producer’s own room requirement.

Third, the subset form (Theorem <a href="#thm:hgap-subset" data-reference-type="ref" data-reference="thm:hgap-subset">217</a>) removes even the requirement that the cancellation happen on the whole dyadic block or a positive-density subset of it: any single explicitly named finite $`T`$ with the averaged bound would do. In particular a supplier-fibre or sparse-subsequence argument — e.g. picking $`N`$ to be one less than a prime, as the exact pivot algebra in already sets up via `pivotArgument`, `pivotPrime`, `pivotSupplierBases` — is a legitimate route to this obligation and does not need to control the discrepancy on a full interval.

</div>

<a id="row-by-row-the-remaining-near-misses-against-249-supply"></a>

## Row-by-row: the remaining near misses against 249-supply

The headline (§<a href="#ssec:headline" data-reference-type="ref" data-reference="ssec:headline">9.2</a>) is row **e1-companion** of the source interface catalogue in full. The remaining thirteen rows below attack the same 249-supply obligation from independent coordinates in the Lean tree: the actual-LCM sign corridor, the top-edge staircase, the raw rational approximant, the short-window arithmetic word, the diagonal pincer certificate bank, the $`h`$-uniform single-window certificate, the Farey/continued-fraction denominator growth law, the 2-adic pulse block, the LCM-jump slack scalar, the prime-jump commutator, the Möbius–Mersenne denominator channel, and the carry-kernel rank. None of them is closed; each is recorded with its exact remaining content.

<a id="sgn-01-the-positive-sign-half-of-the-certified-kill-band-coordactual-lcm-sign"></a>

### SGN-01 — the positive-sign half of the certified-kill band (`coord:actual-lcm-sign`)

<div class="defn">

**Definition 221**. The *actual LCM tail orbit* at exponent $`a`$ is $`\mathtt{actualLcmTailOrbit}\ a = R_{2H+2H} - R_{H+... }`$, precisely $`\mathrm{totientTail}(2H)-\mathrm{totientTail}(H)`$ where $`H = \mathtt{periodLcm}(2^a)`$ ().

</div>

<div class="thm">

**Theorem 222**. *and . <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span>. For every $`a\ge 8`$ and every $`J`$ with $`J+(a{+}6) < 2\cdot 2^a`$,
``` math
0 \;<\; \mathrm{totientTail}(2H{+}J) - \mathrm{totientTail}(H{+}J), \qquad H=\mathtt{periodLcm}(2^a).
```
Hence $`0 < \mathtt{actualLcmTailOrbit}\ a`$ for every $`a\ge 8`$. The proof is genuinely uniform in $`a`$: it rests on two facts proved for all $`a\ge 8`$ by a two-case structural split (divisor letter vs. foreign prime power), with absolute constants $`4,8,32`$ and no lookup table — and .*

</div>

<div class="rem">

*Remark 223* (Exactly half the certificate band, and where the other half goes). $`\mathtt{certifiedKill}`$ needs the residue to avoid a *symmetric* radius-$`(N{+}h{+}L{+}2)`$ neighbourhood of $`0`$ on both sides. SGN-01 gives positivity only. Its companion proves that, under integrality, the consequence is not a kill but the opposite: the residue is forced to the *top edge*, exactly $`2^K - e`$ where $`e`$ is the true carry orbit (). So the lower half of the certified-kill band is discharged unconditionally and cofinally by SGN-01; the upper half is untouched, and what remains open is a genuinely different, one-sided statement about the top edge — row TE-04 below. The corpus’s own normal-form tables tag this row <span class="sans-serif">scale:bounded</span>; that tag is misleading, since only the window offset $`J`$ is bounded relative to the height, and the height $`2\cdot 2^a`$ itself is unbounded: the correct tag is <span class="sans-serif">scale:uniform</span>.

</div>

<a id="te-04-the-one-sided-top-edge-staircase-coordactual-lcm-top-edge"></a>

### TE-04 — the one-sided top-edge staircase (`coord:actual-lcm-top-edge`)

This is the sharpest *landed weakening* of the 249-supply obligation in the corpus: the symmetric certified-kill band is replaced by a single upper inequality, halving the information the open producer must supply.

<div class="thm">

**Theorem 224** (Consumers, fully proved). *, , . <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span>. For every $`a\ge 8`$ and every $`J,K,m`$ inside the sign corridor ($`J{+}K{+}(a{+}6) < 2\cdot 2^a`$), a one-sided residue gap at precision $`m\le K`$ — room $`2H{+}J{+}K{+}2 < 2^m`$ and $`A_{H,H+J,K}\bmod 2^m \le 2^m - (2H{+}J{+}K{+}2)`$ — already forces $`\mathrm{totientTail}(2H{+}J) - \mathrm{totientTail}(H{+}J)\notin\mathbb Z`$. No lower margin at all is demanded. The proof chain is complete: the theorem holds for every $`a\ge 8`$, and *$`\mathtt{PowerTwoActualLcmTopEdgeResidueGapSupply}`$ $`\Rightarrow`$ Irrational $`S`$* is proved.*

</div>

<div class="defn">

**Definition 225** (The open producer). . <span class="sans-serif">\[Open\]</span>. <span class="sans-serif">scale:cofinal</span>.
``` math
\forall a_0\ \exists a,K,m,\ a_0\le a\ \wedge\ 8\le a\ \wedge\ K{+}(a{+}6)<2\cdot 2^a\ \wedge\
  \mathtt{ActualLcmTopEdgeResidueGap}\ a\ 0\ K\ m .
```
No unconditional statement anywhere in the corpus locates the residue of the diagonal word $`A_{H,H,K}`$ (where $`H=\mathtt{periodLcm}(2^a)`$) below the top strip at even one large $`a`$. further reduces the condition to the last $`m`$ arithmetic letters of the word alone.

</div>

<div id="prop:te-chain" class="prop">

**Proposition 226** (The five strictly weaker sufficient links — proving any one closes \#249). *All five are proved sufficient for in the same module, and each is *strictly weaker* in the sense that it drops a hypothesis, widens a band, or asks only for magnitude rather than a signed inequality.*

1.  *(<span class="sans-serif">\[Open\]</span>, <span class="sans-serif">scale:cofinal</span>):
    ``` math
    \forall a_0\ \exists a,m,\ a_0\le a \wedge 8\le a \wedge m{+}1{+}(a{+}6)<2\cdot 2^a \wedge
          2H{+}m{+}3 < 2^m \wedge
    ```
    ``` math
    2H{+}m{+}2 \le \mathtt{diagonalAdjacentSuffixResidue}(2^a)\,0\,m \le 2^m - (2H{+}m{+}2)
    ```
    (a two-sided band on the adjacent-suffix residue directly, one candidate depth $`m`$).*

2.  *(<span class="sans-serif">\[Open\]</span>, <span class="sans-serif">scale:cofinal</span>): at the odd guarded depth $`2q{+}1`$, a two-sided band of half-width $`H{+}q{+}2`$ on the half-word residue mod $`4^q`$ — “substantially weaker than the older fixed $`1/32`$ central band.”*

3.  *(<span class="sans-serif">\[Open\]</span>, <span class="sans-serif">scale:cofinal</span>), *proved equivalent* to the previous one via :
    ``` math
    \forall a_0\ \exists a,q,\ \max(14,a_0)\le a \wedge \mathtt{oddGuardedCanonicalAdjacentSuffixDepth}(2^a)=2q{+}1
          \wedge H{+}q{+}2 \le |\mathtt{actualOddHalfCenteredLift}\ a\ q| .
    ```*

4.  *(<span class="sans-serif">\[Open\]</span>, <span class="sans-serif">scale:cofinal</span>): the same magnitude bound with the depth restriction relaxed from “canonical guarded” to any odd $`2q{+}1`$ satisfying the half-cell fit $`2(H{+}q{+}2)\le 4^q`$ and the sign-corridor room $`2q{+}2{+}(a{+}6)<2\cdot 2^a`$.*

5.  *— the weakest of all five; treated separately as row TE-05-weakest below.*

*Proving *any one* of these five closes Erdős \#249; the corpus has already proved all the implications from each to (chain: midband $`\to`$ residue-gap at ; half-word-band $`\to`$ midband at ; final-magnitude $`\Leftrightarrow`$ half-word-band at ; flexible-magnitude $`\to`$ midband at ; final-magnitude $`\to`$ flexible-magnitude at ).*

</div>

<a id="te-05-weakest-one-scalar-inequality-at-cofinally-many-odd-ranks-coordactual-lcm-top-edge"></a>

### TE-05-weakest — one scalar inequality at cofinally many odd ranks (`coord:actual-lcm-top-edge`)

This is the weakest landed link in the whole \#249 sufficiency lattice: a single comparison between one terminal arithmetic letter and twice a centred lift.

<div class="defn">

**Definition 227**. . <span class="sans-serif">\[Open\]</span>. <span class="sans-serif">scale:cofinal</span>. Writing $`H=\mathtt{periodLcm}(2^a)`$,
``` math
\forall a_0\ \exists a,q,\ a_0\le a \wedge 8\le a \wedge 2q{+}2{+}(a{+}6)<2\cdot 2^a \wedge
  2(H{+}q{+}2)\le 4^q \wedge
```
``` math
\mathtt{diagonalWindowIncrement}(2^a)(2q{+}2) \;\le\; 2\cdot \mathtt{actualOddHalfCenteredLift}\ a\ q .
```

</div>

<div class="thm">

**Theorem 228** (Consumer). *and . <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span>. The dominance hypothesis at a single odd rank already excludes integrality of $`\mathtt{actualLcmTailOrbit}\ a`$, and the supply predicate composes to $`\mathrm{Irrational}(S)`$.*

</div>

<div id="obs:staircase-tension" class="obs">

*Observation 229* (The exact identity, and the internal tension it exposes). . <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span>. For $`a\ge 8`$, room $`2q{+}1{+}1{+}(a{+}6)<2\cdot2^a`$, half-cell fit $`2(H{+}q{+}2)\le 4^q`$, and any integral representative $`z`$ with $`z = \mathtt{actualLcmTailOrbit}\ a`$:
``` math
2\cdot \mathtt{actualOddHalfCenteredLift}\ a\ q
  \;=\; \mathtt{diagonalWindowIncrement}(2^a)(2q{+}2) - \mathtt{carryOrbit}\ H\ H\ z\ (2q{+}1) .
```
This is an *exact equality*, not a bound. Comparing it against the dominance inequality above, *the dominance inequality is literally equivalent to $`\mathtt{carryOrbit}\,H\,H\,z\,(2q{+}1)\le 0`$*.

But SGN-02 (, <span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:uniform</span>) proves that under integrality the true carry orbit is *strictly positive* throughout this exact corridor: for $`a\ge 8`$ and $`J{+}K{+}(a{+}6)<2\cdot 2^a`$,
``` math
0 < \mathtt{carryOrbit}\ H\ (H{+}J)\ d\ K
```
whenever $`d`$ is the real-valued representative of the translated tail difference.

So the two branches of the corridor-escape disjunction that offers are *not* symmetric: SGN-02 has already eliminated the branch that the identity most naturally supplies (dominance, $`\mathtt{carryOrbit}\le 0`$), and the surviving branch is the *lower* escape
``` math
2\cdot \mathtt{actualOddHalfCenteredLift}\ a\ q \;\le\;
  \mathtt{diagonalWindowIncrement}(2^a)(2q{+}2) - (2H{+}2q{+}3) .
```

This is stated precisely so the reader can check it: it is neither a refutation of the dominance route (SGN-02 constrains the sign of $`\mathtt{carryOrbit}`$, it does not itself bound $`\mathtt{diagonalWindowIncrement}`$ or $`\mathtt{actualOddHalfCenteredLift}`$ against $`0`$, so dominance is not shown *false*, only shown to entail a carry-orbit sign the census never violates) nor a proof (no theorem excludes dominance outright). It is the precise reason the finite census keeps landing just inside the corridor rather than outside it, and it identifies the lower-escape branch as the coordinate where a producer is actually needed.

</div>

<div class="prop">

**Proposition 230** (What would close it). *Either (i) the lower-escape branch cofinally — as displayed just above — or (ii) the two-sided magnitude form (item 4 of Proposition <a href="#prop:te-chain" data-reference-type="ref" data-reference="prop:te-chain">226</a>), which asks only $`H{+}q{+}2 \le
|\mathtt{actualOddHalfCenteredLift}\ a\ q|`$ and which the file proves () implies corridor escape via a clean sign split (positive branch escapes above the terminal letter, negative branch escapes below the directed bound), sidestepping the SGN-02 tension entirely because it does not commit to a sign for the centred lift.*

</div>

<a id="sep-02-separation-from-an-explicit-rational-approximant-coordraw-approximant"></a>

### SEP-02 — separation from an explicit rational approximant (`coord:raw-approximant`)

<div class="thm">

**Theorem 231**. *and . <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span>. Unconditionally, for every $`a`$ and $`q`$,
``` math
\bigl|\, \mathtt{actualLcmTailOrbit}\ a - \mathtt{actualLcmRawApprox}\ a\ q \,\bigr|
  \;<\; \frac{4H + 2(2q{+}1) + 4}{2^{2q+2}} ,
```
where $`\mathtt{actualLcmRawApprox}\ a\ q`$ is an explicit finite computable rational block. The error radius is uniform in $`a`$ and $`q`$ and decays like $`H/4^q`$: the analytic tail is fully discharged.*

</div>

<div class="rem">

*Remark 232*. Consequently a cofinal $`1/32`$-separation of the raw approximant from every integer suffices for \#249. The corpus verifies the analogous kill *unconditionally* at exactly two exponents, $`a=4`$ and $`a=6`$ (, <span class="sans-serif">\[Cert\]</span>, <span class="sans-serif">scale:fixed</span>, via and ). Nothing beyond $`a=6`$ is proved. The depth $`q`$ is not free: the supply predicate pins $`2q{+}1 =
\mathtt{oddGuardedCanonicalAdjacentSuffixDepth}(2^a)`$, so per scale $`a`$ there is exactly one admissible depth, not a search over depths.

</div>

<div class="defn">

**Definition 233** (What would close it). $`\mathtt{PowerTwoActualLcmOrbitSeparationSupply}`$: <span class="sans-serif">\[Open\]</span>, <span class="sans-serif">scale:cofinal</span>.
``` math
\forall a_0\ \exists a\ge\max(2,a_0)\ \exists q,\
  \mathtt{oddGuardedCanonicalAdjacentSuffixDepth}(2^a)=2q{+}1 \wedge
```
``` math
\forall z\in\mathbb Z,\ \tfrac1{32} + \mathtt{actualLcmRawErrorRadius}\ a\ q \;\le\;
  |\mathtt{actualLcmTailOrbit}\ a - z| .
```
Since the error radius is explicit, this reduces to a distance-to-nearest-integer lower bound for one explicitly computable rational per scale — the cleanest reduction of the \#249 obligation to a purely finite, computable question in the whole corpus.

</div>

<a id="sk-02-the-short-window-arithmetic-kill-verbatim-truncated-at-a_0le-6-coordshort-window-arithmetic"></a>

### SK-02 — the short-window arithmetic kill, verbatim, truncated at $`a_0\le 6`$ (`coord:short-window-arithmetic`)

<div class="thm">

**Theorem 234**. *and . <span class="sans-serif">\[Cert\]</span> for the witness, <span class="sans-serif">\[Lean\]</span> for the consumer. <span class="sans-serif">scale:bounded</span>.
``` math
\forall a_0\le 6,\ \exists a,L,\ a_0\le a \wedge L < 2\cdot 2^a \wedge
  \mathtt{LcmDiagonalArithmeticKill}(2^a)\,L
```
— literally the open cofinal supply predicate below with its universal quantifier truncated at $`a_0\le 6`$. This is the purest <span class="sans-serif">scale:fixed</span>-vs-<span class="sans-serif">scale:cofinal</span> row in the corpus: the proof term is $`\langle`$`6, 93, ha0, by norm_num, lcmDiagonalArithmeticKill_two_pow_six`$`\rangle`$ — a single hard-coded witness $`(a,L)=(6,93)`$, itself discharged from (a `norm_num` evaluation over an explicit table of $`\varphi`$ values). There is no argument in $`a`$ whatsoever; removing the bound $`a_0\le 6`$ requires an entirely new proof, not a re-run.*

</div>

<div class="defn">

**Definition 235** (What would close it). $`\mathtt{PowerTwoActualLcmShortArithmeticKillSupply}`$: <span class="sans-serif">\[Open\]</span>, <span class="sans-serif">scale:cofinal</span>.
``` math
\forall a_0\ \exists a,L,\ a_0\le a \wedge L < 2\cdot 2^a \wedge
  \mathtt{LcmDiagonalArithmeticKill}(2^a)\,L .
```
The short-window restriction $`L<2\cdot 2^a`$ buys extra structure — every non-divisor offset in that window is a bare prime power, by `eq_prime_pow_of_not_dvd_periodLcm` — so this is a better-equipped target than the raw SEP-02 supply even though it is formally a stronger statement (it implies certified-kill directly, without the separation-and-round step).

</div>

<a id="b11-the-diagonal-pincer-certificate-bank-coorddiagonal-pincer"></a>

### b11 — the diagonal pincer certificate bank (`coord:diagonal-pincer`)

<div class="thm">

**Theorem 236**. *, with and . <span class="sans-serif">\[Cert\]</span>. <span class="sans-serif">scale:fixed</span>.
``` math
\forall t\in\{1,2,3,4,5,7,8,9,11,13,16,17\},\ \exists L,\
  \mathtt{certifiedKill}\ (\mathtt{periodLcm}\ t)\ (\mathtt{periodLcm}\ t)\ L
```
at depths $`\{6,5,7,7,9,14,15,14,21,22,23,26\}`$ respectively, extended by the separate T19…T64 modules to 28 historical values through $`t=64`$ (the $`t=64`$ endpoint is ). The later aggregate theorem closes every scale $`t\le82`$ with no holes (). Every witness is a `norm_num` evaluation over a hard-coded block of $`\varphi`$ values — e.g. the $`t=17`$ certificate lists $`\varphi(12252241),\ldots,\varphi(24504506)`$ explicitly — so nothing in the proof is a function of $`t`$.*

</div>

<div class="rem">

*Remark 237* (A stronger signal in the depth table than the theorem states). forces $`2(2H_t{+}L{+}2)<2^L`$, i.e. $`L \gtrsim \log_2(4\cdot\mathtt{periodLcm}\ t)`$ at any certified depth. Comparing that floor against $`\mathtt{diagonalPincerKillDepth}`$ shows every landed certificate fires within a small additive constant of the theoretical minimum depth, at every tested scale — a numerically supported (<span class="sans-serif">\[Cert\]</span>, not <span class="sans-serif">\[Math\]</span>) anti-concentration observation, not a theorem.

</div>

<div class="prop">

**Proposition 238** (What would close it).
*``` math
\exists C\ \forall t_0\ \exists t\ge t_0\ \exists L\le \log_2(4\cdot\mathtt{periodLcm}\ t)+C,\quad
  \mathtt{certifiedKill}\ (\mathtt{periodLcm}\ t)\ (\mathtt{periodLcm}\ t)\ L .
```
This is an anti-concentration statement about the diagonal word’s residue at the first admissible depth — exactly the shape a doubling-orbit equidistribution argument would produce.*

</div>

<a id="a12-one-window-sixteen-periods-wrong-way-quantifiers-coordh-uniform-certificate"></a>

### a12 — one window, sixteen periods, wrong-way quantifiers (`coord:h-uniform-certificate`)

<div class="thm">

**Theorem 239**. *and (shallower sibling ). <span class="sans-serif">\[Cert\]</span>. <span class="sans-serif">scale:fixed</span>.
``` math
\forall h\in[1,16],\quad \mathtt{certifiedKill}\ h\ 14\ 9
```
— a single position $`N=14`$ and a single depth $`L=9`$ that simultaneously certify every period $`h`$ up to $`16`$. Consequence: $`S\ne r`$ for every rational $`r`$ with $`r.\mathrm{den}\mid 2^{14}(2^h{-}1)`$, $`1\le h\le 16`$. Proof is `decide` on a 9-bit window; no part of it is a function of $`N`$ or of the $`h`$-range.*

</div>

<div class="rem">

*Remark 240* (Quantifier inversion — the only $`h`$-uniform row in the corpus). The 249-supply obligation is $`\forall h\ \forall N_0\ \exists N\ge N_0\ \exists L`$. This row proves $`\exists N\ \exists L\ \forall h\in[1,16]`$: the quantifiers are inverted, and the $`h`$-range is finite. The inversion helps in one direction (one $`(N,L)`$ covers a whole block of periods, more than the obligation asks) and hurts in the other ($`N`$ is pinned at $`14`$, not cofinal). This is the only row in the corpus with $`h`$-uniformity, and it is the reason a scale-uniform version would be unusually strong.

</div>

<div class="prop">

**Proposition 241** (What would close it). *A scale-uniform version of the same shape: $`\exists f:\mathbb N\to\mathbb N`$ with $`f(N)\to\infty`$ such that $`\forall N_0\ \exists N\ge N_0\ \exists L`$ with $`\mathtt{certifiedKill}\ h\ N\ L`$ for all $`h\le f(N)`$. This implies the obligation immediately (fix $`h`$, take $`N_0`$ large enough that $`f(N)\ge h`$) and, unlike the obligation, is a statement about one window at a time rather than a per-period search.*

</div>

<a id="c3-the-farey-denominator-floor-and-its-stalled-growth-law-coordfarey-window"></a>

### c3 — the Farey denominator floor and its stalled growth law (`coord:farey-window`)

<div class="thm">

**Theorem 242**. *, built from the classical mediant lemma and the window sharpness certificate / . <span class="sans-serif">\[Lean\]</span> for the general mediant lemma; <span class="sans-serif">\[Cert\]</span> for the $`K=240`$ window instantiation. <span class="sans-serif">scale:fixed</span>. If $`S`$ is rational, its reduced denominator exceeds $`7.9639646646701375323355774875831053\times 10^{34}`$ (the exact numeral in the declaration name). This is the strongest unconditional statement about $`S`$ in the corpus, logically independent of the certificate-supply reduction.*

</div>

<div class="rem">

*Remark 243* (Why re-running the same window buys nothing). The cofinal upgrade of this statement — $`S\ne p/q`$ for every bound $`q`$, not just $`q =
7.96\times10^{34}`$ — is literally $`\mathrm{Irrational}(S)`$, so the target coordinate is right. What blocks promotion is proved on disk: establishes that the $`K=240`$ window bound is *sharp*, at exactly the mediant $`b{+}d`$, so re-running the same argument at the same window buys nothing further. Each new $`K`$ needs (i) a freshly committed $`2^K`$-scale totient residue $`V_K`$ and (ii) fresh continued-fraction convergents of $`V_K'/2^K`$, both hard-coded numerals in the current proofs. The growth of the bound $`b_K{+}d_K`$ is governed by the convergent denominators of the underlying constant. Rationality would force eventual stalling, so unbounded growth would prove \#249; however, no converse reduction or proved logical equivalence is known. The sentence is therefore a diagnosis of why this fixed-window method reaches the original difficulty, not an iff theorem.

</div>

<div class="obs">

*Observation 244* (A closed sub-route). and , the corpus’s own attempt at strengthening this window refinement via a unit-modulo-odd-part criterion, prove a hard ceiling in and (<span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:n/a</span>): at a prime-power denominator, the strengthening rescues at most *one* extra lattice point. That route is closed — it cannot be the source of a growth law.

</div>

<div class="prop">

**Proposition 245** (What would close it). *A proved growth law for the window family: a function $`g`$ with $`g(K)\to\infty`$ and a proof that for every $`K`$ the $`(N{=}1,K)`$ gap check passes for all $`q\le g(K)`$. Equivalently, a lower bound on the convergent denominators of the totient-window constant, uniform in $`K`$.*

</div>

<a id="ta-01ta-02-the-two-adic-pulse-block-reaches-the-arc-centre-and-fails-by-an-exponential-coordtwo-adic-pulse"></a>

### TA-01/TA-02 — the two-adic pulse block reaches the arc centre and fails by an exponential (`coord:two-adic-pulse`)

<div class="thm">

**Theorem 246**. *, , , . <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span> (the theorem is unconditional and holds for *every* $`K`$, $`H`$, $`B`$, not merely cofinally many). For every $`K\ge 2`$, every $`H>K`$, and every bound $`B`$, there are primes $`p>B`$ with a length-$`(K{-}1)`$ zero prefix and a terminal half-turn, giving
``` math
A_{H,p-K,K} \equiv 2^{K-1} \pmod{2^K}.
```
Under eventual integrality this transfers to an integer $`z`$ with $`(z:\mathbb R) =
\mathrm{totientTail}(p{+}H) - \mathrm{totientTail}(p)`$ and $`z\equiv 2^{K-1}\pmod{2^K}`$.*

</div>

<div class="rem">

*Remark 247* (Lands at the exact centre of the arc, fails by an exponential — and why). This lands the residue at the exact centre of the certified-kill arc: $`2^{K-1}`$ is maximally far from $`0`$ modulo $`2^K`$, precisely the coordinate the obligation wants. Taking $`N{=}p{-}K`$, $`h{=}H`$, $`L{=}K`$ gives radius $`N{+}h{+}L{+}2 = p{+}H{+}2`$, so $`\mathtt{certifiedKill}`$ requires $`2^{K-1} > p{+}H{+}2`$. But $`z\equiv 2^{K-1}\pmod{2^K}`$ forces $`|z|\ge 2^{K-1}`$, while the directed tail bound forces $`|z| < p{+}H{+}2`$; and the construction’s own congruence $`p\equiv 1{+}2^{K-1}\pmod{2^K}`$ (equivalently $`v_2(p{-}1)=K{-}1`$) forces $`p\ge 1{+}2^{K-1}`$. So $`p{+}H{+}2 > 2^{K-1}`$ always, and no choice of $`p`$ rescues it. The quantifier order is inverted: the theorem gives, for fixed $`K`$, cofinally many *large* $`p`$; the certificate needs a $`p`$ *small* relative to $`2^{K-1}`$, impossible for a single letter since $`|\varphi(N{+}H)-\varphi(N)|
< N{+}H`$. Depth-promotion is not the issue: it has already been performed, generalizing an exponent-2 construction to every $`K`$ uniformly by CRT-gluing over a $`\mathrm{Unit}\oplus\mathrm{Fin}(K{-}1)\oplus\mathrm{Fin}(K{-}1)`$ family.

</div>

<div class="prop">

**Proposition 248** (What would close it). *The same half-turn residue realised by an *accumulated* window rather than a single terminal letter: cofinally many $`(h,N,L)`$ with $`A_{h,N,L}\equiv 2^{L-1}\pmod{2^L}`$ and $`2^{L-1} > N{+}h{+}L{+}2`$. Only the weighted sum $`\sum \Delta\varphi\cdot 2^{L-1-j}`$ can carry magnitude $`2^L`$; the per-letter pulse provably cannot. Concretely: a pulse-block construction whose zero prefix and half-turn are imposed on the *word*, not on one delta.*

</div>

<a id="d-3ad-3b-cofinal-jump-positions-one-unproved-slack-sign-coordlcm-jump-slack"></a>

### d-3a/d-3b — cofinal jump positions, one unproved slack sign (`coord:lcm-jump-slack`)

<div class="thm">

**Theorem 249** (Cofinal producer, fully proved). *. <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:cofinal</span> (proved, not open): $`\forall t_0\ \exists t\ge t_0`$ with $`\mathtt{periodLcm}\ t < \mathtt{periodLcm}(t{+}1)`$, witnessed by $`p{-}1`$ for any prime $`p>t_0`$. The power-of-two specialization shows the positions $`t=2^a{-}1`$ already suffice, so no position search is needed at all.*

</div>

<div class="defn">

**Definition 250** (The slack scalar and the open supply). :
``` math
\mathtt{canonicalAdjacentSuffixCentralSlack}\ t = \min\bigl(d-2^{m-5},\ (2^m-2^{m-5})-d\bigr),
```
with $`m`$ the canonical adjacent-suffix depth and $`d`$ the residue at that depth. The open producers, both <span class="sans-serif">\[Open\]</span> <span class="sans-serif">scale:cofinal</span>, are (any strict jump) and (power-of-two positions), each asking $`0\le \mathtt{canonicalAdjacentSuffixCentralSlack}(t{+}1)`$ cofinally, and both compose to $`\mathrm{Irrational}(S)`$ at and .

</div>

<div class="rem">

*Remark 251* (Census evidence only). <span class="sans-serif">\[Cert\]</span>, <span class="sans-serif">scale:fixed</span>. All $`40`$ strict jumps up to endpoint $`113`$ pass, closest margin $`\approx 0.000221`$ of the modulus at $`t=100`$; the power-of-two endpoints $`4,8,16,32`$ pass with slack fractions $`0.41,0.036,0.40,0.19`$. Census, not theorem. The structural handle nobody has used: $`\mathtt{periodLcm\_succ\_eq\_prime\_mul\_of\_strict\_jump}`$ () says a strict jump at $`t`$ means $`t{+}1=p^k`$ and $`\mathtt{periodLcm}(t{+}1) = p\cdot\mathtt{periodLcm}(t)`$ — so the required statement is a transfer lemma for how the adjacent-suffix residue at height $`H`$ moves under $`H\mapsto pH`$. already proves the slack is constant across each LCM plateau, so only jump indices matter.

</div>

<div class="prop">

**Proposition 252** (What would close it). *$`0\le \mathtt{canonicalAdjacentSuffixCentralSlack}(2^a)`$ for cofinally many $`a`$.*

</div>

<a id="e2-the-prime-jump-commutator-one-fixed-witness-coordprime-jump-commutator"></a>

### e2 — the prime-jump commutator, one fixed witness (`coord:prime-jump-commutator`)

<div class="thm">

**Theorem 253**. *and . <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span>. Uniform consumer for all $`H,p,L`$: a residue of the four-vertex commutator $`J(H,p)`$ outside the sharp radius $`3pH{+}(p{+}1)(L{+}2)`$ forces $`J(H,p)\notin\mathbb Z`$. This is tighter than the earlier $`4pH`$ two-cell disjunction.*

</div>

<div class="thm">

**Theorem 254** (The one witness). *. <span class="sans-serif">\[Cert\]</span>. <span class="sans-serif">scale:fixed</span>. $`\mathtt{primeJumpSharpKill}\ 12\ 5\ 15`$ (i.e. $`H=\mathtt{periodLcm}\ 4=12`$, $`p=5`$, $`L=15`$), proved by `decide` on an explicit 15-bit window with no dependence on $`t`$ or $`p`$; only a single instance exists, at $`t=4`$, the smallest nontrivial height. The full endpoint composition is .*

</div>

<div class="rem">

*Remark 255*. The supply hypothesis $`\forall t_0\ \exists t\ge t_0\ \exists p,L{>}0`$ with $`\mathtt{primeJumpSharpKill}(\mathtt{periodLcm}\ t)\ p\ L`$ is a genuinely cheaper target than the raw SEP-02 supply: it asks for one fresh prime $`p`$ per LCM height rather than a full central-arc certificate. Because the consumer route is `rational_totient_series_forces_lcm_cone_flatness`$`\to`$contradiction, the natural attack is to pick $`p`$ as the fresh prime introduced at the next strict LCM jump (linking this row to d-3a), where the commutator’s old-channel contributions are annihilated by .

</div>

<a id="b7-the-möbiusmersenne-denominator-channel-unbounded-but-off-coordinate-coordmobius-mersenne"></a>

### b7 — the Möbius–Mersenne denominator channel: unbounded, but off-coordinate (`coord:mobius-mersenne`)

<div class="thm">

**Theorem 256**. *, , . <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span>. For every $`t\ge 5`$, uniformly in $`t`$:
``` math
2^{t/2} \;\le\; \prod_{p\in \mathrm{upperHalfPrimes}(t)} \mathtt{mersenne}(p) \;\le\;
  \mathrm{den}\bigl(\mathtt{lcmHeight}(t)\cdot \mathtt{numericMobiusShadow}(\mathtt{lcmHeight}(t))\bigr).
```
An unbounded denominator lower bound at every LCM height, with an individual surviving channel isolated ($`2^{t/2}\le \mathtt{mersenne}(p) < 2^t`$). The proof is genuinely uniform in $`t`$ (Bertrand’s postulate via `upperHalfPrimes_nonempty`, plus $`2^{p-1}\le 2^p{-}1`$ factorwise — no table, no constant degrading with $`t`$).*

</div>

<div class="rem">

*Remark 257* (The corpus’s only proved unbounded-growth quantity in this coordinate, but the wrong coordinate for \#249). This lives in a different coordinate from the 249-supply obligation: it bounds the reduced denominator of the *scaled* shadow at LCM height $`t`$, and there is no landed transport from a denominator lower bound to $`\mathtt{certifiedKill}`$ or to a totient-tail non-integrality. Two further honest caveats are recorded in the module’s own docstring: it does not rule out cancellation by the foreign-defect term, and the growth rate $`2^{t/2}`$ is far below the scale $`\mathtt{lcmHeight}(t)\approx 2^{1.44t}`$ against which the enclosure consumers measure error. The existing consumers built on it (`scaleFullTarget_miss_of_lambert_projected_separation`, `scaleFullTarget_miss_of_lambert_projected_num_gap`) are \#257-facing (`ScaleFullTargetHit`), not \#249-facing.

</div>

<div class="prop">

**Proposition 258** (What would close it). *Either (i) a Dirichlet-criterion bridge in the shape of : a sequence of rationals $`u_t`$ with $`u_t\ne S`$ and $`\mathrm{den}(u_t)\cdot|S-u_t|\to 0`$, which requires the approximation error to beat the denominator, not merely the denominator to grow; or (ii) a transport map from “channel of size $`\ge 2^{t/2}`$ survives in the denominator” to “windowDiscrepancy residue avoids the arc,” which does not exist in the corpus. Route (i) needs the growth rate raised from $`2^{t/2}`$ to beat the shadow’s own truncation error.*

</div>

<a id="d4d5-the-parallel-rank-obligation-and-a-corrected-pair-of-citations-coordcarry-rank"></a>

### d4/d5 — the parallel rank obligation, and a corrected pair of citations (`coord:carry-rank`)

This row runs a second, independent open obligation in parallel to 249-supply, in the carry-kernel *rank* coordinate rather than the residue coordinate. **Correction**: the source index attributed the two theorems below to swapped files; direct reads this session confirm the correct attribution is as given.

<div class="thm">

**Theorem 259**. *. <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span>. Unconditional and uniform in $`e`$: the dyadic totient-kernel family is linearly independent at every depth $`e`$ (dimension exactly $`2^e{+}1`$, via CRT and Dirichlet on primes in arithmetic progression).*

</div>

<div class="thm">

**Theorem 260**. *. <span class="sans-serif">\[Lean\]</span>. <span class="sans-serif">scale:uniform</span>. If $`S`$ is rational there is a tempered integral carry orbit $`u`$ with
``` math
2^e - 1 \;\le\; \mathrm{finrank}_{\mathbb Q}\,\mathrm{span}(\mathtt{canonicalCarryKernelFamily}\ u\ e)
  \qquad\text{for every } e .
```*

</div>

<div class="rem">

*Remark 261* (The scale side is finished; the missing direction is proved dead on one route). So: rationality forces *unbounded* carry-kernel rank, and the $`2^e{-}1`$ floor holds for all $`e`$ with a uniform proof. What is missing is the opposite inequality — a rationality-side rank upper bound, which would contradict the floor and close \#249. The corpus proves one natural route to it is dead: (<span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:n/a</span>) shows no ($`Q\cdot v\cdot A =`$ boundary with $`|\mathrm{boundary}| < Q\cdot v`$ and $`A\ne 0`$) can exist, and `not_finiteDimensional_span_fullTotientKernel` (immediately above it in the same file) shows the full family spans an infinite-dimensional space. Cross-checked against a separate row, $`\mathtt{lcm\_factorIdeal\_finiteRank\_shiftAlgebra\_not\_sufficient}`$: a single explicit countermodel defeats every finite-rank shift-polynomial observation simultaneously, so finite-rank amplification per se is not the missing rigidity.

</div>

<div class="prop">

**Proposition 262** (What would close it). *A rationality-side rank upper bound: $`\exists C`$ such that any tempered integral binary carry orbit for a rational $`\mathtt{binaryCoeffSeries}`$ has $`\mathrm{finrank}_{\mathbb Q}\,\mathrm{span}(\mathtt{canonicalCarryKernelFamily}\ u\ e)\le C`$ for all $`e`$, or any bound growing slower than $`2^e{-}1`$. `not_irrational_totientSeries_implies_mod_period_and_unbounded_rank` (`TotientTailCarryPeriod.lean:224`) pins the obstacle precisely: rationality buys uniform eventual periodicity of $`u`$’s dyadic sections mod $`v`$, and that periodicity provably does *not* promote to a $`\mathbb Q`$-rank bound without extra arithmetic input.*

</div>

<a id="synthesis-where-the-frontier-actually-is"></a>

## Synthesis: where the frontier actually is

Collecting the fourteen rows, three facts stand out as loci for future effort, stated with the same precision as the rows themselves rather than as summary rhetoric.

First, the single closest approach to 249-supply is the first-harmonic reduction of §<a href="#ssec:headline" data-reference-type="ref" data-reference="ssec:headline">9.2</a>: a constant-saving ($`21/25`$ or $`9/10`$) exponential-sum cancellation estimate, with a satisfiable room condition and, via the subset consumer (Theorem <a href="#thm:hgap-subset" data-reference-type="ref" data-reference="thm:hgap-subset">217</a>), no requirement that the saving hold on a full interval or a positive-density subset. This is the only row in the index whose remaining content is recognisably a single classical estimate rather than a compound arithmetic-geometric statement.

Second, the top-edge staircase (TE-04 through TE-05-weakest, `coord:actual-lcm-top-edge`) is the only row where the corpus has both halved the obligation (one-sided instead of symmetric) and exposed, via the exact identity of Observation <a href="#obs:staircase-tension" data-reference-type="ref" data-reference="obs:staircase-tension">229</a>, precisely which of two logically symmetric escape branches survives the sign machinery already proved elsewhere in the same file family. That five strictly weaker equivalent or sufficient forms are already proved inter-derivable (Proposition <a href="#prop:te-chain" data-reference-type="ref" data-reference="prop:te-chain">226</a>) means effort here is not fragmented across restatements: proving any one closes the others automatically.

Third, the d4/d5 rank obligation is structurally independent of the residue-coordinate rows above: it is a second, self-contained sufficient condition for \#249 (an upper rank bound contradicting the proved $`2^e{-}1`$ lower bound), in a coordinate (carry-kernel rank) where a natural finite-rank strengthening is already proved impossible. A rank upper bound, if found, would not need to route through $`\mathtt{certifiedKill}`$ at all.

No row in this index is a solution, a partial solution in the sense of resolved cases, or evidence that \#249 is likely true or false. Every open producer listed is exactly as open as the original Erdős–Borwein question it reduces to; what the index adds is the exact remaining content, verified against the live Lean tree, of each reduction.

<a id="closed-routes-with-the-mechanism-that-closed-them"></a>

# Closed routes, with the mechanism that closed them

This section catalogues every no-go, countermodel, obstruction, and refuted proof strategy found in the \#249/#257 corpus that bears on Erdős \#249 ($`S := \sum_{n\ge1}\varphi(n)/2^n`$ irrational). Erdős \#249 is <span class="sans-serif">\[Open\]</span>; nothing in this section decides it. What follows is a machinery inventory: for each dead route, the exact statement that closed it, the exact scope of the closure, and the exact machinery salvaged from the wreckage. The organising warning, stated once here and applicable to every item below: several of these “obstructions” are statements about a *representation* of the problem (a proof strategy, a certificate family, a coordinate system) and not about the object $`S`$ itself. Confusing the two is the single most common error this catalogue exists to prevent.

<a id="meta-level-finite-inspection-cannot-certify-the-supply-the-gamma-splice-remark"></a>

## Meta-level: finite inspection cannot certify the supply (the $`\gamma`$-splice remark)

**(a) Route as conceived.** Every unconditional route to \#249 in this corpus bottoms out in a *certificate-supply* obligation of the shape $`\forall h\ge1\,\forall N_0\,\exists N\ge N_0\,\exists L,\ \mathrm{Sep}(h,N,L)`$ (, the exact open-obligation form quoted throughout the existing manuscript). A natural hope is that verifying $`\mathrm{Sep}`$ — or its diagonal specialisation — at every scale up to some large, explicit bound $`B`$ is evidence that the supply holds, and that pushing $`B`$ far enough would eventually amount to a proof.

**(b) Exact mechanism that closed it.** The manuscript’s own remark (<span class="sans-serif">\[Math\]</span>, prose-only, not formalised in Lean: *§5.4, “finite inspection cannot establish the supply”*) gives an explicit splice construction. Take any coefficient stream $`\gamma:\mathbb
N\to\mathbb N`$ that agrees with $`\varphi`$ on every index $`\le B`$, and alter $`\gamma`$ at one residue class beyond $`B`$ so that the resulting binary series $`\sum\gamma(n)/2^n`$ is forced *rational*. Such a $`\gamma`$ exists for every $`B`$ (this is the same coboundary-splice technique that produces §<a href="#sec:parity-countermodel" data-reference-type="ref" data-reference="sec:parity-countermodel">10.2</a>’s `parityCoboundaryWeight` witness, generalised: insert a lacunary zero-valued coboundary edit $`2/2^m - 4/2^{m+1} = 0`$ at some $`m>B`$). Because $`\gamma`$ agrees with $`\varphi`$ on every index $`\le B`$, $`\gamma`$ passes every finite certificate that only inspects indices $`\le B`$ — in particular every instance of $`\mathrm{Sep}(h,N,L)`$ with $`N+L\le B`$ that $`\varphi`$ itself passes or fails. Yet $`\sum\gamma(n)/2^n\in\mathbb Q`$ by construction.

**(c) Precise scope.** This is a statement about *proof method*, not about $`\varphi`$: it does not touch $`S`$ at all. What it excludes is the inference “$`\mathrm{Sep}`$ verified up to bound $`B`$, for arbitrarily large $`B`$, therefore $`\mathrm{Sep}`$ holds cofinally.” The scope is exactly $`{\small\textsf{scale:bounded}}`$ versus $`{\small\textsf{scale:cofinal}}`$: any finite-B verification, however large, is compatible with both outcomes, because a rational stream can be built to survive any *fixed* inspection horizon. It says nothing about whether $`\varphi`$ itself is such a $`\gamma`$ — only that no finite-horizon check can distinguish $`\varphi`$ from a $`\gamma`$ that is.

**(d) Salvage.** The splice construction is exactly the mechanism underlying §<a href="#sec:parity-countermodel" data-reference-type="ref" data-reference="sec:parity-countermodel">10.2</a>’s Lean-formalised countermodel below, so its *content* is not lost even though this specific remark is unformalised: everywhere a proof strategy in this corpus proposes to certify a supply by exhaustive finite search (the diagonal deposits at $`t\in\{1,\dots,64\}`$, ; the row-200,000 sqrt-escape census on the \#257 side), this remark is the standing reason such a search, however large, is evidence and not proof. <span class="sans-serif">\[Math\]</span> <span class="sans-serif">scale:n/a</span> `coord:binary-digit`.

<a id="sec:parity-countermodel"></a>

## The parity-aperiodicity countermodel (`TotientParityCoboundaryCountermodel`)

**(a) Route as conceived.** A natural strengthening of \#249 attempts: show that any coefficient word $`c:\mathbb N\to\mathbb N`$ that (i) is uniformly bounded, (ii) satisfies the trivial linear-growth bound $`c(n)\le n`$, (iii) matches $`\varphi(n)\bmod 2`$ exactly, and (iv) is not eventually periodic — even strengthened to *cofinally, arbitrarily separated, arbitrarily long blocks* of non-periodicity — must have irrational binary series $`\sum c(n)/2^n`$. This is the natural target for anyone trying to use only $`\varphi`$’s coarse parity/aperiodicity profile.

**(b) Exact mechanism.** The construction $`\mathtt{parityCoboundaryWeight}(n) := \mathtt{parityBaseWeight}(n) +
2\cdot\mathtt{largePowerTwoBit}(n) - 4\cdot\mathtt{largePowerTwoBit}(n-1)`$, where $`\mathtt{parityBaseWeight}`$ is the eventually-constant word $`0,1,1,2,4,4,4,\dots`$ and $`\mathtt{largePowerTwoBit}(n)=1`$ iff $`n=2^{k+3}`$, is a lacunary zero-valued coboundary splice on top of an eventually-constant base. The strongest of five landed theorems,

<div class="prop">

**Proposition 263** (Totient-parity arbitrarily-many-separated-carry rational countermodel). *There exists $`c:\mathbb N\to\mathbb N`$ such that: $`c(n)\le6`$ for all $`n`$; $`c(n)\le n`$; $`c(n)\equiv\varphi(n)\pmod2`$ for every $`n`$; for every $`N,G,K`$ there is a block of $`K`$ explicit $`(6,0)`$ carry-pulse pairs beyond $`N`$, each pair separated by more than $`G`$; and $`\sum_n c(n)/2^n = 3/2`$.*

</div>

(sum computation ; non-periodicity ; exact parity match ). <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:cofinal</span> `coord:binary-digit`.

**(c) Precise scope.** This is an *object*-level existence witness ($`c\ne\varphi`$, only $`c\equiv\varphi\pmod2`$) that closes a *proof-route*: it proves that the hypothesis set $`\{`$bounded, linear growth, $`\varphi`$-parity match, non-eventual-periodicity$`\}`$, no matter how strongly the non-periodicity clause is strengthened (up to the arbitrarily-separated arbitrarily-numerous form above), can never entail irrationality of the associated binary series, because $`c`$ satisfies every hypothesis and is rational. It says nothing about $`\varphi`$ itself — the witness sequence $`c`$ is a different, hand-built sequence. Any future sufficient-condition candidate stated purely in terms of $`\{`$coefficient boundedness, growth, parity, periodicity$`\}`$ must be checked against this countermodel before being trusted, for *either* \#249 or \#257.

**(d) Salvage.** The lacunary coboundary-splice technique itself — inserting zero-valued edits $`2\cdot2^{-m}-4\cdot2^{-(m+1)}=0`$ at sparse ranks to destroy periodicity while preserving the rational sum — is a fully general recipe for building rational-valued, non-eventually-periodic, bounded coefficient sequences matching *any* parity template, and is literally the mechanism instantiated informally in Theorem <a href="#thm:gamma" data-reference-type="ref" data-reference="thm:gamma">13</a>’s $`\gamma`$-splice construction. It is also a ready-made stress-test fixture for any future parity-based sufficient condition proposed anywhere in the corpus. Confirms the corpus-wide lesson (project memory `feedback_erdos_reductions_rejected_bank_real_results`): only arguments using *actual* quantitative totient/Mersenne size or residue information — as in the `TotientActualLcm*`, `TotientFixedRank*` families below — can possibly close \#249; pure symbolic-word arguments cannot.

<a id="two-scoped-249-no-go-countermodels-square-crt-correction-suppression-is-ambiguous"></a>

## Two scoped \#249 no-go countermodels: square-CRT correction suppression is ambiguous

**(a) Route as conceived.** The totient prime-dilation cocycle $`\varphi(pm)=(p-1)\varphi(m)+[p\mid m]\varphi(m)`$ carries a correction term whenever $`p\mid m`$. A natural strategy imposes a square congruence $`n\equiv A+pa\pmod{p^2}`$ with a “clean” shift $`h`$ ($`p\nmid a+h`$) to suppress that correction on a finite horizon, then hopes that correction-suppression (“cleanliness”) is itself enough to guarantee that the resulting finite-difference cube is *nonzero* — i.e. that cleaning away the correction term automatically leaves behind a genuine, nonvanishing arithmetic signal usable in a curvature argument.

**(b) Exact mechanism that closed it.** Two explicit, opposite finite computations refute the hoped-for entailment simultaneously:

- *Vanishing witness.* The smallest returned countermodel has the *entire* two-step finite block $`\mathtt{actualOneCubeCoeff}`$ equal to zero at $`n=52`$, $`r_0=13`$, $`r_1=13/18`$ (, kernel-`decide`d; cleanliness witnessed by ).

- *Nonvanishing witness.* A separate, nearby clean configuration at $`n=27`$ has the same block *nonzero* (; cleanliness witnessed by ).

Both witnesses are exhibited alongside the positive achievability result (a bounded common base satisfying prescribed CRT anchors/residues does exist). <span class="sans-serif">\[Cert\]</span> (theorem bodies not independently re-verified beyond signatures and docstring — flagged `DOCSTRING-SOURCED` in the source bank) <span class="sans-serif">scale:fixed</span> `coord:other:square-crt-cocycle`.

**(c) Precise scope.** These are two \#249-scoped countermodels — the coordinate is the totient prime-dilation cocycle specifically, not a problem-agnostic phenomenon. Together they show that *correction-suppression is logically independent of the sign/nonvanishing question it was hoped to settle*: “clean” (i.e. correction-free) is consistent with *both* outcomes. This is a statement about a specific finite-difference construction (the representation), not about $`\varphi`$: it does not exclude a nonvanishing finite-difference cube in general, only the inference from cleanliness *alone* to nonvanishing.

**(d) Salvage.** The general cocycle identity $`\varphi(pm)=(p-1)\varphi(m)+[p\mid m]\varphi(m)`$ () and the CRT-witness apparatus (, ) remain fully reusable for *any* residue-forcing construction, in any coordinate. More valuably, the abstract cube-cancellation lemma extracted from the same file, — “if inserting one coordinate never changes the value of $`f`$, the alternating powerset sum of $`f`$ vanishes” — is completely divorced from totient/CRT content and is directly reusable for any Hilbert-cube or higher-difference argument on either problem. What remains as the honest open gap: an independent anti-concentration or residue-producer argument for why the clean residual does *not* vanish, which this module explicitly does not supply.

<a id="sec:adelic-height"></a>

## The adelic height obstruction

**(a) Route as conceived.** Several proof strategies attempt to *clear* an unwanted denominator factor from a rational value $`x`$ by multiplying by a small integer coefficient $`c`$, hoping to discard the complementary denominator information entirely (e.g. localising a diagonal tail difference to one LCM ray channel while dropping the rest).

**(b) Exact mechanism.**

<div class="lem">

**Lemma 264** (Scalar-localisation complement divisibility). *For $`x:\mathbb Q`$, $`c:\mathbb Z`$, $`H:\mathbb N`$: if $`H\mid x.\mathrm{den}`$ and $`(c\cdot x).\mathrm{den}\mid H`$, then $`x.\mathrm{den}/H \mid
c.\mathrm{natAbs}`$.*

</div>

. The equality strengthening, $`\exists t:\mathbb Z,\ H\cdot c\cdot x = t\cdot x.\mathrm{num}`$, is . The Mersenne-scale corollary — for positive $`x`$, if $`2^r\mid x.\mathrm{num.natAbs}`$ and $`x<2/(2^n-1)`$, then $`2^r(2^n-1)<2\cdot x.\mathrm{den}`$ — is (generic form ).

A companion rigidity fact rules out smuggling the discarded information back in through a linear channel: if a linear map $`\Lambda:V\to W`$ factors through a surjective evaluation $`\mathrm{ev}`$ ($`\ker\mathrm{ev}\le\ker\Lambda`$), then $`\Lambda`$ is *exactly* $`\mathrm{ev}(\cdot)\bullet w_0`$ for a single fixed $`w_0`$ — .

The upstream primitive these import, and , gives the exact survival/cancellation law: a divisor $`m\mid D`$ of a displayed denominator survives reduction of $`a/D`$ iff $`m`$ is coprime to $`a`$; after scaling the numerator by $`h`$, a surviving coprime divisor $`C\mid D`$ shrinks to exactly $`C/\gcd(C,h)`$, never further. <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:uniform</span> `coord:other:rational-height`.

**(c) Precise scope.** This is pure $`\mathbb Q`$-arithmetic with zero Mersenne or totient content — it is not a statement about $`S`$ at all, but about *any* rational-height bookkeeping argument. Its exact content: scalar denominator-clearing never *erases* the complementary denominator; it moves that complement into the coefficient’s (Archimedean) size. Any construction that tries to shrink a displayed denominator down to one surviving channel pays for it in coefficient growth. This directly explains *why* denominator-compression strategies are structurally hard: the Mersenne-shadow denominator lower bound $`2^{t/2}\le\prod_{p\in\mathrm{upperHalfPrimes}\,t}\mathrm{mersenne}(p)`$ () forces a quadratic-in-scale coefficient cost via this lemma if one tries to localise to a single channel.

**(d) Salvage.** Fully problem-agnostic and directly reusable for \#257 or any other Lambert-type denominator-survival argument as-is. It is the general mechanism underlying the corpus’s Farey-gap denominator-exclusion family (Part C of the certificate bank, , the strongest current unconditional statement about $`S`$: if $`S`$ is rational its reduced denominator exceeds $`79{,}639{,}646{,}646{,}701{,}375{,}323{,}355{,}774{,}875{,}831{,}053\approx7.96\times10^{34}`$).

<a id="the-signed-q-moment-machinery-a-positive-tool-not-an-obstruction"></a>

## The signed $`q`$-moment machinery — a positive tool, not an obstruction

**(a) Route as conceived.** A “signed Hankel determinant” / Hermite–Padé style route to \#249 would exhibit a finite signed linear combination of dyadically-cleared totient terms and show it is provably nonzero, giving a nonvanishing certificate for a first-harmonic or Möbius-companion construction.

**(b) Exact mechanism (a nonvanishing *engine*, not a no-go).**

<div class="lem">

**Lemma 265** (Unique-terminal parity nonvanishing). *If a finite signed sum $`\sum_{i\in s}u(i)\cdot2^{e(m)-e(i)}`$, clearing dyadic denominators to a common exponent $`e(m)`$, has one index $`m\in s`$ with strictly maximal exponent $`e(m)`$ and odd coefficient $`u(m)`$, while every other index has strictly smaller exponent, then the whole cleared sum is $`\equiv1\pmod2`$, hence nonzero.*

</div>

, built from a fully generic rectangular Cauchy–Binet-style determinant-of-product expansion (definitions and ). <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:bounded</span> `coord:p-adic`.

**(c) Precise scope — the point this section exists to make.** Despite living in a file named alongside the corpus’s “obstruction” modules, this is explicitly *not* phrased as a no-go in its own docstring: it is the finite nonvanishing engine that a Hankel–Padé construction for \#249 would *consume*. The parity lemma and the Cauchy–Binet expansion use no totient or Mersenne structure at all — pure linear algebra, fully problem-agnostic, directly transplantable to any base-$`q`$ dyadic-clearing argument including \#257’s series family. What is missing, and what prevents this from closing anything, is a *supply* theorem: no result in the corpus proves that a unique-terminal configuration of this shape exists cofinally for the totient-derived family. The obstruction, such as it is, is not in this lemma but in the absence of its hypothesis’s cofinal supply — exactly the same shape of gap as §<a href="#sec:mahler-defect" data-reference-type="ref" data-reference="sec:mahler-defect">10.8</a>’s Mahler defect below.

**(d) Salvage.** The entire lemma is reusable machinery, not wreckage — nothing here needs salvaging because nothing here failed. It stands ready for whichever future construction can supply the missing cofinal unique-terminal-configuration existence.

<a id="the-residual-gauge-obstruction"></a>

## The residual-gauge obstruction

**(a) Route as conceived.** A “first-harmonic pivot” strategy for \#249 (via exponential/character-sum cancellation, ) might try to certify a nonzero determinant or full-rank minor of a residual-weighted monomial matrix as sufficient evidence that a genuine phase reconstruction (as opposed to a degenerate locked configuration) has occurred.

**(b) Exact mechanism.**

<div class="prop">

**Proposition 266** (Locked reconstruction preserves a nonzero minor). *For a monomial matrix $`\mathrm{residualMonomialMatrix}(e,r,z)(i,j) =
r(i,j)\cdot z(j)^{e(i)}`$ with all residual entries $`z(j)\ne0`$ and $`e(i)=1`$ for a distinguished row $`i`$: $`\det(\mathrm{phasePowerMatrix})
\ne0 \implies \det(\mathrm{residualMonomialMatrix})\ne0`$, *and* the distinguished row is identically $`1`$ regardless.*

</div>

(row-dependent relaxation ; the column-gauge identity underlying it, $`\det(\mathrm{residualMonomialMatrix}) =
\det(\mathrm{phasePowerMatrix})\cdot\prod_j W(j)`$, is ; a row-dependent relaxation still fails at ). <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:uniform</span> `coord:other:first-harmonic-phase`.

**(c) Precise scope.** Pure linear algebra over $`\mathbb C`$, fully generic in dimension $`d`$ and exponent function $`e`$, zero \#249-specific content — this is a statement about *residual-weighted monomial matrices as a representation*, not about the totient object. It rules out exactly one class of certificate: a residual-blind rank/determinant/ conditioning test, used alone, cannot distinguish genuine phase reconstruction from an explicit “locked” degenerate configuration in which a residual weighting scales every column by $`W(j)=z(j)^{-1}`$, collapsing the exponent-one row to the constant row $`(1,\dots,1)`$ while the determinant stays nonzero whenever the base (Vandermonde-shaped) $`\mathrm{phasePowerMatrix}`$ determinant is nonzero. It does *not* rule out determinants carrying an additional arithmetic coupling identity between rows.

**(d) Salvage.** A hard requirement for any future first-harmonic determinant construction (Part E of the certificate bank, ): the construction *must* couple rows by an extra arithmetic identity, not merely gauge-normalise columns. The diagonal-gauge-action technique itself is reusable for any determinant-based nonvanishing strategy in any coordinate.

<a id="cone-flatness-and-cone-nonflatness"></a>

## Cone flatness and cone nonflatness

**(a) Route as conceived.** The diagonal certificate-supply obligation () concerns only the pair $`(H,2H)`$ at LCM height $`H=\mathrm{periodLcm}(t)`$. Two natural strengthenings: (i) show rationality of $`S`$ is even more constrained than a single diagonal pair — it flattens an *entire cone* of ratios; (ii) conversely, exhibit *nonflatness* on a wider “menu” of cone vertices as a cheaper sufficient certificate than a single pairwise $`\mathrm{certifiedKill}`$.

**(b) Exact mechanism — flatness (necessary consequence of rationality).**

<div class="prop">

**Proposition 267** (Wave-24 LCM-cone flatness). *$`\neg\mathrm{Irrational}(S) \implies \exists t_1,\ \forall t\ge t_1,\
\forall q,m:\mathbb N,\ 0<q \implies \mathrm{totientTail}(q\cdot
\mathrm{periodLcm}(t)+m\cdot\mathrm{periodLcm}(t)) -
\mathrm{totientTail}(q\cdot\mathrm{periodLcm}(t)) \in
\mathrm{range}((\uparrow):\mathbb Z\to\mathbb R)`$.*

</div>

(body `LcmConeFlatness.lean`). <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:uniform</span> (for all sufficiently large $`t`$, *given* rationality) `coord:other:lcm-ray-totient`. Rationality forces one fractional constant on the entire LCM cone $`\{k\cdot\mathrm{periodLcm}(t):k\ge1\}`$ at every scale $`t\ge t_1`$, not merely the single diagonal pair — the umbrella collapse theorem shows any $`\mathrm{certifiedKill}`$ *anywhere* on the two-multiplier cone, at arbitrarily large $`t`$, forces $`\mathrm{Irrational}(S)`$.

**(b$`'`$) Exact mechanism — nonflatness (a sharper sufficient certificate).**

<div class="prop">

**Proposition 268** (Wave-25 cone-nonflat menu refuter). *For a nonempty menu $`Q`$ of positive vertex multipliers with a *one-sided* floor $`\forall q\in Q,\ q\cdot H+L+2<2^L`$ (half the pairwise floor of $`\mathrm{certifiedKill}`$): if $`\mathrm{coneNonflatCert}\,
H\,L\,Q`$ fires (an argmin/Helly-avoidance argument: the vertices cannot all share one fractional part, else the minimal-deep-tail vertex would be a common left endpoint of every arc), then $`\exists q_i,q_j\in Q,\
\mathrm{totientTail}(q_j H)-\mathrm{totientTail}(q_i H)\notin
\mathrm{range}((\uparrow):\mathbb Z\to\mathbb R)`$.*

</div>

(supply theorem ). <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:bounded</span> (proved for a given finite menu $`Q`$; an *unbounded*-scale menu is the open sufficient target) `coord:other:lcm-ray-totient`.

**(c) Precise scope.** Flatness is a genuine *necessary consequence* of rationality — it is a statement about what rationality of $`S`$ would force, conditional on rationality, not an unconditional fact about $`S`$. Nonflatness is an unconditional *sufficient* certificate mechanism, information-theoretically half the depth floor of the pairwise $`\mathrm{certifiedKill}`$ (one-sided versus two-sided radius charging), but it has been proved only for individual finite menus $`Q`$; no menu of unbounded scale has been supplied.

Neither direction decides \#249: flatness gives a contrapositive route (exhibit *any* cone nonintegrality at arbitrarily large $`t`$ and rationality is refuted) and nonflatness sharpens the certificate needed, but the underlying producer obligation — a nonintegral tail difference at cofinally many scales — is unchanged.

Note also the coordinate warning from the manuscript’s own Appendix C (): cone flatness is a *necessary* consequence, and only the sharper diagonal-pincer / full-target-avoidance normal forms (, ) are an exact $`\mathrm{iff}`$ with irrationality.

**(d) Salvage.** The argmin/Helly-avoidance combinatorial-geometry technique behind cone-nonflatness is a reusable pattern for any modular-residue pincer argument with more than two points, in any coordinate. The rank-2 second-difference certificate family built on the same window apparatus was independently tested and found *not* to be a shortcut over rank 1 (measured, not merely conjectured: at $`(h,N)=(1,8)`$, rank-1 fires at depth 8 while no rank-2 certificate exists at depth $`\le8`$; ) — an explicitly flagged dead end not to re-attempt without new information.

<a id="sec:mahler-defect"></a>

## The Mahler defect: dyadic totient-kernel finite rank per level, infinite rank overall

**(a) Route as conceived.** A finite-linear-algebra shortcut to \#249: find a bounded-depth linear relation among the dyadic totient-kernel channels $`n\mapsto\varphi(2^jn+r)`$ that would compress the infinite family to a finite-dimensional space, from which a rationality-forcing contradiction (or a genuine rank obstruction) might be extracted.

**(b) Exact mechanism.**

<div class="thm">

**Theorem 269** (Infinite dyadic totient-kernel rank). *For every depth $`e\ge0`$, the canonical family of $`2^e+1`$ dyadic totient-kernel channels ($`\mathtt{card\_totientCanonicalIndex}`$, ) is linearly independent over $`\mathbb Q`$, proved via a `SeparatedMinorCertificate` (an explicit finite evaluation-point assignment with nonzero determinant, forced by CRT + Dirichlet’s theorem on primes in arithmetic progressions — one channel made prime, every other channel forced through a fresh prime $`\equiv1\bmod`$ a large power of $`2`$).*

</div>

; consequently the full infinite family spans an infinite-dimensional $`\mathbb Q`$-space, . A companion impossibility result closes the natural repair attempt directly: a bounded *compressed-adjoint certificate* — a triple $`(Q,A,\mathrm{boundary})`$ with $`Q\cdot v\cdot A=\mathrm{boundary}`$, $`|\mathrm{boundary}|<Q\cdot v`$, $`A\ne0`$ — is provably impossible, . <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:uniform</span> (holds for every $`e`$; existence side is unconditional, via Mathlib’s CRT + primes-in-AP machinery) `coord:binary-digit` (dyadic totient-kernel — *not* the Möbius coordinate).

**(c) Precise scope — coordinate-relative, stated explicitly by the source module.** This does *not* show irrationality of $`S`$. It proves the dyadic-kernel *side* is infinite-rank; the module’s own docstring names the missing input as “a rationality-side finite-rank compression, or equivalent contradiction.”

The companion necessary-consequence-of-rationality theorem, $`\neg\mathrm{Irrational}(S) \implies \exists v>0,\exists U:\mathbb
N\to\mathbb Z,\ \mathrm{IsTemperedBinaryOrbit}(\varphi,v,U)\wedge\forall
e,\ 2^e-1\le\mathrm{finrank}_{\mathbb Q}\,\mathrm{span}(\mathrm{range}(
\mathrm{canonicalCarryKernelFamily}(U,e)))`$ (), shows the SCALE side is finished — the $`2^e-1`$ floor holds for all $`e`$ with a uniform proof — but the opposite inequality (a rationality-side rank *upper* bound) is exactly what is missing, and its absence is the entire open content here.

A *third*, independent coordinate exhibits the same coordinate-relative phenomenon: the Möbius-incidence companion matrix $`U_N(i,j)=\mu((i+1)/(j+1))`$ if $`(j+1)\mid(i+1)`$ else $`0`$ is lower triangular with diagonal $`1`$, hence $`\det U_N=1`$ for every $`N`$, hence its jet-evaluation map is injective — a finite “incidence quotient” compression is impossible at any finite horizon in the Möbius coordinate too (). Both natural finite truncations — dyadic-residue and Möbius-incidence — turn out to have no nontrivial kernel, in two completely different coordinates. That is strong evidence any winning finite-linear-algebra shortcut, if one exists, must live in a genuinely third coordinate or use an infinite/growing-parameter construction, not evidence that no shortcut exists at all.

**(d) Salvage.** and are fully generic finite-rank linear-independence infrastructure — the indexed family is a free variable, reusable for any finite-rank obstruction argument on either problem (e.g. testing independence of Mersenne-indexed sequences for \#257 via an explicit nonzero minor). The CRT+Dirichlet evaluation-forcing technique (make one channel prime, force every other channel through a fresh arithmetic-progression prime) is a reusable construction pattern independent of the totient specifics.

<a id="further-closed-routes-catalogued-for-completeness"></a>

## Further closed routes, catalogued for completeness

The following additional no-gos and route-pruning results were read in full and are recorded here in compressed form; each follows the same (a)/(b)/(c)/(d) discipline as above but is presented as a table row for space.

<div class="landscape">

| **Route** | **Mechanism & site** | **Scope / salvage** |
|:---|:---|:---|
| Full terminal dyadic staircase (annihilate every suffix letter mod growing powers of 2) | $`a\ge8`$, room bound $`\Rightarrow`$ `ActualLcmTerminalDyadicStaircase` is false: the terminal letter would have to be positive (by short-window positivity) and strictly below a wider-than-itself modulus while divisible by it, forcing it to $`0`$, contradicting positivity. . <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:uniform</span> `coord:binary-digit` | Kills the FULL terminal-staircase proof strategy outright and unconditionally; the *punctured* staircase (all but the last letter vanish) survives and is pinned exactly to the half-turn value $`2^{m-1}`$ at the penultimate letter (). The generic mechanism ($`0<e<2^m\wedge2^m\mid e\Rightarrow e=0`$) is reusable anywhere a positive quantity is asked to vanish mod a wider modulus. |
| LCM factor-ideal retention (keep only the homogeneous “factor-only” part of an LCM-ray decomposition) | An explicit nonzero all-horizon countermodel, built from multiples of $`\varphi(\mathrm{periodLcm}(t))`$, agrees with every exact whole-ray anchor $`\Delta\varphi(H,qH)=\varphi(H)`$ for $`2\le q<t`$ and survives every finite commensurate LCM-cube shift-polynomial, at every finite rank. (module docstring; theorem bodies <span class="sans-serif">\[Cert\]</span>, DOCSTRING-SOURCED). <span class="sans-serif">scale:uniform</span> `coord:other:lcm-ray-totient` | This is a *representation*-level exclusion, not an object-level one: it shows the homogeneous factor-ideal projection discards fresh Möbius-channel information that can be adversarially reconstructed. Explicitly flagged SYNTHETIC — no claim that the compensation letters occur as actual totient differences. Salvage: a future factor-ideal argument must control the *fresh* channel via , not just the old one. |
| Two-prime “full-target diamond” (four simultaneous ray hits certify more than one) | The four-hit diamond $`\mathrm{Hit}(H)\wedge\mathrm{Hit}(pH)\wedge\mathrm{Hit}(qH)\wedge
\mathrm{Hit}(pqH)`$ is logically equivalent to $`\mathrm{Hit}(H)`$ alone, no primality of $`p,q`$ needed — hits transport multiplicatively for free because $`\mathrm{Hit}(H)\iff\mathrm{IsIntegralValue}(\text{scaleDiagonalTailDifference}(H))`$ and integrality transports affinely along every ray $`H\mapsto kH`$. . <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:uniform</span> `coord:other:mobius-mersenne` | The 4-condition diamond carries zero information beyond its base point — a “curvature-zero collapse” of a multi-point certificate. Any future positive-holonomy argument needs an independently-defined projection of the foreign state *plus* control of the discarded complement; a bare 2/4-point diamond cannot supply new information beyond its own scale. |
| Fixed-precision local valuation-unit signature (2-adic “tropical curvature carry” attack) | For any finite word of odd-unit-part 2-adic symbols at fixed precision $`u>0`$ and any starting carry state $`e`$, there exists a compatible carry orbit realising the word with every intermediate state centred inside its symbol’s dyadic radius. . <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:bounded</span> `coord:p-adic` | Bounded LOCAL valuation-unit data at FIXED precision can never exclude all finite centred carry completions — no obstruction is derivable from a fixed-window local signature alone; growing precision, or extra arithmetic coupling, is required. Pure 2-adic dynamics, zero totient content, reusable against any similarly-shaped fixed-window carry-certificate attack. |
| Fixed-depth affine carry reset (distinguishing two carry histories after a long common tail) | For the affine binary orbit $`\mathrm{orbit}(0)=u_0`$, $`\mathrm{orbit}(n{+}1)=2\,\mathrm{orbit}(n)-a(n{+}1)`$ with common forcing word $`a`$: $`\mathrm{orbit}_u(L)-\mathrm{orbit}_v(L)=2^L(u_0-v_0)`$ exactly. . <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:uniform</span> `coord:binary-digit` | After $`L`$ common steps the endpoint residue mod $`2^L`$ is *independent* of the initial carry — long common tails erase predecessor information exactly, not approximately. Directly relevant to any argument hoping to distinguish two carry histories from a shared long suffix; the terminal forcing word alone determines the residue. |
| Bounded finite-state / autonomous successor decoder for the binary carry | For a balanced-pulse family at location $`m`$ whose predecessor `State` is constant across the whole family, no $`\mathrm{decode}:\mathrm{State}\to
\mathbb N`$ recovers the radius parameter; any finite `Fintype State` needs $`\mathrm{card}\ge\lfloor m/2\rfloor+2`$, unbounded in $`m`$. . <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:uniform</span> `coord:binary-digit` | Rules out, unconditionally, ANY proof strategy that defines a bounded or autonomous “carry state” summarising pre-$`m`$ history and claims it exactly determines the post-$`m`$ tail — independent of whether the coefficients are $`\varphi`$ or a Möbius-support indicator. A hard stop against finite-automaton-computes-the-expansion style attacks on either problem. |
| Period-4 sign weight as a route to A7’s “frequently nonzero” hypothesis for free | The divisor coefficient of the period-4 sign weight ($`w(a){=}1`$ if $`a{\equiv}1`$, $`-1`$ if $`a{\equiv}3`$, else $`0`$, mod 4) vanishes identically at every $`n\equiv3\pmod4`$, via the divisor-pairing involution $`d\mapsto n/d`$. . <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:fixed</span> `coord:mobius-mersenne` | Witnesses that Dirichlet-convolution coefficients CAN vanish identically on an arithmetic progression, so the “frequently nonzero” hypothesis in the nonnegative-periodic irrationality closure () is not free — it is why the corpus lands a dichotomy for general periodic signed weights rather than an unconditional supply theorem. |
| Certified finite-depth “death” certificates as a route to membership proofs (both problems) | $`\mathtt{CertifiedGreedyMersenneDeath}(x,\mathrm{level},\mathrm{lookahead})`$ is a decidable, finite-depth certificate proving non-membership only (; witness , $`3/4`$ certified dead at level 1). <span class="sans-serif">\[Cert\]</span> <span class="sans-serif">scale:bounded</span> `coord:greedy-orbit` | Structural one-sidedness, recurring across the WHOLE certified-kill family (, , this one): certified-death $`\Rightarrow`$ non-membership, but absence of a found certificate, or survival through any finite depth, proves *nothing* about membership or rationality. |
| Reconstructing one totient value from a two-tail absolute-value linear combination | For any finite $`w:\iota\to\mathbb Q`$, $`x:\iota\to\mathbb N`$ with $`\sum w_i\varphi(x_i)=1`$ (exact isolation), the crude two-tail cost $`\sum|w_i|(2(x_i+1)+(x_i+2))\ge3`$, using only $`\varphi(x)\le x`$. (closure ). <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:uniform</span> `coord:other:totient-adjugate-linear-algebra` | The strategy needs cost $`<1`$ and gets $`\ge3`$ at ANY finite grid height — kills the entire “isolate one coefficient via absolute-value two-tail bookkeeping” family before it starts. The proof mechanism is problem-agnostic (any $`c(n)\le n`$ sequence gets the same floor by the triangle inequality) and transfers verbatim to a \#257 reformulation. |
| Homogeneous Mersenne-primitive prime factor alone forces a contradiction | For the completely-multiplicative control $`c(n)=n`$ (zero totient content): if $`K<q`$, $`q\mid2^K-1`$, the corresponding tail shift is integral at every $`N`$ yet $`q\nmid K`$. . <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:n/a</span> `coord:other:mersenne-modulus` | A primitive prime factor of the homogeneous multiplier $`2^K-1`$ alone supplies NO contradiction from tail integrality. A direct cross-problem warning: \#257’s denominators $`2^n-1`$ are literally this $`q\mid2^K-1`$ object, so “a large primitive Mersenne prime factor alone forces a contradiction” should be checked against this lemma before being attempted on either problem. |
| Prime-power reduced-denominator unit-gap strengthening (rescuing extra Farey lattice points) | At a prime-power reduced denominator $`p^e`$, the unit-gap refinement can rescue at most ONE additional candidate lattice point beyond the ordinary gap certificate. (iff-characterisation ). <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:uniform</span> `coord:other:farey-gap` | A formal ceiling on how much this specific refinement can ever buy — a known dead end for extending the $`\approx7.96\times10^{34}`$ Farey rung (§<a href="#sec:adelic-height" data-reference-type="ref" data-reference="sec:adelic-height">10.4</a>) unboundedly. Do not re-attempt this exact strengthening expecting more than +1 lattice point per prime power; the underlying reduced-denominator-implies-unit-numerator technique is reusable for other denominator-exclusion arguments. |
| Fixed rank-3 finite-difference kernel squeezing more than one dyadic bit of curvature information | $`\mathrm{fixedRankSecondDifference}(2^{n+1}\cdot2,\,2^{n+1}\cdot3)=-2^{n+1}`$ exactly, for all $`n`$: the two-adic valuation gained by the primitive kernel factor $`2\varphi(j)`$ is exactly tight. . <span class="sans-serif">\[Lean\]</span> <span class="sans-serif">scale:n/a</span> `coord:binary-digit` | Route-pruning ammunition: rules out extracting more than one dyadic bit from the bare 3-rank affine kernel $`(1,-2,1)`$; any further progress on the fixed-rank curvature route needs new arithmetic input, not a sharper valuation squeeze from the same kernel. The affine rank-3 kernel classification itself (, pure linear algebra over $`\mathbb Z`$, zero number-theoretic content) is fully reusable for any 3-point finite-difference argument on either problem. |

</div>

<a id="sec:promotion-audit"></a>

# Why the bounds are load-bearing

The near-miss interface between the corpus’s proved results and the four open supply obligations — $`\#249`$-supply, $`\#257`$-reset, $`\#257`$-cofinal-rows, and $`\#257`$-universal — was swept for *promotion candidates*: proved theorems whose *stated* hypotheses looked, on a first read of the `yields` clause, close enough to the open obligation’s shape that a routine strengthening (raising a scale bound, widening a hypothesis, or reindexing a quantifier) might close the gap without new mathematics. Fifty-six near-miss rows were catalogued across the four obligations; eighteen of them were flagged `promotable_claimed: True` on this first pass. **Every one of the eighteen proofs was then opened and read in full**, not merely re-inspected at the statement level, and the promotion claim was checked against the actual proof body. The audit table below reports the verdict for all eighteen.

Of the eighteen, **sixteen are conclusively NOT_PROMOTABLE**: reading the proof body exposes a documented arithmetic, logical, or coordinate obstruction that a routine strengthening cannot cross, and the row’s own record states exactly what new input would be required.

**Two** (`NM-02`, `NM-03` in the $`\#257`$-universal obligation) are genuine exceptions: the auditor found the promotion is available with, in its own words, “no new mathematics” — a pure widening of an already-general proof to a wider stated target. Crucially, *neither of these two closes anything*: they widen an equivalence or a corollary from one fixed target value to a family of targets, without touching the missing arithmetic content (a cofinal certificate supply, a rank upper bound, an anti-concentration estimate) that every genuine closure of $`\#249`$ or $`\#257`$ requires.

So while the promotion audit is not literally eighteen-for-eighteen at the level of “can this exact statement be re-derived for a wider scope,” it is eighteen-for-eighteen at the level that matters for this paper’s obligations: **no promotion candidate in the audited set supplies missing arithmetic content toward closing \#249 or \#257**. The two mechanically-widenable rows are recorded honestly below rather than folded into the sixteen, because collapsing that distinction would itself be exactly the kind of quantifier-slippage error this paper’s accuracy rules forbid.

<div class="landscape">

| **Obligation** | **Row / site** | **Gap kind** | **Verdict and exact blocker** |
|:---|:---|:---|:---|
| -supply | e1-companion, | hypothesis strength | Not promotable. The consumer already has the obligation’s exact quantifier shape; the missing input is a single unproved arithmetic fact — a constant-saving first-harmonic (Weyl-sum) cancellation bound $`\sum_{N\in[X,2X)}\cos(2\pi\cdot(\ldots)/2^L)\le(9/10)X`$ — not proved at any $`X,h,L`$ anywhere in the corpus. |
| 249-supply | SGN-01, | hypothesis strength | Not promotable. Positivity is exactly HALF of the needed certificate: the companion theorem in the same file proves integrality forces the residue to the TOP edge, not a kill — the lower half of the band is discharged unconditionally and cofinally, the upper half is untouched. |
| 249-supply | TE-04, | hypothesis strength | Not promotable. The consumer side is finished and cofinal (proved for every $`a\ge8`$); the residual is purely the one-sided residue-gap *producer*, unconditionally unsupplied at even one large $`a`$. |
| 249-supply | TE-05-weakest, | hypothesis strength | Not promotable. The exact identity pinning the target shows the dominance inequality is equivalent to $`\mathrm{carryOrbit}\le0`$, and the sign machinery (SGN-02) already proves the true carry orbit is strictly *positive* under integrality — the corridor-escape branch the identity naturally supplies is exactly the branch already eliminated. |
| 249-supply | SEP-02, | scale only | Not promotable. The analytic tail is fully discharged with an explicit, uniform error radius; only two exponents ($`a=4,6`$) have the resulting finite distance-to-integer question verified unconditionally (); nothing beyond $`a=6`$ is proved. |
| 249-supply | b7, | coordinate only | Not promotable. The only proved unbounded-growth quantity in the Möbius–Mersenne coordinate, uniform in $`t`$, but there is no landed transport from a denominator lower bound to $`\mathrm{certifiedKill}`$ or to totient-tail non-integrality — a different coordinate from the obligation. |
| 249-supply | d4/d5, , | coordinate only | Not promotable. The scale side of a second, independent open obligation (unbounded carry-kernel rank forced by rationality) is finished uniformly in $`e`$; the opposite (rationality-side rank upper bound) is missing, and one natural route to it is proved dead (). |
| 257-reset | rc-2 / F4-adjacent, | multiple | Not promotable. The excess-side run-length law is only half-assembled: an exact iterate identity exists, and an upper bound on the terminal excess exists separately, but no theorem in Lean composes the two into an excess-side run-length statement, even though every ingredient is present. |
| 257-reset | E1, | coordinate only | Not promotable. Supplies an UPPER bound on the remainder (the ceiling half of the picture); the obligation needs a LOWER bound on the deviation magnitude — the two do not compose without an additional input. |
| 257-reset | rc-8, prose *erdos257_reset_crossing_unification_2026_07_24.md* §6 | multiple | Not promotable. Two gaps at once: the sign law is <span class="sans-serif">\[Cert\]</span>/empirical only (flagged <span class="sans-serif">\[Open\]</span> as an unconditional lemma, not proved), and even if proved it delivers only the SIGN of the deviation, not its magnitude, which is what the obligation needs. |
| 257-cofinal-rows | TH-sharp-capacity-progress, | hypothesis strength | Not promotable. Unconditional and strictly more general than every actual consumer, but it needs a per-$`c`$ input ($`\mathrm{localBinarySuffix}\,D\,1\,(2c{-}2)<2^{c-2}`$) that the corpus only ever supplies through a route which then rigidly collapses onto one specific support family — the deficit hypothesis is a self-imposed restriction of the consumers, and the general input itself is unsupplied. |
| 257-cofinal-rows | precriticalSuffix_lt_of_future_skip_after_takenBlock, | hypothesis strength | Not promotable. Unconditional and uniform in both parameters $`(c,t)`$; the sole missing input is an orbit-level skip-gap bound on the rational half-greedy orbit, never proved and never previously isolated as a target anywhere in the banks. |
| 257-cofinal-rows | greedyHalfFrozenMargin_nonneg, | scale only | Not promotable. The margin-nonnegativity horizon is produced by a *non-effective* limit argument (an existential horizon from a convergence fact); the exact-row route needs the SPECIFIC effective horizon $`J=k-2`$, and effectivising it is explicitly recorded as unfinished bookkeeping, not new mathematics — but it is still unfinished. |
| 257-cofinal-rows | C4a, | multiple | Not promotable. Trades off against the obligation in the opposite direction on *support locality*: tolerates any support inside a depth window but demands a carry inside a tight $`\sim2\sqrt M`$ strip, where the obligation tolerates an exponentially looser carry but demands the support be confined to a lower window — the gap is support locality, not carry size, and neither socket implies the other. |
| 257-universal | NM-02, | scale only | **PROMOTABLE (no new mathematics), but does not close anything.** The proof was opened and found already uniform in the target in every internal step; only the statement’s own quantifier is artificially pinned to $`t=1/2`$. Promoting it converts the whole half-greedy refutation machine from a one-target equivalence to one covering every rational target — the highest-value mechanical promotion in the bank — but it supplies no new arithmetic content: it is a restatement, not a producer. |
| 257-universal | NM-03, | scale only | **PROMOTABLE (no new mathematics), but does not close anything.** The headline is pinned to target $`1/2`$ while its engine () is already fully general over finite supports; verbatim re-derivation at any even-denominator target is available with zero new arithmetic. Paired with NM-02: universal \#257 at $`b=2`$ is false iff some rational $`t`$ with even reduced denominator has an infinitely-skipping greedy Mersenne orbit — a genuine reformulation, not a resolution. |
| 257-universal | NM-04, | coordinate only | Not promotable (partial mechanical content only). The dyadic restriction $`v=1`$ is a call-site choice, not a proof constraint — the general-$`v`$ conclusion is already landed for arbitrary $`(v,h,L,F)`$ at — but the strict form needed for non-dyadic targets requires one genuinely new auxiliary bound (a mean-least-residue estimate) not present in the corpus. |
| 257-universal | NM-12, | scale only | Not promotable (unverified, not merely blocked). The killer and the dichotomy scaffold are already target-generic; the two endpoint kills that pin the dichotomy to $`1/2`$ generalise on their face, but their proof bodies were explicitly *not* read in this audit pass — recorded as a strong promotability hypothesis, not a verified promotion, since a `norm_num`-style numeric step could hide a $`1/2`$-specific bound. |

</div>

<a id="classification-of-the-sixteen-genuine-blockers"></a>

## Classification of the sixteen genuine blockers

Reading all eighteen proof bodies rather than trusting the `yields` clause exposes a small, recurring taxonomy of blocker shapes, tagged by `gap_kind` in the table above:

- **hypothesis_strength** (6 rows: e1-companion, SGN-01, TE-04, TE-05-weakest, TH-sharp-capacity-progress, precriticalSuffix_lt_of_future_skip_after_takenBlock). The consumer theorem is already at the obligation’s exact quantifier shape; a single named arithmetic fact — a Weyl-sum cancellation bound, a one-sided residue gap, an orbit-level skip-gap bound — is missing and is not a re-derivation of anything on disk.

- **scale_only** (5 rows: SEP-02, greedyHalfFrozenMargin_nonneg, NM-02, NM-03, NM-12). The mathematics is either already general or reduces to a finite verified range; what is missing is either extending a finite census (SEP-02) or effectivising a non-constructive existence bound (greedyHalfFrozenMargin_nonneg). NM-02 and NM-03 are the two genuine exceptions where scale widening costs nothing — and, being restatements, buy nothing toward closure either.

- **coordinate_only** (4 rows: b7, d4/d5, E1, NM-04). A quantity is proved unconditionally in one coordinate (Möbius–Mersenne denominator growth, dyadic-kernel rank, remainder upper bound, dyadic support-fraction mass) with no landed transport into the coordinate the obligation is stated in.

- **multiple** (3 rows: rc-2/F4-adjacent, rc-8, C4a). More than one of the above simultaneously — typically an unassembled composition of two otherwise-landed halves, or two orthogonal deficiencies (empirical-only plus sign-not-magnitude) stacked on the same row.

No row in the audited eighteen falls under `quantifier_order` — every row with a genuine quantifier-order mismatch (e.g. `a12`’s $`\exists N\,\exists L\,\forall h`$ versus the obligation’s $`\forall h\,\forall N_0\,\exists N\,\exists L`$) was judged NOT promotable at first read and excluded from the eighteen entirely, rather than surviving to a full proof-body audit. The eighteen audited here are precisely the rows whose *stated* hypotheses looked closest to the obligation; that even this most-favourable subset yields sixteen genuine blockers and only two costless-but-empty restatements is the paper’s evidence that the corpus’s bounds are load-bearing in the strict sense: no amount of routine strengthening of what is already proved, at the level the audit checked, supplies the missing arithmetic content that $`\#249`$ or $`\#257`$ actually needs.

<a id="the-mathematics-this-problem-still-needs"></a>

# The mathematics this problem still needs

Everything in Parts I–IV of this document is either a theorem about $`\varphi`$ or a theorem about proof methods for $`\varphi`$. Nothing in it decides Erdős \#249, and this section does not either. What this section does is different in kind from the rest: it takes each route that survives the barrier classification, states the missing mathematics as an exact sentence, identifies the shape of argument that could supply it, names the precise point at which the nearest existing technique fails, and — where the evidence permits — attempts the construction rather than describing it.

Four things are new here and are marked as such. (i) An exact normal form that turns every surviving \#249 route into a statement about the binary expansion of one explicit real number, with the thresholds computed (Lemma <a href="#lem:orbit" data-reference-type="ref" data-reference="lem:orbit">271</a>, Proposition <a href="#prop:transfer" data-reference-type="ref" data-reference="prop:transfer">272</a>, Corollary <a href="#cor:digitform" data-reference-type="ref" data-reference="cor:digitform">273</a>). (ii) A proof that the first-harmonic gap is strictly stronger than irrationality, by an explicit witness inside the same coefficient class (Theorem <a href="#thm:lacunary" data-reference-type="ref" data-reference="thm:lacunary">275</a>); the corpus had this only as a plausibility argument. (iii) A one-sided smooth-number majorant for the non-supplier budget and a bad-cofactor estimate, with their remaining uniformity hypotheses exposed (Propositions <a href="#prop:dickman" data-reference-type="ref" data-reference="prop:dickman">276</a> and <a href="#prop:badcof" data-reference-type="ref" data-reference="prop:badcof">277</a>); the quantifier audit also shows that the proposed shallow-modulus Siegel–Walfisz route does not fit the predicate. (iv) An audit of the rationality-side rank route: its proposed generic counterexample loses one zero-residue section per level, so it neither refutes nor retires the route.

Where a claim is proved it is marked <span class="sans-serif">\[Math\]</span>; where it is checked by exact or floating-point computation, <span class="sans-serif">\[Cert\]</span>; where it is quoted, <span class="sans-serif">\[Cited\]</span>; where it is a proposal, <span class="sans-serif">\[Open\]</span>. No proposal below is offered as progress towards a solution. Two of them are reductions, and a reduction is not a result.

<div class="rem">

*Remark 270*. Declarations in the shared tree are cited as `Erdos249257.name` with file and line. Declarations in the newer per-problem tree are cited with their path from the repository root, `ErdosProblems/Erdos249/File.lean:line`; the hyperlink target for those is the per-problem directory, not `Erdos249257/`.

</div>

<a id="one-identity-and-what-it-does-to-every-surviving-route"></a>

## One identity, and what it does to every surviving route

Write $`S=\sum_{n\ge 1}\varphi(n)/2^n`$, $`R_N=\sum_{m\ge 1}\varphi(N+m)/2^m`$ for the local tail (), and $`\Phi_N=\sum_{n\le N}\varphi(n)2^{N-n}\in\mathbb{Z}`$ for the integer prefix, so that $`2^N S=\Phi_N+R_N`$. For $`h\ge 1`$ set
``` math
\alpha_h \;:=\; (2^h-1)\,S .
```

<div id="lem:orbit" class="lem">

**Lemma 271** (Doubling normal form). *For all $`N\ge 0`$ and $`h\ge 1`$,
``` math
R_{N+1}=2R_N-\varphi(N+1),
  \qquad
  R_{N+h}-R_N \;=\; 2^N\alpha_h-\bigl(\Phi_{N+h}-\Phi_N\bigr),
```
so $`R_{N+h}-R_N \equiv 2^N\alpha_h \pmod 1`$, and consequently the exact first character of the tail difference is the $`\times 2`$ orbit of one real number:
``` math
\mathrm{tailOrbitFirstExp}(h,N)
  \;=\; e\bigl(2^N\alpha_h\bigr),
  \qquad e(x):=\exp(2\pi i x).
```
Hence, for fixed $`h`$, the phases $`\{\,R_{N+h}-R_N \bmod 1\,\}_{N\ge 0}`$ are the forward orbit of $`\alpha_h \bmod 1`$ under $`x\mapsto 2x`$.*

</div>

The second identity and the character form are landed: and `coord:other:binary-window`. The recurrence $`R_{N+1}=2R_N-\varphi(N+1)`$ is one line from the definition and is used below only for intuition <span class="sans-serif">\[Math\]</span>.

This is not a new fact — it is two landed Lean theorems read together — but reading them together has a consequence the corpus never draws. The first-harmonic block sum, which is the analytic frontier of \#249, is a *lacunary exponential sum in a single real variable*. The following proposition makes the transfer exact, including the truncation budget.

<div id="prop:transfer" class="prop">

**Proposition 272** (Orbit transfer). *Define
``` math
\mathrm{OrbitBlockGap} :\equiv
  \forall h\ge 1\ \forall X_0\ \exists X\ge \max(X_0,1):\quad
  \sum_{N=X}^{2X-1}\cos\bigl(2\pi\,2^{N}\alpha_h\bigr)\;\le\;\tfrac{89}{100}\,X .
```
Then $`\mathrm{OrbitBlockGap}`$ implies that $`S`$ is irrational.*

</div>

<div class="proof">

*Proof.* Fix $`h\ge 1`$ and $`X_0`$, and take $`X`$ as supplied. Choose $`L`$ with $`2^{L}\ge 1024\,(2X+h+L+2)`$; such $`L`$ exists because $`2^L/L\to\infty`$, and it satisfies the room inequality $`16(2X+h+L+2)\le 2^L`$ a fortiori. For every $`N<2X`$ the landed truncation bound gives $`\bigl\|\,\mathrm{windowFirstExp}(h,N,L)-e(2^N\alpha_h)\,\bigr\|
 < 2\pi(N+L+h+2)/2^{L} \le 2\pi/1024 < 1/100`$, so by , $`\mathrm{windowFirstCos}(h,N,L)\le \cos(2\pi 2^N\alpha_h)+1/100`$. Summing over the $`X`$ values $`N\in[X,2X)`$ gives $`\sum_N \mathrm{windowFirstCos}(h,N,L)\le \tfrac{89}{100}X+\tfrac{1}{100}X
=\tfrac{9}{10}X`$, so produces $`N\in[X,2X)`$ with $`\mathrm{certifiedKill}(h,N,L)`$, and $`N\ge X\ge X_0`$. This is exactly the certificate supply consumed by . ◻

</div>

<span class="sans-serif">\[Math\]</span> `coord:other:binary-window`. The proof uses only landed lemmas; formalising it is a variant of with the constant $`21/25`$ replaced by the real-part constant $`89/100`$ and the room factor $`16`$ by $`1024`$. Nothing here is an improvement of the analytic requirement; it is a change of coordinate that makes the requirement legible.

<div id="cor:digitform" class="cor">

**Corollary 273** (Digit form of the analytic requirement). *Let $`\rho_h(X)`$ denote the proportion of $`N\in[X,2X)`$ with $`\|2^N\alpha_h\|_{\mathbb{R}/\mathbb{Z}}\ge 1/4`$. If for every $`h\ge 1`$ there are cofinally many $`X`$ with $`\rho_h(X)\ge 11/100`$, then $`S`$ is irrational. Equivalently, when $`\alpha_h`$ is not a dyadic rational: if for every $`h`$ there are cofinally many dyadic blocks $`[X,2X)`$ in which the binary expansion of $`\alpha_h`$ contains at least $`0.11X`$ digit changes — that is, in which the mean binary run length is at most $`9.1`$ — then $`S`$ is irrational.*

</div>

<div class="proof">

*Proof.* $`\|x\|\ge 1/4`$ forces $`\cos 2\pi x\le 0`$, and the remaining terms are at most $`1`$, so $`\sum_{N}\cos(2\pi 2^N\alpha_h)\le (1-\rho_h(X))X`$; require $`1-\rho\le 89/100`$ and apply Proposition <a href="#prop:transfer" data-reference-type="ref" data-reference="prop:transfer">272</a>. For the digit reading, $`\|2^N\alpha_h\|\ge 1/4`$ holds exactly when the binary digits of $`\alpha_h`$ in positions $`N+1,N+2`$ differ. ◻

</div>

<span class="sans-serif">\[Math\]</span>. This threshold is worth staring at. A single digit change in every ninth position, in one block per scale, for each fixed $`h`$, would settle Erdős \#249. What is actually true, numerically, is far stronger.

<div id="tab:blocks">

| $`h`$ | $`X`$ | $`\rho_h(X)`$ | $`X^{-1}\sum_{N\in[X,2X)}\cos(2\pi 2^N\alpha_h)`$ | required |
|---:|---:|---:|---:|---:|
| $`1`$ | $`256`$ | $`0.4766`$ | $`\phantom{-}0.0037`$ | $`\le 0.89`$ |
| $`1`$ | $`2048`$ | $`0.5073`$ | $`-0.0043`$ | $`\le 0.89`$ |
| $`3`$ | $`256`$ | $`0.4648`$ | $`\phantom{-}0.0296`$ | $`\le 0.89`$ |
| $`3`$ | $`2048`$ | $`0.5020`$ | $`\phantom{-}0.0027`$ | $`\le 0.89`$ |
| $`8`$ | $`2048`$ | $`0.5112`$ | $`-0.0088`$ | $`\le 0.89`$ |
| $`13`$ | $`2048`$ | $`0.5049`$ | $`-0.0195`$ | $`\le 0.89`$ |

Block statistics for $`\alpha_h=(2^h-1)S`$, computed from the exact integer $`\lfloor 2^{6000}S\rfloor`$ (error $`<1`$ in the last bit, tail bound $`(M+2)2^{-M}`$ at $`M=6080`$). Over positions $`1..5800`$ the binary expansion of $`\alpha_1`$ has $`2864`$ runs, mean run length $`2.0251`$, longest run $`13`$; for $`\alpha_3`$, $`2964`$ runs, mean $`1.9568`$, longest $`12`$; for $`\alpha_8`$, $`2927`$ runs, mean $`1.9816`$, longest $`14`$. A uniform digit model predicts mean run length $`2`$ and longest run $`\approx\log_2 5800\approx 12.5`$. <span class="sans-serif">\[Cert\]</span>

</div>

<div id="obs:allroutes" class="obs">

*Observation 274*. Under Lemma <a href="#lem:orbit" data-reference-type="ref" data-reference="lem:orbit">271</a> every route that survives the barrier classification becomes a statement about the binary expansion of $`S`$ or of some $`\alpha_h`$. Routes 1 and 2 ask for a positive proportion of digit changes in a block; Route 3 asks for one short run at a prime-indexed position; Route 4 asks that two blocks of digits of $`S`$ at distance $`h`$ disagree early. The routes differ in *which positions* they interrogate and *how uniform* the margin must be, not in what they are about. This is developed in §<a href="#sub:shape" data-reference-type="ref" data-reference="sub:shape">12.7</a>.

</div>

<a id="route-1-a-constant-saving-cancellation-over-a-dyadic-block"></a>

## Route 1: a constant-saving cancellation over a dyadic block

<a id="the-exact-statement-needed."></a>

#### The exact statement needed.

``` math
\forall h\ge 1\ \forall X_0\ \exists X,L:\quad
  \max(X_0,1)\le X,\quad 16(2X+h+L+2)\le 2^{L},\quad
  \Bigl\|\sum_{N=X}^{2X-1} e\bigl(D(h,N,L)/2^{L}\bigr)\Bigr\|\le \tfrac{21}{25}X,
```
where $`D(h,N,L)=\sum_{j<L}\bigl(\varphi(N+h+1+j)-\varphi(N+1+j)\bigr)2^{L-1-j}`$. , consumer . By Proposition <a href="#prop:transfer" data-reference-type="ref" data-reference="prop:transfer">272</a> the weaker real-part form with constant $`89/100`$ suffices.

<a id="what-d-is-as-an-arithmetic-object."></a>

#### What $`D`$ is, as an arithmetic object.

Dividing by $`2^L`$ and reindexing the two ranges onto a common variable $`t`$, with $`m=N+t`$,
``` math
\begin{equation}
\label{eq:window}
  \frac{D(h,N,L)}{2^{L}}
  =\underbrace{-\sum_{t=1}^{h}\frac{\varphi(N+t)}{2^{t}}}_{\text{head}}
  \;+\;\underbrace{(2^{h}-1)\sum_{t=h+1}^{L}\frac{\varphi(N+t)}{2^{t}}}_{\text{body}}
  \;+\;\underbrace{\sum_{t=L+1}^{L+h}\frac{\varphi(N+t)}{2^{t-h}}}_{\text{tail}} .
\end{equation}
```

So the phase is a *geometrically weighted linear form in $`\varphi`$ at $`L+h`$ consecutive arguments*, with the value at offset $`t`$ entering modulo $`2^{t}`$ and with an odd multiplier $`2^h-1`$ throughout the body.

Two features control everything that follows. First, the weight at offset $`t`$ has denominator exactly $`2^{t}`$, so offset $`t`$ contributes nothing unless $`v_2(\varphi(N+t))<t`$: the $`2`$-adic valuation of the totient is the gate.

Second, $`2^h-1`$ is odd, so the multiplier never closes a gate that $`\varphi`$ leaves open.

<a id="which-technique-family-is-even-the-right-shape."></a>

#### Which technique family is even the right shape.

Four candidates, in decreasing order of relevance.

*Weyl differencing and van der Corput* are the wrong shape and can be dismissed exactly. Both require the phase to be a smooth or polynomial function of the summation variable so that a difference operator lowers its degree. Here $`N\mapsto D(h,N,L)/2^{L}`$ is, by Lemma <a href="#lem:orbit" data-reference-type="ref" data-reference="lem:orbit">271</a>, the $`\times 2`$ orbit map: differencing in $`N`$ multiplies the phase by $`2`$ and subtracts an integer, so the difference operator is an exact isometry of the problem and lowers nothing. This is not a heuristic — it is $`R_{N+1}=2R_N-\varphi(N+1)`$ read modulo $`1`$.

*The large sieve* needs a family of well-separated frequencies and a sum over both the frequencies and the variable. Here there is one frequency per $`N`$ and no family: the sum is over a single orbit. A large-sieve inequality could be applied after introducing an artificial family (for example, over the $`h`$ parameter), but the predicate quantifies $`h`$ universally, so an average over $`h`$ is not admissible.

*Vaughan/Vinogradov bilinear decomposition* is the right shape, and is what Route 2 already implements: decompose the argument $`N+t`$ at a large prime factor, use $`\varphi(mp)=\varphi(m)(p-1)`$ to linearise the phase in $`p`$, and sum over primes. §<a href="#sub:pivot" data-reference-type="ref" data-reference="sub:pivot">12.3</a> carries this as far as it goes.

*Erdős’s 1948 digit method*, which proved irrationality of $`E=\sum_n 1/(2^n-1)=\sum_N d(N)/2^N`$, is the right shape for the `coord:mobius-mersenne` coordinate. That coordinate exists here and is exact: from $`\varphi=\mu * \mathrm{id}`$,
``` math
\begin{equation}
\label{eq:mobmers}
  S=\sum_{d\ge 1}\mu(d)\,\frac{2^{d}}{(2^{d}-1)^{2}}
  \qquad ({\small\textsf{[Math]}};\ \text{verified to }16\ \text{digits},\ S=1.3676308019850223\ldots,\ {\small\textsf{[Cert]}}).
\end{equation}
```

But the method does not transfer, for a reason that can be stated quantitatively rather than vaguely. Erdős’s argument for $`E`$ exploits that the coefficient $`d(N)`$ has enormous multiplicative fluctuation: over $`N\le Y`$ the ratio of its maximum to its typical value is $`Y^{(\log 2+o(1))/\log\log Y}`$, so certain highly composite $`N`$ deposit identifiable spikes into the digit stream. The coefficient here is $`\varphi(N)`$, which satisfies $`\varphi(N)/N\in[c/\log\log N,1]`$: its multiplicative fluctuation over $`N\le Y`$ is a factor $`e^{\gamma}\log\log Y`$, that is, $`\log\log Y`$ rather than $`Y^{c/\log\log Y}`$. There are no spikes to find.

In the Möbius–Mersenne coordinate <a href="#eq:mobmers" data-reference-type="eqref" data-reference="eq:mobmers">[eq:mobmers]</a> the situation is worse rather than better: the coefficients $`\mu(d)`$ change sign, so the digit blocks contributed by successive $`d`$ cancel rather than accumulate, and there is no positivity to run a block argument on. This is, as far as the evidence in this corpus goes, the specific reason \#249 is harder than its Erdős–Borwein ancestor.

<a id="the-specific-obstacle-what-the-estimate-cannot-be-deduced-from."></a>

#### The specific obstacle: what the estimate cannot be deduced from.

The corpus records that no theorem proves the first-harmonic gap inequivalent to irrationality, and argues the point from the structure of a collapse proof. It can be settled outright, and the witness lives in the same coefficient class that carries barriers B1 and B7.

<div id="thm:lacunary" class="thm">

**Theorem 275** (The gap is strictly stronger than irrationality). *Let $`c(n)=1`$ if $`n=k!`$ for some $`k\ge 1`$ and $`c(n)=0`$ otherwise, so $`0\le c(n)\le n`$ for all $`n\ge 1`$, and let $`\beta=\sum_{n\ge1}c(n)/2^{n}
=\sum_{k\ge 1}2^{-k!}`$. Then $`\beta`$ is irrational, and for every $`h\ge 1`$ and every $`X\ge 81(h+5)`$,
``` math
\sum_{N=X}^{2X-1}\cos\bigl(2\pi\,2^{N}(2^{h}-1)\beta\bigr) \;>\; \tfrac{9}{10}X .
```
Consequently the block-gap requirement fails at *every* scale for $`\beta`$, while $`\beta`$ is irrational. No proof of the block gap for $`S`$ can therefore proceed from the irrationality of $`S`$ together with the growth bound $`c(n)\le n`$; it must use arithmetic of $`\varphi`$.*

</div>

<div class="proof">

*Proof.* Irrationality of $`\beta`$ is Liouville’s criterion. Write $`\gamma=(2^{h}-1)\beta=\sum_{k}(2^{h-k!}-2^{-k!})`$, so for every $`k`$ with $`k!>2h`$ the binary expansion of $`\gamma`$ carries ones exactly in the positions $`k!-h+1,\dots,k!`$ and zeros between consecutive such blocks. If $`N\le k!-h-5`$ for the least $`k`$ with $`k!>N`$, then $`\{2^{N}\gamma\}\le 2\cdot 2^{-5}=1/16`$, whence $`\|2^{N}\gamma\|\le 1/16`$ and $`\cos(2\pi 2^{N}\gamma)\ge\cos(\pi/8)>0.9239`$. The remaining $`N`$ lie in $`(k!-h-5,\,k!]`$, at most $`h+5`$ values per factorial, and consecutive factorials differ by a factor exceeding $`2`$ from $`k\ge 3`$, so the window $`[X,2X)`$ meets at most one such interval. Therefore the sum exceeds $`0.9239\,(X-h-5)-(h+5)`$, which exceeds $`\tfrac{9}{10}X`$ once $`X\ge 81(h+5)`$. ◻

</div>

<span class="sans-serif">\[Math\]</span> `coord:other:binary-window`. This upgrades the corpus’s “no collapse mechanism is known to apply” to “no collapse mechanism can exist”. It also says precisely what the missing input must do: it must rule out that $`S`$ behaves, in its doubling orbit, like a Liouville number. That is the content of Corollary <a href="#cor:digitform" data-reference-type="ref" data-reference="cor:digitform">273</a>, and it is why the requirement is a digit-statistics statement and not an irrationality statement.

<a id="size-of-the-quantity-honestly-calibrated."></a>

#### Size of the quantity, honestly calibrated.

Under any model in which the binary digits of $`\alpha_h`$ behave like fair coin flips, $`\rho_h(X)\to 1/2`$ and the block sum is $`O(\sqrt{X\log\log X})`$ by the Erdős–Gál law of the iterated logarithm for lacunary series <span class="sans-serif">\[Cited\]</span>. The requirement is $`\rho_h\ge 0.11`$ and a saving of a constant factor. The measured values in Table <a href="#tab:blocks" data-reference-type="ref" data-reference="tab:blocks">1</a> are $`\rho_h\approx 0.50`$ and a block average of order $`X^{-1/2}`$. So the analytic requirement is weaker than the apparent truth by a factor $`\sqrt X`$, and the difficulty is entirely that no technique produces *any* nontrivial digit statistic for an explicit constant of this kind. That is a statement about technology, and it is worth separating from a statement about $`S`$.

<a id="sub:pivot"></a>

## Route 2: the four-term pivot budget

<a id="the-exact-statement-needed.-1"></a>

#### The exact statement needed.

For every $`h\ge 1`$ there must exist $`s\ge 1`$ and $`\eta\in(0,1)`$ such that for every $`X_0`$ there are $`X\ge\max(X_0,1)`$ and $`L`$ with $`h\le L-s`$, $`16(2X+h+L+2)\le 2^{L}`$, and all four of
``` math
\begin{aligned}
  \operatorname{Re}\bigl(\mathrm{pivotCenteredCorrelation}\bigr) &\le \tfrac{14}{25}X,
  &\qquad \bigl\|\mathrm{pivotFiberMeanContribution}\bigr\| &\le \tfrac{1}{100}X,\\
  \bigl\|\mathrm{pivotBadContribution}\bigr\| &\le \tfrac{1}{100}X,
  &\qquad \bigl\|\mathrm{pivotNonSupplierContribution}\bigr\| &\le \tfrac{8}{25}X .
\end{aligned}
```
, consumer . The decomposition is an exact identity, , and the supplier set at the canonical fibre is a membership equality with a shifted dyadic interval of primes, .

<a id="one-budget-has-a-classical-one-sided-majorant."></a>

#### One budget has a classical one-sided majorant.

The non-supplier term is not identified exactly by smooth numbers. What the factorisation gives is the one-way containment needed for an upper bound.

<div id="prop:dickman" class="prop">

**Proposition 276** (Non-suppliers: the valid one-sided estimate). *Choose the admissible depth $`L`$ minimally for each large $`X`$, with the predicate’s previously fixed $`h`$ and $`s`$. If $`n=N+L-s+1`$ is not a supplier, then its largest prime factor satisfies
``` math
P(n)\le (4+o(1))\sqrt X .
```
Therefore
``` math
\#\{N\in[X,2X):\neg\,\mathrm{pivotSupplier}(X,L,s,N)\}
  \le
  \Psi(2X+O(\log X),(4+o(1))\sqrt X)
  -\Psi(X+O(\log X),(4+o(1))\sqrt X).
```
A uniform smooth-number asymptotic for this shifted interval would make the right side $`(1-\log2+o(1))X<\tfrac8{25}X`$ and would discharge the budget.*

</div>

<div class="proof">

*Proof.* Let $`p=P(n)`$ and $`m=n/p`$. Supplier failure means either $`p\le2\lfloor\sqrt X\rfloor`$ or $`m>\lfloor\sqrt X\rfloor/2`$ (up to the definition’s exact floor and positivity clauses). In the second case $`p=n/m\le(4+o(1))\sqrt X`$, because minimal admissible $`L`$ gives $`L-s+1=O(\log X)`$ and hence $`n<2X+O(\log X)`$. Thus every non-supplier lies in the displayed smooth-number set. This proves only an upper bound, not an asymptotic equality for the non-supplier count. ◻

</div>

<span class="sans-serif">\[Math\]</span> for the containment; <span class="sans-serif">\[Cited\]</span> for the smooth-number estimate needed to finish the numerical budget. In particular the earlier identity with Dickman density, and numerical extrapolations of an exact crossover scale, are not claimed. The implication is sufficient if the required uniform shifted-interval estimate is supplied.

<div id="prop:badcof" class="prop">

**Proposition 277** (The bad-cofactor budget). *For $`\eta\in(0,1)`$ let $`B(\eta)=\{m:\varphi(m)<\eta m\}`$, with natural density $`D(\eta)`$; by Schoenberg’s theorem $`D`$ exists, is continuous, and $`D(0+)=0`$ <span class="sans-serif">\[Cited\]</span>. Then
``` math
\#\{N\in[X,2X): N\ \text{a supplier with cofactor}\ m\in B(\eta)\}
  \;\le\;\bigl(D(\eta)+o(1)\bigr)X ,
```
so a single choice of $`\eta`$ with $`D(\eta)<1/200`$ meets the $`\tfrac{1}{100}X`$ budget for all large $`X`$. Since $`\eta`$ is quantified existentially before $`X_0`$, and a smaller $`\eta`$ only enlarges the good set, this choice costs nothing elsewhere in the budget.*

</div>

<div class="proof">

*Proof sketch.* Suppliers with cofactor $`m`$ number $`\pi(2X/m)-\pi(X/m)`$, which is at most $`(2X/m)/\log X`$ up to $`1+o(1)`$ because $`m\le\sqrt X/2`$ forces $`\log(X/m)\ge\tfrac12\log X`$. Sum over $`m\in B(\eta)`$ with $`m\le\sqrt X/2`$ and use that the logarithmic density of $`B(\eta)`$ tends to $`D(\eta)`$. ◻

</div>

<span class="sans-serif">\[Math\]</span> . The choice is not tight: the least element of $`B(1/5)`$ is $`2\cdot3\cdot5\cdot7\cdot11\cdot13=30030`$, with $`\varphi(m)/m=5760/30030=0.19181`$, and the logarithmic density of $`B(1/5)`$ up to $`3\cdot10^{5}`$ is $`3\cdot 10^{-5}`$ <span class="sans-serif">\[Cert\]</span>. So $`\eta=1/5`$ is already defensible pending an explicit numerical bound on $`D(1/5)`$, and that bound is itself a finite computation a reader could start today.

<a id="the-pivot-quantifiers-force-a-deep-modulus."></a>

#### The pivot quantifiers force a deep modulus.

The pivot sits at offset $`t=L-s+1`$ in <a href="#eq:window" data-reference-type="eqref" data-reference="eq:window">[eq:window]</a>. Crucially, the definition of `DTWPivotResidualDecorrelation` chooses $`s`$ once, after $`h`$ and before the universal threshold $`X_0`$. Thus $`s`$ is fixed as $`X\to\infty`$; it cannot be increased with $`X`$ to make $`t`$ shallow. The room condition gives
``` math
2^L\ge16(2X+h+L+2),\qquad
  t=L-s+1\ge\log_2X-O_{h,s}(1).
```
After removing the $`2`$-part of the coefficient, the prime-progression modulus is still typically of order $`X`$ up to subpolynomial factors, not $`(\log X)^A`$. Standard Siegel–Walfisz therefore does not reach the quantifier order of the stated predicate; choosing a hypothetical $`t=O(\log\log X)`$ would amount to choosing $`s`$ after $`X`$, which the predicate forbids.

The exact $`2`$-adic triviality observation remains useful: if $`v_2(\varphi(m))\ge t`$, then the pivot phase is $`1`$. It does not create a nonempty analytic window under the actual quantifiers. Hence the claimed shallow-modulus route is withdrawn. This does not disprove the pivot predicate; it says only that the proposed prime-distribution argument does not supply it. <span class="sans-serif">\[Math\]</span> <span class="sans-serif">scale:cofinal</span>.

<a id="the-specific-obstacle-the-weight-is-neither-type-i-nor-type-ii."></a>

#### The specific obstacle: the weight is neither Type I nor Type II.

Propositions <a href="#prop:dickman" data-reference-type="ref" data-reference="prop:dickman">276</a> and <a href="#prop:badcof" data-reference-type="ref" data-reference="prop:badcof">277</a> isolate possible bookkeeping bounds, subject to their stated uniform estimates. The fixed-$`s`$ quantifier leaves the fibre-mean modulus deep, and the centred term has a separate correlation obstruction.

Factoring the pivot argument as $`n=mp`$ and dividing out the pivot phase leaves
``` math
\operatorname{Re}\sum_{m}\ \sum_{p\,:\,mp\in[X,2X)+t}
    w(mp)\,\bigl(e\bigl(a_m(p-1)/2^{t}\bigr)-\overline{e}_m\bigr)
  \;\le\;\tfrac{14}{25}X ,
  \qquad |w|\equiv 1 ,
```
where $`\overline{e}_m`$ is the fibre mean and, by <a href="#eq:window" data-reference-type="eqref" data-reference="eq:window">[eq:window]</a>, $`w(n)`$ is the character of the same weighted totient sum with the single offset $`t`$ deleted.

Vinogradov’s bilinear method requires that, after the decomposition $`n=mp`$, the summand split as $`\alpha_m\beta_p`$ (Type II) or be independent of $`p`$ given $`m`$ (Type I), up to boundedly many pieces. The weight $`w(mp)`$ is neither: it is a function of the totients of the $`L+h`$ integers *adjacent* to $`mp`$, and $`\varphi(mp+j)`$ for $`j\ne0`$ bears no relation to the factorisation $`mp`$ — it is not a function of $`m`$, not a function of $`p`$, and not a product of the two. No device is known that converts a weight of this shape into bilinear form.

At $`h=1`$ and the canonical pivot the required estimate becomes fully explicit. There $`e\bigl((p-1)/4\bigr)=i^{\,p-1}=\chi_{-4}(p)`$, so what is needed is
``` math
\operatorname{Re}\sum_{X<p\le 2X}\chi_{-4}(p)\,
    e\Bigl(\frac{\varphi(p+1)}{8}+\frac{\varphi(p+2)}{16}+\cdots\Bigr)
  \;\le\;\Bigl(\frac{9}{10}-\delta\Bigr)\,\bigl(\pi(2X)-\pi(X)\bigr).
```

The missing input is thus a *non-correlation between a fixed quadratic character at $`p`$ and the $`2`$-adic behaviour of $`\varphi`$ at the shifts $`p+1,p+2,\dots`$*: a correlation statement for two arithmetic functions at shifted arguments, of Chowla–Elliott type. The unconditional results in that family — Matomäki–Radziwiłł in almost all short intervals, Tao’s logarithmically averaged Chowla, Tao–Teräväinen for odd order <span class="sans-serif">\[Cited\]</span> — are averaged, never pointwise at a single scale.

<a id="a-swing-the-predicate-needs-only-cofinally-many-x-so-average-over-x."></a>

#### A swing: the predicate needs only cofinally many $`X`$, so average over $`X`$.

This is the one place where the shape of the obligation is a gift. Both $`\mathrm{DTWFirstHarmonicNormGap}`$ and $`\mathrm{DTWPivotResidualDecorrelation}`$ ask for *some* $`X`$ beyond each $`X_0`$, never for all $`X`$. Hence it suffices to prove a logarithmically averaged bound: if
``` math
\sum_{k\le K}\ \frac{1}{2^{k}}
  \Bigl|\sum_{N\in[2^{k},2^{k+1})}e\bigl(D(h,N,L_k)/2^{L_k}\bigr)\Bigr|
  \;=\;o(K)
  \quad\text{for each }h,
```
with $`L_k`$ any admissible depth sequence, then infinitely many blocks satisfy the gap and Proposition <a href="#prop:transfer" data-reference-type="ref" data-reference="prop:transfer">272</a> applies. Logarithmic averaging is exactly the regime in which the entropy-decrement method operates.

The first concrete step is not to prove this but to decide whether the method reaches it: the phase $`e\bigl(D(h,N,L)/2^{L}\bigr)`$ is not multiplicative, but it is a bounded *local function of a multiplicative function* — a fixed continuous function of $`\bigl(\varphi(N+1)/2,\dots,\varphi(N+L)/2^{L}\bigr)`$ read modulo $`1`$ — whereas entropy decrement is stated for correlations of bounded multiplicative functions along fixed shifts. The precise question to settle, and it can be started on immediately, is whether the decrement survives when the observable is a local function of $`\varphi`$ with a growing number of coordinates $`L\approx\log_2X`$ rather than a product of boundedly many multiplicative values. <span class="sans-serif">\[Open\]</span>

<a id="route-3-uniform-quantitative-escape-at-primes"></a>

## Route 3: uniform quantitative escape at primes

<a id="the-exact-statement-needed.-2"></a>

#### The exact statement needed.

``` math
\forall h\ge 1\ \forall N_0\ \exists p\ \text{prime}:\quad
  \max(N_0+h+1,\,h+5)\le p
  \ \wedge\
  \operatorname{Re}\bigl(\mathrm{tailOrbitFirstExp}(h,\,p-h-1)\bigr)<\tfrac{9}{10}.
```
, consumer .

<a id="what-it-says-after-lemma-lemorbit."></a>

#### What it says, after Lemma <a href="#lem:orbit" data-reference-type="ref" data-reference="lem:orbit">271</a>.

$`\operatorname{Re}e(2^{p-h-1}\alpha_h)<9/10`$ says $`\|2^{p-h-1}\alpha_h\|_{\mathbb{R}/\mathbb{Z}}>\arccos(9/10)/2\pi=0.0717831\ldots`$, so the requirement is exactly: *for each $`h`$, the indicated prime-indexed $`\times2`$ orbit point stays more than $`0.0717831\ldots`$ from the nearest integer, for cofinally many primes $`p`$*. A short-run condition on the binary digits can be a sufficient proxy for this circle-distance inequality, but it is not equivalent to it; a run-length description alone does not determine the residual position inside the dyadic cylinder.

<a id="the-specific-obstacle."></a>

#### The specific obstacle.

Two, stacked. First, this is a *pointwise* demand: it names an index, and the promotion audit records that no pointwise producer in this programme has ever been supplied at even one large index, across seven independent attempts, while the single audited row whose missing input is a block average is the first-harmonic row.

Second, and sharper: digit behaviour *along the primes* is strictly harder than digit behaviour on average even for constants where the average case is settled. The only constants whose digits are understood at all along a sparse subsequence are ones built for the purpose (Champernowne; Copeland–Erdős) <span class="sans-serif">\[Cited\]</span>. No technique reads the digits of an explicit constant at prime positions.

<a id="numerical-calibration."></a>

#### Numerical calibration.

Among the $`501`$ primes in $`[1000,5000)`$, the proportion with $`\operatorname{Re}e(2^{p-h-1}\alpha_h)<9/10`$ is $`0.8623`$ for $`h=1`$, $`0.8503`$ for $`h=2`$, $`0.8583`$ for $`h=5`$, with minima below $`-0.9999`$ <span class="sans-serif">\[Cert\]</span>. The cofinal supply is thus met by about six primes in seven at these scales. As with Route 1, the requirement is very weak and the obstacle is that nothing sees it.

<a id="a-swing-replace-the-pointwise-demand-by-a-canonical-fibre."></a>

#### A swing: replace the pointwise demand by a canonical fibre.

The corpus warns against the subset consumer because a predicate quantifying existentially over subsets $`T\subseteq[X,2X)`$ is collapse-exposed: the proved collapse works precisely by *choosing* $`T=\{N,N+1\}`$. That warning applies to a free $`T`$.

It does not apply to a $`T`$ named in advance as a function of $`(h,X,L)`$, and the corpus already contains the right one:
``` math
T_{h,X,L}\;:=\;\mathrm{pivotFiber}(X,L,L-h,1)
  \;=\;\{\,N\in[X,2X)\ :\ N+h+1\ \text{prime}\,\},
```
a membership equality rather than a sampled surrogate (, <span class="sans-serif">\[Lean\]</span>).

The proposal is to prove
``` math
\begin{equation}
\label{eq:primefibre}
  \forall h\ge1\ \forall X_0\ \exists X\ge X_0,\ L:\quad
  16(2X+h+L+2)\le 2^{L}
  \ \wedge\
  \sum_{N\in T_{h,X,L}}\mathrm{windowFirstCos}(h,N,L)\ \le\ \tfrac{9}{10}\,\bigl|T_{h,X,L}\bigr| ,
\end{equation}
```
which by the landed subset consumer yields a certificate at some $`N\ge X\ge X_0`$, hence irrationality. <span class="sans-serif">\[Open\]</span>

Three features make this the sharpest available target.

\(i\) On this fibre the cofactor is $`m=1`$, so the pivot coefficient is $`(2^{h}-1)\varphi(1)=2^{h}-1`$, which is *odd*, so the $`2`$-adic triviality described above cannot occur.

\(ii\) The pivot modulus is $`2^{h+1}`$, *fixed* once $`h`$ is fixed, so the fibre-mean term is governed by the prime number theorem in progressions to a fixed power of two, where the Ramanujan main term $`c_{2^{h+1}}(2^{h}-1)=\mu(2^{h+1})=0`$ vanishes for every $`h\ge1`$ and the error term is effective; the fixed-$`s`$ deep-modulus obstruction does not apply to this separately defined canonical fibre.

\(iii\) The bookkeeping budgets of §<a href="#sub:pivot" data-reference-type="ref" data-reference="sub:pivot">12.3</a> disappear: inside $`T`$ there are no non-suppliers and no bad cofactors. What remains is exactly one estimate — decorrelation of the fixed phase $`e\bigl((2^{h}-1)(p-1)/2^{h+1}\bigr)`$ from the residual totient weight — and it is the same estimate isolated at the end of §<a href="#sub:pivot" data-reference-type="ref" data-reference="sub:pivot">12.3</a>. This does not make that estimate easier. It removes everything that is not that estimate.

<div class="rem">

*Remark 278*. Honesty about <a href="#eq:primefibre" data-reference-type="eqref" data-reference="eq:primefibre">[eq:primefibre]</a>: it is not proved to be strictly stronger than irrationality, and no collapse is proved either. What can be said is that the one collapse mechanism that exists in this lane consumes the freedom to choose the sample, and <a href="#eq:primefibre" data-reference-type="eqref" data-reference="eq:primefibre">[eq:primefibre]</a> has no such freedom. Deciding this either way — exhibiting a collapse, or a witness in the coefficient class of Theorem <a href="#thm:lacunary" data-reference-type="ref" data-reference="thm:lacunary">275</a> that separates it from irrationality — is itself a well-defined finite piece of work.

</div>

<a id="route-4-depth-locked-full-depth-escape"></a>

## Route 4: depth-locked full-depth escape

<a id="the-exact-statement-needed.-3"></a>

#### The exact statement needed.

``` math
\mathrm{ApFullDepthEscape} :\equiv
  \forall d\ge 1\ \forall N\ \exists t\ge 1:\ \mathrm{certifiedKill}(td,\,N,\,td),
```
unpacked, $`(N+2td+2:\mathbb{Z})<D(td,N,td)\bmod 2^{td}<2^{td}-(N+2td+2)`$. , consumer , ambient equivalence . It is the shortest fully stated open inequality the programme has produced.

<a id="what-it-says-an-anti-self-similarity-statement-about-the-digits-of-s-alone."></a>

#### What it says: an anti-self-similarity statement about the digits of $`S`$ alone.

Writing $`h=td`$ and using $`D(h,N,L)/2^{L}=(R_{N+h}-R_N)-(R_{N+L+h}-R_{N+L})/2^{L}`$ at $`L=h`$, together with the landed strip $`|R_{M+h}-R_M|<M+h+2`$ (, <span class="sans-serif">\[Lean\]</span>), applied at $`M=N+h`$, one gets:

<div id="prop:route4" class="prop">

**Proposition 279**. *$`\mathrm{certifiedKill}(h,N,h)`$ holds whenever $`\bigl\|2^{N+h}S-2^{N}S\bigr\|_{\mathbb{R}/\mathbb{Z}}>2(N+2h+2)/2^{h}`$.*

</div>

<div class="proof">

*Proof.* $`\|D(h,N,h)/2^{h}\|\ge\|R_{N+h}-R_N\|-|R_{N+2h}-R_{N+h}|/2^{h}
 >2(N+2h+2)/2^{h}-(N+2h+2)/2^{h}=(N+2h+2)/2^{h}`$, and $`R_{N+h}-R_N\equiv 2^{N}(2^{h}-1)S=2^{N+h}S-2^{N}S\pmod 1`$ by Lemma <a href="#lem:orbit" data-reference-type="ref" data-reference="lem:orbit">271</a>. A residue at distance more than $`(N+2h+2)/2^{h}`$ from $`\mathbb{Z}`$ is exactly a certified kill at depth $`h`$. ◻

</div>

<span class="sans-serif">\[Math\]</span>. So Route 4 asks: *for every ray $`d`$ and every basepoint $`N`$, some multiple $`h=td`$ is such that the tail of the binary expansion of $`S`$ beginning at position $`N+1`$ and the tail beginning at position $`N+h+1`$, read as reals in $`[0,1)`$, are more than $`2(N+2h+2)/2^{h}`$ apart in $`\mathbb{R}/\mathbb{Z}`$.* Two things follow. First, unlike Routes 1–3, this involves only $`S`$ itself, not the multiples $`\alpha_h`$. Second, the required precision grows only like $`\log_2(N+2h)`$ while the available depth grows linearly in $`t`$: the demand weakens rapidly along each ray.

<a id="which-technique-family-fits-and-why-it-is-unavailable."></a>

#### Which technique family fits, and why it is unavailable.

A statement that a sequence does not almost repeat at some multiple of every gap, to logarithmic precision, is a *subword-complexity* statement, and the mature technology for such statements about a specific real number is the Adamczewski–Bugeaud method: the Schmidt subspace theorem applied to the $`b`$-ary expansion, which shows that an algebraic irrational cannot have too many long repetitions <span class="sans-serif">\[Cited\]</span>. The shape fits exactly. The hypothesis does not: the method conditions on algebraicity, and $`S`$ is not known to be algebraic — indeed it is not known to be irrational, which is the whole problem. There is no version of the method that runs from an analytic description of the constant. That is the entire obstruction, and it is worth stating plainly because it explains why Route 4 looks so much easier than it is: the required combinatorial property is weak, but the only machine that produces such properties needs an input we do not have.

<a id="what-the-data-says."></a>

#### What the data says.

At $`N=300`$, the least $`t`$ with $`\mathrm{certifiedKill}(td,300,td)`$ exists and is small for every ray $`d\le 24`$: $`t=10`$ for $`d=1`$, $`t=5`$ for $`d=2`$, $`t=4`$ for $`d=3`$, $`t=3`$ for $`d=4`$, $`t=2`$ for $`5\le d\le 9`$, and $`t=1`$ for $`10\le d\le 24`$ — in every case at or near the first depth admitted by the room floor. The residues are not marginal: $`r/2^{h}=0.3594`$ at $`d=1`$, $`0.5977`$ at $`d=3`$, $`0.6853`$ at $`d=7`$, $`0.2620`$ at $`d=17`$, $`0.5887`$ at $`d=23`$, against edge radii $`3.1\cdot10^{-1}`$, $`8.0\cdot10^{-2}`$, $`2.0\cdot10^{-2}`$, $`2.6\cdot10^{-3}`$, $`4.1\cdot10^{-5}`$ <span class="sans-serif">\[Cert\]</span>. This is a floor, not a trend, exactly as barrier B1 requires; it decides nothing.

<a id="a-heuristic-size-computation."></a>

#### A heuristic size computation.

Under a uniform model for $`\|2^{N}(2^{h}-1)S\|`$ the failure probability at depth $`h=td`$ is $`\approx 4(N+2h+2)/2^{h}`$, which is $`\approx 1`$ at the first admissible $`t`$ and falls by a factor $`2^{d}`$ at each subsequent $`t`$. The probability that a given $`(d,N)`$ fails at every $`t`$ is therefore a product $`\prod_{j\ge0}\min(1,\,c\,2^{-jd})`$, super-exponentially small, and the expected number of failing pairs $`(d,N)`$ over all $`N`$ converges. At $`d=1`$, $`N=300`$ the product evaluates to about $`10^{-5}`$, and the observed value is a success at the very first admissible depth. The model therefore predicts Route 4 holds with enormous margin — which is precisely why no finite computation will ever be evidence for it. <span class="sans-serif">\[Open\]</span> (heuristic).

<a id="route-5-the-rationality-side-rank-bound-remains-open"></a>

## Route 5: the rationality-side rank bound remains open

<a id="the-exact-statement-that-was-wanted."></a>

#### The exact statement that was wanted.

``` math
\exists C\ \forall c:\mathbb{N}\to\mathbb{N}\ \bigl(c(n)\le n,\ \neg\,\mathrm{Irrational}(X_c)\bigr)
  \ \forall v>0\ \forall u\ \mathrm{IsTemperedBinaryOrbit}(c,v,u)\ \forall e:\quad
  \operatorname{rk}_e(u)\le C ,
```
where $`X_c=\sum_{n\ge1}c(n)/2^{n}`$ and $`\operatorname{rk}_e(u)`$ is the dimension of the span of the dyadic sections of $`u`$ through level $`e`$. A suitable subexponential upper bound would also contradict the landed $`\varphi`$-specific floor . No such rationality-side upper bound is proved.

<a id="the-right-vocabulary-and-the-audited-gap."></a>

#### The right vocabulary, and the audited gap.

Finite-dimensional span of all dyadic sections is the definition of a $`2`$-regular sequence in the sense of Allouche and Shallit <span class="sans-serif">\[Cited\]</span>. The unconditional theorem says that $`\varphi`$ is not $`2`$-regular. An attempted generic counterexample chose a coefficient sequence $`c(n)\le n`$ with rational binary series and non-$`2`$-regular dyadic kernel. Those facts do not refute the desired bound for its carry orbit.

The generic recurrence
``` math
v\,c(N+1)=2u(N)-u(N+1)
```
does express each *positive-residue* level-$`j`$ section of $`c`$ as a linear combination of two level-$`j`$ sections of $`u`$. It does not control the zero-residue section at each level. Across levels $`1,\ldots,e`$ those omitted sections can contribute up to $`e`$ new directions, not a fixed $`O(1)`$ error. Consequently non-$`2`$-regularity of $`c`$ alone does not imply unbounded $`\operatorname{rk}_e(u)`$, and the previously claimed bound $`\operatorname{rk}_e(u)\ge2^{e-1}-3`$ has no valid proof here. The proposed greedy set construction therefore supplies neither a counterexample nor a reason to retire the route. <span class="sans-serif">\[Gap\]</span> <span class="sans-serif">scale:uniform</span> `coord:other:carry-kernel`.

The Lean theorem for $`\varphi`$ remains valid: it uses the special structure and independently proved linear independence of the totient kernel, not the invalid generic $`O(1)`$ bridge. The honest status is thus asymmetric. The large $`\varphi`$-specific rank floor is proved; a rationality-driven ceiling is open; and the generic countermodel attempt is inconclusive.

<a id="sub:shape"></a>

## What the shape of the wall suggests about the object

Everything in this subsection is inference from the assembled evidence, not theorem. It is written because the assembly makes one inference available that no individual reformulation does, and because refusing to draw it would be a different kind of dishonesty than drawing it carelessly.

<a id="first-a-fact-rather-than-an-inference-the-routes-are-one-route-in-five-coordinates."></a>

#### First, a fact rather than an inference: the routes are one route in five coordinates.

Lemma <a href="#lem:orbit" data-reference-type="ref" data-reference="lem:orbit">271</a> collapses the coordinate spread that made the corpus look like many independent attacks.

<div class="center">

| Route | What it asks of the binary expansion | Positions interrogated |
|:---|:---|:---|
| 1, 2 | at least $`11\%`$ of positions carry a digit change; mean run length $`\le 9.1`$ in one block per scale | a full dyadic block of $`\alpha_h`$ |
| 3 | one run of length $`\le 3`$ | positions $`p-h`$, $`p`$ prime, in $`\alpha_h`$ |
| 4 | the tails at gap $`h`$ differ by more than $`2(N+2h+2)2^{-h}`$ | every basepoint, some multiple of every ray, in $`S`$ |
| 5 | an open rationality-side upper bound on the carry-orbit kernel rank | all dyadic sections through level $`e`$ |

</div>

This is the honest content of the operator’s “hundred measurements of one wall”. The measurements are of one thing, and the thing is the binary digit sequence of $`S`$ and of its multiples $`(2^{h}-1)S`$. The routes differ in which positions they interrogate and how uniform a margin they demand; they do not differ in subject.

<a id="second-the-wall-is-a-wall-about-explicit-constants-not-about-varphi."></a>

#### Second: the wall is a wall about explicit constants, not about $`\varphi`$.

Of the seven barriers, six — B1, B2, B3, B5, B6, B7 — are statements that a class of proof cannot see the digits: bounded inspection, retargeting, strengthening, bounded state, finite linear compression, coarse invariants. None asserts that the digits misbehave. Only B4 is internal to the object, and even B4 says that one engineering scheme self-cancels, not that the quantity being engineered is unattainable. Meanwhile the two object-level witnesses the corpus can produce — the $`\gamma`$-splice of B1, the parity coboundary of B7 — and the one produced here (Theorem <a href="#thm:lacunary" data-reference-type="ref" data-reference="thm:lacunary">275</a>) are all lacunary or eventually periodic: constructed, measure-zero, and highly structured. In two centuries nobody has exhibited a naturally occurring constant with Liouville-type digit behaviour; every known example is built to have it. So the shape of the barrier set points at our technology, not at $`S`$.

<a id="third-is-the-object-behind-the-measurements-simple-or-complex"></a>

#### Third: is the object behind the measurements simple or complex?

The evidence available leans one way, and I will say how far it leans.

*For “generic, and the difficulty is entirely ours”.* (a) Every statistic measurable is indistinguishable from a fair-coin digit model: $`\rho_h(X)\approx0.50`$ against a required $`0.11`$; mean run length $`1.96`$–$`2.03`$ against a permitted $`9.1`$; longest run $`12`$–$`14`$ over $`5800`$ positions against a model prediction of $`\approx12.5`$; block sums of order $`X^{-1/2}`$ against a permitted $`0.89`$ (Table <a href="#tab:blocks" data-reference-type="ref" data-reference="tab:blocks">1</a>, <span class="sans-serif">\[Cert\]</span>). (b) The requirements are weaker than the apparent truth by a factor $`\sqrt X`$; a proof does not need to understand the digits, only to exclude a pathology. (c) All countermodels are constructed lacunary objects. (d) The one coordinate in which $`S`$ has classical structure — the Möbius–Mersenne form <a href="#eq:mobmers" data-reference-type="eqref" data-reference="eq:mobmers">[eq:mobmers]</a> — is an alternating sum of rational functions of $`2^{d}`$ with no functional equation, no modularity, no continued-fraction structure, and no algebraicity: there is no hidden object to find, which is consistent with genericity.

*Against, or at least complicating.* (a) B4’s self-cancellation is exact, unconditional, and holds at every depth $`K`$: the cost of forcing a depth-$`K`$ residue by a Dirichlet prime is $`p\ge1+2^{K-1}`$ while the payoff is amplitude $`2^{K-1}`$, so the trade is precisely null. An exact null of that form is a structural fact and not an accident of parametrisation, and it is the one place where the object itself pushes back. (b) The exact census records residues approaching the forbidden edge — a closest central margin of about $`2.2\cdot10^{-4}`$ of the modulus at $`t=100`$ — which is what a uniform model predicts and which rules out, permanently, any argument that proceeds by a crude uniform margin. (c) Proposition <a href="#prop:dickman" data-reference-type="ref" data-reference="prop:dickman">276</a> shows that even the pieces of the frontier that are provable become true only past $`X\approx10^{30}`$–$`10^{40}`$; a genuinely simple object would not usually require asymptotics that begin so late.

*Verdict, flagged as inference.* The evidence supports “the digits of $`S`$ are generic and the wall is technological” over “the object is subtle”, but it does not determine it, and the reason it cannot is structural: every test performed is a test a generic object passes, so passing them is weak evidence, and the only tests that would discriminate are exactly the ones no technique can run. What the evidence *does* determine is narrower and firmer: the difficulty of \#249 is not located in $`\varphi`$’s irregularity — $`\varphi`$ is the smoothest interesting multiplicative function, with multiplicative fluctuation $`\log\log Y`$ where $`d(n)`$ has $`Y^{c/\log\log Y}`$ — but in the fact that we possess no method whatsoever for lower-bounding digit changes of a constant that was not designed to have them. That is why the Erdős–Borwein constant fell in 1948 and this one has not: $`d(n)`$ has spikes to deposit into the digit stream and $`\varphi(n)`$ does not, and in the Möbius coordinate the signs cancel.

<a id="what-would-actually-change-the-picture."></a>

#### What would actually change the picture.

One theorem, of any strength, giving a nontrivial digit statistic for $`S`$ or for some $`\alpha_h`$: an upper bound $`o(N)`$ on the longest binary run in the first $`N`$ positions would not by itself decide \#249, but it would be the first evidence that the object is legible at all, and by Corollary <a href="#cor:digitform" data-reference-type="ref" data-reference="cor:digitform">273</a> any bound strong enough to give a positive proportion of digit changes in one block per scale would decide it. Failing that, the two concrete openings identified above are: the logarithmically averaged form of the block gap, where the entropy-decrement method is at least in the right regime (§<a href="#sub:pivot" data-reference-type="ref" data-reference="sub:pivot">12.3</a>); and the canonical prime fibre <a href="#eq:primefibre" data-reference-type="eqref" data-reference="eq:primefibre">[eq:primefibre]</a>, where every budget except one decorrelation estimate has been discharged. Neither is close. Both are well posed, and both can be started on today.

<a id="what-is-open-stated-exactly"></a>

# What is open, stated exactly

Erdős \#249 asks whether $`S = \sum_{n\ge 0} \varphi(n)/2^n`$ is irrational. It is <span class="sans-serif">\[Open\]</span>: nothing in this corpus decides it.

Every attack recorded in Parts I–IV terminates, in one of exactly two ways, at a small number of *cofinal supply obligations* on the totient tail $`R_N := \sum_{j\ge 0}\varphi(N+1+j)/2^{j+1}`$ (): either it proves a genuine theorem of the shape “*if* this cofinal predicate holds, *then* $`S`$ is irrational,” with the predicate itself left completely unproved, or it prunes one specific proof shape and shows it cannot supply the predicate.

This section renders every such obligation exactly as Lean states it, gives its site, records which of them are proved *equivalent* to one another (iff) and which are proved only *sufficient* (one-directional, an easier target implied by a harder one), and closes by naming, without overclaiming, the piece of new mathematics each surviving form would need. Quantifier order is preserved exactly as written in Lean; nowhere below does a finite verified list stand in for a cofinal supply, and nowhere does an implication get reported as a solved case.

Throughout, $`H_t := \mathrm{periodLcm}(t) = \operatorname{lcm}(1,\dots,t)`$ (), $`D(h,N,L) := \sum_{j<L}\bigl(\varphi(N{+}h{+}1{+}j)-\varphi(N{+}1{+}j)\bigr)\cdot 2^{L-1-j}\in\mathbb{Z}`$ is `windowDiscrepancy` (), and the base predicate named “$`\mathrm{Sep}(h,N,L)`$” in the task brief is literally `certifiedKill`:
``` math
\mathrm{certifiedKill}(h,N,L) :\equiv
  (N+h+L+2 : \mathbb{Z}) < D(h,N,L) \bmod 2^L
  \ \wedge\
  D(h,N,L) \bmod 2^L < 2^L - (N+h+L+2).
```
(the definition; decidable, instance at line 84) `coord:other:binary-window`. In words: the residue of the window discrepancy modulo $`2^L`$ avoids a shrinking radius-$`(N+h+L+2)`$ neighbourhood of $`0`$ inside the growing modulus $`2^L`$.

<a id="the-certificate-completeness-converter"></a>

## The certificate-completeness converter

Every reformulation below ultimately measures the same underlying real quantity, because certificates are *complete* receipts of non-integrality, not merely sufficient ones:
``` math
\bigl(\exists L,\ \mathrm{certifiedKill}(h,N,L)\bigr)
  \iff
  R_{N+h} - R_N \notin \operatorname{range}\bigl((\uparrow)\colon \mathbb{Z}\to\mathbb{R}\bigr).
```
(wrapped as `totient_tail_window_kill_exists_iff_tail_diff_not_int` at ) (holds for all $`h,N`$) `coord:other:binary-window`.

*Note.* This iff is the reason every “certificate supply” form below can be restated, without loss, in “pure non-integrality” language with no certificate vocabulary at all (the B8/TE forms). It does *not* assert that the cofinal supply exists; it only says the certificate route and the real-analytic route are the same route.

<a id="the-base-cofinal-obligation-the-wall"></a>

## The base cofinal obligation — the wall

> **Obligation 1 (certificate-supply normal form).**
> ``` math
> \mathrm{Irrational}(S)
>   \quad\Longleftrightarrow\quad
>   \forall h\ge 1,\ \forall N_0,\ \exists N\ge N_0,\ \exists L,\
>   \mathrm{certifiedKill}(h,N,L).
> ```

This is exactly the quantifier structure named “$`\mathrm{Sep}(h,N,L)`$” in the task brief: $`\forall h\ge 1\ \forall N_0\ge 0\ \exists N\ge N_0\ \exists L\ \mathrm{Sep}(h,N,L)`$. (the equivalence is proved; the supply itself is unsupplied) `coord:other:binary-window`.

The reverse direction is by contradiction against the tail-period law: if $`S`$ were rational, `eventual_period_of_not_irrational` (, <span class="sans-serif">\[Lean\]</span>, unconditional) supplies a period $`h>0`$ and pre-period $`N_0`$ with $`R_{N+h}-R_N\in\mathbb{Z}`$ for all $`N\ge N_0`$; the certificate hypothesis instantiated at that $`(h,N_0)`$ produces an $`N\ge N_0`$ where $`R_{N+h}-R_N\notin\mathbb{Z}`$, a contradiction via `tail_diff_notMem_int_of_certifiedKill` ().

For the forward direction, irrationality gives pointwise non-integrality of every positive tail shift and certificate completeness supplies a witness already at $`N=N_0`$.

*What supplying Obligation 1 would take:* an arithmetic (not merely existential) argument that, for every period length $`h`$ and past every threshold $`N_0`$, the totient window discrepancy’s residue mod $`2^L`$ can be pushed off $`0`$ by a margin growing with the modulus — i.e., genuine cancellation/anti-concentration information about $`\varphi`$ on a sliding window, at every scale, for every $`h`$. No such argument exists in the corpus; the rows below are exact normal forms or sufficient producers for this missing input, never a proof that the input holds.

<a id="collapsing-free-parameters-the-multiple-diagonal-cone-chain"></a>

## Collapsing free parameters: the multiple / diagonal / cone chain

Three further reformulations replace Obligation 1’s two free parameters $`(h,N_0)`$ with successively less information. The multiple and cone predicates have explicit reductions to irrationality; the lcm-diagonal predicate has a registered iff. Since Obligation 1 itself is an iff, every predicate both implied by Obligation 1 and sufficient for irrationality is also propositionally equivalent to it, even when the corpus exposes only the two directed constructions rather than a separately named iff.

<a id="multiple-period-collapse-formally-looser-but-endpoint-equivalent."></a>

#### Multiple-period collapse (formally looser, but endpoint-equivalent).

``` math
\forall h_0>0,\ \forall N_0,\ \exists m>0,\ \exists N\ge N_0,\ \exists L,\
    \mathrm{certifiedKill}(m\cdot h_0, N, L)
  \ \Longrightarrow\ \mathrm{Irrational}(S).
```
`coord:other:lcm-period-multiple`. Obligation 1’s hypothesis trivially implies this one (take $`m=1`$), while the displayed theorem sends it back to irrationality and hence, by the base iff, back to Obligation 1. It is an easier-looking target, not progress; it remains exactly as open as \#249.

<a id="diagonal-collapse-one-free-parameter."></a>

#### Diagonal collapse — one free parameter.

``` math
\mathrm{Irrational}(S)
  \ \Longleftrightarrow\
  \forall t_0,\ \exists t\ge t_0,\ \exists L,\
    \mathrm{certifiedKill}(H_t, H_t, L).
```
`coord:other:lcm-diagonal`. This is the canonical single-quantifier restatement: write $`P(t) :\equiv \exists L,\ \mathrm{certifiedKill}(H_t,H_t,L)`$; the obligation is $`\forall t_0\,\exists t\ge t_0,\ P(t)`$. The reduction is a genuine proof, not a relabelling: given $`t\ge\max(h_0,N_0)`$, $`h_0\mid H_t`$ and $`H_t\ge
t\ge N_0`$ simultaneously, so a single diagonal witness at $`t`$ discharges *both* of Obligation 1’s free parameters at once, via the intermediate lemma which itself reduces to the multiple-period form above. Conversely, irrationality and pointwise certificate completeness give the diagonal witness already at $`t=t_0`$.

$`P(t)`$ is verified for every $`t\le82`$ (). The historical bank contained 28 explicit values through $`t=64`$ (, depths $`[6,5,7,7,9,14,15,14,21,22,23,26,\dots]`$ for $`t\in\{1,2,3,4,5,7,8,9,11,13,16,17,\dots\}`$; endpoint ) <span class="sans-serif">\[Cert\]</span> <span class="sans-serif">scale:fixed</span> `coord:other:lcm-diagonal`). The current contiguous band is still a finite floor, not a cofinal supply; no certificate at $`t=83`$ is claimed.

<a id="cone-collapse-two-multipliers-still-the-same-wall."></a>

#### Cone collapse — two multipliers, still the same wall.

``` math
\forall t_0,\ \exists t\ge t_0,\ \exists q,m,L,\ 0<q\ \wedge\
    \mathrm{certifiedKill}(m\cdot H_t,\, q\cdot H_t,\, L)
  \ \Longrightarrow\ \mathrm{Irrational}(S).
```
`coord:other:lcm-cone`. The diagonal form above is exactly the cell $`q=m=1`$, so any diagonal witness trivially witnesses the cone form. The cone predicate is therefore a formally looser target, but its sufficiency theorem and the base iff make it propositionally equivalent to \#249 rather than an unconditional advance. It rests on a genuine strengthening of the tail-period law, *lcm-cone flatness*: if $`S`$ is rational there is $`t_1`$ such that for every $`t\ge t_1`$ and every $`q>0,m`$, $`R_{qH_t+mH_t}-R_{qH_t}\in\mathbb{Z}`$ — rationality flattens the *whole* cone $`\{k H_t : k\ge 1\}`$, not just one difference (, <span class="sans-serif">\[Lean\]</span>, unconditional).

A sharper cone-form producer, `coneNonflatCert`, needs only a *one-sided* radius per vertex — information-theoretically half of `certifiedKill`’s pairwise floor — and proves that some pair in a finite multiplier menu $`Q`$ is non-integral; the corresponding supply, $`\exists`$ an unbounded-scale menu $`Q`$ with `coneNonflatCert` firing, is <span class="sans-serif">\[Open\]</span>, <span class="sans-serif">scale:cofinal</span>, .

<a id="pure-non-integrality-form-certificate-vocabulary-stripped-out."></a>

#### Pure non-integrality form — certificate vocabulary stripped out.

Via the completeness iff above, the diagonal and cone forms restate, *exactly*, with no reference to $`\mathrm{certifiedKill}`$ at all:
``` math
\forall t_0,\ \exists t\ge t_0,\ R_{2H_t}-R_{H_t}\notin\mathbb{Z}
  \ \Longleftrightarrow\ \text{diagonal obligation above}
  \ \Longrightarrow\ \mathrm{Irrational}(S),
```
(cone analogue at ) `coord:other:real-analytic-nonintegrality`. This is the frontier of \#249 with every piece of certificate machinery removed: *does $`R_{2H_t}-R_{H_t}\notin\mathbb{Z}`$ for infinitely many $`t`$?* Nothing decides this either.

<a id="the-exponential-sum-form"></a>

## The exponential-sum form

A first-harmonic (Weyl-sum) cancellation statement is proved sufficient for Obligation 1 by an elementary pigeonhole argument, with no case analysis and no scale-degrading constants:
``` math
\mathrm{DTWFirstHarmonicNormGap} :\equiv\
  \forall h>0,\ \forall X_0,\ \exists X,L,\quad
  \max(X_0,1)\le X\ \wedge\
  16\,(2X+h+L+2)\le 2^L\ \wedge\
  \Bigl\|\sum_{N\in[X,2X)} e\bigl(D(h,N,L)/2^L\bigr)\Bigr\| \le \tfrac{21}{25}X.
```
(the predicate; unproved at every $`h,X_0`$) `coord:other:first-harmonic`.

``` math
\mathrm{DTWFirstHarmonicNormGap} \ \Longrightarrow\ \mathrm{Irrational}(S).
```
`coord:other:first-harmonic`. The consumer already has Obligation 1’s exact free-parameter shape ($`X`$ is a completely free threshold, so applying the gap at $`X\ge N_0`$ gives $`\exists N\ge N_0\ \exists L`$ directly); what is missing is not scale and not coordinate, it is the arithmetic input itself — not one instance of a constant-saving cancellation bound for the complex exponential sum $`\sum_{N\in[X,2X)} e(D(h,N,L)/2^L)`$ is proved anywhere in the corpus, at any $`h,X,L`$.

A strictly stronger *subset* form (a saving on any nonempty finite $`T\subseteq[0,2X)`$, no density or partition hypothesis) is also proved sufficient and unconditional as an implication: consumes the elementary block lemma (<span class="sans-serif">\[Lean\]</span>, unconditional: *any* constant-saving first-harmonic gap on one dyadic block forces a finite kill certificate, via $`\cos(\pi/8)>9/10`$ and averaging).

*What supplying this form would take:* genuine cancellation for the first additive character of the totient window discrepancy — a Weyl-type bound, uniform in $`h`$ and growing $`L`$, on a character sum built from $`\varphi`$ differences, not merely an existence statement. rules out one entire class of candidate proofs: a residual-blind determinant/rank certificate cannot see this cancellation, because an explicit “locked” unit-norm gauge reconstructs the exact bad configuration while keeping any Vandermonde-shaped minor nonzero — any real argument here must couple the rows arithmetically, not merely normalise columns.

<a id="the-actual-orbit-reformulation-and-the-top-edge-staircase"></a>

## The actual-orbit reformulation and the top-edge staircase

A second, independently developed lane (the public pinned modules `TotientActual*`/`TotientFixedRank*`) restates \#249 in terms of the *actual* power-of-two LCM diagonal, $`H = H_{2^a}`$, and proves a genuine **iff** with the totient series itself — the strongest form of “exact statement of what remains” anywhere in the corpus.

> **The exact equivalence.**
> ``` math
> \mathrm{Irrational}(S)
>   \iff
>   \forall a_0,\ \exists a\ge a_0,\ \mathrm{actualLcmTailOrbit}(a)\notin\mathbb{Z}.
> ```

(an unconditional equivalence, not a supply) `coord:mobius-mersenne`, where $`\mathrm{actualLcmTailOrbit}(a) := 2^H(2^H-1)S - (\mathrm{totientPrefix}(2H)-\mathrm{totientPrefix}(H))`$, $`H=H_{2^a}`$ (). *This is \#249 restated with nothing left over*: no auxiliary hypothesis, no scale caveat — cofinal non-integrality of this one sparse sequence at power-of-two heights is exactly Erdős \#249. Everything else in this subsection is an attempt to reach the right-hand side.

<a id="route-pruning-total-staircase-collapse-is-impossible."></a>

#### Route-pruning: total staircase collapse is impossible.

Before any positive target, the file proves one entire proof shape is empty. For $`a\ge 8`$ and room bound $`J+K+(a{+}6)<2\cdot 2^a`$ with a wide enough modulus $`2H+J+K+2<2^m`$, a terminal window where *every* one of the last $`m`$ letters vanishes mod its own growing power of two is impossible:
``` math
\neg\,\mathrm{ActualLcmTerminalDyadicStaircase}(a,J,K,m).
```
`coord:mobius-mersenne`. The mechanism is a bare positivity/divisibility contradiction (a positive quantity below a modulus, divisible by that modulus, must be $`0`$) against the unconditional positivity of every short-window letter, $`0<\mathrm{lcmRayArithmeticLetter}(2^a,j)`$ for $`a\ge8`$, $`0<j<2\cdot2^a`$ (, <span class="sans-serif">\[Lean\]</span>, unconditional, no rationality hypothesis).

*Do not attempt a full terminal-staircase producer*: it is provably empty. The corpus’s own route past this dead end is the *punctured* staircase (all but the last letter vanish; the last is retained and pinned exactly to the half-turn $`2^{m-1}`$, , <span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:bounded</span>) and the one-sided residue-gap family below.

<a id="the-surviving-one-sided-target."></a>

#### The surviving one-sided target.

``` math
\mathrm{ActualLcmTopEdgeResidueGap}(a,J,K,m) :\equiv
  m\le K\ \wedge\
  2H+J+K+2 < 2^m\ \wedge\
  D(H,\,H+J,\,K) \bmod 2^m \le 2^m - (2H+J+K+2).
```
(a definition, unproved at any $`a`$) `coord:mobius-mersenne`.

Note this is a *one-sided* inequality — only the upper (positive) carry arc is excluded, not a symmetric two-sided band — because the corridor’s lower half is already discharged unconditionally: for $`a\ge8`$ and $`J+(a{+}6)<2\cdot2^a`$,
``` math
0 < R_{2H+J}-R_{H+J}
```
`coord:mobius-mersenne` — a rare genuinely unconditional, non-hypothetical real-analytic theorem in this corpus, needing no rationality assumption at all.

Its companion shows that *if* the orbit is integral, the residue is forced to the exact top edge $`2^K-e`$ ($`e>0`$ small), *outside* the arc a symmetric certificate would need: (<span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:bounded</span>) — this is the exact statement of “here is what remains,” pinning the missing exclusion to one named residue class rather than leaving it implicit.

``` math
\mathrm{ActualLcmTopEdgeResidueGap}(a,J,K,m)\ \Longrightarrow\
  R_{2H+J}-R_{H+J}\notin\mathbb{Z}.
```
`coord:mobius-mersenne`.

The cofinal target built from it:
``` math
\mathrm{PowerTwoActualLcmTopEdgeResidueGapSupply} :\equiv\
  \forall a_0,\ \exists a,K,m,\quad
  a_0\le a\ \wedge\ 8\le a\ \wedge\ K+(a{+}6)<2\cdot 2^a\ \wedge\
  \mathrm{ActualLcmTopEdgeResidueGap}(a,0,K,m).
```
`coord:mobius-mersenne`.
``` math
\mathrm{PowerTwoActualLcmTopEdgeResidueGapSupply} \Longrightarrow \mathrm{Irrational}(S).
```
`coord:mobius-mersenne`.

<a id="five-strictly-weaker-links-each-independently-proved-sufficient."></a>

#### Five strictly weaker links, each independently proved sufficient.

The same file proves five further cofinal predicates, each strictly weaker than `PowerTwoActualLcmTopEdgeResidueGapSupply` (each implies it, so each is an easier target), with a direct \#249 endpoint of its own — proving the *weakest* of the six closes the entire cluster.

1.  $`\mathrm{PowerTwoAdjacentSuffixMidbandSupply}`$: replaces the $`m`$-bit residue test with a symmetric two-sided band on the *adjacent-suffix* residue at depth $`m`$, buffered by the larger depth $`m{+}1`$ so either branch stays inside the sign corridor. <span class="sans-serif">\[Open\]</span> <span class="sans-serif">scale:cofinal</span> `coord:mobius-mersenne`. Sufficiency: , direct endpoint .

2.  $`\mathrm{PowerTwoOddGuardTopEdgeHalfWordBandSupply}`$: at odd depth $`m=2q+1`$ the adjacent-suffix residue is exactly twice a half-word residue, and both directed edge widths halve to the same threshold $`H+q+2`$:
    ``` math
    H+q+2 \le \bigl(\text{half-word correction word}\bigr) \bmod 4^q
      \le 4^q - (H+q+2).
    ```
    <span class="sans-serif">\[Open\]</span> <span class="sans-serif">scale:cofinal</span> `coord:mobius-mersenne`. This is a substantially weaker demand than the earlier fixed $`1/32`$ central band elsewhere in the corpus. Sufficiency: .

3.  $`\mathrm{PowerTwoActualFinalTopEdgeMagnitudeSupply}`$: the exact centered-lift restatement of (ii),
    ``` math
    H+q+2 \le |\mathrm{actualOddHalfCenteredLift}(a,q)|,
    ```
    <span class="sans-serif">\[Open\]</span> <span class="sans-serif">scale:cofinal</span> `coord:mobius-mersenne`. Proved **equivalent** (an iff, not merely sufficient) to (ii):
    ``` math
    \mathrm{PowerTwoOddGuardTopEdgeHalfWordBandSupply}
      \iff
      \mathrm{PowerTwoActualFinalTopEdgeMagnitudeSupply}.
    ```
    .

4.  $`\mathrm{PowerTwoFlexibleActualTopEdgeMagnitudeSupply}`$: the same magnitude test at an *arbitrary* odd rank whose adjacent depth still fits the corridor (not forced to the canonical guarded depth): <span class="sans-serif">\[Open\]</span> <span class="sans-serif">scale:cofinal</span> `coord:mobius-mersenne`. Sufficiency routes back through (i), not through the corridor-escape chain below: , direct endpoint .

5.  $`\mathrm{PowerTwoFlexibleActualTerminalDominanceSupply}`$: a strictly *one-sided* version of (iv) — only the upper comparison, no absolute value:
    ``` math
    \mathrm{diagonalWindowIncrement}(2^a,\,2q{+}2) \le 2\cdot\mathrm{actualOddHalfCenteredLift}(a,q).
    ```
    <span class="sans-serif">\[Open\]</span> <span class="sans-serif">scale:cofinal</span> `coord:mobius-mersenne`. Direct endpoint .

<a id="the-weakest-known-link-and-the-exact-identity-pinning-it."></a>

#### The weakest known link, and the exact identity pinning it.

A sixth predicate, strictly weaker again than (v) — it is the disjunction of (v)’s inequality with the opposite-direction escape — is the true minimum of the whole cluster:
``` math
\mathrm{PowerTwoFlexibleActualTerminalCarryCorridorEscapeSupply} :\equiv
  \forall a_0,\ \exists a,q,\quad \cdots\ \wedge\
  \Bigl(2u \le d - B\ \vee\ d \le 2u\Bigr),
```
where $`d=\mathrm{diagonalWindowIncrement}(2^a,2q{+}2)`$, $`u=\mathrm{actualOddHalfCenteredLift}(a,q)`$, $`B=2H+(2q{+}1)+2`$. <span class="sans-serif">\[Open\]</span> <span class="sans-serif">scale:cofinal</span> `coord:mobius-mersenne`. Direct endpoint .

This form is not arbitrary: under integrality it is exactly one side of a proved identity,
``` math
2\cdot\mathrm{actualOddHalfCenteredLift}(a,q)
  = \mathrm{diagonalWindowIncrement}(2^a,2q{+}2) - \mathrm{carryOrbit}(H,H,z,2q{+}1),
```
`coord:mobius-mersenne` — an *equality*, not an inequality: the doubled centered-lift state is exactly (terminal arithmetic letter) minus (true carry). Escaping either side of this named open interval is exactly the corridor-escape supply.

Crucially, the sign machinery has already eliminated the branch this identity most naturally supplies: (<span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:bounded</span>) proves that *under integrality* the true carry orbit is strictly *positive* throughout the corridor, which means the dominance branch (v) is the one the identity naturally produces positive evidence *against*, and the surviving open target is really the *lower*-escape branch, $`2u \le d - B`$ — the dominance branch itself is stated separately as . This is the weakest exact finite arithmetic normal form currently formalised in this corridor cluster, not the programme’s leading theorem interface: the direct fixed-full-block first-harmonic gap above remains the constitutional outward socket. The corpus: a fully closed-form real-integer quantity whose escape from a named interval is necessary and sufficient (mod a fit hypothesis $`2(H{+}q{+}2)\le 4^q`$) for non-integrality at that rank.

<a id="a-second-independent-finite-window-target-the-short-arithmetic-kill-supply."></a>

#### A second, independent finite-window target: the short-arithmetic-kill supply.

A separate reduction ties the diagonal form (the collapsing-free-parameters chain above) to this actual-orbit lane via an exact digit formula with no cleanliness hypothesis at all, $`\mathrm{lcmRayArithmeticLetter}(t,j) = \varphi(H_t+j)-\varphi(H_t)`$ for *every* offset $`j`$ (, <span class="sans-serif">\[Lean\]</span>), and $`\mathrm{LcmDiagonalArithmeticKill}(t,L)\iff\mathrm{certifiedKill}(H_t,H_t,L)`$ (, <span class="sans-serif">\[Lean\]</span>).

Consequently
``` math
\mathrm{PowerTwoActualLcmShortArithmeticKillSupply} :\equiv
  \forall a_0,\ \exists a,L,\quad a_0\le a\ \wedge\ L<2\cdot2^a\ \wedge\
  \mathrm{certifiedKill}(H_{2^a}, H_{2^a}, L)
```
<span class="sans-serif">\[Open\]</span> <span class="sans-serif">scale:cofinal</span> `coord:mobius-mersenne` is *literally the diagonal obligation $`P(t)`$ of the collapsing-free-parameters chain above, restricted to powers of two and to a short window $`L<2\cdot2^a`$*. It is proved sufficient for the actual-orbit iff above via , and it is verified at exactly two exponents, $`a=4`$ (depth $`L=23`$) and $`a=6`$ (depth $`L=93`$), each traced to a pre-existing compressed diagonal certificate: <span class="sans-serif">\[Cert\]</span> <span class="sans-serif">scale:fixed</span>.

The bounded stub (<span class="sans-serif">\[Lean\]</span>, <span class="sans-serif">scale:bounded</span>, proof is a single hard-coded witness $`(a,L)=(6,93)`$, with no argument in $`a`$ at all) proves the supply only for $`a_0\le 6`$; extending it to a single further exponent (say $`a=7`$) is a self-contained, independently interesting target, not a re-run.

<a id="a-diophantine-flavoured-alternative-the-raw-approximant-separation-supply."></a>

#### A Diophantine-flavoured alternative: the raw-approximant separation supply.

Unconditionally, for every $`a,q`$:
``` math
\bigl|\mathrm{actualLcmTailOrbit}(a) - \mathrm{actualLcmRawApprox}(a,q)\bigr|
  < \frac{4H+2(2q{+}1)+4}{2^{2q+2}},
```
`coord:mobius-mersenne`, where $`\mathrm{actualLcmRawApprox}(a,q)`$ is an explicit finite computable rational. This reduces the whole analytic problem to a finite question: a cofinal $`1/32`$-separation of the raw approximant from every integer,
``` math
\mathrm{PowerTwoActualLcmOrbitSeparationSupply} :\equiv
  \forall a_0,\ \exists a\ge\max(2,a_0),\ \exists q,\quad
  \mathrm{oddGuardedCanonicalAdjacentSuffixDepth}(2^a)=2q{+}1\ \wedge\
  \forall z\in\mathbb{Z},\ \tfrac{1}{32}+\mathrm{errorRadius}(a,q)\le|\mathrm{actualLcmTailOrbit}(a)-z|,
```
<span class="sans-serif">\[Open\]</span> <span class="sans-serif">scale:cofinal</span> `coord:mobius-mersenne`, sufficient via (<span class="sans-serif">\[Lean\]</span>). Note the depth $`q`$ is not a free search parameter: the supply pins exactly one admissible depth per scale $`a`$ via $`\mathrm{oddGuardedCanonicalAdjacentSuffixDepth}`$.

<a id="a-problem-agnostic-normal-form-the-guard-cylinder-compression"></a>

## A problem-agnostic normal form: the guard-cylinder compression

Independently of which coordinate is used, *any* tail-difference certificate — for arbitrary $`h,N,L`$, not specific to \#249 — compresses to a two-bit test at logarithmic depth:
``` math
\bigl(\exists L,\ \mathrm{certifiedKill}(h,N,L)\bigr)
  \iff
  \mathrm{GuardCylinderWitness}(h,N).
```
`coord:seam-integer`, where the witness is $`\exists s,b,\ \mathrm{certifiedKill}(h,N{+}s,b{+}1) \vee
(\text{room} \wedge \mathrm{DyadicMixedGuard}(D(h,N{+}s,b{+}2),b))`$ at $`b=\lfloor\log_2(N{+}h{+}L{+}2)\rfloor+1`$. This statement mentions no Mersenne or totient structure whatsoever and is stated for arbitrary $`h,N,L`$; it compresses the search space for *any* tail-difference non-integrality certificate — of any depth $`L`$, however large — down to a socket at a logarithmic scale plus a two-bit mixed-guard cylinder ($`01`$ or $`10`$). This is directly reusable, unchanged, for any binary-series tail-difference problem, including \#257’s own denominators.

<a id="one-open-farey-problem-and-one-failed-rank-shortcut"></a>

## One open Farey problem and one failed rank shortcut

The Farey growth law below is a genuinely independent live obligation. The rank statement is retained only to record a counterfactual sufficient input and the reason that the generic compression route to it is closed; it is not a second open problem supported by the present argument.

<a id="a-counterfactual-rank-criterion."></a>

#### A counterfactual rank criterion.

Unconditionally, for every level $`e`$, the dyadic totient-kernel family of $`2^e+1`$ channels is linearly independent over $`\mathbb{Q}`$ (via CRT and Dirichlet’s theorem on primes in arithmetic progression): `coord:other:carry-kernel-rank`. Consequently, if $`S`$ is rational there is a tempered integral binary carry orbit $`u`$ with
``` math
\forall e,\quad 2^e-1 \le \operatorname{rank}_{\mathbb{Q}}\operatorname{span}\bigl(\mathrm{canonicalCarryKernelFamily}(u,e)\bigr).
```
`coord:other:carry-kernel-rank`.

An opposite inequality — a rationality-side rank *upper* bound — would of course contradict the displayed lower bound:
``` math
\exists C,\quad \forall\text{ tempered integral binary carry orbit } u
  \text{ for a rational } S,\quad
  \forall e,\quad \operatorname{rank}_{\mathbb{Q}}\operatorname{span}\bigl(\mathrm{canonicalCarryKernelFamily}(u,e)\bigr) \le C
```
(or any bound growing slower than $`2^e-1`$). This is a logically sufficient new theorem schema, not an open proposition isolated by the preceding mathematics: the corpus gives no reason rationality should force it, and explicit finite-rank shift-polynomial countermodels show that periodic denominator data alone do not.

The most direct generic construction is also impossible: no `CompressedAdjointCertificate` ($`Q\cdot v\cdot A =
\mathrm{boundary}`$ with $`|\mathrm{boundary}|<Q\cdot v`$ and $`A\ne0`$) can exist — — and the full family is proved infinite-dimensional in span: .

What rationality *does* buy — uniform eventual periodicity of $`u`$’s dyadic sections modulo some $`v>0`$ — is proved to *not* promote to any finite rank bound without further arithmetic input: . This pins the obstacle precisely, but supplies no rank upper bound.

<a id="obligation-3-farey-growth-law."></a>

#### Obligation 3 (Farey growth law).

The corpus’s strongest *unconditional* statement about $`S`$ comes from a Farey-gap denominator exclusion at a single fixed window $`K=240`$:
``` math
\forall p\in\mathbb{Q},\quad p.\mathrm{den} \le 79639646646701375323355774875831053
  \ \Longrightarrow\ S\ne p.
```
`coord:farey`. This bound is *sharp* at $`K=240`$ — the mediant $`q=79639646646701375323355774875831054`$ is proved to be the exact first failing denominator (, <span class="sans-serif">\[Lean\]</span>) — so re-running the same window buys nothing further; a new $`K`$ needs a freshly committed totient residue and freshly computed continued-fraction convergents, both hard-coded numerals.

The cofinal upgrade would be: a proved growth law $`g(K)\to\infty`$ such that for every $`K`$ the $`(N{=}1,K)`$ gap check passes for all $`q\le g(K)`$ — equivalently, a lower bound on the convergent denominators of the underlying totient-window constant, uniform in $`K`$. <span class="sans-serif">\[Open\]</span> <span class="sans-serif">scale:cofinal</span> `coord:farey`.

One natural strengthening is proved to be a hard ceiling, not a route to unboundedness: at a prime-power reduced denominator, the “unit-gap” refinement can rescue *at most one* additional lattice point beyond the ordinary gap certificate — . This route is closed; growing $`K`$ genuinely requires new per-window computation, not a refinement of the existing one.

<a id="equivalence-map"></a>

## Equivalence map

<div class="center">

| **Form** | **Relation to Obligation 1** | **Site** |
|:---|:---|:---|
| Sep$`(h,N,L)`$ supply (Obl. 1, base form) | **equivalent** to Irrational$`(S)`$ | LcmConeFlatness.lean:412 |
| multiple-period supply | propositionally equivalent via Obl. 1; explicit directions are Obl. 1 $`\Rightarrow`$ multiple and multiple $`\Rightarrow`$ irrationality | CarrySurvivorExtinction.lean:502 |
| lcm-diagonal supply $`P(t)`$ | **equivalent** to Irrational$`(S)`$; single free parameter | LcmConeFlatness.lean:426 |
| lcm-cone supply | propositionally equivalent via Obl. 1; $`P(t)`$ is the cell $`q{=}m{=}1`$ | CertificateKernel.lean:18686 |
| cone-menu (`coneNonflatCert`) supply | weaker; half the pairwise radius | CertificateKernel.lean:18812 |
| pure non-integrality (diagonal/cone) | **equivalent** to the corresp. certificate form, via the completeness iff | CertificateKernel.lean:18706, :18718 |
| DTWFirstHarmonicNormGap | sufficient for Obl. 1 (not shown weaker/stronger) | FirstHarmonicPivot.lean:83 |
| actual-orbit nonintegrality supply | **equivalent** to Irrational$`(S)`$ itself | TotientActualLcmOrbitNonintegrality.lean:37 |
| short-arithmetic-kill supply | special case of $`P(t)`$: powers of two, short window | TotientActualLcmOrbitArithmetic.lean:2107 |
| top-edge residue-gap supply | sufficient for actual-orbit supply; one-sided | TotientActualLcmTopEdgeStaircase.lean:1325 |
| adjacent-suffix midband supply | weaker than top-edge residue-gap | TotientActualLcmTopEdgeStaircase.lean:1334 |
| odd-guard half-word band supply | weaker again; **equivalent** to final-magnitude form | TotientActualLcmTopEdgeStaircase.lean:1349 |
| actual final top-edge magnitude supply | **equivalent** to odd-guard half-word band | TotientActualLcmTopEdgeStaircase.lean:1471 |
| flexible top-edge magnitude supply | weaker than midband; feeds midband, not corridor-escape | TotientActualLcmTopEdgeStaircase.lean:1927 |
| flexible terminal-dominance supply | weaker again; one-sided | TotientActualLcmTopEdgeStaircase.lean:1908 |
| flexible terminal carry-corridor-escape supply | **weakest known** in this cluster | TotientActualLcmTopEdgeStaircase.lean:1895 |
| raw-approximant separation supply | alternative (Diophantine) sufficient form, same target | TotientActualLcmOrbitSeparation.lean:305 |
| rank-compression upper bound (Obl. 2) | independent obligation, different coordinate | TotientCarryKernelRigidity.lean:284 |
| Farey growth law (Obl. 3) | independent obligation, different coordinate | GapFareyBound.lean, CertificateKernel.lean:18056 |
| guard-cylinder witness | problem-agnostic normal form of *any* certificate, not scale-comparable | TotientActualLcmTopEdgeStaircase.lean:844 |

</div>

*Reading the table.* *Weaker* in rows not marked equivalent describes an explicit implication between producer predicates: the stronger hypothesis constructs the easier-looking one. *Equivalent* marks a registered `iff`; *propositionally equivalent* marks two proved directions obtained by composing the displayed implications with the base iff. In particular, Obligation 1 and the actual-orbit supply are logically equivalent through $`\mathrm{Irrational}(S)`$, although the corpus does not claim a direct witness-to-witness converter between their predicates. The short-arithmetic-kill supply is one concrete special case of Obligation 1’s diagonal form.

<a id="what-new-mathematics-each-surviving-form-would-need"></a>

## What new mathematics each surviving form would need

None of the forms above is close to complete; every one reduces the open content to a named finite-flavoured arithmetic statement, never removes it. Two forms above have their missing ingredient identified precisely enough to name what field of technique would supply it, without any claim that the technique exists or is easy to apply.

<a id="the-exponential-sum-form."></a>

#### The exponential-sum form.

`DTWFirstHarmonicNormGap` asks for cancellation in the first additive character of a totient-driven discrepancy: a constant-saving bound, uniform in the period $`h`$ and growing with the block size $`X`$ and depth $`L`$, on $`\sum_{N\in[X,2X)} e\bigl(D(h,N,L)/2^L\bigr)`$, where $`D`$ is built from consecutive differences of $`\varphi`$. This is a Weyl-sum-shaped statement about additive character sums of an arithmetic function on a window; no argument of this shape is attempted or proved anywhere in the corpus.

<a id="the-staircase-form."></a>

#### The staircase form.

The actual-orbit top-edge cluster’s surviving target, in every one of its six equivalent-or-sufficient guises, reduces under the exact identity of the actual-orbit lane above to control of a single *terminal arithmetic letter*: the value $`\mathrm{diagonalWindowIncrement}(2^a,2q{+}2)
= \varphi(2H{+}2q{+}2)-\varphi(2H)`$ measured against twice a centred carry-lift state. What is needed is not a new certificate mechanism — the whole apparatus of arithmetic letters, centred lifts, and carry orbits is already exact and unconditional — but a genuine size or residue statement about this one totient value at cofinally many scales $`a`$, sufficient to force it off the interval the identity names. The corpus’s own finite census (through every $`t\le82`$ on the diagonal form, and $`a=4,6`$ on the short arithmetic-kill form) gives no asymptotic evidence either way; it is a floor, not a trend.

No claim is made that either obstruction is close to resolution, and none of the material above decides Erdős \#249, \#257, or any weakening of them.

<a id="statements-and-declarations"></a>

# Statements and declarations

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The linked Lean declarations, fixed toolchain, and library manifest are published in the companion repository. This manuscript provides navigation and exposition rather than proof authority.

<a id="authority-boundary."></a>

#### Authority boundary.

Kernel checking establishes that a proposition was proved; it does not authorise the exposition, literature judgements, or any claim that Problem 249 is solved.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.
