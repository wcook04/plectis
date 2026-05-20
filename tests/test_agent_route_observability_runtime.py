from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.agent_route_observability_runtime import (
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    run,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
OBS_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime/input"


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


def _field_floor() -> dict[str, list[str]]:
    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/agent_route_observability_runtime.fixture_manifest.json"
        ).read_text(encoding="utf-8")
    )
    return manifest["validator_contract_ratchet_v1"]["per_output_receipt_field_floor"]


def test_agent_route_observability_runtime_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    live_receipt_dir = MICROCOSM_ROOT / "receipts/first_wave/agent_route_observability_runtime"
    before = {
        path.name: path.read_text(encoding="utf-8")
        for path in live_receipt_dir.glob("*.json")
    } if live_receipt_dir.exists() else {}
    result = run(OBS_FIXTURE_INPUT, tmp_path / "receipts", command="pytest")

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert all(not Path(path).is_absolute() for path in result["receipt_paths"])
    assert result["route_compliance"]["actor_axis_mismatch_count"] == 1
    assert result["route_compliance"]["authority_rejection_count"] == 1
    assert result["route_lease_mode_control"]["kernel_bloat_before_direct_action_count"] == 1
    assert result["route_lease_mode_control"]["static_metadata_without_trace_feedback_count"] == 1
    assert result["debt_retirement"]["debt_retirement_count"] == 1
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]
    after = {
        path.name: path.read_text(encoding="utf-8")
        for path in live_receipt_dir.glob("*.json")
    } if live_receipt_dir.exists() else {}
    assert after == before


def test_agent_route_observability_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        public_root / "fixtures/first_wave/agent_route_observability_runtime",
    )

    result = run(
        public_root / "fixtures/first_wave/agent_route_observability_runtime/input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == EXPECTED_RECEIPT_PATHS
    for receipt_path in EXPECTED_RECEIPT_PATHS:
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "/private/var" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
        assert payload["missing_negative_cases"] == []
        assert set(payload["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
        for hit in payload["private_state_scan"]["hits"]:
            assert hit["body_redacted"] is True
            assert not Path(hit["path"]).is_absolute()


def test_agent_route_observability_receipts_satisfy_macro_field_floor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/agent_route_observability_runtime",
        public_root / "fixtures/first_wave/agent_route_observability_runtime",
    )
    run(
        public_root / "fixtures/first_wave/agent_route_observability_runtime/input",
        public_root / "receipts/first_wave/agent_route_observability_runtime",
        command="pytest",
    )

    for receipt_path, required_fields in _field_floor().items():
        payload = json.loads((public_root / receipt_path).read_text(encoding="utf-8"))
        missing = [field for field in required_fields if field not in payload]
        assert missing == []
