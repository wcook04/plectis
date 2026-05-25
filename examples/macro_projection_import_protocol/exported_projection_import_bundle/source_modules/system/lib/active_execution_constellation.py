"""Read-only projection of live work over static phase anchors.

The Active Execution Constellation is an entry/pulse view, not authority.
It composes declared phase state, orchestration state, Task Ledger priority,
and Work Ledger claims so cold agents do not mistake an old phase folder for
the sole live execution truth.
"""
from __future__ import annotations

import json
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib import work_ledger_runtime
from system.lib.work_ledger_commands import (
    WORK_LEDGER_CLAIM_CARDS_REFRESH_COMMAND,
    WORK_LEDGER_FULL_CLAIMS_CARDS_COMMAND,
    WORK_LEDGER_REFRESH_CLAIMS_COMMAND,
    WORK_LEDGER_SEED_SPEED_COMMAND,
    WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
)
from system.lib.phase_activation import load_explicit_active_phase

SCHEMA_VERSION = "active_execution_constellation_v0"
FRESHNESS_STALE_AFTER_SECONDS = 15 * 60
ORCHESTRATION_STATE_PATH = Path("tools/meta/control/orchestration_state.json")
SCHEDULABLE_VIEW_PATH = Path("state/task_ledger/views/execution_menu_schedulable.json")
ACTIVE_CLAIMS_SNAPSHOT_PATH = Path("state/work_ledger/active_claims_snapshot.json")
WORK_LEDGER_RUNTIME_STATUS_PATH = Path("state/work_ledger/runtime_status.json")
ENTRY_PRIORITY_ROW_LIMIT = 1
CLAIM_TOPOLOGY_BUCKETS = (
    "true_09_54_dissemination",
    "campaign_claim_misanchored_to_09_54",
    "supervised_scope_candidate",
    "stale_orphan_claim",
    "route_infrastructure_or_aec_cleanup",
    "unknown",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _timestamp_from_path(path: Path) -> str | None:
    try:
        return (
            datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except OSError:
        return None


def _source_freshness(
    repo_root: Path,
    rel_path: Path,
    payload: Mapping[str, Any],
    *,
    refresh_command: str | None = None,
    check_command: str | None = None,
) -> dict[str, Any]:
    path = repo_root / rel_path
    generated_at = payload.get("generated_at") or payload.get("updated_at")
    timestamp_source = "payload.generated_at_or_updated_at"
    if not generated_at:
        generated_at = _timestamp_from_path(path)
        timestamp_source = "filesystem_mtime" if generated_at else "missing"
    parsed = _parse_timestamp(generated_at)
    age_seconds = None
    status = "unknown"
    if not path.exists():
        status = "unavailable"
    elif parsed is not None:
        age_seconds = max(0, int((datetime.now(timezone.utc) - parsed).total_seconds()))
        status = "stale" if age_seconds > FRESHNESS_STALE_AFTER_SECONDS else "fresh"

    row = {
        "path": rel_path.as_posix(),
        "status": status,
        "generated_at": generated_at,
        "timestamp_source": timestamp_source,
        "age_seconds": age_seconds,
        "stale_after_seconds": FRESHNESS_STALE_AFTER_SECONDS,
    }
    if refresh_command:
        row["refresh_command"] = refresh_command
    if check_command:
        row["check_command"] = check_command
    return row


def _projection_freshness(
    repo_root: Path,
    *,
    orchestration_path: Path,
    orchestration: Mapping[str, Any],
    schedulable_view: Mapping[str, Any],
    active_claims_snapshot: Mapping[str, Any],
    work_ledger_runtime_status: Mapping[str, Any],
) -> dict[str, Any]:
    sources = {
        "orchestration_state": _source_freshness(
            repo_root,
            orchestration_path.relative_to(repo_root)
            if orchestration_path.is_absolute()
            else orchestration_path,
            orchestration,
            refresh_command="./repo-python kernel.py --pulse",
        ),
        "task_ledger_schedulable_view": _source_freshness(
            repo_root,
            SCHEDULABLE_VIEW_PATH,
            schedulable_view,
            refresh_command="./repo-python tools/meta/factory/task_ledger_apply.py rebuild",
            check_command="./repo-python tools/meta/factory/task_ledger_apply.py validate",
        ),
        "work_ledger_claim_snapshot": _source_freshness(
            repo_root,
            ACTIVE_CLAIMS_SNAPSHOT_PATH,
            active_claims_snapshot,
            refresh_command=WORK_LEDGER_REFRESH_CLAIMS_COMMAND,
        ),
        "work_ledger_runtime_status": _source_freshness(
            repo_root,
            WORK_LEDGER_RUNTIME_STATUS_PATH,
            work_ledger_runtime_status,
            refresh_command=WORK_LEDGER_SEED_SPEED_COMMAND,
        ),
    }
    required_statuses = {
        str(row.get("status") or "unknown")
        for key, row in sources.items()
        if key != "work_ledger_runtime_status"
    }
    statuses = {str(row.get("status") or "unknown") for row in sources.values()}
    if "unavailable" in required_statuses:
        status = "unavailable"
    elif "stale" in statuses:
        status = "stale"
    elif "unknown" in statuses:
        status = "unknown"
    else:
        status = "fresh"
    return {
        "status": status,
        "generated_at": _utc_now(),
        "stale_after_seconds": FRESHNESS_STALE_AFTER_SECONDS,
        "sources": sources,
    }


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _snippet(value: Any, limit: int = 96) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _phase_id(active_phase: Mapping[str, Any]) -> str:
    return str(
        active_phase.get("active_phase_id")
        or active_phase.get("phase_id")
        or active_phase.get("id")
        or ""
    ).strip()


def _phase_title(active_phase: Mapping[str, Any]) -> str:
    return str(
        active_phase.get("active_phase_title")
        or active_phase.get("phase_title")
        or active_phase.get("title")
        or ""
    ).strip()


def _phase_dir(active_phase: Mapping[str, Any]) -> str:
    return str(
        active_phase.get("active_phase_dir")
        or active_phase.get("phase_dir")
        or active_phase.get("dir")
        or ""
    ).strip()


def _runtime_state(orchestration: Mapping[str, Any]) -> tuple[str, str, str]:
    state = str(
        orchestration.get("active_driver")
        or orchestration.get("state")
        or orchestration.get("active_runtime")
        or ""
    ).strip()
    gate = orchestration.get("gate") if isinstance(orchestration.get("gate"), Mapping) else {}
    gate_reason = str(gate.get("gate_reason") or orchestration.get("gate_reason") or "").strip()
    updated_at = str(orchestration.get("updated_at") or orchestration.get("generated_at") or "").strip()
    return state, gate_reason, updated_at


def _declared_anchor(active_phase: Mapping[str, Any], orchestration: Mapping[str, Any]) -> dict[str, Any]:
    phase_id = _phase_id(active_phase)
    runtime_state, gate_reason, updated_at = _runtime_state(orchestration)
    runtime_dormant = "no_active_runtime_phase" in {runtime_state, gate_reason}

    if not phase_id:
        status = "no_declared_anchor"
        reason = "No explicit active phase anchor is available."
        recommendation = "Use Task Ledger and Work Ledger surfaces until a phase anchor is declared."
    elif runtime_dormant:
        status = "declared_anchor_runtime_dormant"
        reason = (
            f"{phase_id} is the declared phase anchor, but orchestration reports "
            "no_active_runtime_phase."
        )
        recommendation = (
            "Treat the phase as historical/contextual unless Work Ledger claims or "
            "Task Ledger evidence make it live for the current task."
        )
    else:
        status = "declared_anchor_runtime_live_or_unknown"
        reason = (
            f"{phase_id} is the declared phase anchor; runtime state is "
            f"{runtime_state or 'unknown'}."
        )
        recommendation = (
            "Use the declared anchor as context and still verify live work through "
            "Task Ledger and Work Ledger."
        )

    return {
        "phase_id": phase_id,
        "phase_title": _phase_title(active_phase),
        "phase_dir": _phase_dir(active_phase),
        "runtime_state": runtime_state or "unknown",
        "runtime_gate_reason": gate_reason or "unknown",
        "runtime_updated_at": updated_at,
        "status": status,
        "stale_or_live_reason": reason,
        "demotion_recommendation": recommendation,
    }


def _summarize_workitem(item: Mapping[str, Any], *, source_view: str) -> dict[str, Any]:
    workitem_id = str(item.get("id") or "").strip()
    preflight_route = (
        f"./repo-python tools/meta/control/mission_transaction_preflight.py "
        f"--subject-id {workitem_id} --control-summary"
        if workitem_id.startswith(("cap_", "td_"))
        else None
    )
    return {
        "workitem_id": workitem_id,
        "type": str(item.get("work_item_type") or item.get("candidate_work_item_type") or "unknown"),
        "rank": item.get("rank"),
        "state": str(item.get("state") or "unknown"),
        "title": str(item.get("title") or "").strip(),
        "drilldown_command": item.get("drilldown_command")
        or f"./repo-python kernel.py --option-surface task_ledger --band card --ids {workitem_id}",
        "preflight_route": preflight_route,
        "source_view": source_view,
    }


def _live_campaigns(
    repo_root: Path,
    *,
    schedulable_view: Mapping[str, Any] | None = None,
    top_schedulable_workitem: Mapping[str, Any] | None,
    top_ready_workitem: Mapping[str, Any] | None,
    limit: int,
) -> list[dict[str, Any]]:
    view = schedulable_view or _read_json(repo_root / SCHEDULABLE_VIEW_PATH)
    candidates: list[tuple[Mapping[str, Any], str]] = []
    if isinstance(top_schedulable_workitem, Mapping) and top_schedulable_workitem.get("id"):
        candidates.append((top_schedulable_workitem, "kernel.entry.top_schedulable_workitem"))
    if isinstance(top_ready_workitem, Mapping) and top_ready_workitem.get("id"):
        candidates.append((top_ready_workitem, "kernel.entry.top_ready_workitem"))
    for item in view.get("items") or []:
        if isinstance(item, Mapping):
            candidates.append((item, SCHEDULABLE_VIEW_PATH.as_posix()))

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item, source_view in candidates:
        workitem_id = str(item.get("id") or "").strip()
        if not workitem_id or workitem_id in seen:
            continue
        seen.add(workitem_id)
        rows.append(_summarize_workitem(item, source_view=source_view))
        if len(rows) >= limit:
            break
    return rows


def _compact_claim(claim: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": str(claim.get("claim_id") or "").strip(),
        "scope_kind": str(claim.get("scope_kind") or "").strip(),
        "scope_id": str(claim.get("scope_id") or "").strip(),
        "path": str(claim.get("path") or "").strip(),
        "work_item_id": str(claim.get("work_item_id") or "").strip(),
        "td_id": str(claim.get("td_id") or "").strip(),
        "session_id": str(claim.get("session_id") or "").strip(),
        "actor": str(claim.get("actor") or "").strip(),
        "phase_id": str(claim.get("phase_id") or "").strip(),
        "claimed_at": str(claim.get("claimed_at") or "").strip(),
        "leased_until": str(claim.get("leased_until") or "").strip(),
        "note": str(claim.get("note") or "").strip(),
    }


def _session_drilldown_command(session_id: str) -> str:
    return (
        "./repo-python tools/meta/factory/work_ledger.py "
        f"session-status --session-id {shlex.quote(session_id)} --full"
    )


def _session_rows(claims: list[Mapping[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for claim in claims:
        session_id = str(claim.get("session_id") or "unknown_session").strip() or "unknown_session"
        row = grouped.setdefault(
            session_id,
            {
                "session_id": session_id,
                "actor": str(claim.get("actor") or "").strip(),
                "phase_id": str(claim.get("phase_id") or "").strip(),
                "claim_count": 0,
                "scope_kinds": set(),
                "paths": [],
                "work_item_ids": set(),
                "td_ids": set(),
                "leased_until": "",
            },
        )
        row["claim_count"] += 1
        if claim.get("scope_kind"):
            row["scope_kinds"].add(str(claim.get("scope_kind")))
        path = str(claim.get("path") or "").strip()
        if path and path not in row["paths"]:
            row["paths"].append(path)
        work_item_id = str(claim.get("work_item_id") or "").strip()
        if work_item_id:
            row["work_item_ids"].add(work_item_id)
        td_id = str(claim.get("td_id") or "").strip()
        if td_id:
            row["td_ids"].add(td_id)
        leased_until = str(claim.get("leased_until") or "").strip()
        if leased_until and leased_until > str(row.get("leased_until") or ""):
            row["leased_until"] = leased_until

    rows: list[dict[str, Any]] = []
    for row in sorted(grouped.values(), key=lambda item: (-int(item["claim_count"]), item["session_id"])):
        rows.append(
            {
                "session_id": row["session_id"],
                "actor": row["actor"],
                "phase_id": row["phase_id"],
                "claim_count": row["claim_count"],
                "scope_kinds": sorted(row["scope_kinds"]),
                "path_count": len(row["paths"]),
                "paths": row["paths"][:5],
                "work_item_ids": sorted(row["work_item_ids"]),
                "td_ids": sorted(row["td_ids"]),
                "leased_until": row["leased_until"],
                "drilldown": _session_drilldown_command(str(row["session_id"])),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _compact_awareness_card(card: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "session_id": str(card.get("session_id") or "").strip(),
        "actor": str(card.get("actor") or "").strip(),
        "phase_id": str(card.get("phase_id") or "").strip(),
        "freshness_state": str(card.get("freshness_state") or "").strip() or "unknown",
        "idle_seconds": card.get("idle_seconds"),
        "orphaned_active": bool(card.get("orphaned_active")),
        "pass_id": card.get("pass_id"),
        "pass_seq": card.get("pass_seq"),
        "pass_state": card.get("pass_state"),
        "current_pass_line": card.get("current_pass_line"),
        "last_pass_result_line": card.get("last_pass_result_line"),
        "source": card.get("source") or "projected_unknown",
        "updated_at": card.get("updated_at"),
        "scope_refs": list(card.get("scope_refs") or [])[:4],
        "claim_refs": list(card.get("claim_refs") or [])[:4],
        "touched_td_ids": list(card.get("touched_td_ids") or [])[:4],
        "touched_work_item_ids": list(card.get("touched_work_item_ids") or [])[:4],
    }


def _awareness_card_sort_key(card: Mapping[str, Any]) -> tuple[Any, ...]:
    freshness_rank = {
        "live": 0,
        "idle": 1,
        "unknown": 2,
        "stale": 3,
        "expired": 4,
        "orphaned": 5,
        "ended": 6,
    }
    source = str(card.get("source") or "").strip()
    freshness = str(card.get("freshness_state") or "").strip()
    has_public_line = bool(str(card.get("current_pass_line") or "").strip())
    updated = _parse_timestamp(card.get("updated_at"))
    updated_rank = -updated.timestamp() if updated is not None else 0
    return (
        0 if has_public_line and source != "projected_unknown" else 1,
        freshness_rank.get(freshness, 7),
        1 if card.get("orphaned_active") else 0,
        updated_rank,
        str(card.get("session_id") or ""),
    )


def _awareness_rows(
    cohort_overview: Mapping[str, Any],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    raw_cards = (
        cohort_overview.get("awareness_cards")
        if isinstance(cohort_overview.get("awareness_cards"), list)
        else []
    )
    cards = [
        _compact_awareness_card(card)
        for card in raw_cards
        if isinstance(card, Mapping)
    ]
    return sorted(cards, key=_awareness_card_sort_key)[: max(0, int(limit or 0))]


def _session_scope_ref(session: Mapping[str, Any]) -> str:
    for key in ("paths", "work_item_ids", "td_ids"):
        rows = session.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            text = str(row or "").strip()
            if text:
                return text
    return "<path-or-claim>"


def _heartbeat_gap_command(session_id: str, scope_ref: str) -> str:
    return (
        "./repo-python tools/meta/factory/work_ledger.py "
        f"session-heartbeat --session-id {shlex.quote(session_id)} --state <state> "
        "--now '<public current pass>' --done '<public previous result>' "
        f"--scope-ref {shlex.quote(scope_ref)}"
    )


def _heartbeat_gap_rows(
    sessions: list[Mapping[str, Any]],
    awareness_cards: list[Mapping[str, Any]],
    *,
    explicit_session_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    explicit_session_ids = explicit_session_ids or set()
    awareness_by_session = {
        str(card.get("session_id") or "").strip(): card
        for card in awareness_cards
        if isinstance(card, Mapping) and str(card.get("session_id") or "").strip()
    }
    rows: list[dict[str, Any]] = []
    for session in sessions:
        session_id = str(session.get("session_id") or "").strip()
        if not session_id:
            continue
        if session_id in explicit_session_ids:
            continue
        awareness = awareness_by_session.get(session_id) or {}
        heartbeat_source = str(awareness.get("source") or "projected_unknown").strip() or "projected_unknown"
        if heartbeat_source in work_ledger_runtime.EXPLICIT_HEARTBEAT_SOURCES:
            continue
        scope_ref = _session_scope_ref(session)
        rows.append(
            {
                "session_id": session_id,
                "actor": session.get("actor"),
                "phase_id": session.get("phase_id"),
                "active_claim_count": session.get("claim_count"),
                "heartbeat_source": heartbeat_source,
                "freshness_state": awareness.get("freshness_state") or "unknown",
                "scope_ref": scope_ref,
                "heartbeat_command": _heartbeat_gap_command(session_id, scope_ref),
            }
        )
    return rows


def _claim_text(claim: Mapping[str, Any]) -> str:
    fields = (
        claim.get("claim_id"),
        claim.get("scope_kind"),
        claim.get("scope_id"),
        claim.get("path"),
        claim.get("work_item_id"),
        claim.get("td_id"),
        claim.get("session_id"),
        claim.get("note"),
    )
    return " ".join(str(value or "").casefold().replace("-", "_") for value in fields)


def _claim_ref(claim: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": str(claim.get("claim_id") or "").strip(),
        "scope_kind": str(claim.get("scope_kind") or "").strip(),
        "scope_id": str(claim.get("scope_id") or "").strip(),
        "path": str(claim.get("path") or "").strip(),
        "work_item_id": str(claim.get("work_item_id") or "").strip(),
        "td_id": str(claim.get("td_id") or "").strip(),
        "session_id": str(claim.get("session_id") or "").strip(),
        "leased_until": str(claim.get("leased_until") or "").strip(),
    }


def _empty_claim_bucket(bucket_id: str) -> dict[str, Any]:
    descriptions = {
        "true_09_54_dissemination": "Claims still attached to the public/dissemination launch mission.",
        "campaign_claim_misanchored_to_09_54": "Claims whose work appears live but not intrinsically owned by the 09_54 dissemination phase anchor.",
        "supervised_scope_candidate": "Non-exclusive multi-claim/session supervision candidates; verify finalizers before inventing phase hierarchy.",
        "stale_orphan_claim": "Expired, released, or sessionless claims that should drain through Work Ledger cleanup.",
        "route_infrastructure_or_aec_cleanup": "AEC/bootstrap/control-plane cleanup claims that should not keep 09_54 alive after closeout.",
        "unknown": "Claims whose owner lane cannot be inferred from the current snapshot.",
    }
    recommended_lanes = {
        "true_09_54_dissemination": "Keep 09_54 demotion blocked; attach or finish under the dissemination WorkItem/meta_mission.",
        "campaign_claim_misanchored_to_09_54": "Rehome through Task Ledger/Work Ledger owner lanes, or capture a cleanup residual if no rehome actuator exists.",
        "supervised_scope_candidate": "Use or build the narrow Work Ledger supervised-scope lane only after shared finalizers/residue are verified.",
        "stale_orphan_claim": "Drain through Work Ledger stale/orphan cleanup before rerunning the demotion guard.",
        "route_infrastructure_or_aec_cleanup": "Finalize route-infrastructure sessions; do not preserve 09_54 solely for projection cleanup.",
        "unknown": "Keep demotion blocked and request the smallest missing owner/finalizer evidence slice.",
    }
    return {
        "bucket_id": bucket_id,
        "description": descriptions[bucket_id],
        "claim_count": 0,
        "session_count": 0,
        "sessions": set(),
        "work_item_ids": set(),
        "td_ids": set(),
        "path_samples": [],
        "claim_refs": [],
        "recommended_lane": recommended_lanes[bucket_id],
        "exclusive": bucket_id != "supervised_scope_candidate",
    }


def _claim_primary_bucket(claim: Mapping[str, Any], *, now: datetime) -> str:
    text = _claim_text(claim)
    leased_until = _parse_timestamp(claim.get("leased_until"))
    if claim.get("released_at") or claim.get("expired_at") or not claim.get("session_id"):
        return "stale_orphan_claim"
    if leased_until is not None and leased_until < now:
        return "stale_orphan_claim"
    if any(
        token in text
        for token in (
            "active_execution_constellation",
            "agent_bootstrap",
            "bootstrap_projection",
            "orchestration_runtime_projection",
        )
    ):
        return "route_infrastructure_or_aec_cleanup"
    if any(
        token in text
        for token in (
            "dissemination",
            "public_microcosm",
            "public_launch",
            "monday_rollout",
            "proof_bundle",
            "public_safe",
        )
    ):
        return "true_09_54_dissemination"
    if claim.get("work_item_id") or claim.get("path") or claim.get("td_id"):
        return "campaign_claim_misanchored_to_09_54"
    return "unknown"


def _add_claim_to_bucket(bucket: dict[str, Any], claim: Mapping[str, Any]) -> None:
    bucket["claim_count"] += 1
    session_id = str(claim.get("session_id") or "").strip()
    if session_id:
        bucket["sessions"].add(session_id)
    work_item_id = str(claim.get("work_item_id") or "").strip()
    if work_item_id:
        bucket["work_item_ids"].add(work_item_id)
    td_id = str(claim.get("td_id") or "").strip()
    if td_id:
        bucket["td_ids"].add(td_id)
    path = str(claim.get("path") or "").strip()
    if path and path not in bucket["path_samples"] and len(bucket["path_samples"]) < 8:
        bucket["path_samples"].append(path)
    if len(bucket["claim_refs"]) < 8:
        bucket["claim_refs"].append(_claim_ref(claim))


def _finalize_claim_bucket(bucket: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bucket_id": bucket["bucket_id"],
        "description": bucket["description"],
        "claim_count": bucket["claim_count"],
        "session_count": len(bucket["sessions"]),
        "sessions": sorted(bucket["sessions"])[:8],
        "work_item_ids": sorted(bucket["work_item_ids"])[:8],
        "td_ids": sorted(bucket["td_ids"])[:8],
        "path_samples": list(bucket["path_samples"])[:8],
        "claim_refs": list(bucket["claim_refs"])[:8],
        "recommended_lane": bucket["recommended_lane"],
        "exclusive": bucket["exclusive"],
    }


def _phase_claim_topology(
    claims: list[Mapping[str, Any]],
    supervised_scope_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    buckets = {bucket_id: _empty_claim_bucket(bucket_id) for bucket_id in CLAIM_TOPOLOGY_BUCKETS}
    now = datetime.now(timezone.utc)
    phase_ids: set[str] = set()
    session_ids: set[str] = set()
    for claim in claims:
        phase_id = str(claim.get("phase_id") or "").strip()
        if phase_id:
            phase_ids.add(phase_id)
        session_id = str(claim.get("session_id") or "").strip()
        if session_id:
            session_ids.add(session_id)
        bucket_id = _claim_primary_bucket(claim, now=now)
        _add_claim_to_bucket(buckets[bucket_id], claim)

    candidate_session_ids: set[str] = set()
    for candidate in supervised_scope_candidates:
        for session_id in candidate.get("child_session_ids") or []:
            if isinstance(session_id, str) and session_id:
                candidate_session_ids.add(session_id)
    if candidate_session_ids:
        for claim in claims:
            if str(claim.get("session_id") or "").strip() in candidate_session_ids:
                _add_claim_to_bucket(buckets["supervised_scope_candidate"], claim)

    bucket_rows = [_finalize_claim_bucket(buckets[bucket_id]) for bucket_id in CLAIM_TOPOLOGY_BUCKETS]
    return {
        "schema_version": "phase_claim_topology_v0",
        "authority_posture": "projection_not_source_authority",
        "source_path": ACTIVE_CLAIMS_SNAPSHOT_PATH.as_posix(),
        "phase_ids": sorted(phase_ids),
        "claim_count": len(claims),
        "session_count": len(session_ids),
        "bucket_counts": {
            row["bucket_id"]: row["claim_count"]
            for row in bucket_rows
        },
        "buckets": bucket_rows,
        "drilldown_commands": {
            "claims_full": "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 50 --full",
            "phase_full": "./repo-python kernel.py --phase 09_54 --full",
            "task_ledger": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
        },
    }


def _live_sessions(
    repo_root: Path,
    *,
    active_claims_snapshot: Mapping[str, Any] | None = None,
    work_ledger_runtime_status: Mapping[str, Any] | None = None,
    include_runtime_status: bool = True,
    claim_limit: int,
    session_limit: int,
) -> dict[str, Any]:
    snapshot_path = repo_root / ACTIVE_CLAIMS_SNAPSHOT_PATH
    snapshot = active_claims_snapshot or _read_json(snapshot_path)
    raw_claims = snapshot.get("active_claims") if isinstance(snapshot.get("active_claims"), list) else []
    claims = [claim for claim in raw_claims if isinstance(claim, Mapping)]
    counts = snapshot.get("counts") if isinstance(snapshot.get("counts"), Mapping) else {}
    runtime_status_loaded = False
    if work_ledger_runtime_status is None and include_runtime_status:
        try:
            work_ledger_runtime_status = work_ledger_runtime.load_runtime_status(repo_root)
            runtime_status_loaded = True
        except Exception:
            work_ledger_runtime_status = {}
    elif work_ledger_runtime_status is not None and include_runtime_status:
        runtime_status_loaded = True
    elif work_ledger_runtime_status is None:
        work_ledger_runtime_status = {}
    runtime_counts = (
        work_ledger_runtime_status.get("counts")
        if isinstance(work_ledger_runtime_status.get("counts"), Mapping)
        else {}
    )
    cohort_overview = (
        work_ledger_runtime_status.get("cohort_overview")
        if isinstance(work_ledger_runtime_status.get("cohort_overview"), Mapping)
        else {}
    )
    if not cohort_overview and work_ledger_runtime_status and include_runtime_status:
        try:
            cohort_overview = work_ledger_runtime.build_session_cohort_overview(
                work_ledger_runtime_status,
                limit=session_limit,
            )
        except Exception:
            cohort_overview = {}
    cohort_counts = (
        cohort_overview.get("counts")
        if isinstance(cohort_overview.get("counts"), Mapping)
        else {}
    )
    seed_speed_hint = (
        snapshot.get("seed_speed_hint")
        if isinstance(snapshot.get("seed_speed_hint"), Mapping)
        else {}
    )
    seed_speed_counts = (
        seed_speed_hint.get("counts")
        if isinstance(seed_speed_hint.get("counts"), Mapping)
        else {}
    )
    cached_heartbeat_gap_rows = (
        seed_speed_hint.get("heartbeat_gap_claim_sessions")
        if isinstance(seed_speed_hint.get("heartbeat_gap_claim_sessions"), list)
        else []
    )
    source_freshness = _source_freshness(
        repo_root,
        ACTIVE_CLAIMS_SNAPSHOT_PATH,
        snapshot,
        refresh_command=WORK_LEDGER_REFRESH_CLAIMS_COMMAND,
    )
    runtime_source_freshness = _source_freshness(
        repo_root,
        WORK_LEDGER_RUNTIME_STATUS_PATH,
        work_ledger_runtime_status,
        refresh_command=WORK_LEDGER_SEED_SPEED_COMMAND,
    )
    phase_claim_counts: dict[str, int] = {}
    phase_session_ids: dict[str, set[str]] = {}
    for claim in claims:
        phase_id = str(claim.get("phase_id") or "").strip()
        if not phase_id:
            continue
        phase_claim_counts[phase_id] = phase_claim_counts.get(phase_id, 0) + 1
        session_id = str(claim.get("session_id") or "").strip()
        if session_id:
            phase_session_ids.setdefault(phase_id, set()).add(session_id)
    sessions = _session_rows(claims, limit=session_limit)
    topology_sessions = _session_rows(claims, limit=max(len(claims), session_limit))
    awareness_cards = _awareness_rows(cohort_overview, limit=session_limit)
    topology_awareness_cards = _awareness_rows(cohort_overview, limit=max(len(claims), session_limit))
    heartbeat_participation = (
        cohort_overview.get("heartbeat_participation")
        if isinstance(cohort_overview.get("heartbeat_participation"), Mapping)
        else {}
    )
    explicit_session_ids = {
        str(session_id or "").strip()
        for session_id in heartbeat_participation.get("explicit_session_ids") or []
        if str(session_id or "").strip()
    }
    if include_runtime_status and cohort_overview:
        heartbeat_gap_status = "available"
        heartbeat_gap_claim_sessions = _heartbeat_gap_rows(
            topology_sessions,
            topology_awareness_cards,
            explicit_session_ids=explicit_session_ids,
        )
    elif seed_speed_hint:
        heartbeat_gap_status = "cached_snapshot"
        heartbeat_gap_claim_sessions = [
            dict(row)
            for row in cached_heartbeat_gap_rows
            if isinstance(row, Mapping)
        ]
    else:
        heartbeat_gap_status = "deferred_by_fast_path"
        heartbeat_gap_claim_sessions = []
    supervised_candidates = _supervised_scope_candidates({"sessions": topology_sessions})
    if heartbeat_gap_status in {"available", "cached_snapshot"}:
        heartbeat_gap_count: int | None = len(heartbeat_gap_claim_sessions)
    elif seed_speed_counts.get("claim_session_heartbeat_gap_count") is not None:
        heartbeat_gap_count = int(seed_speed_counts.get("claim_session_heartbeat_gap_count") or 0)
    else:
        heartbeat_gap_count = None
    return {
        "source_path": ACTIVE_CLAIMS_SNAPSHOT_PATH.as_posix(),
        "source_freshness": {
            "status": "cached_snapshot"
            if source_freshness.get("status") in {"fresh", "stale", "unknown"}
            else source_freshness.get("status"),
            "freshness_status": source_freshness.get("status"),
            "generated_at": source_freshness.get("generated_at"),
            "age_seconds": source_freshness.get("age_seconds"),
            "stale_after_seconds": source_freshness.get("stale_after_seconds"),
            "refresh_command": WORK_LEDGER_REFRESH_CLAIMS_COMMAND,
        },
        "runtime_source_freshness": {
            "status": (
                "runtime_status"
                if runtime_status_loaded
                and runtime_source_freshness.get("status") in {"fresh", "stale", "unknown"}
                else "deferred_by_fast_path"
                if not include_runtime_status
                else runtime_source_freshness.get("status")
            ),
            "freshness_status": (
                runtime_source_freshness.get("status")
                if runtime_status_loaded
                else "not_checked"
            ),
            "generated_at": runtime_source_freshness.get("generated_at"),
            "age_seconds": runtime_source_freshness.get("age_seconds"),
            "stale_after_seconds": runtime_source_freshness.get("stale_after_seconds"),
            "refresh_command": WORK_LEDGER_SEED_SPEED_COMMAND,
        },
        "counts": {
            "active_claims": cohort_counts.get("active_claims", counts.get("active_claims", len(claims))),
            "effective_active_sessions": cohort_counts.get(
                "effective_active_sessions",
                counts.get("effective_active_sessions", runtime_counts.get("effective_active_sessions")),
            ),
            "orphaned_active_sessions": cohort_counts.get(
                "orphaned_active_sessions",
                counts.get("orphaned_active_sessions", runtime_counts.get("orphaned_active_sessions")),
            ),
            "claim_collisions": cohort_counts.get("claim_collisions", counts.get("claim_collisions", 0)),
            "claim_session_heartbeat_gap_count": heartbeat_gap_count,
        },
        "heartbeat_gap_status": heartbeat_gap_status,
        "first_action": seed_speed_hint.get("first_action"),
        "first_action_kind": seed_speed_hint.get("first_action_kind"),
        "first_action_command": seed_speed_hint.get("first_action_command"),
        "first_action_ref": seed_speed_hint.get("first_action_ref"),
        "awareness_cards": awareness_cards,
        "heartbeat_gap_claim_sessions": heartbeat_gap_claim_sessions[:session_limit],
        "heartbeat_gap_claim_sessions_omitted": max(
            0,
            len(heartbeat_gap_claim_sessions) - session_limit,
        ),
        "phase_claim_counts": dict(sorted(phase_claim_counts.items())),
        "phase_session_counts": {
            phase_id: len(session_ids)
            for phase_id, session_ids in sorted(phase_session_ids.items())
        },
        "sessions": sessions,
        "active_claims": [_compact_claim(claim) for claim in claims[:claim_limit]],
        "claim_topology": _phase_claim_topology(claims, supervised_candidates),
        "claim_collision_count": counts.get("claim_collisions", 0),
        "drilldown_commands": {
            "cards": WORK_LEDGER_SEED_SPEED_COMMAND,
            "seed_speed": WORK_LEDGER_SEED_SPEED_COMMAND,
            "claims": WORK_LEDGER_CLAIM_CARDS_REFRESH_COMMAND,
            "full": WORK_LEDGER_FULL_CLAIMS_CARDS_COMMAND,
            "overview": WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
            "awareness": WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
        },
    }


def _supervised_scope_candidates(live_sessions: Mapping[str, Any]) -> list[dict[str, Any]]:
    sessions = live_sessions.get("sessions") if isinstance(live_sessions.get("sessions"), list) else []
    candidate_sessions = [
        session
        for session in sessions
        if isinstance(session, Mapping) and int(session.get("claim_count") or 0) > 1
    ]
    if len(candidate_sessions) < 2:
        return []

    phase_ids = sorted(
        {
            str(session.get("phase_id") or "").strip()
            for session in candidate_sessions
            if str(session.get("phase_id") or "").strip()
        }
    )
    paths: list[str] = []
    work_item_ids: set[str] = set()
    for session in candidate_sessions:
        for path in session.get("paths") or []:
            if isinstance(path, str) and path and path not in paths:
                paths.append(path)
        for work_item_id in session.get("work_item_ids") or []:
            if isinstance(work_item_id, str) and work_item_id:
                work_item_ids.add(work_item_id)

    return [
        {
            "candidate_id": "work_ledger_multi_session_supervision_candidate",
            "why_candidate": (
                "Multiple active Work Ledger sessions each hold more than one claim; "
                "this may need shared finalizers or residue drainage, but it is not "
                "itself a reason to create a new phase."
            ),
            "child_session_ids": [str(session.get("session_id") or "") for session in candidate_sessions],
            "shared_phase_ids": phase_ids,
            "shared_paths": paths[:12],
            "work_item_ids": sorted(work_item_ids),
            "missing_fields": [
                "explicit_parent_scope_id",
                "claim_policy",
                "finalizer_policy",
                "residue_budget",
            ],
            "recommended_owner": "Work Ledger supervised-scope lane under pri_147",
            "requires_child_phase": False,
            "relation": "candidate_supervised_scope_not_phase_creation",
        }
    ]


def _stale_decorative_pointers(declared_anchor: Mapping[str, Any]) -> list[dict[str, Any]]:
    if declared_anchor.get("status") != "declared_anchor_runtime_dormant":
        return []
    return [
        {
            "pointer": "active_phase",
            "reason": "declared_active_phase_but_runtime_driver_no_active_runtime_phase",
            "declared_phase_id": declared_anchor.get("phase_id"),
            "replacement_surface": "active_execution_constellation.live_campaigns+live_sessions",
            "safe_action": (
                "Use the phase as context, not as sole liveness authority; route work "
                "through Task Ledger WorkItems and Work Ledger claims."
            ),
        }
    ]


def _demotion_guard(
    declared_anchor: Mapping[str, Any],
    live_sessions: Mapping[str, Any],
    supervised_scope_candidates: list[dict[str, Any]],
    projection_freshness: Mapping[str, Any],
) -> dict[str, Any]:
    phase_id = str(declared_anchor.get("phase_id") or "").strip()
    blockers: list[dict[str, Any]] = []
    evidence_refs = [
        ACTIVE_CLAIMS_SNAPSHOT_PATH.as_posix(),
        "kernel.py --phase 09_54 --full",
        "kernel.py --option-surface task_ledger --band cluster_flag",
    ]
    source_freshness = (
        live_sessions.get("source_freshness")
        if isinstance(live_sessions.get("source_freshness"), Mapping)
        else {}
    )
    freshness_status = str(
        source_freshness.get("freshness_status") or source_freshness.get("status") or "unknown"
    )
    if freshness_status in {"unavailable", "unknown"}:
        blockers.append(
            {
                "blocker_id": "work_ledger_claim_snapshot_not_decisive",
                "reason": f"Work Ledger claim snapshot freshness is {freshness_status}.",
                "required_check": WORK_LEDGER_CLAIM_CARDS_REFRESH_COMMAND,
            }
        )

    phase_claim_counts = (
        live_sessions.get("phase_claim_counts")
        if isinstance(live_sessions.get("phase_claim_counts"), Mapping)
        else {}
    )
    phase_session_counts = (
        live_sessions.get("phase_session_counts")
        if isinstance(live_sessions.get("phase_session_counts"), Mapping)
        else {}
    )
    phase_claim_count = int(phase_claim_counts.get(phase_id) or 0) if phase_id else 0
    phase_session_count = int(phase_session_counts.get(phase_id) or 0) if phase_id else 0
    if phase_claim_count:
        claim_topology = (
            live_sessions.get("claim_topology")
            if isinstance(live_sessions.get("claim_topology"), Mapping)
            else {}
        )
        blockers.append(
            {
                "blocker_id": "phase_has_active_work_ledger_claims",
                "phase_id": phase_id,
                "claim_count": phase_claim_count,
                "session_count": phase_session_count,
                "classification": "phase_claim_topology_required",
                "bucket_counts": claim_topology.get("bucket_counts") or {},
                "safe_mutation_allowed": False,
                "recommended_lane": "Classify and drain/rehome claims through Work Ledger and Task Ledger before phase demotion.",
                "reason": "A declared phase with live Work Ledger claims is not just historical context.",
                "required_check": WORK_LEDGER_CLAIM_CARDS_REFRESH_COMMAND,
            }
        )

    matching_scope_candidates = [
        candidate
        for candidate in supervised_scope_candidates
        if phase_id and phase_id in set(candidate.get("shared_phase_ids") or [])
    ]
    if matching_scope_candidates:
        blockers.append(
            {
                "blocker_id": "supervised_scope_candidate_open",
                "phase_id": phase_id,
                "candidate_count": len(matching_scope_candidates),
                "reason": "Live multi-claim sessions may need a Work Ledger supervised-scope/finalizer lane before any phase demotion.",
                "required_check": "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh --limit 50 --full",
            }
        )

    anchor_status = str(declared_anchor.get("status") or "unknown")
    if phase_id and anchor_status != "declared_anchor_runtime_dormant":
        blockers.append(
            {
                "blocker_id": "declared_anchor_not_runtime_dormant",
                "phase_id": phase_id,
                "anchor_status": anchor_status,
                "reason": "Demotion is only considered by this guard after runtime evidence marks the declared anchor dormant.",
                "required_check": "./repo-python kernel.py --pulse",
            }
        )

    if not phase_id:
        closeable: bool | str = "unknown"
        status = "unknown_no_declared_phase"
        recommended_lane = "Use Task Ledger and Work Ledger as liveness authority; no phase demotion target exists."
    elif blockers:
        closeable = False
        status = "blocked"
        recommended_lane = "Do not demote 09_54; resolve live claims/finalizers or bind them to a supervised scope first."
    else:
        closeable = "unknown"
        status = "requires_full_guard"
        recommended_lane = (
            "Run phase/full, Task Ledger dependency, and refreshed Work Ledger checks before demotion; "
            "absence of claims alone is not a closeout receipt."
        )

    return {
        "checked_at": _utc_now(),
        "phase_id": phase_id,
        "closeable": closeable,
        "status": status,
        "blockers": blockers,
        "blocker_topology": (
            live_sessions.get("claim_topology")
            if isinstance(live_sessions.get("claim_topology"), Mapping)
            else {}
        ),
        "projection_freshness_status": projection_freshness.get("status") or "unknown",
        "recommended_lane": recommended_lane,
        "required_commands": [
            "./repo-python kernel.py --phase 09_54 --full",
            WORK_LEDGER_CLAIM_CARDS_REFRESH_COMMAND,
            "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
        ],
        "evidence_refs": evidence_refs,
    }


def build_active_execution_constellation(
    repo_root: Path,
    *,
    active_phase: Mapping[str, Any] | None = None,
    work_priority: Mapping[str, Any] | None = None,
    top_schedulable_workitem: Mapping[str, Any] | None = None,
    top_ready_workitem: Mapping[str, Any] | None = None,
    include_runtime_status: bool = True,
    campaign_limit: int = 4,
    claim_limit: int = 8,
    session_limit: int = 6,
) -> dict[str, Any]:
    """Compose a compact live-work projection for entry and pulse.

    Pulse callers may pass ``include_runtime_status=False`` to avoid loading
    the large Work Ledger runtime file when the active-claims sidecar already
    has the needed counts.
    """
    repo_root = Path(repo_root)
    if active_phase is None:
        active_phase = load_explicit_active_phase(repo_root) or {}
    orchestration_path = repo_root / ORCHESTRATION_STATE_PATH
    orchestration = _read_json(orchestration_path)
    schedulable_view = _read_json(repo_root / SCHEDULABLE_VIEW_PATH)
    active_claims_snapshot = _read_json(repo_root / ACTIVE_CLAIMS_SNAPSHOT_PATH)
    work_ledger_runtime_status: Mapping[str, Any] | None = None
    if include_runtime_status:
        try:
            work_ledger_runtime_status = work_ledger_runtime.load_runtime_status(repo_root)
        except Exception:
            work_ledger_runtime_status = {}
    freshness = _projection_freshness(
        repo_root,
        orchestration_path=orchestration_path,
        orchestration=orchestration,
        schedulable_view=schedulable_view,
        active_claims_snapshot=active_claims_snapshot,
        work_ledger_runtime_status=work_ledger_runtime_status or {},
    )
    if work_priority is None:
        try:
            from system.lib.task_ledger_priority import priority_constellation

            work_priority_payload: dict[str, Any] = priority_constellation(repo_root)
        except Exception as exc:
            work_priority_payload = {
                "schema_version": "task_ledger_priority_constellation_v1",
                "status": "unavailable",
                "reason": type(exc).__name__,
                "drilldown": "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2",
            }
    else:
        work_priority_payload = dict(work_priority)
    declared_anchor = _declared_anchor(active_phase, orchestration)
    sessions = _live_sessions(
        repo_root,
        active_claims_snapshot=active_claims_snapshot,
        work_ledger_runtime_status=work_ledger_runtime_status,
        include_runtime_status=include_runtime_status,
        claim_limit=claim_limit,
        session_limit=session_limit,
    )
    scope_candidates = _supervised_scope_candidates(sessions)
    constellation = {
        "kind": "active_execution_constellation",
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "authority_posture": "projection_not_source_authority",
        "source_refs": [
            _rel(repo_root, orchestration_path),
            SCHEDULABLE_VIEW_PATH.as_posix(),
            ACTIVE_CLAIMS_SNAPSHOT_PATH.as_posix(),
            WORK_LEDGER_RUNTIME_STATUS_PATH.as_posix(),
        ],
        "projection_freshness": freshness,
        "declared_anchor": declared_anchor,
        "work_priority": work_priority_payload,
        "live_campaigns": _live_campaigns(
            repo_root,
            schedulable_view=schedulable_view,
            top_schedulable_workitem=top_schedulable_workitem,
            top_ready_workitem=top_ready_workitem,
            limit=campaign_limit,
        ),
        "live_sessions": sessions,
        "supervised_scope_candidates": scope_candidates,
        "stale_decorative_pointers": _stale_decorative_pointers(declared_anchor),
        "demotion_guard": _demotion_guard(
            declared_anchor,
            sessions,
            scope_candidates,
            freshness,
        ),
        "type_a_type_b_boundary": {
            "type_a": "Work Ledger sessions and claims are the repo-substrate runtime authority.",
            "type_b": (
                "Bridge/HUD reasoning is advisory evidence or bridge_action WorkItem input; "
                "it is not a Work Ledger lease."
            ),
        },
        "next_actions": [
            {
                "command": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
                "reason": "Inspect ranked WorkItems before treating the declared phase as current work.",
            },
            {
                "command": WORK_LEDGER_SEED_SPEED_COMMAND,
                "reason": "Open the compact active-seed session packet before widening into claim rows.",
            },
        ],
    }
    if constellation["stale_decorative_pointers"]:
        constellation["next_actions"].insert(
            0,
            {
                "command": "./repo-python kernel.py --pulse",
                "reason": "Use pulse as the compact control surface that now exposes active execution separately from declared phase.",
            },
        )
    return constellation


def compact_active_execution_constellation_for_entry(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Trim the projection for the first-contact entry packet."""
    live_sessions = (
        payload.get("live_sessions") if isinstance(payload.get("live_sessions"), Mapping) else {}
    )
    counts = live_sessions.get("counts") if isinstance(live_sessions.get("counts"), Mapping) else {}
    sessions = live_sessions.get("sessions") if isinstance(live_sessions.get("sessions"), list) else []
    awareness_cards = (
        live_sessions.get("awareness_cards")
        if isinstance(live_sessions.get("awareness_cards"), list)
        else []
    )
    heartbeat_gap_rows = (
        live_sessions.get("heartbeat_gap_claim_sessions")
        if isinstance(live_sessions.get("heartbeat_gap_claim_sessions"), list)
        else []
    )
    compact_sessions: list[dict[str, Any]] = []
    for session in sessions[:3]:
        if not isinstance(session, Mapping):
            continue
        compact_sessions.append(
            {
                "session_id": session.get("session_id"),
                "actor": session.get("actor"),
                "phase_id": session.get("phase_id"),
                "claim_count": session.get("claim_count"),
                "path_count": session.get("path_count"),
                "work_item_ids": list(session.get("work_item_ids") or [])[:3],
                "leased_until": session.get("leased_until"),
                "drilldown": session.get("drilldown"),
            }
        )
    compact_awareness_cards = [
        {
            key: card.get(key)
            for key in (
                "session_id",
                "actor",
                "phase_id",
                "freshness_state",
                "pass_state",
                "current_pass_line",
                "last_pass_result_line",
                "source",
                "updated_at",
                "orphaned_active",
            )
            if card.get(key) not in (None, "", [], {})
        }
        for card in awareness_cards[:3]
        if isinstance(card, Mapping)
    ]
    compact_heartbeat_gap_rows = [
        {
            key: row.get(key)
            for key in (
                "session_id",
                "actor",
                "phase_id",
                "active_claim_count",
                "heartbeat_source",
                "freshness_state",
                "scope_ref",
                "heartbeat_command",
            )
            if row.get(key) not in (None, "", [], {})
        }
        for row in heartbeat_gap_rows[:2]
        if isinstance(row, Mapping)
    ]

    candidates = (
        payload.get("supervised_scope_candidates")
        if isinstance(payload.get("supervised_scope_candidates"), list)
        else []
    )
    compact_candidates: list[dict[str, Any]] = []
    for candidate in candidates[:2]:
        if not isinstance(candidate, Mapping):
            continue
        child_sessions = candidate.get("child_session_ids")
        child_count = len(child_sessions) if isinstance(child_sessions, list) else 0
        compact_candidates.append(
            {
                "candidate_id": candidate.get("candidate_id"),
                "child_session_count": child_count,
                "shared_phase_ids": list(candidate.get("shared_phase_ids") or [])[:3],
                "work_item_ids": list(candidate.get("work_item_ids") or [])[:5],
                "missing_fields": list(candidate.get("missing_fields") or [])[:5],
                "recommended_owner": candidate.get("recommended_owner"),
                "requires_child_phase": candidate.get("requires_child_phase"),
                "relation": candidate.get("relation"),
            }
        )

    def _compact_topology(topology: Mapping[str, Any]) -> dict[str, Any]:
        buckets = topology.get("buckets") if isinstance(topology.get("buckets"), list) else []
        compact_buckets: list[dict[str, Any]] = []
        empty_bucket_ids: list[str] = []
        for bucket in buckets:
            if not isinstance(bucket, Mapping):
                continue
            if int(bucket.get("claim_count") or 0) == 0:
                bucket_id = str(bucket.get("bucket_id") or "").strip()
                if bucket_id:
                    empty_bucket_ids.append(bucket_id)
                continue
            compact_buckets.append(
                {
                    "bucket_id": bucket.get("bucket_id"),
                    "claim_count": bucket.get("claim_count"),
                    "session_count": bucket.get("session_count"),
                    "work_item_ids": list(bucket.get("work_item_ids") or [])[:3],
                    "recommended_lane": bucket.get("recommended_lane"),
                    "exclusive": bucket.get("exclusive"),
                }
            )
        return {
            "schema_version": topology.get("schema_version"),
            "authority_posture": topology.get("authority_posture"),
            "source_path": topology.get("source_path"),
            "phase_ids": list(topology.get("phase_ids") or [])[:3],
            "claim_count": topology.get("claim_count"),
            "session_count": topology.get("session_count"),
            "bucket_counts": topology.get("bucket_counts") or {},
            "buckets": compact_buckets,
            "empty_bucket_ids": empty_bucket_ids,
            "drilldown_commands": topology.get("drilldown_commands") or {},
        }

    def _compact_projection_freshness(freshness: Mapping[str, Any]) -> dict[str, Any]:
        sources = freshness.get("sources") if isinstance(freshness.get("sources"), Mapping) else {}
        return {
            "status": freshness.get("status"),
            "source_statuses": {
                str(key): {
                    "status": value.get("status") if isinstance(value, Mapping) else "unknown",
                    "age_seconds": value.get("age_seconds") if isinstance(value, Mapping) else None,
                }
                for key, value in sources.items()
            },
        }

    def _compact_campaign(campaign: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "workitem_id": campaign.get("workitem_id"),
            "rank": campaign.get("rank"),
            "state": campaign.get("state"),
            "title": _snippet(campaign.get("title")),
            "drilldown_command": campaign.get("drilldown_command"),
        }

    def _compact_priority_row(row: Mapping[str, Any]) -> dict[str, Any]:
        signal = row.get("priority_signal") if isinstance(row.get("priority_signal"), Mapping) else {}
        summary = (
            row.get("dependency_summary")
            if isinstance(row.get("dependency_summary"), Mapping)
            else {}
        )
        pressure = {
            "score": signal.get("unlock_pressure_score"),
            "waiting": signal.get("waiting_downstream_unlock_count"),
            "downstream_unsatisfied": signal.get("downstream_unsatisfied_dep_total"),
        }
        return {
            "id": row.get("id") or row.get("workitem_id"),
            "rank": row.get("rank"),
            "state": row.get("state"),
            "title": _snippet(row.get("title"), 72),
            "source_view": row.get("source_view") or signal.get("source_view"),
            "schedulable": summary.get("schedulable") if summary else signal.get("schedulable"),
            "pressure": {
                key: value
                for key, value in pressure.items()
                if value not in (None, "", [], {})
            },
        }

    def _compact_priority_lane(
        lane_id: str,
        *,
        label: str,
        rows: Any,
        executable: bool,
        blocked: bool = False,
    ) -> dict[str, Any]:
        lane_rows = [row for row in rows if isinstance(row, Mapping)]
        return {
            "lane_id": lane_id,
            "label": label,
            "executable_now": executable,
            "blocked": blocked,
            "rows": [
                _compact_priority_row(row)
                for row in lane_rows[:ENTRY_PRIORITY_ROW_LIMIT]
            ],
        }

    def _compact_work_priority(priority: Mapping[str, Any]) -> dict[str, Any]:
        counts = priority.get("view_counts") if isinstance(priority.get("view_counts"), Mapping) else {}
        explanation = (
            priority.get("selector_explanation")
            if isinstance(priority.get("selector_explanation"), Mapping)
            else {}
        )
        return {
            "schema_version": priority.get("schema_version")
            or "task_ledger_priority_constellation_v1",
            "view_counts": {
                key: counts.get(key)
                for key in (
                    "execution_menu_schedulable",
                    "dependency_blocked",
                    "unlocks_by_rank",
                    "unlock_pressure",
                )
                if counts.get(key) is not None
            },
            "lane_contract": {
                "schedulable_now": "executable feasibility lane",
                "schedulable_unlock_pressure": "executable pressure lane",
                "global_unlock_pressure": "hidden pressure, not necessarily executable",
                "dependency_blocked": "blocked queue, unblock/classify before execution",
            },
            "lanes": [
                _compact_priority_lane(
                    "schedulable_now",
                    label="schedulable now",
                    rows=priority.get("top_schedulable_workitems") or [],
                    executable=True,
                ),
                _compact_priority_lane(
                    "schedulable_unlock_pressure",
                    label="highest schedulable unlock pressure",
                    rows=priority.get("top_schedulable_unlock_pressure_workitems") or [],
                    executable=True,
                ),
                _compact_priority_lane(
                    "global_unlock_pressure",
                    label="hidden/global unlock pressure, not necessarily schedulable",
                    rows=priority.get("top_global_unlock_pressure_workitems") or [],
                    executable=False,
                ),
                _compact_priority_lane(
                    "dependency_blocked",
                    label="blocked but important",
                    rows=priority.get("top_dependency_blocked_workitems") or [],
                    executable=False,
                    blocked=True,
                ),
            ],
            "drilldowns": {
                key: value
                for key, value in (priority.get("drilldown_commands") or {}).items()
                if key in {
                    "organizer_report",
                    "task_ledger_cluster",
                    "top_schedulable_card",
                    "top_blocked_card",
                }
                and value not in (None, "", [], {})
            },
            "omission_receipt": {
                "omitted": [
                    "rows beyond the first per lane",
                    "full score components",
                    "full dependency edge lists",
                ],
                "reason": "Entry carries lane separation; pulse/Task Ledger cards carry the scheduler detail.",
                "drilldown": "./repo-python kernel.py --pulse",
            },
        }

    def _compact_demotion_guard(guard: Mapping[str, Any]) -> dict[str, Any]:
        topology = (
            guard.get("blocker_topology")
            if isinstance(guard.get("blocker_topology"), Mapping)
            else {}
        )
        blockers = guard.get("blockers") if isinstance(guard.get("blockers"), list) else []
        compact_blockers: list[dict[str, Any]] = []
        for blocker in blockers:
            if not isinstance(blocker, Mapping):
                continue
            compact_blockers.append(
                {
                    "blocker_id": blocker.get("blocker_id"),
                    "phase_id": blocker.get("phase_id"),
                    "claim_count": blocker.get("claim_count"),
                    "session_count": blocker.get("session_count"),
                    "candidate_count": blocker.get("candidate_count"),
                    "classification": blocker.get("classification"),
                    "bucket_counts": blocker.get("bucket_counts"),
                    "safe_mutation_allowed": blocker.get("safe_mutation_allowed"),
                    "recommended_lane": blocker.get("recommended_lane"),
                    "required_check": blocker.get("required_check"),
                }
            )
        return {
            "phase_id": guard.get("phase_id"),
            "closeable": guard.get("closeable"),
            "status": guard.get("status"),
            "blocker_count": len(compact_blockers),
            "blockers": compact_blockers[:2],
            "bucket_counts": (
                topology.get("bucket_counts")
                if isinstance(topology, Mapping)
                else {}
            ),
            "projection_freshness_status": guard.get("projection_freshness_status"),
            "recommended_lane": guard.get("recommended_lane"),
            "required_commands": list(guard.get("required_commands") or [])[:2],
        }

    declared_anchor = payload.get("declared_anchor") or {}
    if not isinstance(declared_anchor, Mapping):
        declared_anchor = {}
    work_priority = (
        payload.get("work_priority") if isinstance(payload.get("work_priority"), Mapping) else {}
    )
    stale_pointers = [
        pointer
        for pointer in list(payload.get("stale_decorative_pointers") or [])[:1]
        if isinstance(pointer, Mapping)
    ]
    return {
        "kind": payload.get("kind") or "active_execution_constellation",
        "schema_version": payload.get("schema_version") or SCHEMA_VERSION,
        "view_profile": "entry_compact",
        "authority_posture": payload.get("authority_posture") or "projection_not_source_authority",
        "source_refs": list(payload.get("source_refs") or []),
        "projection_freshness": _compact_projection_freshness(
            payload.get("projection_freshness") or {}
        ),
        "declared_anchor": {
            "phase_id": declared_anchor.get("phase_id"),
            "runtime_state": declared_anchor.get("runtime_state"),
            "runtime_gate_reason": declared_anchor.get("runtime_gate_reason"),
            "status": declared_anchor.get("status"),
            "liveness_summary": (
                "Declared phase is contextual/dormant when runtime is inactive; "
                "Task Ledger and Work Ledger are the live execution authorities."
            ),
        },
        "work_priority": _compact_work_priority(work_priority) if work_priority else {},
        "live_campaigns": [
            _compact_campaign(campaign)
            for campaign in list(payload.get("live_campaigns") or [])[:3]
            if isinstance(campaign, Mapping)
        ],
        "live_sessions": {
            "counts": {
                "active_claims": counts.get("active_claims"),
                "effective_active_sessions": counts.get("effective_active_sessions"),
                "orphaned_active_sessions": counts.get("orphaned_active_sessions"),
                "claim_collisions": counts.get("claim_collisions"),
                "claim_session_heartbeat_gap_count": counts.get(
                    "claim_session_heartbeat_gap_count"
                ),
            },
            "sessions": compact_sessions[:2],
            "awareness_cards": compact_awareness_cards[:2],
            "heartbeat_gap_status": live_sessions.get("heartbeat_gap_status"),
            "first_action": live_sessions.get("first_action"),
            "first_action_kind": live_sessions.get("first_action_kind"),
            "first_action_command": live_sessions.get("first_action_command"),
            "first_action_ref": live_sessions.get("first_action_ref"),
            "heartbeat_gap_claim_sessions": compact_heartbeat_gap_rows,
            "drilldown_commands": live_sessions.get("drilldown_commands") or {},
        },
        "supervised_scope_candidates": {
            "count": len(compact_candidates),
            "top": compact_candidates[:1],
        },
        "stale_decorative_pointers": [
            {
                "pointer": pointer.get("pointer"),
                "replacement_surface": pointer.get("replacement_surface"),
                "safe_action": pointer.get("safe_action"),
            }
            for pointer in stale_pointers
        ],
        "demotion_guard": _compact_demotion_guard(payload.get("demotion_guard") or {}),
        "type_a_type_b_boundary": payload.get("type_a_type_b_boundary") or {},
        "next_actions": list(payload.get("next_actions") or [])[:2],
        "omission_receipt": {
            "omitted": [
                "live_sessions.active_claims",
                "live_sessions.sessions[].paths",
                "live_sessions.awareness_cards[].scope_refs",
                "supervised_scope_candidates[].child_session_ids",
                "supervised_scope_candidates[].shared_paths",
                "demotion_guard.blocker_topology",
            ],
            "reason": "Entry needs the liveness decision and drilldowns; pulse/full projection carries claim details.",
            "drilldown": "./repo-python kernel.py --pulse --full",
        },
    }
