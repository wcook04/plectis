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
    rows = scan_source_modules_contamination(
        MICROCOSM_ROOT,
        compare_private_bodies=False,
    )
    assert rows == [], (
        "Population contamination gate: exported source_modules payloads must "
        "not carry compiler output, real host paths, or private control-plane "
        "bodies.\n"
        "REPAIR MAP: build_artifact_directory -> delete the build tree from "
        "source_modules (compiler output is not source); host_private_path -> "
        "sanitize the macro source to the synthetic /Users/operator convention "
        "and re-run refresh-exact-copy-source-modules; private_body_* -> "
        "replace with a public-safe body, synthetic stub, fixture, contract/card, "
        "or omission; deliberate fixture -> "
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


def test_contamination_scanner_flags_private_body_matches(tmp_path: Path) -> None:
    private_root = tmp_path / "private"
    public_root = tmp_path / "public"
    exact_private = private_root / "system/lib/work_ledger.py"
    near_private = private_root / "tools/meta/factory/work_ledger.py"
    exact_public = public_root / "source_modules/system/lib/work_ledger.py"
    near_public = (
        public_root
        / "examples/demo/exported_demo_bundle/source_modules/tools/meta/factory/work_ledger.py"
    )
    safe_public = public_root / "source_modules/public_examples/synthetic_runtime.py"
    exact_body = "\n".join(f"def exact_line_{index}(): return {index}" for index in range(40))
    near_body = "\n".join(f"def near_line_{index}(): return {index}" for index in range(60))
    exact_private.parent.mkdir(parents=True, exist_ok=True)
    near_private.parent.mkdir(parents=True, exist_ok=True)
    exact_public.parent.mkdir(parents=True, exist_ok=True)
    near_public.parent.mkdir(parents=True, exist_ok=True)
    safe_public.parent.mkdir(parents=True, exist_ok=True)
    exact_private.write_text(exact_body, encoding="utf-8")
    exact_public.write_text(exact_body, encoding="utf-8")
    near_private.write_text(near_body, encoding="utf-8")
    near_public.write_text(
        near_body.replace("near_line_7", "public_line_7") + "\n# public receipt wrapper\n",
        encoding="utf-8",
    )
    safe_public.write_text("def synthetic_runtime():\n    return 'public'\n", encoding="utf-8")

    rows = scan_source_modules_contamination(public_root, private_root=private_root)

    by_path = {row["path"]: row for row in rows}
    assert by_path["source_modules/system/lib/work_ledger.py"][
        "contamination_class"
    ] == "private_body_exact_match"
    assert by_path[
        "examples/demo/exported_demo_bundle/source_modules/tools/meta/factory/work_ledger.py"
    ]["contamination_class"] == "private_body_near_verbatim"
    receipt_text = json.dumps(rows)
    assert exact_body not in receipt_text
    assert "def near_line_0" not in receipt_text
    assert "source_modules/public_examples/synthetic_runtime.py" not in by_path
