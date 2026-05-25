from __future__ import annotations

import json
from pathlib import Path

from tools.meta.factory import check_station_geometry


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_station_geometry_check_detects_tokenizable_literals() -> None:
    source = """
export function Panel() {
  return <div className="rounded-[12px] gap-2.5 px-2.5 py-2.5 min-h-[1.25rem]" />;
}
"""

    violations = check_station_geometry.scan_text(source, rel_path="fixture.tsx")

    assert [violation.kind for violation in violations] == [
        "raw_radius",
        "raw_dense_spacing",
        "raw_dense_spacing",
        "raw_dense_spacing",
        "raw_dense_min_height",
    ]
    assert violations[0].replacement_hint == "rounded-[var(--zenith-radius-md)]"


def test_station_geometry_live_tree_is_clean_for_tracked_stable_surfaces() -> None:
    payload = check_station_geometry.scan_repo(REPO_ROOT)

    assert payload["ok"], json.dumps(payload["violations"][:10], indent=2)
    assert payload["scanned_file_count"] > 0
    assert "system/server/ui/src/components/world/AgentObservabilityLens.tsx" in payload["allowlisted_paths"]


def test_ui_build_runs_station_geometry_check_first() -> None:
    package = json.loads((REPO_ROOT / "system/server/ui/package.json").read_text())
    scripts = package["scripts"]

    assert scripts["check:station-geometry"] == "cd ../../.. && ./repo-python tools/meta/factory/check_station_geometry.py --check"
    assert scripts["build"].startswith("npm run check:station-geometry && ")
