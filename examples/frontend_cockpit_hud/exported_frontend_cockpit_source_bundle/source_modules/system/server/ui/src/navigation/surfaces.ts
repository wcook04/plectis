import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  Archive,
  BookOpen,
  Brain,
  CandlestickChart,
  Clock3,
  Code2,
  Compass,
  FileSearch,
  FileText,
  Flag,
  Layers,
  Network,
  Orbit,
  Package,
  Radio,
  ReceiptText,
  Route as RouteIcon,
  Settings as SettingsIcon,
  GitBranch,
  ShieldCheck,
  Wrench,
  Workflow,
  Sigma,
  Zap,
} from 'lucide-react';

export type SurfaceId =
  | 'station'
  | 'stationWorkbench'
  | 'stationLegacy'
  | 'demo'
  | 'vantage'
  | 'rootNavigator'
  | 'phase'
  | 'intelligence'
  | 'data'
  | 'financeData'
  | 'ops'
  | 'approvals'
  | 'marketFeeds'
  | 'marketIntelligence'
  | 'labOracleEvolve'
  | 'agentObservability'
  | 'metaDiagnostics'
  | 'launchpad'
  | 'missions'
  | 'control'
  | 'inspector'
  | 'timeline'
  | 'graph'
  | 'codemap'
  | 'topology'
  | 'navigation'
  | 'routes'
  | 'doctrine'
  | 'skills'
  | 'papers'
  | 'leanMathematics'
  | 'imaginations'
  | 'assimilation'
  | 'shards'
  | 'ledger'
  | 'drift'
  | 'reactions'
  | 'metabolism'
  | 'annexes'
  | 'codex'
  | 'doctrineCatalog'
  | 'docs'
  | 'tools'
  | 'acquisitions'
  | 'history'
  | 'metaMissions'
  | 'agentDiagnostics'
  | 'settings';

export type ShellSurfaceGroupId =
  | 'operate'
  | 'missions'
  | 'data'
  | 'inspect'
  | 'map'
  | 'library';
export type StationSurfaceGroupId = 'operate' | 'map' | 'knowledge';

// Navigation-plane extensions (consumed by
// tools/meta/observability/frontend_nav_graph.py). All optional — existing
// surfaces compile unchanged; unregistered fields default as documented below.
export type SurfaceKind = 'page' | 'modal' | 'drawer' | 'overlay' | 'redirect';
export type NavigationActionKind =
  | 'open_route'
  | 'open_entry_route'
  | 'station_lens_switch'
  | 'command_palette_select'
  | 'overlay_open'
  | 'drawer_open'
  | 'external_or_unavailable';
export type NavigationSafetyClass = 'read_only_navigation' | 'transient_ui_open';

export type NavigationInvocationTrigger =
  | { strategy: 'role'; role: 'button' | 'menuitem'; name: string }
  | { strategy: 'testid'; testId: string }
  | { strategy: 'data_attr'; selector: string }
  | { strategy: 'keyboard'; keys: string };

export interface NavigationInvocationContract {
  actionId: string;
  actionKind: NavigationActionKind;
  safetyClass: NavigationSafetyClass;
  trigger: NavigationInvocationTrigger;
  expected: {
    readySelector: string;
    captureSlug?: string;
    focusSelector?: string;
    focusPolicy?: 'dialog_focus_trap' | 'drawer_region' | 'none';
  };
}

export interface CulDeSacDeclaration {
  /** Why this surface is a declared terminal — surfaced to operators + AI. */
  reason: string;
}

export interface SurfaceDefinition {
  id: SurfaceId;
  route: string;
  label: string;
  purpose: string;
  icon: LucideIcon;
  keywords: string[];
  shortcut?: string;
  shellGroup?: ShellSurfaceGroupId;
  stationGroup?: StationSurfaceGroupId;
  homeTileOrder?: number;
  stationLensEligible: boolean;
  isActive: (pathname: string) => boolean;

  // --- Navigation-plane fields (optional; default documented per field). ---
  /**
   * Concrete browser route for direct navigation. Use when `route` is a
   * prefix/pattern claim rather than a directly openable URL.
   */
  entryRoute?: string;
  /**
   * Extra prefix claims over the same surface identity, typically for legacy
   * aliases that intentionally resolve into the same page surface.
   */
  routeAliases?: string[];
  /**
   * Surface kind. Default: 'page'. Overlays + modals + drawers live in
   * `overlays.ts` instead of the SURFACES array; this field is present on
   * SurfaceDefinition so both registries share one type.
   */
  kind?: SurfaceKind;
  /**
   * Explicit outbound-edge declarations beyond group-derived edges. Graph
   * extraction already derives shell-group / station-group / station-lens
   * siblings automatically; list here only the edges those tiers miss
   * (e.g. a "launchpad → ops" edge that crosses shell groups).
   */
  outboundTo?: SurfaceId[];
  /**
   * Declared cul-de-sac. If present, this surface is a deliberate terminal
   * with no outbound navigation; the reason is recorded in the navigation
   * graph and surfaced to AI packets. Unset = surface is expected to have
   * outbound edges; if the extractor finds zero, it fires a drift signal.
   */
  isCulDeSac?: CulDeSacDeclaration;
  /**
   * Binding into `tools/meta/observability/station_views.json` for
   * capture-per-view. When unset, the extractor falls back to route-match.
   */
  captureSlug?: string;
  /**
   * For overlays / modals / drawers only: which page surface hosts them.
   * Ignored on `kind: 'page'` surfaces.
   */
  overlayOf?: SurfaceId;
  /**
   * Source-backed UI traversal contract for non-route edges. This is distinct
   * from entryRoute: entryRoute opens a view directly, while invocation proves
   * a human/agent-operable control from the hosting UI state.
   */
  invocation?: NavigationInvocationContract;
  /**
   * Soft-hide from the Station Surface Atlas catalog. The route stays
   * registered and `getSurface(id)` still resolves the entry; the surface
   * is only suppressed from atlas tile rendering. Use for legacy / broken /
   * empty surfaces that we don't want to advertise in the catalog yet.
   */
  hiddenFromAtlas?: boolean;
}

