"""
[PURPOSE]
- Teleology: Publish a bounded point-in-time liveness snapshot over the local
  Claude Code and Codex session transport artifacts so the overnight chain,
  the Station UI, and any operator-fired meta-mission can cheaply answer
  "is a controller alive right now, and which one?" without re-deriving the
  heartbeat format. Raw-seed anchor:
  par_phase_05_4_agentic_navigation_and_subsystem_convergence_raw_seed__source_7_2026_04_14_infrastructure_integration_note_025
  — "if we read the .codex and .claude, like, backend properly, we can
  figure that out." This module is the distilled implementation of that
  intent for the session-heartbeat surface only.
- Mechanism: Read `tools/meta/bridge/claude_session_transport.json` and
  `tools/meta/bridge/codex_session_transport.json` plus any `.claude/hooks`
  active-session stamp, compute staleness (seconds since the last stamped
  event), classify liveness tone per provider, and emit a single normalized
  snapshot dict. Writes the snapshot to a launcher-owned workspace file when
  `AIWF_META_MISSION_RUN_ID` is set, otherwise to a caller-chosen path.
- Non-goal: Running the bridge, mutating the transports, or interpreting
  session archaeology (transcript_archaeology is the archaeology career).

[INTERFACE]
- snapshot(repo_root)                                                 -> dict
- write_snapshot(repo_root, *, output_path=None)                      -> Path
- main(argv)                                                          -> int

[CONSTRAINTS]
- Pure read over the two transport JSONs plus one optional .claude stamp.
- Never blocks; missing or malformed transports degrade to status=unknown.
- Staleness thresholds are tuned to the Claude Code hook cadence — the hook
  fires on SessionStart / UserPromptSubmit / PostToolUse / Stop, so a normal
  live session re-stamps at least every few seconds during active use.
- When-needed: Open when a mission runtime, the overnight chain pre-flight,
  or the Station /meta-missions surface needs to know whether a Claude or
  Codex controller is currently alive.
- Escalates-to: tools/meta/bridge/claude_session_transport.json;
  tools/meta/bridge/codex_session_transport.json;
  .claude/hooks/runtime_hook.py;
  system/lib/meta_mission_workspace.py
- Navigation-group: meta_missions
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

CLAUDE_TRANSPORT_REL = "tools/meta/bridge/claude_session_transport.json"
CLAUDE_ACTIVE_SESSION_REL = "tools/meta/bridge/claude_active_session.json"
CODEX_TRANSPORT_REL = "tools/meta/bridge/codex_session_transport.json"

LIVE_THRESHOLD_SECONDS = 30
RECENT_THRESHOLD_SECONDS = 300
STALE_THRESHOLD_SECONDS = 1800


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_json(path: Path) -> Mapping[str, Any] | None:
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, Mapping) else None


def _classify_tone(age_seconds: float | None) -> str:
    if age_seconds is None:
        return "unknown"
    if age_seconds <= LIVE_THRESHOLD_SECONDS:
        return "live"
    if age_seconds <= RECENT_THRESHOLD_SECONDS:
        return "recent"
    if age_seconds <= STALE_THRESHOLD_SECONDS:
        return "stale"
    return "cold"


def _claude_slice(repo_root: Path, now: datetime) -> dict[str, Any]:
    active_path = repo_root / CLAUDE_ACTIVE_SESSION_REL
    transport_path = repo_root / CLAUDE_TRANSPORT_REL
    active_payload = _read_json(active_path) or {}
    transport_payload = _read_json(transport_path) or {}

    active_extras = (
        active_payload.get("extras") if isinstance(active_payload.get("extras"), Mapping) else {}
    )
    active = (
        active_extras.get("active_session")
        if isinstance(active_extras.get("active_session"), Mapping)
        else {}
    )

    stamped_at = (
        _parse_iso(active.get("last_seen_at"))
        or _parse_iso(active.get("stamped_at"))
        or _parse_iso(active.get("updated_at"))
    )
    transport_generated_at = _parse_iso(transport_payload.get("generated_at"))
    transport_consumed_at = _parse_iso(transport_payload.get("consumed_at"))
    first_seen_at = _parse_iso(active.get("first_seen_at"))

    reference = stamped_at
    age_seconds = (now - reference).total_seconds() if reference else None

    return {
        "transport_path": CLAUDE_TRANSPORT_REL,
        "active_session_path": CLAUDE_ACTIVE_SESSION_REL,
        "transport_exists": transport_path.exists(),
        "active_session_exists": active_path.exists(),
        "session_id": str(active.get("session_id") or transport_payload.get("session_id") or "") or None,
        "transcript_path": str(active.get("transcript_path") or "") or None,
        "cwd": str(active.get("cwd") or "") or None,
        "last_event": str(active.get("last_event") or active.get("event") or "") or None,
        "last_event_at": reference.isoformat() if reference else None,
        "age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
        "tone": _classify_tone(age_seconds),
        "first_seen_at": first_seen_at.isoformat() if first_seen_at else None,
        "transport_generated_at": transport_generated_at.isoformat() if transport_generated_at else None,
        "transport_consumed_at": transport_consumed_at.isoformat() if transport_consumed_at else None,
        "launch_mode": str(transport_payload.get("launch_mode") or active_payload.get("launch_mode") or "") or None,
    }


def _codex_slice(repo_root: Path, now: datetime) -> dict[str, Any]:
    path = repo_root / CODEX_TRANSPORT_REL
    payload = _read_json(path) or {}

    created_at = _parse_iso(payload.get("created_at"))
    consumed_at = _parse_iso(payload.get("consumed_at"))
    reference = created_at
    age_seconds = (now - reference).total_seconds() if reference else None

    extras = payload.get("extras") if isinstance(payload.get("extras"), Mapping) else {}

    return {
        "transport_path": CODEX_TRANSPORT_REL,
        "transport_exists": path.exists(),
        "source": str(payload.get("source") or "") or None,
        "wait_kind": str(payload.get("wait_kind") or "") or None,
        "job_id": str(payload.get("job_id_or_signal_fingerprint") or "") or None,
        "status": str(payload.get("status") or "") or None,
        "launch_mode": str(payload.get("launch_mode") or "") or None,
        "delivery_method": str(payload.get("delivery_method") or "") or None,
        "created_at": created_at.isoformat() if created_at else None,
        "consumed_at": consumed_at.isoformat() if consumed_at else None,
        "age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
        "tone": _classify_tone(age_seconds) if consumed_at is None else "consumed",
        "failure_reason": str(extras.get("failure_reason") or "") or None,
    }


def snapshot(repo_root: Path) -> dict[str, Any]:
    """Return the normalized liveness snapshot for both surfaces."""
    now = _utc_now()
    claude = _claude_slice(repo_root, now)
    codex = _codex_slice(repo_root, now)

    alive_tones = {"live", "recent"}
    any_alive = claude["tone"] in alive_tones or codex["tone"] in alive_tones

    candidate_ages = [
        slice_["age_seconds"]
        for slice_ in (claude, codex)
        if isinstance(slice_.get("age_seconds"), (int, float))
    ]
    most_recent_age = min(candidate_ages) if candidate_ages else None

    if claude["tone"] in alive_tones and not (
        codex["tone"] in alive_tones
        and isinstance(codex.get("age_seconds"), (int, float))
        and isinstance(claude.get("age_seconds"), (int, float))
        and codex["age_seconds"] < claude["age_seconds"]
    ):
        most_recent_actor = "claude_code"
    elif codex["tone"] in alive_tones:
        most_recent_actor = "codex"
    else:
        most_recent_actor = None

    return {
        "schema_version": "session_heartbeat_v1",
        "mission_id": "session_heartbeat_watch",
        "generated_at": now.isoformat(),
        "any_alive": any_alive,
        "most_recent_actor": most_recent_actor,
        "most_recent_age_seconds": most_recent_age,
        "claude_code": claude,
        "codex": codex,
        "thresholds": {
            "live_seconds": LIVE_THRESHOLD_SECONDS,
            "recent_seconds": RECENT_THRESHOLD_SECONDS,
            "stale_seconds": STALE_THRESHOLD_SECONDS,
        },
    }


def _resolve_output_path(repo_root: Path, output_path: str | None) -> Path:
    if output_path:
        candidate = Path(output_path)
        if not candidate.is_absolute():
            candidate = repo_root / candidate
        return candidate
    run_id = os.environ.get("AIWF_META_MISSION_RUN_ID")
    if run_id:
        return (
            repo_root
            / "state/meta_missions/session_heartbeat_watch/runs"
            / run_id
            / "outputs/heartbeat.json"
        )
    return (
        repo_root
        / "state/meta_missions/session_heartbeat_watch/latest_heartbeat.json"
    )


def write_snapshot(repo_root: Path, *, output_path: str | None = None) -> Path:
    """Compute a snapshot and persist it, returning the written path."""
    target = _resolve_output_path(repo_root, output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = snapshot(repo_root)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def _repo_root_from_env() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="session_heartbeat",
        description="Snapshot local Claude Code + Codex session heartbeats.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="Write one snapshot to disk and print its path.")
    snap.add_argument("--output", dest="output", default=None, help="Explicit output path (overrides workspace default).")
    snap.add_argument("--repo-root", dest="repo_root", default=None, help="Override repo root for tests.")

    show = sub.add_parser("show", help="Print the current snapshot JSON to stdout without writing it.")
    show.add_argument("--repo-root", dest="repo_root", default=None, help="Override repo root for tests.")

    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root) if args.repo_root else _repo_root_from_env()

    if args.command == "snapshot":
        written = write_snapshot(repo_root, output_path=args.output)
        print(written.as_posix())
        return 0

    if args.command == "show":
        payload = snapshot(repo_root)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
