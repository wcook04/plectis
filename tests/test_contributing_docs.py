from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_contributing_direct_validation_names_test_extra_prerequisite() -> None:
    text = (MICROCOSM_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "checkout-keyed temporary venv" in text
    assert "[Public Repo Map](README.md#choose-a-route)" in text
    assert "[Component Map](README.md#choose-a-route)" in text
    assert "contributor routing layer" in text
    assert "validation lanes after that route" in text
    assert text.index("[Public Repo Map](README.md#choose-a-route)") < text.index(
        "The smoke target is the no-install public sanity check."
    )
    assert "`.microcosm/` route state through `tour --card`" in text
    assert "Plectis smoke check: pass" in text
    assert "authority: pass" in text
    assert "workingness: clear" in text
    assert "served status: pass" in text
    assert "make install" in text
    assert "VENV=/tmp/plectis-dev-venv make install" in text
    assert "/tmp/plectis-dev-venv/bin/plectis hello ." in text
    assert "pytest basetemp, Python bytecode" in text
    assert "per-run folders inside" in text
    assert "`$(TMPDIR)/microcosm-substrate-test-tmp`" in text
    assert "do not share the" in text
    assert "same active basetemp" in text
    assert "PYTEST_KEEP_TMP=1" in text
    assert "make clean` removes the shared" in text
    assert "scratch root stays outside" in text
    assert "the checkout so tests" in text
    assert "disables pytest's cache provider" in text
    assert "direct pytest does not create `.pytest_cache`" in text
    assert "run separate pytest subsets at the same time" in text
    assert "unique `--basetemp` to each process" in text
    assert "Parallel direct invocations can still race" in text
    assert ".microcosm/test-tmp/pytest" not in text
    source_only_section = text.split(
        "If editable install is not available",
        1,
    )[1].split("## Standalone Candidate Export", 1)[0]
    assert "source-only minimum: map, reader branches, behavior proof, then" in text
    for command in (
        "PYTHONPATH=src python3 -m microcosm_core hello .",
        "PYTHONPATH=src python3 -m microcosm_core hello --reader cold_cloner .",
        "PYTHONPATH=src python3 -m microcosm_core hello --reader skeptical_reviewer .",
        "PYTHONPATH=src python3 -m microcosm_core hello --reader agent .",
        "PYTHONPATH=src python3 -m microcosm_core hello --reader domain_specialist .",
        "PYTHONPATH=src python3 -m microcosm_core tour --card .",
        "PYTHONPATH=src python3 -m microcosm_core status --card .",
    ):
        assert command in source_only_section
    for command in (
        "PYTHONPATH=src python3 -m microcosm_core hello .",
        "PYTHONPATH=src python3 -m microcosm_core hello --reader cold_cloner .",
        "PYTHONPATH=src python3 -m microcosm_core hello --reader skeptical_reviewer .",
        "PYTHONPATH=src python3 -m microcosm_core hello --reader agent .",
        "PYTHONPATH=src python3 -m microcosm_core hello --reader domain_specialist .",
        "PYTHONPATH=src python3 -m microcosm_core tour --card .",
        "PYTHONPATH=src python3 -m microcosm_core status --card .",
        "PYTHONPATH=src python3 -m microcosm_core authority --card",
        "PYTHONPATH=src python3 -m microcosm_core workingness --card",
        "PYTHONPATH=src python3 -m microcosm_core legibility-scorecard",
        "PYTHONPATH=src python3 -m microcosm_core --version",
        "PYTHONPATH=src python3 -m microcosm_core stripping-guard",
    ):
        assert command in text
    assert "The reader-specific `hello` rows in that source-form smoke are branch checks" in text
    assert "`cold_cloner` / `cold-cloner`" in text
    assert "`skeptical_reviewer` /\n`skeptical-reviewer`" in text
    assert "`agent` / `type-a-agent` are aliases" in text
    assert "`domain_specialist` / `domain-specialist` is the\nspecialty" in text
    assert "generated organ specialty index" in " ".join(text.split())
    assert (
        "PYTHONPATH=src /tmp/plectis-dev-venv/bin/python -m pytest "
        "tests/test_public_entry_docs.py tests/test_secret_exclusion_scan.py "
        "tests/test_private_state_scan.py"
    ) in text
    assert "python3 -m pip install -e '.[test]'" not in text
    assert (
        "\npython3 -m pytest tests/test_public_entry_docs.py "
        "tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py"
    ) not in text
    assert "make standalone-export EXPORT_OUT=/tmp/plectis-export" in text
    assert "receipts/release/release_export_receipt.json" in text
    assert "release_authorized=false" in text
    assert "intentionally not part of `make ci`" in text
    assert "validate it from inside the exported artifact" in text
    assert "cd /tmp/plectis-export/plectis" in text
    assert "That cold-clone check proves the exported package can install" in text
    assert "It does not authorize release" in text
    assert "`make test-all`" in text
    assert "broad drift-detection lane" in text
    assert "tracked source-tree receipts read-only" in text
    assert "explicitly opts into receipt writes" in text
    assert "MICROCOSM_TRACKED_RECEIPT_WRITES=1" in text
    assert "tracked `receipts/**` snapshots are the" in text
    assert "same outside-checkout pytest" in text
    assert "scratch parent as `make test`" in text
    assert "any generated output that needs to change still" in text
    assert "belongs in its owner lane" in text
    assert "and `make ci` are the" in text
    assert "standalone public verification floor" in text
    assert "For a broad cold-clone smoke" not in text
    assert "bounded cold-clone probe" in text
    assert "fixture availability, secret" in text
    assert "exclusion, and pattern-binding receipts" in text
    assert "ignored `.microcosm/cold_clone_probe.json` evidence" in text
    assert "--emit receipts/cold_clone_probe.json" not in text
    assert "--emit receipts/cold_clone_probe_local.json" not in text


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
