from __future__ import annotations

import json
from pathlib import Path

import pytest

from microcosm_core import cold_clone_probe
from microcosm_core.schemas import DuplicateJsonKeyError


def _write_required_inputs(root: Path) -> None:
    for rel_path in cold_clone_probe.REQUIRED_INPUTS:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")


def _write_pattern_receipts(root: Path) -> None:
    for rel_path in cold_clone_probe.PATTERN_RECEIPTS:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")


def _raise_is_file_for(
    monkeypatch: pytest.MonkeyPatch, target: Path, message: str = "metadata unavailable"
) -> None:
    original_is_file = Path.is_file

    def guarded_is_file(path: Path) -> bool:
        if path == target:
            raise OSError(message)
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)


def _raise_exists_for(
    monkeypatch: pytest.MonkeyPatch, target: Path, message: str = "metadata unavailable"
) -> None:
    original_exists = Path.exists

    def guarded_exists(path: Path) -> bool:
        if path == target:
            raise OSError(message)
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", guarded_exists)


def test_cold_clone_probe_reports_secret_exclusion_scan(monkeypatch, tmp_path: Path) -> None:
    _write_required_inputs(tmp_path)
    _write_pattern_receipts(tmp_path)

    def fake_secret_scan(root: Path) -> dict:
        assert root == tmp_path
        return {
            "status": "pass",
            "secret_exclusion_scan": {
                "status": "pass",
                "blocking_hit_count": 0,
                "body_in_receipt": False,
                "real_substrate_default": True,
            },
        }

    def fake_pattern_binding(input_path: Path, out_path: Path, command: str) -> dict:
        assert command == "bootstrap pattern_binding_contract validate"
        assert input_path == tmp_path / "fixtures/first_wave/pattern_binding_contract/input"
        assert out_path != tmp_path / "receipts/first_wave/pattern_binding_contract"
        return {"status": "pass"}

    monkeypatch.setattr(cold_clone_probe, "validate_secret_exclusion_scan", fake_secret_scan)
    monkeypatch.setattr(cold_clone_probe, "validate_pattern_binding", fake_pattern_binding)

    receipt = cold_clone_probe.run_probe(tmp_path, emit_ref="receipts/custom_cold_clone.json")

    assert receipt["status"] == "pass"
    assert (
        receipt["command"]
        == "./bootstrap.sh --suite first-wave --emit receipts/custom_cold_clone.json"
    )
    assert receipt["suite"] == "first-wave"
    assert receipt["fixture_id"] == "first-wave"
    assert receipt["emit_ref"] == "receipts/custom_cold_clone.json"
    assert receipt["receipt_paths"][0] == "receipts/custom_cold_clone.json"
    assert receipt["secret_exclusion_scan"]["status"] == "pass"
    assert receipt["secret_exclusion_scan"]["body_in_receipt"] is False
    assert receipt["private_state_scan"]["compatibility_alias_for"] == "secret_exclusion_scan"
    assert receipt["private_state_scan"]["status"] == "pass"


def test_cold_clone_probe_default_emit_uses_ignored_local_state(
    monkeypatch, tmp_path: Path
) -> None:
    _write_required_inputs(tmp_path)
    _write_pattern_receipts(tmp_path)

    def fake_secret_scan(root: Path) -> dict:
        assert root == tmp_path
        return {
            "status": "pass",
            "secret_exclusion_scan": {
                "status": "pass",
                "blocking_hit_count": 0,
                "body_in_receipt": False,
            },
        }

    def fake_pattern_binding(input_path: Path, out_path: Path, command: str) -> dict:
        assert input_path == tmp_path / "fixtures/first_wave/pattern_binding_contract/input"
        assert out_path == tmp_path / ".microcosm/cold_clone_probe/pattern_binding_contract"
        assert command == "bootstrap pattern_binding_contract validate"
        return {"status": "pass"}

    monkeypatch.setattr(cold_clone_probe, "validate_secret_exclusion_scan", fake_secret_scan)
    monkeypatch.setattr(cold_clone_probe, "validate_pattern_binding", fake_pattern_binding)

    receipt = cold_clone_probe.run_probe(tmp_path)

    assert receipt["status"] == "pass"
    assert receipt["emit_ref"] == ".microcosm/cold_clone_probe.json"
    assert receipt["receipt_paths"][0] == ".microcosm/cold_clone_probe.json"
    assert receipt["command"] == (
        "./bootstrap.sh --suite first-wave --emit .microcosm/cold_clone_probe.json"
    )
    assert "receipts/cold_clone_probe.json" not in receipt["command"]


