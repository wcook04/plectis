from __future__ import annotations

from pathlib import Path

import pytest

from microcosm_core.fixture_registry import (
    load_pattern_binding_fixture,
    load_pattern_binding_substrate_bundle,
)


def _write_pattern_binding_fixture(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "patterns": root / "patterns.jsonl",
        "source_capsules": root / "source_capsules.json",
        "forbidden_terms": root / "private_state_forbidden_terms.json",
    }
    paths["patterns"].write_text('{"pattern_id": "p1"}\n', encoding="utf-8")
    paths["source_capsules"].write_text("[]\n", encoding="utf-8")
    paths["forbidden_terms"].write_text("[]\n", encoding="utf-8")
    return paths


def _write_substrate_bundle_fixture(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "bundle_manifest": root / "bundle_manifest.json",
        "patterns": root / "pattern_rows.jsonl",
        "source_capsules": root / "source_capsules.json",
        "forbidden_terms": root / "private_state_forbidden_terms.json",
        "authority_chain_handles": root / "authority_chain_handles.json",
        "reference_capsules": root / "reference_capsules.json",
        "omission_receipts": root / "omission_receipts.json",
    }
    paths["bundle_manifest"].write_text("{}\n", encoding="utf-8")
    paths["patterns"].write_text('{"pattern_id": "p1"}\n', encoding="utf-8")
    for key in (
        "source_capsules",
        "forbidden_terms",
        "authority_chain_handles",
        "reference_capsules",
        "omission_receipts",
    ):
        paths[key].write_text("[]\n", encoding="utf-8")
    return paths


def _raise_is_file_for(
    monkeypatch: pytest.MonkeyPatch, target: Path, message: str = "metadata unavailable"
) -> None:
    original_is_file = Path.is_file

    def guarded_is_file(path: Path) -> bool:
        if path == target:
            raise OSError(message)
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)


def test_pattern_binding_fixture_treats_unreadable_required_metadata_as_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _write_pattern_binding_fixture(tmp_path)
    _raise_is_file_for(monkeypatch, paths["patterns"])

    with pytest.raises(FileNotFoundError) as excinfo:
        load_pattern_binding_fixture(tmp_path)

    message = str(excinfo.value)
    assert "missing pattern-binding fixture input(s)" in message
    assert paths["patterns"].as_posix() in message
    assert "metadata unavailable" not in message


def test_pattern_binding_fixture_skips_unreadable_optional_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pattern_binding_fixture(tmp_path)
    optional_path = tmp_path / "duplicate_pattern_id_conflict.jsonl"
    optional_path.write_text('{"pattern_id": "p1"}\n', encoding="utf-8")
    _raise_is_file_for(monkeypatch, optional_path)

    payload = load_pattern_binding_fixture(tmp_path)

    assert payload["patterns"] == [{"pattern_id": "p1"}]
    assert "duplicate_patterns" not in payload
    assert "duplicate_patterns" not in payload["input_paths"]


def test_pattern_binding_substrate_bundle_treats_unreadable_required_metadata_as_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _write_substrate_bundle_fixture(tmp_path)
    _raise_is_file_for(monkeypatch, paths["patterns"])

    with pytest.raises(FileNotFoundError) as excinfo:
        load_pattern_binding_substrate_bundle(tmp_path)

    message = str(excinfo.value)
    assert "missing pattern-binding substrate bundle input(s)" in message
    assert paths["patterns"].as_posix() in message
    assert "metadata unavailable" not in message
