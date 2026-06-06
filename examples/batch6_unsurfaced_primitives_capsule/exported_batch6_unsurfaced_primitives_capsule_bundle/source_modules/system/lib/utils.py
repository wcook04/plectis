"""
[PURPOSE]
- Teleology: Shared, stateless utilities used across core/server layers to prevent duplicated helper logic.

[INTERFACE]
- Exports: resolve_value, deep_merge, resolve_root, to_jsonable, relative_time_label

[FLOW]
- Normalize config values (resolve_value) and merge layered dicts (deep_merge).
- Discover repository root via sentinel file (resolve_root).
- Normalize runtime objects into JSON-safe primitives (to_jsonable).
- Emit compact relative time labels for UI/logging (relative_time_label).

[DEPENDENCIES]
- Filesystem contract: repository root contains master_config.json (resolve_root).
- standard_lib.time: wall-clock reads when now is not provided (relative_time_label).

[CONSTRAINTS]
- Writes: None (all helpers are non-mutating); resolve_root performs filesystem reads; relative_time_label may read system clock.
- Orders: deep_merge precedence is override-wins; to_jsonable sorts set/frozenset with key=str for determinism.
- Fails: None (helpers degrade to safe defaults/strings where possible).
- When-needed: Open when shared runtime helpers such as repo-root resolution, JSON normalization, or canonical runs-dir guarding are needed instead of re-implementing them ad hoc.
- Escalates-to: system/lib/types.py; system/lib/workstream_scaffold.py; system/lib/codex_paths.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union, List

# 1. RESOLVE VALUE (Replaces _rv in engine.py, session.py, main.py)
def resolve_value(val: Any, default: Any = None) -> Any:
    """
    [ACTION]
    - Teleology: Normalize config values that may be wrapped as {"value": X, "desc": Y}.
    - Mechanism: If val is a dict containing "value", return val["value"]; otherwise return val; if val is None, return default.
    - Reads: val, default.
    - Writes: None.
    - Fails: None.
    - Guarantee: Returns a usable value for downstream config consumption; returns default when val is None.
    - Non-goal: Does not validate config schema beyond the presence of "value".
    """
    if isinstance(val, dict) and "value" in val:
        return val["value"]
    return val if val is not None else default

# 2. DEEP MERGE (Replaces _deep_merge in loader.py, main.py)
def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Merge layered configuration dicts without mutating inputs.
    - Mechanism: Copy base; for each key in override: recurse when both values are dicts, otherwise override.
    - Reads: base, override.
    - Writes: None (returns a new dict).
    - Orders: override wins on key collisions; nested dicts are merged recursively.
    - Fails: None.
    - Guarantee: base and override are not mutated; return contains base keys with override applied.
    - Non-goal: Does not perform type coercion or schema validation.
    """
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged

# 3. ROOT RESOLUTION (Replaces _resolve_root in builder.py, _find_root in miner.py)
def resolve_root(hint: Optional[Union[str, Path]] = None, max_hops: int = 24) -> Path:
    """
    [ACTION]
    - Teleology: Locate the repository root required for resolving relative paths and configs.
    - Mechanism: If hint is an existing directory, return it; otherwise walk upward from CWD up to max_hops looking for master_config.json; fall back to CWD.
    - Reads: filesystem (Path.cwd(), Path.exists()).
    - Writes: None.
    - Fails: None.
    - Guarantee: Returns an absolute Path; returns the nearest ancestor containing master_config.json when present.
    - Non-goal: Does not assert git root or validate the contents of master_config.json.
    - When-needed: Open when a kernel or runtime surface needs the repo root sentinel resolution contract instead of assuming CWD is already correct.
    - Escalates-to: system/lib/workstream_scaffold.py::execute_workstream_scaffold; system/lib/codex_paths.py
    """
    if hint:
        p = Path(hint).resolve()
        if p.exists() and p.is_dir():
            return p
    
    current = Path.cwd().resolve()
    for _ in range(max_hops):
        if (current / "master_config.json").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path.cwd().resolve()

