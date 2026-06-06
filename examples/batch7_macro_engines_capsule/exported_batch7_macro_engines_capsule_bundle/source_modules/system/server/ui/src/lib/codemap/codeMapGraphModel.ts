import {
  overlayCount,
  pathLeaf,
  totalOverlayCount,
  warningCount,
} from './codeMapSelectors';
import type {
  ClusterGroup,
  CodeMapConnection,
  CodeMapFile,
  CodeMapMode,
  EdgeClass,
  LayerGroup,
} from './types';

const GLOBAL_REPRESENTATIVES_PER_CLUSTER = 7;
const NON_GLOBAL_REPRESENTATIVES_PER_CLUSTER = 18;

export function classifyEdge(edge: CodeMapConnection): EdgeClass {
  switch (edge.kind) {
    case 'same_group':
      return 'containment';
    case 'related':
      return 'affinity';
    case 'import':
    case 'internal_import':
    case 'call':
    case 'dependent':
    case 'blast_transitive':
      return 'dependency';
    case 'escalates_to':
      return 'control';
    case 'test_neighbor':
      return 'verification';
    default:
      return 'unknown';
  }
}

export function deriveFileImportance(file: CodeMapFile): number {
  const fanIn = Number(file.fan_in ?? 0);
  const fanOut = Number(file.fan_out ?? 0);
  const warnings = warningCount(file);
  const paper = overlayCount(file, 'paper_modules');
  const routes = overlayCount(file, 'semantic_routes');
  const annex = overlayCount(file, 'annex_patterns');
  const frontend = overlayCount(file, 'frontend_views');
  const grade = String(file.health?.grade ?? '').toUpperCase();
  const gradePenalty =
    grade.startsWith('F') ? 8 :
      grade.startsWith('D') ? 5 :
        grade.startsWith('C') ? 2 :
          0;

  return (
    Math.log1p(fanIn) * 5 +
    Math.log1p(fanOut) * 3 +
    warnings * 4 +
    paper * 2 +
    routes * 2 +
    annex * 2 +
    frontend * 2 +
    gradePenalty
  );
}

function normalizeLayer(layer: string | null | undefined): string {
  return String(layer || 'unknown').trim() || 'unknown';
}

function pathStem(path: string): string {
  const leaf = pathLeaf(path);
  return leaf.replace(/\.[^.]+$/, '');
}

function uiSubcluster(parts: string[]): string {
  const prefix = 'system/server/ui';
  if (parts[3] === 'src') {
    const area = parts[4] || 'src';
    const next = parts[5];
    if (!next) return `${prefix}/src/${area}`;
    if (next === '__tests__') return `${prefix}/src/${area}/__tests__`;
    if (next.includes('.')) return `${prefix}/src/${area}/${pathStem(next)}`;
    return `${prefix}/src/${area}/${next}`;
  }
  if (parts[3] === 'remotion' && parts[4] === 'src') {
    const area = parts[5] || 'src';
    const next = parts[6];
    if (!next) return `${prefix}/remotion/src/${area}`;
    if (next === '__tests__') return `${prefix}/remotion/src/${area}/__tests__`;
    if (next.includes('.')) return `${prefix}/remotion/src/${area}/${pathStem(next)}`;
    return `${prefix}/remotion/src/${area}/${next}`;
  }
  if (parts[3]) return `${prefix}/${pathStem(parts[3])}`;
  return prefix;
}

export function clusterKeyForFile(file: CodeMapFile): string {
  const path = file.path;
  const parts = path.split('/').filter(Boolean);
  if (parts.length <= 1) return normalizeLayer(file.layer);

  if (parts[0] === 'system' && parts[1] === 'lib') {
    if (parts[2] === 'kernel' && parts[3]) return 'system/lib/kernel/' + parts[3];
    if (parts[2]?.startsWith('kernel_nav')) return 'system/lib/kernel_navigation';
    if (parts[2]?.startsWith('hologram')) return 'system/lib/hologram';
    if (parts[2]?.startsWith('paper')) return 'system/lib/paper_modules';
    if (parts[2]) return 'system/lib/' + pathStem(parts[2]);
  }

  if (parts[0] === 'system' && parts[1] === 'server') {
    if (parts[2] === 'ui') return uiSubcluster(parts);
    if (parts[2] === 'tests') return 'system/server/tests';
    if (parts[2]) return 'system/server/' + pathStem(parts[2]);
  }

  if (parts[0] === 'codex' && parts[1]) return 'codex/' + parts[1];
  if (parts[0] === 'tools' && parts[1]) return 'tools/' + parts[1];
  if (parts[0] === 'annexes' && parts[1]) return 'annexes/' + parts[1];
  return parts.slice(0, Math.min(3, parts.length - 1)).join('/') || parts[0];
}

