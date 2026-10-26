"""
[PURPOSE]
- Teleology: PR 3 of the substrate-general Type A roadmap. Make overnight
  Type A subagent work safe against stale returns: an expired lease, an
  abandoned attempt, or a packet whose digest no longer matches must never
  result in obsolete shards being accepted into the substrate. Implements the
  attempt-aware fencing-token contract documented in
  codex/standards/observe_apply/std_raw_seed_attempt_recovery.json.

[INTERFACE]
- Exports:
    compute_packet_digest, RECOVERY_REPORT_SCHEMA, RECOVERY_REPORT_KIND,
    classify_partial_evidence, detect_stale_attempts, plan_recovery,
    apply_recovery, write_recovery_report,
    log_late_import_rejection, type_a_recovery_summary,
    LATE_IMPORT_REJECTIONS_PATH, RECOVERY_REPORT_PATH.
- Reads: paragraph_ledger.json (via raw_seed_paragraph_ledger), extracted_shards.json,
  state/raw_seed_subagent/<run>/packet.json (via subagent lane callers).
- Writes: state/raw_seed/recovery/latest.json (only --commit), and appends to
  state/raw_seed/late_import_rejections.jsonl when an importer rejects a stale bundle.

[FLOW]
- detect_stale_attempts: walk every attempt across the ledger, mark those whose
  lease_expires_at < now as stale_in_flight (attempt-status transition).
- classify_partial_evidence: per-attempt boolean; partial evidence forces
  operator_review_required at apply time.
- plan_recovery: produce a structured plan describing what --commit would do.
- apply_recovery: actually mutate the ledger with mark_attempt_status calls
  and write the recovery report. Pure when called with apply=False.
- log_late_import_rejection: append-only audit row at the importer boundary.

[CONSTRAINTS]
- Append-only attempts list; only attempt-status fields move.
- Preview mode (apply=False) never writes anything.
- packet_digest contract is canonical-JSON sha256 with the digest field excluded.
- The recovery report path is fixed at state/raw_seed/recovery/latest.json so
  reactions/blackboard surfaces can find it without configuration.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from system.lib.raw_seed_paragraph_ledger import (
    DEFAULT_LEASE_SECONDS,
    DistillationAttempt,
    ParagraphLedgerEntry,
    derive_attempt_status,
    load_ledger,
    mark_attempt_status,
    save_ledger,
)

RECOVERY_REPORT_KIND = "raw_seed_attempt_recovery_report"
RECOVERY_REPORT_SCHEMA = "raw_seed_attempt_recovery_v1"
RECOVERY_REPORT_PATH = Path("state/raw_seed/recovery/latest.json")
LATE_IMPORT_REJECTIONS_PATH = Path("state/raw_seed/late_import_rejections.jsonl")


# ---------------------------------------------------------------------------
# Packet digest
# ---------------------------------------------------------------------------


def compute_packet_digest(packet_payload: Mapping[str, Any]) -> str:
    """sha256 over canonical-JSON of the packet payload, EXCLUDING the
    packet_digest field itself.

    Two packets with byte-equal payloads (modulo the packet_digest key) MUST
    produce equal digests. Returns 'sha256:<hex>'.
    """
    if not isinstance(packet_payload, Mapping):
        raise TypeError("packet_payload must be a mapping")
    redacted: dict[str, Any] = {}
    for k, v in packet_payload.items():
        if k == "packet_digest":
            continue
        redacted[k] = v
    canonical = json.dumps(redacted, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def lease_expires_iso(started_at: str, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> str:
    """Compute lease_expires_at = started_at + lease_seconds. Returns ISO-8601."""
    dt = _parse_iso(started_at) or datetime.now(timezone.utc)
    return (dt + timedelta(seconds=int(lease_seconds))).isoformat()


# ---------------------------------------------------------------------------
# Partial-evidence classification
# ---------------------------------------------------------------------------


@dataclass
class PartialEvidence:
    paragraph_id: str
    attempt_id: str
    kinds: list[str] = field(default_factory=list)

    @property
    def present(self) -> bool:
        return bool(self.kinds)


def classify_partial_evidence(
    entry: ParagraphLedgerEntry,
    attempt: DistillationAttempt,
    *,
    extracted_shards_payload: Optional[Mapping[str, Any]] = None,
) -> PartialEvidence:
    """Return a PartialEvidence record listing every evidence kind for this attempt.

    Per the contract, packet existence does NOT count as partial evidence.
    """
    kinds: list[str] = []
    if attempt.finished_at is not None:
        kinds.append("ledger_attempt_finished_at")
    if attempt.outcome is not None:
        kinds.append("ledger_attempt_outcome")
    try:
        if int(attempt.shard_count or 0) > 0:
            kinds.append("ledger_attempt_shard_count")
    except (TypeError, ValueError):
        pass
    # shard_entries on this paragraph that reference this attempt_id
    for sh in entry.shard_entries.values():
        if sh.attempt_id == attempt.attempt_id:
            kinds.append("paragraph_shard_entries_for_attempt")
            break
    # extracted_shards rows whose source_artifact references this attempt id
    if isinstance(extracted_shards_payload, Mapping):
        cohort_id = (attempt.cohort_id or "")
        for shard in extracted_shards_payload.get("shards") or []:
            if not isinstance(shard, Mapping):
                continue
            src = shard.get("source_artifact") or ""
            if not isinstance(src, str):
                continue
            if attempt.attempt_id and attempt.attempt_id in src:
                kinds.append("extracted_shards_source_artifact_attempt_id")
                break
            if cohort_id and cohort_id in src:
                kinds.append("extracted_shards_source_artifact_cohort_id")
                break
    return PartialEvidence(
        paragraph_id=attempt.paragraph_id,
        attempt_id=attempt.attempt_id,
        kinds=kinds,
    )


# ---------------------------------------------------------------------------
# Stale detection + recovery plan
# ---------------------------------------------------------------------------


@dataclass
class RecoveryAction:
    kind: str  # mark_stale | mark_operator_review | mark_abandoned
    paragraph_id: str
    attempt_id: str
    abandoned_reason: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class RecoveryPlan:
    now: str
    lease_seconds_default: int
    counts: dict[str, int] = field(default_factory=dict)
    stale_attempts: list[dict] = field(default_factory=list)
    operator_review_attempts: list[dict] = field(default_factory=list)
    abandonment_candidates: list[dict] = field(default_factory=list)
    actions: list[RecoveryAction] = field(default_factory=list)


def _attempt_age_seconds(attempt: DistillationAttempt, *, now_dt: datetime) -> Optional[int]:
    started = _parse_iso(attempt.lease_started_at or attempt.started_at)
    if started is None:
        return None
    delta = now_dt - started
    return int(delta.total_seconds())


def _open_attempts(entry: ParagraphLedgerEntry) -> list[DistillationAttempt]:
    """Open = no terminal outcome and not abandoned/reclaimed/operator_review."""
    out: list[DistillationAttempt] = []
    for att in entry.attempts:
        if att.finished_at is not None:
            continue
        status = derive_attempt_status(att)
        if status in {
            "abandoned_stale_no_import_evidence",
            "reclaimed_by_new_attempt",
            "operator_review_required",
            "imported", "rejected", "empty", "error",
        }:
            continue
        out.append(att)
    return out


def detect_stale_attempts(
    ledger: Mapping[str, ParagraphLedgerEntry],
    *,
    now: Optional[str] = None,
    lease_seconds_default: int = DEFAULT_LEASE_SECONDS,
) -> list[dict]:
    """Find every open attempt whose lease has expired."""
    now_iso = now or _utc_now_iso()
    now_dt = _parse_iso(now_iso) or datetime.now(timezone.utc)
    stale: list[dict] = []
    for par_id, entry in ledger.items():
        for att in _open_attempts(entry):
            lease_expires = att.lease_expires_at
            if not lease_expires and att.lease_started_at:
                lease_expires = lease_expires_iso(
                    att.lease_started_at,
                    att.lease_seconds or lease_seconds_default,
                )
            elif not lease_expires:
                # No lease info at all (legacy): treat as stale only if started_at
                # is present and older than lease_seconds_default.
                started = _parse_iso(att.started_at)
                if started is None:
                    continue
                if (now_dt - started).total_seconds() < lease_seconds_default:
                    continue
                lease_expires = (started + timedelta(seconds=lease_seconds_default)).isoformat()
            expires_dt = _parse_iso(lease_expires)
            if expires_dt is None or expires_dt > now_dt:
                continue
            stale.append({
                "paragraph_id": par_id,
                "attempt_id": att.attempt_id,
                "claim_epoch": att.claim_epoch,
                "lease_started_at": att.lease_started_at or att.started_at,
                "lease_expires_at": lease_expires,
                "age_seconds": _attempt_age_seconds(att, now_dt=now_dt),
            })
    stale.sort(key=lambda r: (r["paragraph_id"], r["attempt_id"]))
    return stale


def plan_recovery(
    repo_root: Path,
    family_dir: str,
    *,
    now: Optional[str] = None,
    lease_seconds_default: int = DEFAULT_LEASE_SECONDS,
    extracted_shards_payload: Optional[Mapping[str, Any]] = None,
) -> tuple[Mapping[str, ParagraphLedgerEntry], RecoveryPlan]:
    """Produce a structured plan describing what recovery would do.

    Returned ledger map is the live in-memory ledger; apply_recovery applies the
    plan to that map and (when --commit) writes it back. Preview never writes.
    """
    ledger = load_ledger(repo_root, family_dir)
    now_iso = now or _utc_now_iso()
    plan = RecoveryPlan(
        now=now_iso,
        lease_seconds_default=int(lease_seconds_default),
    )

    counts: dict[str, int] = {
        "in_flight": 0,
        "stale_in_flight": 0,
        "abandoned_stale_no_import_evidence": 0,
        "reclaimed_by_new_attempt": 0,
        "operator_review_required": 0,
        "imported": 0,
        "rejected": 0,
        "empty": 0,
        "error": 0,
        "legacy_missing_packet_digest": 0,
    }

    # Histogram across all attempts.
    for entry in ledger.values():
        for att in entry.attempts:
            status = derive_attempt_status(att)
            counts[status] = counts.get(status, 0) + 1

    stale_rows = detect_stale_attempts(
        ledger, now=now_iso, lease_seconds_default=lease_seconds_default,
    )
    plan.stale_attempts = stale_rows
    plan.counts = counts

    for stale in stale_rows:
        par_id = stale["paragraph_id"]
        att_id = stale["attempt_id"]
        entry = ledger.get(par_id)
        if entry is None:
            continue
        att = next((a for a in entry.attempts if a.attempt_id == att_id), None)
        if att is None:
            continue
        evidence = classify_partial_evidence(
            entry, att, extracted_shards_payload=extracted_shards_payload,
        )
        plan.actions.append(RecoveryAction(
            kind="mark_stale",
            paragraph_id=par_id,
            attempt_id=att_id,
            notes="lease_expires_at < now",
        ))
        if evidence.present:
            plan.operator_review_attempts.append({
                "paragraph_id": par_id,
                "attempt_id": att_id,
                "claim_epoch": att.claim_epoch,
                "evidence_kinds": list(evidence.kinds),
            })
            plan.actions.append(RecoveryAction(
                kind="mark_operator_review",
                paragraph_id=par_id,
                attempt_id=att_id,
                abandoned_reason="lease_expired_with_partial_evidence",
                notes=",".join(evidence.kinds),
            ))
        else:
            plan.abandonment_candidates.append({
                "paragraph_id": par_id,
                "attempt_id": att_id,
                "claim_epoch": att.claim_epoch,
                "abandoned_reason": "lease_expired_no_partial_evidence",
            })
            plan.actions.append(RecoveryAction(
                kind="mark_abandoned",
                paragraph_id=par_id,
                attempt_id=att_id,
                abandoned_reason="lease_expired_no_partial_evidence",
            ))
    return ledger, plan


def apply_recovery(
    repo_root: Path,
    family_dir: str,
    ledger: dict[str, ParagraphLedgerEntry],
    plan: RecoveryPlan,
    *,
    commit: bool,
) -> dict[str, Any]:
    """Apply the plan's actions to the live ledger. When commit=True, persist
    the ledger and write the recovery report. When commit=False, no disk writes.
    Returns a result dict with the report payload regardless of commit mode.
    """
    applied = 0
    for action in plan.actions:
        if action.kind == "mark_stale":
            if mark_attempt_status(
                ledger,
                paragraph_id=action.paragraph_id,
                attempt_id=action.attempt_id,
                new_status="stale_in_flight",
            ):
                applied += 1
        elif action.kind == "mark_operator_review":
            if mark_attempt_status(
                ledger,
                paragraph_id=action.paragraph_id,
                attempt_id=action.attempt_id,
                new_status="operator_review_required",
                abandoned_reason=action.abandoned_reason,
            ):
                applied += 1
        elif action.kind == "mark_abandoned":
            if mark_attempt_status(
                ledger,
                paragraph_id=action.paragraph_id,
                attempt_id=action.attempt_id,
                new_status="abandoned_stale_no_import_evidence",
                abandoned_reason=action.abandoned_reason,
            ):
                applied += 1

    report = {
        "kind": RECOVERY_REPORT_KIND,
        "schema_version": RECOVERY_REPORT_SCHEMA,
        "generated_at": _utc_now_iso(),
        "now": plan.now,
        "lease_seconds_default": plan.lease_seconds_default,
        "scope": {"family_dir": family_dir},
        "counts": dict(plan.counts),
        "stale_attempts": list(plan.stale_attempts),
        "operator_review_attempts": list(plan.operator_review_attempts),
        "abandonment_candidates": list(plan.abandonment_candidates),
        "actions": [
            {
                "kind": a.kind,
                "paragraph_id": a.paragraph_id,
                "attempt_id": a.attempt_id,
                "abandoned_reason": a.abandoned_reason,
                "notes": a.notes,
            }
            for a in plan.actions
        ],
        "applied_count": applied if commit else 0,
        "commit": bool(commit),
    }

    if commit:
        save_ledger(repo_root, family_dir, ledger)
        out_path = (repo_root / RECOVERY_REPORT_PATH).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, out_path)
    return report


# ---------------------------------------------------------------------------
# Late-import rejection logger
# ---------------------------------------------------------------------------


def log_late_import_rejection(
    repo_root: Path,
    *,
    paragraph_id: str,
    attempt_id_in_packet: str,
    packet_digest_in_packet: Optional[str],
    ledger_attempt_status: Optional[str],
    ledger_packet_digest: Optional[str],
    ledger_claim_epoch: Optional[int],
    rejection_reason: str,
) -> dict[str, Any]:
    """Append an audit row at the importer boundary when a stale or mismatched
    bundle is rejected. Returns the row written. Always writes to disk; the
    caller decides whether to surface it further.
    """
    row = {
        "rejected_at": _utc_now_iso(),
        "paragraph_id": paragraph_id,
        "attempt_id_in_packet": attempt_id_in_packet,
        "packet_digest_in_packet": packet_digest_in_packet,
        "ledger_attempt_status": ledger_attempt_status,
        "ledger_packet_digest": ledger_packet_digest,
        "ledger_claim_epoch": ledger_claim_epoch,
        "rejection_reason": rejection_reason,
    }
    out_path = (repo_root / LATE_IMPORT_REJECTIONS_PATH).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
        f.write("\n")
    return row


# ---------------------------------------------------------------------------
# Summary projection (for ledger-status + metabolismd blackboard)
# ---------------------------------------------------------------------------


def type_a_recovery_summary(
    repo_root: Path,
    family_dir: str,
    *,
    now: Optional[str] = None,
    lease_seconds_default: int = DEFAULT_LEASE_SECONDS,
) -> dict[str, Any]:
    """Compute a compact projection suitable for the metabolismd blackboard."""
    _, plan = plan_recovery(
        repo_root, family_dir,
        now=now, lease_seconds_default=lease_seconds_default,
    )
    counts = plan.counts
    return {
        "schema": RECOVERY_REPORT_SCHEMA,
        "scope": {"family_dir": family_dir},
        "now": plan.now,
        "lease_seconds_default": plan.lease_seconds_default,
        "attempt_status_counts": dict(counts),
        # ``plan.stale_attempts`` is the unique live stale set after lease
        # evaluation. It already includes attempts whose persisted status is
        # stale_in_flight, so adding counts.stale_in_flight would double-count.
        "stale_attempts_count": len(plan.stale_attempts),
        "abandoned_count": counts.get("abandoned_stale_no_import_evidence", 0),
        "operator_review_count": counts.get("operator_review_required", 0),
        "legacy_missing_packet_digest_count": counts.get("legacy_missing_packet_digest", 0),
        "stale_pending_recovery": [
            {
                "paragraph_id": s["paragraph_id"],
                "attempt_id": s["attempt_id"],
                "claim_epoch": s["claim_epoch"],
                "lease_expires_at": s["lease_expires_at"],
            }
            for s in plan.stale_attempts[:8]
        ],
    }


__all__ = [
    "RECOVERY_REPORT_KIND",
    "RECOVERY_REPORT_SCHEMA",
    "RECOVERY_REPORT_PATH",
    "LATE_IMPORT_REJECTIONS_PATH",
    "PartialEvidence",
    "RecoveryAction",
    "RecoveryPlan",
    "compute_packet_digest",
    "lease_expires_iso",
    "classify_partial_evidence",
    "detect_stale_attempts",
    "plan_recovery",
    "apply_recovery",
    "log_late_import_rejection",
    "type_a_recovery_summary",
]
