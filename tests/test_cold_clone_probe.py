from __future__ import annotations

from pathlib import Path

from microcosm_core import cold_clone_probe


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
    assert receipt["emit_ref"] == "receipts/custom_cold_clone.json"
    assert receipt["receipt_paths"][0] == "receipts/custom_cold_clone.json"
    assert receipt["secret_exclusion_scan"]["status"] == "pass"
    assert receipt["secret_exclusion_scan"]["body_in_receipt"] is False
    assert receipt["private_state_scan"]["compatibility_alias_for"] == "secret_exclusion_scan"
    assert receipt["private_state_scan"]["status"] == "pass"


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
