import type { Edge, Node } from 'reactflow';

export const CAP_CARTOGRAPHY_SHADOW_RENDER_SCHEMA_VERSION =
  'cap_cartography_shadow_render_model_v0';

const REQUIRED_BLOCKED_ACTIONS = [
  'create_cap',
  'mutate_cap',
  'edit_edge',
  'infer_title_semantics',
] as const;

type UnknownRecord = Record<string, unknown>;

export interface CapCartographyElementActions {
  cap_creation_supported?: boolean;
  mutation_supported?: boolean;
  frontend_actionable_cap_mutation_supported?: boolean;
  inspect_supported?: boolean;
  source_route_supported?: boolean;
}

export interface CapCartographySourceRouteMetadata extends UnknownRecord {
  task_ledger_card?: string;
  projection_path?: string;
  source_view?: string;
}

export interface CapCartographyClusterElement {
  id: string;
  kind?: string;
  label?: string;
  member_count?: number;
  representative_ids?: string[];
  semantic_classes?: UnknownRecord;
  source_route_metadata?: CapCartographySourceRouteMetadata;
  actions?: CapCartographyElementActions;
}

export interface CapCartographyNodeElement {
  id: string;
  kind?: string;
  label?: string;
  node_kind?: string;
  semantic_classes?: UnknownRecord;
  source_route_metadata?: CapCartographySourceRouteMetadata;
  source_refs?: string[];
  lineage?: UnknownRecord;
  actions?: CapCartographyElementActions;
}

export interface CapCartographyEdgeElement {
  id: string;
  kind?: string;
  source: string;
  target: string;
  edge_kind?: string;
  confidence?: string;
  source_ref?: string;
  semantic_classes?: UnknownRecord;
  actions?: CapCartographyElementActions;
}

export interface CapCartographyDrilldownElement {
  id: string;
  kind?: string;
  cluster_kind?: string;
  value?: string;
  member_count?: number;
  overflow_member_count?: number;
  representative_ids?: string[];
  source_route_metadata?: CapCartographySourceRouteMetadata;
  actions?: CapCartographyElementActions;
}

export interface CapCartographyUnclassifiedElement {
  id: string;
  kind?: string;
  title?: string;
  state?: string;
  classification_status?: string;
  candidate_fields_to_check?: string[];
  source_route_metadata?: CapCartographySourceRouteMetadata;
  actions?: CapCartographyElementActions;
}

export interface CapCartographyExpositionSpecimen {
  schema_version: string;
  source_schema_version?: string;
  source_ref?: string;
  source_view?: string;
  mode?: string;
  status?: {
    graph_ready?: boolean;
    complete?: boolean;
    bounded?: boolean;
    edge_limit_hit?: boolean;
    warnings?: string[];
  };
  frontend_posture?: {
    mode?: string;
    cap_creation_supported?: boolean;
    mutation_supported?: boolean;
    frontend_actionable_cap_mutation_supported?: boolean;
    source_route_supported?: boolean;
  };
  overview_tiles?: Array<{ id: string; value: unknown }>;
  cluster_elements?: CapCartographyClusterElement[];
  node_elements?: CapCartographyNodeElement[];
  edge_elements?: CapCartographyEdgeElement[];
  drilldown_elements?: CapCartographyDrilldownElement[];
  unclassified_elements?: CapCartographyUnclassifiedElement[];
  legend?: UnknownRecord;
  blocked_actions?: string[];
  integrity?: {
    orphan_renderer_edge_count?: number;
    omitted_renderer_edge_count?: number;
    renderer_inferred_semantic_count?: number;
    rendered_node_count?: number;
    rendered_cluster_count?: number;
    rendered_edge_count?: number;
  };
}

export interface CapCartographyShadowNodeData {
  element_kind: 'cluster' | 'cap' | 'unclassified_cap';
  source_element_id: string;
  label: string;
  semantic_classes: UnknownRecord;
  source_route_metadata: CapCartographySourceRouteMetadata | null;
  actions: CapCartographyElementActions;
  representative_ids?: string[];
  member_count?: number;
  node_kind?: string;
  lineage?: UnknownRecord;
  source_refs?: string[];
  candidate_fields_to_check?: string[];
}

export interface CapCartographyShadowEdgeData {
  source_element_id: string;
  edge_kind: string;
  confidence: string | null;
  semantic_classes: UnknownRecord;
  source_ref: string | null;
  actions: CapCartographyElementActions;
}

export type CapCartographyShadowNode = Node<
  CapCartographyShadowNodeData,
  'capCluster' | 'capNode' | 'unclassifiedCap'
>;

export type CapCartographyShadowEdge = Edge<CapCartographyShadowEdgeData>;

