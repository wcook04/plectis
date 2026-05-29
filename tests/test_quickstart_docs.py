from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_quickstart_names_source_only_browser_serve_path() -> None:
    quickstart = (MICROCOSM_ROOT / "QUICKSTART.md").read_text(encoding="utf-8")

    assert "[README Component Map](README.md#component-map)" in quickstart
    assert "runtime package, command cards, public" in quickstart
    assert "doctrine, evidence fixtures, source capsules, and validation shell" in (
        quickstart
    )
    assert (
        "microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 6"
        in quickstart
    )
    assert (
        "PYTHONPATH=src python3 -m microcosm_core serve . --host 127.0.0.1 "
        "--port 8765 --max-requests 6"
    ) in quickstart
    assert "If you are staying source-only" in quickstart
    assert "validate the exported artifact as its own clone" in quickstart
    assert "cd /tmp/microcosm-substrate-export/microcosm-substrate" in quickstart
    assert (
        "This checks standalone install, tests, and smoke from the exported root"
        in quickstart
    )
    assert "not authorize release" in quickstart