def test_cold_clone_probe_blocks_unknown_suite_before_validation(
    monkeypatch, tmp_path: Path
) -> None:
    def unexpected_secret_scan(root: Path) -> dict:
        raise AssertionError("secret scan must not run for an unknown suite")

    def unexpected_pattern_binding(input_path: Path, out_path: Path, command: str) -> dict:
        raise AssertionError("pattern binding must not run for an unknown suite")

    monkeypatch.setattr(cold_clone_probe, "validate_secret_exclusion_scan", unexpected_secret_scan)
    monkeypatch.setattr(cold_clone_probe, "validate_pattern_binding", unexpected_pattern_binding)

    receipt = cold_clone_probe.run_probe(tmp_path, suite="missing-suite")

    assert receipt["status"] == "blocked_invalid_input"
    assert receipt["suite"] == "missing-suite"
    assert receipt["fixture_id"] == "missing-suite"
    assert receipt["blocked_dependency_codes"] == ["UNKNOWN_COLD_CLONE_SUITE"]
    assert receipt["supported_suites"] == ["first-wave"]


def test_cold_clone_probe_treats_unreadable_required_metadata_as_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _write_required_inputs(tmp_path)
    unreadable_ref = cold_clone_probe.REQUIRED_INPUTS[0]
    _raise_is_file_for(monkeypatch, tmp_path / unreadable_ref)

    def unexpected_secret_scan(root: Path) -> dict:
        raise AssertionError("secret scan must not run when required inputs are missing")

    def unexpected_pattern_binding(input_path: Path, out_path: Path, command: str) -> dict:
        raise AssertionError("pattern binding must not run when required inputs are missing")

    monkeypatch.setattr(cold_clone_probe, "validate_secret_exclusion_scan", unexpected_secret_scan)
    monkeypatch.setattr(cold_clone_probe, "validate_pattern_binding", unexpected_pattern_binding)

    receipt = cold_clone_probe.run_probe(tmp_path)

    assert receipt["status"] == "blocked_dependency_missing"
    assert receipt["blocked_dependency_codes"] == ["MISSING_FIXTURE_INPUT"]
    assert receipt["missing_inputs"] == [unreadable_ref]
    assert "error" not in receipt