export interface CapCartographyShadowRenderModel {
  schema_version: typeof CAP_CARTOGRAPHY_SHADOW_RENDER_SCHEMA_VERSION;
  source_packet_schema: 'cap_cartography_exposition_specimen_v0';
  source_schema_version: string | null;
  source_ref: string | null;
  source_view: string | null;
  mode: 'observe_only';
  status: {
    graph_ready: boolean;
    complete: boolean;
    bounded: boolean;
    edge_limit_hit: boolean;
    warnings: string[];
    omitted_edge_count: number;
    unclassified_count: number;
  };
  nodes: CapCartographyShadowNode[];
  edges: CapCartographyShadowEdge[];
  legend: UnknownRecord;
  blocked_actions: string[];
  available_actions: string[];
  drilldown: {
    clusters: CapCartographyDrilldownElement[];
    unclassified: CapCartographyUnclassifiedElement[];
  };
  source_route_samples: {
    cluster: CapCartographySourceRouteMetadata | null;
    cap_node: CapCartographySourceRouteMetadata | null;
    edge_source_ref: string | null;
    drilldown: CapCartographySourceRouteMetadata | null;
    unclassified: CapCartographySourceRouteMetadata | null;
  };
  integrity: {
    orphan_edge_count: number;
    omitted_renderer_edge_count: number;
    renderer_inferred_semantic_count: number;
    rendered_cluster_count: number;
    rendered_cap_node_count: number;
    rendered_unclassified_node_count: number;
    rendered_edge_count: number;
  };
}

