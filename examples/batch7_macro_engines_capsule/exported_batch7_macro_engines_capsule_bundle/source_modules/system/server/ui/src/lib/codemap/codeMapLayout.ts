import * as dagre from 'dagre';
import type { Edge, Node } from 'reactflow';
import { overlayCount, pathLeaf } from './codeMapSelectors';
import { buildClusterFlowModel } from './codeMapClusterFlow';
import { buildPanoramaModel } from './codeMapPanorama';
import {
  buildFocusGraphSelection,
  isFocusRelevantEdge,
  isIncidentEdge,
} from './codeMapFocus';
import {
  allRepresentativeFiles,
  buildLayerGroups,
  classifyEdge,
  deriveFileImportance,
} from './codeMapGraphModel';
import { edgeClassTone, edgeStroke, nodeDimensions } from './codeMapStyle';
import { rectsOverlap } from './geometryRelax';
import type {
  ClusterFlowNode,
  ClusterFlowSummary,
  ClusterFlowZone,
  ClusterFlowZoneEdge,
  CodeMapConnection,
  CodeMapFile,
  CodeMapMode,
  CodeMapPacket,
  EdgeClass,
  EgoFocusSummary,
  FocusCollapsedGroup,
  FocusModel,
  FocusRole,
  NodeSize,
  OverlayToggleId,
  PanoramaDistrict,
  PanoramaLens,
  PanoramaSelectionSummary,
  PanoramaSummary,
} from './types';

const FOCUS_NODE_LIMIT = 160;

// Use the largest possible card size for ego-graph collision math; hub cards
// can appear inside focus when the selected file scores as a hub.
const EGO_CARD = nodeDimensions('hub');
const EGO_ROW_GAP_Y = EGO_CARD.height + 28;

// --- Center-orbit (focus mode) radial constants ---------------------------
// Selected card is pinned at the orbit origin; neighbors sit in deterministic
// semantic angular bands (relation -> sector) packed into concentric rings.
// Screen-up convention: 90deg is up, 270deg is down; the cartesian conversion
// uses cy = -R*sin(theta) because ReactFlow's y axis grows downward.
const ORBIT_DEG = Math.PI / 180;
const ORBIT_R_BASE = Math.max(EGO_CARD.width, EGO_CARD.height) * 1.15; // clears the pinned center hub
const ORBIT_RING_STEP = EGO_ROW_GAP_Y; // radial gap between concentric rings (> card height)
const ORBIT_SLOT = EGO_CARD.width + 36; // conservative tangential slot per card within a ring
const ORBIT_ANGLE_STEP = 3 * ORBIT_DEG; // along-arc nudge during the relax pass
const ORBIT_RELAX_PASSES = 24; // bounded, fixed (no convergence-based early-exit that could vary)
const ORBIT_LEFT_PAD = 48;
type OrbitBand = { lo: number; hi: number; center: number };
// Relation class -> fixed angular band so a relation always occupies the same
// screen region across every selection (spatial constancy = the navigability
// payoff). Inter-band gutters are intentional dead zones the relax can slide
// into without a card ever crossing into a foreign sector.
const ORBIT_BAND: Record<'dependency' | 'dependent' | 'transitive', OrbitBand> = {
  dependency: { lo: -48 * ORBIT_DEG, hi: 48 * ORBIT_DEG, center: 0 }, // RIGHT — "what this needs"
  dependent: { lo: Math.PI - 48 * ORBIT_DEG, hi: Math.PI + 48 * ORBIT_DEG, center: Math.PI }, // LEFT — "what depends on this"
  transitive: { lo: 235 * ORBIT_DEG, hi: 305 * ORBIT_DEG, center: 270 * ORBIT_DEG }, // LOWER — cascade falls away below
};
// Top gutter reserves vertical space for the absolute ReactFlow mode controls.
const EGO_HEADER_Y = 118;
const EGO_GROUP_WIDTH = 280;
const EGO_GROUP_HEIGHT = 72;
const EGO_TOTAL_EDGE_LIMIT = 96;
const EGO_CONTEXT_EDGE_LIMIT = 16;

// Cluster Flow zone board: zones placed in a 3-column grid, clusters packed
// 2-column inside each zone. Prevents one dominant layer from collapsing the
// surface into a single vertical lane.
const CLUSTER_FLOW_ZONE_WIDTH = 640;
const CLUSTER_FLOW_ZONE_HEIGHT = 430;
const CLUSTER_FLOW_ZONE_GAP_X = 80;
const CLUSTER_FLOW_ZONE_GAP_Y = 70;
const CLUSTER_FLOW_ZONE_COLUMNS = 3;
const CLUSTER_FLOW_BOARD_TOP_Y = 96;
const CLUSTER_FLOW_ZONE_HEADER_HEIGHT = 54;
const CLUSTER_FLOW_CARD_WIDTH = 260;
const CLUSTER_FLOW_CARD_HEIGHT = 96;
const CLUSTER_FLOW_CARD_GAP_X = 28;
const CLUSTER_FLOW_CARD_GAP_Y = 24;
const CLUSTER_FLOW_ZONE_PAD_X = 28;
const CLUSTER_FLOW_ZONE_PAD_TOP = 12;

const EDGE_BUDGETS: Record<CodeMapMode, Partial<Record<EdgeClass, number>>> = {
  architecture: {
    dependency: 40,
    control: 20,
    affinity: 0,
    verification: 0,
    unknown: 0,
  },
  // Panorama draws its own district-to-district corridors (see
  // buildPanoramaLayout); these per-file edge budgets are unused for it.
  panorama: {
    dependency: 0,
    control: 0,
    affinity: 0,
    verification: 0,
    unknown: 0,
  },
  focus: {
    dependency: 70,
    control: 25,
    affinity: 8,
    verification: 8,
    unknown: 0,
  },
  blast: {
    dependency: 90,
    control: 20,
    affinity: 0,
    verification: 10,
    unknown: 0,
  },
  evidence: {
    dependency: 50,
    control: 20,
    affinity: 0,
    verification: 30,
    unknown: 0,
  },
};

// Ego focus answers "what depends on this / what does this depend on" only.
// Control and verification belong in Evidence/Blast modes; affinity/unknown
// are already excluded by the ego neighbor selection.
const EGO_EDGE_BUDGETS: Partial<Record<EdgeClass, number>> = {
  dependency: 96,
  control: 0,
  verification: 0,
  affinity: 0,
  unknown: 0,
};

export type CodeMapLayoutResult = {
  nodes: Node[];
  edges: Edge[];
  renderedFileNodes: number;
  renderedGroupNodes: number;
  hiddenEdgesByFilter: number;
  egoSummary?: EgoFocusSummary;
  clusterFlowSummary?: ClusterFlowSummary;
  panoramaSummary?: PanoramaSummary;
  panoramaSelection?: PanoramaSelectionSummary | null;
};

type LayoutOptions = {
  packet: CodeMapPacket;
  mode: CodeMapMode;
  focus: FocusModel;
  activeToggles: Record<OverlayToggleId, boolean>;
  // Panorama-local soft selection: highlights the mark and shows its impact via
  // the Impact Lens WITHOUT entering Focus mode.
  panoramaSelectedPath?: string | null;
  // Impact Lens mode: 'impact' = affected regions + routed bundles, zero raw
  // edges (default); 'raw' = a capped, ranked sample of exact edges on demand.
  panoramaLens?: PanoramaLens;
};

function nodeIdForPath(path: string): string {
  return `file:${path}`;
}

function focusRoleForFile(file: CodeMapFile, focus: FocusModel): FocusRole {
  if (!focus.selectedPath) return 'normal';
  return focus.roleByPath.get(file.path) ?? 'background';
}

// Level-of-detail tier for a directed (dagre) graph, derived from how many file
// nodes will render. Denser graphs bias toward compact cards so the board never
// degrades into a wall of unreadable full cards; the selected spine always
// stays a hub. Thresholds mirror readableDirectedZoom's density bands.
export type CodeMapDensityTier = 'detail' | 'packet' | 'overview';

export function densityTier(nodeCount: number): CodeMapDensityTier {
  if (nodeCount > 90) return 'overview';
  if (nodeCount > 36) return 'packet';
  return 'detail';
}

