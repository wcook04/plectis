# Tactic availability from recorded probes

> **In plain terms.** Lean, a program that checks proofs, has automatic methods called tactics, and which of them work depends on the setup. This component is given a table of tactics with their recorded outcomes, timings and environment details, such as whether the Mathlib library was present, plus the original test files behind them. It checks the table against those files, rejecting a tactic called available with no recorded outcome and a Mathlib claim with no evidence. The output is an availability report that a later step can use when choosing which tactic to try. It only checks existing records and does not run Lean, and the results hold only for the recorded setup.

This component reads recorded tactic compile statuses, durations and environment information and produces an availability report for later routing. The included records describe a particular Lean/Std probe, including whether Mathlib was available.

## Run the example

From the repository root, with Python 3.11 or newer available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.tactic_portfolio_availability_probe run \
  --input fixtures/first_wave/tactic_portfolio_availability_probe/input \
  --out .microcosm/component-guides/tactic_portfolio_availability_probe \
  --acceptance-out .microcosm/component-guides/tactic_portfolio_availability_probe/acceptance.json
```

The command writes local output under `.microcosm/component-guides/`. Check the returned status and the result receipt; a blocked result reports findings for the supplied inputs.

## What this checks

The validator compares public tactic and environment rows with source-backed probe artifacts. A row claiming an available tactic without a compile status, or claiming Mathlib availability without supporting evidence, is rejected. Source changes can invalidate a recorded availability label.

## Limits

The run checks existing evidence; it does not run Lean or Lake. Availability and timing are scoped to the recorded environment and do not prove a theorem or establish benchmark performance.

## Verification

Tests exercise specific cases; no component-specific formal proof of its algorithm is established. When its exported-bundle route runs through `make component-replays`, the [shared Dafny-verified admission check](../formal/replay/README.md) checks agreement of source, input, claim-policy and receipt observations. The direct fixture command above does not itself run that check.

## Source

[Implementation](../src/microcosm_core/organs/tactic_portfolio_availability_probe.py) · [Example input](../fixtures/first_wave/tactic_portfolio_availability_probe/input/) · [Tests](../tests/test_tactic_portfolio_availability_probe.py) · [Historical sample result](../receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_result.json) · [JSON record](tactic_portfolio_availability.json)

Background: [Lean tactics](https://lean-lang.org/theorem_proving_in_lean4/Tactics/).
