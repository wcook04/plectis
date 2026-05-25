"""
[PURPOSE]
- Teleology: Validate route-aware bridge configuration merging so backend callers get one effective route, timing overlay, metadata merge, and timeout policy without re-deriving precedence by hand.
- Mechanism: Exercise `system.lib.bridge_routes` pure helpers with minimal inline config fixtures and assert the merged config and resolved timeout values.
- Non-goal: Provider dispatch or bridge capability validation; those belong to other backend cohorts.

[INTERFACE]
- Exports: The module's `test_*` cases only.
- Reads: `system.lib.bridge_routes.merge_bridge_config_with_route` and `bridge_timeout_seconds`.
- Writes: None.
- Schema: Assertions inspect merged route metadata, timing overlays, and resolved timeout scalars.

[FLOW]
- Build inline bridge config fixtures -> call the route helper under test -> assert merged metadata/timing or timeout precedence.
- When-needed: Open when debugging backend route-merging or timeout-precedence regressions without reopening the full bridge runtime.
- Escalates-to: system/lib/bridge_routes.py; system/server/tests/test_bridge_launcher.py
- Couples: These tests couple directly to `system.lib.bridge_routes` precedence rules for nested route timing and timeout overrides.
- Navigation-group: server_backend

[DEPENDENCIES]
- system.lib.bridge_routes: Pure route-resolution helpers under test.

[CONSTRAINTS]
- Guarantee: Tests stay pure and fixture-local with no filesystem or network involvement.
- Orders: Assertions assume route overrides win over base bridge timings only where explicitly configured.
- Non-goal: This module does not validate provider transport behavior or bridge-launch mechanics.
"""
from __future__ import annotations

from system.lib.bridge_routes import bridge_timeout_seconds, merge_bridge_config_with_route


def test_merge_bridge_config_with_route_merges_timings_and_meta() -> None:
    """
    [ACTION]
    - Teleology: Verify that route-specific timings and metadata overlay the base bridge config without losing unrelated base values.
    - Mechanism: Build a nested config fixture with one named route, merge it through `merge_bridge_config_with_route()`, and assert the resulting route id, metadata, and timing cells.
    - Reads: `system.lib.bridge_routes.merge_bridge_config_with_route`.
    - Writes: None.
    - Guarantee: Confirms the route overlay preserves base metadata/timings while applying the route-specific overrides.
    - Fails: Assertion failure when route precedence or metadata/timing merging drifts.
    - When-needed: Open when debugging why a named bridge route is not overriding base timing/meta fields as expected.
    - Escalates-to: system/lib/bridge_routes.py::merge_bridge_config_with_route; system/core/bridge.py::ask_ai
    - Navigation-group: server_backend
    """
    config = {
        "platform": "gemini",
        "meta": {"launch_profile": "experimental"},
        "bridge": {
            "monitor_timeout_s": {"value": 1500},
            "timings": {
                "post_paste_sleep": {"value": 1.5},
                "transport_retry_sleep": {"value": 0.75},
            },
            "routes": {
                "kernel_probe": {
                    "meta": {"lane": "kernel_probe"},
                    "timings": {
                        "post_paste_sleep": {"value": 1.75},
                    },
                }
            },
        },
    }

    merged, route_name = merge_bridge_config_with_route(config, explicit_route="kernel_probe")

    assert route_name == "kernel_probe"
    assert merged["bridge_route"] == "kernel_probe"
    assert merged["meta"]["launch_profile"] == "experimental"
    assert merged["meta"]["lane"] == "kernel_probe"
    assert merged["bridge"]["timings"]["post_paste_sleep"]["value"] == 1.75
    assert merged["bridge"]["timings"]["transport_retry_sleep"]["value"] == 0.75


def test_bridge_timeout_seconds_prefers_route_override() -> None:
    config = {
        "bridge": {
            "monitor_timeout_s": {"value": 1500},
            "routes": {
                "kernel_probe": {
                    "monitor_timeout_s": {"value": 2400},
                }
            },
        }
    }

    assert bridge_timeout_seconds(config, default=1500.0) == 1500.0
    assert bridge_timeout_seconds(config, default=1500.0, route_name="kernel_probe") == 2400.0
