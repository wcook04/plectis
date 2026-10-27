from __future__ import annotations

import json
from pathlib import Path

from microcosm_core.component_descriptions import load_description_atlas
from microcosm_core.projections.organ_atlas import NEGATION_CUES, load_model


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


def test_organ_registry_projects_per_organ_evidence_strength() -> None:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    evidence_registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_evidence_classes.json").read_text(
            encoding="utf-8"
        )
    )
    class_profiles = evidence_registry["class_profiles"]
    evidence_by_id = {
        row["organ_id"]: row for row in evidence_registry["organ_evidence_classes"]
    }
    # Registry claims remain normative. Capsule compression owns the public
    # restatement; the derived atlas view preserves its compatibility key.
    atlas_by_id = {row["organ_id"]: row for row in load_description_atlas(MICROCOSM_ROOT)["organs"]}
    capsules = json.loads((MICROCOSM_ROOT / "core/paper_module_capsules.json").read_text(encoding="utf-8"))
    capsule_by_id = {row["id"]: row for row in capsules["paper_modules"]}
    model_cards = {card["organ_id"]: card for family in load_model(MICROCOSM_ROOT)["families"]
                   for card in family["cards"]}

    rows = registry["implemented_organs"]
    assert registry["evidence_class_registry"] == {
        "schema_version": "organ_registry_evidence_class_projection_v1",
        "source_ref": "core/organ_evidence_classes.json",
        "registry_id": "microcosm_organ_evidence_classes",
        "fail_closed_no_default": True,
        "organ_evidence_class_count": len(evidence_by_id),
        "class_profile_count": len(class_profiles),
        "reader_action": (
            "Read accepted_current_authority together with each row evidence_class, "
            "claim_ceiling, and truth_accounting_bucket; status alone is receipt "
            "inventory, not evidence strength."
        ),
        "row_fields_projected": [
            "evidence_class",
            "evidence_profile_ref",
            "evidence_strength_rank",
            "claim_ceiling",
            "truth_accounting_bucket",
            "counts_as_real_substrate_progress",
            "classification_basis",
        ],
    }
    assert len(rows) == len(evidence_by_id)
    assert {row["organ_id"] for row in rows} == set(evidence_by_id)

    evidence_classes = {row["evidence_class"] for row in rows}
    assert len(evidence_classes) > 1
    assert "fixture_echo_smoke" not in evidence_classes
    assert "fixture_schema_replay" not in evidence_classes
    assert "semantic_validator" in evidence_classes
    assert all(
        class_profiles[evidence_class]["counts_as_real_substrate_progress"] is True
        for evidence_class in evidence_classes
    )

    for row in rows:
        evidence_row = evidence_by_id[row["organ_id"]]
        profile = class_profiles[evidence_row["evidence_class"]]

        assert row["status"] == "accepted_current_authority"
        assert row["evidence_class"] == evidence_row["evidence_class"]
        assert row["evidence_profile_ref"] == (
            "core/organ_evidence_classes.json::"
            f"organ_evidence_classes[{row['organ_id']}]"
        )
        assert row["evidence_strength_rank"] == profile["evidence_strength_rank"]
        # Keep the normative registry ceiling exact in the actual public
        # model, separately from the canonical descriptive restatement.
        registry_ceiling = row["claim_ceiling"]
        assert isinstance(registry_ceiling, str) and registry_ceiling.strip()
        assert model_cards[row["organ_id"]]["claim_ceiling"] == registry_ceiling
        assert model_cards[row["organ_id"]]["evidence_class"] == evidence_row["evidence_class"]
        public_row = atlas_by_id[row["organ_id"]]
        public_ceiling = public_row["claim_ceiling_restated"]
        canonical_ceiling = capsule_by_id[public_row["capsule_id"]]["compression"]["authority_ceiling"]
        assert public_ceiling == canonical_ceiling
        assert model_cards[row["organ_id"]]["claim_ceiling_restated"] == canonical_ceiling
        assert isinstance(public_ceiling, str)
        assert len(public_ceiling.strip()) >= 40, (
            f"{row['organ_id']} public ceiling too thin: {public_ceiling!r}"
        )
        ceiling_lower = public_ceiling.lower()
        assert any(
            cue in ceiling_lower
            for cue in NEGATION_CUES
        ), f"{row['organ_id']} public ceiling states no limitation: {public_ceiling!r}"
        assert row["truth_accounting_bucket"] == profile["truth_accounting_bucket"]
        assert (
            row["counts_as_real_substrate_progress"]
            is profile["counts_as_real_substrate_progress"]
        )
        assert row["classification_basis"] == evidence_row["classification_basis"]

    assert any(
        "Every accepted organ row carries evidence_class" in guard
        for guard in registry["authority_ceiling"]["overread_guard"]
    )
    assert (
        "uniform accepted_current_authority without per-organ evidence strength"
        in registry["authority_ceiling"]["registry_cannot_claim"]
    )
