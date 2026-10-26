"""Invoke the verified ordered budget-packing decision core."""
from .._bridge import invoke


# Bound worker requests while preserving the running budget across batches.
_BATCH_SIZE = 128


def pack(payload):
    """Pack observed section sizes in order under a signed byte budget."""
    if type(payload) is not dict or set(payload) != {"sizes", "budget"}:
        raise ValueError("expected sizes and budget")
    sizes, budget = payload["sizes"], payload["budget"]
    if type(sizes) is not list or type(budget) is not int:
        raise ValueError("sizes must be a list and budget an integer")
    if any(type(size) is not int or size < 0 for size in sizes):
        raise ValueError("sizes must be nonnegative integers")
    decisions = []
    total = 0
    start = 0
    while start < len(sizes) or (not sizes and start == 0):
        budget_hex = format(budget - total, "x")
        batch = []
        while start < len(sizes) and len(batch) < _BATCH_SIZE:
            encoded = format(sizes[start], "x")
            batch.append(encoded)
            start += 1
        result = invoke("budget_packing", {"sizes_hex": batch, "budget_hex": budget_hex})
        decisions.extend(result["decisions"])
        total += int(result["total_hex"], 16)
        if not sizes:
            break
    return {"decisions": decisions, "total": total}
