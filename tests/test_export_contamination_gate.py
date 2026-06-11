"""Population contamination gate over exported source_modules payloads.

The bounded import membrane trusts exact-copy declarations, so committed
compiler output (SwiftPM/Xcode .build trees) and real host paths inside
exported bundles are invisible to it. This gate is the fail-closed tree-level
check that the population/export candidate carries neither class.
"""

from __future__ import annotations

import json
from pathlib import Path

from microcosm_core.release_export import (
    _skip_reason,
    scan_source_modules_contamination,
)

MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_live_source_modules_payloads_are_contamination_free() -> None:
    rows = scan_source_modules_contamination(MICROCOSM_ROOT)
    assert rows == [], (
        "Population contamination gate: exported source_modules payloads must "
        "not carry compiler output or real host paths.\n"
        "REPAIR MAP: build_artifact_directory -> delete the build tree from "
        "source_modules (compiler output is not source); host_private_path -> "
        "sanitize the macro source to the synthetic /Users/operator convention "
        "and re-run refresh-exact-copy-source-modules; deliberate fixture -> "
        "declare a reasoned SOURCE_MODULE_CONTAMINATION_ALLOWLIST entry.\n"
        f"first_rows={json.dumps(rows[:8], indent=1)}"
    )


def test_export_skip_rules_exclude_swift_build_directories() -> None:
    for rel in (
        "apps/zenith-macos/.build/debug.yaml",
        "apps/zenith-macos/.build/debug/output-file-map.json",
        "apps/zenith-macos/.swiftpm/xcode/package.xcworkspace/contents",
        "apps/DerivedData/intermediates.d",
    ):
        assert _skip_reason(Path(rel), is_dir=False) == "cache_or_build_directory", rel


def test_contamination_scanner_flags_planted_specimens(tmp_path: Path) -> None:
    root = tmp_path / "microcosm-substrate"
    modules = root / "examples/demo/exported_demo_bundle/source_modules"
    build_file = modules / "app/.build/description.json"
    build_file.parent.mkdir(parents=True, exist_ok=True)
    build_file.write_text(
        json.dumps({"workingDirectory": "/Users/realname/src"}), encoding="utf-8"
    )
    leak_file = modules / "app/tool.py"
    leak_file.write_text("DEFAULT = '/Users/realname/src/repo'\n", encoding="utf-8")
    synthetic_file = modules / "app/fixture.py"
    synthetic_file.write_text(
        "CWD = '/Users/operator/src/repo'\nHOME = '/Users/example'\n",
        encoding="utf-8",
    )
    route_file = modules / "app/routes.py"
    route_file.write_text("VIEW = '/home/StationSurfaceAtlas.tsx'\n", encoding="utf-8")

    rows = scan_source_modules_contamination(root)

    classes = {
        (row["contamination_class"], row["path"].rsplit("/", 1)[-1]) for row in rows
    }
    assert ("build_artifact_directory", "description.json") in classes
    assert ("host_private_path", "tool.py") in classes
    assert all("fixture.py" not in row["path"] for row in rows)
    assert all("routes.py" not in row["path"] for row in rows)
