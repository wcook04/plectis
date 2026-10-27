"""Verified selection among observed tactic candidates."""
from .._bridge import invoke


def select(payload):
    return invoke("tactic_selection", payload)
