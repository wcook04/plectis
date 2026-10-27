# Premise ranking core

`PremiseRanking.dfy` supplies the executable core used by
`formal_math_premise_retrieval._score_query`. For normalized query token counts
and candidate rows, `Compute` returns exactly the eligible input occurrences.
Each score is the sum of the minimum query and premise count for every token,
plus one when the strategy matches. Results are sorted by descending score,
ascending premise-ID rank, then original position. The last key preserves
Python's stable ordering when IDs and scores are equal.

The independent ghost specification constructs the expected multiset with
`OverlapSpec` and states the lexicographic order with `RankBefore`; the executable
uses a score loop and insertion sort. The contracts prove score equality,
occurrence coverage and ordering for all finite inputs satisfying equal vector
lengths. `negative/SplitFilterMutant.dfy` removes eligibility filtering and
fails the coverage invariant.

The host is trusted to tokenize and count terms, derive split and strategy
membership, map Python's string ordering to ranks, and reconstruct field-hit
metadata. JSON conversion, worker isolation, generated runtime, Dafny, Boogie,
Z3 and Python remain trusted. The proof says nothing about the usefulness of a
retrieved premise or the correctness of the source metadata.

The metadata binds the proof source, mutant, pinned Dafny version and generated
Python. The shared component-kernel checker reproves and regenerates these files;
the component tests exercise the production call and adversarial inputs.
