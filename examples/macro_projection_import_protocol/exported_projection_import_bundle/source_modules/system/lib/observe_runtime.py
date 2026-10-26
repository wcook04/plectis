"""
[PURPOSE]
- Teleology: Centralize grouped-observe runtime policy, dependency waves, runtime manifests, continuation contracts, and cancellation semantics for kernel observe execution.
- Mechanism: Resolves config-driven worker policy, persists grouped runtime state, derives retryability and continuation bundles, and promotes stable artifacts into the history surfaces read by CLI and resume flows.

[INTERFACE]
- Exports: observe_runtime_policy, resolve_effective_workers, grouped_observe_waves, grouped_runtime_continue_contract, grouped_runtime_status_payload, promote_grouped_observe_state, request_grouped_runtime_cancel, and grouped runtime path helpers.
- Reads: master_config.json, grouped runtime manifests, observe history entries, bridge_state.json, and promoted observe history artifacts.
- Writes: grouped runtime manifests/current.json, runtime status updates, promoted digest/result pointers, and cancellation timestamps.

[FLOW]
- Orders: Config and worker policy resolve first -> authored groups are stratified into dependency waves -> runtime manifests accumulate status and retryability -> continuation and status payloads are projected from stored history -> terminal states are promoted or cancelled.

[DEPENDENCIES]
- Couples: system/lib/observe_surfaces.py provides the resume and readback surface builders embedded into runtime status payloads.
- Couples: tools/meta/apply/run_observe_plan.py uses this module as the source of truth for worker ceilings, runtime manifests, state promotion, and cancel handling.

[CONSTRAINTS]
- Guarantee: Runtime status payloads normalize grouped observe state into continuation, readback, promoted-surface, and lineage bundles before callers read them.
- Non-goal: This module does not enrich observe plans or author apply-context digests.
- When-needed: Open when grouped observe execution or status tooling needs runtime policy, manifest state, retryability, or cancellation semantics instead of higher-level session orchestration.
- Escalates-to: tools/meta/apply/run_observe_plan.py; system/lib/observe_surfaces.py; system/lib/observe_plan_enrichment.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
import math
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from system.lib.markdown_routing import normalize_repo_relative_path
from system.lib.observe_surfaces import build_observe_resume_surface

GROUPED_RUNTIME_TERMINAL_STATES = {"aborted", "completed", "error"}
GROUPED_OBSERVE_TERMINAL_GROUP_STATUSES = {
    "success",
    "quality_error",
    "error",
    "aborted",
    "blocked",
    "skipped_no_dump",
    "skipped_missing_dump",
}

RETRYABLE_OBSERVE_ERROR_CATEGORIES = {
    "bridge_group_timeout",
    "bridge_error",
    "browser_launch_failed",
    "cdp_unreachable",
    "provider_cancelled",
    "provider_challenge",
    "provider_selector_failure",
    "provider_submit_failed_fast",
    "provider_timeout",
    "provider_unavailable",
}

RETRYABLE_OBSERVE_ERROR_STAGES = {
    "browser",
    "provider_extract",
    "provider_open",
    "provider_interaction",
    "provider_queue",
    "provider_submit",
    "provider_wait",
}

RETRYABLE_OBSERVE_ERROR_SUBSTRINGS = (
    "broken pipe",
    "cdp ",
    "cdp_",
    "chrome launched but cdp",
    "cloudflare",
    "cf_challenge",
    "editor not found",
    "send button",
    "timeout waiting for ai response",
)

DEGRADED_OBSERVE_GROUP_STATUSES = {
    "quality_error",
    "error",
    "aborted",
    "blocked",
    "skipped_no_dump",
    "skipped_missing_dump",
}

NON_AUTORETRY_REASONS = {
    "group_aborted",
    "non_retryable_failure",
    "quality_gate_failed",
}

LAUNCH_PROFILES = ("safe", "experimental")
DEFAULT_LAUNCH_PROFILE = "experimental"
DEFAULT_SAFE_STAGGER_MS = 100
DEFAULT_EXPERIMENTAL_STAGGER_MS = 0
DEFAULT_MAX_WORKERS = 15
DEFAULT_BRIDGE_RECOMMENDED_PROMPT_CHARS = 200_000
DEFAULT_BRIDGE_HARD_PROMPT_CHARS = 800_000
DEFAULT_CYCLE_TIMELINE_BASENAME = "cycle_timeline.jsonl"


def now_iso() -> str:
    """[ACTION]
    - Teleology: Emit the canonical UTC timestamp string used across grouped-observe runtime manifests and status updates.
    - Mechanism: Read the current UTC time via datetime.now(timezone.utc) and serialize it with isoformat().
    - Reads: System clock.
    - Writes: None.
    - Guarantee: Returns an ISO-8601 timestamp string with timezone information.
    - Fails: None.
    - When-needed: Open when runtime manifest or status code needs the exact timestamp primitive shared by grouped observe writes.
    - Escalates-to: system/lib/observe_runtime.py::write_json; tools/meta/apply/run_observe_plan.py
    """
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Safely load one mapping-shaped runtime JSON artifact without forcing callers to duplicate fallback logic.
    - Mechanism: Read and decode the file as JSON, returning the payload only when it is a dict; otherwise return a copy of the supplied default mapping.
    - Reads: path.
    - Writes: None.
    - Guarantee: Returns a dict for any input, falling back to `default` or `{}` on read, parse, or shape failure.
    - Fails: None.
    - When-needed: Open when grouped runtime status or manifest code needs the canonical tolerant JSON loader for runtime artifacts.
    - Escalates-to: system/lib/observe_runtime.py::write_json; tools/meta/apply/run_observe_plan.py
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default or {})
    return dict(payload) if isinstance(payload, dict) else dict(default or {})


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """[ACTION]
    - Teleology: Persist one runtime mapping atomically so grouped-observe state files do not tear during updates.
    - Mechanism: Serialize the payload to pretty JSON, write it through a temporary sibling file, fsync the temp handle, then replace the target path.
    - Reads: payload and path.parent.
    - Writes: The target JSON file at `path`, via a temporary file in the same directory.
    - Guarantee: Leaves either the previous file or the fully serialized new file at `path`; parent directories are created when missing.
    - Fails: Propagates filesystem exceptions from temp-file creation, fsync, replace, or cleanup.
    - When-needed: Open when grouped runtime manifests or status snapshots need the authoritative atomic-write helper instead of ad hoc JSON writes.
    - Escalates-to: system/lib/observe_runtime.py::read_json; tools/meta/apply/run_observe_plan.py
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(dict(payload), ensure_ascii=False, indent=2)
    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
            tmp_path = Path(handle.name)
        os.replace(tmp_path, path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    """[ACTION]
    - Teleology: Append one grouped-runtime event record to a JSONL timeline without rewriting the full file.
    - Mechanism: Ensure the parent exists, serialize the mapping as one JSON line, append it, flush, and fsync the file handle.
    - Reads: payload and path.parent.
    - Writes: One newline-terminated JSON object appended to `path`.
    - Guarantee: Appends exactly one JSONL record when the write succeeds.
    - Fails: Propagates filesystem exceptions from mkdir(), open(), write(), flush(), or fsync().
    - When-needed: Open when grouped observe runtime code needs the canonical append-only event writer for timelines or status ledgers.
    - Escalates-to: system/lib/observe_runtime.py::observe_cycle_timeline_path; tools/meta/apply/run_observe_plan.py
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(dict(payload), ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def observe_cycle_timeline_path(repo_root: Path, dump_dir: str) -> Path:
    """[ACTION]
    - Teleology: Resolve the append-only timeline file path for one grouped observe cycle dump directory.
    - Mechanism: Require a non-blank dump_dir and join DEFAULT_CYCLE_TIMELINE_BASENAME under the resolved repo-relative dump directory.
    - Reads: repo_root and dump_dir.
    - Writes: None.
    - Guarantee: Returns an absolute Path ending with DEFAULT_CYCLE_TIMELINE_BASENAME for the supplied dump directory.
    - Fails: Raises ValueError when dump_dir is blank.
    - When-needed: Open when grouped runtime status or event logging needs the authoritative cycle timeline location before writing JSONL events.
    - Escalates-to: system/lib/observe_runtime.py::append_jsonl; tools/meta/apply/run_observe_plan.py
    """
    rel = str(dump_dir or "").strip()
    if not rel:
        raise ValueError("dump_dir is required to resolve cycle timeline path")
    return (repo_root / rel).resolve() / DEFAULT_CYCLE_TIMELINE_BASENAME


def config_value(value: Any, default: Any = None) -> Any:
    """[ACTION]
    - Teleology: Normalize config fields that may be stored either as raw literals or `{value: ...}` wrappers.
    - Mechanism: Return `mapping['value']` when the input is a mapping carrying that key; otherwise return the original value or the supplied default when the value is None.
    - Reads: value and default.
    - Writes: None.
    - Guarantee: Returns one resolved config value suitable for downstream integer or string coercion.
    - Fails: None.
    - When-needed: Open when runtime config parsing needs the canonical unwrap rule for optional `{value: ...}` config entries.
    - Escalates-to: system/lib/observe_runtime.py::load_master_config; system/lib/observe_runtime.py::resolve_bridge_prompt_budget
    - Navigation-group: kernel_lib
    """
    if isinstance(value, Mapping) and "value" in value:
        return value.get("value")
    return value if value is not None else default


def load_master_config(repo_root: Path) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Load the repo-wide master observe/runtime config without forcing callers to hand-roll missing-file handling.
    - Mechanism: Delegate to system/lib/kernel/config.py::load_master_config_at, the canonical tolerant loader shared across the federated config plane.
    - Reads: repo_root and `master_config.json`.
    - Writes: None.
    - Guarantee: Returns a mapping-shaped master config, defaulting to `{}` when the file is missing, empty, malformed, or non-object.
    - Fails: None.
    - When-needed: Open when observe runtime code needs the authoritative loader for repo-level master configuration.
    - Escalates-to: system/lib/kernel/config.py::load_master_config_at; system/lib/observe_runtime.py::resolve_bridge_prompt_budget
    - Navigation-group: kernel_lib
    """
    from system.lib.kernel.config import load_master_config_at
    return load_master_config_at(repo_root)


def resolve_bridge_prompt_budget(repo_root: Path) -> dict[str, int]:
    """[ACTION]
    - Teleology: Resolve the recommended and hard prompt-character budgets that grouped observe should honor for bridge prompts.
    - Mechanism: Load master_config.json, read the observe section, normalize wrapped config values, coerce positive integers, and fall back to standard defaults when values are absent or invalid.
    - Reads: repo_root, `master_config.json`, DEFAULT_BRIDGE_RECOMMENDED_PROMPT_CHARS, and DEFAULT_BRIDGE_HARD_PROMPT_CHARS.
    - Writes: None.
    - Guarantee: Returns a dict containing positive `recommended_prompt_chars` and `hard_prompt_chars` integers.
    - Fails: None.
    - When-needed: Open when prompt shaping or bridge dispatch needs the canonical prompt-budget resolution rule from master config.
    - Escalates-to: system/lib/observe_runtime.py::load_master_config; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    config = load_master_config(repo_root)
    observe_cfg = config.get("observe")
    if not isinstance(observe_cfg, Mapping):
        observe_cfg = {}

    def _positive_int(key: str, default: int) -> int:
        raw = config_value(observe_cfg.get(key), default)
        try:
            resolved = int(raw)
        except (TypeError, ValueError):
            return default
        return resolved if resolved > 0 else default

    return {
        "recommended_prompt_chars": _positive_int(
            "max_recommended_prompt_chars",
            DEFAULT_BRIDGE_RECOMMENDED_PROMPT_CHARS,
        ),
        "hard_prompt_chars": _positive_int(
            "max_hard_prompt_chars",
            DEFAULT_BRIDGE_HARD_PROMPT_CHARS,
        ),
    }


def normalize_context_merge_mode(value: object) -> str:
    """[ACTION]
    - Teleology: Normalize grouped-observe context merge mode values into the stable runtime tokens used across dump compilation, dispatch, and validation.
    - Mechanism: Lowercase and trim the candidate string, accepting only `merge` and `group_only`, otherwise defaulting to `merge`.
    - Reads: value.
    - Writes: None.
    - Guarantee: Returns either `merge` or `group_only`.
    - Fails: None.
    - When-needed: Open when grouped observe code needs one authoritative interpretation of `context_merge_mode`.
    - Escalates-to: system/lib/observe_runtime.py::resolve_group_evidence_contract; tools/meta/apply/run_observe_plan.py; kernel.py
    - Navigation-group: kernel_lib
    """
    token = str(value or "merge").strip().lower()
    return token if token in {"merge", "group_only"} else "merge"


def _normalize_observe_evidence_path(repo_root: Path, raw_path: object) -> str:
    token = str(raw_path or "").strip()
    if not token:
        return ""
    normalized = normalize_repo_relative_path(token, repo_root=repo_root)
    return str(normalized or token).strip()


def resolve_group_evidence_contract(
    repo_root: Path,
    *,
    plan_context_files: Sequence[str] | object,
    group_context_files: Sequence[str] | object,
    targets: Sequence[Mapping[str, Any]] | object,
    context_merge_mode: object = "merge",
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Compute the canonical per-group evidence contract so dump compilation, bridge prompt validation, kernel previews, and prompt-manifest audit all operate on the same effective evidence set.
    - Mechanism: Normalize authored context and target paths, merge plan/group context according to `context_merge_mode`, then drop any context path that already appears as a target because target evidence wins.
    - Reads: repo_root plus authored plan context, group context, and targets.
    - Writes: None.
    - Guarantee: Returns normalized plan/group context lists, effective deduped context files, exact context-target overlaps, unique target entries, and role-aware audit file rows.
    - Fails: None.
    - When-needed: Open when grouped observe surfaces need one authoritative answer to “what evidence is actually injected for this group?”
    - Escalates-to: tools/meta/apply.py::SourceSurgeon._observe_grouped; tools/meta/apply/run_observe_plan.py; tools/meta/bridge/dispatch_validator.py; kernel.py
    - Navigation-group: kernel_lib
    """
    merge_mode = normalize_context_merge_mode(context_merge_mode)

    def _normalize_path_list(values: Sequence[str] | object) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            values = []
        for raw in values:
            path = _normalize_observe_evidence_path(repo_root, raw)
            if not path or path in seen:
                continue
            seen.add(path)
            normalized.append(path)
        return normalized

    normalized_plan_context = _normalize_path_list(plan_context_files)
    normalized_group_context = _normalize_path_list(group_context_files)

    target_entries: list[dict[str, Any]] = []
    target_files: list[str] = []
    seen_target_paths: set[str] = set()
    if isinstance(targets, Sequence) and not isinstance(targets, (str, bytes)):
        for raw_target in targets:
            if not isinstance(raw_target, Mapping):
                continue
            path = _normalize_observe_evidence_path(repo_root, raw_target.get("file"))
            if not path or path in seen_target_paths:
                continue
            seen_target_paths.add(path)
            scope = str(raw_target.get("scope", "full") or "full").strip() or "full"
            target_entries.append({"path": path, "scope": scope, "role": "target"})
            target_files.append(path)

    merged_context_files = (
        list(normalized_group_context)
        if merge_mode == "group_only"
        else list(dict.fromkeys([*normalized_plan_context, *normalized_group_context]))
    )
    overlap_paths = [path for path in merged_context_files if path in seen_target_paths]
    effective_context_files = [path for path in merged_context_files if path not in seen_target_paths]
    audit_file_entries = [
        *target_entries,
        *({"path": path, "role": "context"} for path in effective_context_files),
    ]

    return {
        "context_merge_mode": merge_mode,
        "plan_context_files": normalized_plan_context,
        "group_context_files": normalized_group_context,
        "merged_context_files": merged_context_files,
        "effective_context_files": effective_context_files,
        "context_target_overlaps": overlap_paths,
        "target_files": target_files,
        "target_entries": target_entries,
        "audit_file_entries": audit_file_entries,
    }


def suggested_prompt_split_count(prompt_chars: int, *, recommended_prompt_chars: int) -> int:
    """[ACTION]
    - Teleology: Estimate how many prompt slices a grouped-observe bridge prompt should be split into relative to the recommended budget.
    - Mechanism: Return 1 for non-positive inputs, otherwise divide prompt_chars by recommended_prompt_chars and round up.
    - Reads: prompt_chars and recommended_prompt_chars.
    - Writes: None.
    - Guarantee: Returns a positive integer split count of at least 1.
    - Fails: None.
    - When-needed: Open when prompt shaping needs the canonical split-count heuristic before batch or bridge dispatch decisions.
    - Escalates-to: system/lib/observe_runtime.py::resolve_bridge_prompt_budget; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    if prompt_chars <= 0 or recommended_prompt_chars <= 0:
        return 1
    return max(1, int(math.ceil(prompt_chars / float(recommended_prompt_chars))))


def normalize_launch_profile(value: Any, *, default: str = DEFAULT_LAUNCH_PROFILE) -> str:
    """[ACTION]
    - Teleology: Normalize launch-profile inputs so grouped observe chooses a known runtime launch mode.
    - Mechanism: Lowercase and trim the candidate string, return it only when it matches LAUNCH_PROFILES, otherwise fall back to the supplied default.
    - Reads: value, default, and LAUNCH_PROFILES.
    - Writes: None.
    - Guarantee: Returns a valid launch-profile string from LAUNCH_PROFILES.
    - Fails: None.
    - When-needed: Open when runtime policy or CLI argument parsing needs the canonical launch-profile normalization rule.
    - Escalates-to: system/lib/observe_runtime.py::observe_runtime_policy; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    candidate = str(value or "").strip().lower()
    if candidate in LAUNCH_PROFILES:
        return candidate
    return default


def normalize_requested_workers(value: Any) -> tuple[str, Optional[int]]:
    """[ACTION]
    - Teleology: Normalize worker-count requests into either auto mode or one validated fixed-count request.
    - Mechanism: Accept blank or `auto` as automatic mode, otherwise parse a positive integer and reject invalid or non-positive requests with ValueError.
    - Reads: value.
    - Writes: None.
    - Guarantee: Returns `(\"auto\", None)` for auto mode or `(\"fixed\", <positive int>)` for explicit worker counts.
    - Fails: Raises ValueError when the worker request cannot be parsed as a positive integer.
    - When-needed: Open when grouped observe launch logic needs the canonical worker-request normalization and validation rule.
    - Escalates-to: system/lib/observe_runtime.py::resolve_effective_workers; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    text = str(value or "").strip().lower()
    if not text or text == "auto":
        return "auto", None
    try:
        parsed = int(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid worker request: {value}") from exc
    if parsed <= 0:
        raise ValueError("worker request must be > 0")
    return "fixed", parsed


def observe_runtime_policy(repo_root: Path) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Materialize the runtime policy that bounds grouped observe launches for the current repo.
    - Mechanism: Read `master_config.json`, normalize observe and execution settings, and return launch-profile, stagger, and worker-ceiling fields with defaults.
    - Guarantee: Returns a dict with default_launch_profile, safe_launch_stagger_ms, experimental_launch_stagger_ms, and max_workers_ceiling keys.
    - Fails: None.
    - When-needed: Open when grouped observe execution needs the repo's authoritative launch profile and worker ceiling before dispatch.
    - Escalates-to: system/lib/observe_runtime.py::resolve_effective_workers; tools/meta/apply/run_observe_plan.py
    """
    config = load_master_config(repo_root)
    observe_cfg = config.get("observe")
    execution_cfg = config.get("execution")
    if not isinstance(observe_cfg, dict):
        observe_cfg = {}
    if not isinstance(execution_cfg, dict):
        execution_cfg = {}

    def _positive_int(section: Mapping[str, Any], key: str, default: int) -> int:
        raw = config_value(section.get(key), default)
        try:
            parsed = int(raw)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    def _nonnegative_int(section: Mapping[str, Any], key: str, default: int) -> int:
        raw = config_value(section.get(key), default)
        try:
            parsed = int(raw)
        except (TypeError, ValueError):
            return default
        return parsed if parsed >= 0 else default

    return {
        "default_launch_profile": normalize_launch_profile(
            config_value(observe_cfg.get("default_launch_profile"), DEFAULT_LAUNCH_PROFILE)
        ),
        "safe_launch_stagger_ms": _nonnegative_int(
            observe_cfg,
            "safe_launch_stagger_ms",
            DEFAULT_SAFE_STAGGER_MS,
        ),
        "experimental_launch_stagger_ms": _nonnegative_int(
            observe_cfg, "experimental_launch_stagger_ms", DEFAULT_EXPERIMENTAL_STAGGER_MS
        ),
        "max_workers_ceiling": _positive_int(execution_cfg, "max_workers", DEFAULT_MAX_WORKERS),
    }


def resolve_effective_workers(
    *,
    repo_root: Path,
    requested_workers: Any,
    launch_profile: str,
    wave_size: int,
    provider: Any = None,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Reduce requested worker input, runtime policy, and wave size into the actual worker count a grouped observe run may use.
    - Mechanism: Load runtime policy, normalize requested workers and launch profile, clamp to the execution ceiling, then cap against the wave size and the live provider-pressure budget when a provider is supplied.
    - Guarantee: Returns a dict containing policy, requested_workers_mode, requested_workers_value, requested_workers_ceiling, effective_workers, launch_profile, and provider_live_ceiling.
    - Fails: ValueError only when the requested worker token is not parseable as `auto` or a positive integer.
    - When-needed: Open when dispatch logic needs the exact effective worker count rather than the raw CLI request.
    - Escalates-to: system/lib/observe_runtime.py::observe_runtime_policy; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    policy = observe_runtime_policy(repo_root)
    ceiling = max(1, int(policy["max_workers_ceiling"]))
    provider_live_ceiling: int | None = None
    provider_token = str(provider or "").strip().lower()
    if provider_token:
        try:
            from system.lib import metabolism_store as _metabolism_store

            conn = _metabolism_store.connect(repo_root)
            try:
                row = _metabolism_store.get_provider_row(conn, provider_token)
            finally:
                conn.close()
            budget = dict(row.get("budget") or {})
            parsed_ceiling = int(budget.get("max_concurrent") or 0)
            if parsed_ceiling > 0:
                provider_live_ceiling = parsed_ceiling
                ceiling = min(ceiling, parsed_ceiling)
        except Exception:
            provider_live_ceiling = None
    requested_mode, requested_fixed = normalize_requested_workers(requested_workers)
    requested_value = ceiling if requested_mode == "auto" else max(1, int(requested_fixed or 1))
    bounded_requested = min(requested_value, ceiling)
    profile = normalize_launch_profile(launch_profile, default=str(policy["default_launch_profile"]))

    effective = min(max(1, wave_size), bounded_requested)

    return {
        "policy": policy,
        "launch_profile": profile,
        "requested_workers_mode": requested_mode,
        "requested_workers_value": (None if requested_mode == "auto" else requested_fixed),
        "requested_workers_ceiling": bounded_requested,
        "effective_workers": max(1, effective),
        "provider": provider_token or None,
        "provider_live_ceiling": provider_live_ceiling,
    }


def grouped_observe_waves(groups: Iterable[Mapping[str, Any]]) -> tuple[list[list[str]], dict[str, int]]:
    """[ACTION]
    - Teleology: Convert authored observe groups into dependency-safe execution waves.
    - Mechanism: Normalize group labels and depends_on lists, validate duplicates and missing dependencies, then perform a topological layering pass that emits ordered waves and wave indexes by label.
    - Guarantee: Returns `(waves, wave_by_label)` where every group label appears exactly once if the dependency graph is valid.
    - Fails: ValueError on duplicate labels, unknown depends_on targets, self-dependencies, or cycles.
    - When-needed: Open when an authored grouped observe plan must be stratified into executable waves before runtime launch.
    - Escalates-to: tools/meta/apply/run_observe_plan.py; system/lib/observe_plan_enrichment.py
    - Navigation-group: kernel_lib
    """
    normalized: list[dict[str, Any]] = []
    label_order: list[str] = []
    label_set: set[str] = set()
    for idx, group in enumerate(groups, start=1):
        label = str(group.get("label") or f"group_{idx}").strip() or f"group_{idx}"
        if label in label_set:
            raise ValueError(f"duplicate group label: {label}")
        deps = [
            str(item).strip()
            for item in group.get("depends_on", [])
            if str(item).strip()
        ] if isinstance(group.get("depends_on"), list) else []
        normalized.append({"label": label, "depends_on": deps})
        label_order.append(label)
        label_set.add(label)

    for group in normalized:
        for dep in group["depends_on"]:
            if dep not in label_set:
                raise ValueError(f"group '{group['label']}' depends_on unknown label '{dep}'")
            if dep == group["label"]:
                raise ValueError(f"group '{group['label']}' cannot depend_on itself")

    waves: list[list[str]] = []
    wave_by_label: dict[str, int] = {}
    remaining = {group["label"] for group in normalized}
    completed: set[str] = set()

    while remaining:
        ready = [
            label
            for label in label_order
            if label in remaining
            and all(dep in completed for dep in next(group["depends_on"] for group in normalized if group["label"] == label))
        ]
        if not ready:
            raise ValueError("grouped observe dependencies contain a cycle")
        wave_index = len(waves)
        waves.append(ready)
        for label in ready:
            remaining.remove(label)
            completed.add(label)
            wave_by_label[label] = wave_index

    return waves, wave_by_label


def grouped_runtime_dir(history_dir: Path) -> Path:
    """[ACTION]
    - Teleology: Resolve the runtime sidecar directory used to store grouped-observe status manifests under one observe history root.
    - Mechanism: Append `runtime` to the supplied history_dir.
    - Reads: history_dir.
    - Writes: None.
    - Guarantee: Returns the canonical runtime sidecar directory Path for the supplied history root.
    - Fails: None.
    - When-needed: Open when grouped observe status code needs the authoritative runtime-sidecar directory before reading or writing manifests.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_path; system/lib/observe_runtime.py::write_grouped_runtime_manifest
    - Navigation-group: kernel_lib
    """
    return history_dir / "runtime"


def grouped_runtime_path(history_dir: Path, observe_id: str) -> Path:
    """[ACTION]
    - Teleology: Resolve the canonical runtime manifest path for one grouped observe id.
    - Mechanism: Reuse grouped_runtime_dir() and append `<observe_id>.json`.
    - Reads: history_dir and observe_id.
    - Writes: None.
    - Guarantee: Returns the runtime manifest Path for the supplied observe id.
    - Fails: None.
    - When-needed: Open when grouped observe status writes or reads need the authoritative per-observe runtime manifest location.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_dir; system/lib/observe_runtime.py::write_grouped_runtime_manifest
    - Navigation-group: kernel_lib
    """
    return grouped_runtime_dir(history_dir) / f"{observe_id}.json"


def grouped_runtime_current_path(history_dir: Path) -> Path:
    """[ACTION]
    - Teleology: Resolve the canonical pointer file for the most recent grouped-observe runtime manifest under one history root.
    - Mechanism: Reuse grouped_runtime_dir() and append `current.json`.
    - Reads: history_dir.
    - Writes: None.
    - Guarantee: Returns the runtime current-pointer Path for the supplied history root.
    - Fails: None.
    - When-needed: Open when grouped observe launch or resume code needs the authoritative `current.json` sidecar location.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_dir; system/lib/observe_runtime.py::write_grouped_runtime_manifest
    - Navigation-group: kernel_lib
    """
    return grouped_runtime_dir(history_dir) / "current.json"


def write_grouped_runtime_manifest(history_dir: Path, payload: Mapping[str, Any]) -> Path:
    """[ACTION]
    - Teleology: Persist the runtime manifest for one grouped observe run and refresh the shared current-pointer sidecar in one call.
    - Mechanism: Require a non-blank observe_id, derive the per-run manifest path, write the payload there, then mirror the same payload into `current.json`.
    - Reads: history_dir and payload['observe_id'].
    - Writes: The per-observe runtime manifest plus the shared current-pointer manifest under the runtime sidecar directory.
    - Guarantee: Returns the canonical per-observe runtime manifest path after both JSON files are written.
    - Fails: Raises ValueError when observe_id is blank; filesystem exceptions from write_json() propagate.
    - When-needed: Open when grouped observe launch or status code needs the authoritative manifest-write path for runtime sidecars.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_path; system/lib/observe_runtime.py::grouped_runtime_current_path
    - Navigation-group: kernel_lib
    """
    observe_id = str(payload.get("observe_id") or "").strip()
    if not observe_id:
        raise ValueError("runtime manifest requires observe_id")
    runtime_path = grouped_runtime_path(history_dir, observe_id)
    write_json(runtime_path, payload)
    write_json(grouped_runtime_current_path(history_dir), payload)
    return runtime_path


def clear_grouped_runtime_current(history_dir: Path, observe_id: str) -> None:
    """[ACTION]
    - Teleology: Clear the shared current-pointer runtime manifest only when it still points at the observe run being finished or superseded.
    - Mechanism: Read `current.json`, compare its observe_id with the supplied observe_id, and unlink the file only on an exact trimmed match.
    - Reads: history_dir, observe_id, and the existing current-pointer manifest.
    - Writes: Deletes `current.json` when it still belongs to the supplied observe run.
    - Guarantee: Leaves unrelated current-pointer manifests untouched.
    - Fails: None.
    - When-needed: Open when grouped observe teardown or status cleanup needs the exact rule for clearing the shared current-pointer manifest.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_current_path; system/lib/observe_runtime.py::write_grouped_runtime_manifest
    - Navigation-group: kernel_lib
    """
    current_path = grouped_runtime_current_path(history_dir)
    current = read_json(current_path)
    if str(current.get("observe_id") or "").strip() == str(observe_id).strip():
        if current_path.exists():
            current_path.unlink()


def grouped_runtime_idle_payload() -> dict[str, Any]:
    """[ACTION]
    - Teleology: Emit the canonical idle runtime payload so status readers have one stable empty-state shape before any grouped observe run starts.
    - Mechanism: Return a dict literal that prepopulates every grouped runtime field with idle-safe defaults.
    - Reads: None.
    - Writes: None.
    - Guarantee: Returns a mapping-shaped grouped runtime payload with `state=idle` and all optional runtime fields present.
    - Fails: None.
    - When-needed: Open when grouped observe status surfaces need the authoritative idle manifest shape instead of inventing one ad hoc.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_status_payload; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    return {
        "kind": "grouped_observe",
        "observe_id": None,
        "session_slug": None,
        "state": "idle",
        "launch_profile": None,
        "requested_workers": None,
        "effective_workers": None,
        "wave_index": 0,
        "wave_total": 0,
        "total_groups": 0,
        "completed_groups": 0,
        "progress": {
            "total_groups": 0,
            "completed_groups": 0,
            "remaining_groups": 0,
            "percent_complete": 0,
            "active_group_labels": [],
            "pending_group_labels": [],
            "status_counts": {},
            "summary": "idle",
            "last_update_at": None,
        },
        "provider": None,
        "provider_transport": None,
        "latest_stable_artifact": None,
        "status_authority": "idle",
        "status_manifest": None,
        "manifest": None,
        "history_entry": None,
        "pid": None,
        "started_at": None,
        "updated_at": None,
        "cancel_requested_at": None,
        "error": None,
        "round_id": None,
        "error_count": 0,
        "can_continue": False,
        "continue_mode": None,
        "continue_reason": None,
        "pending_group_labels": [],
        "retryable_group_labels": [],
        "launch_receipt": {},
        "launch_dispatch": None,
        "continuation": {},
        "readback_state": {},
        "promoted_surface": {},
        "resume_surface": {},
        "lineage": {},
        "artifacts": {},
        "groups": [],
    }


def normalize_observe_runtime_state(kind: object, state: object) -> str:
    """[ACTION]
    - Teleology: Normalize mixed observe runtime state labels into the canonical status vocabulary expected by grouped-runtime and session-status readers.
    - Mechanism: Coerce kind and state to stripped strings, default blank states to `idle`, and remap the `observe_session` terminal alias `done` to `completed`.
    - Reads: The supplied runtime `kind` and `state` values.
    - Writes: None.
    - Guarantee: Returns one normalized lowercase runtime-state string, with observe-session `done` states rewritten to `completed`.
    - Fails: None.
    - When-needed: Open when grouped observe or session status code needs the exact normalization rule for mixed runtime state labels before building a status payload.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_status_payload; system/server/observe_session.py; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    runtime_kind = str(kind or "").strip()
    runtime_state = str(state or "").strip().lower() or "idle"
    if runtime_kind == "observe_session" and runtime_state == "done":
        return "completed"
    return runtime_state


def grouped_runtime_resolved_group_state(group: Mapping[str, Any]) -> str:
    """[ACTION]
    - Teleology: Resolve one grouped-observe node into the authoritative state token that downstream retry and pending-group logic should inspect.
    - Mechanism: Prefer `response_status` when it is one of the known terminal group statuses; otherwise fall back to `runtime_state`, then `response_status`, then `pending`.
    - Reads: The grouped runtime node mapping plus `GROUPED_OBSERVE_TERMINAL_GROUP_STATUSES`.
    - Writes: None.
    - Guarantee: Returns one state string for the supplied group, favoring terminal response outcomes over in-flight runtime state labels.
    - Fails: None.
    - When-needed: Open when grouped-runtime status, retryability, or pending-group code needs the canonical rule for collapsing a node's runtime and response fields into one state.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_pending_group_labels; system/lib/observe_runtime.py::grouped_runtime_status_payload; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    runtime_state = str(group.get("runtime_state") or "").strip()
    response_status = str(group.get("response_status") or "").strip()
    if response_status in GROUPED_OBSERVE_TERMINAL_GROUP_STATUSES:
        return response_status
    return runtime_state or response_status or "pending"


def grouped_runtime_pending_group_labels(runtime: Mapping[str, Any]) -> list[str]:
    """[ACTION]
    - Teleology: Derive the deduplicated roster of grouped-observe labels that still have in-flight or unresolved work.
    - Mechanism: Iterate the runtime `groups` list, skip non-mapping rows, resolve each group through `grouped_runtime_resolved_group_state()`, and collect unique labels whose state is not terminal.
    - Reads: The grouped runtime mapping, its `groups` list, and `GROUPED_OBSERVE_TERMINAL_GROUP_STATUSES`.
    - Writes: None.
    - Guarantee: Returns a stable-order list of unique pending group labels, or `[]` when no valid non-terminal groups exist.
    - Fails: None.
    - When-needed: Open when grouped-runtime status, continue-mode, or cancellation tooling needs the authoritative list of non-terminal group labels.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_has_pending_groups; system/lib/observe_runtime.py::grouped_runtime_status_payload; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    groups = runtime.get("groups")
    if not isinstance(groups, list):
        return []
    labels: list[str] = []
    for group in groups:
        if not isinstance(group, Mapping):
            continue
        state = grouped_runtime_resolved_group_state(group)
        if state in GROUPED_OBSERVE_TERMINAL_GROUP_STATUSES:
            continue
        label = str(group.get("label") or "").strip()
        if label and label not in labels:
            labels.append(label)
    return labels


def grouped_runtime_has_pending_groups(runtime: Mapping[str, Any]) -> bool:
    """[ACTION]
    - Teleology: Collapse the pending-group label derivation into the boolean gate that grouped-runtime continuation and status callers actually branch on.
    - Mechanism: Reuse `grouped_runtime_pending_group_labels()` and return whether it produced any unresolved labels.
    - Reads: The grouped runtime mapping plus the pending-label resolution performed by `grouped_runtime_pending_group_labels()`.
    - Writes: None.
    - Guarantee: Returns `True` when at least one valid non-terminal group label remains pending; otherwise returns `False`.
    - Fails: None.
    - When-needed: Open when grouped-runtime continuation or status code only needs the yes-or-no pending-work gate rather than the full pending label list.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_pending_group_labels; system/lib/observe_runtime.py::grouped_runtime_status_payload; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    return bool(grouped_runtime_pending_group_labels(runtime))


def grouped_runtime_group_has_retryable_failure(group: object) -> bool:
    """[ACTION]
    - Teleology: Decide whether one grouped-observe result should be treated as retryable before continuation, degradation, or session-status code schedules more work.
    - Mechanism: Reject non-mappings, then inspect normalized response status, quality-gate metadata, error category, stage, body, and error text against the retryable policy constants and stopped-response heuristics.
    - Reads: The supplied group object, `RETRYABLE_OBSERVE_ERROR_CATEGORIES`, `RETRYABLE_OBSERVE_ERROR_STAGES`, and `RETRYABLE_OBSERVE_ERROR_SUBSTRINGS`.
    - Writes: None.
    - Guarantee: Returns `True` only for aborted groups or error/quality-error shapes that match the module's retryable-failure policy; otherwise returns `False`.
    - Fails: None.
    - When-needed: Open when grouped-runtime continuation, degraded-diagnostics, or observe-session status code needs the exact predicate for whether a group failure is retryable.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_group_retry_reason; system/lib/observe_runtime.py::grouped_runtime_retryable_failure_labels; system/server/observe_session.py::_session_group_retry_metadata
    - Navigation-group: kernel_lib
    """
    if not isinstance(group, Mapping):
        return False
    response_status = str(group.get("response_status") or "").strip()
    response_body = str(group.get("response_body") or "").strip()
    normalized_body = re.sub(r"\s+", " ", response_body).strip().lower()
    if response_status == "aborted":
        return True
    if response_status == "quality_error":
        category = str(group.get("response_error_category") or "").strip()
        if category == "response_incomplete" and (
            "you stopped this response" in normalized_body
            or re.fullmatch(r"(answer now\s+)?(gemini|chatgpt)\s+said:?(?:\s+you stopped this response)?", normalized_body)
        ):
            return True
        return False
    if response_status != "error":
        return False
    category = str(group.get("response_error_category") or "").strip()
    if category in RETRYABLE_OBSERVE_ERROR_CATEGORIES:
        return True
    stage = str(group.get("response_error_stage") or "").strip()
    if stage in RETRYABLE_OBSERVE_ERROR_STAGES and not response_body:
        return True
    error_text = str(group.get("response_error") or "").strip().lower()
    return any(token in error_text for token in RETRYABLE_OBSERVE_ERROR_SUBSTRINGS)


def grouped_runtime_group_retry_reason(group: object) -> Optional[str]:
    """[ACTION]
    - Teleology: Emit the stable retry-reason token that explains why a grouped-observe failure is retryable, blocked, or non-retryable.
    - Mechanism: Mirror the retryability classifier over aborted, quality-error, and error states, returning category- or stage-level reason codes plus fallback tokens for quality-gate and non-retryable failures.
    - Reads: The supplied group object, `RETRYABLE_OBSERVE_ERROR_CATEGORIES`, `RETRYABLE_OBSERVE_ERROR_STAGES`, and `RETRYABLE_OBSERVE_ERROR_SUBSTRINGS`.
    - Writes: None.
    - Guarantee: Returns `None` for non-error statuses; otherwise returns one stable reason token describing the matched retry or failure condition.
    - Fails: None.
    - When-needed: Open when grouped-runtime diagnostics or session-status payloads need the canonical reason code paired with retryability for one group failure.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_group_has_retryable_failure; system/lib/observe_runtime.py::observe_group_retry_diagnostic; system/server/observe_session.py::_session_group_retry_metadata
    - Navigation-group: kernel_lib
    """
    if not isinstance(group, Mapping):
        return None
    response_status = str(group.get("response_status") or "").strip()
    response_body = str(group.get("response_body") or "").strip()
    normalized_body = re.sub(r"\s+", " ", response_body).strip().lower()
    if response_status == "aborted":
        return "group_aborted"
    if response_status == "quality_error":
        category = str(group.get("response_error_category") or "").strip()
        if category == "response_incomplete" and (
            "you stopped this response" in normalized_body
            or re.fullmatch(r"(answer now\s+)?(gemini|chatgpt)\s+said:?(?:\s+you stopped this response)?", normalized_body)
        ):
            return category
        return "quality_gate_failed"
    if response_status != "error":
        return None
    category = str(group.get("response_error_category") or "").strip()
    if category in RETRYABLE_OBSERVE_ERROR_CATEGORIES:
        return category
    stage = str(group.get("response_error_stage") or "").strip()
    if stage in RETRYABLE_OBSERVE_ERROR_STAGES and not response_body:
        return stage
    error_text = str(group.get("response_error") or "").strip().lower()
    if any(token in error_text for token in RETRYABLE_OBSERVE_ERROR_SUBSTRINGS):
        return "bridge_error_like_failure"
    return "non_retryable_failure"


def _coerce_retryable_group_view(group: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "response_status": (
            str(
                group.get("response_status")
                or group.get("runtime_state")
                or group.get("status")
                or ""
            ).strip()
        ),
        "response_body": str(group.get("response_body") or group.get("body") or "").strip(),
        "response_error_category": (
            str(group.get("response_error_category") or group.get("error_category") or "").strip()
        ),
        "response_error_stage": (
            str(group.get("response_error_stage") or group.get("error_stage") or "").strip()
        ),
        "response_error": str(group.get("response_error") or group.get("error") or "").strip(),
    }


def observe_group_retry_diagnostic(group: object) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Produce a normalized retry-diagnostic record for one grouped-observe result, unifying retryability, reason, and transport metadata into one shape.
    - Guarantee: Returns a dict with label, status, role, error, error_category, error_stage, transport, retryable, retry_reason, and auto_retry_safe fields.
    - Fails: None.
    """
    if not isinstance(group, Mapping):
        return {
            "label": None,
            "status": "unknown",
            "role": "probe",
            "error": None,
            "error_category": None,
            "error_stage": None,
            "transport": None,
            "retryable": False,
            "retry_reason": None,
            "auto_retry_safe": False,
        }

    retry_view = _coerce_retryable_group_view(group)
    retryable = grouped_runtime_group_has_retryable_failure(retry_view)
    retry_reason = grouped_runtime_group_retry_reason(retry_view)
    auto_retry_safe = bool(retryable and retry_reason not in NON_AUTORETRY_REASONS)
    error_text = str(retry_view.get("response_error") or "").strip() or None
    return {
        "label": str(group.get("label") or "").strip() or None,
        "status": str(retry_view.get("response_status") or "").strip() or "unknown",
        "role": str(group.get("role") or "probe").strip() or "probe",
        "error": error_text,
        "error_category": str(retry_view.get("response_error_category") or "").strip() or None,
        "error_stage": str(retry_view.get("response_error_stage") or "").strip() or None,
        "transport": str(group.get("transport") or group.get("provider_transport") or "").strip() or None,
        "retryable": retryable,
        "retry_reason": retry_reason,
        "auto_retry_safe": auto_retry_safe,
    }


def summarize_degraded_group_diagnostics(
    group_diagnostics: object,
    *,
    degraded_groups: Optional[Iterable[str]] = None,
    probe_count: Optional[int] = None,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Aggregate per-group retry diagnostics into a summary that captures retryable versus non-retryable breakdown, error-category counts, and auto-retry eligibility.
    - Guarantee: Returns a dict with degraded_count, retryable/non-retryable label lists, error_categories, error_stages, retry_reasons, and degraded_details.
    - Fails: None.
    """
    diagnostics = group_diagnostics if isinstance(group_diagnostics, list) else []
    degraded_labels = {
        str(item).split(":", 1)[0].strip()
        for item in (degraded_groups or [])
        if str(item).strip()
    }
    selected: list[dict[str, Any]] = []
    for group in diagnostics:
        diagnostic = observe_group_retry_diagnostic(group)
        label = str(diagnostic.get("label") or "").strip()
        if degraded_labels:
            if not label or label not in degraded_labels:
                continue
        elif str(diagnostic.get("status") or "").strip() not in DEGRADED_OBSERVE_GROUP_STATUSES:
            continue
        selected.append(diagnostic)

    error_categories: dict[str, int] = {}
    error_stages: dict[str, int] = {}
    retry_reasons: dict[str, int] = {}
    retryable_labels: list[str] = []
    non_retryable_labels: list[str] = []
    auto_retry_safe_labels: list[str] = []
    non_auto_retry_labels: list[str] = []

    for diagnostic in selected:
        label = str(diagnostic.get("label") or "").strip()
        if diagnostic.get("retryable"):
            if label:
                retryable_labels.append(label)
        elif label:
            non_retryable_labels.append(label)
        if diagnostic.get("auto_retry_safe"):
            if label:
                auto_retry_safe_labels.append(label)
        elif label:
            non_auto_retry_labels.append(label)

        category = str(diagnostic.get("error_category") or "").strip()
        if category:
            error_categories[category] = int(error_categories.get(category, 0)) + 1
        stage = str(diagnostic.get("error_stage") or "").strip()
        if stage:
            error_stages[stage] = int(error_stages.get(stage, 0)) + 1
        retry_reason = str(diagnostic.get("retry_reason") or "").strip()
        if retry_reason:
            retry_reasons[retry_reason] = int(retry_reasons.get(retry_reason, 0)) + 1

    degraded_count = len(selected)
    degraded_probe_count = sum(1 for item in selected if str(item.get("role") or "").strip() == "probe")
    successful_probe_count = None
    if probe_count is not None:
        successful_probe_count = max(0, int(probe_count) - degraded_probe_count)

    return {
        "degraded_count": degraded_count,
        "retryable_count": len(retryable_labels),
        "non_retryable_count": len(non_retryable_labels),
        "auto_retry_safe_count": len(auto_retry_safe_labels),
        "all_degraded_retryable": bool(degraded_count and len(retryable_labels) == degraded_count),
        "all_degraded_auto_retry_safe": bool(
            degraded_count and len(auto_retry_safe_labels) == degraded_count
        ),
        "successful_probe_count": successful_probe_count,
        "retryable_labels": retryable_labels,
        "non_retryable_labels": non_retryable_labels,
        "auto_retry_safe_labels": auto_retry_safe_labels,
        "non_auto_retry_labels": non_auto_retry_labels,
        "error_categories": error_categories,
        "error_stages": error_stages,
        "retry_reasons": retry_reasons,
        "degraded_details": selected,
    }


def grouped_runtime_contract_group_status(group: object) -> str:
    """[ACTION]
    - Teleology: Reduce one grouped-observe node into the simplified contract status token used by continuation and history projection logic.
    - Guarantee: Returns one of "success", "failure", "aborted", "skipped", "running", or "pending".
    - Fails: None.
    """
    if not isinstance(group, Mapping):
        return "pending"
    resolved = grouped_runtime_resolved_group_state(group)
    if resolved == "success":
        return "success"
    if resolved in {"error", "quality_error", "failure"}:
        return "failure"
    if resolved == "aborted":
        return "aborted"
    if resolved in {"skipped", "skipped_no_dump", "skipped_missing_dump"}:
        return "skipped"
    if resolved == "running":
        return "running"
    return "pending"


def grouped_runtime_retryable_failure_labels(runtime: Mapping[str, Any]) -> list[str]:
    """[ACTION]
    - Teleology: Derive the deduplicated list of grouped-observe labels whose failures are retryable according to the module's retryability policy.
    - Guarantee: Returns a stable-order list of unique retryable group labels; returns `[]` when no retryable groups exist.
    - Fails: None.
    """
    groups = runtime.get("groups")
    if not isinstance(groups, list):
        return []
    labels: list[str] = []
    for group in groups:
        if not grouped_runtime_group_has_retryable_failure(group):
            continue
        label = str(group.get("label") or "").strip() if isinstance(group, Mapping) else ""
        if label and label not in labels:
            labels.append(label)
    return labels


def _pid_is_running(pid: object) -> bool:
    try:
        token = int(str(pid).strip())
    except (TypeError, ValueError):
        return False
    if token <= 0:
        return False
    try:
        os.kill(token, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        token = str(item or "").strip()
        if token and token not in output:
            output.append(token)
    return output


def _load_repo_json(repo_root: Path, rel_path: str | None) -> dict[str, Any]:
    rel = str(rel_path or "").strip()
    if not rel:
        return {}
    path = (repo_root / rel).resolve()
    try:
        path.relative_to(repo_root.resolve())
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _group_dependencies_met(depends_on: list[str], states_by_label: Mapping[str, str]) -> bool:
    return all(states_by_label.get(dep) == "success" for dep in depends_on)


def _grouped_runtime_contract_groups(runtime: Mapping[str, Any]) -> tuple[list[dict[str, Any]], int]:
    raw_groups = runtime.get("groups")
    if not isinstance(raw_groups, list):
        return [], 0
    states_by_label: dict[str, str] = {}
    normalized_groups: list[Mapping[str, Any]] = []
    for group in raw_groups:
        if not isinstance(group, Mapping):
            continue
        normalized_groups.append(group)
        label = str(group.get("label") or "").strip()
        if label:
            states_by_label[label] = grouped_runtime_contract_group_status(group)

    groups: list[dict[str, Any]] = []
    error_count = 0
    for group in normalized_groups:
        label = str(group.get("label") or "").strip()
        depends_on = [
            str(item).strip()
            for item in group.get("depends_on", [])
            if str(item).strip()
        ] if isinstance(group.get("depends_on"), list) else []
        status = grouped_runtime_contract_group_status(group)
        retryable = grouped_runtime_group_has_retryable_failure(group)
        retry_reason = grouped_runtime_group_retry_reason(group)
        dependencies_met = _group_dependencies_met(depends_on, states_by_label)
        if not dependencies_met and status in {"pending", "skipped"}:
            retry_reason = retry_reason or "dependencies_unmet"
        elif status == "failure":
            retry_reason = retry_reason or "non_retryable_failure"
        if status == "failure":
            error_count += 1
        groups.append(
            {
                "label": label,
                "role": str(group.get("role") or "probe").strip() or "probe",
                "depends_on": depends_on,
                "status": status,
                "error": str(group.get("response_error") or group.get("error") or "").strip() or None,
                "response_path": str(group.get("response_file") or group.get("response_path") or "").strip() or None,
                "wave_index": int(group.get("wave_index", 0) or 0),
                "retryable": retryable,
                "retry_reason": retry_reason,
                "dependencies_met": dependencies_met,
            }
        )
    return groups, error_count


def grouped_runtime_progress_payload(runtime: Mapping[str, Any], groups: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Project grouped-observe progress into one compact operator packet for status UIs and CLI readback.
    - Mechanism: Combine manifest totals with normalized group statuses, derive active/pending labels, compute percent complete, and emit a short summary.
    - Guarantee: Returns stable progress fields even when manifests are partial or group totals are missing.
    - Fails: None.
    """
    def _count(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    total_groups = _count(runtime.get("total_groups")) or len(groups)
    completed_groups = _count(runtime.get("completed_groups"))
    terminal_statuses = {"success", "failure", "skipped", "aborted"}
    derived_completed = sum(1 for group in groups if str(group.get("status") or "") in terminal_statuses)
    if completed_groups <= 0 or completed_groups > total_groups:
        completed_groups = derived_completed
    completed_groups = min(completed_groups, total_groups) if total_groups else 0
    remaining_groups = max(total_groups - completed_groups, 0)
    percent_complete = int(round((completed_groups / total_groups) * 100)) if total_groups else 0

    status_counts: dict[str, int] = {}
    active_group_labels: list[str] = []
    pending_group_labels: list[str] = []
    for group in groups:
        status = str(group.get("status") or "pending").strip() or "pending"
        status_counts[status] = status_counts.get(status, 0) + 1
        label = str(group.get("label") or "").strip()
        if not label:
            continue
        if status == "running":
            active_group_labels.append(label)
        if status in {"pending", "running"}:
            pending_group_labels.append(label)

    summary = f"{completed_groups}/{total_groups} groups complete" if total_groups else "idle"
    if active_group_labels:
        summary = f"{summary}; active: {', '.join(active_group_labels[:3])}"
    elif pending_group_labels:
        summary = f"{summary}; pending: {', '.join(pending_group_labels[:3])}"

    return {
        "total_groups": total_groups,
        "completed_groups": completed_groups,
        "remaining_groups": remaining_groups,
        "percent_complete": percent_complete,
        "active_group_labels": active_group_labels,
        "pending_group_labels": pending_group_labels,
        "status_counts": status_counts,
        "summary": summary,
        "last_update_at": str(runtime.get("updated_at") or "").strip() or None,
    }


def _coerce_runtime_resume_bundle(
    *,
    repo_root: Path,
    runtime: Mapping[str, Any],
    history_payload: Mapping[str, Any],
    status_manifest: Optional[str],
    history_entry: Optional[str],
) -> dict[str, Any]:
    continuation = history_payload.get("continuation") if isinstance(history_payload.get("continuation"), dict) else {}
    resume_surface = build_observe_resume_surface(repo_root, history_payload) if history_payload else {}
    read_paths = _string_list(resume_surface.get("read_paths"))
    preferred_artifact = str(resume_surface.get("preferred_artifact") or "").strip() or None
    readback_state = {
        "primary_artifact": preferred_artifact,
        "artifact_queue": read_paths,
        "response_count": len(
            [
                group for group in runtime.get("groups", [])
                if isinstance(group, dict) and str(group.get("response_file") or "").strip()
            ]
        ),
        "selection_basis": str(resume_surface.get("mode") or "").strip() or None,
    }
    promotion = history_payload.get("promotion") if isinstance(history_payload.get("promotion"), dict) else {}
    result_note = history_payload.get("result_note") if isinstance(history_payload.get("result_note"), dict) else {}
    synthesis = history_payload.get("synthesis") if isinstance(history_payload.get("synthesis"), dict) else {}
    digest = history_payload.get("digest") if isinstance(history_payload.get("digest"), dict) else {}
    promoted_surface = {
        "result_note_path": str(result_note.get("path") or "").strip() or None,
        "synthesis_path": str(synthesis.get("path") or "").strip() or None,
        "promotion_target": str(promotion.get("target_path") or "").strip() or None,
        "promotion_status": str(promotion.get("status") or "").strip() or None,
        "digest_path": str(digest.get("path") or "").strip() or None,
    }
    launch_receipt = runtime.get("launch_receipt") if isinstance(runtime.get("launch_receipt"), dict) else {}
    session_continuity = history_payload.get("session_continuity") if isinstance(history_payload.get("session_continuity"), dict) else {}
    lineage = {
        "observe_id": str(runtime.get("observe_id") or "").strip() or None,
        "session_slug": str(runtime.get("session_slug") or "").strip() or None,
        "status_manifest": status_manifest,
        "history_entry": history_entry,
        "digest_artifact": promoted_surface["digest_path"],
        "result_note_path": promoted_surface["result_note_path"],
        "synthesis_path": promoted_surface["synthesis_path"],
        "launch_receipt_id": str(launch_receipt.get("id") or "").strip() or None,
        "campaign_id": str(session_continuity.get("campaign_id") or "").strip() or None,
        "root_observe_id": str(session_continuity.get("root_observe_id") or "").strip() or None,
        "parent_observe_id": str(session_continuity.get("parent_observe_id") or "").strip() or None,
        "round_id": str(session_continuity.get("round_id") or "").strip() or None,
        "round_index": session_continuity.get("round_index"),
        "carry_forward_posture": str(session_continuity.get("carry_forward_posture") or "").strip() or None,
    }
    return {
        "continuation": dict(continuation),
        "resume_surface": dict(resume_surface),
        "readback_state": {k: v for k, v in readback_state.items() if v not in (None, [], "")},
        "promoted_surface": {k: v for k, v in promoted_surface.items() if v not in (None, "", [])},
        "lineage": {k: v for k, v in lineage.items() if v not in (None, "", [])},
    }


def grouped_runtime_continue_contract(
    runtime: Mapping[str, Any],
    *,
    pid_is_running: bool,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Decide whether a grouped runtime may be continued and explain why.
    - Mechanism: Normalize the runtime state, inspect pending and retryable group labels, and map the current state plus PID liveness into can_continue, continue_mode, and continue_reason.
    - Guarantee: Returns a dict with state, can_continue, continue_mode, continue_reason, pending_group_labels, and retryable_group_labels.
    - Fails: None.
    - When-needed: Open when CLI or control-room code needs the resumability contract for a grouped observe runtime instead of the raw manifest fields.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_status_payload; tools/meta/apply/run_observe_plan.py
    """
    state = normalize_observe_runtime_state(runtime.get("kind"), runtime.get("state"))
    pending_group_labels = grouped_runtime_pending_group_labels(runtime)
    retryable_group_labels = grouped_runtime_retryable_failure_labels(runtime)

    can_continue = False
    continue_mode = "none"
    continue_reason = ""

    if state == "awaiting_review":
        can_continue = True
        continue_mode = "review"
        continue_reason = "review_gate_open"
    elif state in {"dispatching", "error", "completed", "aborted"}:
        if pid_is_running:
            continue_reason = "runtime_still_active"
        elif pending_group_labels:
            can_continue = True
            continue_mode = "resume_pending"
            continue_reason = "pending_groups_present"
        elif retryable_group_labels:
            can_continue = True
            continue_mode = "retry_failed"
            continue_reason = "retryable_failures_present"
        else:
            continue_reason = "no_pending_or_retryable_groups"
    else:
        continue_reason = "state_not_resumable"

    return {
        "state": state,
        "can_continue": can_continue,
        "continue_mode": continue_mode,
        "continue_reason": continue_reason,
        "pending_group_labels": pending_group_labels,
        "retryable_group_labels": retryable_group_labels,
    }


def _parse_runtime_timestamp(value: object) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _grouped_runtime_launch_sort_key(path: Path) -> tuple[float, str, float]:
    payload = read_json(path)
    started_at = _parse_runtime_timestamp(payload.get("started_at"))
    observe_id = str(payload.get("observe_id") or path.stem).strip()
    mtime = path.stat().st_mtime
    return (
        started_at if started_at is not None else float("-inf"),
        observe_id,
        mtime,
    )


def resolve_grouped_runtime_manifest_path(repo_root: Path, history_dir: Path, ref: Optional[str] = None) -> Optional[Path]:
    """[ACTION]
    - Teleology: Resolve the filesystem path of a grouped runtime manifest given an observe-id, `latest`/`current` alias, or explicit path reference.
    - Guarantee: Returns the resolved Path when a matching manifest is found; returns `None` when no manifest matches the reference.
    - Fails: None.
    """
    token = str(ref or "latest").strip() or "latest"
    runtime_dir = grouped_runtime_dir(history_dir)
    current_path = grouped_runtime_current_path(history_dir)
    if token == "current":
        if current_path.exists():
            return current_path
        return None
    if token == "latest":
        if current_path.exists():
            return current_path
        if not runtime_dir.exists():
            return None
        manifests = sorted(
            [path for path in runtime_dir.glob("OBS_*.json") if path.is_file()],
            key=_grouped_runtime_launch_sort_key,
            reverse=True,
        )
        return manifests[0] if manifests else None

    explicit = Path(token)
    if explicit.is_absolute() and explicit.exists():
        return explicit
    if not explicit.is_absolute():
        candidate = (repo_root / explicit).resolve()
        if candidate.exists():
            return candidate

    observe_id = token.replace(".json", "")
    candidate = grouped_runtime_path(history_dir, observe_id)
    if candidate.exists():
        return candidate
    return None


def load_grouped_runtime_manifest(repo_root: Path, history_dir: Path, ref: Optional[str] = None) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Load a grouped runtime manifest from disk by reference, injecting the relative manifest path for downstream consumers.
    - Guarantee: Returns the manifest dict with `_manifest_path` populated when found; returns `{}` when no manifest matches the reference or the file is unreadable.
    - Fails: None.
    """
    path = resolve_grouped_runtime_manifest_path(repo_root, history_dir, ref)
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    if payload:
        payload["_manifest_path"] = str(path.relative_to(repo_root))
    return payload


def grouped_runtime_status_payload(repo_root: Path, history_dir: Path, ref: Optional[str] = None) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Project one grouped runtime manifest into the compact status surface consumed by kernel and operator tooling.
    - Mechanism: Load the runtime manifest, derive continuation and retry contracts, merge resume or readback or promotion bundles, and normalize the group list into one status dict.
    - Guarantee: Returns the grouped runtime status payload or the idle payload when no manifest is available.
    - Fails: None.
    - When-needed: Open when a caller needs one normalized observe-runtime status surface instead of stitching together manifest, history entry, and continuation artifacts manually.
    - Escalates-to: system/lib/observe_surfaces.py::build_observe_resume_surface; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    token = str(ref or "latest").strip() or "latest"
    runtime = load_grouped_runtime_manifest(repo_root, history_dir, token)
    if not runtime:
        payload = grouped_runtime_idle_payload()
        payload["requested_ref"] = token
        payload["selection_scope"] = "no_current_runtime" if token == "current" else "no_runtime_manifest"
        payload["current_runtime_selected"] = False
        return payload
    artifacts = runtime.get("artifacts") if isinstance(runtime.get("artifacts"), dict) else {}
    status_manifest = str(runtime.get("_manifest_path") or runtime.get("runtime_manifest") or "").strip() or None
    current_manifest = grouped_runtime_current_path(history_dir)
    selected_current = bool(
        status_manifest
        and (repo_root / status_manifest).resolve(strict=False)
        == current_manifest.resolve(strict=False)
    )
    selection_scope = (
        "current_runtime"
        if selected_current
        else "latest_archived_runtime"
        if token in {"latest", "current"}
        else "explicit_runtime"
    )
    history_entry = str(runtime.get("history_entry") or artifacts.get("history_entry") or "").strip() or None
    history_payload = _load_repo_json(repo_root, history_entry)
    continue_contract = grouped_runtime_continue_contract(
        runtime,
        pid_is_running=_pid_is_running(runtime.get("pid")),
    )
    launch_receipt = runtime.get("launch_receipt") if isinstance(runtime.get("launch_receipt"), dict) else {}
    launch_dispatch = (
        str(runtime.get("launch_dispatch") or "").strip()
        or str(history_payload.get("launch_dispatch") or "").strip()
        or None
    )
    surface_bundle = _coerce_runtime_resume_bundle(
        repo_root=repo_root,
        runtime=runtime,
        history_payload=history_payload,
        status_manifest=status_manifest,
        history_entry=history_entry,
    )
    groups, error_count = _grouped_runtime_contract_groups(runtime)
    progress = grouped_runtime_progress_payload(runtime, groups)
    lineage = surface_bundle.get("lineage") if isinstance(surface_bundle.get("lineage"), dict) else {}
    round_id = (
        str(runtime.get("round_id") or "").strip()
        or str(lineage.get("round_id") or "").strip()
        or None
    )
    return {
        "kind": runtime.get("kind"),
        "observe_id": runtime.get("observe_id"),
        "session_slug": runtime.get("session_slug"),
        "state": normalize_observe_runtime_state(runtime.get("kind"), runtime.get("state")),
        "launch_profile": runtime.get("launch_profile"),
        "requested_workers": runtime.get("requested_workers"),
        "effective_workers": runtime.get("effective_workers"),
        "wave_index": runtime.get("wave_index"),
        "wave_total": runtime.get("wave_total"),
        "total_groups": runtime.get("total_groups"),
        "completed_groups": runtime.get("completed_groups"),
        "progress": progress,
        "provider": runtime.get("provider"),
        "provider_transport": runtime.get("provider_transport"),
        "latest_stable_artifact": artifacts.get("latest_stable_artifact"),
        "status_authority": "grouped_runtime",
        "requested_ref": token,
        "selection_scope": selection_scope,
        "current_runtime_selected": selected_current,
        "status_manifest": status_manifest,
        "manifest": status_manifest,
        "history_entry": history_entry,
        "pid": runtime.get("pid"),
        "started_at": runtime.get("started_at"),
        "updated_at": runtime.get("updated_at"),
        "cancel_requested_at": runtime.get("cancel_requested_at"),
        "error": runtime.get("error"),
        "round_id": round_id,
        "error_count": error_count,
        "can_continue": bool(continue_contract.get("can_continue")),
        "continue_mode": continue_contract.get("continue_mode"),
        "continue_reason": continue_contract.get("continue_reason"),
        "pending_group_labels": _string_list(continue_contract.get("pending_group_labels")),
        "retryable_group_labels": _string_list(continue_contract.get("retryable_group_labels")),
        "launch_receipt": dict(launch_receipt),
        "launch_dispatch": launch_dispatch,
        "continuation": dict(surface_bundle.get("continuation") or {}),
        "readback_state": dict(surface_bundle.get("readback_state") or {}),
        "promoted_surface": dict(surface_bundle.get("promoted_surface") or {}),
        "resume_surface": dict(surface_bundle.get("resume_surface") or {}),
        "lineage": dict(lineage),
        "artifacts": artifacts,
        "groups": groups,
    }


def promote_grouped_observe_state(
    *,
    repo_root: Path,
    history_dir: Path,
    observe_id: str,
    entry_path: Path,
    entry_payload: Mapping[str, Any],
    runtime_payload: Mapping[str, Any],
    result_path: Optional[Path] = None,
    result_pointer: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Commit grouped runtime progress into the durable observe history surfaces once a state transition becomes stable.
    - Mechanism: Rewrite the history entry, generate and attach the grouped observe digest, update runtime artifact pointers, optionally refresh the result pointer, and clear `current.json` on terminal states.
    - Guarantee: Returns updated entry_payload, digest_payload, and runtime_payload dicts reflecting the promoted state.
    - Fails: Propagates write or digest-generation errors from the underlying file and digest helpers.
    - When-needed: Open when grouped observe runtime state must be promoted into history and digest artifacts after review or completion.
    - Escalates-to: system/lib/observe_surfaces.py::build_grouped_observe_continuation; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    from system.lib.observe_memory import write_grouped_observe_digest

    entry_dict = dict(entry_payload)
    write_json(entry_path, entry_dict)
    digest_payload = write_grouped_observe_digest(repo_root, entry_dict, entry_path)
    entry_dict["digest"] = {
        "path": str(digest_payload.get("digest_path") or ""),
        "generated_at": str(digest_payload.get("generated_at") or ""),
    }
    write_json(entry_path, entry_dict)
    runtime_dict = dict(runtime_payload)
    runtime_artifacts = dict(runtime_dict.get("artifacts") or {})
    runtime_artifacts["digest"] = entry_dict["digest"]["path"]
    runtime_dict["artifacts"] = runtime_artifacts
    write_grouped_runtime_manifest(history_dir, runtime_dict)

    runtime_state = str(runtime_dict.get("state") or "").strip().lower()
    if result_path is not None and result_pointer is not None and runtime_state in {"awaiting_review", "completed"}:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_dict = dict(result_pointer)
        result_dict["runtime_manifest"] = runtime_dict.get("runtime_manifest")
        write_json(result_path, result_dict)

    if runtime_state in GROUPED_RUNTIME_TERMINAL_STATES:
        clear_grouped_runtime_current(history_dir, observe_id)

    return {
        "entry_payload": entry_dict,
        "digest_payload": digest_payload,
        "runtime_payload": runtime_dict,
    }


def request_grouped_runtime_cancel(
    *,
    repo_root: Path,
    history_dir: Path,
    ref: Optional[str] = None,
    force: bool = False,
    signal_group: Optional[Any] = None,
    wait_timeout_s: float = 15.0,
    poll_interval_s: float = 0.5,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Request cancellation for one grouped runtime and, if needed, force it into an aborted state.
    - Mechanism: Stamp cancel_requested_at across the manifest set, wait for a terminal state, and optionally send a termination signal when the runtime remains active past the timeout.
    - Guarantee: Returns the latest runtime dict after the cancel attempt, or `{}` when no runtime manifest matched the reference.
    - Fails: None directly; signal errors are captured into the returned runtime payload.
    - When-needed: Open when operator or CLI code needs to stop a grouped observe runtime and persist the cancellation outcome.
    - Escalates-to: system/lib/observe_runtime.py::grouped_runtime_status_payload; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    manifest_path = resolve_grouped_runtime_manifest_path(repo_root, history_dir, ref)
    runtime = load_grouped_runtime_manifest(repo_root, history_dir, ref)
    if manifest_path is None or not runtime:
        return {}

    now = now_iso()
    runtime["cancel_requested_at"] = now
    runtime["updated_at"] = now
    observe_id = str(runtime.get("observe_id") or "").strip()
    target_paths = [manifest_path]
    if observe_id:
        target_paths.append(grouped_runtime_path(history_dir, observe_id))
    current_runtime = load_grouped_runtime_manifest(repo_root, history_dir, "current")
    current_runtime_path = grouped_runtime_current_path(history_dir)
    if observe_id and str(current_runtime.get("observe_id") or "").strip() == observe_id:
        target_paths.append(current_runtime_path)
    for path in {path for path in target_paths if path is not None}:
        write_json(path, {k: v for k, v in runtime.items() if k != "_manifest_path"})

    deadline = time.time() + max(0.0, wait_timeout_s)
    latest_runtime = runtime
    terminal_states = GROUPED_RUNTIME_TERMINAL_STATES | {"completed"}
    while time.time() < deadline:
        latest_runtime = load_grouped_runtime_manifest(repo_root, history_dir, observe_id or str(manifest_path))
        if str(latest_runtime.get("state") or "").strip().lower() in terminal_states:
            break
        time.sleep(max(0.05, poll_interval_s))

    if str(latest_runtime.get("state") or "").strip().lower() not in terminal_states and force:
        pid = latest_runtime.get("pid")
        try:
            if pid:
                if signal_group is None:
                    import os
                    import signal

                    os.killpg(int(pid), signal.SIGTERM)
                else:
                    signal_group(int(pid))
                latest_runtime["state"] = "aborted"
                latest_runtime["updated_at"] = now_iso()
                for path in {path for path in target_paths if path is not None}:
                    write_json(path, {k: v for k, v in latest_runtime.items() if k != "_manifest_path"})
        except Exception as exc:
            latest_runtime["error"] = str(exc)

    if observe_id and str(latest_runtime.get("state") or "").strip().lower() in terminal_states:
        clear_grouped_runtime_current(history_dir, observe_id)

    return latest_runtime


def bridge_state_path(history_dir: Path) -> Path:
    """[ACTION]
    - Teleology: Resolve the canonical path to `bridge_state.json` under the observe history directory.
    - Guarantee: Returns the absolute Path for `<history_dir>/bridge_state.json`.
    - Fails: None.
    """
    return history_dir / "bridge_state.json"


def latest_bridge_transport(history_dir: Path, provider: Optional[str]) -> Optional[str]:
    """[ACTION]
    - Teleology: Look up the last successfully recorded submission transport for a bridge provider from the persisted bridge state.
    - Guarantee: Returns the transport string when one is present in bridge_state.json; returns `None` when the state is missing, malformed, or no transport has been recorded.
    - Fails: None.
    """
    payload = read_json(bridge_state_path(history_dir))
    providers = payload.get("providers")
    if not isinstance(providers, dict):
        return None
    if provider:
        state = providers.get(provider, {})
        if isinstance(state, dict):
            details = state.get("last_success_details")
            if isinstance(details, dict):
                transport = str(details.get("submission_transport") or "").strip()
                return transport or None
    for state in providers.values():
        if not isinstance(state, dict):
            continue
        details = state.get("last_success_details")
        if not isinstance(details, dict):
            continue
        transport = str(details.get("submission_transport") or "").strip()
        if transport:
            return transport
    return None