export interface SurfaceGroupDefinition<Id extends string> {
  id: Id;
  label: string;
  icon: LucideIcon;
  surfaceIds: SurfaceId[];
  /**
   * Operator-job description, surfaced in Station Surface Atlas column
   * headers and similar IA wayfinding contexts. Optional so existing
   * group definitions compile unchanged.
   */
  description?: string;
}

export interface ResolvedSurfaceGroup<Id extends string> extends SurfaceGroupDefinition<Id> {
  surfaces: SurfaceDefinition[];
}

export interface SurfaceAlertLike {
  id: string;
  label: string;
  detail?: string | null;
}

function matchesExact(...paths: string[]) {
  return (pathname: string) => {
    const normalized = pathname.split(/[?#]/, 1)[0] || pathname;
    return paths.includes(normalized);
  };
}

function matchesPrefix(...prefixes: string[]) {
  return (pathname: string) => {
    const normalized = pathname.split(/[?#]/, 1)[0] || pathname;
    return prefixes.some(
      (prefix) => normalized === prefix || normalized.startsWith(`${prefix}/`),
    );
  };
}

const SURFACES: SurfaceDefinition[] = [
  {
    id: 'station',
    route: '/station',
    label: 'Station',
    purpose: 'Launcher, attention rollups, recent context, and quick jumps.',
    icon: Radio,
    keywords: ['home', 'station', 'launcher', 'attention'],
    shortcut: '1',
    shellGroup: 'operate',
    homeTileOrder: undefined,
    stationLensEligible: false,
    hiddenFromAtlas: true,
    isActive: matchesExact('/', '/station', '/world'),
  },
  {
    id: 'stationWorkbench',
    route: '/station/workbench',
    label: 'Station Workbench',
    purpose: 'Operational command-center predecessor parked behind the canonical Station Atlas.',
    icon: Wrench,
    keywords: ['station', 'workbench', 'command center', 'home command center', 'predecessor'],
    shellGroup: 'operate',
    stationGroup: 'operate',
    stationLensEligible: false,
    hiddenFromAtlas: true,
    isActive: matchesExact('/station/workbench'),
    captureSlug: 'home_surface_atlas_workbench_route',
  },
  {
    id: 'stationLegacy',
    route: '/station/legacy',
    label: 'Legacy Station',
    purpose: 'Legacy card-mosaic station home retained for comparison while /station crystallizes as the Atlas.',
    icon: Archive,
    keywords: ['station', 'legacy', 'home station', 'card mosaic', 'predecessor'],
    shellGroup: 'operate',
    stationGroup: 'operate',
    stationLensEligible: false,
    isActive: matchesExact('/station/legacy'),
  },
  {
    id: 'demo',
    route: '/demo',
    label: 'Demo',
    purpose: 'Public-safe demonstration landing and proof-spine entrypoint for the dissemination packet.',
    icon: Flag,
    keywords: ['demo', 'landing', 'public safe', 'proof spine', 'dissemination'],
    shellGroup: 'operate',
    homeTileOrder: 0.25,
    stationLensEligible: false,
    routeAliases: ['/landing', '/station/demo'],
    isActive: matchesExact('/demo', '/landing', '/station/demo'),
    outboundTo: ['launchpad', 'station'],
    captureSlug: 'demo_landing',
  },
  {
    id: 'vantage',
    route: '/station/vantage',
    label: 'Vantage',
    purpose: 'Unified comprehension surface over axioms, principles, papers, annexes, raw seed, code, and next action.',
    icon: Brain,
    keywords: ['vantage', 'comprehension', 'axioms', 'principles', 'papers', 'annexes', 'raw seed', 'github'],
    shellGroup: 'operate',
    stationGroup: 'knowledge',
    homeTileOrder: 0.5,
    stationLensEligible: true,
    routeAliases: ['/world/vantage'],
    isActive: matchesPrefix('/station/vantage', '/world/vantage'),
    captureSlug: 'vantage',
  },
  {
    id: 'rootNavigator',
    route: '/station/root-navigator',
    label: 'Root Navigator',
    purpose: 'Convergence map: axioms / principles / standards govern substrate; mechanisms / concepts / paper modules describe it. Click any layer to drill down.',
    icon: Compass,
    keywords: ['root', 'navigator', 'root navigator', 'self comprehension', 'coverage state', 'convergence map', 'branches', 'doctrine layers', 'axioms', 'principles', 'standards', 'mechanisms', 'concepts', 'paper modules', 'substrate', 'ontology'],
    shellGroup: 'map',
    stationGroup: 'knowledge',
    homeTileOrder: 0.05,
    stationLensEligible: false,
    routeAliases: ['/world/root-navigator', '/root-navigator'],
    isActive: matchesPrefix('/station/root-navigator', '/world/root-navigator', '/root-navigator'),
    captureSlug: 'root_navigator',
  },
  {
    id: 'phase',
    route: '/station/phase',
    label: 'Phase',
    purpose: 'Phase whiteboard, cycle history, and the live controller packet.',
    icon: Layers,
    keywords: ['phase', 'cycle', 'whiteboard'],
    stationGroup: 'operate',
    stationLensEligible: true,
    routeAliases: ['/world/phase'],
    isActive: matchesPrefix('/station/phase', '/world/phase'),
    captureSlug: 'phase',
  },
  {
    id: 'intelligence',
    route: '/station/intelligence',
    label: 'Intelligence',
    purpose:
      'Observation-first Intelligence/Data cockpit. v0 lenses: Markets (salience-and-evidence over market_dashboard_read_model_v0), System (active phase, work spine, drift, approvals), Runs (recent runs by kind). Situations are not recommendations; controls live in sidecars.',
    icon: Brain,
    keywords: [
      'intelligence',
      'data view',
      'data cockpit',
      'observation',
      'markets',
      'system',
      'runs',
      'situation queue',
      'evidence',
      'counterevidence',
      'validation debt',
      'lens',
      'palantir',
      'bloomberg',
    ],
    shortcut: '8',
    shellGroup: 'data',
    stationGroup: 'operate',
    homeTileOrder: 0.7,
    stationLensEligible: true,
    routeAliases: ['/station/runs', '/station/work', '/world/runs', '/world/work'],
    isActive: matchesPrefix('/station/intelligence', '/station/runs', '/station/work', '/world/runs', '/world/work'),
    captureSlug: 'intelligence',
  },
  {
    id: 'data',
    route: '/station/data',
    label: 'Data',
    purpose: 'Finance feed inspection and Derived calculator explanation surface at the legacy data route.',
    icon: CandlestickChart,
    keywords: ['data', 'finance', 'calculator', 'derived', 'explainability', 'feeds'],
    shellGroup: 'data',
    stationLensEligible: false,
    routeAliases: ['/world/data'],
    isActive: matchesPrefix('/station/data', '/world/data'),
    captureSlug: 'data',
  },
  {
    id: 'financeData',
    route: '/station/finance-data',
    label: 'Finance Data',
    purpose: 'Finance feed inspection and Derived calculator explanation surface.',
    icon: CandlestickChart,
    keywords: ['finance', 'data', 'calculator', 'derived', 'explainability', 'feeds'],
    shellGroup: 'data',
    stationGroup: 'operate',
    homeTileOrder: 0.8,
    stationLensEligible: false,
    routeAliases: ['/finance-data'],
    isActive: matchesPrefix('/station/finance-data', '/finance-data'),
    captureSlug: 'data',
  },
  {
    id: 'ops',
    route: '/station/ops',
    label: 'Ops',
    purpose: 'Backend-backed operation preview, launch, and bounded procedures.',
    icon: Orbit,
    keywords: ['ops', 'operations', 'launch', 'preview', 'procedures'],
    shortcut: '3',
    shellGroup: 'operate',
    stationGroup: 'operate',
    homeTileOrder: 2,
    stationLensEligible: true,
    routeAliases: ['/world/ops', '/station/operations', '/world/operations'],
    isActive: matchesPrefix('/station/ops', '/world/ops', '/station/operations', '/world/operations'),
  },
  {
    id: 'approvals',
    route: '/station/approvals',
    label: 'Approvals',
    purpose: 'Unified approval inbox for campaign gates, orchestration decisions, and review-only apply holds.',
    icon: Flag,
    keywords: ['approvals', 'approval inbox', 'gates', 'review', 'pending'],
    shellGroup: 'operate',
    stationGroup: 'operate',
    homeTileOrder: 2.5,
    stationLensEligible: true,
    routeAliases: ['/world/approvals'],
    isActive: matchesPrefix('/station/approvals', '/world/approvals'),
  },
  {
    id: 'marketFeeds',
    route: '/station/market-feeds',
    label: 'Market Feeds',
    purpose: 'Always-on market-clock feed bundle readiness, credential health, ticker pulses, and artifact runs.',
    icon: CandlestickChart,
    keywords: ['market', 'feeds', 'fred', 'telegram', 'open', 'close', 'feed readiness'],
    shellGroup: 'data',
    stationGroup: 'operate',
    homeTileOrder: 2.65,
    stationLensEligible: true,
    routeAliases: ['/world/market-feeds'],
    isActive: matchesPrefix('/station/market-feeds', '/world/market-feeds'),
    captureSlug: 'market_feeds',
  },
  {
    id: 'marketIntelligence',
    route: '/station/market-intelligence',
    label: 'Market Intelligence',
    purpose:
      'Operator cockpit over the market_dashboard_read_model_v0 projection: trust strip, situation queue, evidence and counterevidence, graph slice, safe drilldown, provenance, and validation debt. Situations are not recommendations.',
    icon: Brain,
    keywords: [
      'market intelligence',
      'situations',
      'situation queue',
      'evidence',
      'counterevidence',
      'drilldown',
      'validation debt',
      'dashboard read model',
      'market_dashboard_read_model_v0',
    ],
    shortcut: '2',
    shellGroup: 'data',
    stationGroup: 'operate',
    homeTileOrder: 1,
    stationLensEligible: true,
    routeAliases: ['/world/market-intelligence'],
    isActive: matchesPrefix('/station/market-intelligence', '/world/market-intelligence'),
    captureSlug: 'market_intelligence',
  },
  {
    id: 'labOracleEvolve',
    route: '/station/lab-oracle-evolve',
    label: 'Lab / Oracle',
    purpose: 'Run-pair readiness for feeds, CP2, Oracle artifacts, and Evolve gates.',
    icon: Workflow,
    keywords: ['lab', 'oracle', 'evolve', 'cp1', 'cp2', 'feed readiness', 'run pair'],
    shellGroup: 'missions',
    stationGroup: 'operate',
    homeTileOrder: 2.75,
    stationLensEligible: true,
    routeAliases: ['/world/lab-oracle-evolve'],
    isActive: matchesPrefix('/station/lab-oracle-evolve', '/world/lab-oracle-evolve'),
    captureSlug: 'lab_oracle_evolve',
  },
  {
    id: 'agentObservability',
    route: '/station/agent-observability',
    label: 'Agent Trace',
    purpose: 'Live Type A trace substrate for Claude Code app, Codex app, captures, and runtime claims.',
    icon: Activity,
    keywords: ['agent observability', 'agent trace', 'claude', 'codex', 'sessions', 'runtime', 'subagents'],
    shellGroup: 'operate',
    stationGroup: 'operate',
    homeTileOrder: 2.85,
    stationLensEligible: true,
    routeAliases: ['/world/agent-observability'],
    isActive: matchesPrefix('/station/agent-observability', '/world/agent-observability'),
    captureSlug: 'agent_observability',
  },
  {
    id: 'metaDiagnostics',
    route: '/station/meta-diagnostics',
    label: 'Meta Diagnostics',
    purpose:
      'Surface Atlas entry into the meta_diagnostics_console_projection_v1 visual proof topology: source systems, claims, evidence pressure, behavior timeline, work flow, and drilldown receipts.',
    icon: ShieldCheck,
    keywords: [
      'surface atlas',
      'meta diagnostics',
      'diagnostics',
      'visual proof topology',
      'system correlation',
      'source health',
      'agent telemetry',
      'task ledger',
      'doctrine health',
      'annex intake',
      'proof constellation',
      'evidence pressure',
    ],
    shellGroup: 'inspect',
    stationGroup: 'operate',
    homeTileOrder: 2.9,
    stationLensEligible: true,
    routeAliases: ['/world/meta-diagnostics'],
    isActive: matchesPrefix('/station/meta-diagnostics', '/world/meta-diagnostics'),
    captureSlug: 'meta_diagnostics',
  },
  {
    id: 'launchpad',
    route: '/launchpad',
    label: 'Launchpad',
    purpose: 'Live launch posture, bridge preflight, and observe-session state.',
    icon: Layers,
    keywords: ['launchpad', 'launch', 'bridge', 'observe runtime', 'preflight'],
    shortcut: '4',
    shellGroup: 'operate',
    homeTileOrder: 3,
    stationLensEligible: false,
    isActive: matchesExact('/launchpad'),
    outboundTo: ['control', 'missions', 'phase'],
    captureSlug: 'launchpad_command_center',
  },
  {
    id: 'missions',
    route: '/missions',
    label: 'Missions',
    purpose: 'Mission catalog, resume browser, and mission selection deck.',
    icon: Workflow,
    keywords: ['missions', 'mission deck', 'catalog', 'resume', 'runs'],
    shortcut: '5',
    shellGroup: 'missions',
    homeTileOrder: 4,
    stationLensEligible: false,
    isActive: matchesExact('/missions'),
    captureSlug: 'missions',
  },
  {
    id: 'control',
    route: '/control',
    entryRoute: '/control/feeds',
    label: 'Control Room',
    purpose: 'Mission execution cockpit for one mission: graph, data, contracts, configs, ignition, and bridge recovery.',
    icon: Zap,
    keywords: ['control room', 'control', 'mission cockpit', 'mission execution', 'graph', 'contracts', 'configs'],
    stationLensEligible: false,
    isActive: matchesPrefix('/control'),
    outboundTo: ['missions', 'station'],
    captureSlug: 'control_room',
  },
  {
    id: 'inspector',
    route: '/inspector',
    label: 'Inspector',
    purpose: 'Code, doctrine, artifacts, and observe/apply inspection in one place.',
    icon: FileSearch,
    keywords: ['inspector', 'files', 'artifacts', 'observe', 'apply'],
    shortcut: '6',
    shellGroup: 'inspect',
    homeTileOrder: 5,
    stationLensEligible: false,
    isActive: matchesPrefix('/inspector'),
    outboundTo: ['codemap', 'doctrine', 'tools'],
    captureSlug: 'inspector',
  },
  {
    id: 'graph',
    route: '/station/graph',
    label: 'Graph',
    purpose: 'Mission, observe, provider, and factory lanes as one runtime map.',
    icon: Network,
    keywords: ['graph', 'runtime map', 'lanes', 'system graph'],
    shellGroup: 'missions',
    stationGroup: 'map',
    homeTileOrder: 6,
    stationLensEligible: true,
    routeAliases: ['/world/graph'],
    isActive: matchesPrefix('/station/graph', '/world/graph'),
    captureSlug: 'graph',
  },
  {
    id: 'codemap',
    route: '/station/codemap',
    label: 'Code Map',
    purpose: 'Code architecture Workingness lens: bounded graph, blast radius, provenance, and proof commands.',
    icon: GitBranch,
    keywords: ['code map', 'code architecture', 'blast radius', 'workingness', 'verification'],
    shellGroup: 'map',
    stationGroup: 'map',
    stationLensEligible: true,
    routeAliases: ['/world/codemap'],
    isActive: matchesPrefix('/station/codemap', '/world/codemap'),
    captureSlug: 'codemap',
  },
  {
    id: 'topology',
    route: '/station/topology',
    label: 'Topology',
    purpose: 'Projection clusters, structural browse, and path search.',
    icon: Compass,
    keywords: ['topology', 'system view', 'clusters', 'projection'],
    shellGroup: 'map',
    stationGroup: 'map',
    stationLensEligible: true,
    routeAliases: ['/world/system-view'],
    isActive: matchesPrefix('/station/topology', '/world/system-view'),
  },
  {
    id: 'routes',
    route: '/station/routes',
    label: 'Routes',
    purpose: 'Cold-start routes, coverage pressure, and navigation-owned backlog surfaces.',
    icon: RouteIcon,
    keywords: ['routes', 'coverage', 'routing', 'backlog', 'navigation'],
    shellGroup: 'map',
    stationGroup: 'map',
    stationLensEligible: true,
    routeAliases: ['/world/routes'],
    isActive: matchesPrefix('/station/routes', '/world/routes'),
  },
  {
    id: 'navigation',
    route: '/station/navigation',
    label: 'Navigation',
    purpose: 'Wayfinding Mission Control: generated graph health, scenario suite, receipts, and capability gaps.',
    icon: Compass,
    keywords: ['navigation', 'wayfinding', 'mission control', 'scenario suite', 'receipts', 'capability matrix'],
    shellGroup: 'map',
    stationGroup: 'map',
    stationLensEligible: true,
    isActive: matchesPrefix('/station/navigation'),
    captureSlug: 'station_navigation_mission_control',
  },
  {
    id: 'doctrine',
    route: '/station/doctrine',
    label: 'Doctrine',
    purpose: 'Concepts, mechanisms, and principles with bounded drill-down.',
    icon: BookOpen,
    keywords: ['doctrine', 'principles', 'concepts', 'mechanisms'],
    shellGroup: 'map',
    stationGroup: 'knowledge',
    stationLensEligible: true,
    isActive: matchesPrefix('/station/doctrine'),
  },
  {
    id: 'skills',
    route: '/station/skills',
    label: 'Skills',
    purpose: 'Skill families, type distribution, source authority, and doctrine/standard graph links.',
    icon: Wrench,
    keywords: ['skills', 'agent skills', 'capabilities', 'standards', 'skill registry', 'doctrine edges'],
    shellGroup: 'map',
    stationGroup: 'knowledge',
    stationLensEligible: true,
    routeAliases: ['/world/skills'],
    isActive: matchesPrefix('/station/skills', '/world/skills'),
  },
  {
    id: 'papers',
    route: '/station/papers',
    label: 'Papers',
    purpose: 'Paper-module ontology, freshness posture, and boundary-pressure browse.',
    icon: FileText,
    keywords: ['papers', 'paper modules', 'ontology', 'freshness', 'boundaries'],
    shellGroup: 'map',
    stationGroup: 'knowledge',
    stationLensEligible: true,
    routeAliases: ['/world/papers'],
    isActive: matchesPrefix('/station/papers', '/world/papers'),
  },
  {
    id: 'leanMathematics',
    route: '/station/lean-mathematics',
    label: 'Lean Mathematics',
    purpose:
      'Visual atlas over the Lean / formal-math microcosm: source-anchored declaration graph, proof obligations, receipt timeline, capability rows, validation commands, and boundary claims. Read-only projection over /api/world-model/lean-mathematics.',
    icon: Sigma,
    keywords: [
      'lean',
      'lean mathematics',
      'formal math',
      'proof',
      'proofs',
      'mathlib',
      'declarations',
      'obligations',
      'erdos',
      'receipts',
      'theorem',
      'theorem proving',
      'microcosm',
    ],
    shellGroup: 'map',
    stationGroup: 'knowledge',
    homeTileOrder: 0.6,
    stationLensEligible: false,
    routeAliases: ['/world/lean-mathematics', '/lean-mathematics', '/station/lean'],
    isActive: matchesPrefix(
      '/station/lean-mathematics',
      '/world/lean-mathematics',
      '/lean-mathematics',
      '/station/lean',
    ),
    captureSlug: 'lean_mathematics',
  },
  {
    id: 'imaginations',
    route: '/station/imaginations',
    label: 'Imaginations',
    purpose: 'Vivid future-state affordance scenes with provenance and migration lineage (std_imagination_v1, field-set frozen).',
    icon: Orbit,
    keywords: [
      'imaginations',
      'imagination',
      'imn',
      'counterfactual',
      'affordance',
      'scene',
      'lineage',
      'migration',
      'teleological',
      'voice anchor',
    ],
    shellGroup: 'map',
    stationGroup: 'knowledge',
    stationLensEligible: true,
    isActive: matchesPrefix('/station/imaginations'),
    captureSlug: 'imaginations',
  },
  {
    id: 'assimilation',
    route: '/station/raw-seed-assimilation',
    label: 'Assimilation',
    purpose: 'Raw-seed assimilation workbench: shard clusters, bundles, doctrine triples, and implementation gaps.',
    captureSlug: 'assimilation',
    icon: Layers,
    keywords: ['assimilation', 'raw seed', 'alchemy', 'clusters', 'implementation gaps'],
    shellGroup: 'map',
    stationGroup: 'knowledge',
    stationLensEligible: true,
    routeAliases: ['/station/assimilation', '/world/assimilation', '/world/raw-seed-assimilation'],
    isActive: matchesPrefix(
      '/station/raw-seed-assimilation',
      '/station/assimilation',
      '/world/assimilation',
      '/world/raw-seed-assimilation',
    ),
  },
  {
    id: 'shards',
    route: '/station/shards',
    label: 'Shards',
    purpose: 'Read-only shard browser: search, provenance, and neighborhood navigator for raw-seed deep-links.',
    icon: GitBranch,
    keywords: ['shards', 'raw seed', 'provenance', 'groups', 'query'],
    shellGroup: 'map',
    stationGroup: 'knowledge',
    stationLensEligible: true,
    routeAliases: ['/world/shards'],
    isActive: matchesPrefix('/station/shards', '/world/shards'),
  },
  {
    id: 'ledger',
    route: '/station/ledger',
    label: 'Ledger',
    purpose: 'Event-sourced work memory: open work, closures, stale sessions, and supersession chains.',
    icon: ReceiptText,
    keywords: ['ledger', 'work memory', 'todos', 'handoffs', 'stale sessions'],
    shellGroup: 'map',
    stationGroup: 'operate',
    stationLensEligible: true,
    routeAliases: ['/world/ledger'],
    isActive: matchesPrefix('/station/ledger', '/world/ledger'),
  },
  {
    id: 'timeline',
    route: '/station/timeline',
    label: 'Timeline',
    purpose: 'Reserved: recursive execution timeline (phase → subphase → wave → worker). Placeholder surface — no live feed until the execution-graph backend ships.',
    icon: Clock3,
    keywords: ['timeline', 'execution', 'phase', 'subphase', 'wave', 'worker'],
    shellGroup: 'map',
    stationGroup: 'operate',
    stationLensEligible: true,
    routeAliases: ['/world/timeline'],
    isActive: matchesPrefix('/station/timeline', '/world/timeline'),
    captureSlug: 'timeline',
  },
  {
    id: 'drift',
    route: '/station/drift',
    label: 'Drift',
    purpose: 'Freshness, hologram drift, and rebuild pressure.',
    icon: Flag,
    keywords: ['drift', 'freshness', 'stale', 'hologram'],
    shellGroup: 'inspect',
    stationGroup: 'knowledge',
    stationLensEligible: true,
    isActive: matchesPrefix('/station/drift'),
  },
  {
    id: 'reactions',
    route: '/station/reactions',
    label: 'Reactions',
    purpose: 'Engine ledger, wake barriers, and runtime reaction state.',
    icon: Zap,
    keywords: ['reactions', 'wake barriers', 'engine', 'ledger'],
    shellGroup: 'map',
    stationGroup: 'operate',
    stationLensEligible: true,
    routeAliases: ['/world/reactions'],
    isActive: matchesPrefix('/station/reactions', '/world/reactions'),
  },
  {
    id: 'metabolism',
    route: '/station/metabolism',
    label: 'Metabolism',
    purpose:
      'Daemon cold-start reconciliation findings, queue health, and repair audit trail (pri_119).',
    icon: Activity,
    keywords: [
      'metabolism',
      'metabolismd',
      'reconciliation',
      'reconcile',
      'daemon',
      'queue health',
      'orphaned',
      'pri_119',
    ],
    shellGroup: 'inspect',
    stationGroup: 'operate',
    stationLensEligible: true,
    routeAliases: ['/world/metabolism'],
    isActive: matchesPrefix('/station/metabolism', '/world/metabolism'),
  },
  {
    id: 'annexes',
    route: '/annexes',
    label: 'Annexes',
    purpose: 'External substrate imports, routing context, and annex note coverage.',
    icon: Package,
    keywords: ['annexes', 'annex', 'imports', 'external docs', 'library'],
    shellGroup: 'library',
    homeTileOrder: 7,
    stationLensEligible: false,
    isActive: matchesPrefix('/annexes'),
    outboundTo: ['docs', 'doctrine'],
    captureSlug: 'annexes',
  },
  {
    id: 'codex',
    route: '/agent-diagnostics',
    entryRoute: '/agent-diagnostics?rawTrace=1',
    label: 'Codex Ops',
    purpose: 'Codex IDE/provider context: .codex roles, host-agent wiring, raw traces, and drift signals.',
    icon: Activity,
    keywords: ['codex', 'codex roles', '.codex', 'ide', 'provider context', 'chatgpt ide', 'agent diagnostics', 'raw trace'],
    shellGroup: 'inspect',
    // Raw traces are now a drilldown from the read-only SystemLens operations
    // surface; legacy /agent-diagnostics URLs land there.
    kind: 'drawer',
    overlayOf: 'agentDiagnostics',
    stationLensEligible: false,
    hiddenFromAtlas: true,
    isActive: () => false,
    outboundTo: ['agentDiagnostics'],
    captureSlug: 'agent_diagnostics',
  },
  {
    id: 'doctrineCatalog',
    route: '/codex',
    label: 'Doctrine Catalog',
    purpose: 'Doctrine concepts, mechanisms, standards, and system-map browse.',
    icon: Code2,
    keywords: ['doctrine catalog', 'doctrine', 'standards', 'system map', 'mechanisms', 'concepts'],
    shellGroup: 'map',
    stationLensEligible: false,
    routeAliases: ['/station/doctrine-catalog', '/world/doctrine-catalog', '/doctrine-catalog'],
    isActive: matchesPrefix('/codex', '/station/doctrine-catalog', '/world/doctrine-catalog', '/doctrine-catalog'),
    outboundTo: ['doctrine', 'papers', 'docs'],
    captureSlug: 'codex',
  },
  {
    id: 'docs',
    route: '/docs',
    label: 'Docs',
    purpose: 'Documentation plane browser for core docs and annex docs.',
    icon: FileText,
    keywords: ['docs', 'documentation', 'runbooks', 'instructions'],
    shellGroup: 'inspect',
    stationLensEligible: false,
    isActive: matchesPrefix('/docs'),
    outboundTo: ['doctrine', 'annexes', 'papers'],
  },
  {
    id: 'tools',
    route: '/tools',
    label: 'Tools',
    purpose: 'Grouped tool inventory for packages, modules, and larger subsystem surfaces.',
    icon: Wrench,
    keywords: ['tools', 'tool inventory', 'packages', 'modules', 'subsystems'],
    shellGroup: 'library',
    stationLensEligible: false,
    hiddenFromAtlas: true,
    isActive: matchesPrefix('/tools'),
    outboundTo: ['inspector', 'agentDiagnostics', 'codemap'],
    captureSlug: 'tools',
  },
  {
    id: 'acquisitions',
    route: '/station/acquisitions',
    label: 'Receipts',
    purpose: 'Reference-acquisition receipts and annex inflow provenance.',
    icon: ReceiptText,
    keywords: ['receipts', 'acquisitions', 'reference acquisitions', 'inflow'],
    shellGroup: 'library',
    stationGroup: 'knowledge',
    stationLensEligible: true,
    hiddenFromAtlas: true,
    captureSlug: 'acquisitions',
    routeAliases: ['/world/acquisitions'],
    isActive: matchesPrefix('/station/acquisitions', '/world/acquisitions'),
  },
  {
    id: 'history',
    route: '/history',
    label: 'Archives',
    purpose: 'Historical runs, evidence, and replay.',
    icon: Archive,
    keywords: ['archives', 'history', 'runs', 'evidence'],
    shortcut: '7',
    shellGroup: 'library',
    stationLensEligible: false,
    isActive: matchesPrefix('/history'),
    outboundTo: ['timeline', 'missions'],
  },
  {
    id: 'metaMissions',
    route: '/meta-missions',
    label: 'Meta-missions',
    purpose: 'Registry-backed mission careers, metrics, and longer-running watch surfaces.',
    icon: Workflow,
    keywords: ['meta missions', 'careers', 'registry', 'metrics'],
    shellGroup: 'missions',
    stationLensEligible: false,
    isActive: matchesPrefix('/meta-missions'),
    outboundTo: ['missions', 'phase', 'control'],
  },
  {
    id: 'agentDiagnostics',
    route: '/station/intelligence?lens=system',
    routeAliases: ['/agent-diagnostics', '/cockpit'],
    label: 'System ops',
    purpose: 'Read-only operations topology in SystemLens. Legacy Cockpit and agent-diagnostics URLs redirect here; backend control affordances stay outside the frontend.',
    icon: Activity,
    keywords: [
      'cockpit',
      'agent operations',
      'attention',
      'workstreams',
      'severity',
      'agent diagnostics',
      'agents',
      'dotfiles',
      '.claude',
      '.codex',
      'hooks',
      'permissions',
      'personas',
      'codex roles',
      'host agent',
      'wiring',
    ],
    shellGroup: 'inspect',
    stationLensEligible: false,
    isActive: matchesPrefix('/station/intelligence', '/agent-diagnostics', '/cockpit'),
    outboundTo: ['phase', 'agentObservability', 'ledger'],
    captureSlug: 'agent_diagnostics',
  },
  {
    id: 'settings',
    route: '/settings',
    label: 'Settings',
    purpose: 'Config Control Plane: federated authority registry, effective traces, diagnostics, and scoped system/UI tuning.',
    icon: SettingsIcon,
    keywords: ['settings', 'config', 'preferences', 'tuner', 'master config', 'config authority', 'effective config', 'config_ref'],
    stationLensEligible: false,
    routeAliases: ['/station/settings'],
    isActive: matchesPrefix('/settings', '/station/settings'),
    outboundTo: ['station'],
    captureSlug: 'settings',
  },
];

const SURFACE_BY_ID = new Map<SurfaceId, SurfaceDefinition>(
  SURFACES.map((surface) => [surface.id, surface]),
);

const SHELL_GROUPS: SurfaceGroupDefinition<ShellSurfaceGroupId>[] = [
  {
    id: 'operate',
    label: 'Operate',
    icon: Orbit,
    description: 'Run, decide, launch, approve, and drive runtime forward.',
    surfaceIds: ['stationLegacy', 'demo', 'vantage', 'ops', 'approvals', 'agentObservability', 'launchpad'],
  },
  {
    id: 'missions',
    label: 'Missions',
    icon: Workflow,
    description: 'Mission catalog, careers, runtime graph, and lab/oracle run-pair lanes.',
    surfaceIds: ['missions', 'metaMissions', 'labOracleEvolve', 'graph'],
  },
  {
    id: 'data',
    label: 'Data',
    icon: CandlestickChart,
    description: 'Market feeds, finance intelligence cockpit, and data drill-down.',
    surfaceIds: ['marketIntelligence', 'marketFeeds', 'data'],
  },
  {
    id: 'inspect',
    label: 'Inspect',
    icon: FileSearch,
    description: 'Read live data, artifacts, records, diffs, and diagnostics.',
    surfaceIds: ['inspector', 'drift', 'docs', 'codex', 'agentDiagnostics', 'metabolism', 'metaDiagnostics'],
  },
  {
    id: 'map',
    label: 'Map',
    icon: Network,
    description: 'Understand topology, doctrine, routes, phases, and relationships.',
    surfaceIds: ['rootNavigator', 'codemap', 'topology', 'routes', 'navigation', 'doctrine', 'skills', 'papers', 'leanMathematics', 'doctrineCatalog', 'assimilation', 'ledger', 'timeline', 'reactions'],
  },
  {
    id: 'library',
    label: 'Library',
    icon: Package,
    description: 'Browse durable knowledge: docs, codex, annexes, papers.',
    surfaceIds: ['annexes', 'history'],
  },
];

const STATION_GROUPS: SurfaceGroupDefinition<StationSurfaceGroupId>[] = [
  {
    id: 'operate',
    label: 'Operate',
    icon: Orbit,
    surfaceIds: ['stationWorkbench', 'stationLegacy', 'phase', 'ops', 'approvals', 'marketFeeds', 'marketIntelligence', 'labOracleEvolve', 'agentObservability', 'metaDiagnostics', 'ledger', 'timeline', 'reactions', 'metabolism'],
  },
  {
    id: 'map',
    label: 'Map',
    icon: Network,
    surfaceIds: ['graph', 'codemap', 'topology', 'routes', 'navigation'],
  },
  {
    id: 'knowledge',
    label: 'Knowledge',
    icon: BookOpen,
    surfaceIds: ['rootNavigator', 'vantage', 'doctrine', 'skills', 'papers', 'leanMathematics', 'assimilation', 'shards', 'drift', 'acquisitions'],
  },
];

function resolveGroups<Id extends string>(
  groups: SurfaceGroupDefinition<Id>[],
): ResolvedSurfaceGroup<Id>[] {
  return groups.map((group) => ({
    ...group,
    surfaces: group.surfaceIds.map((surfaceId) => getSurface(surfaceId)),
  }));
}

export function getSurface(id: SurfaceId): SurfaceDefinition {
  const surface = SURFACE_BY_ID.get(id);
  if (!surface) {
    throw new Error(`Unknown surface: ${id}`);
  }
  return surface;
}

export function getSurfaceEntryRoute(surface: SurfaceDefinition | SurfaceId): string | null {
  const resolved = typeof surface === 'string' ? getSurface(surface) : surface;
  return resolved.entryRoute ?? resolved.route ?? null;
}

export function getSurfaceRouteClaims(surface: SurfaceDefinition | SurfaceId): string[] {
  const resolved = typeof surface === 'string' ? getSurface(surface) : surface;
  return [resolved.route, ...(resolved.routeAliases ?? [])].filter(
    (value): value is string => typeof value === 'string' && value.length > 0,
  );
}

export function getAllSurfaces(): SurfaceDefinition[] {
  return SURFACES.slice();
}

export function getShellSurfaceGroups(): ResolvedSurfaceGroup<ShellSurfaceGroupId>[] {
  return resolveGroups(SHELL_GROUPS);
}

export function getStationSurfaceGroups(): ResolvedSurfaceGroup<StationSurfaceGroupId>[] {
  return resolveGroups(STATION_GROUPS);
}

export function getHomeTileSurfaces(): SurfaceDefinition[] {
  return SURFACES.filter((surface) => surface.homeTileOrder != null).sort(
    (left, right) => (left.homeTileOrder ?? 0) - (right.homeTileOrder ?? 0),
  );
}

export function matchSurfaceByPath(pathname: string): SurfaceDefinition | null {
  for (const surface of SURFACES) {
    if (surface.isActive(pathname)) {
      return surface;
    }
  }
  return null;
}

export function getSurfaceLabelForRoute(route: string): string {
  const exact = SURFACES.find((surface) => surface.route === route);
  if (exact) return exact.label;
  const matched = matchSurfaceByPath(route);
  if (matched) return matched.label;
  const tail = route.split('/').filter(Boolean).pop() ?? route;
  return tail.replace(/-/g, ' ').replace(/^\w/, (value) => value.toUpperCase());
}

export function resolveSurfaceFromAlert(alert: SurfaceAlertLike): SurfaceDefinition {
  const id = String(alert.id || '').toLowerCase();
  const text = `${alert.label || ''} ${alert.detail || ''}`.toLowerCase();

  if (
    id.includes('mission') ||
    text.includes('mission deck') ||
    text.includes('blocked mission')
  ) {
    return getSurface('missions');
  }

  if (
    id.includes('work_ledger') ||
    id.includes('ledger') ||
    text.includes('work ledger') ||
    text.includes('work-ledger') ||
    text.includes('stale session') ||
    text.includes('missing append')
  ) {
    return getSurface('ledger');
  }

  if (
    id.includes('approval') ||
    text.includes('approval') ||
    text.includes('approve') ||
    text.includes('review only')
  ) {
    return getSurface('approvals');
  }

  if (
    id.includes('gate') ||
    id.includes('orchestration') ||
    text.includes('gate') ||
    text.includes('manual review') ||
    text.includes('review packet')
  ) {
    return getSurface('approvals');
  }

  if (
    id.includes('bridge') ||
    id.includes('observe') ||
    id.includes('overnight')
  ) {
    return getSurface('launchpad');
  }

  if (
    id.includes('annex') ||
    text.includes('annex')
  ) {
    return getSurface('annexes');
  }

  if (
    id.includes('doc') ||
    text.includes('documentation') ||
    text.includes('runbook')
  ) {
    return getSurface('docs');
  }

  if (
    id.includes('routing') ||
    id.includes('raw_seed') ||
    text.includes('raw-seed') ||
    text.includes('coverage') ||
    text.includes('route')
  ) {
    return getSurface('routes');
  }

  return getSurface('ops');
}

function tokenizeSurfaceText(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length > 0);
}

const ROUTE_RESOLUTION_STOPWORDS = new Set([
  'route',
  'routes',
  'tool',
  'tools',
  'view',
  'views',
  'page',
  'pages',
]);

function scoreSurfaceFromTokens(surface: SurfaceDefinition, tokens: Set<string>, rawText: string): number {
  let score = 0;
  const idTokens = tokenizeSurfaceText(surface.id);
  const labelTokens = tokenizeSurfaceText(surface.label);
  const routeTokens = [
    ...tokenizeSurfaceText(surface.route),
    ...tokenizeSurfaceText(surface.entryRoute ?? ''),
    ...(surface.routeAliases?.flatMap((alias) => tokenizeSurfaceText(alias)) ?? []),
  ];
  const keywordTokens = surface.keywords.flatMap((keyword) => tokenizeSurfaceText(keyword));
  const idHasDistinctSignal = idTokens.some((token) => !ROUTE_RESOLUTION_STOPWORDS.has(token));
  const labelHasDistinctSignal = labelTokens.some(
    (token) => !ROUTE_RESOLUTION_STOPWORDS.has(token),
  );

  for (const token of tokens) {
    if (ROUTE_RESOLUTION_STOPWORDS.has(token)) continue;
    if (idTokens.includes(token)) score += 6;
    if (labelTokens.includes(token)) score += 5;
    if (token.length > 2 && routeTokens.includes(token)) score += 3;
    if (token.length > 3 && keywordTokens.includes(token)) score += 2;
  }

  for (const routeClaim of [surface.route, surface.entryRoute, ...(surface.routeAliases ?? [])]) {
    if (routeClaim && rawText.includes(routeClaim.toLowerCase())) score += 8;
  }
  if (labelHasDistinctSignal && rawText.includes(surface.label.toLowerCase())) score += 5;
  if (idHasDistinctSignal && rawText.includes(surface.id.toLowerCase())) score += 4;

  return score;
}

function surfaceFromKnownRoute(path: string): SurfaceDefinition | null {
  const exact = SURFACES.find((surface) => surface.route === path);
  if (exact) return exact;
  return matchSurfaceByPath(path);
}

export function resolveSurfaceFromRouteCard(route: Record<string, unknown>): SurfaceDefinition | null {
  const directRouteKeys = ['surface_route', 'route_path', 'ui_route', 'route'];
  for (const key of directRouteKeys) {
    const value = route[key];
    if (typeof value === 'string' && value.startsWith('/')) {
      const directSurface = surfaceFromKnownRoute(value);
      if (directSurface) return directSurface;
    }
  }

  const rawParts = [
    route.situation_id,
    route.id,
    route.set,
    route.label,
    route.next,
    route.canonical_next_read,
    route.minimum_read_set_id,
    route.route_command,
    route.surface_label,
  ]
    .filter((value): value is string => typeof value === 'string' && value.trim().length > 0);

  if (rawParts.length === 0) return null;

  const rawText = rawParts.join(' ').toLowerCase();
  if (rawText.includes('--paper-module') || rawText.includes('paper modules')) {
    return getSurface('papers');
  }
  if (
    rawText.includes('codex/doctrine/') ||
    rawText.includes('--paper-lattice') ||
    rawText.includes('doctrine catalog')
  ) {
    return getSurface('doctrineCatalog');
  }
  if (rawText.includes('--docs-route') || rawText.includes('documentation plane')) {
    return getSurface('docs');
  }
  const tokens = new Set(tokenizeSurfaceText(rawText));

  let bestSurface: SurfaceDefinition | null = null;
  let bestScore = 0;
  for (const surface of SURFACES) {
    const score = scoreSurfaceFromTokens(surface, tokens, rawText);
    if (score > bestScore) {
      bestSurface = surface;
      bestScore = score;
    }
  }

  return bestScore >= 6 ? bestSurface : null;
}
