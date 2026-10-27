# Classify tool-server process pressure

> **In plain terms.** When too many programs are running on a computer, someone has to work out which ones belong to whom. This check is given a saved snapshot of the running programs, a list classifying their owners and a policy on how much pressure is too much. It follows ownership links, sorts owners into active, unknown and detached, applies the policy, and rejects any claim that a program with an unknown owner is safe to close. The output is an inventory and a recommendation for easing the pressure, to help decide what needs an owner's attention. It reads only the saved snapshot and sends no signals, and a recommendation is not permission to stop anything.

This component takes a supplied process table, owner classifications and pressure policy and produces an inventory and a relief recommendation. It helps inspect a recorded process snapshot before deciding what needs an owner’s attention.

## Run the example

From the repository root, with Python 3.11 or newer available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.tool_server_pressure_inventory run \
  --input fixtures/first_wave/tool_server_pressure_inventory/input \
  --out .microcosm/component-guides/tool_server_pressure_inventory \
  --acceptance-out .microcosm/component-guides/tool_server_pressure_inventory/acceptance.json
```

The command writes local output under `.microcosm/component-guides/`. Check the returned status and the result receipt; a blocked result reports findings for the supplied inputs.

## What this checks

The classifier follows owner relationships, distinguishes active, unknown and detached owners, and applies the supplied policy. Tests cover cycles and active-owner descendants. It rejects a claim that an unknown-owner process is safe to close, and rejects recorded process signals or exposed command previews.

## Limits

The implementation does not inspect the live process table or send signals. A recommendation in a receipt is not permission to stop a process.

## Verification

Tests exercise specific cases; no component-specific formal proof of its algorithm is established. When its exported-bundle route runs through `make component-replays`, the [shared Dafny-verified admission check](../formal/replay/README.md) checks agreement of source, input, claim-policy and receipt observations. The direct fixture command above does not itself run that check.

## Source

[Implementation](../src/microcosm_core/organs/tool_server_pressure_inventory.py) · [Example input](../fixtures/first_wave/tool_server_pressure_inventory/input/) · [Tests](../tests/test_tool_server_pressure_inventory.py) · [Historical sample result](../receipts/first_wave/tool_server_pressure_inventory/tool_server_pressure_inventory_result.json) · [JSON record](tool_server_pressure_inventory.json)

Background: [psutil process iteration](https://psutil.readthedocs.io/en/latest/#psutil.process_iter).
