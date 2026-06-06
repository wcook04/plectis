#!/usr/bin/env python3
"""Idle-gated Codex tab/window heartbeat.

After a real macOS HID-idle threshold, this helper focuses an already-running
Codex window and presses Command+1, Command+2, ... for active Codex thread
slots. It does not launch Codex, open windows, type into composers, submit
prompts, or use the Codex sidebar.
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
LABEL = "com.aiworkflow.codex-idle-heartbeat"
SERVICE = f"gui/{os.getuid()}/{LABEL}"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
RUNTIME_ROOT = REPO_ROOT / "state" / "autonomy_runtime" / "codex_idle_heartbeat"
STATE_PATH = RUNTIME_ROOT / "heartbeat_state.json"
LEDGER_PATH = RUNTIME_ROOT / "heartbeat_ledger.jsonl"
STDOUT_LOG = RUNTIME_ROOT / "launchd.out.log"
STDERR_LOG = RUNTIME_ROOT / "launchd.err.log"
ACTIVE_CLAIMS_PATH = REPO_ROOT / "state" / "work_ledger" / "active_claims_snapshot.json"
CODEX_STATE_DB_PATH = Path.home() / ".codex" / "state_5.sqlite"

DEFAULT_IDLE_THRESHOLD_SECONDS = 20 * 60
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 60
DEFAULT_POLL_SECONDS = 10
DEFAULT_APP_NAME = "Codex"
DEFAULT_COUNT_SOURCE = "auto"
DEFAULT_MAX_COUNT = 9
DEFAULT_KEY_DELAY_SECONDS = 0.25
DEFAULT_TRACE_REFRESH_SECONDS = 30.0
DEFAULT_SKIP_LOG_INTERVAL_SECONDS = 300.0
DEFAULT_CODEX_DB_RECENT_MINUTES = 30.0
DEFAULT_CODEX_DB_LIMIT = 9
DEFAULT_MAX_WINDOWS_TO_SWEEP = 1
ROLLOUT_OPEN_BOUNDARY_TYPES = {"task_started"}
ROLLOUT_TERMINAL_BOUNDARY_TYPES = {"task_complete", "turn_aborted"}


class HeartbeatError(RuntimeError):
    """Expected host/runtime failure that should be logged, not crash-looped."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mkdir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _mkdir(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _try_write_json(path: Path, payload: dict[str, Any]) -> str | None:
    try:
        _write_json(path, payload)
    except OSError as exc:
        return str(exc)
    return None


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    _mkdir(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _try_append_jsonl(path: Path, payload: dict[str, Any]) -> str | None:
    try:
        _append_jsonl(path, payload)
    except OSError as exc:
        return str(exc)
    return None


def _safe_stderr(message: str) -> None:
    try:
        print(message, file=sys.stderr, flush=True)
    except OSError:
        pass


def _run(
    cmd: list[str],
    *,
    input_text: str | None = None,
    timeout_s: float = 5.0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout_s,
    )


def _path_age_seconds(path: Path) -> Optional[float]:
    try:
        return max(0.0, time.time() - path.stat().st_mtime)
    except OSError:
        return None


def _parse_utc_timestamp(value: Any) -> float | None:
    token = str(value or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = token[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(token).timestamp()
    except ValueError:
        return None


def hid_idle_seconds() -> Optional[float]:
    """Return macOS HID idle seconds, or None when unavailable."""
    try:
        proc = _run(["ioreg", "-c", "IOHIDSystem"], timeout_s=3.0)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', proc.stdout)
    if not match:
        return None
    return int(match.group(1)) / 1_000_000_000.0


def refresh_active_claims_snapshot_if_stale(max_age_seconds: float) -> dict[str, Any]:
    age = _path_age_seconds(ACTIVE_CLAIMS_PATH)
    if age is not None and age <= max_age_seconds:
        return {"status": "fresh", "age_seconds": age, "refreshed": False}
    cmd = [
        str(REPO_ROOT / "repo-python"),
        str(REPO_ROOT / "tools" / "meta" / "factory" / "work_ledger.py"),
        "session-claims",
        "--refresh",
        "--limit",
        "50",
        "--cards-only",
    ]
    proc = _run(cmd, timeout_s=20.0)
    return {
        "status": "refreshed" if proc.returncode == 0 else "refresh_failed",
        "age_seconds": age,
        "refreshed": proc.returncode == 0,
        "returncode": proc.returncode,
        "stderr": (proc.stderr or "").strip()[:500],
    }


def _apple_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def codex_window_count(app_name: str = DEFAULT_APP_NAME) -> dict[str, Any]:
    script = "\n".join(
        [
            'tell application "System Events"',
            f"  if exists process {_apple_string(app_name)} then",
            f"    tell process {_apple_string(app_name)}",
            "      set totalWindowCount to count windows",
            "      set standardWindowCount to 0",
            "      set modalWindowCount to 0",
            "      set sheetWindowCount to 0",
            "      set nonstandardWindowCount to 0",
            "      repeat with candidateWindow in windows",
            '        set roleToken to ""',
            '        set subroleToken to ""',
            "        set modalWindow to false",
            "        set candidateSheetCount to 0",
            "        try",
            "          set roleToken to role of candidateWindow as text",
            "        end try",
            "        try",
            "          set subroleToken to subrole of candidateWindow as text",
            "        end try",
            "        try",
            '          set modalWindow to value of attribute "AXModal" of candidateWindow',
            "        end try",
            "        try",
            "          set candidateSheetCount to count sheets of candidateWindow",
            "        end try",
            "        if modalWindow is true then set modalWindowCount to modalWindowCount + 1",
            "        if candidateSheetCount > 0 then set sheetWindowCount to sheetWindowCount + candidateSheetCount",
            '        if roleToken is "AXWindow" and (subroleToken is "" or subroleToken is "AXStandardWindow") then',
            "          set standardWindowCount to standardWindowCount + 1",
            "        else",
            "          set nonstandardWindowCount to nonstandardWindowCount + 1",
            "        end if",
            "      end repeat",
            '      return (totalWindowCount as text) & tab & (standardWindowCount as text) & tab & (modalWindowCount as text) & tab & (sheetWindowCount as text) & tab & (nonstandardWindowCount as text)',
            "    end tell",
            "  else",
            '    return "0\t0\t0\t0\t0"',
            "  end if",
            "end tell",
        ]
    )
    proc = _run(["osascript", "-"], input_text=script, timeout_s=8.0)
    parsed = _parse_window_count_stdout(proc.stdout if proc.returncode == 0 else "")
    return {
        **parsed,
        "ok": proc.returncode == 0,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "returncode": proc.returncode,
    }


def _parse_window_count_stdout(stdout: str) -> dict[str, Any]:
    token = (stdout or "").strip()
    if not token:
        return {
            "count": 0,
            "raw_count": 0,
            "standard_window_count": 0,
            "modal_window_count": 0,
            "sheet_count": 0,
            "nonstandard_window_count": 0,
            "blocking_overlay_present": False,
        }
    parts = token.split("\t")

    def int_part(index: int) -> int:
        try:
            return max(0, int(str(parts[index]).strip() or "0"))
        except (IndexError, ValueError):
            return 0

    if len(parts) == 1:
        raw_count = int_part(0)
        return {
            "count": raw_count,
            "raw_count": raw_count,
            "standard_window_count": raw_count,
            "modal_window_count": 0,
            "sheet_count": 0,
            "nonstandard_window_count": 0,
            "blocking_overlay_present": False,
        }
    raw_count = int_part(0)
    standard_count = int_part(1)
    modal_count = int_part(2)
    sheet_count = int_part(3)
    nonstandard_count = int_part(4)
    blocking_overlay_present = bool(modal_count or sheet_count or (raw_count > 0 and standard_count <= 0))
    return {
        "count": standard_count,
        "raw_count": raw_count,
        "standard_window_count": standard_count,
        "modal_window_count": modal_count,
        "sheet_count": sheet_count,
        "nonstandard_window_count": nonstandard_count,
        "blocking_overlay_present": blocking_overlay_present,
    }


def active_codex_thread_count_from_trace(*, refresh_max_age_seconds: float) -> dict[str, Any]:
    refresh = refresh_active_claims_snapshot_if_stale(refresh_max_age_seconds)
    data = _load_json(ACTIVE_CLAIMS_PATH)
    claims = data.get("active_claims") if isinstance(data.get("active_claims"), list) else []
    session_ids: set[str] = set()
    claim_ids: list[str] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        if str(claim.get("actor") or "").strip().lower() != "codex":
            continue
        session_id = str(claim.get("session_id") or "").strip()
        if not session_id:
            continue
        session_ids.add(session_id)
        claim_id = str(claim.get("claim_id") or "").strip()
        if claim_id:
            claim_ids.append(claim_id)
    return {
        "count": len(session_ids),
        "source": str(ACTIVE_CLAIMS_PATH.relative_to(REPO_ROOT)),
        "session_ids": sorted(session_ids),
        "claim_ids": claim_ids,
        "generated_at": data.get("generated_at"),
        "refresh": refresh,
    }


def _skipped_trace(reason: str) -> dict[str, Any]:
    return {
        "count": 0,
        "source": str(ACTIVE_CLAIMS_PATH.relative_to(REPO_ROOT)),
        "session_ids": [],
        "claim_ids": [],
        "generated_at": None,
        "refresh": {
            "status": "skipped",
            "refreshed": False,
            "reason": reason,
        },
    }


def _thread_id_set(values: list[str] | None) -> set[str]:
    result: set[str] = set()
    for value in values or []:
        for token in str(value or "").split(","):
            token = token.strip()
            if token:
                result.add(token)
    return result


def codex_db_recent_thread_slots(
    *,
    cwd: Path,
    recent_minutes: float,
    limit: int,
) -> dict[str, Any]:
    """Return recently active Codex desktop thread slots for this repo cwd.

    This mirrors the Command-number sidebar behavior better than Work Ledger:
    Command+N selects a visible recent project thread slot, while Work Ledger
    only tracks claimed work sessions.
    """
    db_path = CODEX_STATE_DB_PATH
    if not db_path.exists():
        return {"ok": False, "count": 0, "reason": "codex_state_db_missing", "db_path": str(db_path)}
    cutoff_ms = int((time.time() - max(0.0, float(recent_minutes)) * 60.0) * 1000)
    max_rows = max(1, min(int(limit), 9))
    query = """
        SELECT
            id,
            title,
            cwd,
            archived,
            COALESCE(updated_at_ms, updated_at * 1000, created_at_ms, created_at * 1000) AS updated_ms
        FROM threads
        WHERE cwd = ?
          AND archived = 0
          AND COALESCE(updated_at_ms, updated_at * 1000, created_at_ms, created_at * 1000) >= ?
        ORDER BY COALESCE(updated_at_ms, updated_at * 1000, created_at_ms, created_at * 1000) DESC
        LIMIT ?
    """
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, (str(cwd), cutoff_ms, max_rows)).fetchall()
    except Exception as exc:
        return {
            "ok": False,
            "count": 0,
            "reason": "codex_state_db_query_failed",
            "error": str(exc),
            "db_path": str(db_path),
        }
    finally:
        if conn is not None:
            conn.close()
    threads: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        title = str(row["title"] or "").replace("\n", " ").replace("\r", " ").strip()
        updated_ms = int(row["updated_ms"] or 0)
        threads.append(
            {
                "slot": index,
                "thread_id": str(row["id"]),
                "title_preview": title[:80],
                "updated_at": datetime.fromtimestamp(updated_ms / 1000.0, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if updated_ms
                else None,
                "age_seconds": round(max(0.0, time.time() - updated_ms / 1000.0), 3) if updated_ms else None,
            }
        )
    return {
        "ok": True,
        "count": len(threads),
        "source": str(db_path),
        "cwd": str(cwd),
        "recent_minutes": float(recent_minutes),
        "limit": max_rows,
        "threads": threads,
    }


def codex_db_project_thread_slots(
    *,
    cwd: Path,
    limit: int,
) -> dict[str, Any]:
    """Return top visible Codex project slots for this repo cwd."""
    db_path = CODEX_STATE_DB_PATH
    if not db_path.exists():
        return {"ok": False, "count": 0, "reason": "codex_state_db_missing", "db_path": str(db_path)}
    max_rows = max(1, min(int(limit), 9))
    query = """
        SELECT
            id,
            title,
            cwd,
            rollout_path,
            archived,
            COALESCE(updated_at_ms, updated_at * 1000, created_at_ms, created_at * 1000) AS updated_ms
        FROM threads
        WHERE cwd = ?
          AND archived = 0
        ORDER BY COALESCE(updated_at_ms, updated_at * 1000, created_at_ms, created_at * 1000) DESC
        LIMIT ?
    """
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, (str(cwd), max_rows)).fetchall()
    except Exception as exc:
        return {
            "ok": False,
            "count": 0,
            "reason": "codex_state_db_query_failed",
            "error": str(exc),
            "db_path": str(db_path),
        }
    finally:
        if conn is not None:
            conn.close()
    threads: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        title = str(row["title"] or "").replace("\n", " ").replace("\r", " ").strip()
        updated_ms = int(row["updated_ms"] or 0)
        threads.append(
            {
                "slot": index,
                "thread_id": str(row["id"]),
                "rollout_path": str(row["rollout_path"] or ""),
                "title_preview": title[:80],
                "updated_at": datetime.fromtimestamp(updated_ms / 1000.0, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if updated_ms
                else None,
                "age_seconds": round(max(0.0, time.time() - updated_ms / 1000.0), 3) if updated_ms else None,
            }
        )
    return {
        "ok": True,
        "count": len(threads),
        "source": str(db_path),
        "cwd": str(cwd),
        "limit": max_rows,
        "threads": threads,
    }


def rollout_open_turn_summary(path_token: str) -> dict[str, Any]:
    path = Path(path_token).expanduser() if path_token else Path()
    if not path_token or not path.is_file():
        return {
            "available": False,
            "path": path_token,
            "event_count": 0,
            "open_turn_ids": [],
            "open_turn_count": 0,
            "last_boundary_type": "",
            "last_boundary_turn_id": "",
        }
    pending_turn_id: str | None = None
    orphan_turn_ids: list[str] = []
    terminal_turn_ids: list[str] = []
    last_boundary_type = ""
    last_boundary_turn_id = ""
    event_count = 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
                event_type = str(payload.get("type") or event.get("type") or "").strip()
                turn_id = str(payload.get("turn_id") or event.get("turn_id") or "").strip()
                event_count += 1
                if event_type in ROLLOUT_OPEN_BOUNDARY_TYPES and turn_id:
                    if pending_turn_id and pending_turn_id != turn_id:
                        orphan_turn_ids.append(pending_turn_id)
                    pending_turn_id = turn_id
                    last_boundary_type = event_type
                    last_boundary_turn_id = turn_id
                elif event_type in ROLLOUT_TERMINAL_BOUNDARY_TYPES:
                    if turn_id and pending_turn_id == turn_id:
                        pending_turn_id = None
                    elif pending_turn_id:
                        orphan_turn_ids.append(pending_turn_id)
                        pending_turn_id = None
                    elif turn_id:
                        try:
                            orphan_turn_ids.remove(turn_id)
                        except ValueError:
                            pass
                    if turn_id:
                        terminal_turn_ids.append(turn_id)
                    last_boundary_type = event_type
                    last_boundary_turn_id = turn_id
    except OSError as exc:
        return {
            "available": False,
            "path": str(path),
            "event_count": event_count,
            "open_turn_ids": [],
            "open_turn_count": 0,
            "last_boundary_type": "",
            "last_boundary_turn_id": "",
            "error": str(exc),
        }
    open_turn_ids = [pending_turn_id] if pending_turn_id and last_boundary_type in ROLLOUT_OPEN_BOUNDARY_TYPES else []
    return {
        "available": True,
        "path": str(path),
        "event_count": event_count,
        "open_turn_ids": open_turn_ids,
        "open_turn_count": len(open_turn_ids),
        "terminal_turn_ids": terminal_turn_ids[-8:],
        "orphan_turn_ids": orphan_turn_ids[-8:],
        "last_boundary_type": last_boundary_type,
        "last_boundary_turn_id": last_boundary_turn_id,
    }


def codex_live_rollout_thread_slots(
    *,
    cwd: Path,
    limit: int,
    exclude_thread_ids: set[str] | None = None,
) -> dict[str, Any]:
    project_slots = codex_db_project_thread_slots(cwd=cwd, limit=limit)
    if not project_slots.get("ok"):
        return {
            "ok": False,
            "count": 0,
            "reason": project_slots.get("reason") or "codex_project_slots_unavailable",
            "project_slots": project_slots,
            "threads": [],
            "selected_slot_numbers": [],
        }
    excluded = {token for token in (exclude_thread_ids or set()) if token}
    threads: list[dict[str, Any]] = []
    selected_slot_numbers: list[int] = []
    for thread in project_slots.get("threads", []):
        if not isinstance(thread, dict):
            continue
        summary = rollout_open_turn_summary(str(thread.get("rollout_path") or ""))
        item = {**thread, "rollout": summary}
        thread_id = str(item.get("thread_id") or "")
        is_excluded = thread_id in excluded
        item["excluded"] = is_excluded
        item["running"] = bool(summary.get("open_turn_count")) and not is_excluded
        if item["running"]:
            selected_slot_numbers.append(int(item["slot"]))
        threads.append(item)
    return {
        "ok": True,
        "count": len(selected_slot_numbers),
        "source": "codex_rollout_open_turns",
        "cwd": str(cwd),
        "limit": int(project_slots.get("limit") or limit),
        "scanned_count": int(project_slots.get("count") or 0),
        "excluded_thread_ids": sorted(excluded),
        "selected_slot_numbers": selected_slot_numbers,
        "threads": threads,
    }


def _factorial(value: int) -> int:
    result = 1
    for item in range(2, max(0, int(value)) + 1):
        result *= item
    return result


def _permutation_preview(session_ids: list[str], slot_numbers: list[int]) -> list[dict[str, Any]]:
    if not slot_numbers:
        return []
    if len(session_ids) != len(slot_numbers) or len(slot_numbers) > 3:
        return []
    if len(slot_numbers) == 1:
        return [{"mapping": {session_ids[0]: slot_numbers[0]}}]
    if len(slot_numbers) == 2:
        a, b = session_ids
        one, two = slot_numbers
        return [{"mapping": {a: one, b: two}}, {"mapping": {a: two, b: one}}]
    a, b, c = session_ids
    one, two, three = slot_numbers
    return [
        {"mapping": {a: one, b: two, c: three}},
        {"mapping": {a: one, b: three, c: two}},
        {"mapping": {a: two, b: one, c: three}},
        {"mapping": {a: two, b: three, c: one}},
        {"mapping": {a: three, b: one, c: two}},
        {"mapping": {a: three, b: two, c: one}},
    ]


def tab_permutation_model(
    *,
    count: int,
    raw_count: int,
    source: str,
    trace: dict[str, Any],
    windows: dict[str, Any],
    codex_db_recent: dict[str, Any],
    codex_live_rollout: dict[str, Any],
    max_count: int,
    max_windows_to_sweep: int,
    selected_slot_numbers: list[int] | None = None,
) -> dict[str, Any]:
    trace_count = int(trace.get("count") or 0)
    db_count = int(codex_db_recent.get("count") or 0)
    live_count = int(codex_live_rollout.get("count") or 0)
    window_count = int(windows.get("count") or 0)
    windows_to_sweep = max(0, min(max(0, window_count), max(1, int(max_windows_to_sweep))))
    return_window_switches = max(0, window_count - windows_to_sweep + 1) if window_count > 1 and windows_to_sweep > 1 else 0
    windows_ok = bool(windows.get("ok"))
    blocking_overlay_present = bool(windows.get("blocking_overlay_present"))
    trace_sources = {"trace", "auto_trace"}
    live_sources = {"auto_codex_live_rollout", "codex_live_rollout"}
    db_sources = {"auto_codex_db_recent", "codex_db_recent"}
    window_fallback_sources = {"windows_fallback", "auto_windows_fallback"}
    if source in live_sources:
        session_ids = [
            str(item.get("thread_id") or item.get("title_preview") or item.get("slot"))
            for item in codex_live_rollout.get("threads", [])
            if isinstance(item, dict) and item.get("running")
        ]
    elif source in db_sources:
        session_ids = [
            str(item.get("thread_id") or item.get("title_preview") or item.get("slot"))
            for item in codex_db_recent.get("threads", [])
            if isinstance(item, dict)
        ]
    else:
        session_ids = [str(item) for item in trace.get("session_ids", []) if str(item).strip()]
    if selected_slot_numbers is None:
        slot_numbers = list(range(1, max(0, int(count)) + 1))
    else:
        slot_numbers = [slot for slot in selected_slot_numbers if 1 <= int(slot) <= 9]

    risks: list[str] = []
    effective_slot_numbers = slot_numbers
    if not windows_ok or (window_count <= 0 and not blocking_overlay_present):
        current_case = "no_open_codex_window"
        alignment = "blocked_no_window"
        coverage = "no_keypress_safe_skip"
        effective_slot_numbers = []
        risks.append("Codex is not visible to System Events, so the heartbeat must skip instead of launching or opening a window.")
    elif blocking_overlay_present:
        current_case = "codex_window_blocking_overlay_present"
        alignment = "blocked_overlay_or_modal"
        coverage = "no_keypress_safe_skip"
        effective_slot_numbers = []
        risks.append("Codex has a modal, sheet, or nonstandard-only window surface; heartbeat skips rather than sending Command-number into an overlay.")
    elif source in trace_sources and window_count == 1 and trace_count == count == 1:
        current_case = "single_window_single_active_trace"
        alignment = "aligned"
        coverage = "slot_1_is_visited"
    elif source in trace_sources and window_count == 1 and trace_count == count and count > 1:
        current_case = "single_window_multi_active_trace"
        alignment = "aligned_by_positional_sweep"
        coverage = "all_trace_thread_to_tab_position_permutations_are_covered"
    elif source in trace_sources and window_count > 1 and trace_count == count:
        current_case = "multi_window_trace_count"
        if window_count <= max_windows_to_sweep:
            alignment = "aligned_by_multi_window_positional_sweep"
            coverage = "front_window_tab_permutations_are_covered_across_all_open_windows"
        else:
            alignment = "partially_aligned_window_cap_exceeded"
            coverage = "front_window_tab_permutations_are_covered_for_swept_windows"
            risks.append("Codex window count exceeds max_windows_to_sweep; some windows will not be visited.")
    elif source in live_sources and window_count == 1:
        current_case = "single_window_live_rollout_open_turn_slots"
        alignment = "aligned_to_rollout_open_turn_slots"
        coverage = "only_slots_with_open_rollout_turns_are_visited"
    elif source in live_sources and window_count > 1:
        current_case = "multi_window_live_rollout_open_turn_slots"
        if window_count <= max_windows_to_sweep:
            alignment = "aligned_by_multi_window_live_slot_sweep"
            coverage = "open_rollout_turn_slots_are_visited_across_all_open_windows"
        else:
            alignment = "partially_aligned_window_cap_exceeded"
            coverage = "open_rollout_turn_slots_are_visited_for_swept_windows"
            risks.append("Codex window count exceeds max_windows_to_sweep; some windows will not be visited.")
    elif source in db_sources and window_count == 1 and db_count == count and count >= 1:
        current_case = "single_window_recent_project_thread_slots"
        alignment = "aligned_to_codex_db_recent_project_slots"
        coverage = "all_recent_project_thread_to_visible_slot_permutations_are_covered"
        if trace_count and trace_count != db_count:
            risks.append(
                "Work Ledger active-trace count differs from Codex desktop recent-thread slots; using Codex DB slots because Command-number targets the UI slot list."
            )
    elif source in db_sources and window_count > 1 and db_count == count and count >= 1:
        current_case = "multi_window_recent_project_thread_slots"
        if window_count <= max_windows_to_sweep:
            alignment = "aligned_by_multi_window_positional_sweep"
            coverage = "recent_project_slot_permutations_are_covered_across_all_open_windows"
        else:
            alignment = "partially_aligned_window_cap_exceeded"
            coverage = "recent_project_slot_permutations_are_covered_for_swept_windows"
            risks.append("Codex window count exceeds max_windows_to_sweep; some windows will not be visited.")
    elif source in window_fallback_sources:
        current_case = "trace_unavailable_window_fallback"
        alignment = "degraded_window_count_fallback"
        coverage = "slot_positions_are_swept_without_thread_identity"
        risks.append("Live trace reported zero active sessions, so the count comes from Codex window visibility rather than thread identity.")
    elif source == "windows":
        current_case = "explicit_window_count_mode"
        alignment = "operator_selected_window_count_mode"
        coverage = "slot_positions_are_swept_without_thread_identity"
        risks.append("Window count is not the same contract as front-window tab count.")
    elif source == "fixed":
        current_case = "explicit_fixed_count_mode"
        alignment = "operator_selected_fixed_count_mode"
        coverage = "fixed_slot_positions_are_swept"
    else:
        current_case = "count_source_ambiguous"
        alignment = "watch"
        coverage = "slot_positions_are_swept_best_effort"
        risks.append("Count source did not match a known aligned case.")

    if trace_count > int(max_count):
        risks.append("Trace count exceeds max_count; only the first max_count positional slots are swept.")

    modeled_permutation_count: int | None = None
    if effective_slot_numbers and source in trace_sources and trace_count == count and count >= 0:
        modeled_permutation_count = _factorial(count)
    if effective_slot_numbers and source in live_sources and live_count == count and count >= 0:
        modeled_permutation_count = _factorial(count)
    if effective_slot_numbers and source in db_sources and db_count == count and count >= 0:
        modeled_permutation_count = _factorial(count)

    return {
        "schema": "codex_idle_heartbeat_tab_permutation_model_v1",
        "current_case": current_case,
        "alignment": alignment,
        "coverage": coverage,
        "trace_count": trace_count,
        "codex_db_recent_count": db_count,
        "codex_live_rollout_count": live_count,
        "window_count": window_count,
        "raw_window_count": int(windows.get("raw_count") or window_count),
        "standard_window_count": int(windows.get("standard_window_count") or window_count),
        "blocking_overlay_present": blocking_overlay_present,
        "windows_to_sweep": windows_to_sweep,
        "return_window_switches": return_window_switches,
        "max_windows_to_sweep": int(max_windows_to_sweep),
        "count_source": source,
        "raw_count": int(raw_count),
        "selected_slot_numbers": effective_slot_numbers,
        "selected_key_sequence": [str(slot) for slot in effective_slot_numbers],
        "modeled_permutation_count": modeled_permutation_count,
        "permutation_policy": "thread_identity_is_not_assumed; every selected positional slot is visited from 1 through N",
        "permutations_preview": _permutation_preview(session_ids, effective_slot_numbers),
        "risks": risks,
    }


def resolve_cycle_count(
    *,
    count_source: str,
    fixed_count: int,
    max_count: int,
    app_name: str,
    trace_refresh_seconds: float,
    codex_db_recent_minutes: float,
    codex_db_limit: int,
    codex_db_cwd: Path,
    max_windows_to_sweep: int,
    exclude_thread_ids: set[str] | None = None,
) -> dict[str, Any]:
    source = str(count_source or DEFAULT_COUNT_SOURCE).strip().lower()
    windows = codex_window_count(app_name)
    trace = _skipped_trace("not_needed_for_primary_count_source")
    db_recent = {"ok": False, "count": 0, "reason": "skipped_for_count_source"}
    live_rollout = {"ok": False, "count": 0, "reason": "skipped_for_count_source", "selected_slot_numbers": []}
    if source in {"auto", "codex_live_rollout"}:
        live_rollout = codex_live_rollout_thread_slots(
            cwd=codex_db_cwd,
            limit=min(int(max_count), int(codex_db_limit)),
            exclude_thread_ids=exclude_thread_ids,
        )
    if source in {"auto", "codex_db_recent"}:
        db_recent = codex_db_recent_thread_slots(
            cwd=codex_db_cwd,
            recent_minutes=codex_db_recent_minutes,
            limit=min(int(max_count), int(codex_db_limit)),
        )
    selected_slots: list[int] | None = None
    if source == "fixed":
        raw_count = fixed_count
        selected_source = "fixed"
    elif source == "windows":
        raw_count = int(windows.get("count") or 0)
        selected_source = "windows"
    elif source == "codex_live_rollout":
        selected_slots = [int(slot) for slot in live_rollout.get("selected_slot_numbers", [])]
        raw_count = len(selected_slots)
        selected_source = "codex_live_rollout"
    elif source == "codex_db_recent":
        raw_count = int(db_recent.get("count") or 0)
        selected_source = "codex_db_recent"
    elif source == "trace":
        trace = active_codex_thread_count_from_trace(refresh_max_age_seconds=trace_refresh_seconds)
        raw_count = int(trace.get("count") or 0)
        selected_source = "trace"
        if raw_count <= 0:
            raw_count = int(windows.get("count") or 0)
            selected_source = "windows_fallback"
    else:
        if live_rollout.get("ok") and int(live_rollout.get("count") or 0) > 0:
            selected_slots = [int(slot) for slot in live_rollout.get("selected_slot_numbers", [])]
            raw_count = len(selected_slots)
            selected_source = "auto_codex_live_rollout"
        else:
            trace = active_codex_thread_count_from_trace(refresh_max_age_seconds=trace_refresh_seconds)
            raw_count = int(trace.get("count") or 0)
            selected_source = "auto_trace"
            if raw_count <= 0 and bool(db_recent.get("ok")) and int(db_recent.get("count") or 0) > 0:
                raw_count = int(db_recent.get("count") or 0)
                selected_source = "auto_codex_db_recent"
            if raw_count <= 0:
                raw_count = int(windows.get("count") or 0)
                selected_source = "auto_windows_fallback"
    count = max(0, min(int(max_count), int(raw_count)))
    if selected_slots is not None:
        selected_slots = [slot for slot in selected_slots if 1 <= int(slot) <= 9][:count]
    return {
        "count": count,
        "raw_count": raw_count,
        "source": selected_source,
        "trace": trace,
        "codex_db_recent": db_recent,
        "codex_live_rollout": live_rollout,
        "windows": windows,
        "max_count": int(max_count),
        "selected_slot_numbers": selected_slots or list(range(1, count + 1)),
        "fallback_chain": [
            {"source": "codex_live_rollout", "ok": bool(live_rollout.get("ok")), "count": int(live_rollout.get("count") or 0)},
            {"source": "trace", "count": int(trace.get("count") or 0)},
            {"source": "codex_db_recent", "ok": bool(db_recent.get("ok")), "count": int(db_recent.get("count") or 0)},
            {"source": "windows", "ok": bool(windows.get("ok")), "count": int(windows.get("count") or 0)},
        ],
        "tab_permutation_model": tab_permutation_model(
            count=count,
            raw_count=raw_count,
            source=selected_source,
            trace=trace,
            windows=windows,
            codex_db_recent=db_recent,
            codex_live_rollout=live_rollout,
            max_count=int(max_count),
            max_windows_to_sweep=int(max_windows_to_sweep),
            selected_slot_numbers=selected_slots,
        ),
    }


def _looks_like_own_heartbeat_idle(
    *,
    state: dict[str, Any],
    now: float,
    idle_seconds: Optional[float],
    idle_threshold_seconds: float,
    key_delay_seconds: float,
    max_count: int,
) -> bool:
    if idle_seconds is None or idle_seconds >= idle_threshold_seconds:
        return False
    if not bool(state.get("armed")):
        return False
    last_tick_at = float(state.get("last_tick_at") or 0.0)
    if last_tick_at <= 0.0:
        return False
    expected_idle_seconds = max(0.0, now - last_tick_at)
    sequence_tolerance_seconds = max(5.0, float(key_delay_seconds) * max(1, int(max_count)) + 3.0)
    return abs(expected_idle_seconds - float(idle_seconds)) <= sequence_tolerance_seconds


def _idle_gate_state(
    *,
    state: dict[str, Any],
    now: float,
    idle_seconds: Optional[float],
    idle_threshold_seconds: float,
    key_delay_seconds: float,
    max_count: int,
) -> dict[str, Any]:
    user_idle_gate_open = None if idle_seconds is None else float(idle_seconds) >= float(idle_threshold_seconds)
    synthetic_idle_continuation = _looks_like_own_heartbeat_idle(
        state=state,
        now=now,
        idle_seconds=idle_seconds,
        idle_threshold_seconds=idle_threshold_seconds,
        key_delay_seconds=key_delay_seconds,
        max_count=max_count,
    )
    heartbeat_gate_open = bool(user_idle_gate_open) or synthetic_idle_continuation
    if idle_seconds is None:
        gate_reason = "hid_idle_unavailable"
    elif bool(user_idle_gate_open):
        gate_reason = "user_idle_threshold_met"
    elif synthetic_idle_continuation:
        gate_reason = "synthetic_heartbeat_continuation"
    else:
        gate_reason = "not_idle"
    return {
        "user_idle_gate_open": user_idle_gate_open,
        "heartbeat_gate_open": heartbeat_gate_open,
        "idle_gate_reason": gate_reason,
        "synthetic_idle_continuation": synthetic_idle_continuation,
    }


def press_command_numbers(
    *,
    app_name: str,
    count: int,
    slot_numbers: list[int] | None,
    window_count: int,
    max_windows_to_sweep: int,
    key_delay_seconds: float,
    dry_run: bool,
) -> dict[str, Any]:
    if slot_numbers is None:
        slots = list(range(1, max(0, min(count, 9)) + 1))
    else:
        slots = [int(slot) for slot in slot_numbers if 1 <= int(slot) <= 9][: max(0, int(count))]
    keys = [str(slot) for slot in slots]
    visible_windows = max(0, int(window_count))
    windows_to_sweep = min(visible_windows, max(1, int(max_windows_to_sweep)))
    return_window_switches = (
        max(0, visible_windows - windows_to_sweep + 1) if visible_windows > 1 and windows_to_sweep > 1 else 0
    )
    sweep_plan = [{"window_index": index, "keys": keys} for index in range(1, windows_to_sweep + 1)]
    if dry_run or not keys:
        return {
            "status": "dry_run" if dry_run else "skipped",
            "keys": keys,
            "windows_to_sweep": windows_to_sweep,
            "return_window_switches": return_window_switches,
            "sweep_plan": sweep_plan,
            "returncode": None,
        }
    key_lines: list[str] = []
    for window_index in range(1, windows_to_sweep + 1):
        for key in keys:
            key_lines.append(f"  keystroke {_apple_string(key)} using command down")
            key_lines.append(f"  delay {max(0.0, float(key_delay_seconds)):.3f}")
        if window_index < windows_to_sweep:
            key_lines.append("  key code 50 using command down")
            key_lines.append("  delay 0.300")
    for _ in range(return_window_switches):
        key_lines.append("  key code 50 using command down")
        key_lines.append("  delay 0.300")
    estimated_delay = (
        0.25
        + windows_to_sweep * len(keys) * max(0.0, float(key_delay_seconds))
        + (max(0, windows_to_sweep - 1) + return_window_switches) * 0.300
    )
    script = "\n".join(
        [
            'tell application "System Events"',
            f"  if not (exists process {_apple_string(app_name)}) then error {_apple_string(app_name + ' is not running')}",
            f"  tell process {_apple_string(app_name)}",
            "    if (count windows) = 0 then error \"Codex has no visible windows\"",
            '    set blockingWindowReason to ""',
            "    repeat with candidateWindow in windows",
            "      set modalWindow to false",
            "      set candidateSheetCount to 0",
            "      try",
            '        set modalWindow to value of attribute "AXModal" of candidateWindow',
            "      end try",
            "      try",
            "        set candidateSheetCount to count sheets of candidateWindow",
            "      end try",
            '      if modalWindow is true then set blockingWindowReason to "Codex has a modal window; heartbeat skipped"',
            '      if candidateSheetCount > 0 then set blockingWindowReason to "Codex has an open sheet; heartbeat skipped"',
            "    end repeat",
            '    if blockingWindowReason is not "" then error blockingWindowReason',
            "    set frontmost to true",
            "  end tell",
            "  delay 0.250",
            *key_lines,
            "end tell",
        ]
    )
    proc = _run(["osascript", "-"], input_text=script, timeout_s=max(10.0, estimated_delay + 5.0))
    if proc.returncode != 0:
        raise HeartbeatError((proc.stderr or proc.stdout or "osascript command-number heartbeat failed").strip())
    return {
        "status": "sent",
        "keys": keys,
        "windows_to_sweep": windows_to_sweep,
        "return_window_switches": return_window_switches,
        "sweep_plan": sweep_plan,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }


def _heartbeat_once(
    *,
    idle_threshold_seconds: float,
    heartbeat_interval_seconds: float,
    app_name: str,
    count_source: str,
    fixed_count: int,
    max_count: int,
    key_delay_seconds: float,
    trace_refresh_seconds: float,
    codex_db_recent_minutes: float,
    codex_db_limit: int,
    codex_db_cwd: Path,
    max_windows_to_sweep: int,
    exclude_thread_ids: set[str] | None,
    dry_run: bool,
    force: bool,
    record_state: bool,
) -> dict[str, Any]:
    now = time.time()
    idle_seconds = hid_idle_seconds()
    state = _load_json(STATE_PATH)
    base: dict[str, Any] = {
        "kind": "codex_idle_heartbeat_tick",
        "timestamp": _utc_now(),
        "idle_seconds": idle_seconds,
        "idle_threshold_seconds": idle_threshold_seconds,
        "heartbeat_interval_seconds": heartbeat_interval_seconds,
        "app_name": app_name,
        "count_source": count_source,
        "dry_run": dry_run,
        "force": force,
    }
    gate = _idle_gate_state(
        state=state,
        now=now,
        idle_seconds=idle_seconds,
        idle_threshold_seconds=idle_threshold_seconds,
        key_delay_seconds=key_delay_seconds,
        max_count=max_count,
    )
    base.update(gate)
    if idle_seconds is None and not force:
        base.update({"status": "skipped", "reason": "hid_idle_unavailable"})
        return base
    if not force and not bool(gate.get("heartbeat_gate_open")):
        state.update(
            {
                "armed": False,
                "last_seen_not_idle_at": _utc_now(),
                "last_idle_seconds": idle_seconds,
                "last_status": "skipped",
                "last_reason": "not_idle",
            }
        )
        state.pop("last_error", None)
        state_write_error = _try_write_json(STATE_PATH, state)
        base.update({"status": "skipped", "reason": "not_idle"})
        if state_write_error:
            base["state_write_error"] = state_write_error
        return base
    last_tick_at = float(state.get("last_tick_at") or 0.0)
    if not force and last_tick_at and now - last_tick_at < heartbeat_interval_seconds:
        base.update(
            {
                "status": "skipped",
                "reason": "interval_not_elapsed",
                "seconds_until_next": round(heartbeat_interval_seconds - (now - last_tick_at), 3),
            }
        )
        return base

    try:
        cycle = resolve_cycle_count(
            count_source=count_source,
            fixed_count=fixed_count,
            max_count=max_count,
            app_name=app_name,
            trace_refresh_seconds=trace_refresh_seconds,
            codex_db_recent_minutes=codex_db_recent_minutes,
            codex_db_limit=codex_db_limit,
            codex_db_cwd=codex_db_cwd,
            max_windows_to_sweep=max_windows_to_sweep,
            exclude_thread_ids=exclude_thread_ids,
        )
        count = int(cycle.get("count") or 0)
        if count <= 0:
            base.update({"status": "skipped", "reason": "no_active_codex_threads", "cycle_count": cycle})
            return base
        windows = cycle.get("windows") if isinstance(cycle.get("windows"), dict) else {}
        window_count = int(windows.get("count") or 0)
        if bool(windows.get("blocking_overlay_present")):
            base.update(
                {
                    "status": "skipped",
                    "reason": "codex_window_blocking_overlay_present",
                    "cycle_count": cycle,
                }
            )
            return base
        if not bool(windows.get("ok")) or window_count <= 0:
            base.update(
                {
                    "status": "skipped",
                    "reason": "codex_window_unavailable",
                    "cycle_count": cycle,
                }
            )
            return base
        sent = press_command_numbers(
            app_name=app_name,
            count=count,
            slot_numbers=cycle.get("selected_slot_numbers") if isinstance(cycle.get("selected_slot_numbers"), list) else None,
            window_count=window_count,
            max_windows_to_sweep=max_windows_to_sweep,
            key_delay_seconds=key_delay_seconds,
            dry_run=dry_run,
        )
        if not dry_run and record_state:
            state.update(
                {
                    "armed": True,
                    "last_tick_at": now,
                    "last_tick_iso": _utc_now(),
                    "last_status": "heartbeat_sent",
                    "last_reason": None,
                    "last_idle_seconds": idle_seconds,
                    "last_count": count,
                    "last_keys": sent.get("keys"),
                    "last_windows_swept": sent.get("windows_to_sweep"),
                    "last_return_window_switches": sent.get("return_window_switches"),
                }
            )
            state.pop("last_error", None)
            state_write_error = _try_write_json(STATE_PATH, state)
        else:
            state_write_error = None
        base.update(
            {
                "status": "dry_run" if dry_run else "heartbeat_sent",
                "reason": None,
                "cycle_count": cycle,
                "keys": sent.get("keys"),
                "windows_swept": sent.get("windows_to_sweep"),
                "return_window_switches": sent.get("return_window_switches"),
                "sweep_plan": sent.get("sweep_plan"),
                "action": "command_number_sequence",
            }
        )
        if state_write_error:
            base["state_write_error"] = state_write_error
        return base
    except Exception as exc:
        state.update(
            {
                "armed": True,
                "last_tick_at": now,
                "last_tick_iso": _utc_now(),
                "last_status": "failed",
                "last_reason": str(exc),
                "last_error": str(exc),
                "last_idle_seconds": idle_seconds,
            }
        )
        state_write_error = _try_write_json(STATE_PATH, state)
        base.update({"status": "failed", "reason": str(exc)})
        if state_write_error:
            base["state_write_error"] = state_write_error
        return base


def _tick_from_args(args: argparse.Namespace, *, force: bool | None = None) -> dict[str, Any]:
    return _heartbeat_once(
        idle_threshold_seconds=float(args.idle_threshold_seconds),
        heartbeat_interval_seconds=float(args.heartbeat_interval_seconds),
        app_name=str(args.app_name or DEFAULT_APP_NAME),
        count_source=str(args.count_source or DEFAULT_COUNT_SOURCE),
        fixed_count=int(args.fixed_count),
        max_count=int(args.max_count),
        key_delay_seconds=float(args.key_delay_seconds),
        trace_refresh_seconds=float(args.trace_refresh_seconds),
        codex_db_recent_minutes=float(args.codex_db_recent_minutes),
        codex_db_limit=int(args.codex_db_limit),
        codex_db_cwd=Path(str(args.codex_db_cwd)).expanduser().resolve(),
        max_windows_to_sweep=int(args.max_windows_to_sweep),
        exclude_thread_ids=_thread_id_set(getattr(args, "exclude_thread_id", [])),
        dry_run=bool(args.dry_run),
        force=bool(args.force if force is None else force),
        record_state=bool(getattr(args, "record_state", True)),
    )


def _cmd_once(args: argparse.Namespace) -> int:
    payload = _tick_from_args(args)
    ledger_write_error = _try_append_jsonl(LEDGER_PATH, payload)
    if ledger_write_error:
        payload["ledger_write_error"] = ledger_write_error
    _print_payload(payload, json_mode=bool(args.json))
    if ledger_write_error:
        return 1
    return 0 if payload.get("status") in {"heartbeat_sent", "dry_run", "skipped"} else 1


def _cmd_run(args: argparse.Namespace) -> int:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    last_skip_log_signature: str | None = None
    last_skip_log_at = 0.0
    while True:
        payload = _tick_from_args(args, force=False)
        should_log = payload.get("status") != "skipped"
        if not should_log:
            now = time.time()
            skip_signature = str(payload.get("reason") or "skipped")
            should_log = (
                skip_signature != last_skip_log_signature
                or now - last_skip_log_at >= DEFAULT_SKIP_LOG_INTERVAL_SECONDS
            )
            if should_log:
                last_skip_log_signature = skip_signature
                last_skip_log_at = now
        if should_log:
            ledger_write_error = _try_append_jsonl(LEDGER_PATH, payload)
            if ledger_write_error:
                _safe_stderr(f"[codex-idle-heartbeat] ledger write failed: {ledger_write_error}")
        time.sleep(float(args.poll_seconds))


def _launch_agent_payload(args: argparse.Namespace) -> dict[str, Any]:
    program_args = [
        str(REPO_ROOT / "repo-python"),
        str(Path(__file__).resolve()),
        "run",
        "--idle-threshold-seconds",
        str(int(args.idle_threshold_seconds)),
        "--heartbeat-interval-seconds",
        str(int(args.heartbeat_interval_seconds)),
        "--poll-seconds",
        str(float(args.poll_seconds)),
        "--app-name",
        str(args.app_name or DEFAULT_APP_NAME),
        "--count-source",
        str(args.count_source or DEFAULT_COUNT_SOURCE),
        "--fixed-count",
        str(int(args.fixed_count)),
        "--max-count",
        str(int(args.max_count)),
        "--key-delay-seconds",
        str(float(args.key_delay_seconds)),
        "--trace-refresh-seconds",
        str(float(args.trace_refresh_seconds)),
        "--codex-db-recent-minutes",
        str(float(args.codex_db_recent_minutes)),
        "--codex-db-limit",
        str(int(args.codex_db_limit)),
        "--codex-db-cwd",
        str(Path(str(args.codex_db_cwd)).expanduser().resolve()),
        "--max-windows-to-sweep",
        str(int(args.max_windows_to_sweep)),
    ]
    return {
        "Label": LABEL,
        "ProgramArguments": program_args,
        "WorkingDirectory": str(REPO_ROOT),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(STDOUT_LOG),
        "StandardErrorPath": str(STDERR_LOG),
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
    }


def _launchctl(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = _run(["launchctl", *args], timeout_s=15.0)
    if check and proc.returncode != 0:
        raise HeartbeatError((proc.stderr or proc.stdout or "launchctl failed").strip())
    return proc


def _cmd_install(args: argparse.Namespace) -> int:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = _launch_agent_payload(args)
    with PLIST_PATH.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=False)
    lint = _run(["plutil", "-lint", str(PLIST_PATH)], timeout_s=5.0)
    if lint.returncode != 0:
        raise HeartbeatError((lint.stderr or lint.stdout or "plist lint failed").strip())
    _launchctl("bootout", f"gui/{os.getuid()}", str(PLIST_PATH), check=False)
    boot = _launchctl("bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH), check=False)
    if boot.returncode != 0 and "Input/output error" in (boot.stderr or boot.stdout):
        _launchctl("unload", str(PLIST_PATH), check=False)
        _launchctl("load", "-w", str(PLIST_PATH), check=True)
    elif boot.returncode != 0:
        raise HeartbeatError((boot.stderr or boot.stdout or "launchctl bootstrap failed").strip())
    _launchctl("enable", SERVICE, check=False)
    _launchctl("kickstart", "-k", SERVICE, check=False)
    result = {
        "status": "installed",
        "label": LABEL,
        "plist": str(PLIST_PATH),
        "service": SERVICE,
        "runtime_root": str(RUNTIME_ROOT),
        "program_arguments": payload["ProgramArguments"],
        "service_status": _service_status(),
    }
    _print_payload(result, json_mode=bool(args.json))
    return 0


def _cmd_uninstall(args: argparse.Namespace) -> int:
    _launchctl("bootout", SERVICE, check=False)
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
    result = {
        "status": "uninstalled",
        "label": LABEL,
        "plist": str(PLIST_PATH),
        "service": SERVICE,
    }
    _print_payload(result, json_mode=bool(args.json))
    return 0


def _service_status() -> dict[str, Any]:
    proc = _launchctl("print", SERVICE, check=False)
    return {
        "label": LABEL,
        "service": SERVICE,
        "plist_exists": PLIST_PATH.exists(),
        "returncode": proc.returncode,
        "loaded": proc.returncode == 0,
        "stdout": (proc.stdout or "").splitlines()[:40],
        "stderr": (proc.stderr or "").strip(),
    }


def _resident_process_status() -> dict[str, Any]:
    proc = _run(["ps", "-axo", "pid,ppid,command"], timeout_s=5.0)
    expected_script = str(Path(__file__).resolve())
    rows: list[dict[str, Any]] = []
    if proc.returncode == 0:
        for line in (proc.stdout or "").splitlines()[1:]:
            parts = line.strip().split(None, 2)
            if len(parts) < 3:
                continue
            pid, ppid, command = parts
            if expected_script not in command:
                continue
            if " run" not in f" {command} ":
                continue
            rows.append({"pid": pid, "ppid": ppid, "command": command})
    return {
        "ok": proc.returncode == 0,
        "count": len(rows),
        "pids": [row["pid"] for row in rows],
        "rows": rows[:5],
        "returncode": proc.returncode,
        "stderr": (proc.stderr or "").strip()[:500],
    }


def _latest_ledger_event(path: Path = LEDGER_PATH) -> dict[str, Any]:
    latest_line = ""
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    latest_line = line
    except OSError as exc:
        return {"ok": False, "reason": str(exc), "path": str(path)}
    if not latest_line:
        return {"ok": False, "reason": "ledger_empty", "path": str(path)}
    try:
        event = json.loads(latest_line)
    except json.JSONDecodeError as exc:
        return {"ok": False, "reason": f"ledger_json_error: {exc}", "path": str(path)}
    if not isinstance(event, dict):
        return {"ok": False, "reason": "ledger_latest_not_object", "path": str(path)}
    timestamp_s = _parse_utc_timestamp(event.get("timestamp"))
    age_seconds = None if timestamp_s is None else max(0.0, time.time() - timestamp_s)
    return {
        "ok": True,
        "path": str(path),
        "event": event,
        "status": event.get("status"),
        "reason": event.get("reason") or event.get("error"),
        "timestamp": event.get("timestamp"),
        "age_seconds": age_seconds,
    }


def _status_payload(args: argparse.Namespace) -> dict[str, Any]:
    idle_seconds = hid_idle_seconds()
    state = _load_json(STATE_PATH)
    gate = _idle_gate_state(
        state=state,
        now=time.time(),
        idle_seconds=idle_seconds,
        idle_threshold_seconds=float(args.idle_threshold_seconds),
        key_delay_seconds=float(args.key_delay_seconds),
        max_count=int(args.max_count),
    )
    cycle = resolve_cycle_count(
        count_source=str(args.count_source or DEFAULT_COUNT_SOURCE),
        fixed_count=int(args.fixed_count),
        max_count=int(args.max_count),
        app_name=str(args.app_name or DEFAULT_APP_NAME),
        trace_refresh_seconds=float(args.trace_refresh_seconds),
        codex_db_recent_minutes=float(args.codex_db_recent_minutes),
        codex_db_limit=int(args.codex_db_limit),
        codex_db_cwd=Path(str(args.codex_db_cwd)).expanduser().resolve(),
        max_windows_to_sweep=int(args.max_windows_to_sweep),
        exclude_thread_ids=_thread_id_set(getattr(args, "exclude_thread_id", [])),
    )
    return {
        "status": "ok",
        "timestamp": _utc_now(),
        "label": LABEL,
        "idle_seconds": idle_seconds,
        "idle_threshold_seconds": float(args.idle_threshold_seconds),
        "idle_gate_open": None if idle_seconds is None else idle_seconds >= float(args.idle_threshold_seconds),
        "user_idle_gate_open": gate["user_idle_gate_open"],
        "heartbeat_gate_open": gate["heartbeat_gate_open"],
        "idle_gate_reason": gate["idle_gate_reason"],
        "synthetic_idle_continuation": gate["synthetic_idle_continuation"],
        "state_path": str(STATE_PATH),
        "ledger_path": str(LEDGER_PATH),
        "state": state,
        "cycle_count": cycle,
        "service": _service_status(),
    }


def _cmd_status(args: argparse.Namespace) -> int:
    payload = _status_payload(args)
    _print_payload(payload, json_mode=bool(args.json))
    return 0


def _read_launch_agent_plist() -> dict[str, Any]:
    if not PLIST_PATH.exists():
        return {}
    try:
        with PLIST_PATH.open("rb") as handle:
            payload = plistlib.load(handle)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _program_arg_value(program_args: list[str], flag: str) -> Optional[str]:
    try:
        index = program_args.index(flag)
    except ValueError:
        return None
    next_index = index + 1
    if next_index >= len(program_args):
        return None
    return str(program_args[next_index])


def _doctor_check(check_id: str, passed: bool, *, severity: str = "fail", detail: str = "") -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "pass" if passed else "fail",
        "severity": severity,
        "detail": detail,
    }


def _doctor_gate_model_checks(
    *,
    idle_threshold_seconds: float,
    key_delay_seconds: float,
    max_count: int,
) -> list[dict[str, Any]]:
    before_threshold_idle = max(0.0, float(idle_threshold_seconds) - 1.0)
    synthetic_idle = max(1.0, min(60.0, float(idle_threshold_seconds) / 2.0))
    gate_samples = {
        "gate_model_blocks_before_threshold": _idle_gate_state(
            state={},
            now=100.0,
            idle_seconds=before_threshold_idle,
            idle_threshold_seconds=idle_threshold_seconds,
            key_delay_seconds=key_delay_seconds,
            max_count=max_count,
        ),
        "gate_model_opens_at_threshold": _idle_gate_state(
            state={},
            now=100.0 + float(idle_threshold_seconds),
            idle_seconds=float(idle_threshold_seconds),
            idle_threshold_seconds=idle_threshold_seconds,
            key_delay_seconds=key_delay_seconds,
            max_count=max_count,
        ),
        "gate_model_allows_synthetic_continuation": _idle_gate_state(
            state={"armed": True, "last_tick_at": 100.0},
            now=100.0 + synthetic_idle,
            idle_seconds=synthetic_idle,
            idle_threshold_seconds=idle_threshold_seconds,
            key_delay_seconds=key_delay_seconds,
            max_count=max_count,
        ),
    }
    return [
        _doctor_check(
            "gate_model_blocks_before_threshold",
            not bool(gate_samples["gate_model_blocks_before_threshold"].get("heartbeat_gate_open"))
            and gate_samples["gate_model_blocks_before_threshold"].get("idle_gate_reason") == "not_idle",
            detail=json.dumps(gate_samples["gate_model_blocks_before_threshold"], sort_keys=True),
        ),
        _doctor_check(
            "gate_model_opens_at_threshold",
            bool(gate_samples["gate_model_opens_at_threshold"].get("heartbeat_gate_open"))
            and gate_samples["gate_model_opens_at_threshold"].get("idle_gate_reason") == "user_idle_threshold_met",
            detail=json.dumps(gate_samples["gate_model_opens_at_threshold"], sort_keys=True),
        ),
        _doctor_check(
            "gate_model_allows_synthetic_continuation",
            bool(gate_samples["gate_model_allows_synthetic_continuation"].get("heartbeat_gate_open"))
            and gate_samples["gate_model_allows_synthetic_continuation"].get("idle_gate_reason")
            == "synthetic_heartbeat_continuation",
            detail=json.dumps(gate_samples["gate_model_allows_synthetic_continuation"], sort_keys=True),
        ),
    ]


def _slot_key_strings(slots: Any) -> list[str]:
    keys: list[str] = []
    if not isinstance(slots, list):
        return keys
    for slot in slots:
        try:
            slot_number = int(slot)
        except (TypeError, ValueError):
            continue
        if 1 <= slot_number <= 9:
            keys.append(str(slot_number))
    return keys


def _cmd_doctor(args: argparse.Namespace) -> int:
    status_payload = _status_payload(args)
    service = status_payload.get("service") if isinstance(status_payload.get("service"), dict) else {}
    cycle = status_payload.get("cycle_count") if isinstance(status_payload.get("cycle_count"), dict) else {}
    model = cycle.get("tab_permutation_model") if isinstance(cycle.get("tab_permutation_model"), dict) else {}
    plist_payload = _read_launch_agent_plist()
    program_args = [str(item) for item in plist_payload.get("ProgramArguments", []) if str(item)]
    expected_threshold = str(int(float(args.idle_threshold_seconds)))
    expected_window_cap = str(int(args.max_windows_to_sweep))
    expected_script = str(Path(__file__).resolve())
    user_idle_gate_open = bool(status_payload.get("user_idle_gate_open"))
    synthetic_idle_continuation = bool(status_payload.get("synthetic_idle_continuation"))
    expected_gate_open = user_idle_gate_open or synthetic_idle_continuation
    resident_process = _resident_process_status()
    latest_ledger = _latest_ledger_event()
    latest_ledger_status = str(latest_ledger.get("status") or "").strip()
    latest_ledger_age = latest_ledger.get("age_seconds")
    latest_ledger_fresh = isinstance(latest_ledger_age, (int, float)) and float(latest_ledger_age) <= (
        DEFAULT_SKIP_LOG_INTERVAL_SECONDS * 2.0 + float(args.poll_seconds if hasattr(args, "poll_seconds") else DEFAULT_POLL_SECONDS)
    )
    state = status_payload.get("state") if isinstance(status_payload.get("state"), dict) else {}
    checks = [
        _doctor_check("launchagent_plist_exists", bool(service.get("plist_exists")), detail=str(PLIST_PATH)),
        _doctor_check("launchagent_loaded", bool(service.get("loaded")), detail=str(service.get("service") or SERVICE)),
        _doctor_check(
            "resident_process_running",
            int(resident_process.get("count") or 0) > 0,
            detail=f"pids={resident_process.get('pids')}",
        ),
        _doctor_check(
            "resident_command_is_run_loop",
            expected_script in program_args and "run" in program_args,
            detail="LaunchAgent ProgramArguments should execute codex_idle_heartbeat.py run",
        ),
        _doctor_check(
            "resident_idle_threshold_is_20_minutes",
            _program_arg_value(program_args, "--idle-threshold-seconds") == expected_threshold,
            detail=f"expected --idle-threshold-seconds {expected_threshold}",
        ),
        _doctor_check(
            "resident_sweeps_one_window",
            _program_arg_value(program_args, "--max-windows-to-sweep") == expected_window_cap,
            detail=f"expected --max-windows-to-sweep {expected_window_cap}",
        ),
        _doctor_check(
            "resident_not_forced",
            "--force" not in program_args,
            detail="resident daemon must not bypass HID idle gate",
        ),
        _doctor_check(
            "resident_not_dry_run",
            "--dry-run" not in program_args,
            detail="resident daemon should be capable of real heartbeat after idle gate opens",
        ),
        _doctor_check(
            "idle_gate_consistent",
            bool(status_payload.get("heartbeat_gate_open")) == expected_gate_open,
            detail=str(status_payload.get("idle_gate_reason")),
        ),
        _doctor_check(
            "single_window_sweep_limit_respected",
            int(model.get("windows_to_sweep") or 0) <= int(args.max_windows_to_sweep),
            detail=f"windows_to_sweep={model.get('windows_to_sweep')}",
        ),
        _doctor_check(
            "single_window_cap_has_no_return_window_switch",
            int(model.get("return_window_switches") or 0) == 0,
            detail=f"return_window_switches={model.get('return_window_switches')}",
        ),
        _doctor_check(
            "latest_ledger_event_fresh",
            latest_ledger_fresh,
            severity="warn",
            detail=f"age_seconds={latest_ledger_age}",
        ),
        _doctor_check(
            "latest_ledger_status_not_failed",
            bool(latest_ledger.get("ok")) and latest_ledger_status != "failed",
            severity="warn",
            detail=f"status={latest_ledger_status} reason={latest_ledger.get('reason')}",
        ),
        _doctor_check(
            "state_status_not_failed",
            str(state.get("last_status") or "").strip() != "failed",
            severity="warn",
            detail=f"state.last_status={state.get('last_status')}",
        ),
    ]
    checks.extend(
        _doctor_gate_model_checks(
            idle_threshold_seconds=float(args.idle_threshold_seconds),
            key_delay_seconds=float(args.key_delay_seconds),
            max_count=int(args.max_count),
        )
    )
    window_count = int(model.get("window_count") or 0)
    active_slot_count = int(cycle.get("count") or 0)
    checks.append(
        _doctor_check(
            "visible_window_or_safe_skip",
            window_count > 0 or bool(model.get("risks")),
            severity="warn",
            detail=f"window_count={window_count}",
        )
    )
    checks.append(
        _doctor_check(
            "active_slots_or_safe_noop",
            active_slot_count > 0 or str(status_payload.get("idle_gate_reason")) == "not_idle",
            severity="warn",
            detail=f"active_slot_count={active_slot_count}",
        )
    )

    dry_run_payload: dict[str, Any] | None = None
    if bool(args.include_dry_run):
        dry_run_payload = _heartbeat_once(
            idle_threshold_seconds=float(args.idle_threshold_seconds),
            heartbeat_interval_seconds=float(args.heartbeat_interval_seconds),
            app_name=str(args.app_name or DEFAULT_APP_NAME),
            count_source=str(args.count_source or DEFAULT_COUNT_SOURCE),
            fixed_count=int(args.fixed_count),
            max_count=int(args.max_count),
            key_delay_seconds=float(args.key_delay_seconds),
            trace_refresh_seconds=float(args.trace_refresh_seconds),
            codex_db_recent_minutes=float(args.codex_db_recent_minutes),
            codex_db_limit=int(args.codex_db_limit),
            codex_db_cwd=Path(str(args.codex_db_cwd)).expanduser().resolve(),
            max_windows_to_sweep=int(args.max_windows_to_sweep),
            exclude_thread_ids=_thread_id_set(getattr(args, "exclude_thread_id", [])),
            dry_run=True,
            force=True,
            record_state=False,
        )
        selected_keys = _slot_key_strings(cycle.get("selected_slot_numbers"))
        dry_run_cycle = (
            dry_run_payload.get("cycle_count") if isinstance(dry_run_payload.get("cycle_count"), dict) else {}
        )
        dry_run_selected_keys = _slot_key_strings(dry_run_cycle.get("selected_slot_numbers")) or selected_keys
        checks.extend(
            [
                _doctor_check(
                    "dry_run_tick_plans_without_keypress",
                    dry_run_payload.get("status") == "dry_run",
                    detail=str(dry_run_payload.get("status")),
                ),
                _doctor_check(
                    "dry_run_respects_one_window_cap",
                    int(dry_run_payload.get("windows_swept") or 0) <= int(args.max_windows_to_sweep),
                    detail=f"windows_swept={dry_run_payload.get('windows_swept')}",
                ),
                _doctor_check(
                    "dry_run_has_no_return_window_switch",
                    int(dry_run_payload.get("return_window_switches") or 0) == 0,
                    detail=f"return_window_switches={dry_run_payload.get('return_window_switches')}",
                ),
                _doctor_check(
                    "dry_run_matches_selected_active_slots",
                    list(dry_run_payload.get("keys") or []) == dry_run_selected_keys,
                    detail=f"expected_keys={dry_run_selected_keys} actual_keys={dry_run_payload.get('keys')}",
                ),
            ]
        )

    failing_required = [check for check in checks if check["status"] != "pass" and check["severity"] == "fail"]
    failing_warnings = [check for check in checks if check["status"] != "pass" and check["severity"] == "warn"]
    overall_status = "failed" if failing_required else ("degraded" if failing_warnings else "ok")
    payload: dict[str, Any] = {
        "status": overall_status,
        "timestamp": _utc_now(),
        "label": LABEL,
        "checks": checks,
        "summary": {
            "required_failed": len(failing_required),
            "warnings_failed": len(failing_warnings),
            "idle_seconds": status_payload.get("idle_seconds"),
            "idle_threshold_seconds": status_payload.get("idle_threshold_seconds"),
            "idle_gate_reason": status_payload.get("idle_gate_reason"),
            "heartbeat_gate_open": status_payload.get("heartbeat_gate_open"),
            "service_loaded": bool(service.get("loaded")),
            "window_count": window_count,
            "active_slot_count": active_slot_count,
            "selected_slot_numbers": cycle.get("selected_slot_numbers"),
            "max_windows_to_sweep": int(args.max_windows_to_sweep),
            "resident_process_count": int(resident_process.get("count") or 0),
            "latest_ledger_status": latest_ledger_status or None,
            "latest_ledger_age_seconds": latest_ledger_age,
            "state_last_status": state.get("last_status"),
        },
        "resident_process": resident_process,
        "latest_ledger": latest_ledger,
    }
    if dry_run_payload is not None:
        payload["dry_run"] = {
            "status": dry_run_payload.get("status"),
            "keys": dry_run_payload.get("keys"),
            "selected_slot_numbers": dry_run_cycle.get("selected_slot_numbers") if isinstance(dry_run_cycle, dict) else None,
            "windows_swept": dry_run_payload.get("windows_swept"),
            "return_window_switches": dry_run_payload.get("return_window_switches"),
            "sweep_plan": dry_run_payload.get("sweep_plan"),
        }
    _print_payload(payload, json_mode=bool(args.json))
    return 0 if not failing_required else 1


def _print_payload(payload: dict[str, Any], *, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    status = payload.get("status")
    print(f"Codex idle heartbeat: {status}")
    for key in ("reason", "idle_seconds", "keys", "plist", "service"):
        if key in payload and payload.get(key) not in (None, ""):
            print(f"  {key}: {payload.get(key)}")
    if "idle_gate_reason" in payload:
        print(f"  idle gate: {payload.get('idle_gate_reason')} (heartbeat_open={payload.get('heartbeat_gate_open')})")
    cycle = payload.get("cycle_count")
    if isinstance(cycle, dict):
        print(f"  count: {cycle.get('count')} ({cycle.get('source')})")
        model = cycle.get("tab_permutation_model")
        if isinstance(model, dict):
            print(f"  tab case: {model.get('current_case')} ({model.get('alignment')})")


def _add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--idle-threshold-seconds", type=float, default=DEFAULT_IDLE_THRESHOLD_SECONDS)
    parser.add_argument("--heartbeat-interval-seconds", type=float, default=DEFAULT_HEARTBEAT_INTERVAL_SECONDS)
    parser.add_argument("--app-name", default=DEFAULT_APP_NAME)
    parser.add_argument(
        "--count-source",
        choices=["auto", "codex_live_rollout", "codex_db_recent", "trace", "windows", "fixed"],
        default=DEFAULT_COUNT_SOURCE,
        help="Where to get the Command-number slots to visit.",
    )
    parser.add_argument("--fixed-count", type=int, default=1)
    parser.add_argument("--max-count", type=int, default=DEFAULT_MAX_COUNT)
    parser.add_argument("--key-delay-seconds", type=float, default=DEFAULT_KEY_DELAY_SECONDS)
    parser.add_argument(
        "--trace-refresh-seconds",
        type=float,
        default=DEFAULT_TRACE_REFRESH_SECONDS,
        help="Refresh Work Ledger active-claims snapshot when older than this before computing N.",
    )
    parser.add_argument(
        "--codex-db-recent-minutes",
        type=float,
        default=DEFAULT_CODEX_DB_RECENT_MINUTES,
        help="For auto/codex_db_recent count mode, include unarchived Codex threads in this cwd updated within this many minutes.",
    )
    parser.add_argument(
        "--codex-db-limit",
        type=int,
        default=DEFAULT_CODEX_DB_LIMIT,
        help="Maximum Codex project slots to scan before the Command+1..9 hard cap.",
    )
    parser.add_argument(
        "--codex-db-cwd",
        default=str(REPO_ROOT),
        help="Codex thread cwd to count in ~/.codex/state_5.sqlite.",
    )
    parser.add_argument(
        "--max-windows-to-sweep",
        type=int,
        default=DEFAULT_MAX_WINDOWS_TO_SWEEP,
        help="When several Codex windows are open, sweep this many windows with Command+1..N and return to the starting window.",
    )
    parser.add_argument(
        "--exclude-thread-id",
        action="append",
        default=[],
        help="Exclude a thread id from rollout-open-turn counting. May be repeated or comma-separated; useful for status checks from the current Codex thread.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Idle-gated Codex Command-number heartbeat")
    sub = parser.add_subparsers(dest="cmd", required=True)

    once = sub.add_parser("once", help="run one idle-gated heartbeat tick")
    _add_shared_args(once)
    once.add_argument("--dry-run", action="store_true")
    once.add_argument("--force", action="store_true", help="bypass the idle threshold for testing")
    once.add_argument(
        "--arm-state",
        dest="record_state",
        action="store_true",
        default=False,
        help="Record the tick as daemon state. Manual trials leave daemon state alone by default.",
    )
    once.add_argument("--json", action="store_true")
    once.set_defaults(fn=_cmd_once)

    run = sub.add_parser("run", help="run the launchd-friendly resident loop")
    _add_shared_args(run)
    run.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--force", action="store_true", default=False, help=argparse.SUPPRESS)
    run.set_defaults(fn=_cmd_run, record_state=True)

    install = sub.add_parser("install", help="install and start the LaunchAgent")
    _add_shared_args(install)
    install.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    install.add_argument("--json", action="store_true")
    install.set_defaults(fn=_cmd_install)

    uninstall = sub.add_parser("uninstall", help="stop and remove the LaunchAgent")
    uninstall.add_argument("--json", action="store_true")
    uninstall.set_defaults(fn=_cmd_uninstall)

    status = sub.add_parser("status", help="show idle, service, and active-count status")
    _add_shared_args(status)
    status.add_argument("--json", action="store_true")
    status.set_defaults(fn=_cmd_status)

    doctor = sub.add_parser("doctor", help="run operational invariant checks without sending keys")
    _add_shared_args(doctor)
    doctor.add_argument(
        "--include-dry-run",
        action="store_true",
        help="Plan a forced dry-run tick in-process; this does not append ledger state or send keypresses.",
    )
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(fn=_cmd_doctor)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.fn(args) or 0)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        payload = {"status": "failed", "timestamp": _utc_now(), "error": str(exc)}
        ledger_write_error = _try_append_jsonl(LEDGER_PATH, payload)
        if ledger_write_error:
            payload["ledger_write_error"] = ledger_write_error
        _print_payload(payload, json_mode=bool(getattr(args, "json", False)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
