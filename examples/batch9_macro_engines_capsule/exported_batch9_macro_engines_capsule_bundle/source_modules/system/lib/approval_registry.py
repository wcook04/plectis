"""
[PURPOSE]
- Teleology: Project scattered approval-pending runtime state into one bounded
  operator inbox while preserving each source system as the authority for its
  own native files and transitions.
- Mechanism: Read campaign summaries, orchestration/factory state, Type A seat
  requests, and bounded approval request manifests; normalize them into
  `ApprovalRecord` rows; persist a small local overlay for first-seen timestamps
  and local dismissals; and coordinate one-at-a-time decisions through a claim
  file and append-only ledger.

[INTERFACE]
- Exports: `list_approvals`, `decide_approval`, `approval_paths`.
- Reads: `campaign_summary.json`, `tools/meta/control/orchestration_state.json`,
  `state/approvals/requests/**/*.json`, and approval overlay artifacts under
  `state/approvals/`.
- Writes: `state/approvals/pending.json`, `decision_state.json`, `claims.json`,
  and `approval_ledger.jsonl`.
- Constraint: Native source files remain authoritative; reject only mutates the
  approval overlay, never the underlying source.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from system.lib.python_std_compliance_runtime import (
    DEFAULT_APPROVED_BY,
    atomic_write_json,
    build_approve_command,
    discover_python_std_campaign_summaries,
)

APPROVAL_STATE_DIR_REL = "state/approvals"
PENDING_REL = f"{APPROVAL_STATE_DIR_REL}/pending.json"
DECISION_STATE_REL = f"{APPROVAL_STATE_DIR_REL}/decision_state.json"
CLAIMS_REL = f"{APPROVAL_STATE_DIR_REL}/claims.json"
LEDGER_REL = f"{APPROVAL_STATE_DIR_REL}/approval_ledger.jsonl"
APPROVAL_REQUESTS_DIR_REL = f"{APPROVAL_STATE_DIR_REL}/requests"
ORCHESTRATION_STATE_REL = "tools/meta/control/orchestration_state.json"
APPROVAL_REQUEST_MANIFEST_SOURCE_KIND = "approval_request_manifest"
APPROVAL_REQUEST_MANIFEST_SCHEMA = "approval_request_v1"
APPROVAL_REQUEST_CLOSED_STATUSES = {
    "approved",
    "cancelled",
    "closed",
    "completed",
    "dismissed",
    "rejected",
    "superseded",
}

# P6: Compute-artifact approvals lane. Flag-gated dark ship so the feature
# exists in code but does not surface receipts in the Approvals list until the
# operator flips the config key below.
COMPUTE_RECEIPTS_DIR_REL = "state/compute_workers/receipts"
METABOLISM_CONFIG_REL = "state/metabolism/metabolism_config.json"
COMPUTE_ARTIFACT_APPROVALS_CONFIG_KEY = "compute_artifact_approvals_enabled"

APPROVAL_STATUS_VALUES = {"pending", "claimed", "approved", "rejected"}
APPROVAL_ACTION_KIND_VALUES = {"decide", "review_only"}
DECISION_VALUES = {"approve", "reject"}
CLAIM_TTL_SECONDS = 300

_STATE_LOCK = threading.Lock()


@dataclass(frozen=True)
class ApprovalPaths:
    state_dir: Path
    pending: Path
    decision_state: Path
    claims: Path
    ledger: Path


def approval_paths(repo_root: Path) -> ApprovalPaths:
    state_dir = (repo_root / APPROVAL_STATE_DIR_REL).resolve()
    return ApprovalPaths(
        state_dir=state_dir,
        pending=(repo_root / PENDING_REL).resolve(),
        decision_state=(repo_root / DECISION_STATE_REL).resolve(),
        claims=(repo_root / CLAIMS_REL).resolve(),
        ledger=(repo_root / LEDGER_REL).resolve(),
    )


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [_string(value)] if _string(value) else []
    return [_string(item) for item in _safe_list(value) if _string(item)]


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = _string(value)
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative(repo_root: Path, path: str | Path | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        return _string(candidate)
    try:
        return str(candidate.resolve().relative_to(repo_root.resolve()))
    except Exception:
        return str(candidate)


def _read_json(path: Path, *, default: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return dict(payload) if isinstance(payload, Mapping) else dict(default or {})
    except Exception:
        return dict(default or {})


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False) + "\n")


def _stable_json_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(payload), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _approval_id(source_kind: str, source_ref: str) -> str:
    return hashlib.sha256(f"{source_kind}:{source_ref}".encode("utf-8")).hexdigest()[:24]


def _severity_rank(severity: str | None) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(_string(severity).upper(), 9)


def _sort_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda item: (
            _severity_rank(item.get("severity")),
            0 if item.get("action_kind") == "decide" else 1,
            _string(item.get("opened_at") or item.get("updated_at") or ""),
            _string(item.get("approval_id")),
        ),
    )


def _load_decision_state(paths: ApprovalPaths) -> dict[str, Any]:
    payload = _read_json(
        paths.decision_state,
        default={
            "schema": "approval_decision_state_v1",
            "updated_at": None,
            "records": {},
        },
    )
    payload["records"] = _safe_mapping(payload.get("records"))
    return payload


def _load_claims(paths: ApprovalPaths) -> dict[str, Any]:
    payload = _read_json(
        paths.claims,
        default={
            "schema": "approval_claims_v1",
            "updated_at": None,
            "claims": {},
        },
    )
    payload["claims"] = _safe_mapping(payload.get("claims"))
    return payload


def _persist_decision_state(paths: ApprovalPaths, payload: Mapping[str, Any]) -> None:
    atomic_write_json(paths.decision_state, payload)


def _persist_claims(paths: ApprovalPaths, payload: Mapping[str, Any]) -> None:
    atomic_write_json(paths.claims, payload)


def _write_pending_snapshot(paths: ApprovalPaths, payload: Mapping[str, Any]) -> None:
    atomic_write_json(paths.pending, payload)


def _claim_expired(claim: Mapping[str, Any]) -> bool:
    expires_at = _string(claim.get("expires_at"))
    if not expires_at:
        return True
    try:
        return datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc)
    except Exception:
        return True


def _cleanup_claims(
    claims_payload: dict[str, Any],
    *,
    current_hashes: Mapping[str, str] | None = None,
) -> bool:
    claims = _safe_mapping(claims_payload.get("claims"))
    kept: dict[str, Any] = {}
    changed = False
    for approval_id, raw in claims.items():
        claim = _safe_mapping(raw)
        source_hash = _string(claim.get("source_state_hash"))
        if _claim_expired(claim):
            changed = True
            continue
        if current_hashes is not None and current_hashes.get(approval_id) != source_hash:
            changed = True
            continue
        kept[approval_id] = claim
    if kept != claims:
        claims_payload["claims"] = kept
        claims_payload["updated_at"] = _iso_now()
        changed = True
    return changed


def _projection_hash(record: Mapping[str, Any]) -> str:
    return _string(record.get("source_state_hash"))


def _project_campaign_preview_ready(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for summary in discover_python_std_campaign_summaries(repo_root):
        lifecycle_state = _string(summary.get("lifecycle_state"))
        approval = _safe_mapping(summary.get("approval"))
        if lifecycle_state != "preview_ready" or bool(approval.get("approved")):
            continue
        summary_path = _string(summary.get("campaign_summary_path"))
        source_ref = summary_path
        summary_digest = {
            "campaign_summary_path": summary_path,
            "lifecycle_state": lifecycle_state,
            "lifecycle_state_updated_at": summary.get("lifecycle_state_updated_at"),
            "approved": bool(approval.get("approved")),
            "approved_at": approval.get("approved_at"),
            "finding_count": (summary.get("summary") or {}).get("finding_count"),
            "bin_count": (summary.get("summary") or {}).get("bin_count"),
            "status": summary.get("status"),
        }
        record = {
            "approval_id": _approval_id("campaign_preview_ready", source_ref),
            "source_kind": "campaign_preview_ready",
            "source_ref": source_ref,
            "title": f"Approve campaign {summary.get('campaign_slug') or Path(summary_path).parent.name}",
            "detail": (
                f"{(summary.get('summary') or {}).get('finding_count') or 0} findings across "
                f"{(summary.get('summary') or {}).get('bin_count') or 0} bins are preview-ready."
            ),
            "status": "pending",
            "action_kind": "decide",
            "severity": "P2",
            "owner_driver": "python_std_compliance",
            "artifacts": [
                value
                for value in [
                    summary_path,
                    _string(summary.get("apply_summary_path")) or None,
                ]
                if value
            ],
            "command": _string(summary.get("approve_command"))
            or build_approve_command(
                repo_root,
                repo_root / summary_path,
                DEFAULT_APPROVED_BY,
            ),
            "operation": {
                "operation_id": "python_std_compliance_campaign_approve",
                "parameters": {
                    "campaign_summary": summary_path,
                    "approved_by": DEFAULT_APPROVED_BY,
                },
            },
            "source_state_hash": _stable_json_hash(summary_digest),
            "opened_at": _string(summary.get("lifecycle_state_updated_at") or summary.get("finished_at") or summary.get("started_at")) or None,
            "updated_at": _string(summary.get("lifecycle_state_updated_at") or summary.get("finished_at") or summary.get("started_at")) or None,
            "surface_route": "/station/ops",
            "surface_label": "Ops",
        }
        rows.append(record)
    return rows


def _load_orchestration_state(repo_root: Path) -> dict[str, Any]:
    return _read_json(repo_root / ORCHESTRATION_STATE_REL)


def _project_orchestration_gate(repo_root: Path, orchestration: Mapping[str, Any]) -> list[dict[str, Any]]:
    gate = _safe_mapping(orchestration.get("gate"))
    if not bool(gate.get("active")):
        return []
    decision = _safe_mapping(orchestration.get("decision"))
    source_ref = f"{ORCHESTRATION_STATE_REL}#gate"
    digest = {
        "gate": {
            "active": bool(gate.get("active")),
            "gate_reason": gate.get("gate_reason"),
            "owner_driver": gate.get("owner_driver"),
            "review_ready": bool(gate.get("review_ready")),
            "command": gate.get("command"),
        },
        "decision": {
            "summary": decision.get("summary"),
            "command": decision.get("command"),
            "immediate_mode": decision.get("immediate_mode"),
        },
        "updated_at": orchestration.get("updated_at"),
    }
    gate_reason = _string(gate.get("gate_reason")) or "active"
    return [
        {
            "approval_id": _approval_id("orchestration_gate", source_ref),
            "source_kind": "orchestration_gate",
            "source_ref": source_ref,
            "title": "Acknowledge orchestration gate",
            "detail": _string(decision.get("summary"))
            or gate_reason.replace("_", " "),
            "status": "pending",
            "action_kind": "decide",
            "severity": "P1",
            "owner_driver": _string(gate.get("owner_driver")) or None,
            "artifacts": [
                ORCHESTRATION_STATE_REL,
                "tools/meta/control/orchestration_events.jsonl",
            ],
            "command": _string(gate.get("command")) or _string(decision.get("command")) or None,
            "operation": None,
            "source_state_hash": _stable_json_hash(digest),
            "opened_at": _string(orchestration.get("updated_at")) or None,
            "updated_at": _string(orchestration.get("updated_at")) or None,
            "surface_route": "/station/approvals",
            "surface_label": "Approvals",
        }
    ]


def _project_factory_apply_review(repo_root: Path, orchestration: Mapping[str, Any]) -> list[dict[str, Any]]:
    gate = _safe_mapping(orchestration.get("gate"))
    drivers = _safe_list(orchestration.get("drivers"))
    factory_driver = next(
        (dict(driver) for driver in drivers if isinstance(driver, Mapping) and _string(driver.get("driver_id")) == "factory_lane"),
        None,
    )
    if not factory_driver:
        return []
    gate_reason = _string(gate.get("gate_reason"))
    stage = _string(factory_driver.get("stage"))
    if gate_reason not in {"apply_review_pending", "missing_review_packet", "invalid_review_packet"} and stage != "apply_review_pending":
        return []
    next_action = _safe_mapping(factory_driver.get("next_action"))
    review_artifacts = [
        _string(item)
        for item in _safe_list(factory_driver.get("review_artifacts"))
        if _string(item)
    ]
    source_ref = f"{_string(factory_driver.get('state_path')) or 'tools/meta/factory/factory_state.json'}#apply_review"
    digest = {
        "gate_reason": gate_reason,
        "review_ready": bool(gate.get("review_ready")),
        "command": gate.get("command"),
        "driver": {
            "stage": stage,
            "blocked": bool(factory_driver.get("blocked")),
            "review_artifacts": review_artifacts,
            "last_updated": factory_driver.get("last_updated"),
            "next_action": {
                "summary": next_action.get("summary"),
                "command": next_action.get("command"),
            },
        },
        "updated_at": orchestration.get("updated_at"),
    }
    severity = "P1" if gate_reason in {"missing_review_packet", "invalid_review_packet"} else "P2"
    detail = _string(next_action.get("summary")) or _string(gate_reason).replace("_", " ")
    return [
        {
            "approval_id": _approval_id("factory_apply_review", source_ref),
            "source_kind": "factory_apply_review",
            "source_ref": source_ref,
            "title": "Factory apply review is waiting",
            "detail": detail,
            "status": "pending",
            "action_kind": "review_only",
            "severity": severity,
            "owner_driver": "factory_lane",
            "artifacts": review_artifacts,
            "command": _string(next_action.get("command")) or _string(gate.get("command")) or None,
            "operation": {
                "operation_id": "factory_stage_apply",
                "parameters": {},
            },
            "source_state_hash": _stable_json_hash(digest),
            "opened_at": _string(factory_driver.get("last_updated") or orchestration.get("updated_at")) or None,
            "updated_at": _string(factory_driver.get("last_updated") or orchestration.get("updated_at")) or None,
            "surface_route": "/launchpad",
            "surface_label": "Launchpad",
        }
    ]


def _iter_approval_request_manifests(repo_root: Path):
    """Yield source-owned approval request manifests.

    This lane is the escape hatch for new subsystems: if a source reaches a
    decision boundary before a dedicated projector exists, it writes one small
    JSON manifest under ``state/approvals/requests/`` and the unified inbox
    surfaces it on the next read.
    """
    requests_root = repo_root / APPROVAL_REQUESTS_DIR_REL
    if not requests_root.exists():
        return
    for path in sorted(requests_root.rglob("*.json")):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, Mapping):
            continue
        status = _string(payload.get("status") or payload.get("approval_status") or "pending").lower()
        if status in APPROVAL_REQUEST_CLOSED_STATUSES:
            continue
        yield path, dict(payload)


def _project_approval_request_manifests(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for manifest_path, manifest in _iter_approval_request_manifests(repo_root) or []:
        manifest_rel = _relative(repo_root, manifest_path) or manifest_path.as_posix()
        source_ref = _string(manifest.get("source_ref")) or manifest_rel
        action_kind = _string(manifest.get("action_kind")).lower()
        if action_kind not in APPROVAL_ACTION_KIND_VALUES:
            action_kind = "decide"
        severity = _string(manifest.get("severity")).upper() or "P2"
        if severity not in {"P0", "P1", "P2", "P3"}:
            severity = "P2"
        metadata = _safe_mapping(manifest.get("metadata"))
        origin_kind = _string(
            manifest.get("origin_kind")
            or manifest.get("origin")
            or metadata.get("origin_kind")
        )
        decision_mode = _string(manifest.get("decision_mode") or metadata.get("decision_mode")).lower()
        if action_kind == "decide":
            decision_mode = "overlay_only"
        else:
            decision_mode = "review_only"
        metadata.update(
            {
                "manifest_path": manifest_rel,
                "manifest_schema": _string(manifest.get("schema_version"))
                or _string(manifest.get("schema"))
                or APPROVAL_REQUEST_MANIFEST_SCHEMA,
                "origin_kind": origin_kind or None,
                "decision_mode": decision_mode,
            }
        )
        artifacts = _dedupe_strings(
            [
                manifest_rel,
                *_safe_string_list(manifest.get("artifacts")),
                *_safe_string_list(manifest.get("evidence_artifacts")),
            ]
        )
        digest = {
            "manifest_path": manifest_rel,
            "manifest": manifest,
            "normalized": {
                "source_ref": source_ref,
                "action_kind": action_kind,
                "decision_mode": decision_mode,
            },
        }
        rows.append(
            {
                "approval_id": _string(manifest.get("approval_id"))
                or _approval_id(APPROVAL_REQUEST_MANIFEST_SOURCE_KIND, source_ref),
                "source_kind": APPROVAL_REQUEST_MANIFEST_SOURCE_KIND,
                "source_ref": source_ref,
                "title": _string(manifest.get("title")) or f"Review approval request {Path(source_ref).stem}",
                "detail": _string(manifest.get("detail") or manifest.get("summary") or manifest.get("reason"))
                or "Approval request manifest is pending.",
                "status": "pending",
                "action_kind": action_kind,
                "severity": severity,
                "owner_driver": _string(manifest.get("owner_driver") or manifest.get("owner")) or None,
                "artifacts": artifacts,
                "command": _string(manifest.get("command")) or None,
                "operation": _safe_mapping(manifest.get("operation")) or None,
                "metadata": metadata,
                "source_state_hash": _stable_json_hash(digest),
                "opened_at": _string(
                    manifest.get("opened_at")
                    or manifest.get("requested_at")
                    or manifest.get("created_at")
                    or manifest.get("updated_at")
                )
                or None,
                "updated_at": _string(manifest.get("updated_at") or manifest.get("requested_at") or manifest.get("created_at"))
                or None,
                "surface_route": _string(manifest.get("surface_route")) or "/station/approvals",
                "surface_label": _string(manifest.get("surface_label")) or "Approval requests",
            }
        )
    return rows


def _project_type_a_seat_dispatch(repo_root: Path) -> list[dict[str, Any]]:
    from system.lib import type_a_seat_control  # local import avoids a registry/router cycle

    rows: list[dict[str, Any]] = []
    for request_path, request in type_a_seat_control.iter_pending_approval_requests(repo_root):
        source_ref = _relative(repo_root, request_path) or request_path.as_posix()
        metadata = type_a_seat_control.build_approval_metadata(request)
        provider = _string(metadata.get("provider")) or "provider"
        model = _string(metadata.get("model")) or "model"
        thread_policy = _string(metadata.get("thread_policy")) or "thread"
        presence = _string(metadata.get("presence_mode")) or "attended"
        digest = {
            "request_id": metadata.get("request_id"),
            "status": metadata.get("status"),
            "reason": metadata.get("reason"),
            "provider": provider,
            "seat_class": metadata.get("seat_class"),
            "model": model,
            "thread_policy": thread_policy,
            "approval_mode": metadata.get("approval_mode"),
            "presence_mode": presence,
            "prompt_artifact": metadata.get("prompt_artifact"),
            "transform_job_path": metadata.get("transform_job_path"),
            "free_only": metadata.get("free_only"),
            "allow_paid": metadata.get("allow_paid"),
            "updated_at": request.get("updated_at"),
        }
        seat_class = _string(metadata.get("seat_class")) or "seat"
        budget_note = ""
        if provider in {"openrouter_api", "nvidia_nim"}:
            budget_note = (
                f" Budget free_only={metadata.get('free_only')} "
                f"allow_paid={metadata.get('allow_paid')} max_usd={metadata.get('max_usd')}."
            )
        rows.append(
            {
                "approval_id": _approval_id("type_a_seat_dispatch", source_ref),
                "source_kind": "type_a_seat_dispatch",
                "source_ref": source_ref,
                "title": f"Approve Type A seat {metadata.get('seat_id') or Path(source_ref).stem}",
                "detail": (
                    f"{provider} / {model} requested {thread_policy.replace('_', ' ')} "
                    f"as {seat_class} while operator presence is {presence}.{budget_note}"
                ),
                "status": "pending",
                "action_kind": "decide",
                "severity": "P1" if provider == "claude_app" else "P2",
                "owner_driver": "type_a_seat_control",
                "artifacts": [
                    item
                    for item in [
                        source_ref,
                        _string(_safe_mapping(request.get("ledger_refs")).get("seat_ledger")),
                        _string(metadata.get("prompt_artifact")),
                        _string(metadata.get("transform_job_path")),
                    ]
                    if item
                ],
                "command": type_a_seat_control.approval_command(repo_root, request_path),
                "operation": None,
                "metadata": metadata,
                "source_state_hash": _stable_json_hash(digest),
                "opened_at": _string(request.get("created_at") or request.get("updated_at")) or None,
                "updated_at": _string(request.get("updated_at")) or None,
                "surface_route": "/station/approvals",
                "surface_label": "Type A seats",
            }
        )
    return rows


def _compute_artifact_approvals_enabled(repo_root: Path) -> bool:
    """Return whether the compute-artifact approvals lane is active.

    Default is OFF (dark ship). Flip by writing
    ``{"compute_artifact_approvals_enabled": true}`` into
    ``state/metabolism/metabolism_config.json``.
    """
    config_path = repo_root / METABOLISM_CONFIG_REL
    if not config_path.exists():
        return False
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(payload, Mapping):
        return False
    return bool(payload.get(COMPUTE_ARTIFACT_APPROVALS_CONFIG_KEY))


def _iter_compute_artifact_receipts(repo_root: Path):
    """Yield (receipt_path, receipt_payload) for every receipt marked for review.

    Walks ``state/compute_workers/receipts/<yyyy-mm>/*.json`` and filters on
    ``approval_review_state == "pending_review"`` — the marker the harness
    stamps for receipts produced outside a seat dispatch.
    """
    receipts_root = repo_root / COMPUTE_RECEIPTS_DIR_REL
    if not receipts_root.exists():
        return
    for month_dir in sorted(receipts_root.iterdir()):
        if not month_dir.is_dir():
            continue
        for path in sorted(month_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(payload, Mapping):
                continue
            if _string(payload.get("approval_review_state")) != "pending_review":
                continue
            yield path, payload


def _project_type_a_compute_artifact(repo_root: Path) -> list[dict[str, Any]]:
    if not _compute_artifact_approvals_enabled(repo_root):
        return []
    rows: list[dict[str, Any]] = []
    for receipt_path, receipt in _iter_compute_artifact_receipts(repo_root):
        source_ref = _relative(repo_root, receipt_path) or receipt_path.as_posix()
        receipt_id = _string(receipt.get("receipt_id")) or Path(source_ref).stem
        provider = _string(receipt.get("provider_id")) or "provider"
        model = _string(receipt.get("model_id")) or "model"
        task_class = _string(receipt.get("task_class")) or "transform"
        promotion_state = _string(receipt.get("promotion_state")) or "draft"
        transform_job_id = _string(receipt.get("transform_job_id"))
        cost = _safe_mapping(receipt.get("cost"))
        metadata = {
            "receipt_id": receipt_id,
            "receipt_path": source_ref,
            "transform_job_id": transform_job_id,
            "provider": provider,
            "model": model,
            "task_class": task_class,
            "promotion_state": promotion_state,
            "cost_amount": cost.get("amount"),
            "cost_unit": cost.get("unit"),
            "http_status": receipt.get("http_status"),
            "latency_ms": receipt.get("latency_ms"),
            "output_digest": _string(receipt.get("output_digest")) or None,
            "row_patch_path": _string(_safe_mapping(receipt.get("artifact_refs")).get("row_patch")) or None,
            "created_at": _string(receipt.get("created_at")) or None,
            "persisted_at": _string(receipt.get("persisted_at")) or None,
        }
        digest = {
            "receipt_id": receipt_id,
            "promotion_state": promotion_state,
            "output_digest": metadata["output_digest"],
            "persisted_at": metadata["persisted_at"],
        }
        rows.append(
            {
                "approval_id": _approval_id("type_a_compute_artifact", source_ref),
                "source_kind": "type_a_compute_artifact",
                "source_ref": source_ref,
                "title": f"Review compute artifact {receipt_id}",
                "detail": (
                    f"{provider} / {model} produced draft row_patch for task "
                    f"{task_class}. Cost {cost.get('amount')} {cost.get('unit')}."
                ),
                "status": "pending",
                "action_kind": "review_only",
                "severity": "P3",
                "owner_driver": "type_a_worker_harness",
                "artifacts": [
                    item
                    for item in [
                        source_ref,
                        metadata["row_patch_path"],
                    ]
                    if item
                ],
                "command": None,
                "operation": None,
                "metadata": metadata,
                "source_state_hash": _stable_json_hash(digest),
                "opened_at": metadata["created_at"],
                "updated_at": metadata["persisted_at"] or metadata["created_at"],
                "surface_route": "/station/approvals",
                "surface_label": "Type A compute artifacts",
            }
        )
    return rows


def _project_records(repo_root: Path) -> list[dict[str, Any]]:
    orchestration = _load_orchestration_state(repo_root)
    rows: list[dict[str, Any]] = []
    rows.extend(_project_campaign_preview_ready(repo_root))
    rows.extend(_project_orchestration_gate(repo_root, orchestration))
    rows.extend(_project_factory_apply_review(repo_root, orchestration))
    rows.extend(_project_approval_request_manifests(repo_root))
    rows.extend(_project_type_a_seat_dispatch(repo_root))
    rows.extend(_project_type_a_compute_artifact(repo_root))
    return rows


def _reconcile_decision_state(
    decision_state: dict[str, Any],
    projected: list[dict[str, Any]],
) -> dict[str, Any]:
    records = _safe_mapping(decision_state.get("records"))
    now_iso = _iso_now()
    next_records: dict[str, Any] = {}
    for record in projected:
        approval_id = _string(record.get("approval_id"))
        source_hash = _projection_hash(record)
        existing = _safe_mapping(records.get(approval_id))
        if _string(existing.get("source_state_hash")) == source_hash:
            first_seen_at = _string(existing.get("first_seen_at")) or _string(record.get("updated_at")) or now_iso
            status = _string(existing.get("status")) or "pending"
            decided_at = existing.get("decided_at")
            actor_id = existing.get("actor_id")
            reason = existing.get("reason")
        else:
            first_seen_at = _string(record.get("updated_at")) or now_iso
            status = "pending"
            decided_at = None
            actor_id = None
            reason = None
        next_records[approval_id] = {
            "approval_id": approval_id,
            "source_state_hash": source_hash,
            "status": status if status in APPROVAL_STATUS_VALUES else "pending",
            "first_seen_at": first_seen_at,
            "decided_at": decided_at,
            "actor_id": actor_id,
            "reason": reason,
        }
    decision_state["records"] = next_records
    decision_state["updated_at"] = now_iso
    return decision_state


def _record_with_state(
    record: Mapping[str, Any],
    *,
    state_entry: Mapping[str, Any] | None,
    claim: Mapping[str, Any] | None,
    status_override: str | None = None,
) -> dict[str, Any]:
    payload = dict(record)
    payload["opened_at"] = _string((state_entry or {}).get("first_seen_at")) or _string(record.get("opened_at") or record.get("updated_at")) or None
    if status_override:
        payload["status"] = status_override
    elif claim is not None:
        payload["status"] = "claimed"
    else:
        payload["status"] = "pending"
    return payload


def _build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    source_kind_counts: dict[str, int] = {}
    action_kind_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for record in records:
        source_kind = _string(record.get("source_kind")) or "unknown"
        action_kind = _string(record.get("action_kind")) or "unknown"
        status = _string(record.get("status")) or "unknown"
        source_kind_counts[source_kind] = source_kind_counts.get(source_kind, 0) + 1
        action_kind_counts[action_kind] = action_kind_counts.get(action_kind, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
    ordered = _sort_records(records)
    return {
        "total_pending": len([record for record in records if record.get("status") in {"pending", "claimed"}]),
        "source_kind_counts": source_kind_counts,
        "action_kind_counts": action_kind_counts,
        "status_counts": status_counts,
        "top_records": ordered[:3],
    }


def list_approvals(
    repo_root: Path,
    *,
    source_kind: str | None = None,
    status: str | None = None,
    action_kind: str | None = None,
) -> dict[str, Any]:
    paths = approval_paths(repo_root)
    projected = _sort_records(_project_records(repo_root))
    current_hashes = {
        _string(record.get("approval_id")): _projection_hash(record)
        for record in projected
    }
    with _STATE_LOCK:
        decision_state = _reconcile_decision_state(
            _load_decision_state(paths),
            projected,
        )
        claims_payload = _load_claims(paths)
        claims_changed = _cleanup_claims(claims_payload, current_hashes=current_hashes)
        _persist_decision_state(paths, decision_state)
        if claims_changed:
            _persist_claims(paths, claims_payload)

    state_records = _safe_mapping(decision_state.get("records"))
    claims = _safe_mapping(claims_payload.get("claims"))

    visible_records: list[dict[str, Any]] = []
    decided_records: list[dict[str, Any]] = []
    for record in projected:
        approval_id = _string(record.get("approval_id"))
        state_entry = _safe_mapping(state_records.get(approval_id))
        claim = _safe_mapping(claims.get(approval_id))
        same_hash = _string(state_entry.get("source_state_hash")) == _projection_hash(record)
        claim_match = _string(claim.get("source_state_hash")) == _projection_hash(record)
        state_status = _string(state_entry.get("status"))
        if same_hash and state_status in {"approved", "rejected"}:
            decided_records.append(
                _record_with_state(
                    record,
                    state_entry=state_entry,
                    claim=None,
                    status_override=state_status,
                )
            )
            continue
        visible_records.append(
            _record_with_state(
                record,
                state_entry=state_entry,
                claim=claim if claim_match else None,
            )
        )

    records = visible_records
    normalized_status = _string(status)
    if normalized_status in {"approved", "rejected"}:
        records = [record for record in decided_records if record.get("status") == normalized_status]
    elif normalized_status:
        records = [record for record in visible_records if record.get("status") == normalized_status]
    if _string(source_kind):
        records = [record for record in records if _string(record.get("source_kind")) == _string(source_kind)]
    if _string(action_kind):
        records = [record for record in records if _string(record.get("action_kind")) == _string(action_kind)]
    records = _sort_records(records)

    pending_payload = {
        "schema": "approval_list_v1",
        "generated_at": _iso_now(),
        "records": visible_records,
        "summary": _build_summary(visible_records),
    }
    with _STATE_LOCK:
        _write_pending_snapshot(paths, pending_payload)

    return {
        "schema": "approval_list_v1",
        "generated_at": pending_payload["generated_at"],
        "records": records,
        "summary": pending_payload["summary"],
    }


def _acquire_claim(
    paths: ApprovalPaths,
    *,
    approval_id: str,
    source_state_hash: str,
    actor_id: str,
) -> tuple[bool, Optional[dict[str, Any]]]:
    with _STATE_LOCK:
        claims_payload = _load_claims(paths)
        _cleanup_claims(claims_payload)
        claims = _safe_mapping(claims_payload.get("claims"))
        existing = _safe_mapping(claims.get(approval_id))
        if existing and not _claim_expired(existing):
            return False, existing
        claimed_at = datetime.now(timezone.utc)
        claim = {
            "approval_id": approval_id,
            "source_state_hash": source_state_hash,
            "actor_id": actor_id,
            "claimed_at": claimed_at.isoformat(),
            "expires_at": (claimed_at + timedelta(seconds=CLAIM_TTL_SECONDS)).isoformat(),
            "nonce": uuid.uuid4().hex,
        }
        claims[approval_id] = claim
        claims_payload["claims"] = claims
        claims_payload["updated_at"] = claimed_at.isoformat()
        _persist_claims(paths, claims_payload)
        return True, claim


def _release_claim(paths: ApprovalPaths, approval_id: str, nonce: str | None) -> None:
    with _STATE_LOCK:
        claims_payload = _load_claims(paths)
        claims = _safe_mapping(claims_payload.get("claims"))
        existing = _safe_mapping(claims.get(approval_id))
        if existing and (not nonce or _string(existing.get("nonce")) == _string(nonce)):
            claims.pop(approval_id, None)
            claims_payload["claims"] = claims
            claims_payload["updated_at"] = _iso_now()
            _persist_claims(paths, claims_payload)


def _write_decision_overlay(
    paths: ApprovalPaths,
    *,
    approval_id: str,
    source_state_hash: str,
    status: str,
    actor_id: str,
    reason: str | None,
) -> dict[str, Any]:
    with _STATE_LOCK:
        decision_state = _load_decision_state(paths)
        records = _safe_mapping(decision_state.get("records"))
        existing = _safe_mapping(records.get(approval_id))
        updated = {
            "approval_id": approval_id,
            "source_state_hash": source_state_hash,
            "status": status,
            "first_seen_at": _string(existing.get("first_seen_at")) or _iso_now(),
            "decided_at": _iso_now(),
            "actor_id": actor_id,
            "reason": reason,
        }
        records[approval_id] = updated
        decision_state["records"] = records
        decision_state["updated_at"] = _iso_now()
        _persist_decision_state(paths, decision_state)
        return updated


def _overlay_decision_supported(record: Mapping[str, Any]) -> bool:
    if _string(record.get("source_kind")) != APPROVAL_REQUEST_MANIFEST_SOURCE_KIND:
        return False
    metadata = _safe_mapping(record.get("metadata"))
    return _string(metadata.get("decision_mode")) == "overlay_only"


def _overlay_decision_effect(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "decision_mode": "overlay_only",
        "source_kind": _string(record.get("source_kind")),
        "source_ref": _string(record.get("source_ref")),
        "decision_state_ref": DECISION_STATE_REL,
        "ledger_ref": LEDGER_REL,
        "note": "Source-owned lane must consume the approval overlay or ledger before mutating its native state.",
    }


def decide_approval(
    repo_root: Path,
    *,
    approval_id: str,
    decision: str,
    actor_id: str,
    reason: str | None = None,
    approve_callbacks: Mapping[str, Callable[[dict[str, Any], str, str | None], Mapping[str, Any]]] | None = None,
    reject_callbacks: Mapping[str, Callable[[dict[str, Any], str, str | None], Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    normalized_decision = _string(decision).lower()
    actor = _string(actor_id)
    note = _string(reason) or None
    if normalized_decision not in DECISION_VALUES:
        return {"ok": False, "error_code": "invalid_decision", "error": "decision must be approve or reject"}
    if not actor:
        return {"ok": False, "error_code": "actor_required", "error": "actor_id is required"}

    current = list_approvals(repo_root)
    record = next(
        (item for item in current.get("records") or [] if _string(item.get("approval_id")) == approval_id),
        None,
    )
    if not isinstance(record, Mapping):
        return {"ok": False, "error_code": "approval_not_found", "error": f"Unknown approval_id: {approval_id}"}

    action_kind = _string(record.get("action_kind"))
    if action_kind != "decide":
        return {
            "ok": False,
            "error_code": "decision_not_supported",
            "error": "review_only approvals cannot be decided through this endpoint",
        }

    paths = approval_paths(repo_root)
    source_state_hash = _projection_hash(record)
    acquired, claim = _acquire_claim(
        paths,
        approval_id=approval_id,
        source_state_hash=source_state_hash,
        actor_id=actor,
    )
    if not acquired:
        return {
            "ok": False,
            "error_code": "claim_conflict",
            "error": "approval is already being processed",
        }

    try:
        refreshed = list_approvals(repo_root)
        current_record = next(
            (item for item in refreshed.get("records") or [] if _string(item.get("approval_id")) == approval_id),
            None,
        )
        if not isinstance(current_record, Mapping):
            return {
                "ok": False,
                "error_code": "approval_not_found",
                "error": f"Unknown approval_id: {approval_id}",
            }
        if _projection_hash(current_record) != source_state_hash:
            return {
                "ok": False,
                "error_code": "stale_source_state",
                "error": "approval source changed before the decision could be applied",
            }

        effect: Mapping[str, Any] | None = None
        if normalized_decision == "approve":
            callbacks = approve_callbacks or {}
            callback = callbacks.get(_string(current_record.get("source_kind")))
            if callback is None:
                if _overlay_decision_supported(current_record):
                    effect = _overlay_decision_effect(current_record)
                else:
                    return {
                        "ok": False,
                        "error_code": "decision_not_supported",
                        "error": "no approve callback registered for this approval source",
                    }
            else:
                try:
                    effect = callback(dict(current_record), actor, note)
                except Exception as exc:
                    return {
                        "ok": False,
                        "error_code": "callback_failed",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                if not bool(_safe_mapping(effect).get("ok", True)):
                    return {
                        "ok": False,
                        "error_code": "callback_failed",
                        "error": _string(_safe_mapping(effect).get("error")) or "approval callback failed",
                    }
        elif normalized_decision == "reject":
            callbacks = reject_callbacks or {}
            callback = callbacks.get(_string(current_record.get("source_kind")))
            if callback is not None:
                try:
                    effect = callback(dict(current_record), actor, note)
                except Exception as exc:
                    return {
                        "ok": False,
                        "error_code": "callback_failed",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                if not bool(_safe_mapping(effect).get("ok", True)):
                    return {
                        "ok": False,
                        "error_code": "callback_failed",
                        "error": _string(_safe_mapping(effect).get("error")) or "reject callback failed",
                    }

        overlay = _write_decision_overlay(
            paths,
            approval_id=approval_id,
            source_state_hash=source_state_hash,
            status="approved" if normalized_decision == "approve" else "rejected",
            actor_id=actor,
            reason=note,
        )
        event = {
            "kind": "approval_decision",
            "schema_version": "approval_decision_v1",
            "recorded_at": _iso_now(),
            "event_id": f"approval_{uuid.uuid4().hex[:16]}",
            "approval_id": approval_id,
            "decision": normalized_decision,
            "actor_id": actor,
            "reason": note,
            "source_kind": _string(current_record.get("source_kind")),
            "source_ref": _string(current_record.get("source_ref")),
            "action_kind": _string(current_record.get("action_kind")),
            "source_state_hash": source_state_hash,
            "effect": effect or {},
            "overlay": overlay,
        }
        _append_jsonl(paths.ledger, event)
        refreshed = list_approvals(repo_root)
        return {
            "ok": True,
            "decision_event": event,
            "records": refreshed.get("records") or [],
            "summary": refreshed.get("summary") or {},
            "generated_at": refreshed.get("generated_at"),
        }
    finally:
        _release_claim(paths, approval_id, _string(claim.get("nonce")) if isinstance(claim, Mapping) else None)
