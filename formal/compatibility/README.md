# Executable compatibility certificate checker

`AcceptedRelationPreservesAllFiniteTraces` proves that an accepted relation
preserves every finite old-admissible input word, its full output sequence and
the relation between its final states. The proof quantifies over arbitrary
valid finite tables and arbitrary finite words. `RelatedTracePreserved` proves
the stronger statement from any related state pair by induction on the word.
`IdentityAccepted` and `UsefulSelfLoopAccepted` provide feasible accepted cases.

`Check` is compiled, while the trace definitions and lemmas are ghost code.
The deployed checker is the unchanged output of official Dafny 4.11.0:

```bash
python3 scripts/check/check_compatibility_kernel.py --dafny /path/to/dafny
```

The script verifies 33 tasks in `Replay.dfy` including the unchanged
`Compatibility.dfy`, and compares all six regenerated Python files byte-for-byte
with the packaged implementation. The original output mutant must fail with
13 verified tasks and one error. That negative source changes only the
output-equality obligation in `Check`. Its failed assertion shows that the
trace proof depends on matching outputs. Default invocation without `--dafny`
checks hashes and reports `hash_binding_only`; it does not rerun a proof.

`Replay.dfy` adds executable negative-word checking. Its bad-prefix soundness
statement connects an accepted mismatch to a concrete approved-admissible prefix
where the candidate lacks a transition or returns a different observation.
It also proves consistency with the positive relation checker and supplies
non-vacuous examples. The stale-input mutant must fail with 30 verified tasks
and seven errors. The generated positive checker remains byte-identical to the
earlier core; the import bridge now includes the generated replay module.

`metadata.json` binds the exact formal sources and generated Python files.
`src/plectis/compatibility/_generated/GENERATED_SHA256.json` repeats the generated
file identities for inspection, and the Dafny runtime's MIT licence is retained
in that directory. Run proofs with the pinned build named in metadata rather
than assuming another version generates identical bytes.

The Python model parser, label-to-integer encoding, certificate hashing,
breadth-first search, subprocess adapter and correspondence to concrete programs
are outside the proof. The generated code, compiler, runtime and
Dafny/Boogie/Z3 verification stack remain trusted. The theorem makes no claim
about Python or SQLite refinement, concrete termination, concurrency, fairness,
arbitrary effects or infinite executions. The two-state exhaustive regression
is a bounded independent check of the adapter/search, rather than another
unbounded theorem.

## Provenance

This is a new mechanisation and portable adapter of the standard deterministic
forward-simulation argument. Two operator-supplied research returns dated
23 October 2026 informed its interface and tests:

- **p12**, `p12-return/FORMAL_MODEL.md` and
  `p12-return/artifacts/refinement/`: finite partial Mealy models, preservation
  of the approved input domain, relation certificates, shortest distinguishing
  continuations and a proposed inductive trace theorem. The source review and
  small exhaustive experiment motivated the proof obligation completed here.
- **p15**, `p15-return/artifact/SPECIFICATION.md`: independently required input
  domains, complete outcome coverage, stale-binding and non-vacuity attacks,
  and the distinction between a finite model and a concrete implementation.
  Its set-valued, one-call finite table is a different model; its 261,632-case
  experiment is not claimed as an experiment of this Mealy checker.

The return labels are research-source identities, not public citations or
external acceptance. Exact identifying hashes are retained in `metadata.json`.
No return text or code is presented as independent proof of the deployed
checker, and no general novelty claim is made for forward simulation or semantic
differencing. The formal source mechanises that argument in Plectis. The adapter
adapts p12's model/search interface, using parent pointers and a generated
acceptance checker; p15 informs the strict input and non-vacuity checks. Copied
compiler/runtime output retains its upstream licence.

Round-two **r2-p14** contributes the executable replay checker and the pattern
of independently checking a negative search result. Its executable `Mismatch`
is retained; local independent bad-prefix and useful-case lemmas strengthen its
proof. No hint-retention service or replay-based learning platform is imported.
Exact source identities appear in the updated metadata.
