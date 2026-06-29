"""
Finite denominator-order certificate capsule.

This capsule is the public, provider-free arithmetic core behind the
``finite_erdos_denominator_certificate_strike`` organ. It computes, in exact
rational arithmetic, the finite denominator-order certificate that sits at the
heart of the Erdos #257 *period-noncollapse* strike, and it self-falsifies:
a forged certificate is rejected by recomputation.

The certified identity (finite case only):

    Let b >= 2 and let F be a finite nonempty set of positive integers.
    Let S_F(b) = sum_{n in F} 1 / (b^n - 1) = P / Q in lowest terms, and let
    L = lcm(F). Then the multiplicative order of b modulo Q equals L:

        ord_Q(b) = lcm(F),  with ord_1(b) = 1.

The capsule computes ``S_F(b)`` exactly as a ``fractions.Fraction`` (no floats),
reads ``Q`` as the reduced ``.denominator``, computes ``ord_Q(b)`` by repeated
multiplication, and cross-checks ``Q`` against the closed form ``Q = B/gcd(A_L,
B)`` where ``B = b^L - 1`` and ``A_L = sum_{n in F} B/(b^n - 1)`` (an exact
integer because every ``n`` in ``F`` divides ``L`` so ``(b^n - 1) | (b^L - 1)``).

This is a *finite* certificate strike. It is NOT a proof of the open infinite
Erdos #257 problem, it does NOT call any provider, prover, or oracle, and a
holding certificate over the bounded fixture grid is empirical/computational
pressure, not a closed proof even of the finite statement.

[PURPOSE]
- Teleology: Exposes `microcosm_core.engine_room.finite_denominator_order_certificate` as a documented Microcosm public source module that does real exact-arithmetic certificate computation.
- Mechanism: Sums 1/(b^n-1) over a finite support as an exact Fraction, extracts the reduced denominator Q, computes ord_Q(b), and verifies ord_Q(b)=lcm(F) with an independent closed-form denominator cross-check.
- Guarantee: Importing this module defines its declared constants and functions without granting authority outside the public package boundary; computations are exact and deterministic.

[INTERFACE]
- Exports: CLAIM_CEILING, ANTI_CLAIMS, SCHEMA_VERSION, ERROR_CODES, multiplicative_order, compute_finite_denominator_order_certificate, verify_finite_denominator_order_certificate
- Reads: call arguments and module constants only.
- Writes: return values only; the capsule performs no IO, no subprocess, no network, and no filesystem mutation.
- Non-goal: Does not prove the infinite Erdos #257, does not call providers/provers, does not authorize release or publication, and does not mutate state.

[FLOW]
- Validates the (support, base) inputs, sums the exact rational, derives Q, computes the multiplicative order, and compares it to lcm(F).
- Computes the closed-form denominator B/gcd(A_L, B) as an independent witness that Q is correct.
- verify_* recomputes the truth from (support, base) and rejects any claimed certificate whose P, Q, or order disagrees.

[DEPENDENCIES]
- Required: fractions.Fraction, math.gcd, math.lcm (Python standard library only)
- Optional Runtime: none.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; all computation is scoped to the explicit function invocation that performs it.
- Determinism: Pure exact-arithmetic computations are fully deterministic for equal inputs; there is no clock, randomness, filesystem, or environment read.
"""

from __future__ import annotations

from fractions import Fraction
from math import gcd, lcm
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "finite_denominator_order_certificate_v1"

CLAIM_CEILING = (
    "Computes, in exact rational arithmetic, the finite denominator-order "
    "certificate ord_Q(b) = lcm(F) for S_F(b) = sum_{n in F} 1/(b^n - 1) = P/Q "
    "over bounded inputs, and rejects forged certificates by recomputation. It "
    "does not prove the open infinite Erdos #257 problem, does not call any "
    "provider, prover, or oracle, and a holding certificate is a bounded "
    "computational witness, not a closed proof of even the finite statement."
)

