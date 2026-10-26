# Check a finite denominator and multiplicative order

For a finite set of positive integers F and base b ≥ 2, the component computes the exact rational sum S = Σ 1/(bⁿ − 1) = P/Q. It calculates the multiplicative order of b modulo Q, compares it with lcm(F), and independently checks Q using a common denominator. Duplicate support entries are normalized to a set.

The verifier recomputes claimed integer fields and rejects a forged denominator or order. An empty support, a base below two, or the degenerate unit denominator is rejected. A passing case is an exact computation for that input; it is neither a proof of the general finite assertion nor a solution of the infinite Erdős problem 257.

## Run the example

Python 3.11 or later is required. From the repository root, run the four fixture cases and write local result and acceptance files.

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.finite_erdos_denominator_certificate_strike run --input fixtures/first_wave/finite_erdos_denominator_certificate_strike/input --out .microcosm/component-guides/finite_erdos_denominator_certificate_strike --acceptance-out .microcosm/component-guides/finite_erdos_denominator_certificate_strike/acceptance.json --json
```

## Verification

Tests and exact recomputation check the supplied finite examples and forged fields; there is no component-specific proof of the general assertion. `make component-replays` uses the [shared Dafny admission check](../formal/replay/README.md) for source, input, claim-policy and receipt agreement within the supplied observations. The direct example does not invoke that gate.

## Source

[Implementation](../src/microcosm_core/organs/finite_erdos_denominator_certificate_strike.py) · [Input](../fixtures/first_wave/finite_erdos_denominator_certificate_strike/input) · [Tests](../tests/test_finite_erdos_denominator_certificate_strike.py) · [Historical sample](../receipts/first_wave/finite_erdos_denominator_certificate_strike/finite_erdos_denominator_certificate_strike_result.json) · [JSON record](finite_erdos_denominator_certificate_strike.json)
