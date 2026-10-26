"""Verified policy decision for normalized sandbox replay actions."""
from .._bridge import invoke


def evaluate(rows):
    """Return verdict/rule pairs for a list of normalized action records."""
    return invoke("sandbox_policy", {"rows": rows})
