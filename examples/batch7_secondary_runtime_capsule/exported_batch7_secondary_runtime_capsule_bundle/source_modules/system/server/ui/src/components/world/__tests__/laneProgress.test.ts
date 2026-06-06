import { describe, expect, it } from 'vitest';
import {
  buildMetaMissionPacket,
  buildMetaMissionPackets,
  buildMetaMissionsPacket,
  buildMetaMissionsRollupPacket,
  buildObservePacket,
  buildObserveRuntimePackets,
  buildOrchestrationEventRail,
  buildOrchestrationPacket,
  buildOvernightChainPacket,
  buildOvernightQueuePacket,
  buildRawSeedPipelinePacket,
  buildStationTimelinePackets,
  classifyMetaMissionStatus,
  classifyObserveGroupStatus,
  classifyObserveRuntimeState,
  classifyOrchestrationEvent,
} from '../laneProgress';
import type {
  MetaMissionCareerMetrics,
  MetaMissionRunSummary,
  MetaMissionSummaryRow,
  MetaMissionsIndexResponse,
  ObserveSessionGroupStatus,
  ObserveSessionStatusResponse,
  OrchestrationEvent,
  StationLauncherSnapshot,
} from '../../../api';

// Minimal factory: tests override only the slices they exercise. The adapter
// contract is that missing / empty fields degrade to `null` or 'idle' rather
// than crashing — that's what pri_108 + pri_109 demand.
function makeLauncher(
  overrides: Partial<StationLauncherSnapshot> = {},
): StationLauncherSnapshot {
  const baseline = {
    schema: 'station_launcher_v1',
    generated_at: '2026-04-24T01:00:00Z',
    family: {},
    active_phase: {},
    current_driver: {},
    next_handoff: {},
    orchestration: {
      gate_reason: null,
      updated_at: null,
      freshness: null,
      active_driver: null,
      current_owner: null,
      next_command: null,
    },
    missions: { total: 0, ready: 0, blocked: 0, candidates: 0 },
    bridge: {
      configured: false,
      browser_running: false,
      cdp_reachable: false,
      provider_count: 0,
      live_provider_count: 0,
    },
    observe_runtime: {
      state: 'idle',
      completed_groups: 0,
      total_groups: 0,
      can_continue: false,
      retryable_group_labels: [],
    },
    raw_seed_pipeline: {
      total_paragraphs: 0,
      total_bins: 0,
      paragraph_level_shards: 0,
      atomized_shards: 0,
      paragraphs_without_atoms: 0,
      pending_routing_shards: 0,
      pending_routing_bins: 0,
      review_queue_entries: 0,
      review_queue_bins: 0,
      fresh_pending_bins: 0,
      surface_queue_entries: 0,
      doctrine_with_no_provenance: 0,
      merge_candidate_count: 0,
      orphan_cluster_count: 0,
      cohort_size: 0,
      wave_width_effective: 0,
      provider_ceiling: 0,
      queue_depth: 0,
      effective_active_workers: 0,
      safe_parallelism: 0,
    },
    overnight_chain: {
      is_running: false,
      progress: { completed_steps: 0, total_steps: 0 },
    },
    meta_missions: { totals: {}, missions: [], urgent: [] },
    run: { is_running: false, recovered_from_disk: false },
    alerts: [],
    operations: [],
  };
  return { ...baseline, ...overrides } as unknown as StationLauncherSnapshot;
}

