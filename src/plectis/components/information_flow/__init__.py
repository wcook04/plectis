"""Verified decisions and reachability over supplied information-flow observations."""

from .._bridge import invoke


def verdicts(rows):
    """Decide each row of normalized boolean policy observations in order."""
    return invoke("information_flow", {"rows": rows})


def closures(episodes):
    """Return per-label node reachability for each normalized episode graph."""
    return invoke("information_flow", {"episodes": episodes})
