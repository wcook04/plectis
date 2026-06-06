import { buildLayerGroups, classifyEdge } from './codeMapGraphModel';
import type {
  ClusterFlowEdge,
  ClusterFlowModel,
  ClusterFlowNode,
  ClusterFlowZone,
  ClusterFlowZoneEdge,
  ClusterFlowZoneKey,
  CodeMapConnection,
  CodeMapPacket,
  EdgeClass,
} from './types';

export const CLUSTER_FLOW_MAX_NODES = 32;
export const CLUSTER_FLOW_MAX_EDGES = 36;
export const CLUSTER_FLOW_MAX_PER_ZONE = 6;
export const CLUSTER_FLOW_MAX_ZONES = 9;
const SAMPLE_EDGES_PER_AGGREGATE = 5;

const edgeClassRank: Record<EdgeClass, number> = {
  dependency: 0,
  control: 1,
  verification: 2,
  affinity: 3,
  containment: 4,
  unknown: 5,
};

const ZONE_ORDER: ClusterFlowZoneKey[] = [
  'kernel_commands',
  'pipeline',
  'agent_runtime',
  'navigation',
  'standards',
  'core_runtime',
  'frontend',
  'tools_codex_annex',
  'support',
];

const ZONE_LABELS: Record<ClusterFlowZoneKey, string> = {
  kernel_commands: 'Kernel commands',
  pipeline: 'Pipeline',
  agent_runtime: 'Agent runtime',
  navigation: 'Navigation / hologram',
  standards: 'Standards / compliance',
  core_runtime: 'Core runtime',
  frontend: 'Frontend / server UI',
  tools_codex_annex: 'Tools / codex / annex',
  support: 'Support',
};

export function zoneForCluster(cluster: ClusterFlowNode): ClusterFlowZoneKey {
  const text = `${cluster.layer} ${cluster.id} ${cluster.label}`.toLowerCase();
  if (text.includes('command')) return 'kernel_commands';
  if (text.includes('pipeline') || text.includes('stage_')) return 'pipeline';
  if (text.includes('agent')) return 'agent_runtime';
  if (
    text.includes('navigation') ||
    text.includes('hologram') ||
    text.includes('kernel_nav')
  ) return 'navigation';
  if (
    text.includes('compliance') ||
    text.includes('standard') ||
    text.includes('codex')
  ) return 'standards';
  if (
    text.includes('core') ||
    text.includes('bridge') ||
    text.includes('controller') ||
    text.includes('metabolism')
  ) return 'core_runtime';
  if (
    text.includes('server/ui') ||
    text.includes('frontend') ||
    text.includes('component') ||
    text.includes('page')
  ) return 'frontend';
  if (text.includes('tools') || text.includes('annex')) return 'tools_codex_annex';
  return 'support';
}

export function zoneLabel(key: ClusterFlowZoneKey): string {
  return ZONE_LABELS[key];
}

const SAMPLE_PATHS_PER_CLUSTER = 6;

function clusterNodeFromCluster(
  cluster: {
    id: string;
    label: string;
    files: Array<{ path: string; fan_in?: number | null; fan_out?: number | null }>;
    totalFiles: number;
    warningCount: number;
    overlayCount: number;
    importance: number;
    representativeFiles: Array<{ path: string }>;
  },
  layerId: string,
): ClusterFlowNode {
  const fanIns = cluster.files.map((file) => Number(file.fan_in ?? 0));
  const fanOuts = cluster.files.map((file) => Number(file.fan_out ?? 0));
  const orderedSamplePaths = [
    ...cluster.representativeFiles.map((file) => file.path),
    ...cluster.files.map((file) => file.path),
  ];
  const dedupedSamplePaths: string[] = [];
  const seen = new Set<string>();
  for (const path of orderedSamplePaths) {
    if (!path || seen.has(path)) continue;
    seen.add(path);
    dedupedSamplePaths.push(path);
    if (dedupedSamplePaths.length >= SAMPLE_PATHS_PER_CLUSTER) break;
  }
  const draft: Omit<ClusterFlowNode, 'zoneKey' | 'zoneLabel'> = {
    id: cluster.id,
    label: cluster.label,
    layer: layerId,
    fileCount: cluster.totalFiles,
    warningCount: cluster.warningCount,
    overlayCount: cluster.overlayCount,
    totalFanIn: fanIns.reduce((sum, value) => sum + value, 0),
    totalFanOut: fanOuts.reduce((sum, value) => sum + value, 0),
    maxFanIn: fanIns.length ? Math.max(...fanIns) : 0,
    maxFanOut: fanOuts.length ? Math.max(...fanOuts) : 0,
    importance: cluster.importance,
    representativePath:
      cluster.representativeFiles[0]?.path ?? cluster.files[0]?.path ?? null,
    samplePaths: dedupedSamplePaths,
    hiddenFileCount: Math.max(0, cluster.totalFiles - dedupedSamplePaths.length),
  };
  const zoneKey = zoneForCluster({
    ...draft,
    zoneKey: 'support',
    zoneLabel: ZONE_LABELS.support,
  } as ClusterFlowNode);
  return {
    ...draft,
    zoneKey,
    zoneLabel: ZONE_LABELS[zoneKey],
  };
}