describe('buildOrchestrationPacket', () => {
  it('marks blocked when gate_reason is present', () => {
    const launcher = makeLauncher({
      orchestration: {
        gate_reason: 'awaiting human confirmation',
        updated_at: '2026-04-24T02:00:00Z',
        freshness: null,
        active_driver: 'control_room_manager',
        current_owner: 'control_room_manager',
        next_command: null,
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    const packet = buildOrchestrationPacket(launcher);
    expect(packet.status).toBe('blocked');
    expect(packet.detail).toBe('awaiting human confirmation');
    expect(packet.authority?.kind).toBe('orchestration');
  });

  it('marks running when a real driver is active and no gate', () => {
    const launcher = makeLauncher({
      orchestration: {
        gate_reason: null,
        updated_at: '2026-04-24T02:00:00Z',
        freshness: null,
        active_driver: 'phase_runtime',
        current_owner: 'phase_runtime',
        next_command: 'kernel.py --phase-step',
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    expect(buildOrchestrationPacket(launcher).status).toBe('running');
  });

  it('marks idle when no-active-runtime-phase sentinel is the driver', () => {
    const launcher = makeLauncher({
      orchestration: {
        gate_reason: null,
        updated_at: null,
        freshness: null,
        active_driver: 'no_active_runtime_phase',
        current_owner: null,
        next_command: null,
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    const packet = buildOrchestrationPacket(launcher);
    expect(packet.status).toBe('idle');
    expect(packet.authority).toBeNull();
  });

  it('marks stale when freshness is expired', () => {
    const launcher = makeLauncher({
      orchestration: {
        gate_reason: null,
        updated_at: null,
        active_driver: null,
        current_owner: null,
        next_command: null,
        freshness: { tone: 'expired', age_seconds: 99999, label: '1d', iso: null },
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    expect(buildOrchestrationPacket(launcher).status).toBe('stale');
  });
});

describe('buildObservePacket', () => {
  it('returns null when no observe_id is bound', () => {
    const launcher = makeLauncher();
    expect(buildObservePacket(launcher)).toBeNull();
  });

  it('derives running status from dispatching state', () => {
    const launcher = makeLauncher({
      observe_runtime: {
        observe_id: 'obs_01',
        session_slug: '09_42-wave_001',
        state: 'dispatching',
        completed_groups: 2,
        total_groups: 6,
        can_continue: false,
        retryable_group_labels: [],
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    const packet = buildObservePacket(launcher)!;
    expect(packet.status).toBe('running');
    expect(packet.progress).toEqual({ completed: 2, total: 6 });
  });

  it('treats error state as failure', () => {
    const launcher = makeLauncher({
      observe_runtime: {
        observe_id: 'obs_02',
        state: 'error',
        completed_groups: 3,
        total_groups: 6,
        can_continue: true,
        retryable_group_labels: ['probe_a', 'probe_b'],
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    const packet = buildObservePacket(launcher)!;
    expect(packet.status).toBe('failure');
    expect(packet.metrics?.find((m) => m.label === 'retryable')?.value).toBe(2);
    expect(packet.metrics?.find((m) => m.label === 'resume')?.value).toBe('ready');
  });

  it('marks awaiting_review as blocked', () => {
    const launcher = makeLauncher({
      observe_runtime: {
        observe_id: 'obs_03',
        state: 'awaiting_review',
        completed_groups: 6,
        total_groups: 6,
        can_continue: false,
        retryable_group_labels: [],
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    expect(buildObservePacket(launcher)!.status).toBe('blocked');
  });

  it('marks completed as success', () => {
    const launcher = makeLauncher({
      observe_runtime: {
        observe_id: 'obs_04',
        state: 'completed',
        completed_groups: 6,
        total_groups: 6,
        can_continue: false,
        retryable_group_labels: [],
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    expect(buildObservePacket(launcher)!.status).toBe('success');
  });
});

describe('buildOvernightChainPacket', () => {
  it('returns null when no chain_id', () => {
    expect(buildOvernightChainPacket(makeLauncher())).toBeNull();
  });

  it('marks running during active chain', () => {
    const launcher = makeLauncher({
      overnight_chain: {
        chain_id: 'chain_A',
        chain_run_id: 'run_1',
        is_running: true,
        progress: {
          completed_steps: 3,
          total_steps: 8,
          current_step_id: 'distill_cycle',
        },
        last_updated: '2026-04-24T02:30:00Z',
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    const packet = buildOvernightChainPacket(launcher)!;
    expect(packet.status).toBe('running');
    expect(packet.progress).toEqual({ completed: 3, total: 8 });
    expect(packet.kicker).toBe('distill_cycle');
  });

  it('marks failure when last_error is set and not running', () => {
    const launcher = makeLauncher({
      overnight_chain: {
        chain_id: 'chain_B',
        is_running: false,
        progress: { completed_steps: 4, total_steps: 8 },
        last_error: 'subprocess exited 2',
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    const packet = buildOvernightChainPacket(launcher)!;
    expect(packet.status).toBe('failure');
    expect(packet.error).toBe('subprocess exited 2');
  });

  it('marks success when terminal status is succeeded', () => {
    const launcher = makeLauncher({
      overnight_chain: {
        chain_id: 'chain_C',
        is_running: false,
        progress: { completed_steps: 8, total_steps: 8 },
        terminal_status: 'succeeded',
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    expect(buildOvernightChainPacket(launcher)!.status).toBe('success');
  });
});

describe('buildOvernightQueuePacket', () => {
  it('returns null without queue_id', () => {
    expect(buildOvernightQueuePacket(makeLauncher())).toBeNull();
  });

  it('marks pending when progress is incomplete and not running', () => {
    const launcher = makeLauncher({
      overnight_queue: {
        queue_id: 'q_1',
        is_running: false,
        progress: {
          completed_items: 2,
          total_items: 5,
        },
        artifact_refs: [],
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    const packet = buildOvernightQueuePacket(launcher)!;
    expect(packet.status).toBe('pending');
    expect(packet.progress).toEqual({ completed: 2, total: 5 });
  });
});

describe('buildMetaMissionsPacket', () => {
  it('returns null when no activity at all', () => {
    const launcher = makeLauncher();
    expect(buildMetaMissionsPacket(launcher)).toBeNull();
  });

  it('marks running when running_total > 0', () => {
    const launcher = makeLauncher({
      meta_missions: {
        generated_at: '2026-04-24T01:00:00Z',
        totals: { active_missions: 3, total_runs: 12, running_total: 2 },
        missions: [],
        urgent: [],
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    const packet = buildMetaMissionsPacket(launcher)!;
    expect(packet.status).toBe('running');
    expect(packet.progress).toEqual({ completed: 1, total: 3 });
  });

  it('marks blocked when urgent missions exist and nothing is running', () => {
    const launcher = makeLauncher({
      meta_missions: {
        generated_at: null,
        totals: { active_missions: 2, total_runs: 4, running_total: 0 },
        missions: [],
        urgent: [
          {
            mission_id: 'mis_A',
            title: 'A',
            status: 'failed',
            supports_resume: true,
            error: 'timeout',
          },
        ],
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    const packet = buildMetaMissionsPacket(launcher)!;
    expect(packet.status).toBe('blocked');
    expect(packet.label).toBe('mis_A');
    expect(packet.detail).toBe('timeout');
  });
});

describe('buildRawSeedPipelinePacket', () => {
  it('returns null without a family substrate', () => {
    expect(buildRawSeedPipelinePacket(makeLauncher())).toBeNull();
  });

  it('marks running when workers are active and queue has depth', () => {
    const launcher = makeLauncher({
      raw_seed_pipeline: {
        family_number: '09',
        family_dir: 'fam_09',
        total_paragraphs: 100,
        paragraphs_without_atoms: 10,
        pending_routing_shards: 5,
        pending_routing_bins: 0,
        review_queue_entries: 0,
        review_queue_bins: 0,
        fresh_pending_bins: 2,
        surface_queue_entries: 0,
        doctrine_with_no_provenance: 0,
        merge_candidate_count: 0,
        orphan_cluster_count: 0,
        total_bins: 0,
        paragraph_level_shards: 0,
        atomized_shards: 0,
        cohort_size: 12,
        wave_width_effective: 3,
        provider_ceiling: 4,
        queue_depth: 6,
        effective_active_workers: 2,
        safe_parallelism: 3,
        last_updated: '2026-04-24T02:40:00Z',
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    const packet = buildRawSeedPipelinePacket(launcher)!;
    expect(packet.status).toBe('running');
    expect(packet.progress).toEqual({ completed: 90, total: 100 });
  });

  it('marks pending when pending work exists but no workers active', () => {
    const launcher = makeLauncher({
      raw_seed_pipeline: {
        family_number: '09',
        total_paragraphs: 50,
        paragraphs_without_atoms: 5,
        pending_routing_shards: 2,
        pending_routing_bins: 0,
        review_queue_entries: 0,
        review_queue_bins: 0,
        fresh_pending_bins: 0,
        surface_queue_entries: 0,
        doctrine_with_no_provenance: 0,
        merge_candidate_count: 0,
        orphan_cluster_count: 0,
        total_bins: 0,
        paragraph_level_shards: 0,
        atomized_shards: 0,
        cohort_size: 0,
        wave_width_effective: 0,
        provider_ceiling: 0,
        queue_depth: 0,
        effective_active_workers: 0,
        safe_parallelism: 0,
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    expect(buildRawSeedPipelinePacket(launcher)!.status).toBe('pending');
  });
});

describe('buildStationTimelinePackets', () => {
  it('returns empty when launcher is null', () => {
    expect(buildStationTimelinePackets(null)).toEqual([]);
  });

  it('returns only the active lanes', () => {
    const launcher = makeLauncher({
      orchestration: {
        gate_reason: null,
        updated_at: '2026-04-24T02:00:00Z',
        freshness: null,
        active_driver: 'phase_runtime',
        current_owner: null,
        next_command: null,
      },
      raw_seed_pipeline: {
        family_number: '09',
        total_paragraphs: 10,
        paragraphs_without_atoms: 0,
        pending_routing_shards: 0,
        pending_routing_bins: 0,
        review_queue_entries: 0,
        review_queue_bins: 0,
        fresh_pending_bins: 0,
        surface_queue_entries: 0,
        doctrine_with_no_provenance: 0,
        merge_candidate_count: 0,
        orphan_cluster_count: 0,
        total_bins: 0,
        paragraph_level_shards: 0,
        atomized_shards: 0,
        cohort_size: 0,
        wave_width_effective: 0,
        provider_ceiling: 0,
        queue_depth: 0,
        effective_active_workers: 0,
        safe_parallelism: 0,
      },
    } as unknown as Partial<StationLauncherSnapshot>);
    const packets = buildStationTimelinePackets(launcher);
    const laneIds = packets.map((p) => p.lane_id);
    expect(laneIds).toContain('orchestration');
    expect(laneIds).toContain('raw_seed_pipeline');
    expect(laneIds).not.toContain('observe_runtime');
    expect(laneIds).not.toContain('overnight_chain');
  });
});

describe('classifyOrchestrationEvent + buildOrchestrationEventRail', () => {
  function evt(overrides: Partial<OrchestrationEvent>): OrchestrationEvent {
    return {
      event_id: 'e_1',
      kind: 'tick',
      recorded_at: '2026-04-24T02:00:00Z',
      drivers: [],
      freshness: {
        tone: 'fresh',
        age_seconds: 0,
        label: 'now',
        iso: null,
      },
      ...overrides,
    } as OrchestrationEvent;
  }

  it('marks gate_reason events as blocked', () => {
    expect(
      classifyOrchestrationEvent(evt({ gate_reason: 'human review' })),
    ).toBe('blocked');
  });

  it('maps known kinds', () => {
    expect(
      classifyOrchestrationEvent(evt({ kind: 'operation_launched' })),
    ).toBe('running');
    expect(
      classifyOrchestrationEvent(evt({ kind: 'operation_failed' })),
    ).toBe('failure');
    expect(
      classifyOrchestrationEvent(evt({ kind: 'gate_acknowledged' })),
    ).toBe('success');
  });

  it('falls back to driver presence', () => {
    expect(
      classifyOrchestrationEvent(
        evt({ kind: 'tick', active_driver: 'phase_runtime' }),
      ),
    ).toBe('running');
    expect(
      classifyOrchestrationEvent(
        evt({ kind: 'tick', active_driver: 'no_active_runtime_phase' }),
      ),
    ).toBe('idle');
  });

  it('buildOrchestrationEventRail respects limit + carries label/detail', () => {
    const events: OrchestrationEvent[] = [
      evt({
        event_id: 'e_1',
        kind: 'operation_launched',
        summary: 'launched raw_seed_distill_cycle',
      }),
      evt({
        event_id: 'e_2',
        kind: 'gate_acknowledged',
        summary: 'ack',
      }),
      evt({
        event_id: 'e_3',
        kind: 'tick',
      }),
    ];
    const rail = buildOrchestrationEventRail(events, 2);
    expect(rail).toHaveLength(2);
    expect(rail[0].status).toBe('running');
    expect(rail[0].label).toBe('launched raw_seed_distill_cycle');
    expect(rail[1].status).toBe('success');
  });
});

// ---------------------------------------------------------------------------
// Observe runtime — full session projection (ObserveRunStatus consumer)
// ---------------------------------------------------------------------------

describe('classifyObserveRuntimeState', () => {
  it('maps running-family states', () => {
    expect(classifyObserveRuntimeState('generating')).toBe('running');
    expect(classifyObserveRuntimeState('dispatching')).toBe('running');
    expect(classifyObserveRuntimeState('synthesizing')).toBe('running');
  });
  it('maps awaiting_review to blocked', () => {
    expect(classifyObserveRuntimeState('awaiting_review')).toBe('blocked');
  });
  it('maps terminal states', () => {
    expect(classifyObserveRuntimeState('completed')).toBe('success');
    expect(classifyObserveRuntimeState('error')).toBe('failure');
    expect(classifyObserveRuntimeState('aborted')).toBe('aborted');
  });
  it('degrades unknown/null to idle', () => {
    expect(classifyObserveRuntimeState(null)).toBe('idle');
    expect(classifyObserveRuntimeState(undefined)).toBe('idle');
    expect(classifyObserveRuntimeState('idle')).toBe('idle');
    expect(classifyObserveRuntimeState('mysterious-future-state')).toBe('idle');
  });
});

describe('classifyObserveGroupStatus', () => {
  it('maps direct group statuses', () => {
    expect(classifyObserveGroupStatus('running', true)).toBe('running');
    expect(classifyObserveGroupStatus('success', true)).toBe('success');
    expect(classifyObserveGroupStatus('failure', true)).toBe('failure');
    expect(classifyObserveGroupStatus('aborted', true)).toBe('aborted');
    expect(classifyObserveGroupStatus('skipped', true)).toBe('skipped');
  });
  it('treats pending-with-unmet-deps as blocked', () => {
    expect(classifyObserveGroupStatus('pending', false)).toBe('blocked');
  });
  it('treats pending-with-met-deps as pending', () => {
    expect(classifyObserveGroupStatus('pending', true)).toBe('pending');
  });
  it('degrades unknown/null to idle', () => {
    expect(classifyObserveGroupStatus(null, true)).toBe('idle');
    expect(classifyObserveGroupStatus(undefined, true)).toBe('idle');
    expect(classifyObserveGroupStatus('mystery', true)).toBe('idle');
  });
});

describe('buildObserveRuntimePackets', () => {
  // Minimal status factory. Tests override only the fields they care about.
  function makeStatus(
    overrides: Partial<ObserveSessionStatusResponse> = {},
  ): ObserveSessionStatusResponse {
    const base: ObserveSessionStatusResponse = {
      observe_id: 'obs_01',
      session_slug: '09_42_wave_001',
      state: 'idle',
      total_groups: 0,
      completed_groups: 0,
      groups: [],
      artifacts: {},
    };
    return { ...base, ...overrides } as ObserveSessionStatusResponse;
  }

  function makeGroup(
    overrides: Partial<ObserveSessionGroupStatus>,
  ): ObserveSessionGroupStatus {
    return {
      label: 'group',
      role: 'probe',
      depends_on: [],
      status: 'pending',
      wave_index: 0,
      retryable: false,
      dependencies_met: true,
      ...overrides,
    } as ObserveSessionGroupStatus;
  }

  it('returns empty array when status is null', () => {
    expect(buildObserveRuntimePackets(null)).toEqual([]);
    expect(buildObserveRuntimePackets(undefined)).toEqual([]);
  });

  it('emits only a session packet when no groups present', () => {
    const packets = buildObserveRuntimePackets(
      makeStatus({
        state: 'dispatching',
        total_groups: 4,
        completed_groups: 1,
        provider: 'chatgpt',
        provider_transport: 'bridge',
        wave_index: 0,
        wave_total: 2,
        effective_workers: 3,
        requested_workers: '3',
      }),
    );
    expect(packets).toHaveLength(1);
    const session = packets[0];
    expect(session.id).toBe('observe_runtime_session:obs_01');
    expect(session.status).toBe('running');
    expect(session.progress).toEqual({ completed: 1, total: 4 });
    expect(session.label).toBe('09_42_wave_001');
    expect(session.kicker).toBe('chatgpt');
    const metricLabels = session.metrics!.map((m) => m.label);
    expect(metricLabels).toContain('wave');
    expect(metricLabels).toContain('transport');
    expect(metricLabels).toContain('workers');
  });

  it('marks awaiting_review as blocked at the session level', () => {
    const packets = buildObserveRuntimePackets(
      makeStatus({
        state: 'awaiting_review',
        total_groups: 6,
        completed_groups: 6,
      }),
    );
    expect(packets[0].status).toBe('blocked');
  });

  it('marks error state as failure and surfaces the error string', () => {
    const packets = buildObserveRuntimePackets(
      makeStatus({
        state: 'error',
        error: 'bridge cdp unreachable',
      }),
    );
    expect(packets[0].status).toBe('failure');
    expect(packets[0].error).toBe('bridge cdp unreachable');
  });

  it('marks aborted as aborted', () => {
    const packets = buildObserveRuntimePackets(
      makeStatus({ state: 'aborted' }),
    );
    expect(packets[0].status).toBe('aborted');
  });

  it('marks completed as success and promotes error if backend disagrees', () => {
    const okPackets = buildObserveRuntimePackets(
      makeStatus({ state: 'completed', total_groups: 3, completed_groups: 3 }),
    );
    expect(okPackets[0].status).toBe('success');

    const mismatch = buildObserveRuntimePackets(
      makeStatus({
        state: 'completed',
        total_groups: 3,
        completed_groups: 3,
        error: 'worker lane panic',
      }),
    );
    expect(mismatch[0].status).toBe('failure');
    expect(mismatch[0].error).toBe('worker lane panic');
  });

  it('emits bounded group packets sorted by priority: running, failure, blocked, ...', () => {
    const packets = buildObserveRuntimePackets(
      makeStatus({
        state: 'dispatching',
        total_groups: 5,
        completed_groups: 1,
        groups: [
          makeGroup({ label: 'g_success', status: 'success' }),
          makeGroup({
            label: 'g_blocked',
            status: 'pending',
            dependencies_met: false,
          }),
          makeGroup({ label: 'g_failure', status: 'failure', error: 'boom' }),
          makeGroup({ label: 'g_running', status: 'running' }),
          makeGroup({ label: 'g_pending_ready', status: 'pending' }),
        ],
      }),
    );
    const groupLabels = packets
      .filter((p) => p.id.startsWith('observe_runtime_group:'))
      .map((p) => p.label);
    expect(groupLabels).toEqual([
      'g_running',
      'g_failure',
      'g_blocked',
      'g_pending_ready',
      'g_success',
    ]);
    const failurePacket = packets.find(
      (p) => p.label === 'g_failure',
    );
    expect(failurePacket?.status).toBe('failure');
    expect(failurePacket?.error).toBe('boom');
    const blockedPacket = packets.find((p) => p.label === 'g_blocked');
    expect(blockedPacket?.status).toBe('blocked');
    expect(blockedPacket?.metrics).toEqual(
      expect.arrayContaining([{ label: 'deps', value: 'blocked' }]),
    );
  });

  it('promotes retryable groups ahead of non-retryable within the same status', () => {
    const packets = buildObserveRuntimePackets(
      makeStatus({
        state: 'awaiting_review',
        total_groups: 2,
        completed_groups: 1,
        groups: [
          makeGroup({ label: 'g_failure_plain', status: 'failure' }),
          makeGroup({
            label: 'g_failure_retryable',
            status: 'failure',
            retryable: true,
            retry_reason: 'timeout',
          }),
        ],
      }),
    );
    const groupLabels = packets
      .filter((p) => p.id.startsWith('observe_runtime_group:'))
      .map((p) => p.label);
    expect(groupLabels).toEqual([
      'g_failure_retryable',
      'g_failure_plain',
    ]);
    const retryable = packets.find((p) => p.label === 'g_failure_retryable');
    expect(retryable?.detail).toBe('timeout');
    expect(retryable?.metrics).toEqual(
      expect.arrayContaining([{ label: 'retry', value: 'yes' }]),
    );
  });

  it('bounds the visible group list and emits a "+N more" summary', () => {
    const groups: ObserveSessionGroupStatus[] = [];
    for (let i = 0; i < 20; i += 1) {
      groups.push(
        makeGroup({
          label: `g_${i}`,
          status: i < 14 ? 'success' : 'pending',
        }),
      );
    }
    const packets = buildObserveRuntimePackets(
      makeStatus({
        state: 'awaiting_review',
        total_groups: 20,
        completed_groups: 14,
        groups,
      }),
      { groupLimit: 5 },
    );
    // Session + 5 visible groups + 1 summary = 7
    expect(packets).toHaveLength(7);
    const summary = packets[packets.length - 1];
    expect(summary.id).toBe('observe_runtime_group_summary:obs_01');
    expect(summary.label).toBe('+15 more');
    expect(summary.status).toBe('idle');
    const summaryLabels = summary.metrics!.map((m) => m.label);
    expect(summaryLabels).toContain('success');
  });

  it('does not emit a summary when groups fit within the limit', () => {
    const packets = buildObserveRuntimePackets(
      makeStatus({
        state: 'dispatching',
        total_groups: 2,
        completed_groups: 0,
        groups: [
          makeGroup({ label: 'g_a', status: 'pending' }),
          makeGroup({ label: 'g_b', status: 'pending' }),
        ],
      }),
      { groupLimit: 8 },
    );
    expect(
      packets.some((p) =>
        p.id.startsWith('observe_runtime_group_summary:'),
      ),
    ).toBe(false);
    expect(packets).toHaveLength(3); // session + 2 groups
  });
});

// ---------------------------------------------------------------------------
// Meta-missions — MetaMissionsIndexResponse projection (MetaMissionsLens consumer)
// ---------------------------------------------------------------------------

function makeMetrics(
  overrides: Partial<MetaMissionCareerMetrics> = {},
): MetaMissionCareerMetrics {
  return {
    total_runs: 0,
    running_total: 0,
    terminal_total: 0,
    succeeded_total: 0,
    failed_total: 0,
    by_status: {},
    ...overrides,
  };
}

function makeRun(
  overrides: Partial<MetaMissionRunSummary> = {},
): MetaMissionRunSummary {
  return {
    run_id: 'run_1',
    mission_id: 'mis_a',
    status: 'succeeded',
    ...overrides,
  } as MetaMissionRunSummary;
}

function makeMissionRow(
  overrides: Partial<MetaMissionSummaryRow> = {},
): MetaMissionSummaryRow {
  const baseline: MetaMissionSummaryRow = {
    mission_id: 'mis_a',
    title: 'Mission A',
    status: 'active',
    supports_resume: false,
    launcher_operation_ids: [],
    launcher_operations: [],
    workspace_root: '/tmp/mis_a',
    metrics: makeMetrics(),
    recent_runs: [],
  };
  return { ...baseline, ...overrides };
}

function makeIndex(
  overrides: Partial<MetaMissionsIndexResponse> = {},
): MetaMissionsIndexResponse {
  return {
    generated_at: '2026-04-24T04:00:00Z',
    registry_version: 'v0.3',
    entries: [],
    summaries: [],
    ...overrides,
  } as MetaMissionsIndexResponse;
}

describe('classifyMetaMissionStatus', () => {
  it('marks running when running_total > 0 regardless of last status', () => {
    const row = makeMissionRow({
      metrics: makeMetrics({
        total_runs: 5,
        running_total: 1,
        last_run: makeRun({ status: 'failed' }),
      }),
    });
    expect(classifyMetaMissionStatus(row)).toBe('running');
  });

  it('maps last_run.status terminal values when nothing is running', () => {
    expect(
      classifyMetaMissionStatus(
        makeMissionRow({
          metrics: makeMetrics({ last_run: makeRun({ status: 'failed' }) }),
        }),
      ),
    ).toBe('failure');
    expect(
      classifyMetaMissionStatus(
        makeMissionRow({
          metrics: makeMetrics({ last_run: makeRun({ status: 'aborted' }) }),
        }),
      ),
    ).toBe('aborted');
    expect(
      classifyMetaMissionStatus(
        makeMissionRow({
          metrics: makeMetrics({
            last_run: makeRun({ status: 'graceful_stop' }),
          }),
        }),
      ),
    ).toBe('blocked');
    expect(
      classifyMetaMissionStatus(
        makeMissionRow({
          metrics: makeMetrics({
            last_run: makeRun({ status: 'interrupted' }),
          }),
        }),
      ),
    ).toBe('blocked');
    expect(
      classifyMetaMissionStatus(
        makeMissionRow({
          metrics: makeMetrics({ last_run: makeRun({ status: 'skipped' }) }),
        }),
      ),
    ).toBe('skipped');
    expect(
      classifyMetaMissionStatus(
        makeMissionRow({
          metrics: makeMetrics({ last_run: makeRun({ status: 'succeeded' }) }),
        }),
      ),
    ).toBe('success');
  });

  it('maps registry status=planned with no runs to pending', () => {
    expect(
      classifyMetaMissionStatus(
        makeMissionRow({ status: 'planned', metrics: makeMetrics() }),
      ),
    ).toBe('pending');
  });

  it('falls through to idle when active-but-idle', () => {
    expect(classifyMetaMissionStatus(makeMissionRow())).toBe('idle');
  });
});

describe('buildMetaMissionPacket', () => {
  it('builds metrics + progress from the summary row', () => {
    const packet = buildMetaMissionPacket(
      makeMissionRow({
        mission_id: 'raw_seed_distill',
        title: 'Raw-seed distillation',
        runtime_surface: 'bridge',
        supports_resume: true,
        metrics: makeMetrics({
          total_runs: 12,
          running_total: 1,
          failed_total: 2,
          succeeded_total: 9,
          success_rate: 0.75,
          last_run: makeRun({
            status: 'running',
            started_at: '2026-04-24T03:30:00Z',
          }),
        }),
      }),
    );
    expect(packet.id).toBe('meta_mission:raw_seed_distill');
    expect(packet.lane_id).toBe('meta_missions');
    expect(packet.label).toBe('Raw-seed distillation');
    expect(packet.kicker).toBe('raw_seed_distill');
    expect(packet.status).toBe('running');
    expect(packet.progress).toEqual({ completed: 9, total: 12 });
    expect(packet.updated_at).toBe('2026-04-24T03:30:00Z');
    const labels = packet.metrics!.map((m) => m.label);
    expect(labels).toContain('runs');
    expect(labels).toContain('running');
    expect(labels).toContain('failed');
    expect(labels).toContain('success');
    expect(labels).toContain('surface');
    expect(labels).toContain('resume');
    expect(labels).toContain('last');
    const successMetric = packet.metrics!.find((m) => m.label === 'success');
    expect(successMetric?.value).toBe('75%');
  });

  it('surfaces error from last_run', () => {
    const packet = buildMetaMissionPacket(
      makeMissionRow({
        metrics: makeMetrics({
          total_runs: 3,
          failed_total: 1,
          last_run: makeRun({
            status: 'failed',
            error: 'bridge cdp unreachable',
            finished_at: '2026-04-24T02:00:00Z',
          }),
        }),
      }),
    );
    expect(packet.status).toBe('failure');
    expect(packet.error).toBe('bridge cdp unreachable');
    expect(packet.updated_at).toBe('2026-04-24T02:00:00Z');
  });

  it('falls back to mission_id when title is empty', () => {
    const packet = buildMetaMissionPacket(
      makeMissionRow({ mission_id: 'mis_x', title: '' }),
    );
    expect(packet.label).toBe('mis_x');
  });

  it('omits progress when total_runs is 0', () => {
    const packet = buildMetaMissionPacket(makeMissionRow());
    expect(packet.progress).toBeNull();
  });
});

describe('buildMetaMissionsRollupPacket', () => {
  it('returns null when index is null or empty', () => {
    expect(buildMetaMissionsRollupPacket(null)).toBeNull();
    expect(buildMetaMissionsRollupPacket(makeIndex())).toBeNull();
  });

  it('marks running when any mission has running_total > 0', () => {
    const rollup = buildMetaMissionsRollupPacket(
      makeIndex({
        summaries: [
          makeMissionRow({ metrics: makeMetrics({ running_total: 1 }) }),
          makeMissionRow({ mission_id: 'mis_b', status: 'planned' }),
        ],
      }),
    );
    expect(rollup?.status).toBe('running');
    const labels = rollup?.metrics?.map((m) => m.label) ?? [];
    expect(labels).toContain('careers');
    expect(labels).toContain('active');
    expect(labels).toContain('planned');
    expect(labels).toContain('running');
    expect(labels).toContain('runs total');
  });

  it('marks failure when a recent run failed and nothing is running', () => {
    const rollup = buildMetaMissionsRollupPacket(
      makeIndex({
        summaries: [
          makeMissionRow({
            metrics: makeMetrics({
              total_runs: 3,
              failed_total: 2,
              last_run: makeRun({ status: 'failed' }),
            }),
          }),
        ],
      }),
    );
    expect(rollup?.status).toBe('failure');
  });

  it('marks blocked when a recent run was gracefully stopped', () => {
    const rollup = buildMetaMissionsRollupPacket(
      makeIndex({
        summaries: [
          makeMissionRow({
            metrics: makeMetrics({
              last_run: makeRun({ status: 'graceful_stop' }),
            }),
          }),
        ],
      }),
    );
    expect(rollup?.status).toBe('blocked');
  });

  it('aggregates progress from succeeded_total / total_runs', () => {
    const rollup = buildMetaMissionsRollupPacket(
      makeIndex({
        summaries: [
          makeMissionRow({
            metrics: makeMetrics({ total_runs: 4, succeeded_total: 3 }),
          }),
          makeMissionRow({
            mission_id: 'mis_b',
            metrics: makeMetrics({ total_runs: 6, succeeded_total: 4 }),
          }),
        ],
      }),
    );
    expect(rollup?.progress).toEqual({ completed: 7, total: 10 });
  });
});

describe('buildMetaMissionPackets', () => {
  it('returns empty when index is null or has no summaries', () => {
    expect(buildMetaMissionPackets(null)).toEqual([]);
    expect(buildMetaMissionPackets(makeIndex())).toEqual([]);
  });

  it('emits rollup + mission packets in priority order', () => {
    const packets = buildMetaMissionPackets(
      makeIndex({
        summaries: [
          makeMissionRow({
            mission_id: 'mis_success',
            title: 'Success career',
            metrics: makeMetrics({
              total_runs: 5,
              succeeded_total: 5,
              last_run: makeRun({ status: 'succeeded' }),
            }),
          }),
          makeMissionRow({
            mission_id: 'mis_running',
            title: 'Running career',
            metrics: makeMetrics({
              total_runs: 2,
              running_total: 1,
              last_run: makeRun({ status: 'running' }),
            }),
          }),
          makeMissionRow({
            mission_id: 'mis_failed',
            title: 'Failed career',
            metrics: makeMetrics({
              total_runs: 3,
              failed_total: 1,
              last_run: makeRun({ status: 'failed' }),
            }),
          }),
          makeMissionRow({
            mission_id: 'mis_planned',
            title: 'Planned career',
            status: 'planned',
          }),
        ],
      }),
    );
    // rollup + 4 mission packets
    expect(packets).toHaveLength(5);
    expect(packets[0].id).toBe('meta_missions:rollup_full');
    const missionIds = packets.slice(1).map((p) => p.id);
    expect(missionIds).toEqual([
      'meta_mission:mis_running',
      'meta_mission:mis_failed',
      'meta_mission:mis_planned',
      'meta_mission:mis_success',
    ]);
  });

  it('orders within-bucket by most recent last_run timestamp', () => {
    const packets = buildMetaMissionPackets(
      makeIndex({
        summaries: [
          makeMissionRow({
            mission_id: 'old_failure',
            metrics: makeMetrics({
              total_runs: 1,
              failed_total: 1,
              last_run: makeRun({
                status: 'failed',
                finished_at: '2026-04-20T00:00:00Z',
              }),
            }),
          }),
          makeMissionRow({
            mission_id: 'new_failure',
            metrics: makeMetrics({
              total_runs: 1,
              failed_total: 1,
              last_run: makeRun({
                status: 'failed',
                finished_at: '2026-04-24T02:00:00Z',
              }),
            }),
          }),
        ],
      }),
      { includeRollup: false },
    );
    expect(packets.map((p) => p.id)).toEqual([
      'meta_mission:new_failure',
      'meta_mission:old_failure',
    ]);
  });

  it('bounds the visible list and emits a "+N more" summary', () => {
    const summaries: MetaMissionSummaryRow[] = [];
    for (let i = 0; i < 30; i += 1) {
      summaries.push(
        makeMissionRow({
          mission_id: `mis_${i}`,
          title: `Mission ${i}`,
          metrics: makeMetrics({
            total_runs: 1,
            succeeded_total: 1,
            last_run: makeRun({ status: 'succeeded' }),
          }),
        }),
      );
    }
    const packets = buildMetaMissionPackets(
      makeIndex({ summaries }),
      { missionLimit: 10, includeRollup: false },
    );
    // 10 visible + 1 tail summary = 11
    expect(packets).toHaveLength(11);
    const tail = packets[packets.length - 1];
    expect(tail.id).toBe('meta_missions:tail_summary');
    expect(tail.label).toBe('+20 more');
    expect(tail.status).toBe('idle');
    const labels = tail.metrics!.map((m) => m.label);
    expect(labels).toContain('success');
  });

  it('does not emit a tail summary when list fits within limit', () => {
    const packets = buildMetaMissionPackets(
      makeIndex({
        summaries: [
          makeMissionRow({ mission_id: 'a' }),
          makeMissionRow({ mission_id: 'b' }),
        ],
      }),
      { missionLimit: 24, includeRollup: false },
    );
    expect(packets).toHaveLength(2);
    expect(
      packets.some((p) => p.id === 'meta_missions:tail_summary'),
    ).toBe(false);
  });

  it('skips rollup when includeRollup=false', () => {
    const packets = buildMetaMissionPackets(
      makeIndex({
        summaries: [makeMissionRow({ mission_id: 'a' })],
      }),
      { includeRollup: false },
    );
    expect(packets).toHaveLength(1);
    expect(packets[0].id).toBe('meta_mission:a');
  });
});
