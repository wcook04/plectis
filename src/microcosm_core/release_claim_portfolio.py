"""
Implements release claim portfolio for the public Plectis package.

Callers enter through `ReleaseClaimRole`, `role`, `primary_product_role`, `gating_roles`,
`specimen_roles`, and `as_payload`; constants such as `PORTFOLIO_SCHEMA_VERSION`,
`COMPARISON_SEMANTIC_ACTION_IDENTITY`, `COMPARISON_SPECIMEN_BINDS_KERNEL`,
`COMPARISON_PAIRED_HOLDOUT_BENCHMARK`, and 2 more pin local fixture names; dependencies
include `dataclasses`, `typing`, and `microcosm_core`. Importing it does not authorize
release work or hidden private-state access; those effects live behind explicit calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from microcosm_core.skeptic_flight_recorder import (
    FIRST_ACTION_CLONE_GOAL,
    FIRST_ACTION_HERO_GOAL,
)

PORTFOLIO_SCHEMA_VERSION = "plectis_release_claim_portfolio_v1"

# How a role's cross-context agreement is judged. ``semantic_action_identity`` is
# the operator-mandated replacement for literal command-string equality: the
# contexts must agree on the owner organ and the action, not on the exact text
# of the recipe (a checkout may use ``PYTHONPATH=src ...``; an installed wheel
# uses the ``plectis`` console).
COMPARISON_SEMANTIC_ACTION_IDENTITY = "semantic_action_identity"
COMPARISON_SPECIMEN_BINDS_KERNEL = "specimen_binds_to_kernel_and_evidence_contract"
COMPARISON_PAIRED_HOLDOUT_BENCHMARK = "paired_holdout_repository_benchmark"

PRIMARY_PRODUCT_CLAIM = (
    "An arbitrary local repository can be transformed into an inspectable record "
    "whose consequential findings resolve to evidence, source, and scope, through "
    "the normal installed interface, with no external model calls and no source "
    "mutation."
)


@dataclass(frozen=True)
class ReleaseClaimRole:
    """
    Record object for Release Claim Role.

    It keeps `role_id`, `gates_release`, `claim_statement`, `bound_goal`,
    `bound_owner_organ_id`, `comparison_contract`, `proof_status`, and 1 more together for
    the release claim portfolio flow. Methods such as `as_payload` derive serialized or
    path-shaped views from that state.
    """

    role_id: str
    gates_release: bool
    claim_statement: str
    # The existing first-action goal this role exercises, if any. Imported from
    # the canonical owner so the portfolio follows the goal rather than re-pinning
    # its text.
    bound_goal: str | None
    # The specimen organ this role binds to, when the role is specimen-shaped.
    bound_owner_organ_id: str | None
    # How cross-context agreement is judged for this role.
    comparison_contract: str
    # Calibrated truth: what is actually proven today, in plain language.
    proof_status: str
    authority_ceiling: dict[str, Any] = field(default_factory=dict)

    def as_payload(self) -> dict[str, Any]:
        """
        Serialize ReleaseClaimRole into the release claim portfolio payload shape.

        The returned mapping uses the key names consumed by downstream receipts, cards, or
        tests.
        """
        return {
            "role_id": self.role_id,
            "gates_release": self.gates_release,
            "claim_statement": self.claim_statement,
            "bound_goal": self.bound_goal,
            "bound_owner_organ_id": self.bound_owner_organ_id,
            "comparison_contract": self.comparison_contract,
            "proof_status": self.proof_status,
            "authority_ceiling": dict(self.authority_ceiling),
        }


RELEASE_CLAIM_PORTFOLIO: tuple[ReleaseClaimRole, ...] = (
    ReleaseClaimRole(
        role_id="primary_product",
        gates_release=True,
        claim_statement=PRIMARY_PRODUCT_CLAIM,
        bound_goal=FIRST_ACTION_CLONE_GOAL,
        bound_owner_organ_id=None,  # generic: the owner is whatever the target repo routes to
        comparison_contract=COMPARISON_SEMANTIC_ACTION_IDENTITY,
        proof_status=(
            "self-application proven in the source checkout; installed-from-wheel "
            "against an unrelated repository is pending the built-artifact lane"
        ),
        authority_ceiling={"release_authorized": False, "gates_release": True},
    ),
    ReleaseClaimRole(
        role_id="distribution",
        gates_release=True,
        claim_statement=(
            "The same product semantics hold across the source checkout, a built "
            "wheel installed in a clean environment, and the standalone export, "
            "judged by semantic action identity (owner organ and action), not by "
            "literal command text."
        ),
        bound_goal=None,
        bound_owner_organ_id=None,
        comparison_contract=COMPARISON_SEMANTIC_ACTION_IDENTITY,
        proof_status=(
            "all three contexts present; command comparison is currently literal "
            "and is migrating to semantic action identity"
        ),
        authority_ceiling={"release_authorized": False, "gates_release": True},
    ),
    ReleaseClaimRole(
        role_id="pack_conformance",
        gates_release=False,
        claim_statement=(
            "Named optional organs bind to the kernel and the evidence contract. "
            "Finance forecasting is one such conformance specimen; it does not "
            "define whether Plectis Core is a usable product."
        ),
        bound_goal=FIRST_ACTION_HERO_GOAL,
        bound_owner_organ_id="finance_forecast_evaluation_spine",
        comparison_contract=COMPARISON_SPECIMEN_BINDS_KERNEL,
        proof_status="specimen present and fixture-validated",
        authority_ceiling={"release_authorized": False, "gates_release": False},
    ),
    ReleaseClaimRole(
        role_id="external_validity",
        gates_release=False,
        claim_statement=(
            "Plectis measurably helps a cold reader or agent form a more accurate, "
            "actionable model of an unfamiliar repository than a cheap baseline."
        ),
        bound_goal=None,
        bound_owner_organ_id=None,
        comparison_contract=COMPARISON_PAIRED_HOLDOUT_BENCHMARK,
        proof_status="pending — no holdout-repository benchmark exists yet",
        authority_ceiling={"release_authorized": False, "gates_release": False},
    ),
)


def role(role_id: str) -> ReleaseClaimRole:
    """
    Return role for the release claim portfolio flow.

    Inputs are `role_id`; notable helpers are `KeyError`; invalid cases raise from the
    explicit checks in the body.
    """
    for entry in RELEASE_CLAIM_PORTFOLIO:
        if entry.role_id == role_id:
            return entry
    raise KeyError(role_id)


def primary_product_role() -> ReleaseClaimRole:
    """
    Derive primary product role without touching module import state.

    Notable helpers are `role`.
    """
    return role("primary_product")


def gating_roles() -> tuple[ReleaseClaimRole, ...]:
    """
    Produce the gating roles value used by `microcosm_core.release_claim_portfolio`.

    The returned value is consumed directly by the caller.
    """
    return tuple(entry for entry in RELEASE_CLAIM_PORTFOLIO if entry.gates_release)


def specimen_roles() -> tuple[ReleaseClaimRole, ...]:
    """
    Derive specimen roles without touching module import state.

    The returned value is consumed directly by the caller.
    """
    return tuple(entry for entry in RELEASE_CLAIM_PORTFOLIO if not entry.gates_release)


def as_payload() -> dict[str, Any]:
    """
    Serialize the local value into the release claim portfolio payload shape.

    The returned mapping uses the key names consumed by downstream receipts, cards, or
    tests.
    """
    return {
        "schema_version": PORTFOLIO_SCHEMA_VERSION,
        "primary_product_claim": PRIMARY_PRODUCT_CLAIM,
        "roles": [entry.as_payload() for entry in RELEASE_CLAIM_PORTFOLIO],
    }