function nodeSizeForFile(
  file: CodeMapFile,
  focus: FocusModel,
  tier: CodeMapDensityTier = 'detail',
): NodeSize {
  const role = focusRoleForFile(file, focus);
  if (role === 'selected') return 'hub';
  const important = deriveFileImportance(file) >= 12;
  // overview: only the spine is a hub; even important neighbors shrink to keep
  // a 100+ node field legible. packet: important neighbors stay full, the rest
  // compact. detail: original behavior (unchanged).
  if (tier === 'overview') return important ? 'normal' : 'compact';
  if (important) return 'hub';
  if (role === 'background') return 'compact';
  if (tier === 'packet') return 'compact';
  return 'normal';
}

function edgeClassRank(klass: EdgeClass): number {
  switch (klass) {
    case 'dependency':
      return 0;
    case 'control':
      return 1;
    case 'verification':
      return 2;
    case 'affinity':
      return 3;
    default:
      return 4;
  }
}

function edgeImportance(edge: CodeMapConnection, focus: FocusModel): number {
  let score = 0;
  const klass = classifyEdge(edge);
  if (klass === 'dependency') score += 20;
  if (klass === 'control') score += 14;
  if (klass === 'verification') score += 8;
  if (edge.confidence === 'high') score += 12;
  if (edge.confidence === 'medium') score += 6;
  if (isIncidentEdge(focus, edge)) score += 40;
  if (focus.depthByPath.has(edge.from) || focus.depthByPath.has(edge.to)) score += 20;
  return score;
}

function shouldRenderEdge(edge: CodeMapConnection, mode: CodeMapMode, focus: FocusModel): boolean {
  const klass = classifyEdge(edge);
  if (klass === 'containment') return false;

  if (mode === 'architecture') {
    if (klass !== 'dependency' && klass !== 'control') return false;
    if (isIncidentEdge(focus, edge)) return true;
    return klass === 'dependency' && edge.confidence === 'high';
  }

  if (mode === 'focus') {
    if (klass === 'affinity' || klass === 'verification') return isIncidentEdge(focus, edge);
    return klass === 'dependency' || klass === 'control' || isFocusRelevantEdge(focus, edge);
  }

  if (mode === 'blast') {
    if (klass === 'affinity') return false;
    return isFocusRelevantEdge(focus, edge) || klass === 'verification';
  }

  if (mode === 'evidence') {
    return true;
  }

  return false;
}

function filterEdges(
  packet: CodeMapPacket,
  renderedPaths: Set<string>,
  mode: CodeMapMode,
  focus: FocusModel,
  activeToggles: Record<OverlayToggleId, boolean>,
): CodeMapConnection[] {
  if (!activeToggles.code) return [];
  const budgets = { ...EDGE_BUDGETS[mode] };
  const used: Partial<Record<EdgeClass, number>> = {};
  return packet.connections
    .filter((edge) => renderedPaths.has(edge.from) && renderedPaths.has(edge.to))
    .filter((edge) => shouldRenderEdge(edge, mode, focus))
    .sort((left, right) => {
      const score = edgeImportance(right, focus) - edgeImportance(left, focus);
      if (score !== 0) return score;
      const rank = edgeClassRank(classifyEdge(left)) - edgeClassRank(classifyEdge(right));
      if (rank !== 0) return rank;
      return `${left.from}:${left.to}`.localeCompare(`${right.from}:${right.to}`);
    })
    .filter((edge) => {
      const klass = classifyEdge(edge);
      const budget = budgets[klass] ?? 0;
      if (budget <= 0) return false;
      const nextCount = (used[klass] ?? 0) + 1;
      if (nextCount > budget) return false;
      used[klass] = nextCount;
      return true;
    });
}

// When a node is selected in a directed mode, edges incident to the selected
// spine become the foreground layer and the rest recede, so the selected path
// reads clearly instead of competing with the whole dependency field.
type DirectedEdgeEmphasis = { hasSelection: boolean; incident: boolean };

function toReactFlowEdge(
  edge: CodeMapConnection,
  index: number,
  mode: CodeMapMode,
  emphasis?: DirectedEdgeEmphasis,
): Edge {
  const stroke = edgeStroke(edge);
  let opacity = stroke.opacity;
  let width = stroke.width;
  if (emphasis?.hasSelection) {
    if (emphasis.incident) {
      opacity = Math.min(1, stroke.opacity + 0.18);
      width = stroke.width + 0.4;
    } else {
      // Recede non-incident edges (transitive cascade / unrelated) so the
      // foreground spine is unambiguous, without erasing them entirely.
      opacity = stroke.opacity * 0.4;
    }
  }
  const evidenceLabel = mode === 'evidence'
    ? `${edge.kind ?? 'unknown'} / ${edge.confidence ?? 'unknown'}`
    : undefined;
  return {
    id: `edge:${edge.from}:${edge.to}:${edge.kind ?? 'unknown'}:${index}`,
    source: nodeIdForPath(edge.from),
    target: nodeIdForPath(edge.to),
    type: 'default',
    label: evidenceLabel,
    // Suppress v11 EdgeWrapper's default "Edge from X to Y" aria-label.
    // Visible `label` (evidence-mode) stays; ariaLabel is independent.
    // Per cap_quick_extend_wayfinding_map_a11y_contract_acro_863da57484ec.
    ariaLabel: '',
    animated: classifyEdge(edge) === 'control',
    style: {
      stroke: stroke.color,
      strokeWidth: width,
      opacity,
      strokeDasharray: stroke.dasharray,
    },
    labelStyle: {
      fill: '#d4d4d8',
      fontSize: 10,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
    },
    labelBgStyle: {
      fill: '#050706',
      fillOpacity: 0.9,
    },
    data: { edge },
  };
}

function toFileNode(
  file: CodeMapFile,
  x: number,
  y: number,
  focus: FocusModel,
  activeToggles: Record<OverlayToggleId, boolean>,
  tier: CodeMapDensityTier = 'detail',
): Node {
  const size = nodeSizeForFile(file, focus, tier);
  const dimensions = nodeDimensions(size);
  return {
    id: nodeIdForPath(file.path),
    type: 'codemapFile',
    position: { x, y },
    data: {
      file,
      size,
      focusRole: focusRoleForFile(file, focus),
      activeToggles,
    },
    style: dimensions,
    zIndex: 10,
  };
}

function filesForDirectedMode(packet: CodeMapPacket, mode: CodeMapMode, focus: FocusModel): CodeMapFile[] {
  const layerGroups = buildLayerGroups(packet.files, mode, focus.selectedPath);
  const representatives = allRepresentativeFiles(layerGroups);
  const sorted = representatives.sort((left, right) => {
    const leftRole = focusRoleForFile(left, focus);
    const rightRole = focusRoleForFile(right, focus);
    const roleRank = (role: FocusRole) => {
      switch (role) {
        case 'selected':
          return 0;
        case 'dependency':
        case 'dependent':
          return 1;
        case 'blast_depth_1':
          return 2;
        case 'blast_depth_2':
          return 3;
        case 'blast_depth_3':
          return 4;
        case 'normal':
          return 5;
        default:
          return 6;
      }
    };
    const roleDelta = roleRank(leftRole) - roleRank(rightRole);
    if (roleDelta !== 0) return roleDelta;
    const importanceDelta = deriveFileImportance(right) - deriveFileImportance(left);
    if (importanceDelta !== 0) return importanceDelta;
    return left.path.localeCompare(right.path);
  });
  return sorted.slice(0, FOCUS_NODE_LIMIT);
}

