"""Defines the bounded claim roles that a release candidate may assert."""

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
    [ROLE]
    One semantic role in the release claim portfolio.
    - Teleology: Groups `ReleaseClaimRole` data or behavior for `microcosm_core.release_claim_portfolio` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.release_claim_portfolio`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
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
        [ACTION]
        - Teleology: Implements `ReleaseClaimRole.as_payload` for `microcosm_core.release_claim_portfolio` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
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
    [ACTION]
    Return the role with ``role_id`` or raise KeyError.
    - Teleology: Implements `role` for `microcosm_core.release_claim_portfolio` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for entry in RELEASE_CLAIM_PORTFOLIO:
        if entry.role_id == role_id:
            return entry
    raise KeyError(role_id)


def primary_product_role() -> ReleaseClaimRole:
    """
    [ACTION]
    The single role whose claim is the product Plectis actually ships.
    - Teleology: Implements `primary_product_role` for `microcosm_core.release_claim_portfolio` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return role("primary_product")


def gating_roles() -> tuple[ReleaseClaimRole, ...]:
    """
    [ACTION]
    Roles whose failure blocks the release proof.
    - Teleology: Implements `gating_roles` for `microcosm_core.release_claim_portfolio` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return tuple(entry for entry in RELEASE_CLAIM_PORTFOLIO if entry.gates_release)


def specimen_roles() -> tuple[ReleaseClaimRole, ...]:
    """
    [ACTION]
    Roles that demonstrate capability without gating the release.
    - Teleology: Implements `specimen_roles` for `microcosm_core.release_claim_portfolio` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return tuple(entry for entry in RELEASE_CLAIM_PORTFOLIO if not entry.gates_release)


def as_payload() -> dict[str, Any]:
    """
    [ACTION]
    A JSON-serializable portfolio block for embedding in the proof packet.
    - Teleology: Implements `as_payload` for `microcosm_core.release_claim_portfolio` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": PORTFOLIO_SCHEMA_VERSION,
        "primary_product_claim": PRIMARY_PRODUCT_CLAIM,
        "roles": [entry.as_payload() for entry in RELEASE_CLAIM_PORTFOLIO],
    }
