from __future__ import annotations

import json
from pathlib import Path

from microcosm_core.validators.axiom_support_cover import _axiom_verdict, evaluate_axiom_support_cover

MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PILOTED_AXIOMS = {f"AX-{i}" for i in range(1, 13)}


def _evaluate() -> dict:
    return evaluate_axiom_support_cover(MICROCOSM_ROOT)


def test_pilot_axioms_present() -> None:
    result = _evaluate()
    assert set(result["piloted_axioms"]) >= PILOTED_AXIOMS
    for axiom_id in PILOTED_AXIOMS:
        assert axiom_id in result["support_frontiers"]


def test_ax8_partial_is_derived_from_layer_debt_not_hand_stamp() -> None:
    # The payoff: the evaluator REPRODUCES AX-8's partial status from first
    # principles (O1 is layer_debt), rather than trusting the row's hand stamp.
    result = _evaluate()
    ax8 = result["support_frontiers"]["AX-8"]
    assert ax8["verdict"] == "partial_capped_by_layer_debt"
    o1 = next(o for o in ax8["obligations"] if o["obligation_id"] == "AX-8.O1.label_propagation")
    assert o1["computed"] == "layer_debt"
    assert o1["layer_debt_ref"] == "AX8-general-taint-propagation"


def test_ax1_strong_is_not_echoed() -> None:
    # The row hand-stamps AX-1 'strong'; a v0 evaluator must refuse to certify it
    # (no negative-case gate, ordered freshness remains unverified). Echoing the label
    # would be the AP-1 failure the calculus exists to prevent.
    result = _evaluate()
    ax1 = result["support_frontiers"]["AX-1"]
    assert ax1["hand_stamped_witness_strength"] == "strong"
    assert ax1["hand_stamped_strong_not_certifiable"] is True
    assert ax1["verdict"] != "strong"
    assert ax1["verdict"] == "bound_resolved_strength_uncomputable"


def test_no_principle_is_a_witness() -> None:
    # Principles mediate governance; they must never appear on the witness path.
    result = _evaluate()
    assert result["principle_as_witness_violations"] == []


def test_principle_support_is_inherited_and_bounded() -> None:
    result = _evaluate()
    index = {row["principle_id"]: row for row in result["principle_support_index"]}
    principle_standard = json.loads(
        (MICROCOSM_ROOT / "standards/std_microcosm_principle.json").read_text()
    )
    support_contract = principle_standard["principle_payload_contract"][
        "support_contract"
    ]
    assert support_contract["computed_by_validator"] == (
        "validator.microcosm.axiom_support_cover"
    )
    assert support_contract["claim_ceiling"]["projection_status"] == (
        "generated_support_projection_not_source_evidence"
    )
    assert any(
        "cannot assert its own support strength" in rule
        for rule in support_contract["non_laundering_rules"]
    )
    assert any(
        "anti-principle guards and negative-case coverage cannot become positive principle support"
        in rule
        for rule in support_contract["non_laundering_rules"]
    )
    # P-3 grounds AX-2: inherited support appears only after AX-2 has source
    # obligations, and it remains bounded by AX-2's unresolved strength ceiling.
    assert "P-3" in index
    assert index["P-3"]["inherited_support_verdicts"]["AX-2"] == "bound_resolved_strength_uncomputable"
    # P-4/P-16 ground AX-3 and inherit the bounded authorization verdict.
    assert "P-4" in index
    assert index["P-4"]["inherited_support_verdicts"]["AX-3"] == "bound_resolved_strength_uncomputable"
    assert "P-16" in index
    assert index["P-16"]["inherited_support_verdicts"]["AX-3"] == "bound_resolved_strength_uncomputable"
    assert index["P-16"]["inherited_support_verdicts"]["AX-9"] == "bound_resolved_strength_uncomputable"
    # P-5/P-14/P-15 inherit AX-4's layer-debt-capped determinism verdict.
    assert "P-5" in index
    assert index["P-5"]["inherited_support_verdicts"]["AX-4"] == "partial_capped_by_layer_debt"
    assert "P-14" in index
    assert index["P-14"]["inherited_support_verdicts"]["AX-4"] == "partial_capped_by_layer_debt"
    assert "P-15" in index
    assert index["P-15"]["inherited_support_verdicts"]["AX-4"] == "partial_capped_by_layer_debt"
    # P-7 grounds AX-6 and inherits open-world support without absence proof.
    assert "P-7" in index
    assert index["P-7"]["inherited_support_verdicts"]["AX-6"] == "bound_resolved_strength_uncomputable"
    # P-8 grounds AX-7's typed refusal/result support.
    assert "P-8" in index
    assert index["P-8"]["inherited_support_verdicts"]["AX-7"] == "bound_resolved_strength_uncomputable"
    # P-9 grounds AX-8: inherits the capped verdict, never amplifies it.
    assert "P-9" in index
    assert index["P-9"]["inherited_support_verdicts"]["AX-8"] == "partial_capped_by_layer_debt"
    assert any("does not witness" in claim for claim in index["P-9"]["anti_claims"])
    # P-12/P-15 ground AX-11; P-13 grounds AX-12, which stays capped by its
    # explicit evidence truth-floor layer debt.
    assert "P-12" in index
    assert index["P-12"]["inherited_support_verdicts"]["AX-11"] == "bound_resolved_strength_uncomputable"
    assert "P-15" in index
    assert index["P-15"]["inherited_support_verdicts"]["AX-11"] == "bound_resolved_strength_uncomputable"
    assert "P-13" in index
    assert index["P-13"]["inherited_support_verdicts"]["AX-12"] == "partial_capped_by_layer_debt"
    # P-2 grounds AX-1 and AX-5; AX-5 inherits only bounded fail-closed support.
    assert "P-2" in index
    assert index["P-2"]["inherited_support_verdicts"]["AX-5"] == "bound_resolved_strength_uncomputable"
    assert "P-6" in index
    assert index["P-6"]["inherited_support_verdicts"]["AX-5"] == "bound_resolved_strength_uncomputable"
    assert "P-10" in index
    assert index["P-10"]["inherited_support_verdicts"]["AX-9"] == "bound_resolved_strength_uncomputable"
    assert "P-11" in index
    assert index["P-11"]["inherited_support_verdicts"]["AX-10"] == "bound_resolved_strength_uncomputable"
    assert "P-18" in index
    assert index["P-18"]["inherited_support_verdicts"] == {
        "AX-3": "bound_resolved_strength_uncomputable",
        "AX-9": "bound_resolved_strength_uncomputable",
        "AX-11": "bound_resolved_strength_uncomputable",
        "AX-12": "partial_capped_by_layer_debt",
    }
    assert any("does not witness" in claim for claim in index["P-18"]["anti_claims"])
    assert "P-19" in index
    assert index["P-19"]["inherited_support_verdicts"] == {
        "AX-5": "bound_resolved_strength_uncomputable",
        "AX-6": "bound_resolved_strength_uncomputable",
        "AX-11": "bound_resolved_strength_uncomputable",
    }
    assert index["P-19"]["grounding_obligation_refs_by_axiom"]["AX-5"] == [
        "AX-5.O2.no_evidence_defaults_blocked",
        "AX-5.O3.authority_cannot_raise_without_derivation",
    ]
    assert index["P-19"]["grounding_obligation_refs_by_axiom"]["AX-6"] == [
        "AX-6.O1.closed_world_domain_declared",
        "AX-6.O2.absence_not_negation",
        "AX-6.O3.fact_claims_cite_loci_and_dag",
    ]
    assert index["P-19"]["grounding_obligation_refs_by_axiom"]["AX-11"] == [
        "AX-11.O1.grammar_membership_required",
        "AX-11.O2.receipts_and_anti_claims_present",
        "AX-11.O3.prose_alone_is_projection",
    ]
    assert index["P-19"]["unresolved_grounding_obligation_refs"] == []
    assert any("does not witness" in claim for claim in index["P-19"]["anti_claims"])
    assert {
        row["grounding_granularity"] for row in index.values()
    } == {"obligation_level_source_owned"}
    assert all(
        row["unresolved_grounding_obligation_refs"] == [] for row in index.values()
    )
    assert index["P-2"]["grounding_obligation_refs_by_axiom"]["AX-1"] == [
        "AX-1.O1.certificate_exists",
        "AX-1.O2.checker_accepts",
        "AX-1.O3.claim_ceiling",
        "AX-1.O4.bare_assertion_bottom",
    ]
    assert index["P-2"]["grounding_obligation_refs_by_axiom"]["AX-5"] == [
        "AX-5.O1.composite_status_meets_parts",
        "AX-5.O2.no_evidence_defaults_blocked",
        "AX-5.O3.authority_cannot_raise_without_derivation",
    ]
    assert index["P-2"]["inherited_obligation_statuses"][
        "AX-1.O3.claim_ceiling"
    ] == "resolved_strength_uncomputable"
    assert index["P-2"]["inherited_obligation_statuses"][
        "AX-5.O3.authority_cannot_raise_without_derivation"
    ] == "resolved_strength_uncomputable"
    assert index["P-18"]["grounding_obligation_refs_by_axiom"]["AX-12"] == [
        "AX-12.O1.microcosm_claims_use_same_gate",
        "AX-12.O2.release_claim_language_blocked",
        "AX-12.O3.receipt_body_and_doctrine_overclaim_blocked",
        "AX-12.O4.evidence_truth_floor_blocks_release",
    ]
    assert index["P-18"]["inherited_obligation_statuses"][
        "AX-12.O4.evidence_truth_floor_blocks_release"
    ] == "layer_debt"
    assert "P-20" in index
    assert index["P-20"]["inherited_support_verdicts"] == {
        "AX-11": "bound_resolved_strength_uncomputable",
        "AX-12": "partial_capped_by_layer_debt",
    }
    assert index["P-20"]["grounding_obligation_refs_by_axiom"]["AX-11"] == [
        "AX-11.O1.grammar_membership_required",
        "AX-11.O2.receipts_and_anti_claims_present",
        "AX-11.O3.prose_alone_is_projection",
    ]
    assert index["P-20"]["grounding_obligation_refs_by_axiom"]["AX-12"] == [
        "AX-12.O1.microcosm_claims_use_same_gate",
        "AX-12.O3.receipt_body_and_doctrine_overclaim_blocked",
        "AX-12.O4.evidence_truth_floor_blocks_release",
    ]
    assert index["P-20"]["inherited_obligation_statuses"][
        "AX-12.O4.evidence_truth_floor_blocks_release"
    ] == "layer_debt"


