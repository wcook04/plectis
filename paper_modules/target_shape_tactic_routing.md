# Target Shape Tactic Routing

`target_shape_tactic_routing_gate` is the public Microcosm organ for the
pre-execution tactic admissibility layer.

It turns a small public tactic portfolio plus synthetic target-shape cases into
route decisions: which tactics are admitted, which are rejected as unavailable,
which are rejected as unprobed, and which are rejected because they do not match
the declared goal shape.

## Authority Boundary

This organ does not run Lean or Lake and does not prove a target. It validates
only metadata that must exist before a proof attempt: tactic probe availability,
target-shape route cases, selected tactic ids, and negative-case receipts.

Forbidden outputs include proof bodies, provider bodies, post-execution route
selection, Lean receipt claims, provider calls, release claims, and
Mathlib-dependent proof authority.

## Runtime Surfaces

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.target_shape_tactic_routing_gate run --input fixtures/first_wave/target_shape_tactic_routing_gate/input --out receipts/first_wave/target_shape_tactic_routing_gate
PYTHONPATH=src python3 -m microcosm_core.cli target-shape-tactic-routing-gate run-routing-bundle --input examples/target_shape_tactic_routing_gate/exported_target_shape_tactic_routing_bundle --out receipts/runtime_shell/demo_project/organs/target_shape_tactic_routing_gate
```

## Negative Cases

- `unavailable_tactic_admitted` rejects an `aesop` route while Mathlib is absent.
- `unprobed_tactic_allowed` rejects a tactic absent from the public probe portfolio.
- `proof_body_leakage` rejects proof/provider/Lean body fields.
- `post_execution_route` rejects route selection after execution evidence.
- `release_overclaim` rejects proof, provider, Lean/Lake, publication, and release authority overclaims.

## Why It Matters

After corpus readiness and strategy scoring, Microcosm needs a visible gate that
prevents wasted or misleading proof attempts. This organ makes the next step
legible to a cold reader: a tactic is not tried just because it exists; it is
admitted only when the target shape and the public availability probe both allow
it.
