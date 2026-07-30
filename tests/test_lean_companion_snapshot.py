from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core.validators.lean_companion_snapshot import (
    refresh_lean_companion_snapshot,
    validate_lean_companion_snapshot,
)


PLECTIS_ROOT = Path(__file__).resolve().parents[1]


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "plectis"
    (root / "docs").mkdir(parents=True)
    shutil.copy2(PLECTIS_ROOT / "README.md", root / "README.md")
    shutil.copy2(
        PLECTIS_ROOT / "docs/lean_companion_snapshot.json",
        root / "docs/lean_companion_snapshot.json",
    )
    return root


def test_real_lean_companion_snapshot_is_bound_to_readme() -> None:
    receipt = validate_lean_companion_snapshot(PLECTIS_ROOT)
    assert receipt["status"] == "pass", receipt["errors"]
    assert receipt["errors"] == []
    assert receipt["findings"]["scale"]["module_count"] > 0
    assert receipt["findings"]["scale"]["theorem_like_count"] > 0
    assert receipt["authority_ceiling"]["release_authorized"] is False
    assert receipt["authority_ceiling"]["proof_correctness_claim"] is False


def test_upstream_checkout_matches_recorded_public_commit() -> None:
    upstream_root = PLECTIS_ROOT.parent / "plectis-lean-erdos249-257"
    if not (upstream_root / ".git").exists():
        return
    receipt = validate_lean_companion_snapshot(
        PLECTIS_ROOT,
        upstream_root=upstream_root,
    )
    assert receipt["status"] == "pass", receipt["errors"]
    assert (
        receipt["findings"]["upstream"]["tracked_branch_head"]
        == receipt["findings"]["public_ref"]
    )


def test_blocks_stale_readme_counts(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    payload = json.loads(
        (root / "docs/lean_companion_snapshot.json").read_text(encoding="utf-8")
    )
    module_count = f"{payload['scale']['module_count']:,}"
    theorem_like_count = f"{payload['scale']['theorem_like_count']:,}"
    readme_path = root / "README.md"
    readme_path.write_text(
        readme_path.read_text(encoding="utf-8").replace(
            f"{module_count} Lean modules and {theorem_like_count}",
            "540 Lean modules and 5,850",
            1,
        ),
        encoding="utf-8",
    )
    receipt = validate_lean_companion_snapshot(root)
    assert receipt["status"] == "blocked"
    assert "LEAN_COMPANION_README_DRIFT" in {
        row["code"] for row in receipt["errors"]
    }


def test_blocks_authority_ceiling_overclaim(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    snapshot_path = root / "docs/lean_companion_snapshot.json"
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    payload["authority_ceiling"]["release_authorized"] = True
    snapshot_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt = validate_lean_companion_snapshot(root)
    assert receipt["status"] == "blocked"
    assert "LEAN_COMPANION_AUTHORITY_OVERCLAIM" in {
        row["code"] for row in receipt["errors"]
    }


def test_refresh_tracks_public_ref_and_is_idempotent(tmp_path: Path) -> None:
    upstream_root = PLECTIS_ROOT.parent / "plectis-lean-erdos249-257"
    if not (upstream_root / ".git").exists():
        return
    root = _fixture_root(tmp_path)

    first = refresh_lean_companion_snapshot(
        root,
        upstream_root=upstream_root,
    )
    assert first["status"] == "pass", first["errors"]
    snapshot_path = root / "docs/lean_companion_snapshot.json"
    readme_path = root / "README.md"
    snapshot_after_first = snapshot_path.read_text(encoding="utf-8")
    readme_after_first = readme_path.read_text(encoding="utf-8")
    payload = json.loads(snapshot_after_first)
    assert payload["upstream"]["public_ref"] == first["findings"]["upstream"][
        "tracked_branch_head"
    ]
    assert payload["refresh"]["local_command"].find("--write") >= 0
    assert payload["upstream"]["public_ref"] in readme_after_first

    second = refresh_lean_companion_snapshot(
        root,
        upstream_root=upstream_root,
    )
    assert second["status"] == "pass", second["errors"]
    assert snapshot_path.read_text(encoding="utf-8") == snapshot_after_first
    assert readme_path.read_text(encoding="utf-8") == readme_after_first
