"""Preserve every admitted observation of a finite deterministic model.

``compare`` searches for a shortest differing input continuation. An accepted
relation is checked by Python generated from the proved Dafny checker. The
negative continuation is independently checked by the generated replay kernel.
The model parser, search, encoding, and correspondence to real programs are trusted.
"""

from ._api import InvalidMachine, check_certificate, check_counterexample, compare

__all__ = ["InvalidMachine", "check_certificate", "check_counterexample", "compare"]
