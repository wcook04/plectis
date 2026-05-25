"""Shared surface-role contract for navigation command outputs.

This module is intentionally small and dependency-light: command handlers and
projection builders can import it without pulling in kernel runtime state.
"""
from __future__ import annotations

import shlex
from typing import Any


CONTROL_ENTRY = "CONTROL_ENTRY"
ATLAS_PROJECTION = "ATLAS_PROJECTION"
DRILLDOWN = "DRILLDOWN"
DEBUG_TRACE = "DEBUG_TRACE"
MUTATOR = "MUTATOR"
PROJECTION = "PROJECTION"
LEGACY_COMPAT = "LEGACY_COMPAT"

ENTRY_REPLACEMENT = './repo-python kernel.py --entry "<task>" --context-budget 12000'


def surface_contract(
    *,
    surface_id: str,
    command: str,
    surface_role: str,
    first_contact_allowed: bool,
    authority_plane: str,
    replacement: str | None = None,
    debug_command: str | None = None,
    safe_drilldown_replacement: str | None = None,
    allowed_callers: list[str] | None = None,
    banned_callers: list[str] | None = None,
    default_output_policy: dict[str, Any] | None = None,
    debug_output_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a machine-readable surface-role contract."""
    contract: dict[str, Any] = {
        "surface_id": surface_id,
        "command": command,
        "surface_role": surface_role,
        "authority_plane": authority_plane,
        "first_contact_allowed": first_contact_allowed,
        "allowed_callers": allowed_callers or [],
        "banned_callers": banned_callers or [],
    }
    if replacement:
        contract["replacement"] = replacement
    if debug_command:
        contract["debug_command"] = debug_command
    if safe_drilldown_replacement:
        contract["safe_drilldown_replacement"] = safe_drilldown_replacement
    if default_output_policy:
        contract["default_output_policy"] = default_output_policy
    if debug_output_policy:
        contract["debug_output_policy"] = debug_output_policy
    return contract


def debug_trace_contract(*, surface_id: str, command: str, query: str) -> dict[str, Any]:
    debug_command = f"{command} {shlex.quote(query)} --debug" if query else f"{command} --debug"
    return surface_contract(
        surface_id=surface_id,
        command=command,
        surface_role=DEBUG_TRACE,
        authority_plane="debug",
        first_contact_allowed=False,
        replacement=ENTRY_REPLACEMENT,
        debug_command=debug_command,
        allowed_callers=[
            "operator_debug",
            "entry_packet.debug_trace",
            "test_failure_triage",
        ],
        banned_callers=[
            "agent_first_contact",
            "normal_task_entry",
            "route_selection",
        ],
        default_output_policy={
            "debug_fields": "hidden",
            "ranked_matches": "hidden",
        },
        debug_output_policy={
            "requires_flag": "--debug",
            "allowed_fields": [
                "score",
                "matched_on",
                "token_overlap",
                "match_count",
                "ranked_alternatives",
            ],
        },
    )


def debug_trace_block(*, surface_id: str, command: str, query: str) -> dict[str, Any]:
    """Return the default non-debug response for a debug/ranked surface."""
    contract = debug_trace_contract(surface_id=surface_id, command=command, query=query)
    contract["debug_output_policy"] = {
        "requires_flag": "--debug",
        "field_names": "hidden_until_debug",
    }
    return {
        "kind": "kernel.route_policy",
        "schema_version": "navigation_surface_contract_v0",
        "surface": command,
        "surface_id": surface_id,
        "surface_role": DEBUG_TRACE,
        "first_contact_allowed": False,
        "status": "blocked_or_demoted",
        "query": query,
        "replacement": contract["replacement"],
        "debug_command": contract["debug_command"],
        "allowed_when": contract["allowed_callers"],
        "banned_when": contract["banned_callers"],
        "why": "Ranked search/debug traces are not legal first-contact control surfaces.",
        "surface_contract": contract,
    }


def atlas_projection_contract(*, surface_id: str, command: str) -> dict[str, Any]:
    return surface_contract(
        surface_id=surface_id,
        command=command,
        surface_role=ATLAS_PROJECTION,
        authority_plane="atlas",
        first_contact_allowed=False,
        replacement=ENTRY_REPLACEMENT,
        allowed_callers=[
            "entry_packet.selected_lane",
            "selected_lane_drilldown",
            "explicit_operator_browse",
        ],
        banned_callers=[
            "agent_first_contact",
            "route_selection_without_entry_packet",
        ],
        default_output_policy={
            "shows": "kinds_rows_clusters_facets_counts_relationships",
            "does_not_choose": "operational_control_flow",
        },
    )
