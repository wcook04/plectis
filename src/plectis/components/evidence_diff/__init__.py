"""Evidence-ID partition and last-row projection through a verified core."""
from .._bridge import invoke


def diff_evidence(lab, oracle):
    """Compare JSON rows with scalar IDs; skip rows without a truthy ID.

    Normalization, Python key equality, ordering and row projection are trusted host
    operations. A worker or validation failure raises; no fallback is used.
    """
    return invoke("evidence_diff", {"lab": lab, "oracle": oracle})


__all__ = ["diff_evidence"]
