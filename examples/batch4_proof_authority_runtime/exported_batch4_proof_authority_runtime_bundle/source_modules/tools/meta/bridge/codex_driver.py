"""
[PURPOSE]
- Teleology: Python driver for the Codex desktop app (Electron) — the Codex
  equivalent of system/core/bridge.py for chatgpt.com. Treats Codex threads
  as subagents: read state, inject user turns, observe streaming output.
- Mechanism: Codex is launched with `--remote-debugging-port=9224`. This
  module connects via Chrome DevTools Protocol (WebSocket JSON-RPC) to the
  main chat renderer. Observability is read-only (DOM + manager fields +
  rollout JSONL on disk). Read-only AppServer manager requests are allowed
  for capability probes. Default writes are user-simulation only (mouse +
  keyboard events). The explicit `manager-start` lane is a new-thread-only
  manager-owned write path, and it is not treated as complete until rollout
  evidence shows the turn finished.
- Non-goal: No raw AppServer RPC writes for existing threads. No direct
  `turn/start` or `thread/resume` via `sendRequest`; those bypass too much UI
  state. Existing-thread mutation still goes through the same path a human
  user does.

[ARCHITECTURE]
    CDPClient ................ 100-line WebSocket JSON-RPC 2.0 client, stdlib only
    CodexDriver .............. high-level API; wraps CDPClient + Codex-specific JS probes
      - observability ........ current_thread_id, list_threads, conversations,
                               streaming_thread_ids, rollout_path, extract_turns,
                               tail_rollout, manager_probe
      - control .............. switch_thread, new_chat, focus_composer, type_text,
                               submit, send_message, interrupt, manager_start
      - future (stretched) ... select_model, select_effort, slash_command

[USER SIMULATION CONTRACT]
- Mouse: Input.dispatchMouseEvent at bounding-rect center of target element.
- Keyboard: Input.dispatchKeyEvent with `text` field for printables, `key`+`code`
  for specials (Enter, Escape, arrows). Modifiers: 1=Alt, 2=Ctrl, 4=Meta, 8=Shift.
- Thread identity: [data-app-action-sidebar-thread-id] + [...-thread-active].
- Composer element: `.ProseMirror[contenteditable="true"]` (single instance in the
  main chat view).
- Submit trigger: Enter key (code=Enter, key=Enter) on the focused composer.

[OBSERVABILITY SURFACES]
- DOM sidebar: thread rows with full dataset (id, title, kind, active, pinned).
- Manager (captured once via prototype wrap on the AppServerManager class):
  conversations Map, streamingConversations Set, each conversation has
  rolloutPath, title, turnCount, threadRuntimeStatus, latestModel, etc.
- Rollout JSONL (~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl):
  append-only, line-per-event. Authoritative for "did a turn land and what did
  the agent actually do". Event taxonomy (empirically confirmed):
    event_msg.task_started          — turn boundary start
    event_msg.task_complete         — turn boundary end (has last_agent_message, duration_ms)
    event_msg.turn_aborted          — interrupted turn boundary end (has reason, completed_at)
    event_msg.user_message          — the user's prompt text
    event_msg.agent_message         — assistant output
    event_msg.agent_reasoning       — chain-of-thought summary
    event_msg.exec_command_end      — shell tool call result (has parsed_cmd, exit_code, stdout)
    event_msg.token_count           — per-event usage
    response_item.message           — assistant messages (role=assistant)
    response_item.function_call     — tool call (has name, arguments)
    response_item.function_call_output — tool output
    response_item.reasoning         — reasoning summary
    turn_context                    — turn metadata (model, effort, cwd, etc.)
    session_meta                    — first line; has id, cwd, source, originator

[DEPENDENCIES]
- stdlib only: socket, struct, secrets, base64, json, urllib, pathlib, subprocess.
- No websocket-client, no aiohttp — CDP client is hand-rolled.

[CONSTRAINTS]
- macOS only (launch tries app-name, bundle-path, then executable fallback).
  Trivial to port to Linux/Windows.
- Codex 0.119+ (verified against 0.119.0-alpha.28).
- Main-window selection: picks the first `?hostId=local` page, filtering out
  `?initialRoute=/hotkey-window` variants. Window snapshots keep target/window
  identity explicit when a CDP launch creates a second Codex window.
- User must have granted CDP port permission (default: no prompt on localhost).

[FAILURE MODES]
- If CDP port is not reachable after 4s launch: returns False from ensure_running.
- If CDP WebSocket connect races app startup: retries with capped exponential
  backoff before declaring the driver unavailable.
- If main chat target not found: pick_main_chat_target returns None.
- If manager capture fails (app not yet mounted): streaming + conversations
  return empty but DOM-based observability still works.
- If composer not found: typing/submit methods raise RuntimeError.
"""
from __future__ import annotations

import base64
import dataclasses
import json
import os
import pathlib
import plistlib
import re
import secrets
import shlex
import socket
import struct
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Iterator, Mapping, Optional


DEFAULT_PORT = 9224
CDP_HOST = "127.0.0.1"
SESSIONS_ROOT = pathlib.Path.home() / ".codex" / "sessions"
DIAGNOSTIC_REPORTS_ROOT = pathlib.Path.home() / "Library" / "Logs" / "DiagnosticReports"
CDP_CONNECT_ATTEMPTS = 5
CDP_CONNECT_INITIAL_BACKOFF_S = 1.0
CDP_CONNECT_MAX_BACKOFF_S = 30.0
CODEX_APP_NAME = "Codex"
DEFAULT_CODEX_APP_BUNDLE = pathlib.Path(os.environ.get("CODEX_APP_BUNDLE", "/Applications/Codex.app"))
LSREGISTER = pathlib.Path(
    "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
)

# CDP modifier flags
_ALT = 1
_CTRL = 2
_META = 4  # Cmd on macOS
_SHIFT = 8


def _text(value: object) -> str:
    return str(value or "").strip()


def _cdp_port_reachable(port: int = DEFAULT_PORT, *, timeout_s: float = 1.5) -> bool:
    try:
        urllib.request.urlopen(f"http://{CDP_HOST}:{port}/json/version", timeout=timeout_s)
    except (urllib.error.URLError, OSError):
        return False
    return True


