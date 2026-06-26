"""The release claim portfolio names roles correctly and keeps finance a specimen.

The constitutional defect being corrected: one finance-forecast demonstration was
the entire release contract. These tests pin the corrected shape — the primary,
release-gating claim is the generic product promise; finance forecasting is a
non-gating pack-conformance specimen — and make the inversion un-resurrectable:
a pack specimen cannot silently become the primary product claim.
"""

from __future__ import annotations

import json

from microcosm_core import release_claim_portfolio as portfolio
from microcosm_core.skeptic_flight_recorder import (
    FIRST_ACTION_CLONE_GOAL,
    FIRST_ACTION_HERO_GOAL,
)


FINANCE_ORGAN = "finance_forecast_evaluation_spine"


def test_portfolio_has_the_four_expected_roles() -> None:
    role_ids = [entry.role_id for entry in portfolio.RELEASE_CLAIM_PORTFOLIO]
    assert role_ids == [
        "primary_product",
        "distribution",
        "pack_conformance",
        "external_validity",
    ]


def test_primary_claim_is_the_generic_product_not_finance() -> None:
    primary = portfolio.primary_product_role()
    assert primary.gates_release is True
    assert primary.claim_statement == portfolio.PRIMARY_PRODUCT_CLAIM
    # The primary claim is the generic repo->record promise: it must mention the
    # product shape and must NOT be the finance demonstration.
    assert "evidence, source, and scope" in primary.claim_statement
    assert "finance" not in primary.claim_statement.lower()
    assert "forecast" not in primary.claim_statement.lower()
    # It is bound to the generic-orientation goal, promoted from the canonical
    # constant (not a re-hardcoded copy), and to no specimen organ.
    assert primary.bound_goal == FIRST_ACTION_CLONE_GOAL
    assert primary.bound_owner_organ_id is None


def test_finance_is_a_non_gating_pack_specimen() -> None:
    pack = portfolio.role("pack_conformance")
    assert pack.gates_release is False
    assert pack.bound_owner_organ_id == FINANCE_ORGAN
    # Promotion, not duplication: the specimen follows the canonical hero goal.
    assert pack.bound_goal == FIRST_ACTION_HERO_GOAL
    assert "finance forecasting" in pack.claim_statement.lower()


def test_pack_specimen_cannot_silently_become_the_primary_claim() -> None:
    # The headline adversarial guard. Whatever role owns the finance organ must
    # never gate the release, and the gating primary role must never be bound to
    # the finance organ or the finance goal.
    primary = portfolio.primary_product_role()
    assert primary.bound_owner_organ_id != FINANCE_ORGAN
    assert primary.bound_goal != FIRST_ACTION_HERO_GOAL

    finance_roles = [
        entry
        for entry in portfolio.RELEASE_CLAIM_PORTFOLIO
        if entry.bound_owner_organ_id == FINANCE_ORGAN
        or entry.bound_goal == FIRST_ACTION_HERO_GOAL
    ]
    assert finance_roles, "the finance specimen must still be present as a role"
    for entry in finance_roles:
        assert entry.gates_release is False, (
            f"finance-bound role {entry.role_id!r} must not gate the release"
        )


def test_distribution_compares_by_semantic_action_not_literal_command() -> None:
    distribution = portfolio.role("distribution")
    assert distribution.gates_release is True
    assert (
        distribution.comparison_contract
        == portfolio.COMPARISON_SEMANTIC_ACTION_IDENTITY
    )
    assert "literal command text" in distribution.claim_statement


def test_external_validity_is_pending_and_non_gating() -> None:
    external = portfolio.role("external_validity")
    assert external.gates_release is False
    assert "pending" in external.proof_status.lower()


def test_gating_and_specimen_partition_is_exact() -> None:
    gating = {entry.role_id for entry in portfolio.gating_roles()}
    specimen = {entry.role_id for entry in portfolio.specimen_roles()}
    assert gating == {"primary_product", "distribution"}
    assert specimen == {"pack_conformance", "external_validity"}
    assert gating.isdisjoint(specimen)


def test_every_role_is_release_unauthorized() -> None:
    # This module declares roles; it never authorizes a release. The authority
    # ceiling on every role keeps release_authorized False.
    for entry in portfolio.RELEASE_CLAIM_PORTFOLIO:
        assert entry.authority_ceiling.get("release_authorized") is False


def test_proof_status_is_calibrated_not_aspirational() -> None:
    # Each role states what is proven today, not a promise. The two claims whose
    # full proof is not yet landed must say so.
    primary = portfolio.primary_product_role()
    assert "pending" in primary.proof_status.lower()
    external = portfolio.role("external_validity")
    assert "pending" in external.proof_status.lower()


def test_payload_is_json_serializable_and_round_trips() -> None:
    payload = portfolio.as_payload()
    encoded = json.dumps(payload)
    decoded = json.loads(encoded)
    assert decoded["schema_version"] == portfolio.PORTFOLIO_SCHEMA_VERSION
    assert decoded["primary_product_claim"] == portfolio.PRIMARY_PRODUCT_CLAIM
    assert [row["role_id"] for row in decoded["roles"]] == [
        "primary_product",
        "distribution",
        "pack_conformance",
        "external_validity",
    ]
