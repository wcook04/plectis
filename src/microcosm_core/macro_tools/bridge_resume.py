from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PASS = "pass"
BLOCKED = "blocked"

KIND = "public_bridge_dispatch_yield_resume"
SCHEMA_VERSION = "public_bridge_dispatch_yield_resume_v1"
SOURCE_REF = "tools/meta/bridge/bridge_resume.py"
SOURCE_REFS = [
    SOURCE_REF,
    "system/lib/controller_heartbeat.py",
    "system/lib/continuation_packet.py",
    "codex/standards/std_continuity_protocol.json",
    "codex/doctrine/paper_modules/bridge_runtime.md",
]
SOURCE_SYMBOL_REFS = [
    "tools/meta/bridge/bridge_resume.py::ResumeTarget",
    "tools/meta/bridge/bridge_resume.py::ResumeJob",
    "tools/meta/bridge/bridge_resume.py::SessionSnapshot",
    "tools/meta/bridge/bridge_resume.py::BridgeResumeManager",
    "tools/meta/bridge/bridge_resume.py::format_resume_message",
    "tools/meta/bridge/bridge_resume.py::assess_session_activity",
    "tools/meta/bridge/bridge_resume.py::bridge_dispatch_and_yield",
    "system/lib/controller_heartbeat.py::build_controller_heartbeat",
    "system/lib/continuation_packet.py::build_continuation_packet",
]
TARGET_REF = "microcosm-substrate/src/microcosm_core/macro_tools/bridge_resume.py"
TARGET_REFS = [TARGET_REF]
TARGET_SYMBOL_REFS = [
    "microcosm_core.macro_tools.bridge_resume::ResumeTarget",
    "microcosm_core.macro_tools.bridge_resume::ResumeJob",
    "microcosm_core.macro_tools.bridge_resume::SessionSnapshot",
    "microcosm_core.macro_tools.bridge_resume::PublicBridgeResumeManager",
    "microcosm_core.macro_tools.bridge_resume::format_resume_message",
    "microcosm_core.macro_tools.bridge_resume::assess_session_activity",
    "microcosm_core.macro_tools.bridge_resume::build_public_bridge_dispatch_yield_resume_view",
]

RESUME_MODES = ("none", "manual_artifact", "public_no_send")
EVENT_BUCKETS: dict[str, str] = {
    "dispatch_scheduled": "pending",
    "dispatch_completed": "pending",
    "dispatch_failed": "failed",
    "dispatch_emit_failed": "failed",
    "trigger_written": "pending",
    "skipped_dup": "deduped",
    "inject_ok": "succeeded",
    "inject_failed": "failed",
    "skipped_already_injected": "blocked_already_injected",
    "skipped_not_idle": "blocked_not_idle",
}
TERMINAL_BUCKETS = frozenset(
    {
        "succeeded",
        "failed",
        "deduped",
        "blocked_already_injected",
        "blocked_not_idle",
    }
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_bridge_dispatch_yield_resume_metadata_not_live_bridge_authority",
    "live_bridge_dispatch_authorized": False,
    "host_app_auto_inject_authorized": False,
    "live_browser_hud_access_authorized": False,
    "provider_payload_read": False,
    "account_session_state_exported": False,
    "credential_or_cookie_exported": False,
    "raw_worker_transcript_exported": False,
    "recipient_send_authorized": False,
    "live_work_ledger_mutation_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "private_root_equivalence_claim": False,
}
ANTI_CLAIM = (
    "This public bridge dispatch/yield/resume tool validates the macro resume "
    "protocol over public metadata envelopes: target shape, resume job shape, "
    "short resume message rendering, once-only trigger accounting, session-delta "
    "idle safety, controller-heartbeat refs, and continuation-packet refs. It "
    "does not dispatch live bridge work, paste into host apps, read provider or "
    "browser/HUD state, export transcript bodies, control accounts, send recipient "
    "material, mutate Work Ledger or source, or authorize release."
)

INPUT_NAMES = (
    "bundle_manifest.json",
    "resume_targets.json",
    "resume_jobs.json",
    "session_activity.json",
    "dispatch_resume_policy.json",
    "controller_heartbeat_refs.json",
    "expected_bridge_summary.json",
)

