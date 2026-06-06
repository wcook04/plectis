import { Lane, type EdgeView, type GraphSnapshot, type NodeView } from '../../api';

export type GraphProjectionMode = 'full' | 'summary';

export interface GraphProjectionOptions {
  renderMode?: GraphProjectionMode;
}

export interface ProjectedGraph {
  nodes: NodeView[];
  edges: EdgeView[];
  canonicalIdByRenderId: Array<[string, string]>;
  memberIdsByRenderId: Array<[string, string[]]>;
}

interface ProjectionGroup {
  key: string;
  wave: number;
  lane: Lane;
  nodes: NodeView[];
}

function toSummaryNode(group: ProjectionGroup): NodeView {
  const members = [...group.nodes].sort((left, right) => left.id.localeCompare(right.id));
  const representative = members[0];
  const branch = representative.lane.toLowerCase();
  const memberCount = members.length;
  return {
    ...representative,
    id: `summary_cluster_${branch}_${group.wave}`,
    label: `${representative.lane} lane · ${memberCount} nodes`,
    instruction: `Summary cluster for ${memberCount} ${representative.lane} lane nodes.`,
    expectation: `${memberCount} summarized nodes`,
    dependencies: [],
    group: branch,
    source_group: branch,
    is_artifact: members.some((node) => node.is_artifact),
    type: members.some((node) => node.type === 'tool') ? 'tool' : 'node',
  };
}

export function projectGraphForRender(
  snapshot: GraphSnapshot,
  { renderMode = 'full' }: GraphProjectionOptions = {},
): ProjectedGraph {
  if (!snapshot || !Array.isArray(snapshot.nodes) || !Array.isArray(snapshot.edges)) {
    return { nodes: [], edges: [], canonicalIdByRenderId: [], memberIdsByRenderId: [] };
  }

  if (renderMode === 'full') {
    return {
      nodes: snapshot.nodes,
      edges: snapshot.edges,
      canonicalIdByRenderId: [],
      memberIdsByRenderId: [],
    };
  }

  const projectionIdByNodeId = new Map<string, string>();
  const projectedNodes = new Map<string, NodeView>();
  const canonicalIdByRenderId = new Map<string, string>();
  const memberIdsByRenderId = new Map<string, string[]>();
  const summaryGroups = new Map<string, ProjectionGroup>();

  snapshot.nodes.forEach((node) => {
    if (node.is_upstream === true || node.lane === Lane.SPINE) {
      projectedNodes.set(node.id, { ...node });
      projectionIdByNodeId.set(node.id, node.id);
      return;
    }

    const key = `${node.wave}:${node.lane}`;
    if (!summaryGroups.has(key)) {
      summaryGroups.set(key, {
        key,
        wave: node.wave,
        lane: node.lane,
        nodes: [],
      });
    }
    summaryGroups.get(key)!.nodes.push(node);
  });

  summaryGroups.forEach((group) => {
    const summaryNode = toSummaryNode(group);
    const memberIds = group.nodes.map((node) => node.id);
    projectedNodes.set(summaryNode.id, summaryNode);
    canonicalIdByRenderId.set(summaryNode.id, memberIds[0] ?? summaryNode.id);
    memberIdsByRenderId.set(summaryNode.id, memberIds);
    memberIds.forEach((memberId) => {
      projectionIdByNodeId.set(memberId, summaryNode.id);
    });
  });

  const dependencyIdsByProjectedId = new Map<string, Set<string>>();
  projectedNodes.forEach((_, projectedId) => {
    dependencyIdsByProjectedId.set(projectedId, new Set<string>());
  });

  const edgeById = new Map<string, EdgeView>();
  snapshot.edges.forEach((edge) => {
    const sourceId = projectionIdByNodeId.get(edge.source);
    const targetId = projectionIdByNodeId.get(edge.target);
    if (!sourceId || !targetId || sourceId === targetId) return;

    const key = `${sourceId}->${targetId}`;
    if (!edgeById.has(key)) {
      edgeById.set(key, {
        id: key,
        source: sourceId,
        target: targetId,
        type: edge.type,
      });
    }
    dependencyIdsByProjectedId.get(targetId)?.add(sourceId);
  });

  dependencyIdsByProjectedId.forEach((dependencyIds, projectedId) => {
    const projectedNode = projectedNodes.get(projectedId);
    if (!projectedNode) return;
    projectedNode.dependencies = Array.from(dependencyIds);
  });

  return {
    nodes: Array.from(projectedNodes.values()),
    edges: Array.from(edgeById.values()),
    canonicalIdByRenderId: Array.from(canonicalIdByRenderId.entries()),
    memberIdsByRenderId: Array.from(memberIdsByRenderId.entries()),
  };
}
