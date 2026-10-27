"""Strict adapter from hexadecimal integer observations to the Dafny packer."""

import re


def evaluate(payload, kernel, dafny):
    if type(payload) is not dict or set(payload) != {"sizes_hex", "budget_hex"}:
        raise ValueError("expected encoded sizes and budget")
    sizes = payload["sizes_hex"]
    budget = payload["budget_hex"]
    if type(sizes) is not list or type(budget) is not str:
        raise ValueError("encoded sizes must be a list and budget a string")
    if not re.fullmatch(r"(?:0|-?[1-9a-f][0-9a-f]*)", budget):
        raise ValueError("invalid encoded budget")
    if any(type(size) is not str or not re.fullmatch(r"(?:0|[1-9a-f][0-9a-f]*)", size) for size in sizes):
        raise ValueError("invalid encoded size")
    decisions, total = kernel.default__.Pack(dafny.Seq([int(size, 16) for size in sizes]), int(budget, 16))
    # Decimal JSON encoding is limited by Python's integer digit guard. Keep
    # the unbounded result on the same hexadecimal wire format as the inputs.
    return {"decisions": list(decisions), "total_hex": format(total, "x")}