FORBIDDEN_PAYLOAD_KEYS = {
    "raw_worker_transcript_body",
    "raw_bridge_transcript",
    "provider_payload",
    "browser_hud_state",
    "browser_hud_cockpit_state",
    "account_session_state",
    "credential_value",
    "cookie_value",
    "recipient_send_payload",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(value: Any) -> str:
    return str(value or "").strip()


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _stable_digest(payload: object, *, length: int | None = None) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return digest[:length] if length else digest


def _walk_keys(payload: object) -> list[str]:
    if isinstance(payload, Mapping):
        keys = [str(key) for key in payload.keys()]
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def bucket_for_event(event: str | None) -> str:
    if not event:
        return "unknown"
    return EVENT_BUCKETS.get(event, "unknown")


@dataclass
class ResumeTarget:
    target_id: str = "public_fixture_target"
    target_app: str = "artifact_only"
    switch_tab: int | str | None = None
    session_id: str | None = None
    session_url: str | None = None
    sentinel_prefix: str = "[public bridge resume]"
    resume_mode: str = "public_no_send"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResumeTarget":
        return cls(
            target_id=_string(data.get("target_id")) or "public_fixture_target",
            target_app=_string(data.get("target_app")) or "artifact_only",
            switch_tab=data.get("switch_tab"),
            session_id=_string(data.get("session_id")) or None,
            session_url=_string(data.get("session_url")) or None,
            sentinel_prefix=_string(data.get("sentinel_prefix")) or "[public bridge resume]",
            resume_mode=_string(data.get("resume_mode")) or "public_no_send",
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_app": self.target_app,
            "switch_tab": self.switch_tab,
            "session_id": self.session_id,
            "session_url": self.session_url,
            "sentinel_prefix": self.sentinel_prefix,
            "resume_mode": self.resume_mode,
            "live_target": False,
            "body_in_receipt": False,
        }


@dataclass
class ResumeJob:
    job_id: str
    plan_id: str | None = None
    group_label: str | None = None
    target_id: str = "public_fixture_target"
    status: str = "ok"
    summary_lines: list[str] = field(default_factory=list)
    artifact_paths: list[str] = field(default_factory=list)
    continue_instruction: str = ""
    duplicate_emit_attempt: bool = False
    extras: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def new_id(prefix: str = "public_bridge") -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        return f"{prefix}_{ts}_{uuid.uuid4().hex[:8]}"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResumeJob":
        return cls(
            job_id=_string(data.get("job_id")) or cls.new_id(),
            plan_id=_string(data.get("plan_id")) or None,
            group_label=_string(data.get("group_label")) or None,
            target_id=_string(data.get("target_id")) or "public_fixture_target",
            status=_string(data.get("status")) or "ok",
            summary_lines=_strings(data.get("summary_lines")),
            artifact_paths=_strings(data.get("artifact_paths")),
            continue_instruction=_string(data.get("continue_instruction")),
            duplicate_emit_attempt=bool(data.get("duplicate_emit_attempt")),
            extras=dict(data.get("extras") or {}),
        )

    def to_public_dict(self) -> dict[str, Any]:
        payload = dataclasses.asdict(self)
        payload["body_in_receipt"] = False
        return payload


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: str | None
    jsonl_path_ref: str
    jsonl_byte_size: int
    jsonl_mtime_ns: int
    captured_at: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SessionSnapshot":
        return cls(
            session_id=_string(data.get("session_id")) or None,
            jsonl_path_ref=_string(data.get("jsonl_path_ref")) or "public_fixture_session.jsonl",
            jsonl_byte_size=int(data.get("jsonl_byte_size") or 0),
            jsonl_mtime_ns=int(data.get("jsonl_mtime_ns") or 0),
            captured_at=_string(data.get("captured_at")) or _utc_now(),
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "jsonl_path_ref": self.jsonl_path_ref,
            "jsonl_byte_size": self.jsonl_byte_size,
            "jsonl_mtime_ns": self.jsonl_mtime_ns,
            "captured_at": self.captured_at,
            "body_in_receipt": False,
        }


@dataclass(frozen=True)
class ActivityReport:
    has_delta: bool
    delta_bytes: int
    delta_contains_sentinel: bool
    delta_contains_foreign_user: bool
    safe_to_inject: bool
    reason: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "has_delta": self.has_delta,
            "delta_bytes": self.delta_bytes,
            "delta_contains_sentinel": self.delta_contains_sentinel,
            "delta_contains_foreign_user": self.delta_contains_foreign_user,
            "safe_to_inject": self.safe_to_inject,
            "reason": self.reason,
            "body_in_receipt": False,
        }


