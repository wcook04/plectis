"""
[PURPOSE]
- Teleology: Expose a WorkItem-first landing status that makes claim,
  receipt, index, and session finalizers actionable without promoting kernel or
  subphase state back to execution authority.
- Mechanism: Compose the existing mission transaction preflight, Task Ledger
  serial intake state, and shared-index quarantine into a compact read model.
- Non-goal: Landing commits, directly appending ledger events, draining intake,
  or clearing finalizers outside explicit controller actions.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib import task_ledger_events, work_ledger, work_ledger_runtime
from system.lib.mission_transaction_landing_preflight import (
    LOCAL_OWNED_PATH_SETTLEMENT_DEFERRED_REASON,
    build_mission_transaction_landing_preflight,
)
from system.lib.workitem_control_picture import build_workitem_control_picture


STATUS_SCHEMA = "work_landing_status_v0"
RECONCILE_SCHEMA = "work_landing_reconcile_plan_v0"
LEGACY_RECONCILE_SCHEMA = "work_landing_reconcile_dry_run_v0"
ATTEMPT_BINDING_SCHEMA = "work_landing_attempt_binding_v0"
BLOCKED_PATCH_CAPSULE_SCHEMA = "blocked_patch_capsule_v0"
WRITE_ADMISSION_SCHEMA = "workitem_write_admission_v0"
AUTHORITY_RECEIPT_OVERLAY_SCHEMA = "work_landing_authority_execution_receipt_overlay_v0"

RECEIPT_INTAKE_ACTION_ID = "ensure_task_ledger_receipt_intake_or_event"
RECEIPT_INTAKE_APPLY_ALIASES = {RECEIPT_INTAKE_ACTION_ID, "receipt_intake"}
RECORD_SCOPED_COMMIT_LANDING_ACTION_ID = "record_scoped_commit_landing"
RECORD_SCOPED_COMMIT_LANDING_ALIASES = {
    RECORD_SCOPED_COMMIT_LANDING_ACTION_ID,
    "attach_commit_hash_to_attempt",
    "commit_landing",
}
CLOSEOUT_LANDING_ATTEMPT_ACTION_ID = "closeout_landing_attempt"
CLOSEOUT_LANDING_ATTEMPT_ALIASES = {
    CLOSEOUT_LANDING_ATTEMPT_ACTION_ID,
    "landing_closeout",
    "closeout",
}
LAND_SCOPED_COMMIT_ATTEMPT_ACTION_ID = "land_scoped_commit_attempt"
LAND_SCOPED_COMMIT_ATTEMPT_ALIASES = {
    LAND_SCOPED_COMMIT_ATTEMPT_ACTION_ID,
    "land_scoped_commit",
    "commit_and_closeout",
}
WORK_LANDING_APPEND_PROJECTION_MODE = "append_event_target_only"
TRANSACTION_READINESS_SCHEMA = "work_landing_transaction_readiness_contract_v0"
WRITE_READINESS_SCHEMA = "workitem_write_readiness_contract_v0"
RECEIPT_INTAKE_READY_OUTCOMES = {
    "receipt_ready_to_record",
    "receipt_blocked_claim_collision",
    "receipt_blocked_same_file_entanglement",
}

ORDERED_CONTROLLER_ACTION_IDS = [
    "verify_scoped_commit_landed",
    "ensure_work_ledger_progress_event",
    LAND_SCOPED_COMMIT_ATTEMPT_ACTION_ID,
    RECORD_SCOPED_COMMIT_LANDING_ACTION_ID,
    RECEIPT_INTAKE_ACTION_ID,
    "drain_task_ledger_intake_if_exclusive",
    CLOSEOUT_LANDING_ATTEMPT_ACTION_ID,
    "rebuild_task_ledger_projection",
    "check_work_ledger_projection",
    "close_work_ledger_transaction_thread",
    "finalize_work_ledger_session",
    "release_claims",
    "recompute_convergence",
]

CONTROLLER_ACTION_PREREQUISITES = {
    "release_claims": ["finalize_work_ledger_session"],
    "recompute_convergence": ["release_claims"],
}
CONTROLLER_ACTION_ORDER_GUARDS = {
    "release_claims": "claim_release_after_work_ledger_session_finalize_only",
    "recompute_convergence": "convergence_after_claim_release_only",
}
CONTROLLER_ACTION_ROW_EXTRAS = {
    "finalize_work_ledger_session": {
        "also_satisfies_action_ids": ["release_claims"],
        "claim_release_mode": "work_ledger_runtime.finalize_session_release_claims_true",
    },
    "release_claims": {
        "satisfaction_source_action_id": "finalize_work_ledger_session",
    },
}


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


FINALIZER_POLICIES: dict[str, dict[str, str]] = {
    "task_ledger_execution_receipt": {
        "owner_plane": "task_ledger_intake",
        "gate_class": "real_gate",
        "clearing_surface": "tools/meta/factory/task_ledger_apply.py enqueue-execution-receipt | drain-intake | record-execution-receipt",
    },
    "claims_released": {
        "owner_plane": "work_ledger_claims",
        "gate_class": "real_gate",
        "clearing_surface": "tools/meta/factory/work_ledger.py session-finalize | session-release-claim",
    },
    "staged_index_empty": {
        "owner_plane": "git_index_owner",
        "gate_class": "external_pressure",
        "clearing_surface": "tools/meta/control/scoped_commit.py | owner-drained shared index",
    },
    "session_not_stale_or_exempt": {
        "owner_plane": "work_ledger_session",
        "gate_class": "real_gate",
        "clearing_surface": "tools/meta/factory/work_ledger.py session-sweep | session-finalize",
    },
    "work_ledger_append_or_exempt": {
        "owner_plane": "work_ledger_event_log",
        "gate_class": "real_gate",
        "clearing_surface": "tools/meta/factory/work_ledger.py progress | close | append-open",
    },
    "generated_projection_fresh": {
        "owner_plane": "generated_projection_owner",
        "gate_class": "projection_gate",
        "clearing_surface": "owning projection builder --check/--rebuild",
    },
}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    return [dict(item) for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _first(values: Sequence[Any]) -> Any | None:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _strings(values: Sequence[Any] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return _strings([value])
    if isinstance(value, Sequence):
        return _strings(value)
    return _strings([value] if value not in (None, "", [], {}) else [])


def _first_string(values: Sequence[Any] | None) -> str | None:
    for value in values or []:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _unique_strings(values: Sequence[Any] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _subject_exists(repo_root: Path, subject_id: str) -> bool:
    token = str(subject_id or "").strip()
    if not token:
        return False
    path = repo_root / "state/task_ledger/ledger.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _subject_exists_in_task_ledger_authority(repo_root, token)
    if not isinstance(payload, Mapping):
        return _subject_exists_in_task_ledger_authority(repo_root, token)
    rows = payload.get("work_items") if isinstance(payload.get("work_items"), list) else None
    if rows is None:
        ledger = payload.get("ledger") if isinstance(payload.get("ledger"), Mapping) else {}
        rows = ledger.get("work_items") if isinstance(ledger, Mapping) else []
    if any(isinstance(row, Mapping) and str(row.get("id") or "").strip() == token for row in rows or []):
        return True
    return _subject_exists_in_task_ledger_authority(repo_root, token)


def _subject_exists_in_task_ledger_authority(repo_root: Path, subject_id: str) -> bool:
    token = str(subject_id or "").strip()
    if not token:
        return False
    path = repo_root / task_ledger_events.EVENTS_REL
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, Mapping):
            continue
        if str(event.get("subject_id") or "").strip() != token:
            continue
        event_type = str(event.get("event_type") or "")
        subject_kind = str(event.get("subject_kind") or "")
        if subject_kind == "work_item" or event_type.startswith("work_item."):
            return True
    return False


def _safe_slug(value: str, *, fallback: str = "agent") -> str:
    slug = re.sub(r"[^A-Za-z0-9_.:-]+", "_", str(value or "").strip()).strip("_")
    return (slug or fallback)[:36]


def _attempt_idempotency_key(
    *,
    subject_id: str,
    base_head: str,
    owned_paths: Sequence[str],
    created_by: str,
) -> str:
    payload = {
        "schema": ATTEMPT_BINDING_SCHEMA,
        "subject_id": subject_id,
        "base_head": base_head,
        "owned_paths": list(owned_paths),
        "created_by": created_by,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"{subject_id}:work_landing_attempt:{base_head or 'no_head'}:{digest}"


def _derived_session_id(
    *,
    subject_id: str,
    base_head: str,
    owned_paths: Sequence[str],
    created_by: str,
) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {
                "subject_id": subject_id,
                "base_head": base_head,
                "owned_paths": list(owned_paths),
                "created_by": created_by,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:14]
    return f"{_safe_slug(created_by)}_work_landing_{digest}"


def _current_git_head(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception:
        return ""
    return result.stdout.strip()


def _run_git_bytes(repo_root: Path, args: Sequence[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _scoped_diff_bytes(repo_root: Path, owned_paths: Sequence[str]) -> tuple[bytes, str | None]:
    paths = [path.strip("/") for path in _unique_strings(owned_paths)]
    if not paths:
        return b"", "owned_path_required"
    result = _run_git_bytes(repo_root, ["diff", "--binary", "--", *paths])
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        return b"", error or f"git_diff_exit_{result.returncode}"
    return result.stdout, None


def _git_apply_cached_check(repo_root: Path, patch_bytes: bytes) -> dict[str, Any]:
    if not patch_bytes:
        return {
            "command": "git apply --cached --check -",
            "result": "skipped",
            "reason": "empty_patch",
            "index_mutated": False,
        }
    result = _run_git_bytes(repo_root, ["apply", "--cached", "--check", "-"], input_bytes=patch_bytes)
    payload = {
        "command": "git apply --cached --check -",
        "result": "passed" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "index_mutated": False,
    }
    if result.stderr:
        payload["stderr"] = result.stderr.decode("utf-8", errors="replace").strip()[:4000]
    return payload


def _blocked_patch_capsule_paths(repo_root: Path, capsule_id: str) -> dict[str, Path]:
    capsule_dir = repo_root / "state" / "blocked_patch_capsules" / capsule_id
    return {
        "dir": capsule_dir,
        "patch": capsule_dir / "patch.diff",
        "manifest": capsule_dir / "manifest.json",
        "handoff": capsule_dir / "handoff.md",
    }


def _blocking_session_ids(collisions: Sequence[Mapping[str, Any]]) -> list[str]:
    return _strings([collision.get("session_id") for collision in collisions])


def _blocking_claim_ids(collisions: Sequence[Mapping[str, Any]]) -> list[str]:
    claim_ids: list[str] = []
    for collision in collisions:
        claim_id = str(collision.get("claim_id") or "").strip()
        if not claim_id:
            claim_id = str(_mapping(collision.get("claim")).get("claim_id") or "").strip()
        if claim_id and claim_id not in claim_ids:
            claim_ids.append(claim_id)
    return claim_ids


def _create_blocked_patch_capsule(
    repo_root: Path,
    *,
    subject_id: str,
    owned_paths: Sequence[str],
    session_id: str,
    base_head: str,
    collisions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    patch_bytes, diff_error = _scoped_diff_bytes(repo_root, owned_paths)
    if diff_error:
        return {
            "schema": BLOCKED_PATCH_CAPSULE_SCHEMA,
            "status": "not_created",
            "reason": "scoped_diff_unavailable",
            "error": diff_error,
        }
    if not patch_bytes.strip():
        return {
            "schema": BLOCKED_PATCH_CAPSULE_SCHEMA,
            "status": "not_created",
            "reason": "no_scoped_diff_for_owned_paths",
        }

    patch_sha = hashlib.sha256(patch_bytes).hexdigest()
    subject_slug = _safe_slug(subject_id, fallback="blocked_patch")
    head_slug = _safe_slug((base_head or "no_head")[:12], fallback="no_head")
    capsule_id = f"{subject_slug}_{head_slug}_{patch_sha[:12]}"
    paths = _blocked_patch_capsule_paths(repo_root, capsule_id)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    paths["patch"].write_bytes(patch_bytes)

    apply_check = _git_apply_cached_check(repo_root, patch_bytes)
    blockers = [dict(collision) for collision in collisions]
    adoption_targets = _blocking_session_ids(blockers)
    claim_ids = _blocking_claim_ids(blockers)
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema": BLOCKED_PATCH_CAPSULE_SCHEMA,
        "capsule_id": capsule_id,
        "status": "queued",
        "created_at": created_at,
        "subject_id": subject_id,
        "owned_paths": list(owned_paths),
        "base_head": base_head,
        "current_head_at_capsule_creation": _current_git_head(repo_root),
        "patch_sha256": patch_sha,
        "patch_path": str(paths["patch"].relative_to(repo_root)),
        "manifest_path": str(paths["manifest"].relative_to(repo_root)),
        "handoff_path": str(paths["handoff"].relative_to(repo_root)),
        "blocking_session_ids": adoption_targets,
        "blocking_claim_ids": claim_ids,
        "blocked_by": blockers,
        "adoption_target": adoption_targets[0] if len(adoption_targets) == 1 else None,
        "adoption_targets": adoption_targets,
        "intended_commit_message": f"Land {subject_id}",
        "apply_check_result": apply_check,
        "proof_receipts": [],
        "proof_staleness_note": "Capsule records patch replayability only; rerun validation after adoption or reclaim.",
        "adoption_owner_obligation": (
            "Adopt/apply the patch, rerun relevant validation, then either land, supersede with reason, "
            "or release the blocking claim."
        ),
        "replay": {
            "commands": [
                f"git apply --index {paths['patch'].relative_to(repo_root)}",
                "./repo-python tools/meta/control/work_landing.py begin --subject-id "
                f"{subject_id} --owned-path <repeat-owned-paths> --session-id <claim-owner-or-new-session>",
            ],
        },
    }
    paths["manifest"].write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["handoff"].write_text(
        "# Blocked Patch Capsule\n\n"
        f"- Capsule: `{capsule_id}`\n"
        f"- Subject: `{subject_id}`\n"
        f"- Patch: `{paths['patch'].relative_to(repo_root)}`\n"
        f"- SHA-256: `{patch_sha}`\n"
        f"- Base HEAD: `{base_head}`\n"
        f"- Adoption target: `{manifest['adoption_target'] or ','.join(adoption_targets)}`\n"
        "- Status: queued behind active Work Landing claim collision.\n",
        encoding="utf-8",
    )
    return {
        "schema": BLOCKED_PATCH_CAPSULE_SCHEMA,
        "status": "queued",
        "capsule_id": capsule_id,
        "patch_sha256": patch_sha,
        "patch_path": str(paths["patch"].relative_to(repo_root)),
        "manifest_path": str(paths["manifest"].relative_to(repo_root)),
        "handoff_path": str(paths["handoff"].relative_to(repo_root)),
        "adoption_target": manifest["adoption_target"],
        "adoption_targets": adoption_targets,
        "blocking_claim_ids": claim_ids,
        "apply_check_result": apply_check,
    }


def _json_digest(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except TypeError:
        raw = json.dumps(str(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _landing_transaction_id(
    *,
    subject_id: str,
    session_id: str,
    base_head: str,
    phase_id: str,
) -> str:
    subject_short = re.sub(r"[^A-Za-z0-9]+", "_", str(subject_id or "").strip()).strip("_")
    subject_short = (subject_short or "subject")[:48]
    session_short = hashlib.sha256(str(session_id or "no_session").encode("utf-8")).hexdigest()[:8]
    head = str(base_head or "nohead")[:8]
    phase = re.sub(r"[^A-Za-z0-9]+", "_", str(phase_id or "").strip()).strip("_")
    phase = (phase or "no_phase")[:24]
    return f"mtx_{phase}_{subject_short}_{session_short}_{head}"


def _begin_transaction_candidate(
    *,
    subject_id: str,
    session_id: str,
    read_receipt_id: str,
    phase_id: str,
    base_head: str,
    owned_paths: Sequence[str],
    claim_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    claim_ids = [
        str(_mapping(result.get("claim")).get("claim_id") or "")
        for result in claim_results
        if str(_mapping(result.get("claim")).get("claim_id") or "").strip()
    ]
    read_set = {
        "schema": "work_landing_begin_read_set_v0",
        "base_head": base_head,
        "subject_id": subject_id,
        "work_ledger_session_id": session_id,
        "work_ledger_read_receipt_id": read_receipt_id,
        "claim_ids": claim_ids,
        "owned_paths": list(owned_paths),
    }
    write_set = {
        "schema": "work_landing_begin_write_set_v0",
        "repo_paths": [
            {
                "path": path,
                "claim_mode": "required_exclusive",
            }
            for path in owned_paths
        ],
        "work_ledger_mutations": [
            {
                "session_id": session_id,
                "required": True,
                "kind": "claim_or_finalize",
            }
        ],
    }
    return {
        "schema": "transaction_candidate_v0",
        "transaction_id": _landing_transaction_id(
            subject_id=subject_id,
            session_id=session_id,
            base_head=base_head,
            phase_id=phase_id,
        ),
        "status": "candidate_ready",
        "task_ledger_subjects": [subject_id],
        "work_ledger_session_id": session_id,
        "work_ledger_read_receipt_id": read_receipt_id,
        "phase_id": phase_id,
        "base_head": base_head,
        "read_set_hash": _json_digest(read_set),
        "write_set_hash": _json_digest(write_set),
        "read_set": read_set,
        "write_set": write_set,
        "candidate_profile": "work_landing_begin_compact_v0",
    }


def _parse_iso_datetime(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _path_overlaps(left: str, right: str) -> bool:
    left_parts = tuple(part for part in str(left or "").strip("/").split("/") if part)
    right_parts = tuple(part for part in str(right or "").strip("/").split("/") if part)
    if not left_parts or not right_parts:
        return False
    return left_parts == right_parts or left_parts[: len(right_parts)] == right_parts or right_parts[: len(left_parts)] == left_parts


def _active_claim_collisions(
    repo_root: Path,
    *,
    session_id: str,
    subject_id: str,
    owned_paths: Sequence[str],
) -> list[dict[str, Any]]:
    status = work_ledger_runtime.load_runtime_status(repo_root)
    sessions = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    now = datetime.now(timezone.utc)
    collisions: list[dict[str, Any]] = []
    for other_session_id, session in sessions.items():
        if str(other_session_id) == str(session_id) or not isinstance(session, Mapping) or session.get("ended_at"):
            continue
        for claim in session.get("claims") or []:
            if not isinstance(claim, Mapping) or claim.get("released_at") or claim.get("expired_at"):
                continue
            leased_until = _parse_iso_datetime(claim.get("leased_until"))
            if leased_until is not None and leased_until <= now:
                continue
            scope_kind = str(claim.get("scope_kind") or "").strip()
            scope_id = str(claim.get("scope_id") or "").strip()
            if scope_kind == work_ledger_runtime.CLAIM_SCOPE_WORK_ITEM and scope_id == subject_id:
                collisions.append(
                    {
                        "scope_kind": scope_kind,
                        "scope_id": scope_id,
                        "session_id": str(other_session_id),
                        "actor": session.get("actor"),
                        "claim_id": claim.get("claim_id"),
                        "leased_until": claim.get("leased_until"),
                    }
                )
            if scope_kind == work_ledger_runtime.CLAIM_SCOPE_PATH:
                claim_path = str(claim.get("path") or scope_id).strip("/")
                for path in owned_paths:
                    if _path_overlaps(path, claim_path):
                        collisions.append(
                            {
                                "scope_kind": scope_kind,
                                "scope_id": claim_path,
                                "requested_path": path,
                                "session_id": str(other_session_id),
                                "actor": session.get("actor"),
                                "claim_id": claim.get("claim_id"),
                                "leased_until": claim.get("leased_until"),
                            }
                        )
    return collisions


def _default_work_ledger_context(repo_root: Path) -> dict[str, str]:
    try:
        return work_ledger.resolve_active_phase_context(repo_root)
    except Exception:
        return {"phase_id": "09_52", "family_id": "09"}


def _runtime_session(repo_root: Path, session_id: str) -> dict[str, Any] | None:
    status = work_ledger_runtime.load_runtime_status(repo_root)
    sessions = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    session = sessions.get(str(session_id or "").strip())
    if not isinstance(session, Mapping) or session.get("ended_at"):
        return None
    return dict(session)


def _runtime_session_any(repo_root: Path, session_id: str) -> dict[str, Any] | None:
    status = work_ledger_runtime.load_runtime_status(repo_root)
    sessions = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    session = sessions.get(str(session_id or "").strip())
    if not isinstance(session, Mapping):
        return None
    return dict(session)


def _active_claim_for_scope(
    repo_root: Path,
    *,
    session_id: str,
    scope_kind: str,
    scope_id: str,
) -> dict[str, Any] | None:
    status = work_ledger_runtime.load_runtime_status(repo_root)
    sessions = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    session = sessions.get(str(session_id or "").strip())
    if not isinstance(session, Mapping) or session.get("ended_at"):
        return None
    for claim in session.get("claims") or []:
        if not isinstance(claim, Mapping):
            continue
        if claim.get("released_at") or claim.get("expired_at"):
            continue
        if str(claim.get("scope_kind") or "").strip() != scope_kind:
            continue
        if str(claim.get("scope_id") or "").strip().strip("/") == str(scope_id or "").strip().strip("/"):
            return dict(claim)
    return None


def _active_claim_for_scope_in_session(
    session: Mapping[str, Any] | None,
    *,
    scope_kind: str,
    scope_id: str,
) -> dict[str, Any] | None:
    if not isinstance(session, Mapping) or session.get("ended_at"):
        return None
    for claim in session.get("claims") or []:
        if not isinstance(claim, Mapping):
            continue
        if claim.get("released_at") or claim.get("expired_at"):
            continue
        if str(claim.get("scope_kind") or "").strip() != scope_kind:
            continue
        if str(claim.get("scope_id") or "").strip().strip("/") == str(scope_id or "").strip().strip("/"):
            return dict(claim)
    return None


def _active_session_path_claims(repo_root: Path, *, session_id: str) -> list[dict[str, Any]]:
    session = _runtime_session(repo_root, session_id)
    if not session:
        return []
    rows: list[dict[str, Any]] = []
    for claim in session.get("claims") or []:
        if not isinstance(claim, Mapping):
            continue
        if claim.get("released_at") or claim.get("expired_at"):
            continue
        if str(claim.get("scope_kind") or "").strip() != work_ledger_runtime.CLAIM_SCOPE_PATH:
            continue
        path = str(_first([claim.get("path"), claim.get("scope_id")]) or "").strip().strip("/")
        if not path:
            continue
        row = dict(claim)
        row["path"] = path
        row["scope_id"] = str(row.get("scope_id") or path).strip().strip("/")
        rows.append(row)
    return rows


def _effective_attempt_owned_paths(repo_root: Path, *, attempt: Mapping[str, Any]) -> list[str]:
    session_id = str(attempt.get("session_id") or "").strip()
    claim_paths = [
        str(_first([claim.get("path"), claim.get("scope_id")]) or "").strip().strip("/")
        for claim in _active_session_path_claims(repo_root, session_id=session_id)
    ]
    return _unique_strings([*_strings(attempt.get("owned_paths") or []), *claim_paths])


def _claim_or_reuse(
    repo_root: Path,
    *,
    session_id: str,
    scope_kind: str,
    scope_id: str,
    lease_minutes: float,
    note: str,
    session_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    existing = _active_claim_for_scope_in_session(
        session_snapshot,
        scope_kind=scope_kind,
        scope_id=scope_id,
    )
    if existing is None:
        existing = _active_claim_for_scope(
            repo_root,
            session_id=session_id,
            scope_kind=scope_kind,
            scope_id=scope_id,
        )
    if existing:
        return {
            "schema": "work_ledger_claim_result_v1",
            "status": "already_claimed",
            "session_id": session_id,
            "scope_kind": scope_kind,
            "scope_id": str(scope_id or "").strip().strip("/"),
            "claim": dict(existing),
            "collisions": [],
        }
    if scope_kind == work_ledger_runtime.CLAIM_SCOPE_WORK_ITEM:
        return work_ledger_runtime.claim_work_item(
            repo_root,
            session_id=session_id,
            work_item_id=scope_id,
            lease_minutes=lease_minutes,
            note=note,
            require_exclusive=True,
        )
    if scope_kind == work_ledger_runtime.CLAIM_SCOPE_PATH:
        return work_ledger_runtime.claim_work_path(
            repo_root,
            session_id=session_id,
            path=scope_id,
            lease_minutes=lease_minutes,
            note=note,
            require_exclusive=True,
        )
    if scope_kind == work_ledger_runtime.CLAIM_SCOPE_THREAD:
        return work_ledger_runtime.claim_work_thread(
            repo_root,
            session_id=session_id,
            td_id=scope_id,
            lease_minutes=lease_minutes,
            note=note,
            require_exclusive=True,
        )
    raise ValueError(f"unsupported claim scope {scope_kind!r}")


def _attempt_metadata_from_thread(thread: Mapping[str, Any]) -> dict[str, Any]:
    metadata = _mapping(thread.get("metadata"))
    attempt = _mapping(metadata.get("work_landing_attempt"))
    if not attempt:
        return {}
    return {
        "schema": attempt.get("schema") or ATTEMPT_BINDING_SCHEMA,
        "status": attempt.get("status") or "active",
        "subject_id": attempt.get("subject_id"),
        "transaction_id": attempt.get("transaction_id"),
        "session_id": attempt.get("session_id"),
        "read_receipt_id": attempt.get("read_receipt_id"),
        "td_id": thread.get("td_id"),
        "phase_id": thread.get("phase_id"),
        "family_id": thread.get("family_id"),
        "base_head": attempt.get("base_head"),
        "read_set_hash": attempt.get("read_set_hash"),
        "write_set_hash": attempt.get("write_set_hash"),
        "owned_paths": list(attempt.get("owned_paths") or []),
        "claim_ids": list(attempt.get("claim_ids") or []),
        "idempotency_key": attempt.get("idempotency_key"),
        "subject_authority_override": attempt.get("subject_authority_override"),
        "commit_hash": attempt.get("commit_hash"),
        "landing_action": attempt.get("landing_action"),
        "pre_mutation_transaction_id": attempt.get("pre_mutation_transaction_id"),
    }


def _normalized_owned_path_set(paths: Sequence[Any]) -> set[str]:
    return {str(path or "").strip().strip("/") for path in paths if str(path or "").strip().strip("/")}


def _attempt_covers_requested_paths(attempt: Mapping[str, Any], requested_paths: set[str]) -> bool:
    if not requested_paths:
        return True
    return requested_paths.issubset(_normalized_owned_path_set(attempt.get("owned_paths") or []))


def _find_attempt_thread(
    repo_root: Path,
    *,
    phase_id: str,
    family_id: str,
    idempotency_key: str | None = None,
    transaction_id: str | None = None,
    subject_id: str | None = None,
    session_id: str | None = None,
    requested_owned_paths: Sequence[str] = (),
    include_closed: bool = False,
) -> dict[str, Any] | None:
    try:
        projection = work_ledger.load_projection(repo_root, phase_id=phase_id, family_id=family_id)
    except Exception:
        return None
    threads = projection.get("threads") if isinstance(projection.get("threads"), Mapping) else {}
    requested_paths = _normalized_owned_path_set(requested_owned_paths)
    fallback_thread: dict[str, Any] | None = None
    noncovering_exact_thread: dict[str, Any] | None = None
    sorted_threads = sorted(
        [dict(thread) for thread in threads.values() if isinstance(thread, Mapping)],
        key=lambda thread: str(thread.get("last_event_at") or thread.get("opened_at") or ""),
        reverse=True,
    )
    for thread in sorted_threads:
        if not isinstance(thread, Mapping):
            continue
        if not include_closed and str(thread.get("status") or "") != "open":
            continue
        attempt = _attempt_metadata_from_thread(thread)
        if not attempt:
            continue
        if idempotency_key and str(attempt.get("idempotency_key") or "") == idempotency_key:
            return dict(thread)
        if idempotency_key:
            continue
        if (
            transaction_id
            and subject_id
            and session_id
            and str(attempt.get("transaction_id") or "") == transaction_id
            and str(attempt.get("subject_id") or "") == subject_id
            and str(attempt.get("session_id") or "") == session_id
        ):
            if _attempt_covers_requested_paths(attempt, requested_paths):
                return dict(thread)
            if noncovering_exact_thread is None:
                noncovering_exact_thread = dict(thread)
            continue
        if (
            subject_id
            and session_id
            and str(attempt.get("subject_id") or "") == subject_id
            and str(attempt.get("session_id") or "") == session_id
        ):
            if _attempt_covers_requested_paths(attempt, requested_paths):
                return dict(thread)
            if fallback_thread is None:
                fallback_thread = dict(thread)
    return noncovering_exact_thread or fallback_thread


def _attempt_binding_from_work_ledger(
    repo_root: Path,
    *,
    preflight: Mapping[str, Any],
    subject_id: str | None,
    session_id: str | None,
    requested_owned_paths: Sequence[str] = (),
) -> dict[str, Any] | None:
    transaction = _mapping(preflight.get("transaction_candidate"))
    phase_id = str(_first([preflight.get("phase_id"), transaction.get("phase_id"), "09_52"]) or "09_52")
    family_id = str(_first([preflight.get("family_id"), transaction.get("family_id"), "09"]) or "09")
    thread = _find_attempt_thread(
        repo_root,
        phase_id=phase_id,
        family_id=family_id,
        transaction_id=str(transaction.get("transaction_id") or ""),
        subject_id=subject_id,
        session_id=session_id,
        requested_owned_paths=requested_owned_paths,
        include_closed=True,
    )
    if not thread:
        return None
    attempt = _attempt_metadata_from_thread(thread)
    current_transaction_id = str(transaction.get("transaction_id") or "").strip()
    if current_transaction_id and str(attempt.get("transaction_id") or "") != current_transaction_id:
        attempt["binding_relation"] = "session_subject_fallback"
        attempt["current_transaction_id"] = current_transaction_id
    else:
        attempt["binding_relation"] = "exact_transaction"
    return attempt


def _compact_bootstrap(bootstrap: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: bootstrap.get(key)
        for key in ("schema", "status", "session_id", "actor", "phase_id", "family_id", "read_receipt_id")
        if bootstrap.get(key) not in (None, "", [], {})
    }


def _compact_work_ledger_event_result(result: Mapping[str, Any] | None) -> dict[str, Any]:
    if not result:
        return {}
    event = _mapping(result.get("event"))
    return {
        "ok": bool(result.get("ok")),
        "event_id": event.get("event_id"),
        "td_id": event.get("td_id"),
        "event_kind": event.get("event_kind"),
        "projection_mode": result.get("projection_mode"),
        "raw_path": result.get("raw_path"),
    }


def _compact_intake_status(repo_root: Path) -> dict[str, Any]:
    try:
        status = task_ledger_events.task_ledger_intake_status(repo_root)
    except Exception as exc:
        return {
            "available": False,
            "reason": str(exc),
        }
    requests = _list_of_mappings(status.get("requests"))
    pending = [row for row in requests if str(row.get("_intake_status") or "") == "pending"]
    blocked = [row for row in requests if str(row.get("_intake_status") or "") == "blocked"]
    return {
        "available": True,
        "schema": status.get("schema"),
        "root": status.get("root"),
        "counts": status.get("counts") or {},
        "pending_preview": [
            {
                "request_id": row.get("request_id"),
                "subject_id": row.get("subject_id"),
                "idempotency_key": row.get("idempotency_key"),
                "path": row.get("_intake_path"),
            }
            for row in pending[:5]
        ],
        "blocked_preview": [
            {
                "request_id": row.get("request_id"),
                "subject_id": row.get("subject_id"),
                "idempotency_key": row.get("idempotency_key"),
                "path": row.get("_intake_path"),
            }
            for row in blocked[:5]
        ],
    }


def _build_work_landing_preflight(
    repo_root: Path,
    *,
    owned_paths: Sequence[str],
    target_ids: Sequence[str],
    session_id: str | None,
    require_exclusive: bool,
) -> dict[str, Any]:
    return build_mission_transaction_landing_preflight(
        repo_root,
        owned_paths=list(owned_paths),
        target_ids=list(target_ids),
        session_id=session_id,
        require_exclusive=require_exclusive,
        include_push_bloat_gate=False,
        include_generated_projection_settlement=False,
        generated_projection_settlement_deferred_reason=LOCAL_OWNED_PATH_SETTLEMENT_DEFERRED_REASON,
    )


def _append_unique(out: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in out:
        out.append(text)


def _receipt_merge_key(receipt: Mapping[str, Any]) -> tuple[str, str]:
    source_event_id = str(receipt.get("source_event_id") or "").strip()
    if source_event_id:
        return ("event", source_event_id)
    transaction_id = str(receipt.get("transaction_id") or receipt.get("id") or "").strip()
    commit_hash = str(receipt.get("commit_hash") or "").strip()
    if transaction_id or commit_hash:
        return ("identity", f"{transaction_id}:{commit_hash}")
    return ("receipt", _json_digest(receipt))


def _task_ledger_authority_execution_receipt_overlay(
    repo_root: Path,
    *,
    subject_ids: Sequence[str],
) -> dict[str, Any]:
    subjects = _unique_strings(subject_ids)
    if not subjects:
        return {
            "schema": AUTHORITY_RECEIPT_OVERLAY_SCHEMA,
            "status": "not_requested",
            "source": str(task_ledger_events.EVENTS_REL),
            "subject_ids": [],
        }
    path = repo_root / task_ledger_events.EVENTS_REL
    if not path.exists():
        return {
            "schema": AUTHORITY_RECEIPT_OVERLAY_SCHEMA,
            "status": "event_log_missing",
            "source": str(task_ledger_events.EVENTS_REL),
            "subject_ids": subjects,
        }

    subject_set = set(subjects)
    event_ids: list[str] = []
    receipt_refs: list[str] = []
    commit_refs: list[str] = []
    work_ledger_refs: list[str] = []
    receipts: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {
            "schema": AUTHORITY_RECEIPT_OVERLAY_SCHEMA,
            "status": "event_log_unreadable",
            "source": str(task_ledger_events.EVENTS_REL),
            "subject_ids": subjects,
            "error": str(exc),
        }

    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, Mapping):
            continue
        if str(event.get("event_type") or "").strip() != "work_item.execution_receipt_recorded":
            continue
        payload = _mapping(event.get("payload"))
        subject_id = str(_first([event.get("subject_id"), payload.get("subject_id")]) or "").strip()
        if subject_id not in subject_set:
            continue
        raw_receipt = payload.get("execution_receipt") or payload.get("receipt")
        if not isinstance(raw_receipt, Mapping):
            continue

        receipt = dict(raw_receipt)
        event_id = str(event.get("event_id") or "").strip()
        receipt_id = str(_first([receipt.get("id"), receipt.get("transaction_id"), event_id]) or "").strip()
        if receipt_id:
            receipt.setdefault("id", receipt_id)
        if event_id:
            receipt["source_event_id"] = event_id
            _append_unique(event_ids, event_id)
        receipt["subject_id"] = subject_id
        receipt["authority_source"] = str(task_ledger_events.EVENTS_REL)
        receipts.append(receipt)

        refs = _mapping(event.get("refs"))
        for ref in [
            receipt.get("transaction_id"),
            receipt.get("id"),
            *_string_values(payload.get("receipt_refs")),
            *_string_values(refs.get("receipt_refs")),
        ]:
            _append_unique(receipt_refs, ref)
        for ref in [
            receipt.get("commit_hash"),
            *_string_values(receipt.get("commit_refs")),
            *_string_values(payload.get("commit_refs")),
            *_string_values(refs.get("commit_refs")),
        ]:
            _append_unique(commit_refs, ref)
        for ref in [
            receipt.get("work_ledger_session_id"),
            *_string_values(receipt.get("work_ledger_refs")),
            *_string_values(payload.get("work_ledger_refs")),
            *_string_values(refs.get("work_ledger_refs")),
        ]:
            _append_unique(work_ledger_refs, ref)

    visibility: dict[str, Any] | None = None
    if event_ids:
        try:
            visibility = task_ledger_events.visibility_receipt(
                repo_root,
                subject_ids=subjects,
                event_ids=event_ids,
                projection_rebuilt=False,
            )
        except Exception as exc:
            visibility = {
                "schema": "task_ledger_visibility_receipt_v0",
                "authority_status": "not_checked",
                "reason": f"visibility_receipt_unavailable:{type(exc).__name__}",
            }
    overlay_status = "no_matching_execution_receipt"
    if receipts:
        overlay_status = (
            "authority_visible"
            if _mapping(visibility).get("authority_status") == "clean"
            else "authority_receipt_unverified"
        )
    return {
        "schema": AUTHORITY_RECEIPT_OVERLAY_SCHEMA,
        "status": overlay_status,
        "source": str(task_ledger_events.EVENTS_REL),
        "subject_ids": subjects,
        "receipt_count": len(receipts),
        "event_ids": event_ids,
        "receipt_refs": receipt_refs,
        "commit_refs": commit_refs,
        "work_ledger_refs": work_ledger_refs,
        "execution_receipts": receipts,
        "latest_execution_receipt": receipts[-1] if receipts else None,
        "visibility_receipt": visibility,
    }


def _merge_receipt_state_with_authority_overlay(
    receipt_state: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(receipt_state)
    if overlay.get("status") != "authority_visible":
        return merged

    for key in ("receipt_refs", "commit_refs", "work_ledger_refs"):
        values = list(merged.get(key) or [])
        for value in overlay.get(key) or []:
            _append_unique(values, value)
        merged[key] = values

    receipt_rows = [dict(row) for row in merged.get("execution_receipts") or [] if isinstance(row, Mapping)]
    index_by_key = {_receipt_merge_key(row): index for index, row in enumerate(receipt_rows)}
    for receipt in overlay.get("execution_receipts") or []:
        if not isinstance(receipt, Mapping):
            continue
        row = dict(receipt)
        key = _receipt_merge_key(row)
        if key in index_by_key:
            index = index_by_key[key]
            receipt_rows[index] = {**receipt_rows[index], **row}
        else:
            index_by_key[key] = len(receipt_rows)
            receipt_rows.append(row)
    if receipt_rows:
        merged["execution_receipts"] = receipt_rows
    latest = overlay.get("latest_execution_receipt")
    if isinstance(latest, Mapping):
        merged["latest_execution_receipt"] = dict(latest)
    merged["authority_execution_receipt_overlay"] = {
        "schema": overlay.get("schema"),
        "status": overlay.get("status"),
        "source": overlay.get("source"),
        "receipt_count": overlay.get("receipt_count"),
        "event_ids": list(overlay.get("event_ids") or []),
        "visibility_receipt": overlay.get("visibility_receipt"),
        "projection_card_visibility": _mapping(
            _mapping(overlay.get("visibility_receipt")).get("projection_assimilation_state")
        ).get("projection_card_visibility"),
    }
    return merged


def _merge_convergence_with_authority_overlay(
    convergence: Mapping[str, Any],
    overlay: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(convergence)
    if not isinstance(overlay, Mapping) or overlay.get("status") != "authority_visible":
        return merged
    merged["task_ledger_receipt_state"] = _merge_receipt_state_with_authority_overlay(
        _mapping(merged.get("task_ledger_receipt_state")),
        overlay,
    )
    return merged


def _receipt_evidence_state(
    *,
    transaction_id: str,
    convergence: Mapping[str, Any],
    reconcile: Mapping[str, Any],
) -> dict[str, Any]:
    receipt_state = _mapping(convergence.get("task_ledger_receipt_state"))
    receipt_refs = [str(ref) for ref in receipt_state.get("receipt_refs") or []]
    latest = _mapping(receipt_state.get("latest_execution_receipt"))
    latest_transaction_id = str(latest.get("transaction_id") or latest.get("id") or "")
    authority_overlay = _mapping(receipt_state.get("authority_execution_receipt_overlay"))
    return {
        "receipt_ref_present": bool(transaction_id and transaction_id in receipt_refs),
        "latest_receipt_matches_current": bool(transaction_id and latest_transaction_id == transaction_id),
        "latest_closeout_state": latest.get("closeout_state"),
        "reconcile_status": reconcile.get("status"),
        "reconcile_next_action": reconcile.get("next_action"),
        "receipt_refs": receipt_refs,
        "commit_refs": list(receipt_state.get("commit_refs") or []),
        "authority_overlay_status": authority_overlay.get("status"),
        "authority_overlay_event_ids": list(authority_overlay.get("event_ids") or []),
        "authority_overlay_projection_card_visibility": authority_overlay.get("projection_card_visibility"),
    }


def _finalizer_next_action(
    *,
    finalizer_id: str,
    finalizer_status: str,
    transaction_id: str,
    convergence: Mapping[str, Any],
    reconcile: Mapping[str, Any],
    shared_index: Mapping[str, Any],
    session_id: str | None,
) -> str:
    receipt = _receipt_evidence_state(
        transaction_id=transaction_id,
        convergence=convergence,
        reconcile=reconcile,
    )
    if finalizer_id == "task_ledger_execution_receipt":
        if receipt["latest_receipt_matches_current"] or receipt["receipt_ref_present"]:
            return "receipt_evidence_present; reconcile_current_transaction_finalizer_or_closeout_state"
        if reconcile.get("next_action") in {"record_task_ledger_execution_receipt", "drain_task_ledger_intake"}:
            return str(reconcile.get("next_action"))
        return "enqueue_or_record_task_ledger_execution_receipt"
    if finalizer_id == "claims_released":
        if not session_id:
            return "bind_attempt_to_work_ledger_session_before_claim_release_can_be_proven"
        return "session-finalize_or_release_active_claims"
    if finalizer_id == "staged_index_empty":
        if shared_index.get("private_index_scoped_commit_allowed"):
            return "normal_commit_blocked; use_private_index_scoped_commit_or_drain_unowned_staged_paths"
        return "drain_or_unstage_owned_shared_index_paths_before_landing"
    if finalizer_id == "session_not_stale_or_exempt":
        if not session_id:
            return "bind_status_to_session_id_or_finalize_owning_session"
        return "session-finalize_or_session-sweep"
    if finalizer_id == "work_ledger_append_or_exempt":
        return "append_work_ledger_progress_closeout_or_mark_explicit_exempt"
    if finalizer_status in {"blocked", "pending", "not_started"}:
        return "inspect_owner_surface_for_finalizer_clearance"
    return "none"


def classify_finalizer(
    finalizer: Mapping[str, Any],
    *,
    transaction_id: str,
    convergence: Mapping[str, Any],
    reconcile: Mapping[str, Any],
    shared_index: Mapping[str, Any],
    session_id: str | None,
) -> dict[str, Any]:
    finalizer_id = str(finalizer.get("id") or "").strip() or "unknown_finalizer"
    status = str(finalizer.get("status") or "unknown").strip()
    policy = FINALIZER_POLICIES.get(
        finalizer_id,
        {
            "owner_plane": "unknown",
            "gate_class": "unknown",
            "clearing_surface": "inspect source finalizer policy",
        },
    )
    row = {
        "id": finalizer_id,
        "status": status,
        "owner_plane": policy["owner_plane"],
        "gate_class": policy["gate_class"],
        "clearing_surface": policy["clearing_surface"],
        "next_action": _finalizer_next_action(
            finalizer_id=finalizer_id,
            finalizer_status=status,
            transaction_id=transaction_id,
            convergence=convergence,
            reconcile=reconcile,
            shared_index=shared_index,
            session_id=session_id,
        ),
    }
    if finalizer_id == "task_ledger_execution_receipt":
        row["evidence_state"] = _receipt_evidence_state(
            transaction_id=transaction_id,
            convergence=convergence,
            reconcile=reconcile,
        )
    if finalizer_id == "staged_index_empty":
        row["index_state"] = {
            "staged_path_count": shared_index.get("staged_path_count"),
            "unowned_staged_path_count": shared_index.get("unowned_staged_path_count"),
            "normal_git_commit_allowed": shared_index.get("normal_git_commit_allowed"),
            "private_index_scoped_commit_allowed": shared_index.get("private_index_scoped_commit_allowed"),
        }
    return row


def _controller_gap_rows(
    *,
    preflight: Mapping[str, Any],
    finalizers: Sequence[Mapping[str, Any]],
    session_id: str | None,
    attempt_binding: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    convergence = _mapping(preflight.get("transaction_convergence"))
    reconcile = _mapping(preflight.get("transaction_convergence_reconcile"))
    shared_index = _mapping(preflight.get("shared_index_quarantine"))
    intake = _mapping(preflight.get("task_ledger_intake"))
    gaps = [
        {
            "id": "claim_lease",
            "status": "available" if session_id else "available_but_not_bound",
            "owner_plane": "work_ledger",
            "evidence": "tools/meta/factory/work_ledger.py session-claim-path/session-finalize",
        },
        {
            "id": "execution_attempt",
            "status": "bound_to_work_landing_attempt" if attempt_binding else "approximated_by_transaction_candidate",
            "owner_plane": "work_landing_attempt_binding" if attempt_binding else "mission_transaction_preflight",
            "evidence": (
                f"{attempt_binding.get('td_id')}:{attempt_binding.get('idempotency_key')}"
                if attempt_binding
                else "transaction_candidate.transaction_id/read_set_hash/write_set_hash"
            ),
        },
        {
            "id": "landing_queue",
            "status": "available_serial_landing_controller",
            "owner_plane": "work_landing_controller",
            "evidence": "work_landing.py reconcile --apply --only land_scoped_commit --commit-hash <hash>",
        },
        {
            "id": "receipt_intake",
            "status": "available" if intake.get("available") is not False else "unavailable",
            "owner_plane": "task_ledger_intake",
            "evidence": "tools/meta/factory/task_ledger_apply.py enqueue-execution-receipt/drain-intake",
        },
        {
            "id": "projection_rebuild",
            "status": "serialized_by_closeout_bundle",
            "owner_plane": "work_landing_controller_and_task_ledger_intake",
            "evidence": "land_scoped_commit runs exact receipt drain and closeout after commit evidence is recorded",
        },
    ]
    if shared_index.get("shared_index_normal_commit_blocked"):
        gaps.append(
            {
                "id": "shared_index_pressure",
                "status": "normal_commit_blocked",
                "owner_plane": "git_index_owner",
                "evidence": f"{shared_index.get('unowned_staged_path_count', 0)} unowned staged paths",
            }
        )
    if convergence.get("status") == "watch" and reconcile.get("status") == "clear" and finalizers:
        gaps.append(
            {
                "id": "finalizer_reconciliation",
                "status": "open_current_finalizers_with_clear_receipt_reconcile",
                "owner_plane": "work_landing_controller_missing",
                "evidence": "transaction_convergence open finalizers need owner/action classification beyond receipt reconcile",
            }
        )
    return gaps


def _axis_status(value: Any, *, default: str = "not_evaluated") -> str:
    text = str(value or "").strip()
    return text or default


def _readiness_overall_status(axes: Mapping[str, Mapping[str, Any]]) -> str:
    statuses = {_axis_status(row.get("status")) for row in axes.values()}
    if statuses & {"blocked", "hard_stop"}:
        return "blocked"
    if statuses & {"watch", "deferred", "pending", "not_run_pre_edit", "not_evaluated"}:
        return "watch"
    return "ready"


def _transaction_readiness_contract(
    *,
    preflight: Mapping[str, Any],
    subject_ids: Sequence[str],
    owned_paths: Sequence[str],
    session_id: str | None,
    transaction_id: str,
    transaction_candidate: Mapping[str, Any],
    convergence: Mapping[str, Any],
    reconcile: Mapping[str, Any],
    shared_index: Mapping[str, Any],
    finalizers: Sequence[Mapping[str, Any]],
    intake: Mapping[str, Any],
    attempt_binding: Mapping[str, Any] | None,
    recommended_next_action: str,
) -> dict[str, Any]:
    closeout_settlement = _mapping(preflight.get("transaction_closeout_settlement"))
    generated_settlement = _mapping(preflight.get("generated_projection_settlement"))
    microcosm_admission = _mapping(preflight.get("microcosm_accepted_organ_admission"))
    landing_decision = _mapping(preflight.get("landing_decision"))
    autonomous_edit_gate = _mapping(preflight.get("autonomous_edit_gate"))
    base_head = str(_first([transaction_candidate.get("base_head"), _mapping(convergence.get("current_transaction")).get("base_head")]) or "").strip()
    claim_bound = bool(session_id or transaction_candidate.get("work_ledger_session_id") or attempt_binding)
    projection_status = _first(
        [
            closeout_settlement.get("projection_settlement_status"),
            generated_settlement.get("status"),
        ]
    )
    companion_status = _axis_status(microcosm_admission.get("status"), default="not_triggered")
    axes = {
        "authority_state": {
            "status": "selected" if subject_ids else "not_selected",
            "subject_ids": list(subject_ids),
            "authority_source": "state/task_ledger/events.jsonl",
            "projection_source": "state/task_ledger/ledger.json",
        },
        "projection_state": {
            "status": _axis_status(projection_status),
            "required_next_command": _first(
                [
                    generated_settlement.get("required_next_command"),
                    closeout_settlement.get("required_next_command"),
                ]
            ),
            "settlement_deferred_reason": _first(
                [
                    closeout_settlement.get("projection_settlement_deferred_reason"),
                    generated_settlement.get("reason"),
                ]
            ),
        },
        "claim_state": {
            "status": "bound" if claim_bound else "unbound",
            "session_id": session_id or transaction_candidate.get("work_ledger_session_id"),
            "attempt_binding_present": bool(attempt_binding),
        },
        "companion_gate_state": {
            "status": companion_status,
            "schema": microcosm_admission.get("schema"),
            "blocking_reason": microcosm_admission.get("blocking_reason"),
            "missing_companion_paths": list(microcosm_admission.get("missing_companion_paths") or []),
            "content_proof_status": microcosm_admission.get("content_proof_status"),
            "next_action": microcosm_admission.get("next_action"),
        },
        "validation_state": {
            "status": "not_run_pre_edit",
            "policy": "post_edit_validation_required; queued validation must carry queue id and must not be reported as passed",
        },
        "staged_index_state": {
            "status": _axis_status(shared_index.get("status")),
            "staged_path_count": shared_index.get("staged_path_count"),
            "unowned_staged_path_count": shared_index.get("unowned_staged_path_count"),
            "private_index_scoped_commit_allowed": shared_index.get("private_index_scoped_commit_allowed"),
            "normal_git_commit_allowed": shared_index.get("normal_git_commit_allowed"),
        },
        "parent_cas_state": {
            "status": "bound" if base_head else "unknown",
            "base_head": base_head or None,
            "read_set_hash": transaction_candidate.get("read_set_hash"),
            "write_set_hash": transaction_candidate.get("write_set_hash"),
        },
        "landing_decision_state": {
            "status": _axis_status(landing_decision.get("status"), default="not_evaluated"),
            "reason": landing_decision.get("reason"),
            "recommended_lane": landing_decision.get("recommended_lane"),
        },
        "allowed_next_action": {
            "status": "available" if recommended_next_action else "missing",
            "command_or_action": recommended_next_action,
        },
    }
    return {
        "schema": TRANSACTION_READINESS_SCHEMA,
        "status": _readiness_overall_status(axes),
        "transaction_id": transaction_id or None,
        "owned_paths": list(owned_paths),
        "axis_order": list(axes.keys()),
        "axes": axes,
        "reconcile": {
            "status": reconcile.get("status"),
            "next_action": reconcile.get("next_action"),
            "counts": reconcile.get("counts") or {},
        },
        "finalizer_count": len(finalizers),
        "intake": {
            "available": intake.get("available"),
            "counts": intake.get("counts") or {},
        },
        "autonomous_edit_gate": {
            "status": autonomous_edit_gate.get("status"),
            "required_mode": autonomous_edit_gate.get("required_mode"),
            "autonomous_feature_mutation_allowed": autonomous_edit_gate.get("autonomous_feature_mutation_allowed"),
        },
        "command_hints": {
            "control_summary": "./repo-python tools/meta/control/mission_transaction_preflight.py --control-summary",
            "reconcile": "./repo-python tools/meta/control/work_landing.py reconcile --dry-run",
            "status": "./repo-python tools/meta/control/work_landing.py status",
        },
    }


def build_work_landing_status_from_preflight(
    preflight: Mapping[str, Any],
    *,
    subject_ids: Sequence[str],
    owned_paths: Sequence[str] = (),
    session_id: str | None = None,
    intake_status: Mapping[str, Any] | None = None,
    attempt_binding: Mapping[str, Any] | None = None,
    closed_attempt_overlay: bool = True,
    authority_receipt_overlay: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    authority_overlay = _mapping(authority_receipt_overlay)
    convergence = _merge_convergence_with_authority_overlay(
        _mapping(preflight.get("transaction_convergence")),
        authority_overlay,
    )
    reconcile = _mapping(preflight.get("transaction_convergence_reconcile"))
    shared_index = _mapping(preflight.get("shared_index_quarantine"))
    transaction_candidate = _mapping(preflight.get("transaction_candidate"))
    current_transaction = _mapping(convergence.get("current_transaction"))
    convergence_finalizer_classes = _mapping(convergence.get("finalizer_classes"))
    transaction_id = str(
        _first(
            [
                current_transaction.get("transaction_id"),
                transaction_candidate.get("transaction_id"),
            ]
        )
        or ""
    )
    open_finalizers = _list_of_mappings(
        convergence_finalizer_classes.get("transaction_local_finalizers")
        if convergence_finalizer_classes
        else current_transaction.get("open_finalizers")
    )
    if not open_finalizers and not convergence_finalizer_classes:
        candidate_finalizers = _mapping(transaction_candidate.get("finalizers"))
        open_finalizers = [
            {"id": key, "status": value.get("status") if isinstance(value, Mapping) else value}
            for key, value in candidate_finalizers.items()
            if isinstance(value, Mapping)
            and str(value.get("status") or "") not in {"clear", "closed", "complete", "recorded"}
        ]
    intake = dict(intake_status or {})
    preflight_with_intake = {**dict(preflight), "task_ledger_intake": intake}
    classified_finalizers = [
        classify_finalizer(
            row,
            transaction_id=transaction_id,
            convergence=convergence,
            reconcile=reconcile,
            shared_index=shared_index,
            session_id=session_id,
        )
        for row in open_finalizers
    ]
    closed_attempt = (
        _closed_attempt_status_overlay(attempt_binding)
        if closed_attempt_overlay
        else {}
    )
    if closed_attempt:
        classified_finalizers = []
        convergence_finalizer_classes = {
            **dict(convergence_finalizer_classes),
            "transaction_local_finalizers": [],
            "ambient_pressure": [],
            "compatibility_finalizers": [],
            "closed_attempt_overlay": closed_attempt,
        }
        transaction_id = str(closed_attempt.get("transaction_id") or transaction_id or "")
    recommended_next_action = (
        "safe_to_continue_sibling_agents"
        if closed_attempt
        else _recommended_next_action(
            finalizers=classified_finalizers,
            convergence=convergence,
            reconcile=reconcile,
            shared_index=shared_index,
        )
    )
    transaction_readiness = _transaction_readiness_contract(
        preflight=preflight_with_intake,
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        session_id=session_id,
        transaction_id=transaction_id,
        transaction_candidate=transaction_candidate,
        convergence=convergence,
        reconcile=reconcile,
        shared_index=shared_index,
        finalizers=classified_finalizers,
        intake=intake,
        attempt_binding=attempt_binding,
        recommended_next_action=recommended_next_action,
    )
    return {
        "schema": STATUS_SCHEMA,
        "mode": "read_only",
        "subject_ids": list(subject_ids),
        "owned_paths": list(owned_paths),
        "session_id": session_id,
        "authority_model": {
            "workitem_authority": "state/task_ledger/events.jsonl",
            "runtime_claims": "state/work_ledger/runtime_status.json",
            "work_ledger_events": "codex/ledger/<phase>/work_ledger.jsonl",
            "receipt_intake": "state/task_ledger_intake",
            "commit_actuator": "tools/meta/control/scoped_commit.py",
            "projection_owner": "system/lib/mission_transaction_landing_preflight.py",
            "kernel_phase_required": False,
            "subphase_role": "compatibility_name_only",
        },
        "transaction": {
            "transaction_id": transaction_id or None,
            "status": (
                closed_attempt.get("status")
                if closed_attempt
                else _first([current_transaction.get("status"), transaction_candidate.get("status")])
            ),
            "base_head": (
                closed_attempt.get("base_head")
                if closed_attempt
                else _first([current_transaction.get("base_head"), transaction_candidate.get("base_head")])
            ),
            "read_set_hash": _first([current_transaction.get("read_set_hash"), transaction_candidate.get("read_set_hash")]),
            "write_set_hash": _first([current_transaction.get("write_set_hash"), transaction_candidate.get("write_set_hash")]),
            "work_ledger_session_id": (
                closed_attempt.get("session_id")
                if closed_attempt
                else transaction_candidate.get("work_ledger_session_id")
            ),
            "work_ledger_read_receipt_id": (
                closed_attempt.get("read_receipt_id")
                if closed_attempt
                else transaction_candidate.get("work_ledger_read_receipt_id")
            ),
            "canonical_state": convergence.get("canonical_transaction_state"),
            "shadow_state": current_transaction.get("shadow_state"),
        },
        "convergence": {
            "status": "clear" if closed_attempt else convergence.get("status"),
            "next_action": "none" if closed_attempt else convergence.get("next_action"),
            "summary": convergence.get("summary") or {},
            "receipt_state": convergence.get("task_ledger_receipt_state") or {},
            "canonical_transaction_state": convergence.get("canonical_transaction_state"),
            "finalizer_classes": convergence.get("finalizer_classes") or {},
            "recent_transaction_count": len(convergence.get("recent_transactions") or []),
        },
        "reconcile": {
            "status": "clear" if closed_attempt else reconcile.get("status"),
            "next_action": "none" if closed_attempt else reconcile.get("next_action"),
            "counts": reconcile.get("counts") or {},
            "actions": [] if closed_attempt else reconcile.get("actions") or [],
            "mutation_policy": reconcile.get("mutation_policy") or {},
        },
        "task_ledger_intake": intake,
        "attempt_binding": dict(attempt_binding or {}),
        "closed_attempt": closed_attempt,
        "authority_receipt_overlay": authority_overlay,
        "shared_index": {
            "status": shared_index.get("status"),
            "next_action": shared_index.get("next_action"),
            "staged_path_count": shared_index.get("staged_path_count"),
            "unowned_staged_path_count": shared_index.get("unowned_staged_path_count"),
            "owned_staged_path_count": shared_index.get("owned_staged_path_count"),
            "normal_git_commit_allowed": shared_index.get("normal_git_commit_allowed"),
            "private_index_scoped_commit_allowed": shared_index.get("private_index_scoped_commit_allowed"),
            "recommended_action": shared_index.get("recommended_action"),
            "paths_preview": shared_index.get("paths_preview") or [],
        },
        "finalizers": classified_finalizers,
        "ambient_pressure": list(convergence_finalizer_classes.get("ambient_pressure") or []),
        "compatibility_finalizers": list(convergence_finalizer_classes.get("compatibility_finalizers") or []),
        "controller_gaps": _controller_gap_rows(
            preflight=preflight_with_intake,
            finalizers=classified_finalizers,
            session_id=session_id,
            attempt_binding=attempt_binding,
        ),
        "transaction_readiness": transaction_readiness,
        "recommended_next_action": recommended_next_action,
    }


def _closed_attempt_status_overlay(attempt_binding: Mapping[str, Any] | None) -> dict[str, Any]:
    attempt = _mapping(attempt_binding)
    status = str(attempt.get("status") or "").strip()
    commit_hash = str(attempt.get("commit_hash") or "").strip()
    if status != "closed_after_commit_landing" or not commit_hash:
        return {}
    return {
        "schema": "work_landing_closed_attempt_overlay_v0",
        "status": status,
        "transaction_id": attempt.get("transaction_id"),
        "pre_mutation_transaction_id": attempt.get("pre_mutation_transaction_id"),
        "commit_hash": commit_hash,
        "td_id": attempt.get("td_id"),
        "session_id": attempt.get("session_id"),
        "read_receipt_id": attempt.get("read_receipt_id"),
        "base_head": attempt.get("base_head"),
        "reason": "closed_attempt_binding_supersedes_newer_head_candidate_for_this_status_call",
    }


def _recommended_next_action(
    *,
    finalizers: Sequence[Mapping[str, Any]],
    convergence: Mapping[str, Any],
    reconcile: Mapping[str, Any],
    shared_index: Mapping[str, Any],
) -> str:
    if shared_index.get("shared_index_normal_commit_blocked"):
        return "use_work_landing_reconcile_dry_run_then_private_index_scoped_landing_only_for_exact_owned_paths"
    if reconcile.get("next_action") not in (None, "", "none"):
        return str(reconcile.get("next_action"))
    if finalizers:
        return "complete_or_reclassify_current_transaction_finalizers"
    if convergence.get("status") == "clear":
        return "safe_to_continue_sibling_agents"
    return str(convergence.get("next_action") or "inspect_work_landing_status")


def build_work_landing_status(
    repo_root: Path,
    *,
    subject_ids: Sequence[str],
    owned_paths: Sequence[str] = (),
    session_id: str | None = None,
    require_exclusive: bool = False,
    closed_attempt_overlay: bool = True,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    preflight = _build_work_landing_preflight(
        repo_root,
        owned_paths=list(owned_paths),
        target_ids=list(subject_ids),
        session_id=session_id,
        require_exclusive=require_exclusive,
    )
    intake_status = _compact_intake_status(repo_root)
    subject_id = _first_string(subject_ids)
    attempt_binding = _attempt_binding_from_work_ledger(
        repo_root,
        preflight=preflight,
        subject_id=subject_id,
        session_id=session_id,
        requested_owned_paths=owned_paths,
    )
    authority_receipt_overlay = _task_ledger_authority_execution_receipt_overlay(
        repo_root,
        subject_ids=subject_ids,
    )
    return build_work_landing_status_from_preflight(
        preflight,
        subject_ids=list(subject_ids),
        owned_paths=list(owned_paths),
        session_id=session_id,
        intake_status=intake_status,
        attempt_binding=attempt_binding,
        closed_attempt_overlay=closed_attempt_overlay,
        authority_receipt_overlay=authority_receipt_overlay,
    )


def _refusal_payload(
    *,
    status: str,
    reason: str,
    subject_ids: Sequence[str],
    owned_paths: Sequence[str],
    session_id: str | None = None,
    blocked_by: Sequence[Any] = (),
    preflight: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema": ATTEMPT_BINDING_SCHEMA,
        "ok": False,
        "status": status,
        "reason": reason,
        "subject_ids": list(subject_ids),
        "owned_paths": list(owned_paths),
        "session_id": session_id,
        "blocked_by": list(blocked_by),
        "active_phase_consulted": False,
        "kernel_phase_required": False,
        "preflight_summary": {
            "transaction_id": _mapping(_mapping(preflight or {}).get("transaction_candidate")).get("transaction_id"),
            "work_ledger_status": _mapping(_mapping(preflight or {}).get("work_ledger")).get("status"),
        },
    }
    if extra:
        payload.update(dict(extra))
    return payload


def _clip_public_heartbeat_line(value: object, *, limit: int) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    if limit <= 3:
        return normalized[:limit]
    return f"{normalized[: limit - 3].rstrip()}..."


def build_work_landing_attempt_binding(
    repo_root: Path,
    *,
    subject_ids: Sequence[str],
    owned_paths: Sequence[str],
    session_id: str | None = None,
    require_exclusive: bool = True,
    created_by: str = "codex",
    lease_minutes: float = 120.0,
    heartbeat_current_pass_line: str | None = None,
    heartbeat_last_pass_result_line: str | None = None,
    heartbeat_clip_lines: bool = False,
    heartbeat_state: str = "inspecting",
    heartbeat_scope_refs: Sequence[object] | None = None,
    heartbeat_source: str = "manual_cli",
    explicit_subject_override: bool = False,
) -> dict[str, Any]:
    """Establish or return a pre-mutation WorkItem landing attempt binding.

    The successful binding uses Work Ledger runtime/session/thread authority.
    When another active claim blocks the requested paths, begin may emit a
    scoped blocked-patch capsule; it still does not mutate Task Ledger events,
    Git index state, kernel routes, or phase/subphase control state.
    """
    repo_root = repo_root.resolve()
    subjects = _unique_strings(subject_ids)
    paths = [path.strip("/") for path in _unique_strings(owned_paths)]
    actor = str(created_by or "codex").strip() or "codex"
    if len(subjects) != 1:
        return _refusal_payload(
            status="refused",
            reason="exactly_one_subject_id_required",
            subject_ids=subjects,
            owned_paths=paths,
            session_id=session_id,
        )
    subject_id = subjects[0]
    subject_exists = _subject_exists(repo_root, subject_id)
    subject_override_accepted = bool(explicit_subject_override and not subject_exists)
    if not subject_exists and not subject_override_accepted:
        return _refusal_payload(
            status="refused",
            reason="subject_id_not_found_in_task_ledger",
            subject_ids=subjects,
            owned_paths=paths,
            session_id=session_id,
        )
    if not paths:
        return _refusal_payload(
            status="refused",
            reason="owned_path_required",
            subject_ids=subjects,
            owned_paths=paths,
            session_id=session_id,
        )

    base_head = _current_git_head(repo_root)
    resolved_session_id = str(session_id or "").strip() or _derived_session_id(
        subject_id=subject_id,
        base_head=base_head,
        owned_paths=paths,
        created_by=actor,
    )
    idempotency_key = _attempt_idempotency_key(
        subject_id=subject_id,
        base_head=base_head,
        owned_paths=paths,
        created_by=actor,
    )
    collisions = _active_claim_collisions(
        repo_root,
        session_id=resolved_session_id,
        subject_id=subject_id,
        owned_paths=paths,
    )
    if collisions:
        capsule = _create_blocked_patch_capsule(
            repo_root,
            subject_id=subject_id,
            owned_paths=paths,
            session_id=resolved_session_id,
            base_head=base_head,
            collisions=collisions,
        )
        if capsule.get("status") == "queued":
            return _refusal_payload(
                status="blocked_but_capsuled",
                reason="exclusive_claim_refused_due_to_collision",
                subject_ids=subjects,
                owned_paths=paths,
                session_id=resolved_session_id,
                blocked_by=collisions,
                extra={
                    "blocked_patch_capsule": capsule,
                    "capsule_id": capsule.get("capsule_id"),
                    "patch_sha256": capsule.get("patch_sha256"),
                    "adoption_target": capsule.get("adoption_target"),
                    "adoption_targets": capsule.get("adoption_targets") or [],
                    "next_allowed_actions": [
                        "claim_owner_adopt",
                        "claim_owner_release",
                        "wait_for_reaper",
                        "mark_capsule_superseded",
                    ],
                },
            )
        return _refusal_payload(
            status="refused",
            reason="exclusive_claim_refused_due_to_collision",
            subject_ids=subjects,
            owned_paths=paths,
            session_id=resolved_session_id,
            blocked_by=collisions,
            extra={
                "blocked_patch_capsule": capsule,
                "next_allowed_actions": [
                    "create_scoped_diff_then_retry_begin",
                    "claim_owner_release",
                    "wait_for_reaper",
                ],
            },
        )

    default_context = _default_work_ledger_context(repo_root)
    phase_id = default_context["phase_id"]
    family_id = default_context["family_id"]
    existing_session = _runtime_session(repo_root, resolved_session_id)
    if existing_session:
        bootstrap = {
            "schema": "work_ledger_bootstrap_v1",
            "status": "already_active",
            "session_id": resolved_session_id,
            "actor": existing_session.get("actor"),
            "phase_id": existing_session.get("phase_id") or phase_id,
            "family_id": existing_session.get("family_id") or family_id,
            "read_receipt_id": existing_session.get("read_receipt_id"),
        }
    else:
        bootstrap = work_ledger_runtime.bootstrap_session(
            repo_root,
            session_id=resolved_session_id,
            actor=actor,
            phase_id=phase_id,
            family_id=family_id,
            auto_sweep=False,
        )
    read_receipt_id = str(bootstrap.get("read_receipt_id") or "").strip()
    if not read_receipt_id:
        return _refusal_payload(
            status="refused",
            reason="work_ledger_session_missing_read_receipt_id",
            subject_ids=subjects,
            owned_paths=paths,
            session_id=resolved_session_id,
        )

    claim_note = f"{ATTEMPT_BINDING_SCHEMA}:{idempotency_key}"
    claim_results: list[dict[str, Any]] = []
    work_item_claim = _claim_or_reuse(
        repo_root,
        session_id=resolved_session_id,
        scope_kind=work_ledger_runtime.CLAIM_SCOPE_WORK_ITEM,
        scope_id=subject_id,
        lease_minutes=lease_minutes,
        note=claim_note,
        session_snapshot=existing_session,
    )
    claim_results.append(work_item_claim)
    if str(work_item_claim.get("status") or "") == "refused":
        return _refusal_payload(
            status="refused",
            reason=str(work_item_claim.get("reason") or "work_item_claim_refused"),
            subject_ids=subjects,
            owned_paths=paths,
            session_id=resolved_session_id,
            blocked_by=work_item_claim.get("collisions") or [],
        )
    for path in paths:
        result = _claim_or_reuse(
            repo_root,
            session_id=resolved_session_id,
            scope_kind=work_ledger_runtime.CLAIM_SCOPE_PATH,
            scope_id=path,
            lease_minutes=lease_minutes,
            note=claim_note,
            session_snapshot=existing_session,
        )
        claim_results.append(result)
        if str(result.get("status") or "") == "refused":
            return _refusal_payload(
                status="refused",
                reason=str(result.get("reason") or "path_claim_refused"),
                subject_ids=subjects,
                owned_paths=paths,
                session_id=resolved_session_id,
                blocked_by=result.get("collisions") or [],
            )

    transaction = _begin_transaction_candidate(
        subject_id=subject_id,
        session_id=resolved_session_id,
        read_receipt_id=read_receipt_id,
        phase_id=phase_id,
        base_head=base_head,
        owned_paths=paths,
        claim_results=claim_results,
    )
    bound_preflight = {"transaction_candidate": transaction}
    transaction_id = str(transaction.get("transaction_id") or "").strip()
    existing_thread = _find_attempt_thread(
        repo_root,
        phase_id=phase_id,
        family_id=family_id,
        idempotency_key=idempotency_key,
        transaction_id=transaction_id,
        subject_id=subject_id,
        session_id=resolved_session_id,
    )
    event_result: dict[str, Any] | None = None
    if existing_thread:
        td_id = str(existing_thread.get("td_id") or "").strip()
        td_status = "already_open"
    else:
        claim_ids = [
            str(_mapping(result.get("claim")).get("claim_id") or "")
            for result in claim_results
            if str(_mapping(result.get("claim")).get("claim_id") or "").strip()
        ]
        attempt_metadata = {
            "schema": ATTEMPT_BINDING_SCHEMA,
            "status": "active",
            "subject_id": subject_id,
            "transaction_id": transaction_id,
            "session_id": resolved_session_id,
            "read_receipt_id": read_receipt_id,
            "base_head": transaction.get("base_head"),
            "read_set_hash": transaction.get("read_set_hash"),
            "write_set_hash": transaction.get("write_set_hash"),
            "owned_paths": paths,
            "claim_ids": claim_ids,
            "idempotency_key": idempotency_key,
        }
        if subject_override_accepted:
            attempt_metadata["subject_authority_override"] = {
                "mode": "explicit_non_workitem_subject_override",
                "subject_exists_in_task_ledger": False,
                "normal_missing_subject_refusal_preserved": True,
            }
        metadata = {
            "work_landing_attempt": attempt_metadata,
            "transaction_id": transaction_id,
            "subject_id": subject_id,
            "receipt_kind": ATTEMPT_BINDING_SCHEMA,
            "task_ledger_work_item_bridge": {
                "receipt_mode": "task_ledger_work_item_progress",
                "task_ledger_work_item_id": subject_id,
                "requested_work_ledger_td_id": subject_id,
            },
        }
        event_result = work_ledger.open_thread(
            repo_root,
            actor=actor,
            actor_session_id=resolved_session_id,
            phase_id=phase_id,
            family_id=family_id,
            title=f"WorkItem landing attempt: {subject_id}",
            body=(
                "Pre-mutation WorkItem landing attempt binding established. "
                "This binds subject/session/path claims/transaction before source edits."
            ),
            evidence_refs=["work_landing.py begin", ATTEMPT_BINDING_SCHEMA],
            read_receipt_id=read_receipt_id,
            metadata=metadata,
            task_ledger_work_item_id=subject_id,
            projection_mode=WORK_LANDING_APPEND_PROJECTION_MODE,
        )
        td_id = str(_mapping(event_result.get("event")).get("td_id") or "").strip()
        work_ledger_runtime.mark_ledger_append(
            repo_root,
            read_receipt_id=read_receipt_id,
            session_id=resolved_session_id,
            td_ids=[td_id],
            work_item_ids=[subject_id],
            event_ids=[str(_mapping(event_result.get("event")).get("event_id") or "")],
        )
        td_status = "opened"

    td_claim = _claim_or_reuse(
        repo_root,
        session_id=resolved_session_id,
        scope_kind=work_ledger_runtime.CLAIM_SCOPE_THREAD,
        scope_id=td_id,
        lease_minutes=lease_minutes,
        note=claim_note,
        session_snapshot=existing_session,
    )
    claim_results.append(td_claim)
    if str(td_claim.get("status") or "") == "refused":
        return _refusal_payload(
            status="refused",
            reason=str(td_claim.get("reason") or "td_claim_refused"),
            subject_ids=subjects,
            owned_paths=paths,
            session_id=resolved_session_id,
            blocked_by=td_claim.get("collisions") or [],
            preflight=bound_preflight,
        )

    resolved_current_pass_line = heartbeat_current_pass_line
    resolved_last_pass_result_line = heartbeat_last_pass_result_line
    if heartbeat_clip_lines:
        resolved_current_pass_line = _clip_public_heartbeat_line(
            resolved_current_pass_line,
            limit=work_ledger_runtime.PASS_CURRENT_LINE_LIMIT,
        )
        resolved_last_pass_result_line = _clip_public_heartbeat_line(
            resolved_last_pass_result_line,
            limit=work_ledger_runtime.PASS_RESULT_LINE_LIMIT,
        )

    initial_heartbeat: dict[str, Any] = {"status": "not_requested"}
    if resolved_current_pass_line or resolved_last_pass_result_line:
        explicit_scope_refs = _unique_strings(heartbeat_scope_refs or [])
        if explicit_scope_refs:
            resolved_scope_refs = explicit_scope_refs
            scope_ref_policy = "explicit"
        else:
            resolved_scope_refs = _unique_strings([subject_id, td_id, *paths])
            scope_ref_policy = "attempt_claims"
        heartbeat_status = work_ledger_runtime.mark_session_pass_heartbeat(
            repo_root,
            session_id=resolved_session_id,
            pass_state=heartbeat_state,
            current_pass_line=resolved_current_pass_line,
            last_pass_result_line=resolved_last_pass_result_line,
            td_id=subject_id,
            scope_refs=resolved_scope_refs,
            source=heartbeat_source,
        )
        heartbeat_session = _mapping(
            _mapping(heartbeat_status.get("sessions")).get(resolved_session_id)
        )
        initial_heartbeat = {
            "schema": "work_landing_begin_initial_heartbeat_v0",
            "status": "written",
            "scope_ref_policy": scope_ref_policy,
            "scope_refs": resolved_scope_refs,
            "pass_heartbeat": dict(heartbeat_session.get("pass_heartbeat") or {}),
        }

    claim_ids = [
        str(_mapping(result.get("claim")).get("claim_id") or "")
        for result in claim_results
        if str(_mapping(result.get("claim")).get("claim_id") or "").strip()
    ]
    binding = {
        "schema": ATTEMPT_BINDING_SCHEMA,
        "ok": True,
        "status": "active",
        "subject_id": subject_id,
        "work_item_id": subject_id,
        "transaction_id": transaction_id,
        "session_id": resolved_session_id,
        "read_receipt_id": read_receipt_id,
        "td_id": td_id,
        "base_head": transaction.get("base_head"),
        "read_set_hash": transaction.get("read_set_hash"),
        "write_set_hash": transaction.get("write_set_hash"),
        "owned_paths": paths,
        "claim_ids": claim_ids,
        "claims": claim_results,
        "idempotency_key": idempotency_key,
        "subject_exists_in_task_ledger": subject_exists,
        "td_thread_status": td_status,
        "mutated": bool(
            not existing_thread
            or any(str(result.get("status") or "") == "claimed" for result in claim_results)
        ),
        "active_phase_consulted": False,
        "kernel_phase_required": False,
        "authority": {
            "session": "state/work_ledger/runtime_status.json",
            "claims": "state/work_ledger/runtime_status.json",
            "td_thread": "codex/ledger/<phase>/work_ledger.jsonl",
            "task_ledger_events_touched": False,
            "git_index_touched": False,
        },
        "bootstrap": _compact_bootstrap(bootstrap),
        "initial_heartbeat": initial_heartbeat,
        "event": _compact_work_ledger_event_result(event_result),
    }
    if subject_override_accepted:
        binding["subject_authority_override"] = {
            "mode": "explicit_non_workitem_subject_override",
            "subject_exists_in_task_ledger": False,
            "normal_missing_subject_refusal_preserved": True,
        }
    return binding


def _receipt_reconcile_action(status: Mapping[str, Any]) -> dict[str, Any] | None:
    actions = _list_of_mappings(_mapping(status.get("reconcile")).get("actions"))
    transaction = _mapping(status.get("transaction"))
    canonical_state = _mapping(transaction.get("canonical_state"))
    attempt = _mapping(status.get("attempt_binding"))
    transaction_ids = [
        str(value or "").strip()
        for value in (
            canonical_state.get("transaction_id"),
            attempt.get("transaction_id"),
            transaction.get("transaction_id"),
        )
        if str(value or "").strip()
    ]
    for transaction_id in dict.fromkeys(transaction_ids):
        for action in actions:
            if str(action.get("transaction_id") or "").strip() == transaction_id:
                return action
    for action in actions:
        outcome = str(action.get("outcome") or "").strip()
        if outcome != "receipt_already_recorded":
            return action
    return None


def _command_with_paths(
    base: str,
    *,
    subject_id: str | None,
    owned_paths: Sequence[str],
    session_id: str | None = None,
) -> str:
    parts = [base]
    if subject_id:
        parts.extend(["--subject-id", subject_id])
    for path in owned_paths:
        parts.extend(["--owned-path", path])
    if session_id:
        parts.extend(["--session-id", session_id])
    return " ".join(parts)


def _compact_claim_ids(claim_state: Mapping[str, Any]) -> list[str]:
    claims = _mapping(claim_state.get("claims"))
    rows: list[Mapping[str, Any]] = []
    for key in ("work_item_claim", "td_claim"):
        claim = claims.get(key)
        if isinstance(claim, Mapping):
            rows.append(claim)
    for claim in claims.get("path_claims") or []:
        if isinstance(claim, Mapping):
            rows.append(claim)
    return _unique_strings([str(row.get("claim_id") or "") for row in rows])


def _write_admission_reason(
    *,
    subject_count_ok: bool,
    subject_authority_selected: bool,
    selector_allowed: bool,
    owned_paths: Sequence[str],
    attempt_binding: Mapping[str, Any],
    missing_fields: Sequence[str],
    claim_collisions: Sequence[Mapping[str, Any]],
    session_any: Mapping[str, Any] | None,
    thread_status: str | None,
) -> str:
    if not subject_count_ok:
        return "exactly_one_subject_id_required"
    if not subject_authority_selected:
        return "subject_id_not_found_in_task_ledger"
    if not selector_allowed:
        return "workitem_not_agent_executable"
    if not owned_paths:
        return "owned_path_required"
    if not attempt_binding:
        return "missing_work_landing_attempt_binding"
    if session_any and session_any.get("ended_at"):
        return "work_ledger_session_finalized"
    if thread_status and thread_status != "open":
        return "work_landing_attempt_not_active"
    if claim_collisions:
        return "active_claim_collision"
    if missing_fields:
        if any(str(item).startswith("path_claim:") or item == "work_item_claim" or item == "td_claim" for item in missing_fields):
            return "missing_active_claims"
        return "missing_required_admission_fields"
    return "ready_to_write"


def _write_readiness_contract(
    *,
    can_write: bool,
    reason: str,
    subject_count_ok: bool,
    subject_exists: bool,
    subject_authority_selected: bool,
    subject_override_accepted: bool,
    selector_allowed: bool,
    selection: Mapping[str, Any],
    status: Mapping[str, Any],
    claim_state: Mapping[str, Any],
    claim_collisions: Sequence[Mapping[str, Any]],
    base_head: str,
    required_next_command: str,
    entry_packet_ref: str,
    landing_status_ref: str,
) -> dict[str, Any]:
    transaction_readiness = _mapping(status.get("transaction_readiness"))
    transaction_axes = _mapping(transaction_readiness.get("axes"))
    claim_missing = _strings(claim_state.get("missing"))
    authority_mode = (
        "explicit_non_workitem_subject_override"
        if subject_override_accepted
        else "task_ledger_work_item"
    )
    axes = {
        "authority_state": {
            "status": "ready"
            if subject_count_ok and subject_authority_selected and selector_allowed
            else "blocked",
            "subject_count_ok": subject_count_ok,
            "subject_exists": subject_exists,
            "subject_authority_selected": subject_authority_selected,
            "subject_override_accepted": subject_override_accepted,
            "authority_mode": authority_mode,
            "selector_allowed": selector_allowed,
            "selected_subject_id": selection.get("subject_id"),
            "executable_by": selection.get("executable_by"),
            "authority_source": "state/task_ledger/events.jsonl",
            "projection_source": "state/task_ledger/ledger.json",
        },
        "projection_state": transaction_axes.get("projection_state") or {
            "status": "not_evaluated",
            "required_next_command": None,
        },
        "claim_state": {
            "status": "ready" if claim_state.get("ok") else "blocked",
            "missing": claim_missing,
            "collision_count": len(claim_collisions),
        },
        "companion_gate_state": transaction_axes.get("companion_gate_state") or {
            "status": "not_evaluated",
        },
        "validation_state": {
            "status": "not_run_pre_edit",
            "policy": "post_edit_validation_required; queued validation must carry queue id and must not be reported as passed",
        },
        "staged_index_state": transaction_axes.get("staged_index_state") or {
            "status": "not_evaluated",
        },
        "parent_cas_state": {
            "status": "bound" if base_head else "blocked",
            "base_head": base_head or None,
        },
        "allowed_next_action": {
            "status": "available" if required_next_command else "missing",
            "command_or_action": required_next_command,
        },
    }
    return {
        "schema": WRITE_READINESS_SCHEMA,
        "status": "ready" if can_write else "blocked",
        "reason": reason,
        "axis_order": list(axes.keys()),
        "axes": axes,
        "source_readiness_schema": transaction_readiness.get("schema"),
        "source_readiness_status": transaction_readiness.get("status"),
        "command_hints": {
            "entry_packet": entry_packet_ref,
            "landing_status": landing_status_ref,
            "required_next": required_next_command,
        },
    }


def build_workitem_write_admission(
    repo_root: Path,
    *,
    subject_ids: Sequence[str],
    owned_paths: Sequence[str],
    session_id: str | None = None,
    require_exclusive: bool = True,
    selector_mode: str = "agent",
    include_signoff: bool = False,
    domain: str | None = None,
    explicit_subject_override: bool = False,
) -> dict[str, Any]:
    """Return the pre-edit WorkItem admission decision for a write-capable agent."""
    repo_root = repo_root.resolve()
    subjects = _unique_strings(subject_ids)
    paths = [path.strip("/") for path in _unique_strings(owned_paths)]
    subject_id = subjects[0] if len(subjects) == 1 else None
    subject_count_ok = len(subjects) == 1
    subject_exists = bool(subject_id and _subject_exists(repo_root, subject_id))
    subject_override_accepted = bool(subject_id and explicit_subject_override and not subject_exists)
    subject_authority_selected = subject_exists or subject_override_accepted
    selection_picture = build_workitem_control_picture(
        repo_root,
        subject_id=subject_id,
        domain=domain,
        selector_mode=selector_mode,
        include_signoff=include_signoff,
        include_transaction=False,
        limit=3,
    )
    selection = _mapping(selection_picture.get("selection"))
    executable_by = str(selection.get("executable_by") or "unknown")
    if subject_override_accepted:
        selection = {
            **selection,
            "subject_id": subject_id,
            "source": "explicit_non_workitem_subject_override",
            "executable_by": "agent",
            "defer_reason": "explicit_subject_not_found",
        }
        executable_by = "agent"
    selector_allowed = bool(
        subject_id
        and (
            (subject_exists and executable_by == "agent")
            or explicit_subject_override
        )
    )

    status = build_work_landing_status(
        repo_root,
        subject_ids=subjects,
        owned_paths=paths,
        session_id=session_id,
        require_exclusive=require_exclusive,
    )
    attempt = _mapping(status.get("attempt_binding"))
    attempt_session_id = str(attempt.get("session_id") or session_id or "").strip()
    attempt_td_id = str(attempt.get("td_id") or "").strip()
    attempt_read_receipt_id = str(attempt.get("read_receipt_id") or "").strip()
    attempt_base_head = str(attempt.get("base_head") or _mapping(status.get("transaction")).get("base_head") or "").strip()
    attempt_owned_paths = [path.strip("/") for path in _strings(attempt.get("owned_paths") or [])]
    attempt_thread = _attempt_thread_for_status(repo_root, status)
    thread_status = str(_mapping(attempt_thread or {}).get("status") or "").strip() or None
    session_any = _runtime_session_any(repo_root, attempt_session_id) if attempt_session_id else None
    claim_state = _active_attempt_claims(repo_root, attempt=attempt) if attempt else {"ok": False, "missing": [], "claims": {}}
    missing_fields: list[str] = []
    for field_name, value in (
        ("subject_id", subject_id),
        ("session_id", attempt_session_id),
        ("td_id", attempt_td_id),
        ("read_receipt_id", attempt_read_receipt_id),
        ("base_head", attempt_base_head),
    ):
        if not value:
            missing_fields.append(field_name)
    if not paths:
        missing_fields.append("owned_paths")
    if not attempt:
        missing_fields.append("attempt_binding")
    if attempt and thread_status != "open":
        missing_fields.append("open_td_thread")
    if attempt and session_any and session_any.get("ended_at"):
        missing_fields.append("active_session")
    for path in paths:
        if path not in attempt_owned_paths:
            missing_fields.append(f"owned_path_not_bound:{path}")
    if attempt:
        missing_fields.extend(_strings(claim_state.get("missing")))
    claim_collisions = (
        _active_claim_collisions(
            repo_root,
            session_id=attempt_session_id or str(session_id or "").strip(),
            subject_id=subject_id or "",
            owned_paths=paths,
        )
        if subject_id and (attempt_session_id or session_id)
        else []
    )
    if not selector_allowed:
        missing_fields.append("agent_executable_workitem")
    reason = _write_admission_reason(
        subject_count_ok=subject_count_ok,
        subject_authority_selected=subject_authority_selected,
        selector_allowed=selector_allowed,
        owned_paths=paths,
        attempt_binding=attempt,
        missing_fields=missing_fields,
        claim_collisions=claim_collisions,
        session_any=session_any,
        thread_status=thread_status,
    )
    can_write = reason == "ready_to_write"
    if can_write:
        required_next_command = "edit_owned_paths_then_scoped_commit"
    elif reason in {"missing_work_landing_attempt_binding", "owned_path_required", "missing_active_claims", "work_ledger_session_finalized"}:
        required_next_command = _command_with_paths(
            "./repo-python tools/meta/control/work_landing.py begin",
            subject_id=subject_id,
            owned_paths=paths,
            session_id=session_id,
        )
        if subject_override_accepted:
            required_next_command = f"{required_next_command} --explicit-subject-override"
    elif reason == "workitem_not_agent_executable":
        required_next_command = "./repo-python tools/meta/control/work_control.py next --for-agent"
    else:
        required_next_command = "inspect_work_landing_admission_check"

    active_claim_ids = _compact_claim_ids(claim_state) if attempt else []
    entry_packet_ref = (
        f"./repo-python tools/meta/control/work_control.py entry --subject-id {subject_id} --for-agent"
        if subject_id
        else "./repo-python tools/meta/control/work_control.py entry --for-agent"
    )
    landing_status_ref = _command_with_paths(
        "./repo-python tools/meta/control/work_landing.py status",
        subject_id=subject_id,
        owned_paths=paths,
        session_id=attempt_session_id or session_id,
    )
    readiness_contract = _write_readiness_contract(
        can_write=can_write,
        reason=reason,
        subject_count_ok=subject_count_ok,
        subject_exists=subject_exists,
        subject_authority_selected=subject_authority_selected,
        subject_override_accepted=subject_override_accepted,
        selector_allowed=selector_allowed,
        selection=selection,
        status=status,
        claim_state=claim_state,
        claim_collisions=claim_collisions,
        base_head=attempt_base_head,
        required_next_command=required_next_command,
        entry_packet_ref=entry_packet_ref,
        landing_status_ref=landing_status_ref,
    )
    return {
        "schema": WRITE_ADMISSION_SCHEMA,
        "mode": "read_only",
        "subject_id": subject_id,
        "selector_mode": selector_mode if selector_mode in {"agent", "operator"} else "agent",
        "session_id": attempt_session_id or session_id,
        "td_id": attempt_td_id or None,
        "read_receipt_id": attempt_read_receipt_id or None,
        "attempt_binding_id": attempt.get("idempotency_key"),
        "idempotency_key": attempt.get("idempotency_key"),
        "base_head": attempt_base_head or None,
        "owned_paths": paths,
        "attempt_owned_paths": attempt_owned_paths,
        "claim_ids": active_claim_ids or list(attempt.get("claim_ids") or []),
        "can_write": can_write,
        "reason": reason,
        "missing_fields": _unique_strings(missing_fields),
        "claim_collisions": claim_collisions,
        "active_phase_consulted": False,
        "kernel_phase_required": False,
        "required_next_command": required_next_command,
        "selection": {
            "subject_id": selection.get("subject_id"),
            "source": selection.get("source"),
            "executable_by": selection.get("executable_by"),
            "defer_reason": selection.get("defer_reason"),
            "selected_is_signoff_bound": selection.get("selected_is_signoff_bound"),
            "explicit_subject_override": bool(explicit_subject_override),
            "subject_override_accepted": subject_override_accepted,
        },
        "readiness_contract": readiness_contract,
        "entry_packet_ref": entry_packet_ref,
        "landing_status_ref": landing_status_ref,
        "attempt_binding": {
            key: attempt.get(key)
            for key in (
                "schema",
                "status",
                "subject_id",
                "transaction_id",
                "session_id",
                "read_receipt_id",
                "td_id",
                "base_head",
                "idempotency_key",
                "binding_relation",
                "subject_authority_override",
            )
            if attempt.get(key) not in (None, "", [], {})
        },
        "claim_state": {
            "ok": bool(claim_state.get("ok")) if attempt else False,
            "missing": _strings(claim_state.get("missing")),
        },
        "session": {
            "session_id": attempt_session_id or session_id,
            "active": bool(session_any and not session_any.get("ended_at")),
            "ended_at": _mapping(session_any or {}).get("ended_at"),
        },
        "td_thread": {
            "td_id": attempt_td_id or None,
            "status": thread_status,
        },
        "authority": {
            "workitem_authority": "state/task_ledger/events.jsonl",
            "attempt_binding": "codex/ledger/<phase>/work_ledger.jsonl::metadata.work_landing_attempt",
            "runtime_claims": "state/work_ledger/runtime_status.json",
            "kernel_phase_required": False,
        },
    }


def _git_command(
    repo_root: Path,
    args: Sequence[str],
    *,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _commit_exists(repo_root: Path, commit_hash: str) -> bool:
    token = str(commit_hash or "").strip()
    if not token:
        return False
    result = _git_command(repo_root, ["cat-file", "-e", f"{token}^{{commit}}"])
    return result.returncode == 0


def _commit_descends_from(repo_root: Path, *, base_head: str, commit_hash: str) -> bool:
    base = str(base_head or "").strip()
    commit = str(commit_hash or "").strip()
    if not base or not commit:
        return False
    result = _git_command(repo_root, ["merge-base", "--is-ancestor", base, commit])
    return result.returncode == 0


def _commit_first_parent(repo_root: Path, commit_hash: str) -> str | None:
    commit = str(commit_hash or "").strip()
    if not commit:
        return None
    result = _git_command(repo_root, ["rev-list", "--parents", "-n", "1", commit])
    if result.returncode != 0:
        return None
    parts = result.stdout.strip().split()
    if len(parts) < 2:
        return None
    return parts[1]


def _commit_changed_paths(repo_root: Path, *, base_head: str, commit_hash: str) -> list[str]:
    base = str(base_head or "").strip()
    commit = str(commit_hash or "").strip()
    if not base or not commit:
        return []
    result = _git_command(repo_root, ["diff", "--name-only", f"{base}..{commit}"])
    if result.returncode != 0:
        return []
    return _unique_strings(result.stdout.splitlines())


def _paths_outside_owned(changed_paths: Sequence[str], owned_paths: Sequence[str]) -> list[str]:
    owned = [str(path or "").strip().strip("/") for path in owned_paths if str(path or "").strip()]
    outside: list[str] = []
    for changed in changed_paths:
        path = str(changed or "").strip().strip("/")
        if path and not any(_path_overlaps(path, owned_path) for owned_path in owned):
            outside.append(path)
    return outside


def _thread_event_metadata(thread: Mapping[str, Any]) -> list[dict[str, Any]]:
    return _list_of_mappings(thread.get("event_metadata"))


def _landing_commit_evidence_from_thread(
    thread: Mapping[str, Any],
    *,
    commit_hash: str | None = None,
) -> dict[str, Any]:
    wanted_commit = str(commit_hash or "").strip()
    attempt = _attempt_metadata_from_thread(thread)
    if attempt.get("commit_hash") and (not wanted_commit or attempt.get("commit_hash") == wanted_commit):
        return {
            "commit_hash": attempt.get("commit_hash"),
            "transaction_id": attempt.get("transaction_id"),
            "td_id": attempt.get("td_id"),
            "source": "thread_metadata",
            "landing_action": attempt.get("landing_action"),
        }
    for event_row in reversed(_thread_event_metadata(thread)):
        metadata = _mapping(event_row.get("metadata"))
        event_commit = str(_first([metadata.get("commit_hash"), _mapping(metadata.get("work_landing_attempt")).get("commit_hash")]) or "").strip()
        if not event_commit:
            continue
        if wanted_commit and event_commit != wanted_commit:
            continue
        return {
            "commit_hash": event_commit,
            "transaction_id": metadata.get("transaction_id") or _mapping(metadata.get("work_landing_attempt")).get("transaction_id"),
            "td_id": thread.get("td_id"),
            "event_id": event_row.get("event_id"),
            "source": "event_metadata",
            "landing_action": metadata.get("landing_action") or _mapping(metadata.get("work_landing_attempt")).get("landing_action"),
        }
    return {}


def _attempt_thread_for_status(
    repo_root: Path,
    status: Mapping[str, Any],
) -> dict[str, Any] | None:
    attempt = _mapping(status.get("attempt_binding"))
    if not attempt:
        return None
    default_context = _default_work_ledger_context(repo_root)
    return _find_attempt_thread(
        repo_root,
        phase_id=str(default_context.get("phase_id") or "09_52"),
        family_id=str(default_context.get("family_id") or "09"),
        idempotency_key=str(attempt.get("idempotency_key") or "").strip() or None,
        transaction_id=str(attempt.get("transaction_id") or "").strip() or None,
        subject_id=str(attempt.get("subject_id") or "").strip() or None,
        session_id=str(attempt.get("session_id") or "").strip() or None,
        include_closed=True,
    )


def _raw_attempt_thread_for_status(
    repo_root: Path,
    status: Mapping[str, Any],
) -> dict[str, Any] | None:
    attempt = _mapping(status.get("attempt_binding"))
    td_id = str(attempt.get("td_id") or "").strip()
    if not td_id:
        return None
    default_context = _default_work_ledger_context(repo_root)
    phase_id = str(attempt.get("phase_id") or default_context.get("phase_id") or "09_52").strip()
    family_id = str(attempt.get("family_id") or default_context.get("family_id") or "09").strip()
    try:
        thread = work_ledger.load_thread(
            repo_root,
            td_id,
            phase_id=phase_id,
            family_id=family_id,
        )
    except Exception:
        return None
    return dict(thread) if isinstance(thread, Mapping) else None


def _attempt_thread_and_landing_evidence(
    repo_root: Path,
    status: Mapping[str, Any],
    *,
    commit_hash: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    projection_thread = _attempt_thread_for_status(repo_root, status)
    if projection_thread:
        projection_evidence = _landing_commit_evidence_from_thread(
            projection_thread,
            commit_hash=commit_hash,
        )
        if projection_evidence:
            return projection_thread, projection_evidence

    raw_thread = _raw_attempt_thread_for_status(repo_root, status)
    if raw_thread:
        raw_evidence = _landing_commit_evidence_from_thread(
            raw_thread,
            commit_hash=commit_hash,
        )
        if raw_evidence:
            return raw_thread, {**raw_evidence, "freshness_source": "raw_td_thread_fallback"}
        return raw_thread, {}
    return projection_thread, {}


def _active_attempt_claims(
    repo_root: Path,
    *,
    attempt: Mapping[str, Any],
    owned_paths: Sequence[str] | None = None,
) -> dict[str, Any]:
    session_id = str(attempt.get("session_id") or "").strip()
    subject_id = str(attempt.get("subject_id") or "").strip()
    td_id = str(attempt.get("td_id") or "").strip()
    effective_owned_paths = _strings(owned_paths if owned_paths is not None else attempt.get("owned_paths") or [])
    missing: list[str] = []
    claims: dict[str, Any] = {}
    if not _runtime_session(repo_root, session_id):
        missing.append("active_session")
    work_item_claim = _active_claim_for_scope(
        repo_root,
        session_id=session_id,
        scope_kind=work_ledger_runtime.CLAIM_SCOPE_WORK_ITEM,
        scope_id=subject_id,
    )
    if not work_item_claim:
        missing.append("work_item_claim")
    else:
        claims["work_item_claim"] = work_item_claim
    td_claim = _active_claim_for_scope(
        repo_root,
        session_id=session_id,
        scope_kind=work_ledger_runtime.CLAIM_SCOPE_THREAD,
        scope_id=td_id,
    )
    if not td_claim:
        missing.append("td_claim")
    else:
        claims["td_claim"] = td_claim
    path_claims: list[dict[str, Any]] = []
    for path in effective_owned_paths:
        claim = _active_claim_for_scope(
            repo_root,
            session_id=session_id,
            scope_kind=work_ledger_runtime.CLAIM_SCOPE_PATH,
            scope_id=path,
        )
        if not claim:
            missing.append(f"path_claim:{path}")
        else:
            path_claims.append(claim)
    claims["path_claims"] = path_claims
    return {
        "ok": not missing,
        "missing": missing,
        "claims": claims,
    }


def _commit_landing_apply_state(
    repo_root: Path,
    status: Mapping[str, Any],
    *,
    commit_hash: str | None,
) -> dict[str, Any]:
    attempt = _mapping(status.get("attempt_binding"))
    transaction = _mapping(status.get("transaction"))
    subject_id = str(_first([attempt.get("subject_id"), (status.get("subject_ids") or [None])[0]]) or "").strip()
    td_id = str(attempt.get("td_id") or "").strip()
    session_id = str(attempt.get("session_id") or _mapping(status.get("session")).get("session_id") or "").strip()
    resolved_commit = str(commit_hash or "").strip()
    base_head = str(attempt.get("base_head") or transaction.get("base_head") or "").strip()
    transaction_id = str(_first([transaction.get("transaction_id"), attempt.get("current_transaction_id"), attempt.get("transaction_id")]) or "").strip()
    idempotency_key = (
        f"{subject_id}:work_landing_commit:{td_id}:{resolved_commit}"
        if subject_id and td_id and resolved_commit
        else None
    )
    identity = {
        "subject_id": subject_id or None,
        "transaction_id": transaction_id or None,
        "commit_hash": resolved_commit or None,
        "td_id": td_id or None,
        "session_id": session_id or None,
        "base_head": base_head or None,
        "idempotency_key": idempotency_key,
    }
    if not attempt:
        return {
            **identity,
            "apply_status": "blocked_missing_attempt_binding",
            "blocked_by": ["missing_work_landing_attempt_binding"],
            "evidence_if_already_done": {},
        }
    missing_identity = [
        key
        for key, value in (
            ("subject_id", subject_id),
            ("transaction_id", transaction_id),
            ("session_id", session_id),
            ("td_id", td_id),
            ("base_head", base_head),
        )
        if not value
    ]
    if not resolved_commit:
        missing_identity.append("commit_hash")
    if missing_identity:
        return {
            **identity,
            "apply_status": "blocked_missing_fields",
            "blocked_by": [f"missing_{field}" for field in missing_identity],
            "evidence_if_already_done": {},
        }
    thread, existing = _attempt_thread_and_landing_evidence(
        repo_root,
        status,
        commit_hash=resolved_commit,
    )
    if not thread:
        return {
            **identity,
            "apply_status": "blocked_missing_attempt_thread",
            "blocked_by": ["missing_work_ledger_td_thread"],
            "evidence_if_already_done": {},
        }
    if existing:
        return {
            **identity,
            "apply_status": "already_done",
            "blocked_by": [],
            "evidence_if_already_done": existing,
        }
    if not _commit_exists(repo_root, resolved_commit):
        return {
            **identity,
            "apply_status": "blocked_commit_not_found",
            "blocked_by": [f"commit_not_found:{resolved_commit}"],
            "evidence_if_already_done": {},
        }
    if not _commit_descends_from(repo_root, base_head=base_head, commit_hash=resolved_commit):
        return {
            **identity,
            "apply_status": "blocked_commit_not_descendant_of_attempt_base",
            "blocked_by": [f"base_head_not_ancestor:{base_head}"],
            "evidence_if_already_done": {},
        }
    # The attempt base remains the ancestry guard, but path ownership must be
    # checked against the scoped commit itself. If HEAD advanced after begin,
    # diffing attempt_base..commit would pull unrelated intervening commits into
    # this transaction's write set.
    path_diff_base = _commit_first_parent(repo_root, resolved_commit) or base_head
    changed_paths = _commit_changed_paths(repo_root, base_head=path_diff_base, commit_hash=resolved_commit)
    effective_owned_paths = _effective_attempt_owned_paths(repo_root, attempt=attempt)
    outside = _paths_outside_owned(changed_paths, effective_owned_paths)
    if outside:
        return {
            **identity,
            "apply_status": "blocked_commit_touches_unowned_paths",
            "blocked_by": [f"unowned_path:{path}" for path in outside],
            "changed_paths": changed_paths,
            "effective_owned_paths": effective_owned_paths,
            "evidence_if_already_done": {},
        }
    claim_state = _active_attempt_claims(repo_root, attempt=attempt, owned_paths=effective_owned_paths)
    if not claim_state["ok"]:
        return {
            **identity,
            "apply_status": "blocked_missing_active_claims",
            "blocked_by": list(claim_state.get("missing") or []),
            "changed_paths": changed_paths,
            "effective_owned_paths": effective_owned_paths,
            "evidence_if_already_done": {},
        }
    return {
        **identity,
        "apply_status": "ready",
        "blocked_by": [],
        "changed_paths": changed_paths,
        "effective_owned_paths": effective_owned_paths,
        "effective_claim_ids": _compact_claim_ids(claim_state),
        "evidence_if_already_done": {},
    }


def _receipt_action_identity(
    status: Mapping[str, Any],
    action: Mapping[str, Any] | None,
) -> dict[str, Any]:
    action_map = _mapping(action or {})
    transaction = _mapping(status.get("transaction"))
    subject_id = str(_first([action_map.get("subject_id"), (status.get("subject_ids") or [None])[0]]) or "").strip()
    transaction_id = str(_first([action_map.get("transaction_id"), transaction.get("transaction_id")]) or "").strip()
    commit_hash = str(action_map.get("commit_hash") or "").strip()
    closeout_state = str(action_map.get("closeout_state") or "").strip()
    valid_uncommitted_closeout = (
        not commit_hash
        and closeout_state in task_ledger_events.VALIDATED_UNCOMMITTED_CLOSEOUT_STATES
    )
    idempotency_key = (
        task_ledger_events.execution_receipt_idempotency_key(
            subject_id=subject_id,
            transaction_id=transaction_id,
            commit_hash=commit_hash,
            closeout_state=closeout_state if valid_uncommitted_closeout else None,
        )
        if subject_id and transaction_id and (commit_hash or valid_uncommitted_closeout)
        else None
    )
    return {
        "subject_id": subject_id or None,
        "transaction_id": transaction_id or None,
        "commit_hash": commit_hash or None,
        "closeout_state": closeout_state or None,
        "receipt_landing_mode": (
            "git_commit"
            if commit_hash
            else "validated_uncommitted"
            if valid_uncommitted_closeout
            else None
        ),
        "idempotency_key": idempotency_key,
    }


def _intake_request_status(request: Mapping[str, Any] | None) -> str:
    if not isinstance(request, Mapping):
        return ""
    return str(request.get("_intake_status") or request.get("status") or request.get("state") or "").strip()


def _exact_intake_requests(
    repo_root: Path,
    *,
    request_ids: Sequence[str] = (),
    idempotency_keys: Sequence[str] = (),
    statuses: Sequence[str] = ("applied",),
) -> list[dict[str, Any]]:
    wanted_request_ids = {
        str(request_id or "").strip()
        for request_id in request_ids
        if str(request_id or "").strip()
    }
    wanted_idempotency_keys = {
        str(key or "").strip()
        for key in idempotency_keys
        if str(key or "").strip()
    }
    if not wanted_request_ids and not wanted_idempotency_keys:
        return []
    matches: list[dict[str, Any]] = []
    for request in task_ledger_events.task_ledger_intake_requests(repo_root, statuses=statuses):
        if (
            str(request.get("request_id") or "").strip() in wanted_request_ids
            or str(request.get("idempotency_key") or "").strip() in wanted_idempotency_keys
        ):
            matches.append(dict(request))
    return matches


def _receipt_event_id_from_intake_request(request: Mapping[str, Any] | None) -> str | None:
    if not isinstance(request, Mapping):
        return None
    settle_result = _mapping(request.get("settle_result"))
    append = _mapping(settle_result.get("append"))
    event = _mapping(append.get("event"))
    event_id = str(event.get("event_id") or "").strip()
    if event_id:
        return event_id
    receipt_reconcile = _mapping(settle_result.get("receipt_reconcile"))
    existing_receipt = _mapping(receipt_reconcile.get("existing_receipt"))
    existing_event_id = str(existing_receipt.get("source_event_id") or "").strip()
    return existing_event_id or None


def _receipt_event_id_from_step_results(step_results: Mapping[str, Any]) -> str | None:
    drain_result = _mapping(step_results.get("exact_receipt_drain"))
    applied_requests = drain_result.get("applied_requests")
    if isinstance(applied_requests, list):
        for request in applied_requests:
            event_id = _receipt_event_id_from_intake_request(_mapping(request))
            if event_id:
                return event_id
    inner = _mapping(drain_result.get("drain_result"))
    for row in inner.get("results") or []:
        if not isinstance(row, Mapping):
            continue
        append = _mapping(row.get("append"))
        event = _mapping(append.get("event"))
        event_id = str(event.get("event_id") or "").strip()
        if event_id:
            return event_id
        receipt_reconcile = _mapping(row.get("receipt_reconcile"))
        existing_receipt = _mapping(receipt_reconcile.get("existing_receipt"))
        existing_event_id = str(existing_receipt.get("source_event_id") or "").strip()
        if existing_event_id:
            return existing_event_id
    return None


def _receipt_apply_state(status: Mapping[str, Any]) -> dict[str, Any]:
    action = _receipt_reconcile_action(status)
    identity = _receipt_action_identity(status, action)
    missing = [
        key
        for key in ("subject_id", "transaction_id")
        if not identity.get(key)
    ]
    if not identity.get("commit_hash") and identity.get("receipt_landing_mode") != "validated_uncommitted":
        missing.append("commit_hash")
    if action is None:
        return {
            **identity,
            "action": None,
            "outcome": None,
            "apply_status": "blocked_no_reconcile_action",
            "blocked_by": ["missing_transaction_convergence_reconcile_action"],
            "evidence_if_already_done": {},
        }
    outcome = str(action.get("outcome") or "").strip()
    evidence = {
        key: value
        for key, value in {
            "outcome": outcome or None,
            "intake_request": action.get("intake_request"),
            "work_ledger_event_ids": action.get("work_ledger_event_ids"),
            "work_ledger_session_ids": action.get("work_ledger_session_ids"),
            "read_receipt_ids": action.get("read_receipt_ids"),
            "closeout_state": action.get("closeout_state"),
            "validation_refs": action.get("validation_refs"),
            "no_commit_reason": action.get("no_commit_reason"),
            "commit_blocker_refs": action.get("commit_blocker_refs"),
        }.items()
        if value not in (None, "", [], {})
    }
    if missing:
        return {
            **identity,
            "action": action,
            "outcome": outcome or None,
            "apply_status": "blocked_missing_fields",
            "blocked_by": [f"missing_{field}" for field in missing],
            "evidence_if_already_done": evidence,
        }
    intake_request = _mapping(evidence.get("intake_request"))
    if _intake_request_status(intake_request) == "applied":
        return {
            **identity,
            "action": action,
            "outcome": outcome or "receipt_already_recorded",
            "apply_status": "already_done",
            "blocked_by": [],
            "evidence_if_already_done": evidence,
        }
    if outcome == "receipt_already_recorded":
        return {
            **identity,
            "action": action,
            "outcome": outcome,
            "apply_status": "already_done",
            "blocked_by": [],
            "evidence_if_already_done": evidence,
        }
    if outcome == "receipt_pending_in_intake":
        return {
            **identity,
            "action": action,
            "outcome": outcome,
            "apply_status": "already_queued",
            "blocked_by": [],
            "evidence_if_already_done": evidence,
        }
    if outcome in RECEIPT_INTAKE_READY_OUTCOMES:
        return {
            **identity,
            "action": action,
            "outcome": outcome,
            "apply_status": "ready",
            "blocked_by": [],
            "evidence_if_already_done": evidence,
        }
    return {
        **identity,
        "action": action,
        "outcome": outcome or None,
        "apply_status": "blocked_unsupported_reconcile_outcome",
        "blocked_by": [f"unsupported_outcome:{outcome or 'missing'}"],
        "evidence_if_already_done": evidence,
    }


def _receipt_scalar(receipt: Mapping[str, Any], key: str) -> str:
    value = receipt.get(key)
    if value in (None, ""):
        value = _mapping(receipt.get("execution")).get(key)
    return str(value or "").strip()


def _matching_same_execution_alias(
    receipt: Mapping[str, Any],
    alias_receipts: Iterable[Any],
) -> dict[str, Any] | None:
    commit_hash = _receipt_scalar(receipt, "commit_hash")
    session_id = _receipt_scalar(receipt, "work_ledger_session_id")
    read_receipt_id = _receipt_scalar(receipt, "read_receipt_id")
    if not (commit_hash and session_id and read_receipt_id):
        return None
    for alias in alias_receipts:
        if not isinstance(alias, Mapping):
            continue
        if (
            _receipt_scalar(alias, "commit_hash") == commit_hash
            and _receipt_scalar(alias, "work_ledger_session_id") == session_id
            and _receipt_scalar(alias, "read_receipt_id") == read_receipt_id
        ):
            return dict(alias)
    return None


def _closeout_apply_state(
    repo_root: Path,
    status: Mapping[str, Any],
    *,
    commit_hash: str | None,
) -> dict[str, Any]:
    attempt = _mapping(status.get("attempt_binding"))
    transaction = _mapping(status.get("transaction"))
    receipt_state = _receipt_apply_state(status)
    thread, thread_evidence = _attempt_thread_and_landing_evidence(
        repo_root,
        status,
        commit_hash=commit_hash,
    )
    subject_id = str(_first([attempt.get("subject_id"), (status.get("subject_ids") or [None])[0]]) or "").strip()
    transaction_id = str(_first([
        thread_evidence.get("transaction_id"),
        transaction.get("transaction_id"),
        attempt.get("current_transaction_id"),
        attempt.get("transaction_id"),
    ]) or "").strip()
    td_id = str(attempt.get("td_id") or _mapping(thread or {}).get("td_id") or "").strip()
    session_id = str(attempt.get("session_id") or transaction.get("work_ledger_session_id") or "").strip()
    read_receipt_id = str(attempt.get("read_receipt_id") or transaction.get("work_ledger_read_receipt_id") or "").strip()
    resolved_commit = str(_first([
        commit_hash,
        attempt.get("commit_hash"),
        thread_evidence.get("commit_hash"),
        receipt_state.get("commit_hash"),
    ]) or "").strip()
    idempotency_key = (
        f"{subject_id}:work_landing_closeout:{td_id}:{resolved_commit}"
        if subject_id and td_id and resolved_commit
        else None
    )
    identity = {
        "subject_id": subject_id or None,
        "transaction_id": transaction_id or None,
        "commit_hash": resolved_commit or None,
        "td_id": td_id or None,
        "session_id": session_id or None,
        "read_receipt_id": read_receipt_id or None,
        "idempotency_key": idempotency_key,
    }
    if not attempt:
        return {
            **identity,
            "apply_status": "blocked_missing_attempt_binding",
            "blocked_by": ["missing_work_landing_attempt_binding"],
            "evidence_if_already_done": {},
        }
    missing_identity = [
        key
        for key, value in (
            ("subject_id", subject_id),
            ("transaction_id", transaction_id),
            ("commit_hash", resolved_commit),
            ("td_id", td_id),
            ("session_id", session_id),
            ("read_receipt_id", read_receipt_id),
        )
        if not value
    ]
    if missing_identity:
        return {
            **identity,
            "apply_status": "blocked_missing_fields",
            "blocked_by": [f"missing_{field}" for field in missing_identity],
            "evidence_if_already_done": {},
        }
    if not thread:
        return {
            **identity,
            "apply_status": "blocked_missing_attempt_thread",
            "blocked_by": ["missing_work_ledger_td_thread"],
            "evidence_if_already_done": {},
        }
    if not thread_evidence:
        return {
            **identity,
            "apply_status": "blocked_missing_commit_landing_evidence",
            "blocked_by": ["missing_work_ledger_commit_landing_evidence"],
            "evidence_if_already_done": {},
        }
    receipt_status = str(receipt_state.get("apply_status") or "")
    receipt_outcome = str(receipt_state.get("outcome") or "").strip()
    receipt_deferred_until_close = (
        receipt_status == "blocked_unsupported_reconcile_outcome"
        and receipt_outcome == "receipt_deferred_with_work_ledger_evidence"
    )
    receipt_evidence = _mapping(receipt_state.get("evidence_if_already_done"))
    intake_request = _mapping(receipt_evidence.get("intake_request"))
    receipt_request_id = str(intake_request.get("request_id") or "").strip()
    receipt_idempotency_key = str(receipt_state.get("idempotency_key") or intake_request.get("idempotency_key") or "").strip()
    if receipt_status not in {"already_done", "already_queued", "ready"} and not receipt_deferred_until_close:
        return {
            **identity,
            "apply_status": "blocked_receipt_not_ready",
            "blocked_by": [receipt_status or "receipt_state_unavailable", *_strings(receipt_state.get("blocked_by"))],
            "evidence_if_already_done": {
                "commit_landing": thread_evidence,
                "receipt": receipt_evidence,
            },
        }
    thread_status = str(thread.get("status") or "").strip()
    session = _runtime_session_any(repo_root, session_id)
    if not session:
        return {
            **identity,
            "apply_status": "blocked_missing_session",
            "blocked_by": ["missing_work_ledger_session"],
            "evidence_if_already_done": {
                "commit_landing": thread_evidence,
                "receipt": receipt_evidence,
            },
        }
    session_ended = bool(session.get("ended_at"))
    if session_ended and thread_status == "open":
        return {
            **identity,
            "apply_status": "blocked_session_finalized_before_thread_close",
            "blocked_by": ["session_finalized_before_td_thread_close"],
            "evidence_if_already_done": {
                "commit_landing": thread_evidence,
                "receipt": receipt_evidence,
            },
        }
    if not session_ended:
        claim_state = _active_attempt_claims(repo_root, attempt=attempt)
        if not claim_state["ok"]:
            return {
                **identity,
                "apply_status": "blocked_missing_active_claims",
                "blocked_by": list(claim_state.get("missing") or []),
                "evidence_if_already_done": {
                    "commit_landing": thread_evidence,
                    "receipt": receipt_evidence,
                },
            }
    close_already_done = thread_status == "closed"
    finalize_already_done = session_ended
    receipt_already_done = receipt_status == "already_done"
    if receipt_already_done and close_already_done and finalize_already_done:
        return {
            **identity,
            "apply_status": "already_done",
            "blocked_by": [],
            "receipt_status": receipt_status,
            "receipt_request_id": receipt_request_id or None,
            "receipt_idempotency_key": receipt_idempotency_key or None,
            "thread_status": thread_status,
            "session_ended": session_ended,
            "evidence_if_already_done": {
                "commit_landing": thread_evidence,
                "receipt": receipt_evidence,
                "thread_status": thread_status,
                "session": {
                    "session_id": session_id,
                    "ended_at": session.get("ended_at"),
                    "active_claim_count": len([
                        claim
                        for claim in session.get("claims") or []
                        if isinstance(claim, Mapping) and not claim.get("released_at") and not claim.get("expired_at")
                    ]),
                },
            },
        }
    if receipt_status == "already_queued" and not (receipt_request_id or receipt_idempotency_key):
        return {
            **identity,
            "apply_status": "blocked_missing_exact_receipt_request",
            "blocked_by": ["missing_receipt_request_id_or_idempotency_key"],
            "evidence_if_already_done": {
                "commit_landing": thread_evidence,
                "receipt": receipt_evidence,
            },
        }
    return {
        **identity,
        "apply_status": "ready",
        "blocked_by": [],
        "receipt_status": receipt_status,
        "receipt_outcome": receipt_outcome or None,
        "receipt_deferred_until_close": receipt_deferred_until_close,
        "receipt_request_id": receipt_request_id or None,
        "receipt_idempotency_key": receipt_idempotency_key or None,
        "thread_status": thread_status,
        "session_ended": session_ended,
        "evidence_if_already_done": {
            "commit_landing": thread_evidence,
            "receipt": receipt_evidence,
        },
    }


def _controller_action_row(
    *,
    action_id: str,
    owner_plane: str,
    preconditions: Sequence[str],
    command_or_function: str,
    apply_supported: bool = False,
    apply_status: str = "unsupported",
    blocked_by: Sequence[str] = (),
    would_mutate: bool = False,
    idempotency_key: str | None = None,
    evidence_if_already_done: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    sequence = (
        ORDERED_CONTROLLER_ACTION_IDS.index(action_id) + 1
        if action_id in ORDERED_CONTROLLER_ACTION_IDS
        else None
    )
    row = {
        "action_id": action_id,
        "sequence": sequence,
        "owner_plane": owner_plane,
        "preconditions": list(preconditions),
        "prerequisite_action_ids": list(CONTROLLER_ACTION_PREREQUISITES.get(action_id, [])),
        "blocked_by": list(blocked_by),
        "would_mutate": bool(would_mutate),
        "idempotency_key": idempotency_key,
        "evidence_if_already_done": dict(evidence_if_already_done or {}),
        "command_or_function": command_or_function,
        "apply_supported": bool(apply_supported),
        "apply_status": apply_status,
    }
    if action_id in CONTROLLER_ACTION_ORDER_GUARDS:
        row["order_guard"] = CONTROLLER_ACTION_ORDER_GUARDS[action_id]
    row.update(CONTROLLER_ACTION_ROW_EXTRAS.get(action_id, {}))
    return row


def _ordered_controller_actions(
    status: Mapping[str, Any],
    *,
    repo_root: Path,
    commit_hash: str | None = None,
) -> list[dict[str, Any]]:
    receipt_state = _receipt_apply_state(status)
    receipt_ready = receipt_state.get("apply_status") == "ready"
    commit_state = _commit_landing_apply_state(repo_root, status, commit_hash=commit_hash)
    commit_status = str(commit_state.get("apply_status") or "")
    commit_ready = commit_status == "ready"
    closeout_state = _closeout_apply_state(repo_root, status, commit_hash=commit_hash)
    closeout_status = str(closeout_state.get("apply_status") or "")
    closeout_ready = closeout_status == "ready"
    if commit_status == "ready":
        land_apply_status = "ready"
        land_blocked_by: list[str] = []
    elif commit_status == "already_done" and closeout_status in {"ready", "already_done"}:
        land_apply_status = closeout_status
        land_blocked_by = _strings(closeout_state.get("blocked_by"))
    elif commit_status == "already_done":
        land_apply_status = closeout_status or "blocked"
        land_blocked_by = _strings(closeout_state.get("blocked_by"))
    else:
        land_apply_status = commit_status or "blocked"
        land_blocked_by = _strings(commit_state.get("blocked_by"))
    land_idempotency_key = (
        f"{commit_state.get('subject_id')}:work_landing_serial_land:{commit_state.get('td_id')}:{commit_state.get('commit_hash')}"
        if commit_state.get("subject_id") and commit_state.get("td_id") and commit_state.get("commit_hash")
        else None
    )
    return [
        _controller_action_row(
            action_id="verify_scoped_commit_landed",
            owner_plane="git_commit_history",
            preconditions=["transaction.commit_hash_present"],
            command_or_function="git cat-file -e <commit_hash>",
            apply_status="unsupported",
            blocked_by=["verify_only_not_controller_owned_in_this_slice"],
        ),
        _controller_action_row(
            action_id="ensure_work_ledger_progress_event",
            owner_plane="work_ledger_event_log",
            preconditions=["work_ledger_session_id_bound", "read_receipt_id_bound"],
            command_or_function="tools/meta/factory/work_ledger.py progress",
            apply_status="unsupported",
            blocked_by=["work_ledger_progress_apply_not_enabled_in_this_slice"],
        ),
        _controller_action_row(
            action_id=LAND_SCOPED_COMMIT_ATTEMPT_ACTION_ID,
            owner_plane="work_landing_controller",
            preconditions=[
                "attempt_binding_present",
                "commit_hash_present",
                "commit_exists",
                "commit_paths_within_owned_paths",
                "session_work_item_path_and_td_claims_active",
                "receipt_recordable_or_already_recorded",
                "work_ledger_td_thread_closeable",
            ],
            command_or_function="work_landing.py reconcile --apply --only land_scoped_commit --commit-hash <commit_hash>",
            apply_supported=True,
            apply_status=land_apply_status,
            blocked_by=land_blocked_by,
            would_mutate=land_apply_status == "ready",
            idempotency_key=land_idempotency_key,
            evidence_if_already_done=(
                {
                    "commit_landing": _mapping(commit_state.get("evidence_if_already_done")),
                    "closeout": _mapping(closeout_state.get("evidence_if_already_done")),
                }
                if land_apply_status == "already_done"
                else {}
            ),
        ),
        _controller_action_row(
            action_id=RECORD_SCOPED_COMMIT_LANDING_ACTION_ID,
            owner_plane="work_ledger_event_log",
            preconditions=[
                "attempt_binding_present",
                "commit_hash_present",
                "commit_exists",
                "commit_paths_within_owned_paths",
                "session_work_item_path_and_td_claims_active",
            ],
            command_or_function="work_ledger.progress_thread(metadata.commit_hash)",
            apply_supported=True,
            apply_status=str(commit_state.get("apply_status") or "blocked"),
            blocked_by=_strings(commit_state.get("blocked_by")),
            would_mutate=commit_ready,
            idempotency_key=commit_state.get("idempotency_key"),
            evidence_if_already_done=_mapping(commit_state.get("evidence_if_already_done")),
        ),
        _controller_action_row(
            action_id=RECEIPT_INTAKE_ACTION_ID,
            owner_plane="task_ledger_intake",
            preconditions=[
                "subject_id_present",
                "transaction_id_present",
                "commit_hash_present_or_validated_uncommitted_closeout_present",
                "receipt_not_already_recorded",
            ],
            command_or_function="system.lib.task_ledger_events.enqueue_task_ledger_intake_request",
            apply_supported=True,
            apply_status=str(receipt_state.get("apply_status") or "blocked"),
            blocked_by=_strings(receipt_state.get("blocked_by")),
            would_mutate=receipt_ready,
            idempotency_key=receipt_state.get("idempotency_key"),
            evidence_if_already_done=_mapping(receipt_state.get("evidence_if_already_done")),
        ),
        _controller_action_row(
            action_id="drain_task_ledger_intake_if_exclusive",
            owner_plane="task_ledger_intake_drainer",
            preconditions=["exclusive_drainer_context", "pending_intake_request_present"],
            command_or_function="tools/meta/factory/task_ledger_apply.py drain-intake --request-id <exact>",
            apply_status="unsupported",
            blocked_by=["serial_drainer_apply_not_enabled_in_this_slice"],
        ),
        _controller_action_row(
            action_id=CLOSEOUT_LANDING_ATTEMPT_ACTION_ID,
            owner_plane="work_landing_controller",
            preconditions=[
                "attempt_binding_present",
                "commit_landing_evidence_present",
                "task_ledger_receipt_recorded_or_exact_request_drainable",
                "work_ledger_td_thread_open_or_already_closed",
                "session_active_or_already_finalized_cleanly",
                "owned_claims_active_or_already_released",
            ],
            command_or_function="work_landing.py reconcile --apply --only closeout_landing_attempt",
            apply_supported=True,
            apply_status=str(closeout_state.get("apply_status") or "blocked"),
            blocked_by=_strings(closeout_state.get("blocked_by")),
            would_mutate=closeout_ready,
            idempotency_key=closeout_state.get("idempotency_key"),
            evidence_if_already_done=_mapping(closeout_state.get("evidence_if_already_done")),
        ),
        _controller_action_row(
            action_id="rebuild_task_ledger_projection",
            owner_plane="task_ledger_projection_owner",
            preconditions=["receipt_event_appended_or_noop"],
            command_or_function="tools/meta/factory/task_ledger_apply.py rebuild",
            apply_status="unsupported",
            blocked_by=["projection_rebuild_apply_not_enabled_in_this_slice"],
        ),
        _controller_action_row(
            action_id="check_work_ledger_projection",
            owner_plane="work_ledger_projection_owner",
            preconditions=["work_ledger_event_written_or_noop"],
            command_or_function="tools/meta/factory/work_ledger.py project --check --all",
            apply_status="unsupported",
            blocked_by=["projection_check_apply_not_enabled_in_this_slice"],
        ),
        _controller_action_row(
            action_id="close_work_ledger_transaction_thread",
            owner_plane="work_ledger_event_log",
            preconditions=[
                "work_ledger_td_id_bound",
                "read_receipt_id_still_valid",
                "receipt_event_recorded_or_noop",
            ],
            command_or_function="tools/meta/factory/work_ledger.py close",
            apply_status="unsupported",
            blocked_by=["work_ledger_close_apply_not_enabled_in_this_slice"],
        ),
        _controller_action_row(
            action_id="finalize_work_ledger_session",
            owner_plane="work_ledger_session",
            preconditions=["exact_session_id_bound", "session_claims_owned"],
            command_or_function="tools/meta/factory/work_ledger.py session-finalize",
            apply_status="unsupported",
            blocked_by=["session_finalize_apply_not_enabled_in_this_slice"],
        ),
        _controller_action_row(
            action_id="release_claims",
            owner_plane="work_ledger_claims",
            preconditions=["exact_session_id_bound", "owned_claim_ids_known"],
            command_or_function="tools/meta/factory/work_ledger.py session-release-claim",
            apply_status="unsupported",
            blocked_by=["claim_release_apply_not_enabled_in_this_slice"],
        ),
        _controller_action_row(
            action_id="recompute_convergence",
            owner_plane="mission_transaction_preflight",
            preconditions=["prior_controller_action_completed_or_noop"],
            command_or_function="tools/meta/control/mission_transaction_preflight.py --convergence",
            apply_status="unsupported",
            blocked_by=["read_only_recompute_not_mutating_controller_action"],
        ),
    ]


def _receipt_request_from_action(
    status: Mapping[str, Any],
    *,
    created_by: str,
    session_id: str | None,
) -> dict[str, Any]:
    receipt_state = _receipt_apply_state(status)
    action = _mapping(receipt_state.get("action"))
    transaction = _mapping(status.get("transaction"))
    subject_id = str(receipt_state.get("subject_id") or "").strip()
    transaction_id = str(receipt_state.get("transaction_id") or "").strip()
    commit_hash = str(receipt_state.get("commit_hash") or "").strip()
    work_ledger_session_id = _first_string(action.get("work_ledger_session_ids") or [transaction.get("work_ledger_session_id"), session_id])
    read_receipt_id = _first_string(action.get("read_receipt_ids") or [transaction.get("work_ledger_read_receipt_id")])
    closeout_state = str(
        action.get("closeout_state")
        or (
            "landed"
            if commit_hash
            else task_ledger_events.DEFAULT_VALIDATED_UNCOMMITTED_CLOSEOUT_STATE
        )
        or ""
    ).strip()
    no_commit_reason = str(
        action.get("no_commit_reason")
        or (
            "commit_hash_absent_in_work_landing_receipt_action"
            if not commit_hash
            else ""
        )
    ).strip()
    commit_blocker_refs = _strings(
        action.get("commit_blocker_refs")
        or (
            ["missing_commit_hash", "validated_uncommitted_git_metadata_blocked"]
            if not commit_hash
            else []
        )
    )
    validation_refs = _strings(
        [
            "work_landing.py reconcile --apply --only receipt_intake",
            "work_landing_status_v0",
            *_string_values(action.get("validation_refs")),
        ]
    )
    projection_refs = _strings(
        [
            "work_landing_reconcile_plan_v0",
            "transaction_convergence_reconcile_v0",
            *_string_values(action.get("projection_refs")),
        ]
    )
    receipt = {
        "schema": "transaction_receipt_v0",
        "transaction_id": transaction_id,
        "work_ledger_session_id": work_ledger_session_id,
        "read_receipt_id": read_receipt_id,
        **({"commit_hash": commit_hash} if commit_hash else {}),
        "read_set_hash": transaction.get("read_set_hash"),
        "write_set_hash": transaction.get("write_set_hash"),
        "validation_refs": validation_refs,
        "projection_refs": projection_refs,
        "closeout_state": closeout_state,
        "no_commit_reason": no_commit_reason,
        "commit_blocker_refs": commit_blocker_refs,
    }
    receipt = {key: value for key, value in receipt.items() if value not in (None, "", [], {})}
    attempt = _mapping(status.get("attempt_binding"))
    owned_paths = _strings(attempt.get("owned_paths") or action.get("owned_paths") or [])
    work_refs = _strings(
        list(action.get("work_ledger_session_ids") or [])
        + list(action.get("read_receipt_ids") or [])
        + list(action.get("work_ledger_event_ids") or [])
        + [work_ledger_session_id, read_receipt_id]
    )
    evidence_refs = _strings(
        [
            f"commit:{commit_hash}" if commit_hash else "",
            f"validated_uncommitted:{closeout_state}" if not commit_hash and closeout_state else "",
            f"no_commit_reason:{no_commit_reason}" if no_commit_reason else "",
            f"transaction:{transaction_id}" if transaction_id else "",
            f"work_ledger_session:{work_ledger_session_id}" if work_ledger_session_id else "",
            f"read_receipt:{read_receipt_id}" if read_receipt_id else "",
            *work_refs,
            *commit_blocker_refs,
            *validation_refs,
            *projection_refs,
        ]
    )
    if commit_hash:
        closeout_claim = (
            "Work Landing recorded a controller-owned execution receipt for "
            f"scoped commit {commit_hash} against transaction {transaction_id}."
        )
        counterexample_checks = [
            "execution_receipt_reconcile_state accepted the receipt identity before intake enqueue",
            "Task Ledger receipt idempotency key binds subject, transaction, and commit hash",
            "scoped commit hash is carried in execution_receipt and commit_refs",
            "Work Ledger session and read receipt refs are carried when available",
        ]
        commit_refs = [commit_hash]
    else:
        closeout_claim = (
            "Work Landing recorded a validated-uncommitted execution receipt for "
            f"transaction {transaction_id}; this is an auditable blocker receipt, not a scoped commit replacement."
        )
        counterexample_checks = [
            "execution_receipt_reconcile_state accepted the validated-uncommitted closeout state before intake enqueue",
            "Task Ledger receipt idempotency key binds subject, transaction, and validated-uncommitted state",
            "no_commit_reason and validation_refs are carried with the execution receipt",
            "commit_refs are not claimed when no scoped commit hash exists",
            "Work Ledger session and read receipt refs are carried when available",
        ]
        commit_refs = []
    closeout_assurance = {
        "claim": closeout_claim,
        "evidence_refs": evidence_refs,
        "corrective_action_strength": "strong",
        "counterexample_checks": _strings(counterexample_checks),
        "owner_surface": "work_landing_controller_v0",
        "owner_surfaces_changed": owned_paths,
        "residuals": [],
    }
    closeout_assurance = {
        key: value
        for key, value in closeout_assurance.items()
        if key == "residuals" or value not in (None, "", [], {})
    }
    payload: dict[str, Any] = {
        "execution_receipt": receipt,
        "closeout_assurance": closeout_assurance,
        "execution": {
            key: value
            for key, value in {
                "work_ledger_session_id": work_ledger_session_id,
                "read_receipt_id": read_receipt_id,
            }.items()
            if value
        },
        "refs": {
            "work_ledger_refs": work_refs,
            "commit_refs": commit_refs,
            "receipt_refs": [transaction_id],
        },
        "work_ledger_refs": work_refs,
        "commit_refs": commit_refs,
        "receipt_refs": [transaction_id],
    }
    payload = {key: value for key, value in payload.items() if value not in (None, "", [], {})}
    return {
        "kind": "execution_receipt",
        "event_type": "work_item.execution_receipt_recorded",
        "subject_id": subject_id,
        "created_by": created_by,
        "agent_run_id": session_id,
        "source": {
            "kind": "work_landing_controller_v0",
            "refs": ["work_landing_reconcile_apply_v0", "work_landing_status_v0"],
        },
        "refs": {
            "work_ledger_refs": work_refs,
            "commit_refs": commit_refs,
            "receipt_refs": [transaction_id],
        },
        "idempotency_key": receipt_state.get("idempotency_key"),
        "payload": payload,
    }


def _apply_receipt_intake(
    repo_root: Path,
    status: Mapping[str, Any],
    *,
    created_by: str,
    session_id: str | None,
) -> dict[str, Any]:
    receipt_state = _receipt_apply_state(status)
    apply_status = str(receipt_state.get("apply_status") or "")
    if apply_status in {"already_done", "already_queued"}:
        return {
            "ok": True,
            "status": apply_status,
            "mutated": False,
            "idempotency_key": receipt_state.get("idempotency_key"),
            "evidence": receipt_state.get("evidence_if_already_done") or {},
        }
    if apply_status != "ready":
        return {
            "ok": False,
            "status": "apply_refused",
            "mutated": False,
            "reason": apply_status or "not_ready",
            "blocked_by": receipt_state.get("blocked_by") or [],
        }
    request = _receipt_request_from_action(status, created_by=created_by, session_id=session_id)
    receipt = _mapping(_mapping(request.get("payload")).get("execution_receipt"))
    receipt_reconcile = task_ledger_events.execution_receipt_reconcile_state(
        repo_root,
        subject_id=str(request.get("subject_id") or ""),
        receipt=receipt,
    )
    if receipt_reconcile.get("status") == "receipt_already_recorded":
        return {
            "ok": True,
            "status": "already_done",
            "mutated": False,
            "idempotency_key": request.get("idempotency_key"),
            "receipt_reconcile": receipt_reconcile,
        }
    alias_receipt = _matching_same_execution_alias(
        receipt,
        receipt_reconcile.get("alias_receipts") or [],
    )
    if alias_receipt:
        return {
            "ok": True,
            "status": "already_done",
            "mutated": False,
            "idempotency_key": request.get("idempotency_key"),
            "receipt_reconcile": {
                **dict(receipt_reconcile),
                "status": "receipt_already_recorded",
                "alias_status": "same_execution_alias_already_recorded",
                "existing_receipt": alias_receipt,
            },
        }
    if not receipt_reconcile.get("ok", True):
        return {
            "ok": False,
            "status": "apply_refused_by_receipt_reconcile",
            "mutated": False,
            "idempotency_key": request.get("idempotency_key"),
            "receipt_reconcile": receipt_reconcile,
        }
    result = task_ledger_events.enqueue_task_ledger_intake_request(repo_root, request)
    return {
        "ok": bool(result.get("ok")),
        "status": result.get("status"),
        "mutated": result.get("status") == "intake_queued",
        "idempotency_key": result.get("idempotency_key") or request.get("idempotency_key"),
        "request_id": result.get("request_id"),
        "request_path": result.get("request_path"),
        "receipt_reconcile": receipt_reconcile,
    }


def _apply_record_scoped_commit_landing(
    repo_root: Path,
    status: Mapping[str, Any],
    *,
    commit_hash: str | None,
    created_by: str,
) -> dict[str, Any]:
    landing_state = _commit_landing_apply_state(repo_root, status, commit_hash=commit_hash)
    apply_status = str(landing_state.get("apply_status") or "")
    if apply_status == "already_done":
        return {
            "ok": True,
            "status": "already_done",
            "mutated": False,
            "idempotency_key": landing_state.get("idempotency_key"),
            "evidence": landing_state.get("evidence_if_already_done") or {},
        }
    if apply_status != "ready":
        return {
            "ok": False,
            "status": "apply_refused",
            "mutated": False,
            "reason": apply_status or "not_ready",
            "blocked_by": landing_state.get("blocked_by") or [],
            "idempotency_key": landing_state.get("idempotency_key"),
        }
    attempt = _mapping(status.get("attempt_binding"))
    transaction = _mapping(status.get("transaction"))
    default_context = _default_work_ledger_context(repo_root)
    subject_id = str(landing_state.get("subject_id") or attempt.get("subject_id") or "").strip()
    transaction_id = str(landing_state.get("transaction_id") or "").strip()
    td_id = str(landing_state.get("td_id") or "").strip()
    session_id = str(landing_state.get("session_id") or "").strip()
    attempt_read_receipt_id = str(attempt.get("read_receipt_id") or transaction.get("work_ledger_read_receipt_id") or "").strip()
    read_receipt_resolution = _resolve_landing_runtime_read_receipt(
        repo_root,
        read_receipt_id=attempt_read_receipt_id,
        session_id=session_id,
    )
    read_receipt_id = str(read_receipt_resolution.get("read_receipt_id") or attempt_read_receipt_id).strip()
    resolved_commit = str(landing_state.get("commit_hash") or "").strip()
    actor = str(created_by or "codex").strip() or "codex"
    pre_mutation_transaction_id = str(attempt.get("transaction_id") or "").strip()
    read_set_hash = str(_first([transaction.get("read_set_hash"), attempt.get("read_set_hash")]) or "").strip()
    write_set_hash = str(_first([transaction.get("write_set_hash"), attempt.get("write_set_hash")]) or "").strip()
    effective_owned_paths = _strings(landing_state.get("effective_owned_paths") or attempt.get("owned_paths") or [])
    effective_claim_ids = _strings(landing_state.get("effective_claim_ids") or attempt.get("claim_ids") or [])
    attempt_metadata = {
        "schema": ATTEMPT_BINDING_SCHEMA,
        "status": "commit_landed",
        "subject_id": subject_id,
        "transaction_id": transaction_id,
        "pre_mutation_transaction_id": pre_mutation_transaction_id,
        "session_id": session_id,
        "read_receipt_id": attempt_read_receipt_id or read_receipt_id,
        "td_id": td_id,
        "base_head": landing_state.get("base_head"),
        "commit_hash": resolved_commit,
        "read_set_hash": read_set_hash or None,
        "write_set_hash": write_set_hash or None,
        "owned_paths": effective_owned_paths,
        "claim_ids": effective_claim_ids,
        "idempotency_key": attempt.get("idempotency_key"),
        "landing_action": RECORD_SCOPED_COMMIT_LANDING_ACTION_ID,
    }
    if str(read_receipt_resolution.get("status") or "") == "refreshed_read_receipt":
        attempt_metadata["runtime_read_receipt_id"] = read_receipt_id
    attempt_metadata = {key: value for key, value in attempt_metadata.items() if value not in (None, "", [], {})}
    metadata = {
        "work_landing_attempt": attempt_metadata,
        "transaction_id": transaction_id,
        "subject_id": subject_id,
        "commit_hash": resolved_commit,
        "base_head": landing_state.get("base_head"),
        "read_set_hash": read_set_hash or None,
        "write_set_hash": write_set_hash or None,
        "landing_action": RECORD_SCOPED_COMMIT_LANDING_ACTION_ID,
        "receipt_kind": "work_landing_scoped_commit_landing_v0",
        "task_ledger_work_item_bridge": {
            "receipt_mode": "task_ledger_work_item_progress",
            "task_ledger_work_item_id": subject_id,
            "requested_work_ledger_td_id": subject_id,
        },
    }
    if str(read_receipt_resolution.get("status") or "") == "refreshed_read_receipt":
        metadata["read_receipt_refresh"] = read_receipt_resolution
    metadata = {key: value for key, value in metadata.items() if value not in (None, "", [], {})}
    event_result = work_ledger.progress_thread(
        repo_root,
        td_id=td_id,
        actor=actor,
        actor_session_id=session_id,
        phase_id=str(default_context.get("phase_id") or "09_52"),
        family_id=str(default_context.get("family_id") or "09"),
        title=f"Scoped commit landed for WorkItem attempt: {subject_id}",
        body=(
            "Controller-owned scoped commit landing evidence recorded. "
            "This binds the landed commit hash back to the active WorkItem landing attempt before Task Ledger receipt intake."
        ),
        evidence_refs=[
            "work_landing.py reconcile --apply --only record_scoped_commit_landing",
            f"commit:{resolved_commit}",
            RECORD_SCOPED_COMMIT_LANDING_ACTION_ID,
        ],
        read_receipt_id=read_receipt_id,
        metadata=metadata,
        task_ledger_work_item_id=subject_id,
        projection_mode=WORK_LANDING_APPEND_PROJECTION_MODE,
    )
    event = _mapping(event_result.get("event"))
    runtime_append_mark = _mark_landing_runtime_append(
        repo_root,
        read_receipt_id=read_receipt_id,
        session_id=session_id,
        td_ids=[td_id],
        work_item_ids=[subject_id],
        event_ids=[str(event.get("event_id") or "")],
    )
    return {
        "ok": bool(event_result.get("ok")),
        "status": "landing_recorded" if event_result.get("ok") else "landing_record_failed",
        "mutated": bool(event_result.get("ok")),
        "idempotency_key": landing_state.get("idempotency_key"),
        "commit_hash": resolved_commit,
        "transaction_id": transaction_id,
        "work_ledger_event_id": event.get("event_id"),
        "td_id": td_id,
        "read_receipt_id": read_receipt_id,
        "original_read_receipt_id": attempt_read_receipt_id if attempt_read_receipt_id != read_receipt_id else None,
        "read_receipt_resolution": read_receipt_resolution,
        "runtime_append_mark": runtime_append_mark,
        "projection_mode": event_result.get("projection_mode"),
    }


def _drain_exact_receipt_request(
    repo_root: Path,
    *,
    request_id: str | None,
    idempotency_key: str | None,
    created_by: str,
) -> dict[str, Any]:
    request_ids = [request_id] if str(request_id or "").strip() else []
    idempotency_keys = [idempotency_key] if str(idempotency_key or "").strip() else []
    if not request_ids and not idempotency_keys:
        return {
            "ok": False,
            "status": "blocked_missing_exact_receipt_request",
            "mutated": False,
            "blocked_by": ["missing_receipt_request_id_or_idempotency_key"],
        }
    result = task_ledger_events.drain_task_ledger_intake(
        repo_root,
        request_ids=request_ids,
        idempotency_keys=idempotency_keys,
        created_by=created_by,
        rebuild=False,
    )
    missing = list(_mapping(result.get("scope")).get("missing_request_ids") or [])
    missing.extend(list(_mapping(result.get("scope")).get("missing_idempotency_keys") or []))
    if missing:
        applied_requests = _exact_intake_requests(
            repo_root,
            request_ids=request_ids,
            idempotency_keys=idempotency_keys,
            statuses=("applied",),
        )
        applied_request_ids = {
            str(request.get("request_id") or "").strip()
            for request in applied_requests
            if str(request.get("request_id") or "").strip()
        }
        applied_idempotency_keys = {
            str(request.get("idempotency_key") or "").strip()
            for request in applied_requests
            if str(request.get("idempotency_key") or "").strip()
        }
        remaining_missing = [
            item
            for item in missing
            if item not in applied_request_ids and item not in applied_idempotency_keys
        ]
        if not remaining_missing:
            projection = task_ledger_events.rebuild_projections(repo_root)
            if not projection.get("ok"):
                return {
                    "ok": False,
                    "status": "task_ledger_projection_rebuild_failed",
                    "mutated": False,
                    "blocked_by": ["task_ledger_projection_rebuild_failed"],
                    "drain_result": result,
                    "applied_requests": applied_requests,
                    "projection": projection,
                }
            return {
                "ok": True,
                "status": "already_drained",
                "mutated": True,
                "drain_result": result,
                "applied_requests": applied_requests,
                "projection_rebuild": "rebuilt_already_drained_exact_receipt",
                "projection": projection,
            }
        return {
            "ok": False,
            "status": "blocked_exact_receipt_request_not_pending",
            "mutated": False,
            "blocked_by": [f"exact_receipt_request_not_pending:{item}" for item in remaining_missing],
            "drain_result": result,
        }
    projection = _mapping(result.get("projection"))
    if result.get("appended_count") and not projection.get("ok"):
        visibility = _mapping(result.get("visibility_receipt"))
        if visibility.get("authority_status") == "clean":
            return {
                "ok": bool(result.get("ok")),
                "status": "drained",
                "mutated": bool(result.get("processed_count")),
                "drain_result": result,
                "projection_rebuild": "deferred_exact_receipt_drain",
            }
        return {
            "ok": False,
            "status": "task_ledger_projection_rebuild_failed",
            "mutated": bool(result.get("processed_count")),
            "blocked_by": ["task_ledger_projection_rebuild_failed"],
            "drain_result": result,
        }
    return {
        "ok": bool(result.get("ok")),
        "status": "drained" if result.get("processed_count") else "nothing_to_drain",
        "mutated": bool(result.get("processed_count")),
        "drain_result": result,
        "projection_rebuild": "rebuilt_exact_receipt_drain" if projection.get("ok") else "not_needed_no_append",
    }


def _mark_landing_runtime_append(
    repo_root: Path,
    *,
    read_receipt_id: str,
    session_id: str,
    td_ids: Sequence[str],
    work_item_ids: Sequence[str],
    event_ids: Sequence[str],
) -> dict[str, Any]:
    read_receipt_resolution = _resolve_landing_runtime_read_receipt(
        repo_root,
        read_receipt_id=read_receipt_id,
        session_id=session_id,
        allow_ended=True,
    )
    effective_read_receipt_id = str(read_receipt_resolution.get("read_receipt_id") or read_receipt_id).strip()
    try:
        work_ledger_runtime.mark_ledger_append(
            repo_root,
            read_receipt_id=effective_read_receipt_id,
            session_id=session_id,
            td_ids=list(td_ids),
            work_item_ids=list(work_item_ids),
            event_ids=list(event_ids),
        )
    except ValueError as exc:
        reason = str(exc)
        if "ended session" not in reason:
            raise
        return {
            "ok": True,
            "status": "already_ended",
            "reason": reason,
            "read_receipt_id": effective_read_receipt_id,
            "original_read_receipt_id": read_receipt_id if read_receipt_id != effective_read_receipt_id else None,
            "read_receipt_resolution": read_receipt_resolution,
            "session_id": session_id,
        }
    return {
        "ok": True,
        "status": "refreshed_read_receipt"
        if str(read_receipt_resolution.get("status") or "") == "refreshed_read_receipt"
        else "marked",
        "read_receipt_id": effective_read_receipt_id,
        "original_read_receipt_id": read_receipt_id if read_receipt_id != effective_read_receipt_id else None,
        "read_receipt_resolution": read_receipt_resolution,
        "session_id": session_id,
    }


def _current_active_session_read_receipt(
    repo_root: Path,
    *,
    session_id: str,
) -> str:
    token = str(session_id or "").strip()
    if not token:
        return ""
    runtime_status = work_ledger_runtime.load_runtime_status(repo_root, rebuild=False)
    sessions = _mapping(runtime_status.get("sessions"))
    session = _mapping(sessions.get(token))
    if session.get("ended_at"):
        return ""
    return str(session.get("read_receipt_id") or "").strip()


def _resolve_landing_runtime_read_receipt(
    repo_root: Path,
    *,
    read_receipt_id: str,
    session_id: str,
    allow_ended: bool = False,
) -> dict[str, Any]:
    requested = str(read_receipt_id or "").strip()
    token = str(session_id or "").strip()
    try:
        work_ledger_runtime.validate_read_receipt(
            repo_root,
            read_receipt_id=requested,
            session_id=token or None,
        )
    except ValueError as exc:
        reason = str(exc)
        if allow_ended and "ended session" in reason:
            return {
                "ok": True,
                "status": "already_ended",
                "read_receipt_id": requested,
                "session_id": token,
                "reason": reason,
            }
        if "read_receipt_id is not valid" not in reason:
            raise
        refreshed = _current_active_session_read_receipt(repo_root, session_id=token)
        if not refreshed or refreshed == requested:
            raise
        work_ledger_runtime.validate_read_receipt(
            repo_root,
            read_receipt_id=refreshed,
            session_id=token or None,
        )
        return {
            "ok": True,
            "status": "refreshed_read_receipt",
            "read_receipt_id": refreshed,
            "original_read_receipt_id": requested,
            "session_id": token,
            "reason": reason,
        }
    return {
        "ok": True,
        "status": "valid",
        "read_receipt_id": requested,
        "session_id": token,
    }


def _apply_closeout_landing_attempt(
    repo_root: Path,
    status: Mapping[str, Any],
    *,
    commit_hash: str | None,
    created_by: str,
    session_id: str | None,
) -> dict[str, Any]:
    closeout_state = _closeout_apply_state(repo_root, status, commit_hash=commit_hash)
    apply_status = str(closeout_state.get("apply_status") or "")
    if apply_status == "already_done":
        return {
            "ok": True,
            "status": "already_done",
            "mutated": False,
            "idempotency_key": closeout_state.get("idempotency_key"),
            "evidence": closeout_state.get("evidence_if_already_done") or {},
        }
    if apply_status != "ready":
        return {
            "ok": False,
            "status": "apply_refused",
            "mutated": False,
            "reason": apply_status or "not_ready",
            "blocked_by": closeout_state.get("blocked_by") or [],
            "idempotency_key": closeout_state.get("idempotency_key"),
        }

    mutated_steps: list[str] = []
    step_results: dict[str, Any] = {}
    receipt_state = _receipt_apply_state(status)
    receipt_status = str(receipt_state.get("apply_status") or "")
    receipt_satisfied = receipt_status == "already_done"
    receipt_deferred_until_close = bool(closeout_state.get("receipt_deferred_until_close"))
    receipt_request_id = str(closeout_state.get("receipt_request_id") or "").strip()
    receipt_idempotency_key = str(closeout_state.get("receipt_idempotency_key") or receipt_state.get("idempotency_key") or "").strip()

    if receipt_status == "ready" and not receipt_deferred_until_close:
        step_started = time.perf_counter()
        receipt_result = _apply_receipt_intake(
            repo_root,
            status,
            created_by=created_by,
            session_id=session_id,
        )
        receipt_result = {**receipt_result, "elapsed_ms": _elapsed_ms(step_started)}
        step_results["receipt_intake"] = receipt_result
        if not receipt_result.get("ok"):
            return {
                "ok": False,
                "status": "receipt_intake_failed",
                "mutated": bool(mutated_steps),
                "idempotency_key": closeout_state.get("idempotency_key"),
                "step_results": step_results,
            }
        if receipt_result.get("mutated"):
            mutated_steps.append("receipt_intake")
        receipt_request_id = str(receipt_result.get("request_id") or receipt_request_id).strip()
        receipt_idempotency_key = str(receipt_result.get("idempotency_key") or receipt_idempotency_key).strip()
        if str(receipt_result.get("status") or "") == "already_done":
            receipt_status = "already_done"
            receipt_satisfied = True

    if receipt_status in {"ready", "already_queued"} and not receipt_deferred_until_close:
        step_started = time.perf_counter()
        drain_result = _drain_exact_receipt_request(
            repo_root,
            request_id=receipt_request_id,
            idempotency_key=receipt_idempotency_key,
            created_by=created_by,
        )
        drain_result = {**drain_result, "elapsed_ms": _elapsed_ms(step_started)}
        step_results["exact_receipt_drain"] = drain_result
        if not drain_result.get("ok"):
            return {
                "ok": False,
                "status": "exact_receipt_drain_failed",
                "mutated": bool(mutated_steps),
                "idempotency_key": closeout_state.get("idempotency_key"),
                "step_results": step_results,
            }
        if drain_result.get("mutated"):
            mutated_steps.append("exact_receipt_drain")
        receipt_satisfied = True

    subject_id = str(closeout_state.get("subject_id") or "").strip()
    attempt = _mapping(status.get("attempt_binding"))
    owned_paths = _strings(attempt.get("owned_paths") or [])
    effective_session_id = str(closeout_state.get("session_id") or session_id or "").strip()
    refreshed_state = closeout_state
    refreshed_attempt = attempt
    thread = _attempt_thread_for_status(repo_root, status)
    thread_satisfied = bool(thread and str(thread.get("status") or "") == "closed")
    default_context = _default_work_ledger_context(repo_root)
    td_id = str(refreshed_state.get("td_id") or refreshed_attempt.get("td_id") or "").strip()
    attempt_read_receipt_id = str(refreshed_state.get("read_receipt_id") or refreshed_attempt.get("read_receipt_id") or "").strip()
    read_receipt_resolution = _resolve_landing_runtime_read_receipt(
        repo_root,
        read_receipt_id=attempt_read_receipt_id,
        session_id=effective_session_id,
        allow_ended=True,
    )
    read_receipt_id = str(read_receipt_resolution.get("read_receipt_id") or attempt_read_receipt_id).strip()
    resolved_commit = str(refreshed_state.get("commit_hash") or "").strip()
    transaction_id = str(refreshed_state.get("transaction_id") or "").strip()
    latest_receipt = _mapping(_mapping(status.get("convergence")).get("receipt_state")).get("latest_execution_receipt")
    latest_receipt = _mapping(latest_receipt)
    drained_receipt_event_id = _receipt_event_id_from_step_results(step_results)
    status_receipt_event_id = str(latest_receipt.get("source_event_id") or "").strip()
    status_receipt_matches_current = (
        str(latest_receipt.get("transaction_id") or "").strip() == transaction_id
        and str(latest_receipt.get("commit_hash") or "").strip() == resolved_commit
    )
    receipt_event_id = drained_receipt_event_id or (
        status_receipt_event_id if status_receipt_matches_current else ""
    )
    if receipt_event_id:
        latest_receipt = {**latest_receipt, "source_event_id": receipt_event_id}
    if thread and str(thread.get("status") or "") == "open":
        step_started = time.perf_counter()
        metadata = {
            "transaction_id": transaction_id,
            "subject_id": subject_id,
            "commit_hash": resolved_commit,
            "task_ledger_receipt_event_id": receipt_event_id,
            "work_landing_attempt": {
                **{
                    key: value
                    for key, value in refreshed_attempt.items()
                    if key in {
                        "schema",
                        "subject_id",
                        "transaction_id",
                        "session_id",
                        "read_receipt_id",
                        "td_id",
                        "base_head",
                        "owned_paths",
                        "claim_ids",
                        "idempotency_key",
                    }
                },
                "status": "closed_after_commit_landing",
                "transaction_id": transaction_id,
                "pre_mutation_transaction_id": refreshed_attempt.get("pre_mutation_transaction_id") or refreshed_attempt.get("transaction_id"),
                "commit_hash": resolved_commit,
            },
            "landing_action": CLOSEOUT_LANDING_ATTEMPT_ACTION_ID,
        }
        if str(read_receipt_resolution.get("status") or "") == "refreshed_read_receipt":
            metadata["read_receipt_refresh"] = read_receipt_resolution
        close_result = work_ledger.close_thread(
            repo_root,
            td_id=td_id,
            actor=str(created_by or "codex").strip() or "codex",
            actor_session_id=effective_session_id,
            phase_id=str(default_context.get("phase_id") or "09_52"),
            family_id=str(default_context.get("family_id") or "09"),
            resolution_episode=work_ledger.build_resolution_episode(
                "git_commit",
                resolved_commit,
                label=f"WorkItem landing closeout: {subject_id}",
            ),
            body="Controller-owned landing closeout after scoped commit evidence.",
            evidence_refs=_strings([
                f"commit:{resolved_commit}",
                receipt_event_id,
                CLOSEOUT_LANDING_ATTEMPT_ACTION_ID,
            ]),
            read_receipt_id=read_receipt_id,
            metadata={key: value for key, value in metadata.items() if value not in (None, "", [], {})},
            projection_mode=WORK_LANDING_APPEND_PROJECTION_MODE,
        )
        close_result = {**close_result, "elapsed_ms": _elapsed_ms(step_started)}
        close_result["read_receipt_resolution"] = read_receipt_resolution
        close_event = _mapping(close_result.get("event"))
        close_result["runtime_append_mark"] = _mark_landing_runtime_append(
            repo_root,
            read_receipt_id=read_receipt_id,
            session_id=effective_session_id,
            td_ids=[td_id],
            work_item_ids=[subject_id],
            event_ids=[str(close_event.get("event_id") or "")],
        )
        step_results["close_thread"] = close_result
        if close_result.get("ok"):
            mutated_steps.append("close_thread")
            thread_satisfied = True

    if receipt_deferred_until_close:
        after_close_status = build_work_landing_status(
            repo_root,
            subject_ids=[subject_id],
            owned_paths=owned_paths,
            session_id=effective_session_id,
            closed_attempt_overlay=False,
        )
        after_close_receipt_state = _receipt_apply_state(after_close_status)
        after_close_receipt_status = str(after_close_receipt_state.get("apply_status") or "")
        after_close_receipt_request_id = str(
            _mapping(_mapping(after_close_receipt_state.get("evidence_if_already_done")).get("intake_request")).get("request_id") or ""
        ).strip()
        after_close_receipt_idempotency_key = str(
            after_close_receipt_state.get("idempotency_key")
            or _mapping(_mapping(after_close_receipt_state.get("evidence_if_already_done")).get("intake_request")).get("idempotency_key")
            or ""
        ).strip()
        if after_close_receipt_status == "ready":
            step_started = time.perf_counter()
            receipt_result = _apply_receipt_intake(
                repo_root,
                after_close_status,
                created_by=created_by,
                session_id=effective_session_id,
            )
            receipt_result = {**receipt_result, "elapsed_ms": _elapsed_ms(step_started)}
            step_results["receipt_intake"] = receipt_result
            if not receipt_result.get("ok"):
                return {
                    "ok": False,
                    "status": "receipt_intake_failed",
                    "mutated": bool(mutated_steps),
                    "idempotency_key": closeout_state.get("idempotency_key"),
                    "step_results": step_results,
                }
            if receipt_result.get("mutated"):
                mutated_steps.append("receipt_intake")
            after_close_receipt_request_id = str(receipt_result.get("request_id") or after_close_receipt_request_id).strip()
            after_close_receipt_idempotency_key = str(
                receipt_result.get("idempotency_key") or after_close_receipt_idempotency_key
            ).strip()
            if str(receipt_result.get("status") or "") == "already_done":
                after_close_receipt_status = "already_done"
                receipt_satisfied = True
        if after_close_receipt_status in {"ready", "already_queued"}:
            step_started = time.perf_counter()
            drain_result = _drain_exact_receipt_request(
                repo_root,
                request_id=after_close_receipt_request_id,
                idempotency_key=after_close_receipt_idempotency_key,
                created_by=created_by,
            )
            drain_result = {**drain_result, "elapsed_ms": _elapsed_ms(step_started)}
            step_results["exact_receipt_drain"] = drain_result
            if not drain_result.get("ok"):
                return {
                    "ok": False,
                    "status": "exact_receipt_drain_failed",
                    "mutated": bool(mutated_steps),
                    "idempotency_key": closeout_state.get("idempotency_key"),
                    "step_results": step_results,
                }
            if drain_result.get("mutated"):
                mutated_steps.append("exact_receipt_drain")
            receipt_satisfied = True
        elif after_close_receipt_status == "already_done":
            receipt_satisfied = True
        elif after_close_receipt_status != "already_done":
            return {
                "ok": False,
                "status": "receipt_after_close_not_ready",
                "mutated": bool(mutated_steps),
                "idempotency_key": closeout_state.get("idempotency_key"),
                "blocked_by": [
                    after_close_receipt_status or "receipt_state_unavailable",
                    *_strings(after_close_receipt_state.get("blocked_by")),
                ],
                "step_results": step_results,
            }

    session = _runtime_session_any(repo_root, effective_session_id)
    session_satisfied = bool(session and session.get("ended_at"))
    if session and not session.get("ended_at"):
        step_started = time.perf_counter()
        finalize_result = work_ledger_runtime.finalize_session(
            repo_root,
            session_id=effective_session_id,
            action="work_landing_closeout_completed",
            release_claims=True,
            release_reason="work_landing_closeout_completed",
        )
        step_results["finalize_session"] = {
            "ok": True,
            "session_id": effective_session_id,
            "ended_at": _mapping(_mapping(finalize_result.get("sessions")).get(effective_session_id)).get("ended_at"),
            "elapsed_ms": _elapsed_ms(step_started),
            "active_claim_count": len([
                claim
                for claim in _mapping(_mapping(finalize_result.get("sessions")).get(effective_session_id)).get("claims") or []
                if isinstance(claim, Mapping) and not claim.get("released_at") and not claim.get("expired_at")
            ]),
        }
        mutated_steps.append("finalize_session")
        session_satisfied = True

    final_blocked_by: list[str] = []
    if not receipt_satisfied:
        final_blocked_by.append("receipt_not_satisfied")
    if not thread_satisfied:
        final_blocked_by.append("thread_not_closed")
    if not session_satisfied:
        final_blocked_by.append("session_not_finalized")
    final_apply_status = "already_done" if not final_blocked_by else "ready"
    final_receipt_event_id = _receipt_event_id_from_step_results(step_results) or receipt_event_id or None
    exact_drain_projection_rebuild = str(
        _mapping(step_results.get("exact_receipt_drain")).get("projection_rebuild") or ""
    ).strip()
    step_results["closeout_fast_path"] = {
        "status": "used",
        "skipped_status_recomputes": 2 if not receipt_deferred_until_close else 1,
        "task_ledger_projection_rebuild": exact_drain_projection_rebuild or "not_applicable_no_exact_receipt_drain",
        "task_ledger_receipt_event_id": final_receipt_event_id,
        "step_elapsed_ms": {
            name: _mapping(result).get("elapsed_ms")
            for name, result in step_results.items()
            if name != "closeout_fast_path" and _mapping(result).get("elapsed_ms") is not None
        },
        "receipt_satisfied": receipt_satisfied,
        "thread_satisfied": thread_satisfied,
        "session_satisfied": session_satisfied,
    }
    return {
        "ok": final_apply_status == "already_done",
        "status": "closeout_completed" if final_apply_status == "already_done" else "closeout_incomplete",
        "mutated": bool(mutated_steps),
        "mutated_steps": mutated_steps,
        "idempotency_key": closeout_state.get("idempotency_key"),
        "transaction_id": transaction_id,
        "commit_hash": resolved_commit,
        "task_ledger_receipt_event_id": final_receipt_event_id,
        "td_id": td_id,
        "session_id": effective_session_id,
        "step_results": step_results,
        "final_state": {
            "apply_status": final_apply_status,
            "blocked_by": final_blocked_by,
        },
    }


def _apply_land_scoped_commit_attempt(
    repo_root: Path,
    status: Mapping[str, Any],
    *,
    commit_hash: str | None,
    created_by: str,
    session_id: str | None,
) -> dict[str, Any]:
    attempt = _mapping(status.get("attempt_binding"))
    subject_ids = _strings(status.get("subject_ids") or [attempt.get("subject_id")])
    owned_paths = _strings(status.get("owned_paths") or attempt.get("owned_paths") or [])
    effective_session_id = str(_first([session_id, attempt.get("session_id")]) or "").strip()
    step_results: dict[str, Any] = {}
    mutated_steps: list[str] = []

    step_started = time.perf_counter()
    commit_result = _apply_record_scoped_commit_landing(
        repo_root,
        status,
        commit_hash=commit_hash,
        created_by=created_by,
    )
    commit_result = {**commit_result, "elapsed_ms": _elapsed_ms(step_started)}
    step_results[RECORD_SCOPED_COMMIT_LANDING_ACTION_ID] = commit_result
    if commit_result.get("mutated"):
        mutated_steps.append(RECORD_SCOPED_COMMIT_LANDING_ACTION_ID)
    if not commit_result.get("ok"):
        return {
            "ok": False,
            "status": "commit_landing_failed",
            "mutated": bool(mutated_steps),
            "mutated_steps": mutated_steps,
            "idempotency_key": commit_result.get("idempotency_key"),
            "step_results": step_results,
        }

    effective_session_id = str(
        _first([effective_session_id, commit_result.get("session_id"), attempt.get("session_id")]) or ""
    ).strip()
    effective_subject_ids = subject_ids or _strings([commit_result.get("subject_id")])
    refreshed_status = build_work_landing_status(
        repo_root,
        subject_ids=effective_subject_ids,
        owned_paths=owned_paths,
        session_id=effective_session_id or session_id,
        closed_attempt_overlay=False,
    )

    step_started = time.perf_counter()
    closeout_result = _apply_closeout_landing_attempt(
        repo_root,
        refreshed_status,
        commit_hash=commit_hash,
        created_by=created_by,
        session_id=effective_session_id or session_id,
    )
    closeout_result = {**closeout_result, "elapsed_ms": _elapsed_ms(step_started)}
    step_results[CLOSEOUT_LANDING_ATTEMPT_ACTION_ID] = closeout_result
    for step_name in _strings(closeout_result.get("mutated_steps") or []):
        if step_name not in mutated_steps:
            mutated_steps.append(step_name)
    if not closeout_result.get("ok"):
        return {
            "ok": False,
            "status": "closeout_landing_failed",
            "mutated": bool(mutated_steps),
            "mutated_steps": mutated_steps,
            "idempotency_key": closeout_result.get("idempotency_key") or commit_result.get("idempotency_key"),
            "commit_hash": closeout_result.get("commit_hash") or commit_result.get("commit_hash"),
            "transaction_id": closeout_result.get("transaction_id") or commit_result.get("transaction_id"),
            "step_results": step_results,
        }

    sequence_already_done = (
        str(commit_result.get("status") or "") == "already_done"
        and str(closeout_result.get("status") or "") == "already_done"
        and not mutated_steps
    )
    return {
        "ok": True,
        "status": "already_done" if sequence_already_done else "land_scoped_commit_completed",
        "mutated": bool(mutated_steps),
        "mutated_steps": mutated_steps,
        "idempotency_key": closeout_result.get("idempotency_key") or commit_result.get("idempotency_key"),
        "commit_hash": closeout_result.get("commit_hash") or commit_result.get("commit_hash"),
        "transaction_id": closeout_result.get("transaction_id") or commit_result.get("transaction_id"),
        "td_id": closeout_result.get("td_id") or commit_result.get("td_id"),
        "session_id": closeout_result.get("session_id") or effective_session_id or session_id,
        "step_results": step_results,
    }


def build_work_landing_reconcile_plan(
    repo_root: Path,
    *,
    subject_ids: Sequence[str],
    owned_paths: Sequence[str] = (),
    session_id: str | None = None,
    require_exclusive: bool = False,
    apply: bool = False,
    only: str | None = None,
    created_by: str = "codex",
    commit_hash: str | None = None,
) -> dict[str, Any]:
    status = build_work_landing_status(
        repo_root,
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        session_id=session_id,
        require_exclusive=require_exclusive,
        closed_attempt_overlay=False,
    )
    actions = _ordered_controller_actions(status, repo_root=repo_root.resolve(), commit_hash=commit_hash)
    mode = "apply" if apply else "dry_run"
    apply_result: dict[str, Any] | None = None
    applied_action_id: str | None = None
    normalized_only = str(only or "").strip()
    if apply:
        supported_aliases = (
            RECEIPT_INTAKE_APPLY_ALIASES
            | RECORD_SCOPED_COMMIT_LANDING_ALIASES
            | LAND_SCOPED_COMMIT_ATTEMPT_ALIASES
            | CLOSEOUT_LANDING_ATTEMPT_ALIASES
        )
        if normalized_only not in supported_aliases:
            apply_result = {
                "ok": False,
                "status": "apply_refused_unsupported_or_missing_only",
                "mutated": False,
                "requested_only": normalized_only or None,
                "supported_only": sorted(supported_aliases),
            }
        elif normalized_only in LAND_SCOPED_COMMIT_ATTEMPT_ALIASES:
            apply_result = _apply_land_scoped_commit_attempt(
                repo_root.resolve(),
                status,
                commit_hash=commit_hash,
                created_by=created_by,
                session_id=session_id,
            )
            applied_action_id = LAND_SCOPED_COMMIT_ATTEMPT_ACTION_ID
        elif normalized_only in RECORD_SCOPED_COMMIT_LANDING_ALIASES:
            apply_result = _apply_record_scoped_commit_landing(
                repo_root.resolve(),
                status,
                commit_hash=commit_hash,
                created_by=created_by,
            )
            applied_action_id = RECORD_SCOPED_COMMIT_LANDING_ACTION_ID
        elif normalized_only in CLOSEOUT_LANDING_ATTEMPT_ALIASES:
            apply_result = _apply_closeout_landing_attempt(
                repo_root.resolve(),
                status,
                commit_hash=commit_hash,
                created_by=created_by,
                session_id=session_id,
            )
            applied_action_id = CLOSEOUT_LANDING_ATTEMPT_ACTION_ID
        else:
            apply_result = _apply_receipt_intake(
                repo_root,
                status,
                created_by=created_by,
                session_id=session_id,
            )
            applied_action_id = RECEIPT_INTAKE_ACTION_ID
        if apply_result is not None and applied_action_id:
            refresh_after_apply = (
                bool(apply_result.get("mutated"))
                and applied_action_id != LAND_SCOPED_COMMIT_ATTEMPT_ACTION_ID
            )
            if refresh_after_apply:
                status = build_work_landing_status(
                    repo_root,
                    subject_ids=subject_ids,
                    owned_paths=owned_paths,
                    session_id=session_id,
                    require_exclusive=require_exclusive,
                    closed_attempt_overlay=False,
                )
                actions = _ordered_controller_actions(status, repo_root=repo_root.resolve(), commit_hash=commit_hash)
            for row in actions:
                if row.get("action_id") == applied_action_id:
                    row["apply_result"] = apply_result
                    row["apply_status"] = str(apply_result.get("status") or row.get("apply_status") or "")
                    row["would_mutate"] = bool(apply_result.get("mutated"))
                    if apply_result.get("mutated") and not refresh_after_apply:
                        row["post_apply_status_refresh"] = "skipped_serial_landing_apply_result_authoritative"
                    break
    return {
        "schema": RECONCILE_SCHEMA,
        "legacy_schema": LEGACY_RECONCILE_SCHEMA,
        "mode": mode,
        "status": status.get("convergence", {}).get("status"),
        "subject_ids": status.get("subject_ids") or [],
        "transaction_id": status.get("transaction", {}).get("transaction_id"),
        "recommended_next_action": status.get("recommended_next_action"),
        "actions": actions,
        "apply_result": apply_result,
        "post_apply_status_refresh": (
            "skipped_serial_landing_apply_result_authoritative"
            if apply_result
            and apply_result.get("mutated")
            and applied_action_id == LAND_SCOPED_COMMIT_ATTEMPT_ACTION_ID
            else "refreshed"
            if apply_result and apply_result.get("mutated")
            else "not_needed"
        ),
        "mutation_policy": {
            "would_mutate": bool(apply_result and apply_result.get("mutated")),
            "auto_mutation_allowed": bool(apply),
            "kernel_phase_required": False,
            "allowed_apply_only": sorted(
                RECEIPT_INTAKE_APPLY_ALIASES
                | RECORD_SCOPED_COMMIT_LANDING_ALIASES
                | LAND_SCOPED_COMMIT_ATTEMPT_ALIASES
                | CLOSEOUT_LANDING_ATTEMPT_ALIASES
            ),
            "broad_shared_index_cleanup_allowed": False,
        },
    }
