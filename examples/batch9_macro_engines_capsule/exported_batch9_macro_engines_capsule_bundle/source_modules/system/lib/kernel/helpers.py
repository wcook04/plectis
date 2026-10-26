"""
[PURPOSE]
- Teleology: Shared utility functions used across multiple kernel command groups.
- Mechanism: Thin wrappers over kernel state and navigation for operations that
  >5 command functions depend on (safe JSON loading, run ID resolution, runs dir).

[INTERFACE]
- safe_load_json_with_error additionally returns loader error evidence alongside the normalized payload.

- Exports: safe_load_json, read_runs_dir_value, resolve_run_id, parse_iso_datetime,
           load_builder_config, truncate_text

[FLOW]
- Command modules import these helpers instead of defining their own copies.

[DEPENDENCIES]
- system.lib.kernel.state: REPO_ROOT, MASTER_CONFIG
- system.lib.kernel_navigation: KernelNavigation
- system.lib.utils: resolve_runs_dir

[CONSTRAINTS]
- Determinism: All functions are filesystem-only reads (no mutations).
- Non-goal: This module does not contain domain-specific helpers (bridge, observe, phase).
- When-needed: Open when multiple kernel command groups reuse the same safe JSON, run-id, or builder-config helper and you need the shared helper surface rather than the callers.
- Escalates-to: system/lib/kernel_navigation.py; system/lib/json_payloads.py; master_config.json
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from system.lib import strict_json
from system.lib.kernel import state


def safe_load_json_with_error(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """
    [ACTION]
    - Teleology: Provide a minimal, non-raising JSON object loader that preserves parse failure detail for callers that need to explain malformed authority artifacts.
    - Mechanism: Read the file through the strict JSON parser, reject duplicate object keys before mapping collapse, and return only mapping-shaped payloads.
    - Reads: The filesystem path passed in.
    - Guarantee: Returns `(dict, None)` for valid JSON objects and `(None, error)` for decode failures, read failures, duplicate keys, or non-object payloads.
    - Fails: None.
    - When-needed: Open when a kernel surface needs best-effort JSON loading but should still preserve duplicate-key or syntax diagnostics for error reporting.
    - Escalates-to: system/lib/strict_json.py; system/lib/json_payloads.py; system/lib/contracts.py
    """
    try:
        payload = strict_json.read_json_strict(path)
    except Exception as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, f"{path}: JSON root must be an object"
    return payload, None


def safe_load_json(path: Path) -> dict | None:
    """
    [ACTION]
    - Teleology: Provide a minimal, non-raising JSON object loader for kernel helpers and commands that treat malformed files as absence rather than a fatal condition.
    - Mechanism: Delegate to `safe_load_json_with_error` and discard parse details.
    - Reads: The filesystem path passed in.
    - Guarantee: Returns a dict for valid JSON objects and None for decode failures, read failures, duplicate object keys, or non-object payloads.
    - Fails: None.
    - When-needed: Open when a kernel surface needs the exact best-effort JSON loading semantics before deciding whether a missing or malformed artifact should be treated as empty state.
    - Escalates-to: system/lib/strict_json.py; system/lib/json_payloads.py; system/lib/contracts.py
    """
    payload, _error = safe_load_json_with_error(path)
    if payload is None:
        return None
    return dict(payload)


def read_runs_dir_value() -> str | None:
    """[ACTION] Best-effort read of configured runs_dir from master_config."""
    try:
        cfg = json.loads(state.MASTER_CONFIG.read_text(encoding="utf-8"))
        return (cfg.get("paths") or {}).get("runs_dir")
    except Exception:
        return None


def resolve_run_id(run_id: str) -> str:
    """
    [ACTION]
    - Teleology: Normalize fuzzy run identifiers through the canonical kernel navigation resolver so command groups share one run-discovery path.
    - Mechanism: Instantiate KernelNavigation at the repo root and delegate to its resolve_run_id() method.
    - Reads: state.REPO_ROOT and system.lib.kernel_navigation.KernelNavigation.
    - Guarantee: Returns the resolved run id chosen by KernelNavigation.
    - Fails: Raises ValueError when the run token cannot be resolved.
    - When-needed: Open when a command accepts partial run ids and you need the authoritative resolver instead of duplicating match logic locally.
    - Escalates-to: system/lib/kernel_navigation.py
    - Navigation-group: kernel_lib
    """
    from system.lib.kernel_navigation import KernelNavigation
    navigator = KernelNavigation(state.REPO_ROOT)
    return navigator.resolve_run_id(run_id)


def parse_iso_datetime(value: object) -> datetime | None:
    """[ACTION] Parse an ISO datetime string, returning None on failure."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def load_builder_config() -> dict[str, object]:
    """
    [ACTION]
    - Teleology: Load the builder-specific config slice with the kernel repo root injected as a stable fallback hint.
    - Mechanism: Read master_config.json when present, extract the builder mapping if valid, and set root_hint when the config omits it.
    - Reads: state.MASTER_CONFIG.
    - Guarantee: Returns a dict and always includes root_hint.
    - Fails: None.
    - When-needed: Open when builder-facing kernel code needs the exact fallback semantics for the builder config section instead of the full master config surface.
    - Escalates-to: master_config.json; system/lib/kernel/config.py::load_master_config
    - Navigation-group: kernel_lib
    """
    config: dict[str, object] = {}
    if state.MASTER_CONFIG.exists():
        try:
            payload = json.loads(state.MASTER_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            builder_cfg = payload.get("builder", {})
            if isinstance(builder_cfg, dict):
                config = dict(builder_cfg)
    config.setdefault("root_hint", str(state.REPO_ROOT))
    return config


def truncate_text(text: str, limit: int = 200) -> str:
    """[ACTION] Truncate text to limit chars, appending '...' if shortened."""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."
