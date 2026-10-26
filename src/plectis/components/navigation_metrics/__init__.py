"""Verified navigation packet matching and decision core."""
from .._bridge import invoke


def evaluate(payload):
    """Evaluate normalized distinct IDs and observed decision flags."""
    return invoke("navigation_metrics", payload)
