<!--
SPDX-FileCopyrightText: 2026 Will Cook
SPDX-License-Identifier: Apache-2.0
-->

# Related Erdős problems

Where this work sits among the numbered problems it is near. Statuses are as listed on the individual problem pages ([68](https://www.erdosproblems.com/68), [249](https://www.erdosproblems.com/249), [257](https://www.erdosproblems.com/257), [1041](https://www.erdosproblems.com/1041), [1049](https://www.erdosproblems.com/1049), [69](https://www.erdosproblems.com/69), [250](https://www.erdosproblems.com/250), [258](https://www.erdosproblems.com/258)) in July 2026; none of the external results is re-proved in this repository.

## Bounded status route

The external catalogue status and the local release status are separate facts.
Use the exact local packets before interpreting an analogy:

For a machine-first return from any indexed problem, run
`python3 scripts/query_corpus.py --route erdos_<n>` for `n` in `68, 243, 249,
251, 257, 269, 1041, 1049`, then follow the [complete eight-problem return
matrix](SOURCE_MAP.md#complete-eight-problem-return-matrix). That matrix binds
each public status row to its strongest checked source, paper and TeX record,
and exact open-obligation handles without changing the status or claim
authority.

- #249 target: `python3 scripts/query_corpus.py --open remaining_open.erdos_249_irrationality`; return to its problem-owned evidence with `python3 scripts/query_corpus.py --route erdos_249`.
- #257 target: `python3 scripts/query_corpus.py --open remaining_open.universal_257_all_infinite_supports`; return to its problem-owned evidence with `python3 scripts/query_corpus.py --route erdos_257`.
- #69 neighbour: `python3 scripts/query_corpus.py --claim prime_support_irrationality`
- #250 neighbour: `python3 scripts/query_corpus.py --claim sigma_transcendence`

The first two packets are `open`; the latter two are `cited only`. A solved
neighbour, shared transform, or formalised special case does not advance an
open target unless `docs/claims.json::machine_readable_paper.argument_graph`
records an `advances_open_target` edge.

## Problem map

| Problem | Catalogue status | Local relation class |
|---|---|---|
| **#68** `∑_{n≥2} 1/(n!−1)` | open | problem-owned checked reductions and finite evidence |
| **#249** `∑ φ(n)/2ⁿ` | open | open target |
| **#257** `∑_{n∈A} 1/(2ⁿ−1)` | open | open target with formalised special cases |
| **#1041** short curves in polynomial lemniscates | open | problem-owned dynamical reductions and proof audit |
| **#1049** `∑ 1/(tⁿ−1)`, rational `t>1` | open (rational `t`) | integer-base theorem plus problem-owned rational-base obstructions |
| **#69** `∑ ω(n)/2ⁿ` | solved (Tao–Teräväinen) | cited-only solved neighbour plus formalised identity bridge |
| **#250** `∑ σ(n)/2ⁿ` | solved (Nesterenko 1996) | cited-only solved neighbour |
| **#258** `∑ τ(n)/(a₁···aₙ)` | solved | untouched analogy |

## Relation in this repository

- **#68** — the [factorial-carry note](papers/full-text/erdos-68-factorial-denominator-irrationality.md)
  routes to the exact [FactorialZeroPlateau source](../ErdosProblems/Erdos68/FactorialZeroPlateau.lean#L1090):
  factorial-successor and carry frontiers, structural consumers, and a finite
  denominator exclusion; open boundary: produce cofinally many non-unit
  carries, not merely one finite miss.
- **#249** — the [problem-owned paper note](papers/full-text/erdos-249-binary-totient-series.md)
  and [canonical source map](SOURCE_MAP.md) return the unconditional denominator
  exclusion and conditional reductions. The new [squared-Lambert/GCD-moment
  family](EXTERNAL_VERIFICATION.md#programme-249) routes to the exact first-moment
  identity in [GcdMomentCalculus](../Erdos249257/GcdMomentCalculus.lean#L235);
  it is an identity with no irrationality consequence, so #249 remains open.
- **#257** — the [problem-owned paper note](papers/full-text/erdos-257-mersenne-support-subseries.md)
  and [canonical source map](SOURCE_MAP.md) return the named infinite-support
  cases and full support (`A = ℕ`), not the universal statement.
- **#243** — the [reciprocal-tail note](papers/full-text/erdos-243-reciprocal-tail-rigidity.md)
  and [ReciprocalTailRigidity source](../ErdosProblems/Erdos243/ReciprocalTailRigidity.lean#L897)
  exclude bounded negative-error regimes; open boundary: the unbounded
  mixed-sign/negative-excursion regime.
- **#251** — the [prime-gap note](papers/full-text/erdos-251-prime-gap-dyadic-series.md)
  and [PrimeGapDyadicTail source](../ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L360)
  expose the exact dyadic-tail machinery; open boundary: cofinally many
  adjacent small tail shifts at indices where prime gaps differ.
- **#269** — the [running-lcm note](papers/full-text/erdos-269-three-prime-running-lcm.md)
  and [ThreePrimeRunningLcm source](../ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L123)
  expose exact three-prime identities and a conditional residue-escape route;
  open boundary: the rationality-to-carry bridge and cofinal window escape.
- **#1041** — the paper-facing route checks Newton-flow ray separation and
  perturbation lemmas. The source-current [frontier delta](../research_corpus/Erdos1041/FRONTIER.md)
  additionally routes the surviving hub-selection, near-Fekete, perimeter,
  inverse-sheet, and degree-five premise families through their exact public
  source notes; it also records the 2026-08-29 refutations that must not be
  rebuilt. The unrestricted topology, attachment-compatible selection, and
  metric gluing remain open. Use the [machine result map](../research_corpus/Erdos1041/STRONGEST_RESULTS.json)
  and [paper note](papers/full-text/erdos-1041-lemniscate-newton-flow.md)
  together, keeping the source-only frontier separate from reviewed claim
  authority.
- **#1049** — the [rational-base note](papers/full-text/erdos-1049-rational-base-lambert.md)
  and its checked source family — [RationalBaseLambert](../ErdosProblems/Erdos1049/RationalBaseLambert.lean#L155)
  for the `3/2` corridor and `7/2` height input, [ZudilinHeightRegion](../ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L91)
  for the `81/200` region, [RationalPadeArithmetic](../ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L30)
  and [HermitePadeNoGo](../ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L103)
  for finite Padé arithmetic and comparison, and [QAperyDiagonalNonEquivalence](../ErdosProblems/Erdos1049/QAperyDiagonalNonEquivalence.lean#L67)
  for the moving-diagonal no-go, with [ZudilinConeArithmetic](../ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L286)
  covering the endpoint-unit common-divisor obstruction — route distinct
  mechanisms without claiming irrationality. The integer-base case `b ≥ 2` is
  `irrational_erdosSum_full_support`; open boundary: irrationality at `3/2`,
  the primitive noncollapsed construction, and analytic remainder control.
- **#69** — the prime-support case of #257; only the identity bridge to
  `∑_p 1/(2ᵖ−1)` is formalised, not the irrationality.
- **#250** — the ladder neighbour `L(Id)`; cited, not re-proved.
- **#258** — not addressed here; the monotone φ/σ sequel is the sibling
  territory of #249.

The one-line summary: formalised settled special cases, exact structural reductions and scoped no-go theorems across eight indexed open problems, and finite certificates whose quantifiers are stated explicitly. None of the eight open problems is solved here.
