# Finite Erdos denominator-order certificate strike — exported bundle

This bundle accompanies the `finite_erdos_denominator_certificate_strike` organ.
The organ surfaces the public `finite_denominator_order_certificate` engine-room
capsule as a first-class formal-math runtime.

## What the mechanism does

For a finite nonempty set `F` of positive integers and an integer base `b >= 2`,
it computes the exact rational

```
S_F(b) = sum_{n in F} 1 / (b^n - 1) = P / Q   (lowest terms)
```

and verifies the *denominator-order certificate*

```
ord_Q(b) = lcm(F)
```

— the multiplicative order of `b` modulo the reduced denominator `Q` equals the
least common multiple of the support. This is the finite identity at the heart
of the Erdos #257 period-noncollapse strike.

The sum is computed exactly with `fractions.Fraction` (no floats); `Q` is the
reduced denominator; the order is found by repeated multiplication; and `Q` is
independently cross-checked against the closed form `Q = B / gcd(A_L, B)` with
`B = b^L - 1` and `A_L = sum_{n in F} B/(b^n - 1)`.

## What it does not claim

It computes a *finite* certificate in exact arithmetic. It does **not** prove
the open infinite Erdos #257 problem, is **not** an oracle, prover, or provider
result, and a holding certificate is a bounded computational witness, **not** a
machine-checked proof of even the finite statement.

## Fixture cases

- `certificate_holds.json` — `F={2}`, `b=2`: `S=1/3`, `ord_3(2)=2=lcm({2})`. Holds, no reduction.
- `certificate_holds_after_reduction.json` — `F={2,3}`, `b=2`: `S=1/3+1/7=10/21`; the prime 3 cancels (`gcd(A_L,B)=3`) yet `ord_21(2)=6=lcm({2,3})` survives (positive, reducing case).
- `forged_order_rejected.json` — `F={1,2}`, `b=2`: a forged order (claims 5, truth 2) is rejected by recomputation (negative case).
- `forged_denominator_rejected.json` — `F={3}`, `b=2`: a forged denominator (claims 5, truth 7) is rejected by recomputation (negative case).

## Run it

```bash
python -m microcosm_core.organs.finite_erdos_denominator_certificate_strike run \
  --input fixtures/first_wave/finite_erdos_denominator_certificate_strike/input \
  --out receipts/first_wave/finite_erdos_denominator_certificate_strike
```
