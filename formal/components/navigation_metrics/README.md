# Navigation packet metric core

`NavigationMetrics.dfy` defines wildcard matches, counts matching expected
patterns and matching selected IDs in their separate units, and computes the
sufficiency and latency decisions. The proved contract states that those
counts equal the cardinalities of independent sets of matching positions and
are bounded by the corresponding sequence lengths. It also specifies the
priority of timeout, error, missing artifact, weak scent and forbidden route,
and the separate latency decision.

The trusted Python host converts expected and selected IDs to distinct sorted
lists and supplies timeout, error, scent and forbidden-route observations. It
computes floating-point ratios and four-place rounding from the verified
integer counts. String normalization, the fidelity of observations, Python,
the adapter, Dafny's compiler/runtime, Boogie, Z3 and the host remain outside
the theorem. It does not prove the truth of labels or the quality of a route.

Dafny 4.11.0 verified 31 tasks with no errors; two independent builds produced identical generated Python. The source-linked negative changes the relevant-selected count to a
matching-pattern count. Overlapping exact and wildcard patterns can then
produce two relevant selections from one selected ID, violating the contract; verification rejects the mutant with a failed postcondition. The shared bridge applies a 30-second worker timeout, which is a host compatibility limit.
