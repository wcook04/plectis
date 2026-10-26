#!/usr/bin/env python3
"""Frontend navigation graph — drift-proof projection over the cockpit surfaces.

Three evidence sources, one projection. Every node in the emitted graph carries a
`evidence` block naming the exact file + line that declared it, so divergence between
the router, the surface registry, and the capture manifest is loud, not silent.

Sources
-------
1. system/server/ui/src/App.tsx                    — route authority (React Router)
2. system/server/ui/src/navigation/surfaces.ts     — surface registry (labels,
                                                      groups, keywords, capture slug,
                                                      outboundTo, cul-de-sac flag, etc.)
3. system/server/ui/src/navigation/overlays.ts     — modal / drawer / palette registry
                                                      (OPTIONAL — skipped if absent)
4. system/server/ui/src/pages/StationLens.tsx      — StationLens sub-router (for
                                                      lens_sibling edge derivation)
5. tools/meta/observability/station_views.json     — per-view capture contract
6. tools/meta/observability/wayfinding_scenarios.json — canonical proof suite

Output
------
state/frontend_navigation/navigation_graph.json (canonical JSON projection)
state/frontend_navigation/navigation_graph.snapshot.md (human-readable render)
state/frontend_navigation/surface_relation_audit.v1.json (relation provenance audit)
state/frontend_navigation/wayfinding_capability_matrix.v1.json (capability coverage)
state/frontend_navigation/wayfinding_scenario_frontier.v1.json (coverage frontier)
state/frontend_navigation/navigation_mission_control.v1.json (Mission Control packet)

CLI
---
    frontend_nav_graph.py --print                 # emit JSON to stdout
    frontend_nav_graph.py --dry-run               # summary counts only
    frontend_nav_graph.py --write                 # write canonical files
    frontend_nav_graph.py --check                 # exit non-zero on drift
    frontend_nav_graph.py --view <slug>           # one view's record
    frontend_nav_graph.py --edges <slug>          # inbound + outbound for one view
    frontend_nav_graph.py --wayfind <from> <to>   # executable wayfinding plan
    frontend_nav_graph.py --capability-matrix     # action-kind capability coverage
    frontend_nav_graph.py --scenario-frontier     # ranked next proof candidates
    frontend_nav_graph.py --mission-control       # cockpit Mission Control packet
    frontend_nav_graph.py --pathway-audit         # hover-pathway zero-island contract
    frontend_nav_graph.py --cul-de-sacs           # list declared terminals + undeclared dead-ends
    frontend_nav_graph.py --drift                 # list drift signals only
    frontend_nav_graph.py --agent-packet <slug>   # one-shot AI packet: view + outbound + capture

Drift discipline (RIG-style, pattern-transferred from annexes/repo-intelligence-graph)
----------------
Never infer navigation. Every node / edge is evidence-backed. Three-way consistency:
every App.tsx route must have (a) a surface or overlay that claims it, and (b) a
capture manifest row OR an explicit capture_excluded flag. Surfaces without routes,
routes without surfaces, and capture rows without surfaces are all drift_signals.

Cul-de-sac discipline (honesty-over-inference, pattern-matched to distillation-rubric)
---------------------
A view with zero outbound edges is either (i) declared terminal via
`isCulDeSac: { reason: "..." }` in surfaces.ts, in which case the reason is recorded,
OR (ii) an undeclared cul-de-sac, which is flagged as a drift_signal for operator
review. We never silently synthesize an "it must be intentional" gloss.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import frontend_surface_contracts

SOURCE_APP_TSX = REPO_ROOT / "system/server/ui/src/App.tsx"
SOURCE_SURFACES_TS = REPO_ROOT / "system/server/ui/src/navigation/surfaces.ts"
SOURCE_OVERLAYS_TS = REPO_ROOT / "system/server/ui/src/navigation/overlays.ts"
SOURCE_STATION_LENS_TSX = REPO_ROOT / "system/server/ui/src/pages/StationLens.tsx"
SOURCE_STATION_VIEWS_JSON = REPO_ROOT / "tools/meta/observability/station_views.json"
SOURCE_WAYFINDING_SCENARIOS_JSON = REPO_ROOT / "tools/meta/observability/wayfinding_scenarios.json"
SOURCE_RENDER_LOAD_INDEX = REPO_ROOT / "state/observability/render_load_index.json"
SOURCE_SEMANTIC_LAYER_JSON = REPO_ROOT / "state/frontend_navigation/semantic_layer.v1.json"
SOURCE_COMPONENT_INDEX_JSON = REPO_ROOT / "state/frontend_navigation/component_index.json"

OUTPUT_DIR = REPO_ROOT / "state/frontend_navigation"
OUTPUT_JSON = OUTPUT_DIR / "navigation_graph.json"
OUTPUT_SNAPSHOT = OUTPUT_DIR / "navigation_graph.snapshot.md"
OUTPUT_SURFACE_RELATION_AUDIT = OUTPUT_DIR / "surface_relation_audit.v1.json"
OUTPUT_CAPABILITY_MATRIX = OUTPUT_DIR / "wayfinding_capability_matrix.v1.json"
OUTPUT_MISSION_CONTROL = OUTPUT_DIR / "navigation_mission_control.v1.json"
OUTPUT_SCENARIO_FRONTIER = OUTPUT_DIR / "wayfinding_scenario_frontier.v1.json"

SCHEMA_VERSION = 8
SURFACE_RELATION_AUDIT_SCHEMA_VERSION = 1
WAYFINDING_CONTRACT = "frontend_wayfinding_v1"
WAYFINDING_PLANNER = "shortest_available_affordance_path_v1"
INVOCATION_CONTRACT = "frontend_invocation_affordance_v1"
CAPABILITY_MATRIX_CONTRACT = "frontend_wayfinding_capability_matrix_v1"
SCENARIO_SUITE_CONTRACT = "frontend_wayfinding_scenario_suite_v1"
SCENARIO_SUITE_RECEIPT_CONTRACT = "frontend_wayfinding_scenario_suite_receipt_v1"
MISSION_CONTROL_CONTRACT = "frontend_navigation_mission_control_v1"
SCENARIO_FRONTIER_CONTRACT = "frontend_wayfinding_scenario_frontier_v1"
FRONTEND_VALIDATION_MATRIX_SCHEMA = "frontend_validation_matrix_v1"
WAYFINDING_ACTION_KINDS = [
    "open_route",
    "open_entry_route",
    "station_lens_switch",
    "command_palette_select",
    "overlay_open",
    "drawer_open",
    "external_or_unavailable",
]
FRONTEND_VALIDATION_ACCEPTANCE_COMMANDS = [
    {
        "id": "frontend_vitest_matrix",
        "covers": ["route_navigation_vitest", "runtime_url_vitest"],
        "command": (
            "cd system/server/ui && npm test -- --host-pressure-policy=warn "
            "src/__tests__/App.navigation.test.tsx src/__tests__/runtime.urls.test.ts"
        ),
    },
    {
        "id": "frontend_pytest_matrix",
        "covers": ["station_render_pytest", "safe_cleanup_pytest"],
        "command": (
            "./repo-pytest --host-pressure-policy=warn system/server/tests/test_station_render.py "
            "system/server/tests/test_frontend_ui_safe_cleanup.py"
        ),
    },
]
FRONTEND_VALIDATION_LANES = {
    "route_navigation_vitest": {
        "kind": "vitest",
        "command": (
            "cd system/server/ui && npm test -- --host-pressure-policy=warn "
            "src/__tests__/App.navigation.test.tsx"
        ),
        "authority": "React navigation behavior and primary route rendering.",
    },
    "runtime_url_vitest": {
        "kind": "vitest",
        "command": (
            "cd system/server/ui && npm test -- --host-pressure-policy=warn "
            "src/__tests__/runtime.urls.test.ts"
        ),
        "authority": "Runtime URL helper behavior for browser/API origins.",
    },
    "station_render_pytest": {
        "kind": "pytest",
        "command": "./repo-pytest --host-pressure-policy=warn system/server/tests/test_station_render.py",
        "authority": "Station render manifest, route readiness, geometry, and receipt contracts.",
    },
    "safe_cleanup_pytest": {
        "kind": "pytest",
        "command": (
            "./repo-pytest --host-pressure-policy=warn "
            "system/server/tests/test_frontend_ui_safe_cleanup.py"
        ),
        "authority": "Frontend route/static cleanup guardrails.",
    },
    "browser_visual_smoke": {
        "kind": "station_render_browser",
        "command_template": (
            "./repo-python tools/meta/observability/station_render.py render "
            "--view <capture_slug> --engine chromium --viewport fhd_landscape "
            "--host-pressure-policy warn"
        ),
        "authority": "Fresh browser screenshot proof for a concrete capture slug.",
    },
    "source_backed_invocation_harness": {
        "kind": "playwright_or_station_render_replay",
        "command_template": (
            "./repo-python tools/meta/observability/view_wayfinding_check.py "
            "--from <source_view_id> --to <target_view_id> --mode embodied --engine chromium"
        ),
        "authority": "Source-backed replay for transient surfaces without a direct route.",
    },
    "capture_contract_repair": {
        "kind": "authoring_contract",
        "command_template": (
            "Bind a surfaces.ts captureSlug to a station_views.json row before browser visual signoff."
        ),
        "authority": "Capture manifest is required before screenshot proof is authoritative.",
    },
}
FRONTEND_VALIDATION_ROUTE_CLASSES = {
    "captured_page": {
        "description": "Routed page with a station_views capture slug and ready selector.",
        "required_lanes": [
            "route_navigation_vitest",
            "runtime_url_vitest",
            "station_render_pytest",
            "safe_cleanup_pytest",
            "browser_visual_smoke",
        ],
        "browser_requirement": "station_render_capture_required",
    },
    "uncaptured_page": {
        "description": "Routed page without a complete capture contract.",
        "required_lanes": [
            "route_navigation_vitest",
            "runtime_url_vitest",
            "station_render_pytest",
            "safe_cleanup_pytest",
            "capture_contract_repair",
        ],
        "browser_requirement": "blocked_until_capture_contract_exists",
    },
    "transient_surface": {
        "description": "Modal, drawer, or overlay surface without a direct browser route.",
        "required_lanes": [
            "route_navigation_vitest",
            "safe_cleanup_pytest",
            "source_backed_invocation_harness",
        ],
        "browser_requirement": "source_backed_invocation_required",
    },
    "redirect": {
        "description": "Redirect route; visual proof belongs to the resolved target route.",
        "required_lanes": ["runtime_url_vitest", "safe_cleanup_pytest"],
        "browser_requirement": "covered_by_target_route",
    },
    "unclassified_surface": {
        "description": "Surface kind not covered by the frontend validation matrix.",
        "required_lanes": ["safe_cleanup_pytest"],
        "browser_requirement": "manual_contract_required",
    },
}


# presentation_role values mirror world_model.NAVIGATION_EDGE_MECHANISM_META;
# the StationSurfaceAtlas renderer (presentationRoleTone / presentationRoleLabel)
# defaults to 'fallback' when this field is absent, which made every edge land
# in the amber low-authority bucket regardless of mechanism.
EDGE_MECHANISM_META: dict[str, dict[str, Any]] = {
    "explicit": {
        "label": "opens",
        "category": "declared_navigation",
        "description": "Surface registry outboundTo declaration; this is an intentional cross-surface jump.",
        "presentation_role": "pathway",
        "rank": 0,
        "weight": 1.0,
    },
    "overlay_anchor": {
        "label": "hosts overlay",
        "category": "hosted_overlay",
        "description": "Overlay, modal, or drawer is hosted by this page surface.",
        "presentation_role": "pathway",
        "rank": 1,
        "weight": 0.86,
    },
    "route_hierarchy": {
        "label": "route child",
        "category": "route_structure",
        "description": "Child surface is hosted under the selected route prefix in App.tsx.",
        "presentation_role": "pathway",
        "rank": 2,
        "weight": 0.82,
    },
    "legacy_or_workbench_of": {
        "label": "workbench of",
        "category": "surface_lifecycle",
        "description": "Workbench or legacy route is parked behind a canonical surface instead of replacing it.",
        "presentation_role": "pathway",
        "rank": 3,
        "weight": 0.78,
    },
    "shared_backend_api": {
        "label": "shares API",
        "category": "backend_dependency",
        "description": "Both surfaces call the same typed API method from their owning component file.",
        "presentation_role": "pathway",
        "rank": 4,
        "weight": 0.70,
    },
    "shared_component": {
        "label": "shares component",
        "category": "frontend_dependency",
        "description": "Both surfaces render through the same primary component or shared frontend primitive.",
        "presentation_role": "pathway",
        "rank": 5,
        "weight": 0.64,
    },
    "station_group": {
        "label": "same Station group",
        "category": "station_lens_navigation",
        "description": "Both views are siblings inside the Station lens group.",
        "presentation_role": "membership",
        "rank": 20,
        "weight": 0.40,
    },
    "shell_group": {
        "label": "same shell group",
        "category": "global_shell_navigation",
        "description": "Both views are reachable from the same global shell navigation group.",
        "presentation_role": "membership",
        "rank": 30,
        "weight": 0.30,
    },
    "station_lens_menu": {
        "label": "Station lens menu",
        "category": "station_lens_navigation",
        "description": "Both views are Station lens members reachable through the lens menu.",
        "presentation_role": "membership",
        "rank": 40,
        "weight": 0.26,
    },
    "unknown": {
        "label": "navigation relation",
        "category": "unknown",
        "description": "Navigation graph relation with no known mechanism metadata.",
        "presentation_role": "fallback",
        "rank": 99,
        "weight": 0.20,
    },
}

PATHWAY_PRESENTATION_ROLE = "pathway"
EXPLICIT_PATHWAY_MECHANISMS = {"explicit"}
ALLOWED_ZERO_PATHWAY_VIEW_IDS = {
    "command_palette",
    "console_drawer",
}


# ---------------------------------------------------------------------------
# Data shapes (plain dicts in the JSON output; typed here for authoring clarity)
# ---------------------------------------------------------------------------


@dataclass
class _Evidence:
    file: str
    line: int

    def to_json(self) -> dict[str, Any]:
        return {"file": self.file, "line": self.line}


@dataclass
class _RouteDecl:
    path: str
    element: str  # component name, OR "Navigate:<target>" for redirects
    evidence: _Evidence


@dataclass
class _SurfaceDecl:
    id: str
    route: str
    entry_route: str | None
    route_aliases: list[str]
    label: str
    purpose: str
    keywords: list[str]
    shortcut: str | None
    shell_group: str | None
    station_group: str | None
    home_tile_order: float | None
    station_lens_eligible: bool
    kind: str  # "page" | "modal" | "drawer" | "overlay" | "redirect"
    outbound_to: list[str]
    is_cul_de_sac: dict[str, Any] | None  # {"reason": "..."} when declared
    capture_slug: str | None
    overlay_of: str | None
    invocation: dict[str, Any] | None
    evidence: _Evidence


@dataclass
class _CaptureRow:
    slug: str
    route: str
    purpose: str | None
    ready_selector: str | None
    stabilize_ms: int | None
    capture_group: str | None
    notes: str | None
    capture_mode: str | None
    full_page: bool | None
    canonical_slug: str | None
    row_role: str | None
    evidence: _Evidence


# ---------------------------------------------------------------------------
# Parsers (regex-based against stable TS literals; fail loud on unexpected shape)
# ---------------------------------------------------------------------------


_ROUTE_PATTERN = re.compile(
    r'<Route\s+path="([^"]+)"\s+element=\{\s*<(\w+)(?:\s+to="([^"]+)")?'
)


def _parse_app_tsx(text: str) -> list[_RouteDecl]:
    routes: list[_RouteDecl] = []
    for match in _ROUTE_PATTERN.finditer(text):
        path, component, navigate_to = match.group(1), match.group(2), match.group(3)
        line = text.count("\n", 0, match.start()) + 1
        if component in {"Navigate", "RedirectPreservingLocation"} and navigate_to:
            element = f"Navigate:{navigate_to}"
        else:
            element = component
        routes.append(
            _RouteDecl(
                path=path,
                element=element,
                evidence=_Evidence(file=str(SOURCE_APP_TSX.relative_to(REPO_ROOT)), line=line),
            )
        )
    return routes


def _strip_ts_comments(text: str) -> str:
    # Strip block comments and line comments for cleaner literal parsing.
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"(^|[^:])//[^\n]*", r"\1", text)
    return text


def _find_balanced_block(text: str, start_idx: int, open_char: str, close_char: str) -> int:
    """Return the index one past the matching close_char for the block starting at start_idx."""
    depth = 0
    i = start_idx
    in_str: str | None = None
    while i < len(text):
        ch = text[i]
        if in_str is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"', "`"):
            in_str = ch
            i += 1
            continue
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError(f"Unbalanced {open_char}{close_char} starting at {start_idx}")


_SURFACE_FIELD_PATTERNS = {
    "id": re.compile(r"\bid:\s*'([^']+)'"),
    "route": re.compile(r"\broute:\s*'([^']+)'"),
    "entry_route": re.compile(r"\bentryRoute:\s*'([^']+)'"),
    "label": re.compile(r"\blabel:\s*'([^']*)'"),
    "purpose": re.compile(r"\bpurpose:\s*'((?:[^'\\]|\\.)*)'"),
    "shortcut": re.compile(r"\bshortcut:\s*'([^']*)'"),
    "shell_group": re.compile(r"\bshellGroup:\s*'([^']+)'"),
    "station_group": re.compile(r"\bstationGroup:\s*'([^']+)'"),
    "home_tile_order": re.compile(r"\bhomeTileOrder:\s*([0-9]+(?:\.[0-9]+)?)"),
    "station_lens_eligible": re.compile(r"\bstationLensEligible:\s*(true|false)"),
    "kind": re.compile(r"\bkind:\s*'([^']+)'"),
    "capture_slug": re.compile(r"\bcaptureSlug:\s*'([^']+)'"),
    "overlay_of": re.compile(r"\boverlayOf:\s*'([^']+)'"),
}

_KEYWORDS_PATTERN = re.compile(r"\bkeywords:\s*\[([^\]]*)\]", re.DOTALL)
_ROUTE_ALIASES_PATTERN = re.compile(r"\brouteAliases:\s*\[([^\]]*)\]", re.DOTALL)
_OUTBOUND_PATTERN = re.compile(r"\boutboundTo:\s*\[([^\]]*)\]", re.DOTALL)
_CUL_DE_SAC_PATTERN = re.compile(
    r"\bisCulDeSac:\s*\{\s*reason:\s*'((?:[^'\\]|\\.)*)'[\s,]*\}",
    re.DOTALL,
)
_INVOCATION_FIELD_PATTERNS = {
    "action_id": re.compile(r"\bactionId:\s*'([^']+)'"),
    "action_kind": re.compile(r"\bactionKind:\s*'([^']+)'"),
    "safety_class": re.compile(r"\bsafetyClass:\s*'([^']+)'"),
    "strategy": re.compile(r"\bstrategy:\s*'([^']+)'"),
    "role": re.compile(r"\brole:\s*'([^']+)'"),
    "name": re.compile(r"\bname:\s*'([^']+)'"),
    "test_id": re.compile(r"\btestId:\s*'([^']+)'"),
    "selector": re.compile(r"\bselector:\s*'([^']+)'"),
    "keys": re.compile(r"\bkeys:\s*'([^']+)'"),
    "ready_selector": re.compile(r"\breadySelector:\s*'([^']+)'"),
    "capture_slug": re.compile(r"\bcaptureSlug:\s*'([^']+)'"),
    "focus_selector": re.compile(r"\bfocusSelector:\s*'([^']+)'"),
    "focus_policy": re.compile(r"\bfocusPolicy:\s*'([^']+)'"),
}


def _extract_string_list(fragment: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"'([^']+)'", fragment)]


def _extract_object_block(block: str, field_name: str) -> str | None:
    match = re.search(rf"\b{re.escape(field_name)}:\s*\{{", block)
    if not match:
        return None
    start = match.end() - 1
    end = _find_balanced_block(block, start, "{", "}")
    return block[start:end]


def _extract_invocation_contract(block: str) -> dict[str, Any] | None:
    invocation_block = _extract_object_block(block, "invocation")
    if invocation_block is None:
        return None

    def _get(field: str) -> str | None:
        match = _INVOCATION_FIELD_PATTERNS[field].search(invocation_block)
        return match.group(1) if match else None

    trigger_block = _extract_object_block(invocation_block, "trigger") or ""
    expected_block = _extract_object_block(invocation_block, "expected") or ""

    def _get_from(block_text: str, field: str) -> str | None:
        match = _INVOCATION_FIELD_PATTERNS[field].search(block_text)
        return match.group(1) if match else None

    trigger = {
        key: value
        for key, value in {
            "strategy": _get_from(trigger_block, "strategy"),
            "role": _get_from(trigger_block, "role"),
            "name": _get_from(trigger_block, "name"),
            "test_id": _get_from(trigger_block, "test_id"),
            "selector": _get_from(trigger_block, "selector"),
            "keys": _get_from(trigger_block, "keys"),
        }.items()
        if value
    }
    expected = {
        key: value
        for key, value in {
            "ready_selector": _get_from(expected_block, "ready_selector"),
            "capture_slug": _get_from(expected_block, "capture_slug"),
            "focus_selector": _get_from(expected_block, "focus_selector"),
            "focus_policy": _get_from(expected_block, "focus_policy"),
        }.items()
        if value
    }

    return {
        key: value
        for key, value in {
            "action_id": _get("action_id"),
            "action_kind": _get("action_kind"),
            "safety_class": _get("safety_class"),
            "trigger": trigger if trigger else None,
            "expected": expected if expected else None,
        }.items()
        if value
    }


def _parse_surfaces_ts(text: str) -> list[_SurfaceDecl]:
    clean = _strip_ts_comments(text)
    # Find the SURFACES array literal.
    array_match = re.search(
        r"const\s+SURFACES\s*:\s*SurfaceDefinition\[\]\s*=\s*\[", clean
    )
    if not array_match:
        raise SystemExit(
            f"[frontend_nav_graph] SURFACES array not found in {SOURCE_SURFACES_TS}"
        )
    array_start = array_match.end() - 1
    array_end = _find_balanced_block(clean, array_start, "[", "]")
    array_body = clean[array_start + 1 : array_end - 1]

    surfaces: list[_SurfaceDecl] = []
    cursor = 0
    while cursor < len(array_body):
        brace_idx = array_body.find("{", cursor)
        if brace_idx == -1:
            break
        obj_end = _find_balanced_block(array_body, brace_idx, "{", "}")
        block = array_body[brace_idx:obj_end]
        cursor = obj_end
        if "id:" not in block:
            continue
        # Line number of the declaration within the raw TS (1-indexed).
        # Recompute from cleaned-then-raw offset: use raw text search for 'id: ...'.
        surface = _surface_from_block(block, text, SOURCE_SURFACES_TS)
        surfaces.append(surface)
    return surfaces


def _surface_from_block(block: str, full_raw_text: str, source_path: Path) -> _SurfaceDecl:
    def _get(field: str, cast=str, default=None):  # noqa: A002 — shadow builtin by design
        pat = _SURFACE_FIELD_PATTERNS[field]
        m = pat.search(block)
        if not m:
            return default
        raw = m.group(1)
        if cast is bool:
            return raw == "true"
        if cast is float:
            return float(raw)
        return raw

    kw = _KEYWORDS_PATTERN.search(block)
    keywords = _extract_string_list(kw.group(1)) if kw else []

    aliases_match = _ROUTE_ALIASES_PATTERN.search(block)
    route_aliases = _extract_string_list(aliases_match.group(1)) if aliases_match else []

    outbound_match = _OUTBOUND_PATTERN.search(block)
    outbound = _extract_string_list(outbound_match.group(1)) if outbound_match else []

    cul_match = _CUL_DE_SAC_PATTERN.search(block)
    is_cul_de_sac = (
        {"reason": cul_match.group(1).replace("\\'", "'")} if cul_match else None
    )

    surface_id = _get("id") or "unknown"

    # Locate declaration line in the raw text for evidence.
    anchor = f"id: '{surface_id}'"
    raw_idx = full_raw_text.find(anchor)
    if raw_idx == -1:
        raw_idx = full_raw_text.find(f'id: "{surface_id}"')
    line = full_raw_text.count("\n", 0, raw_idx) + 1 if raw_idx >= 0 else 0

    return _SurfaceDecl(
        id=surface_id,
        route=_get("route") or "",
        entry_route=_get("entry_route"),
        route_aliases=route_aliases,
        label=_get("label") or surface_id,
        purpose=(_get("purpose") or "").replace("\\'", "'"),
        keywords=keywords,
        shortcut=_get("shortcut"),
        shell_group=_get("shell_group"),
        station_group=_get("station_group"),
        home_tile_order=_get("home_tile_order", cast=float),
        station_lens_eligible=_get("station_lens_eligible", cast=bool, default=False),
        kind=_get("kind") or "page",
        outbound_to=outbound,
        is_cul_de_sac=is_cul_de_sac,
        capture_slug=_get("capture_slug"),
        overlay_of=_get("overlay_of"),
        invocation=_extract_invocation_contract(block),
        evidence=_Evidence(
            file=str(source_path.relative_to(REPO_ROOT)), line=line
        ),
    )


def _parse_overlays_ts(path: Path) -> list[_SurfaceDecl]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    clean = _strip_ts_comments(text)
    array_match = re.search(
        r"const\s+OVERLAYS\s*:\s*SurfaceDefinition\[\]\s*=\s*\[", clean
    )
    if not array_match:
        return []
    array_start = array_match.end() - 1
    array_end = _find_balanced_block(clean, array_start, "[", "]")
    array_body = clean[array_start + 1 : array_end - 1]

    overlays: list[_SurfaceDecl] = []
    cursor = 0
    while cursor < len(array_body):
        brace_idx = array_body.find("{", cursor)
        if brace_idx == -1:
            break
        obj_end = _find_balanced_block(array_body, brace_idx, "{", "}")
        block = array_body[brace_idx:obj_end]
        cursor = obj_end
        if "id:" not in block:
            continue
        overlays.append(_surface_from_block(block, text, SOURCE_OVERLAYS_TS))
    # Force kind default for overlays to "overlay" if not specified.
    for ov in overlays:
        if ov.kind == "page":
            ov.kind = "overlay"
    return overlays


_LENS_SWITCH_PATTERN = re.compile(
    r"pathname\.startsWith\('([^']+)'\)\)\s*return\s*'(\w+)'"
)


def _parse_station_lens(text: str) -> dict[str, str]:
    """Return a path-prefix -> lens_id mapping derived from resolveLensId()."""
    mapping: dict[str, str] = {}
    for match in _LENS_SWITCH_PATTERN.finditer(text):
        mapping[match.group(1)] = match.group(2)
    return mapping


def _parse_station_views(path: Path) -> list[_CaptureRow]:
    if not path.exists():
        raise SystemExit(f"[frontend_nav_graph] Missing manifest: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[_CaptureRow] = []
    for idx, v in enumerate(data.get("views", [])):
        rows.append(
            _CaptureRow(
                slug=v["slug"],
                route=v["route"],
                purpose=v.get("purpose"),
                ready_selector=v.get("ready_selector"),
                stabilize_ms=v.get("stabilize_ms"),
                capture_group=v.get("capture_group"),
                notes=v.get("notes"),
                capture_mode=(
                    v.get("capture_mode") if isinstance(v.get("capture_mode"), str) else None
                ),
                full_page=v.get("full_page"),
                canonical_slug=(
                    v.get("canonical_slug") if isinstance(v.get("canonical_slug"), str) else None
                ),
                row_role=v.get("row_role") if isinstance(v.get("row_role"), str) else None,
                evidence=_Evidence(
                    file=str(path.relative_to(REPO_ROOT)),
                    line=idx,  # array index, not file line (JSON lines are shapeless)
                ),
            )
        )
    return rows


def _maybe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _load_render_load_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _load_semantic_layer(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": None, "views": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema_version": None, "views": []}
    return data if isinstance(data, dict) else {"schema_version": None, "views": []}


def _load_component_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"__meta": {}, "components": [], "files": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"__meta": {}, "components": [], "files": {}}
    return data if isinstance(data, dict) else {"__meta": {}, "components": [], "files": {}}


def _load_output_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _repo_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _path_from_index_value(path_value: Any) -> Path | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    path = Path(path_value)
    return path if path.is_absolute() else REPO_ROOT / path


def _file_meta(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload: dict[str, Any] = {
        "path": _display_path(path),
        "exists": path.exists(),
    }
    if not path.exists() or not path.is_file():
        return payload
    stat = path.stat()
    payload.update(
        {
            "mtime": _dt.datetime.fromtimestamp(
                stat.st_mtime, _dt.timezone.utc
            ).isoformat(timespec="seconds"),
            "mtime_ns": stat.st_mtime_ns,
            "sha256_12": hashlib.sha256(path.read_bytes()).hexdigest()[:12],
        }
    )
    return payload


def _sha256_12_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()[:12]


def _committed_file_sha256_12(path: Path) -> str | None:
    try:
        rel_path = _repo_rel(path)
    except ValueError:
        return None
    result = subprocess.run(
        ["git", "show", f"HEAD:{rel_path}"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return None
    return _sha256_12_bytes(result.stdout)


def _render_load_index_commit_policy(load_index: Mapping[str, Any]) -> str | None:
    lifecycle = load_index.get("artifact_lifecycle")
    if not isinstance(lifecycle, Mapping):
        return None
    policy = lifecycle.get("commit_policy")
    return policy if isinstance(policy, str) and policy else None


def _render_load_index_authority(load_index: Mapping[str, Any]) -> dict[str, Any]:
    policy = _render_load_index_commit_policy(load_index)
    live_meta = _file_meta(SOURCE_RENDER_LOAD_INDEX) or {}
    live_hash = live_meta.get("sha256_12")
    committed_hash = _committed_file_sha256_12(SOURCE_RENDER_LOAD_INDEX)
    use_committed_projection = (
        isinstance(policy, str)
        and "do_not_commit_as_source" in policy
        and committed_hash is not None
        and live_hash != committed_hash
    )
    authority_hash = committed_hash if use_committed_projection else live_hash
    mode = (
        "committed_projection_source_latest_index_dirty"
        if use_committed_projection
        else (
            "tracked_latest_projection"
            if isinstance(policy, str) and "do_not_commit_as_source" in policy
            else "working_tree_source"
        )
    )
    return {
        "schema": "frontend_navigation_render_status_authority_v1",
        "mode": mode,
        "hash": authority_hash,
        "index_path": _display_path(SOURCE_RENDER_LOAD_INDEX),
        "working_tree_hash": live_hash,
        "committed_hash": committed_hash,
        "working_tree_dirty": (
            live_hash != committed_hash if live_hash and committed_hash else None
        ),
        "commit_policy": policy,
        "reason": (
            "render_load_index is a runtime latest projection; frontend navigation "
            "uses the tracked projection as source authority until a render receipt "
            "is explicitly promoted"
            if use_committed_projection
            else "frontend navigation uses the current render-load projection as source authority"
        ),
    }


def _render_status_source(load_index: Mapping[str, Any]) -> dict[str, Any]:
    source_log_path = _path_from_index_value(load_index.get("source_log"))
    return {
        "schema": "frontend_navigation_render_status_source_v1",
        "index_path": _display_path(SOURCE_RENDER_LOAD_INDEX),
        "index_generated_at": load_index.get("generated_at"),
        "authority": _render_load_index_authority(load_index),
        "index": _file_meta(SOURCE_RENDER_LOAD_INDEX),
        "source_log": _file_meta(source_log_path),
        "projection_generated_at": None,
    }


def _resolve_ts_import_path(source_path: Path, import_path: str) -> str | None:
    if not import_path.startswith("."):
        return None
    base = (source_path.parent / import_path).resolve()
    candidates = [
        base,
        base.with_suffix(".tsx"),
        base.with_suffix(".ts"),
        base / "index.tsx",
        base / "index.ts",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            try:
                return _repo_rel(candidate)
            except ValueError:
                return None
    return None


_DEFAULT_IMPORT_PATTERN = re.compile(
    r"import\s+([A-Z][A-Za-z0-9_]*)\s+from\s+['\"]([^'\"]+)['\"]"
)
# React lazy-loaded pages — App.tsx routes all use this shape:
#   const LeanMathematicsLens = lazy(() => import('./pages/LeanMathematicsLens'));
# Without this, the extractor falls back to App.tsx as the page's primary
# component and loses every backend/api call the lazy page actually makes.
_LAZY_DEFAULT_IMPORT_PATTERN = re.compile(
    r"const\s+([A-Z][A-Za-z0-9_]*)\s*=\s*lazy\(\s*\(\)\s*=>\s*import\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\)"
)
_NAMED_IMPORT_PATTERN = re.compile(
    r"import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"]",
    re.DOTALL,
)
_API_CALL_PATTERN = re.compile(r"\bapi((?:\.[A-Za-z_$][A-Za-z0-9_$]*)+)")
_FETCH_CALL_PATTERN = re.compile(r"\bfetch\(\s*['\"]([^'\"]+)['\"]")
_LENS_RENDER_PATTERN = re.compile(
    r"if\s*\(\s*targetLensId\s*===\s*'([^']+)'\s*\)[\s\S]{0,220}?<([A-Z][A-Za-z0-9_]*)"
)


def _parse_default_imports(text: str, source_path: Path) -> dict[str, str]:
    imports: dict[str, str] = {}
    for match in _DEFAULT_IMPORT_PATTERN.finditer(text):
        resolved = _resolve_ts_import_path(source_path, match.group(2))
        if resolved:
            imports[match.group(1)] = resolved
    for match in _LAZY_DEFAULT_IMPORT_PATTERN.finditer(text):
        # First match wins to mirror static-import precedence above.
        if match.group(1) in imports:
            continue
        resolved = _resolve_ts_import_path(source_path, match.group(2))
        if resolved:
            imports[match.group(1)] = resolved
    return imports


def _parse_all_component_imports(text: str, source_path: Path) -> dict[str, str]:
    imports = _parse_default_imports(text, source_path)
    for match in _NAMED_IMPORT_PATTERN.finditer(text):
        resolved = _resolve_ts_import_path(source_path, match.group(2))
        if not resolved:
            continue
        for raw_name in match.group(1).split(","):
            token = raw_name.strip()
            if not token or token.startswith("type "):
                token = token.replace("type ", "", 1).strip()
            if not token:
                continue
            local = token.split(" as ")[-1].strip()
            if re.match(r"^[A-Z][A-Za-z0-9_]*$", local):
                imports[local] = resolved
    return imports


def _parse_lens_component_map(station_lens_text: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for match in _LENS_RENDER_PATTERN.finditer(station_lens_text):
        lens_id, component = match.group(1), match.group(2)
        mapping.setdefault(lens_id, component)
    return mapping


def _matching_route_decl(surface: _SurfaceDecl, routes: list[_RouteDecl]) -> _RouteDecl | None:
    candidates = [surface.entry_route, surface.route, *surface.route_aliases]
    for candidate in candidates:
        if not candidate:
            continue
        for route in routes:
            if route.path == candidate:
                return route
    route = surface.entry_route or surface.route
    if not route:
        return None
    best: _RouteDecl | None = None
    for decl in routes:
        if decl.element.startswith("Navigate:"):
            continue
        bare = decl.path.split(":")[0].rstrip("/")
        if not bare:
            continue
        if route == bare or route.startswith(bare + "/"):
            if best is None or len(bare) > len(best.path.split(":")[0].rstrip("/")):
                best = decl
    return best


def _component_source_for_surface(
    surface: _SurfaceDecl,
    *,
    routes: list[_RouteDecl],
    app_imports: dict[str, str],
    station_lens_imports: dict[str, str],
    station_lens_components: dict[str, str],
) -> dict[str, Any]:
    if surface.station_lens_eligible:
        component = station_lens_components.get(surface.id)
        if component:
            return {
                "component": component,
                "path": station_lens_imports.get(component, _repo_rel(SOURCE_STATION_LENS_TSX)),
                "host_component": "StationLens",
                "source": "StationLens.renderLens",
            }
    route_decl = _matching_route_decl(surface, routes)
    if route_decl is not None:
        component = route_decl.element.replace("Navigate:", "")
        return {
            "component": component,
            "path": app_imports.get(component, _repo_rel(SOURCE_APP_TSX)),
            "host_component": "App",
            "source": route_decl.evidence.to_json(),
        }
    return {
        "component": None,
        "path": None,
        "host_component": None,
        "source": surface.evidence.to_json(),
    }


def _source_text_for_rel_path(rel_path: str | None) -> str:
    if not rel_path:
        return ""
    path = REPO_ROOT / rel_path
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _extract_api_calls(source_text: str) -> list[str]:
    calls = {f"api{match.group(1)}" for match in _API_CALL_PATTERN.finditer(source_text)}
    calls.update(f"fetch:{match.group(1)}" for match in _FETCH_CALL_PATTERN.finditer(source_text))
    return sorted(calls)


def _extract_store_slices(source_text: str) -> list[str]:
    slices: list[str] = []
    if "useStation" in source_text:
        slices.append("useStation")
    if "useZenith" in source_text:
        slices.append("useZenith")
    return slices


def _extract_shared_components(source_text: str, source_path: str | None) -> list[str]:
    if not source_path:
        return []
    imports = _parse_all_component_imports(source_text, REPO_ROOT / source_path)
    out: list[str] = []
    for name, rel_path in imports.items():
        if "/components/" not in rel_path:
            continue
        if name in {"Fragment", "ReactNode"}:
            continue
        out.append(name)
    return sorted(dict.fromkeys(out))


def _derive_posture(surface: _SurfaceDecl, semantic_row: Mapping[str, Any] | None) -> str:
    route = surface.route or ""
    if "legacy" in route:
        return "legacy"
    if "workbench" in route:
        return "workbench"
    health = semantic_row.get("health") if isinstance(semantic_row, Mapping) else None
    if health == "live":
        return "canonical"
    if health == "degraded":
        return "workbench"
    if health == "placeholder":
        return "placeholder"
    if health == "authority_debt":
        return "experimental"
    if health == "broken":
        return "stale"
    return "uncaptured"


def _surface_relation_audit(
    *,
    surfaces: list[_SurfaceDecl],
    routes: list[_RouteDecl],
    captures: list[_CaptureRow],
    semantic_layer: dict[str, Any],
    component_index: dict[str, Any],
    app_text: str,
    station_lens_text: str,
) -> dict[str, Any]:
    app_imports = _parse_default_imports(app_text, SOURCE_APP_TSX)
    station_lens_imports = _parse_default_imports(station_lens_text, SOURCE_STATION_LENS_TSX)
    station_lens_components = _parse_lens_component_map(station_lens_text)
    semantic_by_id = {
        str(row.get("view_id")): row
        for row in (semantic_layer.get("views") or [])
        if isinstance(row, Mapping) and isinstance(row.get("view_id"), str)
    }
    component_meta = component_index.get("__meta") if isinstance(component_index.get("__meta"), dict) else {}

    rows: list[dict[str, Any]] = []
    for surface in surfaces:
        semantic_row = semantic_by_id.get(surface.id)
        component_source = _component_source_for_surface(
            surface,
            routes=routes,
            app_imports=app_imports,
            station_lens_imports=station_lens_imports,
            station_lens_components=station_lens_components,
        )
        component_path = component_source.get("path") if isinstance(component_source.get("path"), str) else None
        source_text = _source_text_for_rel_path(component_path)
        capture = _capture_for_surface(captures, surface)
        substrate_bindings = [
            "frontend_views",
            *(
                ["frontend_components"]
                if component_path and component_path != _repo_rel(SOURCE_APP_TSX)
                else []
            ),
            *(["station_lens"] if surface.station_lens_eligible else []),
        ]
        if isinstance(semantic_row, Mapping):
            substrate_bindings.extend(
                item
                for item in (semantic_row.get("related_paper_or_skill") or [])
                if isinstance(item, str)
            )
        evidence_refs = [
            f"{surface.evidence.file}:{surface.evidence.line}",
            *(f"{alias}:alias" for alias in surface.route_aliases),
        ]
        route_decl = _matching_route_decl(surface, routes)
        if route_decl:
            evidence_refs.append(f"{route_decl.evidence.file}:{route_decl.evidence.line}")
        if capture:
            evidence_refs.append(f"station_views:{capture.slug}")
        if component_path:
            evidence_refs.append(component_path)
        if isinstance(semantic_row, Mapping):
            evidence_refs.extend(
                item
                for item in (semantic_row.get("evidence_refs") or [])
                if isinstance(item, str)
            )

        rows.append(
            {
                "surface_id": surface.id,
                "route": surface.route,
                "entry_route": surface.entry_route or surface.route,
                "route_aliases": surface.route_aliases,
                "operator_job": surface.purpose,
                "group": surface.shell_group or surface.station_group or "utility",
                "posture": _derive_posture(surface, semantic_row),
                "primary_component": component_path,
                "primary_component_name": component_source.get("component"),
                "host_component": component_source.get("host_component"),
                "backend_endpoints": _extract_api_calls(source_text),
                "store_slices": _extract_store_slices(source_text),
                "shared_components": _extract_shared_components(source_text, component_path),
                "capture_slug": capture.slug if capture else None,
                "capture_status_basis": "station_views" if capture else "unbound",
                "substrate_bindings": sorted(dict.fromkeys(substrate_bindings)),
                "semantic_health": (
                    semantic_row.get("health")
                    if isinstance(semantic_row, Mapping) and isinstance(semantic_row.get("health"), str)
                    else "unknown"
                ),
                "semantic_summary": (
                    semantic_row.get("summary")
                    if isinstance(semantic_row, Mapping) and isinstance(semantic_row.get("summary"), str)
                    else None
                ),
                "evidence_refs": sorted(dict.fromkeys(evidence_refs)),
            }
        )

    return {
        "schema_version": SURFACE_RELATION_AUDIT_SCHEMA_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "source_evidence": {
            "app_router": _repo_rel(SOURCE_APP_TSX),
            "surface_registry": _repo_rel(SOURCE_SURFACES_TS),
            "station_lens": _repo_rel(SOURCE_STATION_LENS_TSX),
            "capture_manifest": _repo_rel(SOURCE_STATION_VIEWS_JSON),
            "semantic_layer": _repo_rel(SOURCE_SEMANTIC_LAYER_JSON),
            "component_index": _repo_rel(SOURCE_COMPONENT_INDEX_JSON),
        },
        "component_index_generated_at": component_meta.get("generated_at"),
        "relation_ontology": EDGE_MECHANISM_META,
        "surfaces": rows,
        "clusters": _build_relation_clusters(rows),
    }


def _build_relation_clusters(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    def _cluster(field: str, *, max_items: int = 12) -> list[dict[str, Any]]:
        buckets: dict[str, list[str]] = {}
        for row in rows:
            values = row.get(field)
            if isinstance(values, str):
                values = [values]
            if not isinstance(values, list):
                continue
            for value in values:
                if not isinstance(value, str) or not value:
                    continue
                buckets.setdefault(value, []).append(str(row["surface_id"]))
        out = [
            {"value": value, "surface_ids": sorted(dict.fromkeys(ids)), "count": len(set(ids))}
            for value, ids in buckets.items()
            if len(set(ids)) > 1
        ]
        return sorted(out, key=lambda row: (-int(row["count"]), str(row["value"])))[:max_items]

    return {
        "primary_component": _cluster("primary_component"),
        "backend_endpoints": _cluster("backend_endpoints"),
        "shared_components": _cluster("shared_components"),
        "store_slices": _cluster("store_slices"),
        "substrate_bindings": _cluster("substrate_bindings"),
    }


def _capture_load_timing(
    capture: _CaptureRow | None,
    load_index: dict[str, Any],
) -> dict[str, Any] | None:
    if capture is None:
        return None
    rows = load_index.get("views") if isinstance(load_index.get("views"), dict) else {}
    row = rows.get(capture.slug) if isinstance(rows, dict) else None
    if not isinstance(row, dict):
        return None
    latest = row.get("latest") if isinstance(row.get("latest"), dict) else {}
    return {
        "sample_count": _maybe_int(row.get("sample_count")),
        "captured_sample_count": _maybe_int(row.get("captured_sample_count")),
        "latest_status": (
            latest.get("status")
            if isinstance(latest.get("status"), str)
            else row.get("latest_status")
        ),
        "latest_attempt_status": row.get("latest_attempt_status")
        if isinstance(row.get("latest_attempt_status"), str)
        else None,
        "latest_promoted_status": row.get("latest_promoted_status")
        if isinstance(row.get("latest_promoted_status"), str)
        else None,
        "latest_environment_status": row.get("latest_environment_status")
        if isinstance(row.get("latest_environment_status"), str)
        else None,
        "latest_required_engine_coverage": row.get("latest_required_engine_coverage")
        if isinstance(row.get("latest_required_engine_coverage"), Mapping)
        else None,
        "latest_capture_mode": (
            latest.get("capture_mode")
            if isinstance(latest.get("capture_mode"), str)
            else row.get("latest_capture_mode")
        ),
        "latest_full_page": (
            latest.get("full_page")
            if isinstance(latest.get("full_page"), bool)
            else row.get("latest_full_page")
        ),
        "latest_page_height": _maybe_int(
            latest.get("page_height")
            if latest.get("page_height") is not None
            else row.get("latest_page_height")
        ),
        "latest_segment_count": _maybe_int(
            latest.get("segment_count")
            if latest.get("segment_count") is not None
            else row.get("latest_segment_count")
        ),
        "latest_segment_height": _maybe_int(
            latest.get("segment_height")
            if latest.get("segment_height") is not None
            else row.get("latest_segment_height")
        ),
        "latest_segment_overlap_px": _maybe_int(
            latest.get("segment_overlap_px")
            if latest.get("segment_overlap_px") is not None
            else row.get("latest_segment_overlap_px")
        ),
        "latest_segment_manifest_path": (
            latest.get("segment_manifest_path")
            if isinstance(latest.get("segment_manifest_path"), str)
            else row.get("latest_segment_manifest_path")
        ),
        "latest_load_ms": _maybe_int(row.get("latest_load_ms")),
        "latest_ready_ms": _maybe_int(row.get("latest_ready_ms")),
        "latest_run_stamp": (
            latest.get("run_stamp")
            if isinstance(latest.get("run_stamp"), str)
            else row.get("latest_run_stamp")
        ),
        "latest_engine": (
            latest.get("engine")
            if isinstance(latest.get("engine"), str)
            else row.get("latest_engine")
        ),
        "latest_viewport_slug": (
            latest.get("viewport_slug")
            if isinstance(latest.get("viewport_slug"), str)
            else row.get("latest_viewport_slug")
        ),
        "latest_output_path": (
            latest.get("output_path")
            if isinstance(latest.get("output_path"), str)
            else row.get("latest_output_path")
        ),
        "latest_preload_output_path": (
            latest.get("preload_output_path")
            if isinstance(latest.get("preload_output_path"), str)
            else row.get("latest_preload_output_path")
        ),
        "p50_load_ms": _maybe_int(row.get("p50_load_ms")),
        "p95_load_ms": _maybe_int(row.get("p95_load_ms")),
        "min_load_ms": _maybe_int(row.get("min_load_ms")),
        "max_load_ms": _maybe_int(row.get("max_load_ms")),
        "avg_load_ms": _maybe_int(row.get("avg_load_ms")),
    }


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------


def _route_matches(surface_route: str, candidate_route: str) -> bool:
    if surface_route == candidate_route:
        return True
    return candidate_route.startswith(surface_route + "/")


def _surface_route_claims(surface: _SurfaceDecl) -> list[str]:
    return [surface.route, *surface.route_aliases]


def _surface_claims_route(surface: _SurfaceDecl, route: str) -> bool:
    return any(_route_matches(claim, route) for claim in _surface_route_claims(surface) if claim)


def _surface_for_route(
    surfaces: list[_SurfaceDecl], route: str
) -> _SurfaceDecl | None:
    # Prefer the longest matching registered route.
    best: _SurfaceDecl | None = None
    for s in surfaces:
        if _surface_claims_route(s, route):
            s_len = max((len(claim) for claim in _surface_route_claims(s)), default=0)
            best_len = (
                max((len(claim) for claim in _surface_route_claims(best)), default=0)
                if best is not None
                else 0
            )
            if best is None or s_len > best_len:
                best = s
    return best


def _capture_for_surface(
    captures: list[_CaptureRow], surface: _SurfaceDecl
) -> _CaptureRow | None:
    if surface.capture_slug:
        for row in captures:
            if row.slug == surface.capture_slug:
                return row
    candidate_routes = [surface.entry_route, *_surface_route_claims(surface)]
    # Fallback: exact route match.
    for row in captures:
        if any(route and row.route == route for route in candidate_routes):
            return row
    # Fallback: prefix match (first one wins).
    for row in captures:
        if any(route and row.route.startswith(route) for route in candidate_routes):
            return row
    return None


def _resolve_entry_route(surface: _SurfaceDecl, routes: list[_RouteDecl]) -> str | None:
    if surface.entry_route:
        return surface.entry_route
    route_paths = {r.path for r in routes}
    if surface.route in route_paths:
        return surface.route
    return None


def _edge(
    source: str,
    target: str,
    mechanism: str,
    *,
    group: str | None = None,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    meta = EDGE_MECHANISM_META.get(mechanism, EDGE_MECHANISM_META["unknown"])
    edge: dict[str, Any] = {
        "from": source,
        "to": target,
        "mechanism": mechanism,
        "label": meta["label"],
        "category": meta["category"],
        "description": meta["description"],
        "presentation_role": meta.get("presentation_role", "fallback"),
        "rank": meta["rank"],
        "weight": meta["weight"],
    }
    if group:
        edge["group"] = group
    if evidence_refs:
        edge["evidence_refs"] = sorted(dict.fromkeys(evidence_refs))
    return edge


def _edge_rank(edge: Mapping[str, Any]) -> int:
    rank = edge.get("rank")
    if isinstance(rank, int):
        return rank
    mechanism = edge.get("mechanism")
    if isinstance(mechanism, str):
        return int(EDGE_MECHANISM_META.get(mechanism, EDGE_MECHANISM_META["unknown"])["rank"])
    return int(EDGE_MECHANISM_META["unknown"]["rank"])


def _semantic_relation_edges(
    surfaces: list[_SurfaceDecl],
    surface_relation_audit: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    by_id = {s.id: s for s in surfaces}

    # Parent route relation: /station owns the route family, but each child
    # route keeps its own surface identity. This replaces broad same-group
    # labels for Station children when inspecting the home map.
    if "station" in by_id:
        for surface in surfaces:
            if surface.id == "station" or not surface.route.startswith("/station/"):
                continue
            edges.append(
                _edge(
                    "station",
                    surface.id,
                    "route_hierarchy",
                    group="/station",
                    evidence_refs=[
                        f"{by_id['station'].evidence.file}:{by_id['station'].evidence.line}",
                        f"{surface.evidence.file}:{surface.evidence.line}",
                    ],
                )
            )

    for surface in surfaces:
        if surface.id == "station" or "station" not in by_id:
            continue
        if "workbench" in surface.route or "legacy" in surface.route:
            edges.append(
                _edge(
                    surface.id,
                    "station",
                    "legacy_or_workbench_of",
                    group="workbench" if "workbench" in surface.route else "legacy",
                    evidence_refs=[
                        f"{surface.evidence.file}:{surface.evidence.line}",
                        f"{by_id['station'].evidence.file}:{by_id['station'].evidence.line}",
                    ],
                )
            )

    if not isinstance(surface_relation_audit, dict):
        return edges
    rows = {
        str(row.get("surface_id")): row
        for row in surface_relation_audit.get("surfaces", [])
        if isinstance(row, Mapping) and isinstance(row.get("surface_id"), str)
    }

    def _add_cluster_edges(
        field: str,
        mechanism: str,
        *,
        max_cluster_size: int,
        ignore_values: set[str] | None = None,
    ) -> None:
        ignore = ignore_values or set()
        buckets: dict[str, list[str]] = {}
        for surface_id, row in rows.items():
            values = row.get(field)
            if isinstance(values, str):
                values = [values]
            if not isinstance(values, list):
                continue
            for value in values:
                if not isinstance(value, str) or not value or value in ignore:
                    continue
                buckets.setdefault(value, []).append(surface_id)
        for value, members in buckets.items():
            unique = sorted(dict.fromkeys(members))
            if len(unique) < 2 or len(unique) > max_cluster_size:
                continue
            for source in unique:
                for target in unique:
                    if source == target:
                        continue
                    edges.append(
                        _edge(
                            source,
                            target,
                            mechanism,
                            group=value,
                            evidence_refs=[
                                *rows.get(source, {}).get("evidence_refs", [])[:4],
                                *rows.get(target, {}).get("evidence_refs", [])[:4],
                            ],
                        )
                    )

    _add_cluster_edges(
        "primary_component",
        "shared_component",
        max_cluster_size=4,
        ignore_values={_repo_rel(SOURCE_STATION_LENS_TSX), _repo_rel(SOURCE_APP_TSX)},
    )
    # Caps raised 3->10 / 4->10 to fix operator complaint that hover on most
    # views shows nothing on the canvas. Before: shared_components cap=3 and
    # backend_endpoints cap=4 dropped every meaningful shared resource
    # (Exoskeleton x24, FreshnessBadge x9, api.worldModel x9, ...), leaving
    # 13 views with zero pathway edges. Higher caps surface those clusters
    # as pathway edges; in 'clean' mode they only paint on hover so the
    # rest canvas stays uncluttered. Exoskeleton is the universal app shell
    # -- sharing it is meaningless ("they both render inside the app") --
    # so it's filtered out the same way SOURCE_APP_TSX is for primary_component.
    _add_cluster_edges(
        "shared_components",
        "shared_component",
        max_cluster_size=10,
        ignore_values={"Exoskeleton"},
    )
    _add_cluster_edges(
        "backend_endpoints",
        "shared_backend_api",
        max_cluster_size=10,
    )
    return edges


def _derive_edges(
    surfaces: list[_SurfaceDecl],
    lens_prefix_to_id: dict[str, str],
    surface_relation_audit: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build the edge list from four authority tiers, annotated by mechanism."""
    edges: list[dict[str, Any]] = []
    by_id = {s.id: s for s in surfaces}

    edges.extend(_semantic_relation_edges(surfaces, surface_relation_audit))

    # 1. Explicit outboundTo (highest authority)
    for s in surfaces:
        for target in s.outbound_to:
            if target in by_id:
                edges.append(_edge(s.id, target, "explicit"))

    # 2. Shell-group siblings (the navigation menu bar makes these reachable)
    by_shell: dict[str, list[str]] = {}
    for s in surfaces:
        if s.shell_group:
            by_shell.setdefault(s.shell_group, []).append(s.id)
    for group_id, members in by_shell.items():
        for source in members:
            for target in members:
                if source != target:
                    edges.append(_edge(source, target, "shell_group", group=group_id))

    # 3. Station-group siblings (inside /station/ lens shell)
    by_station: dict[str, list[str]] = {}
    for s in surfaces:
        if s.station_group:
            by_station.setdefault(s.station_group, []).append(s.id)
    for group_id, members in by_station.items():
        for source in members:
            for target in members:
                if source != target:
                    edges.append(_edge(source, target, "station_group", group=group_id))

    # 4. StationLens sub-siblings (all station_lens_eligible surfaces can jump to each other)
    lens_members = [s.id for s in surfaces if s.station_lens_eligible]
    for source in lens_members:
        for target in lens_members:
            if source != target:
                edges.append(_edge(source, target, "station_lens_menu"))

    # 5. Overlays: overlay surfaces get an edge FROM their overlayOf parent.
    for s in surfaces:
        if s.overlay_of and s.overlay_of in by_id:
            edges.append(_edge(s.overlay_of, s.id, "overlay_anchor"))

    # Dedupe: keep the strongest-authority mechanism per (from,to) pair.
    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for e in edges:
        key = (e["from"], e["to"])
        existing = dedup.get(key)
        if existing is None or _edge_rank(e) < _edge_rank(existing):
            dedup[key] = e
    return sorted(
        dedup.values(),
        key=lambda edge: (edge["from"], edge["to"]),
    )