def test_candidate_pressure_routes_debt_not_weakening() -> None:
    result = _evaluate()
    pressures = result["candidate_axiom_pressure"]
    assert any(
        p.get("pressure_type") == "witness_debt"
        and p.get("layer_debt_ref") == "AX8-general-taint-propagation"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "witness_debt"
        and p.get("layer_debt_ref") == "AX4-work-landing-freshness-code-unmaterialized"
        for p in pressures
    )
    assert not any(
        p.get("pressure_type") == "witness_debt"
        and p.get("layer_debt_ref") == "AX10-volatile-numeric-code-unmaterialized"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "freshness_debt"
        and p.get("scope") == "evaluator_dimensions"
        and p.get("forbidden_action") == "do_not_treat_basis_digest_as_live_freshness_proof"
        for p in pressures
    )
    # The hand-stamped 'strong' row must generate sharpen pressure, not silent acceptance.
    assert any(
        p.get("pressure_type") == "sharpen" and p.get("axiom_ref") == "AX-1"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "sharpen" and p.get("axiom_ref") == "AX-2"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "sharpen" and p.get("axiom_ref") == "AX-3"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "sharpen" and p.get("axiom_ref") == "AX-4"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "sharpen" and p.get("axiom_ref") == "AX-5"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "sharpen" and p.get("axiom_ref") == "AX-6"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "sharpen" and p.get("axiom_ref") == "AX-7"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "sharpen" and p.get("axiom_ref") == "AX-9"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "sharpen" and p.get("axiom_ref") == "AX-10"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "sharpen" and p.get("axiom_ref") == "AX-11"
        for p in pressures
    )
    assert any(
        p.get("pressure_type") == "sharpen" and p.get("axiom_ref") == "AX-12"
        for p in pressures
    )
    # Every pressure forbids the lower-the-bar move.
    weakening = [p for p in pressures if p.get("forbidden_action")]
    assert all(
        p["forbidden_action"]
        in {
            "do_not_lower_axiom_bar_to_make_coverage_green",
            "do_not_treat_basis_digest_as_live_freshness_proof",
        }
        for p in weakening
    )


