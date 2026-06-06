"""Governed campaign state transition helpers."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


CAMPAIGN_TRANSITION_SCHEMA_VERSION = "campaign_state_transition_v1"
CAMPAIGN_SYNC_SCHEMA_VERSION = "campaign_state_sync_v0"
CAMPAIGN_DISPATCH_REGISTER_SCHEMA_VERSION = "campaign_dispatch_register_v0"
CAMPAIGN_STATE_SCHEMA_VERSION = "campaign_state_v1"

CAMPAIGN_STATE_STANDARD_REL = Path("codex") / "standards" / "std_campaign_state.json"
CAMPAIGN_TRANSITION_STANDARD_REL = Path("codex") / "standards" / "std_campaign_transition.json"

LEGAL_DISPATCH_TRANSITIONS: dict[str, set[str]] = {
    "candidate": {"claimed", "blocked", "completed"},
    "claimed": {"running", "blocked", "completed", "failed"},
    "running": {"blocked", "completed", "failed"},
    "blocked": {"candidate", "failed"},
    "failed": {"candidate"},
    "completed": set(),
}


class CampaignTransitionError(ValueError):
    """Raised when a campaign transition cannot be applied safely."""


def _safe_load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CampaignTransitionError(f"Missing required JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CampaignTransitionError(f"Invalid JSON file: {path}: {exc}") from exc


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _parse_datetime(value: Any) -> datetime | None:
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
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_z(value: Any, *, default: datetime | None = None) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        parsed = default or datetime.now(timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _event_id(*, campaign_id: str, receipt_id: str, mission_id: str, work_ledger_event_id: str, event_kind: str, valid_at: str) -> str:
    digest = hashlib.sha256(
        "|".join([campaign_id, receipt_id, mission_id, work_ledger_event_id, event_kind]).encode("utf-8")
    ).hexdigest()[:12]
    stamp = valid_at.replace("-", "").replace(":", "").replace("Z", "Z")
    return f"cse_{stamp}_{digest}"


def _registration_event_id(*, campaign_id: str, mission_id: str, lane_id: str, event_kind: str, valid_at: str) -> str:
    digest = hashlib.sha256(
        "|".join([campaign_id, mission_id, lane_id, event_kind]).encode("utf-8")
    ).hexdigest()[:12]
    stamp = valid_at.replace("-", "").replace(":", "").replace("Z", "Z")
    return f"cse_{stamp}_{digest}"


def _campaign_state_path(root: Path, campaign_id: str) -> Path:
    return root / "codex" / "campaigns" / campaign_id / "campaign_state.json"


def _campaign_events_path(root: Path, campaign_id: str) -> Path:
    return root / "codex" / "campaigns" / campaign_id / "campaign_events.jsonl"


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def validate_dispatch_transition(current_status: str, target_status: str, *, superseding: bool = False) -> str:
    """Validate one dispatch-status transition and return its transition semantics."""
    current = str(current_status or "candidate").strip()
    target = str(target_status or "").strip()
    if not target:
        raise CampaignTransitionError("Target dispatch status is required.")
    if current == target:
        return "already_target"
    if current == "completed" and not superseding:
        raise CampaignTransitionError("completed dispatches are terminal without a superseding transition event")
    legal_targets = LEGAL_DISPATCH_TRANSITIONS.get(current)
    if legal_targets is None:
        raise CampaignTransitionError(f"Unknown current dispatch status: {current}")
    if target not in legal_targets:
        raise CampaignTransitionError(f"Illegal campaign dispatch transition: {current} -> {target}")
    return "legal_transition"


def _load_standard(root: Path, rel_path: Path) -> dict[str, Any]:
    payload = _safe_load_json(root / rel_path)
    if not isinstance(payload, dict):
        raise CampaignTransitionError(f"Invalid standard payload: {rel_path.as_posix()}")
    return payload


def _load_state(root: Path, campaign_id: str) -> dict[str, Any]:
    path = _campaign_state_path(root, campaign_id)
    payload = _safe_load_json(path)
    if not isinstance(payload, dict):
        raise CampaignTransitionError(f"Invalid campaign state payload: {_rel(root, path)}")
    if payload.get("schema_version") != CAMPAIGN_STATE_SCHEMA_VERSION:
        raise CampaignTransitionError(
            f"Unsupported campaign state schema_version: {payload.get('schema_version')!r}"
        )
    if payload.get("campaign_id") != campaign_id:
        raise CampaignTransitionError(
            f"Campaign state id mismatch: expected {campaign_id}, got {payload.get('campaign_id')!r}"
        )
    return payload


def validate_campaign_state(root: Path | str, campaign_id: str, state_payload: Mapping[str, Any]) -> None:
    repo_root = Path(root)
    _load_standard(repo_root, CAMPAIGN_STATE_STANDARD_REL)
    required = {
        "kind",
        "schema_version",
        "campaign_id",
        "active_phase_id",
        "campaign_status",
        "campaign_envelope_status",
        "effective_authority_rule",
        "lanes",
        "dispatches",
        "last_receipts",
        "next_campaign_actions",
        "updated_at",
    }
    missing = sorted(required - set(state_payload.keys()))
    if missing:
        raise CampaignTransitionError(f"Campaign state missing required keys: {', '.join(missing)}")
    if state_payload.get("schema_version") != CAMPAIGN_STATE_SCHEMA_VERSION:
        raise CampaignTransitionError("Campaign state schema_version must be campaign_state_v1")
    if state_payload.get("campaign_id") != campaign_id:
        raise CampaignTransitionError("Campaign state campaign_id does not match requested campaign")
    lanes = state_payload.get("lanes")
    dispatches = state_payload.get("dispatches")
    if not isinstance(lanes, Mapping) or not isinstance(dispatches, list):
        raise CampaignTransitionError("Campaign state lanes and dispatches must be structured collections")
    for row in dispatches:
        if not isinstance(row, Mapping):
            raise CampaignTransitionError("Campaign state dispatch rows must be objects")
        lane_id = str(row.get("lane_id") or "").strip()
        if lane_id not in lanes:
            raise CampaignTransitionError(
                f"Campaign state dispatch {row.get('mission_id')!r} references unknown lane {lane_id!r}"
            )


def _event_for_registered_dispatch(events_path: Path, *, mission_id: str) -> dict[str, Any] | None:
    for row in _iter_jsonl(events_path):
        if row.get("event_kind") != "dispatch_registered":
            continue
        if str(row.get("mission_id") or "") == mission_id:
            return row
    return None


def register_campaign_dispatch(
    root: Path | str,
    campaign_id: str,
    *,
    mission_id: str,
    lane_id: str,
    objective: str,
    source_refs: Sequence[str] | None = None,
    write_scope: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Register a new campaign dispatch row through a governed event."""
    repo_root = Path(root)
    campaign = str(campaign_id or "").strip()
    mission = str(mission_id or "").strip()
    lane = str(lane_id or "").strip()
    objective_text = str(objective or "").strip()
    if not campaign:
        raise CampaignTransitionError("campaign_id is required")
    if not mission:
        raise CampaignTransitionError("mission id is required")
    if not lane:
        raise CampaignTransitionError("lane id is required")
    if not objective_text:
        raise CampaignTransitionError("objective is required")

    validate_transition_standard(repo_root)
    state_payload = _load_state(repo_root, campaign)
    validate_campaign_state(repo_root, campaign, state_payload)

    lanes = state_payload.get("lanes")
    if not isinstance(lanes, Mapping) or lane not in lanes:
        raise CampaignTransitionError(f"Unknown campaign lane for dispatch registration: {lane}")

    dispatches = _dispatch_rows(state_payload)
    events_path = _campaign_events_path(repo_root, campaign)
    state_path = _campaign_state_path(repo_root, campaign)
    existing = dispatches.get(mission)
    existing_event = _event_for_registered_dispatch(events_path, mission_id=mission)
    if existing is not None:
        if str(existing.get("lane_id") or "") != lane:
            raise CampaignTransitionError(
                f"Campaign dispatch {mission!r} is already registered on lane {existing.get('lane_id')!r}"
            )
        if str(existing.get("dispatch_status") or "") == "completed":
            raise CampaignTransitionError("completed dispatches cannot be re-registered without a superseding event")
        return {
            "kind": "campaign_dispatch_register",
            "schema_version": CAMPAIGN_DISPATCH_REGISTER_SCHEMA_VERSION,
            "campaign_id": campaign,
            "status": "already_registered",
            "mission_id": mission,
            "lane_id": lane,
            "event_id": existing_event.get("event_id") if existing_event else None,
            "event_path": _rel(repo_root, events_path),
            "state_path": _rel(repo_root, state_path),
            "appended_event": False,
            "state_changed": False,
        }

    valid_at = _iso_z(None)
    event_kind = "dispatch_registered"
    event_id = _registration_event_id(
        campaign_id=campaign,
        mission_id=mission,
        lane_id=lane,
        event_kind=event_kind,
        valid_at=valid_at,
    )
    dispatch_row = {
        "mission_id": mission,
        "lane_id": lane,
        "dispatch_status": "candidate",
        "claim_id": None,
        "receipt_id": None,
        "acceptance_status": "unknown",
        "updated_at": None,
    }
    state_payload.setdefault("dispatches", []).append(dispatch_row)
    actions = state_payload.get("next_campaign_actions")
    if not isinstance(actions, list):
        actions = []
        state_payload["next_campaign_actions"] = actions
    if not any(isinstance(action, Mapping) and str(action.get("action_id") or "") == mission for action in actions):
        actions.insert(
            0,
            {
                "action_id": mission,
                "lane_id": lane,
                "command": f'./repo-python kernel.py --campaign --task "{mission.replace("_", " ")}"',
                "why": objective_text,
            },
        )
    state_payload["updated_at"] = valid_at
    state_patch = {
        f"dispatches.{mission}": dispatch_row,
        "next_campaign_actions[0]": state_payload["next_campaign_actions"][0],
        "updated_at": valid_at,
    }
    validate_campaign_state(repo_root, campaign, state_payload)

    event_payload = {
        "event_id": event_id,
        "schema_version": CAMPAIGN_TRANSITION_SCHEMA_VERSION,
        "campaign_id": campaign,
        "event_kind": event_kind,
        "valid_at": valid_at,
        "source_registration": {
            "authority": "campaign_dispatch_register",
            "objective": objective_text,
            "source_refs": [str(ref) for ref in (source_refs or []) if str(ref).strip()],
            "write_scope": [str(ref) for ref in (write_scope or []) if str(ref).strip()],
        },
        "mission_id": mission,
        "lane_id": lane,
        "transition": {
            "from": None,
            "to": {
                "dispatch_status": "candidate",
                "acceptance_status": "unknown",
            },
        },
        "state_patch": state_patch,
        "validation": {
            "standard": CAMPAIGN_STATE_STANDARD_REL.as_posix(),
            "transition_standard": CAMPAIGN_TRANSITION_STANDARD_REL.as_posix(),
            "result": "passed",
        },
    }
    _append_jsonl(events_path, event_payload)
    _write_json(state_path, state_payload)

    return {
        "kind": "campaign_dispatch_register",
        "schema_version": CAMPAIGN_DISPATCH_REGISTER_SCHEMA_VERSION,
        "campaign_id": campaign,
        "status": "applied",
        "mission_id": mission,
        "lane_id": lane,
        "event_id": event_id,
        "event_path": _rel(repo_root, events_path),
        "state_path": _rel(repo_root, state_path),
        "appended_event": True,
        "state_changed": True,
        "state_patch": state_patch,
    }


