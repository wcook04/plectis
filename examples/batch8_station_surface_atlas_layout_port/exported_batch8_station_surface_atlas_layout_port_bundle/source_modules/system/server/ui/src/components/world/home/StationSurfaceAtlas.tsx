// [PURPOSE] Atlas Surface (v3 — semantic focus map). Atlas is the authority;
// `/station` is a routing alias that mounts this surface for compatibility.
// Per std_station_aesthetic.json::P9_station_is_compatibility_alias.
//
// Home is the map of the frontend, not another view. This is a 2D graph of
// all Atlas views/routes grouped by shell_group, with explicit edges
// pulled from worldModel.navigation_graph (the substrate publishes the
// topology with backend relation metadata: label/category/description/
// presentation_role/rank/weight).
//
// v3 thesis: Atlas is a wayfinding map with focus+context, not a static
// node-link diagram. The node layer IS the map; the edge layer is
// explanation on demand. Per Shneiderman's visual information-seeking
// mantra: overview first, zoom/filter, details on demand.
//
// Three interaction modes:
//   Rest        — All nodes visible, only structural skeleton edges showing.
//                 No edge labels. Cards are opaque.
//   Hover       — 1-hop ego network: focused node 1.0 opacity + gold halo,
//                 adjacent nodes 0.78, unrelated drops to 0.10. Active
//                 edges get relation palette + backend label.
//   Pinned      — Right-click pins focus so the operator can study a
//                 neighborhood. Escape or click pane clears.
//
// Click semantics:
//   Hover         → preview ego network
//   Left-click    → navigate (Home is an app launcher)
//   Right-click   → pin focus (stays in the map)
//   Alt/Meta+click→ pin focus without navigating (keyboard equivalent)
//   Escape        → clear pin
//
// Layout:
//   Top strip            — Wordmark, search, density mode, refresh, UTC.
//   Center dominant      — ReactFlow graph. Nodes coloured by shell_group;
//                          column headers carry operator-job description.
//   Left rail            — Categories + capture legend + density help.
//   Right detail panel   — Selected view card with connected-by-how grouping.
//   Bottom action bar    — Open selected / Command palette / Legacy / Refresh.
//
// Composition source: navigation/surfaces.ts (semantic registry) +
// worldModel.navigation_graph (edges with backend relation metadata).
// No new route registry invented. The graph IS the data.
//
// Authority posture: frontend adapter view over the existing nav-graph
// projection. The substrate (frontend_nav_graph.py +
// state/frontend_navigation/navigation_graph.json) remains the authority.
// Per cap_station_surface_atlas_focus_legibility_interaction_v1.
import { memo, useCallback, useDeferredValue, useEffect, useLayoutEffect, useMemo, useRef, useState, useTransition } from 'react';
import type { MouseEvent as ReactMouseEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ReactFlow, {
  Background,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  Handle,
  Position,
  ReactFlowProvider,
  getSmoothStepPath,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  routeOrthogonal,
  pointsToRoundedPath,
  polylineHitsObstacle,
  chordCrossesAnyObstacle,
  type RObstacle,
  type RSide,
} from './atlasEdgeRouter';
import clsx from 'clsx';
import {
  ArrowDownRight,
  ArrowUpLeft,
  Boxes,
  CandlestickChart,
  CircleDot,
  Compass,
  Eye,
  ExternalLink,
  Filter,
  GitBranch,
  Layers,
  Map as MapIcon,
  MousePointer2,
  Network,
  Pin,
  Radio,
  RefreshCw,
  Search,
  Terminal,
  Workflow,
  X,
  type LucideIcon,
} from 'lucide-react';
import { useZenith } from '../../../stores/useZenith';
import { useStation } from '../../../stores/useStation';
import {
  getAllSurfaces,
  getShellSurfaceGroups,
  type ShellSurfaceGroupId,
} from '../../../navigation/surfaces';
import {
  isCaptureModeEnabled,
  useCaptureBudgetBlocker,
  useCaptureDiagnostic,
} from '../../../lib/captureMode';
import { api } from '../../../api';
import type {
  StationAliveCockpitRow,
  StationAliveCockpitSnapshot,
  WorldModelNavigationEdgesResponse,
  WorldModelNavigationGraphEdge,
  WorldModelNavigationGraphEvidenceCoverage,
  WorldModelNavigationGraphGroupFlow,
  WorldModelNavigationGraphPathwayAudit,
  WorldModelNavigationGraphPresentationRole,
  WorldModelNavigationGraphReadModelContract,
  WorldModelNavigationGraphReadModelState,
  WorldModelNavigationGraphRelationSummary,
  WorldModelNavigationGraphSampleEdge,
} from '../../../api';
import {
  ATLAS_GRAPH_FIRST_DRAWER_RAIL_WIDTH,
  ATLAS_GRAPH_FIRST_DRAWER_WIDTH,
  ATLAS_GRAPH_FIRST_RAIL_TO_STAGE_MAX,
  shouldUseGraphFirstDrawers,
  type AtlasSceneViewport,
} from './stationSurfaceAtlasScenePolicy';

type AtlasPerfRenderKey =
  | 'AtlasNodeRenderer'
  | 'AtlasRelationEdge'
  | 'ColumnHeaderRenderer'
  | 'AtlasGroupBackplateRenderer'
  | 'RelationLegend'
  | 'DetailPanel'
  | 'GroupFlowDrillthrough'
  | 'AtlasInteractionGuide'
  | 'GroupRail';

type AtlasPerfEventKey =
  | 'nodeMouseEnter'
  | 'nodeMouseLeave'
  | 'nodeClick'
  | 'nodeContextMenu'
  | 'edgeClick'
  | 'paneClick'
  | 'paneContextMenu'
  | 'moveStart'
  | 'moveEnd'
  | 'relationSelect'
  | 'groupFlowSelect'
  | 'sampleEdgeSelect'
  | 'searchChange';

interface StationSurfaceAtlasPerfSurface {
  schema: 'station_surface_atlas_perf_surface_v1';
  createdAt: string;
  renders: Partial<Record<AtlasPerfRenderKey, number>>;
  events: Partial<Record<AtlasPerfEventKey, number>>;
  graph: {
    rfNodes: number;
    rfEdges: number;
    visibleCanvasEdgeCount: number;
    sourceEdgeCount: number;
    relationRows: number;
    groupFlowRows: number;
    moving: boolean;
    railTransitionPending: boolean;
    searchDeferred: boolean;
  };
  reset: () => void;
  snapshot: () => {
    schema: 'station_surface_atlas_perf_snapshot_v1';
    createdAt: string;
    renders: Partial<Record<AtlasPerfRenderKey, number>>;
    events: Partial<Record<AtlasPerfEventKey, number>>;
    graph: StationSurfaceAtlasPerfSurface['graph'];
  };
}

declare global {
  interface Window {
    __ZENITH_STATION_SURFACE_ATLAS_PERF__?: StationSurfaceAtlasPerfSurface;
  }
}

function getStationSurfaceAtlasPerf(): StationSurfaceAtlasPerfSurface | null {
  if (typeof window === 'undefined') return null;
  const existing = window.__ZENITH_STATION_SURFACE_ATLAS_PERF__;
  if (existing) return existing;
  const surface: StationSurfaceAtlasPerfSurface = {
    schema: 'station_surface_atlas_perf_surface_v1',
    createdAt: new Date().toISOString(),
    renders: {},
    events: {},
    graph: {
      rfNodes: 0,
      rfEdges: 0,
      visibleCanvasEdgeCount: 0,
      sourceEdgeCount: 0,
      relationRows: 0,
      groupFlowRows: 0,
      moving: false,
      railTransitionPending: false,
      searchDeferred: false,
    },
    reset() {
      this.createdAt = new Date().toISOString();
      this.renders = {};
      this.events = {};
    },
    snapshot() {
      return {
        schema: 'station_surface_atlas_perf_snapshot_v1',
        createdAt: this.createdAt,
        renders: { ...this.renders },
        events: { ...this.events },
        graph: { ...this.graph },
      };
    },
  };
  window.__ZENITH_STATION_SURFACE_ATLAS_PERF__ = surface;
  return surface;
}

function recordAtlasRender(key: AtlasPerfRenderKey): void {
  const perf = getStationSurfaceAtlasPerf();
  if (!perf) return;
  perf.renders[key] = (perf.renders[key] ?? 0) + 1;
}

function recordAtlasEvent(key: AtlasPerfEventKey): void {
  const perf = getStationSurfaceAtlasPerf();
  if (!perf) return;
  perf.events[key] = (perf.events[key] ?? 0) + 1;
}

function updateAtlasPerfGraph(graph: Partial<StationSurfaceAtlasPerfSurface['graph']>): void {
  const perf = getStationSurfaceAtlasPerf();
  if (!perf) return;
  perf.graph = { ...perf.graph, ...graph };
}

function interactionNowMs(): number {
  if (typeof window === 'undefined' || !window.performance) return Date.now();
  return window.performance.now();
}

const ATLAS_HOVER_INTENT_MS = 70;
type AtlasRailRegionMode = 'persistent' | 'overlay' | 'collapsed';
type AtlasSceneCandidateId =
  | 'current_persistent_dual_rails'
  | 'right_rail_collapsed'
  | 'graph_first_drawers';

function initialAtlasSceneViewport(): AtlasSceneViewport {
  if (typeof window === 'undefined') return { width: 1440, height: 900 };
  return {
    width: window.innerWidth || document.documentElement.clientWidth || 1440,
    height: window.innerHeight || document.documentElement.clientHeight || 900,
  };
}

// ---------------------------------------------------------------------------
// Node + edge shapes — derived from worldModel.navigation_graph when present,
// fall back to navigation/surfaces.ts so the atlas renders even without
// backend data.
// ---------------------------------------------------------------------------

interface AtlasView {
  id: string;
  label: string;
  route: string;
  entryRoute: string;
  purpose: string;
  kind: string;
  shellGroup: ShellSurfaceGroupId | 'unassigned';
  stationGroup: string | null;
  captureSlug: string | null;
  captureLatestStatus: string | null;
  captureLatestLoadMs: number | null;
  captureSampleCount: number;
  fanout: number;
  fanin: number;
  // Pathway counts come from the backend pathway hover contract
  // (frontend_navigation_pathway_hover_contract_v1, plumbed via
  // world_model.navigation_graph.views[].pathway_*). Pathway edges are the
  // ones the canvas paints on hover in 'clean' mode; fanin/fanout above
  // include folded membership edges that never draw. Surfacing both lets
  // the operator see "how many neighbours light up on hover" (pathway) vs
  // "how many neighbours exist at all" (fanin+fanout).
  pathwayCount: number;
  pathwayFanout: number;
  pathwayFanin: number;
  culDeSacEffective: boolean;
  isLegacy: boolean;
  evidenceFile: string | null;
  posture: string;
  primaryComponent: string | null;
  backendEndpoints: string[];
  storeSlices: string[];
  sharedComponents: string[];
  substrateBindings: string[];
  authorityNote: string | null;
  semanticEvidenceRefs: string[];
}

interface AtlasEdge {
  edgeKey: string | null;
  edgeKeySource: 'backend' | 'frontend_fallback';
  source: string;
  target: string;
  relation: string;
  label: string;
  category: string | null;
  description: string | null;
  presentationRole: WorldModelNavigationGraphPresentationRole;
  presentationRoleSource: 'backend' | 'frontend_fallback';
  group: string | null;
  rank: number | null;
  weight: number | null;
  evidenceRefs: string[];
}

// Backend-owned stable edge key. The fallback exists only for old payload
// compatibility and is surfaced in addressability receipts.
function edgeKeyFor(edge: AtlasEdge): string {
  if (edge.edgeKey) return edge.edgeKey;
  const cat = edge.category ?? '';
  return `${edge.source}|${edge.target}|${edge.relation}|${cat}`;
}

// ---------------------------------------------------------------------------
// Relation palette — pairs each backend mechanism with a color, line style,
// priority rank, and short label suitable for hover badges. The backend
// already projects label/category/description/rank/weight via
// system/server/world_model.py::NAVIGATION_EDGE_MECHANISM_META; this palette
// is the visual half of that contract. Color is paired with dash + priority
// so relation meaning is never encoded in hue alone.
// ---------------------------------------------------------------------------
interface RelationStyle {
  /** Solid stroke when edge is active (hover / pinned ego-network member). */
  activeStroke: string;
  /** Faint stroke when shown as background structural skeleton. */
  restStroke: string;
  /** SVG stroke-dasharray; undefined = solid line. */
  dash: string | undefined;
  /** Drawing priority — lower means painted on top of higher-rank edges. */
  priority: number;
  /** Short hover badge — used only when backend label is missing. */
  fallbackLabel: string;
  /** Category tone — drives the right-panel relation-group header colour. */
  tone: 'gold' | 'violet' | 'sky' | 'sage' | 'cyan' | 'rose' | 'gray';
}

const RELATION_STYLE: Record<string, RelationStyle> = {
  // Declared outbound edges — the highest-authority relation. Saturated gold.
  explicit: {
    activeStroke: 'rgba(244, 206, 120, 0.95)',
    restStroke: 'rgba(244, 206, 120, 0.18)',
    dash: undefined,
    priority: 1,
    fallbackLabel: 'declared edge',
    tone: 'gold',
  },
  outbound_declaration: {
    activeStroke: 'rgba(244, 206, 120, 0.95)',
    restStroke: 'rgba(244, 206, 120, 0.16)',
    dash: undefined,
    priority: 1,
    fallbackLabel: 'declared edge',
    tone: 'gold',
  },
  // Overlay anchors — modal/drawer hosted on this page. Violet short-dash.
  overlay_anchor: {
    activeStroke: 'rgba(192, 164, 201, 0.88)',
    restStroke: 'rgba(192, 164, 201, 0.10)',
    dash: '4 3',
    priority: 2,
    fallbackLabel: 'overlay host',
    tone: 'violet',
  },
  overlay_of: {
    activeStroke: 'rgba(192, 164, 201, 0.88)',
    restStroke: 'rgba(192, 164, 201, 0.10)',
    dash: '4 3',
    priority: 2,
    fallbackLabel: 'overlay',
    tone: 'violet',
  },
  route_hierarchy: {
    activeStroke: 'rgba(244, 206, 120, 0.86)',
    restStroke: 'rgba(244, 206, 120, 0.11)',
    dash: undefined,
    priority: 2,
    fallbackLabel: 'route child',
    tone: 'gold',
  },
  legacy_or_workbench_of: {
    activeStroke: 'rgba(247, 144, 92, 0.82)',
    restStroke: 'rgba(247, 144, 92, 0.08)',
    dash: '6 3',
    priority: 3,
    fallbackLabel: 'workbench of',
    tone: 'rose',
  },
  shared_backend_api: {
    activeStroke: 'rgba(132, 199, 207, 0.84)',
    restStroke: 'rgba(132, 199, 207, 0.07)',
    dash: '5 3',
    priority: 4,
    fallbackLabel: 'shares API',
    tone: 'cyan',
  },
  shared_component: {
    activeStroke: 'rgba(154, 183, 212, 0.82)',
    restStroke: 'rgba(154, 183, 212, 0.07)',
    dash: '3 3',
    priority: 5,
    fallbackLabel: 'shares component',
    tone: 'sky',
  },
  // Station group siblings — muted sky blue, solid.
  station_group: {
    activeStroke: 'rgba(154, 183, 212, 0.82)',
    restStroke: 'rgba(154, 183, 212, 0.08)',
    dash: undefined,
    priority: 20,
    fallbackLabel: 'station group',
    tone: 'sky',
  },
  // Station lens menu — cyan dashed (lens-level relation, not declared).
  station_lens_menu: {
    activeStroke: 'rgba(132, 199, 207, 0.78)',
    restStroke: 'rgba(132, 199, 207, 0.07)',
    dash: '6 4',
    priority: 40,
    fallbackLabel: 'lens menu',
    tone: 'cyan',
  },
  // Shell group — broadest structural relation. Muted sage; lowest weight.
  shell_group: {
    activeStroke: 'rgba(123, 199, 142, 0.62)',
    restStroke: 'rgba(123, 199, 142, 0.05)',
    dash: undefined,
    priority: 30,
    fallbackLabel: 'shell group',
    tone: 'sage',
  },
  // Adjacency-fallback (when backend hasn't projected mechanism yet).
  adjacency: {
    activeStroke: 'rgba(192, 199, 180, 0.50)',
    restStroke: 'rgba(192, 199, 180, 0.04)',
    dash: '2 4',
    priority: 6,
    fallbackLabel: 'navigation adjacency',
    tone: 'gray',
  },
  command_palette: {
    activeStroke: 'rgba(123, 199, 142, 0.65)',
    restStroke: 'rgba(123, 199, 142, 0.05)',
    dash: '2 3',
    priority: 7,
    fallbackLabel: 'palette',
    tone: 'sage',
  },
  recent_surface: {
    activeStroke: 'rgba(192, 199, 180, 0.55)',
    restStroke: 'rgba(192, 199, 180, 0.04)',
    dash: '1 4',
    priority: 8,
    fallbackLabel: 'recent',
    tone: 'gray',
  },
  redirect: {
    activeStroke: 'rgba(247, 144, 92, 0.78)',
    restStroke: 'rgba(247, 144, 92, 0.08)',
    dash: '6 3',
    priority: 9,
    fallbackLabel: 'redirect',
    tone: 'rose',
  },
  alert_route: {
    activeStroke: 'rgba(244, 63, 94, 0.85)',
    restStroke: 'rgba(244, 63, 94, 0.08)',
    dash: undefined,
    priority: 10,
    fallbackLabel: 'alert route',
    tone: 'rose',
  },
  unknown: {
    activeStroke: 'rgba(160, 175, 145, 0.55)',
    restStroke: 'rgba(160, 175, 145, 0.04)',
    dash: '2 4',
    priority: 99,
    fallbackLabel: 'related',
    tone: 'gray',
  },
};

function styleForMechanism(mechanism: string): RelationStyle {
  return RELATION_STYLE[mechanism] ?? RELATION_STYLE.unknown;
}

// Compact operator-facing label for a relation mechanism. The backend supplies
// human prose like "SAME STATION GROUP" / "STATION LENS MENU" / "SHARES API",
// which is correct for debug/tooltip but visually heavy when stacked in the
// right-rail legend and group-flow rows (operator screenshot, 2026-05-20).
// This adapter keeps backend strings discoverable via `title`/`data-` attrs
// while the on-screen chip uses a short controlled vocabulary so each line
// fits in one row and the cockpit reads as an instrument panel, not prose.
const RELATION_COMPACT_LABEL: Record<string, string> = {
  explicit: 'OPEN',
  outbound_declaration: 'OPEN',
  overlay_anchor: 'OVR',
  overlay_of: 'OVR',
  route_hierarchy: 'ROUTE',
  legacy_or_workbench_of: 'WORK',
  shared_backend_api: 'API',
  shared_component: 'COMP',
  station_group: 'GROUP',
  station_lens_menu: 'LENS',
  shell_group: 'SHELL',
  // Low-authority fallbacks. The backend serves `adjacency` (presentation_role
  // 'fallback') ONLY when per-edge mechanism metadata is unavailable — e.g. the
  // first_paint snapshot omits the typed `edges` array, so the canvas receives
  // untyped adjacency. Mark these WEAK so a drawn line never *implies* a confident
  // relation class it cannot name (operator: "do not let generic fallback look
  // authoritative"). Real per-edge typing is the typed-edges serving residual
  // (cap: serve typed navigation edges to Atlas).
  adjacency: 'WEAK',
  command_palette: 'CMD',
  recent_surface: 'RECENT',
  redirect: 'REDIR',
  alert_route: 'ALERT',
  unknown: 'WEAK',
};

function compactLabelForMechanism(mechanism: string): string {
  return RELATION_COMPACT_LABEL[mechanism] ?? 'REL';
}

// ---------------------------------------------------------------------------
// Atlas v6 semantic-edge rendering taxonomy
// ---------------------------------------------------------------------------
// Core rule (operator 2026-05-18): no visible line unless the viewer can
// immediately read what that exact line means. If a line cannot carry a
// readable relation, it is folded into a count/panel/context highlight,
// never drawn across the atlas.
//
// DRAWN_CANVAS_MECHANISMS: relations rendered as labelled semantic pathways
//   on hover/pin. Every drawn edge in this set is labelled. These are the
//   wayfinding relations: declared opens, hosted overlays, route children,
//   workbench-of parking, and the low-volume shared backend API ties.
// FOLDED_CONTEXT_MECHANISMS: relations whose presence informs counts and the
//   detail panel but never draw a line on the canvas. This includes the
//   high-cardinality `shared_component` (the 254-edge cyan spaghetti the
//   operator flagged), shell/station group membership, lens menu reachability,
//   command palette, recent surfaces, and adjacency/unknown fallbacks.
const DRAWN_CANVAS_MECHANISMS = new Set<string>([
  'explicit',
  'outbound_declaration',
  'outbound_declared',
  'overlay_anchor',
  'overlay_of',
  'route_hierarchy',
  'legacy_or_workbench_of',
  'shared_backend_api',
  'redirect',
  'alert_route',
]);
const FOLDED_CONTEXT_MECHANISMS = new Set<string>([
  'shared_component',
  'command_palette',
  'recent_surface',
  'shell_group',
  'station_group',
  'station_lens_menu',
  'adjacency',
  'unknown',
]);
// Backcompat alias for older callsites (layout receipts, drift tests).
const HIGH_AUTHORITY_MECHANISMS = DRAWN_CANVAS_MECHANISMS;
const STRUCTURAL_MECHANISMS_ON_CANVAS = FOLDED_CONTEXT_MECHANISMS;
// Max edges drawn per focus pass. Past this, the rest are surfaced as
// folded counts + a panel list, not painted as unlabelled lines. Eight is
// the visual headroom of one column-stack of cards on the cockpit grid;
// above it the canvas starts to read as spaghetti even with labels.
const ATLAS_VISIBLE_EDGE_CAP_PER_FOCUS = 6;
// Only the highest-priority focus edges get a text label; the rest draw as
// quiet unlabelled lines. Labelling every drawn edge produced overlapping
// "label soup" across the cards on hover/pin (operator: edges "colliding with
// the nodes"). Lines still show the full neighbourhood; only the labels are
// rationed so the canvas stays readable.
const ATLAS_FOCUS_LABEL_CAP = 3;
// Kept for layout-receipt backcompat; identical to the edge cap so old
// telemetry consumers don't see a count drift.
const ATLAS_LABEL_CAP_PER_FOCUS = ATLAS_VISIBLE_EDGE_CAP_PER_FOCUS;
// Mechanisms that carry NO nameable relation class — the backend serves these
// only when per-edge mechanism metadata is absent (e.g. the first_paint snapshot
// omits the typed `edges` array). They are never given a canvas label: a "WEAK"
// chip on a short membership corridor lands on an adjacent card (label×node
// collision) and would imply a confident relation we cannot name. They draw as
// quiet neutral lines; the relation makeup lives in the right-rail legend until
// typed edges are served (cap: serve typed navigation edges to Atlas).
const UNLABELLED_FALLBACK_MECHANISMS = new Set<string>(['adjacency', 'unknown']);

// Side-aware port anchors. Each card exposes a source + target handle on every
// side; rfEdges selects the pair by direction so edges connect sensible sides
// (same-column -> top/bottom, cross-cluster -> facing sides) instead of always
// routing left->right and doubling back across the card stack.
const ATLAS_PORT_SIDES = [
  { id: 'left', pos: Position.Left },
  { id: 'right', pos: Position.Right },
  { id: 'top', pos: Position.Top },
  { id: 'bottom', pos: Position.Bottom },
] as const;

// ---------------------------------------------------------------------------
// Wave SFA-2 — backend-owned Station Atlas edge grammar. The backend projects
// the relation presentation role and group-flow rail; the frontend only renders
// those fields and flags any compatibility fallback in the layout receipt.
// ---------------------------------------------------------------------------
const EDGE_GRAMMAR_CONTRACT = 'shape_a_plus_unified_v1' as const;
const EDGE_EXPLAINABILITY_CONTRACT = 'station_relation_explainability_v1' as const;
const EDGE_ADDRESSABILITY_CONTRACT = 'station_relation_addressability_v1' as const;

const VALID_PRESENTATION_ROLES = new Set<WorldModelNavigationGraphPresentationRole>([
  'pathway',
  'membership',
  'fallback',
]);

function isPresentationRole(value: unknown): value is WorldModelNavigationGraphPresentationRole {
  return typeof value === 'string' && VALID_PRESENTATION_ROLES.has(value as WorldModelNavigationGraphPresentationRole);
}

const VALID_READ_MODEL_STATES = new Set<WorldModelNavigationGraphReadModelState>([
  'populated',
  'resting',
  'stale',
  'fallback',
  'missing',
  'invalid',
]);

function isReadModelState(value: unknown): value is WorldModelNavigationGraphReadModelState {
  return typeof value === 'string' && VALID_READ_MODEL_STATES.has(value as WorldModelNavigationGraphReadModelState);
}

const VALID_EVIDENCE_COVERAGE = new Set<WorldModelNavigationGraphEvidenceCoverage>([
  'full',
  'partial',
  'none',
  'not_applicable',
  'unknown',
]);

function evidenceCoverageValue(value: unknown): WorldModelNavigationGraphEvidenceCoverage {
  return typeof value === 'string' && VALID_EVIDENCE_COVERAGE.has(value as WorldModelNavigationGraphEvidenceCoverage)
    ? (value as WorldModelNavigationGraphEvidenceCoverage)
    : 'unknown';
}

function countValue(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function isMembershipEdge(edge: AtlasEdge): boolean {
  return edge.presentationRole === 'membership';
}

function presentationRoleLabel(role: WorldModelNavigationGraphPresentationRole): string {
  if (role === 'pathway') return 'drawn: pathway';
  if (role === 'membership') return 'folded: membership';
  return 'fallback: low-authority adjacency';
}

function presentationRoleTone(role: WorldModelNavigationGraphPresentationRole): string {
  if (role === 'pathway') return 'border-emerald-400/25 text-emerald-200';
  if (role === 'membership') return 'border-sky-400/25 text-sky-200';
  return 'border-amber-400/25 text-amber-200';
}

function groupFlowKey(flow: WorldModelNavigationGraphGroupFlow): string {
  if (typeof flow.group_flow_key === 'string' && flow.group_flow_key) return flow.group_flow_key;
  return `${flow.source_group}->${flow.target_group}`;
}

function relationKey(row: WorldModelNavigationGraphRelationSummary): string {
  if (typeof row.relation_key === 'string' && row.relation_key) return row.relation_key;
  return row.relation;
}

function relationCountEntries(counts?: Record<string, number>): Array<[string, number]> {
  if (!counts) return [];
  return Object.entries(counts).filter(([, count]) => Number.isFinite(count));
}

const RELATION_LEGEND_VISIBLE_LIMIT = 8;
const RELATION_LEGEND_MIN_BAR_PCT = 14;

function relationLegendBarWidthPct(edgeCount: number, roleMaxCount: number): number {
  if (!Number.isFinite(edgeCount) || edgeCount <= 0) return 0;
  if (!Number.isFinite(roleMaxCount) || roleMaxCount <= 0) return 100;
  const normalized = Math.min(1, edgeCount / roleMaxCount);
  return Math.min(
    100,
    Math.max(RELATION_LEGEND_MIN_BAR_PCT, Math.round(Math.sqrt(normalized) * 100)),
  );
}

const TONE_TEXT_CLASS: Record<RelationStyle['tone'], string> = {
  gold: 'text-[var(--zenith-accent)]',
  violet: 'text-[#c0a4c9]',
  sky: 'text-[#9ab7d4]',
  sage: 'text-[#7bc78e]',
  cyan: 'text-[#84c7cf]',
  rose: 'text-rose-300',
  gray: 'text-zenith-soft',
};

const TONE_BORDER_CLASS: Record<RelationStyle['tone'], string> = {
  gold: 'border-[var(--zenith-accent-edge)]',
  violet: 'border-[#c0a4c9]/30',
  sky: 'border-[#9ab7d4]/30',
  sage: 'border-[#7bc78e]/30',
  cyan: 'border-[#84c7cf]/30',
  rose: 'border-rose-400/30',
  gray: 'border-white/10',
};

// Focus-reveal stroke: bright, high-luminance, near-opaque per-tone colours used
// for the SELECTED/focused edge set only. The base RelationStyle.activeStroke is
// a low-alpha tint tuned for the legend/rest register (e.g. adjacency is
// rgba(192,199,180,0.50)); at element opacity 0.72 that nets ~0.36 alpha grey,
// which the perceptual evaluator measured at ~1.1:1 contrast on the dark
// backplate — invisible. Hue still encodes relation type; luminance is raised so
// the line is actually perceptible. Paired with the dark under-stroke (separates
// it over the tinted backplates), this makes a real demo focus reveal.
const TONE_FOCUS_STROKE: Record<RelationStyle['tone'], string> = {
  gold: 'rgba(250, 222, 150, 0.98)',
  violet: 'rgba(214, 193, 224, 0.97)',
  sky: 'rgba(188, 212, 236, 0.97)',
  sage: 'rgba(180, 224, 192, 0.96)',
  cyan: 'rgba(168, 222, 230, 0.97)',
  rose: 'rgba(250, 178, 146, 0.97)',
  gray: 'rgba(220, 226, 212, 0.96)',
};

// ---------------------------------------------------------------------------
// Edge density modes — operator-facing knob over how much edge surface is
// painted at rest. The graph carries hundreds of edges; without a default
// floor the visual reads as a hairball. Per the v3 contour: Clean is
// default (background skeleton only; full edges only on focus).
// ---------------------------------------------------------------------------
type EdgeDensityMode = 'clean' | 'structural' | 'capture';

const EDGE_DENSITY_MODES: Array<{ id: EdgeDensityMode; label: string; description: string }> = [
  // Wave SFA-1 (Station Atlas Edge Grammar Unification) — descriptions now
  // match what the canvas actually paints. Aggregate group-pair corridors
  // moved off the canvas into the right-rail Group flows panel; membership
  // relations (shell_group, station_group, station_lens_menu) fold into
  // rails/columns instead of competing as canvas pathway edges. Per
  // cap_quick_atlas_edge_mode_incoherence_corridor_lin_56b4ec4c5e64.
  {
    id: 'clean',
    label: 'Clean',
    description: 'No canvas edges at rest. Group flows appear in the right rail; exact pathway edges appear on hover or pin.',
  },
  {
    id: 'structural',
    label: 'Structural',
    description: 'Pathway edges only (declared, overlay, route, shared API/component). Membership/group relations fold into the right rail.',
  },
  {
    id: 'capture',
    label: 'Capture',
    description: 'Evidence-bearing pathway edges only; nodes coloured by capture posture.',
  },
];

// ---------------------------------------------------------------------------
// AtlasFocus — interaction state primitive for v3 semantic focus map.
// Rest = nothing focused, every node visible at full opacity, edges faint.
// Hover = mouse is over a node; transient, clears on mouse-leave unless
//         the same node is also pinned.
// Pinned = right-clicked or alt-clicked; persists until Escape / pane-click.
// `focusId` resolves to pinned over hover so pinning sticks.
// ---------------------------------------------------------------------------
type AtlasFocus =
  | { mode: 'rest' }
  | { mode: 'hover'; nodeId: string }
  | { mode: 'pinned'; nodeId: string };

type FocusStatus = 'rest' | 'focused' | 'adjacent' | 'same_group' | 'dimmed';

// ---------------------------------------------------------------------------
// RelationBrush — second focus layer on top of AtlasFocus. Lets a hovered
// row in the connected-views panel act as a brush handle: keep the anchor
// (pinned/hovered node) at 100%, lift the brushed neighbour to ~90%,
// emphasize the exact anchor↔neighbour edge, demote everything else.
// This is classic coordinated-view brushing-and-linking — the right panel
// and the graph behave like two views of the same relationship object.
// ---------------------------------------------------------------------------
type RelationBrush =
  | { mode: 'none' }
  | {
      mode: 'connected_row';
      anchorId: string;
      neighborId: string;
      relation: string;
      /** Indices into the edges[] array for the active anchor↔neighbour edge(s). */
      edgeIdxs: number[];
    };

type RelationSelectionSource = 'url' | 'row' | 'default' | 'none';
type GroupFlowSelectionSource = 'url' | 'row' | 'default' | 'none';
type EdgeSelectionSource = 'url' | 'sample' | 'canvas' | 'none';
type CoordinationMode = 'none' | 'relation' | 'group_flow' | 'edge' | 'mixed';
type EdgeCoordinationRole =
  | 'selected_edge'
  | 'relation_match'
  | 'group_flow_match'
  | 'context'
  | 'demoted';
type NodeCoordinationRole =
  | 'selected_endpoint'
  | 'relation_endpoint'
  | 'group_flow_endpoint'
  | 'context'
  | 'demoted';
type ColumnCoordinationRole = 'group_flow_source' | 'group_flow_target' | null;

const EDGE_COORDINATION_CONTRACT = 'station_relation_coordination_v1';

/**
 * BrushStatus is a refinement of FocusStatus that only applies when a
 * RelationBrush is active. It supersedes FocusStatus for node opacity
 * decisions so the brush ranking dominates the ego-network ranking.
 *   anchor        — pinned/hovered node (the focus anchor itself)
 *   neighbor      — the brushed connected-view target
 *   ego_context   — other neighbours of the anchor (demoted from v3 hover)
 *   dimmed        — everything else (unrelated)
 */
type BrushStatus = 'anchor' | 'neighbor' | 'ego_context' | 'dimmed';

// ReactFlow node data — what gets passed to the custom node renderer.
interface AtlasNodeData {
  view: AtlasView;
  /**
   * Focus posture relative to current AtlasFocus + group filter / search.
   *   rest       — no node is focused; render neutral card chrome (no halo).
   *   focused    — this node IS the focus anchor; full opacity + gold halo.
   *   adjacent   — 1-hop neighbour of the focus anchor.
   *   same_group — same shell column as focus but not in ego network.
   *   dimmed     — out of focus + out of column.
   */
  focusStatus: FocusStatus;
  /**
   * Brush posture when a connected-view row is hovered. null when no brush
   * is active — fall back to focusStatus. When set, brushStatus dominates.
   */
  brushStatus: BrushStatus | null;
  /** Relation-color tone for the brushed neighbour halo (only when brushed). */
  brushTone: RelationStyle['tone'] | null;
  /** URL/rail selected identity posture; null when no coordinated selection is active. */
  coordinationRole: NodeCoordinationRole | null;
  coordinationTone: RelationStyle['tone'] | null;
  /** Search/filter match (independent of focus). When false the node dims. */
  isMatch: boolean;
  /** True when this node is the pinned anchor — gets a pin glyph + sharper glow. */
  isPinned: boolean;
  /** True when this node is the live hover target — drives subtle outline pulse. */
  isHovered: boolean;
  /** Heuristic capture posture, used for the per-node status pill. */
  captureTone: 'signal' | 'amber' | 'rose' | 'muted';
}

interface CachedNodeData<T> {
  key: string;
  data: T;
}

function cachedNodeData<T>(
  cache: Map<string, CachedNodeData<T>>,
  id: string,
  key: string,
  create: () => T,
): T {
  const cached = cache.get(id);
  if (cached?.key === key) return cached.data;
  const data = create();
  cache.set(id, { key, data });
  return data;
}

function pruneNodeDataCache<T>(cache: Map<string, CachedNodeData<T>>, seenIds: Set<string>): void {
  for (const id of cache.keys()) {
    if (!seenIds.has(id)) cache.delete(id);
  }
}

function atlasViewRenderKey(view: AtlasView): string {
  return [
    view.id,
    view.label,
    view.route,
    view.shellGroup,
    view.captureLatestStatus ?? '',
    view.isLegacy ? 'legacy' : 'current',
    view.culDeSacEffective ? 'terminal' : 'open',
    view.fanin,
    view.fanout,
    view.pathwayCount,
  ].join('|');
}

const SHELL_GROUP_LABEL: Record<ShellSurfaceGroupId | 'unassigned', string> = {
  operate: 'Operate',
  missions: 'Missions',
  data: 'Data',
  inspect: 'Inspect',
  map: 'Map',
  library: 'Library',
  unassigned: 'Other',
};

function shellGroupLabel(group: string): string {
  return SHELL_GROUP_LABEL[group as ShellSurfaceGroupId | 'unassigned']
    ?? group.replace(/_/g, ' ');
}

const SHELL_GROUP_ICON: Record<ShellSurfaceGroupId | 'unassigned', LucideIcon> = {
  operate: Radio,
  missions: Workflow,
  data: CandlestickChart,
  inspect: Eye,
  map: Compass,
  library: Layers,
  unassigned: Boxes,
};

const SHELL_GROUP_COLOR: Record<ShellSurfaceGroupId | 'unassigned', string> = {
  operate: '#c7b06a',  // muted gold
  missions: '#d49a8a', // warm rose (active mission lane)
  data: '#84c7cf',     // cyan-teal (feeds + finance cockpit)
  inspect: '#7bc78e',  // soft green
  map: '#9ab7d4',      // muted cyan
  library: '#c0a4c9',  // muted violet (used sparingly)
  unassigned: '#7b8675',
};

const SHELL_GROUP_ORDER: Array<ShellSurfaceGroupId | 'unassigned'> = [
  'operate',
  'missions',
  'data',
  'inspect',
  'map',
  'library',
  'unassigned',
];

function captureStatusLabel(status: string | null, captureSlug: string | null): string {
  if (!status) return captureSlug ? 'capture pending' : 'not configured';
  return status.replace(/_/g, ' ');
}

function captureTone(view: AtlasView): 'signal' | 'amber' | 'rose' | 'muted' {
  if (view.captureLatestStatus === 'captured') return 'signal';
  if (view.captureLatestStatus === 'failed' || view.captureLatestStatus === 'readiness_timeout') return 'rose';
  if (view.captureSlug && view.captureSampleCount === 0) return 'amber';
  return 'muted';
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function postureFromRoute(route: string, health?: string | null): string {
  if (route.includes('/legacy')) return 'legacy';
  if (route.includes('/workbench')) return 'workbench';
  if (health === 'live') return 'canonical';
  if (health === 'degraded') return 'workbench';
  if (health === 'placeholder') return 'placeholder';
  if (health === 'authority_debt') return 'experimental';
  if (health === 'broken') return 'stale';
  return 'uncaptured';
}

// ---------------------------------------------------------------------------
// View resolution — pull from worldModel.navigation_graph if present,
// otherwise build from the static SURFACES registry.
// ---------------------------------------------------------------------------

function viewsFromSurfaces(): AtlasView[] {
  const surfaces = getAllSurfaces().filter((surface) => !surface.hiddenFromAtlas);
  return surfaces.map((surface): AtlasView => ({
    id: surface.id,
    label: surface.label,
    route: surface.route,
    entryRoute: surface.entryRoute ?? surface.route,
    purpose: surface.purpose,
    kind: surface.kind ?? 'page',
    shellGroup: surface.shellGroup ?? 'unassigned',
    stationGroup: surface.stationGroup ?? null,
    captureSlug: surface.captureSlug ?? null,
    captureLatestStatus: null,
    captureLatestLoadMs: null,
    captureSampleCount: 0,
    fanout: 0,
    fanin: 0,
    pathwayCount: 0,
    pathwayFanout: 0,
    pathwayFanin: 0,
    culDeSacEffective: false,
    isLegacy: surface.route.includes('/legacy') || surface.route.includes('/workbench'),
    evidenceFile: 'system/server/ui/src/navigation/surfaces.ts',
    posture: postureFromRoute(surface.route),
    primaryComponent: null,
    backendEndpoints: [],
    storeSlices: [],
    sharedComponents: [],
    substrateBindings: ['frontend_views'],
    authorityNote: null,
    semanticEvidenceRefs: [],
  }));
}

function viewsFromNavigationGraph(graph: Record<string, unknown>): AtlasView[] {
  const rawViews = Array.isArray((graph as { views?: unknown }).views)
    ? ((graph as { views: unknown[] }).views)
    : [];
  // Static surface catalog overrides the backend projection for two fields:
  //   - hiddenFromAtlas: lets us soft-hide surfaces without waiting for the
  //     navigation-graph generator to regenerate.
  //   - shellGroup: lets shell-group reorganisation land before the backend
  //     rebuild has caught up.
  const staticById = new Map(getAllSurfaces().map((surface) => [surface.id, surface]));
  return rawViews
    .map((raw) => {
      const v = raw as Record<string, unknown>;
      const capture = (v.capture ?? null) as Record<string, unknown> | null;
      const loadTiming = (capture?.load_timing ?? null) as Record<string, unknown> | null;
      const culDeSac = (v.cul_de_sac ?? null) as Record<string, unknown> | null;
      const evidence = (v.evidence ?? null) as Record<string, unknown> | null;
      const semantic = (v.semantic_health ?? null) as Record<string, unknown> | null;
      const audit = (v.surface_audit ?? null) as Record<string, unknown> | null;
      const id = typeof v.id === 'string' ? v.id : null;
      const route = typeof v.route === 'string' ? v.route : null;
      if (!id || !route) return null;
      const staticSurface = staticById.get(id as never);
      if (staticSurface?.hiddenFromAtlas) return null;
      const semanticHealth = typeof semantic?.health === 'string' ? semantic.health : null;
      const substrateBindings = [
        ...stringList(semantic?.related_paper_or_skill),
        ...stringList(audit?.substrate_bindings),
      ];
      const semanticEvidenceRefs = [
        ...stringList(semantic?.evidence_refs),
        ...stringList(audit?.evidence_refs),
      ];
      const view: AtlasView = {
        id,
        label: typeof v.label === 'string' ? v.label : id,
        route,
        entryRoute: typeof v.entry_route === 'string' ? v.entry_route : route,
        purpose: typeof v.purpose === 'string' ? v.purpose : '',
        kind: typeof v.kind === 'string' ? v.kind : 'page',
        shellGroup: (staticSurface?.shellGroup
          ?? (typeof v.shell_group === 'string' ? v.shell_group : 'unassigned')) as ShellSurfaceGroupId | 'unassigned',
        stationGroup: typeof v.station_group === 'string' ? v.station_group : null,
        captureSlug: typeof capture?.slug === 'string' ? capture.slug : null,
        captureLatestStatus: typeof loadTiming?.latest_status === 'string' ? loadTiming.latest_status : null,
        captureLatestLoadMs: typeof loadTiming?.latest_load_ms === 'number' ? loadTiming.latest_load_ms : null,
        captureSampleCount: typeof loadTiming?.sample_count === 'number' ? loadTiming.sample_count : 0,
        fanout: typeof v.fanout_count === 'number' ? v.fanout_count : 0,
        fanin: typeof v.fanin_count === 'number' ? v.fanin_count : 0,
        pathwayCount: typeof v.pathway_count === 'number' ? v.pathway_count : 0,
        pathwayFanout: typeof v.pathway_fanout_count === 'number' ? v.pathway_fanout_count : 0,
        pathwayFanin: typeof v.pathway_fanin_count === 'number' ? v.pathway_fanin_count : 0,
        culDeSacEffective: Boolean(culDeSac?.effective),
        isLegacy: route.includes('/legacy') || route.includes('/workbench'),
        evidenceFile: typeof evidence?.file === 'string' ? evidence.file : null,
        posture: typeof audit?.posture === 'string' ? audit.posture : postureFromRoute(route, semanticHealth),
        primaryComponent: typeof audit?.primary_component === 'string' ? audit.primary_component : null,
        backendEndpoints: stringList(audit?.backend_endpoints),
        storeSlices: stringList(audit?.store_slices),
        sharedComponents: stringList(audit?.shared_components),
        substrateBindings: [...new Set(substrateBindings.length > 0 ? substrateBindings : ['frontend_views'])],
        authorityNote: typeof semantic?.authority_note === 'string' ? semantic.authority_note : null,
        semanticEvidenceRefs: [...new Set(semanticEvidenceRefs)],
      };
      return view;
    })
    .filter((v): v is AtlasView => v !== null);
}

function edgesFromNavigationGraph(graph: Record<string, unknown>): AtlasEdge[] {
  // World-model projection emits edges with backend-owned edge_key plus
  // {from, to, mechanism} (see server/world_model.py::_condense_navigation_graph).
  // When the projection is older and only exposes `adjacency`, we derive edges
  // from that and mark key source as frontend fallback.
  const rawEdges = (graph as { edges?: unknown }).edges;
  if (Array.isArray(rawEdges)) {
    return (rawEdges as unknown[])
      .map((edge) => {
        const e = edge as Record<string, unknown>;
        const source = typeof e.from === 'string' ? e.from : null;
        const target = typeof e.to === 'string' ? e.to : null;
        if (!source || !target) return null;
        const backendRole = isPresentationRole(e.presentation_role) ? e.presentation_role : null;
        const edgeKey = typeof e.edge_key === 'string' && e.edge_key ? e.edge_key : null;
        return {
          edgeKey,
          edgeKeySource: edgeKey ? 'backend' : 'frontend_fallback',
          source,
          target,
          relation: typeof e.mechanism === 'string' ? e.mechanism : 'unknown',
          label: typeof e.label === 'string' ? e.label : (
            typeof e.mechanism === 'string' ? e.mechanism.replace(/_/g, ' ') : 'navigation relation'
          ),
          category: typeof e.category === 'string' ? e.category : null,
          description: typeof e.description === 'string' ? e.description : null,
          presentationRole: backendRole ?? 'fallback',
          presentationRoleSource: backendRole ? 'backend' : 'frontend_fallback',
          group: typeof e.group === 'string' ? e.group : null,
          rank: typeof e.rank === 'number' ? e.rank : null,
          weight: typeof e.weight === 'number' ? e.weight : null,
          evidenceRefs: stringList(e.evidence_refs),
        };
      })
      .filter((e): e is AtlasEdge => e !== null);
  }
  const adjacency = (graph as { adjacency?: unknown }).adjacency;
  if (adjacency && typeof adjacency === 'object') {
    const out: AtlasEdge[] = [];
    for (const [from, neighbours] of Object.entries(adjacency as Record<string, unknown>)) {
      const n = neighbours as { outbound_ids?: unknown };
      if (!Array.isArray(n.outbound_ids)) continue;
      for (const to of n.outbound_ids as unknown[]) {
        if (typeof to !== 'string') continue;
        out.push({
          edgeKey: null,
          edgeKeySource: 'frontend_fallback',
          source: from,
          target: to,
          relation: 'adjacency',
          label: 'navigation adjacency',
          category: null,
          description: null,
          presentationRole: 'fallback',
          presentationRoleSource: 'frontend_fallback',
          group: null,
          rank: null,
          weight: null,
          evidenceRefs: [],
        });
      }
    }
    return out;
  }
  return [];
}

function edgesFromSurfaces(views: AtlasView[]): AtlasEdge[] {
  // Group-derived edges as a fallback: every view in a shell_group has an
  // edge to every other view in the same group, plus station_group ties.
  // We restrict fan-out to keep the synthetic graph readable.
  const byGroup = new Map<string, AtlasView[]>();
  for (const view of views) {
    const key = `shell:${view.shellGroup}`;
    if (!byGroup.has(key)) byGroup.set(key, []);
    byGroup.get(key)!.push(view);
  }
  const edges: AtlasEdge[] = [];
  for (const group of byGroup.values()) {
    for (let i = 0; i < group.length; i++) {
      for (let j = i + 1; j < group.length && j < i + 3; j++) {
        edges.push({
          edgeKey: null,
          edgeKeySource: 'frontend_fallback',
          source: group[i].id,
          target: group[j].id,
          relation: 'shell_group',
          label: 'same shell group',
          category: 'global_shell_navigation',
          description: null,
          presentationRole: 'membership',
          presentationRoleSource: 'frontend_fallback',
          group: String(group[i].shellGroup),
          rank: 30,
          weight: 0.55,
          evidenceRefs: [],
        });
      }
    }
  }
  return edges;
}

function isNavigationGroupFlow(value: unknown): value is WorldModelNavigationGraphGroupFlow {
  const flow = value as Partial<WorldModelNavigationGraphGroupFlow> | null;
  return Boolean(
    flow
    && typeof flow.source_group === 'string'
    && typeof flow.target_group === 'string'
    && typeof flow.source_anchor_view_id === 'string'
    && typeof flow.target_anchor_view_id === 'string'
    && typeof flow.edge_count === 'number'
    && typeof flow.evidence_count === 'number'
    && typeof flow.dominant_relation === 'string',
  );
}

function isNavigationRelationSummary(value: unknown): value is WorldModelNavigationGraphRelationSummary {
  const row = value as Partial<WorldModelNavigationGraphRelationSummary> | null;
  return Boolean(
    row
    && typeof row.relation === 'string'
    && isPresentationRole(row.presentation_role)
    && typeof row.edge_count === 'number'
    && typeof row.evidence_count === 'number',
  );
}

// ---------------------------------------------------------------------------
// Layout — Atlas v5 hybrid shell-group packer.
// ---------------------------------------------------------------------------
// Operator complaint receipts pin this slice: MAP-13 stacks tall while
// DATA-4 leaves whitespace because the prior layout fixed COLUMN_GAP=360 +
// ROW_GAP=90 per node, treating every shell group as a peer-equal lane.
// v5 preserves SHELL_GROUP_ORDER (the operator's spatial grammar — Operate
// > Missions > Data > Inspect > Map > Library > Other reads left-to-right
// every time) but lets dense groups widen to 2 or 3 lanes inside their
// column. Within each group the order is now meaning-first: capture
// attention posture (failed first, then uncaptured, then captured, then
// muted), then centrality (fanin + fanout), then alphabetical. Pin state
// is intentionally NOT a sort key — moving the pinned card would jitter
// the operator's spatial memory on every pin change; the gold halo and
// brush keep pin/focus discoverable instead.
// Per cap_quick_atlas_v5_semantic_layout_planner_edge_la_f610b4d55425
// (operator refinement: hybrid shell packer is primary, Dagre is comparator).

const COLUMN_GAP = 320;
// Density-pass v2 (operator: "right side is wasted space, we can make them
// bigger if we remove that wasted space so its more legible"). Cards shrunk
// 320 → 280 to cut right-side whitespace on short labels (DEMO, OPS, GRAPH);
// every font inside the card was bumped one tier so the saved horizontal
// space pays for legibility instead of disappearing. ROW_GAP tracks the
// taller content stack (label 17px line-clamp-2 + route 12px + pill/stats 11px).
const ROW_GAP = 132;
const COLUMN_HEADER_HEIGHT = 88;
const NODE_WIDTH = 280;
const LANE_GAP = 28;
const LANE_OFFSET = NODE_WIDTH + LANE_GAP;
// Local obstacle router (atlasEdgeRouter.ts) geometry, in FLOW coords. Cards
// measure ~56-65px tall on screen at the fitView zoom (~0.586, since 164px
// screen width = NODE_WIDTH 280 * zoom), i.e. ~96-111px in flow space; model
// the obstacle slightly above that max so routed paths over-avoid relative to
// the real cards the evaluator measures. ROUTE_INFLATE exceeds half the ~16px
// inter-row flow gap (ROW_GAP 132 - obstacle 116), so a column's stacked cards
// fuse into one obstacle and cross-cluster routes take clean avenues above/
// below the stacks instead of threading fragile inter-row gaps; it stays under
// half the ~40px inter-column gap so vertical corridors stay open.
const NODE_OBST_HEIGHT = 116;
const ROUTE_INFLATE = 8;
const ROUTE_BEND_PENALTY = 14;
const ROUTE_STAGE_MARGIN = 120;
// Density thresholds — counts at which a group earns extra lanes. Lowered
// 8→5 / 16→11 in density-pass v3 because the 7-card OPERATE, 5-card DATA,
// and 6-card INSPECT columns were stacking as single tall lanes inside a
// ~2080×2170 square-aspect bounding box; fitView constrained by height on
// the 16:9 stage and the canvas left huge L/R wings empty (operator: "this
// is just this column, the left and right space unused"). Splitting those
// groups into 2 lanes widens the bounding box, fitView zooms in
// horizontally instead, and the wings collapse. MAP (15) escalates to 3
// lanes at the new LANE3 threshold so its column doesn't dominate the
// vertical axis on its own.
const LAYOUT_LANE2_THRESHOLD = 5;
const LAYOUT_LANE3_THRESHOLD = 11;

// Atlas Layout Utilization Pass (cap UI-Atlas-Layout-Utilization-Pass-004).
// The prior single-row layout produced a wide/shallow bounding box: 7-8
// shell groups × COLUMN_GAP=360 = ~2500-2900px wide, while max lane height
// landed near 600-1100px. React Flow's fitView shrank that 4:1 strip into
// the ~1.9:1 stage and left the lower half of the cockpit black. Banding
// the groups into 2 rows when there are >= LAYOUT_BAND_TRIGGER groups
// nearly halves horizontal span, lets fitView zoom in, and uses the
// vertical field instead of wasting it. SHELL_GROUP_ORDER is preserved
// within the read order — the first ceil(N/2) groups land in band 0,
// the remainder in band 1 — so the operator's left-to-right spatial
// grammar still holds within each band.
const LAYOUT_BAND_TRIGGER = 5;
const BAND_GAP = 100;

function capturePostureSortKey(view: AtlasView): number {
  // Lower returns sort earlier (top of column). Failed/attention surfaces
  // sit on top so the operator's eye lands on them first. Captured
  // surfaces stay middle-of-pack. Muted surfaces drop to the bottom of
  // their lane so attention-worthy work is never hidden under cosmetic
  // chaff.
  const status = view.captureLatestStatus;
  if (status === 'failed' || status === 'readiness_timeout') return 0;
  if (view.captureSlug && view.captureSampleCount === 0) return 1;
  if (status === 'captured') return 2;
  return 3;
}

const MAP_PAIR_LAYOUT_ORDER: Record<string, number> = {
  codemap: 0,
  doctrine: 1,
  ledger: 2,
  reactions: 3,
  timeline: 4,
  assimilation: 5,
};

function mapPairLayoutSortKey(view: AtlasView): number | null {
  if (view.shellGroup !== 'map') return null;
  return MAP_PAIR_LAYOUT_ORDER[view.id] ?? null;
}

function laneCountForGroup(count: number): number {
  if (count >= LAYOUT_LANE3_THRESHOLD) return 3;
  if (count >= LAYOUT_LANE2_THRESHOLD) return 2;
  return 1;
}

interface AtlasColumnGeometry {
  group: ShellSurfaceGroupId | 'unassigned';
  x: number;
  // Band offset (y position of the column header). 0 for single-band
  // layouts; band 1 sits below band 0 by bandHeight + BAND_GAP. Consumers
  // that previously assumed y=0 must now read this field.
  y: number;
  count: number;
  laneCount: number;
  width: number;
  band: number;
}

function layoutNodes(views: AtlasView[]): {
  positions: Map<string, { x: number; y: number }>;
  columns: AtlasColumnGeometry[];
} {
  const byGroup = new Map<ShellSurfaceGroupId | 'unassigned', AtlasView[]>();
  for (const group of SHELL_GROUP_ORDER) byGroup.set(group, []);
  for (const view of views) {
    const group = byGroup.get(view.shellGroup) ?? byGroup.get('unassigned')!;
    group.push(view);
  }

  // Filter SHELL_GROUP_ORDER down to groups that actually have content.
  // Empty groups must not consume a slot in the banding heuristic or the
  // bands look lopsided.
  const populated = SHELL_GROUP_ORDER.filter(
    (g) => (byGroup.get(g)?.length ?? 0) > 0,
  );

  // Banding decision: when there are LAYOUT_BAND_TRIGGER or more populated
  // groups, split them into two horizontal bands so the bounding-box
  // aspect ratio matches the cockpit stage (~1.9:1) rather than the
  // wide/shallow strip the prior single-row layout produced. The first
  // ceil(N/2) groups stay in band 0 (preserves left-to-right reading
  // grammar for the dominant groups: Operate / Missions / Data / Inspect);
  // remaining groups land in band 1.
  const bandCount = populated.length >= LAYOUT_BAND_TRIGGER ? 2 : 1;
  const groupsPerBand = Math.ceil(populated.length / bandCount);

  // First pass: base lane counts + per-band base width. Then SPEND unused
  // horizontal slack — a narrower band gives its TALLEST group extra lanes,
  // which shortens the band that binds the (height-constrained) fitView and so
  // lifts the fit zoom: bigger, more legible cards from the same stage. This is
  // the substrate-native alternative to band-centring (audited and rejected:
  // centring floats the band under a left-anchored top band). Territory order
  // and the left anchor stay intact, and a bump never widens the graph past
  // the dominant band, because lanes are only added while they still fit the
  // widest band's width. Per cap_quick_atlas_refinement_follow_on_visual_waves.
  const groupBand = new Map<ShellSurfaceGroupId | 'unassigned', number>();
  const finalLanes = new Map<ShellSurfaceGroupId | 'unassigned', number>();
  const bandWidths: number[] = new Array(bandCount).fill(0);
  const bandHeights: number[] = new Array(bandCount).fill(0);
  {
    const cursors = new Array(bandCount).fill(0);
    populated.forEach((group, idx) => {
      const bandIdx = Math.floor(idx / groupsPerBand);
      groupBand.set(group, bandIdx);
      const lane = laneCountForGroup(byGroup.get(group)!.length);
      finalLanes.set(group, lane);
      const laneSpan = lane === 1 ? 0 : (lane - 1) * LANE_OFFSET;
      bandWidths[bandIdx] = cursors[bandIdx] + NODE_WIDTH + laneSpan;
      cursors[bandIdx] += COLUMN_GAP + laneSpan;
    });
    const maxBandWidth = bandWidths.reduce((m, w) => Math.max(m, w), 0);
    for (let band = 0; band < bandCount; band += 1) {
      while (maxBandWidth - bandWidths[band] >= LANE_OFFSET) {
        let tallestGroup: (ShellSurfaceGroupId | 'unassigned') | null = null;
        let tallestRows = 0;
        for (const group of populated) {
          if (groupBand.get(group) !== band) continue;
          const rows = Math.ceil(byGroup.get(group)!.length / finalLanes.get(group)!);
          if (rows > tallestRows) { tallestRows = rows; tallestGroup = group; }
        }
        if (!tallestGroup) break;
        const count = byGroup.get(tallestGroup)!.length;
        const nextLane = finalLanes.get(tallestGroup)! + 1;
        if (Math.ceil(count / nextLane) >= tallestRows) break; // bump would not shorten
        finalLanes.set(tallestGroup, nextLane);
        bandWidths[band] += LANE_OFFSET;
      }
    }
    populated.forEach((group) => {
      const bandIdx = groupBand.get(group)!;
      const perLane = Math.ceil(byGroup.get(group)!.length / finalLanes.get(group)!);
      const colHeight = COLUMN_HEADER_HEIGHT + perLane * ROW_GAP;
      if (colHeight > bandHeights[bandIdx]) bandHeights[bandIdx] = colHeight;
    });
  }

  const positions = new Map<string, { x: number; y: number }>();
  const columns: AtlasColumnGeometry[] = [];
  let cursorX = 0;
  let currentBand = 0;
  let groupInBand = 0;
  let bandY = 0;

  for (const group of populated) {
    const list = byGroup.get(group)!;

    // Wrap to the next band when this one is full.
    if (groupInBand >= groupsPerBand) {
      bandY += bandHeights[currentBand] + BAND_GAP;
      currentBand += 1;
      cursorX = 0;
      groupInBand = 0;
    }

    // Meaning-first sort: capture attention, then centrality, then label.
    const sorted = [...list].sort((a, b) => {
      const pairA = mapPairLayoutSortKey(a);
      const pairB = mapPairLayoutSortKey(b);
      if (pairA !== null || pairB !== null) {
        return (pairA ?? Number.MAX_SAFE_INTEGER) - (pairB ?? Number.MAX_SAFE_INTEGER);
      }
      const pa = capturePostureSortKey(a);
      const pb = capturePostureSortKey(b);
      if (pa !== pb) return pa - pb;
      const ca = a.fanout + a.fanin;
      const cb = b.fanout + b.fanin;
      if (cb !== ca) return cb - ca;
      return a.label.localeCompare(b.label);
    });
    const laneCount = finalLanes.get(group) ?? laneCountForGroup(sorted.length);
    const width = laneCount === 1 ? 0 : (laneCount - 1) * LANE_OFFSET;
    columns.push({
      group,
      x: cursorX,
      y: bandY,
      count: sorted.length,
      laneCount,
      width,
      band: currentBand,
    });
    // Distribute into lanes round-robin so attention-priority nodes lead
    // each lane and the column reads top-down across all lanes evenly.
    const lanes: AtlasView[][] = Array.from({ length: laneCount }, () => []);
    sorted.forEach((view, idx) => {
      lanes[idx % laneCount].push(view);
    });
    lanes.forEach((lane, laneIdx) => {
      const laneX = cursorX + laneIdx * LANE_OFFSET;
      lane.forEach((view, rowIdx) => {
        positions.set(view.id, {
          x: laneX,
          y: bandY + COLUMN_HEADER_HEIGHT + rowIdx * ROW_GAP,
        });
      });
    });
    // Step the cursor by COLUMN_GAP plus any extra width contributed by
    // multi-lane columns, so column-to-column whitespace stays stable
    // regardless of lane count.
    cursorX += COLUMN_GAP + width;
    groupInBand += 1;
  }
  return { positions, columns };
}

// ---------------------------------------------------------------------------
// Custom node renderer
// ---------------------------------------------------------------------------

function areAtlasNodeRendererPropsEqual(
  prev: NodeProps<AtlasNodeData>,
  next: NodeProps<AtlasNodeData>,
): boolean {
  const a = prev.data;
  const b = next.data;
  return (
    atlasViewRenderKey(a.view) === atlasViewRenderKey(b.view)
    && a.focusStatus === b.focusStatus
    && a.brushStatus === b.brushStatus
    && a.brushTone === b.brushTone
    && a.coordinationRole === b.coordinationRole
    && a.coordinationTone === b.coordinationTone
    && a.isMatch === b.isMatch
    && a.isPinned === b.isPinned
    && a.isHovered === b.isHovered
    && a.captureTone === b.captureTone
  );
}

const AtlasNodeRenderer = memo(function AtlasNodeRenderer({ data }: NodeProps<AtlasNodeData>) {
  recordAtlasRender('AtlasNodeRenderer');
  const {
    view,
    focusStatus,
    brushStatus,
    brushTone,
    coordinationRole,
    coordinationTone,
    isMatch,
    isPinned,
    isHovered,
    captureTone: tone,
  } = data;
  const color = SHELL_GROUP_COLOR[view.shellGroup];
  const Icon = SHELL_GROUP_ICON[view.shellGroup];
  const isCaptured = view.captureLatestStatus === 'captured';
  // Semantic capture status is a SEPARATE visual axis from interaction state
  // (rest/hover/focus/pin). Legacy is a quiet neutral posture — the card is
  // already greyscaled — so it must not borrow the amber "capture pending"
  // language and read as a warning. The `!== 'rose'` guard is load-bearing:
  // a failed / readiness-timeout legacy surface must still pierce the legacy
  // quieting, so real failure is never hidden behind "this is just legacy".
  const semanticCaptureTone = tone;
  const statusTone: 'signal' | 'amber' | 'rose' | 'muted' =
    view.isLegacy && semanticCaptureTone !== 'rose' ? 'muted' : semanticCaptureTone;
  const showStatusPill = !isCaptured || view.isLegacy;
  // Only a failed / timed-out capture is a true interrupt that earns the
  // full-card treatment (tonal fill + coloured border + icon emphasis).
  // `amber` (capture pending) is routine attention: it speaks through the
  // thin left rail + status chip ONLY, so a field of pending cards (the 0/43
  // setup state) stays calm instead of an amber storm and never masquerades
  // as a selected / warning card. The strong border + tonal-fill channel
  // stays reserved for interaction state and genuine failure.
  const isInterruptStatus = statusTone === 'rose';
  const isRoutineAttentionStatus = statusTone === 'amber';

  // Per Atlas v3 focus opacity math
  // (cap_station_surface_atlas_focus_legibility_interaction_v1):
  //   rest       → 1.00, neutral card chrome (no gold halo).
  //   focused    → 1.00 + gold halo (anchor node).
  //   adjacent   → 0.78 (one-hop ego network member).
  //   same_group → 0.28 (column context, faintly visible).
  //   dimmed     → 0.10 (out of focus + out of column).
  //
  // Per Atlas v4 brush opacity math
  // (cap_station_surface_atlas_relation_brushing_v1):
  // when brushStatus != null, it supersedes focusStatus for node ranking.
  //   anchor      → 1.00 + gold halo (pinned/hovered anchor stays dominant).
  //   neighbor    → 0.92 + relation-color halo (the brushed connected view).
  //   ego_context → 0.45 (other anchor neighbours, demoted from v3's 0.78).
  //   dimmed      → 0.08 (unrelated graph drops harder than v3 to make the
  //                  relationship pop).
  // Search/filter miss multiplies by 0.55 to retain filter awareness.
  const focusOpacity =
    focusStatus === 'rest' || focusStatus === 'focused'
      ? 1.0
      : focusStatus === 'adjacent'
        ? 0.78
        : focusStatus === 'same_group'
          ? 0.28
          : 0.1;
  const brushOpacity =
    brushStatus === 'anchor'
      ? 1.0
      : brushStatus === 'neighbor'
        ? 0.92
        : brushStatus === 'ego_context'
          ? 0.45
          : 0.08;
  const coordinationOpacity =
    coordinationRole === 'selected_endpoint'
      ? 1.0
      : coordinationRole === 'group_flow_endpoint' || coordinationRole === 'relation_endpoint'
        ? 0.82
        : coordinationRole === 'context'
          ? 0.48
          : coordinationRole === 'demoted'
            ? 0.16
            : focusOpacity;
  const baseOpacity = brushStatus ? brushOpacity : coordinationRole ? coordinationOpacity : focusOpacity;
  const opacity = Math.max(isMatch ? baseOpacity : baseOpacity * 0.55, 0.06);

  const isRest = focusStatus === 'rest';
  const isCoordinationEndpoint = coordinationRole === 'selected_endpoint';
  const isCoordinationContext =
    coordinationRole === 'group_flow_endpoint' || coordinationRole === 'relation_endpoint' || coordinationRole === 'context';
  const isFocused = focusStatus === 'focused' || brushStatus === 'anchor' || isCoordinationEndpoint;
  const isAdjacent = focusStatus === 'adjacent';
  const isBrushNeighbor = brushStatus === 'neighbor';
  // Brushed-neighbour ring uses the active relation tone so the operator
  // sees which kind of relation is being inspected, not just that something
  // is connected.
  const brushHaloColor: string | null = isBrushNeighbor && brushTone
    ? (
        brushTone === 'gold'
          ? 'rgba(244, 206, 120, 0.55)'
          : brushTone === 'violet'
            ? 'rgba(192, 164, 201, 0.55)'
            : brushTone === 'sky'
              ? 'rgba(154, 183, 212, 0.55)'
              : brushTone === 'sage'
                ? 'rgba(123, 199, 142, 0.55)'
                : brushTone === 'cyan'
                  ? 'rgba(132, 199, 207, 0.55)'
                  : brushTone === 'rose'
                    ? 'rgba(244, 63, 94, 0.55)'
                    : 'rgba(192, 199, 180, 0.45)'
      )
    : null;
  const coordinationHaloColor: string | null = coordinationTone
    ? (
        coordinationTone === 'gold'
          ? 'rgba(244, 206, 120, 0.48)'
          : coordinationTone === 'violet'
            ? 'rgba(192, 164, 201, 0.42)'
            : coordinationTone === 'sky'
              ? 'rgba(154, 183, 212, 0.42)'
              : coordinationTone === 'sage'
                ? 'rgba(123, 199, 142, 0.42)'
                : coordinationTone === 'cyan'
                  ? 'rgba(132, 199, 207, 0.42)'
                  : coordinationTone === 'rose'
                    ? 'rgba(244, 63, 94, 0.42)'
                    : 'rgba(192, 199, 180, 0.35)'
      )
    : null;

  // Shadow priority: brush neighbour (relation halo) > focus (gold halo) >
  // hover > rest. Halo color comes from the active relation tone so the
  // operator sees which relation is being inspected, not just that there
  // is one. Selection (focused / coordination-endpoint) is palette-bound to
  // var(--zenith-accent-edge)/var(--zenith-accent-soft) so the gold-accent
  // identity stays consistent with .panel selection + .dot-info.
  const shadow = isBrushNeighbor && brushHaloColor
    ? `0 0 18px 3px ${brushHaloColor}, 0 2px 8px -2px rgba(0,0,0,0.85)`
    : isCoordinationEndpoint
      ? '0 0 0 1px var(--zenith-accent-edge), 0 0 26px 5px var(--zenith-accent-soft), 0 2px 10px -2px rgba(0,0,0,0.9)'
    : isFocused
      ? '0 0 0 1px var(--zenith-accent-edge), 0 0 28px 6px var(--zenith-accent-soft), 0 2px 10px -2px rgba(0,0,0,0.9)'
      : isCoordinationContext && coordinationHaloColor
        ? `0 0 16px 2px ${coordinationHaloColor}, 0 2px 8px -2px rgba(0,0,0,0.85)`
      : isHovered
        // Subtle hover lift — gold-tinted edge wash + slightly deeper drop
        // shadow telegraphs "selectable" without competing with focus.
        ? '0 0 0 1px var(--zenith-accent-edge), 0 0 18px 3px var(--zenith-accent-soft), 0 6px 18px -8px rgba(0,0,0,0.85)'
        : '0 1px 4px -1px rgba(0,0,0,0.75)';

  return (
    <div
      data-zenith-atlas-node-id={view.id}
      data-zenith-atlas-node-label={view.label}
      data-zenith-atlas-node-capture-slug={view.captureSlug ?? ''}
      data-zenith-atlas-node-capture-status={captureStatusLabel(view.captureLatestStatus, view.captureSlug)}
      data-zenith-atlas-node-coordination={coordinationRole ?? 'none'}
      // Capture-status grammar receipt (testable without pixels): semantic
      // tone, and whether this node is a true interrupt (failed/timeout) vs
      // routine attention (capture pending). Lets the navigation test assert
      // a "capture pending" node is NOT interrupt-status.
      data-zenith-atlas-node-status-tone={statusTone}
      data-zenith-atlas-node-interrupt-status={isInterruptStatus ? 'true' : 'false'}
      data-zenith-atlas-node-routine-attention={isRoutineAttentionStatus ? 'true' : 'false'}
      // Opaque-card contract: solid deep-bg backplate so edges never tunnel
      // through node text. Tonal gradient sits on top for column identity.
      className={clsx(
        // Density-pass v2: width 320 → 280. Right-side whitespace removed
        // and the saved horizontal pixels go into bigger fonts inside the
        // card. 40px of clearance remains within COLUMN_GAP=320. Padding
        // px-3 py-[var(--zenith-space-2-5)] keeps the denser stack readable.
        // motion-fast already animates background/border/opacity/box-shadow/
        // transform, so hover lift + selected gold glow share one timing
        // function. hover:-translate-y-px is the cockpit-hover-lift idiom
        // for ReactFlow custom nodes (we can't compose .cockpit-hover-lift
        // here because it conflicts with the inline boxShadow we compute).
        'group relative flex w-[280px] items-start gap-[var(--zenith-space-2-5)] rounded-[var(--zenith-radius-xs)] border px-3 py-[var(--zenith-space-2-5)] text-left motion-fast hover:-translate-y-px',
        view.isLegacy && !isFocused && 'grayscale-[0.35]',
      )}
      style={{
        // Root opacity is intentionally NOT applied here. The card must stay a
        // fully OPAQUE occluding obstacle so focus/hover edges drawn behind it
        // can never tunnel through a dimmed card. Dimming is painted as a
        // near-black scrim overlay (last child) scaled by (1 - opacity).
        boxShadow: shadow,
        background: isInterruptStatus
          ? 'linear-gradient(180deg, rgba(244,63,94,0.13) 0%, rgba(9,6,6,0.97) 70%), var(--zenith-bg-deep)'
          : isFocused
            ? `linear-gradient(180deg, ${color}1d 0%, rgba(5,8,5,0.97) 68%), var(--zenith-bg-deep)`
            : isCoordinationContext
              ? `linear-gradient(180deg, ${color}12 0%, rgba(5,8,5,0.97) 72%), var(--zenith-bg-deep)`
            : isBrushNeighbor
              ? `linear-gradient(180deg, ${color}16 0%, rgba(5,8,5,0.97) 70%), var(--zenith-bg-deep)`
              : isAdjacent
                ? `linear-gradient(180deg, ${color}0e 0%, rgba(5,8,5,0.97) 74%), var(--zenith-bg-deep)`
                : 'linear-gradient(180deg, rgba(255,255,255,0.035) 0%, rgba(5,8,5,0.97) 76%), var(--zenith-bg-deep)',
        borderColor: isFocused
          ? 'var(--zenith-accent)'
          : isCoordinationContext && coordinationHaloColor
            ? coordinationHaloColor
          : isBrushNeighbor && brushHaloColor
            ? brushHaloColor
            : statusTone === 'rose'
              ? 'rgba(244,63,94,0.55)'
            : isAdjacent
              ? `${color}70`
              : isHovered
                // Hover lifts the border to the gold accent-edge token so
                // it agrees with the gold-tinted hover shadow (selection-
                // but-softer). Shell-group hue continues to live in the
                // icon chip + label color.
                ? 'var(--zenith-accent-edge)'
                : isRest
                  ? 'rgba(255,255,255,0.09)'
                  : 'rgba(255,255,255,0.06)',
      }}
    >
      {/* Status stripe — failed surfaces visually interrupt the map; captured stays subtle so the
          map reads as overview not green wallpaper. Sits over the card's left border so failed
          rose pops past the shell-group hue. */}
      <span
        aria-hidden
        className={clsx(
          'pointer-events-none absolute inset-y-0 left-0 w-[4px] rounded-l-[6px]',
          statusTone === 'rose'
            ? 'bg-rose-500'
            : statusTone === 'amber'
              ? 'bg-amber-400'
              : statusTone === 'signal'
                ? 'bg-emerald-300/12'
                : 'bg-white/8',
        )}
        style={{
          boxShadow: statusTone === 'rose' ? '0 0 10px 1px rgba(244,63,94,0.55)' : undefined,
        }}
      />
      {/* Side-aware ports: a source + target handle on every side. rfEdges
          picks the pair by direction so an edge leaves/enters the sensible
          sides instead of always doubling back through left/right. Invisible
          connection anchors, not visual dots. */}
      {ATLAS_PORT_SIDES.map((side) => (
        <Handle
          key={`s-${side.id}`}
          type="source"
          id={`s-${side.id}`}
          position={side.pos}
          className="!h-1.5 !w-1.5 !min-h-0 !min-w-0 !border-0 !bg-transparent !opacity-0"
        />
      ))}
      {ATLAS_PORT_SIDES.map((side) => (
        <Handle
          key={`t-${side.id}`}
          type="target"
          id={`t-${side.id}`}
          position={side.pos}
          className="!h-1.5 !w-1.5 !min-h-0 !min-w-0 !border-0 !bg-transparent !opacity-0"
        />
      ))}
      <span
        aria-hidden
        className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-[5px]"
        style={{
          background: isInterruptStatus ? `${color}26` : `${color}17`,
          borderColor: color,
          borderWidth: 1,
          borderStyle: 'solid',
          opacity: isInterruptStatus || isFocused ? 1 : 0.74,
        }}
      >
        <Icon size={14} style={{ color }} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-start gap-1.5">
          <span
            className={clsx(
              // Density-pass v2: label 14px → 17px line-clamp-2. Short labels
              // (DEMO, OPS, GRAPH) now visually fill the narrower card width
              // instead of looking stranded next to empty right-side space;
              // long labels wrap to 2 lines without an ellipsis tax.
              'line-clamp-2 min-w-0 flex-1 font-display text-[18px] leading-tight tracking-normal',
              isFocused ? 'text-white' : 'text-white/92',
            )}
          >
            {view.label}
          </span>
          {view.culDeSacEffective ? (
            <span className="mt-0.5 shrink-0 font-mono text-[8.5px] uppercase tracking-[0.18em] text-amber-200/70">
              terminal
            </span>
          ) : null}
          {isPinned ? (
            <span
              title="pinned focus — Esc clears"
              className="mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-[3px] border border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] text-[var(--zenith-accent)]"
            >
              <Pin size={9} strokeWidth={2.4} />
            </span>
          ) : null}
        </span>
        {/* Density-pass v2: route + capture pill + fan stats always-on.
         * Fonts bumped one tier (route 10.5→12, pill/stats 9.5→11) so the
         * card content is readable at fitView zoom without leaning on hover. */}
        <span className="mt-1 flex items-center gap-1.5 font-mono text-[12px] text-white/80">
          <span className="truncate">{view.route}</span>
        </span>
        <span className="mt-1.5 flex items-center gap-1.5">
          {showStatusPill ? (
            <span
              className={clsx(
                'inline-flex items-center gap-1 rounded-[3px] border px-1.5 py-0.5 font-mono text-[11px] uppercase tracking-[0.14em]',
                statusTone === 'amber'
                  ? 'border-amber-400/45 bg-amber-500/[0.10] text-amber-200'
                  : statusTone === 'rose'
                    ? 'border-rose-400/55 bg-rose-500/[0.14] text-rose-100'
                    : 'border-zenith-edge-soft bg-white/[0.035] text-zenith-soft',
              )}
            >
              <CircleDot size={9} />
              {view.isLegacy ? 'legacy' : captureStatusLabel(view.captureLatestStatus, view.captureSlug)}
            </span>
          ) : (
            <span
              aria-label="captured"
              title="captured"
              className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-300/30"
            />
          )}
          {/* v6 count chip: the canvas paints semantic pathway edges only;
           * membership/component-affinity relations fold into the "ctx"
           * tally rather than spraying unlabelled lines. Split makes the
           * "hover 1 of 55" mystery readable — 1 line will draw, 54
           * relations exist as context that the right-panel rail surfaces. */}
          <span
            className="font-mono text-[11px] tracking-[0.02em] text-white/72"
            title={`paths: semantic pathways drawn as labelled lines on hover. ctx: folded relations (shared component, shell/station group, palette) shown as context in the right-panel rail, never as canvas lines.`}
          >
            paths {view.pathwayCount} · ctx {Math.max(0, view.fanin + view.fanout - view.pathwayCount)}
          </span>
        </span>
      </span>
      {/* Dimming scrim — keeps the card root fully OPAQUE so it is always a real
          occluding obstacle: edges drawn behind a card can never tunnel through
          a dimmed card. Dimming is a near-black overlay scaled by (1 - opacity)
          instead of fading the whole card to transparent. Closes the
          opaque-card-occlusion leg of the obstacle-aware focus-edge router cap. */}
      {opacity < 0.999 ? (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 z-10 rounded-[var(--zenith-radius-xs)] motion-fast"
          style={{ background: 'var(--zenith-bg)', opacity: Math.min(0.96, 1 - opacity) }}
        />
      ) : null}
    </div>
  );
}, areAtlasNodeRendererPropsEqual);

// Column-header node — renders the group label + operator-job description
// as a non-interactive ReactFlow node that pans/zooms with the graph so
// it stays aligned with its column at every zoom level.
interface ColumnHeaderData {
  group: ShellSurfaceGroupId | 'unassigned';
  count: number;
  failedCount: number;
  noCaptureCount: number;
  legacyCount: number;
  description: string;
  coordinationRole: ColumnCoordinationRole;
}

const ColumnHeaderRenderer = memo(function ColumnHeaderRenderer({ data }: NodeProps<ColumnHeaderData>) {
  recordAtlasRender('ColumnHeaderRenderer');
  const { group, count, failedCount, noCaptureCount, legacyCount, description, coordinationRole } = data;
  const color = SHELL_GROUP_COLOR[group];
  const Icon = SHELL_GROUP_ICON[group];
  const label = SHELL_GROUP_LABEL[group];
  const isSelectedGroup = coordinationRole !== null;
  return (
    <div
      data-zenith-atlas-column-coordination={coordinationRole ?? 'none'}
      data-zenith-atlas-column-failed-count={failedCount}
      data-zenith-atlas-column-no-capture-count={noCaptureCount}
      className="flex w-[280px] flex-col gap-1 px-2 py-1.5"
      style={{
        background: 'transparent',
        boxShadow: isSelectedGroup ? `0 8px 18px -18px ${color}` : undefined,
        pointerEvents: 'none',
      }}
    >
      <span className="kicker-mono" style={{ color: 'var(--zenith-soft)' }}>
        cluster
      </span>
      <div className="flex items-baseline gap-2">
        <span aria-hidden className="inline-flex h-4 w-4 items-center justify-center">
          <Icon size={10} style={{ color }} />
        </span>
        <span
          className="font-display text-[18px] leading-none tracking-normal"
          style={{ color }}
        >
          {label}
        </span>
        <span className="kicker-mono ml-auto">
          {count} {count === 1 ? 'view' : 'views'}
        </span>
      </div>
      {(failedCount > 0 || noCaptureCount > 0 || legacyCount > 0) ? (
        <div className="flex flex-wrap items-center gap-1">
          {failedCount > 0 ? (
            <span
              className="inline-flex items-center gap-1 rounded-[3px] border border-rose-400/55 bg-rose-500/15 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-rose-200"
              style={{ boxShadow: '0 0 8px -2px rgba(244,63,94,0.35)' }}
            >
              {failedCount} failed
            </span>
          ) : null}
          {noCaptureCount > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-[3px] border border-amber-400/45 bg-amber-500/[0.10] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-amber-200">
              {noCaptureCount} no-capture
            </span>
          ) : null}
          {/* Legacy is quiet metadata, not a warning — a neutral chip, never
              amber. Mirrors the card-state grammar (legacy -> muted). */}
          {legacyCount > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-[3px] border border-white/15 bg-white/[0.04] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-soft/80">
              {legacyCount} legacy
            </span>
          ) : null}
        </div>
      ) : null}
      <div
        aria-hidden
        className="h-px w-full"
        style={{ background: `linear-gradient(90deg, ${color}88, ${color}1c 55%, transparent)` }}
      />
      <p className="max-w-[250px] text-[11px] leading-[1.35] text-zenith-soft/85">{description}</p>
    </div>
  );
}, (prev, next) => {
  const a = prev.data;
  const b = next.data;
  return (
    a.group === b.group
    && a.count === b.count
    && a.failedCount === b.failedCount
    && a.noCaptureCount === b.noCaptureCount
    && a.legacyCount === b.legacyCount
    && a.description === b.description
    && a.coordinationRole === b.coordinationRole
  );
});

// Group backplate — a tinted rounded rectangle behind each shell-group column.
// Promotes shell groups from loose card clusters into visible territories
// (operator's "make groups real regions" prescription from the composition pass).
// Pointer-events-none so it never intercepts card clicks; sits behind cards via
// negative zIndex on the emitted ReactFlow node.
interface GroupBackplateData {
  group: ShellSurfaceGroupId | 'unassigned';
  width: number;
  height: number;
  coordinationRole: ColumnCoordinationRole;
}

const AtlasGroupBackplateRenderer = memo(function AtlasGroupBackplateRenderer({ data }: NodeProps<GroupBackplateData>) {
  recordAtlasRender('AtlasGroupBackplateRenderer');
  const { group, width, height, coordinationRole } = data;
  const color = SHELL_GROUP_COLOR[group];
  const isSelectedGroup = coordinationRole !== null;
  return (
    <div
      aria-hidden
      data-zenith-atlas-group-backplate={group}
      data-zenith-atlas-group-backplate-coordination={coordinationRole ?? 'none'}
      style={{
        width,
        height,
        background: isSelectedGroup
          ? `radial-gradient(ellipse at top, ${color}24 0%, ${color}0f 50%, transparent 92%)`
          : `radial-gradient(ellipse at top, ${color}16 0%, ${color}08 50%, transparent 92%)`,
        borderRadius: 22,
        border: `1px solid ${isSelectedGroup ? `${color}2e` : `${color}12`}`,
        boxShadow: isSelectedGroup
          ? `0 0 30px -16px ${color}, inset 0 0 52px -26px ${color}44`
          : `inset 0 0 54px -34px ${color}2d`,
        pointerEvents: 'none',
      }}
    />
  );
}, (prev, next) => {
  const a = prev.data;
  const b = next.data;
  return (
    a.group === b.group
    && a.width === b.width
    && a.height === b.height
    && a.coordinationRole === b.coordinationRole
  );
});

const NODE_TYPES = {
  atlas: AtlasNodeRenderer,
  columnHeader: ColumnHeaderRenderer,
  groupBackplate: AtlasGroupBackplateRenderer,
};

// ---------------------------------------------------------------------------
// AtlasRelationEdge — v6 custom edge. The orchestrator only emits edges that
// will both render AND carry a readable label (see visibleEdgeBudget in
// rfEdges). The component stays presentational: it draws the smoothstep
// path and renders an endpoint-aware HTML chip near the focus side of the
// edge, never at the raw geometric midpoint. The v5 midpoint-only placement
// dropped chips on top of intervening cards; the new placement keeps them
// in the gap next to the focus card so the relation is read as belonging to
// the hovered node, not floating in dead space.
// ---------------------------------------------------------------------------
type AtlasEdgeSemanticRole = 'primary' | 'pathway' | 'affinity';

interface AtlasRelationEdgeData {
  relation: string;
  /** Backend presentation role (pathway | membership | fallback). Surfaced on
   *  the DOM so the semantic evaluator can prove every drawn edge is typed and
   *  measure the pathway-vs-membership makeup of the drawn focus set. */
  presentationRole: WorldModelNavigationGraphPresentationRole;
  /** Compact endpoint-aware label, e.g. "OPENS → META-MISSIONS" or
   *  "← OPENS LAUNCHPAD". Pre-composed in rfEdges so the component
   *  stays presentational and the read direction is unambiguous. */
  label: string;
  /** True when the edge is admitted into the drawn-canvas budget. v6
   *  invariant: visibleEdgeBudget gates BOTH stroke and label, so this is
   *  always true on edges that reach the renderer. Kept on data for
   *  backcompat with layout-receipt readers. */
  labelVisible: boolean;
  tone: RelationStyle['tone'];
  priority: number;
  isBrushed: boolean;
  isFocusPrimary: boolean;
  coordinationRole: EdgeCoordinationRole | null;
  activeStroke: string;
  /** Which endpoint is the operator-anchored focus card, or null when the
   *  edge is brushed/coordination-driven without a single anchor. Drives
   *  label position: chip sits 28% of the way from focus toward the other
   *  end, so the operator's eye reads the line as belonging to focus. */
  focusEndpoint: 'source' | 'target' | null;
  /** Precomputed obstacle-avoiding orthogonal SVG path (flow coords) from the
   *  local router. Present ONLY when the straight route crossed a card AND the
   *  routed path validated collision-free; otherwise null and the renderer
   *  falls back to getSmoothStepPath. Lets the cross-cluster focus edges route
   *  around intervening cards instead of tunnelling through them. */
  routedPath: string | null;
  /** Salience ladder: primary (selected/brushed) > pathway (exact route) >
   *  affinity (membership/adjacency). A drawn edge must be legible AS its class
   *  — never a faint proof line — so this drives both the top-stroke weight and
   *  the dark contrast under-stroke. */
  semanticRole: AtlasEdgeSemanticRole;
  /** Paint the dark contrast under-stroke (the halo that keeps the line legible
   *  across tinted cluster backplates). Off for brush-dimmed background edges so
   *  they stay quiet. */
  showUnderStroke: boolean;
}

function areAtlasRelationEdgePropsEqual(
  prev: EdgeProps<AtlasRelationEdgeData>,
  next: EdgeProps<AtlasRelationEdgeData>,
): boolean {
  const a = prev.data;
  const b = next.data;
  return (
    prev.id === next.id
    && prev.sourceX === next.sourceX
    && prev.sourceY === next.sourceY
    && prev.targetX === next.targetX
    && prev.targetY === next.targetY
    && prev.sourcePosition === next.sourcePosition
    && prev.targetPosition === next.targetPosition
    && prev.markerEnd === next.markerEnd
    && prev.style?.stroke === next.style?.stroke
    && prev.style?.strokeWidth === next.style?.strokeWidth
    && prev.style?.strokeDasharray === next.style?.strokeDasharray
    && prev.style?.opacity === next.style?.opacity
    && a?.relation === b?.relation
    && a?.presentationRole === b?.presentationRole
    && a?.label === b?.label
    && a?.labelVisible === b?.labelVisible
    && a?.tone === b?.tone
    && a?.priority === b?.priority
    && a?.isBrushed === b?.isBrushed
    && a?.isFocusPrimary === b?.isFocusPrimary
    && a?.coordinationRole === b?.coordinationRole
    && a?.activeStroke === b?.activeStroke
    && a?.focusEndpoint === b?.focusEndpoint
    && a?.routedPath === b?.routedPath
    && a?.semanticRole === b?.semanticRole
    && a?.showUnderStroke === b?.showUnderStroke
  );
}

const AtlasRelationEdge = memo(function AtlasRelationEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
  data,
}: EdgeProps<AtlasRelationEdgeData>) {
  recordAtlasRender('AtlasRelationEdge');
  const [smoothPath, midX, midY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 6,
  });
  // Prefer the local obstacle router's path when it produced one (cross-cluster
  // edges that would otherwise tunnel through cards). It is null for edges whose
  // straight route was already clear, so same-column/clean edges keep the
  // familiar smoothstep curve untouched.
  const edgePath = data?.routedPath ?? smoothPath;
  const labelVisible = data?.labelVisible ?? false;
  const tone = data?.tone ?? 'gray';
  const activeStroke = data?.activeStroke ?? 'rgba(192,199,180,0.55)';
  // Anchor the chip to a point on the ACTUAL routed SVG path, not the
  // source→target chord. The v6 chord-interpolation placement landed chips
  // beside cards rather than on the routed segment, so when multiple edges
  // shared a focus card their chips clustered into the same gutter with no
  // visible binding to a specific line. We measure the rendered path and
  // place the chip relative to a path point chosen by focus side.
  //
  // focus-endpoint biasing:
  //   source focus → t=0.72 (chip near the other end, where edges diverge)
  //   target focus → t=0.28 (symmetric: chip near the non-focus end)
  //   no focus     → t=0.50 (mid-path)
  const defaultLabelT =
    data?.focusEndpoint === 'source' ? 0.72
    : data?.focusEndpoint === 'target' ? 0.28
    : 0.50;
  const NORMAL_OFFSET = 16;
  const measurePathRef = useRef<SVGPathElement | null>(null);
  const [anchor, setAnchor] = useState<{ x: number; y: number; nx: number; ny: number }>({
    x: midX,
    y: midY,
    nx: 0,
    ny: 1,
  });
  useLayoutEffect(() => {
    const path = measurePathRef.current;
    if (!path) return;
    const len = path.getTotalLength();
    if (!len) return;
    const t = Math.max(0.04, Math.min(0.96, defaultLabelT));
    const p = path.getPointAtLength(len * t);
    const before = path.getPointAtLength(Math.max(0, len * t - 2));
    const after = path.getPointAtLength(Math.min(len, len * t + 2));
    const tx = after.x - before.x;
    const ty = after.y - before.y;
    const mag = Math.hypot(tx, ty) || 1;
    setAnchor({ x: p.x, y: p.y, nx: -ty / mag, ny: tx / mag });
  }, [edgePath, defaultLabelT]);
  const labelX = anchor.x + anchor.nx * NORMAL_OFFSET;
  const labelY = anchor.y + anchor.ny * NORMAL_OFFSET;
  // Dual-stroke salience: a dark contrast under-stroke beneath the semantic top
  // stroke keeps every drawn edge legible across the tinted cluster backplates
  // without brightening the whole canvas. Width/opacity step by role so exact
  // routes read stronger than affinity ties. The under-stroke is solid even
  // when the top stroke is dotted, so dotted affinity ties gain a readable spine.
  const semanticRole: AtlasEdgeSemanticRole = data?.semanticRole ?? 'affinity';
  const showUnderStroke = data?.showUnderStroke ?? false;
  const topWidth = typeof style?.strokeWidth === 'number' ? style.strokeWidth : 1.4;
  const underOpacity = semanticRole === 'primary' ? 0.74 : semanticRole === 'pathway' ? 0.62 : 0.52;
  return (
    <>
      {showUnderStroke ? (
        <path
          d={edgePath}
          data-atlas-edge-role={semanticRole}
          fill="none"
          stroke="rgba(2,6,4,0.95)"
          strokeWidth={topWidth + 2.4}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={underOpacity}
          pointerEvents="none"
        />
      ) : null}
      <BaseEdge id={id} path={edgePath} style={style} markerEnd={markerEnd} />
      {/* Invisible measurement twin of the rendered path. Lets us measure
       *  the routed geometry with getTotalLength/getPointAtLength so the
       *  label anchor lands on the line, not on the source-target chord. */}
      <path
        ref={measurePathRef}
        d={edgePath}
        data-atlas-edge-mechanism={data?.relation ?? 'unknown'}
        data-atlas-edge-presentation-role={data?.presentationRole ?? 'fallback'}
        data-atlas-edge-labelled={labelVisible ? '1' : '0'}
        fill="none"
        stroke="transparent"
        pointerEvents="none"
      />
      {labelVisible && data ? (
        <>
          {/* Anchor pip + dashed leader binds the chip to its specific edge.
           *  Solves label-edge attribution when chips cluster in a shared
           *  corridor: every chip is visibly tethered to one line. */}
          <circle
            cx={anchor.x}
            cy={anchor.y}
            r={2.25}
            fill={activeStroke}
            opacity={0.95}
            pointerEvents="none"
          />
          <path
            d={`M ${anchor.x} ${anchor.y} L ${labelX} ${labelY}`}
            stroke={activeStroke}
            strokeWidth={1}
            strokeDasharray="2 2"
            opacity={0.72}
            fill="none"
            pointerEvents="none"
          />
          <EdgeLabelRenderer>
            <div
              className={clsx(
                'pointer-events-none absolute select-none whitespace-nowrap rounded-[4px] border bg-[rgba(6,10,7,0.96)] px-1.5 py-[2px] font-mono text-[9px] uppercase tracking-[0.14em] shadow-[0_2px_6px_-3px_rgba(0,0,0,0.85)] nodrag nopan',
                TONE_BORDER_CLASS[tone],
                TONE_TEXT_CLASS[tone],
                data.isBrushed && 'shadow-[0_0_10px_-1px_rgba(244,206,120,0.45)]',
              )}
              style={{
                transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
                borderColor: activeStroke,
                zIndex: data.isBrushed ? 120 : 110,
              }}
            >
              {data.label}
            </div>
          </EdgeLabelRenderer>
        </>
      ) : null}
    </>
  );
}, areAtlasRelationEdgePropsEqual);

