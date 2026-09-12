from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from microcosm_core.validators import lean_companion_snapshot as companion
from microcosm_core.validators.lean_companion_snapshot import (
    refresh_lean_companion_snapshot,
    validate_lean_companion_snapshot,
)


PLECTIS_ROOT = Path(__file__).resolve().parents[1]

def _companion_checkout() -> Path:
    parent = PLECTIS_ROOT.parent
    for name in ("plectis-erdos", "plectis-lean-erdos249-257"):
        candidate = parent / name
        if (candidate / ".git").exists():
            return candidate
    return parent / "plectis-erdos"




def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "plectis"
    (root / "docs").mkdir(parents=True)
    shutil.copy2(PLECTIS_ROOT / "README.md", root / "README.md")
    # The compact agent entry is a governed surface, not decoration: it asserts
    # the companion's problem scope to every provider adapter that routes here.
    # A fixture without it would let the surface checks pass vacuously.
    shutil.copy2(
        PLECTIS_ROOT / "AGENTS.override.md",
        root / "AGENTS.override.md",
    )
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
    upstream_root = _companion_checkout()
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


def test_accepts_previous_scale_and_citation_wording(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "These counts include library declarations; they do\n"
        "  not count solutions to Erdős problems.",
        "These are scale and navigation counts, not separate\n"
        "  mathematical claims;",
    ).replace("remains the version to cite", "remains the tagged citation anchor")
    path.write_text(text, encoding="utf-8")
    receipt = validate_lean_companion_snapshot(root)
    assert receipt["status"] == "pass", receipt["errors"]


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("These counts include library declarations; they do\n"
         "  not count solutions to Erdős problems.", ""),
        ("they do\n  not count solutions", "they do count solutions"),
        ("remains the version to cite", "is not the version to cite"),
        ("releases/tag/", "releases/retired-tag/"),
    ],
)
def test_blocks_missing_or_reversed_count_and_citation_limits(
    tmp_path: Path, old: str, new: str,
) -> None:
    root = _fixture_root(tmp_path)
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")
    receipt = validate_lean_companion_snapshot(root)
    assert receipt["status"] == "blocked"
    assert "LEAN_COMPANION_README_DRIFT" in {row["code"] for row in receipt["errors"]}


@pytest.mark.parametrize("legacy_prose", [False, True])
def test_refresh_preserves_surrounding_prose_and_uses_literal_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, legacy_prose: bool,
) -> None:
    """Refreshing either prose edition needs no sibling checkout or network."""
    root = _fixture_root(tmp_path)
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    if legacy_prose:
        text = text.replace(
            "the version to cite when referring to that release.",
            "the tagged, citable scholarly artefact and citation anchor.",
        )
    prefix, _ = text.split("- [**Browse the Lean source**]", 1)
    suffix = "\n## A later section\n\nKeep this prose exactly.\n"
    path.write_text(text + suffix, encoding="utf-8")
    payload = json.loads((root / "docs/lean_companion_snapshot.json").read_text())
    payload["upstream"]["public_ref"] = "a" * 40
    payload["upstream"]["latest_tag"] = "v99.0.0"
    payload["scale"]["module_count"] += 1
    monkeypatch.setattr(companion, "_build_snapshot_from_upstream", lambda *_: payload)
    monkeypatch.setattr(companion, "_validate_upstream", lambda *_: {})

    first = refresh_lean_companion_snapshot(root, upstream_root=tmp_path)
    assert first["status"] == "pass", first["errors"]
    refreshed = path.read_text(encoding="utf-8")
    assert refreshed.startswith(prefix)
    assert refreshed.endswith(suffix)
    assert "not count solutions to Erdős problems" in refreshed
    assert "`v99.0.0` remains the version to cite" in refreshed
    assert "/releases/tag/v99.0.0" in refreshed
    assert f"{payload['scale']['module_count']:,} Lean modules" in refreshed
    assert "citation anchor" not in refreshed[len(prefix):]
    second = refresh_lean_companion_snapshot(root, upstream_root=tmp_path)
    assert second["status"] == "pass", second["errors"]
    assert path.read_text(encoding="utf-8") == refreshed


def test_blocks_stale_companion_problem_count_in_the_agent_entry(
    tmp_path: Path,
) -> None:
    """The defect this check exists for.

    The README named eight open problems while the compact agent entry -- the
    file every provider adapter routes to -- named six. The README was bound to
    the companion registry and the agent entry was not, so an unprimed agent
    inherited the wrong scope from the one surface written for it.
    """
    root = _fixture_root(tmp_path)
    entry_path = root / "AGENTS.override.md"
    entry_path.write_text(
        entry_path.read_text(encoding="utf-8").replace(
            "eight open Erdős problems",
            "six open Erdős problems",
            1,
        ),
        encoding="utf-8",
    )
    receipt = validate_lean_companion_snapshot(root)
    assert receipt["status"] == "blocked"
    assert "LEAN_COMPANION_FACT_DRIFT" in {row["code"] for row in receipt["errors"]}
    assert receipt["findings"]["companion_fact_missing_in"] == ["AGENTS.override.md"]


def test_blocks_open_problem_claim_once_a_problem_stops_being_open(
    tmp_path: Path,
) -> None:
    """A solved problem must not leave "N open problems" standing anywhere.

    This is the direction that would embarrass the project rather than merely
    age: prose asserting a problem is open after the registry says otherwise.
    The validator refuses to spell a phrase it can no longer support.
    """
    root = _fixture_root(tmp_path)
    snapshot_path = root / "docs/lean_companion_snapshot.json"
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    payload["problem_inventory"]["all_open"] = False
    payload["problem_inventory"]["observed_statuses"] = ["open", "resolved"]
    snapshot_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt = validate_lean_companion_snapshot(root)
    assert receipt["status"] == "blocked"
    assert "LEAN_COMPANION_PROBLEM_INVENTORY_INVALID" in {
        row["code"] for row in receipt["errors"]
    }


def test_problem_inventory_tracks_the_companion_registry(tmp_path: Path) -> None:
    upstream_root = _companion_checkout()
    if not (upstream_root / ".git").exists():
        return
    root = _fixture_root(tmp_path)
    snapshot_path = root / "docs/lean_companion_snapshot.json"
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    payload["problem_inventory"]["problem_count"] += 1
    snapshot_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt = validate_lean_companion_snapshot(root, upstream_root=upstream_root)
    assert receipt["status"] == "blocked"
    assert "LEAN_COMPANION_PROBLEM_INVENTORY_DRIFT" in {
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
    upstream_root = _companion_checkout()
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
