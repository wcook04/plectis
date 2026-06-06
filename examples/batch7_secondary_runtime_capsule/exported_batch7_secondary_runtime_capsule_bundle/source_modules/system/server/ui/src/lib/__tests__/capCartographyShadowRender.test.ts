import { describe, expect, it } from 'vitest';
import {
  CAP_CARTOGRAPHY_SHADOW_RENDER_SCHEMA_VERSION,
  capCartographySpecimenToGraphElements,
  type CapCartographyExpositionSpecimen,
} from '../capCartographyShadowRender';

function createSpecimen(): CapCartographyExpositionSpecimen {
  return {
    schema_version: 'cap_cartography_exposition_specimen_v0',
    source_schema_version: 'cap_cartography_v0',
    source_ref: '/api/world-model/task-ledger/projection',
    source_view: 'state/task_ledger/views/cap_cartography.json',
    mode: 'observe_only',
    status: {
      graph_ready: true,
      complete: false,
      bounded: true,
      edge_limit_hit: true,
      warnings: ['edge_limit_hit', 'unclassified_caps_present'],
    },
    frontend_posture: {
      mode: 'observe_only',
      cap_creation_supported: false,
      mutation_supported: false,
      frontend_actionable_cap_mutation_supported: false,
      source_route_supported: true,
    },
    overview_tiles: [
      { id: 'cap_universe_count', value: 1760 },
      { id: 'edge_count', value: 512 },
      { id: 'omitted_edge_count', value: 17120 },
      { id: 'unclassified_count', value: 18 },
    ],
    cluster_elements: [
      {
        id: 'cluster:semantic_role:evidence',
        kind: 'cluster',
        label: 'Evidence',
        member_count: 24,
        representative_ids: ['cap_evidence', 'cap_followup'],
        semantic_classes: {
          cluster_kind: 'semantic_role',
          color_basis: 'semantic_role',
          confidence: 'source_evidenced',
          size_basis: 'member_count',
        },
        source_route_metadata: {
          projection_path: 'state/task_ledger/views/cap_cartography.json',
          source_view: 'state/task_ledger/views/cap_census.json',
          option_surface: './repo-python kernel.py --option-surface task_ledger --band cluster_flag --ids cap_cartography',
        },
        actions: {
          cap_creation_supported: false,
          mutation_supported: false,
          frontend_actionable_cap_mutation_supported: false,
          inspect_supported: true,
          source_route_supported: true,
        },
      },
    ],
    node_elements: [
      {
        id: 'cap_evidence',
        kind: 'node',
        label: 'Infrastructure-looking title that must not drive semantics',
        node_kind: 'cap',
        semantic_classes: {
          node_kind: 'cap',
          semantic_role: 'evidence',
          temporal_role: 'active_conversion',
          color_basis: 'temporal_role',
          size_basis: 'view_count',
          cluster_ids: ['cluster:semantic_role:evidence'],
        },
        source_route_metadata: {
          task_ledger_card:
            './repo-python kernel.py --option-surface task_ledger --band card --ids cap_evidence',
          views: ['cap_census', 'cap_cartography'],
          frontend_actionable: false,
        },
        source_refs: ['wie_001'],
        lineage: {
          task_ledger_card:
            './repo-python kernel.py --option-surface task_ledger --band card --ids cap_evidence',
        },
        actions: {
          cap_creation_supported: false,
          mutation_supported: false,
          frontend_actionable_cap_mutation_supported: false,
          inspect_supported: true,
          source_route_supported: true,
        },
      },
      {
        id: 'cap_followup',
        kind: 'node',
        label: 'Follow-up cap',
        node_kind: 'cap',
        semantic_classes: {
          node_kind: 'cap',
          semantic_role: 'residual',
          temporal_role: 'future_open',
          color_basis: 'temporal_role',
          size_basis: 'view_count',
          cluster_ids: ['cluster:semantic_role:evidence'],
        },
        source_route_metadata: {
          task_ledger_card:
            './repo-python kernel.py --option-surface task_ledger --band card --ids cap_followup',
        },
        actions: {
          cap_creation_supported: false,
          mutation_supported: false,
          frontend_actionable_cap_mutation_supported: false,
          inspect_supported: true,
          source_route_supported: true,
        },
      },
    ],
    edge_elements: [
      {
        id: 'edge:unlocks:cap_evidence->cap_followup',
        kind: 'edge',
        source: 'cap_evidence',
        target: 'cap_followup',
        edge_kind: 'unlocks',
        confidence: 'source_evidenced',
        semantic_classes: {
          edge_kind: 'unlocks',
          confidence: 'source_evidenced',
        },
        source_ref: 'state/task_ledger/views/unlocks_by_rank.json',
        actions: {
          cap_creation_supported: false,
          mutation_supported: false,
          frontend_actionable_cap_mutation_supported: false,
          inspect_supported: true,
          source_route_supported: true,
        },
      },
    ],
    drilldown_elements: [
      {
        id: 'cluster:semantic_role:evidence',
        kind: 'cluster',
        cluster_kind: 'semantic_role',
        value: 'evidence',
        member_count: 24,
        overflow_member_count: 19,
        representative_ids: ['cap_evidence', 'cap_followup'],
        source_route_metadata: {
          projection_path: 'state/task_ledger/views/cap_cartography.json',
          source_view: 'state/task_ledger/views/cap_census.json',
          member_filter: {
            cluster_kind: 'semantic_role',
            value: 'evidence',
          },
        },
        actions: {
          cap_creation_supported: false,
          mutation_supported: false,
          frontend_actionable_cap_mutation_supported: false,
          inspect_supported: true,
          source_route_supported: true,
        },
      },
    ],
    unclassified_elements: [
      {
        id: 'cap_020',
        kind: 'unclassified_cap',
        title: 'Metabolism as WorkItem lane',
        state: 'captured',
        classification_status: 'unclassified',
        candidate_fields_to_check: [
          'work_item_type',
          'candidate_work_item_type',
          'satisfaction_contract',
          'integration_contract',
          'tags',
          'proof_refs',
          'imagined_state_refs',
        ],
        source_route_metadata: {
          source_view: 'state/task_ledger/views/cap_census.json',
          task_ledger_card:
            './repo-python kernel.py --option-surface task_ledger --band card --ids cap_020',
        },
        actions: {
          cap_creation_supported: false,
          mutation_supported: false,
          frontend_actionable_cap_mutation_supported: false,
          inspect_supported: true,
          source_route_supported: true,
        },
      },
    ],
    legend: {
      color_basis_options: ['temporal_role', 'semantic_role'],
      size_basis_options: ['view_count', 'member_count'],
      edge_kinds: { unlocks: 1 },
      confidence_values: ['source_evidenced'],
      levels: ['level:0:universe_summary', 'level:4:lineage_drilldown'],
    },
    blocked_actions: ['create_cap', 'mutate_cap', 'edit_edge', 'infer_title_semantics'],
    integrity: {
      orphan_renderer_edge_count: 0,
      omitted_renderer_edge_count: 0,
      renderer_inferred_semantic_count: 0,
      rendered_cluster_count: 1,
      rendered_node_count: 2,
      rendered_edge_count: 1,
    },
  };
}