# 4. JSON NORMALIZATION (Replaces _to_jsonable in builder.py)
def to_jsonable(obj: Any) -> Any:
    """
    [ACTION]
    - Teleology: Convert runtime objects into JSON-safe primitives for logging/artifacts/config snapshots.
    - Mechanism: Type-dispatch conversion: primitives pass through; Path->str; Enum->value; list/tuple->list; set/frozenset->sorted list; dict->str-keyed dict; dataclass->asdict; fallback->str(obj).
    - Reads: obj.
    - Writes: None.
    - Orders: set/frozenset are sorted with key=str; dict keys are coerced to str.
    - Fails: None.
    - Guarantee: Returns only JSON-serializable structures (primitives, lists, dicts).
    - Non-goal: Does not preserve object identity or rich types.
    - When-needed: Open when runtime objects or dataclasses need to be normalized into artifact-safe JSON primitives before persistence or logging.
    - Escalates-to: system/lib/types.py; system/lib/workstream_scaffold.py
    - Navigation-group: kernel_lib
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted([to_jsonable(x) for x in obj], key=str)
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict
        return to_jsonable(asdict(obj))
    return str(obj)

# 5. TIME LABEL (Replaces inline logic in translator.py)
def relative_time_label(timestamp: float, now: Optional[float] = None) -> str:
    """
    [ACTION]
    - Teleology: Produce compact human-readable elapsed-time labels for UI/logs.
    - Mechanism: Compute delta = now - timestamp (now defaults to time.time()) and format into buckets (Future / Just now / Xm / Xh / Xd).
    - Reads: timestamp; system clock when now is None.
    - Writes: None.
    - Orders: Threshold buckets are fixed: <0, <60, <3600, <86400, else days.
    - Schema: Returns one of: "Future", "Just now", "{m}m ago", "{h}h ago", "{d}d ago".
    - Fails: None.
    - Guarantee: Always returns a string label.
    - Non-goal: Does not format absolute timestamps or handle locale/timezone rendering.
    """
    if now is None:
        now = time.time()
    delta = now - timestamp
    if delta < 0: return "Future"
    if delta < 60: return "Just now"
    if delta < 3600: return f"{int(delta // 60)}m ago"
    if delta < 86400: return f"{int(delta // 3600)}h ago"
    
    days = int(delta // 86400)
    hours = int((delta % 86400) // 3600)
    if hours > 0:
        return f"{days}d {hours}h ago"
    return f"{days}d ago"

# 6. RUNS DIR RESOLUTION (Canonical single source of truth)
def resolve_runs_dir(root_dir: Union[str, Path], runs_dir_val: Any = None) -> Path:
    """
    [ACTION]
    - Teleology: Resolve the canonical runs directory with a root-boundary escape guard.
    - Mechanism:
        1. Unwrap runs_dir_val via resolve_value if it is a dict-wrapped config object.
        2. If val is empty/None, return the deterministic fallback `root_dir/state/runs`.
        3. Resolve the candidate path relative to root_dir.
        4. Guard: if the resolved path escapes root_dir (path traversal), return fallback.
    - Reads: root_dir (filesystem), runs_dir_val (config value; may be a {value, desc} dict).
    - Writes: None.
    - Fails: None (always returns a valid Path; never raises).
    - Guarantee: Returned path is always at or under root_dir; root_dir/state/runs on invalid/escaping input.
    - Non-goal: Does not create the directory; callers must mkdir as required.
    - When-needed: Open when runtime config needs the canonical runs directory with root-boundary enforcement rather than trusting a raw config path.
    - Escalates-to: system/lib/workstream_scaffold.py::execute_workstream_scaffold; system/lib/codex_paths.py
    """
    root = Path(root_dir).resolve()
    fallback = root / "state" / "runs"
    val = resolve_value(runs_dir_val) if runs_dir_val is not None else None
    if not val:
        return fallback
    candidate = (root / str(val)).resolve()
    try:
        candidate.relative_to(root)  # raises ValueError if escaping root boundary
    except ValueError:
        return fallback
    return candidate
