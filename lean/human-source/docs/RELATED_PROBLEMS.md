<!--
SPDX-FileCopyrightText: 2026 Will Cook
SPDX-License-Identifier: Apache-2.0
-->

# Related Erdős problems

Where this work sits among the numbered problems it is near. Statuses are as listed on the individual problem pages ([68](https://www.erdosproblems.com/68), [249](https://www.erdosproblems.com/249), [257](https://www.erdosproblems.com/257), [1041](https://www.erdosproblems.com/1041), [1049](https://www.erdosproblems.com/1049), [69](https://www.erdosproblems.com/69), [250](https://www.erdosproblems.com/250), [258](https://www.erdosproblems.com/258)) in July 2026; none of the external results is re-proved in this repository.

## Bounded status route

The external catalogue status and the local release status are separate facts.
Use the exact local packets before interpreting an analogy:

- #249 target: `python3 scripts/query_corpus.py --open remaining_open.erdos_249_irrationality`
- #257 target: `python3 scripts/query_corpus.py --open remaining_open.universal_257_all_infinite_supports`
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

- **#68** — exact factorial-successor and carry frontiers, structural consumers,
  and a finite denominator exclusion; no irrationality proof.
- **#249** — an unconditional denominator exclusion and conditional reductions,
  no solution.
- **#257** — named infinite-support cases and full support (`A = ℕ`), not the
  universal statement.
- **#1041** — Newton-flow ray separation and perturbation lemmas are checked;
  the global topology and metric gluing are open.
- **#1049** — the integer-base case `b ≥ 2` is
  `irrational_erdosSum_full_support`; at rational noninteger bases the public
  modules check clearing, height-region, and Padé obstructions but no
  irrationality theorem.
- **#69** — the prime-support case of #257; only the identity bridge to
  `∑_p 1/(2ᵖ−1)` is formalised, not the irrationality.
- **#250** — the ladder neighbour `L(Id)`; cited, not re-proved.
- **#258** — not addressed here; the monotone φ/σ sequel is the sibling
  territory of #249.

The one-line summary: formalised settled special cases, exact structural reductions and scoped no-go theorems across eight indexed open problems, and finite certificates whose quantifiers are stated explicitly. None of the eight open problems is solved here.
