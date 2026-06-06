import { describe, expect, it } from 'vitest';
import type {
  AgentObservabilityStatus,
  AgentTraceEvent,
  AgentTraceMissionIndexResponse,
  AgentTraceMissionRow,
} from '../../../api';
import { compileAgentTraceViewModel, type TraceCompilerTurn, type TraceCompilerVariant } from '../agentTraceViewModel';

function makeRow(overrides: Partial<AgentTraceMissionRow> = {}): AgentTraceMissionRow {
  return {
    provider: 'codex',
    session_id: 'session-123',
    session_file: '/tmp/session-123.jsonl',
    title: 'Agent trace speed pass',
    short_label: 'Trace pass',
    model: 'gpt-5',
    size_bytes: 447_906,
    mtime_utc: '2026-05-20T19:00:00Z',
    last_activity_at: '2026-05-20T19:05:00Z',
    latest_completed_turn: {
      turn_index: 4,
      started_at: '2026-05-20T19:00:00Z',
      completed_at: '2026-05-20T19:04:00Z',
      tool_count: 117,
      error_count: 2,
      prompt_sha16: 'c2c73a46feedbeef',
      prompt_preview: 'make agent trace faster',
      is_complete: true,
    },
    latest_clip: { thin_clip_bytes: 704_000, full_bytes: null, carrier_mode: 'truncated', raw_sidecar: null },
    artifact_refs: { compressed: '/tmp/denoised.md', parsed: '/tmp/compact.json', full: null, full_bytes: 900_000 },
    artifact_freshness: { state: 'current', reason: 'raw current' },
    status: 'active',
    source_newer_than_index: false,
    source_size_changed: false,
    source_missing: false,
    ...overrides,
  };
}

function makeStatus(overrides: Partial<AgentObservabilityStatus> = {}): AgentObservabilityStatus {
  return {
    kind: 'agent_observability_status',
    trace_path: '/tmp/events.jsonl',
    seq: 42,
    history_size: 300,
    max_history: 1500,
    dropped_count: 0,
    gap_count: 0,
    source_status: {},
    active_sessions: [],
    canonical_counts: {},
    source_counts: {},
    sampler: { poll_interval_s: 2 },
    ...overrides,
  } as AgentObservabilityStatus;
}

function makeMissionIndex(row: AgentTraceMissionRow): AgentTraceMissionIndexResponse {
  return {
    available: true,
    source_path: '/Users/example/Library/Application Support/Agent Trace Structurer/mission_index.json',
    generated_at: '2026-05-20T19:06:00Z',
    rows: [row],
    active_rows: [row],
    inactive_rows: [],
    row_count: 1,
    inactive_count: 0,
    hidden_old_count: 0,
  } as AgentTraceMissionIndexResponse;
}

function makeEvent(seq: number, canonicalType: string, summary: string): AgentTraceEvent {
  return {
    id: `event-${seq}`,
    seq,
    schema: 'agent_event_v1',
    trace_id: 'trace-123',
    parent_id: null,
    source_runtime: 'codex',
    source_event_name: canonicalType,
    canonical_type: canonicalType,
    session_id: 'session-123',
    turn_id: 'turn-4',
    tool_use_id: null,
    subagent_id: null,
    cwd: '/workspace/ai_workflow',
    transcript_path: '/tmp/session-123.jsonl',
    artifact_refs: [],
    observed_at: `2026-05-20T19:00:${String(seq).padStart(2, '0')}Z`,
    occurred_at: `2026-05-20T19:00:${String(seq).padStart(2, '0')}Z`,
    summary,
    payload: { content: summary, command: summary },
  };
}

const variants: TraceCompilerVariant[] = [
  { id: 'denoised', name: 'Denoised Handoff v0', state: 'ready', tone: 'ready', size: '704 KB', provenance: 'denoised.md' },
  { id: 'compact', name: 'Compact Evidence v0', state: 'prepare latest', tone: 'prepare_latest', size: '704 KB', provenance: 'not materialized yet' },
  { id: 'full', name: 'Full Manifest', state: 'blocked', tone: 'blocked', size: 'manifest', provenance: 'canonical full producer pending' },
  { id: 'raw', name: 'Raw JSONL', state: 'ready', tone: 'ready', size: '438 KB', provenance: '/tmp/session-123.jsonl' },
];

