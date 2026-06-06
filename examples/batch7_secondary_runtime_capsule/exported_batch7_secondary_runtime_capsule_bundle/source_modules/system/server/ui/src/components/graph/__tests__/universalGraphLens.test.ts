import { describe, expect, it } from 'vitest';
import { buildUniversalGraphLens, universalGraphFocusOpacity } from '../universalGraphLens';

describe('buildUniversalGraphLens', () => {
  it('assigns selected, upstream, downstream, and context focus roles', () => {
    const lens = buildUniversalGraphLens(
      {
        nodes: [
          { id: 'ingest', kind: 'task' },
          { id: 'compile', kind: 'task' },
          { id: 'receipt', kind: 'artifact' },
          { id: 'unrelated', kind: 'task' },
        ],
        edges: [
          { id: 'ingest-compile', source: 'ingest', target: 'compile', relation: 'feeds' },
          { id: 'compile-receipt', source: 'compile', target: 'receipt', relation: 'emits' },
        ],
      },
      {
        selectedNodeId: 'compile',
      },
    );

    expect(lens.metrics).toMatchObject({
      nodeCount: 4,
      edgeCount: 2,
      selectedNeighborCount: 2,
    });
    expect(lens.selectedNodeId).toBe('compile');
    expect(lens.directUpstreamIds).toEqual(new Set(['ingest']));
    expect(lens.directDownstreamIds).toEqual(new Set(['receipt']));
    expect(lens.nodeById.get('compile')?.focusRole).toBe('selected');
    expect(lens.nodeById.get('ingest')?.focusRole).toBe('upstream');
    expect(lens.nodeById.get('receipt')?.focusRole).toBe('downstream');
    expect(lens.nodeById.get('unrelated')?.focusRole).toBe('context');
    expect(lens.edgeById.get('ingest-compile')?.focusRole).toBe('selected');
    expect(lens.edgeById.get('compile-receipt')?.focusRole).toBe('selected');
  });

  it('keeps collapsed parent nodes visible while hiding descendants', () => {
    const lens = buildUniversalGraphLens(
      {
        nodes: [
          { id: 'root', kind: 'kind' },
          { id: 'cluster', kind: 'cluster', parentId: 'root' },
          { id: 'object', kind: 'object', parentId: 'cluster' },
          { id: 'evidence', kind: 'source', parentId: 'object' },
        ],
        edges: [
          { id: 'cluster-object', source: 'cluster', target: 'object' },
          { id: 'object-evidence', source: 'object', target: 'evidence' },
        ],
      },
      {
        collapsedNodeIds: ['cluster'],
      },
    );

    expect(lens.nodeById.get('cluster')?.isVisible).toBe(true);
    expect(lens.nodeById.get('object')?.isVisible).toBe(false);
    expect(lens.nodeById.get('evidence')?.isVisible).toBe(false);
    expect(lens.metrics.visibleNodeCount).toBe(2);
    expect(lens.metrics.visibleEdgeCount).toBe(0);
    expect(lens.metrics.maxDepth).toBe(3);
  });

  it('emits kind counts and stable fallback edge ids for graph receipts', () => {
    const lens = buildUniversalGraphLens({
      nodes: [
        { id: 'paper', kind: 'paper_module' },
        { id: 'standard', kind: 'standard' },
        { id: 'source', kind: 'source' },
      ],
      edges: [
        { source: 'paper', target: 'standard', relation: 'governed_by' },
        { source: 'standard', target: 'source' },
      ],
    });

    expect(Object.fromEntries(lens.kindCounts)).toEqual({
      paper_module: 1,
      standard: 1,
      source: 1,
    });
    expect(lens.edges.map((edge) => edge.id)).toEqual([
      'paper->standard:governed_by:0',
      'standard->source:edge:1',
    ]);
    expect(universalGraphFocusOpacity('context', 'paper')).toBeLessThan(
      universalGraphFocusOpacity('selected', 'paper'),
    );
  });
});