def _extract_user_text_from_public_row(row: Mapping[str, Any]) -> str | None:
    if _string(row.get("type")) != "user":
        return None
    content = row.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, Mapping) and _string(block.get("type")) == "text":
                parts.append(_string(block.get("text")))
        return " ".join(part for part in parts if part)
    return None


def assess_session_activity(
    snapshot: SessionSnapshot,
    sentinel: str,
    *,
    delta_rows: Sequence[Mapping[str, Any]] = (),
    delta_bytes: int | None = None,
) -> ActivityReport:
    contains_sentinel = False
    contains_foreign_user = False
    saw_user_row = False
    for row in delta_rows:
        user_text = _extract_user_text_from_public_row(row)
        if user_text is None:
            continue
        saw_user_row = True
        if sentinel and sentinel in user_text:
            contains_sentinel = True
        else:
            contains_foreign_user = True
    if contains_foreign_user:
        return ActivityReport(
            has_delta=True,
            delta_bytes=int(delta_bytes if delta_bytes is not None else len(delta_rows)),
            delta_contains_sentinel=contains_sentinel,
            delta_contains_foreign_user=True,
            safe_to_inject=False,
            reason="foreign_user_activity",
        )
    if contains_sentinel:
        return ActivityReport(
            has_delta=True,
            delta_bytes=int(delta_bytes if delta_bytes is not None else len(delta_rows)),
            delta_contains_sentinel=True,
            delta_contains_foreign_user=False,
            safe_to_inject=False,
            reason="already_injected",
        )
    if saw_user_row:
        return ActivityReport(
            has_delta=True,
            delta_bytes=int(delta_bytes if delta_bytes is not None else len(delta_rows)),
            delta_contains_sentinel=False,
            delta_contains_foreign_user=False,
            safe_to_inject=False,
            reason="unclassified_user_row",
        )
    if delta_rows:
        return ActivityReport(
            has_delta=True,
            delta_bytes=int(delta_bytes if delta_bytes is not None else len(delta_rows)),
            delta_contains_sentinel=False,
            delta_contains_foreign_user=False,
            safe_to_inject=True,
            reason="assistant_only_delta",
        )
    return ActivityReport(
        has_delta=False,
        delta_bytes=0,
        delta_contains_sentinel=False,
        delta_contains_foreign_user=False,
        safe_to_inject=True,
        reason="no_delta",
    )


def format_resume_message(
    job: ResumeJob,
    *,
    max_summary_lines: int = 10,
    include_continue: bool = True,
) -> str:
    lines: list[str] = []
    preamble = _string(job.extras.get("dispatch_loop_preamble"))
    if preamble:
        lines.append(preamble)
    lines.append(f"BRIDGE RESUME job={job.job_id} status={job.status}")
    lines.append(f"plan: {job.plan_id or 'n/a'}")
    lines.append(f"group: {job.group_label or 'n/a'}")
    summary = list(job.summary_lines or [])
    if len(summary) > max_summary_lines:
        truncated = summary[:max_summary_lines]
        truncated.append(
            f"... ({len(summary) - max_summary_lines} more lines truncated; open the artifact for full output)"
        )
        summary = truncated
    if summary:
        lines.append("")
        lines.append("summary:")
        for item in summary:
            token = _string(item)
            if token:
                lines.append(f"- {token}")
    if job.artifact_paths:
        lines.append("")
        lines.append("artifacts:")
        for item in job.artifact_paths:
            token = _string(item)
            if token:
                lines.append(f"- {token}")
    if include_continue and job.continue_instruction:
        lines.append("")
        lines.append(f"continue: {job.continue_instruction.strip()}")
    return "\n".join(lines)