describe('capCartographySpecimenToGraphElements', () => {
  it('projects the world-model exposition specimen into observe-only React Flow elements', () => {
    const model = capCartographySpecimenToGraphElements(createSpecimen());

    expect(model.schema_version).toBe(CAP_CARTOGRAPHY_SHADOW_RENDER_SCHEMA_VERSION);
    expect(model.source_packet_schema).toBe('cap_cartography_exposition_specimen_v0');
    expect(model.source_ref).toBe('/api/world-model/task-ledger/projection');
    expect(model.mode).toBe('observe_only');
    expect(model.status).toMatchObject({
      graph_ready: true,
      complete: false,
      bounded: true,
      edge_limit_hit: true,
      omitted_edge_count: 17120,
      unclassified_count: 18,
    });

    expect(model.blocked_actions).toEqual(
      expect.arrayContaining(['create_cap', 'mutate_cap', 'edit_edge', 'infer_title_semantics']),
    );
    expect(model.available_actions).toEqual(['inspect_source_route']);

    const cluster = model.nodes.find((node) => node.type === 'capCluster');
    expect(cluster?.data.semantic_classes).toMatchObject({
      cluster_kind: 'semantic_role',
      color_basis: 'semantic_role',
    });
    expect(cluster?.data.source_route_metadata?.projection_path).toBe(
      'state/task_ledger/views/cap_cartography.json',
    );

    const capNode = model.nodes.find((node) => node.id === 'cap_evidence');
    expect(capNode?.data.semantic_classes).toMatchObject({
      semantic_role: 'evidence',
      color_basis: 'temporal_role',
    });
    expect(capNode?.data.source_route_metadata?.task_ledger_card).toContain('cap_evidence');

    const edge = model.edges[0];
    expect(edge.source).toBe('cap_evidence');
    expect(edge.target).toBe('cap_followup');
    expect(edge.data?.semantic_classes).toMatchObject({
      edge_kind: 'unlocks',
      confidence: 'source_evidenced',
    });
    expect(edge.data?.source_ref).toBe('state/task_ledger/views/unlocks_by_rank.json');

    const unclassified = model.nodes.find((node) => node.type === 'unclassifiedCap');
    expect(unclassified?.data.candidate_fields_to_check).toContain('candidate_work_item_type');
    expect(unclassified?.data.source_route_metadata?.task_ledger_card).toContain('cap_020');

    expect(model.drilldown.clusters[0]?.source_route_metadata?.projection_path).toBe(
      'state/task_ledger/views/cap_cartography.json',
    );
    expect(model.source_route_samples).toMatchObject({
      edge_source_ref: 'state/task_ledger/views/unlocks_by_rank.json',
    });
    expect(model.integrity).toMatchObject({
      orphan_edge_count: 0,
      omitted_renderer_edge_count: 0,
      renderer_inferred_semantic_count: 0,
      rendered_cluster_count: 1,
      rendered_cap_node_count: 2,
      rendered_unclassified_node_count: 1,
      rendered_edge_count: 1,
    });

    const nodeIds = new Set(model.nodes.map((node) => node.id));
    expect(model.edges.every((renderedEdge) => nodeIds.has(renderedEdge.source))).toBe(true);
    expect(model.edges.every((renderedEdge) => nodeIds.has(renderedEdge.target))).toBe(true);
  });

  it('omits renderer edges whose endpoints are outside the specimen', () => {
    const specimen = createSpecimen();
    specimen.edge_elements = [
      ...(specimen.edge_elements ?? []),
      {
        id: 'edge:depends_on:cap_evidence->cap_missing',
        kind: 'edge',
        source: 'cap_evidence',
        target: 'cap_missing',
        edge_kind: 'depends_on',
        confidence: 'source_evidenced',
        semantic_classes: { edge_kind: 'depends_on', confidence: 'source_evidenced' },
        source_ref: 'state/task_ledger/views/dependency_graph.json',
      },
    ];

    const model = capCartographySpecimenToGraphElements(specimen);

    expect(model.edges.map((edge) => edge.id)).not.toContain('edge:depends_on:cap_evidence->cap_missing');
    expect(model.integrity.omitted_renderer_edge_count).toBe(1);
    expect(model.integrity.orphan_edge_count).toBe(0);
  });

  it('rejects non-specimen inputs instead of adapting an arbitrary payload', () => {
    expect(() =>
      capCartographySpecimenToGraphElements({
        ...createSpecimen(),
        schema_version: 'cap_cartography_v0',
      }),
    ).toThrow(/Unsupported cap cartography specimen schema/);
  });
});
