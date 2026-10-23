# Formal decision cores

Two small executable cores have Dafny specifications. Their generated Python
is the code called by the public APIs, not a separate handwritten simulation.

| Core | What is established for valid supplied inputs | What is outside the proof |
|---|---|---|
| [Repair](repair/README.md) | The producer terminates; the accepted plan is the unique least propagation of invalid inputs and blocked effects through any finite topologically ordered DAG. | Dependency discovery, callback behavior, persistence and external effects. |
| [Compatibility](compatibility/README.md) | An accepted state relation preserves every finite allowed input sequence and its outputs in the supplied deterministic transition models. | Whether a model faithfully describes a Python program, SQLite or the intended policy. |

These are SMT-backed Dafny proofs. Dafny's verification encoding, Boogie, Z3,
the compiler and support runtime, Python, and the execution platform remain
trusted. They are not Lean/Rocq proof objects checked by an independent kernel.
The generated runtimes retain the upstream MIT licence; Plectis source uses the
repository's Apache-2.0 licence.

## Run and recheck

Python 3.11+ is enough to run the [examples](../examples/operations/README.md).
To recheck formal obligations, install the pinned official
[Dafny 4.11.0 release](https://github.com/dafny-lang/dafny/releases/tag/v4.11.0):

```sh
make verify-operations DAFNY=/absolute/path/to/dafny
```

Both checkers verify the source, regenerate deployed Python and compare its
bytes, and demand rejection of a deliberately broken specification. The
per-core guides record the exact version, source hashes and trust boundary.
`make check` runs only hash binding; it does not rerun the prover. CI has a
separate proof job using the official Linux distribution and a pinned checksum.

Source changes require reviewing the statement and implementation together;
updating a hash alone does not renew a guarantee. A negative fixture tests a
specific failure, not the soundness of the entire verification toolchain.

The [study](../docs/guides/verification-study.md) connects these cores to the
Python operations and explains the experiments still needed. SQLite publication
is tested engineering and has no formal implementation proof in this repository.