function buildDirectedNodes(
  packet: CodeMapPacket,
  mode: CodeMapMode,
  focus: FocusModel,
  activeToggles: Record<OverlayToggleId, boolean>,
): { nodes: Node[]; files: CodeMapFile[] } {
  const files = filesForDirectedMode(packet, mode, focus);
  const tier = densityTier(files.length);
  // Tighten dagre spacing as density rises so compact cards pack closer and the
  // overview tier stays a coherent board instead of a sprawling poster.
  const nodesep = tier === 'overview' ? 28 : tier === 'packet' ? 36 : 44;
  const ranksep = tier === 'overview' ? 64 : tier === 'packet' ? 80 : 92;
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({ rankdir: 'LR', nodesep, ranksep, marginx: 30, marginy: 30 });
  graph.setDefaultEdgeLabel(() => ({}));

  files.forEach((file) => {
    const dimensions = nodeDimensions(nodeSizeForFile(file, focus, tier));
    graph.setNode(file.path, dimensions);
  });

  const renderedPaths = new Set(files.map((file) => file.path));
  packet.connections.forEach((edge) => {
    if (!renderedPaths.has(edge.from) || !renderedPaths.has(edge.to)) return;
    if (classifyEdge(edge) === 'containment' || classifyEdge(edge) === 'affinity') return;
    graph.setEdge(edge.from, edge.to);
  });

  dagre.layout(graph);

  const nodes = files.map((file) => {
    const point = graph.node(file.path) as { x?: number; y?: number } | undefined;
    const dimensions = nodeDimensions(nodeSizeForFile(file, focus, tier));
    const x = (point?.x ?? 0) - dimensions.width / 2;
    const y = (point?.y ?? 0) - dimensions.height / 2;
    return toFileNode(file, x, y, focus, activeToggles, tier);
  });

  if (nodes.length === 0 && packet.files.length > 0) {
    const file = packet.files[0];
    return { nodes: [toFileNode(file, 30, 30, focus, activeToggles, tier)], files: [file] };
  }

  return { nodes, files };
}

function toEgoGroupNode(
  group: FocusCollapsedGroup,
  x: number,
  y: number,
): Node {
  const layerLabel =
    group.direction === 'transitive'
      ? 'transitive dependents'
      : group.direction === 'outgoing'
        ? 'dependency overflow'
        : 'dependent overflow';
  return {
    id: `group:${group.id}`,
    type: 'codemapGroup',
    position: { x, y },
    data: {
      label: group.label,
      layer: layerLabel,
      totalFiles: group.count,
      shownFiles: 0,
      collapsedCount: group.count,
      warningCount: 0,
      overlayCount: 0,
      paths: group.paths,
    },
    style: { width: EGO_GROUP_WIDTH, height: EGO_GROUP_HEIGHT },
    zIndex: 1,
    selectable: false,
    draggable: false,
  };
}

function toEgoGroupEdge(
  group: FocusCollapsedGroup,
  selectedPath: string,
  index: number,
): Edge {
  const incoming = group.direction === 'incoming' || group.direction === 'transitive';
  const groupNodeId = `group:${group.id}`;
  const selectedNodeId = nodeIdForPath(selectedPath);
  return {
    id: `ego-group-edge:${group.id}:${index}`,
    source: incoming ? groupNodeId : selectedNodeId,
    target: incoming ? selectedNodeId : groupNodeId,
    type: 'egoDogleg',
    label: `+${group.count}`,
    ariaLabel: '',
    animated: false,
    style: {
      stroke: group.direction === 'transitive' ? '#22d3ee' : '#fbbf24',
      strokeWidth: 1.3,
      opacity: 0.45,
      strokeDasharray: '4 7',
    },
    labelStyle: {
      fill: '#d4d4d8',
      fontSize: 10,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
    },
    labelBgStyle: {
      fill: '#050706',
      fillOpacity: 0.92,
    },
    data: {
      edge: {
        from: incoming ? group.label : selectedPath,
        to: incoming ? selectedPath : group.label,
        kind: group.direction === 'transitive' ? 'hidden_transitive_dependents' : 'hidden_focus_overflow',
      },
      egoDirection: incoming ? 'back' : 'forward',
      egoLane: index,
      egoLaneCount: 1,
    },
  };
}

type OrbitPlaced = {
  file: CodeMapFile;
  angle: number;
  radius: number;
  band: OrbitBand;
  size: { width: number; height: number };
};

// Pack files (already in deterministic priority order) into concentric arcs
// inside `band`, starting at `baseRadius`: fill a ring to its angular capacity
// before stepping outward, so a dense sector becomes a compact set of
// concentric fans rather than one ring pushed to an enormous radius. A narrow
// band's inner ring holds few cards, so capacity grows with radius. Returns the
// placements plus the outermost radius reached (so a caller can stack a deeper
// depth group beyond it).
function packOrbitSector(
  files: CodeMapFile[],
  band: OrbitBand,
  baseRadius: number,
  sizeOf: (file: CodeMapFile) => { width: number; height: number },
): { placed: OrbitPlaced[]; outerRadius: number } {
  const placed: OrbitPlaced[] = [];
  const span = band.hi - band.lo;
  let radius = baseRadius;
  let index = 0;
  while (index < files.length) {
    const capacity = Math.max(1, Math.floor((span * radius) / ORBIT_SLOT));
    const members = files.slice(index, index + capacity);
    const k = members.length;
    members.forEach((file, i) => {
      // (i+1)/(k+1) centers the fan within the band with equal margins; index 0
      // (most important, lists are importance-sorted) lands nearest the low edge.
      const angle = band.lo + span * ((i + 1) / (k + 1));
      placed.push({ file, angle, radius, band, size: sizeOf(file) });
    });
    index += capacity;
    radius += ORBIT_RING_STEP;
  }
  return { placed, outerRadius: Math.max(baseRadius, radius - ORBIT_RING_STEP) };
}

// Polar -> top-left rect about the orbit origin. cy negates sin so the screen-up
// grammar reads correctly over ReactFlow's y-down axis.
function orbitRect(p: { angle: number; radius: number; size: { width: number; height: number } }): {
  x: number; y: number; width: number; height: number;
} {
  const cx = p.radius * Math.cos(p.angle);
  const cy = -p.radius * Math.sin(p.angle);
  return { x: cx - p.size.width / 2, y: cy - p.size.height / 2, width: p.size.width, height: p.size.height };
}

