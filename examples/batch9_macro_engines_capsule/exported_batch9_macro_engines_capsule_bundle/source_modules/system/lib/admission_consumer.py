"""Shared consumer-side host-pressure admission helpers.

This module normalizes quote-plane decisions for launchers. It intentionally
does not schedule, poll, or inspect host pressure itself; callers pass in an
action quote and decide whether they are about to create new work.
"""
from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any


ADMISSION_CONSUMER_SCHEMA = "admission_consumer_decision_v0"
ADMISSION_POLICY_VALUES = ("auto", "warn", "off")
ADMISSION_TEMPFAIL = 75


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def normalize_admission_policy(policy: str | None, *, surface: str = "host pressure") -> str:
    value = str(policy or "auto").strip().lower()
    if value not in ADMISSION_POLICY_VALUES:
        expected = ", ".join(ADMISSION_POLICY_VALUES)
        raise ValueError(f"{surface} admission policy must be one of: {expected}")
    return value


def _blocked_by_recommendation(
    recommendation: str,
    block_recommendations: Collection[str],
) -> bool:
    if recommendation in block_recommendations:
        return True
    if not block_recommendations and recommendation.startswith("queue_"):
        return True
    if not block_recommendations and (
        recommendation.startswith("use_cached")
        or "summary" in recommendation
        or "override" in recommendation
    ):
        return True
    return False


def _policy_result(
    *,
    admission_decision: str,
    recommendation: str,
    operator_override_required: bool,
) -> str:
    if operator_override_required or admission_decision == "require_operator_override":
        return "explicit_override_required"
    if recommendation.startswith("use_cached") or "summary" in recommendation:
        return "summary_first"
    if admission_decision == "queue_until_pressure_clears" or recommendation.startswith("queue_"):
        return "queue_until_pressure_clears"
    return "queue_until_pressure_clears"


def build_admission_consumer_decision(
    quote: Mapping[str, Any],
    *,
    policy: str,
    consumer_id: str,
    action_class: str,
    block_recommendations: Collection[str] = (),
    override_hint: str,
) -> dict[str, Any]:
    """Convert an action quote into a launcher-facing admission decision."""
    normalized_policy = normalize_admission_policy(policy, surface=consumer_id)
    admission = _as_mapping(quote.get("host_pressure_admission"))
    admission_body = _as_mapping(admission.get("admission"))
    recommendation = str(quote.get("recommendation") or "")
    admission_decision = str(admission.get("decision") or admission_body.get("decision") or "")
    operator_override_required = bool(admission_body.get("operator_override_required"))
    admission_quote_command = admission.get("quote_command")
    recheck_command = (
        quote.get("host_pressure_recheck_command")
        or quote.get("suggested_command")
        or admission_quote_command
    )
    base: dict[str, Any] = {
        "schema": ADMISSION_CONSUMER_SCHEMA,
        "consumer_id": consumer_id,
        "action_id": quote.get("action_id"),
        "action_class": action_class,
        "policy": normalized_policy,
        "recommendation": recommendation,
        "current_status": quote.get("current_status"),
        "host_pressure_decision": admission_decision or None,
        "host_pressure_status": admission.get("status") or "missing",
        "reason": admission_body.get("reason"),
        "quote_command": recheck_command,
        "profile_command": admission.get("profile_command"),
        "host_pressure_recheck_command": recheck_command,
        "process_gate_command": quote.get("host_pressure_process_gate_command")
        or admission_quote_command,
        "deferred_command": (
            quote.get("narrow_render_command")
            or quote.get("deferred_suggested_command")
            or quote.get("host_pressure_original_suggested_command")
            or quote.get("suggested_command")
        ),
        "override_hint": override_hint,
        "tempfail_exit_code": ADMISSION_TEMPFAIL,
    }
    if normalized_policy == "off":
        return {
            **base,
            "result": "allow",
            "status": "skipped_by_policy",
            "allow": True,
            "new_work_admitted": True,
            "new_heavy_work_launched": None,
        }
    if quote.get("host_pressure_attach_allowed") is True:
        return {
            **base,
            "result": "attach_allowed",
            "status": "attach_allowed",
            "allow": True,
            "new_work_admitted": False,
            "new_heavy_work_launched": False,
            "reason": quote.get("host_pressure_attach_reason") or base.get("reason"),
        }
    if admission.get("status") != "available":
        return {
            **base,
            "result": "allow",
            "status": "no_available_host_pressure_admission",
            "allow": True,
            "new_work_admitted": True,
            "new_heavy_work_launched": None,
        }

    should_block = bool(admission.get("should_block_run")) and (
        admission_decision == "require_operator_override"
        or _blocked_by_recommendation(
            recommendation,
            block_recommendations,
        )
    )
    if not should_block:
        return {
            **base,
            "result": "allow",
            "status": "allowed_by_admission",
            "allow": True,
            "new_work_admitted": True,
            "new_heavy_work_launched": None,
        }

    blocked_result = _policy_result(
        admission_decision=admission_decision,
        recommendation=recommendation,
        operator_override_required=operator_override_required,
    )
    if normalized_policy == "warn":
        return {
            **base,
            "result": "allow",
            "blocked_result": blocked_result,
            "status": "warn_only",
            "allow": True,
            "new_work_admitted": True,
            "new_heavy_work_launched": None,
        }
    return {
        **base,
        "result": blocked_result,
        "status": "blocked",
        "allow": False,
        "new_work_admitted": False,
        "new_heavy_work_launched": False,
    }
