# Public-view transformation

`Release.dfy` defines a finite text/Boolean report language, its full mixed
execution, a static information-flow checker, a public-slice transformation
and the interpreter that runs that slice. The deployed generated Python calls
`CheckAndSlice` and `CheckAndRun`; the transformation is executable proof-backed
code, not an informal model beside a handwritten renderer.

For a well-typed environment, a fixed checked program and an independently
supplied public/private field policy:

- `FullExecutionPublicProjection` connects the full event trace to public
  observation, including order, multiplicity and absence of output.
- `CheckedNoninterference` proves equal public observations for environments
  agreeing on public inputs.
- `SlicePreservesTrace` proves that the compiled slice emits exactly the
  original program's public trace.
- `SliceIsPublicOnly` and `PublicOnlyReadsAreLow` establish that the slice's
  syntactic read footprint contains no private input slot.
- `SliceStaysChecked` preserves typing and flow checks after transformation.

These statements range over arbitrary finite programs in the defined language;
the Python host imposes additional finite input limits. A confidential empty
report still satisfies the flow theorem. Independent expected outputs and a
meaningful field policy remain the application's responsibility.

The plan, schema, constants, row membership and row order must themselves be
public. A plan built after reading a secret can leak it through a literal. A
private SQL filter can leak it through missing rows. The proof does not cover
such upstream choices, arbitrary Python, declassification, timing/resource
side channels, operating-system confinement or deployment permissions.

## Reproduce

```sh
python3 scripts/check/check_views_kernel.py
python3 scripts/check/check_views_kernel.py --dafny /path/to/dafny --logs /path/to/logs
```

The default checks hashes and the reviewed loader inventory only. The full
mode requires Dafny `4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2`, verifies
30 tasks, regenerates five Python files and requires byte identity. The
`IgnoreControl` mutant drops private-control tracking; `RetainPrivateRead`
keeps a private guard in the public slice. Each must fail a proof obligation.
Their rejection is a specific regression check, not proof of toolchain soundness.

The source and generated hashes are in [metadata.json](metadata.json). This
core was retained unchanged from the second-round p15 research return dated
23 October 2026; Plectis adapted its wrapper, loading boundary, examples and
packaging. The generated runtime's MIT licence accompanies the code.

Dafny, Boogie, Z3, compilation, the generated support runtime, CPython and the
platform remain trusted. The Python decoder, manifest-pinned private source
loader and API protocol are tested rather than deductively verified. This is
not an independently checked Lean/Rocq certificate or a verified SQL adapter.
See the [user guide](../../docs/guides/public-views.md) for practical limits.
