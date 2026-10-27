# Dependency reachability

`DependencyReachability.dfy` specifies paths independently of the computation:
a path is a sequence of at least two vertices whose consecutive pairs are
edges. `Compute` returns exactly the vertices reached by such paths from the
start. It terminates on every finite input graph, including graphs with cycles.
The start is returned only when a positive-length cycle reaches it.

The Batch 5 evaluator converts each dependency relation to an edge from the
dependency to its dependent. Its adapter maps normalized strings to integers,
invokes the generated core and sorts the decoded strings. The theorem concerns
that finite graph; it does not establish that the graph contains all real
relationships. Python normalization, JSON transport, the isolated worker,
compiler and host remain trusted. The worker also has request and time limits.

The proof derives soundness by extending path witnesses and completeness from
closure under edges. Its loop decreases the finite set of vertices not yet
reached. `negative/OneHopMutant.dfy` replaces transitive expansion with an
empty set while retaining the theorem; verification rejects the mutant. The
focused tests exercise cycles, absent nodes, normalization and the Batch 5 call
path as well as comparisons with an independent traversal.

The recorded [metadata](metadata.json) binds the source, mutant and generated
Python hashes to Dafny 4.11.0. Recheck with the repository's component-kernel
checker and the [focused tests](../../../tests/test_component_dependency_reachability.py).