const EDGE_TYPES = { atlasRelation: AtlasRelationEdge };

// ---------------------------------------------------------------------------
// Detail panel — selected view card.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Connected-by-how — group adjacency by relation rather than direction.
// Returns a list of ConnectedGroup buckets ordered by relation priority
// (lower priority numbers come first = strongest semantic relations on top).
// Each group surfaces the backend label + description from edge metadata
// so the operator reads HOW two views connect, not just THAT they do.
// ---------------------------------------------------------------------------
interface ConnectedNeighbour {
  view: AtlasView;
  direction: 'upstream' | 'downstream';
  weight: number | null;
  /** Edge index into the atlas edges[] array — used by relation brush to
   *  light up the exact line in the graph, not all edges of the same relation. */
  edgeIdx: number;
  /** Backend edge metadata for inline tooltip render. */
  edge: AtlasEdge;
}

interface ConnectedGroup {
  relation: string;
  label: string;
  category: string | null;
  description: string | null;
  tone: RelationStyle['tone'];
  priority: number;
  neighbours: ConnectedNeighbour[];
}

const WEAK_STRUCTURAL_RELATIONS = new Set(['shell_group', 'station_group', 'station_lens_menu']);

function groupConnectedByRelation(
  selectedId: string | null,
  edges: AtlasEdge[],
  viewsById: Map<string, AtlasView>,
): ConnectedGroup[] {
  if (!selectedId) return [];
  const buckets = new Map<string, ConnectedGroup>();
  edges.forEach((edge, idx) => {
    let direction: 'upstream' | 'downstream' | null = null;
    let otherId: string | null = null;
    if (edge.target === selectedId) {
      direction = 'upstream';
      otherId = edge.source;
    } else if (edge.source === selectedId) {
      direction = 'downstream';
      otherId = edge.target;
    }
    if (!direction || !otherId) return;
    const otherView = viewsById.get(otherId);
    if (!otherView) return;
    const style = styleForMechanism(edge.relation);
    const bucketKey = edge.relation;
    let bucket = buckets.get(bucketKey);
    if (!bucket) {
      bucket = {
        relation: edge.relation,
        label: edge.label || style.fallbackLabel,
        category: edge.category,
        description: edge.description ?? null,
        tone: style.tone,
        priority: style.priority,
        neighbours: [],
      };
      buckets.set(bucketKey, bucket);
    }
    // Avoid duplicates: same neighbour can appear twice if both directions
    // exist for the same relation. The first edge index wins as the brush
    // probe; the duplicate is dropped (still represented in the graph).
    if (!bucket.neighbours.some((n) => n.view.id === otherView.id)) {
      bucket.neighbours.push({
        view: otherView,
        direction,
        weight: edge.weight,
        edgeIdx: idx,
        edge,
      });
    }
  });
  return Array.from(buckets.values()).sort((a, b) => a.priority - b.priority);
}

