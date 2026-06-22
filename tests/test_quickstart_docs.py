from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_quickstart_names_source_only_browser_serve_path() -> None:
    quickstart = (MICROCOSM_ROOT / "QUICKSTART.md").read_text(encoding="utf-8")
    compact_smoke = quickstart.split(
        "If you are staying source-only, use the exact same hand smoke through the",
        maxsplit=1,
    )[0]
    source_only_smoke = quickstart.split(
        "If you are staying source-only, use the exact same hand smoke through the",
        maxsplit=1,
    )[1].split("Read those as a first-screen contract", maxsplit=1)[0]

    assert "[README Component Map](README.md#component-map)" in quickstart
    assert "runtime package, command cards, public" in quickstart
    assert "doctrine, evidence fixtures, source capsules, and validation shell" in (
        quickstart
    )
    assert "./bootstrap.sh" in quickstart
    assert "./bootstrap.sh --dry-run" in quickstart
    assert ".microcosm/cold_clone_probe.json" in quickstart
    assert "--emit receipts/cold_clone_probe.json" not in quickstart
    assert (
        quickstart.index("## 0. Run The Bounded Cold-Clone Probe")
        < quickstart.index("## 1. Install The Local Command")
    )
    assert (
        "plectis serve . --host 127.0.0.1 --port 8765 --max-requests 7"
        in quickstart
    )
    assert (
        "PYTHONPATH=src python3 -m microcosm_core serve . --host 127.0.0.1 "
        "--port 8765 --max-requests 7"
    ) in quickstart
    assert "If you are staying source-only" in quickstart
    assert "- `/workingness-card`" in quickstart
    assert "compact Demo To Scale bridge" in quickstart
    assert "runtime bridge summary" in quickstart
    assert "projection status counts" in quickstart
    assert "open/closed intake-cell counts" in quickstart
    assert quickstart.index("- `/project/observatory-card`") < quickstart.index(
        "Treat `/project/observatory-card` as the compact Demo To Scale bridge"
    ) < quickstart.index("/project/observatory` only")
    assert (
        "Open `/workingness` only when you need the full per-organ "
        "failure-envelope map."
    ) in quickstart
    assert "validates those receipts" in quickstart
    assert "Plectis smoke check: pass" in quickstart
    assert "authority: pass" in quickstart
    assert "workingness: clear" in quickstart
    assert "served status: pass" in quickstart
    assert "make flight-recorder FLIGHT_RECORDER_OUT=/tmp/microcosm-flight-recorder" in (
        quickstart
    )
    assert (
        "make flight-recorder-verify FLIGHT_RECORDER_VERIFY_DIR=/tmp/microcosm-flight-recorder"
        in quickstart
    )
    assert "blocked/non-zero command evidence" in quickstart
    assert "not a launch, standards, external-model" in quickstart
    assert quickstart.index("- `/workingness-card`") < quickstart.index(
        "Open `/workingness` only"
    )
    assert "plectis first-screen --card ." in compact_smoke
    assert (
        compact_smoke.index("plectis hello .")
        < compact_smoke.index("plectis first-screen --card .")
        < compact_smoke.index("plectis tour --card .")
    )
    assert (
        "PYTHONPATH=src python3 -m microcosm_core first-screen --card ."
        in source_only_smoke
    )
    assert (
        source_only_smoke.index("PYTHONPATH=src python3 -m microcosm_core hello .")
        < source_only_smoke.index(
            "PYTHONPATH=src python3 -m microcosm_core first-screen --card ."
        )
        < source_only_smoke.index(
            "PYTHONPATH=src python3 -m microcosm_core tour --card ."
        )
    )
    assert "validate the exported artifact as its own clone" in quickstart
    assert "cd /tmp/plectis-export/plectis" in quickstart
    assert (
        "This checks standalone install, tests, and smoke from the exported root"
        in quickstart
    )
    assert "not authorize release" in quickstart


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
