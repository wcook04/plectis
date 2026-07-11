from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_quickstart_is_a_short_install_first_path() -> None:
    quickstart = (MICROCOSM_ROOT / "QUICKSTART.md").read_text(encoding="utf-8")

    # Short by contract: a quickstart that regrows into an operator manual has
    # failed its one job. The deep lanes live in CONTRIBUTING.md and
    # docs/maintainers/.
    assert len(quickstart.splitlines()) <= 110

    # Install-first ordering, with the pre-install probe available but not
    # blocking the first screen.
    assert quickstart.index("## 1. Install") < quickstart.index("## 2. First result")
    assert quickstart.index("## 2. First result") < quickstart.index(
        "## 5. Verify the public floor"
    )
    assert "python3 -m pip install ." in quickstart
    assert "./bootstrap.sh" in quickstart
    assert "./bootstrap.sh --dry-run" in quickstart
    assert ".microcosm/cold_clone_probe.json" in quickstart
    assert "--emit receipts/cold_clone_probe.json" not in quickstart

    # The public commands use the plectis name only; the source form routes
    # through the plectis module facade, never the internal package name.
    assert "plectis tour --format text ." in quickstart
    assert "plectis tour --card ." in quickstart
    assert "plectis hello ." in quickstart
    assert "PYTHONPATH=src python3 -m plectis" in quickstart
    assert "-m microcosm_core" not in quickstart

    # The bounded browser surface keeps its request ceiling by default.
    assert (
        "plectis serve . --host 127.0.0.1 --port 8765 --max-requests 7"
        in quickstart
    )
    assert "Omit `--max-requests` only when" in quickstart

    # Routing back into the deeper map.
    assert "[README Component Map](README.md#choose-a-route)" in quickstart
    assert "[CONTRIBUTING.md](CONTRIBUTING.md)" in quickstart
    assert "make check" in quickstart
    assert "make ci" in quickstart

    # Boundary language survives the shortening.
    assert "no network or model calls" in quickstart
    assert "no source mutation" in quickstart
    assert "plectis evidence list . --limit 25" in quickstart


def test_quickstart_cross_doc_anchors_resolve_in_generated_organs() -> None:
    # ORGANS.md is builder-generated (build_organ_atlas.py). QUICKSTART and README
    # advertise these anchors as the cold-reader "one-line organ ladder" and the
    # "find your specialty" index. Lock each advertised anchor literal to the live
    # generated heading literal in the same test so a future build_organ_atlas.py
    # heading rename must update both sides together (no silent 404 for a cold reader).
    quickstart = (MICROCOSM_ROOT / "QUICKSTART.md").read_text(encoding="utf-8")
    organs = (MICROCOSM_ROOT / "ORGANS.md").read_text(encoding="utf-8")

    # "one-line organ ladder": the em-dash drops out and the two spaces around it
    # each become a hyphen, so the GitHub slug carries a doubled hyphen.
    assert "ORGANS.md#plectis-at-a-glance--every-organ-in-one-line" in quickstart
    assert "## Plectis at a glance — every organ in one line" in organs

    # "find your specialty" human index.
    assert "ORGANS.md#find-your-specialty" in quickstart
    assert "## Find your specialty" in organs