const RelationLegend = memo(function RelationLegend({
  relationSummary,
  selectedRelationKey,
  onSelectRelation,
}: {
  relationSummary: WorldModelNavigationGraphRelationSummary[];
  selectedRelationKey?: string | null;
  onSelectRelation?: (key: string) => void;
}) {
  recordAtlasRender('RelationLegend');
  if (relationSummary.length === 0) return null;
  return (
    <div
      className="shrink-0 border-b border-[var(--zenith-border)]/35 px-5 py-3"
      style={{ contain: 'layout style' }}
      data-zenith-surface-atlas-relation-legend="ready"
      data-zenith-surface-atlas-relation-legend-row-count={relationSummary.length}
    >
      <div className="flex items-center gap-2">
        <h3 className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-zenith-muted">
          Relation legend
        </h3>
        <span className="ml-auto inline-flex items-center gap-1 rounded-[4px] border border-[var(--zenith-border)] bg-white/[0.03] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-soft">
          backend
        </span>
      </div>
      {(() => {
        const visibleRows = relationSummary.slice(0, RELATION_LEGEND_VISIBLE_LIMIT);
        const maxCountByRole = visibleRows.reduce((acc, row) => {
          acc[row.presentation_role] = Math.max(acc[row.presentation_role] ?? 0, row.edge_count);
          return acc;
        }, {} as Record<WorldModelNavigationGraphPresentationRole, number>);
        return (
          <ul className="mt-2 space-y-1">
            {visibleRows.map((row) => {
              const style = styleForMechanism(row.relation);
              const compactLabel = compactLabelForMechanism(row.relation);
              const backendLabel = row.label || style.fallbackLabel || row.relation;
              const key = relationKey(row);
              const selected = selectedRelationKey === key;
              const scaleMax = maxCountByRole[row.presentation_role] ?? row.edge_count;
              const widthPct = relationLegendBarWidthPct(row.edge_count, scaleMax);
              return (
                <li
                  key={key}
                  data-zenith-surface-atlas-relation-key={key}
                  data-zenith-surface-atlas-relation-backend-label={backendLabel}
                  data-zenith-surface-atlas-relation-compact-label={compactLabel}
                  data-zenith-surface-atlas-relation-role={row.presentation_role}
                  data-zenith-surface-atlas-relation-bar-scale="role_sqrt_min"
                  data-zenith-surface-atlas-relation-bar-width={widthPct}
                  data-zenith-surface-atlas-relation-edge-count={row.edge_count}
                >
                  <button
                    type="button"
                    onClick={() => onSelectRelation?.(key)}
                    aria-label={`${compactLabel} relation, ${row.edge_count} edges, ${presentationRoleLabel(row.presentation_role)}`}
                    className={clsx(
                      'w-full rounded-[5px] border px-2 py-1 text-left transition-colors',
                      selected
                        ? 'border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)]/75'
                        : 'border-transparent bg-transparent hover:border-white/10 hover:bg-white/[0.03]',
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={clsx(
                          'min-w-0 flex-1 truncate font-mono text-[10px] uppercase tracking-[0.16em]',
                          TONE_TEXT_CLASS[style.tone],
                        )}
                        title={`${row.relation} · ${backendLabel}`}
                      >
                        {compactLabel}
                      </span>
                      <span className="num-tab shrink-0 font-mono text-[10px] text-white/80">
                        {row.edge_count}
                      </span>
                    </div>
                    {/* Ranked bar — width is role-scaled and sqrt-compressed.
                        Backend counts stay literal; the visual scale keeps low-volume
                        pathway rows visible beside high-volume membership rows.
                        Replaces stacked role-tag + description chips at rest so the legend
                        reads as a chart, not paragraphs. Selected row expands details. */}
                    <div className="mt-1.5 h-[5px] w-full overflow-hidden rounded-[3px] bg-white/[0.04]">
                      <div
                        className="h-full rounded-[3px] transition-[width] duration-200"
                        style={{
                          width: `${widthPct}%`,
                          background: style.activeStroke,
                          opacity: selected ? 1 : 0.55,
                          boxShadow: selected ? `0 0 6px ${style.activeStroke}55` : undefined,
                        }}
                      />
                    </div>
                    {selected ? (
                      <div className="mt-2 space-y-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span
                            className={clsx(
                              'inline-flex rounded-[4px] border px-1.5 py-0.5 font-mono text-[8.5px] uppercase tracking-[0.14em]',
                              presentationRoleTone(row.presentation_role),
                            )}
                          >
                            {presentationRoleLabel(row.presentation_role)}
                          </span>
                          <span className="num-tab font-mono text-[9px] text-zenith-muted">
                            evidence {row.evidence_count}
                          </span>
                          {row.category ? (
                            <span className="truncate font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
                              {row.category.replace(/_/g, ' ')}
                            </span>
                          ) : null}
                        </div>
                        {row.description ? (
                          <p className="text-[10px] leading-snug text-zenith-soft">
                            {row.description}
                          </p>
                        ) : null}
                        {row.presentation_role === 'membership' ? (
                          <div className="rounded-[4px] border border-sky-400/15 bg-sky-400/[0.06] px-1.5 py-1 font-mono text-[8.5px] uppercase tracking-[0.14em] text-sky-100/80">
                            canvas: folded into columns/rail
                          </div>
                        ) : null}
                        {row.presentation_role === 'fallback' ? (
                          <div className="rounded-[4px] border border-amber-400/15 bg-amber-400/[0.06] px-1.5 py-1 font-mono text-[8.5px] uppercase tracking-[0.14em] text-amber-100/80">
                            fallback: low-authority adjacency
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </button>
                </li>
              );
            })}
          </ul>
        );
      })()}
    </div>
  );
});

function SampleEdgeList({
  edges,
  selectedEdgeKey,
  onSelectEdge,
}: {
  edges: WorldModelNavigationGraphSampleEdge[];
  selectedEdgeKey?: string | null;
  onSelectEdge?: (edgeKey: string) => void;
}) {
  if (edges.length === 0) return null;
  return (
    <ul className="mt-1 space-y-1 font-mono text-[10px]">
      {edges.slice(0, 5).map((edge, idx) => {
        const key = edge.edge_key ?? `${edge.source}:${edge.target}:${edge.relation ?? 'relation'}:${idx}`;
        const selectable = typeof edge.edge_key === 'string' && edge.edge_key.length > 0;
        const selected = selectedEdgeKey === edge.edge_key;
        const body = (
          <>
            <div className="flex items-center gap-1.5 text-white/75">
              <span className="truncate" title={edge.source_label ?? edge.source}>
                {edge.source_label ?? edge.source}
              </span>
              <span className="text-zenith-muted">→</span>
              <span className="truncate" title={edge.target_label ?? edge.target}>
                {edge.target_label ?? edge.target}
              </span>
            </div>
            <div className="truncate text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
              {edge.relation_label ?? edge.relation ?? 'relation'}
              {edge.evidence_refs && edge.evidence_refs.length > 0 ? ` · ${edge.evidence_refs.length} refs` : ''}
            </div>
          </>
        );
        return (
          <li
            key={key}
            className="min-w-0"
            data-zenith-surface-atlas-sample-edge-key={edge.edge_key ?? 'frontend_fallback'}
          >
            {selectable ? (
              <button
                type="button"
                onClick={() => onSelectEdge?.(edge.edge_key!)}
                onFocus={() => onSelectEdge?.(edge.edge_key!)}
                className={clsx(
                  'w-full min-w-0 rounded-[4px] px-1 py-0.5 text-left transition-colors',
                  selected ? 'bg-white/[0.07]' : 'hover:bg-white/[0.04]',
                )}
              >
                {body}
              </button>
            ) : (
              <div className="px-1 py-0.5">{body}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

const GroupFlowDrillthrough = memo(function GroupFlowDrillthrough({
  flow,
  selectedEdgeKey,
  onSelectEdge,
}: {
  flow: WorldModelNavigationGraphGroupFlow | null;
  selectedEdgeKey?: string | null;
  onSelectEdge?: (edgeKey: string) => void;
}) {
  recordAtlasRender('GroupFlowDrillthrough');
  if (!flow) return null;
  const sourceLabel = shellGroupLabel(flow.source_group);
  const targetLabel = shellGroupLabel(flow.target_group);
  const relationEntries = relationCountEntries(flow.relation_counts).slice(0, 6);
  const sampleEdges = Array.isArray(flow.sample_edges) ? flow.sample_edges : [];
  return (
    <div
      className="mt-2 rounded-[var(--zenith-radius-2xs)] border border-white/[0.09] bg-black/30 p-2.5"
      style={{ contain: 'layout style' }}
      data-zenith-surface-atlas-group-flow-drillthrough-panel="ready"
    >
      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-white/80">
        <span className="truncate" title={sourceLabel}>{sourceLabel}</span>
        <span className="text-zenith-muted">→</span>
        <span className="truncate" title={targetLabel}>{targetLabel}</span>
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1 font-mono text-[9.5px]">
        <dt className="text-zenith-muted">edges</dt>
        <dd className="num-tab text-right text-white">{flow.edge_count}</dd>
        <dt className="text-zenith-muted">evidence</dt>
        <dd className="num-tab text-right text-zenith-soft">{flow.evidence_count}</dd>
        <dt className="text-zenith-muted">dominant</dt>
        <dd className="truncate text-right text-[var(--zenith-accent)]" title={flow.dominant_relation}>
          {flow.dominant_relation_label ?? flow.dominant_relation}
        </dd>
      </dl>
      {relationEntries.length > 0 ? (
        <div className="mt-2">
          <div className="font-mono text-[8.5px] uppercase tracking-[0.18em] text-zenith-muted">
            relation breakdown
          </div>
          <div className="mt-1 flex flex-wrap gap-1">
            {relationEntries.map(([relation, count]) => {
              const style = styleForMechanism(relation);
              return (
                <span
                  key={relation}
                  className={clsx(
                    'inline-flex max-w-full items-center gap-1 rounded-[4px] border border-white/[0.08] bg-white/[0.03] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.12em]',
                    TONE_TEXT_CLASS[style.tone],
                  )}
                  title={relation}
                >
                  <span className="truncate">{relation.replace(/_/g, ' ')}</span>
                  <span className="num-tab text-white/70">{count}</span>
                </span>
              );
            })}
          </div>
        </div>
      ) : null}
      <div className="mt-2">
        <div className="font-mono text-[8.5px] uppercase tracking-[0.18em] text-zenith-muted">
          role breakdown
        </div>
        <div className="mt-1 grid grid-cols-3 gap-1 font-mono text-[9px]">
          {(['pathway', 'membership', 'fallback'] as const).map((role) => (
            <div key={role} className={clsx('rounded-[4px] border px-1 py-0.5', presentationRoleTone(role))}>
              <div className="uppercase tracking-[0.14em]">{role}</div>
              <div className="num-tab text-white/75">{flow.presentation_roles?.[role] ?? 0}</div>
            </div>
          ))}
        </div>
      </div>
      {sampleEdges.length > 0 ? (
        <div className="mt-2 border-t border-white/[0.07] pt-2">
          <div className="font-mono text-[8.5px] uppercase tracking-[0.18em] text-zenith-muted">
            sample edges
          </div>
          <SampleEdgeList
            edges={sampleEdges}
            selectedEdgeKey={selectedEdgeKey}
            onSelectEdge={onSelectEdge}
          />
          {typeof flow.sample_omitted_count === 'number' && flow.sample_omitted_count > 0 ? (
            <div className="mt-1 font-mono text-[9px] text-zenith-muted">
              +{flow.sample_omitted_count} more
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
});

const AtlasInteractionGuide = memo(function AtlasInteractionGuide() {
  recordAtlasRender('AtlasInteractionGuide');
  const rows = [
    {
      label: 'Hover',
      value: 'preview',
      icon: MousePointer2,
    },
    {
      label: 'Right-click',
      value: 'pin',
      icon: Pin,
    },
    {
      label: 'Left-click',
      value: 'open',
      icon: ExternalLink,
    },
    {
      label: 'Esc',
      value: 'clear',
      icon: null,
    },
  ];

  return (
    <section
      className="mt-5 border-t border-[var(--zenith-border)]/20 px-3 py-3"
      style={{ contain: 'layout style' }}
      data-zenith-surface-atlas-interactions="left-rail"
    >
      <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-zenith-muted">
        Interactions
      </div>
      <ul className="mt-2 space-y-1.5">
        {rows.map((row) => {
          const Icon = row.icon;
          return (
            <li key={row.label} className="flex items-center gap-2 text-[10.5px] text-zenith-soft/80">
              <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-[4px] border border-white/[0.08] bg-white/[0.02] text-zenith-muted">
                {Icon ? <Icon size={10} /> : <span className="font-mono text-[8px] uppercase tracking-[0.08em]">esc</span>}
              </span>
              <span className="min-w-[60px] font-mono text-[9.5px] uppercase tracking-[0.14em] text-zenith-muted">
                {row.label}
              </span>
              <span className="text-white/25">→</span>
              <span className="truncate text-zenith-soft/75">{row.value}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
});

const DetailPanel = memo(function DetailPanel({
  view,
  onOpen,
  connectedGroups,
  focusMode,
  onClearPin,
  brush,
  onBrushNeighbour,
  onClearBrush,
  mapStats,
  relationSummary,
  selectedRelationKey,
  onSelectRelation,
  groupFlows,
  selectedGroupFlow,
  selectedGroupFlowKey,
  onSelectGroupFlow,
  selectedEdgeKey,
  edgeFocus,
  onClearEdgeFocus,
  onSelectSampleEdge,
  onCollapseRail,
  regionMode = 'persistent',
}: {
  view: AtlasView | null;
  onOpen: (route: string) => void;
  connectedGroups: ConnectedGroup[];
  focusMode: AtlasFocus['mode'];
  onClearPin: () => void;
  brush: RelationBrush;
  onBrushNeighbour: (
    anchorId: string,
    relation: string,
    neighbour: ConnectedNeighbour,
  ) => void;
  onClearBrush: () => void;
  // Map-level stats surfaced when the rail is at rest. Lets the operator
  // read the Atlas's overall posture (count + capture ratio + legacy
  // count) without selecting a node. Optional so the prop stays
  // backward-compatible; rest-state degrades to interaction-only copy
  // when omitted.
  mapStats?: {
    views: number;
    edges: number;
    captured: number;
    legacy: number;
    failed?: number;
    overlays?: number;
  };
  relationSummary?: WorldModelNavigationGraphRelationSummary[];
  selectedRelationKey?: string | null;
  onSelectRelation?: (key: string) => void;
  // Wave SFA-2 — backend-owned edge grammar. Group-pair aggregate flows are
  // supplied by worldModel.navigation_graph.group_flows; the panel slices and
  // renders, but does not re-derive the aggregate.
  groupFlows?: WorldModelNavigationGraphGroupFlow[];
  selectedGroupFlow?: WorldModelNavigationGraphGroupFlow | null;
  selectedGroupFlowKey?: string | null;
  onSelectGroupFlow?: (key: string) => void;
  selectedEdgeKey?: string | null;
  // Wave 22 Phase 2 — Atlas Relation Audition. When an edge is clicked
  // in the React Flow canvas, the orchestrator passes the resolved
  // AtlasEdge + source/target view payload here. DetailPanel renders an
  // edge dossier section at the top of the rail (above the view
  // dossier / rest copy) so the operator can audition relationships
  // without losing surface selection context. Null = no edge in focus.
  edgeFocus?: {
    edge: AtlasEdge;
    sourceView: AtlasView | null;
    targetView: AtlasView | null;
  } | null;
  onClearEdgeFocus?: () => void;
  onSelectSampleEdge?: (edgeKey: string) => void;
  // Collapse the entire right rail. Optional so DetailPanel renders with or
  // without a parent that supports the affordance.
  onCollapseRail?: () => void;
  regionMode?: AtlasRailRegionMode;
}) {
  recordAtlasRender('DetailPanel');
  // Edge dossier section. Rendered at the top of the aside whenever an
  // edge is in focus, regardless of whether a node is also selected —
  // an edge click is an explicit relation-audition signal and should
  // dominate the rail until cleared (pane-click / Escape).
  const edgeDossier = edgeFocus ? (
    <div className="shrink-0 border-b border-[var(--zenith-border)]/60 bg-[var(--zenith-panel-muted)] px-5 py-3">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-zenith-muted">
          Relation
        </span>
        <span className="ml-auto inline-flex items-center gap-1.5 rounded-[4px] border border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] px-1.5 py-0.5 font-mono text-[9.5px] uppercase tracking-[0.18em] text-[var(--zenith-accent)]">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--zenith-accent)]" />
          edge focus
        </span>
        {onClearEdgeFocus ? (
          <button
            type="button"
            onClick={onClearEdgeFocus}
            className="inline-flex items-center gap-1 rounded-[4px] border border-zenith-edge bg-white/[0.03] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted transition-colors hover:border-zenith-edge-strong hover:text-zenith-soft"
            title="Clear edge focus (Esc)"
          >
            <X size={9} />
            esc
          </button>
        ) : null}
      </div>
      <h2 className="mt-2 truncate font-display text-[14px] uppercase leading-tight tracking-[0.04em] text-white">
        {edgeFocus.edge.label || edgeFocus.edge.relation}
      </h2>
      <div className="mt-1 flex items-center gap-1.5 font-mono text-[10px] tracking-[0.02em] text-zenith-muted">
        <span>{edgeFocus.edge.relation}</span>
        {edgeFocus.edge.category ? (
          <>
            <span className="text-white/25">·</span>
            <span>{edgeFocus.edge.category}</span>
          </>
        ) : null}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <span
          className={clsx(
            'inline-flex rounded-[4px] border px-1.5 py-0.5 font-mono text-[8.5px] uppercase tracking-[0.14em]',
            presentationRoleTone(edgeFocus.edge.presentationRole),
          )}
        >
          {presentationRoleLabel(edgeFocus.edge.presentationRole)}
        </span>
        <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
          {edgeFocus.edge.presentationRole === 'membership' ? 'rail only' : 'canvas eligible'}
        </span>
      </div>
      <dl className="mt-3 grid grid-cols-[44px_minmax(0,1fr)] gap-x-2 gap-y-1.5 font-mono text-[11px]">
        <dt className="text-zenith-muted">from</dt>
        <dd className="truncate text-white" title={edgeFocus.sourceView?.label ?? edgeFocus.edge.source}>
          {edgeFocus.sourceView?.label ?? edgeFocus.edge.source}
        </dd>
        <dt className="text-zenith-muted">to</dt>
        <dd className="truncate text-white" title={edgeFocus.targetView?.label ?? edgeFocus.edge.target}>
          {edgeFocus.targetView?.label ?? edgeFocus.edge.target}
        </dd>
        {edgeFocus.edge.weight !== null ? (
          <>
            <dt className="text-zenith-muted">weight</dt>
            <dd className="num-tab text-zenith-soft">{edgeFocus.edge.weight.toFixed(2)}</dd>
          </>
        ) : null}
        {edgeFocus.edge.rank !== null ? (
          <>
            <dt className="text-zenith-muted">rank</dt>
            <dd className="num-tab text-zenith-soft">{edgeFocus.edge.rank}</dd>
          </>
        ) : null}
      </dl>
      {edgeFocus.edge.description ? (
        <p className="mt-2 text-[11px] leading-snug text-zenith-soft">
          {edgeFocus.edge.description}
        </p>
      ) : null}
      {edgeFocus.edge.evidenceRefs.length > 0 ? (
        <div className="mt-2">
          <div className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-zenith-muted">
            evidence
          </div>
          <ul className="mt-1 space-y-0.5 font-mono text-[10px] text-zenith-soft">
            {edgeFocus.edge.evidenceRefs.slice(0, 4).map((ref) => (
              <li key={ref} className="truncate" title={ref}>{ref}</li>
            ))}
            {edgeFocus.edge.evidenceRefs.length > 4 ? (
              <li className="text-zenith-muted">
                +{edgeFocus.edge.evidenceRefs.length - 4} more
              </li>
            ) : null}
          </ul>
        </div>
      ) : null}
    </div>
  ) : null;
  if (!view) {
    return (
      <aside
        // P8 (std_station_aesthetic.json aesthetic_primitives_v1): resting
        // Atlas chrome has no overflow:scroll on rails. The at-rest rail
        // content (Inspector chrome + map-posture body + Interactions
        // section) fits h-full at supported viewports; `overflow-y-visible`
        // removes the unwanted scroll container without clipping content.
        // Selected rail (later in file) keeps overflow-y-auto because
        // selection legitimately surfaces more content.
        // Closes cap_quick_station_render_no_scroll_rail_overflow_a_5a273b3412d2;
        // evaluator gate G3 (atlas_aesthetic_evaluator.gate_rail_no_overflow_at_rest).
        className={clsx(
          'relative flex h-full min-h-0 shrink-0 flex-col overflow-y-visible border-l border-[var(--zenith-border)]/60 bg-[var(--zenith-panel-muted)]',
          regionMode === 'overlay' ? 'w-full' : 'w-[300px]',
        )}
        data-zenith-surface-atlas-rail="ready"
        data-zenith-view-region="rail"
        data-zenith-view-region-role="right_detail_rail"
        data-zenith-view-region-mode={regionMode}
        data-zenith-surface-atlas-selected-rail-state="resting"
        data-zenith-surface-atlas-selected-id="none"
        data-zenith-surface-atlas-selected-label=""
        data-zenith-surface-atlas-selected-pathway-count="0"
        data-zenith-surface-atlas-selected-pathway-fanin="0"
        data-zenith-surface-atlas-selected-pathway-fanout="0"
      >
        {edgeDossier}
        {/* Inspector chrome — at rest the rail leads with map posture (operator's
            cockpit prescription), not with "awaiting selection" copy. The chip
            still reports resting state, but the body carries pulse: surface
            count, capture ratio, legacy, edges. Interaction hints are demoted
            to the Interactions section at the bottom. */}
        <div className="shrink-0 border-b border-[var(--zenith-border)]/60 px-5 py-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-zenith-muted">
              Inspector
            </span>
            <span className="ml-auto inline-flex items-center gap-1.5 rounded-[4px] border border-[var(--zenith-border)] bg-white/[0.03] px-1.5 py-0.5 font-mono text-[9.5px] uppercase tracking-[0.18em] text-zenith-soft">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--zenith-accent)]/70" />
              resting
            </span>
            {onCollapseRail ? (
              <button
                type="button"
                onClick={onCollapseRail}
                className="inline-flex items-center gap-1 rounded-[4px] border border-zenith-edge bg-white/[0.03] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted transition-colors hover:border-zenith-edge-strong hover:text-zenith-soft"
                title="Hide rail (Esc)"
                aria-label="Hide rail"
              >
                <X size={9} />
                hide
              </button>
            ) : null}
          </div>
          <h2 className="mt-2 font-display text-[18px] uppercase leading-tight tracking-[0.04em] text-white">
            Atlas posture
          </h2>
          {mapStats ? (
            (() => {
              const ratio = mapStats.captured / Math.max(1, mapStats.views);
              const pct = Math.round(ratio * 100);
              const uncaptured = Math.max(0, mapStats.views - mapStats.captured);
              // Posture telemetry -> the single next move. Priority: genuine
              // failure (rose) outranks routine uncaptured (amber) outranks
              // settled. This is what turns "what exists" into "what to do".
              const failed = mapStats.failed ?? 0;
              const nextAction =
                failed > 0
                  ? { key: 'review_failed', tone: 'rose' as const, label: `Review ${failed} failed capture${failed === 1 ? '' : 's'}` }
                  : uncaptured > 0
                    ? { key: 'inspect_uncaptured', tone: 'amber' as const, label: `Inspect ${uncaptured} uncaptured surface${uncaptured === 1 ? '' : 's'}` }
                    : { key: 'all_captured', tone: 'signal' as const, label: 'All captured · monitor relation drift' };
              const nextActionDot =
                nextAction.tone === 'rose' ? 'bg-rose-400' : nextAction.tone === 'amber' ? 'bg-amber-300' : 'bg-emerald-300';
              const nextActionText =
                nextAction.tone === 'rose' ? 'text-rose-100' : nextAction.tone === 'amber' ? 'text-amber-100' : 'text-zenith-soft';
              return (
                <>
                  {/* Hero number — surface count dominates the rail so the
                      operator gets a system-scale read at a glance. */}
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="num-tab font-display text-[36px] leading-none text-white">
                      {mapStats.views}
                    </span>
                    <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-muted">
                      surfaces
                    </span>
                  </div>
                  {/* Capture-health bar — visual ratio replaces the spreadsheet
                      dl/dt grid so posture reads as a chart, not numbers. */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.16em] text-zenith-muted">
                      <span>capture health</span>
                      <span className="num-tab text-white">{pct}%</span>
                    </div>
                    <div className="mt-1.5 h-[8px] w-full overflow-hidden rounded-[4px] bg-white/[0.05]">
                      <div
                        className="h-full rounded-[4px] bg-emerald-400/80"
                        style={{
                          width: `${pct}%`,
                          boxShadow: '0 0 8px -2px rgba(16,185,129,0.45)',
                        }}
                      />
                    </div>
                    <div className="mt-1 flex justify-between font-mono text-[10px] text-zenith-soft/80">
                      <span>
                        <span className="num-tab text-zenith-signal">{mapStats.captured}</span>
                        <span className="text-zenith-muted"> captured</span>
                      </span>
                      {uncaptured > 0 ? (
                        <span>
                          <span className="num-tab text-amber-200">{uncaptured}</span>
                          <span className="text-zenith-muted"> uncaptured</span>
                        </span>
                      ) : null}
                    </div>
                  </div>
                  {/* Next action — converts posture telemetry into the single
                      most useful operator move. Quieter than the hero count,
                      louder than the demoted relation legend below. Tone tracks
                      the attention class so the eye lands on it before reading
                      cards. */}
                  <div
                    className="mt-3 flex items-center gap-2"
                    data-zenith-atlas-next-action={nextAction.key}
                    data-zenith-atlas-next-action-tone={nextAction.tone}
                  >
                    <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-zenith-muted">next</span>
                    <span aria-hidden className={clsx('inline-block h-1.5 w-1.5 shrink-0 rounded-full', nextActionDot)} />
                    <span className={clsx('font-mono text-[11px] leading-tight tracking-[0.01em]', nextActionText)}>
                      {nextAction.label}
                    </span>
                  </div>
                  {/* Secondary posture — edges + legacy on one row. */}
                  <div className="mt-3 flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
                    <span>
                      <span className="num-tab text-white">{mapStats.edges}</span>
                      <span> edges</span>
                    </span>
                    {typeof mapStats.overlays === 'number' && mapStats.overlays > 0 ? (
                      <span data-zenith-surface-atlas-posture-overlays={mapStats.overlays}>
                        <span className="num-tab text-[#c0a4c9]">{mapStats.overlays}</span>
                        <span> overlays</span>
                      </span>
                    ) : null}
                    {mapStats.legacy > 0 ? (
                      <span>
                        <span className="num-tab text-amber-200">{mapStats.legacy}</span>
                        <span> legacy</span>
                      </span>
                    ) : null}
                  </div>
                </>
              );
            })()
          ) : (
            <p className="mt-1 text-[11.5px] leading-snug text-zenith-soft">
              Waiting on backend posture.
            </p>
          )}
        </div>

        <RelationLegend
          relationSummary={relationSummary ?? []}
          selectedRelationKey={selectedRelationKey}
          onSelectRelation={onSelectRelation}
        />

        {/* Wave SFA-2 — Station Atlas edge grammar. Group-pair aggregates are
            backend-projected rail data, not a parallel ReactFlow edge layer. */}
        {groupFlows && groupFlows.length > 0 ? (
          <div
            className="shrink-0 border-b border-[var(--zenith-border)]/60 px-5 py-3"
            data-zenith-surface-atlas-group-flow-rail-mount="ready"
            data-zenith-surface-atlas-group-flow-rail-row-count={groupFlows.length}
          >
            <div className="flex items-center gap-2">
              <h3 className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-zenith-muted">
                Group flows
              </h3>
              <span className="ml-auto inline-flex items-center gap-1 rounded-[4px] border border-[var(--zenith-border)] bg-white/[0.03] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-soft">
                folded
              </span>
            </div>
            <p className="mt-1 text-[10.5px] leading-snug text-zenith-muted">
              Aggregate edges by shell-group pair. Folded out of the canvas so a line on the graph always means one exact pathway.
            </p>
            <ul className="mt-2 space-y-1.5 font-mono text-[10.5px]">
              {groupFlows.slice(0, 12).map((flow) => {
                const sourceLabel = shellGroupLabel(flow.source_group);
                const targetLabel = shellGroupLabel(flow.target_group);
                const relationStyle = styleForMechanism(flow.dominant_relation);
                const relationLabel = flow.dominant_relation_label
                  || relationStyle.fallbackLabel
                  || flow.dominant_relation;
                const key = groupFlowKey(flow);
                const selected = selectedGroupFlowKey ? selectedGroupFlowKey === key : selectedGroupFlow === flow;
                return (
                  <li
                    key={key}
                    data-zenith-surface-atlas-group-flow={key}
                  >
                    <button
                      type="button"
                      onClick={() => onSelectGroupFlow?.(key)}
                      onFocus={() => onSelectGroupFlow?.(key)}
                      className={clsx(
                        'flex w-full items-center gap-1.5 rounded-[4px] px-1 py-0.5 text-left transition-colors',
                        selected
                          ? 'bg-white/[0.07] text-white'
                          : 'text-zenith-soft hover:bg-white/[0.04] hover:text-white',
                      )}
                    >
                      <span className="truncate" title={sourceLabel}>{sourceLabel}</span>
                      <span className="text-zenith-muted">→</span>
                      <span className="truncate text-white" title={targetLabel}>{targetLabel}</span>
                      <span className="ml-auto flex shrink-0 items-center gap-1.5">
                        <span className="num-tab text-zenith-soft">{flow.edge_count}</span>
                        <span className="text-white/25">·</span>
                        <span
                          className={clsx(
                            'text-[9.5px] uppercase tracking-[0.14em]',
                            TONE_TEXT_CLASS[relationStyle.tone],
                          )}
                          title={flow.dominant_relation}
                        >
                          {relationLabel}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
            <GroupFlowDrillthrough
              flow={selectedGroupFlow ?? groupFlows[0] ?? null}
              selectedEdgeKey={selectedEdgeKey}
              onSelectEdge={onSelectSampleEdge}
            />
          </div>
        ) : null}

      </aside>
    );
  }
  const tone = captureTone(view);
  const strongConnectedGroups = connectedGroups.filter(
    (group) => !WEAK_STRUCTURAL_RELATIONS.has(group.relation),
  );
  const structuralConnectedGroups = connectedGroups.filter(
    (group) => WEAK_STRUCTURAL_RELATIONS.has(group.relation),
  );

  return (
    <aside
      className={clsx(
        'relative flex h-full min-h-0 shrink-0 flex-col overflow-y-auto border-l border-[var(--zenith-border)]/60 bg-[var(--zenith-panel-muted)]',
        regionMode === 'overlay' ? 'w-full' : 'w-[300px]',
      )}
      data-zenith-surface-atlas-rail="ready"
      data-zenith-view-region="rail"
      data-zenith-view-region-role="right_detail_rail"
      data-zenith-view-region-mode={regionMode}
      data-zenith-surface-atlas-selected-rail-state={focusMode === 'pinned' ? 'pinned' : 'selected'}
      data-zenith-surface-atlas-selected-id={view.id}
      data-zenith-surface-atlas-selected-label={view.label}
      data-zenith-surface-atlas-selected-kind={view.kind}
      data-zenith-surface-atlas-selected-pathway-count={view.pathwayCount}
      data-zenith-surface-atlas-selected-pathway-fanin={view.pathwayFanin}
      data-zenith-surface-atlas-selected-pathway-fanout={view.pathwayFanout}
      data-zenith-surface-atlas-selected-relation-fanin={view.fanin}
      data-zenith-surface-atlas-selected-relation-fanout={view.fanout}
      data-zenith-surface-atlas-selected-island={view.pathwayCount === 0 && view.kind === 'page' ? 'true' : 'false'}
    >
      {edgeDossier}
      <div className="shrink-0 border-b border-[var(--zenith-border)]/60 bg-[var(--zenith-panel-muted)] px-5 py-3">
        <div className="flex items-center gap-2">
          <span
            className="inline-flex h-6 w-6 items-center justify-center rounded-[var(--zenith-radius-2xs)]"
            style={{
              borderColor: SHELL_GROUP_COLOR[view.shellGroup],
              borderWidth: 1,
              borderStyle: 'solid',
              background: `${SHELL_GROUP_COLOR[view.shellGroup]}1f`,
            }}
          >
            <CircleDot size={11} style={{ color: SHELL_GROUP_COLOR[view.shellGroup] }} />
          </span>
          <span className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-zenith-muted">
            Surface
          </span>
          <span className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-[var(--zenith-accent)]">
            {view.kind}
          </span>
          {focusMode === 'pinned' ? (
            <button
              type="button"
              onClick={onClearPin}
              title="Clear pinned focus (Esc)"
              className="ml-auto inline-flex items-center gap-1 rounded-[4px] border border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] px-1.5 py-0.5 font-mono text-[9.5px] uppercase tracking-[0.18em] text-[var(--zenith-accent)] hover:border-[var(--zenith-accent)]"
            >
              <Pin size={9} />
              Pinned · Esc
            </button>
          ) : (
            <span
              className={clsx(
                'ml-auto inline-flex items-center gap-1 rounded-[4px] border px-1.5 py-0.5 font-mono text-[9.5px] uppercase tracking-[0.18em]',
                tone === 'signal'
                  ? 'border-emerald-400/30 text-emerald-200'
                  : tone === 'amber'
                    ? 'border-amber-400/30 text-amber-200'
                    : tone === 'rose'
                      ? 'border-rose-400/30 text-rose-200'
                      : 'border-white/[0.10] text-zenith-soft',
              )}
            >
              <CircleDot size={9} />
              {captureStatusLabel(view.captureLatestStatus, view.captureSlug)}
            </span>
          )}
          {onCollapseRail ? (
            <button
              type="button"
              onClick={onCollapseRail}
              className="inline-flex items-center gap-1 rounded-[4px] border border-zenith-edge bg-white/[0.03] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted transition-colors hover:border-zenith-edge-strong hover:text-zenith-soft"
              title="Hide rail (Esc)"
              aria-label="Hide rail"
            >
              <X size={9} />
              hide
            </button>
          ) : null}
        </div>
        <h2 className="mt-2 truncate font-display text-[18px] uppercase leading-tight tracking-[0.04em] text-white">
          {view.label}
        </h2>
        <div className="mt-1 flex items-center gap-2 font-mono text-[10.5px] tracking-[0.04em] text-zenith-muted">
          <Terminal size={10} className="opacity-70" />
          {view.route}
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        <section className="border-l border-[var(--zenith-accent-edge)] pl-4">
          <h3 className="font-display text-[10.5px] uppercase tracking-[0.28em] text-[var(--zenith-accent)]">
            Purpose
          </h3>
          <p className="mt-2 text-[12.5px] leading-[1.55] text-[var(--zenith-text)]">
            {view.purpose || 'No purpose declared.'}
          </p>
        </section>

        <div className="grid grid-cols-2 gap-2 font-mono text-[10.5px]">
          <KeyValue label="shell group" value={SHELL_GROUP_LABEL[view.shellGroup]} />
          <KeyValue label="station group" value={view.stationGroup ?? '—'} />
          <KeyValue label="kind" value={view.kind} />
          <KeyValue label="posture" value={view.posture.replace(/_/g, ' ')} />
          <KeyValue label="terminal" value={view.culDeSacEffective ? 'yes' : 'no'} />
          {/* Hover pathway is the operator-facing "what lights up on hover"
           * truth; all-relations is the raw substrate count (includes folded
           * membership). Hover row leads because it matches what the canvas
           * actually does. Island warning fires when a substantive page has
           * zero pathway -- under the pathway hover contract this should
           * only happen if the audit has drifted. */}
          <KeyValue
            label="hover pathway"
            value={
              view.pathwayCount === 0 && view.kind === 'page'
                ? `0 ⚠ island`
                : `${view.pathwayCount} (in ${view.pathwayFanin} · out ${view.pathwayFanout})`
            }
          />
          <KeyValue label="all relations" value={`${view.fanin} in · ${view.fanout} out`} />
          <KeyValue label="primary" value={view.primaryComponent?.split('/').pop() ?? '—'} />
        </div>

        <section>
          <h3 className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-zenith-muted">
            Substrate binding
          </h3>
          <div className="mt-2 rounded-[var(--zenith-radius-xs)] border border-white/[0.10] bg-black/25 p-3">
            <div className="flex flex-wrap gap-1.5">
              {(view.substrateBindings.length > 0 ? view.substrateBindings : ['unbound']).slice(0, 8).map((binding) => (
                <span
                  key={binding}
                  className={clsx(
                    'rounded-[4px] border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em]',
                    binding === 'unbound'
                      ? 'border-rose-400/25 text-rose-200/80'
                      : 'border-white/[0.12] text-zenith-soft',
                  )}
                >
                  {binding}
                </span>
              ))}
            </div>
            {view.authorityNote ? (
              <p className="mt-2 text-[10.5px] leading-snug text-zenith-muted">
                {view.authorityNote}
              </p>
            ) : null}
            {view.backendEndpoints.length > 0 || view.sharedComponents.length > 0 ? (
              <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-[9.5px] text-white/50">
                <div className="min-w-0">
                  <span className="text-white/30">api</span>{' '}
                  <span className="text-zenith-soft">{view.backendEndpoints.length}</span>
                </div>
                <div className="min-w-0">
                  <span className="text-white/30">components</span>{' '}
                  <span className="text-zenith-soft">{view.sharedComponents.length}</span>
                </div>
              </div>
            ) : null}
          </div>
        </section>

        <section>
          <h3 className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-zenith-muted">
            Capture posture
          </h3>
          <div className="mt-2 rounded-[var(--zenith-radius-xs)] border border-white/[0.10] bg-black/30 p-3 font-mono text-[10.5px]">
            <div className="flex items-center justify-between gap-2">
              <span className="text-zenith-muted">slug</span>
              <span className="truncate text-[var(--zenith-accent)]">
                {view.captureSlug ?? '—'}
              </span>
            </div>
            <div className="mt-1 flex items-center justify-between gap-2">
              <span className="text-zenith-muted">samples</span>
              <span className="text-white/80">{view.captureSampleCount}</span>
            </div>
            {view.captureLatestLoadMs != null ? (
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="text-zenith-muted">latest load</span>
                <span className="text-white/80">{view.captureLatestLoadMs}ms</span>
              </div>
            ) : null}
          </div>
        </section>

        {connectedGroups.length > 0 ? (
          <section>
            <h3 className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-zenith-muted">
              Connected views — by relation
            </h3>
            <p className="mt-1 text-[10.5px] leading-snug text-zenith-muted">
              Hover a row to brush the graph: anchor stays at 100%, neighbour
              jumps to 90% with relation halo, unrelated drops to ~10%.
              Click to open. Backend metadata from
              {' '}<code className="text-zenith-soft">worldModel.navigation_graph.edges</code>.
            </p>
            {strongConnectedGroups.length > 0 ? (
              <ul className="mt-2 space-y-2.5">
                {strongConnectedGroups.map((group) => (
                <li
                  key={group.relation}
                  className={clsx(
                    'rounded-[var(--zenith-radius-2xs)] border bg-black/30 p-2.5',
                    TONE_BORDER_CLASS[group.tone],
                  )}
                >
                  <div className="flex items-center gap-1.5">
                    <span
                      aria-hidden
                      className="inline-flex h-2 w-2 shrink-0 rounded-full"
                      style={{ background: styleForMechanism(group.relation).activeStroke }}
                    />
                    <span
                      className={clsx(
                        'font-mono text-[10px] uppercase tracking-[0.18em]',
                        TONE_TEXT_CLASS[group.tone],
                      )}
                    >
                      {group.label}
                    </span>
                    <span className="ml-auto font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted">
                      {group.neighbours.length}
                    </span>
                  </div>
                  {group.description ? (
                    <p className="mt-1 text-[10px] leading-snug text-zenith-soft">
                      {group.description}
                    </p>
                  ) : null}
                  <ul className="mt-2 space-y-px">
                    {group.neighbours.slice(0, 8).map((n) => {
                      const isBrushed =
                        brush.mode === 'connected_row' &&
                        brush.anchorId === view.id &&
                        brush.relation === group.relation &&
                        brush.neighborId === n.view.id;
                      return (
                        <li key={`${group.relation}:${n.view.id}:${n.direction}`}>
                          <button
                            type="button"
                            onClick={() => onOpen(n.view.entryRoute)}
                            onMouseEnter={() => onBrushNeighbour(view.id, group.relation, n)}
                            onMouseLeave={onClearBrush}
                            onFocus={() => onBrushNeighbour(view.id, group.relation, n)}
                            onBlur={onClearBrush}
                            className={clsx(
                              'flex w-full items-center gap-1.5 rounded-[3px] px-1 py-0.5 text-left font-mono text-[10.5px] transition-colors',
                              isBrushed
                                ? clsx('bg-white/[0.07]', TONE_TEXT_CLASS[group.tone])
                                : 'text-white/75 hover:bg-white/[0.05] hover:text-[var(--zenith-accent)]',
                            )}
                          >
                            {n.direction === 'upstream' ? (
                              <ArrowUpLeft size={9} className="shrink-0 opacity-70" />
                            ) : (
                              <ArrowDownRight size={9} className="shrink-0 opacity-70" />
                            )}
                            <span className="truncate">{n.view.label}</span>
                            <span className="ml-auto truncate font-mono text-[9px] text-zenith-muted">
                              {n.view.route}
                            </span>
                          </button>
                          {isBrushed ? (
                            <BrushedEdgeTooltip
                              anchorLabel={view.label}
                              neighbourLabel={n.view.label}
                              edge={n.edge}
                              tone={group.tone}
                            />
                          ) : null}
                        </li>
                      );
                    })}
                    {group.neighbours.length > 8 ? (
                      <li className="px-1 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted">
                        + {group.neighbours.length - 8} more
                      </li>
                    ) : null}
                  </ul>
                </li>
                ))}
              </ul>
            ) : null}
            {structuralConnectedGroups.length > 0 ? (
              <div className="mt-2 rounded-[var(--zenith-radius-2xs)] border border-white/[0.08] bg-black/20 p-2.5">
                <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-zenith-muted">
                  Structural reachability
                </div>
                <ul className="mt-1.5 space-y-1">
                  {structuralConnectedGroups.map((group) => (
                    <li
                      key={group.relation}
                      className="flex items-center gap-2 font-mono text-[10px] text-white/50"
                    >
                      <span
                        aria-hidden
                        className="inline-flex h-1.5 w-1.5 rounded-full"
                        style={{ background: styleForMechanism(group.relation).activeStroke }}
                      />
                      <span className={clsx('uppercase tracking-[0.14em]', TONE_TEXT_CLASS[group.tone])}>
                        {group.label}
                      </span>
                      <span className="ml-auto text-zenith-muted">
                        {group.neighbours.length} grouped {group.neighbours.length === 1 ? 'neighbour' : 'neighbours'}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        ) : null}

        <section>
          <h3 className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-zenith-muted">
            Authority
          </h3>
          <p className="mt-1 break-all font-mono text-[10.5px] text-zenith-soft">
            {view.evidenceFile ?? 'system/server/ui/src/navigation/surfaces.ts'}
          </p>
        </section>

        <button
          type="button"
          onClick={() => onOpen(view.entryRoute)}
          className="inline-flex w-full items-center justify-center gap-1.5 rounded-[var(--zenith-radius-2xs)] border border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-[var(--zenith-accent)] transition-all hover:border-[var(--zenith-accent)] hover:bg-[var(--zenith-accent)] hover:text-[var(--zenith-accent-ink)]"
        >
          <ExternalLink size={11} />
          Open {view.label}
        </button>
      </div>
    </aside>
  );
});

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--zenith-radius-2xs)] border border-white/[0.10] bg-black/25 px-2 py-1.5">
      <div className="font-mono text-[8.5px] uppercase tracking-[0.22em] text-zenith-muted">
        {label}
      </div>
      <div className="mt-0.5 truncate font-mono text-[11px] text-white/85">{value}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// BrushedEdgeTooltip — inline edge-detail card rendered directly beneath
// a hovered connected-views row. This is the "unfolding edge" pattern from
// the v4 contour: edge metadata appears on demand instead of always-on
// labels. Pulls label / description / category / weight straight from the
// backend edge metadata so the operator reads HOW two views relate.
// ---------------------------------------------------------------------------
function BrushedEdgeTooltip({
  anchorLabel,
  neighbourLabel,
  edge,
  tone,
}: {
  anchorLabel: string;
  neighbourLabel: string;
  edge: AtlasEdge;
  tone: RelationStyle['tone'];
}) {
  return (
    <div
      className={clsx(
        'mt-1 rounded-[5px] border bg-black/55 px-2 py-1.5 font-mono text-[10px] leading-tight',
        TONE_BORDER_CLASS[tone],
      )}
    >
      <div className={clsx('flex items-center gap-1 text-[10px]', TONE_TEXT_CLASS[tone])}>
        <span className="truncate">{anchorLabel}</span>
        <span aria-hidden className="opacity-70">↔</span>
        <span className="truncate">{neighbourLabel}</span>
      </div>
      <div className="mt-1 font-mono text-[9.5px] uppercase tracking-[0.16em] text-white/80">
        {edge.label || edge.relation}
      </div>
      {edge.description ? (
        <div className="mt-1 text-[10px] leading-snug text-zenith-soft normal-case tracking-normal">
          {edge.description}
        </div>
      ) : null}
      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
        {edge.category ? (
          <span>
            <span className="text-white/30">category</span>{' '}
            <span className="text-zenith-soft">{edge.category.replace(/_/g, ' ')}</span>
          </span>
        ) : null}
        {edge.weight != null ? (
          <span>
            <span className="text-white/30">weight</span>{' '}
            <span className="text-zenith-soft">{edge.weight.toFixed(2)}</span>
          </span>
        ) : null}
        <span>
          <span className="text-white/30">mech</span>{' '}
          <span className="text-zenith-soft">{edge.relation}</span>
        </span>
      </div>
      {edge.evidenceRefs.length > 0 ? (
        // Substrate evidence rail. Upstream extractors in
        // tools/meta/observability/frontend_nav_graph.py populate
        // edge.evidence_refs with file:line / station_views:slug / shared-
        // component-path tokens; system/server/world_model.py:1336 caps the
        // payload at 12 entries. Render at most 4 here so the tooltip stays
        // legible; the rest fold into a "+N more" affordance.
        <div className="mt-1.5 border-t border-white/[0.07] pt-1 font-mono text-[9px] normal-case tracking-[0.04em] text-zenith-soft">
          <div className="text-[8.5px] uppercase tracking-[0.16em] text-zenith-muted">evidence</div>
          <ul className="mt-0.5 space-y-px text-zenith-soft">
            {edge.evidenceRefs.slice(0, 4).map((ref) => (
              <li key={ref} className="truncate">
                {ref}
              </li>
            ))}
            {edge.evidenceRefs.length > 4 ? (
              <li className="text-zenith-muted">+ {edge.evidenceRefs.length - 4} more</li>
            ) : null}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Group rail — categories with counts.
// ---------------------------------------------------------------------------

const GroupRail = memo(function GroupRail({
  views,
  activeGroup,
  setActiveGroup,
  regionMode = 'persistent',
}: {
  views: AtlasView[];
  activeGroup: ShellSurfaceGroupId | 'unassigned' | 'all';
  setActiveGroup: (g: ShellSurfaceGroupId | 'unassigned' | 'all') => void;
  regionMode?: AtlasRailRegionMode;
}) {
  recordAtlasRender('GroupRail');
  const counts = useMemo(() => {
    const c = new Map<ShellSurfaceGroupId | 'unassigned', number>();
    for (const group of SHELL_GROUP_ORDER) c.set(group, 0);
    for (const v of views) {
      c.set(v.shellGroup, (c.get(v.shellGroup) ?? 0) + 1);
    }
    return c;
  }, [views]);

  return (
    <aside
      className={clsx(
        'relative flex h-full min-h-0 flex-col border-r border-[var(--zenith-border)]/35 bg-[rgba(5,8,5,0.76)]',
        regionMode === 'overlay' ? 'overflow-y-auto' : 'overflow-y-visible',
      )}
      data-zenith-surface-atlas-rail="ready"
      data-zenith-view-region="rail"
      data-zenith-view-region-role="left_group_rail"
      data-zenith-view-region-mode={regionMode}
      style={{ contain: 'layout style' }}
    >
      <div className="shrink-0 border-b border-[var(--zenith-border)]/30 px-3 py-[var(--zenith-space-2-5)]">
        <div className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-zenith-muted">
          Categories
        </div>
      </div>
      <ul className="px-2 py-2 space-y-px">
        <GroupRailRow
          label="All surfaces"
          icon={Network}
          count={views.length}
          color="var(--zenith-accent)"
          active={activeGroup === 'all'}
          onClick={() => setActiveGroup('all')}
        />
        {SHELL_GROUP_ORDER.map((group) => {
          const count = counts.get(group) ?? 0;
          if (count === 0 && group === 'unassigned') return null;
          const Icon = SHELL_GROUP_ICON[group];
          return (
            <GroupRailRow
              key={group}
              label={SHELL_GROUP_LABEL[group]}
              icon={Icon}
              count={count}
              color={SHELL_GROUP_COLOR[group]}
              active={activeGroup === group}
              onClick={() => setActiveGroup(group)}
            />
          );
        })}
      </ul>

      <section className="mt-4 border-t border-[var(--zenith-border)]/25 px-3 py-3 opacity-80">
        <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-zenith-muted">
          Legend
        </div>
        <ul className="mt-1.5 space-y-1 font-mono text-[10px]">
          <li className="flex items-center gap-1.5 text-zenith-soft">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-300/90" />
            captured
          </li>
          <li className="flex items-center gap-1.5 text-zenith-soft">
            <span className="inline-block h-2 w-2 rounded-full bg-amber-300/90" />
            uncaptured
          </li>
          <li className="flex items-center gap-1.5 text-zenith-soft">
            <span className="inline-block h-2 w-2 rounded-full bg-rose-300/90" />
            failed
          </li>
          <li className="flex items-center gap-1.5 text-zenith-soft">
            <span className="inline-block h-2 w-2 rounded-full bg-white/30" />
            not configured
          </li>
        </ul>
      </section>

      <AtlasInteractionGuide />

      <section className="mt-auto border-t border-[var(--zenith-border)]/20 px-3 py-3 text-[10px] leading-snug text-zenith-soft/55">
        {/* Bumped from white/35 + white/45 to white/65 + white/70 so the
            authority caption clears WCAG AA contrast on the dark panel
            background. The "Atlas" label still reads as a header weight
            via the uppercase + tracking treatment; the prose body is
            now legible without leaning in. Per
            cap_quick_atlas_footer_caption_text_fails_comforta_8f7e4cee76cd. */}
        <div className="font-mono uppercase tracking-[0.18em] text-zenith-soft/70">Atlas</div>
        Adapter view over <code className="text-[var(--zenith-accent)]">/world-model/snapshot::navigation_graph</code>. Layout columns the 4 shell groups; node fanin/fanout come from the substrate.
      </section>
    </aside>
  );
});

const GroupRailRow = memo(function GroupRailRow({
  label,
  icon: Icon,
  count,
  color,
  active,
  onClick,
}: {
  label: string;
  icon: LucideIcon;
  count: number;
  color: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className={clsx(
          'flex w-full items-center gap-2 rounded-[4px] px-2 py-1.5 text-left transition-colors',
          active
            ? 'bg-[linear-gradient(90deg,rgba(199,176,106,0.10),rgba(199,176,106,0.025))]'
            : 'hover:bg-white/[0.04]',
        )}
      >
        <span
          aria-hidden
          className="inline-block h-2 w-2 shrink-0 rounded-full"
          style={{ background: color }}
        />
        <Icon size={11} className="shrink-0 text-zenith-soft" />
        <span
          className={clsx(
            'min-w-0 flex-1 truncate font-mono text-[11px] tracking-[0.04em]',
            active ? 'text-[var(--zenith-accent)]' : 'text-white/70',
          )}
        >
          {label}
        </span>
        <span className="shrink-0 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted">
          {count}
        </span>
      </button>
    </li>
  );
});

// ---------------------------------------------------------------------------
// Shell header + bottom action bar
// ---------------------------------------------------------------------------

function ShellHeader({
  totalViews,
  totalEdges,
  capturedCount,
  legacyCount,
  pathwayEdgeCount,
  pathwayAuditStatus,
  pathwayZeroSubstantiveCount,
  search,
  setSearch,
  onRefresh,
  densityMode,
  setDensityMode,
}: {
  totalViews: number;
  totalEdges: number;
  capturedCount: number;
  legacyCount: number;
  pathwayEdgeCount: number;
  pathwayAuditStatus: 'ok' | 'drift' | string;
  pathwayZeroSubstantiveCount: number;
  search: string;
  setSearch: (s: string) => void;
  onRefresh: () => void;
  densityMode: EdgeDensityMode;
  setDensityMode: (mode: EdgeDensityMode) => void;
}) {
  const [utc, setUtc] = useState<string>(() => formatUtc(new Date()));
  useEffect(() => {
    const id = window.setInterval(() => setUtc(formatUtc(new Date())), 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <header className="relative flex shrink-0 items-center gap-3 border-b border-[var(--zenith-border)]/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.018),rgba(255,255,255,0)),rgba(7,10,7,0.92)] px-5 py-2 backdrop-blur-xl">
      <div className="flex items-center gap-[var(--zenith-space-2-5)]">
        <div className="relative flex h-6 w-6 items-center justify-center rounded-[var(--zenith-radius-2xs)] border border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)]">
          <MapIcon size={11} className="text-[var(--zenith-accent)]" strokeWidth={2.2} />
        </div>
        <div className="flex flex-col leading-none">
          <span className="font-mono text-[9.5px] uppercase tracking-[0.32em] text-zenith-muted">
            Station
          </span>
          <span className="font-display text-[14px] leading-none tracking-normal text-white/90">
            Surface Atlas
          </span>
        </div>
      </div>

      <div className="mx-2 h-7 w-px bg-[var(--zenith-border)]" aria-hidden />

      <div className="relative flex min-w-[280px] items-center">
        <Search size={11} className="absolute left-2.5 text-zenith-muted" />
        <input
          type="search"
          placeholder="search routes, purposes, keywords…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-[var(--zenith-radius-2xs)] border border-white/[0.12] bg-black/30 px-7 py-1 font-mono text-[11px] tracking-[0.02em] text-white/85 placeholder:text-white/30 focus:border-[var(--zenith-accent-edge)] focus:outline-none focus:ring-0"
        />
      </div>

      <div className="ml-auto flex flex-wrap items-center gap-1.5">
        <StatChip label="Pages" value={String(totalViews)} tone="muted" />
        <StatChip label="Edges" value={String(totalEdges)} tone="muted" />
        {/* Pathway hover edges = the subset of `Edges` that paints on hover
         * in 'clean' mode. Tone tracks the pathway hover audit: signal when
         * the backend contract reports ok (no substantive zero-pathway
         * pages), rose when drift (an island shipped without outboundTo
         * declarations -- the regression the audit was built to catch). */}
        <StatChip
          label="Hover"
          value={
            pathwayZeroSubstantiveCount > 0
              ? `${pathwayEdgeCount} · ${pathwayZeroSubstantiveCount} island${pathwayZeroSubstantiveCount === 1 ? '' : 's'}`
              : String(pathwayEdgeCount)
          }
          tone={
            pathwayAuditStatus === 'ok'
              ? 'signal'
              : pathwayAuditStatus === 'drift'
                ? 'rose'
                : 'muted'
          }
        />
        <StatChip label="Captured" value={`${capturedCount}/${totalViews}`} tone="signal" />
        {legacyCount > 0 ? <StatChip label="Legacy" value={String(legacyCount)} tone="amber" /> : null}
        <DensityModeToggle mode={densityMode} setMode={setDensityMode} />
        <button
          type="button"
          onClick={onRefresh}
          title="Refresh navigation graph"
          className="inline-flex h-7 w-7 items-center justify-center rounded-[var(--zenith-radius-2xs)] border border-white/[0.15] bg-white/[0.04] text-zenith-soft transition-colors hover:border-white/30 hover:text-white"
        >
          <RefreshCw size={12} />
        </button>
        <div className="ml-1 inline-flex items-center gap-1.5 rounded-[var(--zenith-radius-2xs)] border border-white/[0.12] bg-black/30 px-2 py-1 font-mono text-[11px] tracking-[0.04em] text-white/85">
          <span className="relative inline-flex h-1.5 w-1.5 items-center justify-center">
            <span className="absolute inset-0 animate-ping rounded-full bg-emerald-300/40" />
            <span className="relative inline-block h-1.5 w-1.5 rounded-full bg-emerald-300/95" />
          </span>
          {utc}
        </div>
      </div>
    </header>
  );
}

function formatUtc(d: Date): string {
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  return `${hh}:${mm}:${ss}`;
}

function DensityModeToggle({
  mode,
  setMode,
}: {
  mode: EdgeDensityMode;
  setMode: (mode: EdgeDensityMode) => void;
}) {
  const active = EDGE_DENSITY_MODES.find((m) => m.id === mode) ?? EDGE_DENSITY_MODES[0];
  return (
    <div
      className="inline-flex items-center rounded-[var(--zenith-radius-2xs)] border border-white/[0.12] bg-black/30 p-0.5 font-mono text-[10px]"
      title={`Edge density: ${active.label} — ${active.description}`}
    >
      <Filter size={11} className="ml-1 mr-1 text-zenith-muted" />
      {EDGE_DENSITY_MODES.map((m) => (
        <button
          key={m.id}
          type="button"
          onClick={() => setMode(m.id)}
          title={m.description}
          className={clsx(
            'rounded-[4px] px-1.5 py-0.5 uppercase tracking-[0.16em] transition-colors',
            m.id === mode
              ? 'bg-[var(--zenith-accent-soft)] text-[var(--zenith-accent)]'
              : 'text-zenith-soft hover:text-white/85',
          )}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}

function StatChip({ label, value, tone }: { label: string; value: string; tone: 'signal' | 'amber' | 'rose' | 'muted' }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-[var(--zenith-radius-2xs)] border bg-white/[0.02] px-2 py-1 font-mono text-[10px] tracking-[0.04em]',
        tone === 'signal'
          ? 'border-emerald-400/30 text-emerald-300'
          : tone === 'amber'
            ? 'border-amber-400/30 text-amber-200'
            : tone === 'rose'
              ? 'border-rose-400/40 text-rose-200'
              : 'border-white/[0.10] text-zenith-soft',
      )}
    >
      <span className="text-zenith-muted">{label}</span>
      <span className="text-white/85">{value}</span>
    </span>
  );
}

function aliveStateTone(state: string | null | undefined): 'signal' | 'amber' | 'rose' | 'muted' {
  if (state === 'populated' || state === 'correctly_empty' || state === 'ready') return 'signal';
  if (state === 'blocked' || state === 'error') return 'rose';
  if (state === 'dormant' || state === 'mixed' || state === 'loading') return 'amber';
  return 'muted';
}

function aliveMetric(row: StationAliveCockpitRow, key: string): string | number | boolean | null | undefined {
  return row.metrics?.[key];
}

function formatAliveMetricValue(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined) return '0';
  if (typeof value === 'boolean') return value ? 'yes' : 'no';
  return String(value);
}

function compactMetricLabel(key: string): string {
  return key
    .replace(/_count$/u, '')
    .replace(/_runs$/u, '')
    .replace(/_/gu, ' ');
}

function aliveMetricSummary(row: StationAliveCockpitRow): string {
  const backendSummary = row.summary_label?.trim();
  if (backendSummary) return backendSummary;
  if (row.surface_id === 'demo_takes') {
    return `takes ${formatAliveMetricValue(aliveMetric(row, 'take_count'))}`;
  }
  if (row.surface_id === 'imaginations') {
    return `items ${formatAliveMetricValue(aliveMetric(row, 'imagination_count'))}`;
  }
  if (row.surface_id === 'finance_data') {
    return `ready ${formatAliveMetricValue(aliveMetric(row, 'ready_runs'))}/${formatAliveMetricValue(aliveMetric(row, 'feed_runs'))}`;
  }
  if (row.surface_id === 'phase_cycles') {
    return `${formatAliveMetricValue(aliveMetric(row, 'phase_ref'))} · cycles ${formatAliveMetricValue(aliveMetric(row, 'cycle_count'))}`;
  }
  if (row.surface_id === 'lab_oracle_evolve') {
    return `oracle ${formatAliveMetricValue(aliveMetric(row, 'oracle_runs'))} · pair ${formatAliveMetricValue(aliveMetric(row, 'pair_ready'))}/${formatAliveMetricValue(aliveMetric(row, 'pair_blocked'))}`;
  }
  if (row.surface_id === 'approvals') {
    return `pending ${formatAliveMetricValue(aliveMetric(row, 'total_pending'))}`;
  }
  const firstMetrics = Object.entries(row.metrics ?? {}).slice(0, 2);
  if (!firstMetrics.length) return row.state;
  return firstMetrics
    .map(([key, value]) => `${compactMetricLabel(key)} ${formatAliveMetricValue(value)}`)
    .join(' · ');
}

function aliveStatusLabel(
  aliveCockpit: StationAliveCockpitSnapshot | null,
  loading: boolean,
  error: string | null,
): string {
  if (aliveCockpit?.status) return aliveCockpit.status;
  if (error) return 'error';
  if (loading) return 'loading';
  return 'empty';
}

function BackendAliveStrip({
  aliveCockpit,
  loading,
  error,
  onOpenRoute,
}: {
  aliveCockpit: StationAliveCockpitSnapshot | null;
  loading: boolean;
  error: string | null;
  onOpenRoute: (route: string) => void;
}) {
  const rows = aliveCockpit?.rows ?? [];
  const status = aliveStatusLabel(aliveCockpit, loading, error);
  const stateCounts = aliveCockpit?.state_counts ?? {};
  const populatedTotal =
    (stateCounts.populated ?? 0) + (stateCounts.correctly_empty ?? 0);
  const statusTone = aliveStateTone(status);
  const stripState = rows.length > 0 ? 'ready' : error ? 'error' : loading ? 'loading' : 'empty';

  return (
    <section
      className="flex min-h-[34px] items-center gap-2 border-t border-white/[0.055] pt-1.5"
      data-zenith-alive-cockpit={stripState}
      data-zenith-alive-cockpit-source="station_launcher"
      data-zenith-alive-cockpit-status={status}
      data-zenith-alive-cockpit-row-count={rows.length}
      data-zenith-alive-cockpit-populated-count={populatedTotal}
    >
      <div className="flex shrink-0 items-center gap-1.5 font-mono text-[9.5px] uppercase tracking-[0.18em] text-white/36">
        <Radio size={11} className="text-emerald-300/70" />
        Backend
        <span
          className={clsx(
            'rounded-[4px] border px-1.5 py-0.5',
            statusTone === 'signal'
              ? 'border-emerald-400/28 text-emerald-300'
              : statusTone === 'amber'
                ? 'border-amber-400/28 text-amber-200'
                : statusTone === 'rose'
                  ? 'border-rose-400/34 text-rose-200'
                  : 'border-white/[0.10] text-zenith-soft',
          )}
        >
          {status}
        </span>
      </div>
      <div className="flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto">
        {rows.length > 0 ? (
          rows.map((row) => {
            const tone = aliveStateTone(row.state);
            const metricSummary = aliveMetricSummary(row);
            const stateDetail = row.state_detail ?? null;
            const primaryAction = stateDetail?.primary_action ?? null;
            const title = [
              stateDetail?.state_label ? `State: ${stateDetail.state_label}` : null,
              stateDetail?.plain_reason ?? row.reason,
              stateDetail?.what_populates ? `Populates: ${stateDetail.what_populates}` : null,
              primaryAction?.label
                ? `Action: ${[
                  primaryAction.label,
                  primaryAction.command,
                ].filter(Boolean).join(' · ')}`
                : null,
              row.source_mode ? `Source: ${row.source_mode}` : null,
              row.api_refs.length ? `API: ${row.api_refs.join(', ')}` : null,
              row.payload_route ? `Payload: ${row.payload_route}` : null,
              row.reentry_condition ? `Re-entry: ${row.reentry_condition}` : null,
            ].filter(Boolean).join('\n');
            return (
              <button
                key={row.surface_id}
                type="button"
                onClick={() => onOpenRoute(row.route)}
                title={title}
                className={clsx(
                  'group inline-flex h-7 min-w-[150px] max-w-[230px] shrink-0 items-center gap-1.5 rounded-[4px] border bg-white/[0.018] px-2 font-mono text-[10px] tracking-normal transition-colors',
                  tone === 'signal'
                    ? 'border-emerald-400/18 text-emerald-100 hover:border-emerald-300/45'
                    : tone === 'amber'
                      ? 'border-amber-400/18 text-amber-100 hover:border-amber-300/42'
                      : tone === 'rose'
                        ? 'border-rose-400/28 text-rose-100 hover:border-rose-300/50'
                        : 'border-white/[0.08] text-white/58 hover:border-white/[0.18]',
                )}
                data-zenith-alive-cockpit-row={row.surface_id}
                data-zenith-alive-cockpit-row-state={row.state}
              >
                <span
                  aria-hidden
                  className={clsx(
                    'h-1.5 w-1.5 shrink-0 rounded-full',
                    tone === 'signal'
                      ? 'bg-emerald-300'
                      : tone === 'amber'
                        ? 'bg-amber-300'
                        : tone === 'rose'
                          ? 'bg-rose-300'
                          : 'bg-white/34',
                  )}
                />
                <span className="min-w-0 flex-1 truncate text-left text-white/76 group-hover:text-white/92">
                  {row.label}
                </span>
                <span className="shrink-0 truncate text-[9.5px] text-white/38 group-hover:text-white/58">
                  {metricSummary}
                </span>
                <ArrowDownRight size={10} className="shrink-0 text-white/28 group-hover:text-white/60" />
              </button>
            );
          })
        ) : (
          <span className="font-mono text-[10px] text-white/34">
            {error ?? 'launcher snapshot pending'}
          </span>
        )}
      </div>
    </section>
  );
}

function ActionBar({
  selectedView,
  aliveCockpit,
  launcherLoading,
  launcherError,
  onOpen,
  onOpenRoute,
  onRefresh,
  onPalette,
  onShowLegacy,
}: {
  selectedView: AtlasView | null;
  aliveCockpit: StationAliveCockpitSnapshot | null;
  launcherLoading: boolean;
  launcherError: string | null;
  onOpen: () => void;
  onOpenRoute: (route: string) => void;
  onRefresh: () => void;
  onPalette: () => void;
  onShowLegacy: () => void;
}) {
  return (
    <footer className="relative flex shrink-0 flex-col gap-1.5 border-t border-[var(--zenith-border)]/40 bg-[linear-gradient(0deg,rgba(255,255,255,0.014),rgba(255,255,255,0)),rgba(7,10,7,0.82)] px-5 py-2 backdrop-blur-xl">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[9.5px] uppercase tracking-[0.2em] text-white/32">
          Bounded actions
        </span>
        <span className="mr-2 h-5 w-px bg-[var(--zenith-border)]/45" aria-hidden />
        <button
          type="button"
          onClick={onOpen}
          disabled={!selectedView}
          className={clsx(
            'inline-flex items-center gap-1.5 rounded-[var(--zenith-radius-2xs)] border px-3 py-1 font-mono text-[10.5px] uppercase tracking-[0.14em] transition-all motion-fast',
            selectedView
              ? 'border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)] text-[var(--zenith-accent)] hover:border-[var(--zenith-accent)] hover:bg-[var(--zenith-accent)] hover:text-[var(--zenith-accent-ink)]'
              : 'cursor-not-allowed border-transparent bg-white/[0.015] text-white/24',
          )}
        >
          <ExternalLink size={11} />
          {selectedView ? `Open ${selectedView.label}` : 'Open selected'}
        </button>
        <button
          type="button"
          onClick={onPalette}
          aria-label="Quick jump command palette"
          title="Open command palette (ctrl/cmd+k)"
          className="inline-flex items-center gap-1.5 rounded-[var(--zenith-radius-2xs)] border border-white/[0.08] bg-white/[0.025] px-3 py-1 font-mono text-[10.5px] uppercase tracking-[0.14em] text-white/62 transition-all hover:border-white/22 hover:text-white/85"
        >
          <Search size={11} />
          Command palette
        </button>
        <button
          type="button"
          onClick={onShowLegacy}
          className="inline-flex items-center gap-1.5 rounded-[var(--zenith-radius-2xs)] border border-white/[0.08] bg-white/[0.025] px-3 py-1 font-mono text-[10.5px] uppercase tracking-[0.14em] text-white/62 transition-all hover:border-white/22 hover:text-white/85"
        >
          <GitBranch size={11} />
          Legacy + workbench
        </button>
        <button
          type="button"
          onClick={onRefresh}
          className="inline-flex items-center gap-1.5 rounded-[var(--zenith-radius-2xs)] border border-white/[0.08] bg-white/[0.025] px-3 py-1 font-mono text-[10.5px] uppercase tracking-[0.14em] text-white/62 transition-all hover:border-white/22 hover:text-white/85"
        >
          <RefreshCw size={11} />
          Refresh
        </button>
        <span className="ml-auto font-mono text-[9.5px] uppercase tracking-[0.16em] text-white/22">
          ViewGraphRenderer · station-surface-atlas
        </span>
      </div>
      <BackendAliveStrip
        aliveCockpit={aliveCockpit}
        loading={launcherLoading}
        error={launcherError}
        onOpenRoute={onOpenRoute}
      />
    </footer>
  );
}

// ---------------------------------------------------------------------------
// Orchestrator
// ---------------------------------------------------------------------------

export default function StationSurfaceAtlas() {
  const navigate = useNavigate();
  // ReactFlow nodeTypes/edgeTypes must be referentially stable — the React
  // Flow runtime logs ~50 warnings per mount when these are recreated on
  // every render. NODE_TYPES (1865) / EDGE_TYPES (2059) are module-scope
  // constants; pass them directly rather than wrapping in useMemo (which
  // still allocates a new closure identity per call site).
  // Wave 24 governance: URL-driven deep-link state for Atlas relation audition.
  // ?node=<view-id>  → pin that surface (drives node dossier)
  // ?edge=<key>      → select that relation (drives edge dossier)
  // ?edge_key=<key>  → same relation selection with backend-owned key naming
  // ?relation=<key>  → select a backend relation_summary row
  // ?group_flow=<key> → select a backend group_flows row
  // ?density=<mode>  → set CLEAN / STRUCTURAL / CAPTURE
  // Per UI-Atlas-Relation-Audition-Phase2B-008. The query layer is the
  // station_render-capturable shadow of the click/hover state.
  const [searchParams, setSearchParams] = useSearchParams();
  const navigationGraph = useZenith((state) => state.worldModel?.navigation_graph ?? null);
  const worldModelError = useZenith((state) => state.worldModelError);
  const refreshWorldModel = useZenith((state) => state.refreshWorldModel);
  const init = useZenith((state) => state.init);
  const launcher = useStation((state) => state.launcher);
  const launcherLoading = useStation((state) => state.launcherLoading);
  const launcherError = useStation((state) => state.launcherError);
  const refreshLauncher = useStation((state) => state.refreshLauncher);
  const aliveCockpit = launcher?.alive_cockpit ?? null;
  const captureMode = isCaptureModeEnabled();

  useEffect(() => {
    if (captureMode) {
      void refreshWorldModel({ force: true });
      void refreshLauncher({ force: true });
      return;
    }
    void init();
    void refreshWorldModel();
    void refreshLauncher();
  }, [captureMode, init, refreshWorldModel, refreshLauncher]);

  // Progressive typed-edge hydration. The first_paint world-model snapshot omits
  // the per-edge `edges` array, so navigationGraph carries only untyped adjacency
  // and the Atlas would render every focus edge as fallback 'adjacency'. After
  // first paint we fetch the typed edge slice once and splice it into the graph
  // below, activating the existing typed branch of edgesFromNavigationGraph so
  // focus edges render real relation classes (GROUP / LENS / SHELL / ROUTE /
  // OPEN). Best-effort: on failure the canvas keeps its honest first_paint
  // adjacency rather than inventing typing.
  const [hydratedEdges, setHydratedEdges] = useState<WorldModelNavigationGraphEdge[] | null>(null);
  useEffect(() => {
    let cancelled = false;
    void api.worldModel
      .navigationEdges()
      .then((res: WorldModelNavigationEdgesResponse) => {
        if (cancelled) return;
        if (res?.available && Array.isArray(res.edges) && res.edges.length > 0) {
          setHydratedEdges(res.edges);
        }
      })
      .catch(() => {
        // Typed hydration is an enhancement; keep first_paint adjacency on error.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const onRefresh = useCallback(() => {
    void refreshWorldModel({ force: true });
    void refreshLauncher({ force: true });
  }, [refreshWorldModel, refreshLauncher]);

  const onPalette = useCallback(() => {
    // Dispatch a command-palette open event; the CommandPalette listens for
    // the same key handler regardless of host shell.
    const evt = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, metaKey: true, bubbles: true });
    window.dispatchEvent(evt);
  }, []);

  const onShowLegacy = useCallback(() => {
    navigate('/station/legacy');
  }, [navigate]);

  // Pull views from navigation_graph only when it carries valid view rows;
  // otherwise use the static registry so partial/empty snapshots do not
  // trip the ready selector with a blank graph.
  const atlasData = useMemo((): {
    views: AtlasView[];
    source: 'navigation_graph' | 'fallback';
  } => {
    if (navigationGraph) {
      const graphViews = viewsFromNavigationGraph(navigationGraph as unknown as Record<string, unknown>);
      if (graphViews.length > 0) {
        return { views: graphViews, source: 'navigation_graph' };
      }
    }
    return { views: viewsFromSurfaces(), source: 'fallback' };
  }, [navigationGraph]);
  const views = atlasData.views;
  const atlasSource = atlasData.source;

  const edges: AtlasEdge[] = useMemo(() => {
    // Prefer real edges from the navigation graph. The first_paint snapshot
    // surfaces views + adjacency but omits the typed `edges` array, so we splice
    // in the lazily-hydrated typed edges (when present) — activating the typed
    // branch of edgesFromNavigationGraph so focus edges carry real relation
    // classes (GROUP / LENS / SHELL / ROUTE / OPEN) instead of fallback
    // adjacency. When neither typed edges nor a usable graph exist we synthesise
    // group-derived edges so the atlas still reads as a graph, not loose cards.
    const graphForEdges =
      atlasSource === 'navigation_graph' && navigationGraph
        ? hydratedEdges
          ? { ...(navigationGraph as unknown as Record<string, unknown>), edges: hydratedEdges }
          : (navigationGraph as unknown as Record<string, unknown>)
        : null;
    const fromGraph = graphForEdges ? edgesFromNavigationGraph(graphForEdges) : [];
    if (fromGraph.length > 0) return fromGraph;
    return edgesFromSurfaces(views);
  }, [atlasSource, navigationGraph, hydratedEdges, views]);

  const [activeGroup, setActiveGroup] = useState<ShellSurfaceGroupId | 'unassigned' | 'all'>('all');
  const [search, setSearch] = useState<string>('');
  // AtlasFocus state — split into pinned + hovered so the right-click pin
  // can persist while the mouse continues to roam over neighbours.
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [pinnedId, setPinnedId] = useState<string | null>(null);
  const [densityMode, setDensityMode] = useState<EdgeDensityMode>('clean');
  // Atlas v4 — relation brush layer. Set when a connected-views row in the
  // detail panel is hovered/focused. Independent of focus so the anchor
  // (pinned/hovered) stays dominant while the brushed neighbour is lifted
  // and unrelated nodes dim harder. Per cap_station_surface_atlas_relation_brushing_v1.
  const [relationBrush, setRelationBrush] = useState<RelationBrush>({ mode: 'none' });
  // Wave 22 Phase 2 — Atlas Relation Audition Pass
  // (cap_quick_wave_22_phase_2_atlas_hover_preview_edge_6b81029f0713).
  // Edge focus turns a clicked atlas edge into a first-class dossier
  // target alongside hover/pin node focus. Stores the index into the
  // canonical `edges` array because rfEdge ids are `e:${idx}:...` and
  // the AtlasEdge payload (relation / category / weight / evidenceRefs)
  // sits in `edges`, not in the React Flow projection.
  const [selectedEdgeIdx, setSelectedEdgeIdx] = useState<number | null>(null);
  const [selectedRelationKey, setSelectedRelationKey] = useState<string | null>(null);
  const [selectedRelationSource, setSelectedRelationSource] = useState<RelationSelectionSource>('none');
  const [selectedGroupFlowKey, setSelectedGroupFlowKey] = useState<string | null>(null);
  const [selectedGroupFlowSource, setSelectedGroupFlowSource] = useState<GroupFlowSelectionSource>('none');
  const [selectedEdgeSource, setSelectedEdgeSource] = useState<EdgeSelectionSource>('none');
  const [railHoveredId, setRailHoveredId] = useState<string | null>(null);
  const [isRailTransitionPending, startRailTransition] = useTransition();
  // Right rail can be collapsed so the operator can see the canvas in full
  // when the resting dossier (relation legend, group flows, interactions) is
  // not wanted. Persists for the session; a reopen handle stays mounted.
  const [railCollapsed, setRailCollapsed] = useState<boolean>(false);
  const [atlasSceneViewport, setAtlasSceneViewport] = useState<AtlasSceneViewport>(initialAtlasSceneViewport);
  const [leftRailDrawerOpen, setLeftRailDrawerOpen] = useState<boolean>(false);
  const [rightRailDrawerOpen, setRightRailDrawerOpen] = useState<boolean>(false);
  const sceneRailPolicy: AtlasSceneCandidateId = shouldUseGraphFirstDrawers(atlasSceneViewport, railCollapsed)
    ? 'graph_first_drawers'
    : railCollapsed
      ? 'right_rail_collapsed'
      : 'current_persistent_dual_rails';
  const graphFirstDrawersActive = sceneRailPolicy === 'graph_first_drawers';
  const projectedPersistentRailWidth = railCollapsed ? 244 : 520;
  const projectedGraphWidth = Math.max(1, atlasSceneViewport.width - projectedPersistentRailWidth);
  const projectedRailToStage = projectedPersistentRailWidth / projectedGraphWidth;
  const atlasSceneCandidateReceipt = useMemo(() => ({
    schema: 'scene_candidate_receipt_v0',
    view_id: 'surface_atlas',
    mode: 'map_first',
    viewport: atlasSceneViewport,
    source_quality_receipt: 'view_quality_receipt_v0',
    selected_candidate: sceneRailPolicy,
    selection_reason: graphFirstDrawersActive
      ? 'graph_first_drawers preserves map-first graph survival when persistent rails dominate the stage.'
      : 'current rail policy stays under graph-first escalation thresholds.',
    candidates: [
      {
        id: 'current_persistent_dual_rails',
        status: projectedRailToStage > ATLAS_GRAPH_FIRST_RAIL_TO_STAGE_MAX ? 'fail' : 'pass',
        failed_gates: projectedRailToStage > ATLAS_GRAPH_FIRST_RAIL_TO_STAGE_MAX
          ? ['rail_dominance_not_excessive']
          : [],
        predicted_metrics: {
          railArea_to_reactFlow: Number(projectedRailToStage.toFixed(3)),
          graphWidth_to_viewport: Number((projectedGraphWidth / Math.max(1, atlasSceneViewport.width)).toFixed(3)),
        },
      },
      {
        id: 'graph_first_drawers',
        status: 'pass',
        tradeoffs: ['rail_detail_requires_open_action'],
        predicted_metrics: {
          railArea_to_reactFlow: 0,
          graphWidth_to_viewport: Number(
            ((atlasSceneViewport.width - (ATLAS_GRAPH_FIRST_DRAWER_RAIL_WIDTH * 2))
              / Math.max(1, atlasSceneViewport.width)).toFixed(3),
          ),
        },
      },
    ],
  }), [
    atlasSceneViewport,
    graphFirstDrawersActive,
    projectedGraphWidth,
    projectedRailToStage,
    sceneRailPolicy,
  ]);
  // Refs let the global Escape handler clear pin without re-binding on
  // every state change.
  const pinnedIdRef = useRef<string | null>(null);
  const hoveredIdRef = useRef<string | null>(null);
  const railHoveredIdRef = useRef<string | null>(null);
  const selectedEdgeIdxRef = useRef<number | null>(null);
  const selectedRelationKeyRef = useRef<string | null>(null);
  const selectedRelationSourceRef = useRef<RelationSelectionSource>('none');
  const selectedGroupFlowKeyRef = useRef<string | null>(null);
  const selectedGroupFlowSourceRef = useRef<GroupFlowSelectionSource>('none');
  const selectedEdgeSourceRef = useRef<EdgeSelectionSource>('none');
  const railCollapsedRef = useRef<boolean>(false);
  const leftRailDrawerOpenRef = useRef<boolean>(false);
  const rightRailDrawerOpenRef = useRef<boolean>(false);
  const atlasRootRef = useRef<HTMLDivElement | null>(null);
  const viewportGestureActiveRef = useRef<boolean>(false);
  const viewportMovingRef = useRef<boolean>(false);
  const viewportMovedDuringGestureRef = useRef<boolean>(false);
  const viewportMoveEndTimerRef = useRef<number | null>(null);
  const hoverIntentTimerRef = useRef<number | null>(null);
  const suppressPointerUntilRef = useRef<number>(0);
  useEffect(() => {
    pinnedIdRef.current = pinnedId;
  }, [pinnedId]);
  useEffect(() => {
    hoveredIdRef.current = hoveredId;
  }, [hoveredId]);
  useEffect(() => {
    railHoveredIdRef.current = railHoveredId;
  }, [railHoveredId]);
  useEffect(() => {
    selectedEdgeIdxRef.current = selectedEdgeIdx;
  }, [selectedEdgeIdx]);
  useEffect(() => {
    selectedRelationKeyRef.current = selectedRelationKey;
  }, [selectedRelationKey]);
  useEffect(() => {
    selectedRelationSourceRef.current = selectedRelationSource;
  }, [selectedRelationSource]);
  useEffect(() => {
    selectedGroupFlowKeyRef.current = selectedGroupFlowKey;
  }, [selectedGroupFlowKey]);
  useEffect(() => {
    selectedGroupFlowSourceRef.current = selectedGroupFlowSource;
  }, [selectedGroupFlowSource]);
  useEffect(() => {
    selectedEdgeSourceRef.current = selectedEdgeSource;
  }, [selectedEdgeSource]);
  useEffect(() => {
    railCollapsedRef.current = railCollapsed;
  }, [railCollapsed]);
  useEffect(() => {
    leftRailDrawerOpenRef.current = leftRailDrawerOpen;
  }, [leftRailDrawerOpen]);
  useEffect(() => {
    rightRailDrawerOpenRef.current = rightRailDrawerOpen;
  }, [rightRailDrawerOpen]);
  useEffect(() => {
    const onResize = () => setAtlasSceneViewport(initialAtlasSceneViewport());
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  useEffect(() => {
    if (!graphFirstDrawersActive) {
      setLeftRailDrawerOpen(false);
      setRightRailDrawerOpen(false);
    }
  }, [graphFirstDrawersActive]);

  const setViewportMoving = useCallback((moving: boolean) => {
    if (viewportMovingRef.current === moving) return;
    viewportMovingRef.current = moving;
    const root = atlasRootRef.current;
    root?.classList.toggle('atlas-moving', moving);
    root?.setAttribute('data-zenith-surface-atlas-moving', moving ? 'true' : 'false');
    updateAtlasPerfGraph({ moving });
  }, []);

  const shouldSuppressPointerAfterMove = useCallback(() => (
    viewportMovedDuringGestureRef.current
    && (viewportMovingRef.current || interactionNowMs() < suppressPointerUntilRef.current)
  ), []);

  const clearHoverIntent = useCallback(() => {
    if (hoverIntentTimerRef.current !== null) {
      window.clearTimeout(hoverIntentTimerRef.current);
      hoverIntentTimerRef.current = null;
    }
  }, []);

  useEffect(() => () => {
    if (viewportMoveEndTimerRef.current !== null) {
      window.clearTimeout(viewportMoveEndTimerRef.current);
    }
    if (hoverIntentTimerRef.current !== null) {
      window.clearTimeout(hoverIntentTimerRef.current);
    }
  }, []);

  const focus: AtlasFocus = pinnedId
    ? { mode: 'pinned', nodeId: pinnedId }
    : hoveredId
      ? { mode: 'hover', nodeId: hoveredId }
      : { mode: 'rest' };
  const focusId = focus.mode === 'rest' ? null : focus.nodeId;
  const railFocus: AtlasFocus = pinnedId
    ? { mode: 'pinned', nodeId: pinnedId }
    : railHoveredId
      ? { mode: 'hover', nodeId: railHoveredId }
      : { mode: 'rest' };
  const railFocusId = railFocus.mode === 'rest' ? null : railFocus.nodeId;

  // Escape escalates through dismissals so a single key always frees the
  // canvas: edge focus → pinned node → selected relation/group-flow row →
  // collapse the right rail. Mounted once; refs read current state without
  // re-binding on every change. Ignored when the operator is typing.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      const target = event.target;
      if (target instanceof HTMLElement) {
        const tag = target.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable) return;
      }
      let handled = false;
      if (rightRailDrawerOpenRef.current) {
        setRightRailDrawerOpen(false);
        handled = true;
      }
      if (leftRailDrawerOpenRef.current) {
        setLeftRailDrawerOpen(false);
        handled = true;
      }
      if (handled) {
        event.preventDefault();
        event.stopPropagation();
        return;
      }
      if (selectedEdgeIdxRef.current !== null) {
        setSelectedEdgeIdx(null);
        setSelectedEdgeSource('none');
        handled = true;
      }
      if (pinnedIdRef.current) {
        setPinnedId(null);
        handled = true;
      }
      if (selectedRelationKeyRef.current) {
        setSelectedRelationKey(null);
        setSelectedRelationSource('none');
        handled = true;
      }
      if (selectedGroupFlowKeyRef.current) {
        setSelectedGroupFlowKey(null);
        setSelectedGroupFlowSource('none');
        handled = true;
      }
      if (hoveredIdRef.current || railHoveredIdRef.current) {
        setHoveredId(null);
        setRailHoveredId(null);
        handled = true;
      }
      if (!railCollapsedRef.current) {
        setRailCollapsed(true);
        handled = true;
      }
      if (handled) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const deferredSearch = useDeferredValue(search);
  const lowerSearch = deferredSearch.trim().toLowerCase();
  const matchSet = useMemo(() => {
    if (!lowerSearch && activeGroup === 'all') return new Set(views.map((v) => v.id));
    const out = new Set<string>();
    for (const v of views) {
      if (activeGroup !== 'all' && v.shellGroup !== activeGroup) continue;
      if (lowerSearch) {
        const haystack = `${v.label} ${v.route} ${v.purpose}`.toLowerCase();
        if (!haystack.includes(lowerSearch)) continue;
      }
      out.add(v.id);
    }
    return out;
  }, [views, lowerSearch, activeGroup]);

  const viewsById = useMemo(() => new Map(views.map((v) => [v.id, v] as const)), [views]);

  // Adjacency derived from the focus node — collects upstream/downstream
  // neighbours and the set of edge ids that touch focus (active edges).
  const focusContext = useMemo(() => {
    if (!focusId) {
      return {
        adjacentSet: new Set<string>(),
        activeEdgeIdxSet: new Set<number>(),
      };
    }
    const adjacentSet = new Set<string>();
    const activeEdgeIdxSet = new Set<number>();
    edges.forEach((edge, idx) => {
      if (edge.target === focusId) {
        adjacentSet.add(edge.source);
        activeEdgeIdxSet.add(idx);
      } else if (edge.source === focusId) {
        adjacentSet.add(edge.target);
        activeEdgeIdxSet.add(idx);
      }
    });
    return { adjacentSet, activeEdgeIdxSet };
  }, [focusId, edges]);

  const connectedGroups = useMemo(
    () => groupConnectedByRelation(railFocusId, edges, viewsById),
    [railFocusId, edges, viewsById],
  );

  // Auto-clear brush when the anchor changes (pin moved, focus cleared, etc).
  // Without this the brush would point at a stale anchor↔neighbour pair.
  useEffect(() => {
    if (relationBrush.mode === 'connected_row' && relationBrush.anchorId !== railFocusId) {
      setRelationBrush({ mode: 'none' });
    }
  }, [railFocusId, relationBrush]);

  const onBrushNeighbour = useCallback(
    (anchorId: string, relation: string, neighbour: ConnectedNeighbour) => {
      setRelationBrush((current) => {
        if (
          current.mode === 'connected_row'
          && current.anchorId === anchorId
          && current.neighborId === neighbour.view.id
          && current.relation === relation
          && current.edgeIdxs.length === 1
          && current.edgeIdxs[0] === neighbour.edgeIdx
        ) {
          return current;
        }
        return {
          mode: 'connected_row',
          anchorId,
          neighborId: neighbour.view.id,
          relation,
          edgeIdxs: [neighbour.edgeIdx],
        };
      });
    },
    [],
  );
  const onClearBrush = useCallback(() => {
    setRelationBrush((current) => (current.mode === 'none' ? current : { mode: 'none' }));
  }, []);

  // Brush context — quick lookup helpers used by rfNodes/rfEdges so the
  // hot render loop doesn't re-derive sets on every node/edge.
  const brushContext = useMemo(() => {
    if (relationBrush.mode !== 'connected_row') {
      return {
        active: false as const,
        anchorId: null as string | null,
        neighborId: null as string | null,
        edgeIdxSet: new Set<number>(),
        relation: null as string | null,
        tone: null as RelationStyle['tone'] | null,
      };
    }
    return {
      active: true as const,
      anchorId: relationBrush.anchorId,
      neighborId: relationBrush.neighborId,
      edgeIdxSet: new Set(relationBrush.edgeIdxs),
      relation: relationBrush.relation,
      tone: styleForMechanism(relationBrush.relation).tone,
    };
  }, [relationBrush]);

  // ReactFlow nodes / edges built from atlas state.
  const { positions, columns } = useMemo(() => layoutNodes(views), [views]);

  // Shell-group registry, used to look up operator-job descriptions for
  // each column-header node.
  const shellGroupDescription = useMemo(() => {
    const map = new Map<string, string>();
    for (const group of getShellSurfaceGroups()) {
      if (group.description) map.set(group.id, group.description);
    }
    return map;
  }, []);

  const groupCapturePosture = useMemo(() => {
    const failed = new Map<string, number>();
    const noCapture = new Map<string, number>();
    const legacy = new Map<string, number>();
    for (const view of views) {
      if (view.isLegacy) legacy.set(view.shellGroup, (legacy.get(view.shellGroup) ?? 0) + 1);
      const status = (view.captureLatestStatus ?? '').toLowerCase();
      if (status === 'failed' || status === 'failure' || status === 'error') {
        failed.set(view.shellGroup, (failed.get(view.shellGroup) ?? 0) + 1);
      } else if (
        status === ''
        || status === 'no_capture'
        || status === 'no-capture'
        || status === 'missing'
        || status === 'unknown'
      ) {
        noCapture.set(view.shellGroup, (noCapture.get(view.shellGroup) ?? 0) + 1);
      }
    }
    return { failed, noCapture, legacy };
  }, [views]);

  const atlasNodeDataCacheRef = useRef(new Map<string, CachedNodeData<AtlasNodeData>>());
  const columnHeaderDataCacheRef = useRef(new Map<string, CachedNodeData<ColumnHeaderData>>());
  const groupBackplateDataCacheRef = useRef(new Map<string, CachedNodeData<GroupBackplateData>>());

  // ---------------------------------------------------------------------
  // rfEdges — relation-aware + density-aware edge styling.
  // ---------------------------------------------------------------------
  // Clean mode (default): edges at rest are a faint skeleton (restStroke).
  //   On focus the touching ego-network edges flip to activeStroke; only
  //   the top 1-2 high-authority labels show via the EdgeLabelRenderer HTML
  //   overlay (see AtlasRelationEdge). Non-active edges drop to barely-
  //   there.
  // Structural mode: rest edges carry their full relation tone so the
  //   operator can scan the whole topology. Active edges still highlight,
  //   but labels are NEVER painted at rest — repeated structural labels
  //   like SAME STATION GROUP belong in the right-panel "Structural
  //   reachability" fold, not sprayed across the canvas.
  // Capture mode: edges fade hard so node capture posture dominates.
  //
  // Atlas v5 label gating (per cap_quick_atlas_v5_semantic_layout_planner_
  // edge_la_f610b4d55425 + operator refinement 2026-05-13):
  //   Rest                  → no labels.
  //   Hover/pin (focus)     → at most 2 high-authority labels per pass,
  //                           selected by relation priority (priority<=5).
  //                           Structural mechanisms (shell_group, station_
  //                           group, station_lens_menu) never land on the
  //                           canvas; they stay in the right-panel fold.
  //   Brush (panel→graph)   → exactly the brushed edge label, regardless
  //                           of relation kind. Competing incident-edge
  //                           labels are suppressed.
  //
  // Edges are drawn in priority order (lower priority = higher rank =
  // painted later = on top), so declared edges sit above shell-group
  // chaff.
  // Atlas v6 visible-edge budget. Single gate that decides BOTH whether an
  // edge is drawn on the canvas and which nodes are highlighted as adjacent
  // to the focused card. The v5 split (label budget separate from edge
  // budget) painted unlabelled spaghetti — every focus-touching pathway
  // edge drew a line, but only 2 lines carried a readable relation. The
  // operator's screenshot of 254 SHARES COMPONENT lines without labels was
  // the exact symptom; v6 collapses the two budgets.
  //
  // Rules:
  //   Rest                    → drawnEdgeIdxSet empty. No canvas lines.
  //   Focus (hover/pin)       → walk every focus-touching edge whose
  //                             mechanism is in DRAWN_CANVAS_MECHANISMS,
  //                             rank by relation priority, keep the top
  //                             ATLAS_VISIBLE_EDGE_CAP_PER_FOCUS. Every
  //                             other focus-touching relation increments
  //                             foldedFocusEdgeCount and shows up in the
  //                             panel rather than as a line.
  //   Brush (panel → graph)   → exactly the brushed edge(s); everything
  //                             else is suppressed.
  //   Coordination (URL row)  → handled in rfEdges (selected/relation/
  //                             group-flow edge sets get drawn even when
  //                             no focus is anchored, preserving the
  //                             audit lanes).
  //
  // visibleEndpointIdSet is the union of source/target ids of every drawn
  // edge — node renderer brightens only these as "adjacent" so the dimming
  // is honest (no more bright-but-disconnected cards from folded-only
  // relations).
  const visibleEdgeBudget = useMemo((): {
    drawnEdgeIdxSet: Set<number>;
    labelEdgeIdxSet: Set<number>;
    visibleEndpointIdSet: Set<string>;
    foldedFocusEdgeCount: number;
  } => {
    const drawnEdgeIdxSet = new Set<number>();
    const visibleEndpointIdSet = new Set<string>();
    const recordEndpoint = (idx: number) => {
      const edge = edges[idx];
      if (!edge) return;
      if (!viewsById.has(edge.source) || !viewsById.has(edge.target)) return;
      visibleEndpointIdSet.add(edge.source);
      visibleEndpointIdSet.add(edge.target);
    };
    if (brushContext.active) {
      for (const brushedIdx of brushContext.edgeIdxSet) {
        drawnEdgeIdxSet.add(brushedIdx);
        recordEndpoint(brushedIdx);
      }
      return { drawnEdgeIdxSet, labelEdgeIdxSet: new Set(drawnEdgeIdxSet), visibleEndpointIdSet, foldedFocusEdgeCount: 0 };
    }
    if (focusContext.activeEdgeIdxSet.size > 0) {
      const candidates: Array<{ idx: number; mechanism: string; tier: number; priority: number; weight: number }> = [];
      let foldedFocusEdgeCount = 0;
      for (const focusIdx of focusContext.activeEdgeIdxSet) {
        const focusEdge = edges[focusIdx];
        if (!focusEdge) continue;
        if (!viewsById.has(focusEdge.source) || !viewsById.has(focusEdge.target)) {
          foldedFocusEdgeCount += 1;
          continue;
        }
        const mechanism = focusEdge.relation;
        // A hovered / pinned node's neighbourhood is bounded, so draw it in
        // full: pathway ties (declared / overlay / route / shared API) win the
        // budget first (tier 0), then membership ties (shell / station group,
        // shared component, lens) fill the remaining slots (tier 1). This is
        // "show what this node connects to" — NOT the at-rest spaghetti the v6
        // fold prevents (at rest nothing is budgeted). Without the membership
        // fill, hovering / right-clicking a node whose ties are all membership
        // drew zero edges — the regression the operator flagged.
        candidates.push({
          idx: focusIdx,
          mechanism,
          tier: DRAWN_CANVAS_MECHANISMS.has(mechanism) ? 0 : 1,
          priority: styleForMechanism(mechanism).priority,
          weight: typeof focusEdge.weight === 'number' ? focusEdge.weight : 0,
        });
      }
      candidates.sort((a, b) => a.tier - b.tier || a.priority - b.priority || b.weight - a.weight);
      const picked = candidates.slice(0, ATLAS_VISIBLE_EDGE_CAP_PER_FOCUS);
      const labelEdgeIdxSet = new Set<number>();
      for (const { idx: pickIdx } of picked) {
        drawnEdgeIdxSet.add(pickIdx);
        recordEndpoint(pickIdx);
      }
      // Focus auto-text-labelling is DEFERRED in the typed-edge hydration wave.
      // Now that real typed edges are hydrated, a per-mechanism chip lands on the
      // rendered line — but the chip anchor sits toward the NON-focus end
      // (defaultLabelT), so an edge to a DISTANT neighbour drops its "GROUP" /
      // "OPEN" chip onto an intervening card (measured label×node=1-2). Collision-
      // safe chip placement is a separate label-layout concern (see cap: collision-
      // safe typed relation chips). Until it lands, the relation CLASS is carried
      // by the per-mechanism TONE the hydration now unlocks (gold OPEN / sky GROUP
      // / sage SHELL / cyan LENS / violet overlay) plus the right-rail
      // RelationLegend, and a full text chip is still shown on rail-row brush / URL
      // coordination — which target ONE edge on demand, so they neither flood nor
      // collide. Flip this flag once collision-safe placement lands to re-light the
      // per-distinct-mechanism focus chips.
      const AUTO_LABEL_FOCUS_EDGES = false;
      const labelledMechanisms = new Set<string>();
      for (const cand of picked) {
        if (!AUTO_LABEL_FOCUS_EDGES) break;
        if (labelEdgeIdxSet.size >= ATLAS_FOCUS_LABEL_CAP) break;
        if (UNLABELLED_FALLBACK_MECHANISMS.has(cand.mechanism)) continue;
        if (labelledMechanisms.has(cand.mechanism)) continue;
        labelEdgeIdxSet.add(cand.idx);
        labelledMechanisms.add(cand.mechanism);
      }
      // Pathway edges past the cap are folded too — operator sees them in
      // the side panel as "+N more pathways" rather than as unlabelled
      // spaghetti.
      foldedFocusEdgeCount += Math.max(0, candidates.length - picked.length);
      return { drawnEdgeIdxSet, labelEdgeIdxSet, visibleEndpointIdSet, foldedFocusEdgeCount };
    }
    return { drawnEdgeIdxSet, labelEdgeIdxSet: new Set<number>(), visibleEndpointIdSet, foldedFocusEdgeCount: 0 };
  }, [edges, focusContext.activeEdgeIdxSet, brushContext, viewsById]);
  // Backcompat alias so the layout receipt + downstream readers that
  // referenced the v5 `labelBudget` set continue to compile. In v6 the
  // label budget IS the edge budget.
  const labelBudget = visibleEdgeBudget.drawnEdgeIdxSet;

  // Wave SFA-2 — group flows are backend-owned rail data from
  // worldModel.navigation_graph.group_flows. The frontend may render fewer rows,
  // but it no longer recomputes the aggregate from edges[].
  const groupFlows = useMemo((): WorldModelNavigationGraphGroupFlow[] => {
    if (atlasSource !== 'navigation_graph' || !navigationGraph) return [];
    const flows = navigationGraph.group_flows;
    if (!Array.isArray(flows)) return [];
    return flows.filter(isNavigationGroupFlow);
  }, [atlasSource, navigationGraph]);

  const relationSummary = useMemo((): WorldModelNavigationGraphRelationSummary[] => {
    if (atlasSource !== 'navigation_graph' || !navigationGraph) return [];
    const rows = navigationGraph.relation_summary;
    if (!Array.isArray(rows)) return [];
    return rows.filter(isNavigationRelationSummary);
  }, [atlasSource, navigationGraph]);

  const selectedRelation = useMemo(() => {
    if (relationSummary.length === 0) return null;
    if (selectedRelationKey) {
      const selected = relationSummary.find((row) => relationKey(row) === selectedRelationKey);
      if (selected) return selected;
    }
    return relationSummary[0];
  }, [relationSummary, selectedRelationKey]);
  const selectedRelationResolvedKey = selectedRelation ? relationKey(selectedRelation) : null;
  const selectedRelationRole: WorldModelNavigationGraphPresentationRole | 'none' =
    selectedRelation?.presentation_role ?? 'none';
  const effectiveRelationSelection: RelationSelectionSource =
    selectedRelationResolvedKey
      ? (selectedRelationKey === selectedRelationResolvedKey ? selectedRelationSource : 'default')
      : 'none';
  const fallbackRelationAvailable = relationSummary.some((row) => row.presentation_role === 'fallback');

  const selectedGroupFlow = useMemo(() => {
    if (groupFlows.length === 0) return null;
    if (selectedGroupFlowKey) {
      const selected = groupFlows.find((flow) => groupFlowKey(flow) === selectedGroupFlowKey);
      if (selected) return selected;
    }
    return groupFlows[0];
  }, [groupFlows, selectedGroupFlowKey]);
  const selectedGroupFlowResolvedKey = selectedGroupFlow ? groupFlowKey(selectedGroupFlow) : null;
  const effectiveGroupFlowSelection: GroupFlowSelectionSource =
    selectedGroupFlowResolvedKey
      ? (selectedGroupFlowKey === selectedGroupFlowResolvedKey ? selectedGroupFlowSource : 'default')
      : 'none';

  const coordinationContext = useMemo(() => {
    const selectedEdgeIdxSet = new Set<number>();
    const relationEdgeIdxSet = new Set<number>();
    const groupFlowEdgeIdxSet = new Set<number>();
    const coordinationEdgeIdxSet = new Set<number>();
    const selectedEndpointIdSet = new Set<string>();
    const relationEndpointIdSet = new Set<string>();
    const groupFlowEndpointIdSet = new Set<string>();
    const columnRoles = new Map<ShellSurfaceGroupId | 'unassigned', ColumnCoordinationRole>();
    const relationSelectionActive =
      effectiveRelationSelection === 'url' || effectiveRelationSelection === 'row';
    const groupFlowSelectionActive =
      effectiveGroupFlowSelection === 'url' || effectiveGroupFlowSelection === 'row';
    const selectedEdge = selectedEdgeIdx !== null ? edges[selectedEdgeIdx] ?? null : null;
    const selectedEdgeTone = selectedEdge ? styleForMechanism(selectedEdge.relation).tone : null;
    const selectedRelationMechanism =
      relationSelectionActive && selectedRelation ? selectedRelation.relation : null;
    const selectedRelationTone = selectedRelationMechanism
      ? styleForMechanism(selectedRelationMechanism).tone
      : null;
    const selectedGroupFlowTone =
      groupFlowSelectionActive && selectedGroupFlow
        ? styleForMechanism(selectedGroupFlow.dominant_relation).tone
        : null;
    const selectedRelationRole = selectedRelation?.presentation_role ?? null;
    const membershipSelectionActive =
      relationSelectionActive && selectedRelationRole === 'membership';
    const fallbackSelectionActive =
      relationSelectionActive && selectedRelationRole === 'fallback';
    let selectedMembershipRelationEdgeCount = 0;

    if (selectedEdge && !isMembershipEdge(selectedEdge) && selectedEdgeIdx !== null) {
      selectedEdgeIdxSet.add(selectedEdgeIdx);
      selectedEndpointIdSet.add(selectedEdge.source);
      selectedEndpointIdSet.add(selectedEdge.target);
    }

    if (groupFlowSelectionActive && selectedGroupFlow) {
      const sourceGroup = selectedGroupFlow.source_group as ShellSurfaceGroupId | 'unassigned';
      const targetGroup = selectedGroupFlow.target_group as ShellSurfaceGroupId | 'unassigned';
      columnRoles.set(sourceGroup, 'group_flow_source');
      columnRoles.set(targetGroup, 'group_flow_target');
    }

    edges.forEach((edge, idx) => {
      const sourceView = viewsById.get(edge.source);
      const targetView = viewsById.get(edge.target);
      const relationMatched = selectedRelationMechanism !== null && edge.relation === selectedRelationMechanism;
      if (relationMatched) {
        if (isMembershipEdge(edge)) {
          selectedMembershipRelationEdgeCount += 1;
        } else {
          relationEdgeIdxSet.add(idx);
          relationEndpointIdSet.add(edge.source);
          relationEndpointIdSet.add(edge.target);
        }
      }
      if (
        groupFlowSelectionActive
        && selectedGroupFlow
        && sourceView?.shellGroup === selectedGroupFlow.source_group
        && targetView?.shellGroup === selectedGroupFlow.target_group
      ) {
        if (!isMembershipEdge(edge)) {
          groupFlowEdgeIdxSet.add(idx);
        }
        groupFlowEndpointIdSet.add(edge.source);
        groupFlowEndpointIdSet.add(edge.target);
      }
    });

    for (const idx of selectedEdgeIdxSet) coordinationEdgeIdxSet.add(idx);
    for (const idx of relationEdgeIdxSet) coordinationEdgeIdxSet.add(idx);
    for (const idx of groupFlowEdgeIdxSet) coordinationEdgeIdxSet.add(idx);

    const selectedEdgeActive = selectedEdgeIdx !== null;
    const activeKinds = [
      selectedEdgeActive,
      relationSelectionActive,
      groupFlowSelectionActive,
    ].filter(Boolean).length;
    const mode: CoordinationMode =
      activeKinds === 0
        ? 'none'
        : activeKinds > 1
          ? 'mixed'
          : selectedEdgeActive
            ? 'edge'
            : relationSelectionActive
              ? 'relation'
              : 'group_flow';
    const active = mode !== 'none';
    const unrelatedPathwayEdgeCount = active
      ? edges.reduce((count, edge, idx) => {
          if (isMembershipEdge(edge)) return count;
          return coordinationEdgeIdxSet.has(idx) ? count : count + 1;
        }, 0)
      : 0;
    const membershipCanvasEdgeCount = 0;
    const membershipSelectionFolded =
      membershipSelectionActive
      && selectedMembershipRelationEdgeCount > 0
      && relationEdgeIdxSet.size === 0
      && membershipCanvasEdgeCount === 0;
    const membershipSelectionContextReady =
      membershipSelectionActive
      && selectedRelation !== null
      && selectedMembershipRelationEdgeCount > 0;

    return {
      active,
      mode,
      selectedRelationRole: selectedRelationRole ?? 'none',
      selectedEdgeIdxSet,
      relationEdgeIdxSet,
      groupFlowEdgeIdxSet,
      coordinationEdgeIdxSet,
      selectedEndpointIdSet,
      relationEndpointIdSet,
      groupFlowEndpointIdSet,
      columnRoles,
      selectedEdgeTone,
      selectedRelationTone,
      selectedGroupFlowTone,
      selectedEdgeVisible: selectedEdgeIdx !== null && selectedEdgeIdxSet.has(selectedEdgeIdx),
      selectedEdgeEndpointsReady: selectedEndpointIdSet.size >= 2,
      unrelatedEdgeDemotionReady: active && unrelatedPathwayEdgeCount > 0,
      membershipSelectionActive,
      membershipSelection:
        membershipSelectionActive
          ? ('active' as const)
          : selectedRelationRole === 'membership'
            ? ('unavailable' as const)
            : ('inactive' as const),
      membershipCanvasEdgeCount,
      membershipSelectionFolded,
      membershipSelectionContextReady,
      fallbackSelectionActive,
      relationSelectionActive,
      groupFlowSelectionActive,
    };
  }, [
    edges,
    selectedEdgeIdx,
    selectedRelation,
    selectedGroupFlow,
    effectiveRelationSelection,
    effectiveGroupFlowSelection,
    viewsById,
  ]);

  const rfNodes: Node[] = useMemo(() => {
    const nodes: Node[] = [];
    const seenAtlasDataIds = new Set<string>();
    const seenColumnHeaderDataIds = new Set<string>();
    const seenBackplateDataIds = new Set<string>();

    // Group backplate nodes — render BEHIND everything else (zIndex 0; cards
    // get zIndex 1 implicitly via ReactFlow node ordering plus an explicit
    // zIndex bump). Each backplate spans the column's actual content height
    // (header + cards) plus padding so the territory survives the squint
    // test. Pointer-events-none in the renderer so cards remain clickable.
    const BACKPLATE_PAD_X = 22;
    const BACKPLATE_PAD_TOP = 14;
    const BACKPLATE_PAD_BOTTOM = 26;
    for (const column of columns) {
      const perLane = Math.ceil(column.count / Math.max(1, column.laneCount));
      const cardStackHeight = Math.max(1, perLane) * ROW_GAP;
      const backplateHeight = COLUMN_HEADER_HEIGHT + cardStackHeight + BACKPLATE_PAD_TOP + BACKPLATE_PAD_BOTTOM;
      const backplateWidth = NODE_WIDTH + column.width + BACKPLATE_PAD_X * 2;
      nodes.push({
        id: `__group_backplate__${column.group}`,
        type: 'groupBackplate',
        position: {
          x: column.x - BACKPLATE_PAD_X,
          y: column.y - BACKPLATE_PAD_TOP,
        },
        data: cachedNodeData(
          groupBackplateDataCacheRef.current,
          column.group,
          [
            column.group,
            backplateWidth,
            backplateHeight,
            coordinationContext.columnRoles.get(column.group) ?? 'none',
          ].join('|'),
          () => ({
            group: column.group,
            width: backplateWidth,
            height: backplateHeight,
            coordinationRole: coordinationContext.columnRoles.get(column.group) ?? null,
          }),
        ),
        draggable: false,
        selectable: false,
        focusable: false,
        zIndex: 0,
      });
      seenBackplateDataIds.add(column.group);
    }

    // Column header nodes — sit ON the backplate; carry the territory label,
    // view count, and pressure badges (failed / no-capture).
    for (const column of columns) {
      const description = shellGroupDescription.get(column.group) ?? (
        column.group === 'unassigned'
          ? 'Utilities, settings, terminal routes, or surfaces without a declared shell group.'
          : ''
      );
      const failedCount = groupCapturePosture.failed.get(column.group) ?? 0;
      const noCaptureCount = groupCapturePosture.noCapture.get(column.group) ?? 0;
      const legacyCount = groupCapturePosture.legacy.get(column.group) ?? 0;
      nodes.push({
        id: `__column_header__${column.group}`,
        type: 'columnHeader',
        position: { x: column.x, y: column.y },
        data: cachedNodeData(
          columnHeaderDataCacheRef.current,
          column.group,
          [
            column.group,
            column.count,
            failedCount,
            noCaptureCount,
            legacyCount,
            description,
            coordinationContext.columnRoles.get(column.group) ?? 'none',
          ].join('|'),
          () => ({
            group: column.group,
            count: column.count,
            failedCount,
            noCaptureCount,
            legacyCount,
            description,
            coordinationRole: coordinationContext.columnRoles.get(column.group) ?? null,
          }),
        ),
        draggable: false,
        selectable: false,
        focusable: false,
        zIndex: 2,
      });
      seenColumnHeaderDataIds.add(column.group);
    }
    // Atlas view nodes — compute focusStatus, brushStatus, and coordinationRole
    // per node so the renderer can read its opacity bucket directly without
    // re-deriving sets in the render hot path.
    const focusGroup = focusId ? viewsById.get(focusId)?.shellGroup ?? null : null;
    for (const view of views) {
      const pos = positions.get(view.id) ?? { x: 0, y: 0 };
      const isMatch = matchSet.has(view.id);
      const isFocused = view.id === focusId;
      // v6: a card is "adjacent" only when a drawn semantic pathway lands on
      // it. Folded relations (shares_component, shell_group, …) used to keep
      // bright cards without a visible line; now those cards dim correctly.
      const isAdjacent = !isFocused && visibleEdgeBudget.visibleEndpointIdSet.has(view.id);
      const isSameGroup = !isFocused && !isAdjacent && focusGroup != null && view.shellGroup === focusGroup;
      const focusStatus: FocusStatus = !focusId
        ? 'rest' // no focus selected: neutral card chrome, no gold halo
        : isFocused
          ? 'focused'
          : isAdjacent
            ? 'adjacent'
            : isSameGroup
              ? 'same_group'
              : 'dimmed';
      // v4: brushStatus only applies when the relation brush is active.
      // It supersedes focusStatus for opacity math in the renderer.
      //   anchor      — pinned/hovered anchor (kept dominant)
      //   neighbor    — the brushed connected-views target
      //   ego_context — other anchor neighbours, demoted from v3's 0.78
      //   dimmed      — everything else
      let brushStatus: BrushStatus | null = null;
      let brushTone: RelationStyle['tone'] | null = null;
      if (brushContext.active) {
        if (view.id === brushContext.anchorId) brushStatus = 'anchor';
        else if (view.id === brushContext.neighborId) {
          brushStatus = 'neighbor';
          brushTone = brushContext.tone;
        } else if (focusContext.adjacentSet.has(view.id)) brushStatus = 'ego_context';
        else brushStatus = 'dimmed';
      }
      let coordinationRole: NodeCoordinationRole | null = null;
      let coordinationTone: RelationStyle['tone'] | null = null;
      if (coordinationContext.active) {
        if (coordinationContext.selectedEndpointIdSet.has(view.id)) {
          coordinationRole = 'selected_endpoint';
          coordinationTone = coordinationContext.selectedEdgeTone;
        } else if (coordinationContext.groupFlowEndpointIdSet.has(view.id)) {
          coordinationRole = 'group_flow_endpoint';
          coordinationTone = coordinationContext.selectedGroupFlowTone;
        } else if (coordinationContext.relationEndpointIdSet.has(view.id)) {
          coordinationRole = 'relation_endpoint';
          coordinationTone = coordinationContext.selectedRelationTone;
        } else {
          coordinationRole = 'demoted';
        }
      }
      const nodeDataKey = [
        atlasViewRenderKey(view),
        focusStatus,
        brushStatus ?? 'none',
        brushTone ?? 'none',
        coordinationRole ?? 'none',
        coordinationTone ?? 'none',
        isMatch ? 'match' : 'miss',
        view.id === pinnedId ? 'pinned' : 'unpinned',
        view.id === hoveredId ? 'hovered' : 'idle',
        captureTone(view),
      ].join('|');
      nodes.push({
        id: view.id,
        type: 'atlas',
        position: pos,
        data: cachedNodeData(
          atlasNodeDataCacheRef.current,
          view.id,
          nodeDataKey,
          () => ({
            view,
            focusStatus,
            brushStatus,
            brushTone,
            coordinationRole,
            coordinationTone,
            isMatch,
            isPinned: view.id === pinnedId,
            isHovered: view.id === hoveredId,
            captureTone: captureTone(view),
          } satisfies AtlasNodeData),
        ),
        draggable: false,
        selectable: true,
        // Node z-index above edges so edges never tunnel through text.
        // ReactFlow exposes z-index via inline style on the wrapper.
        style: { zIndex: coordinationRole === 'selected_endpoint' ? 12 : 10 },
      });
      seenAtlasDataIds.add(view.id);
    }
    pruneNodeDataCache(atlasNodeDataCacheRef.current, seenAtlasDataIds);
    pruneNodeDataCache(columnHeaderDataCacheRef.current, seenColumnHeaderDataIds);
    pruneNodeDataCache(groupBackplateDataCacheRef.current, seenBackplateDataIds);
    return nodes;
  }, [
    views,
    positions,
    columns,
    matchSet,
    focusId,
    focusContext.adjacentSet,
    visibleEdgeBudget,
    pinnedId,
    hoveredId,
    viewsById,
    shellGroupDescription,
    groupCapturePosture,
    brushContext,
    coordinationContext,
  ]);

  // Relation layer reflects which edge substrate is dominant at this
  // moment. Wave SFA-1 unified the canvas grammar so aggregate corridors
  // never paint as graph edges — they live in the right-rail Group flows
  // panel instead. Layer semantics now:
  //   `aggregate` = CLEAN rest. Canvas has zero edges; Group flows panel
  //                  carries the group-pair aggregate.
  //   `skeleton`  = STRUCTURAL rest. Canvas paints exact pathway edges
  //                  only (membership relations are folded to the rail).
  //   `capture`   = CAPTURE rest. Canvas paints evidence-bearing pathway
  //                  edges only.
  //   `focus`     = any mode under focus, relation brush, or selected-key
  //                  coordination. Canvas paints the relevant pathway network.
  // Per cap_quick_atlas_edge_mode_incoherence_corridor_lin_56b4ec4c5e64.
  type AtlasRelationLayer = 'aggregate' | 'skeleton' | 'capture' | 'focus';
  const relationLayer: AtlasRelationLayer = useMemo(() => {
    if (focusContext.activeEdgeIdxSet.size > 0 || brushContext.active || coordinationContext.active) return 'focus';
    if (densityMode === 'capture') return 'capture';
    if (densityMode === 'structural') return 'skeleton';
    return 'aggregate';
  }, [focusContext.activeEdgeIdxSet, brushContext.active, coordinationContext.active, densityMode]);

  const edgeGrammarContract =
    typeof navigationGraph?.edge_grammar_contract === 'string'
      ? navigationGraph.edge_grammar_contract
      : 'missing';
  const edgeGrammarContractSource =
    edgeGrammarContract === EDGE_GRAMMAR_CONTRACT ? 'backend' : 'missing';
  const edgeExplainabilityContract =
    typeof navigationGraph?.edge_explainability_contract === 'string'
      ? navigationGraph.edge_explainability_contract
      : 'missing';
  const edgeAddressabilityContract =
    typeof navigationGraph?.edge_addressability_contract === 'string'
      ? navigationGraph.edge_addressability_contract
      : 'missing';
  const relationSummarySource =
    atlasSource === 'navigation_graph'
    && edgeExplainabilityContract === EDGE_EXPLAINABILITY_CONTRACT
    && relationSummary.length > 0
      ? 'backend'
      : 'unavailable';
  const relationExplainabilityState = relationSummarySource === 'backend' ? 'ready' : 'missing';
  const presentationRoleSource =
    atlasSource === 'navigation_graph'
    && edges.length > 0
    && edges.every((edge) => edge.presentationRoleSource === 'backend')
      ? 'backend'
      : 'frontend_fallback';
  const groupFlowSource =
    atlasSource === 'navigation_graph' && Array.isArray(navigationGraph?.group_flows)
      ? 'backend'
      : 'unavailable';
  const edgeKeySource =
    atlasSource === 'navigation_graph'
    && edges.length > 0
    && edges.every((edge) => edge.edgeKeySource === 'backend')
      ? 'backend'
      : 'frontend_fallback';
  const relationKeySource =
    atlasSource === 'navigation_graph'
    && relationSummary.length > 0
    && relationSummary.every((row) => typeof row.relation_key === 'string' && row.relation_key.length > 0)
      ? 'backend'
      : 'frontend_fallback';
  const groupFlowKeySource =
    atlasSource === 'navigation_graph'
    && groupFlows.length > 0
    && groupFlows.every((flow) => typeof flow.group_flow_key === 'string' && flow.group_flow_key.length > 0)
      ? 'backend'
      : 'frontend_fallback';
  const addressabilityState =
    edgeAddressabilityContract === EDGE_ADDRESSABILITY_CONTRACT
    && edgeKeySource === 'backend'
    && relationKeySource === 'backend'
    && groupFlowKeySource === 'backend'
      ? 'ready'
      : 'missing';
  // Pathway hover audit (frontend_navigation_pathway_hover_contract_v1)
  // -- backend invariant added in commit 8b16be5e5 saying every substantive
  // routable page must have at least one pathway edge. We surface its
  // status in the header chip + readiness attrs so a regression (a new
  // island view shipped without outboundTo) is visible at first glance
  // and to render-engine receipts, not buried in CLI output.
  const pathwayAudit: WorldModelNavigationGraphPathwayAudit | null =
    navigationGraph?.pathway_audit ?? null;
  const pathwayAuditStatus: string = pathwayAudit?.status ?? 'missing';
  const pathwayEdgeCount = countValue(
    pathwayAudit?.pathway_edge_count,
    edges.filter((e) => e.presentationRole === 'pathway').length,
  );
  const pathwayExplicitCount = countValue(pathwayAudit?.explicit_pathway_count, 0);
  const pathwayDerivedCount = countValue(pathwayAudit?.derived_pathway_count, 0);
  const pathwayZeroSubstantiveCount = countValue(
    pathwayAudit?.zero_substantive_pathway_view_count,
    0,
  );

  const readModelContract: WorldModelNavigationGraphReadModelContract | null =
    navigationGraph?.read_model_contract && isReadModelState(navigationGraph.read_model_contract.state)
      ? navigationGraph.read_model_contract
      : null;
  const atlasReadModelState: WorldModelNavigationGraphReadModelState =
    readModelContract?.state ?? 'missing';
  const atlasReadModelRouteReady = readModelContract?.route_ready ?? (atlasReadModelState === 'populated');
  const atlasReadModelReady =
    atlasSource === 'navigation_graph'
    && atlasReadModelState === 'populated'
    && atlasReadModelRouteReady;
  const atlasCaptureBudgetElapsed = useCaptureBudgetBlocker(
    !atlasReadModelReady,
    'station-surface-atlas-navigation-graph',
    3000,
  );
  useCaptureDiagnostic(
    atlasCaptureBudgetElapsed && !atlasReadModelReady
      ? (worldModelError ? 'http_error' : 'error')
      : null,
    atlasCaptureBudgetElapsed && !atlasReadModelReady
      ? (worldModelError ?? 'station-surface-atlas-navigation-graph-timeout')
      : null,
  );
  const atlasReadModelContractId = readModelContract?.contract_id ?? 'missing';
  const atlasReadModelNodeCount = countValue(readModelContract?.node_count, views.length);
  const atlasReadModelEdgeCount = countValue(readModelContract?.edge_count, edges.length);
  const atlasReadModelCaptureCount = countValue(
    readModelContract?.capture_count,
    views.filter((view) => view.captureSlug).length,
  );
  const atlasReadModelOverlayCount = countValue(
    readModelContract?.overlay_count,
    views.filter((view) => view.kind !== 'page').length,
  );
  const atlasReadModelDriftCount = countValue(readModelContract?.drift_count, 0);
  const atlasReadModelEvidenceRefCount = countValue(readModelContract?.evidence_ref_count, 0);
  const atlasReadModelEvidenceCoverage = evidenceCoverageValue(
    readModelContract?.edge_evidence_coverage,
  );

  const rfEdges: Edge[] = useMemo(() => {
    const indexed = edges.map((edge, idx) => ({ edge, idx, style: styleForMechanism(edge.relation) }));
    // Stable ordering: paint lower-priority first so high-priority ones
    // (declared outbound) stack on top.
    indexed.sort((a, b) => b.style.priority - a.style.priority);

    const drawnEdgeIdxSet = visibleEdgeBudget.drawnEdgeIdxSet;

    // ---- Local obstacle router setup (atlasEdgeRouter.ts) -------------------
    // Card obstacle rects in FLOW coords from positions + known card geometry,
    // built once per layout. Cross-cluster focus edges route AROUND intervening
    // cards through these instead of letting smoothstep tunnel through them
    // (the evaluator measured meta-diagnostics edge×node=14 on smoothstep).
    const obstacleRects: RObstacle[] = [];
    positions.forEach((p, id) => {
      obstacleRects.push({ id, x: p.x, y: p.y, w: NODE_WIDTH, h: NODE_OBST_HEIGHT });
    });
    let routeStage = { x: 0, y: 0, w: 1, h: 1 };
    if (obstacleRects.length > 0) {
      const minX = Math.min(...obstacleRects.map((r) => r.x));
      const minY = Math.min(...obstacleRects.map((r) => r.y));
      const maxX = Math.max(...obstacleRects.map((r) => r.x + r.w));
      const maxY = Math.max(...obstacleRects.map((r) => r.y + r.h));
      routeStage = {
        x: minX - ROUTE_STAGE_MARGIN,
        y: minY - ROUTE_STAGE_MARGIN,
        w: maxX - minX + 2 * ROUTE_STAGE_MARGIN,
        h: maxY - minY + 2 * ROUTE_STAGE_MARGIN,
      };
    }
    // Side-centre port point for a side (matches ReactFlow's Position handles).
    const portPt = (p: { x: number; y: number }, side: RSide): { x: number; y: number } => {
      const cx = p.x + NODE_WIDTH / 2;
      const cy = p.y + NODE_OBST_HEIGHT / 2;
      if (side === 'right') return { x: p.x + NODE_WIDTH, y: cy };
      if (side === 'left') return { x: p.x, y: cy };
      if (side === 'top') return { x: cx, y: p.y };
      return { x: cx, y: p.y + NODE_OBST_HEIGHT };
    };
    const sideFromHandle = (handle: string): RSide =>
      handle.endsWith('right') ? 'right'
        : handle.endsWith('left') ? 'left'
          : handle.endsWith('top') ? 'top'
            : 'bottom';
    // Preferred (direction-chosen) side first, then the perpendicular gutter
    // sides as fallbacks. When the preferred side faces a stacked neighbour the
    // entry/exit stub is blocked; retrying from a gutter side routes cleanly
    // instead of falling back to a card-crossing smoothstep.
    const sideCandidates = (preferred: RSide): RSide[] => {
      const perp: RSide[] = preferred === 'left' || preferred === 'right' ? ['top', 'bottom'] : ['left', 'right'];
      return [preferred, ...perp];
    };
    // Returns an obstacle-avoiding orthogonal path, or null when the straight
    // route was already clear / every side combo failed / the result still
    // collides. Null keeps the edge on getSmoothStepPath, so already-clean
    // edges stay untouched and the router can only REPLACE a path with a
    // verified-cleaner one (it cannot regress the collision metric).
    const computeRoutedPath = (
      srcPos: { x: number; y: number },
      tgtPos: { x: number; y: number },
      srcId: string,
      tgtId: string,
      sHandle: string,
      tHandle: string,
    ): string | null => {
      const others = obstacleRects.filter((o) => o.id !== srcId && o.id !== tgtId);
      const sCenter = { x: srcPos.x + NODE_WIDTH / 2, y: srcPos.y + NODE_OBST_HEIGHT / 2 };
      const tCenter = { x: tgtPos.x + NODE_WIDTH / 2, y: tgtPos.y + NODE_OBST_HEIGHT / 2 };
      // Only route when the straight chord actually crosses a card.
      if (!chordCrossesAnyObstacle(sCenter, tCenter, others, ROUTE_INFLATE)) return null;
      const sSides = sideCandidates(sideFromHandle(sHandle));
      const tSides = sideCandidates(sideFromHandle(tHandle));
      for (const ts of tSides) {
        for (const ss of sSides) {
          const route = routeOrthogonal(portPt(srcPos, ss), ss, portPt(tgtPos, ts), ts, others, {
            inflate: ROUTE_INFLATE,
            bendPenalty: ROUTE_BEND_PENALTY,
            stage: routeStage,
          });
          if (route && route.length >= 2 && !polylineHitsObstacle(route, others)) {
            return pointsToRoundedPath(route, 6);
          }
        }
      }
      return null;
    };

    // Helper: compose the endpoint-aware label text. When a focus card is
    // anchored, the chip reads "OPENS → META-MISSIONS" outbound from focus
    // or "← OPENS LAUNCHPAD" inbound to focus, so the line's direction is
    // unambiguous. When there is no focus (brush / coordination paths) we
    // fall back to the bidirectional "LAUNCHPAD opens META-MISSIONS" shape.
    const formatEdgeLabel = (
      edge: AtlasEdge,
      focusEndpoint: 'source' | 'target' | null,
    ): string => {
      // Compact relation code (OPEN / ROUTE / GROUP / COMP / ADJ ...) instead
      // of the verbose backend prose ("navigation adjacency"): the on-canvas
      // chip must be short so labels do not collide with cards or each other.
      // The full relation prose stays available in the detail panel.
      const relationText = compactLabelForMechanism(edge.relation);
      const sourceLabel = viewsById.get(edge.source)?.label ?? edge.source;
      const targetLabel = viewsById.get(edge.target)?.label ?? edge.target;
      if (focusEndpoint === 'source') return `${relationText} → ${targetLabel}`;
      if (focusEndpoint === 'target') return `← ${relationText} ${sourceLabel}`;
      return `${sourceLabel} ${relationText} → ${targetLabel}`;
    };

    return indexed.flatMap(({ edge, idx, style }) => {
      const touchesFocus = focusContext.activeEdgeIdxSet.has(idx);
      const isBrushed = brushContext.active && brushContext.edgeIdxSet.has(idx);
      const coordinationRole: EdgeCoordinationRole | null =
        coordinationContext.selectedEdgeIdxSet.has(idx)
          ? 'selected_edge'
          : coordinationContext.relationEdgeIdxSet.has(idx) && coordinationContext.groupFlowEdgeIdxSet.has(idx)
            ? 'context'
            : coordinationContext.relationEdgeIdxSet.has(idx)
              ? 'relation_match'
              : coordinationContext.groupFlowEdgeIdxSet.has(idx)
                ? 'group_flow_match'
                : coordinationContext.active
                  ? 'demoted'
                  : null;
      const isCoordinationMatch =
        coordinationRole === 'selected_edge'
        || coordinationRole === 'relation_match'
        || coordinationRole === 'group_flow_match'
        || coordinationRole === 'context';
      const touchesBrushNeighbor =
        brushContext.active &&
        brushContext.neighborId != null &&
        (edge.source === brushContext.neighborId || edge.target === brushContext.neighborId);
      if (!viewsById.has(edge.source) || !viewsById.has(edge.target)) return [];
      // Draw gate. The visibleEdgeBudget (focus / brush) is the authority on the
      // hovered / pinned node's neighbourhood and now includes membership ties,
      // capped — so hover / right-click reveals connections for EVERY node, not
      // only nodes that happen to declare pathway edges (the regression the
      // operator flagged). At rest nothing is budgeted, so the v6 anti-spaghetti
      // fold still holds for the whole canvas. The coordination / URL audit lane
      // keeps the stricter rule: it must not smuggle a folded relation onto the
      // canvas, so a coordination-only match draws only a true pathway relation.
      const inFocusOrBrushBudget = drawnEdgeIdxSet.has(idx);
      if (!inFocusOrBrushBudget) {
        if (!isCoordinationMatch) return [];
        if (isMembershipEdge(edge) || !DRAWN_CANVAS_MECHANISMS.has(edge.relation)) return [];
      }

      // Pathway ties (declared / overlay / route / shared API) are exact routes;
      // membership / adjacency ties (shell or station group, shared component,
      // lens) are affinity ties. They render as different mark classes so the
      // map never dresses a membership tie up as an exact route.
      const isPathwayEdge = DRAWN_CANVAS_MECHANISMS.has(edge.relation);

      const focusEndpoint: 'source' | 'target' | null = focusId
        ? edge.source === focusId
          ? 'source'
          : edge.target === focusId
            ? 'target'
            : null
        : null;

      const sourceMatched = matchSet.has(edge.source);
      const targetMatched = matchSet.has(edge.target);
      const matchedPair = sourceMatched && targetMatched;
      let visualWeight: number;
      let isVisuallyActive: boolean;
      if (coordinationRole === 'selected_edge') {
        visualWeight = 1.0;
        isVisuallyActive = true;
      } else if (brushContext.active) {
        if (isBrushed) {
          visualWeight = 1.0;
          isVisuallyActive = true;
        } else if (touchesFocus) {
          visualWeight = 0.30;
          isVisuallyActive = false;
        } else if (touchesBrushNeighbor) {
          visualWeight = 0.22;
          isVisuallyActive = false;
        } else {
          visualWeight = 0.05;
          isVisuallyActive = false;
        }
      } else if (coordinationContext.active) {
        if (coordinationRole === 'relation_match' || coordinationRole === 'group_flow_match') {
          visualWeight = 0.76;
          isVisuallyActive = true;
        } else if (coordinationRole === 'context') {
          visualWeight = 0.66;
          isVisuallyActive = true;
        } else {
          visualWeight = 0.40;
          isVisuallyActive = false;
        }
      } else if (touchesFocus) {
        // Focused node's neighbourhood: exact pathway ties read as authoritative
        // routes; membership / adjacency ties stay SECONDARY but must remain
        // LEGIBLE. The prior 0.4 ghosted affinity into a failed mark — a drawn
        // edge below the readability floor carries no semantics. Affinity now
        // sits at a readable floor (0.72), kept secondary by thinner width +
        // dotted dash + the dark under-stroke (not by near-invisibility).
        visualWeight = isPathwayEdge ? 1.0 : 0.85;
        isVisuallyActive = isPathwayEdge;
      } else {
        visualWeight = matchedPair ? 0.85 : 0.75;
        isVisuallyActive = false;
      }
      const strokeActive = coordinationRole === 'selected_edge'
        || coordinationRole === 'relation_match'
        || coordinationRole === 'group_flow_match'
        || coordinationRole === 'context'
        || isBrushed
        || (isVisuallyActive && !brushContext.active);
      // Only the budgeted top-N focus edges (and coordination/URL matches) get
      // a text label; the remaining neighbourhood edges draw as quiet
      // unlabelled lines. This kills the overlapping "label soup" the operator
      // hit on hover/pin while still showing every connection as a line.
      const labelVisible = visibleEdgeBudget.labelEdgeIdxSet.has(idx) || isCoordinationMatch;
      // Focus reveal: the selected/active edge set uses the BRIGHT per-tone
      // stroke so it is actually perceptible (the base activeStroke is a low-
      // alpha legend tint that nets ~1.1:1 contrast on the dark backplate).
      // Rest/dimmed edges keep the quiet activeStroke.
      const stroke = touchesFocus || strokeActive
        ? (TONE_FOCUS_STROKE[style.tone] ?? style.activeStroke)
        : style.activeStroke;
      let strokeWidth = Math.max(1.0, (edge.weight ?? 0.5) * 1.6);
      if (coordinationRole === 'selected_edge') strokeWidth = 2.8;
      else if (coordinationRole === 'relation_match' || coordinationRole === 'group_flow_match') strokeWidth = 2.0;
      else if (isBrushed) strokeWidth = 2.4;
      else if (coordinationRole === 'context' || isVisuallyActive) strokeWidth = 1.8;
      else if (touchesFocus) strokeWidth = 1.6; // readable affinity floor (kept < pathway 1.8)
      // Salience ladder: primary (selected/brushed) > pathway (exact route) >
      // affinity. Drives the dual-stroke so each drawn edge is legible AS its
      // class. The dark under-stroke is the contrast halo across tinted
      // backplates; skip it on brush-dimmed background edges so they stay quiet.
      const semanticRole: AtlasEdgeSemanticRole =
        coordinationRole === 'selected_edge' || isBrushed
          ? 'primary'
          : isPathwayEdge && isVisuallyActive
            ? 'pathway'
            : 'affinity';
      const showUnderStroke = visualWeight >= 0.5;
      // Side-aware ports: choose the handle pair by the direction between the two
      // cards so the edge leaves/enters sensible sides — a same-column tie uses
      // top/bottom instead of doubling back across the stack, a cross-cluster tie
      // uses the facing sides. AtlasRelationEdge re-routes the smoothstep from the
      // chosen sides automatically.
      const sPos = positions.get(edge.source);
      const tPos = positions.get(edge.target);
      let sourceHandle = 's-right';
      let targetHandle = 't-left';
      if (sPos && tPos) {
        const ddx = tPos.x - sPos.x;
        const ddy = tPos.y - sPos.y;
        if (Math.abs(ddx) >= Math.abs(ddy)) {
          sourceHandle = ddx >= 0 ? 's-right' : 's-left';
          targetHandle = ddx >= 0 ? 't-left' : 't-right';
        } else {
          sourceHandle = ddy >= 0 ? 's-bottom' : 's-top';
          targetHandle = ddy >= 0 ? 't-top' : 't-bottom';
        }
      }
      // Obstacle-avoiding route for cross-cluster edges (null = keep smoothstep).
      const routedPath = sPos && tPos
        ? computeRoutedPath(sPos, tPos, edge.source, edge.target, sourceHandle, targetHandle)
        : null;
      return [{
        id: `e:${idx}:${edge.source}->${edge.target}`,
        source: edge.source,
        target: edge.target,
        sourceHandle,
        targetHandle,
        // Suppress ReactFlow v11's default edge accessible name. Without
        // this, EdgeWrapper emits `aria-label="Edge from <source> to
        // <target>"` for every edge — the topology meaning lives at the
        // whole-graph level, not per-edge. Nodes remain fully labelled.
        ariaLabel: '',
        // Atlas v6 custom edge: visibleEdgeBudget enforces "drawn = labelled"
        // and AtlasRelationEdge positions the chip near the focus endpoint.
        type: 'atlasRelation',
        data: {
          relation: edge.relation,
          presentationRole: edge.presentationRole,
          label: formatEdgeLabel(edge, focusEndpoint),
          labelVisible,
          tone: style.tone,
          priority: style.priority,
          isBrushed,
          isFocusPrimary: isVisuallyActive,
          coordinationRole,
          activeStroke: style.activeStroke,
          focusEndpoint,
          routedPath,
          semanticRole,
          showUnderStroke,
        } satisfies AtlasRelationEdgeData,
        style: {
          stroke,
          strokeWidth,
          // Affinity ties read as DASHED (not exact routes) but with a dense
          // dash so the line stays legible — the prior sparse '2 5' (~29% ink)
          // measured ~1.1-1.6:1 contrast (near-invisible) because the gaps
          // dominate. '5 3' (~63% ink) keeps the dashed-=-weaker semantic while
          // crossing the perceptual floor. Pathway edges keep their own dash.
          strokeDasharray: isPathwayEdge ? style.dash : '5 3',
          opacity: visualWeight,
        },
        // Animate only the brushed/touching-focus edges so the inspected
        // relationship reads as alive without the whole graph wobbling.
        animated: strokeActive && style.priority <= 4,
        zIndex: coordinationRole === 'selected_edge' ? 9 : isBrushed ? 8 : isVisuallyActive ? 5 : 1,
        // Wave 24 — invisible 14px-wide click target around the visible
        // edge path.
        interactionWidth: 14,
      } satisfies Edge];
    });
  }, [edges, focusId, focusContext.activeEdgeIdxSet, matchSet, brushContext, visibleEdgeBudget, coordinationContext, viewsById, positions]);

  // Wave SFA-2 — group-pair aggregates are backend-projected Group flows,
  // not a parallel ReactFlow edge layer. The canvas carries one grammar:
  // exact pathway/fallback relation edges after the backend presentation-role
  // filter.
  //
  // INVARIANT: aggregate corridors never render as ReactFlow graph edges.
  const corridorCanvasEdgeCount = 0;
  const allRfEdges: Edge[] = rfEdges;

  // Atlas v5 layout receipt — deterministic geometry/budget snapshot of the
  // current layout pass. Emitted as a data attribute on the root container
  // so station_render.py and frontend tests can read it without spinning up
  // a measurement harness. Estimates use known card geometry (NODE_WIDTH /
  // NODE_HEIGHT + ROW_GAP / COLUMN_GAP) rather than DOM bounding boxes so
  // the receipt is stable across engines and runs at zero render cost.
  const layoutReceipt = useMemo(() => {
    const focusedNodeId = focusId;
    const focusTouchingCount = focusContext.activeEdgeIdxSet.size;
    const visibleLabelCount = labelBudget.size;
    // Per-column descriptive statistics for the current manual-column
    // layout. maxColumnHeight is the tallest column in node units; blank-
    // SpaceRatio is the fraction of the union bounding box that is empty
    // beneath shorter columns. Both are direct numeric witnesses to the
    // operator's "MAP has 13, DATA has 4" complaint.
    const columnCounts = columns.map((c) => c.count);
    const maxColumnHeight = columnCounts.length > 0 ? Math.max(...columnCounts) : 0;
    const totalLane = maxColumnHeight * Math.max(columnCounts.length, 1);
    const totalUsed = columnCounts.reduce((acc, c) => acc + c, 0);
    const blankSpaceRatio = totalLane > 0 ? 1 - totalUsed / totalLane : 0;
    // Suppressed-label count: focus-touching edges whose labels did NOT
    // make the budget. Includes both structural mechanisms (always folded
    // to the panel) and high-authority candidates beyond the cap.
    const foldedOrSuppressedLabels = Math.max(0, focusTouchingCount - visibleLabelCount);
    // Structural mechanism count on focus-touching edges — operator's
    // "SAME STATION GROUP / STATION LENS MENU" noise lives here.
    let structuralOnFocus = 0;
    for (const idx of focusContext.activeEdgeIdxSet) {
      const e = edges[idx];
      if (e && STRUCTURAL_MECHANISMS_ON_CANVAS.has(e.relation)) structuralOnFocus += 1;
    }
    // Cheap graph hash for change detection. Not cryptographic; just a
    // stable string that flips when the topology changes.
	    const graphHash =
	      `n${views.length}:e${edges.length}:c${columns.length}:fh${focusedNodeId ?? ''}` +
	      `:bh${brushContext.active ? brushContext.relation ?? '' : ''}` +
	      `:coord${coordinationContext.mode}:${selectedRelationResolvedKey ?? ''}:${selectedGroupFlowResolvedKey ?? ''}`;
    // Per-lane height once the hybrid packer distributes nodes round-
    // robin. With laneCount > 1, the tallest visible lane is ceil(count /
    // laneCount). This is the actual operator-visible column height after
    // packing — not the raw node count.
    const maxLaneHeight = columns.reduce((acc, c) => {
      const tallestLane = c.laneCount > 0 ? Math.ceil(c.count / c.laneCount) : c.count;
      return Math.max(acc, tallestLane);
    }, 0);
    // Total occupied lane slots vs total available lane slots in the
    // tallest packed lane × total lanes — the actual whitespace ratio
    // after v5 packing, not the raw column-vs-count blank ratio.
    const totalLanes = columns.reduce((acc, c) => acc + c.laneCount, 0);
    const totalLaneSlots = maxLaneHeight * Math.max(totalLanes, 1);
    const packedBlankSpaceRatio = totalLaneSlots > 0 ? 1 - totalUsed / totalLaneSlots : 0;
    return {
      schema: 'station_atlas_layout_receipt_v0',
      generated_at: 'render_time',
      graphHash,
      layoutMode: 'hybrid_shell_packer' as const,
      densityMode,
	      activeLens: coordinationContext.active
	        ? 'selection_coordination'
	        : brushContext.active
	          ? 'relation_brush'
	          : focusedNodeId
	            ? 'focus'
	            : 'rest',
      focusedNodeId,
      brushedNeighborId: brushContext.active ? brushContext.neighborId : null,
      brushedRelation: brushContext.active ? brushContext.relation : null,
      relationKinds: edges.reduce<Record<string, number>>((acc, e) => {
        acc[e.relation] = (acc[e.relation] ?? 0) + 1;
        return acc;
      }, {}),
      counts: {
        nodes: views.length,
        edges: edges.length,
        columns: columns.length,
        totalLanes,
        visibleLabels: visibleLabelCount,
        focusTouchingEdges: focusTouchingCount,
        suppressedLabels: foldedOrSuppressedLabels,
        structuralOnFocus,
        // Wave SFA-2 — aggregate counts. exactEdgesVisible names the
        // ReactFlow edges currently painted; corridorsTotal is retained for
        // compatibility and now reflects backend group_flows length.
        exactEdgesVisible: rfEdges.length,
        corridorsTotal: groupFlows.length,
        corridorsVisible: corridorCanvasEdgeCount,
        relationLayer,
        // Wave SFA-2 — edge grammar invariants.
        canvasPathwayEdgeCount: rfEdges.length,
        canvasAggregateCorridorCount: corridorCanvasEdgeCount,
        groupFlowRailItemCount: groupFlows.length,
      },
      columnGeometry: {
        // Raw max — kept for backward-compatible diff against the v1
        // manual_columns receipt. maxLaneHeight is the actual v5 packed
        // height the operator sees.
        maxColumnHeight,
        maxLaneHeight,
        blankSpaceRatio: Number(blankSpaceRatio.toFixed(3)),
        packedBlankSpaceRatio: Number(packedBlankSpaceRatio.toFixed(3)),
        perColumn: columns.map((c) => ({
          group: c.group,
          count: c.count,
          laneCount: c.laneCount,
        })),
      },
      packingPolicy: {
        lane2Threshold: LAYOUT_LANE2_THRESHOLD,
        lane3Threshold: LAYOUT_LANE3_THRESHOLD,
        laneOffsetPx: LANE_OFFSET,
        columnGapPx: COLUMN_GAP,
        rowGapPx: ROW_GAP,
        sortKeys: ['capture_posture', 'centrality_fanin_plus_fanout', 'label_alpha'],
      },
      budgetPolicy: {
        labelCapPerFocus: ATLAS_LABEL_CAP_PER_FOCUS,
        highAuthorityMechanisms: [...HIGH_AUTHORITY_MECHANISMS],
        structuralMechanismsFoldedToPanel: [...STRUCTURAL_MECHANISMS_ON_CANVAS],
      },
      // Wave SFA-2 — Station Atlas Edge Grammar receipt. Names the backend
      // contract so station_render selectors can assert that presentation
      // roles and group flows came from world_model.py, not a frontend reducer.
      edgeGrammar: {
        contract: edgeGrammarContract,
        contractSource: edgeGrammarContractSource,
        presentationRoleSource,
        groupFlowSource,
        canvasEdgeRole:
          rfEdges.length === 0
            ? ('none' as const)
            : ('pathway' as const),
        canvasAggregateCorridorCount: corridorCanvasEdgeCount,
        groupFlowRailReady: groupFlows.length > 0,
        membershipFolded: true,
        membershipGloballyFolded: true,
      },
      relationExplainability: {
        contract: edgeExplainabilityContract,
        contractSource: relationSummarySource === 'backend' ? 'backend' : 'missing',
        relationSummarySource,
        relationSummaryCount: relationSummary.length,
        groupFlowDrillthrough:
          selectedGroupFlow !== null && Array.isArray(selectedGroupFlow.sample_edges)
            ? ('ready' as const)
            : ('empty' as const),
        edgeInspector: selectedEdgeIdx !== null ? ('ready' as const) : ('idle' as const),
      },
	      addressability: {
	        contract: edgeAddressabilityContract,
	        state: addressabilityState,
        edgeKeySource,
        relationKeySource,
        groupFlowKeySource,
        relationSelection: effectiveRelationSelection,
        selectedRelation: selectedRelationResolvedKey,
        groupFlowSelection: effectiveGroupFlowSelection,
        selectedGroupFlow: selectedGroupFlowResolvedKey,
	        edgeSelection: selectedEdgeIdx !== null ? selectedEdgeSource : 'none',
	      },
	      coordination: {
	        contract: EDGE_COORDINATION_CONTRACT,
	        state: coordinationContext.active || addressabilityState === 'ready' ? 'ready' : 'idle',
	        mode: coordinationContext.mode,
	        selectedEdgeVisible: coordinationContext.selectedEdgeVisible ? 'ready' : 'idle',
	        selectedEdgeEndpoints: coordinationContext.selectedEdgeEndpointsReady ? 'ready' : 'idle',
        selectedRelationEdgeCount: coordinationContext.relationEdgeIdxSet.size,
        selectedGroupFlowEdgeCount: coordinationContext.groupFlowEdgeIdxSet.size,
        unrelatedEdgeDemotion: coordinationContext.unrelatedEdgeDemotionReady ? 'ready' : 'idle',
        selectedRelationRole,
        selectedRelationRoleSource: selectedRelation ? 'backend' : 'unavailable',
        membershipSelection: coordinationContext.membershipSelection,
        membershipCanvasEdgeCount: coordinationContext.membershipCanvasEdgeCount,
        membershipSelectionFolded:
          coordinationContext.membershipSelectionFolded
            ? 'ready'
            : coordinationContext.membershipSelectionActive
              ? 'missing'
              : 'idle',
        membershipSelectionContext:
          coordinationContext.membershipSelectionContextReady
            ? 'ready'
            : coordinationContext.membershipSelectionActive
              ? 'missing'
              : 'idle',
        fallbackSelection:
          coordinationContext.fallbackSelectionActive
            ? 'active'
            : fallbackRelationAvailable
              ? 'inactive'
              : 'unavailable',
      },
	      readModelContract: {
        contract: atlasReadModelContractId,
        state: atlasReadModelState,
        routeReady: atlasReadModelReady,
        nodeCount: atlasReadModelNodeCount,
        edgeCount: atlasReadModelEdgeCount,
        captureCount: atlasReadModelCaptureCount,
        overlayCount: atlasReadModelOverlayCount,
        driftCount: atlasReadModelDriftCount,
        evidenceRefCount: atlasReadModelEvidenceRefCount,
        edgeEvidenceCoverage: atlasReadModelEvidenceCoverage,
        fallback: readModelContract?.fallback_reason ? 'present' : 'absent',
        stale: readModelContract?.stale_reason ? 'present' : 'absent',
        invalid: readModelContract?.invalid_reason ? 'present' : 'absent',
      },
    };
  }, [
    views,
    edges,
    columns,
    focusId,
    focusContext.activeEdgeIdxSet,
    labelBudget,
    brushContext,
    densityMode,
    groupFlows.length,
    rfEdges.length,
    relationLayer,
    edgeGrammarContract,
    edgeGrammarContractSource,
    edgeExplainabilityContract,
    edgeAddressabilityContract,
    addressabilityState,
    edgeKeySource,
    relationKeySource,
    groupFlowKeySource,
    relationSummarySource,
    relationSummary.length,
    effectiveRelationSelection,
	    selectedRelationResolvedKey,
    selectedRelation,
    selectedRelationRole,
	    effectiveGroupFlowSelection,
	    selectedGroupFlowResolvedKey,
	    selectedGroupFlow,
	    selectedEdgeIdx,
	    selectedEdgeSource,
	    coordinationContext,
    fallbackRelationAvailable,
	    presentationRoleSource,
    groupFlowSource,
    atlasReadModelContractId,
    atlasReadModelState,
    atlasReadModelReady,
    atlasReadModelNodeCount,
    atlasReadModelEdgeCount,
    atlasReadModelCaptureCount,
    atlasReadModelOverlayCount,
    atlasReadModelDriftCount,
    atlasReadModelEvidenceRefCount,
    atlasReadModelEvidenceCoverage,
    readModelContract?.fallback_reason,
    readModelContract?.stale_reason,
    readModelContract?.invalid_reason,
  ]);

  const onOpenRoute = useCallback(
    (route: string) => {
      navigate(route);
    },
    [navigate],
  );

  const onSetSearch = useCallback((value: string) => {
    recordAtlasEvent('searchChange');
    setSearch((current) => (current === value ? current : value));
  }, []);

  const onSetActiveGroup = useCallback((group: ShellSurfaceGroupId | 'unassigned' | 'all') => {
    setActiveGroup((current) => (current === group ? current : group));
  }, []);

  const onAtlasPointerDownCapture = useCallback(() => {
    viewportGestureActiveRef.current = true;
    viewportMovedDuringGestureRef.current = false;
    suppressPointerUntilRef.current = 0;
    clearHoverIntent();
    setViewportMoving(true);
    if (viewportMoveEndTimerRef.current !== null) {
      window.clearTimeout(viewportMoveEndTimerRef.current);
      viewportMoveEndTimerRef.current = null;
    }
  }, [clearHoverIntent, setViewportMoving]);
  const onAtlasPointerUpCapture = useCallback(() => {
    if (viewportMovedDuringGestureRef.current) return;
    viewportGestureActiveRef.current = false;
    setViewportMoving(false);
  }, [setViewportMoving]);

  const selectedView = useMemo(
    () => (railFocusId ? viewsById.get(railFocusId) ?? null : null),
    [railFocusId, viewsById],
  );

  // Wave 24 — edgeKey lookup. Maps stable edge keys back to runtime
  // indexes so URL/capture state can deep-link relations without
  // depending on the array-order fragile index.
  const edgeKeyToIdx = useMemo(() => {
    const map = new Map<string, number>();
    edges.forEach((edge, idx) => {
      map.set(edgeKeyFor(edge), idx);
    });
    return map;
  }, [edges]);

  // Stable key for the currently-selected edge; null when no edge focused.
  // Used by both the data-attr receipt and the URL-sync effect.
  const selectedEdgeKey = useMemo(() => {
    if (selectedEdgeIdx === null) return null;
    const edge = edges[selectedEdgeIdx];
    return edge ? edgeKeyFor(edge) : null;
  }, [selectedEdgeIdx, edges]);
  const selectedEdgeKeySource =
    selectedEdgeIdx !== null
      ? edges[selectedEdgeIdx]?.edgeKeySource ?? 'frontend_fallback'
      : 'none';
  const effectiveEdgeSelection: EdgeSelectionSource = selectedEdgeIdx !== null ? selectedEdgeSource : 'none';

  // Wave 22 Phase 2 — resolve the selected edge into the dossier payload.
  // Carries the AtlasEdge itself plus the source/target view labels +
  // shell groups so DetailPanel can render the relation context without
  // needing the viewsById map. Null whenever no edge is selected (which
  // includes the default rest state and any pane-click / Escape clear).
  const edgeFocus = useMemo(() => {
    if (selectedEdgeIdx === null) return null;
    const edge = edges[selectedEdgeIdx];
    if (!edge) return null;
    const sourceView = viewsById.get(edge.source) ?? null;
    const targetView = viewsById.get(edge.target) ?? null;
    return { edge, sourceView, targetView };
  }, [selectedEdgeIdx, edges, viewsById]);

  const onClearPin = useCallback(() => {
    setPinnedId((current) => (current === null ? current : null));
  }, []);
  const onClearEdgeFocus = useCallback(() => {
    if (selectedEdgeIdxRef.current === null && selectedEdgeSourceRef.current === 'none') return;
    setSelectedEdgeIdx(null);
    setSelectedEdgeSource('none');
  }, []);
  const onSelectRelation = useCallback((key: string) => {
    if (selectedRelationKeyRef.current === key && selectedRelationSourceRef.current === 'row') return;
    recordAtlasEvent('relationSelect');
    startRailTransition(() => {
      setSelectedRelationKey(key);
      setSelectedRelationSource('row');
    });
  }, [startRailTransition]);
  const onSelectGroupFlow = useCallback((key: string) => {
    if (selectedGroupFlowKeyRef.current === key && selectedGroupFlowSourceRef.current === 'row') return;
    recordAtlasEvent('groupFlowSelect');
    startRailTransition(() => {
      setSelectedGroupFlowKey(key);
      setSelectedGroupFlowSource('row');
    });
  }, [startRailTransition]);
  const onSelectSampleEdge = useCallback((edgeKey: string) => {
    const idx = edgeKeyToIdx.get(edgeKey);
    if (idx === undefined) return;
    if (selectedEdgeIdxRef.current === idx && selectedEdgeSourceRef.current === 'sample') return;
    recordAtlasEvent('sampleEdgeSelect');
    startRailTransition(() => {
      setSelectedEdgeIdx(idx);
      setSelectedEdgeSource('sample');
    });
  }, [edgeKeyToIdx, startRailTransition]);

  // Wave 24 URL → state sync. Read `?node`, `?edge`, `?density` from the
  // current location and project them onto the Atlas's interaction state.
  // One-way (URL drives state, not the reverse) so user clicks don't fight
  // the address bar; the URL is a deep-link entry point that
  // station_render uses to capture deterministic node/edge/density states.
  useEffect(() => {
    const queryNode = searchParams.get('node');
    if (queryNode && queryNode !== pinnedId) {
      setPinnedId(queryNode);
    }
    const queryRelation = searchParams.get('relation');
    if (queryRelation) {
      setSelectedRelationKey(queryRelation);
      setSelectedRelationSource('url');
    }
    const queryGroupFlow = searchParams.get('group_flow');
    if (queryGroupFlow) {
      setSelectedGroupFlowKey(queryGroupFlow);
      setSelectedGroupFlowSource('url');
    }
    const queryEdge = searchParams.get('edge_key') ?? searchParams.get('edge');
    if (queryEdge) {
      const idx = edgeKeyToIdx.get(queryEdge);
      if (idx !== undefined && idx !== selectedEdgeIdx) {
        setSelectedEdgeIdx(idx);
        setSelectedEdgeSource('url');
      }
    }
    const queryDensity = searchParams.get('density');
    if (
      (queryDensity === 'clean' || queryDensity === 'structural' || queryDensity === 'capture')
      && queryDensity !== densityMode
    ) {
      setDensityMode(queryDensity);
    }
    // pinnedId/selectedEdgeIdx/densityMode intentionally NOT in deps:
    // including them would re-fire whenever the operator clicks (clearing
    // pin/edge would re-apply the stale URL value). We only want to
    // *apply* URL when the URL changes, not when state mutates.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, edgeKeyToIdx]);
  void setSearchParams;

  const capturedCount = useMemo(() => views.filter((v) => v.captureLatestStatus === 'captured').length, [views]);
  const legacyCount = useMemo(() => views.filter((v) => v.isLegacy).length, [views]);
  // Failed / timed-out captures are the highest-priority attention class — they
  // drive the inspector's "next action" line above routine uncaptured surfaces.
  const failedCount = useMemo(
    () => views.filter((v) => v.captureLatestStatus === 'failed' || v.captureLatestStatus === 'readiness_timeout').length,
    [views],
  );
  const perfReceipt = useMemo(() => ({
    schema: 'station_surface_atlas_perf_receipt_v1',
    rfNodes: rfNodes.length,
    rfEdges: allRfEdges.length,
    visibleCanvasEdgeCount: rfEdges.length,
    sourceEdgeCount: edges.length,
    relationRows: relationSummary.length,
    groupFlowRows: groupFlows.length,
    moving: viewportMovingRef.current,
    railTransitionPending: isRailTransitionPending,
    searchDeferred: deferredSearch !== search,
    memoizedRenderers: [
      'AtlasNodeRenderer',
      'AtlasRelationEdge',
      'ColumnHeaderRenderer',
      'AtlasGroupBackplateRenderer',
      'RelationLegend',
      'DetailPanel',
      'GroupFlowDrillthrough',
      'AtlasInteractionGuide',
      'GroupRail',
    ],
  }), [
    rfNodes.length,
    allRfEdges.length,
    rfEdges.length,
    edges.length,
    relationSummary.length,
    groupFlows.length,
    isRailTransitionPending,
    deferredSearch,
    search,
  ]);
  useEffect(() => {
    updateAtlasPerfGraph({
      rfNodes: rfNodes.length,
      rfEdges: allRfEdges.length,
      visibleCanvasEdgeCount: rfEdges.length,
      sourceEdgeCount: edges.length,
      relationRows: relationSummary.length,
      groupFlowRows: groupFlows.length,
      moving: viewportMovingRef.current,
      railTransitionPending: isRailTransitionPending,
      searchDeferred: deferredSearch !== search,
    });
  }, [
    rfNodes.length,
    allRfEdges.length,
    rfEdges.length,
    edges.length,
    relationSummary.length,
    groupFlows.length,
    isRailTransitionPending,
    deferredSearch,
    search,
  ]);
  const onViewportMoveStart = useCallback(() => {
    viewportGestureActiveRef.current = true;
    viewportMovedDuringGestureRef.current = false;
    suppressPointerUntilRef.current = 0;
    clearHoverIntent();
    if (viewportMoveEndTimerRef.current !== null) {
      window.clearTimeout(viewportMoveEndTimerRef.current);
      viewportMoveEndTimerRef.current = null;
    }
  }, [clearHoverIntent]);
  const onViewportMove = useCallback(() => {
    if (!viewportGestureActiveRef.current) return;
    if (viewportMovedDuringGestureRef.current) return;
    viewportMovedDuringGestureRef.current = true;
    recordAtlasEvent('moveStart');
    setViewportMoving(true);
  }, [setViewportMoving]);
  const onViewportMoveEnd = useCallback(() => {
    viewportGestureActiveRef.current = false;
    if (!viewportMovedDuringGestureRef.current) {
      setViewportMoving(false);
      return;
    }
    recordAtlasEvent('moveEnd');
    suppressPointerUntilRef.current = interactionNowMs() + 48;
    if (viewportMoveEndTimerRef.current !== null) {
      window.clearTimeout(viewportMoveEndTimerRef.current);
    }
    viewportMoveEndTimerRef.current = window.setTimeout(() => {
      viewportMoveEndTimerRef.current = null;
      setViewportMoving(false);
      clearHoverIntent();
      setHoveredId((current) => (current === null ? current : null));
      setRailHoveredId((current) => (current === null ? current : null));
      setRelationBrush((current) => (current.mode === 'none' ? current : { mode: 'none' }));
    }, 48);
  }, [clearHoverIntent, setViewportMoving]);
  const onReactFlowNodeClick = useCallback((event: ReactMouseEvent, node: Node) => {
    if (node.type !== 'atlas') return;
    if (shouldSuppressPointerAfterMove()) return;
    recordAtlasEvent('nodeClick');
    if (event.altKey || event.metaKey) {
      setPinnedId((current) => (current === node.id ? current : node.id));
      return;
    }
    const view = viewsById.get(node.id);
    if (view) onOpenRoute(view.entryRoute);
  }, [onOpenRoute, shouldSuppressPointerAfterMove, viewsById]);
  const onReactFlowNodeMouseEnter = useCallback((_event: ReactMouseEvent, node: Node) => {
    if (node.type !== 'atlas') return;
    if (viewportGestureActiveRef.current || viewportMovingRef.current) return;
    recordAtlasEvent('nodeMouseEnter');
    clearHoverIntent();
    hoverIntentTimerRef.current = window.setTimeout(() => {
      hoverIntentTimerRef.current = null;
      if (viewportGestureActiveRef.current || viewportMovingRef.current) return;
      setHoveredId((current) => (current === node.id ? current : node.id));
      startRailTransition(() => {
        setRailHoveredId((current) => (current === node.id ? current : node.id));
      });
    }, ATLAS_HOVER_INTENT_MS);
  }, [clearHoverIntent, startRailTransition]);
  const onReactFlowNodeMouseLeave = useCallback((_event: ReactMouseEvent, node: Node) => {
    if (node.type !== 'atlas') return;
    clearHoverIntent();
    if (viewportGestureActiveRef.current || viewportMovingRef.current) return;
    recordAtlasEvent('nodeMouseLeave');
    setHoveredId((current) => (current === node.id ? null : current));
    startRailTransition(() => {
      setRailHoveredId((current) => (current === node.id ? null : current));
    });
  }, [clearHoverIntent, startRailTransition]);
  const onReactFlowNodeContextMenu = useCallback((event: ReactMouseEvent, node: Node) => {
    if (node.type !== 'atlas') return;
    event.preventDefault();
    if (shouldSuppressPointerAfterMove()) return;
    recordAtlasEvent('nodeContextMenu');
    setPinnedId((current) => (current === node.id ? null : node.id));
  }, [shouldSuppressPointerAfterMove]);
  const onReactFlowEdgeClick = useCallback((_event: ReactMouseEvent, edge: Edge) => {
    if (shouldSuppressPointerAfterMove()) return;
    const match = /^e:(\d+):/.exec(edge.id);
    if (!match) return;
    recordAtlasEvent('edgeClick');
    const idx = Number(match[1]);
    const next = selectedEdgeIdxRef.current === idx ? null : idx;
    setSelectedEdgeIdx(next);
    setSelectedEdgeSource(next === null ? 'none' : 'canvas');
  }, [shouldSuppressPointerAfterMove]);
  const onReactFlowPaneClick = useCallback(() => {
    if (shouldSuppressPointerAfterMove()) return;
    recordAtlasEvent('paneClick');
    setHoveredId((current) => (current === null ? current : null));
    setRailHoveredId((current) => (current === null ? current : null));
    setPinnedId((current) => (current === null ? current : null));
    setSelectedEdgeIdx((current) => (current === null ? current : null));
    setSelectedEdgeSource((current) => (current === 'none' ? current : 'none'));
  }, [shouldSuppressPointerAfterMove]);
  const onReactFlowPaneContextMenu = useCallback((event: ReactMouseEvent) => {
    event.preventDefault();
    if (shouldSuppressPointerAfterMove()) return;
    recordAtlasEvent('paneContextMenu');
    setPinnedId((current) => (current === null ? current : null));
    setSelectedEdgeIdx((current) => (current === null ? current : null));
    setSelectedEdgeSource((current) => (current === 'none' ? current : 'none'));
  }, [shouldSuppressPointerAfterMove]);

  return (
    <div
      ref={atlasRootRef}
      data-zenith-home-surface="ready"
      data-zenith-view-id="surface_atlas"
      data-zenith-view-mode="map_first"
      data-zenith-view-dominant-artifact="navigation_graph"
      data-zenith-view-region-policy={sceneRailPolicy}
      data-zenith-surface-atlas-scene-candidate={sceneRailPolicy}
      data-zenith-surface-atlas-scene-candidate-receipt={JSON.stringify(atlasSceneCandidateReceipt)}
      data-zenith-station-surface-atlas={atlasReadModelReady ? 'ready' : 'loading'}
      data-zenith-station-surface-atlas-source={atlasSource}
      data-zenith-station-surface-atlas-state={atlasReadModelState}
      data-zenith-station-surface-atlas-contract={atlasReadModelContractId}
      data-zenith-station-surface-atlas-route-ready={atlasReadModelReady ? 'true' : 'false'}
      data-zenith-station-surface-atlas-node-count={atlasReadModelNodeCount}
      data-zenith-station-surface-atlas-edge-count={atlasReadModelEdgeCount}
      data-zenith-station-surface-atlas-capture-count={atlasReadModelCaptureCount}
      data-zenith-station-surface-atlas-overlay-count={atlasReadModelOverlayCount}
      data-zenith-station-surface-atlas-drift-count={atlasReadModelDriftCount}
      data-zenith-station-surface-atlas-evidence-ref-count={atlasReadModelEvidenceRefCount}
      data-zenith-station-surface-atlas-evidence-coverage={atlasReadModelEvidenceCoverage}
      data-zenith-station-surface-atlas-fallback={readModelContract?.fallback_reason ? 'present' : 'absent'}
      data-zenith-station-surface-atlas-stale={readModelContract?.stale_reason ? 'present' : 'absent'}
      data-zenith-station-surface-atlas-invalid={readModelContract?.invalid_reason ? 'present' : 'absent'}
      data-zenith-station-surface-atlas-alive-cockpit-status={
        aliveCockpit?.status ?? (launcherError ? 'error' : launcherLoading ? 'loading' : 'empty')
      }
      data-zenith-station-surface-atlas-alive-cockpit-row-count={aliveCockpit?.rows.length ?? 0}
      data-zenith-surface-atlas-pathway-audit-status={pathwayAuditStatus}
      data-zenith-surface-atlas-pathway-edge-count={pathwayEdgeCount}
      data-zenith-surface-atlas-pathway-explicit-count={pathwayExplicitCount}
      data-zenith-surface-atlas-pathway-derived-count={pathwayDerivedCount}
      data-zenith-surface-atlas-pathway-zero-substantive-count={pathwayZeroSubstantiveCount}
      data-zenith-atlas-focus={focus.mode}
      data-zenith-atlas-selected={focusId ?? 'none'}
      data-zenith-atlas-pinned={pinnedId ?? 'none'}
      data-zenith-atlas-density={densityMode}
      data-zenith-atlas-group={activeGroup}
      data-zenith-atlas-brush={relationBrush.mode}
      data-zenith-atlas-brush-neighbor={
        relationBrush.mode === 'connected_row' ? relationBrush.neighborId : 'none'
      }
      data-zenith-atlas-brush-relation={
        relationBrush.mode === 'connected_row' ? relationBrush.relation : 'none'
      }
      // Wave 24 — Relation Audition receipt fields. Make the dossier
      // state machine inspectable to station_render selectors and
      // downstream observers without re-deriving it from screenshots.
      // dossier-state priority: edge_focus > node_pinned > node_preview
      // (hover) > rest.
      data-zenith-atlas-dossier-state={
        selectedEdgeIdx !== null
          ? 'edge_focus'
          : pinnedId
            ? 'node_pinned'
            : hoveredId
              ? 'node_preview'
              : 'rest'
      }
      data-zenith-atlas-selected-edge={selectedEdgeKey ?? 'none'}
      data-zenith-atlas-edge-total-count={edges.length}
      data-zenith-atlas-edge-visible-count={rfEdges.length}
      // Wave 12 — relation layer receipts. corridor-visible-count names the
      // aggregate group-pair rollups currently painted; relation-layer is
      // the high-level grammar (aggregate|skeleton|capture|focus) the
      // operator should expect from the canvas.
      data-zenith-atlas-corridor-total-count={groupFlows.length}
      data-zenith-atlas-corridor-visible-count={corridorCanvasEdgeCount}
      data-zenith-atlas-relation-layer={relationLayer}
      data-zenith-atlas-layout-receipt={JSON.stringify(layoutReceipt)}
      // Wave SFA-1 — Station Atlas Edge Grammar Unification receipts.
      // Shape A+: aggregate corridors moved to the right-rail Group flows
      // panel; membership relations fold to rails/columns instead of
      // competing as canvas pathway edges. canvas-edge-role is the single-
      // grammar invariant: a line on the canvas is always a pathway, or
      // there is no line. corridor-canvas-count is 0 by invariant.
      // Per cap_quick_atlas_edge_mode_incoherence_corridor_lin_56b4ec4c5e64.
      data-zenith-surface-atlas-edge-grammar="ready"
      data-zenith-surface-atlas-edge-grammar-contract={edgeGrammarContract}
      data-zenith-surface-atlas-edge-grammar-contract-source={edgeGrammarContractSource}
      data-zenith-surface-atlas-presentation-role-source={presentationRoleSource}
      data-zenith-surface-atlas-group-flow-source={groupFlowSource}
      data-zenith-surface-atlas-canvas-edge-role={rfEdges.length === 0 ? 'none' : 'pathway'}
      data-zenith-surface-atlas-corridor-canvas-count={corridorCanvasEdgeCount}
      data-zenith-surface-atlas-group-flow-rail={groupFlows.length > 0 ? 'ready' : 'empty'}
      data-zenith-surface-atlas-group-flow-rail-count={groupFlows.length}
      data-zenith-surface-atlas-membership-folded="ready"
      data-zenith-surface-atlas-membership-globally-folded="ready"
      data-zenith-surface-atlas-relation-explainability={relationExplainabilityState}
      data-zenith-surface-atlas-edge-explainability-contract={edgeExplainabilityContract}
      data-zenith-surface-atlas-relation-summary-source={relationSummarySource}
      data-zenith-surface-atlas-relation-summary-count={relationSummary.length}
      data-zenith-surface-atlas-group-flow-drillthrough={
        selectedGroupFlow !== null && Array.isArray(selectedGroupFlow.sample_edges) ? 'ready' : 'empty'
      }
      data-zenith-surface-atlas-addressability={addressabilityState}
      data-zenith-surface-atlas-addressability-contract={edgeAddressabilityContract}
      data-zenith-surface-atlas-relation-selection={effectiveRelationSelection}
      data-zenith-surface-atlas-selected-relation={selectedRelationResolvedKey ?? 'none'}
      data-zenith-surface-atlas-group-flow-selection={effectiveGroupFlowSelection}
      data-zenith-surface-atlas-selected-group-flow={selectedGroupFlowResolvedKey ?? 'none'}
	      data-zenith-surface-atlas-edge-selection={effectiveEdgeSelection}
	      data-zenith-surface-atlas-selected-edge-key={selectedEdgeKey ?? 'none'}
	      data-zenith-surface-atlas-selected-edge-key-source={selectedEdgeKeySource}
	      data-zenith-surface-atlas-edge-inspector={selectedEdgeIdx !== null ? 'ready' : 'idle'}
	      data-zenith-surface-atlas-coordination={
	        coordinationContext.active || addressabilityState === 'ready' ? 'ready' : 'idle'
	      }
	      data-zenith-surface-atlas-coordination-contract={EDGE_COORDINATION_CONTRACT}
	      data-zenith-surface-atlas-coordination-mode={coordinationContext.mode}
	      data-zenith-surface-atlas-selected-relation-role={selectedRelationRole}
	      data-zenith-surface-atlas-selected-relation-role-source={
	        selectedRelation ? 'backend' : 'unavailable'
	      }
	      data-zenith-surface-atlas-selected-edge-visible={
	        coordinationContext.selectedEdgeVisible ? 'ready' : 'idle'
	      }
	      data-zenith-surface-atlas-selected-edge-endpoints={
	        coordinationContext.selectedEdgeEndpointsReady ? 'ready' : 'idle'
	      }
	      data-zenith-surface-atlas-selected-relation-edge-count={coordinationContext.relationEdgeIdxSet.size}
	      data-zenith-surface-atlas-selected-group-flow-edge-count={coordinationContext.groupFlowEdgeIdxSet.size}
	      data-zenith-surface-atlas-unrelated-edge-demotion={
	        coordinationContext.unrelatedEdgeDemotionReady ? 'ready' : 'idle'
	      }
	      data-zenith-surface-atlas-membership-selection={coordinationContext.membershipSelection}
	      data-zenith-surface-atlas-membership-canvas-edge-count={
	        coordinationContext.membershipCanvasEdgeCount
	      }
	      data-zenith-surface-atlas-membership-selection-folded={
	        coordinationContext.membershipSelectionFolded
	          ? 'ready'
	          : coordinationContext.membershipSelectionActive
	            ? 'missing'
	            : 'idle'
	      }
	      data-zenith-surface-atlas-membership-selection-rail-context={
	        coordinationContext.membershipSelectionContextReady
	          ? 'ready'
	          : coordinationContext.membershipSelectionActive
	            ? 'missing'
	            : 'idle'
	      }
	      data-zenith-surface-atlas-fallback-selection={
	        coordinationContext.fallbackSelectionActive
	          ? 'active'
	          : fallbackRelationAvailable
	            ? 'inactive'
	            : 'unavailable'
	      }
      data-zenith-surface-atlas-density-mode={densityMode}
      data-zenith-surface-atlas-moving={viewportMovingRef.current ? 'true' : 'false'}
      data-zenith-surface-atlas-search-deferred={deferredSearch !== search ? 'true' : 'false'}
      data-zenith-surface-atlas-perf-receipt={JSON.stringify(perfReceipt)}
      className="relative grid h-full w-full grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden bg-[var(--zenith-bg)] text-[var(--zenith-text)]"
      style={{
        backgroundImage:
          'radial-gradient(ellipse 58% 34% at 14% -10%, rgba(123, 199, 142, 0.06), transparent 64%), radial-gradient(ellipse 62% 50% at 84% -8%, rgba(199, 176, 106, 0.06), transparent 68%), linear-gradient(180deg, #050805 0%, #060a06 60%, #020402 100%)',
      }}
    >
      <ShellHeader
        totalViews={views.length}
        totalEdges={edges.length}
        capturedCount={capturedCount}
        legacyCount={legacyCount}
        pathwayEdgeCount={pathwayEdgeCount}
        pathwayAuditStatus={pathwayAuditStatus}
        pathwayZeroSubstantiveCount={pathwayZeroSubstantiveCount}
        search={search}
        setSearch={onSetSearch}
        onRefresh={onRefresh}
        densityMode={densityMode}
        setDensityMode={setDensityMode}
      />

      <main
        className="relative grid min-h-0 overflow-hidden bg-white/[0.035]"
        style={{
          // Wave 22 Atlas Relational Dossier Pass
          // (UI-Atlas-Relational-Dossier-Pass-006): the right inspector
          // column carries map posture + interaction grammar when the
          // operator wants substrate signal, but the operator can also
          // collapse it to a thin reopen handle so the canvas reads
          // full-width when the rail is in the way. Hide-rail control
          // lives on the DetailPanel header and on Escape escalation.
          gridTemplateColumns: graphFirstDrawersActive
            ? `${ATLAS_GRAPH_FIRST_DRAWER_RAIL_WIDTH}px minmax(0, 1fr) ${ATLAS_GRAPH_FIRST_DRAWER_RAIL_WIDTH}px`
            : railCollapsed
              ? '220px minmax(0, 1fr) 24px'
              : '220px minmax(0, 1fr) 300px',
          gap: '1px',
        }}
      >
        {graphFirstDrawersActive ? (
          <button
            type="button"
            onClick={() => setLeftRailDrawerOpen((current) => !current)}
            aria-label={leftRailDrawerOpen ? 'Hide categories rail' : 'Show categories rail'}
            title={leftRailDrawerOpen ? 'Hide categories rail' : 'Show categories rail'}
            className={clsx(
              'flex h-full w-full items-center justify-center border-r border-[var(--zenith-border)]/60 bg-[var(--zenith-panel-muted)] text-zenith-muted transition-colors hover:bg-white/[0.04] hover:text-zenith-soft',
              leftRailDrawerOpen && 'text-[var(--zenith-accent)]',
            )}
            data-zenith-view-region="rail"
            data-zenith-view-region-role="left_group_rail"
            data-zenith-view-region-mode="collapsed"
            data-zenith-view-region-policy={sceneRailPolicy}
          >
            <Layers size={14} />
          </button>
        ) : (
          <GroupRail views={views} activeGroup={activeGroup} setActiveGroup={onSetActiveGroup} />
        )}

        <section
          className="relative h-full min-h-0 overflow-hidden bg-[var(--zenith-bg-deep)]"
          onPointerDownCapture={onAtlasPointerDownCapture}
          onPointerUpCapture={onAtlasPointerUpCapture}
          onPointerCancelCapture={onAtlasPointerUpCapture}
          style={{
            backgroundImage:
              'radial-gradient(ellipse 62% 48% at 50% 46%, rgba(199,176,106,0.075), transparent 70%), radial-gradient(ellipse 72% 54% at 52% 54%, rgba(123,199,142,0.045), transparent 74%), radial-gradient(circle at center, rgba(255,255,255,0.035) 0 1px, transparent 1px)',
            backgroundSize: '100% 100%, 100% 100%, 28px 28px',
            backgroundPosition: 'center, center, center',
          }}
        >
          <ReactFlowProvider>
            <ReactFlow
              nodes={rfNodes}
              edges={allRfEdges}
              nodeTypes={NODE_TYPES}
              edgeTypes={EDGE_TYPES}
              fitView
              // Reduced from 0.25 → 0.08 after the layout banding fix.
              // The prior strip-shape layout needed huge padding to look
              // intentional; the banded 2-row layout has a stage-matched
              // aspect ratio and only needs a hairline gutter.
              // minZoom floor on the *fit* (distinct from the interaction
              // minZoom below): the banded layout is wide, so an unfloored
              // fitView shrinks nodes until labels are illegible ("everything
              // feels small"). Floor the rest-state fit at 0.55 (~154px cards)
              // and let the operator pan; they can still zoom out to 0.25.
              fitViewOptions={{ padding: graphFirstDrawersActive ? 0.04 : 0.08, includeHiddenNodes: true, minZoom: 0.55 }}
              minZoom={0.25}
              maxZoom={1.6}
              // The Atlas has a bounded node count; keeping all elements mounted
              // avoids ReactFlow virtualization churn and edge-label pop-in while
              // the operator pans around.
              onlyRenderVisibleElements={false}
              // Atlas is a read-only wayfinding map: operator launches views by
              // click, never edits the graph. Stripping ReactFlow's edit-mode
              // defaults removes the per-edge "Press enter or space to select…
              // delete to remove…" a11y announcement (one button per edge,
              // ~780 buttons at last count), keeps backspace from accidentally
              // deleting nodes, and drops nodes/edges out of the tab order so
              // keyboard navigation lands on the surrounding chrome instead
              // of every relation in the graph.
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
              edgesFocusable={false}
              nodesFocusable={false}
              deleteKeyCode={null}
              // Atlas v3 interaction split — Home is an app launcher.
              //   left-click            → navigate to view (enter)
              //   right-click           → pin focus (preventDefault, stay in map)
              //   hover                 → preview ego network (transient)
              //   leave node            → clear hover (pin persists)
              //   alt/meta + left-click → pin without navigating
              //   pane-click            → clear pin
              //   Escape                → clear pin (bound globally above)
              onNodeClick={onReactFlowNodeClick}
              onNodeMouseEnter={onReactFlowNodeMouseEnter}
              onNodeMouseLeave={onReactFlowNodeMouseLeave}
              onNodeContextMenu={onReactFlowNodeContextMenu}
              // Wave 22 Phase 2 — edge click toggles relation focus.
              // rfEdge ids are `e:${idx}:${source}->${target}`, so parse
              // the canonical edges-array index back out and use it to
              // key the AtlasEdge dossier in the right rail.
              onEdgeClick={onReactFlowEdgeClick}
              onPaneClick={onReactFlowPaneClick}
              onPaneContextMenu={onReactFlowPaneContextMenu}
              onMove={onViewportMove}
              onMoveStart={onViewportMoveStart}
              onMoveEnd={onViewportMoveEnd}
              proOptions={{ hideAttribution: true }}
            >
              <Background gap={32} size={1} color="rgba(255,255,255,0.05)" />
              <Controls
                position="bottom-right"
                showInteractive={false}
                style={{
                  background: 'var(--zenith-panel)',
                  border: '1px solid var(--zenith-border)',
                  borderRadius: 6,
                }}
              />
            </ReactFlow>
          </ReactFlowProvider>
        </section>

        {/* Wave 22 Atlas Relational Dossier Pass — the rail mounts the
            resting dossier (map posture, relation legend, group flows,
            interactions) or the selected-surface dossier. The operator
            can collapse the whole rail (Esc once nothing else is selected,
            or the `hide` button on the header) when it gets in the way;
            a thin reopen handle stays mounted so the toggle is reversible. */}
        {graphFirstDrawersActive ? (
          <button
            type="button"
            onClick={() => setRightRailDrawerOpen((current) => !current)}
            aria-label={rightRailDrawerOpen ? 'Hide inspector rail' : 'Show inspector rail'}
            title={rightRailDrawerOpen ? 'Hide inspector rail' : 'Show inspector rail'}
            className={clsx(
              'flex h-full w-full items-center justify-center border-l border-[var(--zenith-border)]/60 bg-[var(--zenith-panel-muted)] text-zenith-muted transition-colors hover:bg-white/[0.04] hover:text-zenith-soft',
              rightRailDrawerOpen && 'text-[var(--zenith-accent)]',
            )}
            data-zenith-view-region="rail"
            data-zenith-view-region-role="right_detail_rail"
            data-zenith-view-region-mode="collapsed"
            data-zenith-view-region-policy={sceneRailPolicy}
          >
            <Eye size={14} />
          </button>
        ) : railCollapsed ? (
          <button
            type="button"
            onClick={() => setRailCollapsed(false)}
            aria-label="Show rail"
            title="Show rail"
            className="flex h-full w-[24px] items-center justify-center border-l border-[var(--zenith-border)]/60 bg-[var(--zenith-panel-muted)] text-zenith-muted transition-colors hover:bg-white/[0.04] hover:text-zenith-soft"
            data-zenith-view-region="rail"
            data-zenith-view-region-role="right_detail_rail"
            data-zenith-view-region-mode="collapsed"
            data-zenith-view-region-policy={sceneRailPolicy}
          >
            <span className="font-mono text-[10px] tracking-[0.2em]">‹</span>
          </button>
        ) : (
          <DetailPanel
            view={selectedView}
            onOpen={onOpenRoute}
            connectedGroups={connectedGroups}
            focusMode={railFocus.mode}
            onClearPin={onClearPin}
            brush={relationBrush}
            onBrushNeighbour={onBrushNeighbour}
            onClearBrush={onClearBrush}
            mapStats={{
              views: views.length,
              edges: edges.length,
              captured: capturedCount,
              legacy: legacyCount,
              failed: failedCount,
              overlays: atlasReadModelOverlayCount,
            }}
            relationSummary={relationSummary}
            selectedRelationKey={
              effectiveRelationSelection === 'default' ? null : selectedRelationResolvedKey
            }
            onSelectRelation={onSelectRelation}
            groupFlows={groupFlows}
            selectedGroupFlow={selectedGroupFlow}
            selectedGroupFlowKey={selectedGroupFlowResolvedKey}
            onSelectGroupFlow={onSelectGroupFlow}
            selectedEdgeKey={selectedEdgeKey}
            edgeFocus={edgeFocus}
            onClearEdgeFocus={onClearEdgeFocus}
            onSelectSampleEdge={onSelectSampleEdge}
            onCollapseRail={() => setRailCollapsed(true)}
          />
        )}
        {graphFirstDrawersActive && leftRailDrawerOpen ? (
          <div
            className="absolute top-0 z-30 h-full shadow-[14px_0_30px_rgba(0,0,0,0.42)]"
            style={{
              left: ATLAS_GRAPH_FIRST_DRAWER_RAIL_WIDTH,
              width: `min(${ATLAS_GRAPH_FIRST_DRAWER_WIDTH}px, calc(100% - ${ATLAS_GRAPH_FIRST_DRAWER_RAIL_WIDTH * 2}px))`,
            }}
            data-zenith-surface-atlas-drawer="left_group_rail"
          >
            <GroupRail
              views={views}
              activeGroup={activeGroup}
              setActiveGroup={onSetActiveGroup}
              regionMode="overlay"
            />
          </div>
        ) : null}
        {graphFirstDrawersActive && rightRailDrawerOpen ? (
          <div
            className="absolute top-0 z-30 h-full shadow-[-14px_0_30px_rgba(0,0,0,0.42)]"
            style={{
              right: ATLAS_GRAPH_FIRST_DRAWER_RAIL_WIDTH,
              width: `min(${ATLAS_GRAPH_FIRST_DRAWER_WIDTH}px, calc(100% - ${ATLAS_GRAPH_FIRST_DRAWER_RAIL_WIDTH * 2}px))`,
            }}
            data-zenith-surface-atlas-drawer="right_detail_rail"
          >
            <DetailPanel
              view={selectedView}
              onOpen={onOpenRoute}
              connectedGroups={connectedGroups}
              focusMode={railFocus.mode}
              onClearPin={onClearPin}
              brush={relationBrush}
              onBrushNeighbour={onBrushNeighbour}
              onClearBrush={onClearBrush}
              mapStats={{
                views: views.length,
                edges: edges.length,
                captured: capturedCount,
                legacy: legacyCount,
                failed: failedCount,
                overlays: atlasReadModelOverlayCount,
              }}
              relationSummary={relationSummary}
              selectedRelationKey={
                effectiveRelationSelection === 'default' ? null : selectedRelationResolvedKey
              }
              onSelectRelation={onSelectRelation}
              groupFlows={groupFlows}
              selectedGroupFlow={selectedGroupFlow}
              selectedGroupFlowKey={selectedGroupFlowResolvedKey}
              onSelectGroupFlow={onSelectGroupFlow}
              selectedEdgeKey={selectedEdgeKey}
              edgeFocus={edgeFocus}
              onClearEdgeFocus={onClearEdgeFocus}
              onSelectSampleEdge={onSelectSampleEdge}
              onCollapseRail={() => setRightRailDrawerOpen(false)}
              regionMode="overlay"
            />
          </div>
        ) : null}
      </main>

      <ActionBar
        selectedView={selectedView}
        aliveCockpit={aliveCockpit}
        launcherLoading={launcherLoading}
        launcherError={launcherError}
        onOpen={() => selectedView && onOpenRoute(selectedView.entryRoute)}
        onOpenRoute={onOpenRoute}
        onRefresh={onRefresh}
        onPalette={onPalette}
        onShowLegacy={onShowLegacy}
      />
    </div>
  );
}
