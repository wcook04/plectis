<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Scope of this release

This release does not prove Erdős #68, #243, #249, #251, #257, #269, #1041,
or #1049. All eight remain open; their papers give checked results and
surviving obligations. Claims apply only to the source and dependencies at the
immutable formal-source checkpoint in
[`docs/claims.json`](docs/claims.json). The last release tag remains the
citation identity and can differ from that checkpoint.

Mathematical proof authority is Lean source at that declared checkpoint after
checking by the pinned Lean kernel. Unreleased work, private repositories,
generated prose, provider output, and hidden proof sketches are not part of
the public proof artefact. Work later than the declared checkpoint is out of
scope even if it checks locally; a later tagged release is a separate citation
and release action, not a substitute for an exact proof-source identity.

## What the corpus is, by shape

Size is not evidence. The semantic graph classifies every statement; re-derive
these with `python3 scripts/query_semantic.py <shape>`.

| Shape | Count | Meaning |
|---|---:|---|
| `nonrecurring` | 283 | substantive content, weighted to #257 (168) over #249 (88) |
| `classical` | 101 | already in the literature or matched to prior art; formalisation value only |
| `bare-equivalences` | 32 | restatements, labelled by this project's own audit |

Neither count asserts novelty: `nonrecurring` means a statement does not recur
inside this corpus, not that it is new to mathematics. That judgement is a human
number theorist's, and no query here supplies it.

The `K = 240` denominator exclusion is the classical Farey/mediant bound on a
committed window. Its improvement over that argument is zero and the window
length is free: `python3 scripts/check_farey_denominator_scaling.py` reproduces
the formalised constant, then returns a 2,406-digit bound in a fraction of a
second. Cite it as a finite computation, never as progress.

## Exact open propositions

Machine-resolvable open propositions:

- `remaining_open.erdos_249_irrationality`:
  `python3 scripts/query_corpus.py --open remaining_open.erdos_249_irrationality`
- `remaining_open.unbounded_certificate_supply`:
  `python3 scripts/query_corpus.py --open remaining_open.unbounded_certificate_supply`
- `remaining_open.half_value_membership`:
  `python3 scripts/query_corpus.py --open remaining_open.half_value_membership`
- `remaining_open.twenty_one_permanent_affine_supercapacity`:
  `python3 scripts/query_corpus.py --open remaining_open.twenty_one_permanent_affine_supercapacity`
- `remaining_open.universal_257_all_infinite_supports`:
  `python3 scripts/query_corpus.py --open remaining_open.universal_257_all_infinite_supports`

Finite instances, conditional reductions, cited neighbours, and named
infinite-support families do not discharge these propositions. Only a future
claim transition recorded against the exact identifier, with the evidence
required by `docs/methodology.json`, can change this boundary.

## Machine identifiers

These identifiers are the machine-readable form of the scope statement above.
They are declared once in [`docs/claims.json`](docs/claims.json) and
cross-checked against this file by `scripts/check_release.py`, which fails
when any public surface drifts from them.

| Identifier | Public meaning |
|---|---|
| `not_erdos_249_solution` | The release does not settle Erdős #249 |
| `not_erdos_257_solution` | The release does not settle the universal Erdős #257 |
| `not_publication_authority` | The release is not itself a peer-reviewed publication record |
| `not_private_root_equivalence` | The release is not asserted to be equivalent to any private development |
| `not_provider_proof_authority` | Provider or model output is not proof authority; the Lean kernel check is |
| `not_hidden_proof_body_authority` | No unpublished proof sketch or hidden artefact carries proof authority |