ANTI_CLAIMS = (
    "The finite denominator-order certificate capsule computes exact rationals "
    "and multiplicative orders over public inputs only. It does not solve or "
    "claim to solve Erdos #257, does not assert a machine-checked proof, does "
    "not call providers or external solvers, does not export private state or "
    "credentials, and does not authorize release or publication.",
)

# Error codes the verifier emits when a claimed certificate is forged or the
# inputs are degenerate. These are the guard signals the organ asserts on.
ERROR_CODES = {
    "empty_support": "ERDOS_CERT_EMPTY_SUPPORT_REJECTED",
    "bad_base": "ERDOS_CERT_BASE_BELOW_TWO_REJECTED",
    "bad_support": "ERDOS_CERT_NONPOSITIVE_SUPPORT_REJECTED",
    "denominator": "ERDOS_CERT_DENOMINATOR_MISMATCH",
    "order": "ERDOS_CERT_ORDER_MISMATCH",
    "numerator": "ERDOS_CERT_NUMERATOR_MISMATCH",
    "not_coprime": "ERDOS_CERT_BASE_NOT_COPRIME_TO_Q",
}


def multiplicative_order(base: int, modulus: int) -> int | None:
    """
    [ACTION]
    Return the multiplicative order of ``base`` modulo ``modulus``.

    The order is the smallest k >= 1 with base**k congruent to 1 mod modulus,
    found by repeated multiplication (no factorization required).
    - Teleology: Provides the from-scratch multiplicative-order primitive the certificate identity is checked against.
    - Preconditions: base and modulus are integers; modulus may be any non-negative integer.
    - Guarantee: Returns 1 for modulus <= 1 (degenerate), None when base is not invertible mod modulus, else the exact order.
    - Fails: Returns None rather than raising when the order is undefined (gcd(base, modulus) != 1) or the safety bound is exceeded.
    - Reads: call arguments only.
    - Writes: return value only.
    """
    if modulus <= 1:
        return 1
    if gcd(base, modulus) != 1:
        return None
    value = base % modulus
    order = 1
    # ord_Q(b) divides Euler phi(Q) < Q, so this bound is never hit for valid
    # input; it only guards against a non-invertible slip-through.
    while value != 1:
        value = (value * base) % modulus
        order += 1
        if order > modulus * modulus:
            return None
    return order


def _normalise_support(support: Sequence[int]) -> tuple[list[int], list[str]]:
    """
    [ACTION]
    - Teleology: Validates and canonicalises the finite support F for `microcosm_core.engine_room.finite_denominator_order_certificate`.
    - Preconditions: support is a sequence of integers.
    - Guarantee: Returns the sorted, de-duplicated support and a list of error codes for any degeneracy found.
    - Fails: Reports empty support and non-positive members via error codes rather than raising.
    - Reads: call arguments and module constants.
    - Writes: return values only.
    """
    members = sorted({int(n) for n in support})
    errors: list[str] = []
    if not members:
        errors.append(ERROR_CODES["empty_support"])
    if any(n < 1 for n in members):
        errors.append(ERROR_CODES["bad_support"])
    return members, errors


