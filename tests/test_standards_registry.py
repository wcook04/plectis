from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.validators.standards_registry import validate_standards_registry


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def _copy_public_standards_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "standards", public_root / "standards")
    return public_root


def test_standards_registry_validation_passes_and_is_redacted(tmp_path: Path) -> None:
    public_root = _copy_public_standards_tree(tmp_path)
    out = public_root / "receipts/first_wave/standards_registry_validation.json"

    receipt = validate_standards_registry(
        public_root / "core/standards_registry.json",
        public_root / "standards",
        public_root / "core/acceptance/first_wave_acceptance.json",
        out,
        command="pytest",
    )

    assert receipt["status"] == "pass"
    assert receipt["standard_count"] == 51
    assert receipt["checked_standard_count"] == 51
    assert receipt["duplicate_standard_ids"] == []
    assert receipt["missing_standard_files"] == []
    assert receipt["missing_required_fields_by_standard"] == {}
    assert receipt["acceptance_status"]["lean_lake_authorized"] is False
    assert receipt["acceptance_status"]["release_authorized"] is False
    assert receipt["private_state_scan"]["blocking_hit_count"] == 0
    assert receipt["private_state_scan"]["body_redacted"] is True
    text = out.read_text(encoding="utf-8")
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(receipt)
    assert "body" not in _walk_keys(receipt)


def test_standards_registry_rejects_duplicate_standard_ids(tmp_path: Path) -> None:
    public_root = _copy_public_standards_tree(tmp_path)
    registry_path = public_root / "core/standards_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["standards"].append(dict(registry["standards"][0]))
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    receipt = validate_standards_registry(
        registry_path,
        public_root / "standards",
        public_root / "core/acceptance/first_wave_acceptance.json",
        public_root / "receipts/first_wave/standards_registry_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert registry["standards"][0]["standard_id"] in receipt["duplicate_standard_ids"]