def test_rejection_mapping_debt_routes_to_receipt_level_evidence() -> None:
    result = _evaluate()
    mapping_debt = [
        row
        for row in result["candidate_axiom_pressure"]
        if row.get("pressure_type") == "rejection_mapping_debt"
    ]
    assert mapping_debt
    assert {
        row["mapping_source"] for row in mapping_debt
    } == {"source_owned_anti_axiom_rejection_mapping_row"}
    assert {
        row["recommended_route"] for row in mapping_debt
    } == {"receipt_level_per_obligation_rejection_evidence"}
    assert all(
        "receipt-level per-obligation mapping" in row["next_required_authority"]
        for row in mapping_debt
    )


def test_truth_calculus_summary_separates_support_from_rejection_mapping() -> None:
    result = _evaluate()
    summary = result["truth_calculus_summary"]

    assert summary["schema_version"] == "microcosm_axiom_truth_calculus_summary_v1"
    assert summary["axiom_count"] == 12
    assert summary["obligation_count"] == 39
    assert summary["required_obligation_count"] == 39
    assert summary["support_and_rejection_are_separate"] is True
    assert "meet of positive_support_status and rejection_mapping_status" in summary[
        "claim_ceiling_rule"
    ]

    assert summary["positive_support_status_counts"] == {
        "layer_debt_present": 3,
        "resolved_strength_uncomputable": 9,
    }
    assert summary["strongest_allowed_claim_counts"] == {
        "not_strong_rejection_mapping_unverified": 9,
        "partial_capped_by_layer_debt": 3,
    }
    assert summary["verified_rejection_mapping_count"] == 0
    assert summary["source_owned_mapping_count"] == 39
    assert summary["mapping_source_counts"] == {
        "source_owned_anti_axiom_rejection_mapping_row": 39
    }
    assert summary["authority_boundary"] == (
        "computed_from_source_bindings_receipts_and_checker_material; "
        "projection_output_is_not_source_evidence"
    )
    assert summary["mapping_relation_counts"].get("exact_obligation_rejection", 0) == 0
    assert summary["mapping_relation_counts"].get("subsumes_obligation", 0) == 0
    assert summary["anti_axiom_rejection_tier_counts"]["organ_receipt_coverage_present"] > 0
    assert summary["anti_axiom_rejection_tier_counts"]["referenced_in_bound_checker"] > 0
    assert summary["witness_gap_counts"]["anti_axiom_rejection_unverified"] == 39
    assert summary["witness_gap_counts"].get("ceiling_component_no_order_owner", 0) == 0
    assert summary["witness_gap_counts"]["ceiling_component_uncomputed"] == 49
    assert summary["witness_gap_counts"]["layer_debt"] == 3
    assert summary["witness_gap_counts"]["negative_case_absent"] == 20
    assert summary["witness_gap_counts"]["negative_case_declared_only"] == 7

    per_axiom = {row["axiom_id"]: row for row in summary["per_axiom"]}
    assert set(per_axiom) == PILOTED_AXIOMS
    assert per_axiom["AX-8"]["strongest_allowed_claim"] == "partial_capped_by_layer_debt"
    assert per_axiom["AX-8"]["mapping_relation_counts"] == {
        "illustrative_only": 1,
        "partial_overlap": 1,
        "unmapped": 1,
    }
    assert per_axiom["AX-8"]["witness_gap_counts"]["layer_debt"] == 1
    assert per_axiom["AX-8"]["witness_gap_counts"]["anti_axiom_rejection_unverified"] == 3
    assert per_axiom["AX-1"]["unverified_required_rejection_mapping_count"] == 4
    assert all(
        row["verified_rejection_mapping_count"] == 0 for row in summary["per_axiom"]
    )


def test_claim_ceiling_and_witness_gaps_are_explicit_on_axiom_nodes() -> None:
    result = _evaluate()

    for axiom_id, frontier in result["support_frontiers"].items():
        claim_ceiling = frontier["claim_ceiling"]
        assert claim_ceiling["schema_version"] == "microcosm_axiom_node_claim_ceiling_v1"
        assert claim_ceiling["computed_by"] == "checker.microcosm.validators.axiom_support_cover"
        assert claim_ceiling["strong_certified"] is False
        assert "generated projections do not raise source support" in claim_ceiling[
            "authority_boundary"
        ]
        assert claim_ceiling["strongest_allowed_claim"] in {
            "not_strong_rejection_mapping_unverified",
            "partial_capped_by_layer_debt",
            "blocked_conflict_detected",
        }

        for obligation in frontier["obligations"]:
            obligation_ceiling = obligation["claim_ceiling"]
            assert (
                obligation_ceiling["schema_version"]
                == "microcosm_axiom_obligation_claim_ceiling_v1"
            )
            assert obligation_ceiling["computed_by"] == (
                "checker.microcosm.validators.axiom_support_cover"
            )
            assert obligation_ceiling["strong_certified"] is False
            assert "generated support-cover output is not source evidence" in (
                obligation_ceiling["authority_boundary"]
            )
            assert obligation["witness_gaps"] == obligation_ceiling["witness_gaps"]
            assert {
                gap["gap_class"] for gap in obligation["witness_gaps"]
            } >= {"ceiling_component_uncomputed", "anti_axiom_rejection_unverified"}
            if obligation["computed"] == "layer_debt":
                assert any(
                    gap["gap_class"] == "layer_debt"
                    for gap in obligation["witness_gaps"]
                ), (axiom_id, obligation["obligation_id"])


def test_obligation_claim_ceiling_refuses_negative_case_laundering() -> None:
    obligations = _obligations_by_id()

    ax11_o3 = obligations["AX-11.O3.prose_alone_is_projection"]
    assert ax11_o3["negative_case_status"] == "referenced_in_bound_checker"
    assert ax11_o3["claim_ceiling"]["strongest_allowed_claim"] == (
        "not_strong_rejection_mapping_unverified"
    )
    assert any(
        gap["gap_id"] == "anti_axiom_rejection_unverified:illustrative_only"
        for gap in ax11_o3["witness_gaps"]
    )
    assert not any(
        gap["gap_class"].startswith("negative_case_")
        for gap in ax11_o3["witness_gaps"]
    )

    ax8_o1 = obligations["AX-8.O1.label_propagation"]
    assert ax8_o1["claim_ceiling"]["strongest_allowed_claim"] == (
        "partial_capped_by_layer_debt"
    )
    assert {
        gap["gap_id"] for gap in ax8_o1["witness_gaps"]
    } >= {
        "layer_debt:AX8-general-taint-propagation",
        "anti_axiom_rejection_unverified:unmapped",
    }