function buildEgoFocusLayout(
  packet: CodeMapPacket,
  focus: FocusModel,
  activeToggles: Record<OverlayToggleId, boolean>,
): CodeMapLayoutResult | null {
  const selection = buildFocusGraphSelection(packet, focus);
  if (!selection) return null;

  const nodes: Node[] = [];
  const renderedFiles: CodeMapFile[] = [];

  // --- Center-Orbit placement -------------------------------------------------
  // The selected card is pinned at the orbit origin; neighbors are placed in
  // deterministic semantic sectors (relation -> angle band) and rings
  // (blast-depth / importance order -> concentric arcs), then a bounded
  // deterministic AABB relax repairs residual rectangular overlap by growing
  // radius along a card's own spoke and sliding along-arc within its band —
  // never by zooming out (that would recreate the microscopic-strip failure).
  // Every input is a pure function of (packet, selectedPath): the selection
  // lists are already totally ordered (importance then path), angle/radius are
  // closed-form, and the relax is fixed-pass with no RNG / wall-clock, so
  // positions are viewport-independent and identical across rerenders.
  const orbitTier = densityTier(
    1 +
      selection.directDependencies.length +
      selection.directDependents.length +
      selection.transitiveDependents.length,
  );
  const orbitSizeOf = (file: CodeMapFile) => nodeDimensions(nodeSizeForFile(file, focus, orbitTier));
  const centerSize = nodeDimensions(
    selection.selectedFile ? nodeSizeForFile(selection.selectedFile, focus, orbitTier) : 'hub',
  );

  // Transitive dependents split by blast depth so topological distance reads as
  // radial distance: direct (depth 1) dependents ride the inner ring (R_BASE),
  // depth-2 transitives sit one ring out (R_BASE + step), depth-3 stacked beyond
  // them — so a card's radius tracks its blast depth.
  const transitiveDepth2 = selection.transitiveDependents.filter(
    (file) => (focus.depthByPath.get(file.path) ?? 2) <= 2,
  );
  const transitiveDepth3 = selection.transitiveDependents.filter(
    (file) => (focus.depthByPath.get(file.path) ?? 2) >= 3,
  );
  const dependentPack = packOrbitSector(selection.directDependents, ORBIT_BAND.dependent, ORBIT_R_BASE, orbitSizeOf);
  const transitive2Pack = packOrbitSector(transitiveDepth2, ORBIT_BAND.transitive, ORBIT_R_BASE + ORBIT_RING_STEP, orbitSizeOf);
  const transitive3Pack = packOrbitSector(
    transitiveDepth3,
    ORBIT_BAND.transitive,
    transitive2Pack.outerRadius + ORBIT_RING_STEP,
    orbitSizeOf,
  );
  const dependencyPack = packOrbitSector(selection.directDependencies, ORBIT_BAND.dependency, ORBIT_R_BASE, orbitSizeOf);

  // Global priority order for the relax "lower-priority yields" rule: the pinned
  // center is the immovable obstacle, then dependencies, direct dependents,
  // transitive (each list already importance/depth ordered, a total order).
  const orbiters: OrbitPlaced[] = [
    ...dependencyPack.placed,
    ...dependentPack.placed,
    ...transitive2Pack.placed,
    ...transitive3Pack.placed,
  ];

  const centerRect = {
    x: -centerSize.width / 2,
    y: -centerSize.height / 2,
    width: centerSize.width,
    height: centerSize.height,
  };
  const orbitRects = orbiters.map(orbitRect);

  for (let pass = 0; pass < ORBIT_RELAX_PASSES; pass += 1) {
    let moved = false;
    for (let i = 0; i < orbiters.length; i += 1) {
      const placement = orbiters[i];
      // Higher-priority cards (earlier in `orbiters`) plus the pinned center
      // hold position; this card yields.
      const obstacles = [centerRect, ...orbitRects.slice(0, i)];
      let guard = 0;
      while (guard < 16 && obstacles.some((obstacle) => rectsOverlap(orbitRects[i], obstacle))) {
        placement.radius += ORBIT_RING_STEP * 0.25; // grow along the spoke first
        orbitRects[i] = orbitRect(placement);
        if (obstacles.some((obstacle) => rectsOverlap(orbitRects[i], obstacle))) {
          const nextAngle = Math.min(placement.angle + ORBIT_ANGLE_STEP, placement.band.hi);
          if (nextAngle === placement.angle) {
            placement.radius += ORBIT_RING_STEP; // band saturated -> promote a ring
          } else {
            placement.angle = nextAngle; // else slide along-arc within the band
          }
          orbitRects[i] = orbitRect(placement);
        }
        moved = true;
        guard += 1;
        if (placement.radius > ORBIT_R_BASE + 14 * ORBIT_RING_STEP) break; // non-trapping safety stop
      }
    }
    if (!moved) break; // stable: deterministic early-out, not time/RNG based
  }

  // Translate the origin-centered orbit into positive space so no card sits
  // above the reserved header band (test gate: minY >= 80). The camera
  // (focusViewportForSelectedNode) re-centers the selected hub in the live pane
  // regardless of this offset.
  const boundedRects = [centerRect, ...orbitRects];
  const orbitMinX = Math.min(...boundedRects.map((rect) => rect.x));
  const orbitMinY = Math.min(...boundedRects.map((rect) => rect.y));
  const orbitOffX = -orbitMinX + ORBIT_LEFT_PAD;
  const orbitOffY = -orbitMinY + EGO_HEADER_Y;

  if (selection.selectedFile) {
    nodes.push(toFileNode(selection.selectedFile, centerRect.x + orbitOffX, centerRect.y + orbitOffY, focus, activeToggles, orbitTier));
    renderedFiles.push(selection.selectedFile);
  }
  orbiters.forEach((placement, index) => {
    nodes.push(toFileNode(placement.file, orbitRects[index].x + orbitOffX, orbitRects[index].y + orbitOffY, focus, activeToggles, orbitTier));
    renderedFiles.push(placement.file);
  });

  // Overflow group cards parked on each sector's centroid beyond its outer ring.
  const bandOuterRadius = (band: OrbitBand): number =>
    orbiters.reduce(
      (max, placement) => (placement.band === band ? Math.max(max, placement.radius) : max),
      ORBIT_R_BASE,
    );
  const parkOverflowGroup = (group: FocusCollapsedGroup | null, band: OrbitBand) => {
    if (!group) return;
    const radius = bandOuterRadius(band) + ORBIT_RING_STEP + EGO_GROUP_HEIGHT / 2;
    const cx = radius * Math.cos(band.center);
    const cy = -radius * Math.sin(band.center);
    nodes.push(toEgoGroupNode(group, cx - EGO_GROUP_WIDTH / 2 + orbitOffX, cy - EGO_GROUP_HEIGHT / 2 + orbitOffY));
  };
  parkOverflowGroup(selection.collapsedDependentGroup, ORBIT_BAND.dependent);
  parkOverflowGroup(selection.collapsedTransitiveGroup, ORBIT_BAND.transitive);
  parkOverflowGroup(selection.collapsedDependencyGroup, ORBIT_BAND.dependency);

  const renderedPaths = new Set(renderedFiles.map((file) => file.path));
  const selectedPath = selection.selectedPath;
  const codeGraphEnabled = activeToggles.code;

  type ScoredEdge = { edge: CodeMapConnection; klass: EdgeClass };
  // De-dupe by directed pair (from -> to): if a packet has multiple relations
  // between the same two files, render one line in Focus mode chosen by class
  // then confidence. Details live in Evidence/drawer.
  const classRank: Record<EdgeClass, number> = {
    dependency: 0,
    control: 1,
    verification: 2,
    affinity: 3,
    containment: 4,
    unknown: 5,
  };
  const confidenceRank = (confidence: string | null | undefined): number => {
    switch (confidence) {
      case 'high': return 0;
      case 'medium': return 1;
      case 'low': return 2;
      default: return 3;
    }
  };
  const bestByPair = new Map<string, ScoredEdge>();
  const contextByPair = new Map<string, ScoredEdge>();
  let hiddenFocusEdgeCount = 0;
  packet.connections.forEach((edge) => {
    const klass = classifyEdge(edge);
    if (klass === 'containment') return;
    const incidentOnSelected = edge.from === selectedPath || edge.to === selectedPath;
    const fromRendered = renderedPaths.has(edge.from);
    const toRendered = renderedPaths.has(edge.to);
    if (!fromRendered || !toRendered) {
      const focusBoundaryEdge = (fromRendered || toRendered) && incidentOnSelected;
      if (focusBoundaryEdge) hiddenFocusEdgeCount += 1;
      return;
    }
    const budgetForClass = EGO_EDGE_BUDGETS[klass] ?? 0;
    if (budgetForClass <= 0) {
      if (incidentOnSelected) hiddenFocusEdgeCount += 1;
      return;
    }
    if (!incidentOnSelected) {
      const contextualInNeighborhood = focus.depthByPath.has(edge.from) || focus.depthByPath.has(edge.to);
      if (!contextualInNeighborhood) return;
      const key = `${edge.from}->${edge.to}`;
      const candidate: ScoredEdge = { edge, klass };
      const existing = contextByPair.get(key);
      if (!existing) {
        contextByPair.set(key, candidate);
        return;
      }
      const newScore = classRank[klass] * 10 + confidenceRank(edge.confidence);
      const oldScore = classRank[existing.klass] * 10 + confidenceRank(existing.edge.confidence);
      if (newScore < oldScore) {
        contextByPair.set(key, candidate);
      }
      return;
    }
    const key = `${edge.from}->${edge.to}`;
    const candidate: ScoredEdge = { edge, klass };
    const existing = bestByPair.get(key);
    if (!existing) {
      bestByPair.set(key, candidate);
      return;
    }
    const newScore = classRank[klass] * 10 + confidenceRank(edge.confidence);
    const oldScore = classRank[existing.klass] * 10 + confidenceRank(existing.edge.confidence);
    if (newScore < oldScore) {
      bestByPair.set(key, candidate);
      hiddenFocusEdgeCount += 1;
    } else {
      hiddenFocusEdgeCount += 1;
    }
  });
  const incidentEdges: ScoredEdge[] = Array.from(bestByPair.values());
  const contextEdges: ScoredEdge[] = Array.from(contextByPair.values());

  const budgets = { ...EGO_EDGE_BUDGETS };
  const used: Partial<Record<EdgeClass, number>> = {};
  incidentEdges.sort((left, right) => {
    const score = edgeImportance(right.edge, focus) - edgeImportance(left.edge, focus);
    if (score !== 0) return score;
    const rank = edgeClassRank(left.klass) - edgeClassRank(right.klass);
    if (rank !== 0) return rank;
    return `${left.edge.from}:${left.edge.to}`.localeCompare(`${right.edge.from}:${right.edge.to}`);
  });
  const accepted: CodeMapConnection[] = [];
  let budgetDroppedCount = 0;
  incidentEdges.forEach(({ edge, klass }) => {
    const budget = budgets[klass] ?? 0;
    if (budget <= 0) {
      budgetDroppedCount += 1;
      return;
    }
    const next = (used[klass] ?? 0) + 1;
    if (next > budget) {
      budgetDroppedCount += 1;
      return;
    }
    used[klass] = next;
    accepted.push(edge);
  });

  const acceptedContext: CodeMapConnection[] = [];
  const contextBudget = Math.max(0, Math.min(EGO_CONTEXT_EDGE_LIMIT, EGO_TOTAL_EDGE_LIMIT - accepted.length));
  contextEdges
    .sort((left, right) => {
      const score = edgeImportance(right.edge, focus) - edgeImportance(left.edge, focus);
      if (score !== 0) return score;
      const rank = edgeClassRank(left.klass) - edgeClassRank(right.klass);
      if (rank !== 0) return rank;
      return `${left.edge.from}:${left.edge.to}`.localeCompare(`${right.edge.from}:${right.edge.to}`);
    })
    .forEach(({ edge, klass }) => {
      if (acceptedContext.length >= contextBudget) {
        return;
      }
      const budget = budgets[klass] ?? 0;
      if (budget <= 0) {
        return;
      }
      const next = (used[klass] ?? 0) + 1;
      if (next > budget) {
        return;
      }
      used[klass] = next;
      acceptedContext.push(edge);
    });

  const existingImpactPairs = new Set<string>();
  [...accepted, ...acceptedContext].forEach((edge) => {
    existingImpactPairs.add(`${edge.from}->${edge.to}`);
    existingImpactPairs.add(`${edge.to}->${edge.from}`);
  });
  const synthesizeImpactEdge = (file: CodeMapFile, index: number): CodeMapConnection | null => {
    if (!renderedPaths.has(file.path) || file.path === selectedPath) return null;
    const pairKey = `${file.path}->${selectedPath}`;
    if (existingImpactPairs.has(pairKey)) return null;
    existingImpactPairs.add(pairKey);
    const depth = focus.depthByPath.get(file.path);
    return {
      from: file.path,
      to: selectedPath,
      kind: 'blast_transitive',
      confidence: depth === 1 ? 'medium' : 'low',
      edge_sources: ['blast_radius'],
      evidence: `blast depth ${depth ?? 'unknown'} #${index + 1}`,
    };
  };
  const impactCandidates = [
    ...selection.directDependents,
    ...selection.transitiveDependents,
  ]
    .map(synthesizeImpactEdge)
    .filter((edge): edge is CodeMapConnection => Boolean(edge));
  const impactBudget = Math.max(0, EGO_TOTAL_EDGE_LIMIT - accepted.length - acceptedContext.length);
  const impactEdges = impactCandidates.slice(0, impactBudget);
  budgetDroppedCount += Math.max(0, impactCandidates.length - impactEdges.length);

  type EgoEdgeAnnotation = { edge: CodeMapConnection; direction: 'forward' | 'back' };
  const forwardEdges: CodeMapConnection[] = [];
  const backEdges: CodeMapConnection[] = [];
  [...accepted, ...impactEdges].forEach((edge) => {
    if (edge.from === selectedPath) forwardEdges.push(edge);
    else backEdges.push(edge);
  });
  const annotated: Array<EgoEdgeAnnotation & { lane: number; laneCount: number }> = [];
  forwardEdges.forEach((edge, index) => {
    annotated.push({ edge, direction: 'forward', lane: index, laneCount: forwardEdges.length });
  });
  backEdges.forEach((edge, index) => {
    annotated.push({ edge, direction: 'back', lane: index, laneCount: backEdges.length });
  });

  const edges = codeGraphEnabled
    ? [
        ...annotated.map((row, index) => {
        const baseEdge = toReactFlowEdge(row.edge, index, 'focus');
        return {
          ...baseEdge,
          type: 'egoDogleg',
          data: {
            ...(baseEdge.data ?? {}),
            egoDirection: row.direction,
            egoLane: row.lane,
            egoLaneCount: row.laneCount,
            // Center-orbit spokes radiate from the pinned hub; the edge renderer
            // draws a near-straight radial spoke instead of the horizontal
            // dogleg. Group-overflow edges (toEgoGroupEdge) omit this flag and
            // keep the dogleg.
            egoRadial: true,
          },
        };
        }),
        ...acceptedContext.map((edge, index) => toReactFlowEdge(edge, annotated.length + index, 'focus')),
        ...[
          selection.collapsedDependentGroup,
          selection.collapsedTransitiveGroup,
          selection.collapsedDependencyGroup,
        ]
          .filter((group): group is FocusCollapsedGroup => Boolean(group))
          .map((group, index) => toEgoGroupEdge(group, selectedPath, annotated.length + acceptedContext.length + index)),
      ]
    : [];
  const hiddenEdges = codeGraphEnabled
    ? hiddenFocusEdgeCount + budgetDroppedCount
    : Math.max(0, packet.connections.length);

  return {
    nodes,
    edges,
    renderedFileNodes: renderedFiles.length,
    renderedGroupNodes: nodes.length - renderedFiles.length,
    hiddenEdgesByFilter: hiddenEdges,
    egoSummary: {
      dependencyOverflow: selection.hiddenCounts.dependencyOverflow,
      dependentOverflow: selection.hiddenCounts.dependentOverflow,
      transitiveDependents: selection.hiddenCounts.transitiveDependents,
      hiddenEdges,
      visibleDirectDependencies: selection.directDependencies.length,
      visibleDirectDependents: selection.directDependents.length,
      visibleTransitiveDependents: selection.transitiveDependents.length,
    },
  };
}

