# MCP tool-call decision core

`McpAuthority.dfy` specifies the normalized metadata checks used by the MCP
tool-authority replay. The generated Python supplies all ten ordered fault
flags and the positive-call batch counts and acceptance decision to
`validate_tool_calls`. The Python host converts input values to observations
and maps flags back to the existing diagnostic records.

`RowExact` proves each fault flag has its stated predicate and that a row is
accepted exactly when the declarative policy holds. An accepted `write` or
`external_mutation` row has a non-placeholder approval reference and
nonempty ledger and rollback references. Every accepted row has all required
fields and nonempty scope, argument-hash, source-capsule, instruction/data-split
and cold-replay references. These five citations are supplied as strings and
checked directly by the generated core. `BatchExact` proves acceptance of a
finite positive-call sequence exactly when it has three allowed rows, one
qualifying `write` and one `untrusted_result` row. `Batch` proves its iterative
counts and decision equal the specification. `ConcreteBoundary` supplies an
accepted case and a rejected missing-rollback case.

The source-linked mutants remove the rollback fault, swap two diagnostic
positions and remove the empty-scope check; verification rejects all three.
The checker regenerates the deployed
Python and compares its bytes. Python host normalization, declaration
membership, top-level forbidden-key observation, result rendering, Dafny,
Boogie, Z3, compiler and execution environment remain trusted. The predicate
checks synthetic metadata, not whether an action occurred, an approval is
authentic, or an MCP deployment is secure. Python admits textual citations,
trims their whitespace and maps other JSON types to empty strings; raw input
and public trace observations are retained. A nonempty string does not prove
reference resolution, capability semantics or cryptographic hash validity.
The complete bundle checks manifest membership. The standalone row helper may
omit that separate observation by passing `declared_tool_ids=None`.
