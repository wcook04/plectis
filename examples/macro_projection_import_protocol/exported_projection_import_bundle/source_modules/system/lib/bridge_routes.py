"""
[PURPOSE]
- Teleology: Normalize bridge configuration shapes so callers can resolve one effective route, metadata overlay, and timeout policy without duplicating nested-versus-flat config handling.
- Mechanism: Converts flat config into the nested bridge shape when needed, unwraps literal-or-{"value": ...} fields, merges route-level timings and metadata, and exposes helpers for route name and timeout lookup.

[INTERFACE]
- Exports: config_value, resolve_bridge_route_name, merge_bridge_config_with_route, bridge_timeout_seconds.
- Reads: Caller-provided config mappings only.
- Writes: None.

[FLOW]
- Orders: config_value() unwraps literal config cells -> resolve_bridge_route_name() chooses the active route token -> merge_bridge_config_with_route() overlays route timings and metadata -> bridge_timeout_seconds() extracts the effective monitor timeout from the merged config.
- When-needed: Open when bridge callers need the authoritative route-merging rules for flat versus nested config payloads instead of re-deriving them from scattered runtime call sites.
- Escalates-to: system/lib/agent_providers.py::resolve_provider_callable; system/core/bridge.py::ask_ai
- Navigation-group: kernel_lib

[DEPENDENCIES]
- copy.deepcopy: Preserve caller config isolation while building merged views.
- typing.Mapping: Accept mapping-like config inputs without requiring concrete dicts.

[CONSTRAINTS]
- Guarantee: All helpers are pure and return fresh mappings rather than mutating caller-owned config objects.
- Non-goal: This module does not dispatch providers or validate bridge capabilities; it only prepares effective route-aware config views.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def config_value(value: Any, default: Any = None) -> Any:
    """
    [ACTION]
    - Teleology: Resolve a config cell that may be stored either as a raw value or as a mapping with a nested `value` field.
    - Mechanism: Returns mapping["value"] when present; otherwise returns the raw value or the provided default when the raw value is None.
    - Guarantee: Never mutates the input and always returns one scalar/object candidate for downstream route merging.
    - Fails: None.
    - When-needed: Open when a caller sees mixed literal-versus-wrapper config cells and needs the exact unwrap rule used by bridge routing helpers.
    - Escalates-to: system/lib/bridge_routes.py::merge_bridge_config_with_route
    """
    if isinstance(value, Mapping) and "value" in value:
        return value["value"]
    return value if value is not None else default


def _copy_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    return {}


def _bridge_root_and_mode(config: Mapping[str, Any] | None) -> tuple[dict[str, Any], bool]:
    root = _copy_mapping(config)
    if isinstance(root.get("bridge"), Mapping):
        return root, True
    bridge_root = _copy_mapping(root)
    passthrough: dict[str, Any] = {}
    for key in ("platform", "meta", "url", "bridge_route", "runtime"):
        if key in root:
            passthrough[key] = deepcopy(root[key])
    nested_root = {**passthrough, "bridge": bridge_root}
    return nested_root, False


def _unwrap_text(value: Any) -> str:
    resolved = config_value(value, "")
    return str(resolved or "").strip()


def resolve_bridge_route_name(
    config: Mapping[str, Any] | None,
    *,
    explicit_route: str | None = None,
    default_route: str | None = None,
) -> str | None:
    """
    [ACTION]
    - Teleology: Pick the single bridge route name that downstream callers should treat as active for this dispatch.
    - Mechanism: Normalizes the config into bridge-root form, then checks explicit_route, root bridge_route, nested bridge.route, and default_route in that precedence order.
    - Guarantee: Returns the first non-empty route token after trimming whitespace, or None when no route is configured anywhere.
    - Fails: None.
    - Orders: Precedence is explicit_route -> root bridge_route -> nested bridge.route -> default_route.
    - When-needed: Open when a bridge caller needs the exact precedence rule for selecting one route id from mixed flat and nested config inputs.
    - Escalates-to: system/lib/bridge_routes.py::merge_bridge_config_with_route
    """
    root, _ = _bridge_root_and_mode(config)
    bridge_cfg = _copy_mapping(root.get("bridge"))
    for candidate in (
        explicit_route,
        root.get("bridge_route"),
        bridge_cfg.get("route"),
        default_route,
    ):
        text = _unwrap_text(candidate)
        if text:
            return text
    return None


def _merge_meta(base_meta: Any, route_meta: Any) -> dict[str, Any]:
    merged = _copy_mapping(base_meta)
    if isinstance(route_meta, Mapping):
        for key, value in route_meta.items():
            merged[str(key)] = deepcopy(value)
    return merged


def merge_bridge_config_with_route(
    config: Mapping[str, Any] | None,
    *,
    explicit_route: str | None = None,
    default_route: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    """
    [ACTION]
    - Teleology: Produce the effective bridge config after applying one selected route's overrides.
    - Mechanism: Normalizes config shape, resolves the active route, overlays route timings and metadata onto the base bridge config, and returns either nested or flattened output to match the caller's original mode.
    - Guarantee: Returns a fresh config mapping plus the resolved route name; caller-owned inputs remain unchanged.
    - Fails: None.
    - Orders: Route-level timings overlay base timings first; other route fields overlay the base bridge config after timings; merged meta is only attached when a route was selected.
    - When-needed: Open when a caller needs the authoritative route-overlay behavior, especially the flat-versus-nested output contract.
    - Escalates-to: system/lib/bridge_routes.py::resolve_bridge_route_name; system/lib/bridge_routes.py::bridge_timeout_seconds
    """
    root, already_nested = _bridge_root_and_mode(config)
    bridge_cfg = _copy_mapping(root.get("bridge"))
    route_name = resolve_bridge_route_name(
        root,
        explicit_route=explicit_route,
        default_route=default_route,
    )
    routes = _copy_mapping(bridge_cfg.get("routes"))
    route_cfg = _copy_mapping(routes.get(route_name)) if route_name else {}

    merged_bridge = _copy_mapping(bridge_cfg)
    base_timings = _copy_mapping(bridge_cfg.get("timings"))
    route_timings = _copy_mapping(route_cfg.pop("timings", {}))
    if route_timings:
        base_timings.update(route_timings)
        merged_bridge["timings"] = base_timings

    route_meta = route_cfg.pop("meta", {})
    if route_cfg:
        merged_bridge.update(route_cfg)

    merged_root = _copy_mapping(root)
    merged_root["bridge"] = merged_bridge

    merged_meta = _merge_meta(merged_root.get("meta"), route_meta)
    if route_name:
        merged_root["bridge_route"] = route_name
        merged_root["meta"] = merged_meta

    if already_nested:
        return merged_root, route_name

    flat_config = _copy_mapping(merged_bridge)
    for key in ("platform", "meta", "url", "bridge_route", "runtime"):
        if key in merged_root:
            flat_config[key] = deepcopy(merged_root[key])
    return flat_config, route_name


def bridge_timeout_seconds(
    config: Mapping[str, Any] | None,
    *,
    default: float,
    route_name: str | None = None,
    default_route: str | None = None,
) -> float:
    """
    [ACTION]
    - Teleology: Resolve the effective monitor timeout after route overlays have been applied.
    - Mechanism: Reuses merge_bridge_config_with_route(), reads bridge.monitor_timeout_s through config_value(), coerces it to float, and falls back to the supplied default on invalid or non-positive values.
    - Guarantee: Returns a positive float timeout suitable for bridge monitors and callers that need one resolved number.
    - Fails: None.
    - When-needed: Open when a bridge caller needs the exact timeout resolution rule after route-specific overrides.
    - Escalates-to: system/lib/bridge_routes.py::merge_bridge_config_with_route; system/core/bridge.py::ask_ai
    """
    merged, _ = merge_bridge_config_with_route(
        config,
        explicit_route=route_name,
        default_route=default_route,
    )
    bridge_cfg = merged.get("bridge") if isinstance(merged, Mapping) else None
    if not isinstance(bridge_cfg, Mapping):
        bridge_cfg = merged if isinstance(merged, Mapping) else {}
    raw_timeout = config_value(bridge_cfg.get("monitor_timeout_s"), default)
    try:
        resolved = float(raw_timeout)
    except (TypeError, ValueError):
        return default
    return resolved if resolved > 0 else default
