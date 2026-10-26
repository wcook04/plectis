"""Verified normalized premise scoring and ordering."""
from .._bridge import invoke


def rank(payload):
    return invoke("premise_ranking", payload)
