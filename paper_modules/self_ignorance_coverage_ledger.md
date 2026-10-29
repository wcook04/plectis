# Compare known atlas coverage

> **In plain terms.** A project keeps a map of its own parts, and some parts it knows exist may be missing from the map. This comparison reads counts and identifiers for categories such as concepts and standards, plus a saved map that represents some of them. For each category it works out the shortfall between the listed count and the number shown on the map, and checks that required identifiers are present. The shortfall, called coverage debt, points to known gaps, and a claim that a missing entry shows something does not exist is rejected.

The exported bundle contains counts and IDs for categories such as concepts and standards, plus a saved system graph representing some of those entities. This component compares the two: for each category it reports the shortfall between the listed count and the number represented in the graph, and checks required IDs. The resulting coverage debt helps locate known gaps in that graph.

## Run the example

From the repository root, with Python 3.11 or newer and the checkout dependencies available:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.self_ignorance_coverage_ledger run-self-ignorance-bundle \
  --input examples/self_ignorance_coverage_ledger/exported_self_ignorance_coverage_ledger_bundle \
  --out .microcosm/component-guides/self_ignorance_coverage_ledger
```

Inspect `.microcosm/component-guides/self_ignorance_coverage_ledger/exported_self_ignorance_coverage_ledger_bundle_validation_result.json` for the result and findings.

The graph is a snapshot: the reported debt is relative to the selected kind rows and materialized entities in that bundle. Inspect the board to see which kinds contribute to it.

## What the result means

Compares the kind-atlas counts and required IDs with the saved system graph and reports each category's shortfall, rejecting a mismatched debt count or a claim that an absent entry proves something does not exist. The small static fixture lacks the graph and is expected to block.

## Verification

When `make component-replays` runs this component, the shared [Dafny-verified replay admission](../formal/replay/README.md) checks observed source and input identities, claim-policy identity, and receipt agreement. The example above runs directly and does not invoke that gate. There is no component-specific formal proof of the coverage computation; the tests do not establish completeness.

## Source

[Implementation](../src/microcosm_core/organs/self_ignorance_coverage_ledger.py) · [input](../examples/self_ignorance_coverage_ledger/exported_self_ignorance_coverage_ledger_bundle) · [tests](../tests/test_self_ignorance_coverage_ledger.py) · [historical sample result](../receipts/runtime_shell/demo_project/organs/self_ignorance_coverage_ledger/exported_self_ignorance_coverage_ledger_bundle_validation_result.json) · [component record](../core/paper_module_capsules.json).
