from __future__ import annotations

import json
import shutil
from pathlib import Path

from microcosm_core.validators.fixture_freshness import run_fixture_freshness


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_SUPPORT = MICROCOSM_ROOT / "core/preflight_support"
READINESS = PREFLIGHT_SUPPORT / "organ_fixture_validator_readiness_v1.json"
NEGATIVE_MATRIX = PREFLIGHT_SUPPORT / "fixture_negative_case_matrix_v1.json"
MISSION_DAG = PREFLIGHT_SUPPORT / "microcosm_rebuild_mission_graph_v1.json"
RECEIPT_COVERAGE = PREFLIGHT_SUPPORT / "validator_receipt_coverage_map_v1.json"


def _copy_public_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "fixtures", public_root / "fixtures")
    shutil.copytree(MICROCOSM_ROOT / "receipts", public_root / "receipts")
    return public_root


def test_first_wave_acceptance_plan_keeps_deferred_boundaries() -> None:
    acceptance = json.loads(
        (MICROCOSM_ROOT / "core/acceptance/first_wave_acceptance.json").read_text(
            encoding="utf-8"
        )
    )

    assert acceptance["status"] == "accepted_runtime_spine_lean_deferred"
    assert len(acceptance["accepted_current_authority_organs"]) == 7
    assert {row["organ_id"] for row in acceptance["deferred_organs"]} == {
        "formal_math_lean_proof_witness"
    }
    assert acceptance["lean_lake_authorized"] is False
    assert acceptance["release_authorized"] is False
    assert acceptance["hosted_public_authorized"] is False
    assert acceptance["publication_authorized"] is False
    assert acceptance["recipient_work_authorized"] is False
    assert acceptance["provider_calls_authorized"] is False
    assert acceptance["private_data_equivalence_authorized"] is False


def test_acceptance_summary_records_runtime_spine_without_lean_authority(tmp_path: Path) -> None:
    public_root = _copy_public_tree(tmp_path)
    run_fixture_freshness(
        READINESS,
        NEGATIVE_MATRIX,
        MISSION_DAG,
        RECEIPT_COVERAGE,
        public_root / "receipts/preflight/fixture_runner_freshness.json",
        command="pytest",
    )
    summary = json.loads(
        (public_root / "receipts/first_wave/acceptance_summary.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["status"] == "pass"
    assert summary["accepted_current_authority_organs"] == [
        "pattern_binding_contract",
        "executable_doctrine_grammar",
        "proof_diagnostic_evidence_spine",
        "navigation_hologram_route_plane",
        "mission_transaction_work_spine",
        "agent_route_observability_runtime",
        "pattern_assimilation_step",
    ]
    assert summary["deferred_organs"] == ["formal_math_lean_proof_witness"]
    assert summary["lean_lake_authorized"] is False
    assert summary["release_authorized"] is False
    assert summary["private_data_equivalence_authorized"] is False
