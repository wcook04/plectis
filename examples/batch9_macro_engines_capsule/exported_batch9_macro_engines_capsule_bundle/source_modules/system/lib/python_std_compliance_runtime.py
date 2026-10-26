"""

[PURPOSE]
- Teleology: Centralize the runtime paths, campaign discovery, lifecycle
  normalization, and SELF-refresh helpers for the autonomous `std_python`
  compliance factory.
- Mechanism: Provide one lane-local authority for stable paths under
  `state/meta_missions/python_std_compliance_authoring/`, normalized campaign
  summaries, and builder-backed SELF refresh.
- Non-goal: Mining compliance findings or executing author/apply campaigns.
  Those stay in their dedicated modules.

[INTERFACE]
- Exports: Mission/run/coverage path helpers, campaign load/write/discovery/normalization, cycle/resume/apply command builders and refresh_python_std_self_authority.
- Writes: Atomic campaign-summary JSON; SELF refresh delegates generated authority updates to the repository builder.

[FLOW]
- Reads: Lane coverage and campaign summaries plus bridge runtime context.
- Mechanism: Resolve summary locations, normalize lifecycle state, discover nonterminal campaigns and construct CLI continuation commands; SELF refresh initializes kernel state and runs only that builder phase.

[DEPENDENCIES]
- Couples: preview_campaign_lifecycle defines normalized lifecycle states; kernel.helpers loads builder config; tools.meta.builder owns SELF projection refresh.

[CONSTRAINTS]
- Non-goal: Campaign execution/mining stays outside this lane-local runtime helper.
- Fails: Campaign path/JSON and builder failures are represented where helper loaders/results handle them; requested filesystem writes may raise.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib.kernel.helpers import load_builder_config
from system.lib.preview_campaign_lifecycle import (
    NONTERMINAL_LIFECYCLE_STATES,
    normalize_preview_campaign_summary,
)

MISSION_ID = "python_std_compliance_authoring"
MISSION_ROOT_REL = f"state/meta_missions/{MISSION_ID}"
RUNS_ROOT_REL = f"{MISSION_ROOT_REL}/runs"
COVERAGE_REL = f"{MISSION_ROOT_REL}/python_std_compliance_coverage.json"
COVERAGE_PATH_REL = COVERAGE_REL
COVERAGE_STANDARD_PATH = "codex/standards/std_python_compliance_coverage.json"
CAMPAIGN_SUMMARY_BASENAME = "campaign_summary.json"
DEFAULT_APPROVED_BY = "human_operator"
BRIDGE_STATE_REL = "tools/meta/apply/observe_history/bridge_state.json"
DEFAULT_BRIDGE_MONITOR_TIMEOUT_S = 300.0


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _relative(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return _load_json(path)
    except Exception:
        return None


def _parse_iso_timestamp(value: Any) -> datetime | None:
    text = _string(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _format_char_count(value: Any) -> str:
    count = max(0, _int_or_zero(value))
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}m chars"
    if count >= 1_000:
        return f"{count / 1_000:.1f}k chars"
    return f"{count} chars"


def _lane_mode(value: Any) -> str:
    text = _string(value).lower()
    if any(token in text for token in ("join", "synthesis", "evaluation")):
        return "join"
    return "probe"


def _bridge_monitor_timeout_s(repo_root: Path) -> float:
    payload = _load_json_if_exists((repo_root / "master_config.json").resolve()) or {}
    bridge = payload.get("bridge") if isinstance(payload.get("bridge"), Mapping) else {}
    raw_value = bridge.get("monitor_timeout_s") if isinstance(bridge, Mapping) else None
    if isinstance(raw_value, Mapping):
        raw_value = raw_value.get("value")
    try:
        parsed = float(raw_value or DEFAULT_BRIDGE_MONITOR_TIMEOUT_S)
    except (TypeError, ValueError):
        parsed = DEFAULT_BRIDGE_MONITOR_TIMEOUT_S
    return max(30.0, parsed)


def _bridge_wait_stale_threshold_s(repo_root: Path) -> float:
    return max(45.0, min(120.0, _bridge_monitor_timeout_s(repo_root) / 4.0))


def _batch_artifact_paths(repo_root: Path, batch: Mapping[str, Any]) -> list[Path]:
    bridge_run_root = (repo_root / _string(batch.get("bridge_run_root"))).resolve()
    return [
        bridge_run_root / "session_summary.json",
        bridge_run_root / "compiled_apply_plan.json",
        bridge_run_root / "apply_preview.json",
        bridge_run_root / "result_note.md",
        bridge_run_root / "run_summary.json",
    ]


def _latest_artifact_timestamp(paths: list[Path]) -> datetime | None:
    latest_ts: datetime | None = None
    for path in paths:
        if not path.exists():
            continue
        try:
            current = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if latest_ts is None or current > latest_ts:
            latest_ts = current
    return latest_ts


def _extract_session_observe_id(repo_root: Path, batch: Mapping[str, Any]) -> str | None:
    result = batch.get("result") if isinstance(batch.get("result"), Mapping) else {}
    session_summary = result.get("session_summary") if isinstance(result.get("session_summary"), Mapping) else {}
    observe_id = _string(session_summary.get("observe_id"))
    if observe_id:
        return observe_id
    session_summary_path = _string(result.get("session_summary_path"))
    if session_summary_path:
        payload = _load_json_if_exists((repo_root / session_summary_path).resolve()) or {}
        observe_id = _string(payload.get("observe_id"))
        if observe_id:
            return observe_id
    for candidate in _batch_artifact_paths(repo_root, batch):
        if candidate.name != "session_summary.json":
            continue
        payload = _load_json_if_exists(candidate) or {}
        observe_id = _string(payload.get("observe_id"))
        if observe_id:
            return observe_id
    return None


def _extract_provider_tab_progress(
    *,
    session_id: str,
    provider: str,
    session_payload: Mapping[str, Any],
    provider_payload: Mapping[str, Any],
) -> dict[str, Any] | None:
    tabs = provider_payload.get("tabs")
    if not isinstance(tabs, Mapping):
        return None
    best_payload: dict[str, Any] | None = None
    best_ts: datetime | None = None
    for tab_id, tab_payload in tabs.items():
        if not isinstance(tab_payload, Mapping):
            continue
        phase = _string(tab_payload.get("phase")).lower()
        if phase == "tab_closed":
            continue
        updated_at = (
            _string(tab_payload.get("updated_at"))
            or _string(provider_payload.get("updated_at"))
            or _string(session_payload.get("updated_at"))
            or _string(session_payload.get("started_at"))
        )
        updated_ts = _parse_iso_timestamp(updated_at) or datetime.fromtimestamp(0, tz=timezone.utc)
        progress = {
            "session_id": _string(session_id) or None,
            "provider": _string(provider) or None,
            "tab_id": _string(tab_id) or None,
            "node_id": _string(tab_payload.get("node_id")) or None,
            "lane": _string(tab_payload.get("lane")) or None,
            "phase": phase or None,
            "status": _string(tab_payload.get("status")) or "ok",
            "wait_status": _string(tab_payload.get("wait_status")) or None,
            "response_chars": _int_or_zero(tab_payload.get("response_chars")),
            "response_count": _int_or_zero(tab_payload.get("response_count")),
            "response_started": bool(tab_payload.get("response_started")),
            "transport": _string(tab_payload.get("transport")) or None,
            "updated_at": updated_at or None,
        }
        if best_ts is None or updated_ts > best_ts:
            best_ts = updated_ts
            best_payload = progress
    return best_payload


def _latest_runtime_progress(
    *,
    runtime: Mapping[str, Any],
    provider: str,
    observe_id: str | None,
    not_before: datetime | None,
) -> dict[str, Any] | None:
    sessions = runtime.get("sessions")
    if not isinstance(sessions, Mapping):
        return None
    provider_key = _string(provider).lower()
    if observe_id:
        session_payload = sessions.get(observe_id)
        if isinstance(session_payload, Mapping):
            providers = session_payload.get("providers")
            provider_payload = providers.get(provider_key) if isinstance(providers, Mapping) else None
            if isinstance(provider_payload, Mapping):
                progress = _extract_provider_tab_progress(
                    session_id=observe_id,
                    provider=provider_key,
                    session_payload=session_payload,
                    provider_payload=provider_payload,
                )
                if progress is not None:
                    return progress
    best_payload: dict[str, Any] | None = None
    best_ts: datetime | None = None
    for session_id, session_payload in sessions.items():
        if not isinstance(session_payload, Mapping):
            continue
        if not _string(session_id).startswith("OBS_"):
            continue
        providers = session_payload.get("providers")
        provider_payload = providers.get(provider_key) if isinstance(providers, Mapping) else None
        if not isinstance(provider_payload, Mapping):
            continue
        progress = _extract_provider_tab_progress(
            session_id=_string(session_id),
            provider=provider_key,
            session_payload=session_payload,
            provider_payload=provider_payload,
        )
        if progress is None:
            continue
        updated_ts = _parse_iso_timestamp(progress.get("updated_at"))
        if not_before is not None and updated_ts is not None and updated_ts < not_before:
            continue
        if best_ts is None or (updated_ts is not None and updated_ts > best_ts):
            best_ts = updated_ts
            best_payload = progress
    return best_payload


def _summarize_live_bridge_progress(progress: Mapping[str, Any], *, stale: bool) -> str:
    node_id = _string(progress.get("node_id")) or "unknown"
    lane_mode = _lane_mode(progress.get("lane"))
    phase = _string(progress.get("phase")).lower()
    wait_status = _string(progress.get("wait_status")).lower()
    response_chars = _int_or_zero(progress.get("response_chars"))
    response_started = bool(progress.get("response_started"))
    if stale:
        return f"stale {lane_mode}: {node_id}, {_format_char_count(response_chars)}"
    if phase == "provider_wait":
        if wait_status == "stabilizing":
            state = "stabilizing"
        elif wait_status == "receiving" or response_started or response_chars > 0:
            state = "receiving"
        else:
            state = "thinking"
        return f"running {lane_mode}: {node_id}, {state}, {_format_char_count(response_chars)}"
    if phase:
        return f"running {lane_mode}: {node_id}, {phase}"
    return f"running {lane_mode}: {node_id}"


def _running_batch_bridge_progress(
    repo_root: Path,
    summary: Mapping[str, Any],
) -> dict[str, Any] | None:
    running_batch = next(
        (
            dict(batch)
            for batch in (summary.get("batches") or [])
            if isinstance(batch, Mapping) and _string(batch.get("status")).lower() == "running"
        ),
        None,
    )
    if running_batch is None:
        return None
    bridge_state = _load_json_if_exists((repo_root / BRIDGE_STATE_REL).resolve()) or {}
    runtime = bridge_state.get("runtime")
    if not isinstance(runtime, Mapping):
        return None
    provider = (
        _string(running_batch.get("effective_provider"))
        or _string(summary.get("provider"))
        or "chatgpt"
    ).lower()
    batch_started_at = _parse_iso_timestamp(running_batch.get("started_at"))
    observe_id = _extract_session_observe_id(repo_root, running_batch)
    progress = _latest_runtime_progress(
        runtime=runtime,
        provider=provider,
        observe_id=observe_id,
        not_before=batch_started_at,
    )
    if progress is None:
        return None
    updated_ts = _parse_iso_timestamp(progress.get("updated_at"))
    now = datetime.now(timezone.utc)
    stale_threshold_s = _bridge_wait_stale_threshold_s(repo_root)
    latest_artifact_ts = _latest_artifact_timestamp(_batch_artifact_paths(repo_root, running_batch))
    stale = False
    if updated_ts is not None and (now - updated_ts).total_seconds() > stale_threshold_s:
        if latest_artifact_ts is None or (now - latest_artifact_ts).total_seconds() > stale_threshold_s:
            stale = True
    live_progress = dict(progress)
    live_progress["batch_index"] = _int_or_zero(running_batch.get("batch_index")) or None
    live_progress["bin_id"] = _string(running_batch.get("bin_id")) or None
    live_progress["bridge_run_root"] = _string(running_batch.get("bridge_run_root")) or None
    live_progress["stale"] = stale
    live_progress["stale_threshold_s"] = stale_threshold_s
    live_progress["batch_artifacts_updated_at"] = latest_artifact_ts.isoformat() if latest_artifact_ts is not None else None
    live_progress["operator_summary"] = _summarize_live_bridge_progress(live_progress, stale=stale)
    if stale:
        live_progress["stale_reason"] = "bridge_wait_state_stopped_advancing"
    return live_progress


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def mission_root(repo_root: Path) -> Path:
    return (repo_root / MISSION_ROOT_REL).resolve()


def runs_root(repo_root: Path) -> Path:
    return (repo_root / RUNS_ROOT_REL).resolve()


def coverage_path(repo_root: Path) -> Path:
    return (repo_root / COVERAGE_REL).resolve()


def load_python_std_compliance_coverage(repo_root: Path) -> dict[str, Any] | None:
    path = coverage_path(repo_root)
    if not path.exists():
        return None
    try:
        return _load_json(path)
    except Exception:
        return None


def resolve_campaign_summary_path(repo_root: Path, token: str) -> Path:
    path = Path(_string(token))
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    return path


def _derive_snapshot_finding_ids(summary: Mapping[str, Any]) -> list[str]:
    explicit = [
        _string(item)
        for item in (summary.get("snapshot_finding_ids") or [])
        if _string(item)
    ]
    if explicit:
        return sorted(dict.fromkeys(explicit))
    finding_ids: list[str] = []
    for batch in summary.get("batches") or []:
        if not isinstance(batch, Mapping):
            continue
        for item in batch.get("finding_ids") or []:
            token = _string(item)
            if token:
                finding_ids.append(token)
    return sorted(dict.fromkeys(finding_ids))


def _derive_snapshot_bin_ids(summary: Mapping[str, Any]) -> list[str]:
    explicit = [
        _string(item)
        for item in (summary.get("snapshot_bin_ids") or [])
        if _string(item)
    ]
    if explicit:
        return sorted(dict.fromkeys(explicit))
    bin_ids: list[str] = []
    for batch in summary.get("batches") or []:
        if not isinstance(batch, Mapping):
            continue
        token = _string(batch.get("bin_id"))
        if token:
            bin_ids.append(token)
    return sorted(dict.fromkeys(bin_ids))


def normalize_python_std_campaign_summary(
    summary: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    payload = normalize_preview_campaign_summary(summary)
    payload["snapshot_finding_ids"] = _derive_snapshot_finding_ids(payload)
    payload["snapshot_bin_ids"] = _derive_snapshot_bin_ids(payload)
    payload.setdefault("coverage_standard_path", COVERAGE_STANDARD_PATH)
    payload.setdefault("coverage_path", COVERAGE_REL)
    if repo_root is not None and summary_path is not None:
        rel_summary_path = _relative(repo_root, summary_path)
        payload["campaign_summary_path"] = rel_summary_path
        payload["approve_command"] = build_approve_command(repo_root, summary_path)
        payload["resume_command"] = build_resume_command(repo_root, summary_path)
        payload["live_apply_command"] = build_live_apply_command(repo_root, summary_path)
    return payload


def load_python_std_campaign_summary(repo_root: Path, token: str | Path) -> dict[str, Any]:
    path = resolve_campaign_summary_path(repo_root, str(token))
    return normalize_python_std_campaign_summary(
        _load_json(path),
        repo_root=repo_root,
        summary_path=path,
    )


def write_python_std_campaign_summary(repo_root: Path, path: Path, summary: Mapping[str, Any]) -> dict[str, Any]:
    normalized = normalize_python_std_campaign_summary(summary, repo_root=repo_root, summary_path=path)
    atomic_write_json(path, normalized)
    return normalized


def discover_python_std_campaign_summaries(repo_root: Path) -> list[dict[str, Any]]:
    root = runs_root(repo_root)
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob(CAMPAIGN_SUMMARY_BASENAME)):
        try:
            summary = normalize_python_std_campaign_summary(
                _load_json(path),
                repo_root=repo_root,
                summary_path=path,
            )
        except Exception:
            continue
        rows.append(summary)
    rows.sort(
        key=lambda item: (
            _string(item.get("lifecycle_state_updated_at") or item.get("finished_at") or item.get("started_at")),
            _string(item.get("campaign_summary_path")),
        ),
        reverse=True,
    )
    return rows


def nonterminal_python_std_campaigns(repo_root: Path) -> list[dict[str, Any]]:
    return [
        summary
        for summary in discover_python_std_campaign_summaries(repo_root)
        if _string(summary.get("lifecycle_state")) in NONTERMINAL_LIFECYCLE_STATES
    ]


def build_cycle_command(provider: str = "auto") -> str:
    token = _string(provider) or "auto"
    return f"./repo-python tools/meta/factory/python_std_compliance_cycle.py --provider {token}"


def build_approve_command(repo_root: Path, summary_path: Path, approved_by: str = DEFAULT_APPROVED_BY) -> str:
    rel_path = _relative(repo_root, summary_path)
    approver = _string(approved_by) or DEFAULT_APPROVED_BY
    return (
        "./repo-python tools/meta/factory/python_std_compliance_cycle.py "
        f"--approve-campaign-summary {rel_path} --approved-by {approver}"
    )


def build_resume_command(repo_root: Path, summary_path: Path, provider: str = "auto") -> str:
    rel_path = _relative(repo_root, summary_path)
    token = _string(provider) or "auto"
    return (
        "./repo-python tools/meta/factory/python_std_compliance_campaign.py "
        f"--resume-campaign-summary {rel_path} --provider {token} --run-session --preview-apply"
    )


def build_live_apply_command(repo_root: Path, summary_path: Path) -> str:
    rel_path = _relative(repo_root, summary_path)
    return (
        "./repo-python tools/meta/factory/python_std_compliance_apply_campaign.py "
        f"--campaign-summary {rel_path} --live"
    )


def compact_python_std_campaign_record(
    repo_root: Path,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    summary_path = resolve_campaign_summary_path(repo_root, _string(summary.get("campaign_summary_path")))
    normalized = normalize_python_std_campaign_summary(summary, repo_root=repo_root, summary_path=summary_path)
    approval = _safe_mapping(normalized.get("approval"))
    apply_summary_rel = _string(normalized.get("apply_summary_path"))
    running_batch = next(
        (
            dict(batch)
            for batch in (normalized.get("batches") or [])
            if isinstance(batch, Mapping) and _string(batch.get("status")).lower() == "running"
        ),
        None,
    )
    live_bridge_progress = _running_batch_bridge_progress(repo_root, normalized)
    return {
        "campaign_slug": _string(normalized.get("campaign_slug")) or summary_path.parent.name,
        "campaign_summary_path": _string(normalized.get("campaign_summary_path")) or _relative(repo_root, summary_path),
        "campaign_root": _string(normalized.get("campaign_root")) or _relative(repo_root, summary_path.parent),
        "lifecycle_state": _string(normalized.get("lifecycle_state")),
        "status": _string(normalized.get("status")),
        "approval": approval,
        "started_at": normalized.get("started_at"),
        "finished_at": normalized.get("finished_at"),
        "lifecycle_state_updated_at": normalized.get("lifecycle_state_updated_at"),
        "apply_summary_path": apply_summary_rel or None,
        "snapshot_findings_total": len(normalized.get("snapshot_finding_ids") or []),
        "snapshot_bins_total": len(normalized.get("snapshot_bin_ids") or []),
        "approve_command": build_approve_command(repo_root, summary_path),
        "resume_command": build_resume_command(repo_root, summary_path),
        "live_apply_command": build_live_apply_command(repo_root, summary_path),
        "running_batch": (
            {
                "batch_index": _int_or_zero(running_batch.get("batch_index")) or None,
                "bin_id": _string(running_batch.get("bin_id")) or None,
                "status": _string(running_batch.get("status")) or None,
                "bridge_run_root": _string(running_batch.get("bridge_run_root")) or None,
            }
            if isinstance(running_batch, Mapping)
            else None
        ),
        "live_bridge_progress": dict(live_bridge_progress) if isinstance(live_bridge_progress, Mapping) else None,
    }


def refresh_python_std_self_authority(repo_root: Path) -> dict[str, Any]:
    from tools.meta import builder
    from system.lib.kernel import state as kernel_state

    kernel_state.init(repo_root.resolve())
    config = load_builder_config()
    config["root_hint"] = str(repo_root.resolve())
    result = builder.run(config, phases=["SELF"])
    metadata = result.get("metadata", {}) if isinstance(result, Mapping) else {}
    data = result.get("data", {}) if isinstance(result, Mapping) else {}
    warnings = list(data.get("warnings") or []) if isinstance(data, Mapping) else []
    return {
        "status": _string(metadata.get("status")) or "unknown",
        "error": _string(metadata.get("error")) or None,
        "warnings": warnings,
        "phases": list(data.get("phases") or []) if isinstance(data, Mapping) else [],
    }
