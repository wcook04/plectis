# Standards coverage diagnostics

> **In plain terms.** Each accepted component of a project should have a written standard, a command that runs it and saved records backing what is said about it. This check reads the project's public list of accepted components, along with inventory and command entries, and some deliberately flawed example inputs. It compares accepted components with those entries, checks that each cited standard and saved record exists, and rejects a claim of permission to release. It writes a result listing what it found, so maintainers can see which components lack standards or references.

This validator checks whether accepted components have the declared standards, runtime commands and receipt references needed to describe their public contracts. The fixture run derives positive rows from the current public registry and checks negative examples from the input directory.

## Run the example

From the repository root, with Python 3.11 or newer available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.standards_meta_diagnostics run \
  --input fixtures/first_wave/standards_meta_diagnostics/input \
  --out .microcosm/component-guides/standards_meta_diagnostics \
  --acceptance-out .microcosm/component-guides/standards_meta_diagnostics/acceptance.json
```

The command writes local output under `.microcosm/component-guides/`. Check the returned status and the result receipt; a blocked result reports findings for the supplied inputs.

## What this checks

The checker compares accepted component IDs against inventory and runtime-contract rows, checks standard and receipt references, and scans inputs for forbidden material. A missing standard reference or a claimed release authorization is rejected. The exported bundle uses supplied rows and checks a source-module manifest.

## Limits

Compares accepted component IDs with inventory and runtime-contract rows and checks their standard and receipt references, rejecting a missing standard reference or a claimed release approval.

## Verification

Tests exercise specific cases; no component-specific formal proof of its algorithm is established. When its exported-bundle route runs through `make component-replays`, the [shared Dafny-verified admission check](../formal/replay/README.md) checks agreement of source, input, claim-policy and receipt observations. The direct fixture command above does not itself run that check.

## Source

[Implementation](../src/microcosm_core/organs/standards_meta_diagnostics.py) · [Example input](../fixtures/first_wave/standards_meta_diagnostics/input/) · [Tests](../tests/test_standards_meta_diagnostics.py) · [Historical sample result](../receipts/first_wave/standards_meta_diagnostics/standards_meta_diagnostics_result.json) · [JSON record](standards_meta_diagnostics.json)

Background: [JSON Schema](https://json-schema.org/).
