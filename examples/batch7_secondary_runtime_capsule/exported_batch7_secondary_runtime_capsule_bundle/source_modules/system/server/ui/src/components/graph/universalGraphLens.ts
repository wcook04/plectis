export type UniversalGraphFocusRole = 'selected' | 'upstream' | 'downstream' | 'context' | 'hidden';

export type UniversalGraphEdgeFocusRole =
  | 'selected'
  | 'upstream'
  | 'downstream'
  | 'context'
  | 'hidden';

export const UNIVERSAL_GRAPH_FOCUS_TIERS: Record<
  UniversalGraphFocusRole,
  { opacity: number; label: string }
> = {
  selected: { opacity: 1, label: 'Selected' },
  upstream: { opacity: 0.9, label: 'Upstream' },
  downstream: { opacity: 0.68, label: 'Downstream' },
  context: { opacity: 0.18, label: 'Context' },
  hidden: { opacity: 0.05, label: 'Hidden' },
};

export interface UniversalGraphNodeInput {
  id: string;
  label?: string | null;
  kind?: string | null;
  parentId?: string | null;
  groupId?: string | null;
  collapsed?: boolean | null;
  collapsible?: boolean | null;
}

export interface UniversalGraphEdgeInput {
  id?: string | null;
  source: string;
  target: string;
  relation?: string | null;
}

export interface UniversalGraphLensOptions {
  selectedNodeId?: string | null;
  collapsedNodeIds?: Iterable<string> | null;
}

export interface UniversalGraphLensNode extends UniversalGraphNodeInput {
  depth: number;
  childCount: number;
  visibleChildCount: number;
  descendantCount: number;
  isCollapsed: boolean;
  isHiddenByCollapse: boolean;
  isVisible: boolean;
  focusRole: UniversalGraphFocusRole;
  graphPath: string[];
}

export interface UniversalGraphLensEdge extends Required<Pick<UniversalGraphEdgeInput, 'source' | 'target'>> {
  id: string;
  relation: string | null;
  isVisible: boolean;
  isHiddenByCollapse: boolean;
  focusRole: UniversalGraphEdgeFocusRole;
}

export interface UniversalGraphLensMetrics {
  nodeCount: number;
  edgeCount: number;
  visibleNodeCount: number;
  visibleEdgeCount: number;
  collapsedNodeCount: number;
  maxDepth: number;
  kindCount: number;
  selectedNeighborCount: number;
}

export interface UniversalGraphLens {
  nodes: UniversalGraphLensNode[];
  edges: UniversalGraphLensEdge[];
  nodeById: Map<string, UniversalGraphLensNode>;
  edgeById: Map<string, UniversalGraphLensEdge>;
  selectedNodeId: string | null;
  visibleNodeIds: Set<string>;
  visibleEdgeIds: Set<string>;
  collapsedNodeIds: Set<string>;
  directUpstreamIds: Set<string>;
  directDownstreamIds: Set<string>;
  upstreamClosureIds: Set<string>;
  downstreamClosureIds: Set<string>;
  kindCounts: Map<string, number>;
  metrics: UniversalGraphLensMetrics;
}

function stableEdgeId(edge: UniversalGraphEdgeInput, index: number): string {
  return edge.id && edge.id.trim().length > 0
    ? edge.id
    : `${edge.source}->${edge.target}:${edge.relation ?? 'edge'}:${index}`;
}

function buildAdjacency(edges: UniversalGraphEdgeInput[]) {
  const outgoing = new Map<string, Set<string>>();
  const incoming = new Map<string, Set<string>>();
  for (const edge of edges) {
    if (!outgoing.has(edge.source)) outgoing.set(edge.source, new Set());
    if (!incoming.has(edge.target)) incoming.set(edge.target, new Set());
    outgoing.get(edge.source)!.add(edge.target);
    incoming.get(edge.target)!.add(edge.source);
  }
  return { outgoing, incoming };
}

