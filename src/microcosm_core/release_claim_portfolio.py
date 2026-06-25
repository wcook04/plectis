"""The release claim portfolio: which claims gate a release, and which are specimens.

For a long time Plectis's release proof had exactly one hero goal —
``"How do I evaluate the finance forecasting system?"`` — and that single
finance-forecast demonstration *was* the release constitution. That inverted the
product: a domain specimen stood in for the thing Plectis actually ships. A pack
specimen passing or failing should never be the definition of whether Plectis
Core is a usable product.

This module is the declarative correction. It names the distinct semantic ROLES a
release claim can hold and binds each to its existing owner goal, so the proof
builder, the review generator, and the human card can read *role* from one place
instead of treating one specimen as the whole contract.

It deliberately PROMOTES surfaces that already exist rather than inventing a
parallel claim schema:

* the generic-orientation goal already runs as ``FIRST_ACTION_CLONE_GOAL``;
* the finance demonstration already runs as ``FIRST_ACTION_HERO_GOAL`` against the
  ``finance_forecast_evaluation_spine`` organ;
* the three distribution contexts already exist as
  ``release_candidate_proof.CONTEXT_IDS``.

Each role carries a *calibrated* ``proof_status``: not a promise, but an honest
statement of what is actually proven today versus what is still pending. The
portfolio is therefore a self-truth surface from the start — it states the claim
and, in the same breath, the boundary of its current proof.

Roles
-----
``primary_product``
    Gates the release. The generic promise: an arbitrary local repository becomes
    an inspectable, evidence-bound record through the normal installed interface,
    with no external model calls and no source mutation.
``distribution``
    Gates the release. The same product *semantics* hold across the source
    checkout, a built wheel, and the standalone export — judged by semantic action
    identity (owner organ and action), NOT by literal command text. A checkout may
    legitimately use the source form; an installed wheel uses the ``plectis``
    console.
``pack_conformance``
    Does NOT gate the release. Named specimens (finance forecasting, and others)
    prove that an optional organ binds to the kernel and the evidence contract.
``external_validity``
    Does NOT gate the release yet. Reserved for holdout-repository usefulness
    evidence; currently pending, claimed by nothing.
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
    """One semantic role in the release claim portfolio."""

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
    """Return the role with ``role_id`` or raise KeyError."""
    for entry in RELEASE_CLAIM_PORTFOLIO:
        if entry.role_id == role_id:
            return entry
    raise KeyError(role_id)


def primary_product_role() -> ReleaseClaimRole:
    """The single role whose claim is the product Plectis actually ships."""
    return role("primary_product")


def gating_roles() -> tuple[ReleaseClaimRole, ...]:
    """Roles whose failure blocks the release proof."""
    return tuple(entry for entry in RELEASE_CLAIM_PORTFOLIO if entry.gates_release)


def specimen_roles() -> tuple[ReleaseClaimRole, ...]:
    """Roles that demonstrate capability without gating the release."""
    return tuple(entry for entry in RELEASE_CLAIM_PORTFOLIO if not entry.gates_release)


def as_payload() -> dict[str, Any]:
    """A JSON-serializable portfolio block for embedding in the proof packet."""
    return {
        "schema_version": PORTFOLIO_SCHEMA_VERSION,
        "primary_product_claim": PRIMARY_PRODUCT_CLAIM,
        "roles": [entry.as_payload() for entry in RELEASE_CLAIM_PORTFOLIO],
    }