function buildClusterFlowLayout(
  packet: CodeMapPacket,
  activeToggles: Record<OverlayToggleId, boolean>,
): CodeMapLayoutResult {
  const model = buildClusterFlowModel(packet);
  const nodes: Node[] = [];

  // Only render zones that actually have a visible cluster card. A
  // header-only row with no cluster cards wastes a full board row.
  const visibleZones = model.zones.filter((zone) => zone.clusters.length > 0);
  visibleZones.forEach((zone: ClusterFlowZone, zoneIndex) => {
    const col = zoneIndex % CLUSTER_FLOW_ZONE_COLUMNS;
    const row = Math.floor(zoneIndex / CLUSTER_FLOW_ZONE_COLUMNS);
    const zoneX = col * (CLUSTER_FLOW_ZONE_WIDTH + CLUSTER_FLOW_ZONE_GAP_X);
    const zoneY = CLUSTER_FLOW_BOARD_TOP_Y + row * (CLUSTER_FLOW_ZONE_HEIGHT + CLUSTER_FLOW_ZONE_GAP_Y);

    // Zone header (non-clickable summary node).
    nodes.push({
      id: `zone:${zone.key}`,
      type: 'codemapZoneHeader',
      position: { x: zoneX, y: zoneY },
      data: {
        key: zone.key,
        label: zone.label,
        clusterCount: zone.clusters.length,
        totalFiles: zone.totalFiles,
        totalFanIn: zone.totalFanIn,
        totalFanOut: zone.totalFanOut,
        warningCount: zone.warningCount,
        overlayCount: zone.overlayCount,
        hiddenClusterCount: zone.hiddenClusterCount,
        representativePath:
          zone.clusters.find((cluster) => cluster.representativePath)?.representativePath ??
          zone.clusters.flatMap((cluster) => cluster.samplePaths).find((path) => path.trim()) ??
          null,
      },
      style: { width: CLUSTER_FLOW_ZONE_WIDTH, height: CLUSTER_FLOW_ZONE_HEADER_HEIGHT },
      zIndex: 5,
      selectable: false,
      draggable: false,
    });

    // 2-column cluster pack inside this zone.
    const cardsTop = zoneY + CLUSTER_FLOW_ZONE_HEADER_HEIGHT + CLUSTER_FLOW_ZONE_PAD_TOP;
    zone.clusters.forEach((cluster: ClusterFlowNode, clusterIndex) => {
      const cardCol = clusterIndex % 2;
      const cardRow = Math.floor(clusterIndex / 2);
      const cardX = zoneX + CLUSTER_FLOW_ZONE_PAD_X +
        cardCol * (CLUSTER_FLOW_CARD_WIDTH + CLUSTER_FLOW_CARD_GAP_X);
      const cardY = cardsTop + cardRow * (CLUSTER_FLOW_CARD_HEIGHT + CLUSTER_FLOW_CARD_GAP_Y);
      nodes.push({
        id: `cluster:${cluster.id}`,
        type: 'codemapCluster',
        position: { x: cardX, y: cardY },
        data: { cluster },
        style: { width: CLUSTER_FLOW_CARD_WIDTH, height: CLUSTER_FLOW_CARD_HEIGHT },
        zIndex: 10,
      });
    });
  });

  const codeGraphEnabled = activeToggles.code;
  // Cluster-flow edges are context, not the headline. Lower opacity and only
  // label aggregates that actually carry weight (count >= 3).
  const visibleZoneKeys = new Set(visibleZones.map((zone) => zone.key));
  const edges: Edge[] = codeGraphEnabled
    ? model.zoneEdges
        .filter((aggregate) => visibleZoneKeys.has(aggregate.sourceZone) && visibleZoneKeys.has(aggregate.targetZone))
        .map((aggregate: ClusterFlowZoneEdge, index) => {
          const tone = edgeClassTone(aggregate.edgeClass);
          const widthBucket = aggregate.count >= 30 ? 2.4 : aggregate.count >= 10 ? 1.9 : 1.35;
          return {
            id: `zone-edge:${index}:${aggregate.id}`,
            source: `zone:${aggregate.sourceZone}`,
            target: `zone:${aggregate.targetZone}`,
            type: 'default',
            label: aggregate.count >= 3 ? String(aggregate.count) : undefined,
            ariaLabel: '',
            animated: false,
            style: {
              stroke: tone.color,
              strokeWidth: widthBucket,
              strokeDasharray: tone.dasharray,
              // Architecture flow edges were 0.45 — too faint to trace
              // cluster-to-cluster at fhd. Lifted to 0.6; still dashed +
              // sub-headline so the board doesn't become a neon hairball.
              opacity: 0.6,
            },
            labelStyle: {
              fill: '#d4d4d8',
              fontSize: 10,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            },
            labelBgStyle: {
              fill: '#050706',
              fillOpacity: 0.9,
            },
            data: { aggregate },
          } satisfies Edge;
        })
    : [];

  return {
    nodes,
    edges,
    renderedFileNodes: 0,
    renderedGroupNodes: model.visibleClusters + visibleZones.length,
    hiddenEdgesByFilter: codeGraphEnabled
      ? model.hiddenEdges
      : Math.max(0, packet.connections.length),
    clusterFlowSummary: {
      visibleClusters: model.visibleClusters,
      visibleZones: visibleZones.length,
      hiddenClusters: model.hiddenClusters,
      visibleEdges: codeGraphEnabled ? model.visibleEdges : 0,
      hiddenEdges: codeGraphEnabled
        ? model.hiddenEdges
        : Math.max(0, packet.connections.length),
    },
  };
}