def test_unknown_is_distinct_from_blocked() -> None:
    result = _evaluate()
    semantics = result["coverage_state_semantics"]
    assert "blocked" in semantics
    assert "unknown_no_order_owner" in semantics
    # AX-8.O2 resolves and now has ordered checker/provenance/negative-case
    # components, while freshness still has no owner. Unknown is NOT blocked.
    ax8 = result["support_frontiers"]["AX-8"]
    o2 = next(o for o in ax8["obligations"] if o["obligation_id"] == "AX-8.O2.sink_policy")
    assert o2["computed"] == "resolved_strength_uncomputable"
    assert o2["ceiling_vector"]["checker_scope"] == (
        "checker_surface_refs_with_negative_case_reference"
    )
    assert o2["ceiling_vector"]["provenance_class"] == "checker_surface_refs_only"
    assert o2["ceiling_vector"]["authority_scope"] == (
        "source_binding_with_read_only_validator_authority"
    )
    assert o2["ceiling_vector"]["projection_scope"] == (
        "source_binding_with_generated_projection_boundary"
    )
    assert o2["ceiling_vector"]["domain_scope"] == (
        "declared_obligation_domain_with_bound_witness_material"
    )
    assert o2["ceiling_vector"]["freshness_state"] == (
        "unknown_live_freshness_no_refresh_contract"
    )


def test_ceiling_dimension_registry_is_source_owned_and_consumed() -> None:
    result = _evaluate()
    registry = json.loads(
        (MICROCOSM_ROOT / "core/axiom_support_ceiling_dimensions.json").read_text()
    )
    readback = result["ceiling_dimension_registry"]

    assert readback["schema_version"] == "microcosm_axiom_support_ceiling_dimensions_v1"
    assert readback["source_ref"] == "core/axiom_support_ceiling_dimensions.json"
    assert readback["component_order"] == registry["component_order"]
    assert readback["order_owned_component_ids"] == [
        "evidence_class",
        "checker_scope",
        "provenance_class",
        "freshness_state",
        "domain_scope",
        "negative_case_status",
        "authority_scope",
        "projection_scope",
    ]
    assert readback["explicitly_unowned_component_ids"] == []
    assert readback["unknown_no_order_owner_count"] == 0
    assert "Missing source order owners" in registry["unknown_dimension_policy"]
    assert "unknown_live_freshness_no_refresh_contract" in registry[
        "unknown_dimension_policy"
    ]
    assert "core/axiom_support_ceiling_dimensions.json" in result["self_attestation"][
        "basis_refs"
    ]
    assert "core/axiom_support_checker_scope_order.json" in result["self_attestation"][
        "basis_refs"
    ]
    assert "core/axiom_support_authority_scope_order.json" in result["self_attestation"][
        "basis_refs"
    ]
    assert "core/axiom_support_projection_scope_order.json" in result["self_attestation"][
        "basis_refs"
    ]
    assert "core/axiom_support_freshness_state_order.json" in result["self_attestation"][
        "basis_refs"
    ]
    assert "core/axiom_support_domain_scope_order.json" in result["self_attestation"][
        "basis_refs"
    ]
    assert "core/axiom_support_provenance_order.json" in result["self_attestation"][
        "basis_refs"
    ]

    pressure = next(
        row
        for row in result["candidate_axiom_pressure"]
        if row.get("pressure_type") == "freshness_debt"
        and row.get("scope") == "evaluator_dimensions"
    )
    assert "39 axiom obligations" in pressure["detail"]
    assert "no source-owned refresh contract" in pressure["detail"]
    assert pressure["forbidden_action"] == (
        "do_not_treat_basis_digest_as_live_freshness_proof"
    )
    assert not any(
        row.get("pressure_type") == "extend"
        and row.get("scope") == "evaluator_dimensions"
        for row in result["candidate_axiom_pressure"]
    )


def test_checker_scope_registry_is_source_owned_and_consumed() -> None:
    result = _evaluate()
    registry = json.loads(
        (MICROCOSM_ROOT / "core/axiom_support_checker_scope_order.json").read_text()
    )
    checker_scope_values = {
        obligation["ceiling_vector"]["checker_scope"]
        for frontier in result["support_frontiers"].values()
        for obligation in frontier["obligations"]
    }

    assert registry["schema_version"] == "microcosm_axiom_support_checker_scope_order_v1"
    assert registry["component_id"] == "checker_scope"
    assert registry["order_values"] == [
        "no_checker_surface_bound",
        "non_checker_source_surface_refs_only",
        "checker_surface_refs_bound",
        "checker_surface_refs_with_negative_case_reference",
    ]
    assert checker_scope_values == {
        "no_checker_surface_bound",
        "checker_surface_refs_bound",
        "checker_surface_refs_with_negative_case_reference",
    }
    assert not any(value == "unknown_no_order_owner" for value in checker_scope_values)
    assert any(
        "does not make any checker complete" in claim
        for claim in registry["anti_claims"]
    )
    assert any(
        "not proof that the anti-axiom is rejected" in rule
        for rule in registry["non_laundering_rules"]
    )

    ax1 = result["support_frontiers"]["AX-1"]
    o1 = next(o for o in ax1["obligations"] if o["obligation_id"] == "AX-1.O1.certificate_exists")
    assert o1["ceiling_vector"]["checker_scope"] == "no_checker_surface_bound"
    assert o1["claim_ceiling"]["strongest_allowed_claim"] == (
        "not_strong_rejection_mapping_unverified"
    )

    ax8 = result["support_frontiers"]["AX-8"]
    o2 = next(o for o in ax8["obligations"] if o["obligation_id"] == "AX-8.O2.sink_policy")
    assert o2["ceiling_vector"]["checker_scope"] == (
        "checker_surface_refs_with_negative_case_reference"
    )
    assert any(
        gap["gap_class"] == "anti_axiom_rejection_unverified"
        for gap in o2["witness_gaps"]
    )


