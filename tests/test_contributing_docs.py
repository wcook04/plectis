from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_contributing_is_a_concise_community_contract() -> None:
    text = (MICROCOSM_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())

    # Concise by contract: the deep review lanes belong to the maintainer
    # runbook, not the community front door.
    assert len(text.splitlines()) <= 110

    # Routing: contributors enter through the README route table, then the
    # validation lanes.
    assert "[Choose a route](README.md#choose-a-route)" in text
    assert "contributor routing layer" in normalized
    assert "validation lanes after that route" in normalized

    # Development setup keeps the checkout-keyed venv truth and a stable
    # override path.
    assert "checkout-keyed temporary venv" in text
    assert "VENV=/tmp/plectis-dev-venv make install" in text
    assert "/tmp/plectis-dev-venv/bin/plectis hello ." in text

    # The command floor.
    for command in ("make check", "make test", "make ci", "make validate"):
        assert command in text

    # The two direct-pytest safety rules survive the shortening.
    assert "One basetemp per process." in text
    assert "unique `--basetemp`" in text
    assert "Tracked receipts are read-only under pytest." in text
    assert "MICROCOSM_TRACKED_RECEIPT_WRITES=1" in text

    # Generated files are builder-owned.
    assert "Do not hand-edit" in text
    assert "scripts/build_organ_atlas.py --write" in text

    # PR expectations still route through the template guardrail.
    assert ".github/PULL_REQUEST_TEMPLATE.md" in text
    assert "inline checklist" in text
    assert "not a release approval surface" in text

    # Hard boundaries are stated, not linked away.
    assert "Do not contribute secrets, credentials" in text
    assert "hosted-release" in text

    # The deep lane is owned and linked.
    assert "[docs/maintainers/validation.md](docs/maintainers/validation.md)" in text


def test_maintainer_validation_runbook_conserves_review_lane_truth() -> None:
    runbook = " ".join(
        (MICROCOSM_ROOT / "docs/maintainers/validation.md")
        .read_text(encoding="utf-8")
        .split()
    )

    # The truths that used to live in CONTRIBUTING.md must survive in the
    # runbook: full smoke card set, isolation detail, drift lane, proof
    # packets, and the standalone export validation loop.
    for phrase in (
        "Plectis smoke check: pass",
        "authority: pass",
        "workingness: clear",
        "served status: pass",
        "plectis first-screen --card .",
        "$(TMPDIR)/microcosm-substrate-venv-<checkout-key>",
        "do not share the same active basetemp",
        "PYTEST_KEEP_TMP=1",
        "disabled in `pyproject.toml`",
        "make test-all",
        "drift-detection suite",
        "MICROCOSM_TRACKED_RECEIPT_WRITES=1",
        "make flight-recorder FLIGHT_RECORDER_OUT=/tmp/microcosm-flight-recorder",
        "make flight-recorder-verify FLIGHT_RECORDER_VERIFY_DIR=/tmp/microcosm-flight-recorder",
        "blocked/non-zero command evidence",
        "make release-candidate-proof",
        "make release-review",
        "make standalone-export EXPORT_OUT=/tmp/plectis-export",
        "receipts/release/release_export_receipt.json",
        "release_authorized=false",
        "intentionally not part of `make ci`",
        "cd /tmp/plectis-export/plectis",
        "proves the exported package can install",
        "It does not authorize release",
    ):
        assert phrase in runbook, phrase

    # The source-only spelling routes through the plectis module facade.
    assert "python3 -m plectis" in runbook


def test_pull_request_template_keeps_public_boundary_inline() -> None:
    template = (
        MICROCOSM_ROOT / ".github/PULL_REQUEST_TEMPLATE.md"
    ).read_text(encoding="utf-8")
    contributing = (MICROCOSM_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert ".github/PULL_REQUEST_TEMPLATE.md" in contributing
    assert "inline checklist" in contributing
    assert "not a release approval surface" in contributing

    for phrase in (
        "What public runtime, fixture, receipt, standard, doc, or test surface changed?",
        "Ran the focused tests for the touched surface.",
        "Ran `make ci` or explained why a narrower validation lane is sufficient.",
        "not a host interpreter by accident",
        "No secrets, credentials, sessions, provider payload bodies",
        "No source-mutation, provider-call, hosted-release, recipient-send",
        "Synthetic fixtures are used only as regression wrappers",
        "runnable behavior, a validator, a receipt, or an explicit omission boundary",
        "release_authorized=false",
        "New GitHub/source surfaces are included in `MANIFEST.in`, package data, or release export",
    ):
        assert phrase in template