def _codex_launchservices_metadata(app_path: pathlib.Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [
                "mdls",
                "-name",
                "kMDItemCFBundleIdentifier",
                "-name",
                "kMDItemDisplayName",
                "-name",
                "kMDItemFSName",
                str(app_path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
    except Exception as exc:  # pragma: no cover - host dependent fallback
        return {
            "available": False,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "error": str(exc),
        }
    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    return {
        "available": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "error": stderr if proc.returncode != 0 else None,
    }


def _codex_app_bundle_diagnostics(app_path: pathlib.Path = DEFAULT_CODEX_APP_BUNDLE) -> dict[str, Any]:
    info_plist_path = app_path / "Contents" / "Info.plist"
    bundle_executable = ""
    bundle_identifier = ""
    bundle_name = ""
    display_name = ""
    short_version = ""
    bundle_version = ""
    info_error = None
    if info_plist_path.exists():
        try:
            info = plistlib.loads(info_plist_path.read_bytes())
            bundle_executable = str(info.get("CFBundleExecutable") or "")
            bundle_identifier = str(info.get("CFBundleIdentifier") or "")
            bundle_name = str(info.get("CFBundleName") or "")
            display_name = str(info.get("CFBundleDisplayName") or "")
            short_version = str(info.get("CFBundleShortVersionString") or "")
            bundle_version = str(info.get("CFBundleVersion") or "")
        except Exception as exc:  # pragma: no cover - host dependent corrupt bundle
            info_error = str(exc)
    executable_path = app_path / "Contents" / "MacOS" / (bundle_executable or CODEX_APP_NAME)
    return {
        "bundle_path": str(app_path),
        "bundle_exists": app_path.exists(),
        "info_plist_path": str(info_plist_path),
        "info_plist_exists": info_plist_path.exists(),
        "info_plist_error": info_error,
        "bundle_executable": bundle_executable or None,
        "bundle_identifier": bundle_identifier or None,
        "bundle_name": bundle_name or None,
        "display_name": display_name or None,
        "short_version": short_version or None,
        "bundle_version": bundle_version or None,
        "executable_path": str(executable_path),
        "executable_exists": executable_path.exists(),
        "executable_is_file": executable_path.is_file(),
        "executable_is_executable": os.access(executable_path, os.X_OK),
        "launch_services_metadata": _codex_launchservices_metadata(app_path),
    }


def _codex_recovery_commands(*, requested_port: int, app_bundle: Mapping[str, Any] | None = None) -> dict[str, str | None]:
    app_bundle = app_bundle or _codex_app_bundle_diagnostics()
    open_by_name = f"open -a {shlex.quote(CODEX_APP_NAME)} --args --remote-debugging-port={requested_port}"
    bundle_path = _text(app_bundle.get("bundle_path"))
    executable_path = _text(app_bundle.get("executable_path"))
    open_bundle = (
        f"open {shlex.quote(bundle_path)} --args --remote-debugging-port={requested_port}"
        if bundle_path and app_bundle.get("bundle_exists")
        else None
    )
    direct_executable = (
        f"nohup {shlex.quote(executable_path)} --remote-debugging-port={requested_port} >/tmp/codex-cdp-{requested_port}.log 2>&1 &"
        if executable_path and app_bundle.get("executable_exists") and app_bundle.get("executable_is_executable")
        else None
    )
    return {
        "open_by_name": open_by_name,
        "open_bundle": open_bundle,
        "direct_executable": direct_executable,
        "primary": direct_executable or open_bundle or open_by_name,
    }


def _codex_launch_command_specs(*, port: int) -> list[dict[str, Any]]:
    app_bundle = _codex_app_bundle_diagnostics()
    specs: list[dict[str, Any]] = [
        {
            "method": "open_by_name",
            "command": ["open", "-a", CODEX_APP_NAME, "--args", f"--remote-debugging-port={port}"],
        }
    ]
    bundle_identifier = _text(app_bundle.get("bundle_identifier"))
    if bundle_identifier:
        specs.append(
            {
                "method": "open_by_bundle_id",
                "command": ["open", "-b", bundle_identifier, "--args", f"--remote-debugging-port={port}"],
            }
        )
    bundle_path = _text(app_bundle.get("bundle_path"))
    if app_bundle.get("bundle_exists") and bundle_path:
        specs.append(
            {
                "method": "open_bundle",
                "command": ["open", bundle_path, "--args", f"--remote-debugging-port={port}"],
            }
        )
    executable_path = _text(app_bundle.get("executable_path"))
    if app_bundle.get("executable_exists") and app_bundle.get("executable_is_executable") and executable_path:
        specs.append(
            {
                "method": "direct_executable",
                "command": [executable_path, f"--remote-debugging-port={port}"],
            }
        )
    return specs


def _probe_launchservices_registration(app_path: pathlib.Path = DEFAULT_CODEX_APP_BUNDLE) -> dict[str, Any]:
    command = [str(LSREGISTER), "-f", str(app_path)]
    result: dict[str, Any] = {
        "kind": "codex_launchservices_registration_probe",
        "requested": True,
        "command": command,
        "command_text": shlex.join(command),
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "error": None,
        "metadata_after": None,
    }
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=5.0,
        )
    except subprocess.TimeoutExpired as exc:
        result["error"] = f"timeout: {exc}"
    except Exception as exc:  # pragma: no cover - host-dependent launcher failures
        result["error"] = str(exc)
    else:
        result["returncode"] = proc.returncode
        result["stdout"] = (proc.stdout or "").strip()
        result["stderr"] = (proc.stderr or "").strip()
    result["metadata_after"] = _codex_launchservices_metadata(app_path)
    result["recovered"] = bool((result.get("metadata_after") or {}).get("available"))
    return result


def _codex_launch_commands(*, port: int) -> list[list[str]]:
    return [list(spec["command"]) for spec in _codex_launch_command_specs(port=port)]


def _codex_cdp_window_launch_specs(*, port: int) -> list[dict[str, Any]]:
    specs = _codex_launch_command_specs(port=port)
    direct = [spec for spec in specs if spec.get("method") == "direct_executable"]
    rest = [spec for spec in specs if spec.get("method") != "direct_executable"]
    return direct + rest


def _wait_for_cdp_probe(port: int, *, wait_s: float, poll_s: float = 0.25) -> dict[str, Any]:
    end = time.time() + max(float(wait_s), 0.0)
    probe = _probe_cdp_port(port)
    while time.time() < end and not probe.get("reachable"):
        time.sleep(max(float(poll_s), 0.05))
        probe = _probe_cdp_port(port)
    return probe


def probe_codex_launch(*, requested_port: int = DEFAULT_PORT, wait_s: float = 4.0) -> dict[str, Any]:
    """Try the known launch routes and report structured evidence.

    This is intentionally separate from read-only doctor/preflight paths: callers
    only get launch side effects by asking for this probe explicitly.
    """
    attempts: list[dict[str, Any]] = []
    probe_started_epoch = time.time()
    preexisting_crash_paths = {
        _text(report.get("path"))
        for report in _recent_codex_crash_reports(limit=20)
        if _text(report.get("path"))
    }
    app_bundle = _codex_app_bundle_diagnostics()
    registration_probe = None
    launch_services_metadata = app_bundle.get("launch_services_metadata")
    if app_bundle.get("bundle_exists") and not bool(
        isinstance(launch_services_metadata, Mapping) and launch_services_metadata.get("available")
    ):
        registration_probe = _probe_launchservices_registration(pathlib.Path(_text(app_bundle.get("bundle_path"))))
    start_probe = _probe_cdp_port(requested_port)
    if start_probe.get("reachable"):
        return {
            "kind": "codex_driver_launch_probe",
            "requested": True,
            "status": "already_reachable",
            "port": requested_port,
            "wait_s": wait_s,
            "launch_services_registration_probe": registration_probe,
            "attempts": attempts,
            "final_probe": start_probe,
        }

    for spec in _codex_launch_command_specs(port=requested_port):
        attempt_started_epoch = time.time()
        command = list(spec["command"])
        method = _text(spec.get("method")) or command[0]
        attempt: dict[str, Any] = {
            "method": method,
            "command": command,
            "command_text": shlex.join(command),
            "returncode": None,
            "pid": None,
            "stdout": "",
            "stderr": "",
            "error": None,
        }
        try:
            if command and command[0] == "open":
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=max(wait_s, 1.0),
                )
                attempt["returncode"] = completed.returncode
                attempt["stdout"] = (completed.stdout or "").strip()
                attempt["stderr"] = (completed.stderr or "").strip()
            else:
                log_path = pathlib.Path(f"/tmp/codex-cdp-{requested_port}-{method}.log")
                attempt["log_path"] = str(log_path)
                env = dict(os.environ)
                env.setdefault("ELECTRON_ENABLE_LOGGING", "1")
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_handle = log_path.open("wb")
                proc = subprocess.Popen(
                    command,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=env,
                )
                attempt["pid"] = proc.pid
                try:
                    attempt["returncode"] = proc.wait(timeout=min(max(wait_s, 1.0), 1.0))
                except subprocess.TimeoutExpired:
                    attempt["returncode"] = None
                finally:
                    log_handle.close()
                try:
                    attempt["log_excerpt"] = log_path.read_text(encoding="utf-8", errors="replace")[-4000:].strip()
                except OSError as exc:  # pragma: no cover - host dependent filesystem failure
                    attempt["log_excerpt_error"] = str(exc)
                if attempt.get("returncode") is not None and int(attempt.get("returncode") or 0) < 0:
                    # CrashReporter writes asynchronously; a short pause makes
                    # the direct-launch abort visible without hiding the launch
                    # failure behind a long wait.
                    time.sleep(0.5)
                    crash_reports = _recent_codex_crash_reports(
                        pid=int(attempt["pid"]) if attempt.get("pid") else None,
                        limit=1,
                    )
                    attempt["crash_reports"] = crash_reports or _recent_codex_crash_reports(limit=1)
        except subprocess.TimeoutExpired as exc:
            attempt["error"] = f"timeout: {exc}"
        except Exception as exc:  # pragma: no cover - host-dependent launcher failures
            attempt["error"] = str(exc)
        probe = _wait_for_cdp_probe(requested_port, wait_s=wait_s)
        attempt["probe_after"] = probe
        attempt["cdp_reachable_after"] = bool(probe.get("reachable"))
        attempt["main_chat_target_found_after"] = bool(probe.get("main_chat_target_found"))
        attempt_crash_reports = _recent_codex_crash_reports(
            since_epoch=attempt_started_epoch - 1.0,
            exclude_paths=preexisting_crash_paths,
            limit=3,
        )
        if attempt_crash_reports:
            attempt["desktop_launch_crashed"] = True
            attempt["crash_reports"] = attempt_crash_reports
            attempt["desktop_crash"] = _desktop_crash_summary(attempt_crash_reports)
        attempts.append(attempt)
        if probe.get("main_chat_target_found"):
            return {
                "kind": "codex_driver_launch_probe",
                "requested": True,
                "status": "recovered_main_chat",
                "port": requested_port,
                "wait_s": wait_s,
                "launch_services_registration_probe": registration_probe,
                "attempts": attempts,
                "final_probe": probe,
            }
        if probe.get("reachable"):
            return {
                "kind": "codex_driver_launch_probe",
                "requested": True,
                "status": "recovered_cdp_without_main_chat",
                "port": requested_port,
                "wait_s": wait_s,
                "launch_services_registration_probe": registration_probe,
                "attempts": attempts,
                "final_probe": probe,
            }

    crash_reports = _recent_codex_crash_reports(
        since_epoch=probe_started_epoch - 1.0,
        exclude_paths=preexisting_crash_paths,
        limit=3,
    )
    desktop_crash = _desktop_crash_summary(crash_reports)
    status = "desktop_launch_crashed" if desktop_crash.get("detected") else "failed"
    return {
        "kind": "codex_driver_launch_probe",
        "requested": True,
        "status": status,
        "port": requested_port,
        "wait_s": wait_s,
        "launch_services_registration_probe": registration_probe,
        "attempts": attempts,
        "final_probe": _probe_cdp_port(requested_port),
        "desktop_crash": desktop_crash,
        "recent_crash_reports": crash_reports or _recent_codex_crash_reports(limit=3),
    }


def _read_cdp_json(port: int, path: str, *, timeout_s: float = 1.5) -> tuple[Any | None, str | None]:
    try:
        with urllib.request.urlopen(f"http://{CDP_HOST}:{port}{path}", timeout=timeout_s) as response:
            return json.loads(response.read()), None
    except Exception as exc:
        return None, str(exc)


def _codex_process_rows() -> list[str]:
    errors: list[str] = []
    try:
        proc = subprocess.run(
            ["pgrep", "-fl", "Codex"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - host dependent fallback
        errors.append(f"pgrep_unavailable: {exc}")
    else:
        rows = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
        if rows:
            return rows
        if proc.stderr.strip():
            errors.append(f"pgrep_error: {proc.stderr.strip()}")
    try:
        ps_proc = subprocess.run(
            ["ps", "ax", "-o", "pid=,command="],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - host dependent fallback
        errors.append(f"ps_unavailable: {exc}")
    else:
        rows = [
            line.strip()
            for line in (ps_proc.stdout or "").splitlines()
            if "Codex" in line or "/Applications/Codex.app" in line
        ]
        if rows:
            return rows
        if ps_proc.stderr.strip():
            errors.append(f"ps_error: {ps_proc.stderr.strip()}")
    return errors


def _process_probe_available(process_rows: list[str]) -> bool:
    if not process_rows:
        return True
    error_prefixes = ("pgrep_", "ps_")
    return not all(row.startswith(error_prefixes) for row in process_rows)


def _remote_debugging_ports_from_processes(process_rows: list[str]) -> list[int]:
    ports: list[int] = []
    for row in process_rows:
        for match in re.finditer(r"--remote-debugging-port[=\s](\d+)", row):
            try:
                port = int(match.group(1))
            except ValueError:
                continue
            if port not in ports:
                ports.append(port)
    return ports


def _codex_process_summary(process_rows: list[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in process_rows:
        match = re.match(r"\s*(\d+)\s+(.*)", row)
        pid = int(match.group(1)) if match else None
        command = match.group(2) if match else row
        role = "other"
        if re.search(r"/Contents/MacOS/Codex(?:\s+--|$)", command):
            role = "app_main"
        elif "Resources/codex app-server" in command:
            role = "app_server"
        elif "crashpad_handler" in command:
            role = "crashpad"
        elif "Helper (Renderer)" in command:
            role = "renderer"
        elif "Helper" in command:
            role = "helper"
        ports: list[int] = []
        for port_match in re.finditer(r"--remote-debugging-port[=\s](\d+)", command):
            try:
                ports.append(int(port_match.group(1)))
            except ValueError:
                pass
        rows.append(
            {
                "pid": pid,
                "role": role,
                "remote_debugging_ports": ports,
                "remote_debugging_enabled": bool(ports),
                "command": command,
            }
        )
    main_processes = [row for row in rows if row["role"] == "app_main"]
    return {
        "process_count": len(rows),
        "main_processes": main_processes,
        "remote_debugging_main_processes": [
            row for row in main_processes if row["remote_debugging_enabled"]
        ],
        "app_server_processes": [row for row in rows if row["role"] == "app_server"],
        "renderer_processes": [row for row in rows if row["role"] == "renderer"],
    }


def _parse_port_list(raw: str, *, requested_port: int, process_ports: list[int] | None = None) -> list[int]:
    ports: list[int] = [requested_port]
    for port in process_ports or []:
        if port not in ports:
            ports.append(port)
    if raw.strip():
        tokens = re.split(r"[\s,]+", raw.strip())
    else:
        tokens = ["9222", "9223", "9224", "9225", "9226"]
    for token in tokens:
        if not token:
            continue
        try:
            port = int(token)
        except ValueError:
            continue
        if 0 < port < 65536 and port not in ports:
            ports.append(port)
    return ports


def _listener_rows_for_ports(ports: list[int]) -> dict[str, list[str]]:
    if not ports:
        return {}
    listeners: dict[str, list[str]] = {}
    for port in ports:
        try:
            proc = subprocess.run(
                ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as exc:  # pragma: no cover - host dependent fallback
            listeners[str(port)] = [f"lsof_unavailable: {exc}"]
            continue
        rows = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
        if not rows and proc.stderr.strip():
            rows = [f"lsof_error: {proc.stderr.strip()}"]
        listeners[str(port)] = rows[1:] if rows and rows[0].startswith("COMMAND") else rows
    return listeners


def _line_value(text: str, label: str) -> str | None:
    pattern = rf"^{re.escape(label)}:\s*(.+)$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _process_version(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    match = re.match(r"([^\s]+)(?:\s+\(([^)]+)\))?", raw.strip())
    if not match:
        return raw.strip(), None
    return match.group(1), match.group(2)


def _application_specific_information(text: str) -> str | None:
    marker = "Application Specific Information:"
    if marker not in text:
        return None
    tail = text.split(marker, 1)[1]
    lines: list[str] = []
    for line in tail.splitlines()[1:]:
        if not line.strip():
            break
        lines.append(line.strip())
    return "\n".join(lines).strip() or None


def _application_specific_information_from_payload(body: Mapping[str, Any]) -> str | None:
    asi = body.get("asi") if isinstance(body.get("asi"), Mapping) else {}
    lines: list[str] = []
    for value in asi.values():
        if isinstance(value, list):
            lines.extend(str(item).strip() for item in value if item)
        elif value:
            lines.append(str(value).strip())
    return "\n".join(line for line in lines if line) or None


def _parse_codex_crash_report(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        header_text, body_text = text.split("\n", 1)
        header = json.loads(header_text)
        body = json.loads(body_text)
    except Exception:
        header = {}
        body = {}
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = None
    if header and body:
        exception = body.get("exception") if isinstance(body.get("exception"), Mapping) else {}
        termination = body.get("termination") if isinstance(body.get("termination"), Mapping) else {}
        bundle_info = body.get("bundleInfo") if isinstance(body.get("bundleInfo"), Mapping) else {}
        return {
            "path": str(path),
            "report_format": "ips_json",
            "file_mtime_epoch": mtime,
            "timestamp": header.get("timestamp"),
            "app_version": header.get("app_version") or bundle_info.get("CFBundleShortVersionString"),
            "build_version": header.get("build_version") or bundle_info.get("CFBundleVersion"),
            "bundle_id": header.get("bundleID") or bundle_info.get("CFBundleIdentifier"),
            "pid": body.get("pid"),
            "proc_path": body.get("procPath"),
            "parent_process": body.get("parentProc"),
            "parent_pid": body.get("parentPid"),
            "exception_type": exception.get("type"),
            "exception_signal": exception.get("signal"),
            "termination_namespace": termination.get("namespace"),
            "termination_code": termination.get("code"),
            "termination_indicator": termination.get("indicator"),
            "application_specific_information": _application_specific_information_from_payload(body),
        }
    if "Process:" not in text or "Codex" not in text:
        return None
    version, build_version = _process_version(_line_value(text, "Version"))
    pid = None
    process_line = _line_value(text, "Process")
    if process_line:
        match = re.search(r"\[(\d+)\]", process_line)
        if match:
            pid = int(match.group(1))
    parent_process = None
    parent_pid = None
    parent_line = _line_value(text, "Parent Process")
    if parent_line:
        parent_process = parent_line.split("[", 1)[0].strip()
        match = re.search(r"\[(\d+)\]", parent_line)
        if match:
            parent_pid = int(match.group(1))
    termination = _line_value(text, "Termination Reason") or ""
    termination_namespace = None
    termination_code = None
    termination_indicator = termination or None
    match = re.search(r"Namespace\s+([^,]+),\s+Code\s+([^ ]+)\s+(.+)$", termination)
    if match:
        termination_namespace = match.group(1).strip()
        termination_code = match.group(2).strip()
        termination_indicator = match.group(3).strip()
    exception_type = _line_value(text, "Exception Type")
    return {
        "path": str(path),
        "report_format": "crash_text",
        "file_mtime_epoch": mtime,
        "timestamp": _line_value(text, "Date/Time"),
        "app_version": version,
        "build_version": build_version,
        "bundle_id": _line_value(text, "Identifier"),
        "pid": pid,
        "proc_path": _line_value(text, "Path"),
        "parent_process": parent_process,
        "parent_pid": parent_pid,
        "exception_type": exception_type.split(" ", 1)[0] if exception_type else None,
        "exception_signal": "SIGABRT" if "SIGABRT" in (exception_type or "") or "Abort trap" in termination else None,
        "termination_namespace": termination_namespace,
        "termination_code": termination_code,
        "termination_indicator": termination_indicator,
        "application_specific_information": _application_specific_information(text),
    }


def _codex_crash_report_paths(diagnostic_root: pathlib.Path) -> list[pathlib.Path]:
    patterns = ("Codex-*.ips", "Codex_*.ips", "Codex*.ips", "Codex-*.crash", "Codex_*.crash", "Codex*.crash")
    seen: set[pathlib.Path] = set()
    paths: list[pathlib.Path] = []
    for pattern in patterns:
        for path in diagnostic_root.glob(pattern):
            if path in seen:
                continue
            seen.add(path)
            paths.append(path)
    return sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)


def _recent_codex_crash_reports(
    *,
    pid: int | None = None,
    limit: int = 3,
    since_epoch: float | None = None,
    exclude_paths: set[str] | None = None,
) -> list[dict[str, Any]]:
    diagnostic_root = DIAGNOSTIC_REPORTS_ROOT
    exclude_paths = exclude_paths or set()
    try:
        paths = _codex_crash_report_paths(diagnostic_root)
    except OSError:
        return []
    reports: list[dict[str, Any]] = []
    for path in paths:
        if str(path) in exclude_paths:
            continue
        if since_epoch is not None:
            try:
                if path.stat().st_mtime < since_epoch:
                    continue
            except OSError:
                continue
        report = _parse_codex_crash_report(path)
        if not report:
            continue
        if pid is not None and report.get("pid") != pid:
            continue
        reports.append(report)
        if len(reports) >= limit:
            break
    return reports


def _desktop_crash_summary(reports: list[dict[str, Any]]) -> dict[str, Any]:
    latest = reports[0] if reports else None
    return {
        "detected": bool(latest),
        "status": "desktop_launch_crashed" if latest else "not_detected",
        "latest": latest,
        "report_count": len(reports),
        "app_version": latest.get("app_version") if latest else None,
        "build_version": latest.get("build_version") if latest else None,
        "termination_namespace": latest.get("termination_namespace") if latest else None,
        "termination_code": latest.get("termination_code") if latest else None,
        "termination_indicator": latest.get("termination_indicator") if latest else None,
        "exception_type": latest.get("exception_type") if latest else None,
        "exception_signal": latest.get("exception_signal") if latest else None,
    }


def _main_chat_targets(targets: Any) -> list[dict[str, Any]]:
    if not isinstance(targets, list):
        return []
    matches: list[dict[str, Any]] = []
    for target in targets:
        if not isinstance(target, dict) or target.get("type") != "page":
            continue
        url = str(target.get("url") or "")
        if "?hostId=local" in url and "initialRoute=" not in url:
            matches.append(dict(target))
    return matches


def _cdp_targets_summary(port: int) -> list[dict[str, Any]]:
    payload, _error = _read_cdp_json(port, "/json")
    if not isinstance(payload, list):
        return []
    rows: list[dict[str, Any]] = []
    for target in payload:
        if not isinstance(target, Mapping):
            continue
        rows.append(
            {
                "id": target.get("id"),
                "type": target.get("type"),
                "title": target.get("title"),
                "url": target.get("url"),
                "webSocketDebuggerUrl": target.get("webSocketDebuggerUrl"),
                "main_chat_target": bool(
                    target.get("type") == "page"
                    and "?hostId=local" in str(target.get("url") or "")
                    and "initialRoute=" not in str(target.get("url") or "")
                ),
            }
        )
    return rows


def _probe_cdp_port(port: int) -> dict[str, Any]:
    targets_payload, targets_error = _read_cdp_json(port, "/json")
    # Preserve the historical /json/version check as the reachability source;
    # /json may be reachable while /json/version reports more precise browser
    # metadata and gives better errors for blocked ports.
    version_metadata, version_metadata_error = _read_cdp_json(port, "/json/version")
    targets = targets_payload if isinstance(targets_payload, list) else []
    main_targets = _main_chat_targets(targets)
    errors = [error for error in (targets_error, version_metadata_error) if error]
    return {
        "port": port,
        "reachable": version_metadata is not None or targets_payload is not None,
        "json_version_available": version_metadata is not None,
        "target_count": len(targets),
        "main_chat_target_found": bool(main_targets),
        "main_chat_targets": [
            {
                "id": target.get("id"),
                "title": target.get("title"),
                "url": target.get("url"),
                "webSocketDebuggerUrl": target.get("webSocketDebuggerUrl"),
            }
            for target in main_targets[:3]
        ],
        "browser": (version_metadata or {}).get("Browser") if isinstance(version_metadata, dict) else None,
        "webSocketDebuggerUrl": (
            (version_metadata or {}).get("webSocketDebuggerUrl")
            if isinstance(version_metadata, dict)
            else None
        ),
        "targets": _cdp_targets_summary(port),
        "errors": errors,
    }


def diagnose_cdp(
    *,
    requested_port: int = DEFAULT_PORT,
    scan: bool = True,
    scan_ports: str = "",
) -> dict[str, Any]:
    process_rows = _codex_process_rows()
    process_probe_available = _process_probe_available(process_rows)
    process_ports = _remote_debugging_ports_from_processes(process_rows)
    ports = _parse_port_list(scan_ports, requested_port=requested_port, process_ports=process_ports)
    requested_probe = _probe_cdp_port(requested_port)
    scanned = []
    if scan:
        for port in ports:
            scanned.append(requested_probe if port == requested_port else _probe_cdp_port(port))
    else:
        scanned = [requested_probe]
    best = next((row for row in scanned if row.get("main_chat_target_found")), None)
    if best is None:
        best = next((row for row in scanned if row.get("reachable")), None)
    requested_reachable = bool(requested_probe.get("reachable"))
    discovered_other = best if best and int(best.get("port") or 0) != requested_port else None
    app_bundle = _codex_app_bundle_diagnostics()
    recovery_commands = _codex_recovery_commands(requested_port=requested_port, app_bundle=app_bundle)
    recovery_command = recovery_commands["primary"]

    if not process_probe_available:
        app_state = "process_probe_unavailable" if not requested_reachable and not discovered_other else "running_with_cdp_process_probe_unavailable"
    elif not process_rows:
        app_state = "not_observed"
    elif requested_reachable:
        app_state = "running_with_cdp"
    elif discovered_other:
        app_state = "running_with_cdp_on_different_port"
    else:
        app_state = "running_without_reachable_cdp"

    if requested_reachable and requested_probe.get("main_chat_target_found"):
        status = "ok"
        recommended_action = "Codex CDP is reachable and the main chat target is visible."
    elif discovered_other and discovered_other.get("main_chat_target_found"):
        status = "wrong_port"
        recommended_action = (
            f"Codex main chat is reachable on port {discovered_other['port']}; rerun with "
            f"--port {discovered_other['port']} or relaunch with the requested recovery command."
        )
    elif requested_reachable:
        status = "degraded"
        recommended_action = "Codex CDP is reachable, but the main chat target was not discovered; focus the main Codex window or relaunch with the recovery command."
    elif discovered_other:
        status = "degraded_wrong_port"
        recommended_action = (
            f"A CDP endpoint is reachable on port {discovered_other['port']}, but no Codex main chat target was found there."
        )
    else:
        status = "unavailable"
        recommended_action = "Relaunch Codex with remote debugging enabled, then rerun preflight."

    recovery_steps = []
    if not process_probe_available:
        recovery_steps.append(
            "Process listing is unavailable from this sandbox, so trust CDP port probes and listener rows over process rows."
        )
    launch_services_metadata = (
        app_bundle.get("launch_services_metadata")
        if isinstance(app_bundle.get("launch_services_metadata"), Mapping)
        else {}
    )
    if app_bundle.get("bundle_exists") and launch_services_metadata and not launch_services_metadata.get("available"):
        recovery_steps.append(
            "LaunchServices metadata cannot resolve the Codex bundle even though the executable exists; re-register or reinstall the app before expecting `open -a Codex` to work."
        )
        recovery_steps.append(
            f"/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f {shlex.quote(_text(app_bundle.get('bundle_path')))}"
        )
    if status not in {"ok", "wrong_port"}:
        recovery_steps.extend(
            [
                "Quit any already-running Codex app before relying on new launch arguments; macOS open may only focus an existing app.",
                recovery_command or f"open -a {CODEX_APP_NAME} --args --remote-debugging-port={requested_port}",
                f"./repo-python tools/meta/bridge/codex_driver.py --port {requested_port} doctor --json",
                f"./repo-python tools/meta/bridge/codex_driver.py --port {requested_port} preflight --json --no-launch",
            ]
        )
        launchservices_command = recovery_commands.get("open_bundle") or recovery_commands.get("open_by_name")
        direct_command = recovery_commands.get("direct_executable")
        if launchservices_command and launchservices_command != recovery_command:
            recovery_steps.insert(2, f"If LaunchServices is healthy, this also works: {launchservices_command}")
        if direct_command and direct_command != recovery_command:
            recovery_steps.insert(2, f"If LaunchServices cannot open the bundle, use the executable fallback: {direct_command}")
    elif status == "wrong_port":
        recovery_steps.extend(
            [
                f"Use the discovered port for this run: ./repo-python tools/meta/bridge/codex_driver.py --port {best['port']} preflight --json --no-launch",
                f"Relaunch Codex with {recovery_command} when the runtime must standardize on port {requested_port}.",
            ]
        )
    recent_crash_reports = _recent_codex_crash_reports(limit=3)
    recent_desktop_crash = _desktop_crash_summary(recent_crash_reports)

    return {
        "kind": "codex_driver_doctor",
        "status": status,
        "port": requested_port,
        "host": CDP_HOST,
        "app_launch_state": app_state,
        "port_reachable": requested_reachable,
        "json_version_available": requested_probe.get("json_version_available"),
        "target_count": requested_probe.get("target_count"),
        "main_chat_target_found": requested_probe.get("main_chat_target_found"),
        "main_chat_targets": requested_probe.get("main_chat_targets") or [],
        "best_port": best.get("port") if best else None,
        "best_port_main_chat_target_found": bool(best and best.get("main_chat_target_found")),
        "best_port_reason": (
            "main_chat_target_found"
            if best and best.get("main_chat_target_found")
            else ("reachable_cdp_endpoint" if best else "none")
        ),
        "requested_port_probe": requested_probe,
        "scanned_ports": ports if scan else [requested_port],
        "scan_enabled": bool(scan),
        "port_probes": scanned,
        "reachable_cdp_ports": [row["port"] for row in scanned if row.get("reachable")],
        "observed_remote_debugging_ports": process_ports,
        "process_probe_available": process_probe_available,
        "port_listeners": _listener_rows_for_ports(ports if scan else [requested_port]),
        "processes": process_rows,
        "process_summary": _codex_process_summary(process_rows),
        "app_bundle": app_bundle,
        "expected_remote_debugging_arg": f"--remote-debugging-port={requested_port}",
        "recovery_command": recovery_command,
        "recovery_commands": recovery_commands,
        "use_discovered_port_command": (
            f"./repo-python tools/meta/bridge/codex_driver.py --port {best['port']} preflight --json --no-launch"
            if best and best.get("main_chat_target_found")
            else None
        ),
        "recommended_action": recommended_action,
        "recovery_steps": recovery_steps,
        "recent_desktop_crash": recent_desktop_crash,
        "recent_crash_reports": recent_crash_reports,
        "sandbox_process_probe_limited": not process_probe_available,
        "errors": requested_probe.get("errors") or [],
    }


# =============================================================================
# CDP CLIENT
# =============================================================================


def _capped_backoff_delays(
    *,
    attempts: int,
    initial_delay_s: float = CDP_CONNECT_INITIAL_BACKOFF_S,
    max_delay_s: float = CDP_CONNECT_MAX_BACKOFF_S,
) -> list[float]:
    """Return retry sleeps between attempts using capped exponential backoff."""
    if attempts <= 1:
        return []
    delays: list[float] = []
    delay = initial_delay_s
    for _ in range(attempts - 1):
        delays.append(min(delay, max_delay_s))
        delay = min(delay * 2, max_delay_s)
    return delays


def _connect_socket_with_backoff(
    host: str,
    port: int,
    *,
    timeout_s: float,
    attempts: int = CDP_CONNECT_ATTEMPTS,
    sleep_fn=None,
) -> socket.socket:
    """Connect to CDP, tolerating the short window where Electron is still mounting.

    Pattern: capped WebSocket reconnect backoff, adapted from wterm
    `packages/@wterm/core/src/transport.ts`.
    """
    sleep = sleep_fn or time.sleep
    delays = _capped_backoff_delays(attempts=attempts)
    last_error: OSError | None = None
    for attempt_index in range(attempts):
        try:
            return socket.create_connection((host, port), timeout=timeout_s)
        except OSError as exc:
            last_error = exc
            if attempt_index >= attempts - 1:
                break
            sleep(delays[attempt_index])
    if last_error is None:
        raise OSError(f"unable to connect to {host}:{port}")
    raise last_error


class CDPClient:
    """Tiny WebSocket JSON-RPC 2.0 client for Chrome DevTools Protocol.

    Blocking I/O with per-call deadline. stdlib only.
    """

    def __init__(self, host: str, port: int, path: str, timeout_s: float = 10.0):
        self.s = _connect_socket_with_backoff(host, port, timeout_s=timeout_s)
        self.s.settimeout(timeout_s)
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.s.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        self.next_id = 1

    def _frame_send(self, payload: bytes) -> None:
        mask = secrets.token_bytes(4)
        L = len(payload)
        hdr = bytes([0x81])
        if L < 126:
            hdr += bytes([0x80 | L])
        elif L < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack(">H", L)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack(">Q", L)
        hdr += mask
        self.s.sendall(hdr + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def _frame_recv(self) -> Optional[dict]:
        h = self.s.recv(2)
        if len(h) < 2:
            return None
        plen = h[1] & 0x7F
        if plen == 126:
            plen = struct.unpack(">H", self.s.recv(2))[0]
        elif plen == 127:
            plen = struct.unpack(">Q", self.s.recv(8))[0]
        data = b""
        while len(data) < plen:
            chunk = self.s.recv(plen - len(data))
            if not chunk:
                break
            data += chunk
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {"_raw": data[:200].decode(errors="replace")}

    def call(
        self,
        method: str,
        params: Optional[dict] = None,
        timeout_s: float = 15.0,
    ) -> Optional[dict]:
        mid = self.next_id
        self.next_id += 1
        payload = json.dumps({"id": mid, "method": method, "params": params or {}}).encode()
        self._frame_send(payload)
        end = time.time() + timeout_s
        while time.time() < end:
            self.s.settimeout(max(0.05, end - time.time()))
            try:
                msg = self._frame_recv()
            except socket.timeout:
                continue
            if msg is None:
                return None
            if msg.get("id") == mid:
                return msg
        return None

    def evaluate(self, expr: str, await_promise: bool = False, timeout_s: float = 15.0):
        r = self.call(
            "Runtime.evaluate",
            {"expression": expr, "returnByValue": True, "awaitPromise": await_promise},
            timeout_s=timeout_s,
        )
        if not r:
            return {"_exc": "no response from Runtime.evaluate"}
        ex = r.get("result", {}).get("exceptionDetails")
        if ex:
            desc = (ex.get("exception") or {}).get("description") or ex.get("text") or "?"
            return {"_exc": desc[:600]}
        return r.get("result", {}).get("result", {}).get("value")

    def close(self) -> None:
        try:
            self.s.close()
        except OSError:
            pass


# =============================================================================
# DATACLASSES
# =============================================================================


@dataclasses.dataclass
class ThreadRow:
    """A thread row in the Codex sidebar."""
    thread_id: str
    title: str
    kind: str
    active: bool
    pinned: bool


@dataclasses.dataclass
class Turn:
    """A single prompt↔response pair extracted from the rollout JSONL."""
    turn_id: str
    user_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_ms: Optional[int]
    agent_messages: list[str]
    tool_calls: list[dict]
    last_agent_message: Optional[str]
    token_usage: Optional[dict]


# =============================================================================
# DRIVER
# =============================================================================


class CodexDriver:
    """High-level driver for the Codex desktop app via CDP + user simulation.

    Usage:
        d = CodexDriver.connect()          # launches Codex if needed
        d.send_message("do a thing")       # injects into currently focused thread
        for ev in d.tail_rollout(tid):     # stream events
            ...
        d.close()
    """

    def __init__(
        self,
        cdp: CDPClient,
        port: int,
        *,
        target_id: str | None = None,
        target_url: str | None = None,
        target_title: str | None = None,
    ):
        self.cdp = cdp
        self.port = port
        self.target_id = target_id
        self.target_url = target_url
        self.target_title = target_title
        self.cdp.call("Runtime.enable")
        # Install manager-capture prototype wrap once (idempotent; safe read-only)
        self._ensure_manager_captured()

    # ---------------------------------------------------------------- lifecycle

    @classmethod
    def ensure_running(cls, port: int = DEFAULT_PORT, wait_s: float = 4.0) -> bool:
        """Launch Codex.app with --remote-debugging-port if not already listening."""
        if _cdp_port_reachable(port, timeout_s=1.5):
            return True
        for command in _codex_launch_commands(port=port):
            try:
                if command and command[0] == "open":
                    subprocess.run(command, check=False, capture_output=True, text=True)
                else:
                    subprocess.Popen(
                        command,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
            except Exception:
                continue
            end = time.time() + wait_s
            while time.time() < end:
                try:
                    urllib.request.urlopen(f"http://{CDP_HOST}:{port}/json/version", timeout=1.0)
                    return True
                except (urllib.error.URLError, OSError):
                    time.sleep(0.2)
        return False

    @classmethod
    def ensure_cdp_window(cls, port: int = DEFAULT_PORT, wait_s: float = 8.0) -> dict[str, Any]:
        """Ensure a CDP-enabled main Codex window exists, preferring direct launch.

        `open -a Codex --args ...` may only focus an already-running non-CDP
        app. For manager-backed automation we need a debuggable second window,
        so this path tries the bundle executable first and only falls back to
        LaunchServices routes if direct launch is unavailable.
        """
        initial = _probe_cdp_port(port)
        if initial.get("reachable") and initial.get("main_chat_target_found"):
            return {
                "ok": True,
                "status": "already_available",
                "port": port,
                "initial_probe": initial,
                "attempts": [],
            }
        attempts: list[dict[str, Any]] = []
        for spec in _codex_cdp_window_launch_specs(port=port):
            command = list(spec.get("command") or [])
            if not command:
                continue
            attempt = {
                "method": spec.get("method"),
                "command": command,
                "command_text": shlex.join(command),
                "returncode": None,
                "error": None,
                "probe": None,
            }
            try:
                if command[0] == "open":
                    proc = subprocess.run(command, check=False, capture_output=True, text=True)
                    attempt["returncode"] = proc.returncode
                    attempt["stdout"] = (proc.stdout or "").strip()
                    attempt["stderr"] = (proc.stderr or "").strip()
                else:
                    proc = subprocess.Popen(
                        command,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    attempt["pid"] = proc.pid
            except Exception as exc:
                attempt["error"] = str(exc)
                attempts.append(attempt)
                continue
            probe = _wait_for_cdp_probe(port, wait_s=wait_s)
            attempt["probe"] = probe
            attempts.append(attempt)
            if probe.get("reachable") and probe.get("main_chat_target_found"):
                return {
                    "ok": True,
                    "status": "launched",
                    "port": port,
                    "method": attempt.get("method"),
                    "initial_probe": initial,
                    "probe": probe,
                    "attempts": attempts,
                }
        final_probe = _probe_cdp_port(port)
        return {
            "ok": False,
            "status": "unavailable",
            "port": port,
            "initial_probe": initial,
            "probe": final_probe,
            "attempts": attempts,
            "recovery_command": _codex_recovery_commands(requested_port=port).get("direct_executable"),
        }

    @classmethod
    def connect(cls, port: int = DEFAULT_PORT) -> "CodexDriver":
        """Connect to Codex (launching it if needed), return a driver bound to main chat."""
        if not cls.ensure_running(port=port):
            raise RuntimeError(f"Codex CDP port {port} not reachable")
        targets = json.loads(
            urllib.request.urlopen(f"http://{CDP_HOST}:{port}/json", timeout=3.0).read()
        )
        main = None
        for t in targets:
            if t.get("type") != "page":
                continue
            url = t.get("url", "")
            if "?hostId=local" in url and "initialRoute=" not in url:
                main = t
                break
        if not main:
            raise RuntimeError("Codex main chat webContents not found")
        ws_path = "/" + main["webSocketDebuggerUrl"].split("/", 3)[3]
        cdp = CDPClient(CDP_HOST, port, ws_path)
        return cls(
            cdp,
            port=port,
            target_id=main.get("id"),
            target_url=main.get("url"),
            target_title=main.get("title"),
        )

    def close(self) -> None:
        self.cdp.close()

    # ---------------------------------------------------------------- internals

    _MANAGER_CAPTURE_JS = r"""
    (async () => {
      const state = window.__aiwf_capture_state || {
        attempts: 0,
        chunks: [],
        wrapped_exports: [],
        errors: [],
        scanned_objects: 0,
      };
      window.__aiwf_capture_state = state;
      state.attempts = (state.attempts || 0) + 1;

      function looksLikeManager(value) {
        return !!(
          value &&
          typeof value === "object" &&
          typeof value.sendRequest === "function" &&
          value.conversations instanceof Map &&
          value.streamingConversations instanceof Set
        );
      }

      function rememberManager(value, source) {
        if (!looksLikeManager(value)) return false;
        window.__aiwf_manager = value;
        state.manager_source = source;
        return true;
      }

      if (rememberManager(window.__aiwf_manager, "window.__aiwf_manager")) {
        return { captured: true, cached: true, ...state };
      }

      async function discoverChunks() {
        const names = new Set(state.chunks || []);
        const scriptUrls = [...document.scripts].map((script) => script.src).filter(Boolean);
        for (const scriptUrl of scriptUrls) {
          if (!/\/assets\/index-[^/]+\.js$/.test(scriptUrl)) continue;
          try {
            const text = await (await fetch(scriptUrl)).text();
            for (const match of text.matchAll(/(?:app-server-manager-[A-Za-z0-9_-]+|send-app-server-request-[A-Za-z0-9_-]+)\.js/g)) {
              names.add(match[0]);
            }
          } catch (error) {
            state.errors.push(`index_discovery:${String(error).slice(0, 160)}`);
          }
        }
        state.chunks = [...names];
        return state.chunks;
      }

      function wrapPrototype(value, exportName, chunkName) {
        if (!value || !value.prototype || typeof value.prototype.sendRequest !== "function") return false;
        const proto = value.prototype;
        if (proto.__aiwf_wrapped_sendRequest) return true;
        const original = proto.sendRequest;
        proto.sendRequest = function(...args) {
          rememberManager(this, `${chunkName}:${exportName}.prototype.sendRequest`);
          return original.apply(this, args);
        };
        proto.__aiwf_wrapped_sendRequest = true;
        state.wrapped_exports.push(`${chunkName}:${exportName}`);
        return true;
      }

      function scanForLiveManager() {
        const queue = [
          { value: window.__codexRoot?._internalRoot?.current, path: "__codexRoot._internalRoot.current", depth: 0 },
        ];
        const seen = new Set();
        while (queue.length && seen.size < 4000) {
          const item = queue.shift();
          const value = item.value;
          if (!value || (typeof value !== "object" && typeof value !== "function") || seen.has(value)) continue;
          if (value === window || value === document || value instanceof Node) continue;
          seen.add(value);
          if (rememberManager(value, item.path)) {
            state.scanned_objects = seen.size;
            return true;
          }
          if (item.depth >= 9) continue;
          let names = [];
          try {
            names = Object.getOwnPropertyNames(value);
          } catch (_) {
            continue;
          }
          for (const name of names.slice(0, 80)) {
            let child;
            try {
              child = value[name];
            } catch (_) {
              continue;
            }
            if (child && (typeof child === "object" || typeof child === "function") && !seen.has(child)) {
              queue.push({ value: child, path: `${item.path}.${name}`, depth: item.depth + 1 });
            }
          }
        }
        state.scanned_objects = seen.size;
        return false;
      }

      const chunks = await discoverChunks();
      for (const chunkName of chunks) {
        try {
          const mod = await import(`./assets/${chunkName}`);
          for (const [exportName, value] of Object.entries(mod)) {
            wrapPrototype(value, exportName, chunkName);
          }
        } catch (error) {
          state.errors.push(`import:${chunkName}:${String(error).slice(0, 160)}`);
        }
      }

      scanForLiveManager();
      return { captured: !!window.__aiwf_manager, cached: false, ...state };
    })()
    """

    def _ensure_manager_captured(self) -> dict:
        return self.cdp.evaluate(self._MANAGER_CAPTURE_JS, await_promise=True, timeout_s=15.0)

    def target_snapshot(self) -> dict[str, Any]:
        """Capture identity and read-only affordances for the connected CDP target."""
        manager_capture = self._ensure_manager_captured()
        process_rows = _codex_process_rows()
        renderer = self.cdp.evaluate(
            r"""
            (() => {
              const composer = document.querySelector('.ProseMirror[contenteditable="true"]');
              const buttons = [...document.querySelectorAll('button, [role=button]')]
                .map((el) => (el.textContent || '').trim())
                .filter(Boolean)
                .slice(0, 40);
              return {
                location: location.href,
                title: document.title,
                ready_state: document.readyState,
                codex_window_type: window.codexWindowType || null,
                user_agent: navigator.userAgent,
                viewport: {
                  inner_width: window.innerWidth,
                  inner_height: window.innerHeight,
                  device_pixel_ratio: window.devicePixelRatio,
                },
                composer_available: !!composer,
                sidebar_thread_count: document.querySelectorAll('[data-app-action-sidebar-thread-id]').length,
                active_thread_id: document.querySelector('[data-app-action-sidebar-thread-active="true"]')
                  ?.getAttribute('data-app-action-sidebar-thread-id') || null,
                buttons,
              };
            })()
            """,
            timeout_s=8.0,
        )
        browser_window: dict[str, Any] | None = None
        if self.target_id:
            response = self.cdp.call(
                "Browser.getWindowForTarget",
                {"targetId": self.target_id},
                timeout_s=5.0,
            )
            if response and isinstance(response.get("result"), Mapping):
                browser_window = dict(response["result"])
            elif response and isinstance(response.get("error"), Mapping):
                browser_window = {"error": response["error"]}
        return {
            "kind": "codex_driver_window_snapshot",
            "port": self.port,
            "target": {
                "id": self.target_id,
                "title": self.target_title,
                "url": self.target_url,
            },
            "browser_window": browser_window,
            "renderer": renderer,
            "manager_capture": manager_capture,
            "cdp_targets": _cdp_targets_summary(self.port),
            "processes": process_rows,
            "process_summary": _codex_process_summary(process_rows),
        }

    def manager_probe(
        self,
        *,
        app_query: str = "GitHub",
        thread_id: str | None = None,
        app_limit: int = 200,
        thread_limit: int = 10,
        force_refetch: bool = False,
    ) -> dict[str, Any]:
        """Read the Electron AppServer manager for loaded threads and app state.

        This intentionally uses read-only manager requests. It proves whether
        the renderer owns a live AppServer bridge and whether connectors such as
        GitHub are visible for that runtime, without submitting a turn.
        """
        manager_capture = self._ensure_manager_captured()
        probe_args = {
            "appQuery": app_query,
            "threadId": thread_id,
            "appLimit": max(1, int(app_limit)),
            "threadLimit": max(1, int(thread_limit)),
            "forceRefetch": bool(force_refetch),
        }
        expr = rf"""
        (async (probeArgs) => {{
          const out = {{
            captured: false,
            manager_source: window.__aiwf_capture_state?.manager_source || null,
            current_thread_id: null,
            loaded_threads: null,
            app_query: probeArgs.appQuery,
            app_matches: [],
            connector_status: null,
            errors: [],
          }};
          const m = window.__aiwf_manager;
          if (!m || typeof m.sendRequest !== "function") {{
            out.errors.push("manager_unavailable");
            return out;
          }}
          out.captured = true;
          const activeThreadId = document.querySelector('[data-app-action-sidebar-thread-active="true"]')
            ?.getAttribute('data-app-action-sidebar-thread-id') || null;
          out.current_thread_id = activeThreadId;
          out.probed_thread_id = probeArgs.threadId || activeThreadId;
          const query = String(probeArgs.appQuery || "").toLowerCase();
          try {{
            const loaded = await m.sendRequest("thread/loaded/list", {{
              limit: probeArgs.threadLimit,
            }});
            out.loaded_threads = loaded;
          }} catch (error) {{
            out.errors.push(`thread/loaded/list:${{String(error).slice(0, 240)}}`);
          }}
          try {{
            const apps = await m.sendRequest("app/list", {{
              limit: probeArgs.appLimit,
              threadId: out.probed_thread_id,
              forceRefetch: !!probeArgs.forceRefetch,
            }});
            const data = Array.isArray(apps?.data) ? apps.data : [];
            out.app_count_scanned = data.length;
            const matches = data.filter((app) => {{
              if (!query) return true;
              const haystack = [
                app?.id,
                app?.name,
                app?.description,
                ...(Array.isArray(app?.pluginDisplayNames) ? app.pluginDisplayNames : []),
              ].filter(Boolean).join(" ").toLowerCase();
              return haystack.includes(query);
            }}).slice(0, 20).map((app) => ({{
              id: app?.id || null,
              name: app?.name || null,
              description: app?.description || null,
              distributionChannel: app?.distributionChannel || null,
              installUrl: app?.installUrl || null,
              isAccessible: !!app?.isAccessible,
              isEnabled: !!app?.isEnabled,
              labels: app?.labels || null,
              pluginDisplayNames: Array.isArray(app?.pluginDisplayNames) ? app.pluginDisplayNames : [],
            }}));
            out.app_matches = matches;
            const github = matches.find((app) => String(app.name || "").toLowerCase() === "github")
              || matches.find((app) => String(app.id || "").toLowerCase().includes("github"));
            out.connector_status = github ? {{
              query: probeArgs.appQuery,
              found: true,
              id: github.id,
              name: github.name,
              isAccessible: github.isAccessible,
              isEnabled: github.isEnabled,
              installUrl: github.installUrl,
              labels: github.labels,
            }} : {{
              query: probeArgs.appQuery,
              found: false,
              id: null,
              name: null,
              isAccessible: false,
              isEnabled: false,
              installUrl: null,
              labels: null,
            }};
          }} catch (error) {{
            out.errors.push(`app/list:${{String(error).slice(0, 240)}}`);
          }}
          return out;
        }})({json.dumps(probe_args)})
        """
        payload = self.cdp.evaluate(expr, await_promise=True, timeout_s=30.0) or {}
        return {
            "kind": "codex_driver_manager_probe",
            "port": self.port,
            "target": {
                "id": self.target_id,
                "title": self.target_title,
                "url": self.target_url,
            },
            "manager_capture": manager_capture,
            **payload,
        }

    def manager_start(
        self,
        *,
        message: str,
        cwd: pathlib.Path,
        model: str = "gpt-5.4",
        effort: str = "medium",
        approval_policy: str = "never",
        wait: bool = False,
        max_wait_s: float = 120.0,
        thread_id_placeholder: str | None = None,
        session_id_placeholder: str | None = None,
        session_id_prefix: str = "codex-manager:",
    ) -> dict[str, Any]:
        """Start a new Codex thread through the renderer's own manager.

        This is deliberately narrower than raw AppServer RPC: it calls the same
        high-level manager method the UI uses to create a conversation, then
        verifies completion from the rollout file when requested.
        """
        self._ensure_manager_captured()
        cwd = cwd.expanduser().resolve()
        start_args = {
            "message": message,
            "cwd": str(cwd),
            "model": model,
            "effort": effort,
            "approvalPolicy": approval_policy,
            "threadIdPlaceholder": thread_id_placeholder,
            "sessionIdPlaceholder": session_id_placeholder,
            "sessionIdPrefix": session_id_prefix,
        }
        expr = rf"""
        (async (payload) => {{
          const m = window.__aiwf_manager;
          if (!m || typeof m.startConversation !== "function") {{
            return {{ ok: false, status: "manager_unavailable", error: "startConversation unavailable" }};
          }}
          try {{
            const turnInput = [{{ type: "text", text: payload.message, text_elements: [] }}];
            const applyThreadIdentity = (conversationId) => {{
              const threadId = String(conversationId || "");
              if (!threadId) return;
              const sessionId = `${{payload.sessionIdPrefix || "codex-manager:"}}${{threadId}}`;
              if (payload.threadIdPlaceholder) {{
                turnInput[0].text = String(turnInput[0].text).split(payload.threadIdPlaceholder).join(threadId);
              }}
              if (payload.sessionIdPlaceholder) {{
                turnInput[0].text = String(turnInput[0].text).split(payload.sessionIdPlaceholder).join(sessionId);
              }}
            }};
            const threadId = await m.startConversation({{
              input: turnInput,
              collaborationMode: {{
                mode: "default",
                settings: {{
                  model: payload.model,
                  reasoning_effort: payload.effort,
                  developer_instructions: null,
                }},
              }},
              serviceTier: null,
              workspaceRoots: [payload.cwd],
              workspaceKind: "project",
              cwd: payload.cwd,
              permissions: {{
                approvalPolicy: payload.approvalPolicy,
                approvalsReviewer: "user",
                sandboxPolicy: {{ type: "dangerFullAccess" }},
              }},
              attachments: [],
              commentAttachments: [],
              skipAutoTitleGeneration: true,
            }}, {{
              runFirstTurnInBackground: true,
              beforeFirstTurn: (context) => applyThreadIdentity(context?.conversationId),
            }});
            applyThreadIdentity(threadId);
            const c = m.conversations.get(threadId);
            return {{
              ok: true,
              status: "started",
              thread_id: threadId,
              session_id: `${{payload.sessionIdPrefix || "codex-manager:"}}${{threadId}}`,
              cwd: c?.cwd || payload.cwd,
              rollout_path: c?.rolloutPath || null,
              title: c?.title || null,
              runtime: c?.threadRuntimeStatus || null,
              streaming: Array.from(m.streamingConversations || []).includes(threadId),
            }};
          }} catch (error) {{
            return {{
              ok: false,
              status: "failed_to_start",
              error: String(error),
              stack: String(error && error.stack || "").slice(0, 1200),
            }};
          }}
        }})({json.dumps(start_args)})
        """
        started = self.cdp.evaluate(expr, await_promise=True, timeout_s=30.0) or {}
        payload: dict[str, Any] = {
            "kind": "codex_driver_manager_start",
            "port": self.port,
            "target": {
                "id": self.target_id,
                "title": self.target_title,
                "url": self.target_url,
            },
            **started,
        }
        thread_id = _text(payload.get("thread_id"))
        if not wait or not thread_id or not payload.get("ok"):
            return payload

        deadline = time.time() + max(float(max_wait_s), 0.0)
        latest: Turn | None = None
        while time.time() < deadline:
            latest = self.latest_turn(thread_id)
            if latest and latest.completed_at:
                break
            time.sleep(0.5)
        if latest and latest.completed_at:
            payload["status"] = "completed"
            payload["turn"] = dataclasses.asdict(latest)
        else:
            payload["status"] = "timeout"
            payload["turn"] = dataclasses.asdict(latest) if latest else None
        return payload

    def capture_screenshot(self, path: pathlib.Path) -> dict[str, Any]:
        """Write a PNG screenshot for the connected renderer target."""
        self.cdp.call("Page.enable", timeout_s=5.0)
        response = self.cdp.call(
            "Page.captureScreenshot",
            {"format": "png", "captureBeyondViewport": False},
            timeout_s=15.0,
        )
        if not response or not isinstance(response.get("result"), Mapping):
            return {"status": "failed", "path": str(path), "reason": "captureScreenshot returned no result"}
        data = response["result"].get("data")
        if not isinstance(data, str) or not data:
            return {"status": "failed", "path": str(path), "reason": "captureScreenshot returned no image data"}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(data))
        return {
            "status": "written",
            "path": str(path),
            "bytes": path.stat().st_size,
        }

    # ------------------------------------------------------------ observability

    def list_threads(self, limit: int = 50) -> list[ThreadRow]:
        """All thread rows currently visible in the sidebar."""
        expr = rf"""
        (() => {{
          const rows = [...document.querySelectorAll('[data-app-action-sidebar-thread-id]')].slice(0, {limit});
          return rows.map(r => ({{
            thread_id: r.getAttribute('data-app-action-sidebar-thread-id'),
            title: r.getAttribute('data-app-action-sidebar-thread-title'),
            kind: r.getAttribute('data-app-action-sidebar-thread-kind'),
            active: r.getAttribute('data-app-action-sidebar-thread-active') === 'true',
            pinned: r.getAttribute('data-app-action-sidebar-thread-pinned') === 'true',
          }}));
        }})()
        """
        data = self.cdp.evaluate(expr) or []
        return [ThreadRow(**d) for d in data if isinstance(d, dict)]

    def current_thread_id(self) -> Optional[str]:
        """The thread currently loaded in the main pane (active=true in sidebar)."""
        for row in self.list_threads():
            if row.active:
                return row.thread_id
        return None

    def streaming_thread_ids(self) -> list[str]:
        """Thread ids that are currently mid-turn (model generating)."""
        self._ensure_manager_captured()
        expr = r"""
        (() => {
          const m = window.__aiwf_manager;
          if (!m) return [];
          return Array.from(m.streamingConversations || []);
        })()
        """
        return self.cdp.evaluate(expr) or []

    def conversation_meta(self, thread_id: str) -> Optional[dict]:
        """Metadata for a specific thread from the live manager."""
        self._ensure_manager_captured()
        expr = rf"""
        (() => {{
          const m = window.__aiwf_manager;
          if (!m) return null;
          const c = m.conversations && m.conversations.get && m.conversations.get("{thread_id}");
          if (!c) return null;
          return {{
            id: c.id,
            hostId: c.hostId,
            title: c.title,
            cwd: c.cwd,
            rolloutPath: c.rolloutPath,
            turnCount: c.turns ? c.turns.length : null,
            threadRuntimeStatus: c.threadRuntimeStatus,
            latestModel: c.latestModel,
            latestReasoningEffort: c.latestReasoningEffort,
            hasUnreadTurn: c.hasUnreadTurn,
            resumeState: c.resumeState,
            workspaceKind: c.workspaceKind,
          }};
        }})()
        """
        return self.cdp.evaluate(expr)

    def is_streaming(self, thread_id: str) -> bool:
        return thread_id in self.streaming_thread_ids()

    # ------------------------------------------------------------ rollout disk

    def rollout_path(self, thread_id: str) -> Optional[pathlib.Path]:
        """Locate the rollout JSONL for a thread id. Prefer manager.rolloutPath, fallback to filesystem search."""
        meta = self.conversation_meta(thread_id)
        if meta and meta.get("rolloutPath"):
            p = pathlib.Path(meta["rolloutPath"])
            if p.exists():
                return p
        # Fallback: scan recent days
        for day_offset in (0, -1, -2, -3):
            day = time.gmtime(time.time() + day_offset * 86400)
            d = SESSIONS_ROOT / f"{day.tm_year:04d}" / f"{day.tm_mon:02d}" / f"{day.tm_mday:02d}"
            if not d.exists():
                continue
            for p in d.glob(f"rollout-*-{thread_id}.jsonl"):
                return p
        return None

    def read_rollout_events(self, thread_id: str, tail_n: Optional[int] = None) -> list[dict]:
        """Read all (or tail_n) events from the thread's rollout JSONL as parsed dicts."""
        p = self.rollout_path(thread_id)
        if not p:
            return []
        events: list[dict] = []
        for line in p.read_text().splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        if tail_n is not None:
            events = events[-tail_n:]
        return events

    def extract_turns(self, thread_id: str) -> list[Turn]:
        """Parse rollout into [Turn] — one per turn_id, with user prompt + agent output + tool calls.

        Event attribution rules (empirically verified):
        - task_started / task_complete / agent_message / token_count carry turn_id.
        - user_message has NO turn_id. It appears AFTER task_started on a new turn
          but BEFORE it on resume. So we attach to whichever turn is "currently open"
          (last task_started seen without its matching task_complete) — or, if none
          open, to the NEXT task_started after this user_message.
        - function_call / exec_command_end carry turn_id.
        """
        events = self.read_rollout_events(thread_id)

        order: list[str] = []
        bucket: dict[str, dict] = {}
        active_turn: Optional[str] = None  # most recent task_started without task_complete
        pending_user: Optional[str] = None  # user_message awaiting a task_started

        def get_bucket(tid: str) -> dict:
            if tid not in bucket:
                bucket[tid] = {
                    "turn_id": tid,
                    "user_message": None,
                    "started_at": None,
                    "completed_at": None,
                    "duration_ms": None,
                    "agent_messages": [],
                    "tool_calls": [],
                    "last_agent_message": None,
                    "token_usage": None,
                }
                order.append(tid)
            return bucket[tid]

        for ev in events:
            p = ev.get("payload") or {}
            pt = p.get("type")
            tid = p.get("turn_id")
            ts = ev.get("timestamp")

            if pt == "task_started" and tid:
                b = get_bucket(tid)
                b["started_at"] = ts
                active_turn = tid
                if pending_user and not b["user_message"]:
                    b["user_message"] = pending_user
                    pending_user = None

            elif pt == "task_complete" and tid:
                b = get_bucket(tid)
                b["completed_at"] = ts
                b["duration_ms"] = p.get("duration_ms")
                b["last_agent_message"] = p.get("last_agent_message")
                if active_turn == tid:
                    active_turn = None

            elif pt == "user_message":
                msg = p.get("message") or p.get("text") or ""
                target = tid or active_turn
                if target:
                    b = get_bucket(target)
                    if not b["user_message"]:
                        b["user_message"] = msg
                else:
                    pending_user = msg

            elif pt == "agent_message" and tid:
                msg = p.get("message")
                if msg:
                    get_bucket(tid)["agent_messages"].append(msg)

            elif pt == "exec_command_end" and tid:
                get_bucket(tid)["tool_calls"].append({
                    "kind": "exec",
                    "parsed_cmd": p.get("parsed_cmd"),
                    "command": p.get("command"),
                    "exit_code": p.get("exit_code"),
                    "stdout_preview": (p.get("stdout") or "")[:200],
                    "duration_ms": p.get("duration_ms"),
                })

            elif pt == "function_call" and tid:
                args_raw = p.get("arguments") or ""
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                except json.JSONDecodeError:
                    args = args_raw
                get_bucket(tid)["tool_calls"].append({"kind": "function", "name": p.get("name"), "args": args})

            elif pt == "token_count" and tid:
                get_bucket(tid)["token_usage"] = (p.get("info") or {}).get("total_token_usage") or p.get("info")

        return [Turn(**bucket[tid]) for tid in order]

    def latest_turn(self, thread_id: str) -> Optional[Turn]:
        """The most recent turn (prompt↔response pair) on disk."""
        turns = self.extract_turns(thread_id)
        return turns[-1] if turns else None

    def tail_rollout(
        self,
        thread_id: str,
        poll_s: float = 0.5,
        stop_on_task_complete: bool = True,
        max_wait_s: float = 120.0,
    ) -> Iterator[dict]:
        """Yield rollout events as they're appended. Stops on task_complete by default.

        Caller is responsible for consuming the generator (does not fire if iterator is dropped).
        """
        p = self.rollout_path(thread_id)
        if not p:
            return
        with p.open("rb") as f:
            f.seek(0, 2)  # end
            deadline = time.time() + max_wait_s
            buf = b""
            while time.time() < deadline:
                chunk = f.read()
                if not chunk:
                    time.sleep(poll_s)
                    continue
                buf += chunk
                while b"\n" in buf:
                    line, _, buf = buf.partition(b"\n")
                    if not line.strip():
                        continue
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    yield ev
                    if stop_on_task_complete and (ev.get("payload") or {}).get("type") == "task_complete":
                        return

    # ---------------------------------------------------------- control: mouse

    def _click_xy(self, x: float, y: float) -> None:
        self.cdp.call(
            "Input.dispatchMouseEvent",
            {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1},
        )
        self.cdp.call(
            "Input.dispatchMouseEvent",
            {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1},
        )

    def _click_selector(self, selector: str) -> bool:
        """Click element at center of its bounding rect. Returns True if found+clicked."""
        expr = rf"""
        (() => {{
          const el = document.querySelector({json.dumps(selector)});
          if (!el) return null;
          const b = el.getBoundingClientRect();
          if (b.width <= 0 || b.height <= 0) return null;
          return {{x: b.left + b.width/2, y: b.top + b.height/2}};
        }})()
        """
        pos = self.cdp.evaluate(expr)
        if not pos or "x" not in pos:
            return False
        self._click_xy(pos["x"], pos["y"])
        return True

    def switch_thread(self, thread_id: str, wait_composer_s: float = 1.5) -> bool:
        """Click the sidebar row for this thread, wait for composer to mount."""
        ok = self._click_selector(f'[data-app-action-sidebar-thread-id="{thread_id}"]')
        if not ok:
            return False
        # Wait for composer
        deadline = time.time() + wait_composer_s
        while time.time() < deadline:
            if self.cdp.evaluate(r"!!document.querySelector('.ProseMirror[contenteditable=\"true\"]')"):
                return True
            time.sleep(0.1)
        return False

    # ------------------------------------------------------- control: keyboard

    def _key(self, type_: str, key: str, code: str, text: str = "", modifiers: int = 0, vkey: Optional[int] = None) -> None:
        p: dict = {"type": type_, "key": key, "code": code, "modifiers": modifiers}
        if text:
            p["text"] = text
            p["unmodifiedText"] = text
        if vkey is not None:
            p["windowsVirtualKeyCode"] = vkey
            p["nativeVirtualKeyCode"] = vkey
        self.cdp.call("Input.dispatchKeyEvent", p)

    def _key_press(self, key: str, code: str, text: str = "", modifiers: int = 0, vkey: Optional[int] = None) -> None:
        self._key("keyDown", key, code, text=text, modifiers=modifiers, vkey=vkey)
        self._key("keyUp", key, code, text=text, modifiers=modifiers, vkey=vkey)

    def focus_composer(self) -> bool:
        """Focus the composer input (ProseMirror)."""
        return self._click_selector('.ProseMirror[contenteditable="true"]')

    def type_text(self, text: str, per_char_delay_s: float = 0.0) -> None:
        """Type text into the currently focused element. Each char = keyDown+keyUp."""
        for ch in text:
            # Special handling for newline — Enter doesn't type a newline in ProseMirror
            # by default (it submits). Use Shift+Enter for literal newline.
            if ch == "\n":
                self._key_press("Enter", "Enter", modifiers=_SHIFT, vkey=13)
            else:
                self._key_press(ch, "", text=ch)
            if per_char_delay_s:
                time.sleep(per_char_delay_s)

    def submit(self) -> None:
        """Press Enter — submits the composer."""
        self._key_press("Enter", "Enter", vkey=13)

    def send_message(self, text: str, ensure_focused: bool = True, settle_s: float = 0.15) -> None:
        """Type text + submit. Focuses composer first if requested."""
        if ensure_focused:
            self.focus_composer()
            time.sleep(settle_s)
        self.type_text(text)
        time.sleep(settle_s)
        self.submit()

    def interrupt(self) -> None:
        """Press Escape — interrupts the current turn (if the UI accepts Esc as stop)."""
        self._key_press("Escape", "Escape", vkey=27)

    def new_chat(self, settle_s: float = 0.5) -> bool:
        """Click the sidebar 'New chat' button (safer than Cmd+N: native menu
        shortcuts don't reach the renderer via CDP, and Cmd+N accidentally
        flashed the About dialog in testing).

        The button is labelled 'New chat⌘N' and is the first button with that
        text in the sidebar. After click, composer resets + focuses; the actual
        new thread row appears in the sidebar only after the first send.
        """
        expr = r"""
        (() => {
          const btn = [...document.querySelectorAll('button, [role=button]')]
            .find(e => (e.textContent || '').trim().startsWith('New chat'));
          if (!btn) return null;
          const b = btn.getBoundingClientRect();
          if (b.width <= 0 || b.height <= 0) return null;
          return {x: b.left + b.width/2, y: b.top + b.height/2};
        })()
        """
        pos = self.cdp.evaluate(expr)
        if not pos or "x" not in pos:
            return False
        self._click_xy(pos["x"], pos["y"])
        time.sleep(settle_s)
        return True

    # -------------------------------------------------- higher-level workflow

    def send_and_wait(
        self,
        text: str,
        thread_id: Optional[str] = None,
        max_wait_s: float = 180.0,
    ) -> Optional[Turn]:
        """Send a message + wait until task_complete + return the parsed Turn.

        If thread_id is provided, switches to it first. Otherwise uses the current thread.
        Returns None if the turn didn't complete in max_wait_s.
        """
        if thread_id:
            self.switch_thread(thread_id)
        target_id = thread_id or self.current_thread_id()
        if not target_id:
            raise RuntimeError("No current thread id; pass thread_id explicitly")

        turns_before = len(self.extract_turns(target_id))
        self.send_message(text)

        # Watch rollout for task_complete — use tail_rollout
        start = time.time()
        for _ in self.tail_rollout(target_id, stop_on_task_complete=True, max_wait_s=max_wait_s):
            if time.time() - start > max_wait_s:
                break

        turns_after = self.extract_turns(target_id)
        if len(turns_after) > turns_before:
            return turns_after[-1]
        return None


# =============================================================================
# CLI
# =============================================================================


def _cmd_status(driver: CodexDriver, args) -> int:
    print(f"Codex driver connected on port {driver.port}")
    current = driver.current_thread_id()
    streaming = driver.streaming_thread_ids()
    print(f"  current thread: {current}")
    print(f"  streaming:      {streaming}")
    print(f"  sidebar rows:")
    for r in driver.list_threads(limit=10):
        mark = "*" if r.active else " "
        pinned = "[P]" if r.pinned else "   "
        print(f"    {mark} {pinned} {r.thread_id}  {r.title!r}")
    return 0


def _cmd_status_unavailable(args, exc: Exception) -> int:
    """Emit a machine-readable unavailable status without a traceback."""
    print(
        json.dumps(
            {
                "status": "unavailable",
                "reachable": False,
                "port": args.port,
                "error": str(exc),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cmd_preflight_unavailable(args, exc: Exception | None = None) -> int:
    doctor: dict[str, Any] = {}
    try:
        doctor = diagnose_cdp(requested_port=args.port, scan=True, scan_ports="")
    except Exception as doctor_exc:  # pragma: no cover - host dependent fallback
        doctor = {
            "status": "diagnostic_failed",
            "diagnostic_error": str(doctor_exc),
        }
    doctor_status = _text(doctor.get("status"))
    recovery_command = doctor.get("recovery_command")
    recovery_commands = doctor.get("recovery_commands") if isinstance(doctor.get("recovery_commands"), Mapping) else {}
    payload = {
        "kind": "codex_driver_preflight",
        "status": "unavailable",
        "reachable": False,
        "port": args.port,
        "no_launch": bool(getattr(args, "no_launch", False)),
        "doctor_status": doctor_status or None,
        "app_launch_state": doctor.get("app_launch_state"),
        "port_reachable": bool(doctor.get("port_reachable")),
        "main_chat_target_found": bool(doctor.get("main_chat_target_found")),
        "target_count": doctor.get("target_count"),
        "best_port": doctor.get("best_port"),
        "reachable_cdp_ports": doctor.get("reachable_cdp_ports") or [],
        "sandbox_process_probe_limited": bool(doctor.get("sandbox_process_probe_limited")),
        "driver_unavailable_reason": doctor_status or "codex_cdp_unavailable",
        "recovery_command": recovery_command,
        "recovery_commands": recovery_commands,
        "recommended_action": doctor.get("recommended_action"),
        "use_discovered_port_command": doctor.get("use_discovered_port_command"),
        "doctor": doctor,
        "capability_level": "unavailable",
        "capabilities": {
            "observe_only": False,
            "control_dry_run": False,
            "allow_send_probe": False,
        },
        "automatic_dispatch_safe": False,
        "dispatch_gate": "Codex CDP was unavailable; runtime must use attributed manual-assist state and the attached doctor recovery packet.",
        "error": str(exc) if exc is not None else f"Codex CDP port {args.port} not reachable",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _composer_available(driver: CodexDriver) -> bool:
    return bool(driver.cdp.evaluate(r"!!document.querySelector('.ProseMirror[contenteditable=\"true\"]')"))


def _new_chat_available(driver: CodexDriver) -> bool:
    expr = r"""
    (() => {
      const btn = [...document.querySelectorAll('button, [role=button]')]
        .find(e => (e.textContent || '').trim().startsWith('New chat'));
      if (!btn) return false;
      const b = btn.getBoundingClientRect();
      return b.width > 0 && b.height > 0;
    })()
    """
    return bool(driver.cdp.evaluate(expr))


def _default_window_screenshot_path(port: int) -> pathlib.Path:
    return (
        pathlib.Path("state")
        / "autonomy_runtime"
        / "codex_driver"
        / "window_snapshots"
        / f"codex_window_{port}_{int(time.time())}.png"
    )


def _cmd_preflight(driver: CodexDriver, args) -> int:
    current = driver.current_thread_id()
    threads = driver.list_threads(limit=25)
    streaming = driver.streaming_thread_ids()
    rollout_path = str(driver.rollout_path(current)) if current else None
    latest_turn = driver.latest_turn(current) if current else None
    composer_available = _composer_available(driver)
    new_chat_available = _new_chat_available(driver)
    control_dry_run = bool(composer_available and new_chat_available)
    send_probe: dict[str, object] = {
        "requested": bool(args.allow_send),
        "submitted": False,
        "status": "not_requested",
    }
    if args.allow_send:
        if not args.probe_message:
            send_probe = {
                "requested": True,
                "submitted": False,
                "status": "skipped_missing_probe_message",
            }
        else:
            turn = None if args.dry_run else driver.send_and_wait(args.probe_message, max_wait_s=args.max_wait)
            send_probe = {
                "requested": True,
                "submitted": not bool(args.dry_run),
                "status": "dry_run" if args.dry_run else ("completed" if turn else "timeout"),
                "turn_id": getattr(turn, "turn_id", None) if turn else None,
            }
    capability_level = "control_dry_run" if control_dry_run else "observe_only"
    if send_probe.get("status") == "completed":
        capability_level = "allow_send_probe"
    window_snapshot = driver.target_snapshot() if hasattr(driver, "target_snapshot") else None
    payload = {
        "kind": "codex_driver_preflight",
        "status": "ok",
        "reachable": True,
        "port": driver.port,
        "no_launch": bool(args.no_launch),
        "capability_level": capability_level,
        "capabilities": {
            "observe_only": True,
            "control_dry_run": control_dry_run,
            "allow_send_probe": send_probe.get("status") == "completed",
        },
        "automatic_dispatch_safe": send_probe.get("status") == "completed",
        "dispatch_gate": (
            "open/inject/read/session attribution/rollout detection/completion detection"
            if send_probe.get("status") != "completed"
            else "allow_send probe completed; runtime still requires explicit opt-in before autonomous dispatch"
        ),
        "current_thread_id": current,
        "streaming_thread_ids": streaming,
        "thread_count": len(threads),
        "threads": [dataclasses.asdict(row) for row in threads],
        "rollout_path": rollout_path,
        "latest_turn": (
            {
                "turn_id": latest_turn.turn_id,
                "completed_at": latest_turn.completed_at,
                "duration_ms": latest_turn.duration_ms,
            }
            if latest_turn
            else None
        ),
        "control_dry_run": {
            "composer_available": composer_available,
            "new_chat_available": new_chat_available,
        },
        "window_snapshot": window_snapshot,
        "send_probe": send_probe,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Codex preflight: {payload['capability_level']} on port {driver.port}")
        print(f"  current thread: {current}")
        print(f"  rollout path:   {rollout_path}")
        print(f"  dispatch safe:  {payload['automatic_dispatch_safe']}")
    return 0


def _cmd_window_snapshot(driver: CodexDriver, args) -> int:
    payload = driver.target_snapshot()
    screenshot_arg = getattr(args, "screenshot", None)
    if screenshot_arg is not None:
        screenshot_path = (
            _default_window_screenshot_path(driver.port)
            if not screenshot_arg
            else pathlib.Path(screenshot_arg).expanduser()
        )
        if not screenshot_path.is_absolute():
            screenshot_path = pathlib.Path.cwd() / screenshot_path
        payload["screenshot"] = driver.capture_screenshot(screenshot_path)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        target = payload.get("target") or {}
        renderer = payload.get("renderer") or {}
        window = payload.get("browser_window") or {}
        print(f"Codex window snapshot on port {driver.port}")
        print(f"  target:   {target.get('id')} {target.get('title')!r}")
        print(f"  url:      {target.get('url')}")
        print(f"  renderer: {renderer.get('codex_window_type') or '?'} {renderer.get('viewport') or {}}")
        if window:
            print(f"  window:   id={window.get('windowId')} bounds={window.get('bounds')}")
        screenshot = payload.get("screenshot") or {}
        if screenshot:
            print(f"  screenshot: {screenshot.get('status')} {screenshot.get('path')}")
    return 0


def _cmd_manager_probe(driver: CodexDriver, args) -> int:
    payload = driver.manager_probe(
        app_query=args.app_query,
        thread_id=args.thread_id,
        app_limit=args.app_limit,
        thread_limit=args.thread_limit,
        force_refetch=bool(args.force_refetch),
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        connector = payload.get("connector_status") or {}
        loaded = payload.get("loaded_threads") or {}
        loaded_count = len(loaded.get("data") or []) if isinstance(loaded, Mapping) else 0
        print(f"Codex manager probe on port {driver.port}")
        print(f"  manager:  {'captured' if payload.get('captured') else 'unavailable'}")
        print(f"  current:  {payload.get('current_thread_id')}")
        print(f"  probed:   {payload.get('probed_thread_id')}")
        print(f"  loaded:   {loaded_count} thread(s)")
        print(
            "  connector: "
            f"{connector.get('name') or args.app_query} "
            f"found={bool(connector.get('found'))} "
            f"accessible={bool(connector.get('isAccessible'))} "
            f"enabled={bool(connector.get('isEnabled'))}"
        )
        errors = payload.get("errors") or []
        if errors:
            print(f"  errors:   {errors}")
    return 0


def _cmd_manager_start(driver: CodexDriver, args) -> int:
    payload = driver.manager_start(
        message=args.message,
        cwd=pathlib.Path(args.cwd).expanduser(),
        model=args.model,
        effort=args.effort,
        approval_policy=args.approval_policy,
        wait=bool(args.wait),
        max_wait_s=float(args.max_wait),
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Codex manager start on port {driver.port}: {payload.get('status')}")
        print(f"  thread:  {payload.get('thread_id')}")
        print(f"  cwd:     {payload.get('cwd')}")
        print(f"  rollout: {payload.get('rollout_path')}")
        turn = payload.get("turn") if isinstance(payload.get("turn"), Mapping) else None
        if turn:
            print(f"  turn:    {turn.get('turn_id')} dur={turn.get('duration_ms')}ms")
            print(f"  reply:   {(_text(turn.get('last_agent_message')))[:400]!r}")
        if payload.get("error"):
            print(f"  error:   {payload.get('error')}")
    return 0 if payload.get("ok") else 1


def _cmd_ensure_window(args) -> int:
    payload = CodexDriver.ensure_cdp_window(port=args.port, wait_s=float(args.wait))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    else:
        print(f"Codex CDP window ensure on port {args.port}: {payload.get('status')}")
        if payload.get("method"):
            print(f"  method: {payload.get('method')}")
        for attempt in payload.get("attempts") or []:
            probe = attempt.get("probe") if isinstance(attempt.get("probe"), Mapping) else {}
            print(
                "  "
                f"{attempt.get('method')}: "
                f"reachable={bool(probe.get('reachable'))} "
                f"main_chat={bool(probe.get('main_chat_target_found'))}"
            )
        if payload.get("recovery_command"):
            print(f"  recovery: {payload.get('recovery_command')}")
    return 0 if payload.get("ok") else 1


def _cmd_doctor(args) -> int:
    payload = diagnose_cdp(
        requested_port=args.port,
        scan=bool(args.scan),
        scan_ports=str(args.scan_ports or ""),
    )
    if bool(getattr(args, "launch_probe", False)):
        pre_launch_payload = payload
        launch_probe = probe_codex_launch(
            requested_port=args.port,
            wait_s=float(getattr(args, "launch_wait", 4.0) or 4.0),
        )
        payload = diagnose_cdp(
            requested_port=args.port,
            scan=bool(args.scan),
            scan_ports=str(args.scan_ports or ""),
        )
        payload["pre_launch_diagnosis"] = pre_launch_payload
        payload["launch_probe"] = launch_probe
        if _text(launch_probe.get("status")) == "desktop_launch_crashed":
            desktop_crash = launch_probe.get("desktop_crash") if isinstance(launch_probe.get("desktop_crash"), Mapping) else {}
            latest = desktop_crash.get("latest") if isinstance(desktop_crash.get("latest"), Mapping) else None
            payload["desktop_launch_crashed"] = True
            payload["desktop_launch_crash_report"] = latest
            payload["app_launch_state"] = "desktop_launch_crashed"
            payload["recommended_action"] = (
                "Codex.app launched but crashed before a usable CDP target appeared; keep codex exec as the primary "
                "Type A transport and repair Desktop separately."
            )
            payload["recovery_steps"] = [
                "Do not treat Desktop/CDP as an executable runtime lane until a launch probe reaches the main chat target.",
                "Inspect the attached desktop_launch_crash_report for app version, build, exception, and termination reason.",
                "Update or reinstall Codex.app, then rerun doctor with --launch-probe.",
            ] + list(payload.get("recovery_steps") or [])
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        status = payload.get("status")
        app_state = payload.get("app_launch_state")
        reachable = bool(payload.get("port_reachable"))
        target_count = int(payload.get("requested_port_probe", {}).get("target_count") or 0)
        main_targets = payload.get("main_chat_targets") or []
        recovery_command = payload.get("recovery_command")
        recommended_action = payload.get("recommended_action")
        print(f"Codex doctor: {status} on {CDP_HOST}:{args.port}")
        print(f"  app:          {app_state}")
        print(f"  port:         {'reachable' if reachable else 'unreachable'}")
        print(f"  targets:      {target_count} (main chat: {bool(main_targets)})")
        print(f"  recovery:     {recovery_command}")
        print(f"  recommendation: {recommended_action}")
        if payload.get("sandbox_process_probe_limited"):
            print("  process probe: unavailable in this sandbox")
        if payload.get("launch_probe"):
            launch_probe = payload.get("launch_probe") or {}
            print(f"  launch probe: {launch_probe.get('status')} ({len(launch_probe.get('attempts') or [])} attempt(s))")
        if payload.get("desktop_launch_crashed"):
            crash = payload.get("desktop_launch_crash_report") or {}
            print(
                "  desktop crash: "
                f"{crash.get('app_version') or '?'} ({crash.get('build_version') or '?'}) "
                f"{crash.get('exception_type') or '?'} {crash.get('termination_indicator') or ''}".strip()
            )
    return 0


def _cmd_tail(driver: CodexDriver, args) -> int:
    tid = args.thread_id or driver.current_thread_id()
    if not tid:
        print("no thread id (pass --thread-id or focus a thread in the UI)")
        return 2
    print(f"tailing rollout for {tid} (ctrl-c to stop) ...")
    for ev in driver.tail_rollout(tid, stop_on_task_complete=False, max_wait_s=args.max_wait):
        p = ev.get("payload") or {}
        pt = p.get("type", "?")
        ts = ev.get("timestamp", "?")[:23]
        preview = json.dumps({k: v for k, v in p.items() if k != "type"}, default=str)[:120]
        print(f"  {ts}  {pt:25s}  {preview}")
    return 0


def _cmd_send(driver: CodexDriver, args) -> int:
    tid = args.thread_id or driver.current_thread_id()
    if not tid:
        print("no thread id (pass --thread-id or focus a thread in the UI)")
        return 2
    if args.wait:
        print(f"sending + waiting for completion on {tid} ...")
        turn = driver.send_and_wait(args.message, thread_id=tid, max_wait_s=args.max_wait)
        if turn:
            print(f"  turn {turn.turn_id}  dur={turn.duration_ms}ms")
            print(f"  user:  {(turn.user_message or '')[:200]!r}")
            for tc in turn.tool_calls:
                print(f"  tool:  {json.dumps(tc, default=str)[:200]}")
            print(f"  reply: {(turn.last_agent_message or '')[:400]!r}")
        else:
            print(f"  turn did not complete within {args.max_wait}s")
            return 1
    else:
        driver.switch_thread(tid)
        driver.send_message(args.message)
        print("sent (no wait)")
    return 0


def _cmd_turns(driver: CodexDriver, args) -> int:
    tid = args.thread_id or driver.current_thread_id()
    if not tid:
        print("no thread id")
        return 2
    turns = driver.extract_turns(tid)
    print(f"{len(turns)} turns on disk for {tid}:")
    for i, t in enumerate(turns[-args.tail:], start=max(1, len(turns) - args.tail + 1)):
        print(f"  #{i} {t.turn_id}  dur={t.duration_ms}ms  tools={len(t.tool_calls)}")
        print(f"     user:   {(t.user_message or '')[:140]!r}")
        print(f"     reply:  {(t.last_agent_message or '')[:140]!r}")
    return 0


def main(argv: Optional[list[str]] = None):
    import argparse
    p = argparse.ArgumentParser(description="Codex driver CLI (user-simulation via CDP)")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("status", help="show current thread + streaming state + sidebar")
    sp.set_defaults(fn=_cmd_status)

    sp = sub.add_parser("preflight", help="probe Codex driver capabilities without claiming autonomous dispatch")
    sp.add_argument("--json", action="store_true", help="emit a machine-readable capability report")
    sp.add_argument("--no-launch", action="store_true", help="do not launch Codex if the CDP port is unavailable")
    sp.add_argument("--allow-send", action="store_true", help="explicitly allow a send probe")
    sp.add_argument("--probe-message", default="", help="message for --allow-send probe")
    sp.add_argument("--dry-run", action="store_true", help="report the send probe shape without submitting")
    sp.add_argument("--max-wait", type=float, default=60.0)
    sp.set_defaults(fn=_cmd_preflight)

    sp = sub.add_parser("window-snapshot", help="capture CDP target/window identity and optional screenshot")
    sp.add_argument("--json", action="store_true", help="emit a machine-readable window snapshot")
    sp.add_argument(
        "--screenshot",
        nargs="?",
        const="",
        default=None,
        help="write a PNG screenshot; omit the path to use the runtime snapshot directory",
    )
    sp.set_defaults(fn=_cmd_window_snapshot)

    sp = sub.add_parser("ensure-window", help="ensure a second CDP-enabled Codex window exists")
    sp.add_argument("--json", action="store_true", help="emit a machine-readable ensure result")
    sp.add_argument("--wait", type=float, default=8.0, help="seconds to wait after each launch attempt")
    sp.set_defaults(fn=_cmd_ensure_window)

    sp = sub.add_parser("manager-probe", help="read the Electron AppServer manager capability state")
    sp.add_argument("--json", action="store_true", help="emit a machine-readable manager probe")
    sp.add_argument("--app-query", default="GitHub", help="connector/app name or id substring to report")
    sp.add_argument("--thread-id", default=None, help="thread id to use when evaluating app connector gating")
    sp.add_argument("--app-limit", type=int, default=200, help="maximum app catalog entries to scan")
    sp.add_argument("--thread-limit", type=int, default=10, help="maximum loaded thread ids to report")
    sp.add_argument("--force-refetch", action="store_true", help="ask app/list to bypass app caches")
    sp.set_defaults(fn=_cmd_manager_probe)

    sp = sub.add_parser("manager-start", help="start a new thread through the Electron AppServer manager")
    sp.add_argument("message")
    sp.add_argument("--json", action="store_true", help="emit a machine-readable start result")
    sp.add_argument("--cwd", default=str(pathlib.Path.cwd()), help="workspace cwd for the new thread")
    sp.add_argument("--model", default="gpt-5.4", help="model for the new thread")
    sp.add_argument("--effort", default="medium", help="reasoning effort for the new thread")
    sp.add_argument("--approval-policy", default="never", help="approval policy for the new thread")
    sp.add_argument("--wait", action="store_true", help="wait for rollout task_complete")
    sp.add_argument("--max-wait", type=float, default=120.0)
    sp.set_defaults(fn=_cmd_manager_start)

    sp = sub.add_parser("doctor", help="diagnose Codex CDP reachability and recovery steps")
    sp.add_argument("--json", action="store_true", help="emit a machine-readable diagnostic report")
    sp.add_argument("--scan", dest="scan", action="store_true", default=True, help="scan common/local CDP ports for the Codex main chat target")
    sp.add_argument("--no-scan", dest="scan", action="store_false", help="only inspect the requested --port")
    sp.add_argument("--scan-ports", default="", help="comma/space separated extra CDP ports to inspect")
    sp.add_argument("--launch-probe", action="store_true", help="explicitly try Codex launch/recovery commands and report the result")
    sp.add_argument("--launch-wait", type=float, default=4.0, help="seconds to wait for CDP after each launch-probe attempt")
    sp.set_defaults(fn=_cmd_doctor)

    sp = sub.add_parser("tail", help="live-tail a thread's rollout jsonl")
    sp.add_argument("--thread-id")
    sp.add_argument("--max-wait", type=float, default=300.0)
    sp.set_defaults(fn=_cmd_tail)

    sp = sub.add_parser("send", help="send a message (defaults to current thread)")
    sp.add_argument("message")
    sp.add_argument("--thread-id")
    sp.add_argument("--wait", action="store_true", help="wait for task_complete + print turn")
    sp.add_argument("--max-wait", type=float, default=180.0)
    sp.set_defaults(fn=_cmd_send)

    sp = sub.add_parser("turns", help="list parsed turns (prompt↔response pairs)")
    sp.add_argument("--thread-id")
    sp.add_argument("--tail", type=int, default=5)
    sp.set_defaults(fn=_cmd_turns)

    args = p.parse_args(argv)
    if args.cmd == "doctor":
        return _cmd_doctor(args)
    if args.cmd == "ensure-window":
        return _cmd_ensure_window(args)
    if args.cmd == "preflight" and args.no_launch and not _cdp_port_reachable(args.port):
        return _cmd_preflight_unavailable(args)
    try:
        driver = CodexDriver.connect(port=args.port)
    except Exception as exc:
        if args.cmd == "status":
            return _cmd_status_unavailable(args, exc)
        if args.cmd == "preflight":
            return _cmd_preflight_unavailable(args, exc)
        print(f"Codex driver unavailable on port {args.port}: {exc}")
        return 1
    try:
        return args.fn(driver, args) or 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