// --- Panorama / System Atlas whole-system terrain ---------------------------
// THREE nested coordinate systems: a stable MACRO geography of district hulls
// (architecture zones in a deterministic 3-wide masonry), a MESO geography of
// SUBDISTRICT blocks (clusters/folders shelf-packed inside each district), and
// a MICRO packing of every file as a mark inside its subdistrict. The cluster
// structure is what stops a district reading as a uniform carpet. All pure
// arithmetic over the fixed ZONE_ORDER + importance-sorted files -> the map is
// a learnable place, identical across rerenders.
const PANORAMA_DOT = 16; // file mark edge length (square)
const PANORAMA_PITCH = 22; // cell pitch inside a subdistrict grid (mark + gap)
const PANORAMA_SUB_MAX_COLS = 14; // cap a subdistrict's grid width so blocks wrap, not sprawl
const PANORAMA_SUB_HEADER = 18; // subdistrict label band
const PANORAMA_SUB_PAD = 7; // subdistrict inner padding
const PANORAMA_SUB_GAP = 14; // gutter between subdistrict blocks
const PANORAMA_HEADER = 48; // district header band (label + chips)
const PANORAMA_PAD = 16; // district inner padding around the subdistrict shelf
const PANORAMA_COLUMNS = 3; // districts per board row
const PANORAMA_GAP_X = 84; // horizontal gutter between districts
const PANORAMA_GAP_Y = 84; // vertical gutter between board rows
const PANORAMA_BOARD_TOP = 60; // top margin reserving space for mode controls
const PANORAMA_BASE_CORRIDORS = 36; // heaviest baseline roads shown with no selection
const PANORAMA_LABEL_MIN_FILES = 4; // below this a subdistrict is unlabeled (no "C... 1" farm)
// Impact Lens ink budget. A hub selection must NEVER spray raw edges across the
// map: the default lens draws affected REGIONS + a few routed bundles and zero
// raw file-to-file edges. Raw edges are an explicit, capped drilldown only.
const PANORAMA_IMPACT_BUNDLE_LIMIT = 12; // routed district bundles in Impact lens
const PANORAMA_RAW_EDGE_LIMIT = 24; // capped raw edges in Raw lens (on demand)

type SubPlacement = {
  sub: PanoramaDistrict['subdistricts'][number];
  cols: number;
  x: number;
  y: number;
  width: number;
  height: number;
};
type PanoramaBox = { district: PanoramaDistrict; subs: SubPlacement[]; width: number; height: number };

function subdistrictGridCols(n: number): number {
  return Math.min(PANORAMA_SUB_MAX_COLS, Math.max(1, Math.round(Math.sqrt(n * 1.3))));
}

// Shelf-pack a district's subdistrict blocks (already largest-first) into rows
// inside a target content width chosen so the district reads roughly square.
function panoramaDistrictBox(district: PanoramaDistrict): PanoramaBox {
  const blocks = district.subdistricts.map((sub) => {
    const cols = subdistrictGridCols(sub.fileCount);
    const rows = Math.ceil(sub.fileCount / cols);
    const width = cols * PANORAMA_PITCH + PANORAMA_SUB_PAD * 2;
    const height = PANORAMA_SUB_HEADER + rows * PANORAMA_PITCH + PANORAMA_SUB_PAD * 2;
    return { sub, cols, width, height };
  });
  const totalArea = blocks.reduce((sum, block) => sum + block.width * block.height, 0);
  const maxBlockWidth = blocks.reduce((max, block) => Math.max(max, block.width), 0);
  const targetWidth = Math.max(maxBlockWidth, Math.round(Math.sqrt(totalArea) * 1.25));

  const subs: SubPlacement[] = [];
  let cursorX = 0;
  let cursorY = 0;
  let rowHeight = 0;
  let contentWidth = 0;
  blocks.forEach((block) => {
    if (cursorX > 0 && cursorX + block.width > targetWidth) {
      cursorY += rowHeight + PANORAMA_SUB_GAP;
      cursorX = 0;
      rowHeight = 0;
    }
    subs.push({ sub: block.sub, cols: block.cols, x: cursorX, y: cursorY, width: block.width, height: block.height });
    cursorX += block.width + PANORAMA_SUB_GAP;
    rowHeight = Math.max(rowHeight, block.height);
    contentWidth = Math.max(contentWidth, cursorX - PANORAMA_SUB_GAP);
  });
  const contentHeight = cursorY + rowHeight;
  return {
    district,
    subs,
    width: contentWidth + PANORAMA_PAD * 2,
    height: PANORAMA_HEADER + contentHeight + PANORAMA_PAD,
  };
}

type ImpactAgg = { incoming: number; outgoing: number; total: number };

