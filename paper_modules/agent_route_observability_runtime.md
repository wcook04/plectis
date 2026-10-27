# Validate recorded agent routes

This runtime validates recorded agent observability metadata. The exported example checks recorded route events and whether their actors claim only the authority allowed to them. It also checks source-copy digests and writes a validation result. The broader fixture runner checks trace IDs and references supporting claimed behaviour changes.

The exported-bundle tests reject a changed source digest. The fixture runner also rejects a behaviour-change claim with an unresolved evidence reference. The validator works on recorded inputs, not a live event tap. A passing result is evidence about these records and checks, not proof that a real agent followed a route or changed its behaviour.

## Run the example

From the repository root, with Python 3.11 or newer and the repository dependencies available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.agent_route_observability_runtime \
  validate-observability-bundle \
  --input examples/agent_route_observability_runtime/exported_observability_bundle \
  --out .microcosm/component-guides/agent_route_observability_runtime/output --card
```

The command prints a compact card and writes a validation result under `.microcosm/component-guides/agent_route_observability_runtime/output`, separate from checked-in receipts. A pass reports that this bundle’s checks succeeded; inspect the result for findings if it blocks. The first-wave fixture runner additionally expects a route-compliance bundle at a `microcosm-substrate` sibling path; that layout is not present in every checkout.

## Verification

Tests and fixtures exercise the recorded route and authority checks; they do not formally prove the route-observability algorithm. The command above runs directly, without the shared admission gate. `make component-replays` separately runs the exported observability bundle through the [Dafny-verified admission decision](../formal/replay/README.md), checking the host's observations of source and input identities, claim policy and receipt agreement.

## Source

[Implementation](../src/microcosm_core/organs/agent_route_observability_runtime.py) · [example bundle](../examples/agent_route_observability_runtime/exported_observability_bundle/) · [fixture input](../fixtures/first_wave/agent_route_observability_runtime/input/) · [tests](../tests/test_agent_route_observability_runtime.py) · [sample result (historical)](../receipts/first_wave/agent_route_observability_runtime/exported_observability_bundle_validation_result.json) · [JSON record](agent_route_observability_runtime.json).
