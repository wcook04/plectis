from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.validators.fixture_freshness import run_fixture_freshness


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_SUPPORT = MICROCOSM_ROOT / "core/preflight_support"
READINESS = PREFLIGHT_SUPPORT / "organ_fixture_validator_readiness_v1.json"
NEGATIVE_MATRIX = PREFLIGHT_SUPPORT / "fixture_negative_case_matrix_v1.json"
MISSION_DAG = PREFLIGHT_SUPPORT / "microcosm_rebuild_mission_graph_v1.json"
RECEIPT_COVERAGE = PREFLIGHT_SUPPORT / "validator_receipt_coverage_map_v1.json"


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


def _copy_public_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "fixtures", public_root / "fixtures")
    shutil.copytree(MICROCOSM_ROOT / "receipts", public_root / "receipts")
    return public_root


def test_fixture_freshness_passes_and_emits_acceptance_summary(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    out = public_root / "receipts/preflight/fixture_runner_freshness.json"

    receipt = run_fixture_freshness(
        READINESS,
        NEGATIVE_MATRIX,
        MISSION_DAG,
        RECEIPT_COVERAGE,
        out,
        command="pytest",
    )

    summary_path = public_root / "receipts/first_wave/acceptance_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "pass"
    assert receipt["stale_receipt_count"] == 0
    assert receipt["stale_receipt_codes"] == []
    assert receipt["acceptance_summary_receipt"] == "receipts/first_wave/acceptance_summary.json"
    assert receipt["private_state_scan"]["body_redacted"] is True
    assert receipt["private_state_scan"]["blocking_hit_count"] == 0
    assert summary["status"] == "pass"
    assert summary["accepted_count"] == 46
    assert summary["truth_accounting"]["real_substrate_progress_count"] == 36
    assert summary["truth_accounting"]["non_progress_accepted_count"] == 10
    assert summary["truth_accounting"]["real_import_validation_count"] == 16
    assert summary["truth_accounting"]["regression_negative_fixture_count"] == 10
    assert summary["truth_accounting"]["evidence_class_counts"] == {
        "algorithmic_projection": 17,
        "external_subprocess_witness": 3,
        "fixture_echo_smoke": 10,
        "semantic_validator": 16,
    }
    assert summary["lean_lake_authorized"] == "bounded_public_witness_only"
    assert summary["release_authorized"] is False
    assert summary["provider_calls_authorized"] is False
    assert summary["trading_or_financial_advice_authorized"] is False
    assert "receipts/preflight/dependency_preflight.json" in summary["preflight_receipts"]

    for path in (out, summary_path):
        text = path.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(receipt)
    assert "body" not in _walk_keys(receipt)
    assert "matched_excerpt" not in _walk_keys(summary)
    assert "body" not in _walk_keys(summary)


def test_fixture_freshness_blocks_missing_command_receipt(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    missing = public_root / "receipts/first_wave/navigation_hologram_route_plane/route_lease.json"
    missing.unlink()

    receipt = run_fixture_freshness(
        READINESS,
        NEGATIVE_MATRIX,
        MISSION_DAG,
        RECEIPT_COVERAGE,
        public_root / "receipts/preflight/fixture_runner_freshness.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert receipt["stale_receipt_count"] == 1
    assert receipt["stale_receipt_codes"] == [
        "MISSING_RECEIPT:receipts/first_wave/navigation_hologram_route_plane/route_lease.json"
    ]