function bumpImpact(map: Map<string, ImpactAgg>, key: string, outgoing: boolean): void {
  const agg = map.get(key) ?? { incoming: 0, outgoing: 0, total: 0 };
  if (outgoing) agg.outgoing += 1;
  else agg.incoming += 1;
  agg.total += 1;
  map.set(key, agg);
}

// Rank a raw edge for the capped Raw lens: dependency > control > verification,
// then high > medium > low confidence. Higher score = more worth showing.
function rawEdgeScore(edge: CodeMapConnection): number {
  const klass = classifyEdge(edge);
  const classRank = klass === 'dependency' ? 3 : klass === 'control' ? 2 : klass === 'verification' ? 1 : 0;
  const confRank = edge.confidence === 'high' ? 3 : edge.confidence === 'medium' ? 2 : edge.confidence === 'low' ? 1 : 0;
  return classRank * 10 + confRank;
}

function buildPanoramaLayout(
  packet: CodeMapPacket,
  activeToggles: Record<OverlayToggleId, boolean>,
  panoramaSelectedPath: string | null,
  lens: PanoramaLens,
): CodeMapLayoutResult {
  const model = buildPanoramaModel(packet);
  const boxes = model.districts.map(panoramaDistrictBox);

  // Macro placement: left-aligned masonry rows of PANORAMA_COLUMNS districts.
  const placements = new Map<string, { x: number; y: number; box: PanoramaBox }>();
  let cursorY = PANORAMA_BOARD_TOP;
  for (let rowStart = 0; rowStart < boxes.length; rowStart += PANORAMA_COLUMNS) {
    const row = boxes.slice(rowStart, rowStart + PANORAMA_COLUMNS);
    let cursorX = 0;
    let rowHeight = 0;
    row.forEach((box) => {
      placements.set(box.district.zone, { x: cursorX, y: cursorY, box });
      cursorX += box.width + PANORAMA_GAP_X;
      rowHeight = Math.max(rowHeight, box.height);
    });
    cursorY += rowHeight + PANORAMA_GAP_Y;
  }

  // path -> zone / subdistrict, built from the model so impact bucketing can run
  // before nodes are created (node data carries the impact flags).
  const pathToZone = new Map<string, string>();
  const pathToSub = new Map<string, string>();
  model.districts.forEach((district) => {
    district.subdistricts.forEach((sub) => {
      const subId = `${district.zone}:${sub.id}`;
      sub.files.forEach((file) => {
        pathToZone.set(file.path, district.zone);
        pathToSub.set(file.path, subId);
      });
    });
  });
  const renderedPaths = new Set(pathToZone.keys());

  const codeGraphEnabled = activeToggles.code;
  const hasSelection = Boolean(panoramaSelectedPath && renderedPaths.has(panoramaSelectedPath));

  // --- Impact Lens computation ----------------------------------------------
  // For a soft-selected file, bucket its incident edges by the OTHER endpoint's
  // district + subdistrict (regions), count direction, and rank raw samples.
  // Never draw all raw edges — that is the spiderweb failure.
  const districtImpact = new Map<string, ImpactAgg>();
  const subImpact = new Map<string, ImpactAgg>();
  const affected = new Set<string>();
  const rawCandidates: Array<{ edge: CodeMapConnection; index: number; score: number; outgoing: boolean }> = [];
  let incoming = 0;
  let outgoing = 0;
  const selectedZone = hasSelection ? pathToZone.get(panoramaSelectedPath as string) ?? null : null;
  if (hasSelection) {
    const sel = panoramaSelectedPath as string;
    const seenPair = new Set<string>();
    packet.connections.forEach((edge, index) => {
      if (classifyEdge(edge) === 'containment') return;
      const isOut = edge.from === sel;
      const isIn = edge.to === sel;
      if (!isOut && !isIn) return;
      const other = isOut ? edge.to : edge.from;
      if (other === sel || !renderedPaths.has(other)) return;
      const pairKey = `${edge.from}->${edge.to}`;
      if (seenPair.has(pairKey)) return;
      seenPair.add(pairKey);
      affected.add(other);
      if (isOut) outgoing += 1; else incoming += 1;
      const zone = pathToZone.get(other);
      const subId = pathToSub.get(other);
      if (zone) bumpImpact(districtImpact, zone, isOut);
      if (subId) bumpImpact(subImpact, subId, isOut);
      rawCandidates.push({ edge, index, score: rawEdgeScore(edge), outgoing: isOut });
    });
  }
  const totalIncident = incoming + outgoing;
  const maxDistrictTotal = Math.max(1, ...Array.from(districtImpact.values()).map((agg) => agg.total));

  const nodes: Node[] = [];
  let selectedDotCenter: { x: number; y: number } | null = null;

  // District hulls (low z) carry their impact so the hull tints by influence.
  placements.forEach(({ x, y, box }) => {
    const agg = districtImpact.get(box.district.zone) ?? null;
    nodes.push({
      id: `district:${box.district.zone}`,
      type: 'codemapDistrict',
      position: { x, y },
      data: {
        district: box.district,
        selected: hasSelection && box.district.zone === selectedZone,
        impact: agg,
        impactIntensity: agg ? Math.min(1, agg.total / maxDistrictTotal) : 0,
        dimmed: hasSelection && !agg && box.district.zone !== selectedZone,
      },
      style: { width: box.width, height: box.height },
      zIndex: 1,
      selectable: false,
      draggable: false,
    });
  });

  // Subdistrict blocks (meso). PERFORMANCE: a district's file marks are NOT
  // individual ReactFlow nodes — that put ~1930 wrapped DOM nodes on the canvas
  // and tanked the frame rate. Instead each subdistrict carries its file list
  // and paints them as cheap <rect>s in one SVG. Only the SELECTED file gets a
  // real ReactFlow node (below) as the beacon/bundle anchor.
  let selectedFile: CodeMapFile | null = null;
  placements.forEach(({ x, y, box }) => {
    const contentX = x + PANORAMA_PAD;
    const contentY = y + PANORAMA_HEADER;
    box.subs.forEach((placement) => {
      const subId = `${box.district.zone}:${placement.sub.id}`;
      const agg = subImpact.get(subId) ?? null;
      const subX = contentX + placement.x;
      const subY = contentY + placement.y;
      // Locate the selected mark's centre (for the beacon) without emitting a
      // node per file.
      const selIndex = placement.sub.files.findIndex((file) => file.path === panoramaSelectedPath);
      if (selIndex >= 0) {
        const col = selIndex % placement.cols;
        const row = Math.floor(selIndex / placement.cols);
        const cx = subX + PANORAMA_SUB_PAD + col * PANORAMA_PITCH + PANORAMA_PITCH / 2;
        const cy = subY + PANORAMA_SUB_HEADER + PANORAMA_SUB_PAD + row * PANORAMA_PITCH + PANORAMA_PITCH / 2;
        selectedDotCenter = { x: cx, y: cy };
        selectedFile = placement.sub.files[selIndex];
      }
      nodes.push({
        id: `sub:${subId}`,
        type: 'codemapSubdistrict',
        position: { x: subX, y: subY },
        data: {
          label: placement.sub.label,
          fileCount: placement.sub.fileCount,
          impacted: Boolean(agg),
          dimmed: hasSelection && !agg,
          // Label admission: never render a truncated singleton label ("C... 1").
          // Only label clusters worth naming, plus any affected area.
          labelVisible: placement.sub.fileCount >= PANORAMA_LABEL_MIN_FILES || Boolean(agg),
          marks: placement.sub.files.map((file) => ({
            path: file.path,
            grade: file.health?.grade ?? null,
            landmark: deriveFileImportance(file) >= 12,
          })),
          cols: placement.cols,
          dotSize: PANORAMA_DOT,
          pitch: PANORAMA_PITCH,
          gridOffsetX: PANORAMA_SUB_PAD,
          gridOffsetY: PANORAMA_SUB_HEADER + PANORAMA_SUB_PAD,
          hasSelection,
          // onSelectFile / onEnterFocus injected in CodeMapFlow.
        },
        style: { width: placement.width, height: placement.height },
        zIndex: 2,
        selectable: false,
        draggable: false,
      });
    });
  });

  // The selected file's single ReactFlow node: the amber-ring mark that anchors
  // the beacon and the impact bundles.
  if (hasSelection && selectedDotCenter && selectedFile) {
    const center = selectedDotCenter as { x: number; y: number };
    const sf = selectedFile as CodeMapFile;
    nodes.push({
      id: nodeIdForPath(sf.path),
      type: 'codemapDot',
      position: { x: center.x - PANORAMA_DOT / 2, y: center.y - PANORAMA_DOT / 2 },
      data: { file: sf, landmark: deriveFileImportance(sf) >= 12, selected: true },
      style: { width: PANORAMA_DOT, height: PANORAMA_DOT },
      zIndex: 14,
    });
  }

  // Selection beacon: a large amber ring + glow centred on the selected mark so
  // the operator can find it at macro zoom (a 16px dot is invisible fitted to
  // the whole board). Pure decoration — clicks fall through.
  if (hasSelection && selectedDotCenter) {
    const beaconSize = 96;
    nodes.push({
      id: 'beacon:selected',
      type: 'codemapBeacon',
      position: {
        x: (selectedDotCenter as { x: number; y: number }).x - beaconSize / 2,
        y: (selectedDotCenter as { x: number; y: number }).y - beaconSize / 2,
      },
      data: {},
      style: { width: beaconSize, height: beaconSize },
      zIndex: 15,
      selectable: false,
      draggable: false,
    });
  }

  // --- Edge layer -----------------------------------------------------------
  // No selection: faint district-to-district corridors (the global roads).
  // Selection + Impact lens: a few routed bundles from the file to affected
  // districts, ZERO raw edges. Selection + Raw lens: a capped, ranked, calm
  // sample of exact edges.
  let edges: Edge[] = [];
  let bundleCount = 0;
  let rawShown = 0;

  if (!hasSelection) {
    // Quiet baseline roads: only the heaviest district links, very faint, so the
    // no-selection board reads as calm terrain (not a web). Real routing is the
    // selection's job.
    const renderedCorridors = codeGraphEnabled
      ? model.corridors.slice(0, PANORAMA_BASE_CORRIDORS).filter((corridor) => corridor.count >= 6)
      : [];
    edges = renderedCorridors.map((corridor, index) => {
      const tone = edgeClassTone(corridor.edgeClass);
      const width = corridor.count >= 60 ? 1.6 : corridor.count >= 20 ? 1.3 : 1;
      return {
        id: `corridor:${index}:${corridor.id}`,
        source: `district:${corridor.sourceZone}`,
        target: `district:${corridor.targetZone}`,
        type: 'default',
        ariaLabel: '',
        animated: false,
        style: { stroke: tone.color, strokeWidth: width, strokeDasharray: tone.dasharray, opacity: 0.13 },
        data: { corridor },
      } satisfies Edge;
    });
  } else if (codeGraphEnabled && lens === 'impact') {
    // Routed bundles: selected file -> each affected OTHER district, thick and
    // translucent, capped. Colour by dominant direction. No raw file edges.
    const bundles = Array.from(districtImpact.entries())
      .filter(([zone]) => zone !== selectedZone)
      .sort((a, b) => b[1].total - a[1].total)
      .slice(0, PANORAMA_IMPACT_BUNDLE_LIMIT);
    bundleCount = bundles.length;
    const selId = nodeIdForPath(panoramaSelectedPath as string);
    // Each bundle is a bright CORE over a wide translucent GLOW underlay so the
    // few routes read clearly at macro zoom over a busy field.
    edges = bundles.flatMap(([zone, agg], index) => {
      const outDominant = agg.outgoing >= agg.incoming;
      const color = outDominant ? '#fbbf24' : '#38bdf8'; // amber out / cyan in
      const core = agg.total >= 24 ? 5 : agg.total >= 8 ? 4 : 3;
      const base = { source: selId, target: `district:${zone}`, type: 'default', ariaLabel: '', animated: false };
      return [
        {
          ...base,
          id: `bundle-glow:${index}:${zone}`,
          zIndex: 16,
          style: { stroke: color, strokeWidth: core + 7, strokeLinecap: 'round', opacity: 0.16 },
          data: { bundleGlow: true },
        } satisfies Edge,
        {
          ...base,
          id: `bundle:${index}:${zone}`,
          zIndex: 18,
          label: String(agg.total),
          style: { stroke: color, strokeWidth: core, strokeLinecap: 'round', opacity: 0.95 },
          labelStyle: { fill: '#f8fafc', fontSize: 12, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' },
          labelBgStyle: { fill: '#0b0f0d', fillOpacity: 0.95 },
          data: { bundle: { zone, ...agg } },
        } satisfies Edge,
      ];
    });
  } else if (codeGraphEnabled && lens === 'raw') {
    const ranked = rawCandidates
      .slice()
      .sort((a, b) => (b.score - a.score) || (a.index - b.index))
      .slice(0, PANORAMA_RAW_EDGE_LIMIT);
    rawShown = ranked.length;
    edges = ranked.map(({ edge, index }) => {
      const stroke = edgeStroke(edge);
      return {
        ...toReactFlowEdge(edge, index, 'focus'),
        zIndex: 18,
        // Calm, not white: keep the class colour, modest opacity, thin.
        style: { stroke: stroke.color, strokeWidth: 1.2, strokeDasharray: stroke.dasharray, opacity: 0.55 },
      } satisfies Edge;
    });
  }

  const rawAvailable = totalIncident;
  const panoramaSelection: PanoramaSelectionSummary | null = hasSelection
    ? {
        selectedPath: panoramaSelectedPath as string,
        lens,
        incoming,
        outgoing,
        total: totalIncident,
        affectedDistricts: districtImpact.size,
        affectedSubdistricts: subImpact.size,
        bundles: bundleCount,
        rawShown,
        hiddenRawEdges: lens === 'raw' ? Math.max(0, rawAvailable - rawShown) : rawAvailable,
      }
    : null;

  return {
    nodes,
    edges,
    renderedFileNodes: model.renderedFiles,
    renderedGroupNodes: model.districts.length,
    hiddenEdgesByFilter: hasSelection
      ? Math.max(0, totalIncident - rawShown - bundleCount)
      : Math.max(0, model.corridors.length - edges.length),
    panoramaSummary: {
      districts: model.districts.length,
      renderedFiles: model.renderedFiles,
      hiddenFiles: model.hiddenFiles,
      corridors: hasSelection ? 0 : edges.length,
    },
    panoramaSelection,
  };
}

export function buildCodeMapLayout({
  packet,
  mode,
  focus,
  activeToggles,
  panoramaSelectedPath = null,
  panoramaLens = 'impact',
}: LayoutOptions): CodeMapLayoutResult {
  if (mode === 'focus' && focus.selectedPath) {
    const ego = buildEgoFocusLayout(packet, focus, activeToggles);
    if (ego) return ego;
  }

  if (mode === 'panorama') {
    return buildPanoramaLayout(packet, activeToggles, panoramaSelectedPath, panoramaLens);
  }

  if (mode === 'architecture') {
    return buildClusterFlowLayout(packet, activeToggles);
  }

  const base = buildDirectedNodes(packet, mode, focus, activeToggles);
  const renderedPaths = new Set(base.files.map((file) => file.path));
  const visibleConnections = filterEdges(packet, renderedPaths, mode, focus, activeToggles);
  const selectedPath = focus.selectedPath;
  const edges = visibleConnections.map((edge, index) => toReactFlowEdge(edge, index, mode, {
    hasSelection: Boolean(selectedPath),
    incident: Boolean(selectedPath) && (edge.from === selectedPath || edge.to === selectedPath),
  }));

  return {
    nodes: base.nodes,
    edges,
    renderedFileNodes: base.files.length,
    renderedGroupNodes: base.nodes.length - base.files.length,
    hiddenEdgesByFilter: Math.max(0, packet.connections.length - edges.length),
  };
}

export function describeNode(file: CodeMapFile): string {
  const parts = [
    pathLeaf(file.path),
    file.layer ?? 'layer unknown',
    `in ${file.fan_in ?? 0}`,
    `out ${file.fan_out ?? 0}`,
  ];
  const paper = overlayCount(file, 'paper_modules');
  if (paper > 0) parts.push(`${paper} paper module${paper === 1 ? '' : 's'}`);
  return parts.join(' · ');
}