function sortClustersWithinZone(left: ClusterFlowNode, right: ClusterFlowNode): number {
  if (right.importance !== left.importance) return right.importance - left.importance;
  if (right.warningCount !== left.warningCount) return right.warningCount - left.warningCount;
  if (right.totalFanIn !== left.totalFanIn) return right.totalFanIn - left.totalFanIn;
  return left.label.localeCompare(right.label);
}

export function buildClusterFlowModel(
  packet: CodeMapPacket | null,
  options: {
    maxClusters?: number;
    maxEdges?: number;
    maxPerZone?: number;
    maxZones?: number;
  } = {},
): ClusterFlowModel {
  if (!packet) {
    return {
      zones: [],
      clusterEdges: [],
      zoneEdges: [],
      visibleClusters: 0,
      visibleZones: 0,
      hiddenClusters: 0,
      visibleEdges: 0,
      hiddenEdges: 0,
    };
  }
  const maxClusters = options.maxClusters ?? CLUSTER_FLOW_MAX_NODES;
  const maxEdges = options.maxEdges ?? CLUSTER_FLOW_MAX_EDGES;
  const maxPerZone = options.maxPerZone ?? CLUSTER_FLOW_MAX_PER_ZONE;
  const maxZones = options.maxZones ?? CLUSTER_FLOW_MAX_ZONES;

  const layers = buildLayerGroups(packet.files);
  const pathToClusterId = new Map<string, string>();
  const allClusters: ClusterFlowNode[] = [];
  layers.forEach((layer) => {
    layer.clusters.forEach((cluster) => {
      allClusters.push(clusterNodeFromCluster(cluster, layer.id));
      cluster.files.forEach((file) => {
        pathToClusterId.set(file.path, cluster.id);
      });
    });
  });

  // Bucket every cluster by zone first; zone caps are applied per bucket.
  const clustersByZone = new Map<ClusterFlowZoneKey, ClusterFlowNode[]>();
  allClusters.forEach((cluster) => {
    const zone = zoneForCluster(cluster);
    if (!clustersByZone.has(zone)) clustersByZone.set(zone, []);
    clustersByZone.get(zone)!.push(cluster);
  });

  const populatedZones = ZONE_ORDER.filter((key) => (clustersByZone.get(key) ?? []).length > 0)
    .slice(0, maxZones);
  // Sort each zone's pool once.
  const pools = new Map<ClusterFlowZoneKey, ClusterFlowNode[]>();
  populatedZones.forEach((key) => {
    pools.set(key, (clustersByZone.get(key) ?? []).slice().sort(sortClustersWithinZone));
  });

  // Two-pass fair allocation so later zones never starve while earlier zones
  // greedily take the whole budget:
  //   pass 1: every populated zone gets at least 1 visible cluster (capped)
  //   pass 2: round-robin remaining budget by zone importance (sum of pool
  //           importance) until either maxClusters or per-zone caps fill.
  const visibleByZone = new Map<ClusterFlowZoneKey, ClusterFlowNode[]>();
  populatedZones.forEach((key) => {
    const pool = pools.get(key)!;
    visibleByZone.set(key, pool.length > 0 ? pool.slice(0, 1) : []);
  });
  const zoneImportance = (key: ClusterFlowZoneKey): number =>
    (pools.get(key) ?? []).reduce((sum, cluster) => sum + cluster.importance, 0);
  const zonesByImportance = populatedZones
    .slice()
    .sort((a, b) => zoneImportance(b) - zoneImportance(a));
  let remaining = Math.max(0, maxClusters - visibleByZone.size);
  let progress = true;
  while (remaining > 0 && progress) {
    progress = false;
    for (const key of zonesByImportance) {
      if (remaining <= 0) break;
      const current = visibleByZone.get(key)!;
      if (current.length >= maxPerZone) continue;
      const pool = pools.get(key)!;
      const next = pool[current.length];
      if (!next) continue;
      current.push(next);
      remaining -= 1;
      progress = true;
    }
  }

  const visibleZones: ClusterFlowZone[] = [];
  let visibleClusterCount = 0;
  let hiddenClusterCount = 0;
  const clusterIdToZone = new Map<string, ClusterFlowZoneKey>();
  const visibleClusterIds = new Set<string>();

  populatedZones.forEach((key) => {
    const visible = visibleByZone.get(key) ?? [];
    const pool = pools.get(key) ?? [];
    const hidden = pool.length - visible.length;
    visibleClusterCount += visible.length;
    hiddenClusterCount += hidden;
    visible.forEach((cluster) => {
      clusterIdToZone.set(cluster.id, key);
      visibleClusterIds.add(cluster.id);
    });
    visibleZones.push({
      key,
      label: zoneLabel(key),
      clusters: visible,
      totalFiles: visible.reduce((sum, cluster) => sum + cluster.fileCount, 0),
      totalFanIn: visible.reduce((sum, cluster) => sum + cluster.totalFanIn, 0),
      totalFanOut: visible.reduce((sum, cluster) => sum + cluster.totalFanOut, 0),
      warningCount: visible.reduce((sum, cluster) => sum + cluster.warningCount, 0),
      overlayCount: visible.reduce((sum, cluster) => sum + cluster.overlayCount, 0),
      hiddenClusterCount: hidden,
    });
  });

  // Cluster-to-cluster aggregates (kept for drawer surfaces; not used as the
  // default rendered edges).
  const clusterAggregates = new Map<string, ClusterFlowEdge>();
  // Zone-to-zone aggregates (the default rendered edge set).
  const zoneAggregates = new Map<string, ClusterFlowZoneEdge>();

  packet.connections.forEach((connection: CodeMapConnection) => {
    const klass = classifyEdge(connection);
    if (klass === 'containment' || klass === 'unknown' || klass === 'affinity') return;
    const sourceCluster = pathToClusterId.get(connection.from);
    const targetCluster = pathToClusterId.get(connection.to);
    if (!sourceCluster || !targetCluster) return;
    if (sourceCluster === targetCluster) return;

    // Cluster aggregate (always recorded for drawer-side use).
    const clusterKey = `${sourceCluster}->${targetCluster}:${klass}`;
    const clusterExisting = clusterAggregates.get(clusterKey);
    if (clusterExisting) {
      clusterExisting.count += 1;
      if (connection.confidence === 'high') clusterExisting.highConfidenceCount += 1;
      else if (connection.confidence === 'medium') clusterExisting.mediumConfidenceCount += 1;
      else if (connection.confidence === 'low') clusterExisting.lowConfidenceCount += 1;
      if (clusterExisting.sampleEdges.length < SAMPLE_EDGES_PER_AGGREGATE) {
        clusterExisting.sampleEdges.push(connection);
      }
    } else {
      clusterAggregates.set(clusterKey, {
        id: clusterKey,
        sourceClusterId: sourceCluster,
        targetClusterId: targetCluster,
        edgeClass: klass,
        count: 1,
        highConfidenceCount: connection.confidence === 'high' ? 1 : 0,
        mediumConfidenceCount: connection.confidence === 'medium' ? 1 : 0,
        lowConfidenceCount: connection.confidence === 'low' ? 1 : 0,
        sampleEdges: [connection],
      });
    }

    // Zone aggregate: skip if either endpoint cluster isn't in the visible
    // set, or both endpoints are in the same zone (no same-zone default edges).
    if (!visibleClusterIds.has(sourceCluster) || !visibleClusterIds.has(targetCluster)) return;
    const sourceZone = clusterIdToZone.get(sourceCluster)!;
    const targetZone = clusterIdToZone.get(targetCluster)!;
    if (sourceZone === targetZone) return;
    const zoneKey = `${sourceZone}->${targetZone}:${klass}`;
    const zoneExisting = zoneAggregates.get(zoneKey);
    if (zoneExisting) {
      zoneExisting.count += 1;
      if (connection.confidence === 'high') zoneExisting.highConfidenceCount += 1;
      else if (connection.confidence === 'medium') zoneExisting.mediumConfidenceCount += 1;
      else if (connection.confidence === 'low') zoneExisting.lowConfidenceCount += 1;
      if (zoneExisting.sampleEdges.length < SAMPLE_EDGES_PER_AGGREGATE) {
        zoneExisting.sampleEdges.push(connection);
      }
    } else {
      zoneAggregates.set(zoneKey, {
        id: zoneKey,
        sourceZone,
        targetZone,
        sourceZoneLabel: ZONE_LABELS[sourceZone],
        targetZoneLabel: ZONE_LABELS[targetZone],
        edgeClass: klass,
        count: 1,
        highConfidenceCount: connection.confidence === 'high' ? 1 : 0,
        mediumConfidenceCount: connection.confidence === 'medium' ? 1 : 0,
        lowConfidenceCount: connection.confidence === 'low' ? 1 : 0,
        sampleEdges: [connection],
      });
    }
  });

  const sortedZoneEdges = Array.from(zoneAggregates.values()).sort((left, right) => {
    if (right.count !== left.count) return right.count - left.count;
    if (right.highConfidenceCount !== left.highConfidenceCount) {
      return right.highConfidenceCount - left.highConfidenceCount;
    }
    const classDelta = edgeClassRank[left.edgeClass] - edgeClassRank[right.edgeClass];
    if (classDelta !== 0) return classDelta;
    return left.id.localeCompare(right.id);
  });
  const visibleZoneEdges = sortedZoneEdges.slice(0, maxEdges);

  const sortedClusterEdges = Array.from(clusterAggregates.values()).sort((left, right) => {
    if (right.count !== left.count) return right.count - left.count;
    return left.id.localeCompare(right.id);
  });

  return {
    zones: visibleZones,
    clusterEdges: sortedClusterEdges,
    zoneEdges: visibleZoneEdges,
    visibleClusters: visibleClusterCount,
    visibleZones: visibleZones.length,
    hiddenClusters: hiddenClusterCount,
    visibleEdges: visibleZoneEdges.length,
    hiddenEdges: Math.max(0, sortedZoneEdges.length - visibleZoneEdges.length),
  };
}
