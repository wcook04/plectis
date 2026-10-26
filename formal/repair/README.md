# Repair's verified decision core

Repair computes which declared workflow results can be reused, which need
recomputation, and which remain blocked by a nonreplayable prerequisite. The
public operation is `plectis.repair`; it runs with Python's standard library
and the retained Dafny runtime. A prover installation is only needed to rebuild
the guarantee.

`Repair.dfy` is the original Plectis Repair research prototype of 23 October
2026. Its source and five generated Python files are retained unchanged. The
Python host and strict JSON worker adapt that core into the public API. Dafny's
generated runtime is MIT licensed; its licence is retained beside the generated
files in `src/plectis/repair/_generated/Dafny-LICENSE.txt`.

## Exact statement

The caller supplies a finite DAG in topological order: every dependency index
of node `i` is smaller than `i`. It also supplies Boolean invalid-root and
nonreplayable masks. The two checked recurrences are:

```text
dirty[i] = roots[i] or any(dirty[d] for d in deps[i])
blocked[i] = (dirty[i] and effects[i]) or any(blocked[d] for d in deps[i])
```

For every valid typed input, `MakePlan` terminates and produces an accepted
plan. `AcceptedPlanIsLeast` proves that dirty is the least forward closure of
the roots and blocked is the least forward closure of dirty effect nodes. It
also proves blocked is a subset of dirty, no declared effect is eligible for
automatic rerun, and every node has exactly one classification. Reuse means
not dirty; rerun means dirty and not blocked. `AcceptedPlansAreUnique` proves
that at most one pair of masks can pass for fixed inputs. There is no fixed
node-count bound. Leastness is graph set inclusion, not minimum execution cost.

The generated producer uses immutable sequence appends and can incur quadratic
copying cost. The checker traverses materialized nodes and edges. No formal
performance theorem is claimed.

## Recheck

From the repository root, the quick check binds the retained formal sources and
generated files to their recorded hashes:

```sh
python3 scripts/check/check_repair_kernel.py
```

This is a hash check, not a new proof run. To verify every obligation, rebuild
the generated Python, compare all five files byte for byte, and require the
negative fixture to fail, install the official Dafny 4.11.0 release and run:

```sh
python3 scripts/check/check_repair_kernel.py --dafny /path/to/dafny
```

The exact required version is
`4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2`. The clean build reports
21 verified tasks and zero errors. These are verification tasks, not 21
components. The negative fixture removes dependency propagation from the
dirty checker condition while retaining the soundness and uniqueness theorems;
it must fail with 19 verified tasks and three errors. The checker writes build
output in a temporary directory and does not refresh hashes to accept changes.

The official Linux x64 release for CI is
[Dafny 4.11.0 for Ubuntu 22.04](https://github.com/dafny-lang/dafny/releases/download/v4.11.0/dafny-4.11.0-x64-ubuntu-22.04.zip),
whose publisher SHA-256 is
`a46a9ff7cdd720f7955854c78e95df13f4cfe6b80691b05f8654fe19e8267179`.
Other platforms use the corresponding assets in the
[official release](https://github.com/dafny-lang/dafny/releases/tag/v4.11.0).

## Interpretation and runtime boundary

The proof is SMT backed through Dafny, Boogie and Z3. The verifier encoding,
compiler, emitted support runtime, CPython and execution platform remain
trusted. This is not an independently kernel-checked Lean or Rocq proof object.
There is no `assume`, admitted lemma, external implementation or
verification-disabling attribute in the formal source.

Raw generated Python does not enforce Dafny's static types or the producer's
precondition. The worker requires exact Boolean flags and integer earlier-node
indices, rejects malformed JSON and then invokes the generated validator. It
runs in a fresh `python -I -B` process so generated absolute module names cannot
collide with a caller's imports. There is no fallback planner if it fails.

The host is tested engineering, not a formally verified executor. It requires
complete declared dependencies, meaningful code/environment/freshness identities,
honest replayability declarations, cooperative callbacks and one synchronous
writer. Changing a callback or hidden file without changing its declared identity
can reuse a stale result. The graph theorem cannot discover such a dependency.

Persist the same effect journal across restarts and graph changes to retain
unknown outcomes, including removed tasks. In-memory sessions are not durable
recovery. Checkpoint and journal writes are separate; crash atomicity is not
established. A hash chain detects accidental edits, not authenticated history.
External resolvers report outcomes outside the theorem. No concurrency,
mandatory sandboxing or exactly-once external-effect guarantee is claimed.
