# Scan public projection fixtures for leaks

The gate scans rendered file paths and contents for configured private-path and secret patterns, and checks symlink escapes. Findings are reported without reproducing matching secret values. The optional Gitleaks integration needs an installed `gitleaks` binary; requiring it when unavailable fails closed.

The fixture suite checks both clean and blocked projections, including a private home path and secret-shaped text. `scan --fail-on-blocking` is needed if a blocked scan should produce a nonzero exit; without it the scan command can return zero even for a non-green result. Policy exception paths change the scan outcome and should be reviewed carefully.

A green scan means the configured checks found no blocking match. It is not a general security scan, a sandbox, or a proof that information cannot leak.

## Run the example

Python 3.11 or later is required. From the repository root, run the public fixture matrix. JSON is printed to standard output.

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.public_projection_leak_gate evaluate-fixtures --input fixtures/first_wave/engine_room_public_projection_leak_gate/input --json
```

## Verification

Tests cover the configured patterns, symlink and optional scanner behavior. This helper has no separate registered component replay or component-specific formal proof. Passing fixtures do not prove that every secret or private path will be detected.

## Source

[Implementation](../src/microcosm_core/engine_room/public_projection_leak_gate.py) · [Input](../fixtures/first_wave/engine_room_public_projection_leak_gate/input) · [Tests](../tests/test_engine_room_public_projection_leak_gate.py) · [Historical sample](../receipts/first_wave/engine_room_demo/engine_room_demo_result.json) · [JSON record](engine_room_public_projection_leak_gate.json) (the sample is the composed Engine Room result)

[Gitleaks](https://github.com/gitleaks/gitleaks) is the optional external scanner.