def test_authority_scope_registry_is_source_owned_and_consumed() -> None:
    result = _evaluate()
    registry = json.loads(
        (MICROCOSM_ROOT / "core/axiom_support_authority_scope_order.json").read_text()
    )
    authority_values = {
        obligation["ceiling_vector"]["authority_scope"]
        for frontier in result["support_frontiers"].values()
        for obligation in frontier["obligations"]
    }

    assert registry["schema_version"] == "microcosm_axiom_support_authority_scope_order_v1"
    assert registry["component_id"] == "authority_scope"
    assert registry["order_values"] == [
        "read_only_validator_projection_authority",
        "source_binding_with_read_only_validator_authority",
    ]
    assert authority_values == {"source_binding_with_read_only_validator_authority"}
    assert not any(value == "unknown_no_order_owner" for value in authority_values)
    assert any(
        "does not grant source mutation or release authority" in claim
        for claim in registry["anti_claims"]
    )
    assert any(
        "not source mutation authority" in rule
        for rule in registry["non_laundering_rules"]
    )

    cases = _cases_by_obligation()
    o1 = cases["AX-1.O1.certificate_exists"]["authority_scope_component"]
    assert o1["source_ref"] == "core/axiom_support_authority_scope_order.json"
    assert o1["value"] == "source_binding_with_read_only_validator_authority"
    assert "does not become source mutation" in o1["non_laundering_boundary"]

    ax8 = result["support_frontiers"]["AX-8"]
    o2 = next(o for o in ax8["obligations"] if o["obligation_id"] == "AX-8.O2.sink_policy")
    assert o2["ceiling_vector"]["authority_scope"] == (
        "source_binding_with_read_only_validator_authority"
    )
    assert o2["claim_ceiling"]["strongest_allowed_claim"] == (
        "not_strong_rejection_mapping_unverified"
    )


def test_projection_scope_registry_is_source_owned_and_consumed() -> None:
    result = _evaluate()
    registry = json.loads(
        (MICROCOSM_ROOT / "core/axiom_support_projection_scope_order.json").read_text()
    )
    projection_values = {
        obligation["ceiling_vector"]["projection_scope"]
        for frontier in result["support_frontiers"].values()
        for obligation in frontier["obligations"]
    }

    assert registry["schema_version"] == "microcosm_axiom_support_projection_scope_order_v1"
    assert registry["component_id"] == "projection_scope"
    assert registry["order_values"] == [
        "generated_support_projection_boundary_only",
        "source_binding_with_generated_projection_boundary",
    ]
    assert projection_values == {"source_binding_with_generated_projection_boundary"}
    assert not any(value == "unknown_no_order_owner" for value in projection_values)
    assert any(
        "does not make projection output source authority" in claim
        for claim in registry["anti_claims"]
    )
    assert any(
        "Generated support-cover output cannot cite itself as evidence" in rule
        for rule in registry["non_laundering_rules"]
    )

    cases = _cases_by_obligation()
    o1 = cases["AX-1.O1.certificate_exists"]["projection_scope_component"]
    assert o1["source_ref"] == "core/axiom_support_projection_scope_order.json"
    assert o1["value"] == "source_binding_with_generated_projection_boundary"
    assert "do not become source evidence" in o1["non_laundering_boundary"]

    ax8 = result["support_frontiers"]["AX-8"]
    o2 = next(o for o in ax8["obligations"] if o["obligation_id"] == "AX-8.O2.sink_policy")
    assert o2["ceiling_vector"]["projection_scope"] == (
        "source_binding_with_generated_projection_boundary"
    )
    assert o2["claim_ceiling"]["strongest_allowed_claim"] == (
        "not_strong_rejection_mapping_unverified"
    )


def test_freshness_state_registry_is_source_owned_and_consumed_but_not_green() -> None:
    result = _evaluate()
    registry = json.loads(
        (MICROCOSM_ROOT / "core/axiom_support_freshness_state_order.json").read_text()
    )
    freshness_values = {
        obligation["ceiling_vector"]["freshness_state"]
        for frontier in result["support_frontiers"].values()
        for obligation in frontier["obligations"]
    }

    assert registry["schema_version"] == "microcosm_axiom_support_freshness_state_order_v1"
    assert registry["component_id"] == "freshness_state"
    assert registry["order_values"] == [
        "unknown_live_freshness_no_refresh_contract",
        "source_refresh_contract_checked",
    ]
    assert freshness_values == {"unknown_live_freshness_no_refresh_contract"}
    assert not any(value == "unknown_no_order_owner" for value in freshness_values)
    assert any(
        "does not certify live freshness" in claim
        for claim in registry["anti_claims"]
    )
    assert any(
        "not live freshness proof" in rule
        for rule in registry["non_laundering_rules"]
    )

    cases = _cases_by_obligation()
    o1 = cases["AX-1.O1.certificate_exists"]["freshness_state_component"]
    assert o1["source_ref"] == "core/axiom_support_freshness_state_order.json"
    assert o1["value"] == "unknown_live_freshness_no_refresh_contract"
    assert "do not become live freshness proof" in o1["non_laundering_boundary"]

    ax8 = result["support_frontiers"]["AX-8"]
    o2 = next(o for o in ax8["obligations"] if o["obligation_id"] == "AX-8.O2.sink_policy")
    assert o2["ceiling_vector"]["freshness_state"] == (
        "unknown_live_freshness_no_refresh_contract"
    )
    assert any(
        gap["gap_id"] == "ceiling_component_uncomputed:freshness_state"
        for gap in o2["witness_gaps"]
    )


def test_domain_scope_registry_is_source_owned_and_consumed() -> None:
    result = _evaluate()
    registry = json.loads(
        (MICROCOSM_ROOT / "core/axiom_support_domain_scope_order.json").read_text()
    )
    domain_values = {
        obligation["ceiling_vector"]["domain_scope"]
        for frontier in result["support_frontiers"].values()
        for obligation in frontier["obligations"]
    }

    assert registry["schema_version"] == "microcosm_axiom_support_domain_scope_order_v1"
    assert registry["component_id"] == "domain_scope"
    assert registry["order_values"] == [
        "declared_obligation_domain_only",
        "declared_obligation_domain_with_bound_witness_material",
    ]
    assert domain_values == {
        "declared_obligation_domain_with_bound_witness_material"
    }
    assert not any(value == "unknown_no_order_owner" for value in domain_values)
    assert any(
        "does not make any axiom substrate-general" in claim
        for claim in registry["anti_claims"]
    )
    assert any(
        "cannot become domain-general proof" in rule
        for rule in registry["non_laundering_rules"]
    )

    cases = _cases_by_obligation()
    o1 = cases["AX-1.O1.certificate_exists"]["domain_scope_component"]
    assert o1["source_ref"] == "core/axiom_support_domain_scope_order.json"
    assert o1["value"] == "declared_obligation_domain_with_bound_witness_material"
    assert "do not become substrate-general proof" in o1["non_laundering_boundary"]

    ax8 = result["support_frontiers"]["AX-8"]
    o2 = next(o for o in ax8["obligations"] if o["obligation_id"] == "AX-8.O2.sink_policy")
    assert o2["ceiling_vector"]["domain_scope"] == (
        "declared_obligation_domain_with_bound_witness_material"
    )
    assert o2["claim_ceiling"]["strongest_allowed_claim"] == (
        "not_strong_rejection_mapping_unverified"
    )


