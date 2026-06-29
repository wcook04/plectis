from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_security_docs_name_release_authority_receipt_boundary() -> None:
    security = (MICROCOSM_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    normalized = " ".join(security.split())

    for phrase in (
        "[Public Repo Map](README.md#choose-a-route)",
        "[Component Map](README.md#choose-a-route)",
        "Security reports should name paths through those public surfaces",
        "command cards, evidence fixtures, source capsules, validation shell, and release receipts",
        "## Release-Authority Reports",
        "make standalone-export EXPORT_OUT=/tmp/microcosm-security-boundary-export",
        "receipts/release/release_export_receipt.json",
        "receipt id, artifact hash, blocking codes, and release gate fields",
        "authority_receipt.release_authorized=false",
        "authority_receipt.publish_authorized=false",
        "release_candidate_packet.authority_state.release_authorization_gate.invoked=false",
        "release_candidate_packet.release_authorization_gate_decision.release_authorization_allowed_now=false",
        "must name the separate operator authorization receipt",
        "Do not attach local validation byproducts",
        "The release receipt path is the evidence handle",
    ):
        assert phrase in normalized

    assert security.index("[Public Repo Map](README.md#choose-a-route)") < security.index(
        "## Reportable Boundary Failures"
    )
