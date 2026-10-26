"""Validate normalized walkthrough steps through the verified decision core."""
from .._bridge import invoke


def validate(steps, time_budget_minutes=10):
    """Check normalized steps and a numeric minute budget; raises on failure."""
    return invoke("walkthrough_validation", {"steps": steps, "time_budget_minutes": time_budget_minutes})