def test_provenance_class_registry_is_source_owned_and_consumed() -> None:
    result = _evaluate()
    registry = json.loads(
        (MICROCOSM_ROOT / "core/axiom_support_provenance_order.json").read_text()
    )
    provenance_values = {
        obligation["ceiling_vector"]["provenance_class"]
        for frontier in result["support_frontiers"].values()
        for obligation in frontier["obligations"]
    }

    assert registry["schema_version"] == "microcosm_axiom_support_provenance_order_v1"
    assert registry["component_id"] == "provenance_class"
    assert registry["order_values"] == [
        "declared_negative_case_only_no_positive_witness_material",
        "checker_surface_refs_only",
        "accepted_organ_material_chain",
        "accepted_organ_material_chain_with_checker_surfaces",
    ]
    assert provenance_values == set(registry["order_values"])
    assert not any(value == "unknown_no_order_owner" for value in provenance_values)
    assert any(
        "does not make any axiom strong" in claim
        for claim in registry["anti_claims"]
    )
    assert any(
        "cannot become proof that an anti-axiom is rejected" in rule
        for rule in registry["non_laundering_rules"]
    )

    ax1 = result["support_frontiers"]["AX-1"]
    o1 = next(o for o in ax1["obligations"] if o["obligation_id"] == "AX-1.O1.certificate_exists")
    assert o1["ceiling_vector"]["provenance_class"] == "accepted_organ_material_chain"
    assert o1["claim_ceiling"]["strongest_allowed_claim"] == (
        "not_strong_rejection_mapping_unverified"
    )
    o4 = next(o for o in ax1["obligations"] if o["obligation_id"] == "AX-1.O4.bare_assertion_bottom")
    assert o4["ceiling_vector"]["provenance_class"] == (
        "declared_negative_case_only_no_positive_witness_material"
    )
    assert any(
        gap["gap_class"] == "anti_axiom_rejection_unverified"
        for gap in o4["witness_gaps"]
    )


def test_evaluation_is_deterministic() -> None:
    # No wall-clock; basis_digest anchors freshness, so repeated runs are identical.
    first = _evaluate()
    second = _evaluate()
    assert first == second
    assert first["self_attestation"]["basis_digest"].startswith("sha256:")


def _cases_by_obligation() -> dict[str, dict]:
    return {case["obligation_ref"]: case for case in _evaluate()["support_cases"]}


def test_support_cases_compiled_for_every_pilot_obligation() -> None:
    cases = _cases_by_obligation()
    # AX-1, AX-4, and AX-12 have 4 obligations; the remaining piloted
    # axioms have 3 each.
    assert len([c for c in cases if c.startswith("AX-1.")]) == 4
    assert len([c for c in cases if c.startswith("AX-4.")]) == 4
    assert len([c for c in cases if c.startswith("AX-5.")]) == 3
    assert len([c for c in cases if c.startswith("AX-9.")]) == 3
    assert len([c for c in cases if c.startswith("AX-10.")]) == 3
    assert len([c for c in cases if c.startswith("AX-11.")]) == 3
    assert len([c for c in cases if c.startswith("AX-12.")]) == 4
    assert len([c for c in cases if c.startswith("AX-2.")]) == 3
    assert len([c for c in cases if c.startswith("AX-3.")]) == 3
    assert len([c for c in cases if c.startswith("AX-6.")]) == 3
    assert len([c for c in cases if c.startswith("AX-7.")]) == 3
    assert len([c for c in cases if c.startswith("AX-8.")]) == 3
    for case in cases.values():
        assert case["case_id"].endswith(".support_case")
        assert case["axiom_ref"] in PILOTED_AXIOMS
        assert case["basis_env"]["basis_digest"].startswith("sha256:")
        assert set(case["ceiling_vector"]) == {
            "evidence_class",
            "checker_scope",
            "provenance_class",
            "freshness_state",
            "domain_scope",
            "negative_case_status",
            "authority_scope",
            "projection_scope",
        }
        assert case["provenance_class_component"]["source_ref"] == (
            "core/axiom_support_provenance_order.json"
        )
        assert case["checker_scope_component"]["source_ref"] == (
            "core/axiom_support_checker_scope_order.json"
        )
        assert case["authority_scope_component"]["source_ref"] == (
            "core/axiom_support_authority_scope_order.json"
        )
        assert case["projection_scope_component"]["source_ref"] == (
            "core/axiom_support_projection_scope_order.json"
        )
        assert case["freshness_state_component"]["source_ref"] == (
            "core/axiom_support_freshness_state_order.json"
        )
        assert case["domain_scope_component"]["source_ref"] == (
            "core/axiom_support_domain_scope_order.json"
        )
        assert case["anti_claims"]


def test_support_case_citations_resolve_to_real_files() -> None:
    cases = _cases_by_obligation()
    # AX-1.O1 binds witness organs, so it cites real receipts and bundles on disk.
    o1 = cases["AX-1.O1.certificate_exists"]
    assert o1["materials"]["receipt_refs"], "organ-bound obligation must cite receipts"
    assert o1["materials"]["example_bundle_refs"], "organ-bound obligation must cite bundles"
    for ref in o1["materials"]["receipt_refs"] + o1["materials"]["example_bundle_refs"]:
        assert (MICROCOSM_ROOT / ref).exists(), ref


def test_ax8_layer_debt_case_is_partial_witness() -> None:
    case = _cases_by_obligation()["AX-8.O1.label_propagation"]
    assert case["relation_kind"] == "partial_witness_layer_debt"
    assert any("AX8-general-taint-propagation" in claim for claim in case["anti_claims"])


def test_support_cases_never_cite_a_principle() -> None:
    for case in _evaluate()["support_cases"]:
        materials = case["materials"]
        flat = (
            materials["witness_organs"]
            + materials["source_refs"]
            + materials["example_bundle_refs"]
            + materials["receipt_refs"]
            + materials["negative_case_refs"]
        )
        assert not any(str(ref).startswith("P-") and str(ref)[2:3].isdigit() for ref in flat)


