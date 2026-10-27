"""Dependency-to-dependent reachability, evaluated by the generated core."""
from .._bridge import invoke


def dependents(edges, starts):
    """Return one sorted positive-length reachability set for each start."""
    return invoke("dependency_reachability", {"edges": edges, "starts": starts})