class PublicBridgeResumeManager:
    def __init__(self, target: ResumeTarget) -> None:
        self.target = target
        self.ledger_rows: list[dict[str, Any]] = []
        self._emitted: set[str] = set()

    def append_ledger(self, event: str, job_id: str, **details: Any) -> None:
        self.ledger_rows.append(
            {
                "ts": _utc_now(),
                "event": event,
                "job_id": job_id,
                "details": details,
                "body_in_receipt": False,
            }
        )

    def emit_trigger(
        self,
        job: ResumeJob,
        *,
        allow_dup: bool = False,
        submit: bool = False,
        snapshot: SessionSnapshot | None = None,
    ) -> dict[str, Any] | None:
        if not allow_dup and job.job_id in self._emitted:
            self.append_ledger("skipped_dup", job.job_id, reason="already_in_ledger")
            return None
        self._emitted.add(job.job_id)
        sentinel = f"{self.target.sentinel_prefix} job={job.job_id}"
        trigger = {
            "trigger_id": f"public_trigger_{_stable_digest({'job_id': job.job_id}, length=12)}",
            "text": format_resume_message(job),
            "sentinel": sentinel,
            "submit": bool(submit),
            "target": self.target.to_public_dict(),
            "_resume": {
                "schema_version": SCHEMA_VERSION,
                "job_id": job.job_id,
                "plan_id": job.plan_id,
                "group_label": job.group_label,
                "status": job.status,
                "dispatch_snapshot": snapshot.to_public_dict() if snapshot else None,
                "no_send_fixture": True,
            },
            "body_in_receipt": False,
        }
        self.append_ledger(
            "trigger_written",
            job.job_id,
            schema_version=SCHEMA_VERSION,
            sentinel=sentinel,
            target_id=self.target.target_id,
            status=job.status,
            submit=False,
            dispatch_snapshot=snapshot.to_public_dict() if snapshot else None,
        )
        return trigger

    def job_states(self) -> dict[str, dict[str, Any]]:
        states: dict[str, dict[str, Any]] = {}
        for row in self.ledger_rows:
            job_id = _string(row.get("job_id"))
            if not job_id:
                continue
            state = states.setdefault(
                job_id,
                {
                    "job_id": job_id,
                    "current_state": None,
                    "bucket": "unknown",
                    "events": [],
                    "body_in_receipt": False,
                },
            )
            event = _string(row.get("event"))
            state["current_state"] = event
            state["bucket"] = bucket_for_event(event)
            state["events"].append({"event": event, "ts": row.get("ts")})
        return states