const turns: TraceCompilerTurn[] = [{
  index: 4,
  startedAt: Date.parse('2026-05-20T19:00:00Z'),
  endedAt: Date.parse('2026-05-20T19:04:00Z'),
  toolCount: 117,
  errorCount: 2,
  isCompleted: true,
  firstUserSummary: 'make agent trace faster',
}];

function compileFixture(overrides: {
  row?: AgentTraceMissionRow;
  events?: AgentTraceEvent[];
  status?: AgentObservabilityStatus | null;
  timelineSource?: string;
} = {}) {
  const row = overrides.row ?? makeRow();
  return compileAgentTraceViewModel({
    row,
    variants,
    turns,
    events: overrides.events ?? [],
    status: overrides.status === undefined ? makeStatus() : overrides.status,
    missionIndex: makeMissionIndex(row),
    missionStatus: null,
    timelineSource: overrides.timelineSource ?? 'mission_index_fallback',
    initialEventWindowLimit: 300,
    sessionEventHistoryLimit: 600,
    streamConnectDelayMs: 1200,
    sessionHistoryDelayMs: 1600,
    sessionProjectionDelayMs: 2800,
  });
}

describe('compileAgentTraceViewModel', () => {
  it('makes fallback and missingness explicit instead of implying authority', () => {
    const vm = compileFixture({
      row: makeRow({
        source_newer_than_index: true,
        source_size_changed: true,
        artifact_freshness: { state: 'stale', reason: 'source newer than index' },
      }),
      status: makeStatus({ dropped_count: 47, gap_count: 2 }),
    });

    expect(vm.provenanceBadges.map((badge) => badge.trust)).toContain('fallback');
    expect(vm.provenanceBadges.map((badge) => badge.trust)).toContain('stale');
    expect(vm.provenanceBadges.map((badge) => badge.trust)).toContain('truncated');
    expect(vm.attention.map((item) => item.id)).toContain('attention-stale-index');
    expect(vm.attention.map((item) => item.id)).toContain('attention-store-gaps');
    expect(vm.unknowns.some((unknown) => unknown.includes('mission_index'))).toBe(true);
  });

  it('classifies observable commands into forensic span lanes and receipts', () => {
    const events = [
      makeEvent(1, 'turn.prompt', 'operator asked for trace viewer course correction'),
      makeEvent(2, 'tool.completed', 'rg AgentObservabilityLens system/server/ui/src'),
      makeEvent(3, 'tool.completed', 'apply_patch AgentObservabilityLens.tsx'),
      makeEvent(4, 'tool.completed', 'npm --prefix system/server/ui run build'),
      makeEvent(5, 'tool.completed', 'station_render screenshot manifest for /station/agent-observability'),
      makeEvent(6, 'tool.completed', 'scoped_commit commit abc123def456'),
      makeEvent(7, 'runtime.error', 'HEAD CAS failed then retry changed parent only'),
    ];

    const vm = compileFixture({ events, timelineSource: 'session_history' });
    const kinds = vm.spans.map((span) => span.kind);

    expect(kinds).toContain('read');
    expect(kinds).toContain('edit');
    expect(kinds).toContain('validation');
    expect(kinds).toContain('render');
    expect(kinds).toContain('commit');
    expect(kinds).toContain('gap');
    expect(vm.receipts.map((receipt) => receipt.kind)).toEqual(expect.arrayContaining(['build', 'screenshot', 'commit']));
    expect(vm.nodes.some((node) => node.kind === 'commit')).toBe(true);
  });

  it('emits an artifact matrix with ready, prepare-latest, blocked, and missing cells', () => {
    const vm = compileFixture();
    const byColumn = new Map(vm.artifactMatrix.map((cell) => [cell.column, cell]));

    expect(byColumn.get('raw')?.state).toBe('ready');
    expect(byColumn.get('compact')?.state).toBe('prepare_latest');
    expect(byColumn.get('full')?.state).toBe('blocked');
    expect(byColumn.get('commit')?.state).toBe('missing');
    expect(vm.attention.some((item) => item.title.includes('Full Manifest'))).toBe(true);
  });
});