function hasOwnRecord(value: unknown): value is UnknownRecord {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function numberTile(
  specimen: CapCartographyExpositionSpecimen,
  id: string,
  fallback = 0,
): number {
  const tile = specimen.overview_tiles?.find((item) => item.id === id);
  return typeof tile?.value === 'number' && Number.isFinite(tile.value) ? tile.value : fallback;
}

function routeOrNull(value: unknown): CapCartographySourceRouteMetadata | null {
  return hasOwnRecord(value) ? (value as CapCartographySourceRouteMetadata) : null;
}

function observeOnlyActions(actions: CapCartographyElementActions | undefined): CapCartographyElementActions {
  return {
    cap_creation_supported: actions?.cap_creation_supported === true,
    mutation_supported: actions?.mutation_supported === true,
    frontend_actionable_cap_mutation_supported:
      actions?.frontend_actionable_cap_mutation_supported === true,
    inspect_supported: actions?.inspect_supported === true,
    source_route_supported: actions?.source_route_supported === true,
  };
}

function isMutationActionAvailable(actions: CapCartographyElementActions): boolean {
  return (
    actions.cap_creation_supported === true ||
    actions.mutation_supported === true ||
    actions.frontend_actionable_cap_mutation_supported === true
  );
}

function clusterNode(cluster: CapCartographyClusterElement, index: number): CapCartographyShadowNode {
  const route = routeOrNull(cluster.source_route_metadata);
  return {
    id: cluster.id,
    type: 'capCluster',
    position: { x: 0, y: index * 96 },
    data: {
      element_kind: 'cluster',
      source_element_id: cluster.id,
      label: cluster.label ?? cluster.id,
      semantic_classes: cluster.semantic_classes ?? {},
      source_route_metadata: route,
      actions: observeOnlyActions(cluster.actions),
      representative_ids: stringArray(cluster.representative_ids),
      member_count: typeof cluster.member_count === 'number' ? cluster.member_count : undefined,
    },
    draggable: false,
  };
}

function capNode(node: CapCartographyNodeElement, index: number): CapCartographyShadowNode {
  const route = routeOrNull(node.source_route_metadata);
  return {
    id: node.id,
    type: 'capNode',
    position: { x: 360 + (index % 3) * 280, y: Math.floor(index / 3) * 112 },
    data: {
      element_kind: 'cap',
      source_element_id: node.id,
      label: node.label ?? node.id,
      semantic_classes: node.semantic_classes ?? {},
      source_route_metadata: route,
      actions: observeOnlyActions(node.actions),
      node_kind: node.node_kind,
      lineage: node.lineage,
      source_refs: stringArray(node.source_refs),
    },
    draggable: false,
  };
}

function unclassifiedNode(
  row: CapCartographyUnclassifiedElement,
  index: number,
): CapCartographyShadowNode {
  const route = routeOrNull(row.source_route_metadata);
  return {
    id: `unclassified:${row.id}`,
    type: 'unclassifiedCap',
    position: { x: 1240, y: index * 96 },
    data: {
      element_kind: 'unclassified_cap',
      source_element_id: row.id,
      label: row.title ?? row.id,
      semantic_classes: {
        classification_status: row.classification_status ?? 'unclassified',
        state: row.state ?? null,
      },
      source_route_metadata: route,
      actions: observeOnlyActions(row.actions),
      candidate_fields_to_check: stringArray(row.candidate_fields_to_check),
    },
    draggable: false,
  };
}

function rfEdge(edge: CapCartographyEdgeElement): CapCartographyShadowEdge {
  return {
    id: edge.id,
    type: 'capEdge',
    source: edge.source,
    target: edge.target,
    data: {
      source_element_id: edge.id,
      edge_kind: edge.edge_kind ?? 'unknown',
      confidence: edge.confidence ?? null,
      semantic_classes: edge.semantic_classes ?? {},
      source_ref: typeof edge.source_ref === 'string' ? edge.source_ref : null,
      actions: observeOnlyActions(edge.actions),
    },
    animated: false,
  };
}

function firstRoute<T extends { source_route_metadata?: CapCartographySourceRouteMetadata }>(
  rows: T[] | undefined,
): CapCartographySourceRouteMetadata | null {
  return routeOrNull(rows?.find((row) => hasOwnRecord(row.source_route_metadata))?.source_route_metadata);
}

export function capCartographySpecimenToGraphElements(
  specimen: CapCartographyExpositionSpecimen,
): CapCartographyShadowRenderModel {
  if (specimen.schema_version !== 'cap_cartography_exposition_specimen_v0') {
    throw new Error(
      `Unsupported cap cartography specimen schema: ${specimen.schema_version || 'unknown'}`,
    );
  }

  const blockedActions = Array.from(
    new Set([...REQUIRED_BLOCKED_ACTIONS, ...stringArray(specimen.blocked_actions)]),
  );
  const clusters = specimen.cluster_elements ?? [];
  const capNodes = specimen.node_elements ?? [];
  const unclassifiedRows = specimen.unclassified_elements ?? [];
  const renderedNodes: CapCartographyShadowNode[] = [
    ...clusters.map(clusterNode),
    ...capNodes.map(capNode),
    ...unclassifiedRows.map(unclassifiedNode),
  ];
  const nodeIds = new Set(renderedNodes.map((node) => node.id));

  let omittedRendererEdgeCount = 0;
  const renderedEdges: CapCartographyShadowEdge[] = [];
  for (const edge of specimen.edge_elements ?? []) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
      omittedRendererEdgeCount += 1;
      continue;
    }
    renderedEdges.push(rfEdge(edge));
  }

  const mutationActionCount =
    renderedNodes.filter((node) => isMutationActionAvailable(node.data.actions)).length +
    renderedEdges.filter((edge) => isMutationActionAvailable(edge.data?.actions ?? {})).length;

  const edgeSourceRef =
    renderedEdges.find((edge) => typeof edge.data?.source_ref === 'string')?.data?.source_ref ?? null;

  return {
    schema_version: CAP_CARTOGRAPHY_SHADOW_RENDER_SCHEMA_VERSION,
    source_packet_schema: 'cap_cartography_exposition_specimen_v0',
    source_schema_version: specimen.source_schema_version ?? null,
    source_ref: specimen.source_ref ?? null,
    source_view: specimen.source_view ?? null,
    mode: 'observe_only',
    status: {
      graph_ready: specimen.status?.graph_ready === true,
      complete: specimen.status?.complete === true,
      bounded: specimen.status?.bounded === true,
      edge_limit_hit: specimen.status?.edge_limit_hit === true,
      warnings: stringArray(specimen.status?.warnings),
      omitted_edge_count: numberTile(specimen, 'omitted_edge_count'),
      unclassified_count: numberTile(specimen, 'unclassified_count'),
    },
    nodes: renderedNodes,
    edges: renderedEdges,
    legend: specimen.legend ?? {},
    blocked_actions: blockedActions,
    available_actions:
      specimen.frontend_posture?.source_route_supported === true ? ['inspect_source_route'] : [],
    drilldown: {
      clusters: specimen.drilldown_elements ?? [],
      unclassified: unclassifiedRows,
    },
    source_route_samples: {
      cluster: firstRoute(clusters),
      cap_node: firstRoute(capNodes),
      edge_source_ref: edgeSourceRef,
      drilldown: firstRoute(specimen.drilldown_elements),
      unclassified: firstRoute(unclassifiedRows),
    },
    integrity: {
      orphan_edge_count: 0,
      omitted_renderer_edge_count: omittedRendererEdgeCount,
      renderer_inferred_semantic_count:
        Number(specimen.integrity?.renderer_inferred_semantic_count ?? 0) + mutationActionCount,
      rendered_cluster_count: clusters.length,
      rendered_cap_node_count: capNodes.length,
      rendered_unclassified_node_count: unclassifiedRows.length,
      rendered_edge_count: renderedEdges.length,
    },
  };
}