def _validate_policy(policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for key, expected in {
        "live_bridge_dispatch_authorized": False,
        "host_app_auto_inject_authorized": False,
        "browser_hud_cockpit_state_read": False,
        "provider_payload_read": False,
        "account_session_state_exported": False,
        "credential_or_cookie_exported": False,
        "raw_worker_transcript_exported": False,
        "recipient_send_authorized": False,
        "live_work_ledger_mutation_authorized": False,
        "source_mutation_authorized": False,
        "release_authorized": False,
        "private_data_equivalence_claim": False,
        "metadata_envelope_only": True,
        "body_in_receipt": False,
    }.items():
        if policy.get(key) is not expected:
            findings.append(
                {
                    "error_code": "BRIDGE_RESUME_POLICY_AUTHORITY_OVERCLAIM",
                    "message": f"dispatch_resume_policy.{key} must be {expected!r}.",
                    "subject_id": key,
                    "subject_kind": "dispatch_resume_policy",
                    "body_in_receipt": False,
                }
            )
    return findings


def build_public_bridge_dispatch_yield_resume_view(
    payloads: Mapping[str, Any],
) -> dict[str, Any]:
    manifest = payloads.get("bundle_manifest")
    manifest = manifest if isinstance(manifest, Mapping) else {}
    targets = [ResumeTarget.from_dict(row) for row in _rows(payloads.get("resume_targets"), "resume_targets")]
    jobs = [ResumeJob.from_dict(row) for row in _rows(payloads.get("resume_jobs"), "resume_jobs")]
    snapshots = {
        _string(row.get("session_id")): {
            "snapshot": SessionSnapshot.from_dict(row),
            "delta_rows": _rows(row, "delta_rows"),
            "delta_bytes": int(row.get("delta_bytes") or 0),
        }
        for row in _rows(payloads.get("session_activity"), "session_activity")
    }
    policy = payloads.get("dispatch_resume_policy")
    policy = policy if isinstance(policy, Mapping) else {}
    expected = payloads.get("expected_bridge_summary")
    expected = expected if isinstance(expected, Mapping) else {}
    controller_refs = _rows(payloads.get("controller_heartbeat_refs"), "controller_heartbeat_refs")

    findings = _validate_policy(policy)
    forbidden_keys = sorted(set(_walk_keys(payloads)) & FORBIDDEN_PAYLOAD_KEYS)
    for key in forbidden_keys:
        findings.append(
            {
                "error_code": "BRIDGE_RESUME_FORBIDDEN_PAYLOAD_KEY",
                "message": "Bridge dispatch/yield/resume bundle contains a forbidden payload key.",
                "subject_id": key,
                "subject_kind": "public_bridge_bundle",
                "body_in_receipt": False,
            }
        )
    target_by_id = {target.target_id: target for target in targets}
    trigger_rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    activity_reports: list[dict[str, Any]] = []
    message_lengths: list[int] = []
    no_send_trigger_count = 0
    skipped_dup_count = 0
    safe_to_inject_count = 0
    blocked_activity_count = 0

    for job in jobs:
        target = target_by_id.get(job.target_id)
        if target is None:
            findings.append(
                {
                    "error_code": "BRIDGE_RESUME_TARGET_MISSING",
                    "message": "Resume job must reference a public resume target.",
                    "subject_id": job.job_id,
                    "subject_kind": "resume_job",
                    "body_in_receipt": False,
                }
            )
            continue
        session_key = _string(target.session_id)
        snapshot_row = snapshots.get(session_key, {})
        snapshot = snapshot_row.get("snapshot")
        manager = PublicBridgeResumeManager(target)
        trigger = manager.emit_trigger(
            job,
            submit=False,
            snapshot=snapshot if isinstance(snapshot, SessionSnapshot) else None,
        )
        if trigger is not None:
            trigger_rows.append(trigger)
            message_lengths.append(len(_string(trigger.get("text"))))
            if trigger.get("submit") is False:
                no_send_trigger_count += 1
        if job.duplicate_emit_attempt:
            manager.emit_trigger(
                job,
                submit=False,
                snapshot=snapshot if isinstance(snapshot, SessionSnapshot) else None,
            )
        ledger_rows.extend(manager.ledger_rows)
        skipped_dup_count += sum(1 for row in manager.ledger_rows if row.get("event") == "skipped_dup")
        if isinstance(snapshot, SessionSnapshot):
            sentinel = _string(trigger.get("sentinel")) if trigger else f"{target.sentinel_prefix} job={job.job_id}"
            report = assess_session_activity(
                snapshot,
                sentinel,
                delta_rows=snapshot_row.get("delta_rows", []),
                delta_bytes=snapshot_row.get("delta_bytes", 0),
            )
            report_row = report.to_public_dict()
            report_row["job_id"] = job.job_id
            activity_reports.append(report_row)
            if report.safe_to_inject:
                safe_to_inject_count += 1
            else:
                blocked_activity_count += 1
        else:
            findings.append(
                {
                    "error_code": "BRIDGE_RESUME_SESSION_SNAPSHOT_MISSING",
                    "message": "Resume job target must have a public session snapshot row.",
                    "subject_id": job.job_id,
                    "subject_kind": "resume_job",
                    "body_in_receipt": False,
                }
            )
    trigger_written_count = sum(1 for row in ledger_rows if row.get("event") == "trigger_written")
    controller_ref_count = len(controller_refs)
    summary = {
        "target_count": len(targets),
        "resume_job_count": len(jobs),
        "trigger_written_count": trigger_written_count,
        "no_send_trigger_count": no_send_trigger_count,
        "skipped_dup_count": skipped_dup_count,
        "safe_to_inject_count": safe_to_inject_count,
        "blocked_activity_count": blocked_activity_count,
        "controller_heartbeat_ref_count": controller_ref_count,
        "message_under_2kb_count": sum(1 for length in message_lengths if length < 2048),
        "body_in_receipt": False,
    }
    expected_summary = expected.get("summary") if isinstance(expected.get("summary"), Mapping) else {}
    for key, value in expected_summary.items():
        if key in summary and summary[key] != value:
            findings.append(
                {
                    "error_code": "BRIDGE_RESUME_EXPECTED_SUMMARY_MISMATCH",
                    "message": "Expected bridge summary does not match computed public dispatch/yield/resume view.",
                    "subject_id": key,
                    "subject_kind": "expected_bridge_summary",
                    "body_in_receipt": False,
                }
            )
    if not controller_refs:
        findings.append(
            {
                "error_code": "BRIDGE_RESUME_CONTROLLER_HEARTBEAT_REF_MISSING",
                "message": "Bundle must include at least one controller heartbeat ref.",
                "subject_id": "controller_heartbeat_refs",
                "subject_kind": "controller_heartbeat_refs",
                "body_in_receipt": False,
            }
        )
    bundle_id = _string(manifest.get("bundle_id")) or "public_bridge_dispatch_yield_resume_bundle"
    view_fingerprint = _stable_digest(
        {
            "bundle_id": bundle_id,
            "summary": summary,
            "ledger_rows": [
                {"event": row.get("event"), "job_id": row.get("job_id")}
                for row in ledger_rows
            ],
        },
        length=16,
    )
    return {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "status": PASS if not findings and jobs and targets else BLOCKED,
        "bundle_id": bundle_id,
        "bundle_manifest_schema_version": manifest.get("schema_version"),
        "summary": summary,
        "findings": findings,
        "error_codes": sorted({str(row.get("error_code") or "") for row in findings}),
        "source_refs": _strings(manifest.get("source_refs")) or SOURCE_REFS,
        "target_refs": _strings(manifest.get("target_refs")) or TARGET_REFS,
        "source_symbols": SOURCE_SYMBOL_REFS,
        "target_symbols": TARGET_SYMBOL_REFS,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "policy_validation": {
            "status": PASS if not _validate_policy(policy) else BLOCKED,
            "policy_id": policy.get("policy_id"),
            "forbidden_authority_rejected": not _validate_policy(policy),
            "metadata_envelope_only": policy.get("metadata_envelope_only") is True,
            "body_in_receipt": False,
        },
        "resume_targets": [target.to_public_dict() for target in targets],
        "resume_jobs": [job.to_public_dict() for job in jobs],
        "public_trigger_rows": trigger_rows,
        "public_ledger_rows": ledger_rows,
        "activity_reports": activity_reports,
        "controller_heartbeat_refs": controller_refs,
        "expected_summary": expected_summary,
        "forbidden_payload_keys": forbidden_keys,
        "view_fingerprint": view_fingerprint,
        "body_import_verification": {
            "verification_status": "verified",
            "verification_mode": "source_faithful_public_refactor",
            "source_to_target_relation": "source_faithful_public_light_edit",
            "source_ref": SOURCE_REF,
            "target_ref": TARGET_REF,
            "body_in_receipt": False,
        },
        "metadata_envelope_only": True,
        "body_in_receipt": False,
    }


def load_public_bridge_dispatch_yield_resume_bundle(input_dir: str | Path) -> dict[str, Any]:
    root = Path(input_dir)
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in (root / name for name in INPUT_NAMES)
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m microcosm_core.macro_tools.bridge_resume")
    parser.add_argument("action", choices=["validate-public-bundle"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    view = build_public_bridge_dispatch_yield_resume_view(
        load_public_bridge_dispatch_yield_resume_bundle(args.input)
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(view, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if view.get("status") == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
