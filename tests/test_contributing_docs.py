from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_contributing_direct_validation_names_test_extra_prerequisite() -> None:
    text = (MICROCOSM_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "repository-local `.venv`" in text
    assert "[Public Repo Map](README.md#public-repo-map)" in text
    assert "[Component Map](README.md#component-map)" in text
    assert "contributor routing layer" in text
    assert "validation lanes after that route" in text
    assert text.index("[Public Repo Map](README.md#public-repo-map)") < text.index(
        "The smoke target is the no-install public sanity check."
    )
    assert "`.microcosm/` route state through `tour --card`" in text
    assert "make install" in text
    assert ".venv/bin/python -m pip install -e '.[test]'" in text
    assert ".venv/bin/microcosm hello ." in text
    assert "pytest basetemp, Python bytecode" in text
    assert "per-run folders inside" in text
    assert "`$(TMPDIR)/microcosm-substrate-test-tmp`" in text
    assert "do not share the" in text
    assert "same active basetemp" in text
    assert "PYTEST_KEEP_TMP=1" in text
    assert "make clean` removes the shared" in text
    assert "scratch root stays outside" in text
    assert "the checkout so tests" in text
    for command in (
        "PYTHONPATH=src python3 -m microcosm_core hello .",
        "PYTHONPATH=src python3 -m microcosm_core tour --card .",
        "PYTHONPATH=src python3 -m microcosm_core status --card .",
        "PYTHONPATH=src python3 -m microcosm_core authority --card",
        "PYTHONPATH=src python3 -m microcosm_core workingness --card",
        "PYTHONPATH=src python3 -m microcosm_core legibility-scorecard",
        "PYTHONPATH=src python3 -m microcosm_core --version",
        "PYTHONPATH=src python3 -m microcosm_core stripping-guard",
    ):
        assert command in text
    assert (
        "PYTHONPATH=src .venv/bin/python -m pytest tests/test_public_entry_docs.py "
        "tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py"
    ) in text
    assert "python3 -m pip install -e '.[test]'" not in text
    assert (
        "\npython3 -m pytest tests/test_public_entry_docs.py "
        "tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py"
    ) not in text
    assert "make standalone-export EXPORT_OUT=/tmp/microcosm-substrate-export" in text
    assert "receipts/release/release_export_receipt.json" in text
    assert "release_authorized=false" in text
    assert "intentionally not part of `make ci`" in text
    assert "validate it from inside the exported artifact" in text
    assert "cd /tmp/microcosm-substrate-export/microcosm-substrate" in text
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
    assert "ignored `.microcosm/cold_clone_probe.json` evidence" in text
    assert "--emit receipts/cold_clone_probe.json" not in text
    assert "--emit receipts/cold_clone_probe_local.json" not in text