function labelForClusterKey(key: string): string {
  return key
    .replace(/^system\/server\/ui\/src\/components\//, '')
    .replace(/^system\/server\/ui\/src\/pages\//, '')
    .replace(/^system\/server\/ui\/src\/lib\//, '')
    .replace(/^system\/server\/ui\/src\/hooks\//, '')
    .replace(/^system\/server\/ui\/src\//, 'ui / ')
    .replace(/^system\/server\/ui\/remotion\/src\//, 'remotion / ')
    .replace(/^system\/lib\//, '')
    .replace(/^system\/server\//, '')
    .replace(/^codex\//, 'codex / ')
    .replace(/\//g, ' / ')
    .replace(/_/g, ' ');
}

function shouldAlwaysRepresent(file: CodeMapFile, selectedPath: string | null): boolean {
  return (
    file.path === selectedPath ||
    warningCount(file) > 0 ||
    totalOverlayCount(file) > 0 ||
    String(file.health?.grade ?? '').toUpperCase().startsWith('D') ||
    String(file.health?.grade ?? '').toUpperCase().startsWith('F')
  );
}

function pickRepresentatives(
  files: CodeMapFile[],
  mode: CodeMapMode,
  selectedPath: string | null,
): CodeMapFile[] {
  const limit = mode === 'architecture'
    ? GLOBAL_REPRESENTATIVES_PER_CLUSTER
    : NON_GLOBAL_REPRESENTATIVES_PER_CLUSTER;
  const sorted = [...files].sort((left, right) => {
    const score = deriveFileImportance(right) - deriveFileImportance(left);
    if (score !== 0) return score;
    return left.path.localeCompare(right.path);
  });
  const representatives = new Map<string, CodeMapFile>();
  sorted.slice(0, limit).forEach((file) => representatives.set(file.path, file));
  files.forEach((file) => {
    if (shouldAlwaysRepresent(file, selectedPath)) representatives.set(file.path, file);
  });
  return Array.from(representatives.values()).sort((left, right) => {
    const score = deriveFileImportance(right) - deriveFileImportance(left);
    if (score !== 0) return score;
    return left.path.localeCompare(right.path);
  });
}

export function buildLayerGroups(
  files: CodeMapFile[],
  mode: CodeMapMode = 'architecture',
  selectedPath: string | null = null,
): LayerGroup[] {
  const byLayer = new Map<string, CodeMapFile[]>();
  files.forEach((file) => {
    const layer = normalizeLayer(file.layer);
    if (!byLayer.has(layer)) byLayer.set(layer, []);
    byLayer.get(layer)!.push(file);
  });

  const layers = Array.from(byLayer.entries()).map(([layer, layerFiles]) => {
    const byCluster = new Map<string, CodeMapFile[]>();
    layerFiles.forEach((file) => {
      const key = clusterKeyForFile(file);
      if (!byCluster.has(key)) byCluster.set(key, []);
      byCluster.get(key)!.push(file);
    });

    const clusters: ClusterGroup[] = Array.from(byCluster.entries()).map(([clusterId, clusterFiles]) => {
      const representativeFiles = pickRepresentatives(clusterFiles, mode, selectedPath);
      const importance = clusterFiles.reduce((total, file) => total + deriveFileImportance(file), 0);
      const warnings = clusterFiles.reduce((total, file) => total + warningCount(file), 0);
      const overlays = clusterFiles.reduce((total, file) => total + totalOverlayCount(file), 0);
      return {
        id: `${layer}:${clusterId}`,
        label: labelForClusterKey(clusterId),
        layer,
        files: clusterFiles,
        totalFiles: clusterFiles.length,
        representativeFiles,
        collapsedCount: Math.max(0, clusterFiles.length - representativeFiles.length),
        warningCount: warnings,
        overlayCount: overlays,
        importance,
      };
    }).sort((left, right) => {
      if (right.importance !== left.importance) return right.importance - left.importance;
      return left.label.localeCompare(right.label);
    });

    const importance = clusters.reduce((total, cluster) => total + cluster.importance, 0);
    return {
      id: layer,
      label: layer.replace(/_/g, ' '),
      files: layerFiles,
      clusters,
      totalFiles: layerFiles.length,
      warningCount: clusters.reduce((total, cluster) => total + cluster.warningCount, 0),
      overlayCount: clusters.reduce((total, cluster) => total + cluster.overlayCount, 0),
      importance,
    };
  });

  return layers.sort((left, right) => {
    if (right.importance !== left.importance) return right.importance - left.importance;
    return left.label.localeCompare(right.label);
  });
}

export function allRepresentativeFiles(layers: LayerGroup[]): CodeMapFile[] {
  const seen = new Map<string, CodeMapFile>();
  layers.forEach((layer) => {
    layer.clusters.forEach((cluster) => {
      cluster.representativeFiles.forEach((file) => seen.set(file.path, file));
    });
  });
  return Array.from(seen.values());
}
