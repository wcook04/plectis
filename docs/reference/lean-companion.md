# Lean companion reference

[Back to Plectis](../../README.md). For current mathematical results,
start with the companion's [results guide](https://github.com/wcook04/plectis-erdos/blob/main/docs/RESULTS.md).

The text below records the companion snapshot previously linked from the
toolkit README. It preserves those source and release references for
reproduction. The counts describe the recorded revision.

The snapshot data lives in [`lean_companion_snapshot.json`](../lean_companion_snapshot.json).
The two source and release bullets are maintained by
[`check_lean_companion_snapshot.py`](../../scripts/check_lean_companion_snapshot.py).
Run its check from the repository root:

```bash
PYTHONPATH=src python3 scripts/check_lean_companion_snapshot.py
```

<!-- The two snapshot/release bullets are maintained by scripts/check_lean_companion_snapshot.py. -->

## Companion project: eight open Erdős problems in Lean 4

The toolkit’s [mathematics and proof area](../../ORGANS.md#formal-math--proof)
includes examples drawn from a separate repository containing the Lean proof source and mathematical papers:

[**plectis-erdos**](https://github.com/wcook04/plectis-erdos)
contains Lean 4 work on Erdős Problems **#68, #243, #249, #251, #257, #269,
#1041, and #1049**. For ani's explicit degree-seven polynomial, Lean proves
that every path through its strict lemniscate joining two distinct roots has
image of one-dimensional Hausdorff measure greater than two. This refutes the
[Formal Conjectures path-image formulation of #1041](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/Counterexample/HausdorffLength.lean#L393),
as well as the earlier total-variation statement. Independent human review of
its correspondence with the 1958 curve-length wording has not been recorded.
The other seven target problems are not resolved there.
Its README gives each problem's statement, results and remaining questions.
Lean verifies the proofs
against their formal statements; the claim records and papers explain how
those statements relate to the original problems. Running a software example
here does not rerun the companion repository's Lean proofs.

For the Lean example files in this software repository, `make check` rejects proof placeholders, project-defined axioms, native
evaluation, unsafe/partial declarations, and unbounded kernel limits before
the broader test suite runs.

- [**Read the proven partial results, problem by problem**](https://github.com/wcook04/plectis-erdos/blob/main/docs/RESULTS.md):
  one entry per problem, with links to the Lean declarations, an explanation
  of what each result proves, and its limits or remaining questions.
- [**Choose a problem paper**](https://github.com/wcook04/plectis-erdos#problem-papers):
  the companion README lists one short paper for each covered problem and
  states the partial results beside it.
- [**Read the systems paper**](https://wcook04.github.io/plectis/papers/claim-faithful-publication-systems-paper.pdf):
  how the authors compare the claims in the papers with the statements
  proved in Lean, and record which source version they used.
- [**Browse the Lean source**](https://github.com/wcook04/plectis-erdos/tree/a08529a329578d172a9a2e602bacba4a8cc760cd):
  the recorded public source snapshot contains 1,816 Lean modules and 159,482
  theorem-like declarations, checked by the pinned kernel; start from
  `docs/ORIENTATION.md`. These counts include library declarations; they do
  not count solutions to Erdős problems. For this source snapshot, cite
  commit `a08529a329578d172a9a2e602bacba4a8cc760cd` and the relevant paper. `v0.10.0` is the
  latest tagged release.
- [**Release v0.10.0**](https://github.com/wcook04/plectis-erdos/releases/tag/v0.10.0):
  the version to cite when referring to that release.
