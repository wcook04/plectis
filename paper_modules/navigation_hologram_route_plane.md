# Navigation route-plane validation

Checks public route rows and records that bind them to an entry route, then writes a validation receipt.

## Run the example

From the repository root with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.navigation_hologram_route_plane run --input fixtures/first_wave/navigation_hologram_route_plane/input --out /tmp/plectis-component-guides/navigation_hologram_route_plane/out --card
```

Inspect the status and findings under `/tmp/plectis-component-guides/navigation_hologram_route_plane/out`. The command also writes a preflight receipt under `/tmp/plectis-component-guides/navigation_hologram_route_plane/receipts/preflight/`; the linked result below is a historical sample.

## What it checks

A route row describes a navigation option and its command. For example, the fixture’s `route_card_candidate` gives a safe drilldown command and conditions for opening it. The validator also checks the required entry-packet fields, the actions a route lease permits, and conditions that demote unsuitable options. A source-coupling manifest contains a hash and row count; the validator compares these with the route rows. It rejects a row without a command and a projection claiming current authority when coupling is stale. The selected fixture card is a small routing example.

## Limits

Matching hashes establish consistency with referenced bytes, not that the routes are useful or correct. This fixture does not exercise a live private navigation system.

## Verification

The focused tests exercise this component’s checks; they do not prove its algorithm. `make component-replays` runs its registered exported route-plane bundle through the shared [Dafny admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement within the host’s observations. The direct command above does not itself invoke that admission gate.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/navigation_hologram_route_plane.py) and [focused tests](../tests/test_navigation_hologram_route_plane.py)
- [Example input](../fixtures/first_wave/navigation_hologram_route_plane/input) and [historical sample result](../receipts/first_wave/navigation_hologram_route_plane/toy_kind_card.json)
- [Component JSON record](./navigation_hologram_route_plane.json) and [canonical capsule](../core/paper_module_capsules.json)

For interface context see the [CLI Guidelines](https://clig.dev/) and [progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/).