def validate_transition_standard(root: Path | str) -> None:
    repo_root = Path(root)
    standard = _load_standard(repo_root, CAMPAIGN_TRANSITION_STANDARD_REL)
    if standard.get("schema_version") != "std_campaign_transition_v1":
        raise CampaignTransitionError("Campaign transition standard schema_version must be std_campaign_transition_v1")
    legal = standard.get("legal_dispatch_transitions")
    if not isinstance(legal, Mapping):
        raise CampaignTransitionError("Campaign transition standard must define legal_dispatch_transitions")


def _dispatch_rows(state_payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = state_payload.get("dispatches")
    if not isinstance(rows, list):
        return {}
    dispatches: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        mission_id = str(row.get("mission_id") or "").strip()
        if mission_id:
            dispatches[mission_id] = row
    return dispatches


def _ledger_events(root: Path) -> list[dict[str, Any]]:
    ledger_root = root / "codex" / "ledger"
    events: list[dict[str, Any]] = []
    for path in sorted(ledger_root.glob("*/work_ledger.jsonl")):
        for row in _iter_jsonl(path):
            row = dict(row)
            row["_ledger_path"] = _rel(root, path)
            events.append(row)
    return events


def _receipt_events(root: Path, receipt_id: str) -> list[dict[str, Any]]:
    rows = [row for row in _ledger_events(root) if str(row.get("td_id") or "").strip() == receipt_id]
    if not rows:
        raise CampaignTransitionError(f"Work Ledger receipt not found: {receipt_id}")
    return rows


def _select_receipt_close(events: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    for row in reversed(list(events)):
        if row.get("event_kind") == "todo_close":
            return row
    return events[-1]


def _select_receipt_open(events: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    for row in events:
        if row.get("event_kind") == "todo_open":
            return row
    return events[0]


def _slug(value: Any) -> str:
    return "_".join(
        part
        for part in str(value or "")
        .casefold()
        .replace("-", "_")
        .replace("/", "_")
        .replace(":", "_")
        .split()
        if part
    )


def _candidate_strings(receipt_events: Sequence[Mapping[str, Any]]) -> list[str]:
    candidates: list[str] = []
    for row in receipt_events:
        metadata = row.get("metadata")
        if isinstance(metadata, Mapping):
            for key in ("mission_id", "reason", "work_kind", "campaign_mission_id"):
                value = metadata.get(key)
                if value:
                    candidates.append(str(value))
        for key in ("title", "resolution_label", "body"):
            value = row.get(key)
            if value:
                candidates.append(str(value))
        episode = row.get("resolution_episode")
        if isinstance(episode, Mapping):
            for key in ("label", "ref", "kind"):
                value = episode.get(key)
                if value:
                    candidates.append(str(value))
            episode_metadata = episode.get("metadata")
            if isinstance(episode_metadata, Mapping):
                for key in ("mission_id", "campaign_mission_id", "reason"):
                    value = episode_metadata.get(key)
                    if value:
                        candidates.append(str(value))
    return candidates


def _explicit_mission_candidates(receipt_events: Sequence[Mapping[str, Any]]) -> list[str]:
    candidates: list[str] = []
    for row in receipt_events:
        metadata = row.get("metadata")
        if isinstance(metadata, Mapping):
            for key in ("mission_id", "campaign_mission_id"):
                value = metadata.get(key)
                if value:
                    candidates.append(str(value))
        episode = row.get("resolution_episode")
        if isinstance(episode, Mapping):
            episode_metadata = episode.get("metadata")
            if isinstance(episode_metadata, Mapping):
                for key in ("mission_id", "campaign_mission_id"):
                    value = episode_metadata.get(key)
                    if value:
                        candidates.append(str(value))
    return candidates


def _resolve_mission_id(
    *,
    state_payload: Mapping[str, Any],
    receipt_events: Sequence[Mapping[str, Any]],
) -> str:
    dispatches = _dispatch_rows(state_payload)
    explicit_candidates = _explicit_mission_candidates(receipt_events)
    for candidate in explicit_candidates:
        if candidate in dispatches:
            return candidate
    explicit_slugs = [_slug(candidate) for candidate in explicit_candidates]
    for mission_id in dispatches:
        mission_slug = _slug(mission_id)
        if any(candidate == mission_slug for candidate in explicit_slugs):
            return mission_id
    if explicit_candidates:
        raise CampaignTransitionError("Receipt does not reference a known campaign mission")

    candidates = _candidate_strings(receipt_events)
    for candidate in candidates:
        if candidate in dispatches:
            return candidate
    candidate_slugs = [_slug(candidate) for candidate in candidates]
    for mission_id in dispatches:
        mission_slug = _slug(mission_id)
        if any(candidate == mission_slug for candidate in candidate_slugs):
            return mission_id
    for mission_id in dispatches:
        mission_slug = _slug(mission_id)
        if any(mission_slug and mission_slug in candidate for candidate in candidate_slugs):
            return mission_id
    raise CampaignTransitionError("Receipt does not reference a known campaign mission")


def _target_from_receipt(close_event: Mapping[str, Any]) -> tuple[str, str, str]:
    event_kind = str(close_event.get("event_kind") or "").strip()
    if event_kind == "todo_close":
        return "dispatch_completed", "completed", "passed"
    metadata = close_event.get("metadata")
    if isinstance(metadata, Mapping):
        requested_status = str(metadata.get("dispatch_status") or "").strip()
        acceptance = str(metadata.get("acceptance_status") or "unknown").strip()
        if requested_status:
            return f"dispatch_{requested_status}", requested_status, acceptance
    raise CampaignTransitionError("Receipt does not carry a supported campaign transition event")


def _event_already_applied(events_path: Path, *, receipt_id: str, mission_id: str) -> dict[str, Any] | None:
    for row in _iter_jsonl(events_path):
        source = row.get("source_receipt")
        if not isinstance(source, Mapping):
            continue
        if str(source.get("td_id") or "") == receipt_id and str(row.get("mission_id") or "") == mission_id:
            return row
    return None


def _receipt_row(
    *,
    receipt_id: str,
    event_id: str,
    mission_id: str,
    status: str,
    close_event: Mapping[str, Any],
) -> dict[str, Any]:
    body = str(close_event.get("body") or "").strip()
    return {
        "receipt_id": receipt_id,
        "event_id": event_id,
        "mission_id": mission_id,
        "status": status,
        "summary": body[:240] if body else f"Campaign transition {mission_id} -> {status}.",
    }


def _apply_state_update(
    *,
    root: Path,
    campaign_id: str,
    state_payload: dict[str, Any],
    mission_id: str,
    target_status: str,
    acceptance_status: str,
    receipt_id: str,
    work_ledger_event_id: str,
    close_event: Mapping[str, Any],
    valid_at: str,
    write_state: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    dispatches = _dispatch_rows(state_payload)
    dispatch = dispatches[mission_id]
    lane_id = str(dispatch.get("lane_id") or "").strip()
    current_status = str(dispatch.get("dispatch_status") or "candidate").strip()
    current_acceptance_status = str(dispatch.get("acceptance_status") or "unknown")
    transition_semantics = validate_dispatch_transition(current_status, target_status)
    state_patch: dict[str, Any] = {}
    changed = False

    if current_status != target_status:
        dispatch["dispatch_status"] = target_status
        state_patch[f"dispatches.{mission_id}.dispatch_status"] = target_status
        changed = True
    if str(dispatch.get("acceptance_status") or "") != acceptance_status:
        dispatch["acceptance_status"] = acceptance_status
        state_patch[f"dispatches.{mission_id}.acceptance_status"] = acceptance_status
        changed = True
    if str(dispatch.get("receipt_id") or "") != receipt_id:
        dispatch["receipt_id"] = receipt_id
        state_patch[f"dispatches.{mission_id}.receipt_id"] = receipt_id
        changed = True
    if str(dispatch.get("updated_at") or "") != valid_at:
        dispatch["updated_at"] = valid_at
        state_patch[f"dispatches.{mission_id}.updated_at"] = valid_at
        changed = True

    lanes = state_payload.get("lanes")
    if target_status == "completed" and isinstance(lanes, Mapping):
        lane = lanes.get(lane_id)
        if isinstance(lane, dict):
            if str(lane.get("status") or "") != "completed":
                lane["status"] = "completed"
                state_patch[f"lanes.{lane_id}.status"] = "completed"
                changed = True
            if lane.get("next_receipt") is not None:
                lane["next_receipt"] = None
                state_patch[f"lanes.{lane_id}.next_receipt"] = None
                changed = True

    actions = state_payload.get("next_campaign_actions")
    if target_status == "completed" and isinstance(actions, list):
        retained_actions = [
            action
            for action in actions
            if not (
                isinstance(action, Mapping)
                and (
                    str(action.get("action_id") or "") == mission_id
                    or str(action.get("lane_id") or "") == lane_id
                )
            )
        ]
        if len(retained_actions) != len(actions):
            state_payload["next_campaign_actions"] = retained_actions
            state_patch["next_campaign_actions"] = retained_actions
            changed = True

    last_receipts = state_payload.get("last_receipts")
    if not isinstance(last_receipts, list):
        last_receipts = []
        state_payload["last_receipts"] = last_receipts
        changed = True
    receipt_entry = _receipt_row(
        receipt_id=receipt_id,
        event_id=work_ledger_event_id,
        mission_id=mission_id,
        status=target_status,
        close_event=close_event,
    )
    if not any(
        isinstance(row, Mapping)
        and row.get("receipt_id") == receipt_id
        and row.get("mission_id") == mission_id
        for row in last_receipts
    ):
        last_receipts.insert(0, receipt_entry)
        del last_receipts[8:]
        state_patch["last_receipts[0]"] = receipt_entry
        changed = True

    if changed:
        state_payload["updated_at"] = valid_at
        state_patch["updated_at"] = valid_at
        validate_campaign_state(root, campaign_id, state_payload)
        if write_state:
            _write_json(_campaign_state_path(root, campaign_id), state_payload)

    return {
        "from": {
            "dispatch_status": current_status,
            "acceptance_status": current_acceptance_status,
        },
        "to": {
            "dispatch_status": target_status,
            "acceptance_status": acceptance_status,
        },
        "semantics": transition_semantics,
    }, state_patch, changed


def _project_existing_event(
    *,
    root: Path,
    campaign_id: str,
    state_payload: dict[str, Any],
    event_payload: Mapping[str, Any],
    mission_id: str,
    receipt_id: str,
    close_event: Mapping[str, Any],
) -> tuple[str, dict[str, Any], bool]:
    transition = event_payload.get("transition")
    if not isinstance(transition, Mapping):
        raise CampaignTransitionError("Campaign event is missing a transition object")
    target = transition.get("to")
    if not isinstance(target, Mapping):
        raise CampaignTransitionError("Campaign event transition is missing a target state")
    target_status = str(target.get("dispatch_status") or "").strip()
    acceptance_status = str(target.get("acceptance_status") or "unknown").strip()
    if not target_status:
        raise CampaignTransitionError("Campaign event target dispatch_status is required")
    source_receipt = event_payload.get("source_receipt")
    work_ledger_event_id = (
        str(source_receipt.get("work_ledger_event_id") or "").strip()
        if isinstance(source_receipt, Mapping)
        else ""
    )
    valid_at = _iso_z(event_payload.get("valid_at") or close_event.get("created_at") or close_event.get("valid_at"))
    _transition, state_patch, state_changed = _apply_state_update(
        root=root,
        campaign_id=campaign_id,
        state_payload=state_payload,
        mission_id=mission_id,
        target_status=target_status,
        acceptance_status=acceptance_status,
        receipt_id=receipt_id,
        work_ledger_event_id=work_ledger_event_id,
        close_event=close_event,
        valid_at=valid_at,
        write_state=True,
    )
    return "projection_repaired" if state_changed else "already_applied", state_patch, state_changed


def sync_campaign_state_from_receipt(
    root: Path | str,
    campaign_id: str,
    receipt_id: str,
) -> dict[str, Any]:
    """Assimilate one Work Ledger receipt into campaign state and event history."""
    repo_root = Path(root)
    campaign = str(campaign_id or "").strip()
    receipt = str(receipt_id or "").strip()
    if not campaign:
        raise CampaignTransitionError("campaign_id is required")
    if not receipt:
        raise CampaignTransitionError("receipt id is required")

    validate_transition_standard(repo_root)
    state_payload = _load_state(repo_root, campaign)
    validate_campaign_state(repo_root, campaign, state_payload)

    receipt_events = _receipt_events(repo_root, receipt)
    open_event = _select_receipt_open(receipt_events)
    close_event = _select_receipt_close(receipt_events)
    mission_id = _resolve_mission_id(state_payload=state_payload, receipt_events=receipt_events)
    dispatch = _dispatch_rows(state_payload)[mission_id]
    lane_id = str(dispatch.get("lane_id") or "").strip()
    event_kind, target_status, acceptance_status = _target_from_receipt(close_event)
    events_path = _campaign_events_path(repo_root, campaign)
    already = _event_already_applied(events_path, receipt_id=receipt, mission_id=mission_id)
    state_path = _campaign_state_path(repo_root, campaign)

    if already:
        status, state_patch, state_changed = _project_existing_event(
            root=repo_root,
            campaign_id=campaign,
            state_payload=state_payload,
            event_payload=already,
            mission_id=mission_id,
            receipt_id=receipt,
            close_event=close_event,
        )
        return {
            "kind": "campaign_state_sync",
            "schema_version": CAMPAIGN_SYNC_SCHEMA_VERSION,
            "campaign_id": campaign,
            "status": status,
            "receipt_id": receipt,
            "event_id": already.get("event_id"),
            "event_path": _rel(repo_root, events_path),
            "state_path": _rel(repo_root, state_path),
            "transition": {
                "mission_id": mission_id,
                "lane_id": lane_id,
                "from": (already.get("transition") or {}).get("from"),
                "to": (already.get("transition") or {}).get("to"),
            },
            "validation": {
                "state_standard": "passed",
                "transition_standard": "passed",
            },
            "appended_event": False,
            "state_changed": state_changed,
            "state_patch": state_patch,
        }

    valid_at = _iso_z(close_event.get("created_at") or close_event.get("valid_at"))
    work_ledger_event_id = str(close_event.get("event_id") or "").strip() or str(open_event.get("event_id") or "")
    projected_state = deepcopy(state_payload)
    transition, state_patch, state_changed = _apply_state_update(
        root=repo_root,
        campaign_id=campaign,
        state_payload=projected_state,
        mission_id=mission_id,
        target_status=target_status,
        acceptance_status=acceptance_status,
        receipt_id=receipt,
        work_ledger_event_id=work_ledger_event_id,
        close_event=close_event,
        valid_at=valid_at,
        write_state=False,
    )
    event_id = _event_id(
        campaign_id=campaign,
        receipt_id=receipt,
        mission_id=mission_id,
        work_ledger_event_id=work_ledger_event_id,
        event_kind=event_kind,
        valid_at=valid_at,
    )
    event_payload = {
        "event_id": event_id,
        "schema_version": CAMPAIGN_TRANSITION_SCHEMA_VERSION,
        "campaign_id": campaign,
        "event_kind": event_kind,
        "valid_at": valid_at,
        "source_receipt": {
            "td_id": receipt,
            "work_ledger_event_id": work_ledger_event_id,
            "work_ledger_open_event_id": str(open_event.get("event_id") or ""),
            "phase_id": close_event.get("phase_id") or open_event.get("phase_id"),
            "ledger_path": close_event.get("_ledger_path") or open_event.get("_ledger_path"),
        },
        "mission_id": mission_id,
        "lane_id": lane_id,
        "transition": transition,
        "state_patch": state_patch,
        "validation": {
            "standard": CAMPAIGN_STATE_STANDARD_REL.as_posix(),
            "transition_standard": CAMPAIGN_TRANSITION_STANDARD_REL.as_posix(),
            "result": "passed",
        },
    }
    _append_jsonl(events_path, event_payload)
    if state_changed:
        validate_campaign_state(repo_root, campaign, projected_state)
        _write_json(state_path, projected_state)

    return {
        "kind": "campaign_state_sync",
        "schema_version": CAMPAIGN_SYNC_SCHEMA_VERSION,
        "campaign_id": campaign,
        "status": "applied",
        "receipt_id": receipt,
        "event_id": event_id,
        "event_path": _rel(repo_root, events_path),
        "state_path": _rel(repo_root, state_path),
        "transition": {
            "mission_id": mission_id,
            "lane_id": lane_id,
            "from": transition["from"]["dispatch_status"],
            "to": transition["to"]["dispatch_status"],
        },
        "validation": {
            "state_standard": "passed",
            "transition_standard": "passed",
        },
        "appended_event": True,
        "state_changed": state_changed,
    }
