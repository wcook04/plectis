"""
[PURPOSE]
- Teleology: Provide one reusable lifecycle contract for preview-first
  campaigns that must move through preview, approval, apply, and terminal
  states without each lane reinventing the same state mapping logic.
- Mechanism: Normalize legacy campaign summaries, infer a compatible lifecycle
  state when older summaries omit one, project a backward-compatible legacy
  `status`, and record explicit lifecycle transitions.
- Non-goal: Lane-specific drain logic, coverage digests, or scheduler policy.
  This module owns only the shared lifecycle vocabulary and transitions.

[INTERFACE]
- Exports: Lifecycle terminal/status helpers, summary normalization/inference and transition_preview_campaign_summary.

[FLOW]
- Infer missing lifecycle fields from legacy status, project compatible status values and append explicit transition evidence to returned summaries.

[DEPENDENCIES]
- Caller-provided campaign summaries and this module's lifecycle/status tables.

[CONSTRAINTS]
- Guarantee: Helpers operate on returned summary dictionaries; they do not persist campaign state or spend approval authority.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

STANDARD_PATH = "codex/standards/std_preview_campaign_lifecycle.json"
SCHEMA_VERSION = "1.0"

VALID_LIFECYCLE_STATES = (
    "preview_pending",
    "preview_ready",
    "approved",
    "apply_active",
    "drained",
    "blocked",
)
TERMINAL_LIFECYCLE_STATES = {"drained", "blocked"}
NONTERMINAL_LIFECYCLE_STATES = set(VALID_LIFECYCLE_STATES) - TERMINAL_LIFECYCLE_STATES


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_sequence(values: Any) -> list[Any]:
    return list(values) if isinstance(values, Sequence) and not isinstance(values, (str, bytes, bytearray)) else []


def is_terminal_lifecycle_state(state: str) -> bool:
    return _string(state) in TERMINAL_LIFECYCLE_STATES


def project_legacy_status(state: str) -> str:
    token = _string(state)
    if token in {"preview_pending", "apply_active"}:
        return "running"
    if token == "blocked":
        return "completed_with_errors"
    return "completed"


def _has_batch_failure(batch: Mapping[str, Any]) -> bool:
    if _string(batch.get("status")).lower() == "failed":
        return True
    if int(batch.get("exit_code") or 0) not in {0} and batch.get("exit_code") is not None:
        return True
    result = _safe_mapping(batch.get("result"))
    return _string(result.get("status")).lower() in {"failure", "preview_blocked", "blocked"}


def infer_preview_campaign_lifecycle_state(summary: Mapping[str, Any]) -> str:
    explicit = _string(summary.get("lifecycle_state"))
    if explicit in VALID_LIFECYCLE_STATES:
        return explicit

    status = _string(summary.get("status")).lower()
    batches = [dict(item) for item in _safe_sequence(summary.get("batches")) if isinstance(item, Mapping)]
    if status == "completed_with_errors" or any(_has_batch_failure(batch) for batch in batches):
        return "blocked"

    if not batches:
        finding_count = int(_safe_mapping(summary.get("summary")).get("finding_count") or 0)
        if finding_count == 0 and status in {"completed", "success"}:
            return "drained"
        if status == "running":
            return "preview_pending"
        if status in {"completed", "success"}:
            return "preview_ready" if bool(summary.get("preview_apply")) else "preview_pending"
        return "preview_pending"

    if any(_string(batch.get("status")).lower() in {"pending", "running"} for batch in batches):
        return "preview_pending"

    if any(_string(_safe_mapping(batch.get("result")).get("status")).lower() == "preview_blocked" for batch in batches):
        return "blocked"

    if bool(summary.get("preview_apply")):
        preview_ready = [
            batch
            for batch in batches
            if _string(_safe_mapping(batch.get("result")).get("status")).lower() == "preview_ready"
        ]
        if len(preview_ready) == len(batches):
            return "preview_ready"

    return "preview_pending"


def normalize_preview_campaign_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(summary)
    lifecycle_state = infer_preview_campaign_lifecycle_state(payload)
    approval = _safe_mapping(payload.get("approval"))
    approved_at = _string(approval.get("approved_at") or payload.get("approved_at"))
    approved_by = _string(approval.get("approved_by") or payload.get("approved_by"))
    approval["approved"] = bool(approval.get("approved")) or bool(approved_at or approved_by)
    approval["approved_at"] = approved_at or None
    approval["approved_by"] = approved_by or None
    payload["approval"] = approval
    payload["lifecycle_state"] = lifecycle_state
    payload["lifecycle_standard_path"] = STANDARD_PATH
    payload["lifecycle_schema_version"] = SCHEMA_VERSION
    payload["status"] = project_legacy_status(lifecycle_state)
    payload["lifecycle_state_updated_at"] = (
        _string(payload.get("lifecycle_state_updated_at"))
        or _string(payload.get("finished_at"))
        or _string(payload.get("resumed_at"))
        or _string(payload.get("started_at"))
        or None
    )
    history = payload.get("lifecycle_history")
    payload["lifecycle_history"] = [
        dict(item) for item in _safe_sequence(history) if isinstance(item, Mapping)
    ]
    return payload


def transition_preview_campaign_summary(
    summary: Mapping[str, Any],
    *,
    to_state: str,
    reason: str | None = None,
    actor: str | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    token = _string(to_state)
    if token not in VALID_LIFECYCLE_STATES:
        raise ValueError(f"Unknown lifecycle state: {to_state}")

    payload = normalize_preview_campaign_summary(summary)
    current_state = _string(payload.get("lifecycle_state"))
    changed = current_state != token
    at = _string(now_iso) or _utc_now_iso()

    approval = _safe_mapping(payload.get("approval"))
    if token == "approved":
        approval["approved"] = True
        approval["approved_at"] = approval.get("approved_at") or at
        approval["approved_by"] = approval.get("approved_by") or (_string(actor) or None)
    elif token in {"preview_pending", "preview_ready"} and not approval.get("approved_at") and not approval.get("approved_by"):
        approval["approved"] = False
        approval["approved_at"] = None
        approval["approved_by"] = None
    payload["approval"] = approval

    payload["lifecycle_state"] = token
    payload["status"] = project_legacy_status(token)
    payload["lifecycle_standard_path"] = STANDARD_PATH
    payload["lifecycle_schema_version"] = SCHEMA_VERSION
    payload["lifecycle_state_updated_at"] = at

    if changed:
        history = payload.get("lifecycle_history")
        if not isinstance(history, list):
            history = []
        history.append(
            {
                "from_state": current_state or None,
                "to_state": token,
                "changed_at": at,
                "actor": _string(actor) or None,
                "reason": _string(reason) or None,
            }
        )
        payload["lifecycle_history"] = history
    return payload
