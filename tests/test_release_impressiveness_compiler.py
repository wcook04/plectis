from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

from microcosm_core import release_impressiveness_compiler


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _copy_compiler_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    for name in ("core", "examples", "receipts"):
        shutil.copytree(MICROCOSM_ROOT / name, public_root / name)
    shutil.copy2(MICROCOSM_ROOT / "pyproject.toml", public_root / "pyproject.toml")
    return public_root


def test_release_impressiveness_compiler_emits_flagship_transfer_cards() -> None:
    receipt = release_impressiveness_compiler.build_receipt(MICROCOSM_ROOT)

    assert receipt["status"] == "pass"
    assert receipt["transfer_status"] == "pass"
    assert receipt["dependency_preflight_gate_status"] == "pass"
    assert receipt["capability_transfer_card_count"] == 6
    assert receipt["selected_pattern_count"] == 23
    assert receipt["authority_ceiling"]["release_authorized"] is False
    assert receipt["authority_ceiling"]["private_data_equivalence_claim"] is False
    assert {card["lane_id"] for card in receipt["capability_transfer_cards"]} == {
        "proof_formal_kernel",
        "prover_evaluator_lab",
        "work_landing_governance",
        "navigation_option_surface",
        "pattern_doctrine_compiler",
        "observatory_provenance_diagnostics",
    }
    assert all(
        card["transfer_status"] == "pass"
        and card["product_surface_status"] == "pass"
        and card["runtime_surface_refs"]
        and card["release_artifact_refs"]
        and card["validation_refs"]
        for card in receipt["capability_transfer_cards"]
    )


def test_release_impressiveness_compiler_reports_claim_card_coverage() -> None:
    receipt = release_impressiveness_compiler.build_receipt(MICROCOSM_ROOT)

    assert receipt["claim_card_coverage_status"] == "pass"
    assert receipt["lane_specific_claim_coverage_status"] == "pass"
    assert receipt["release_grade_claim_binding_status"] == "pass"
    assert receipt["claim_card_coverage"]["covered_lane_count"] == 6
    assert receipt["lane_specific_claim_coverage"]["covered_lane_count"] == 6
    assert receipt["lane_specific_claim_coverage"]["broad_only_lane_ids"] == []
    for card in receipt["capability_transfer_cards"]:
        assert "macro_pattern_import_membrane" in card["linked_claim_card_ids"]
        assert card["lane_specific_claim_coverage_status"] == "pass"
        assert card["lane_specific_claim_card_ids"]
        assert card["global_claim_card_ids"]


def test_release_impressiveness_compiler_demotes_hollow_lane(tmp_path: Path) -> None:
    public_root = _copy_compiler_root(tmp_path)
    tranche_path = (
        public_root
        / release_impressiveness_compiler.FLAGSHIP_TRANCHE_REL
    )
    payload = json.loads(tranche_path.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["lanes"][0]["runtime_surface_refs"] = []
    tranche_path.write_text(
        json.dumps(mutated, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    receipt = release_impressiveness_compiler.build_receipt(public_root)
    first_card = receipt["capability_transfer_cards"][0]

    assert receipt["status"] == "blocked"
    assert receipt["transfer_status"] == "blocked"
    assert first_card["product_surface_status"] == "blocked"
    assert first_card["blockers"][0]["error_code"] == (
        "CAPABILITY_TRANSFER_RUNTIME_SURFACE_MISSING"
    )
    assert "metadata-only" in first_card["demotion_rule"]


def test_release_impressiveness_compiler_blocks_broad_only_claim_coverage(
    tmp_path: Path,
) -> None:
    public_root = _copy_compiler_root(tmp_path)
    registry_path = (
        public_root
        / release_impressiveness_compiler.CLAIM_CARD_REGISTRY_REL
    )
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["claim_cards"] = [
        row
        for row in mutated["claim_cards"]
        if not row.get("lane_refs")
        and not row.get("capability_refs")
        and not row.get("selected_pattern_refs")
    ]
    registry_path.write_text(
        json.dumps(mutated, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    receipt = release_impressiveness_compiler.build_receipt(
        public_root,
        require_claim_card_coverage=True,
    )

    assert receipt["claim_card_coverage_status"] == "pass"
    assert receipt["lane_specific_claim_coverage_status"] == "partial"
    assert receipt["release_grade_claim_binding_status"] == "partial"
    assert receipt["status"] == "blocked"
    assert release_impressiveness_compiler.LANE_SPECIFIC_COVERAGE_BLOCK_CODE in (
        receipt["blocking_codes"]
    )
    assert set(receipt["lane_specific_claim_coverage"]["broad_only_lane_ids"]) == {
        "proof_formal_kernel",
        "prover_evaluator_lab",
        "work_landing_governance",
        "navigation_option_surface",
        "pattern_doctrine_compiler",
        "observatory_provenance_diagnostics",
    }
