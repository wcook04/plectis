# Compose the first-screen command card

The first-screen composition reads its public standard and assembles a card describing reader routes, source-checkout commands, a pre-install probe and the local-state trail. Its validation checks the assembled fields against the standard. The human-facing `hello` command displays a first screen without writing project state; `tour --card` is the separate state-writing behavior demonstration.

Assembles the first-screen command card from its public standard and checks each field against it, rejecting a missing required section or a disallowed authority claim.

## Run the example

Python 3.11 or later is required. From the repository root, print the composed first-screen card.

```bash
PYTHONPATH=src python3 -m microcosm_core first-screen --card .
```

The card also shows `plectis comprehend --first-action "<your goal>" --format text` for selecting a command and stop condition from the public task routes. This selection does not execute the command. [FIRST_ACTION.md](../FIRST_ACTION.md) contains worked examples.

## Verification

The composition tests and standard-backed checks assess required fields, routes and authority flags. This helper has no separate registered component replay or component-specific formal proof. A passing card is evidence about the tested composition, not a proof that its presentation works for every reader.

## Source

[Implementation](../src/microcosm_core/first_screen_composition.py) · [Standard](../standards/std_microcosm_first_screen_composition_root.json) · [Tests](../tests/test_first_screen_composition_card.py) · [Historical sample](../receipts/public_site/first_screen_composition_root_site_ready_payload.json) · [JSON record](first_screen_composition_root.json)

[Command Line Interface Guidelines](https://clig.dev/) provide wider context for command-line presentation.