def test_negative_case_status_is_order_owned_and_differentiates() -> None:
    result = _evaluate()
    obligations = {
        o["obligation_id"]: o
        for axiom in result["support_frontiers"].values()
        for o in axiom["obligations"]
    }
    # AX-1.O1 binds organs only (no negative codes) -> absent.
    assert obligations["AX-1.O1.certificate_exists"]["negative_case_status"] == "absent"
    # AX-8.O2 binds a real negative code -> at least declared, never absent.
    assert obligations["AX-8.O2.sink_policy"]["negative_case_status"] != "absent"
    # negative_case_status is now an order-owned (non-unknown) ceiling component
    # where a code is present, while a still-unowned component stays unknown.
    o2_case = _cases_by_obligation()["AX-8.O2.sink_policy"]
    assert o2_case["ceiling_vector"]["negative_case_status"] != "unknown_no_order_owner"
    assert o2_case["ceiling_vector"]["checker_scope"] == (
        "checker_surface_refs_with_negative_case_reference"
    )
    assert o2_case["ceiling_vector"]["provenance_class"] == "checker_surface_refs_only"
    assert o2_case["ceiling_vector"]["authority_scope"] == (
        "source_binding_with_read_only_validator_authority"
    )
    assert o2_case["ceiling_vector"]["projection_scope"] == (
        "source_binding_with_generated_projection_boundary"
    )
    assert o2_case["ceiling_vector"]["domain_scope"] == (
        "declared_obligation_domain_with_bound_witness_material"
    )
    assert o2_case["ceiling_vector"]["freshness_state"] == (
        "unknown_live_freshness_no_refresh_contract"
    )


def test_strong_blocked_reasons_are_explicit() -> None:
    result = _evaluate()
    ax1 = result["support_frontiers"]["AX-1"]
    # AX-1's 'strong' is refused with a stated reason, not silently.
    assert ax1["strong_blocked_reasons"]
    assert any("no negative case" in reason for reason in ax1["strong_blocked_reasons"])
    ax2 = result["support_frontiers"]["AX-2"]
    assert ax2["verdict"] == "bound_resolved_strength_uncomputable"
    assert any("no negative case" in reason for reason in ax2["strong_blocked_reasons"])
    assert any("anti-axiom rejection unverified" in reason for reason in ax2["strong_blocked_reasons"])
    ax3 = result["support_frontiers"]["AX-3"]
    assert ax3["verdict"] == "bound_resolved_strength_uncomputable"
    assert all(
        "anti-axiom rejection unverified" in reason
        for reason in ax3["strong_blocked_reasons"]
    )
    ax4 = result["support_frontiers"]["AX-4"]
    assert ax4["verdict"] == "partial_capped_by_layer_debt"
    assert any("AX4-work-landing-freshness-code-unmaterialized" in reason for reason in ax4["strong_blocked_reasons"])
    ax5 = result["support_frontiers"]["AX-5"]
    assert ax5["verdict"] == "bound_resolved_strength_uncomputable"
    assert any("no negative case" in reason for reason in ax5["strong_blocked_reasons"])
    assert any("anti-axiom rejection unverified" in reason for reason in ax5["strong_blocked_reasons"])
    ax6 = result["support_frontiers"]["AX-6"]
    assert ax6["verdict"] == "bound_resolved_strength_uncomputable"
    assert any("no negative case" in reason for reason in ax6["strong_blocked_reasons"])
    assert any("anti-axiom rejection unverified" in reason for reason in ax6["strong_blocked_reasons"])
    ax7 = result["support_frontiers"]["AX-7"]
    assert ax7["verdict"] == "bound_resolved_strength_uncomputable"
    assert any("no negative case" in reason for reason in ax7["strong_blocked_reasons"])
    assert any("anti-axiom rejection unverified" in reason for reason in ax7["strong_blocked_reasons"])
    ax8 = result["support_frontiers"]["AX-8"]
    assert any("layer_debt" in reason for reason in ax8["strong_blocked_reasons"])
    ax9 = result["support_frontiers"]["AX-9"]
    assert ax9["verdict"] == "bound_resolved_strength_uncomputable"
    assert all(
        "anti-axiom rejection unverified" in reason
        for reason in ax9["strong_blocked_reasons"]
    )
    ax10 = result["support_frontiers"]["AX-10"]
    assert ax10["verdict"] == "bound_resolved_strength_uncomputable"
    assert not any(
        "AX10-volatile-numeric-code-unmaterialized" in reason
        for reason in ax10["strong_blocked_reasons"]
    )
    assert any("no negative case" in reason for reason in ax10["strong_blocked_reasons"])
    assert any("anti-axiom rejection unverified" in reason for reason in ax10["strong_blocked_reasons"])
    ax11 = result["support_frontiers"]["AX-11"]
    assert ax11["verdict"] == "bound_resolved_strength_uncomputable"
    assert any("no negative case" in reason for reason in ax11["strong_blocked_reasons"])
    assert any("anti-axiom rejection unverified" in reason for reason in ax11["strong_blocked_reasons"])
    ax12 = result["support_frontiers"]["AX-12"]
    assert ax12["verdict"] == "partial_capped_by_layer_debt"
    assert any("AX12-evidence-truth-floor-blocking-release" in reason for reason in ax12["strong_blocked_reasons"])


def _obligations_by_id() -> dict[str, dict]:
    return {
        o["obligation_id"]: o
        for axiom in _evaluate()["support_frontiers"].values()
        for o in axiom["obligations"]
    }


def test_anti_axiom_rejection_is_a_judgment_separate_from_positive_support() -> None:
    # The bilattice split: AX-8.O1's positive side is capped by layer debt, while its
    # anti-axiom has independent receipt coverage -- which must NOT be read as rejection.
    o1 = _obligations_by_id()["AX-8.O1.label_propagation"]
    assert o1["computed"] == "layer_debt"
    rejection = o1["anti_axiom_rejection"]
    assert rejection["anti_axiom_ref"] == "endpoint_label_assertion_without_propagation"
    assert rejection["tier"] == "organ_receipt_coverage_present"
    assert rejection["mapping_relation"] == "unmapped"
    assert rejection["mapping_verified"] is False
    assert rejection["mapping"]["mapping_relation"] == "unmapped"
    assert rejection["mapping"]["receipt_coverage_basis"] == "complete_passing_negative_case_suite"


