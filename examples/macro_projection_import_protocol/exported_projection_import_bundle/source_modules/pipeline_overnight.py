#!/usr/bin/env python3
"""
pipeline_overnight.py — Arm an unattended synth-refresh + planning loop.

Default behavior:
- pause any in-flight automation so the phase can be safely re-armed
- bootstrap missing phase harbor artifacts
- refresh synth_seed.json from raw_seed.md when needed
- sync synth_seed.json into authored/synced form
- initialize or reinitialize pipeline_state.json when the synth changed
- start launchd autopilot plus optional Codex / Claude wake watchers

This is the operator entry point for:
    "I updated the raw seed; figure out the synth seed, run overnight,
     and wake an IDE agent only when the plan loop needs review."
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib.repo_env import maybe_reexec_into_repo_python

REPO_ROOT = Path(__file__).resolve().parent
if __name__ == "__main__":
    maybe_reexec_into_repo_python(REPO_ROOT)

import pipeline_advance
from emergency_stop_observe import pause_automation, resume_automation, status_payload
from pipeline_control import (
    CLAUDE_SIGNAL_WATCHER_LABEL,
    CODEX_SIGNAL_WATCHER_LABEL,
    PIPELINE_AUTOPILOT_LABEL,
    ensure_wake_lock,
    load_control_state,
    mark_pipeline_resumed,
    resolve_wake_agent,
    resolve_sleep_policy,
    save_control_state,
)
from seed_pipeline import init_state, load_state, save_state
from system.lib.observe_apply_contracts import (
    PENDING_SYNTH_AUTHORING,
    normalize_synth_payload,
)
from system.lib.phase_lifecycle import resolve_preferred_phase_entry
from system.lib.phase_dock import preflight_phase_dock, run_phase_dock
from system.lib.phase_harbor import bootstrap_phase_harbor, resolve_phase_harbor
from system.lib.seed_pipeline_controller import write_controller_artifacts

VALID_WAKE_AGENTS = {"auto", "none", "codex", "claude", "both"}
VALID_REFRESH_MODES = {"auto", "always", "never"}
SYNTH_REFRESH_DEFER_FILENAME = "synth_refresh_deferred.json"
LAUNCH_AGENT_INSTALL_TIMEOUT_SECONDS = 15.0
INSTALL_SCRIPTS = {
    PIPELINE_AUTOPILOT_LABEL: REPO_ROOT / "pipeline_autopilot_install.sh",
    CODEX_SIGNAL_WATCHER_LABEL: REPO_ROOT / "pipeline_signal_install.sh",
    CLAUDE_SIGNAL_WATCHER_LABEL: REPO_ROOT / "claude_signal_install.sh",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(value: Any) -> str:
    return str(value or "").strip()


def _relative(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def _mtime(path: Path) -> float | None:
    try:
        return float(path.stat().st_mtime)
    except OSError:
        return None


def _timestamp(path: Path) -> str | None:
    mtime = _mtime(path)
    if mtime is None:
        return None
    return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()


def _sha256(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _phase_ref(phase_entry: Mapping[str, Any]) -> str:
    return (
        _string(phase_entry.get("phase_id"))
        or _string(phase_entry.get("phase_number"))
        or _string(phase_entry.get("phase_dir"))
    )


def _phase_token_aliases(value: Any) -> set[str]:
    token = _string(value)
    if not token:
        return set()
    normalized = re.sub(r"[^a-z0-9]+", "_", token.casefold()).strip("_")
    dotted = normalized.replace("_", ".")
    compact = re.sub(r"[^a-z0-9]+", "", token.casefold())
    aliases = {
        token.casefold(),
        normalized,
        dotted,
        compact,
    }
    return {item for item in aliases if item}


def _discover_phase_entries(root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    obsidian_root = root / "obsidian"
    if not obsidian_root.exists():
        return []
    entries: list[dict[str, Any]] = []
    for scaffold_path in sorted(obsidian_root.rglob("phase_scaffold.json")):
        payload = _load_json(scaffold_path)
        if not isinstance(payload, Mapping):
            continue
        phase_dir = _string(payload.get("phase_dir")) or _relative(scaffold_path.parent) or str(scaffold_path.parent)
        entries.append(
            {
                "phase_id": _string(payload.get("phase_id")) or None,
                "phase_number": _string(payload.get("phase_number")) or None,
                "phase_title": _string(payload.get("phase_title")) or None,
                "phase_dir": phase_dir,
                "family_dir": _string(payload.get("family_dir")) or None,
                "spec_path": _relative(scaffold_path),
                "_sort_mtime": _mtime(scaffold_path) or 0.0,
            }
        )
    entries.sort(key=lambda item: float(item.get("_sort_mtime") or 0.0), reverse=True)
    return entries


def _resolve_phase_entry(phase_token: str | None, *, root: Path = REPO_ROOT) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    entries = _discover_phase_entries(root)
    if not entries:
        raise RuntimeError("No phase_scaffold.json files were found under obsidian/.")

    requested = _string(phase_token)
    if not requested or requested == "__active__":
        preferred = resolve_preferred_phase_entry(root, eligibility="routing")
        preferred_phase_dir = _string((preferred or {}).get("phase_dir"))
        preferred_phase_id = _string((preferred or {}).get("phase_id"))
        preferred_phase_number = _string((preferred or {}).get("phase_number"))
        for entry in entries:
            if preferred_phase_dir and _string(entry.get("phase_dir")) == preferred_phase_dir:
                return entry, entries
            if preferred_phase_id and _string(entry.get("phase_id")) == preferred_phase_id:
                return entry, entries
            if preferred_phase_number and _string(entry.get("phase_number")) == preferred_phase_number:
                return entry, entries
        state_path, state = pipeline_advance.find_state()
        if state_path and isinstance(state, Mapping):
            active_phase_dir = _string(state.get("phase_dir"))
            if active_phase_dir:
                for entry in entries:
                    if _string(entry.get("phase_dir")) == active_phase_dir:
                        return entry, entries
        return entries[0], entries

    requested_aliases = _phase_token_aliases(requested)
    matches: list[dict[str, Any]] = []
    for entry in entries:
        candidate_values = (
            entry.get("phase_id"),
            entry.get("phase_number"),
            entry.get("phase_title"),
            entry.get("phase_dir"),
            entry.get("spec_path"),
        )
        candidate_aliases: set[str] = set()
        for value in candidate_values:
            candidate_aliases.update(_phase_token_aliases(value))
        if requested.casefold() in candidate_aliases or requested_aliases & candidate_aliases:
            matches.append(entry)

    if not matches:
        raise RuntimeError(f"Could not resolve phase token: {requested}")
    if len(matches) > 1:
        formatted = ", ".join(_phase_ref(item) or _string(item.get("phase_dir")) for item in matches[:5])
        raise RuntimeError(f"Phase token is ambiguous: {requested} -> {formatted}")
    return matches[0], entries


def _desired_launch_labels(wake_agent: str) -> list[str]:
    labels = [PIPELINE_AUTOPILOT_LABEL]
    if wake_agent in {"codex", "both"}:
        labels.append(CODEX_SIGNAL_WATCHER_LABEL)
    if wake_agent in {"claude", "both"}:
        labels.append(CLAUDE_SIGNAL_WATCHER_LABEL)
    return labels


def _file_card(path: Path) -> dict[str, Any]:
    return {
        "path": _relative(path),
        "exists": path.exists(),
        "modified_at": _timestamp(path) if path.exists() else None,
        "bytes": int(path.stat().st_size) if path.exists() else None,
    }


def _synth_refresh_defer_path(synth_seed_path: Path) -> Path:
    return synth_seed_path.parent / SYNTH_REFRESH_DEFER_FILENAME


def _matching_synth_refresh_defer(
    *,
    raw_seed_path: Path | None,
    synth_seed_path: Path,
    reason: str,
) -> dict[str, Any] | None:
    payload = _load_json(_synth_refresh_defer_path(synth_seed_path))
    if not payload:
        return None
    if _string(payload.get("refresh_reason")) != reason:
        return None
    raw_sha = _string(payload.get("raw_seed_sha256"))
    synth_sha = _string(payload.get("synth_seed_sha256"))
    if raw_sha and synth_sha:
        if raw_sha == (_sha256(raw_seed_path) or "") and synth_sha == (_sha256(synth_seed_path) or ""):
            return payload
        return None
    if _string(payload.get("raw_seed_modified_at")) != (_timestamp(raw_seed_path) if raw_seed_path else None):
        return None
    if _string(payload.get("synth_seed_modified_at")) != _timestamp(synth_seed_path):
        return None
    return payload


def _write_synth_refresh_defer(
    *,
    phase_ref: str,
    raw_seed_path: Path | None,
    synth_seed_path: Path,
    refresh_reason: str,
    dock_guard_error: str,
    dock_preflight: Mapping[str, Any] | None,
) -> dict[str, Any]:
    prompt_metrics = (
        dock_preflight.get("prompt_metrics")
        if isinstance(dock_preflight, Mapping) and isinstance(dock_preflight.get("prompt_metrics"), Mapping)
        else {}
    )
    dispatch_budget = None
    must_have = dock_preflight.get("must_have") if isinstance(dock_preflight, Mapping) else None
    if isinstance(must_have, list):
        dispatch_budget = next(
            (
                dict(item)
                for item in must_have
                if isinstance(item, Mapping) and _string(item.get("id")) == "dispatch_budget"
            ),
            None,
        )
    payload = {
        "kind": "synth_refresh_deferred",
        "generated_at": _utc_now(),
        "phase_ref": phase_ref,
        "refresh_reason": refresh_reason,
        "defer_reason": "phase_dock_dispatch_budget",
        "dock_guard_error": dock_guard_error,
        "raw_seed_path": _relative(raw_seed_path),
        "raw_seed_modified_at": _timestamp(raw_seed_path) if raw_seed_path else None,
        "raw_seed_sha256": _sha256(raw_seed_path),
        "synth_seed_path": _relative(synth_seed_path),
        "synth_seed_modified_at": _timestamp(synth_seed_path),
        "synth_seed_sha256": _sha256(synth_seed_path),
        "prompt_metrics": dict(prompt_metrics),
        "dispatch_budget": dispatch_budget,
        "recovery": {
            "next_step": "Split the phase-dock extraction packet or update synth_seed.json through a bounded phase-local write, then sync the synth projection.",
            "status_command": "python3 pipeline_overnight.py --status",
        },
    }
    path = _synth_refresh_defer_path(synth_seed_path)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "path": _relative(path),
        "written": True,
        "payload": payload,
    }


def _assess_synth_refresh(
    *,
    raw_seed_path: Path | None,
    synth_seed_path: Path,
    refresh_mode: str,
) -> dict[str, Any]:
    raw_exists = bool(raw_seed_path and raw_seed_path.exists())
    synth_exists = synth_seed_path.exists()
    raw_mtime = _mtime(raw_seed_path) if raw_seed_path else None
    synth_mtime = _mtime(synth_seed_path)
    synth_payload = normalize_synth_payload(_load_json(synth_seed_path) or {}) if synth_exists else {}
    synth_status = _string(synth_payload.get("authoring_status")) if isinstance(synth_payload, Mapping) else ""

    assessment = {
        "mode": refresh_mode,
        "needs_refresh": False,
        "blocked": False,
        "reason": "up_to_date",
        "raw_seed": _file_card(raw_seed_path) if raw_seed_path else {"path": None, "exists": False, "modified_at": None, "bytes": None},
        "synth_seed": _file_card(synth_seed_path),
        "synth_authoring_status": synth_status or None,
    }

    if refresh_mode == "never":
        if not synth_exists:
            assessment.update(
                {
                    "blocked": True,
                    "reason": "synth_missing_refresh_disabled",
                }
            )
        elif not synth_payload:
            assessment.update(
                {
                    "blocked": True,
                    "reason": "synth_invalid_refresh_disabled",
                }
            )
        elif synth_status == PENDING_SYNTH_AUTHORING:
            assessment.update(
                {
                    "blocked": True,
                    "reason": "synth_pending_refresh_disabled",
                }
            )
        return assessment

    if refresh_mode == "always":
        assessment.update({"needs_refresh": True, "reason": "forced_refresh"})
        return assessment

    if not synth_exists:
        assessment.update({"needs_refresh": True, "reason": "synth_missing"})
        return assessment
    if not synth_payload:
        assessment.update({"needs_refresh": True, "reason": "synth_invalid"})
        return assessment
    if synth_status == PENDING_SYNTH_AUTHORING:
        assessment.update({"needs_refresh": True, "reason": "synth_pending_initial_authoring"})
        return assessment
    if raw_exists and raw_mtime is not None and synth_mtime is not None and raw_mtime > synth_mtime:
        deferred = _matching_synth_refresh_defer(
            raw_seed_path=raw_seed_path,
            synth_seed_path=synth_seed_path,
            reason="raw_seed_newer_than_synth",
        )
        if deferred:
            assessment.update(
                {
                    "needs_refresh": False,
                    "reason": "raw_seed_newer_than_synth_deferred",
                    "deferred": True,
                    "deferred_path": _relative(_synth_refresh_defer_path(synth_seed_path)),
                    "defer_reason": _string(deferred.get("defer_reason")) or None,
                    "dock_guard_error": _string(deferred.get("dock_guard_error")) or None,
                    "raw_seed_newer_than_synth": True,
                }
            )
            return assessment
        assessment.update({"needs_refresh": True, "reason": "raw_seed_newer_than_synth"})
        return assessment
    return assessment


def _can_defer_synth_refresh(
    *,
    synth_assessment: Mapping[str, Any],
    refresh_mode: str,
) -> bool:
    if refresh_mode != "auto":
        return False
    if _string(synth_assessment.get("reason")) != "raw_seed_newer_than_synth":
        return False
    synth_card = synth_assessment.get("synth_seed") if isinstance(synth_assessment.get("synth_seed"), Mapping) else {}
    if not bool(synth_card.get("exists")):
        return False
    synth_status = _string(synth_assessment.get("synth_authoring_status"))
    return synth_status != PENDING_SYNTH_AUTHORING


def _assess_pipeline_state(
    *,
    state_path: Path,
    synth_seed_path: Path,
    force_reinit: bool,
) -> dict[str, Any]:
    assessment = {
        "path": _relative(state_path),
        "exists": state_path.exists(),
        "needs_reinit": False,
        "reason": "state_current",
        "stage": None,
        "cycle": None,
    }

    if force_reinit:
        assessment.update({"needs_reinit": True, "reason": "forced_reinit"})
        return assessment
    if not state_path.exists():
        assessment.update({"needs_reinit": True, "reason": "state_missing"})
        return assessment

    try:
        state = load_state(state_path)
    except Exception:
        assessment.update({"needs_reinit": True, "reason": "state_invalid"})
        return assessment

    assessment["stage"] = _string(state.get("stage")) or None
    assessment["cycle"] = int(state.get("cycle") or 0)
    synth_mtime = _mtime(synth_seed_path)
    state_mtime = _mtime(state_path)
    if synth_mtime is not None and state_mtime is not None and synth_mtime > state_mtime:
        assessment.update({"needs_reinit": True, "reason": "synth_newer_than_state"})
    return assessment


def _dock_live_dispatch_guard(preflight_receipt: Mapping[str, Any] | None) -> str | None:
    if not isinstance(preflight_receipt, Mapping):
        return None

    response_artifact = (
        preflight_receipt.get("response_artifact")
        if isinstance(preflight_receipt.get("response_artifact"), Mapping)
        else {}
    )
    if bool(response_artifact.get("will_reuse_existing_response")):
        return None

    prompt_metrics = (
        preflight_receipt.get("prompt_metrics")
        if isinstance(preflight_receipt.get("prompt_metrics"), Mapping)
        else {}
    )
    risk_flags = {str(item).strip() for item in prompt_metrics.get("risk_flags", []) if str(item).strip()}
    must_have = preflight_receipt.get("must_have") if isinstance(preflight_receipt.get("must_have"), list) else []
    dispatch_budget = next(
        (
            item
            for item in must_have
            if isinstance(item, Mapping) and _string(item.get("id")) == "dispatch_budget"
        ),
        None,
    )
    dispatch_budget_status = _string(dispatch_budget.get("status")) if isinstance(dispatch_budget, Mapping) else ""
    dispatch_budget_detail = _string(dispatch_budget.get("detail")) if isinstance(dispatch_budget, Mapping) else ""
    warnings = [str(item).strip() for item in prompt_metrics.get("warnings", []) if str(item).strip()]

    if dispatch_budget_status == "blocked":
        detail = dispatch_budget_detail or next(iter(warnings), "") or "phase dock dispatch budget is blocked."
        return f"extract_subphase_seed blocked before live dispatch: {detail}"

    if "prompt_decomposition_required" in risk_flags:
        detail = (
            dispatch_budget_detail
            or next(iter(warnings), "")
            or "phase dock exceeds the single-packet design budget and must be split before live dispatch."
        )
        return f"extract_subphase_seed blocked before live dispatch: {detail}"

    return None


def _parse_json_output(stdout: str) -> dict[str, Any] | None:
    text = _string(stdout)
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def _sync_synth(phase_ref: str) -> dict[str, Any]:
    command = [sys.executable, str(REPO_ROOT / "kernel.py"), "--sync-synth", phase_ref, "--live"]
    result = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    payload = _parse_json_output(result.stdout) or {}
    if result.returncode != 0:
        raise RuntimeError(
            f"sync-synth failed for {phase_ref}: {(result.stderr or result.stdout or '').strip() or 'unknown error'}"
        )
    if _string(payload.get("status")) != "applied":
        raise RuntimeError(
            f"sync-synth did not apply for {phase_ref}: {(payload or {'stdout': result.stdout.strip()})}"
        )
    payload["command"] = command
    return payload


def _run_launch_agent_install_script(script: Path) -> tuple[subprocess.CompletedProcess[str], bool]:
    command = ["/bin/bash", str(script)]
    proc = subprocess.Popen(
        command,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=LAUNCH_AGENT_INSTALL_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        for kill_signal in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, kill_signal)
            except OSError:
                pass
            try:
                stdout, stderr = proc.communicate(timeout=2.0)
                break
            except subprocess.TimeoutExpired:
                continue
        else:
            stdout, stderr = proc.communicate()
        return subprocess.CompletedProcess(command, 124, stdout=stdout, stderr=stderr), True
    return subprocess.CompletedProcess(command, int(proc.returncode or 0), stdout=stdout, stderr=stderr), False


def _install_launch_agent(label: str) -> dict[str, Any]:
    script = INSTALL_SCRIPTS[label]
    result, timed_out = _run_launch_agent_install_script(script)
    payload = {
        "label": label,
        "script": _relative(script),
        "returncode": int(result.returncode),
        "stdout": _string(result.stdout) or None,
        "stderr": _string(result.stderr) or None,
        "status": "installed" if result.returncode == 0 else "failed",
        "permission_blocked": False,
        "timed_out": timed_out,
    }
    if timed_out:
        payload["status"] = "skipped_timeout"
        payload["warning"] = (
            f"LaunchAgent install timed out after {LAUNCH_AGENT_INSTALL_TIMEOUT_SECONDS:g}s; "
            "overnight arming continued without waiting for that watcher."
        )
        return payload
    if result.returncode != 0:
        combined = " ".join(
            part for part in (payload["stdout"], payload["stderr"]) if isinstance(part, str) and part
        ).casefold()
        if "sandbox detected" in combined or "operation not permitted" in combined:
            payload["status"] = "skipped_permission_blocked"
            payload["permission_blocked"] = True
            payload["warning"] = (
                "LaunchAgent install is blocked in the current sandboxed environment; "
                "phase arming will continue without installing that watcher."
            )
            return payload
        payload["warning"] = "LaunchAgent install failed; overnight arming continued without that watcher."
        return payload
    return payload


def _load_or_init_state(
    *,
    state_path: Path,
    raw_seed_rel: str,
    phase_dir_rel: str,
    family_dir_rel: str,
    needs_reinit: bool,
) -> tuple[dict[str, Any], str]:
    if needs_reinit:
        state = init_state(raw_seed_rel, phase_dir_rel, family_dir_rel)
        write_controller_artifacts(state, repo_root=REPO_ROOT)
        save_state(state, state_path)
        return state, "initialized"

    state = load_state(state_path)
    write_controller_artifacts(state, repo_root=REPO_ROOT)
    save_state(state, state_path)
    return state, "retained"


def _restore_control_state_after_failed_arm(
    initial_control_state: Mapping[str, Any] | None,
    *,
    fallback_sleep_policy: str,
) -> dict[str, Any] | None:
    if not isinstance(initial_control_state, Mapping):
        return None
    wake_lock = (
        initial_control_state.get("wake_lock")
        if isinstance(initial_control_state.get("wake_lock"), Mapping)
        else {}
    )
    restore_sleep_policy = _string(wake_lock.get("sleep_policy")) or fallback_sleep_policy
    if bool(initial_control_state.get("paused")):
        save_control_state(dict(initial_control_state), repo_root=REPO_ROOT)
        return load_control_state(REPO_ROOT)
    resume_receipt = resume_automation(
        root=REPO_ROOT,
        dry_run=False,
        sleep_policy=restore_sleep_policy,
    )
    control_state = resume_receipt.get("control_state")
    return dict(control_state) if isinstance(control_state, Mapping) else None


def arm_overnight(
    *,
    phase_token: str | None,
    wake_agent: str,
    refresh_mode: str,
    sleep_policy: str,
    force_reinit: bool,
    pause_reason: str,
) -> dict[str, Any]:
    phase_entry, phase_entries = _resolve_phase_entry(phase_token, root=REPO_ROOT)
    phase_ref = _phase_ref(phase_entry)
    harbor = resolve_phase_harbor(REPO_ROOT, phase_entry, phase_entries=phase_entries)

    phase_dir_rel = _string(harbor.get("paths", {}).get("phase_dir"))
    family_dir_rel = _string(harbor.get("paths", {}).get("blackboard_dir"))
    raw_seed_rel = _string(harbor.get("paths", {}).get("raw_seed"))
    synth_seed_rel = _string(harbor.get("paths", {}).get("synth_seed"))
    if not phase_dir_rel or not synth_seed_rel:
        raise RuntimeError(f"Could not resolve phase harbor paths for {phase_ref}.")

    raw_seed_path = (REPO_ROOT / raw_seed_rel).resolve() if raw_seed_rel else None
    synth_seed_path = (REPO_ROOT / synth_seed_rel).resolve()
    state_path = (REPO_ROOT / phase_dir_rel / "pipeline_state.json").resolve()
    initial_control_state = load_control_state(REPO_ROOT)

    pause_receipt = pause_automation(
        root=REPO_ROOT,
        reason=pause_reason,
        dry_run=False,
        wait_timeout=2.0,
        every_manifest=False,
        terminate_browser=False,
        sleep_policy=sleep_policy,
    )
    try:
        bootstrap_receipt = bootstrap_phase_harbor(
            REPO_ROOT,
            phase_entry,
            phase_entries=phase_entries,
            live=True,
        )

        synth_assessment = _assess_synth_refresh(
            raw_seed_path=raw_seed_path,
            synth_seed_path=synth_seed_path,
            refresh_mode=refresh_mode,
        )
        if synth_assessment["blocked"]:
            raise RuntimeError(
                f"Synth refresh is required but disabled: {synth_assessment['reason']} ({synth_seed_rel})."
            )
        if synth_assessment["needs_refresh"] and (raw_seed_path is None or not raw_seed_path.exists()):
            raise RuntimeError(f"raw_seed.md not found for synth refresh: {raw_seed_rel or phase_dir_rel}")

        dock_preflight: dict[str, Any] | None = None
        dock_receipt: dict[str, Any] | None = None
        sync_receipt: dict[str, Any] | None = None
        defer_receipt: dict[str, Any] | None = None
        if synth_assessment["needs_refresh"]:
            dock_preflight = preflight_phase_dock(
                REPO_ROOT,
                phase_entry,
                phase_entries=phase_entries,
                operation="extract_subphase_seed",
                consumer="bridge",
                bridge_provider="chatgpt",
                live=True,
            )
            dock_guard_error = _dock_live_dispatch_guard(dock_preflight)
            if dock_guard_error:
                if not _can_defer_synth_refresh(
                    synth_assessment=synth_assessment,
                    refresh_mode=refresh_mode,
                ):
                    raise RuntimeError(dock_guard_error)
                defer_receipt = _write_synth_refresh_defer(
                    phase_ref=phase_ref,
                    raw_seed_path=raw_seed_path,
                    synth_seed_path=synth_seed_path,
                    refresh_reason=_string(synth_assessment.get("reason")) or "raw_seed_newer_than_synth",
                    dock_guard_error=dock_guard_error,
                    dock_preflight=dock_preflight,
                )
                synth_assessment = {
                    **synth_assessment,
                    "needs_refresh": False,
                    "reason": "raw_seed_newer_than_synth_deferred",
                    "deferred": True,
                    "defer_reason": "phase_dock_dispatch_budget",
                    "deferred_path": defer_receipt.get("path"),
                    "dock_guard_error": dock_guard_error,
                    "raw_seed_newer_than_synth": True,
                }
            else:
                dock_receipt = run_phase_dock(
                    REPO_ROOT,
                    phase_entry,
                    phase_entries=phase_entries,
                    operation="extract_subphase_seed",
                    consumer="bridge",
                    bridge_provider="chatgpt",
                    live=True,
                )
                if _string(dock_receipt.get("status")) != "applied":
                    raise RuntimeError(f"extract_subphase_seed did not apply cleanly: {dock_receipt}")
                sync_receipt = _sync_synth(phase_ref)

        pipeline_assessment = _assess_pipeline_state(
            state_path=state_path,
            synth_seed_path=synth_seed_path,
            force_reinit=force_reinit or sync_receipt is not None,
        )
        state, pipeline_action = _load_or_init_state(
            state_path=state_path,
            raw_seed_rel=raw_seed_rel,
            phase_dir_rel=phase_dir_rel,
            family_dir_rel=family_dir_rel,
            needs_reinit=bool(pipeline_assessment["needs_reinit"]),
        )
        if defer_receipt is not None:
            defer_receipt = _write_synth_refresh_defer(
                phase_ref=phase_ref,
                raw_seed_path=raw_seed_path,
                synth_seed_path=synth_seed_path,
                refresh_reason="raw_seed_newer_than_synth",
                dock_guard_error=_string(synth_assessment.get("dock_guard_error")) or "phase dock dispatch budget is blocked.",
                dock_preflight=dock_preflight,
            )
            synth_assessment = {
                **synth_assessment,
                "deferred_path": defer_receipt.get("path"),
            }
        resume_json_path, resume_md_path = pipeline_advance.write_resume_artifacts(state_path, state)
        packet = pipeline_advance.build_resume_packet(state_path, state)

        resolved_wake_agent = resolve_wake_agent(wake_agent, repo_root=REPO_ROOT)
        launch_labels = _desired_launch_labels(resolved_wake_agent)
        control_state = mark_pipeline_resumed(repo_root=REPO_ROOT, sleep_policy=sleep_policy)
        control_state = ensure_wake_lock(sleep_policy=sleep_policy, repo_root=REPO_ROOT)
        launch_results = [_install_launch_agent(label) for label in launch_labels]

        return {
            "action": "arm_overnight",
            "armed_at": _utc_now(),
            "phase": {
                "phase_ref": phase_ref,
                "phase_id": phase_entry.get("phase_id"),
                "phase_number": phase_entry.get("phase_number"),
                "phase_title": phase_entry.get("phase_title"),
                "phase_dir": phase_dir_rel,
                "family_dir": family_dir_rel or None,
            },
            "pause_receipt": pause_receipt,
            "harbor_bootstrap": bootstrap_receipt,
            "synth_refresh": {
                **synth_assessment,
                "dock_preflight": dock_preflight,
                "dock_receipt": dock_receipt,
                "sync_receipt": sync_receipt,
                "defer_receipt": defer_receipt,
            },
            "pipeline": {
                **pipeline_assessment,
                "action": pipeline_action,
                "pipeline_id": state.get("pipeline_id"),
                "stage": state.get("stage"),
                "cycle": state.get("cycle"),
                "state_path": _relative(state_path),
                "resume_json_path": _relative(resume_json_path),
                "resume_md_path": _relative(resume_md_path),
                "next_action": packet.get("next_action"),
                "attention": packet.get("codex_attention"),
            },
            "launch_agents": {
                "requested_wake_agent": wake_agent,
                "wake_agent": resolved_wake_agent,
                "enabled_labels": launch_labels,
                "install_results": launch_results,
            },
            "control_state": control_state,
        }
    except BaseException:
        _restore_control_state_after_failed_arm(
            initial_control_state,
            fallback_sleep_policy=sleep_policy,
        )
        raise


def overnight_status(*, phase_token: str | None, refresh_mode: str) -> dict[str, Any]:
    phase_entry, phase_entries = _resolve_phase_entry(phase_token, root=REPO_ROOT)
    phase_ref = _phase_ref(phase_entry)
    harbor = resolve_phase_harbor(REPO_ROOT, phase_entry, phase_entries=phase_entries)
    phase_dir_rel = _string(harbor.get("paths", {}).get("phase_dir"))
    raw_seed_rel = _string(harbor.get("paths", {}).get("raw_seed"))
    synth_seed_rel = _string(harbor.get("paths", {}).get("synth_seed"))
    state_path = (REPO_ROOT / phase_dir_rel / "pipeline_state.json").resolve()
    raw_seed_path = (REPO_ROOT / raw_seed_rel).resolve() if raw_seed_rel else None
    synth_seed_path = (REPO_ROOT / synth_seed_rel).resolve() if synth_seed_rel else None
    if synth_seed_path is None:
        raise RuntimeError(f"Could not resolve synth_seed.json for {phase_ref}.")

    synth_assessment = _assess_synth_refresh(
        raw_seed_path=raw_seed_path,
        synth_seed_path=synth_seed_path,
        refresh_mode=refresh_mode,
    )
    pipeline_assessment = _assess_pipeline_state(
        state_path=state_path,
        synth_seed_path=synth_seed_path,
        force_reinit=False,
    )

    state_summary: dict[str, Any] | None = None
    if state_path.exists():
        try:
            state = load_state(state_path)
        except Exception:
            state_summary = {"path": _relative(state_path), "status": "invalid"}
        else:
            packet = pipeline_advance.build_resume_packet(state_path, state)
            state_summary = {
                "path": _relative(state_path),
                "pipeline_id": state.get("pipeline_id"),
                "stage": state.get("stage"),
                "cycle": state.get("cycle"),
                "next_action": packet.get("next_action"),
                "attention": packet.get("codex_attention"),
            }

    return {
        "action": "status",
        "phase": {
            "phase_ref": phase_ref,
            "phase_id": phase_entry.get("phase_id"),
            "phase_number": phase_entry.get("phase_number"),
            "phase_title": phase_entry.get("phase_title"),
            "phase_dir": phase_dir_rel,
            "family_dir": _string(harbor.get("paths", {}).get("blackboard_dir")) or None,
        },
        "synth_refresh": synth_assessment,
        "pipeline": {
            **pipeline_assessment,
            "state": state_summary,
        },
        "automation": status_payload(root=REPO_ROOT),
        "control_state": load_control_state(REPO_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Arm or inspect the unattended overnight planning loop.")
    parser.add_argument("--phase", type=str, default=None, help="Phase token. Defaults to the active phase.")
    parser.add_argument("--status", action="store_true", help="Show overnight readiness for the target phase.")
    parser.add_argument("--pause", action="store_true", help="Pause unattended automation immediately.")
    parser.add_argument(
        "--wake-agent",
        choices=sorted(VALID_WAKE_AGENTS),
        default="auto",
        help="Which IDE agent watcher to enable when the overnight run hits a durable gate. auto follows master_config pipeline.orchestrator_primary.",
    )
    parser.add_argument(
        "--refresh-synth",
        choices=sorted(VALID_REFRESH_MODES),
        default="auto",
        help="When to rebuild synth_seed.json from raw_seed.md before re-arming.",
    )
    parser.add_argument(
        "--sleep-policy",
        default=None,
        help="Automation sleep policy. Defaults to the persisted control-state preference, else master_config.json.",
    )
    parser.add_argument(
        "--force-reinit",
        action="store_true",
        help="Always reinitialize pipeline_state.json even if the synth is unchanged.",
    )
    parser.add_argument(
        "--reason",
        default="overnight_arm",
        help="Pause reason recorded before the system is re-armed.",
    )
    args = parser.parse_args()

    sleep_policy = resolve_sleep_policy(args.sleep_policy, repo_root=REPO_ROOT)

    if args.pause:
        print(
            json.dumps(
                pause_automation(
                    root=REPO_ROOT,
                    reason=_string(args.reason) or "manual_pause",
                    dry_run=False,
                    wait_timeout=2.0,
                    every_manifest=False,
                    terminate_browser=False,
                    sleep_policy=sleep_policy,
                ),
                indent=2,
            )
        )
        return 0

    if args.status:
        payload = overnight_status(
            phase_token=args.phase,
            refresh_mode=args.refresh_synth,
        )
        try:
            from system.control.orchestration import write_orchestration_artifacts

            wrote = write_orchestration_artifacts(repo_root=REPO_ROOT, phase_token=args.phase)
            payload["orchestration"] = {
                "state_path": wrote["state_path"],
                "brief_json_path": wrote["brief_json_path"],
                "brief_markdown_path": wrote["brief_markdown_path"],
                "event_log_path": wrote.get("event_log_path"),
                "latest_event_id": ((wrote.get("state") or {}).get("event_log") or {}).get("latest_event_id"),
                "active_driver": wrote["state"].get("active_driver"),
                "gate": wrote["state"].get("gate"),
            }
        except Exception:
            pass
        print(
            json.dumps(payload, indent=2)
        )
        return 0

    payload = arm_overnight(
        phase_token=args.phase,
        wake_agent=args.wake_agent,
        refresh_mode=args.refresh_synth,
        sleep_policy=sleep_policy,
        force_reinit=bool(args.force_reinit),
        pause_reason=_string(args.reason) or "overnight_arm",
    )
    try:
        from system.control.orchestration import write_orchestration_artifacts

        wrote = write_orchestration_artifacts(repo_root=REPO_ROOT, phase_token=args.phase)
        payload["orchestration"] = {
            "state_path": wrote["state_path"],
            "brief_json_path": wrote["brief_json_path"],
            "brief_markdown_path": wrote["brief_markdown_path"],
            "event_log_path": wrote.get("event_log_path"),
            "latest_event_id": ((wrote.get("state") or {}).get("event_log") or {}).get("latest_event_id"),
            "active_driver": wrote["state"].get("active_driver"),
            "gate": wrote["state"].get("gate"),
        }
    except Exception:
        pass
    print(
        json.dumps(payload, indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