def compute_finite_denominator_order_certificate(
    support: Sequence[int], base: int
) -> dict[str, Any]:
    """
    [ACTION]
    Compute the finite denominator-order certificate for ``S_F(b)``.

    Sums 1/(b^n - 1) over F as an exact Fraction, reads the reduced denominator
    Q, computes ord_Q(b), and reports whether ord_Q(b) == lcm(F). Also computes
    the closed-form denominator B/gcd(A_L, B) as an independent witness for Q.
    - Teleology: The exact-arithmetic certificate computation the organ surfaces and the verifier checks against.
    - Preconditions: support is a finite nonempty set of positive integers; base is an integer >= 2.
    - Guarantee: On valid input returns the exact P, Q, order, lcm, closed-form witness, and a `holds` boolean; on degenerate input returns a `holds=False` envelope carrying error codes.
    - Fails: Encodes input degeneracy as error codes in the returned envelope rather than raising.
    - Reads: call arguments and module constants.
    - Writes: return values only.
    """
    members, errors = _normalise_support(support)
    base = int(base)
    if base < 2:
        errors.append(ERROR_CODES["bad_base"])
    if errors:
        return {
            "schema_version": SCHEMA_VERSION,
            "support": members,
            "base": base,
            "holds": False,
            "error_codes": errors,
        }

    value = sum((Fraction(1, base**n - 1) for n in members), Fraction(0, 1))
    numerator = value.numerator
    denominator = value.denominator
    period = lcm(*members)
    order = multiplicative_order(base, denominator)

    # Independent closed-form witness for Q: every n in F divides L=lcm(F), so
    # (b^n - 1) divides B = b^L - 1, hence A_L = sum_{n} B/(b^n - 1) is an exact
    # integer and Q = B / gcd(A_L, B). Defensive exact-division asserts guard a
    # corrupted B from silently truncating A_L.
    big_b = base**period - 1
    a_l = 0
    for n in members:
        term = base**n - 1
        assert big_b % term == 0, "b^n-1 must divide b^L-1 for n | L"
        a_l += big_b // term
    closed_form_q = big_b // gcd(a_l, big_b)

    holds = (
        order is not None
        and order == period
        and denominator == closed_form_q
        and gcd(base, denominator) == 1
        and denominator > 1
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "support": members,
        "base": base,
        "numerator": numerator,
        "denominator": denominator,
        "order": order,
        "lcm": period,
        "closed_form_denominator": closed_form_q,
        "closed_form_b": big_b,
        "closed_form_a_l": a_l,
        "reduced": denominator != big_b,
        "coprime_base_denominator": gcd(base, denominator) == 1,
        "holds": holds,
        "error_codes": [],
    }


def verify_finite_denominator_order_certificate(
    support: Sequence[int], base: int, claimed: Mapping[str, Any]
) -> dict[str, Any]:
    """
    [ACTION]
    Recompute the certificate from (support, base) and reject a forged claim.

    The verifier never trusts the claimed values: it recomputes P, Q, and
    ord_Q(b) and emits a mismatch error code for every claimed field that
    disagrees with the truth, plus the identity check ord_Q(b) == lcm(F).
    - Teleology: The self-falsifying check that makes the certificate trustworthy: a tampered certificate is caught by recomputation.
    - Preconditions: support/base as for compute_*; claimed is a mapping that may carry P/numerator, Q/denominator, and order keys.
    - Guarantee: Returns `valid=True` only when the input is well-formed, every supplied claimed field matches the recomputation, and ord_Q(b)=lcm(F); otherwise `valid=False` with the triggered error codes.
    - Fails: Encodes every degeneracy and mismatch as an error code rather than raising.
    - Reads: call arguments and module constants.
    - Writes: return values only.
    """
    truth = compute_finite_denominator_order_certificate(support, base)
    error_codes: list[str] = list(truth.get("error_codes", []))

    if not truth.get("error_codes"):
        claimed_numerator = claimed.get("numerator", claimed.get("P"))
        claimed_denominator = claimed.get("denominator", claimed.get("Q"))
        claimed_order = claimed.get("order")
        if claimed_numerator is not None and int(claimed_numerator) != truth["numerator"]:
            error_codes.append(ERROR_CODES["numerator"])
        if claimed_denominator is not None and int(claimed_denominator) != truth["denominator"]:
            error_codes.append(ERROR_CODES["denominator"])
        if claimed_order is not None and int(claimed_order) != truth["order"]:
            error_codes.append(ERROR_CODES["order"])
        if not truth["coprime_base_denominator"]:
            error_codes.append(ERROR_CODES["not_coprime"])

    valid = not error_codes and bool(truth.get("holds"))
    return {
        "schema_version": SCHEMA_VERSION,
        "support": truth.get("support"),
        "base": truth.get("base"),
        "valid": valid,
        "recomputed": truth,
        "claimed": dict(claimed),
        "error_codes": error_codes,
    }
