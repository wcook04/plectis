# Validate a routing anti-pattern registry

The input is a JSON registry of named routing mistakes and explanatory text. The validator checks its kind and version, required named entries, unique IDs and nonempty descriptions, then writes findings and a board.

## Run the example

From the repository root, with Python 3.11 or newer and the checkout dependencies available:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.routing_anti_patterns_registry run \
  --input fixtures/first_wave/routing_anti_patterns_registry/input \
  --out .microcosm/component-guides/routing_anti_patterns_registry \
  --acceptance-out .microcosm/component-guides/routing_anti_patterns_registry/acceptance.json
```

Inspect `.microcosm/component-guides/routing_anti_patterns_registry/routing_anti_patterns_registry_result.json` for the result and findings.

The bundled fixture contains deliberately invalid registries. A passing run records detection of the expected failures as well as the checks on the named entries.

## What the result means

A duplicate ID or a missing required entry is rejected. This verifies the registry projection; it does not change routing policy or demonstrate that a real route is correct.

Related reading: [Hillside patterns library](https://hillside.net/patterns/), [Command Line Interface Guidelines](https://clig.dev/).

## Verification

When `make component-replays` runs this component, the shared [Dafny-verified replay admission](../formal/replay/README.md) checks observed source and input identities, claim-policy identity, and receipt agreement. The example above runs directly and does not invoke that gate. There is no component-specific formal proof of the registry checker, and its checks do not prove a routing policy correct.

## Source

[Implementation](../src/microcosm_core/organs/routing_anti_patterns_registry.py) · [input](../fixtures/first_wave/routing_anti_patterns_registry/input) · [tests](../tests/test_routing_anti_patterns_registry.py) · [historical sample result](../receipts/acceptance/first_wave/routing_anti_patterns_registry_fixture_acceptance.json) · [component record](../core/paper_module_capsules.json).
