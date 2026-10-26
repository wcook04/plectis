"""
[PURPOSE]
- Teleology: Publish the shared Type A policy that local system evidence overrides prompt contours.
- Mechanism: Return a fresh policy mapping with caller metadata applied before canonical fields; render the same required-action list into worker prompt text.

[INTERFACE]
- Exports: TYPE_A_LOCAL_EVIDENCE_OVERRIDE_POLICY_ID, TYPE_A_LOCAL_EVIDENCE_OVERRIDE_POLICY, type_a_local_evidence_override_policy, type_a_policy_prompt_prefix.

[FLOW]
- Reads: Optional caller metadata.
- Orders: Canonical policy fields overwrite conflicting extras before prompt rendering.

[DEPENDENCIES]
- Reads: In-module policy constants only; no live state or external runtime is inspected.

[CONSTRAINTS]
- Guarantee: Extra metadata cannot override the canonical policy keys.
- Writes: None.
"""

from __future__ import annotations

from typing import Any, Mapping


TYPE_A_LOCAL_EVIDENCE_OVERRIDE_POLICY_ID = "type_a_local_evidence_over_prompt_contour_v1"

TYPE_A_LOCAL_EVIDENCE_OVERRIDE_POLICY: dict[str, Any] = {
    "policy_id": TYPE_A_LOCAL_EVIDENCE_OVERRIDE_POLICY_ID,
    "status": "strict_global",
    "short_name": "local_system_findings_override_proposed_contours",
    "rule": (
        "Treat operator memos, continuation notes, dispatch contours, and source packets as "
        "proposed contours. Type A must verify the local system surfaces it can inspect; when "
        "local evidence conflicts with the proposed contour, local system evidence wins."
    ),
    "required_actions": [
        "Run bounded local discovery before mutation when exact local affordances are uncertain.",
        "Prefer governing standards, source artifacts, tests, campaign state, and Work Ledger receipts over pasted recommendations.",
        "Record any override with evidence refs, reason, and residual risk in the receipt or final return packet.",
        "Escalate only when local evidence is missing, conflicting at an irreversible boundary, or outside the actor's authority.",
    ],
    "forbidden_behaviors": [
        "Following a pasted memo over contradictory repo evidence.",
        "Treating a dispatch packet as source authority after local tests or standards disconfirm it.",
        "Suppressing a useful local finding because it was not named by the operator.",
    ],
}


def type_a_local_evidence_override_policy(extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the strict policy, allowing callers to add metadata but not weaken it."""
    payload = dict(extra or {})
    payload.update(TYPE_A_LOCAL_EVIDENCE_OVERRIDE_POLICY)
    return payload


def type_a_policy_prompt_prefix(extra: Mapping[str, Any] | None = None) -> str:
    """Compact prompt prefix for runtime-owned Type A workers."""
    policy = type_a_local_evidence_override_policy(extra)
    actions = policy.get("required_actions") if isinstance(policy.get("required_actions"), list) else []
    action_text = "\n".join(f"- {item}" for item in actions)
    return (
        "Type A global policy: local system findings override proposed contours.\n"
        f"Policy id: {policy['policy_id']} ({policy['status']}).\n"
        f"Rule: {policy['rule']}\n"
        f"Required actions:\n{action_text}\n\n"
    )
