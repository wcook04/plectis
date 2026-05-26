"""
[PURPOSE]
- Teleology: Track per-paragraph and per-shard lifecycle state for the raw-seed
  distillation metabolism loop. Makes the backlog legible: what is untouched,
  what is in flight, what has been validated, imported, rejected, or superseded.
  Enables backlog-aware dispatch from both bridge and subagent lanes.

[INTERFACE]
- Exports:
  - ShardLedgerEntry, DistillationAttempt, ParagraphLedgerEntry dataclasses
  - PARAGRAPH_STATES: the exhaustive computed-state enum
  - load_ledger, save_ledger
  - record_dispatch, record_validator_result, record_import, record_rejection
  - compute_paragraph_state, paragraph_state_counts
  - paragraph_ledger_path_for_family
- Reads / writes:
  - <family_dir>/raw_seed/raw_seed_paragraph_ledger.json
    schema: raw_seed_paragraph_ledger_v1
- State transitions append to `attempts` — never mutated retroactively.

[FLOW]
- backlog-slice marks N paragraphs in_flight via record_dispatch; writes an
  attempt row with lane + cohort_id + attempt_id.
- Per-shard validator result updates shard_entries[shard_id].state via
  record_validator_result (imported / validated / rejected).
- record_import closes the attempt and stamps imported_at.
- compute_paragraph_state reduces shard_entries into the computed enum
  (untouched / in_flight / partially_imported / fully_imported / fully_rejected
  / superseded).

[CONSTRAINTS]
- attempts list is append-only.
- The ledger does not own shard storage (that is extracted_shards.json); it
  tracks provenance and lifecycle only.
- Timestamps are UTC ISO-8601 with offset.
- Opus-seed entries are provenance-sticky: state `superseded` reserved for
  the case where a later Opus re-seed explicitly replaces an earlier attempt.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Optional

from system.lib.raw_seed_registry import raw_seed_workspace_dir_for_family

LEDGER_FILENAME = "raw_seed_paragraph_ledger.json"
LEDGER_SCHEMA = "raw_seed_paragraph_ledger_v1"

ShardState = Literal[
    "in_flight",
    "validated",
    "imported",
    "rejected",
    "superseded",
]

Lane = Literal["bridge", "subagent", "opus_seed", "local_atomize"]

ParagraphState = Literal[
    "untouched",
    "in_flight",
    "partially_imported",
    "fully_imported",
    "fully_rejected",
    "superseded",
    "operator_review_required",
]

PARAGRAPH_STATES: tuple[ParagraphState, ...] = (
    "untouched",
    "in_flight",
    "partially_imported",
    "fully_imported",
    "fully_rejected",
    "superseded",
    "operator_review_required",
)

# PR 3 — attempt-aware state machine. See codex/standards/observe_apply/std_raw_seed_attempt_recovery.json.
AttemptStatus = Literal[
    "in_flight",
    "stale_in_flight",
    "abandoned_stale_no_import_evidence",
    "reclaimed_by_new_attempt",
    "operator_review_required",
    "imported",
    "rejected",
    "empty",
    "error",
    "legacy_missing_packet_digest",
]

ATTEMPT_STATUSES: tuple[AttemptStatus, ...] = (
    "in_flight",
    "stale_in_flight",
    "abandoned_stale_no_import_evidence",
    "reclaimed_by_new_attempt",
    "operator_review_required",
    "imported",
    "rejected",
    "empty",
    "error",
    "legacy_missing_packet_digest",
)

DEFAULT_LEASE_SECONDS = 1800  # 30 minutes


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_attempt_id() -> str:
    return f"att_{uuid.uuid4().hex[:16]}"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ShardLedgerEntry:
    shard_id: str
    paragraph_id: str
    state: ShardState
    lane: Lane
    attempt_id: str
    created_at: str
    updated_at: str
    source_substrate: str = "raw_seed"
    authored_by: str = "operator"
    last_reason: Optional[str] = None


@dataclass
class DistillationAttempt:
    attempt_id: str
    paragraph_id: str
    lane: Lane
    cohort_id: Optional[str]
    started_at: str
    source_substrate: str = "raw_seed"
    authored_by: str = "operator"
    finished_at: Optional[str] = None
    outcome: Optional[str] = None  # imported / rejected / empty / error
    shard_count: int = 0
    reason: Optional[str] = None
    # PR 3: attempt-aware identity + recovery state. All optional with safe
    # legacy defaults so v0 ledgers coerce cleanly.
    claim_id: Optional[str] = None
    claim_epoch: int = 1
    packet_digest: Optional[str] = None  # 'sha256:<hex>' or None for legacy attempts
    lease_started_at: Optional[str] = None
    lease_expires_at: Optional[str] = None
    lease_seconds: Optional[int] = None
    attempt_status: Optional[str] = None  # AttemptStatus or None for legacy
    abandoned_at: Optional[str] = None
    abandoned_reason: Optional[str] = None
    replaced_by_attempt_id: Optional[str] = None


@dataclass
class ParagraphLedgerEntry:
    paragraph_id: str
    source_substrate: str = "raw_seed"
    authored_by: str = "operator"
    shard_entries: dict[str, ShardLedgerEntry] = field(default_factory=dict)
    attempts: list[DistillationAttempt] = field(default_factory=list)
    first_touched_at: Optional[str] = None
    last_touched_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def paragraph_ledger_path_for_family(family_dir: str) -> str:
    workspace = raw_seed_workspace_dir_for_family(family_dir)
    return f"{workspace}/{LEDGER_FILENAME}" if workspace else LEDGER_FILENAME


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------


def _coerce_shard_entry(payload: Mapping[str, Any]) -> ShardLedgerEntry:
    return ShardLedgerEntry(
        shard_id=str(payload.get("shard_id") or ""),
        paragraph_id=str(payload.get("paragraph_id") or ""),
        state=str(payload.get("state") or "in_flight"),  # type: ignore[arg-type]
        lane=str(payload.get("lane") or "bridge"),  # type: ignore[arg-type]
        attempt_id=str(payload.get("attempt_id") or ""),
        created_at=str(payload.get("created_at") or _utc_now()),
        updated_at=str(payload.get("updated_at") or _utc_now()),
        source_substrate=str(payload.get("source_substrate") or "raw_seed"),
        authored_by=str(payload.get("authored_by") or "operator"),
        last_reason=payload.get("last_reason"),
    )


def _coerce_attempt(payload: Mapping[str, Any]) -> DistillationAttempt:
    claim_epoch_raw = payload.get("claim_epoch")
    try:
        claim_epoch = int(claim_epoch_raw) if claim_epoch_raw is not None else 1
    except (TypeError, ValueError):
        claim_epoch = 1
    lease_seconds_raw = payload.get("lease_seconds")
    try:
        lease_seconds = int(lease_seconds_raw) if lease_seconds_raw is not None else None
    except (TypeError, ValueError):
        lease_seconds = None
    return DistillationAttempt(
        attempt_id=str(payload.get("attempt_id") or _new_attempt_id()),
        paragraph_id=str(payload.get("paragraph_id") or ""),
        lane=str(payload.get("lane") or "bridge"),  # type: ignore[arg-type]
        cohort_id=payload.get("cohort_id"),
        started_at=str(payload.get("started_at") or _utc_now()),
        source_substrate=str(payload.get("source_substrate") or "raw_seed"),
        authored_by=str(payload.get("authored_by") or "operator"),
        finished_at=payload.get("finished_at"),
        outcome=payload.get("outcome"),
        shard_count=int(payload.get("shard_count") or 0),
        reason=payload.get("reason"),
        claim_id=payload.get("claim_id"),
        claim_epoch=claim_epoch,
        packet_digest=payload.get("packet_digest"),
        lease_started_at=payload.get("lease_started_at"),
        lease_expires_at=payload.get("lease_expires_at"),
        lease_seconds=lease_seconds,
        attempt_status=payload.get("attempt_status"),
        abandoned_at=payload.get("abandoned_at"),
        abandoned_reason=payload.get("abandoned_reason"),
        replaced_by_attempt_id=payload.get("replaced_by_attempt_id"),
    )


def _coerce_paragraph_entry(payload: Mapping[str, Any]) -> ParagraphLedgerEntry:
    shard_entries_raw = payload.get("shard_entries") or {}
    shard_entries: dict[str, ShardLedgerEntry] = {}
    if isinstance(shard_entries_raw, Mapping):
        for shard_id, shard_payload in shard_entries_raw.items():
            if isinstance(shard_payload, Mapping):
                entry = _coerce_shard_entry({"shard_id": shard_id, **shard_payload})
                shard_entries[entry.shard_id] = entry
    attempts_raw = payload.get("attempts") or []
    attempts = [
        _coerce_attempt(att) for att in attempts_raw if isinstance(att, Mapping)
    ]
    return ParagraphLedgerEntry(
        paragraph_id=str(payload.get("paragraph_id") or ""),
        source_substrate=str(payload.get("source_substrate") or "raw_seed"),
        authored_by=str(payload.get("authored_by") or "operator"),
        shard_entries=shard_entries,
        attempts=attempts,
        first_touched_at=payload.get("first_touched_at"),
        last_touched_at=payload.get("last_touched_at"),
    )


def load_ledger(repo_root: Path, family_dir: str) -> dict[str, ParagraphLedgerEntry]:
    """Load the ledger for a family. Returns an empty dict if the file is absent."""
    path = repo_root / paragraph_ledger_path_for_family(family_dir)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    entries_raw = payload.get("paragraphs") or {}
    if not isinstance(entries_raw, Mapping):
        return {}
    result: dict[str, ParagraphLedgerEntry] = {}
    for par_id, entry_payload in entries_raw.items():
        if not isinstance(entry_payload, Mapping):
            continue
        entry = _coerce_paragraph_entry({"paragraph_id": par_id, **entry_payload})
        result[entry.paragraph_id] = entry
    return result


def save_ledger(
    repo_root: Path,
    family_dir: str,
    ledger: Mapping[str, ParagraphLedgerEntry],
) -> None:
    """Atomic-ish write of the ledger payload."""
    path = repo_root / paragraph_ledger_path_for_family(family_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "raw_seed_paragraph_ledger",
        "schema_version": LEDGER_SCHEMA,
        "family_dir": family_dir,
        "updated_at": _utc_now(),
        "paragraphs": {
            par_id: {
                "paragraph_id": entry.paragraph_id,
                "source_substrate": entry.source_substrate,
                "authored_by": entry.authored_by,
                "first_touched_at": entry.first_touched_at,
                "last_touched_at": entry.last_touched_at,
                "shard_entries": {
                    shard_id: asdict(shard)
                    for shard_id, shard in entry.shard_entries.items()
                },
                "attempts": [asdict(att) for att in entry.attempts],
            }
            for par_id, entry in ledger.items()
        },
    }
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    tmp_path.replace(path)


# ---------------------------------------------------------------------------
# Mutators (record_*)
# ---------------------------------------------------------------------------


def _normalize_source_substrate(value: str | None) -> str:
    token = str(value or "").strip()
    return token or "raw_seed"


def _normalize_authored_by(value: str | None, *, source_substrate: str) -> str:
    token = str(value or "").strip()
    if token:
        return token
    return "operator" if source_substrate == "raw_seed" else "agent_collective"


def _ensure_entry(
    ledger: dict[str, ParagraphLedgerEntry],
    paragraph_id: str,
    *,
    source_substrate: str = "raw_seed",
    authored_by: str = "operator",
) -> ParagraphLedgerEntry:
    entry = ledger.get(paragraph_id)
    normalized_substrate = _normalize_source_substrate(source_substrate)
    normalized_author = _normalize_authored_by(
        authored_by,
        source_substrate=normalized_substrate,
    )
    if entry is None:
        entry = ParagraphLedgerEntry(
            paragraph_id=paragraph_id,
            source_substrate=normalized_substrate,
            authored_by=normalized_author,
        )
        ledger[paragraph_id] = entry
        return entry
    if not str(entry.source_substrate or "").strip():
        entry.source_substrate = normalized_substrate
    if not str(entry.authored_by or "").strip():
        entry.authored_by = normalized_author
    return entry


def next_claim_epoch_for_paragraph(entry: ParagraphLedgerEntry) -> int:
    """Compute the next claim_epoch for a new attempt on this paragraph.

    Reclaiming a paragraph after stale-abandonment must issue an epoch strictly
    greater than every prior attempt's epoch on this paragraph. PR 3 fencing
    token contract: late writes with epoch < current MUST be rejected.
    """
    if not entry.attempts:
        return 1
    max_epoch = 0
    for att in entry.attempts:
        try:
            ep = int(att.claim_epoch or 0)
        except (TypeError, ValueError):
            ep = 0
        if ep > max_epoch:
            max_epoch = ep
    return max_epoch + 1 if max_epoch >= 1 else 1


def derive_attempt_status(att: DistillationAttempt) -> str:
    """Derive an attempt_status when one is missing (legacy ledger rows)."""
    if att.attempt_status:
        return att.attempt_status
    if att.outcome == "imported":
        return "imported"
    if att.outcome == "rejected":
        return "rejected"
    if att.outcome == "empty":
        return "empty"
    if att.outcome == "error":
        return "error"
    if att.finished_at is None:
        if att.packet_digest is None and att.claim_id is None:
            # Pre-PR-3 in-flight rows have no packet_digest. Surface explicitly.
            return "legacy_missing_packet_digest"
        return "in_flight"
    return "in_flight"


def lookup_attempt(
    entry: ParagraphLedgerEntry,
    attempt_id: str,
) -> Optional[DistillationAttempt]:
    for att in entry.attempts:
        if att.attempt_id == attempt_id:
            return att
    return None


def record_dispatch(
    ledger: dict[str, ParagraphLedgerEntry],
    *,
    paragraph_id: str,
    lane: Lane,
    cohort_id: Optional[str] = None,
    attempt_id: Optional[str] = None,
    source_substrate: str = "raw_seed",
    authored_by: str = "operator",
    claim_id: Optional[str] = None,
    claim_epoch: Optional[int] = None,
    packet_digest: Optional[str] = None,
    lease_started_at: Optional[str] = None,
    lease_expires_at: Optional[str] = None,
    lease_seconds: Optional[int] = None,
    replaces_attempt_id: Optional[str] = None,
) -> DistillationAttempt:
    """Mark a paragraph in_flight for a new attempt. Returns the attempt record.

    PR 3: callers may pass claim_id, claim_epoch, packet_digest, lease window.
    If ``replaces_attempt_id`` is set, the previous attempt is marked
    reclaimed_by_new_attempt and its replaced_by_attempt_id is filled.
    If claim_epoch is omitted it is computed via next_claim_epoch_for_paragraph.
    """
    entry = _ensure_entry(
        ledger,
        paragraph_id,
        source_substrate=source_substrate,
        authored_by=authored_by,
    )
    now = _utc_now()
    normalized_substrate = _normalize_source_substrate(
        source_substrate or entry.source_substrate
    )
    normalized_author = _normalize_authored_by(
        authored_by or entry.authored_by,
        source_substrate=normalized_substrate,
    )
    entry.source_substrate = normalized_substrate
    entry.authored_by = normalized_author

    new_attempt_id = attempt_id or _new_attempt_id()
    epoch = claim_epoch if claim_epoch is not None else next_claim_epoch_for_paragraph(entry)

    if replaces_attempt_id:
        prior = lookup_attempt(entry, replaces_attempt_id)
        if prior is not None:
            if prior.attempt_status not in {"imported", "rejected"}:
                prior.attempt_status = "reclaimed_by_new_attempt"
                prior.replaced_by_attempt_id = new_attempt_id
                if prior.abandoned_at is None:
                    prior.abandoned_at = now
                if prior.abandoned_reason is None:
                    prior.abandoned_reason = "reclaim_succeeded"

    attempt = DistillationAttempt(
        attempt_id=new_attempt_id,
        paragraph_id=paragraph_id,
        lane=lane,
        cohort_id=cohort_id,
        started_at=now,
        source_substrate=normalized_substrate,
        authored_by=normalized_author,
        claim_id=claim_id,
        claim_epoch=int(epoch),
        packet_digest=packet_digest,
        lease_started_at=lease_started_at or now,
        lease_expires_at=lease_expires_at,
        lease_seconds=lease_seconds,
        attempt_status="in_flight",
    )
    entry.attempts.append(attempt)
    if entry.first_touched_at is None:
        entry.first_touched_at = now
    entry.last_touched_at = now
    return attempt


def record_validator_result(
    ledger: dict[str, ParagraphLedgerEntry],
    *,
    paragraph_id: str,
    attempt_id: str,
    lane: Lane,
    accepted_shard_ids: Iterable[str],
    flagged_shard_ids: Iterable[str] = (),
    rejected_shard_ids: Iterable[str] = (),
    rejected_reasons: Mapping[str, str] | None = None,
    source_substrate: str | None = None,
    authored_by: str | None = None,
) -> None:
    """Record per-shard validator outcomes. Imported shards flip to 'imported'
    in record_import; this records the upstream validator classification.

    States set here:
      - accepted_shard_ids → 'validated' (will be flipped to 'imported' on record_import)
      - flagged_shard_ids  → 'validated' with last_reason set to the flag
      - rejected_shard_ids → 'rejected' with last_reason
    """
    entry = _ensure_entry(
        ledger,
        paragraph_id,
        source_substrate=source_substrate or "raw_seed",
        authored_by=authored_by or "operator",
    )
    now = _utc_now()
    reasons = dict(rejected_reasons or {})
    normalized_substrate = _normalize_source_substrate(
        source_substrate or entry.source_substrate
    )
    normalized_author = _normalize_authored_by(
        authored_by or entry.authored_by,
        source_substrate=normalized_substrate,
    )
    entry.source_substrate = normalized_substrate
    entry.authored_by = normalized_author

    def _upsert(shard_id: str, state: ShardState, reason: Optional[str]) -> None:
        existing = entry.shard_entries.get(shard_id)
        if existing is None:
            entry.shard_entries[shard_id] = ShardLedgerEntry(
                shard_id=shard_id,
                paragraph_id=paragraph_id,
                state=state,
                lane=lane,
                attempt_id=attempt_id,
                created_at=now,
                updated_at=now,
                source_substrate=normalized_substrate,
                authored_by=normalized_author,
                last_reason=reason,
            )
        else:
            existing.state = state
            existing.lane = lane
            existing.attempt_id = attempt_id
            existing.updated_at = now
            existing.source_substrate = normalized_substrate
            existing.authored_by = normalized_author
            if reason is not None:
                existing.last_reason = reason

    for shard_id in accepted_shard_ids:
        _upsert(shard_id, "validated", None)
    for shard_id in flagged_shard_ids:
        _upsert(shard_id, "validated", "flagged_by_validator")
    for shard_id in rejected_shard_ids:
        _upsert(shard_id, "rejected", reasons.get(shard_id, "validator_rejected"))
    entry.last_touched_at = now


def record_import(
    ledger: dict[str, ParagraphLedgerEntry],
    *,
    paragraph_id: str,
    attempt_id: str,
    imported_shard_ids: Iterable[str],
    lane: Lane = "bridge",
    source_substrate: str | None = None,
    authored_by: str | None = None,
) -> None:
    """Flip accepted shards to 'imported' and close the attempt."""
    entry = _ensure_entry(
        ledger,
        paragraph_id,
        source_substrate=source_substrate or "raw_seed",
        authored_by=authored_by or "operator",
    )
    now = _utc_now()
    imported_list = list(imported_shard_ids)
    normalized_substrate = _normalize_source_substrate(
        source_substrate or entry.source_substrate
    )
    normalized_author = _normalize_authored_by(
        authored_by or entry.authored_by,
        source_substrate=normalized_substrate,
    )
    entry.source_substrate = normalized_substrate
    entry.authored_by = normalized_author
    for shard_id in imported_list:
        existing = entry.shard_entries.get(shard_id)
        if existing is None:
            entry.shard_entries[shard_id] = ShardLedgerEntry(
                shard_id=shard_id,
                paragraph_id=paragraph_id,
                state="imported",
                lane=lane,
                attempt_id=attempt_id,
                created_at=now,
                updated_at=now,
                source_substrate=normalized_substrate,
                authored_by=normalized_author,
            )
        else:
            existing.state = "imported"
            existing.lane = lane
            existing.attempt_id = attempt_id
            existing.updated_at = now
            existing.source_substrate = normalized_substrate
            existing.authored_by = normalized_author
    for attempt in entry.attempts:
        if attempt.attempt_id != attempt_id:
            continue
        attempt.source_substrate = normalized_substrate
        attempt.authored_by = normalized_author
        if attempt.finished_at is None:
            attempt.finished_at = now
            attempt.outcome = "imported" if imported_list else "empty"
            attempt.shard_count = len(imported_list)
            attempt.attempt_status = "imported" if imported_list else "empty"
            break
    entry.last_touched_at = now


def record_rejection(
    ledger: dict[str, ParagraphLedgerEntry],
    *,
    paragraph_id: str,
    attempt_id: str,
    reason: str,
    source_substrate: str | None = None,
    authored_by: str | None = None,
) -> None:
    """Close an attempt as fully rejected (e.g. bundle-level failure)."""
    entry = _ensure_entry(
        ledger,
        paragraph_id,
        source_substrate=source_substrate or "raw_seed",
        authored_by=authored_by or "operator",
    )
    now = _utc_now()
    normalized_substrate = _normalize_source_substrate(
        source_substrate or entry.source_substrate
    )
    normalized_author = _normalize_authored_by(
        authored_by or entry.authored_by,
        source_substrate=normalized_substrate,
    )
    entry.source_substrate = normalized_substrate
    entry.authored_by = normalized_author
    for attempt in entry.attempts:
        if attempt.attempt_id != attempt_id:
            continue
        attempt.source_substrate = normalized_substrate
        attempt.authored_by = normalized_author
        if attempt.finished_at is None:
            attempt.finished_at = now
            attempt.outcome = "rejected"
            attempt.reason = reason
            attempt.attempt_status = "rejected"
            break
    entry.last_touched_at = now


def mark_attempt_status(
    ledger: dict[str, ParagraphLedgerEntry],
    *,
    paragraph_id: str,
    attempt_id: str,
    new_status: str,
    abandoned_reason: Optional[str] = None,
) -> bool:
    """Transition a single attempt's attempt_status. Used by the recovery library
    for stale_in_flight / abandoned_stale_no_import_evidence /
    operator_review_required transitions. Returns True if a transition was made.

    Append-only contract: only the attempt's status fields move; attempts list
    itself is never mutated retroactively for shape.
    """
    entry = ledger.get(paragraph_id)
    if entry is None:
        return False
    att = lookup_attempt(entry, attempt_id)
    if att is None:
        return False
    if new_status not in ATTEMPT_STATUSES:
        raise ValueError(f"invalid attempt_status: {new_status}")
    now = _utc_now()
    att.attempt_status = new_status
    if new_status in {"abandoned_stale_no_import_evidence", "reclaimed_by_new_attempt"}:
        if att.abandoned_at is None:
            att.abandoned_at = now
        if abandoned_reason is not None and att.abandoned_reason is None:
            att.abandoned_reason = abandoned_reason
    entry.last_touched_at = now
    return True


# ---------------------------------------------------------------------------
# Reducer
# ---------------------------------------------------------------------------


def compute_paragraph_state(entry: ParagraphLedgerEntry) -> ParagraphState:
    """Derive the paragraph-level computed state from shard entries and attempts.

    PR 3 additions:
      - any attempt with attempt_status='operator_review_required' surfaces the
        paragraph state as 'operator_review_required' (highest priority after
        actual import outcomes).
      - attempts with attempt_status in {abandoned_stale_no_import_evidence,
        reclaimed_by_new_attempt} are NOT counted as 'open' — paragraphs whose
        only attempts are abandoned/reclaimed (with no shard evidence) are
        reclaimable and reduce to 'untouched'.
    """
    if not entry.attempts and not entry.shard_entries:
        return "untouched"

    # PR 3: operator_review_required wins over the in_flight / untouched fall-throughs
    # but never over imported-with-evidence (we still want fully_imported
    # to show in the happy case). Apply after the imported short-circuit below.
    has_review_required_attempt = any(
        (a.attempt_status == "operator_review_required")
        for a in entry.attempts
    )

    # An attempt is "open" only if it is actively in_flight or stale_in_flight.
    # Abandoned / reclaimed / operator_review attempts are not open work.
    def _is_open(a: DistillationAttempt) -> bool:
        if a.finished_at is not None:
            return False
        status = a.attempt_status
        if status in {
            "abandoned_stale_no_import_evidence",
            "reclaimed_by_new_attempt",
            "operator_review_required",
        }:
            return False
        return True

    shard_states = [shard.state for shard in entry.shard_entries.values()]
    open_attempts = [att for att in entry.attempts if _is_open(att)]

    if not shard_states:
        if open_attempts:
            return "in_flight"
        if has_review_required_attempt:
            return "operator_review_required"
        # All attempts are terminal in some way. Find the most informative.
        last_terminal = None
        for att in entry.attempts:
            if att.attempt_status in {
                "imported", "rejected", "empty", "error",
                "abandoned_stale_no_import_evidence", "reclaimed_by_new_attempt",
            } or att.outcome is not None:
                last_terminal = att
        if last_terminal is None:
            return "untouched"
        if last_terminal.attempt_status in {
            "abandoned_stale_no_import_evidence",
            "reclaimed_by_new_attempt",
        } or last_terminal.outcome is None:
            # Reclaimable: no import evidence, no terminal-with-outcome.
            return "untouched"
        if last_terminal.outcome == "rejected":
            return "fully_rejected"
        if last_terminal.outcome == "imported" and last_terminal.shard_count > 0:
            return "fully_imported"
        if last_terminal.outcome in {"empty", "error"}:
            return "fully_rejected"
        return "untouched"

    imported = [state for state in shard_states if state == "imported"]
    rejected = [state for state in shard_states if state == "rejected"]
    superseded = [state for state in shard_states if state == "superseded"]
    if superseded and not imported:
        return "superseded"
    if imported and rejected:
        return "partially_imported"
    if imported:
        return "fully_imported"
    if rejected and not imported:
        return "fully_rejected"
    if open_attempts:
        return "in_flight"
    if has_review_required_attempt:
        return "operator_review_required"
    return "in_flight"


def paragraph_state_counts(
    ledger: Mapping[str, ParagraphLedgerEntry],
    *,
    known_paragraph_ids: Iterable[str] | None = None,
) -> dict[str, int]:
    """Count paragraphs per computed state.

    If ``known_paragraph_ids`` is provided, paragraphs in that set with no
    ledger entry are counted as ``untouched``.
    """
    counts: dict[str, int] = {state: 0 for state in PARAGRAPH_STATES}
    ledger_ids = set(ledger.keys())
    all_ids: set[str] = set(ledger_ids)
    if known_paragraph_ids is not None:
        all_ids.update(known_paragraph_ids)
    for par_id in all_ids:
        entry = ledger.get(par_id)
        if entry is None:
            counts["untouched"] += 1
            continue
        state = compute_paragraph_state(entry)
        counts[state] = counts.get(state, 0) + 1
    return counts


__all__ = [
    "ShardLedgerEntry",
    "DistillationAttempt",
    "ParagraphLedgerEntry",
    "PARAGRAPH_STATES",
    "ATTEMPT_STATUSES",
    "DEFAULT_LEASE_SECONDS",
    "LEDGER_FILENAME",
    "LEDGER_SCHEMA",
    "next_claim_epoch_for_paragraph",
    "derive_attempt_status",
    "lookup_attempt",
    "mark_attempt_status",
    "paragraph_ledger_path_for_family",
    "load_ledger",
    "save_ledger",
    "record_dispatch",
    "record_validator_result",
    "record_import",
    "record_rejection",
    "compute_paragraph_state",
    "paragraph_state_counts",
]