function closure(start: Iterable<string>, adjacency: Map<string, Set<string>>): Set<string> {
  const out = new Set<string>();
  const stack = Array.from(start);
  while (stack.length > 0) {
    const current = stack.pop()!;
    if (out.has(current)) continue;
    out.add(current);
    for (const next of adjacency.get(current) ?? []) {
      if (!out.has(next)) stack.push(next);
    }
  }
  return out;
}

export function buildUniversalGraphLens(
  input: {
    nodes: UniversalGraphNodeInput[];
    edges: UniversalGraphEdgeInput[];
  },
  options: UniversalGraphLensOptions = {},
): UniversalGraphLens {
  const rawNodeById = new Map(input.nodes.map((node) => [node.id, node]));
  const childIdsByParent = new Map<string, string[]>();
  const collapsedNodeIds = new Set<string>(options.collapsedNodeIds ?? []);

  for (const node of input.nodes) {
    if (node.collapsed) collapsedNodeIds.add(node.id);
    if (node.parentId && rawNodeById.has(node.parentId)) {
      const children = childIdsByParent.get(node.parentId) ?? [];
      children.push(node.id);
      childIdsByParent.set(node.parentId, children);
    }
  }

  const hiddenByCollapse = new Set<string>();
  for (const collapsedId of collapsedNodeIds) {
    const stack = [...(childIdsByParent.get(collapsedId) ?? [])];
    while (stack.length > 0) {
      const id = stack.pop()!;
      if (hiddenByCollapse.has(id)) continue;
      hiddenByCollapse.add(id);
      stack.push(...(childIdsByParent.get(id) ?? []));
    }
  }

  const depthCache = new Map<string, number>();
  const pathCache = new Map<string, string[]>();
  const depthFor = (nodeId: string, seen = new Set<string>()): number => {
    if (depthCache.has(nodeId)) return depthCache.get(nodeId)!;
    if (seen.has(nodeId)) return 0;
    const node = rawNodeById.get(nodeId);
    const parentId = node?.parentId ?? null;
    const depth = parentId && rawNodeById.has(parentId)
      ? depthFor(parentId, new Set(seen).add(nodeId)) + 1
      : 0;
    depthCache.set(nodeId, depth);
    return depth;
  };
  const pathFor = (nodeId: string, seen = new Set<string>()): string[] => {
    if (pathCache.has(nodeId)) return pathCache.get(nodeId)!;
    if (seen.has(nodeId)) return [nodeId];
    const node = rawNodeById.get(nodeId);
    const parentId = node?.parentId ?? null;
    const path = parentId && rawNodeById.has(parentId)
      ? [...pathFor(parentId, new Set(seen).add(nodeId)), nodeId]
      : [nodeId];
    pathCache.set(nodeId, path);
    return path;
  };

  const { incoming, outgoing } = buildAdjacency(input.edges);
  const selectedNodeId =
    options.selectedNodeId && rawNodeById.has(options.selectedNodeId)
      ? options.selectedNodeId
      : null;
  const directUpstreamIds = selectedNodeId
    ? new Set(incoming.get(selectedNodeId) ?? [])
    : new Set<string>();
  const directDownstreamIds = selectedNodeId
    ? new Set(outgoing.get(selectedNodeId) ?? [])
    : new Set<string>();
  const upstreamClosureIds = selectedNodeId ? closure(directUpstreamIds, incoming) : new Set<string>();
  const downstreamClosureIds = selectedNodeId
    ? closure(directDownstreamIds, outgoing)
    : new Set<string>();

  const childIdsByParentSet = childIdsByParentAsSet(childIdsByParent);
  const kindCounts = new Map<string, number>();
  const nodes: UniversalGraphLensNode[] = input.nodes.map((node) => {
    const kind = node.kind ?? 'unknown';
    kindCounts.set(kind, (kindCounts.get(kind) ?? 0) + 1);
    const isHiddenByCollapse = hiddenByCollapse.has(node.id);
    const isVisible = !isHiddenByCollapse;
    const childIds = childIdsByParent.get(node.id) ?? [];
    const visibleChildCount = childIds.filter((id) => !hiddenByCollapse.has(id)).length;
    let focusRole: UniversalGraphFocusRole = selectedNodeId ? 'context' : 'selected';
    if (isHiddenByCollapse) focusRole = 'hidden';
    else if (selectedNodeId) {
      if (node.id === selectedNodeId) focusRole = 'selected';
      else if (upstreamClosureIds.has(node.id)) focusRole = 'upstream';
      else if (downstreamClosureIds.has(node.id)) focusRole = 'downstream';
    }
    return {
      ...node,
      depth: depthFor(node.id),
      childCount: childIds.length,
      visibleChildCount,
      descendantCount: closure(childIds, childIdsByParentSet).size,
      isCollapsed: collapsedNodeIds.has(node.id),
      isHiddenByCollapse,
      isVisible,
      focusRole,
      graphPath: pathFor(node.id),
    };
  });

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const visibleNodeIds = new Set(nodes.filter((node) => node.isVisible).map((node) => node.id));

  const edges: UniversalGraphLensEdge[] = input.edges.map((edge, index) => {
    const id = stableEdgeId(edge, index);
    const isHiddenByCollapse = !visibleNodeIds.has(edge.source) || !visibleNodeIds.has(edge.target);
    let focusRole: UniversalGraphEdgeFocusRole = selectedNodeId ? 'context' : 'selected';
    if (isHiddenByCollapse) focusRole = 'hidden';
    else if (selectedNodeId) {
      if (edge.source === selectedNodeId || edge.target === selectedNodeId) focusRole = 'selected';
      else if (upstreamClosureIds.has(edge.source) || upstreamClosureIds.has(edge.target)) {
        focusRole = 'upstream';
      } else if (downstreamClosureIds.has(edge.source) || downstreamClosureIds.has(edge.target)) {
        focusRole = 'downstream';
      }
    }
    return {
      id,
      source: edge.source,
      target: edge.target,
      relation: edge.relation ?? null,
      isVisible: !isHiddenByCollapse,
      isHiddenByCollapse,
      focusRole,
    };
  });

  const edgeById = new Map(edges.map((edge) => [edge.id, edge]));
  const visibleEdgeIds = new Set(edges.filter((edge) => edge.isVisible).map((edge) => edge.id));
  const maxDepth = nodes.reduce((max, node) => Math.max(max, node.depth), 0);

  return {
    nodes,
    edges,
    nodeById,
    edgeById,
    selectedNodeId,
    visibleNodeIds,
    visibleEdgeIds,
    collapsedNodeIds,
    directUpstreamIds,
    directDownstreamIds,
    upstreamClosureIds,
    downstreamClosureIds,
    kindCounts,
    metrics: {
      nodeCount: nodes.length,
      edgeCount: edges.length,
      visibleNodeCount: visibleNodeIds.size,
      visibleEdgeCount: visibleEdgeIds.size,
      collapsedNodeCount: collapsedNodeIds.size,
      maxDepth,
      kindCount: kindCounts.size,
      selectedNeighborCount: directUpstreamIds.size + directDownstreamIds.size,
    },
  };
}

function childIdsByParentAsSet(childIdsByParent: Map<string, string[]>): Map<string, Set<string>> {
  const out = new Map<string, Set<string>>();
  for (const [parent, children] of childIdsByParent) out.set(parent, new Set(children));
  return out;
}

export function universalGraphFocusOpacity(
  role: UniversalGraphFocusRole | undefined,
  selectedNodeId?: string | null,
): number {
  if (!selectedNodeId || !role) return 1;
  return UNIVERSAL_GRAPH_FOCUS_TIERS[role]?.opacity ?? 1;
}
