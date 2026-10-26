"""Verified decisions for normalized MCP tool-call metadata."""
from .._bridge import invoke


def evaluate(positive, negative):
    """Return fault flags and the positive-call floor for one replay."""
    return invoke("mcp_authority", {"positive": positive, "negative": negative})
