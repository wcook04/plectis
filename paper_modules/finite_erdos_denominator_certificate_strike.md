# Check a finite denominator and multiplicative order

> **In plain terms.** A claimed answer to one finite case of the fraction sum in Erdős problem 257 can be checked by redoing it exactly. The input is a short list of positive whole numbers, a base of at least 2, and the claimed values. For each number n it adds 1 divided by (base to the power n, minus 1), finds the smallest power of the base leaving a remainder of 1 when divided by the sum's bottom number, and compares that power with the list's least common multiple. It recomputes the claimed values and rejects a forged bottom number or power.

For a finite set of positive integers F and base b ≥ 2, the component computes the exact rational sum S = Σ 1/(bⁿ − 1) = P/Q. It calculates the multiplicative order of b modulo Q, compares it with lcm(F), and independently checks Q using a common denominator. Duplicate support entries are normalized to a set.

Recomputes the claimed integer fields exactly for one finite set and base, and rejects a forged denominator or order, an empty support, a base below two and the degenerate unit denominator. A pass is an exact computation for that one input.

## Run the example

Python 3.11 or later is required. From the repository root, run the four fixture cases and write local result and acceptance files.

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.finite_erdos_denominator_certificate_strike run --input fixtures/first_wave/finite_erdos_denominator_certificate_strike/input --out .microcosm/component-guides/finite_erdos_denominator_certificate_strike --acceptance-out .microcosm/component-guides/finite_erdos_denominator_certificate_strike/acceptance.json --json
```

## Verification

Tests and exact recomputation check the supplied finite examples and forged fields; there is no component-specific proof of the general assertion. `make component-replays` uses the [shared Dafny admission check](../formal/replay/README.md) for source, input, claim-policy and receipt agreement within the supplied observations. The direct example does not invoke that gate.

## Source

[Implementation](../src/microcosm_core/organs/finite_erdos_denominator_certificate_strike.py) · [Input](../fixtures/first_wave/finite_erdos_denominator_certificate_strike/input) · [Tests](../tests/test_finite_erdos_denominator_certificate_strike.py) · [Historical sample](../receipts/first_wave/finite_erdos_denominator_certificate_strike/finite_erdos_denominator_certificate_strike_result.json) · [JSON record](finite_erdos_denominator_certificate_strike.json)
