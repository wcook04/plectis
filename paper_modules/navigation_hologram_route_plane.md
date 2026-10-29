# Navigation route-plane validation

> **In plain terms.** A list of suggested ways to dig deeper into a project can go stale or include an option with no command. This check reads the options, each meant to name a command, plus a note recording a fingerprint (a short code that changes if the list changes) and a row count. It rejects an option without a command, compares the fingerprint and count with the list, and refuses a derived summary that claims to be current when they differ. It writes a status and a list of problems, so a maintainer can see what needs fixing.

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

Compares the hash and row count in the source-coupling manifest with the fixture's route rows, and rejects a row without a command or a stale projection that claims to be current.

## Verification

The focused tests exercise this component’s checks; they do not prove its algorithm. `make component-replays` runs its registered exported route-plane bundle through the shared [Dafny admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement within the host’s observations. The direct command above does not itself invoke that admission gate.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/navigation_hologram_route_plane.py) and [focused tests](../tests/test_navigation_hologram_route_plane.py)
- [Example input](../fixtures/first_wave/navigation_hologram_route_plane/input) and [historical sample result](../receipts/first_wave/navigation_hologram_route_plane/toy_kind_card.json)
- [Component JSON record](./navigation_hologram_route_plane.json) and [canonical capsule](../core/paper_module_capsules.json)

For interface context see the [CLI Guidelines](https://clig.dev/) and [progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/).