def test_cold_clone_probe_mirrors_generated_pattern_receipts(
    monkeypatch, tmp_path: Path
) -> None:
    _write_required_inputs(tmp_path)

    def fake_secret_scan(root: Path) -> dict:
        assert root == tmp_path
        return {
            "status": "pass",
            "secret_exclusion_scan": {
                "status": "pass",
                "blocking_hit_count": 0,
                "body_in_receipt": False,
            },
        }

    def fake_pattern_binding(input_path: Path, out_path: Path, command: str) -> dict:
        assert input_path == tmp_path / "fixtures/first_wave/pattern_binding_contract/input"
        assert out_path == tmp_path / ".microcosm/cold_clone_probe/pattern_binding_contract"
        for receipt_ref in cold_clone_probe.PATTERN_RECEIPTS:
            receipt_path = out_path / Path(receipt_ref).name
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text(
                json.dumps(
                    {
                        "status": "pass",
                        "source": "fresh_cold_clone_probe",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        return {"status": "pass"}

    monkeypatch.setattr(cold_clone_probe, "validate_secret_exclusion_scan", fake_secret_scan)
    monkeypatch.setattr(cold_clone_probe, "validate_pattern_binding", fake_pattern_binding)

    receipt = cold_clone_probe.run_probe(tmp_path, emit_ref="receipts/cold_clone_probe.json")

    assert receipt["status"] == "pass"
    assert receipt["receipt_paths"] == [
        "receipts/cold_clone_probe.json",
        *cold_clone_probe.PATTERN_RECEIPTS,
    ]
    for receipt_ref in cold_clone_probe.PATTERN_RECEIPTS:
        assert (tmp_path / receipt_ref).is_file()
    validation_payload = json.loads(
        (
            tmp_path
            / "receipts/first_wave/pattern_binding_contract/pattern_binding_validation_result.json"
        ).read_text(encoding="utf-8")
    )
    assert validation_payload["receipt_paths"] == cold_clone_probe.PATTERN_RECEIPTS


def test_cold_clone_probe_mirrors_receipts_when_destination_exists_probe_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _write_required_inputs(tmp_path)
    unreadable_ref = "receipts/first_wave/pattern_binding_contract/source_capsules.json"
    unreadable_destination = tmp_path / unreadable_ref
    _raise_exists_for(monkeypatch, unreadable_destination)

    def fake_secret_scan(root: Path) -> dict:
        assert root == tmp_path
        return {
            "status": "pass",
            "secret_exclusion_scan": {
                "status": "pass",
                "blocking_hit_count": 0,
                "body_in_receipt": False,
            },
        }

    def fake_pattern_binding(input_path: Path, out_path: Path, command: str) -> dict:
        assert input_path == tmp_path / "fixtures/first_wave/pattern_binding_contract/input"
        assert out_path == tmp_path / ".microcosm/cold_clone_probe/pattern_binding_contract"
        for receipt_ref in cold_clone_probe.PATTERN_RECEIPTS:
            receipt_path = out_path / Path(receipt_ref).name
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text('{"status": "pass"}\n', encoding="utf-8")
        return {"status": "pass"}

    monkeypatch.setattr(cold_clone_probe, "validate_secret_exclusion_scan", fake_secret_scan)
    monkeypatch.setattr(cold_clone_probe, "validate_pattern_binding", fake_pattern_binding)

    receipt = cold_clone_probe.run_probe(tmp_path, emit_ref="receipts/cold_clone_probe.json")

    assert receipt["status"] == "pass"
    assert unreadable_destination.is_file()


def test_cold_clone_probe_skips_unreadable_generated_receipt_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _write_required_inputs(tmp_path)
    unreadable_ref = (
        "receipts/first_wave/pattern_binding_contract/source_capsules.json"
    )
    unreadable_name = Path(unreadable_ref).name

    def fake_secret_scan(root: Path) -> dict:
        assert root == tmp_path
        return {
            "status": "pass",
            "secret_exclusion_scan": {
                "status": "pass",
                "blocking_hit_count": 0,
                "body_in_receipt": False,
            },
        }

    def fake_pattern_binding(input_path: Path, out_path: Path, command: str) -> dict:
        assert input_path == tmp_path / "fixtures/first_wave/pattern_binding_contract/input"
        assert out_path == tmp_path / ".microcosm/cold_clone_probe/pattern_binding_contract"
        for receipt_ref in cold_clone_probe.PATTERN_RECEIPTS:
            receipt_path = out_path / Path(receipt_ref).name
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text('{"status": "pass"}\n', encoding="utf-8")
        _raise_is_file_for(monkeypatch, out_path / unreadable_name)
        return {"status": "pass"}

    monkeypatch.setattr(cold_clone_probe, "validate_secret_exclusion_scan", fake_secret_scan)
    monkeypatch.setattr(cold_clone_probe, "validate_pattern_binding", fake_pattern_binding)

    receipt = cold_clone_probe.run_probe(tmp_path, emit_ref="receipts/cold_clone_probe.json")

    assert receipt["status"] == "blocked_dependency_missing"
    assert receipt["blocked_dependency_codes"] == ["MISSING_PATTERN_BINDING_RECEIPT"]
    assert receipt["missing_receipts"] == [unreadable_ref]
    assert "error" not in receipt


def test_cold_clone_probe_treats_unreadable_mirrored_receipt_as_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _write_required_inputs(tmp_path)
    unreadable_ref = (
        "receipts/first_wave/pattern_binding_contract/source_capsules.json"
    )

    def fake_secret_scan(root: Path) -> dict:
        assert root == tmp_path
        return {
            "status": "pass",
            "secret_exclusion_scan": {
                "status": "pass",
                "blocking_hit_count": 0,
                "body_in_receipt": False,
            },
        }

    def fake_pattern_binding(input_path: Path, out_path: Path, command: str) -> dict:
        assert input_path == tmp_path / "fixtures/first_wave/pattern_binding_contract/input"
        assert out_path == tmp_path / ".microcosm/cold_clone_probe/pattern_binding_contract"
        for receipt_ref in cold_clone_probe.PATTERN_RECEIPTS:
            receipt_path = out_path / Path(receipt_ref).name
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text('{"status": "pass"}\n', encoding="utf-8")
        return {"status": "pass"}

    monkeypatch.setattr(cold_clone_probe, "validate_secret_exclusion_scan", fake_secret_scan)
    monkeypatch.setattr(cold_clone_probe, "validate_pattern_binding", fake_pattern_binding)
    _raise_is_file_for(monkeypatch, tmp_path / unreadable_ref)

    receipt = cold_clone_probe.run_probe(tmp_path, emit_ref="receipts/cold_clone_probe.json")

    assert receipt["status"] == "blocked_dependency_missing"
    assert receipt["blocked_dependency_codes"] == ["MISSING_PATTERN_BINDING_RECEIPT"]
    assert receipt["missing_receipts"] == [unreadable_ref]
    assert "error" not in receipt


def test_cold_clone_probe_rejects_duplicate_keys_in_mirrored_validation_receipt(
    monkeypatch, tmp_path: Path
) -> None:
    _write_required_inputs(tmp_path)

    def fake_secret_scan(root: Path) -> dict:
        assert root == tmp_path
        return {
            "status": "pass",
            "secret_exclusion_scan": {
                "status": "pass",
                "blocking_hit_count": 0,
                "body_in_receipt": False,
            },
        }

    def fake_pattern_binding(input_path: Path, out_path: Path, command: str) -> dict:
        assert input_path == tmp_path / "fixtures/first_wave/pattern_binding_contract/input"
        assert out_path == tmp_path / ".microcosm/cold_clone_probe/pattern_binding_contract"
        for receipt_ref in cold_clone_probe.PATTERN_RECEIPTS:
            receipt_path = out_path / Path(receipt_ref).name
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            if receipt_path.name == "pattern_binding_validation_result.json":
                receipt_path.write_text(
                    '{"status": "pass", "status": "shadowed"}\n',
                    encoding="utf-8",
                )
            else:
                receipt_path.write_text('{"status": "pass"}\n', encoding="utf-8")
        return {"status": "pass"}

    monkeypatch.setattr(cold_clone_probe, "validate_secret_exclusion_scan", fake_secret_scan)
    monkeypatch.setattr(cold_clone_probe, "validate_pattern_binding", fake_pattern_binding)

    with pytest.raises(DuplicateJsonKeyError):
        cold_clone_probe.run_probe(tmp_path, emit_ref="receipts/cold_clone_probe.json")


def test_cold_clone_probe_blocks_on_secret_exclusion_scan(monkeypatch, tmp_path: Path) -> None:
    _write_required_inputs(tmp_path)

    def fake_secret_scan(root: Path) -> dict:
        assert root == tmp_path
        return {
            "status": "blocked_private",
            "secret_exclusion_scan": {
                "status": "blocked_private",
                "blocking_hit_count": 1,
                "body_in_receipt": False,
            },
        }

    def unexpected_pattern_binding(input_path: Path, out_path: Path, command: str) -> dict:
        raise AssertionError("pattern binding must not run after a blocked secret scan")

    monkeypatch.setattr(cold_clone_probe, "validate_secret_exclusion_scan", fake_secret_scan)
    monkeypatch.setattr(
        cold_clone_probe,
        "validate_pattern_binding",
        unexpected_pattern_binding,
    )

    receipt = cold_clone_probe.run_probe(tmp_path)

    assert receipt["status"] == "blocked_secret_exclusion"
    assert receipt["blocked_dependency_codes"] == ["SECRET_EXCLUSION_SCAN_BLOCKED"]
    assert receipt["secret_exclusion_scan"]["blocking_hit_count"] == 1
    assert receipt["private_state_scan"]["compatibility_alias_for"] == "secret_exclusion_scan"
