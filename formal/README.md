# Formal executable cores

Four executable decision cores have Dafny specifications. Their generated Python
is the code called by the public APIs, not a separate handwritten simulation.

| Core | What is established for valid supplied inputs | What is outside the proof |
|---|---|---|
| [Repair](repair/README.md) | The producer terminates; the accepted plan is the unique least propagation of invalid inputs and blocked effects through any finite topologically ordered DAG. | Dependency discovery, callback behavior, persistence and external effects. |
| [Compatibility](compatibility/README.md) | An accepted state relation preserves every finite allowed input sequence and its outputs in the supplied deterministic transition models; the replay checker detects exactly the words with a differing allowed prefix. | Whether a model faithfully describes a Python program, SQLite or the intended policy. |
| [Public views](views/README.md) | A checked mixed report compiles to a public-only program preserving its exact ordered public trace; the slice reads no private input slot. | Policy correctness, secret-dependent plan construction, row selection, host decoding and side channels. |
| [Replay admission](replay/README.md) | Acceptance is equivalent to complete, unique coverage of a nonempty supplied registry with matching component, input, claim-policy, source, public payload and required witness observations. | Whether a runner executed honestly, whether its public receipt expresses the right domain claim, filesystem/hash observations and policy adequacy. |

These are SMT-backed Dafny proofs. Dafny's verification encoding, Boogie, Z3,
the compiler and support runtime, Python, and the execution platform remain
trusted. They are not Lean/Rocq proof objects checked by an independent kernel.
The generated runtimes retain the upstream MIT licence; Plectis source uses the
repository's Apache-2.0 licence.

## Run and recheck

Python 3.11+ is enough to run the [workflow examples](../examples/operations/README.md).
The replay core is called by the [shared component host](../src/microcosm_core/component_replay.py);
full component replays also need their declared native tools.
To recheck formal obligations, install the pinned official
[Dafny 4.11.0 release](https://github.com/dafny-lang/dafny/releases/tag/v4.11.0):

```sh
make verify-operations DAFNY=/absolute/path/to/dafny
```

The checkers verify the source, regenerate deployed Python and compare its
bytes, and demand rejection of a deliberately broken specification. The
per-core guides record the exact version, source hashes and trust boundary.
`make check` runs only hash binding; it does not rerun the prover. CI has a
separate proof job using the official Linux distribution and a pinned checksum.

Workers validate a release-pinned manifest and file inventory, capture the
source bytes, then import a private copy in an isolated Python process. Package
shadows and installation bytecode cannot select an unchecked implementation.
This is tested host code, not a theorem about Python's importer or a sandbox
against control of the host, loader or private temporary directory.

Source changes require reviewing the statement and implementation together;
updating a hash alone does not renew a guarantee. A negative fixture tests a
specific failure, not the soundness of the entire verification toolchain.

The [study](../docs/guides/verification-study.md) connects these cores to the
Python operations and explains the experiments still needed. SQLite publication
is tested engineering and has no formal implementation proof in this repository.
