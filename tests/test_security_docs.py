from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_security_docs_name_release_authority_receipt_boundary() -> None:
    security = (MICROCOSM_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    normalized = " ".join(security.split())

    for phrase in (
        "## Release-Authority Reports",
        "make standalone-export EXPORT_OUT=/tmp/microcosm-security-boundary-export",
        "receipts/release/release_export_receipt.json",
        "receipt id, artifact hash, blocking codes, and release gate fields",
        "release_authorized=false",
        "gate_invoked=false",
        "release_authorization_allowed_now=false",
        "separate operator authorization receipt",
        "Do not attach local validation byproducts",
        "The release receipt path is the evidence handle",
    ):
        assert phrase in normalized