def test_no_obligation_certifies_anti_axiom_rejection_in_v0() -> None:
    # Laundering guard: organ/endpoint coverage must never become a per-obligation
    # rejection without verified mapping.
    for axiom in _evaluate()["support_frontiers"].values():
        for obligation in axiom["obligations"]:
            assert obligation["anti_axiom_rejection"]["mapping_verified"] is False


def test_anti_axiom_rejection_mapping_layer_separates_ax8_obligations() -> None:
    result = _evaluate()
    mappings = {row["obligation_ref"]: row for row in result["anti_axiom_rejection_mappings"]}

    o1 = mappings["AX-8.O1.label_propagation"]
    assert o1["mapping_source"] == "source_owned_anti_axiom_rejection_mapping_row"
    assert o1["mapping_relation"] == "unmapped"
    assert "AX8-general-taint-propagation" in o1["reason"]
    assert o1["basis_env"]["source_authority_ref"].startswith("core/axiom_organ_routing.json")

    o2 = mappings["AX-8.O2.sink_policy"]
    assert o2["mapping_source"] == "source_owned_anti_axiom_rejection_mapping_row"
    assert o2["mapping_relation"] == "partial_overlap"
    assert any("untrusted_to_privileged_sink" in ref for ref in o2["observed_negative_case_refs"])
    assert o2["mapping_verified"] is False

    o3 = mappings["AX-8.O3.lying_endpoint_rejected"]
    assert o3["mapping_source"] == "source_owned_anti_axiom_rejection_mapping_row"
    assert o3["mapping_relation"] == "illustrative_only"
    assert o3["mapping_verified"] is False

    summary = result["strong_gate_summary"]["AX-8"]
    assert summary["positive_support_status"] == "layer_debt_present"
    assert summary["rejection_mapping_status"] == "partial_or_illustrative_unverified"
    assert summary["strongest_allowed_claim"] == "partial_capped_by_layer_debt"


def test_no_mapping_relation_certifies_exact_rejection_in_v1() -> None:
    for mapping in _evaluate()["anti_axiom_rejection_mappings"]:
        assert mapping["mapping_relation"] != "exact_obligation_rejection"
        assert mapping["mapping_verified"] is False
        assert any(
            "not source law" in claim or "non-certifying" in claim
            for claim in mapping["anti_claims"]
        )


def test_standard_declares_mapping_shape_not_hidden_code_schema() -> None:
    standard = json.loads((MICROCOSM_ROOT / "standards/std_microcosm_axiom.json").read_text())
    owner_contract = standard["axiom_payload_contract"]["ceiling_dimension_owner_contract"]
    assert owner_contract["source_registry_ref"] == "core/axiom_support_ceiling_dimensions.json"
    assert owner_contract["registry_status"].endswith(
        "validator.microcosm.axiom_support_cover"
    )
    assert set(owner_contract["order_owned"]) == {
        "evidence_class",
        "checker_scope",
        "provenance_class",
        "freshness_state",
        "domain_scope",
        "negative_case_status",
        "authority_scope",
        "projection_scope",
    }
    assert owner_contract["unknown_no_order_owner"] == []
    assert "ordered unknown values such as freshness_state" in owner_contract[
        "unknown_dimension_policy"
    ]
    assert "core/axiom_support_freshness_state_order.json" in owner_contract[
        "order_owned"
    ]["freshness_state"]
    assert set(standard["axiom_payload_contract"]["pilot_status"]["piloted_axioms"]) == (
        PILOTED_AXIOMS
    )
    shape = standard["axiom_payload_contract"]["anti_axiom_rejection_contract"][
        "anti_axiom_rejection_mapping_shape"
    ]
    assert "mapping_relation" in shape["required_fields"]
    assert "exact_obligation_rejection" in shape["mapping_relation_enum"]
    assert "conflict_detected" in shape["mapping_relation_enum"]
    assert shape["source_owned_mapping_row_ref"].endswith("anti_axiom_rejection_mappings[]")
    assert any("generated support-cover output" in item for item in shape["forbidden"])

    anti_principle_standard = json.loads(
        (
            MICROCOSM_ROOT / "standards/std_microcosm_anti_principle.json"
        ).read_text()
    )
    boundary = anti_principle_standard["anti_principle_payload_contract"][
        "rejection_mapping_boundary_contract"
    ]
    assert boundary["instance_payload_field"] == "anti_principle_payload"
    assert "relationships.edges[].relation_id" in boundary["rejection_mapping_fields"]
    assert any(
        "std_microcosm_axiom.axiom_payload_contract.anti_axiom_rejection_contract"
        in rule
        for rule in boundary["non_laundering_rules"]
    )
    assert any(
        "cannot certify rejection without source-owned obligation mapping" in rule
        for rule in boundary["non_laundering_rules"]
    )
    assert boundary["residual_policy"]["unpopulated_selective_relations"].startswith(
        "typed residual pressure"
    )


def test_ax8_mapping_relations_are_source_owned_not_hidden_code() -> None:
    routing = json.loads((MICROCOSM_ROOT / "core/axiom_organ_routing.json").read_text())
    ax8 = next(row for row in routing["rows"] if row["axiom_id"] == "AX-8")
    mappings = {
        row["obligation_ref"]: row
        for row in ax8["anti_axiom_rejection_mappings"]
    }
    assert set(mappings) == {
        "AX-8.O1.label_propagation",
        "AX-8.O2.sink_policy",
        "AX-8.O3.lying_endpoint_rejected",
    }
    assert mappings["AX-8.O1.label_propagation"]["mapping_relation"] == "unmapped"
    assert mappings["AX-8.O2.sink_policy"]["mapping_relation"] == "partial_overlap"
    assert mappings["AX-8.O3.lying_endpoint_rejected"]["mapping_relation"] == "illustrative_only"
    assert all(mapping["mapping_verified"] is False for mapping in mappings.values())


def test_conflict_relation_blocks_strong_verdict() -> None:
    verdict = _axiom_verdict(
        [
            {
                "required": True,
                "computed": "resolved_strength_uncomputable",
                "obligation_id": "AX-X.O1.synthetic_conflict",
                "negative_case_status": "referenced_in_bound_checker",
                "anti_axiom_rejection": {
                    "tier": "organ_receipt_coverage_present",
                    "mapping_relation": "conflict_detected",
                    "mapping_verified": False,
                },
            }
        ],
        "strong",
    )
    assert verdict["verdict"] == "blocked_conflict_detected"
    assert any("conflict" in reason for reason in verdict["strong_blocked_reasons"])
