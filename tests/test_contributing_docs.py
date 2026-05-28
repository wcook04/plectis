from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_contributing_direct_validation_names_test_extra_prerequisite() -> None:
    text = (MICROCOSM_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "repository-local `.venv`" in text
    assert "`.microcosm/` route state through `tour --card`" in text
    assert "make install" in text
    assert ".venv/bin/python -m pip install -e '.[test]'" in text
    assert ".venv/bin/microcosm hello ." in text
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