def _pathway_audit(
    surfaces: list[_SurfaceDecl],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    pathway_edges = [
        edge for edge in edges if edge.get("presentation_role") == PATHWAY_PRESENTATION_ROLE
    ]
    pathway_out: Counter[str] = Counter()
    pathway_in: Counter[str] = Counter()
    explicit_count = 0
    derived_count = 0

    for edge in pathway_edges:
        source = str(edge.get("from") or "")
        target = str(edge.get("to") or "")
        if source:
            pathway_out[source] += 1
        if target:
            pathway_in[target] += 1
        if edge.get("mechanism") in EXPLICIT_PATHWAY_MECHANISMS:
            explicit_count += 1
        else:
            derived_count += 1

    per_view: list[dict[str, Any]] = []
    zero_pathway_views: list[dict[str, Any]] = []
    zero_substantive: list[dict[str, Any]] = []
    allowed_zero: list[dict[str, Any]] = []

    for surface in surfaces:
        inbound = int(pathway_in.get(surface.id, 0))
        outbound = int(pathway_out.get(surface.id, 0))
        total = inbound + outbound
        is_substantive = surface.kind == "page" and bool(surface.route)
        is_allowed_zero = surface.id in ALLOWED_ZERO_PATHWAY_VIEW_IDS
        row = {
            "id": surface.id,
            "label": surface.label,
            "kind": surface.kind,
            "route": surface.route or None,
            "pathway_count": total,
            "pathway_fanout_count": outbound,
            "pathway_fanin_count": inbound,
            "substantive_routable": is_substantive,
            "allowed_zero": is_allowed_zero,
            "evidence": surface.evidence.to_json(),
        }
        if total == 0:
            zero_pathway_views.append(row)
            if is_allowed_zero:
                allowed_zero.append(row)
            elif is_substantive:
                zero_substantive.append(row)
        per_view.append(row)

    return {
        "contract": "frontend_navigation_pathway_hover_contract_v1",
        "status": "ok" if not zero_substantive else "drift",
        "presentation_role": PATHWAY_PRESENTATION_ROLE,
        "pathway_edge_count": len(pathway_edges),
        "explicit_pathway_count": explicit_count,
        "derived_pathway_count": derived_count,
        "zero_pathway_view_count": len(zero_pathway_views),
        "zero_substantive_pathway_view_count": len(zero_substantive),
        "allowed_zero_pathway_view_count": len(allowed_zero),
        "allowed_zero_pathway_view_ids": sorted(ALLOWED_ZERO_PATHWAY_VIEW_IDS),
        "zero_pathway_views": zero_pathway_views,
        "zero_substantive_pathway_views": zero_substantive,
        "allowed_zero_pathway_views": allowed_zero,
        "per_view": sorted(per_view, key=lambda row: str(row["id"])),
    }


def _compute_drift(
    routes: list[_RouteDecl],
    surfaces: list[_SurfaceDecl],
    captures: list[_CaptureRow],
    edges: list[dict[str, Any]],
    pathway_audit: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []

    # Routes declared in App.tsx but no surface claims them (ignore pure Navigate redirects).
    for r in routes:
        if r.element.startswith("Navigate:"):
            continue
        if r.path == "*":  # catch-all, no surface mapping needed
            continue
        if r.path.endswith(":mission") or ":" in r.path:
            # Parameterised routes — check by prefix.
            bare = r.path.split(":")[0].rstrip("/")
            matched = any(_surface_claims_route(s, bare) for s in surfaces)
        else:
            matched = any(_surface_claims_route(s, r.path) for s in surfaces)
        if not matched:
            signals.append(
                {
                    "kind": "route_without_surface",
                    "route": r.path,
                    "element": r.element,
                    "evidence": r.evidence.to_json(),
                }
            )

    # Surfaces declared but no route in App.tsx hosts them.
    route_paths = {r.path for r in routes if not r.element.startswith("Navigate:")}
    for s in surfaces:
        if s.kind in ("overlay", "modal", "drawer"):
            continue  # overlays don't need a top-level route
        if not s.route:
            signals.append(
                {
                    "kind": "surface_without_route",
                    "surface": s.id,
                    "evidence": s.evidence.to_json(),
                }
            )
            continue
        host_match = any(
            claim in route_paths
            or any(claim.startswith(path.rstrip("*/").rstrip("/") + "/") for path in route_paths)
            or any(path.startswith(claim + "/") or path == claim for path in route_paths)
            for claim in _surface_route_claims(s)
            if claim
        )
        if not host_match:
            signals.append(
                {
                    "kind": "surface_without_route",
                    "surface": s.id,
                    "declared_route": s.route,
                    "evidence": s.evidence.to_json(),
                }
            )

    # Capture rows whose route is not claimed by any surface.
    for row in captures:
        if not any(
            _surface_claims_route(s, row.route.split("?")[0])
            for s in surfaces
        ):
            signals.append(
                {
                    "kind": "capture_without_surface",
                    "slug": row.slug,
                    "route": row.route,
                    "evidence": row.evidence.to_json(),
                }
            )

    # Surfaces whose declared captureSlug doesn't match any capture row.
    capture_slugs = {row.slug for row in captures}
    for s in surfaces:
        if s.capture_slug and s.capture_slug not in capture_slugs:
            signals.append(
                {
                    "kind": "surface_capture_slug_missing",
                    "surface": s.id,
                    "capture_slug": s.capture_slug,
                    "evidence": s.evidence.to_json(),
                }
            )

    # Undeclared cul-de-sacs: zero outbound edges AND no isCulDeSac reason.
    outbound_by_id: dict[str, int] = {}
    for e in edges:
        outbound_by_id[e["from"]] = outbound_by_id.get(e["from"], 0) + 1
    for s in surfaces:
        if outbound_by_id.get(s.id, 0) == 0 and not s.is_cul_de_sac and s.kind == "page":
            signals.append(
                {
                    "kind": "undeclared_cul_de_sac",
                    "surface": s.id,
                    "evidence": s.evidence.to_json(),
                }
            )

    # Hover-edge contract: every substantive routable page should have at
    # least one real pathway edge, not just folded membership edges. Global
    # overlays/drawers can be intentional zero-pathway surfaces only when
    # whitelisted in ALLOWED_ZERO_PATHWAY_VIEW_IDS.
    if isinstance(pathway_audit, Mapping):
        for row in pathway_audit.get("zero_substantive_pathway_views", []):
            if not isinstance(row, Mapping):
                continue
            signals.append(
                {
                    "kind": "zero_pathway_view",
                    "surface": row.get("id"),
                    "label": row.get("label"),
                    "pathway_count": row.get("pathway_count"),
                    "contract": pathway_audit.get("contract"),
                    "evidence": row.get("evidence"),
                }
            )

    return signals


def _view_evidence_ref(view: Mapping[str, Any]) -> str | None:
    evidence = view.get("evidence")
    if not isinstance(evidence, Mapping):
        return None
    file_ref = evidence.get("file")
    line = evidence.get("line")
    if not isinstance(file_ref, str) or not file_ref:
        return None
    if isinstance(line, int):
        return f"{file_ref}:{line}"
    return file_ref


def _capture_dict(view: Mapping[str, Any]) -> Mapping[str, Any]:
    capture = view.get("capture")
    return capture if isinstance(capture, Mapping) else {}


def _entry_action_kind(view: Mapping[str, Any]) -> str:
    kind = str(view.get("kind") or "")
    view_id = str(view.get("id") or "")
    if view_id == "command_palette":
        return "command_palette_select"
    if kind in {"drawer"}:
        return "drawer_open"
    if kind in {"overlay", "modal"}:
        return "overlay_open"
    route = view.get("route")
    entry_route = view.get("entry_route")
    if isinstance(entry_route, str) and entry_route and entry_route != route:
        return "open_entry_route"
    if isinstance(entry_route, str) and entry_route:
        return "open_route"
    return "external_or_unavailable"


def _entry_affordance_for_view(view: Mapping[str, Any]) -> dict[str, Any]:
    entry_route = view.get("entry_route")
    route = view.get("route")
    capture = _capture_dict(view)
    ready_selector = capture.get("ready_selector")
    capture_slug = capture.get("slug")
    evidence_refs = [ref for ref in [_view_evidence_ref(view)] if ref]
    action_kind = _entry_action_kind(view)

    if isinstance(entry_route, str) and entry_route:
        proof_status = (
            "station_render_ready"
            if isinstance(capture_slug, str) and capture_slug and isinstance(ready_selector, str) and ready_selector
            else "capture_contract_missing"
        )
        return {
            "status": "ready",
            "action_kind": action_kind,
            "entry_route": entry_route,
            "route": route,
            "ready_selector": ready_selector if isinstance(ready_selector, str) else None,
            "capture_slug": capture_slug if isinstance(capture_slug, str) else None,
            "safety_class": "read_only_navigation",
            "proof_status": proof_status,
            "evidence_refs": evidence_refs,
        }

    unavailable_reason = "selector_contract_missing"
    if action_kind == "external_or_unavailable":
        unavailable_reason = "entry_route_missing"
    return {
        "status": "unavailable",
        "action_kind": action_kind,
        "entry_route": None,
        "route": route,
        "ready_selector": ready_selector if isinstance(ready_selector, str) else None,
        "capture_slug": capture_slug if isinstance(capture_slug, str) else None,
        "safety_class": "read_only_navigation",
        "proof_status": "unavailable",
        "unavailable_reason": unavailable_reason,
        "evidence_refs": evidence_refs,
    }


def _frontend_validation_route_class(view: Mapping[str, Any]) -> str:
    kind = str(view.get("kind") or "")
    capture = _capture_dict(view)
    capture_slug = capture.get("slug")
    ready_selector = capture.get("ready_selector")
    if kind in {"modal", "drawer", "overlay"}:
        return "transient_surface"
    if kind == "redirect":
        return "redirect"
    if kind == "page":
        if isinstance(capture_slug, str) and capture_slug and isinstance(ready_selector, str) and ready_selector:
            return "captured_page"
        return "uncaptured_page"
    return "unclassified_surface"


def _station_render_visual_command(capture_slug: str) -> str:
    return (
        "./repo-python tools/meta/observability/station_render.py render "
        f"--view {capture_slug} --engine chromium --viewport fhd_landscape "
        "--host-pressure-policy warn"
    )


def _frontend_validation_evidence_refs(view: Mapping[str, Any]) -> list[str]:
    refs = [ref for ref in [_view_evidence_ref(view)] if ref]
    audit = view.get("surface_audit")
    if isinstance(audit, Mapping):
        refs.extend(
            str(ref)
            for ref in audit.get("evidence_refs", [])
            if isinstance(ref, str) and ref
        )
    return sorted(dict.fromkeys(refs))


def _browser_visual_requirement_for_view(
    view: Mapping[str, Any],
    route_class: str,
) -> dict[str, Any]:
    capture = _capture_dict(view)
    capture_slug = capture.get("slug")
    ready_selector = capture.get("ready_selector")
    view_id = view.get("id")
    if route_class == "captured_page":
        return {
            "status": "required",
            "lane": "browser_visual_smoke",
            "proof": "station_render_capture",
            "capture_slug": capture_slug,
            "ready_selector": ready_selector,
            "command": _station_render_visual_command(str(capture_slug)),
            "evidence_refs": _frontend_validation_evidence_refs(view),
        }
    if route_class == "uncaptured_page":
        return {
            "status": "blocked_missing_capture_contract",
            "lane": "capture_contract_repair",
            "proof": "station_render_capture",
            "missing": ["capture.slug", "capture.ready_selector"],
            "next_actuator": (
                "Add a station_views.json capture row and bind it from surfaces.ts captureSlug "
                "before browser screenshot signoff."
            ),
            "evidence_refs": _frontend_validation_evidence_refs(view),
        }
    if route_class == "transient_surface":
        invocation = view.get("invocation") if isinstance(view.get("invocation"), Mapping) else {}
        expected = invocation.get("expected") if isinstance(invocation.get("expected"), Mapping) else {}
        source_view_id = invocation.get("source_view_id") if isinstance(invocation, Mapping) else None
        ready_selector = expected.get("ready_selector") if isinstance(expected, Mapping) else None
        status = (
            "required_source_backed_invocation"
            if isinstance(ready_selector, str) and ready_selector
            else "blocked_missing_invocation_contract"
        )
        return {
            "status": status,
            "lane": "source_backed_invocation_harness",
            "proof": "source_backed_action_replay",
            "target_view_id": view_id,
            "source_view_id": source_view_id,
            "ready_selector": ready_selector if isinstance(ready_selector, str) else None,
            "direct_route_capture_authoritative": False,
            "command_template": FRONTEND_VALIDATION_LANES["source_backed_invocation_harness"][
                "command_template"
            ],
            "evidence_refs": _frontend_validation_evidence_refs(view),
        }
    if route_class == "redirect":
        return {
            "status": "not_applicable_redirect",
            "lane": "runtime_url_vitest",
            "proof": "resolved_target_route",
            "direct_route_capture_authoritative": False,
            "evidence_refs": _frontend_validation_evidence_refs(view),
        }
    return {
        "status": "manual_contract_required",
        "lane": "safe_cleanup_pytest",
        "proof": "unknown",
        "direct_route_capture_authoritative": False,
        "evidence_refs": _frontend_validation_evidence_refs(view),
    }


def _frontend_validation_contract_for_view(view: Mapping[str, Any]) -> dict[str, Any]:
    route_class = _frontend_validation_route_class(view)
    route_class_def = FRONTEND_VALIDATION_ROUTE_CLASSES[route_class]
    required_lanes = list(route_class_def["required_lanes"])
    browser_visual_requirement = _browser_visual_requirement_for_view(view, route_class)
    return {
        "schema": FRONTEND_VALIDATION_MATRIX_SCHEMA,
        "route_class": route_class,
        "route_class_definition": route_class_def["description"],
        "required_lanes": required_lanes,
        "browser_visual_requirement": browser_visual_requirement,
        "acceptance_command_refs": [row["id"] for row in FRONTEND_VALIDATION_ACCEPTANCE_COMMANDS],
        "lane_authorities": {
            lane: FRONTEND_VALIDATION_LANES[lane]["authority"]
            for lane in required_lanes
            if lane in FRONTEND_VALIDATION_LANES
        },
        "matrix_source": "state/frontend_navigation/navigation_graph.json::validation_matrix",
        "evidence_refs": _frontend_validation_evidence_refs(view),
    }


def _build_frontend_validation_matrix(views: list[dict[str, Any]]) -> dict[str, Any]:
    route_class_counts = Counter(
        str((view.get("validation_contract") or {}).get("route_class") or "missing")
        for view in views
    )
    browser_status_counts = Counter(
        str(
            ((view.get("validation_contract") or {}).get("browser_visual_requirement") or {}).get("status")
            or "missing"
        )
        for view in views
    )
    return {
        "schema": FRONTEND_VALIDATION_MATRIX_SCHEMA,
        "source": "tools/meta/observability/frontend_nav_graph.py",
        "authority_posture": "generated_projection_not_source_authority",
        "lanes": FRONTEND_VALIDATION_LANES,
        "route_classes": FRONTEND_VALIDATION_ROUTE_CLASSES,
        "acceptance_commands": FRONTEND_VALIDATION_ACCEPTANCE_COMMANDS,
        "route_class_counts": dict(sorted(route_class_counts.items())),
        "browser_visual_requirement_status_counts": dict(sorted(browser_status_counts.items())),
        "visual_smoke_lane": "browser_visual_smoke",
        "workitem": "cap_frontend_test_matrix_browser_harness_contract",
    }


def attach_frontend_validation_contracts(graph: dict[str, Any]) -> dict[str, Any]:
    views = [view for view in graph.get("views", []) if isinstance(view, dict)]
    for view in views:
        view["validation_contract"] = _frontend_validation_contract_for_view(view)
    validation_matrix = _build_frontend_validation_matrix(views)
    graph["frontend_validation_matrix_schema"] = FRONTEND_VALIDATION_MATRIX_SCHEMA
    graph["validation_matrix"] = validation_matrix
    return graph


def _edge_action_kind(edge: Mapping[str, Any], target_view: Mapping[str, Any]) -> str:
    target_kind = str(target_view.get("kind") or "")
    target_id = str(target_view.get("id") or "")
    mechanism = str(edge.get("mechanism") or "")
    if target_id == "command_palette":
        return "command_palette_select"
    if target_kind == "drawer":
        return "drawer_open"
    if mechanism == "overlay_anchor" or target_kind in {"overlay", "modal"}:
        return "overlay_open"
    if (
        mechanism in {"station_lens_menu", "station_group"}
        and bool(target_view.get("station_lens_eligible"))
    ):
        return "station_lens_switch"
    entry_route = target_view.get("entry_route")
    route = target_view.get("route")
    if isinstance(entry_route, str) and entry_route and entry_route != route:
        return "open_entry_route"
    if isinstance(entry_route, str) and entry_route:
        return "open_route"
    return "external_or_unavailable"


def _navigation_affordance_for_edge(
    edge: Mapping[str, Any],
    views_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    target_view = views_by_id.get(str(edge.get("to") or ""))
    source_view = views_by_id.get(str(edge.get("from") or ""))
    edge_evidence = edge.get("evidence_refs") if isinstance(edge.get("evidence_refs"), list) else []
    evidence_refs = [str(ref) for ref in edge_evidence if isinstance(ref, str)]
    if source_view:
        source_ref = _view_evidence_ref(source_view)
        if source_ref:
            evidence_refs.append(source_ref)
    if target_view:
        target_ref = _view_evidence_ref(target_view)
        if target_ref:
            evidence_refs.append(target_ref)
    evidence_refs = sorted(dict.fromkeys(evidence_refs))

    if not target_view:
        return {
            "status": "unavailable",
            "action_kind": "external_or_unavailable",
            "safety_class": "read_only_navigation",
            "proof_status": "unavailable",
            "unavailable_reason": "target_view_missing",
            "evidence_refs": evidence_refs,
        }

    target_entry = target_view.get("entry_affordance")
    if not isinstance(target_entry, Mapping):
        target_entry = _entry_affordance_for_view(target_view)
    action_kind = _edge_action_kind(edge, target_view)
    entry_route = target_entry.get("entry_route")
    ready_selector = target_entry.get("ready_selector")
    capture_slug = target_entry.get("capture_slug")
    status = "ready" if isinstance(entry_route, str) and entry_route else "unavailable"
    proof_status = (
        "station_render_ready"
        if status == "ready" and isinstance(capture_slug, str) and capture_slug and isinstance(ready_selector, str) and ready_selector
        else ("capture_contract_missing" if status == "ready" else "unavailable")
    )
    affordance: dict[str, Any] = {
        "status": status,
        "action_kind": action_kind,
        "entry_route": entry_route if isinstance(entry_route, str) else None,
        "target_view_id": target_view.get("id"),
        "ready_selector": ready_selector if isinstance(ready_selector, str) else None,
        "capture_slug": capture_slug if isinstance(capture_slug, str) else None,
        "safety_class": "read_only_navigation",
        "proof_status": proof_status,
        "evidence_refs": evidence_refs,
    }
    if status != "ready":
        affordance["unavailable_reason"] = (
            "selector_contract_missing"
            if action_kind in {"command_palette_select", "overlay_open", "drawer_open"}
            else "entry_route_missing"
        )
    return affordance


def _edge_evidence_refs(
    edge: Mapping[str, Any],
    views_by_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    evidence_refs = [
        str(ref)
        for ref in edge.get("evidence_refs", [])
        if isinstance(ref, str)
    ] if isinstance(edge.get("evidence_refs"), list) else []
    for view_id in (edge.get("from"), edge.get("to")):
        if not isinstance(view_id, str):
            continue
        view_ref = _view_evidence_ref(views_by_id.get(view_id, {}))
        if view_ref:
            evidence_refs.append(view_ref)
    return sorted(dict.fromkeys(evidence_refs))


def _invocation_affordance_for_edge(
    edge: Mapping[str, Any],
    views_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    target_view = views_by_id.get(str(edge.get("to") or ""))
    source_view = views_by_id.get(str(edge.get("from") or ""))
    evidence_refs = _edge_evidence_refs(edge, views_by_id)
    if not target_view:
        return {
            "contract": INVOCATION_CONTRACT,
            "status": "unavailable",
            "action_kind": "external_or_unavailable",
            "proof_status": "unavailable",
            "unavailable_reason": "target_view_missing",
            "evidence_refs": evidence_refs,
        }

    action_kind = _edge_action_kind(edge, target_view)
    if action_kind in {"open_route", "open_entry_route", "station_lens_switch"}:
        return {
            "contract": INVOCATION_CONTRACT,
            "status": "not_applicable",
            "action_kind": action_kind,
            "proof_status": "entry_affordance_owned",
            "unavailable_reason": "route_entry_affordance",
            "evidence_refs": evidence_refs,
        }

    invocation = target_view.get("invocation")
    if not isinstance(invocation, Mapping):
        return {
            "contract": INVOCATION_CONTRACT,
            "status": "unavailable",
            "action_kind": action_kind,
            "target_view_id": target_view.get("id"),
            "source_view_id": source_view.get("id") if isinstance(source_view, Mapping) else edge.get("from"),
            "proof_status": "unavailable",
            "unavailable_reason": "selector_contract_missing",
            "evidence_refs": evidence_refs,
        }

    trigger = invocation.get("trigger") if isinstance(invocation.get("trigger"), Mapping) else {}
    expected = invocation.get("expected") if isinstance(invocation.get("expected"), Mapping) else {}
    ready_selector = expected.get("ready_selector") if isinstance(expected, Mapping) else None
    status = "ready" if isinstance(ready_selector, str) and ready_selector else "unavailable"
    payload: dict[str, Any] = {
        "contract": INVOCATION_CONTRACT,
        "status": status,
        "action_id": invocation.get("action_id"),
        "action_kind": invocation.get("action_kind") or action_kind,
        "target_view_id": target_view.get("id"),
        "source_view_id": source_view.get("id") if isinstance(source_view, Mapping) else edge.get("from"),
        "trigger": trigger,
        "expected": expected,
        "safety_class": invocation.get("safety_class") or "transient_ui_open",
        "selector_contract_source": "source",
        "proof_status": "source_backed_replay_ready" if status == "ready" else "unavailable",
        "evidence_refs": evidence_refs,
    }
    if status != "ready":
        payload["unavailable_reason"] = "target_ready_selector_missing"
    return payload


def attach_wayfinding_affordances(graph: dict[str, Any]) -> dict[str, Any]:
    """Attach source-derived executable navigation affordances to views and edges."""
    views = [view for view in graph.get("views", []) if isinstance(view, dict)]
    for view in views:
        view["entry_affordance"] = _entry_affordance_for_view(view)

    views_by_id: dict[str, Mapping[str, Any]] = {
        str(view.get("id")): view
        for view in views
        if isinstance(view.get("id"), str)
    }
    ready_edges = 0
    proof_ready_edges = 0
    unavailable_edges = 0
    ready_invocation_edges = 0
    unavailable_invocation_edges = 0
    not_applicable_invocation_edges = 0
    unavailable_action_kinds: Counter[str] = Counter()
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        affordance = _navigation_affordance_for_edge(edge, views_by_id)
        edge["navigation_affordance"] = affordance
        invocation_affordance = _invocation_affordance_for_edge(edge, views_by_id)
        edge["invocation_affordance"] = invocation_affordance
        if affordance.get("status") == "ready":
            ready_edges += 1
            if affordance.get("proof_status") == "station_render_ready":
                proof_ready_edges += 1
        else:
            unavailable_edges += 1
        invocation_status = invocation_affordance.get("status")
        if invocation_status == "ready":
            ready_invocation_edges += 1
        elif invocation_status == "unavailable":
            unavailable_invocation_edges += 1
            unavailable_action_kinds[str(invocation_affordance.get("action_kind") or "unknown")] += 1
        else:
            not_applicable_invocation_edges += 1

    ready_views = 0
    proof_ready_views = 0
    unavailable_views = 0
    for view in views:
        affordance = view.get("entry_affordance")
        if not isinstance(affordance, Mapping):
            continue
        if affordance.get("status") == "ready":
            ready_views += 1
            if affordance.get("proof_status") == "station_render_ready":
                proof_ready_views += 1
        else:
            unavailable_views += 1

    graph["wayfinding_contract"] = WAYFINDING_CONTRACT
    graph["invocation_contract"] = INVOCATION_CONTRACT
    graph["wayfinding"] = {
        "contract": WAYFINDING_CONTRACT,
        "planner": WAYFINDING_PLANNER,
        "invocation_contract": INVOCATION_CONTRACT,
        "action_kinds": WAYFINDING_ACTION_KINDS,
        "ready_view_count": ready_views,
        "proof_ready_view_count": proof_ready_views,
        "unavailable_view_count": unavailable_views,
        "ready_edge_count": ready_edges,
        "proof_ready_edge_count": proof_ready_edges,
        "unavailable_edge_count": unavailable_edges,
        "ready_invocation_edge_count": ready_invocation_edges,
        "unavailable_invocation_edge_count": unavailable_invocation_edges,
        "not_applicable_invocation_edge_count": not_applicable_invocation_edges,
        "unavailable_action_kinds": dict(sorted(unavailable_action_kinds.items())),
        "safety_class": "read_only_navigation",
    }
    return graph


def _resolve_view_query(graph: Mapping[str, Any], query: str) -> dict[str, Any]:
    token = str(query or "").strip()
    views = [view for view in graph.get("views", []) if isinstance(view, Mapping)]
    exact_sources = (
        ("view_id", lambda view: view.get("id") == token),
        ("route", lambda view: view.get("route") == token),
        ("entry_route", lambda view: view.get("entry_route") == token),
        ("route_alias", lambda view: token in (view.get("route_aliases") or [])),
    )
    for source, predicate in exact_sources:
        for view in views:
            if predicate(view):
                return {
                    "input": token,
                    "resolved_view_id": view.get("id"),
                    "source": source,
                    "label": view.get("label"),
                    "route": view.get("route"),
                    "entry_route": view.get("entry_route"),
                }

    lowered = token.lower()
    label_matches = [
        view
        for view in views
        if isinstance(view.get("label"), str) and str(view.get("label")).lower() == lowered
    ]
    if len(label_matches) == 1:
        view = label_matches[0]
        return {
            "input": token,
            "resolved_view_id": view.get("id"),
            "source": "label",
            "label": view.get("label"),
            "route": view.get("route"),
            "entry_route": view.get("entry_route"),
        }
    if len(label_matches) > 1:
        return {
            "input": token,
            "resolved_view_id": None,
            "source": "ambiguous_label",
            "candidates": [view.get("id") for view in label_matches],
        }
    return {"input": token, "resolved_view_id": None, "source": "unresolved"}


def _wayfinding_graph_hash(graph: Mapping[str, Any]) -> str:
    source_hashes = graph.get("source_hashes")
    stable_source_hashes = (
        {
            key: value
            for key, value in source_hashes.items()
            if key != "render_load_index"
        }
        if isinstance(source_hashes, Mapping)
        else None
    )
    counts = graph.get("counts")
    stable_counts = (
        {
            key: counts.get(key)
            for key in (
                "pages",
                "overlays",
                "edges",
                "cul_de_sacs_effective",
                "cul_de_sacs_declared",
                "routes_declared",
                "redirects",
                "capture_rows",
                "drift_signals",
            )
            if key in counts
        }
        if isinstance(counts, Mapping)
        else None
    )
    payload = {
        "schema_version": graph.get("schema_version"),
        "wayfinding_contract": graph.get("wayfinding_contract"),
        "invocation_contract": graph.get("invocation_contract"),
        "source_hashes": stable_source_hashes,
        "counts": stable_counts,
        "edges": [
            {
                "from": edge.get("from"),
                "to": edge.get("to"),
                "mechanism": edge.get("mechanism"),
                "group": edge.get("group"),
                "action_kind": (edge.get("navigation_affordance") or {}).get("action_kind")
                if isinstance(edge.get("navigation_affordance"), Mapping)
                else None,
                "affordance_status": (edge.get("navigation_affordance") or {}).get("status")
                if isinstance(edge.get("navigation_affordance"), Mapping)
                else None,
                "invocation_action_kind": (edge.get("invocation_affordance") or {}).get("action_kind")
                if isinstance(edge.get("invocation_affordance"), Mapping)
                else None,
                "invocation_status": (edge.get("invocation_affordance") or {}).get("status")
                if isinstance(edge.get("invocation_affordance"), Mapping)
                else None,
            }
            for edge in graph.get("edges", [])
            if isinstance(edge, Mapping)
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _plan_hash(plan: Mapping[str, Any]) -> str:
    payload = dict(plan)
    payload.pop("generated_at", None)
    payload.pop("plan_hash", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _scenario_hash(plan: Mapping[str, Any]) -> str:
    payload = {
        "contract": plan.get("contract"),
        "planner": plan.get("planner"),
        "mode": plan.get("mode"),
        "from": plan.get("from"),
        "to": plan.get("to"),
        "graph_hash": plan.get("graph_hash"),
        "path": plan.get("path"),
        "proof_hint": plan.get("proof_hint"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_action_ready_selector(ready_selector: object) -> str | None:
    """Use the root ready attr for action replay instead of full capture readiness."""
    if not isinstance(ready_selector, str) or not ready_selector:
        return None
    match = re.match(r"(\[[^\]]+\])", ready_selector.strip())
    return match.group(1) if match else ready_selector


def _direct_entry_step(
    *,
    source_id: str,
    target_id: str,
    target_view: Mapping[str, Any],
    entry: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "step_kind": "direct_entry",
        "from": source_id,
        "to": target_id,
        "mechanism": "entry_affordance",
        "label": "open route",
        "category": "route_entry",
        "action_kind": entry.get("action_kind") or "open_route",
        "entry_route": entry.get("entry_route"),
        "source_ready_selector": None,
        "ready_selector": _source_action_ready_selector(entry.get("ready_selector")),
        "capture_ready_selector": entry.get("ready_selector"),
        "capture_slug": entry.get("capture_slug"),
        "safety_class": entry.get("safety_class") or "read_only_navigation",
        "proof_status": entry.get("proof_status"),
        "target_view_id": target_id,
        "target_label": target_view.get("label"),
        "evidence_refs": entry.get("evidence_refs") or [],
    }


def _hybrid_wayfinding_plan(
    graph: dict[str, Any],
    base: dict[str, Any],
    *,
    source_id: str,
    target_id: str,
    views_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Compose direct route entry with source-backed invocation replay."""
    candidates: list[tuple[float, list[dict[str, Any]], dict[str, Any]]] = []
    unavailable_edges: list[dict[str, Any]] = []

    for edge in graph.get("edges", []):
        if not isinstance(edge, Mapping) or edge.get("to") != target_id:
            continue
        invocation = edge.get("invocation_affordance")
        if not isinstance(invocation, Mapping):
            continue
        action_kind = invocation.get("action_kind")
        if invocation.get("status") != "ready":
            if invocation.get("status") == "unavailable":
                unavailable_edges.append(
                    {
                        "from": edge.get("from"),
                        "to": edge.get("to"),
                        "mechanism": edge.get("mechanism"),
                        "action_kind": action_kind,
                        "reason": invocation.get("unavailable_reason"),
                    }
                )
            continue

        host_id = edge.get("from")
        if not isinstance(host_id, str) or not host_id:
            continue
        host_view = views_by_id.get(host_id, {})
        host_entry = host_view.get("entry_affordance") if isinstance(host_view, Mapping) else None
        if not isinstance(host_entry, Mapping):
            host_entry = _entry_affordance_for_view(host_view)
        if host_entry.get("status") != "ready":
            unavailable_edges.append(
                {
                    "from": source_id,
                    "to": host_id,
                    "mechanism": "entry_affordance",
                    "action_kind": host_entry.get("action_kind") or "open_route",
                    "reason": host_entry.get("unavailable_reason") or "host_entry_unavailable",
                }
            )
            continue

        embodied_plan = plan_wayfinding(graph, host_id, target_id, mode="embodied")
        embodied_path = embodied_plan.get("path")
        if embodied_plan.get("blocked") or not isinstance(embodied_path, list) or not embodied_path:
            unavailable_edges.append(
                {
                    "from": host_id,
                    "to": target_id,
                    "mechanism": edge.get("mechanism"),
                    "action_kind": action_kind,
                    "reason": embodied_plan.get("blocker") or "invocation_plan_unavailable",
                }
            )
            continue

        path_rows: list[dict[str, Any]] = []
        if source_id != host_id:
            path_rows.append(
                _direct_entry_step(
                    source_id=source_id,
                    target_id=host_id,
                    target_view=host_view,
                    entry=host_entry,
                )
            )

        for row in embodied_path:
            if not isinstance(row, Mapping):
                continue
            action_step = dict(row)
            action_step["step_kind"] = "source_backed_action_replay"
            action_step["proof_mode"] = "source_backed_action_replay"
            path_rows.append(action_step)

        if not path_rows:
            continue
        final_step = path_rows[-1]
        proof_hint = {
            "engine": "playwright",
            "proof_mode": "mixed_route_and_action_replay",
            "entry_route": host_entry.get("entry_route"),
            "source_ready_selector": _source_action_ready_selector(host_entry.get("ready_selector")),
            "target_ready_selector": final_step.get("ready_selector"),
            "capture_slug": host_entry.get("capture_slug"),
            "trigger": final_step.get("trigger"),
            "expected": final_step.get("expected"),
            "proof_status": final_step.get("proof_status"),
        }
        cost = float(_edge_rank(edge)) + 2.0 + (0.0 if source_id != host_id else -0.5)
        candidates.append((cost, path_rows, proof_hint))

    target_view = views_by_id.get(target_id, {})
    target_entry = target_view.get("entry_affordance") if isinstance(target_view, Mapping) else None
    if isinstance(target_entry, Mapping) and target_entry.get("status") == "ready":
        path_rows = [
            _direct_entry_step(
                source_id=source_id,
                target_id=target_id,
                target_view=target_view,
                entry=target_entry,
            )
        ] if source_id != target_id else []
        proof_hint = {
            "engine": "station_render",
            "proof_mode": "direct_route_arrival",
            "entry_route": target_entry.get("entry_route"),
            "ready_selector": target_entry.get("ready_selector"),
            "capture_slug": target_entry.get("capture_slug"),
            "proof_status": target_entry.get("proof_status"),
        }
        if path_rows:
            candidates.append((10_000.0, path_rows, proof_hint))

    if not candidates:
        base.update(
            {
                "blocked": True,
                "blocker": "no_hybrid_scenario_path",
                "path": [],
                "unavailable_edges": unavailable_edges[:24],
            }
        )
        base["scenario_hash"] = _scenario_hash(base)
        base["plan_hash"] = _plan_hash(base)
        return base

    candidates.sort(key=lambda row: (row[0], len(row[1]), json.dumps(row[1], sort_keys=True)))
    cost, path_rows, proof_hint = candidates[0]
    base.update(
        {
            "blocked": False,
            "cost": cost,
            "path": path_rows,
            "unavailable_edges": unavailable_edges[:24],
            "proof_hint": proof_hint,
        }
    )
    base["scenario_hash"] = _scenario_hash(base)
    base["plan_hash"] = _plan_hash(base)
    return base


def plan_wayfinding(
    graph: dict[str, Any],
    source_query: str,
    target_query: str,
    *,
    mode: str = "direct",
) -> dict[str, Any]:
    """Return a deterministic route plan over direct entry or embodied invocation edges."""
    if graph.get("wayfinding_contract") != WAYFINDING_CONTRACT:
        attach_wayfinding_affordances(graph)
    if mode not in {"direct", "embodied", "hybrid"}:
        raise ValueError(f"unsupported wayfinding mode: {mode}")

    generated_at = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    source_resolution = _resolve_view_query(graph, source_query)
    target_resolution = _resolve_view_query(graph, target_query)
    base: dict[str, Any] = {
        "contract": WAYFINDING_CONTRACT,
        "planner": WAYFINDING_PLANNER,
        "generated_at": generated_at,
        "from": source_query,
        "to": target_query,
        "mode": mode,
        "source_resolution": source_resolution,
        "target_resolution": target_resolution,
        "graph_hash": _wayfinding_graph_hash(graph),
        "drift_signals": graph.get("drift_signals", []),
    }
    if graph.get("drift_signals"):
        base.update(
            {
                "blocked": True,
                "blocker": "blocked_by_drift",
                "path": [],
                "unavailable_edges": [],
            }
        )
        base["plan_hash"] = _plan_hash(base)
        return base

    source_id = source_resolution.get("resolved_view_id")
    target_id = target_resolution.get("resolved_view_id")
    if not isinstance(source_id, str) or not source_id:
        base.update({"blocked": True, "blocker": "source_unresolved", "path": [], "unavailable_edges": []})
        base["plan_hash"] = _plan_hash(base)
        return base
    if not isinstance(target_id, str) or not target_id:
        base.update({"blocked": True, "blocker": "target_unresolved", "path": [], "unavailable_edges": []})
        base["plan_hash"] = _plan_hash(base)
        return base

    views_by_id = {
        str(view.get("id")): view
        for view in graph.get("views", [])
        if isinstance(view, Mapping) and isinstance(view.get("id"), str)
    }
    if mode == "hybrid":
        return _hybrid_wayfinding_plan(
            graph,
            base,
            source_id=source_id,
            target_id=target_id,
            views_by_id=views_by_id,
        )

    if source_id == target_id:
        target_view = views_by_id.get(target_id, {})
        entry = target_view.get("entry_affordance") if isinstance(target_view, Mapping) else None
        if not isinstance(entry, Mapping):
            entry = _entry_affordance_for_view(target_view)
        proof_hint = {
            "engine": "station_render",
            "entry_route": entry.get("entry_route"),
            "ready_selector": entry.get("ready_selector"),
            "capture_slug": entry.get("capture_slug"),
            "proof_status": entry.get("proof_status"),
        }
        base.update({"blocked": False, "path": [], "unavailable_edges": [], "proof_hint": proof_hint})
        base["plan_hash"] = _plan_hash(base)
        return base

    adjacency: dict[str, list[Mapping[str, Any]]] = {}
    unavailable_edges: list[dict[str, Any]] = []
    for edge in graph.get("edges", []):
        if not isinstance(edge, Mapping):
            continue
        affordance_key = "invocation_affordance" if mode == "embodied" else "navigation_affordance"
        affordance = edge.get(affordance_key)
        if not isinstance(affordance, Mapping):
            continue
        if affordance.get("status") != "ready":
            if affordance.get("status") != "unavailable":
                continue
            unavailable_edges.append(
                {
                    "from": edge.get("from"),
                    "to": edge.get("to"),
                    "mechanism": edge.get("mechanism"),
                    "action_kind": affordance.get("action_kind"),
                    "reason": affordance.get("unavailable_reason"),
                }
            )
            continue
        from_id = edge.get("from")
        if isinstance(from_id, str):
            adjacency.setdefault(from_id, []).append(edge)

    import heapq

    queue: list[tuple[float, int, str, list[Mapping[str, Any]]]] = [(0.0, 0, source_id, [])]
    sequence = 1
    best: dict[str, float] = {source_id: 0.0}
    selected_path: list[Mapping[str, Any]] | None = None
    while queue:
        cost, _, current, path = heapq.heappop(queue)
        if current == target_id:
            selected_path = path
            break
        if cost > best.get(current, float("inf")):
            continue
        for edge in adjacency.get(current, []):
            next_id = edge.get("to")
            if not isinstance(next_id, str):
                continue
            affordance = edge.get("invocation_affordance") if mode == "embodied" else edge.get("navigation_affordance")
            action_penalty = 0.0
            expected_proof = "source_backed_replay_ready" if mode == "embodied" else "station_render_ready"
            if isinstance(affordance, Mapping) and affordance.get("proof_status") != expected_proof:
                action_penalty = 4.0
            edge_cost = float(_edge_rank(edge)) + 1.0 + action_penalty
            new_cost = cost + edge_cost
            if new_cost < best.get(next_id, float("inf")):
                best[next_id] = new_cost
                heapq.heappush(queue, (new_cost, sequence, next_id, [*path, edge]))
                sequence += 1

    if selected_path is None:
        base.update(
            {
                "blocked": True,
                "blocker": "no_available_path",
                "path": [],
                "unavailable_edges": unavailable_edges[:24],
            }
        )
        base["plan_hash"] = _plan_hash(base)
        return base

    path_rows = []
    for edge in selected_path:
        affordance_key = "invocation_affordance" if mode == "embodied" else "navigation_affordance"
        affordance = edge.get(affordance_key) if isinstance(edge.get(affordance_key), Mapping) else {}
        source_view = views_by_id.get(str(edge.get("from") or ""), {})
        source_entry = (
            source_view.get("entry_affordance")
            if isinstance(source_view, Mapping) and isinstance(source_view.get("entry_affordance"), Mapping)
            else {}
        )
        path_rows.append(
            {
                "from": edge.get("from"),
                "to": edge.get("to"),
                "mechanism": edge.get("mechanism"),
                "label": edge.get("label"),
                "category": edge.get("category"),
                "action_kind": affordance.get("action_kind"),
                "entry_route": (
                    source_entry.get("entry_route")
                    if mode == "embodied"
                    else affordance.get("entry_route")
                ),
                "source_ready_selector": (
                    _source_action_ready_selector(source_entry.get("ready_selector"))
                    if mode == "embodied"
                    else None
                ),
                "ready_selector": (
                    (affordance.get("expected") or {}).get("ready_selector")
                    if mode == "embodied" and isinstance(affordance.get("expected"), Mapping)
                    else affordance.get("ready_selector")
                ),
                "capture_slug": (
                    source_entry.get("capture_slug")
                    if mode == "embodied"
                    else affordance.get("capture_slug")
                ),
                "safety_class": affordance.get("safety_class"),
                "proof_status": affordance.get("proof_status"),
                "invocation_contract": affordance.get("contract") if mode == "embodied" else None,
                "action_id": affordance.get("action_id") if mode == "embodied" else None,
                "trigger": affordance.get("trigger") if mode == "embodied" else None,
                "expected": affordance.get("expected") if mode == "embodied" else None,
                "selector_contract_source": affordance.get("selector_contract_source") if mode == "embodied" else None,
                "evidence_refs": affordance.get("evidence_refs") or edge.get("evidence_refs") or [],
            }
        )

    final_step = path_rows[-1] if path_rows else {}
    if mode == "embodied":
        proof_hint = {
            "engine": "playwright",
            "proof_mode": "source_backed_action_replay",
            "entry_route": final_step.get("entry_route"),
            "source_ready_selector": final_step.get("source_ready_selector"),
            "target_ready_selector": final_step.get("ready_selector"),
            "capture_slug": final_step.get("capture_slug"),
            "trigger": final_step.get("trigger"),
            "expected": final_step.get("expected"),
            "proof_status": final_step.get("proof_status"),
        }
    else:
        proof_hint = {
            "engine": "station_render",
            "entry_route": final_step.get("entry_route"),
            "ready_selector": final_step.get("ready_selector"),
            "capture_slug": final_step.get("capture_slug"),
            "proof_status": final_step.get("proof_status"),
        }
    base.update(
        {
            "blocked": False,
            "cost": best.get(target_id),
            "path": path_rows,
            "unavailable_edges": unavailable_edges[:24],
            "proof_hint": proof_hint,
        }
    )
    base["plan_hash"] = _plan_hash(base)
    return base


def _receipt_action_kinds(receipt: Mapping[str, Any]) -> set[str]:
    if receipt.get("result") != "passed":
        return set()
    kinds: set[str] = set()
    steps = receipt.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, Mapping) and isinstance(step.get("action_kind"), str):
                kinds.add(str(step["action_kind"]))
    plan = receipt.get("plan") if isinstance(receipt.get("plan"), Mapping) else {}
    path = plan.get("path") if isinstance(plan, Mapping) else None
    if isinstance(path, list):
        for step in path:
            if isinstance(step, Mapping) and isinstance(step.get("action_kind"), str):
                kinds.add(str(step["action_kind"]))
    return kinds


def _load_wayfinding_receipts(receipt_root: Path | None = None) -> list[dict[str, Any]]:
    root = receipt_root or (OUTPUT_DIR / "wayfinding_receipts")
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        payload = dict(payload)
        try:
            default_receipt_path = _repo_rel(path)
        except ValueError:
            default_receipt_path = str(path)
        payload.setdefault("receipt_path", default_receipt_path)
        rows.append(payload)
    return rows


def load_wayfinding_scenario_suite(path: Path | None = None) -> dict[str, Any]:
    """Load the canonical scenario suite with a stable, UI-friendly shape."""
    source = path or SOURCE_WAYFINDING_SCENARIOS_JSON
    payload: dict[str, Any] = {
        "contract": SCENARIO_SUITE_CONTRACT,
        "path": _display_path(source),
        "status": "missing",
        "scenarios": [],
    }
    if not source.exists():
        return payload
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        payload["status"] = "invalid"
        payload["error"] = f"{type(exc).__name__}: {exc}"
        return payload
    if not isinstance(raw, Mapping):
        payload["status"] = "invalid"
        payload["error"] = "scenario_suite_not_object"
        return payload

    scenarios: list[dict[str, Any]] = []
    for index, row in enumerate(raw.get("scenarios") or []):
        if not isinstance(row, Mapping):
            continue
        scenario_id = row.get("id")
        source_view = row.get("from")
        target_view = row.get("to")
        mode = row.get("mode")
        if not all(isinstance(value, str) and value for value in (scenario_id, source_view, target_view, mode)):
            continue
        if mode not in {"direct", "embodied", "hybrid"}:
            continue
        required_action_kinds = [
            str(kind)
            for kind in (row.get("required_action_kinds") or [])
            if isinstance(kind, str) and kind
        ]
        coverage_tags = [
            str(tag)
            for tag in (row.get("coverage_tags") or [])
            if isinstance(tag, str) and tag
        ]
        scenarios.append(
            {
                "id": scenario_id,
                "from": source_view,
                "to": target_view,
                "mode": mode,
                "required_action_kinds": required_action_kinds,
                "expected_receipt_contract": (
                    row.get("expected_receipt_contract")
                    if isinstance(row.get("expected_receipt_contract"), str)
                    else None
                ),
                "coverage_tags": coverage_tags,
                "ordinal": index,
                "planner_command": (
                    f"./repo-python kernel.py --view-wayfind {source_view} {target_view}"
                    + (f" --view-wayfind-mode {mode}" if mode != "direct" else "")
                ),
                "proof_command": (
                    f"./repo-python tools/meta/observability/view_wayfinding_check.py "
                    f"--from {source_view} --to {target_view} --mode {mode} --engine chromium"
                ),
            }
        )

    payload.update(
        {
            "contract": raw.get("contract") if raw.get("contract") == SCENARIO_SUITE_CONTRACT else SCENARIO_SUITE_CONTRACT,
            "status": "ready" if scenarios else "empty",
            "scenarios": scenarios,
        }
    )
    if raw.get("contract") != SCENARIO_SUITE_CONTRACT:
        payload["declared_contract"] = raw.get("contract")
        payload["status"] = "contract_mismatch"
    return payload


def build_wayfinding_capability_matrix(
    graph: dict[str, Any],
    *,
    receipt_root: Path | None = None,
) -> dict[str, Any]:
    """Build generated coverage posture from graph capability facts plus receipts."""
    if graph.get("wayfinding_contract") != WAYFINDING_CONTRACT:
        attach_wayfinding_affordances(graph)

    graph_hash = _wayfinding_graph_hash(graph)
    action_rows: dict[str, dict[str, Any]] = {
        kind: {
            "present_edges": 0,
            "present_entry_views": 0,
            "ready_edges": 0,
            "ready_entry_views": 0,
            "ready_invocation_edges": 0,
            "unavailable_edges": 0,
            "unavailable_invocation_edges": 0,
            "proved_receipts": 0,
            "status": "absent_no_specimen",
        }
        for kind in WAYFINDING_ACTION_KINDS
    }

    for edge in graph.get("edges", []):
        if not isinstance(edge, Mapping):
            continue
        nav = edge.get("navigation_affordance") if isinstance(edge.get("navigation_affordance"), Mapping) else {}
        inv = edge.get("invocation_affordance") if isinstance(edge.get("invocation_affordance"), Mapping) else {}
        kind = str(nav.get("action_kind") or inv.get("action_kind") or "external_or_unavailable")
        row = action_rows.setdefault(
            kind,
            {
                "present_edges": 0,
                "present_entry_views": 0,
                "ready_edges": 0,
                "ready_entry_views": 0,
                "ready_invocation_edges": 0,
                "unavailable_edges": 0,
                "unavailable_invocation_edges": 0,
                "proved_receipts": 0,
                "status": "absent_no_specimen",
            },
        )
        row["present_edges"] += 1
        if nav.get("status") == "ready":
            row["ready_edges"] += 1
        elif nav.get("status") == "unavailable":
            row["unavailable_edges"] += 1
        if inv.get("status") == "ready":
            row["ready_invocation_edges"] += 1
        elif inv.get("status") == "unavailable":
            row["unavailable_invocation_edges"] += 1

    for view in graph.get("views", []):
        if not isinstance(view, Mapping):
            continue
        entry = view.get("entry_affordance") if isinstance(view.get("entry_affordance"), Mapping) else {}
        kind = str(entry.get("action_kind") or "open_route")
        row = action_rows.setdefault(
            kind,
            {
                "present_edges": 0,
                "present_entry_views": 0,
                "ready_edges": 0,
                "ready_entry_views": 0,
                "ready_invocation_edges": 0,
                "unavailable_edges": 0,
                "unavailable_invocation_edges": 0,
                "proved_receipts": 0,
                "status": "absent_no_specimen",
            },
        )
        row["present_entry_views"] += 1
        if entry.get("status") == "ready":
            row["ready_entry_views"] += 1

    scenario_proofs: list[dict[str, Any]] = []
    for receipt in _load_wayfinding_receipts(receipt_root):
        kinds = _receipt_action_kinds(receipt)
        if receipt.get("result") == "passed":
            for kind in kinds:
                action_rows.setdefault(
                    kind,
                    {
                        "present_edges": 0,
                        "present_entry_views": 0,
                        "ready_edges": 0,
                        "ready_entry_views": 0,
                        "ready_invocation_edges": 0,
                        "unavailable_edges": 0,
                        "unavailable_invocation_edges": 0,
                        "proved_receipts": 0,
                        "status": "absent_no_specimen",
                    },
                )["proved_receipts"] += 1
        if receipt.get("contract") == "frontend_wayfinding_scenario_receipt_v1" and receipt.get("result") == "passed":
            plan = receipt.get("plan") if isinstance(receipt.get("plan"), Mapping) else {}
            scenario_proofs.append(
                {
                    "from": receipt.get("from"),
                    "to": receipt.get("to"),
                    "mode": receipt.get("mode"),
                    "result": receipt.get("result"),
                    "receipt_path": receipt.get("receipt_path"),
                    "plan_hash": receipt.get("plan_hash"),
                    "scenario_hash": receipt.get("scenario_hash") or plan.get("scenario_hash"),
                }
            )

    drift_blocked = bool(graph.get("drift_signals"))
    for kind, row in action_rows.items():
        if drift_blocked:
            row["status"] = "blocked_by_drift"
        elif row["proved_receipts"] > 0:
            row["status"] = "proved"
        elif row["present_edges"] == 0 and row["present_entry_views"] == 0:
            row["status"] = "absent_no_specimen"
        elif row["unavailable_invocation_edges"] > 0 or (
            row["ready_edges"] == 0 and row["ready_entry_views"] == 0 and row["ready_invocation_edges"] == 0
        ):
            row["status"] = "unavailable"
        elif row["ready_edges"] > 0 or row["ready_entry_views"] > 0 or row["ready_invocation_edges"] > 0:
            row["status"] = "ready_unproved"
        else:
            row["status"] = "unavailable"

    return {
        "contract": CAPABILITY_MATRIX_CONTRACT,
        "wayfinding_contract": WAYFINDING_CONTRACT,
        "invocation_contract": INVOCATION_CONTRACT,
        "graph_hash": graph_hash,
        "drift_signal_count": len(graph.get("drift_signals") or []),
        "action_kinds": {kind: action_rows[kind] for kind in sorted(action_rows)},
        "scenario_proofs": sorted(
            scenario_proofs,
            key=lambda row: (
                str(row.get("from") or ""),
                str(row.get("to") or ""),
                str(row.get("mode") or ""),
                str(row.get("receipt_path") or ""),
            ),
        ),
    }


def _frontier_slug(*parts: object) -> str:
    text = "_".join(str(part or "").strip() for part in parts if str(part or "").strip())
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return slug or "unknown"


def _frontier_hash(packet: Mapping[str, Any]) -> str:
    payload = dict(packet)
    payload.pop("generated_at", None)
    payload.pop("frontier_hash", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _scenario_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("from") or ""),
        str(row.get("to") or ""),
        str(row.get("mode") or ""),
    )


def _frontier_status_priority(status: str, action_kind: str, row: Mapping[str, Any]) -> tuple[int, str]:
    if status == "ready_unproved":
        return (10, "high")
    if status == "proved" and int(row.get("proved_receipts") or 0) <= 1:
        return (20, "medium")
    if status == "unavailable":
        return (30, "medium")
    if status == "absent_no_specimen":
        return (40, "low")
    if status == "blocked_by_drift":
        return (50, "high")
    return (60, "low")


def _frontier_mode_for_action_kind(action_kind: str, invocation_ready: bool = False) -> str:
    if action_kind in {"open_route", "open_entry_route"}:
        return "direct"
    if action_kind in {"overlay_open", "drawer_open", "command_palette_select"}:
        return "embodied"
    if action_kind == "station_lens_switch":
        # A Station route is directly openable, but proving the lens-switch class
        # requires a source UI action rather than a route-open teleport.
        return "embodied" if invocation_ready else "embodied"
    return "direct"


def _frontier_candidate_commands(
    *,
    source_view: str | None,
    target_view: str | None,
    mode: str,
    proof_ready: bool,
) -> tuple[str | None, str | None]:
    if not source_view or not target_view:
        return (None, None)
    planner_command = (
        f"./repo-python kernel.py --view-wayfind {source_view} {target_view}"
        + (f" --view-wayfind-mode {mode}" if mode != "direct" else "")
    )
    proof_command = None
    if proof_ready:
        proof_command = (
            f"./repo-python tools/meta/observability/view_wayfinding_check.py "
            f"--from {source_view} --to {target_view} --mode {mode} --engine chromium"
        )
    return (planner_command, proof_command)


def _frontier_edge_candidates(
    graph: Mapping[str, Any],
    action_kind: str,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for edge in graph.get("edges", []):
        if not isinstance(edge, Mapping):
            continue
        nav = edge.get("navigation_affordance") if isinstance(edge.get("navigation_affordance"), Mapping) else {}
        inv = edge.get("invocation_affordance") if isinstance(edge.get("invocation_affordance"), Mapping) else {}
        edge_action_kind = str(nav.get("action_kind") or inv.get("action_kind") or "")
        invocation_action_kind = str(inv.get("action_kind") or "")
        if action_kind not in {edge_action_kind, invocation_action_kind}:
            continue
        source_view = edge.get("from") if isinstance(edge.get("from"), str) else None
        target_view = edge.get("to") if isinstance(edge.get("to"), str) else None
        invocation_ready = inv.get("status") == "ready"
        navigation_ready = nav.get("status") == "ready"
        mode = _frontier_mode_for_action_kind(action_kind, invocation_ready=invocation_ready)
        proof_ready = (mode == "embodied" and invocation_ready) or (
            mode == "direct" and navigation_ready and action_kind in {"open_route", "open_entry_route"}
        )
        blocker = None
        if action_kind == "station_lens_switch" and not invocation_ready:
            blocker = "source_backed_lens_switch_trigger_missing"
        elif mode == "embodied" and not invocation_ready:
            blocker = inv.get("unavailable_reason") or "selector_or_command_contract_missing"
        elif mode == "direct" and not navigation_ready:
            blocker = nav.get("unavailable_reason") or "entry_route_missing"
        planner_command, proof_command = _frontier_candidate_commands(
            source_view=source_view,
            target_view=target_view,
            mode=mode,
            proof_ready=proof_ready,
        )
        candidates.append(
            {
                "from": source_view,
                "to": target_view,
                "mode": mode,
                "mechanism": edge.get("mechanism"),
                "category": edge.get("category"),
                "navigation_status": nav.get("status"),
                "invocation_status": inv.get("status"),
                "planner_command": planner_command,
                "proof_command": proof_command,
                "blocker": blocker,
                "evidence_refs": sorted(
                    {
                        str(ref)
                        for ref in [
                            *(edge.get("evidence_refs") or [] if isinstance(edge.get("evidence_refs"), list) else []),
                            *(nav.get("evidence_refs") or [] if isinstance(nav.get("evidence_refs"), list) else []),
                            *(inv.get("evidence_refs") or [] if isinstance(inv.get("evidence_refs"), list) else []),
                        ]
                        if isinstance(ref, str) and ref
                    }
                ),
            }
        )
    return sorted(
        candidates,
        key=lambda row: (
            0 if row.get("from") == "station" and row.get("to") == "navigation" else 1,
            0 if row.get("to") == "navigation" else 1,
            0 if row.get("proof_command") else 1,
            str(row.get("from") or ""),
            str(row.get("to") or ""),
            str(row.get("mechanism") or ""),
        ),
    )


def _frontier_entry_candidates(
    graph: Mapping[str, Any],
    action_kind: str,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for view in graph.get("views", []):
        if not isinstance(view, Mapping):
            continue
        entry = view.get("entry_affordance") if isinstance(view.get("entry_affordance"), Mapping) else {}
        if entry.get("action_kind") != action_kind:
            continue
        target_view = view.get("id") if isinstance(view.get("id"), str) else None
        mode = "direct" if action_kind in {"open_route", "open_entry_route"} else "embodied"
        proof_ready = mode == "direct" and entry.get("status") == "ready"
        planner_command, proof_command = _frontier_candidate_commands(
            source_view="station",
            target_view=target_view,
            mode=mode,
            proof_ready=proof_ready,
        )
        candidates.append(
            {
                "from": "station",
                "to": target_view,
                "mode": mode,
                "mechanism": "entry_affordance",
                "category": "entry_view",
                "navigation_status": entry.get("status"),
                "invocation_status": "not_applicable",
                "planner_command": planner_command,
                "proof_command": proof_command,
                "blocker": (
                    None
                    if proof_ready
                    else entry.get("unavailable_reason") or "source_backed_invocation_contract_missing"
                ),
                "evidence_refs": entry.get("evidence_refs") or [],
            }
        )
    return sorted(candidates, key=lambda row: (0 if row.get("proof_command") else 1, str(row.get("to") or "")))


def build_wayfinding_scenario_frontier(
    graph: dict[str, Any],
    *,
    scenario_suite_path: Path | None = None,
    receipt_root: Path | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    """Rank the next governed wayfinding scenarios from graph, suite, matrix, and receipts."""
    if graph.get("wayfinding_contract") != WAYFINDING_CONTRACT:
        attach_wayfinding_affordances(graph)
    graph_hash = _wayfinding_graph_hash(graph)
    scenario_suite = load_wayfinding_scenario_suite(scenario_suite_path)
    matrix = build_wayfinding_capability_matrix(graph, receipt_root=receipt_root)
    suite_rows = scenario_suite.get("scenarios") if isinstance(scenario_suite.get("scenarios"), list) else []
    suite_keys = {
        _scenario_key(row)
        for row in suite_rows
        if isinstance(row, Mapping)
    }

    frontier: list[dict[str, Any]] = []
    action_kinds = matrix.get("action_kinds") if isinstance(matrix.get("action_kinds"), Mapping) else {}
    for action_kind in WAYFINDING_ACTION_KINDS:
        row = action_kinds.get(action_kind)
        if not isinstance(row, Mapping):
            continue
        status = str(row.get("status") or "unknown")
        priority_rank, priority = _frontier_status_priority(status, action_kind, row)
        if status == "proved" and int(row.get("proved_receipts") or 0) > 1:
            continue

        candidates = _frontier_edge_candidates(graph, action_kind)
        if not candidates:
            candidates = _frontier_entry_candidates(graph, action_kind)

        candidate = candidates[0] if candidates else {
            "from": None,
            "to": None,
            "mode": "direct",
            "mechanism": None,
            "category": None,
            "navigation_status": "unavailable",
            "invocation_status": "unavailable",
            "planner_command": None,
            "proof_command": None,
            "blocker": "live_specimen_missing",
            "evidence_refs": [],
        }
        source_view = candidate.get("from") if isinstance(candidate.get("from"), str) else None
        target_view = candidate.get("to") if isinstance(candidate.get("to"), str) else None
        mode = str(candidate.get("mode") or "direct")
        suite_key = (source_view or "", target_view or "", mode)
        already_in_suite = suite_key in suite_keys
        reason = {
            "ready_unproved": "action_kind_ready_but_no_receipt",
            "proved": "action_kind_proved_once_needs_second_specimen",
            "unavailable": "action_kind_unavailable_without_source_backed_invocation",
            "absent_no_specimen": "action_kind_has_no_live_specimen",
            "blocked_by_drift": "graph_drift_blocks_wayfinding",
        }.get(status, "action_kind_requires_review")
        blocker = candidate.get("blocker")
        if status == "ready_unproved" and action_kind == "station_lens_switch" and not blocker:
            blocker = "source_backed_lens_switch_trigger_missing"
        if status == "proved" and already_in_suite:
            reason = "proved_action_kind_already_in_canonical_suite"
        frontier.append(
            {
                "id": _frontier_slug("prove", action_kind, source_view or "source", "to", target_view or "target", mode),
                "from": source_view,
                "to": target_view,
                "mode": mode,
                "target_action_kind": action_kind,
                "status": status,
                "priority": priority,
                "priority_rank": priority_rank,
                "reason": reason,
                "mechanism": candidate.get("mechanism"),
                "category": candidate.get("category"),
                "navigation_status": candidate.get("navigation_status"),
                "invocation_status": candidate.get("invocation_status"),
                "planner_command": candidate.get("planner_command"),
                "proof_command": candidate.get("proof_command"),
                "blocker": blocker,
                "suite_status": "already_in_suite" if already_in_suite else (
                    "blocked" if blocker else "candidate"
                ),
                "present_edges": row.get("present_edges"),
                "present_entry_views": row.get("present_entry_views"),
                "ready_edges": row.get("ready_edges"),
                "ready_entry_views": row.get("ready_entry_views"),
                "ready_invocation_edges": row.get("ready_invocation_edges"),
                "unavailable_edges": row.get("unavailable_edges"),
                "unavailable_invocation_edges": row.get("unavailable_invocation_edges"),
                "proved_receipts": row.get("proved_receipts"),
                "evidence_refs": candidate.get("evidence_refs") or [],
            }
        )

    frontier = sorted(
        frontier,
        key=lambda row: (
            int(row.get("priority_rank") or 99),
            0 if row.get("proof_command") else 1,
            str(row.get("target_action_kind") or ""),
            str(row.get("id") or ""),
        ),
    )[: max(1, limit)]
    packet = {
        "contract": SCENARIO_FRONTIER_CONTRACT,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "wayfinding_contract": WAYFINDING_CONTRACT,
        "invocation_contract": INVOCATION_CONTRACT,
        "scenario_suite_contract": SCENARIO_SUITE_CONTRACT,
        "capability_matrix_contract": CAPABILITY_MATRIX_CONTRACT,
        "graph_hash": graph_hash,
        "matrix_graph_hash": matrix.get("graph_hash"),
        "drift_signal_count": len(graph.get("drift_signals") or []),
        "scenario_count": len(suite_rows),
        "frontier": frontier,
        "commands": {
            "frontier": "./repo-python kernel.py --view-scenario-frontier",
            "suite_dry_run": "./repo-python kernel.py --view-scenario-suite --view-scenario-suite-dry-run",
            "suite": "./repo-python kernel.py --view-scenario-suite",
        },
    }
    packet["frontier_hash"] = _frontier_hash(packet)
    return packet


def _receipt_summary(receipt: Mapping[str, Any]) -> dict[str, Any]:
    scenario_replay = receipt.get("scenario_replay") if isinstance(receipt.get("scenario_replay"), Mapping) else {}
    action_replay = receipt.get("action_replay") if isinstance(receipt.get("action_replay"), Mapping) else {}
    station_render_receipt = (
        receipt.get("station_render") if isinstance(receipt.get("station_render"), Mapping) else {}
    )
    run_dir = (
        scenario_replay.get("run_dir")
        or action_replay.get("run_dir")
        or station_render_receipt.get("run_dir")
    )
    scenarios = receipt.get("scenarios") if isinstance(receipt.get("scenarios"), list) else []
    return {
        "contract": receipt.get("contract"),
        "result": receipt.get("result"),
        "from": receipt.get("from"),
        "to": receipt.get("to"),
        "mode": receipt.get("mode"),
        "scenario_id": receipt.get("scenario_id"),
        "scenario_count": len(scenarios),
        "passed_count": len(
            [
                row
                for row in scenarios
                if isinstance(row, Mapping) and row.get("result") in {"passed", "dry_run"}
            ]
        ),
        "receipt_path": receipt.get("receipt_path"),
        "plan_hash": receipt.get("plan_hash"),
        "scenario_hash": receipt.get("scenario_hash"),
        "action_trace_hash": receipt.get("action_trace_hash"),
        "proof_mode": receipt.get("proof_mode"),
        "generated_at": receipt.get("generated_at"),
        "run_dir": run_dir,
    }


def build_navigation_mission_control_packet(
    graph: dict[str, Any],
    *,
    scenario_suite_path: Path | None = None,
    receipt_root: Path | None = None,
) -> dict[str, Any]:
    """Assemble the read-only Station Mission Control packet from generated state."""
    if graph.get("wayfinding_contract") != WAYFINDING_CONTRACT:
        attach_wayfinding_affordances(graph)
    graph_hash = _wayfinding_graph_hash(graph)
    capability_matrix = build_wayfinding_capability_matrix(graph, receipt_root=receipt_root)
    scenario_suite = load_wayfinding_scenario_suite(scenario_suite_path)
    scenario_frontier = build_wayfinding_scenario_frontier(
        graph,
        scenario_suite_path=scenario_suite_path,
        receipt_root=receipt_root,
    )
    receipts = _load_wayfinding_receipts(receipt_root)
    latest_receipts = sorted(
        (_receipt_summary(receipt) for receipt in receipts),
        key=lambda row: str(row.get("generated_at") or row.get("receipt_path") or ""),
        reverse=True,
    )[:12]

    action_kinds = capability_matrix.get("action_kinds")
    action_rows = action_kinds if isinstance(action_kinds, Mapping) else {}
    gaps = [
        {
            "action_kind": kind,
            "status": row.get("status"),
            "ready_edges": row.get("ready_edges"),
            "ready_entry_views": row.get("ready_entry_views"),
            "ready_invocation_edges": row.get("ready_invocation_edges"),
            "unavailable_edges": row.get("unavailable_edges"),
            "unavailable_invocation_edges": row.get("unavailable_invocation_edges"),
            "proved_receipts": row.get("proved_receipts"),
            "next_owner": (
                "source-backed invocation contract"
                if row.get("status") == "unavailable"
                else (
                    "scenario-suite proof"
                    if row.get("status") == "ready_unproved"
                    else "live specimen"
                )
            ),
        }
        for kind, row in sorted(action_rows.items())
        if isinstance(row, Mapping) and row.get("status") != "proved"
    ]

    return {
        "contract": MISSION_CONTROL_CONTRACT,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "wayfinding_contract": WAYFINDING_CONTRACT,
        "invocation_contract": INVOCATION_CONTRACT,
        "capability_matrix_contract": CAPABILITY_MATRIX_CONTRACT,
        "scenario_suite_contract": SCENARIO_SUITE_CONTRACT,
        "scenario_suite_receipt_contract": SCENARIO_SUITE_RECEIPT_CONTRACT,
        "scenario_frontier_contract": SCENARIO_FRONTIER_CONTRACT,
        "graph": {
            "path": _display_path(OUTPUT_JSON),
            "hash": graph_hash,
            "schema_version": graph.get("schema_version"),
            "counts": graph.get("counts") if isinstance(graph.get("counts"), Mapping) else {},
            "drift_count": len(graph.get("drift_signals") or []),
        },
        "capability_matrix": {
            "path": _display_path(OUTPUT_CAPABILITY_MATRIX),
            "contract": capability_matrix.get("contract"),
            "graph_hash": capability_matrix.get("graph_hash"),
            "drift_signal_count": capability_matrix.get("drift_signal_count"),
            "action_kinds": capability_matrix.get("action_kinds") or {},
            "scenario_proofs": capability_matrix.get("scenario_proofs") or [],
        },
        "scenario_suite": scenario_suite,
        "scenario_frontier": {
            "path": _display_path(OUTPUT_SCENARIO_FRONTIER),
            "contract": scenario_frontier.get("contract"),
            "graph_hash": scenario_frontier.get("graph_hash"),
            "frontier_hash": scenario_frontier.get("frontier_hash"),
            "drift_signal_count": scenario_frontier.get("drift_signal_count"),
            "frontier": scenario_frontier.get("frontier") or [],
        },
        "latest_receipts": latest_receipts,
        "gaps": gaps,
        "commands": {
            "graph_check": "./repo-python kernel.py --view-graph-check",
            "capability_matrix": "./repo-python kernel.py --view-capability-matrix",
            "suite": (
                "./repo-python tools/meta/observability/view_wayfinding_check.py "
                "--suite tools/meta/observability/wayfinding_scenarios.json --engine chromium"
            ),
            "scenario_frontier": "./repo-python kernel.py --view-scenario-frontier",
        },
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_graph() -> dict[str, Any]:
    app_text = SOURCE_APP_TSX.read_text(encoding="utf-8")
    surfaces_text = SOURCE_SURFACES_TS.read_text(encoding="utf-8")
    station_lens_text = (
        SOURCE_STATION_LENS_TSX.read_text(encoding="utf-8")
        if SOURCE_STATION_LENS_TSX.exists()
        else ""
    )

    routes = _parse_app_tsx(app_text)
    surfaces = _parse_surfaces_ts(surfaces_text)
    overlays = _parse_overlays_ts(SOURCE_OVERLAYS_TS)
    captures = _parse_station_views(SOURCE_STATION_VIEWS_JSON)
    load_index = _load_render_load_index(SOURCE_RENDER_LOAD_INDEX)
    generated_at = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    render_status_source = _render_status_source(load_index)
    render_status_source["projection_generated_at"] = generated_at
    semantic_layer = _load_semantic_layer(SOURCE_SEMANTIC_LAYER_JSON)
    component_index = _load_component_index(SOURCE_COMPONENT_INDEX_JSON)
    lens_prefix_to_id = _parse_station_lens(station_lens_text)

    all_surfaces = surfaces + overlays
    surface_relation_audit = _surface_relation_audit(
        surfaces=all_surfaces,
        routes=routes,
        captures=captures,
        semantic_layer=semantic_layer,
        component_index=component_index,
        app_text=app_text,
        station_lens_text=station_lens_text,
    )
    audit_by_id = {
        str(row.get("surface_id")): row
        for row in surface_relation_audit.get("surfaces", [])
        if isinstance(row, Mapping) and isinstance(row.get("surface_id"), str)
    }
    edges = _derive_edges(all_surfaces, lens_prefix_to_id, surface_relation_audit)
    pathway_audit = _pathway_audit(all_surfaces, edges)
    pathway_by_id = {
        str(row.get("id")): row
        for row in pathway_audit.get("per_view", [])
        if isinstance(row, Mapping) and isinstance(row.get("id"), str)
    }
    drift = _compute_drift(routes, all_surfaces, captures, edges, pathway_audit)

    # Assemble view records
    views: list[dict[str, Any]] = []
    for s in all_surfaces:
        capture = _capture_for_surface(captures, s)
        load_timing = _capture_load_timing(capture, load_index)
        fanout = [e for e in edges if e["from"] == s.id]
        fanin = [e for e in edges if e["to"] == s.id]
        pathway_row = pathway_by_id.get(s.id) or {}
        entry_route = _resolve_entry_route(s, routes)
        surface_audit = audit_by_id.get(s.id)
        views.append(
            {
                "id": s.id,
                "kind": s.kind,
                "route": s.route or None,
                "entry_route": entry_route,
                "route_aliases": s.route_aliases,
                "label": s.label,
                "purpose": s.purpose,
                "keywords": s.keywords,
                "shortcut": s.shortcut,
                "shell_group": s.shell_group,
                "station_group": s.station_group,
                "home_tile_order": s.home_tile_order,
                "station_lens_eligible": s.station_lens_eligible,
                "overlay_of": s.overlay_of,
                "invocation": s.invocation,
                "cul_de_sac": {
                    "declared": bool(s.is_cul_de_sac),
                    "reason": (s.is_cul_de_sac or {}).get("reason"),
                    "effective": len(fanout) == 0,
                },
                "capture": {
                    "slug": capture.slug if capture else None,
                    "route": capture.route if capture else None,
                    "ready_selector": capture.ready_selector if capture else None,
                    "stabilize_ms": capture.stabilize_ms if capture else None,
                    "capture_group": capture.capture_group if capture else None,
                    "canonical_slug": capture.canonical_slug if capture else None,
                    "row_role": capture.row_role if capture else None,
                    "capture_mode": capture.capture_mode if capture else None,
                    "full_page": capture.full_page if capture else None,
                    "notes": capture.notes if capture else None,
                    "bound_via": (
                        "capture_slug"
                        if s.capture_slug and capture
                        else ("route_match" if capture else None)
                    ),
                    "load_timing": load_timing,
                } if capture or s.capture_slug else None,
                "fanout_count": len(fanout),
                "fanin_count": len(fanin),
                "pathway_count": pathway_row.get("pathway_count", 0),
                "pathway_fanout_count": pathway_row.get("pathway_fanout_count", 0),
                "pathway_fanin_count": pathway_row.get("pathway_fanin_count", 0),
                "evidence": s.evidence.to_json(),
                "surface_audit": surface_audit,
            }
        )

    # One-line + five-line compressions for the whole system
    page_count = sum(1 for v in views if v["kind"] == "page")
    overlay_count = sum(1 for v in views if v["kind"] in ("overlay", "modal", "drawer"))
    cul_de_sac_count = sum(
        1 for v in views if v["cul_de_sac"]["effective"] and v["kind"] == "page"
    )
    declared_culdesacs = sum(
        1 for v in views if v["cul_de_sac"]["declared"] and v["kind"] == "page"
    )
    timed_capture_rows = sum(
        1 for v in views if (v.get("capture") or {}).get("load_timing")
    )

    compression = {
        "one_line": (
            f"{page_count} pages, {overlay_count} overlays, {len(edges)} edges, "
            f"{cul_de_sac_count} cul-de-sacs ({declared_culdesacs} declared), "
            f"{len(drift)} drift signal{'s' if len(drift) != 1 else ''}."
        ),
        "five_line": [
            f"{page_count} pages live under the cockpit router; "
            f"{overlay_count} overlays float above them.",
            f"{len(edges)} declared + group-derived navigation edges connect the pages.",
            f"{cul_de_sac_count} pages are cul-de-sacs ({declared_culdesacs} declared via "
            f"isCulDeSac, the rest undeclared and flagged as drift).",
            f"{sum(1 for v in views if v.get('capture'))} pages have capture contracts; "
            f"{timed_capture_rows} have durable load timing; "
            f"the rest are capture-excluded, unregistered, or not rendered yet.",
            (
                "Drift-proof extraction: every node + edge carries evidence (file + line); "
                "surfaces.ts, App.tsx, and station_views.json are reconciled on every build."
                if not drift
                else f"Drift detected: {len(drift)} signals — re-align before shipping."
            ),
        ],
    }

    hashables = {
        "app_tsx": hashlib.sha256(app_text.encode()).hexdigest()[:12],
        "surfaces_ts": hashlib.sha256(surfaces_text.encode()).hexdigest()[:12],
        "overlays_ts": (
            hashlib.sha256(SOURCE_OVERLAYS_TS.read_text(encoding="utf-8").encode()).hexdigest()[:12]
            if SOURCE_OVERLAYS_TS.exists()
            else None
        ),
        "station_views_json": hashlib.sha256(
            SOURCE_STATION_VIEWS_JSON.read_text(encoding="utf-8").encode()
        ).hexdigest()[:12],
        "semantic_layer_json": (
            hashlib.sha256(SOURCE_SEMANTIC_LAYER_JSON.read_text(encoding="utf-8").encode()).hexdigest()[:12]
            if SOURCE_SEMANTIC_LAYER_JSON.exists()
            else None
        ),
        "component_index_json": (
            hashlib.sha256(SOURCE_COMPONENT_INDEX_JSON.read_text(encoding="utf-8").encode()).hexdigest()[:12]
            if SOURCE_COMPONENT_INDEX_JSON.exists()
            else None
        ),
        "render_load_index": (
            (render_status_source.get("authority") or {}).get("hash")
            if isinstance(render_status_source.get("authority"), Mapping)
            else None
        ),
    }

    graph = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_evidence": {
            "app_router": str(SOURCE_APP_TSX.relative_to(REPO_ROOT)),
            "surface_registry": str(SOURCE_SURFACES_TS.relative_to(REPO_ROOT)),
            "overlay_registry": str(SOURCE_OVERLAYS_TS.relative_to(REPO_ROOT))
                if SOURCE_OVERLAYS_TS.exists() else None,
            "station_lens": str(SOURCE_STATION_LENS_TSX.relative_to(REPO_ROOT)),
            "capture_manifest": str(SOURCE_STATION_VIEWS_JSON.relative_to(REPO_ROOT)),
            "semantic_layer": (
                str(SOURCE_SEMANTIC_LAYER_JSON.relative_to(REPO_ROOT))
                if SOURCE_SEMANTIC_LAYER_JSON.exists()
                else None
            ),
            "component_index": (
                str(SOURCE_COMPONENT_INDEX_JSON.relative_to(REPO_ROOT))
                if SOURCE_COMPONENT_INDEX_JSON.exists()
                else None
            ),
            "render_load_index": (
                str(SOURCE_RENDER_LOAD_INDEX.relative_to(REPO_ROOT))
                if SOURCE_RENDER_LOAD_INDEX.exists()
                else None
            ),
        },
        "source_hashes": hashables,
        "render_status_source": render_status_source,
        "counts": {
            "pages": page_count,
            "overlays": overlay_count,
            "edges": len(edges),
            "pathway_edges": pathway_audit["pathway_edge_count"],
            "explicit_pathway_edges": pathway_audit["explicit_pathway_count"],
            "derived_pathway_edges": pathway_audit["derived_pathway_count"],
            "zero_substantive_pathway_views": pathway_audit["zero_substantive_pathway_view_count"],
            "allowed_zero_pathway_views": pathway_audit["allowed_zero_pathway_view_count"],
            "cul_de_sacs_effective": cul_de_sac_count,
            "cul_de_sacs_declared": declared_culdesacs,
            "routes_declared": len([r for r in routes if not r.element.startswith("Navigate:")]),
            "redirects": len([r for r in routes if r.element.startswith("Navigate:")]),
            "capture_rows": len(captures),
            "timed_capture_rows": timed_capture_rows,
            "drift_signals": len(drift),
        },
        "compression": compression,
        "views": views,
        "edges": edges,
        "pathway_audit": pathway_audit,
        "surface_relation_audit": surface_relation_audit,
        "routes": [
            {"path": r.path, "element": r.element, "evidence": r.evidence.to_json()}
            for r in routes
        ],
        "captures": [
            {
                "slug": c.slug,
                "route": c.route,
                "purpose": c.purpose,
                "ready_selector": c.ready_selector,
                "stabilize_ms": c.stabilize_ms,
                "capture_group": c.capture_group,
                "canonical_slug": c.canonical_slug,
                "row_role": c.row_role,
                "capture_mode": c.capture_mode,
                "full_page": c.full_page,
                "notes": c.notes,
                "load_timing": _capture_load_timing(c, load_index),
            }
            for c in captures
        ],
        "drift_signals": drift,
        "lens_prefix_map": lens_prefix_to_id,
    }
    return attach_frontend_validation_contracts(attach_wayfinding_affordances(graph))


def _render_snapshot_md(graph: dict[str, Any]) -> str:
    lines = [
        "# Frontend Navigation Graph — snapshot",
        "",
        f"_Regenerated {graph['generated_at']} via `tools/meta/observability/frontend_nav_graph.py`._",
        "",
        f"**One line:** {graph['compression']['one_line']}",
        "",
        "**Five-line system sketch:**",
    ]
    for s in graph["compression"]["five_line"]:
        lines.append(f"- {s}")
    lines.append("")
    lines.append("## Counts")
    for k, v in graph["counts"].items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")

    pathway_audit = graph.get("pathway_audit") if isinstance(graph.get("pathway_audit"), Mapping) else {}
    if pathway_audit:
        zero_substantive = pathway_audit.get("zero_substantive_pathway_views") or []
        allowed_zero = pathway_audit.get("allowed_zero_pathway_views") or []
        lines.extend(
            [
                "## Pathway Hover Audit",
                f"- `contract`: {pathway_audit.get('contract')}",
                f"- `status`: {pathway_audit.get('status')}",
                f"- `pathway_edge_count`: {pathway_audit.get('pathway_edge_count')}",
                f"- `explicit_pathway_count`: {pathway_audit.get('explicit_pathway_count')}",
                f"- `derived_pathway_count`: {pathway_audit.get('derived_pathway_count')}",
                f"- `zero_substantive_pathway_view_count`: {pathway_audit.get('zero_substantive_pathway_view_count')}",
                f"- `allowed_zero_pathway_view_count`: {pathway_audit.get('allowed_zero_pathway_view_count')}",
            ]
        )
        if zero_substantive:
            lines.append("- zero substantive views:")
            for row in zero_substantive:
                if isinstance(row, Mapping):
                    lines.append(f"  - `{row.get('id')}` ({row.get('label')})")
        if allowed_zero:
            lines.append("- allowed zero-pathway overlays/drawers:")
            for row in allowed_zero:
                if isinstance(row, Mapping):
                    lines.append(f"  - `{row.get('id')}` ({row.get('label')})")
        lines.append("")

    wayfinding = graph.get("wayfinding") if isinstance(graph.get("wayfinding"), Mapping) else {}
    if wayfinding:
        lines.extend(
            [
                "## Wayfinding",
                f"- `contract`: {wayfinding.get('contract')}",
                f"- `planner`: {wayfinding.get('planner')}",
                f"- `invocation_contract`: {wayfinding.get('invocation_contract')}",
                f"- `ready_view_count`: {wayfinding.get('ready_view_count')}",
                f"- `proof_ready_view_count`: {wayfinding.get('proof_ready_view_count')}",
                f"- `ready_edge_count`: {wayfinding.get('ready_edge_count')}",
                f"- `proof_ready_edge_count`: {wayfinding.get('proof_ready_edge_count')}",
                f"- `unavailable_edge_count`: {wayfinding.get('unavailable_edge_count')}",
                f"- `ready_invocation_edge_count`: {wayfinding.get('ready_invocation_edge_count')}",
                f"- `unavailable_invocation_edge_count`: {wayfinding.get('unavailable_invocation_edge_count')}",
                "",
            ]
        )

    validation_matrix = (
        graph.get("validation_matrix")
        if isinstance(graph.get("validation_matrix"), Mapping)
        else {}
    )
    if validation_matrix:
        lines.extend(
            [
                "## Validation Matrix",
                f"- `schema`: {validation_matrix.get('schema')}",
                f"- `visual_smoke_lane`: {validation_matrix.get('visual_smoke_lane')}",
                f"- `route_class_counts`: {json.dumps(validation_matrix.get('route_class_counts') or {}, sort_keys=True)}",
                f"- `browser_visual_requirement_status_counts`: {json.dumps(validation_matrix.get('browser_visual_requirement_status_counts') or {}, sort_keys=True)}",
            ]
        )
        for row in validation_matrix.get("acceptance_commands", []):
            if isinstance(row, Mapping):
                lines.append(f"- `{row.get('id')}`: `{row.get('command')}`")
        lines.append("")

    if graph["drift_signals"]:
        lines.append("## Drift signals")
        for sig in graph["drift_signals"]:
            ev = sig.get("evidence", {})
            where = f"{ev.get('file','?')}:{ev.get('line','?')}" if ev else "?"
            lines.append(f"- **{sig['kind']}** — {json.dumps({k:v for k,v in sig.items() if k!='evidence'})} @ {where}")
        lines.append("")

    lines.append("## Views")
    for v in graph["views"]:
        culdesac = ""
        if v["cul_de_sac"]["effective"]:
            culdesac = (
                f" _(cul-de-sac: {v['cul_de_sac']['reason']})_"
                if v["cul_de_sac"]["declared"]
                else " _(undeclared dead-end — drift)_"
            )
        route_disp = f" `{v['route']}`" if v["route"] else ""
        entry_disp = (
            f" → open `{v['entry_route']}`"
            if v.get("entry_route") and v.get("entry_route") != v.get("route")
            else ""
        )
        timing = (v.get("capture") or {}).get("load_timing") if v.get("capture") else None
        timing_disp = (
            f" _(latest load {timing.get('latest_load_ms')}ms)_"
            if isinstance(timing, dict) and timing.get("latest_load_ms") is not None
            else ""
        )
        lines.append(
            f"- **{v['label']}** (`{v['id']}`, {v['kind']}){route_disp} — "
            f"fanout {v['fanout_count']}, fanin {v['fanin_count']}, "
            f"pathway {v.get('pathway_count', 0)}{entry_disp}{timing_disp}{culdesac}"
        )
    lines.append("")

    lines.append("## Edges")
    for e in graph["edges"]:
        group = f" group={e['group']}" if "group" in e else ""
        label = f" — {e.get('label')}" if e.get("label") else ""
        lines.append(f"- `{e['from']}` → `{e['to']}` via {e['mechanism']}{group}{label}")
    lines.append("")

    audit = graph.get("surface_relation_audit") if isinstance(graph.get("surface_relation_audit"), dict) else {}
    if audit:
        lines.append("## Surface Relation Audit")
        posture_counts: dict[str, int] = {}
        for row in audit.get("surfaces", []):
            if not isinstance(row, dict):
                continue
            posture = str(row.get("posture") or "unknown")
            posture_counts[posture] = posture_counts.get(posture, 0) + 1
        for posture, count in sorted(posture_counts.items()):
            lines.append(f"- `{posture}`: {count}")
        lines.append("")

    return "\n".join(lines)


def _display_path(path: Path) -> str:
    try:
        return _repo_rel(path)
    except ValueError:
        return str(path)


def _edge_signature(edge: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(edge.get("from") or ""),
        str(edge.get("to") or ""),
        str(edge.get("mechanism") or ""),
        str(edge.get("group") or ""),
    )


def _projection_output_drift(
    graph: dict[str, Any],
    *,
    graph_path: Path = OUTPUT_JSON,
    audit_path: Path = OUTPUT_SURFACE_RELATION_AUDIT,
    snapshot_path: Path = OUTPUT_SNAPSHOT,
    mission_control_path: Path = OUTPUT_MISSION_CONTROL,
    scenario_frontier_path: Path = OUTPUT_SCENARIO_FRONTIER,
) -> list[dict[str, Any]]:
    """Detect stale generated artifacts without comparing volatile timestamps."""
    drift: list[dict[str, Any]] = []
    saved_graph = _load_output_json(graph_path)
    if saved_graph is None:
        drift.append({"path": _display_path(graph_path), "reason": "missing_or_invalid_artifact"})
    else:
        if saved_graph.get("schema_version") != graph.get("schema_version"):
            drift.append(
                {
                    "path": _display_path(graph_path),
                    "reason": "schema_version_changed",
                    "expected": graph.get("schema_version"),
                    "actual": saved_graph.get("schema_version"),
                }
            )
        if saved_graph.get("counts") != graph.get("counts"):
            drift.append({"path": _display_path(graph_path), "reason": "counts_changed"})
        saved_view_ids = sorted(
            str(row.get("id"))
            for row in (saved_graph.get("views") or [])
            if isinstance(row, Mapping) and isinstance(row.get("id"), str)
        )
        live_view_ids = sorted(
            str(row.get("id"))
            for row in (graph.get("views") or [])
            if isinstance(row, Mapping) and isinstance(row.get("id"), str)
        )
        if saved_view_ids != live_view_ids:
            drift.append(
                {
                    "path": _display_path(graph_path),
                    "reason": "view_id_set_changed",
                    "expected_count": len(live_view_ids),
                    "actual_count": len(saved_view_ids),
                    "missing_in_artifact": sorted(set(live_view_ids) - set(saved_view_ids))[:20],
                    "extra_in_artifact": sorted(set(saved_view_ids) - set(live_view_ids))[:20],
                }
            )
        saved_edges = sorted(
            _edge_signature(row)
            for row in (saved_graph.get("edges") or [])
            if isinstance(row, Mapping)
        )
        live_edges = sorted(
            _edge_signature(row)
            for row in (graph.get("edges") or [])
            if isinstance(row, Mapping)
        )
        if saved_edges != live_edges:
            drift.append(
                {
                    "path": _display_path(graph_path),
                    "reason": "edge_set_changed",
                    "expected_count": len(live_edges),
                    "actual_count": len(saved_edges),
                }
            )
        saved_hashes = (
            saved_graph.get("source_hashes")
            if isinstance(saved_graph.get("source_hashes"), Mapping)
            else {}
        )
        live_hashes = (
            graph.get("source_hashes")
            if isinstance(graph.get("source_hashes"), Mapping)
            else {}
        )
        if saved_hashes.get("render_load_index") != live_hashes.get("render_load_index"):
            drift.append(
                {
                    "path": _display_path(graph_path),
                    "reason": "render_status_source_changed",
                    "message": "navigation_graph render status is stale; run frontend_nav_graph.py --write",
                    "expected": live_hashes.get("render_load_index"),
                    "actual": saved_hashes.get("render_load_index"),
                }
            )
        saved_render_status_source = saved_graph.get("render_status_source")
        if not isinstance(saved_render_status_source, Mapping):
            drift.append(
                {
                    "path": _display_path(graph_path),
                    "reason": "render_status_source_missing",
                    "message": "navigation_graph render status is stale; run frontend_nav_graph.py --write",
                }
            )
        authority = None
        live_render_status_source = graph.get("render_status_source")
        if isinstance(live_render_status_source, Mapping):
            authority = live_render_status_source.get("authority")
        uses_tracked_latest_projection_authority = (
            isinstance(authority, Mapping)
            and authority.get("mode") == "committed_projection_source_latest_index_dirty"
        )
        if (
            SOURCE_RENDER_LOAD_INDEX.exists()
            and graph_path.exists()
            and not uses_tracked_latest_projection_authority
        ):
            try:
                if SOURCE_RENDER_LOAD_INDEX.stat().st_mtime_ns > graph_path.stat().st_mtime_ns:
                    drift.append(
                        {
                            "path": _display_path(graph_path),
                            "reason": "render_status_source_stale",
                            "message": "navigation_graph render status is stale; run frontend_nav_graph.py --write",
                            "render_load_index_mtime_ns": SOURCE_RENDER_LOAD_INDEX.stat().st_mtime_ns,
                            "navigation_graph_mtime_ns": graph_path.stat().st_mtime_ns,
                        }
                    )
            except OSError:
                pass

    live_audit = graph.get("surface_relation_audit")
    saved_audit = _load_output_json(audit_path)
    if isinstance(live_audit, Mapping):
        if saved_audit is None:
            drift.append({"path": _display_path(audit_path), "reason": "missing_or_invalid_artifact"})
        else:
            if saved_audit.get("schema_version") != live_audit.get("schema_version"):
                drift.append(
                    {
                        "path": _display_path(audit_path),
                        "reason": "schema_version_changed",
                        "expected": live_audit.get("schema_version"),
                        "actual": saved_audit.get("schema_version"),
                    }
                )
            saved_surface_ids = sorted(
                str(row.get("surface_id"))
                for row in (saved_audit.get("surfaces") or [])
                if isinstance(row, Mapping) and isinstance(row.get("surface_id"), str)
            )
            live_surface_ids = sorted(
                str(row.get("surface_id"))
                for row in (live_audit.get("surfaces") or [])
                if isinstance(row, Mapping) and isinstance(row.get("surface_id"), str)
            )
            if saved_surface_ids != live_surface_ids:
                drift.append(
                    {
                        "path": _display_path(audit_path),
                        "reason": "surface_id_set_changed",
                        "expected_count": len(live_surface_ids),
                        "actual_count": len(saved_surface_ids),
                        "missing_in_artifact": sorted(set(live_surface_ids) - set(saved_surface_ids))[:20],
                        "extra_in_artifact": sorted(set(saved_surface_ids) - set(live_surface_ids))[:20],
                    }
                )
            saved_posture_counts = Counter(
                str(row.get("posture") or "unknown")
                for row in saved_audit.get("surfaces", [])
                if isinstance(row, Mapping) and isinstance(row.get("surface_id"), str)
            )
            live_posture_counts = Counter(
                str(row.get("posture") or "unknown")
                for row in live_audit.get("surfaces", [])
                if isinstance(row, Mapping) and isinstance(row.get("surface_id"), str)
            )
            if saved_posture_counts != live_posture_counts:
                drift.append(
                    {
                        "path": _display_path(audit_path),
                        "reason": "surface_posture_counts_changed",
                        "expected": dict(sorted(live_posture_counts.items())),
                        "actual": dict(sorted(saved_posture_counts.items())),
                    }
                )

    if not snapshot_path.exists():
        drift.append({"path": _display_path(snapshot_path), "reason": "missing_artifact"})
    else:
        try:
            snapshot_text = snapshot_path.read_text(encoding="utf-8")
        except OSError:
            snapshot_text = ""
        if isinstance(live_audit, Mapping) and "## Surface Relation Audit" not in snapshot_text:
            drift.append(
                {
                    "path": _display_path(snapshot_path),
                    "reason": "snapshot_missing_surface_relation_audit_section",
                }
            )

    live_mission_control = build_navigation_mission_control_packet(graph)
    saved_mission_control = _load_output_json(mission_control_path)
    if saved_mission_control is None:
        drift.append({"path": _display_path(mission_control_path), "reason": "missing_or_invalid_artifact"})
    else:
        live_graph_ref = (
            live_mission_control.get("graph")
            if isinstance(live_mission_control.get("graph"), Mapping)
            else {}
        )
        saved_graph_ref = (
            saved_mission_control.get("graph")
            if isinstance(saved_mission_control.get("graph"), Mapping)
            else {}
        )
        live_suite = (
            live_mission_control.get("scenario_suite")
            if isinstance(live_mission_control.get("scenario_suite"), Mapping)
            else {}
        )
        saved_suite = (
            saved_mission_control.get("scenario_suite")
            if isinstance(saved_mission_control.get("scenario_suite"), Mapping)
            else {}
        )
        comparisons = (
            ("contract", live_mission_control.get("contract"), saved_mission_control.get("contract")),
            ("graph_hash", live_graph_ref.get("hash"), saved_graph_ref.get("hash")),
            ("scenario_suite_status", live_suite.get("status"), saved_suite.get("status")),
            (
                "scenario_count",
                len(live_suite.get("scenarios") or []),
                len(saved_suite.get("scenarios") or []),
            ),
        )
        for reason, expected, actual in comparisons:
            if expected != actual:
                drift.append(
                    {
                        "path": _display_path(mission_control_path),
                        "reason": f"{reason}_changed",
                        "expected": expected,
                        "actual": actual,
                    }
                )

    live_frontier = build_wayfinding_scenario_frontier(graph)
    saved_frontier = _load_output_json(scenario_frontier_path)
    if saved_frontier is None:
        drift.append({"path": _display_path(scenario_frontier_path), "reason": "missing_or_invalid_artifact"})
    else:
        live_frontier_rows = live_frontier.get("frontier") if isinstance(live_frontier.get("frontier"), list) else []
        saved_frontier_rows = saved_frontier.get("frontier") if isinstance(saved_frontier.get("frontier"), list) else []
        comparisons = (
            ("contract", live_frontier.get("contract"), saved_frontier.get("contract")),
            ("graph_hash", live_frontier.get("graph_hash"), saved_frontier.get("graph_hash")),
            ("frontier_hash", live_frontier.get("frontier_hash"), saved_frontier.get("frontier_hash")),
            ("frontier_count", len(live_frontier_rows), len(saved_frontier_rows)),
        )
        for reason, expected, actual in comparisons:
            if expected != actual:
                drift.append(
                    {
                        "path": _display_path(scenario_frontier_path),
                        "reason": f"{reason}_changed",
                        "expected": expected,
                        "actual": actual,
                    }
                )
    return drift


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main() -> int:
    p = argparse.ArgumentParser(
        description="Frontend navigation graph extractor (drift-proof, evidence-backed)."
    )
    p.add_argument("--print", dest="print_json", action="store_true",
                   help="Emit full JSON graph to stdout")
    p.add_argument("--dry-run", action="store_true", help="Print summary counts only")
    p.add_argument("--write", action="store_true", help="Write canonical JSON + snapshot")
    p.add_argument("--check", action="store_true",
                   help="Exit non-zero when drift_signals or generated output drift is non-empty")
    p.add_argument("--view", metavar="ID", help="Dump one view's record (by id or route)")
    p.add_argument("--edges", metavar="ID", help="Show inbound + outbound edges for one view")
    p.add_argument("--wayfind", nargs=2, metavar=("FROM", "TO"),
                   help="Plan an executable read-only route from one frontend view to another")
    p.add_argument("--wayfind-mode", choices=("direct", "embodied", "hybrid"), default="direct",
                   help="Planner mode: direct route arrival, embodied source-backed invocation, or hybrid scenario")
    p.add_argument("--capability-matrix", action="store_true",
                   help="Emit generated wayfinding capability coverage matrix")
    p.add_argument("--scenario-suite", action="store_true",
                   help="Emit canonical wayfinding scenario suite")
    p.add_argument("--scenario-frontier", action="store_true",
                   help="Emit generated wayfinding scenario frontier")
    p.add_argument("--mission-control", action="store_true",
                   help="Emit generated Station navigation Mission Control packet")
    p.add_argument("--pathway-audit", action="store_true",
                   help="Emit the pathway hover audit and fail if substantive routable views have zero pathway edges")
    p.add_argument("--cul-de-sacs", action="store_true",
                   help="List declared cul-de-sacs + undeclared dead-ends")
    p.add_argument("--drift", action="store_true", help="List drift signals only")
    p.add_argument("--agent-packet", metavar="ID",
                   help="Agent-oriented packet: view record + outbound neighbours + capture contract")
    p.add_argument("--root-navigator-handoff", action="store_true",
                   help="Emit the Root Navigator Claude frontend handoff packet")
    p.add_argument("--health-report", action="store_true",
                   help="Emit frontend semantic health report")
    p.add_argument("--semantic-check", action="store_true",
                   help="Check semantic_layer.v1.json coverage against the navigation graph")
    p.add_argument("--output", metavar="PATH", help="Override output path for --write")

    args = p.parse_args()
    graph = build_graph()

    def _resolve_view(target: str) -> dict[str, Any] | None:
        return next(
            (
                v
                for v in graph["views"]
                if v["id"] == target
                or v.get("route") == target
                or v.get("entry_route") == target
                or target in (v.get("route_aliases") or [])
            ),
            None,
        )

    if args.dry_run and not args.write:
        print(json.dumps({"counts": graph["counts"], "compression": graph["compression"]}, indent=2))
        return 0

    if args.view:
        target = args.view
        match = _resolve_view(target)
        if match is None:
            print(json.dumps({"error": "view_not_found", "query": target}), file=sys.stderr)
            return 2
        print(json.dumps(match, indent=2))
        return 0

    if args.edges:
        target = args.edges
        out_edges = [e for e in graph["edges"] if e["from"] == target]
        in_edges = [e for e in graph["edges"] if e["to"] == target]
        print(json.dumps({"outbound": out_edges, "inbound": in_edges}, indent=2))
        return 0

    if args.wayfind:
        plan = plan_wayfinding(graph, args.wayfind[0], args.wayfind[1], mode=args.wayfind_mode)
        print(json.dumps(plan, indent=2))
        if plan.get("blocked"):
            return 1
        return 0

    if args.capability_matrix:
        print(json.dumps(build_wayfinding_capability_matrix(graph), indent=2))
        return 0

    if args.scenario_suite:
        print(json.dumps(load_wayfinding_scenario_suite(), indent=2))
        return 0

    if args.scenario_frontier:
        print(json.dumps(build_wayfinding_scenario_frontier(graph), indent=2))
        return 0

    if args.mission_control:
        print(json.dumps(build_navigation_mission_control_packet(graph), indent=2))
        return 0

    if args.pathway_audit:
        audit = graph.get("pathway_audit") if isinstance(graph.get("pathway_audit"), Mapping) else {}
        print(json.dumps(audit, indent=2))
        return 0 if audit.get("status") == "ok" else 1

    if args.cul_de_sacs:
        rows = [
            {
                "id": v["id"],
                "label": v["label"],
                "route": v["route"],
                "declared": v["cul_de_sac"]["declared"],
                "reason": v["cul_de_sac"]["reason"],
            }
            for v in graph["views"]
            if v["cul_de_sac"]["effective"] and v["kind"] == "page"
        ]
        print(json.dumps(rows, indent=2))
        return 0

    if args.drift:
        print(json.dumps(graph["drift_signals"], indent=2))
        return 1 if graph["drift_signals"] else 0

    if args.health_report:
        print(json.dumps(frontend_surface_contracts.build_health_report(REPO_ROOT), indent=2))
        return 0

    if args.semantic_check:
        payload = frontend_surface_contracts.semantic_check(
            REPO_ROOT,
            write_missing_stub=True,
        )
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("ok") else 1

    if args.agent_packet:
        target = args.agent_packet
        match = _resolve_view(target)
        if match is None:
            print(json.dumps({"error": "view_not_found", "query": target}), file=sys.stderr)
            return 2
        packet = frontend_surface_contracts.build_surface_agent_packet(REPO_ROOT, match["id"])
        print(json.dumps(packet, indent=2))
        return 0

    if args.root_navigator_handoff:
        print(
            json.dumps(
                frontend_surface_contracts.build_root_navigator_frontend_handoff_packet(REPO_ROOT),
                indent=2,
            )
        )
        return 0

    if args.write:
        target_path = Path(args.output) if args.output else OUTPUT_JSON
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
        audit_path = OUTPUT_SURFACE_RELATION_AUDIT
        audit_path.write_text(
            json.dumps(graph["surface_relation_audit"], indent=2) + "\n",
            encoding="utf-8",
        )
        capability_matrix = build_wayfinding_capability_matrix(graph)
        OUTPUT_CAPABILITY_MATRIX.write_text(
            json.dumps(capability_matrix, indent=2) + "\n",
            encoding="utf-8",
        )
        scenario_frontier = build_wayfinding_scenario_frontier(graph)
        OUTPUT_SCENARIO_FRONTIER.write_text(
            json.dumps(scenario_frontier, indent=2) + "\n",
            encoding="utf-8",
        )
        mission_control = build_navigation_mission_control_packet(graph)
        OUTPUT_MISSION_CONTROL.write_text(
            json.dumps(mission_control, indent=2) + "\n",
            encoding="utf-8",
        )
        snapshot_path = (
            target_path.with_suffix(".snapshot.md")
            if target_path.suffix == ".json"
            else OUTPUT_SNAPSHOT
        )
        snapshot_path.write_text(_render_snapshot_md(graph), encoding="utf-8")
        print(json.dumps({
            "written": str(target_path.relative_to(REPO_ROOT)),
            "surface_relation_audit": str(audit_path.relative_to(REPO_ROOT)),
            "capability_matrix": str(OUTPUT_CAPABILITY_MATRIX.relative_to(REPO_ROOT)),
            "scenario_frontier": str(OUTPUT_SCENARIO_FRONTIER.relative_to(REPO_ROOT)),
            "mission_control": str(OUTPUT_MISSION_CONTROL.relative_to(REPO_ROOT)),
            "snapshot": str(snapshot_path.relative_to(REPO_ROOT)),
            "counts": graph["counts"],
        }, indent=2))
        if args.check and graph["drift_signals"]:
            return 1
        return 0

    if args.check:
        projection_output_drift = _projection_output_drift(graph)
        if graph["drift_signals"] or projection_output_drift:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "drift": graph["drift_signals"],
                        "projection_output_drift": projection_output_drift,
                    },
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 1
        print(json.dumps({"ok": True, "counts": graph["counts"], "projection_output_drift": []}, indent=2))
        return 0

    if args.print_json:
        print(json.dumps(graph, indent=2))
        return 0

    # Default: compact summary
    print(json.dumps({
        "counts": graph["counts"],
        "compression": graph["compression"],
        "wayfinding_contract": graph.get("wayfinding_contract"),
        "invocation_contract": graph.get("invocation_contract"),
        "wayfinding": graph.get("wayfinding"),
        "drift_signals": graph["drift_signals"][:5],
        "hint": "Use --print / --write / --view <id> / --wayfind <from> <to> / --capability-matrix / --scenario-frontier / --mission-control / --cul-de-sacs / --drift / --agent-packet <id>",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
