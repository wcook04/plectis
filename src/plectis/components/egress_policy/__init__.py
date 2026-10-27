"""Verified phrase scanning and egress rule decisions on normalized text."""
from .._bridge import invoke


def evaluate(payload):
    return invoke("egress_policy", payload)
