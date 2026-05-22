from __future__ import annotations

import copy
import shutil
from pathlib import Path

from microcosm_core import release_claim_projection


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _copy_projection_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "fixtures", public_root / "fixtures")
    shutil.copytree(MICROCOSM_ROOT / "receipts", public_root / "receipts")
    shutil.copytree(MICROCOSM_ROOT / "src", public_root / "src")
    shutil.copytree(MICROCOSM_ROOT / "standards", public_root / "standards")
    shutil.copytree(MICROCOSM_ROOT / "examples", public_root / "examples")
    shutil.copytree(MICROCOSM_ROOT / "tests", public_root / "tests")
    shutil.copy2(MICROCOSM_ROOT / "README.md", public_root / "README.md")
    shutil.copy2(MICROCOSM_ROOT / "pyproject.toml", public_root / "pyproject.toml")
    return public_root


def test_release_claim_cards_validate_and_readme_projection_is_current() -> None:
    receipt = release_claim_projection.build_receipt(MICROCOSM_ROOT, check_readme=True)

    assert receipt["status"] == "pass"
    assert receipt["claim_registry"]["status"] == "pass"
    assert receipt["claim_registry"]["claim_card_count"] >= 5
    assert receipt["claim_registry"]["readme_rendered_claim_count"] >= 5
    assert receipt["readme_projection"]["status"] == "pass"
    assert receipt["readme_projection"]["matches_projection"] is True
    assert receipt["claim_registry"]["blocking_codes"] == []


def test_release_claim_projection_blocks_schema_only_capability_upgrade(tmp_path: Path) -> None:
    public_root = _copy_projection_root(tmp_path)
    registry_path = public_root / release_claim_projection.CLAIM_CARD_REGISTRY_REL
    registry = release_claim_projection.load_claim_registry(public_root)
    mutated = copy.deepcopy(registry)
    for row in mutated["claim_cards"]:
        if row["claim_id"] == "schema_replay_boundary":
            row["render_as_capability"] = True
            row["promotion_rule"] = "May render as live monitoring once accepted."
            break
    registry_path.write_text(
        release_claim_projection_json(mutated),
        encoding="utf-8",
    )

    receipt = release_claim_projection.validate_claim_registry(public_root)

    assert receipt["status"] == "blocked"
    assert "SCHEMA_ONLY_RENDER_CAPABILITY_FORBIDDEN" in receipt["blocking_codes"]
    assert "SCHEMA_ONLY_CAPABILITY_LANGUAGE_FORBIDDEN" in receipt["blocking_codes"]


def test_release_claim_projection_blocks_readme_drift(tmp_path: Path) -> None:
    public_root = _copy_projection_root(tmp_path)
    readme_path = public_root / "README.md"
    readme_path.write_text(
        readme_path.read_text(encoding="utf-8").replace(
            "Local project substrate",
            "Hand-edited local project substrate",
            1,
        ),
        encoding="utf-8",
    )

    status = release_claim_projection.readme_projection_status(public_root)

    assert status["status"] == "blocked"
    assert status["matches_projection"] is False
    assert status["findings"][0]["error_code"] == "README_PROJECTION_DRIFT"


def release_claim_projection_json(payload: dict) -> str:
    import json

    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
