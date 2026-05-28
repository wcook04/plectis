from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_contributing_direct_validation_names_test_extra_prerequisite() -> None:
    text = (MICROCOSM_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "make install" in text
    assert "python3 -m pip install -e '.[test]'" in text
    assert (
        "PYTHONPATH=src python3 -m pytest tests/test_public_entry_docs.py "
        "tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py"
    ) in text
    assert (
        "\npython3 -m pytest tests/test_public_entry_docs.py "
        "tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py"
    ) not in text
