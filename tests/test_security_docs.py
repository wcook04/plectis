from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_security_doc_is_a_concise_reporting_contract() -> None:
    security = (MICROCOSM_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    normalized = " ".join(security.split())

    # Concise by contract; the verification depth lives in the runbook.
    assert len(security.splitlines()) <= 70

    for phrase in (
        "https://github.com/wcook04/plectis/security/advisories/new",
        "do not open a public issue with vulnerability details",
        "No `security@` email route is published yet",
        "real secrets, credentials, tokens, cookies, private keys",
        "raw operator voice, private personal material, or provider payload bodies",
        "not automatically leaks",
        "Do not paste the suspected secret, private payload, raw prompt body",
        "do not attach local validation byproducts",
        "[Choose a route](README.md#choose-a-route)",
        "[docs/maintainers/security-runbook.md](docs/maintainers/security-runbook.md)",
    ):
        assert phrase in normalized, phrase

    # The reporting route comes before the taxonomy of reportable classes.
    assert security.index("## Reporting privately") < security.index(
        "## What to report"
    )


def test_security_runbook_conserves_release_authority_receipt_boundary() -> None:
    runbook = (MICROCOSM_ROOT / "docs/maintainers/security-runbook.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(runbook.split())

    for phrase in (
        "./bootstrap.sh",
        "VENV=/tmp/plectis-security-venv make install",
        "/tmp/plectis-security-venv/bin/plectis authority --card",
        "/tmp/plectis-security-venv/bin/plectis stripping-guard",
        "tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py tests/test_public_entry_docs.py",
        "make standalone-export EXPORT_OUT=/tmp/plectis-security-boundary-export",
        "receipts/release/release_export_receipt.json",
        "receipt id, artifact hash, blocking codes, and release gate fields",
        "authority_receipt.release_authorized=false",
        "authority_receipt.publish_authorized=false",
        "release_candidate_packet.authority_state.release_authorization_gate.invoked=false",
        "release_candidate_packet.release_authorization_gate_decision.release_authorization_allowed_now=false",
        "must name the separate operator authorization receipt",
        "The release receipt path is the evidence handle",
    ):
        assert phrase in normalized, phrase
