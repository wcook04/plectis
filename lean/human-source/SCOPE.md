<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Scope of this release

This release does not prove Erdős #68, #243, #249, #251, #257, #269, #1041, or #1049. All eight remain open. Claims use only the immutable formal-source checkpoint in [`docs/claims.json`](docs/claims.json); the last release tag is its citation identity, not a substitute for an exact proof-source identity.

Lean source checked by the pinned kernel is proof authority. Unreleased work, private repositories, generated/provider output, and hidden sketches are not public proof artefact. Committed `research_corpus/Erdos1041` is source-only and extends neither the checkpoint nor `docs/claims.json`; it makes no peer-review, priority, novelty, or significance claim. Later work is out of scope even if locally checked; a later tag is a separate citation action.

#1041: `python3 scripts/query_corpus.py --route erdos_1041` verifies four indexed digests and reports the 35-result/open envelope; resume with `python3 scripts/query_route_memory.py --problem 1041`. These navigation/evidence routes do not promote research rows into reviewed claims or Comparator or close #1041.

The [complete eight-problem return matrix](docs/SOURCE_MAP.md#complete-eight-problem-return-matrix) binds each problem to its strongest source/paper route and frontier. The [Palomar showcase](docs/PALOMAR_RESULT_SHOWCASE.json) maps source-reviewed family dispositions without adding claims. The generated [external-verification dossier](docs/EXTERNAL_VERIFICATION.md) gives the exact spine and boundaries; neither replaces `docs/claims.json` or Lean proof authority.

## Exact open propositions

Machine-resolvable open propositions:

- `remaining_open.erdos_1041_lemniscate_connection`: python3 scripts/query_corpus.py --open remaining_open.erdos_1041_lemniscate_connection
- `remaining_open.erdos_1049_irrationality`: python3 scripts/query_corpus.py --open remaining_open.erdos_1049_irrationality
- `remaining_open.erdos_243_eventual_recurrence`: python3 scripts/query_corpus.py --open remaining_open.erdos_243_eventual_recurrence
- `remaining_open.erdos_243_overlap_height_growth`: python3 scripts/query_corpus.py --open remaining_open.erdos_243_overlap_height_growth
- `remaining_open.erdos_249_first_harmonic_anti_concentration`: python3 scripts/query_corpus.py --open remaining_open.erdos_249_first_harmonic_anti_concentration
- `remaining_open.erdos_249_irrationality`: python3 scripts/query_corpus.py --open remaining_open.erdos_249_irrationality
- `remaining_open.erdos_251_irrationality`: python3 scripts/query_corpus.py --open remaining_open.erdos_251_irrationality
- `remaining_open.erdos_269_cofinal_local_window_escape`: python3 scripts/query_corpus.py --open remaining_open.erdos_269_cofinal_local_window_escape
- `remaining_open.erdos_269_reduced_tail_nonintegrality`: python3 scripts/query_corpus.py --open remaining_open.erdos_269_reduced_tail_nonintegrality
- `remaining_open.erdos_269_three_prime_irrationality`: python3 scripts/query_corpus.py --open remaining_open.erdos_269_three_prime_irrationality
- `remaining_open.erdos_269_two_dimensional_representation`: python3 scripts/query_corpus.py --open remaining_open.erdos_269_two_dimensional_representation
- `remaining_open.erdos_68_irrationality`: python3 scripts/query_corpus.py --open remaining_open.erdos_68_irrationality
- `remaining_open.half_value_membership`: python3 scripts/query_corpus.py --open remaining_open.half_value_membership
- `remaining_open.twenty_one_actual_orbit_invariant`: python3 scripts/query_corpus.py --open remaining_open.twenty_one_actual_orbit_invariant
- `remaining_open.twenty_one_final_skip_exclusion`: python3 scripts/query_corpus.py --open remaining_open.twenty_one_final_skip_exclusion
- `remaining_open.twenty_one_permanent_affine_supercapacity`: python3 scripts/query_corpus.py --open remaining_open.twenty_one_permanent_affine_supercapacity
- `remaining_open.twenty_one_scaled_remainder_cofinal_return`: python3 scripts/query_corpus.py --open remaining_open.twenty_one_scaled_remainder_cofinal_return
- `remaining_open.unbounded_certificate_supply`: python3 scripts/query_corpus.py --open remaining_open.unbounded_certificate_supply
- `remaining_open.universal_257_all_infinite_supports`: python3 scripts/query_corpus.py --open remaining_open.universal_257_all_infinite_supports

Finite instances, conditional reductions, cited neighbours, and named infinite-support families do not discharge these propositions. Only a future claim transition against an exact identifier with evidence required by `docs/methodology.json` can change this boundary.

## Machine identifiers

Machine IDs in [`docs/claims.json`](docs/claims.json), cross-checked by `scripts/check_release.py`:

- `not_erdos_249_solution` / `not_erdos_257_solution`: #249 and universal #257 remain open.
- `not_publication_authority`: not a peer-reviewed publication record.
- `not_private_root_equivalence`: no equivalence to private work is asserted.
- `not_provider_proof_authority`: provider/model output is not proof authority.
- `not_hidden_proof_body_authority`: unpublished sketches are not proof authority.
