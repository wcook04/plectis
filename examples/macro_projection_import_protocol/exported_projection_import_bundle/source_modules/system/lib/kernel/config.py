"""
[PURPOSE]
- Teleology: Master configuration loading, bridge runtime config resolution, and observe budget derivation.
- Mechanism: Reads master_config.json once and derives typed configuration values for bridge, observe,
  and launch profile subsystems. Centralizes config-dependent logic that was previously scattered
  across kernel.py helper functions.

[INTERFACE]
- Exports: load_master_config, config_value, default_bridge_timeout_s, observe_budget_config,
           observe_launch_profile_default, resolve_bridge_runtime_config, runner_python_executable,
           coerce_bridge_workers_arg

[FLOW]
- Command modules call these functions to get resolved configuration before dispatching work.
- Bridge-related commands use resolve_bridge_runtime_config() for provider + timeout + route merge.

[DEPENDENCIES]
- system.lib.kernel.state: REPO_ROOT, DEFAULT_BRIDGE_TIMEOUT_S
- system.lib.bridge_routes: bridge_timeout_seconds, merge_bridge_config_with_route
- system.lib.observe_runtime: observe_runtime_policy, normalize_launch_profile, DEFAULT_LAUNCH_PROFILE,
  DEFAULT_BRIDGE_HARD_PROMPT_CHARS, DEFAULT_BRIDGE_RECOMMENDED_PROMPT_CHARS

[CONSTRAINTS]
- Determinism: config_value is a pure extractor; master_config reads are filesystem-only.
- Non-goal: Does not start or manage bridge processes.
- When-needed: Open when kernel commands need resolved master_config values, observe budgets, or bridge runtime defaults without re-reading kernel.py and the downstream bridge helpers separately.
- Escalates-to: master_config.json; system/lib/bridge_routes.py; system/lib/observe_runtime.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

from system.lib.kernel import state


def config_value(value: Any, default: Any = None) -> Any:
    """[ACTION] Extract value from a config entry that may be wrapped as {\"value\": X}."""
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value if value is not None else default


def load_master_config_at(repo_root: Any) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load master_config.json from an explicit repo root with the canonical tolerant fallback semantics shared by every read loader in the federated config plane.
    - Mechanism: Resolve repo_root / master_config.json, return {} when missing, parse JSON-tolerantly (return {} on any exception), and coerce non-dict payloads to {}.
    - Reads: master_config.json under the supplied repo_root.
    - Guarantee: Returns a dict for any input — valid mapping pass-through, {} for missing/empty/malformed/non-object.
    - Fails: None.
    - When-needed: Open when any subsystem needs to read master_config.json against an explicit repo root (worktree, test tmpdir, alternate checkout) with parity-tested tolerant semantics.
    - Escalates-to: master_config.json; system/lib/kernel/state.py
    - Navigation-group: kernel_lib
    """
    from pathlib import Path
    config_path = Path(repo_root) / "master_config.json"
    if not config_path.exists():
        return {}
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_master_config() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load the kernel's root configuration document in one place so downstream helpers do not each re-implement repo-root config reads.
    - Mechanism: Delegate to load_master_config_at(state.REPO_ROOT); same tolerant semantics, no-arg surface.
    - Reads: master_config.json under the repo root.
    - Guarantee: Returns a dict for valid mapping-shaped config payloads and {} when the file is missing, unreadable, or not a JSON object.
    - Fails: None.
    - When-needed: Open when a caller needs the exact fallback semantics for reading master_config.json before deriving bridge or observe settings.
    - Escalates-to: master_config.json; system/lib/kernel/state.py
    - Navigation-group: kernel_lib
    """
    return load_master_config_at(state.REPO_ROOT)


def default_bridge_timeout_s(*, bridge_route: str | None = None) -> float:
    """
    [ACTION]
    - Teleology: Resolve the effective bridge timeout that command surfaces should use when they have not been given an explicit runtime timeout.
    - Mechanism: Load master config, then delegate the timeout merge to bridge_timeout_seconds() with the kernel default timeout as fallback.
    - Reads: load_master_config(), state.DEFAULT_BRIDGE_TIMEOUT_S, and system.lib.bridge_routes.bridge_timeout_seconds().
    - Guarantee: Returns a float timeout that incorporates route-specific overrides when bridge_route is provided.
    - Fails: None.
    - When-needed: Open when timeout behavior is unclear and you need the authoritative default-plus-route merge path rather than only the raw config file.
    - Escalates-to: system/lib/bridge_routes.py; master_config.json
    """
    from system.lib.bridge_routes import bridge_timeout_seconds
    config = load_master_config()
    return bridge_timeout_seconds(
        config,
        default=state.DEFAULT_BRIDGE_TIMEOUT_S,
        route_name=bridge_route,
    )


def observe_budget_config() -> dict[str, int]:
    """
    [ACTION]
    - Teleology: Produce the observe budgeting limits that keep prompt size, group size, and context payload growth inside configured guardrails.
    - Mechanism: Read the observe section of master_config.json, coerce each budget field through local positive/non-negative integer helpers, and fall back to runtime defaults when values are absent or invalid.
    - Reads: load_master_config(), observe.* keys in master_config.json, observe-runtime default constants, and kernel state defaults for group/context budgets.
    - Guarantee: Returns a dict containing all supported observe budget keys with non-negative or positive integer values as required.
    - Fails: None.
    - When-needed: Open when an observe-plan authoring or validation path needs the exact budget derivation logic instead of only the raw config values.
    - Escalates-to: system/lib/observe_runtime.py; master_config.json
    - Navigation-group: kernel_lib
    """
    from system.lib.observe_runtime import (
        DEFAULT_BRIDGE_HARD_PROMPT_CHARS,
        DEFAULT_BRIDGE_RECOMMENDED_PROMPT_CHARS,
    )
    config = load_master_config()
    observe_cfg = config.get("observe", {})
    if not isinstance(observe_cfg, dict):
        observe_cfg = {}

    def _positive_int(key: str, default: int) -> int:
        raw = config_value(observe_cfg.get(key), default)
        try:
            resolved = int(raw)
        except (TypeError, ValueError):
            return default
        return resolved if resolved > 0 else default

    def _non_negative_int(key: str, default: int) -> int:
        raw = config_value(observe_cfg.get(key), default)
        try:
            resolved = int(raw)
        except (TypeError, ValueError):
            return default
        return resolved if resolved >= 0 else default

    return {
        "max_recommended_prompt_chars": _non_negative_int(
            "max_recommended_prompt_chars", DEFAULT_BRIDGE_RECOMMENDED_PROMPT_CHARS,
        ),
        "max_hard_prompt_chars": _positive_int(
            "max_hard_prompt_chars", DEFAULT_BRIDGE_HARD_PROMPT_CHARS,
        ),
        "max_recommended_group_targets": _non_negative_int(
            "max_recommended_group_targets", state.DEFAULT_OBSERVE_RECOMMENDED_GROUP_TARGETS,
        ),
        "max_recommended_runtime_artifacts": _non_negative_int(
            "max_recommended_runtime_artifacts", state.DEFAULT_OBSERVE_RECOMMENDED_RUNTIME_ARTIFACTS,
        ),
        "max_recommended_context_file_bytes": _non_negative_int(
            "max_recommended_context_file_bytes", state.DEFAULT_OBSERVE_RECOMMENDED_CONTEXT_FILE_BYTES,
        ),
        "max_recommended_context_total_bytes": _non_negative_int(
            "max_recommended_context_total_bytes", state.DEFAULT_OBSERVE_RECOMMENDED_CONTEXT_TOTAL_BYTES,
        ),
    }


# These constants are needed by observe_budget_config but sourced from observe_runtime;
# re-export them so callers don't need a separate import.
DEFAULT_OBSERVE_RECOMMENDED_GROUP_TARGETS = 10
DEFAULT_OBSERVE_RECOMMENDED_RUNTIME_ARTIFACTS = 4
DEFAULT_OBSERVE_RECOMMENDED_CONTEXT_FILE_BYTES = 200_000
DEFAULT_OBSERVE_RECOMMENDED_CONTEXT_TOTAL_BYTES = 600_000


def observe_launch_profile_default() -> str:
    """[ACTION] Resolve default launch profile from runtime policy."""
    from system.lib.observe_runtime import (
        DEFAULT_LAUNCH_PROFILE as OBSERVE_DEFAULT_LAUNCH_PROFILE,
        normalize_launch_profile,
        observe_runtime_policy,
    )
    policy = observe_runtime_policy(state.REPO_ROOT)
    return normalize_launch_profile(
        policy.get("default_launch_profile"), default=OBSERVE_DEFAULT_LAUNCH_PROFILE,
    )


def coerce_bridge_workers_arg(value: Any) -> str:
    """[ACTION] Coerce --bridge-workers to 'auto' or a positive int string."""
    text = str(value or "").strip().lower()
    if not text or text == "auto":
        return "auto"
    parsed = int(text)
    if parsed <= 0:
        raise ValueError("--bridge-workers must be 'auto' or > 0")
    return str(parsed)


def runner_python_executable() -> str:
    """[ACTION] Return the venv python path if present, else sys.executable."""
    runner_python = state.REPO_ROOT / "venv" / "bin" / "python"
    return str(runner_python) if runner_python.exists() else sys.executable


def resolve_bridge_runtime_config(
    *,
    provider: str | None,
    timeout_s: float | None = None,
    bridge_route: str | None = None,
) -> tuple[dict[str, Any], str]:
    """
    [ACTION]
    - Teleology: Materialize the final bridge runtime config that bridge-dispatching command paths should hand to runners and validators.
    - Mechanism: Load master config, merge route overlays through merge_bridge_config_with_route(), apply an explicit timeout when provided, and resolve the effective provider from CLI input or bridge.default_target.
    - Reads: load_master_config(), system.lib.bridge_routes.merge_bridge_config_with_route(), and bridge settings under master_config.json.
    - Guarantee: Returns (config_dict, provider_string) with a normalized non-empty provider and a bridge subsection that reflects explicit timeout overrides.
    - Fails: None.
    - When-needed: Open when a bridge launch path needs the exact precedence order between CLI provider, bridge-route overlays, timeout overrides, and bridge.default_target.
    - Escalates-to: system/lib/bridge_routes.py; master_config.json
    - Navigation-group: kernel_lib
    """
    from system.lib.bridge_routes import merge_bridge_config_with_route
    config = load_master_config()
    merged, _route_name = merge_bridge_config_with_route(config, explicit_route=bridge_route)
    bridge_cfg = merged.get("bridge", {}) if isinstance(merged, dict) else {}
    if not isinstance(bridge_cfg, dict):
        bridge_cfg = {}
    else:
        bridge_cfg = dict(bridge_cfg)
    if timeout_s is not None and timeout_s > 0:
        bridge_cfg["monitor_timeout_s"] = timeout_s
    resolved_provider = str(provider or "").strip().lower()
    if not resolved_provider:
        resolved_provider = str(
            config_value(bridge_cfg.get("default_target"), "chatgpt") or "chatgpt"
        ).strip().lower()
    if not resolved_provider:
        resolved_provider = "chatgpt"
    runtime_config = dict(merged) if isinstance(merged, dict) else {}
    runtime_config["bridge"] = bridge_cfg
    runtime_config["platform"] = resolved_provider
    return runtime_config, resolved_provider
