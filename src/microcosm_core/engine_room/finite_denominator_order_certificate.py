"""
Implements engine room finite denominator order certificate for the public Plectis package.

Callers enter through `multiplicative_order`,
`compute_finite_denominator_order_certificate`, and
`verify_finite_denominator_order_certificate`; constants such as `SCHEMA_VERSION`,
`CLAIM_CEILING`, `ANTI_CLAIMS`, and `ERROR_CODES` pin local fixture names; dependencies
include `fractions`, `math`, and `typing`. The implementation is source-owned engine-room
code, so receipts and tests should name these callables directly.
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
    "no_claim": "ERDOS_CERT_NO_CLAIMED_FIELDS",
    "unit_denominator": "ERDOS_CERT_UNIT_DENOMINATOR_DEGENERATE",
}


def _claim_mismatches(claimed_value: Any, truth_value: Any) -> bool:
    """
    Return whether a claimed certificate field fails strict comparison.

    Claims must be exact integers: a float that truncates to the truth
    (12.7 vs 12) or a bool is a mismatch, not a match, and a non-numeric
    claim is a typed mismatch rather than a crash.
    """
    return not (
        isinstance(claimed_value, int)
        and not isinstance(claimed_value, bool)
        and claimed_value == truth_value
    )


def multiplicative_order(base: int, modulus: int) -> int | None:
    """
    Derive multiplicative order without touching module import state.

    Inputs are `base` and `modulus`; notable helpers are `gcd`.
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
    Return normalise support for the engine room finite denominator order certificate flow.

    Inputs are `support`; notable helpers are `append`.
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
    Serialize
    `microcosm_core.engine_room.finite_denominator_order_certificate.compute_finite_denominator_order_certificate`
    into the payload shape expected by engine room finite denominator order certificate.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
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
    Serialize
    `microcosm_core.engine_room.finite_denominator_order_certificate.verify_finite_denominator_order_certificate`
    into the payload shape expected by engine room finite denominator order certificate.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    truth = compute_finite_denominator_order_certificate(support, base)
    error_codes: list[str] = list(truth.get("error_codes", []))

    if not truth.get("error_codes"):
        claimed_numerator = claimed.get("numerator", claimed.get("P"))
        claimed_denominator = claimed.get("denominator", claimed.get("Q"))
        claimed_order = claimed.get("order")
        if claimed_numerator is None and claimed_denominator is None and claimed_order is None:
            # A certificate that claims nothing verifies nothing: valid=True
            # here would read as "claims verified" to any consumer.
            error_codes.append(ERROR_CODES["no_claim"])
        if claimed_numerator is not None and _claim_mismatches(claimed_numerator, truth["numerator"]):
            error_codes.append(ERROR_CODES["numerator"])
        if claimed_denominator is not None and _claim_mismatches(claimed_denominator, truth["denominator"]):
            error_codes.append(ERROR_CODES["denominator"])
        if claimed_order is not None and _claim_mismatches(claimed_order, truth["order"]):
            error_codes.append(ERROR_CODES["order"])
        if not truth["coprime_base_denominator"]:
            error_codes.append(ERROR_CODES["not_coprime"])
        if not truth.get("holds") and truth.get("denominator") == 1:
            # The only reachable holds=False case with otherwise-consistent
            # arithmetic is the unit denominator (support=[1] style inputs);
            # rejections stay typed instead of emitting an empty code list.
            error_codes.append(ERROR_CODES["unit_denominator"])

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
