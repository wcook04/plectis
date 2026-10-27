"""Invoke the verified ownership classification decision core."""
from .._bridge import invoke


def classify(payload):
    """Classify normalized paths and ordered claims through the sealed core."""
    return invoke("ownership_classification", payload)
