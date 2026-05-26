from __future__ import annotations

import json
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_organ_registry_denies_status_and_count_overread() -> None:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    ceiling = registry["authority_ceiling"]
    denied = ceiling["denied_authority"]

    assert registry["anti_claim"].startswith(
        "Organ registry rows are public runtime authority metadata"
    )
    assert ceiling["registry_authority"] == (
        "public_runtime_target_inventory_and_receipt_index_only"
    )
    assert "accepted_current_authority" in ceiling["reader_action"]
    assert "organ counts" in ceiling["reader_action"]
    assert denied["accepted_current_authority_is_product_progress"] is False
    assert denied["adapter_backed_count_is_product_completeness"] is False
    assert denied["complete_secret_detection_claim"] is False
    assert denied["generated_receipt_count_is_proof"] is False
    assert denied["organ_count_is_release_readiness"] is False
    assert denied["private_data_equivalence_claim"] is False
    assert denied["product_completeness_claim"] is False
    assert denied["proof_correctness_claim"] is False
    assert denied["provider_calls_authorized"] is False
    assert denied["release_authorized"] is False
    assert denied["score_based_progress_authority"] is False
    assert denied["source_mutation_authorized"] is False
    assert denied["whole_system_correctness_claim"] is False
    assert "product completeness" in ceiling["registry_cannot_claim"]
    assert "private_root_equivalence" in ceiling["registry_cannot_claim"]
    assert "score_based_progress_authority" in ceiling["registry_cannot_claim"]
    assert any(
        "accepted_current_authority names current public receipts only" in guard
        for guard in ceiling["overread_guard"]
    )
    assert any(
        "organ counts and adapter-backed counts are inventory fields" in guard
        for guard in ceiling["overread_guard"]
    )
