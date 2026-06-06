import type {
  AgentMissionStatus,
  AgentObservabilityStatus,
  AgentTraceEvent,
  AgentTraceMissionIndexResponse,
  AgentTraceMissionRow,
} from '../../api';

export type TraceTrustClass =
  | 'authority'
  | 'projection'
  | 'fallback'
  | 'derived'
  | 'missing'
  | 'stale'
  | 'truncated';

export type TraceStatus = 'ok' | 'warn' | 'error' | 'missing' | 'running' | 'unknown';

export type TraceSpanKind =
  | 'operator'
  | 'decision'
  | 'read'
  | 'edit'
  | 'validation'
  | 'render'
  | 'commit'
  | 'artifact'
  | 'tool'
  | 'gap'
  | 'ui_hydration';

export type TraceNodeKind =
  | 'source'
  | 'prompt'
  | 'decision'
  | 'read'
  | 'edit'
  | 'validation'
  | 'artifact'
  | 'commit'
  | 'receipt'
  | 'residual'
  | 'gap';

export type TraceEdgeKind =
  | 'caused'
  | 'read_before'
  | 'edited'
  | 'validated_by'
  | 'generated'
  | 'committed_as'
  | 'blocked_by'
  | 'superseded_by'
  | 'evidenced_by';

export type ArtifactColumn =
  | 'raw'
  | 'denoised'
  | 'compact'
  | 'full'
  | 'render'
  | 'manifest'
  | 'commit'
  | 'workitem';

export interface TraceCompilerVariant {
  id: string;
  name: string;
  state: string;
  tone: string;
  size: string;
  provenance: string;
  note?: string;
}

export interface TraceCompilerTurn {
  index: number;
  startedAt: number;
  endedAt: number;
  toolCount: number;
  errorCount: number;
  isCompleted: boolean;
  firstUserSummary: string;
  events?: AgentTraceEvent[];
}

export interface TraceEvidenceRef {
  label: string;
  kind: 'event' | 'file' | 'api' | 'artifact' | 'command' | 'projection';
  value: string;
  seq?: number;
}

export interface TraceSpan {
  id: string;
  kind: TraceSpanKind;
  lane: string;
  title: string;
  summary: string;
  startMs: number;
  endMs: number;
  durationMs: number;
  trust: TraceTrustClass;
  source: string;
  status: TraceStatus;
  eventSeq?: number;
  evidenceRefs: TraceEvidenceRef[];
}

export interface TraceNode {
  id: string;
  kind: TraceNodeKind;
  label: string;
  detail: string;
  trust: TraceTrustClass;
  status: TraceStatus;
  evidenceRefs: TraceEvidenceRef[];
}

export interface TraceEdge {
  id: string;
  from: string;
  to: string;
  kind: TraceEdgeKind;
  trust: TraceTrustClass;
}

export interface ArtifactCell {
  id: string;
  turnIndex: number | null;
  column: ArtifactColumn;
  label: string;
  state: 'ready' | 'prepare_latest' | 'blocked' | 'stale' | 'missing' | 'projection_only' | 'running';
  trust: TraceTrustClass;
  detail: string;
  evidenceRef?: TraceEvidenceRef;
}

export interface ValidationReceipt {
  id: string;
  kind: 'build' | 'test' | 'render' | 'screenshot' | 'commit' | 'cleanup' | 'trace' | 'unknown';
  label: string;
  status: TraceStatus;
  trust: TraceTrustClass;
  detail: string;
  evidenceRef?: TraceEvidenceRef;
}

export interface AttentionItem {
  id: string;
  priority: number;
  severity: TraceStatus;
  title: string;
  detail: string;
  action: string;
  trust: TraceTrustClass;
  evidenceRef?: TraceEvidenceRef;
}

export interface TraceStoryStep {
  id: string;
  label: string;
  detail: string;
  status: TraceStatus;
  trust: TraceTrustClass;
  spanIds: string[];
}

export interface LoadAnatomyMetric {
  id: string;
  label: string;
  value: string;
  status: TraceStatus;
  detail: string;
}

export interface AgentTraceViewModel {
  schemaVersion: 'agent_trace_forensics_vm_v1';
  identity: {
    provider: string;
    model: string;
    title: string;
    sessionId: string;
    sessionFile: string | null;
    sourcePath: string | null;
    promptHash: string | null;
    timelineSource: string;
  };
  provenanceBadges: Array<{
    label: string;
    trust: TraceTrustClass;
    status: TraceStatus;
    detail: string;
  }>;
  story: TraceStoryStep[];
  spans: TraceSpan[];
  nodes: TraceNode[];
  edges: TraceEdge[];
  artifactMatrix: ArtifactCell[];
  receipts: ValidationReceipt[];
  attention: AttentionItem[];
  loadAnatomy: LoadAnatomyMetric[];
  unknowns: string[];
  modeCounts: {
    story: number;
    waterfall: number;
    causal: number;
    artifacts: number;
    receipts: number;
    attention: number;
  };
}

export interface AgentTraceViewModelInput {
  row: AgentTraceMissionRow;
  variants: TraceCompilerVariant[];
  turns: TraceCompilerTurn[];
  events: AgentTraceEvent[];
  status: AgentObservabilityStatus | null;
  missionIndex: AgentTraceMissionIndexResponse | null;
  missionStatus: AgentMissionStatus | null;
  timelineSource: string;
  initialEventWindowLimit: number;
  sessionEventHistoryLimit: number;
  streamConnectDelayMs: number;
  sessionHistoryDelayMs: number;
  sessionProjectionDelayMs: number;
}

const TRACE_LANES: Record<TraceSpanKind, string> = {
  operator: 'operator input',
  decision: 'decision rail',
  read: 'reads/searches',
  edit: 'edits',
  validation: 'validation',
  render: 'render/screenshot',
  commit: 'commit/receipt',
  artifact: 'artifacts',
  tool: 'tools',
  gap: 'gaps',
  ui_hydration: 'ui hydration',
};

function compactPath(path?: string | null): string {
  if (!path) return '—';
  const parts = path.split('/').filter(Boolean);
  return parts.length > 3 ? `…/${parts.slice(-3).join('/')}` : path;
}

function formatBytes(bytes?: number | null): string {
  if (bytes == null || !Number.isFinite(bytes)) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(bytes >= 102_400 ? 0 : 1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(bytes >= 100 * 1024 * 1024 ? 0 : 1)} MB`;
}

function formatDurationMs(ms?: number | null): string {
  if (ms == null || !Number.isFinite(ms) || ms < 0) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`;
  const minutes = seconds / 60;
  if (minutes < 60) return `${Math.floor(minutes)}m ${Math.round(seconds - Math.floor(minutes) * 60)}s`;
  return `${Math.floor(minutes / 60)}h ${Math.round(minutes % 60)}m`;
}

function eventTimestamp(event: AgentTraceEvent): number {
  const iso = event.occurred_at || event.observed_at;
  if (!iso) return 0;
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? 0 : t;
}

function payloadText(event: AgentTraceEvent): string {
  const payload = event.payload ?? {};
  const content = payload.content;
  const command = payload.command;
  const toolName = payload.tool_name ?? payload.name;
  return [event.summary, event.source_event_name, content, command, toolName]
    .filter((part): part is string => typeof part === 'string' && part.trim().length > 0)
    .join(' ')
    .trim();
}

function eventTitle(event: AgentTraceEvent): string {
  const payload = event.payload ?? {};
  const toolName = payload.tool_name ?? payload.name;
  if (typeof toolName === 'string' && toolName.trim()) return toolName.trim();
  if (event.summary) return event.summary.slice(0, 64);
  return event.canonical_type;
}

function commandEvidence(event: AgentTraceEvent): TraceEvidenceRef {
  return {
    label: `seq #${event.seq}`,
    kind: 'event',
    value: `${event.canonical_type} · ${event.source_runtime}`,
    seq: event.seq,
  };
}

function classifySpanKind(event: AgentTraceEvent): TraceSpanKind {
  const text = payloadText(event).toLowerCase();
  if (event.canonical_type === 'turn.prompt' || event.canonical_type === 'message.user') return 'operator';
  if (
    event.canonical_type === 'intent.observed'
    || event.canonical_type === 'plan.observed'
    || event.canonical_type === 'message.assistant'
    || event.canonical_type === 'message.thinking'
  ) {
    return 'decision';
  }
  if (event.canonical_type === 'runtime.error' || event.canonical_type === 'stream.gap') return 'gap';
  if (text.match(/\b(apply_patch|multiedit|write|edit)\b/)) return 'edit';
  if (text.match(/\b(station_render|screenshot|playwright|render|viewport)\b/)) return 'render';
  if (text.match(/\b(git|scoped_commit|commit|cas)\b/)) return 'commit';
  if (text.match(/\b(pytest|vitest|npm|run build|build|tsc|lint|test|check)\b/)) return 'validation';
  if (text.match(/\b(rg|grep|sed|cat|nl|find|ls|open|read)\b/)) return 'read';
  if (event.artifact_refs?.length) return 'artifact';
  return event.canonical_type.startsWith('tool.') ? 'tool' : 'decision';
}

function statusForSpan(kind: TraceSpanKind, event: AgentTraceEvent): TraceStatus {
  const text = payloadText(event).toLowerCase();
  if (kind === 'gap') return 'error';
  if (text.match(/\b(error|failed|failure|traceback|exception|cas failed|unreachable)\b/)) return 'error';
  if (text.match(/\b(blocked|missing|stale|truncated|unavailable)\b/)) return 'warn';
  if (event.canonical_type === 'tool.started' || event.canonical_type === 'subagent.started') return 'running';
  return 'ok';
}

function trustForTimelineSource(source: string): TraceTrustClass {
  if (source === 'session_history' || source === 'live_window') return 'authority';
  if (source === 'session_file_projection') return 'projection';
  if (source === 'mission_index_fallback') return 'fallback';
  return 'missing';
}

function trustForVariant(variant: TraceCompilerVariant): TraceTrustClass {
  const state = variant.state.toLowerCase();
  if (state.includes('stale')) return 'stale';
  if (state.includes('blocked') || state.includes('missing') || state.includes('no turn')) return 'missing';
  if (state.includes('prepare')) return 'projection';
  if (state.includes('manifest')) return 'projection';
  return 'authority';
}

function artifactStateForVariant(variant: TraceCompilerVariant): ArtifactCell['state'] {
  const state = variant.state.toLowerCase();
  if (state.includes('stale')) return 'stale';
  if (state.includes('blocked')) return 'blocked';
  if (state.includes('missing') || state.includes('no turn')) return 'missing';
  if (state.includes('prepare')) return 'prepare_latest';
  if (state.includes('manifest')) return 'projection_only';
  return 'ready';
}

function columnForVariant(id: string): ArtifactColumn {
  if (id === 'raw') return 'raw';
  if (id === 'denoised') return 'denoised';
  if (id === 'compact') return 'compact';
  if (id === 'full') return 'full';
  return 'manifest';
}

function latestTurnIndex(row: AgentTraceMissionRow, turns: TraceCompilerTurn[]): number | null {
  return row.latest_completed_turn?.turn_index ?? turns.find((turn) => turn.isCompleted)?.index ?? turns[0]?.index ?? null;
}

function eventSpans(events: AgentTraceEvent[]): TraceSpan[] {
  return [...events].sort((a, b) => a.seq - b.seq).map((event, index) => {
    const kind = classifySpanKind(event);
    const t = eventTimestamp(event);
    const next = events[index + 1] ? eventTimestamp(events[index + 1]) : 0;
    const end = t > 0 ? Math.max(t + 750, next > 0 ? Math.min(next, t + 30_000) : t + 1200) : index + 1;
    return {
      id: `event-${event.seq}`,
      kind,
      lane: TRACE_LANES[kind],
      title: eventTitle(event),
      summary: payloadText(event).slice(0, 180) || event.canonical_type,
      startMs: t || index,
      endMs: end,
      durationMs: Math.max(1, end - (t || index)),
      trust: 'authority',
      source: event.source_runtime,
      status: statusForSpan(kind, event),
      eventSeq: event.seq,
      evidenceRefs: [commandEvidence(event)],
    };
  });
}

function turnSpans(turns: TraceCompilerTurn[], source: string): TraceSpan[] {
  return turns.map((turn) => {
    const start = turn.startedAt || turn.index;
    const end = Math.max(start + 1000, turn.endedAt || start + 1000);
    const kind: TraceSpanKind = turn.errorCount > 0 ? 'gap' : turn.isCompleted ? 'decision' : 'operator';
    return {
      id: `turn-${turn.index}`,
      kind,
      lane: turn.isCompleted ? 'turn cycle' : 'active turn',
      title: `Turn #${turn.index}`,
      summary: turn.firstUserSummary || (turn.isCompleted ? 'completed cycle' : 'in flight'),
      startMs: start,
      endMs: end,
      durationMs: end - start,
      trust: trustForTimelineSource(source),
      source,
      status: turn.errorCount > 0 ? 'error' : turn.isCompleted ? 'ok' : 'running',
      evidenceRefs: [
        {
          label: `turn #${turn.index}`,
          kind: source === 'mission_index_fallback' ? 'projection' : 'event',
          value: `${turn.toolCount} tools · ${turn.errorCount} errors`,
        },
      ],
    };
  });
}

function syntheticHydrationSpans(input: AgentTraceViewModelInput, baseStart: number): TraceSpan[] {
  const rowCount = input.missionIndex?.row_count ?? input.missionIndex?.rows?.length ?? 0;
  return [
    {
      id: 'ui-mission-index',
      kind: 'ui_hydration',
      lane: TRACE_LANES.ui_hydration,
      title: 'mission index fetch',
      summary: `${rowCount} rows · ${formatBytes(input.row.size_bytes ?? null)} selected source`,
      startMs: baseStart,
      endMs: baseStart + 220,
      durationMs: 220,
      trust: input.missionIndex?.available ? 'projection' : 'missing',
      source: '/api/agent-trace/mission-index',
      status: input.missionIndex?.available ? 'ok' : 'missing',
      evidenceRefs: [{
        label: 'mission index',
        kind: 'api',
        value: input.missionIndex?.source_path ?? 'mission_index.json unavailable',
      }],
    },
    {
      id: 'ui-stream-delay',
      kind: 'ui_hydration',
      lane: TRACE_LANES.ui_hydration,
      title: 'live stream deferral',
      summary: `WS opens after first paint delay ${formatDurationMs(input.streamConnectDelayMs)}`,
      startMs: baseStart,
      endMs: baseStart + input.streamConnectDelayMs,
      durationMs: input.streamConnectDelayMs,
      trust: 'derived',
      source: '/ws/agent-observability',
      status: input.status ? 'ok' : 'unknown',
      evidenceRefs: [{ label: 'client constant', kind: 'projection', value: 'STREAM_CONNECT_DELAY_MS' }],
    },
    {
      id: 'ui-session-hydration',
      kind: 'ui_hydration',
      lane: TRACE_LANES.ui_hydration,
      title: 'session history deferral',
      summary: `events after ${formatDurationMs(input.sessionHistoryDelayMs)} · file projection after ${formatDurationMs(input.sessionProjectionDelayMs)}`,
      startMs: baseStart,
      endMs: baseStart + Math.max(input.sessionHistoryDelayMs, input.sessionProjectionDelayMs),
      durationMs: Math.max(input.sessionHistoryDelayMs, input.sessionProjectionDelayMs),
      trust: 'derived',
      source: 'client scheduler',
      status: 'ok',
      evidenceRefs: [{ label: 'client constants', kind: 'projection', value: 'SESSION_HISTORY_DELAY_MS / SESSION_PROJECTION_DELAY_MS' }],
    },
  ];
}

function buildArtifactMatrix(input: AgentTraceViewModelInput): ArtifactCell[] {
  const turnIndex = latestTurnIndex(input.row, input.turns);
  const missionStatusRow = input.missionStatus?.missions.find((mission) => mission.session_id === input.row.session_id)
    ?? input.missionStatus?.demoted_missions.find((mission) => mission.session_id === input.row.session_id)
    ?? null;
  const workItemIds = missionStatusRow?.touched_td_ids ?? [];
  const cells: ArtifactCell[] = input.variants.map((variant) => ({
    id: `artifact-${variant.id}`,
    turnIndex,
    column: columnForVariant(variant.id),
    label: variant.name,
    state: artifactStateForVariant(variant),
    trust: trustForVariant(variant),
    detail: `${variant.state} · ${variant.size} · ${variant.provenance}`,
    evidenceRef: {
      label: variant.name,
      kind: variant.id === 'raw' ? 'file' : 'artifact',
      value: variant.provenance,
    },
  }));
  const eventText = input.events.map(payloadText).join('\n').toLowerCase();
  const hasRender = eventText.includes('station_render') || eventText.includes('screenshot') || eventText.includes('render manifest');
  const hasCommit = eventText.includes('commit ') || eventText.includes('scoped_commit') || eventText.includes('git commit');
  cells.push({
    id: 'artifact-render',
    turnIndex,
    column: 'render',
    label: 'Render receipt',
    state: hasRender ? 'ready' : 'projection_only',
    trust: hasRender ? 'authority' : 'projection',
    detail: hasRender ? 'render command observed in trace events' : 'latest render manifest may exist outside this session trace',
  });
  cells.push({
    id: 'artifact-manifest',
    turnIndex,
    column: 'manifest',
    label: 'Manifest',
    state: input.row.artifact_refs?.full ? 'ready' : 'projection_only',
    trust: input.row.artifact_refs?.full ? 'authority' : 'projection',
    detail: input.row.artifact_refs?.full ? compactPath(input.row.artifact_refs.full) : 'canonical full producer pending or external',
  });
  cells.push({
    id: 'artifact-commit',
    turnIndex,
    column: 'commit',
    label: 'Commit',
    state: hasCommit ? 'ready' : 'missing',
    trust: hasCommit ? 'authority' : 'missing',
    detail: hasCommit ? 'commit evidence appears in events' : 'no commit receipt event in selected trace',
  });
  cells.push({
    id: 'artifact-workitem',
    turnIndex,
    column: 'workitem',
    label: 'WorkItem receipt',
    state: workItemIds.length ? 'ready' : 'projection_only',
    trust: workItemIds.length ? 'authority' : 'projection',
    detail: workItemIds.length ? `linked ${workItemIds.slice(0, 3).join(', ')}` : 'no selected WorkItem receipt bound to this trace',
  });
  return cells;
}

function receiptKind(span: TraceSpan): ValidationReceipt['kind'] {
  const text = `${span.title} ${span.summary}`.toLowerCase();
  if (span.kind === 'render' && text.includes('screenshot')) return 'screenshot';
  if (span.kind === 'render') return 'render';
  if (span.kind === 'commit') return 'commit';
  if (text.includes('cleanup')) return 'cleanup';
  if (text.includes('test') || text.includes('vitest') || text.includes('pytest')) return 'test';
  if (text.includes('build') || text.includes('tsc')) return 'build';
  return span.kind === 'validation' ? 'test' : 'unknown';
}

function buildReceipts(input: AgentTraceViewModelInput, spans: TraceSpan[]): ValidationReceipt[] {
  const receipts: ValidationReceipt[] = spans
    .filter((span) => span.kind === 'validation' || span.kind === 'render' || span.kind === 'commit')
    .slice(-16)
    .map((span) => ({
      id: `receipt-${span.id}`,
      kind: receiptKind(span),
      label: span.title,
      status: span.status,
      trust: span.trust,
      detail: span.summary,
      evidenceRef: span.evidenceRefs[0],
    }));
  receipts.unshift({
    id: 'receipt-trace-store',
    kind: 'trace',
    label: 'agent_observability store',
    status: input.status ? (input.status.gap_count || input.status.dropped_count ? 'warn' : 'ok') : 'unknown',
    trust: input.status ? 'authority' : 'missing',
    detail: input.status
      ? `seq ${input.status.seq} · history ${input.status.history_size}/${input.status.max_history} · dropped ${input.status.dropped_count} · gaps ${input.status.gap_count}`
      : 'store status unavailable',
    evidenceRef: { label: 'status API', kind: 'api', value: '/api/agent-observability/status' },
  });
  receipts.unshift({
    id: 'receipt-mission-index',
    kind: 'trace',
    label: 'mission index',
    status: input.missionIndex?.available ? 'ok' : 'missing',
    trust: input.missionIndex?.available ? 'projection' : 'missing',
    detail: input.missionIndex?.available
      ? `${input.missionIndex.row_count ?? input.missionIndex.rows?.length ?? 0} rows · generated ${input.missionIndex.generated_at ?? 'unknown'}`
      : input.missionIndex?.hint ?? 'mission index unavailable',
    evidenceRef: { label: 'mission index', kind: 'api', value: input.missionIndex?.source_path ?? 'unavailable' },
  });
  return receipts;
}

function buildAttention(input: AgentTraceViewModelInput, matrix: ArtifactCell[], receipts: ValidationReceipt[]): AttentionItem[] {
  const out: AttentionItem[] = [];
  const freshState = (input.row.artifact_freshness?.state ?? '').toLowerCase();
  if (input.row.source_missing) {
    out.push({
      id: 'attention-source-missing',
      priority: 100,
      severity: 'missing',
      title: 'Source JSONL missing',
      detail: 'The mission row points at a provider session file that is not currently on disk.',
      action: 'Open raw source or rebuild mission index on the producer host',
      trust: 'missing',
    });
  }
  if (input.row.source_newer_than_index || input.row.source_size_changed || freshState.includes('stale')) {
    out.push({
      id: 'attention-stale-index',
      priority: 92,
      severity: 'warn',
      title: 'Index is stale against source',
      detail: 'The UI may be rendering an older projection than the provider session file.',
      action: 'Refresh mission index before citing artifact state',
      trust: 'stale',
    });
  }
  if (input.status?.dropped_count || input.status?.gap_count) {
    out.push({
      id: 'attention-store-gaps',
      priority: 88,
      severity: 'warn',
      title: 'Live trace store has gaps',
      detail: `dropped ${input.status.dropped_count} · gaps ${input.status.gap_count}`,
      action: 'Treat waterfall as incomplete and inspect raw session file',
      trust: 'truncated',
    });
  }
  if (input.timelineSource === 'mission_index_fallback') {
    out.push({
      id: 'attention-fallback',
      priority: 82,
      severity: 'warn',
      title: 'Timeline is mission-index fallback',
      detail: 'Turn rows are synthesized; per-command causality is not authority-backed.',
      action: 'Hydrate session events or session-file projection',
      trust: 'fallback',
    });
  }
  for (const cell of matrix) {
    if (cell.state === 'blocked' || cell.state === 'missing') {
      out.push({
        id: `attention-${cell.id}`,
        priority: cell.column === 'raw' ? 86 : 65,
        severity: cell.state === 'blocked' ? 'warn' : 'missing',
        title: `${cell.label} ${cell.state.replace(/_/g, ' ')}`,
        detail: cell.detail,
        action: cell.column === 'commit' ? 'Find commit receipt or leave as uncommitted evidence' : 'Prepare latest or mark unknowable',
        trust: cell.trust,
        evidenceRef: cell.evidenceRef,
      });
    }
  }
  const failedReceipt = receipts.find((receipt) => receipt.status === 'error');
  if (failedReceipt) {
    out.push({
      id: `attention-${failedReceipt.id}`,
      priority: 96,
      severity: 'error',
      title: 'Failed proof receipt',
      detail: failedReceipt.detail,
      action: 'Inspect failure, retry history, and recovery receipt',
      trust: failedReceipt.trust,
      evidenceRef: failedReceipt.evidenceRef,
    });
  }
  if (input.row.active_turn?.turn_index != null) {
    out.push({
      id: 'attention-active-turn',
      priority: 54,
      severity: 'running',
      title: `Turn #${input.row.active_turn.turn_index} in flight`,
      detail: input.row.active_turn.partial_reason ?? 'active turn still open',
      action: 'Watch live stream before promoting artifacts',
      trust: input.timelineSource === 'live_window' || input.timelineSource === 'session_history' ? 'authority' : 'projection',
    });
  }
  return out.sort((a, b) => b.priority - a.priority).slice(0, 12);
}

function buildLoadAnatomy(input: AgentTraceViewModelInput): LoadAnatomyMetric[] {
  const activeRows = input.missionIndex?.active_rows?.length ?? 0;
  const inactiveRows = input.missionIndex?.inactive_rows?.length ?? 0;
  const noiseClasses = input.missionStatus?.telemetry_quality?.noise_classes?.length ?? 0;
  return [
    {
      id: 'load-index',
      label: 'mission index',
      value: `${input.missionIndex?.row_count ?? activeRows + inactiveRows}`,
      status: input.missionIndex?.available ? 'ok' : 'missing',
      detail: `${activeRows} active · ${inactiveRows} inactive · source ${compactPath(input.missionIndex?.source_path)}`,
    },
    {
      id: 'load-events',
      label: 'event window',
      value: `${input.events.length}/${input.sessionEventHistoryLimit}`,
      status: input.timelineSource === 'mission_index_fallback' ? 'warn' : 'ok',
      detail: `initial limit ${input.initialEventWindowLimit} · selected session source ${input.timelineSource}`,
    },
    {
      id: 'load-store',
      label: 'store history',
      value: input.status ? `${input.status.history_size}/${input.status.max_history}` : '—',
      status: input.status ? (input.status.dropped_count || input.status.gap_count ? 'warn' : 'ok') : 'unknown',
      detail: input.status ? `seq ${input.status.seq} · dropped ${input.status.dropped_count} · gaps ${input.status.gap_count}` : 'status unavailable',
    },
    {
      id: 'load-source',
      label: 'source size',
      value: formatBytes(input.row.size_bytes ?? null),
      status: input.row.source_missing ? 'missing' : input.row.source_size_changed ? 'warn' : 'ok',
      detail: compactPath(input.row.session_file),
    },
    {
      id: 'load-stream',
      label: 'stream deferral',
      value: formatDurationMs(input.streamConnectDelayMs),
      status: 'ok',
      detail: 'WS connect is deferred until after mission index first paint',
    },
    {
      id: 'load-noise',
      label: 'telemetry noise',
      value: `${noiseClasses}`,
      status: noiseClasses ? 'warn' : 'ok',
      detail: noiseClasses ? 'mission-status reducer classified noise rows' : 'no classified telemetry noise in mission-status projection',
    },
  ];
}

function buildStory(input: AgentTraceViewModelInput, spans: TraceSpan[], receipts: ValidationReceipt[], attention: AttentionItem[]): TraceStoryStep[] {
  const buckets: Array<[string, string, TraceSpanKind[]]> = [
    ['story-identity', 'Identify', ['operator', 'decision']],
    ['story-read', 'Read / route', ['read', 'tool']],
    ['story-edit', 'Patch', ['edit']],
    ['story-proof', 'Validate / render', ['validation', 'render']],
    ['story-commit', 'Commit / residual', ['commit', 'artifact']],
  ];
  return buckets.map(([id, label, kinds]) => {
    const matching = spans.filter((span) => kinds.includes(span.kind));
    const errors = matching.filter((span) => span.status === 'error').length;
    const warn = matching.filter((span) => span.status === 'warn' || span.status === 'missing').length;
    const receiptCount = receipts.filter((receipt) => {
      if (label.startsWith('Validate')) return receipt.kind === 'build' || receipt.kind === 'test' || receipt.kind === 'render' || receipt.kind === 'screenshot';
      if (label.startsWith('Commit')) return receipt.kind === 'commit';
      return false;
    }).length;
    const status: TraceStatus = errors ? 'error' : warn ? 'warn' : matching.length || receiptCount ? 'ok' : 'unknown';
    return {
      id,
      label,
      detail: matching.length
        ? `${matching.length} observed span${matching.length === 1 ? '' : 's'}${receiptCount ? ` · ${receiptCount} receipt${receiptCount === 1 ? '' : 's'}` : ''}`
        : attention.length && id === 'story-commit'
          ? `${attention.length} attention item${attention.length === 1 ? '' : 's'}`
          : 'not observed in selected trace',
      status,
      trust: matching.some((span) => span.trust === 'authority') ? 'authority' : trustForTimelineSource(input.timelineSource),
      spanIds: matching.map((span) => span.id),
    };
  });
}

function buildNodesAndEdges(input: AgentTraceViewModelInput, spans: TraceSpan[], matrix: ArtifactCell[], receipts: ValidationReceipt[]): {
  nodes: TraceNode[];
  edges: TraceEdge[];
} {
  const nodes: TraceNode[] = [{
    id: 'source',
    kind: 'source',
    label: 'Provider session',
    detail: input.row.session_file ? compactPath(input.row.session_file) : 'session_file missing',
    trust: input.row.session_file ? 'authority' : 'missing',
    status: input.row.source_missing ? 'missing' : 'ok',
    evidenceRefs: [{ label: 'session file', kind: 'file', value: input.row.session_file ?? 'missing' }],
  }];
  const representativeKinds: Array<[TraceSpanKind, TraceNodeKind, string]> = [
    ['operator', 'prompt', 'Operator prompt'],
    ['decision', 'decision', 'Decision rail'],
    ['read', 'read', 'Reads / owner surfaces'],
    ['edit', 'edit', 'Edits'],
    ['validation', 'validation', 'Validations'],
    ['render', 'receipt', 'Render proof'],
    ['commit', 'commit', 'Commit receipt'],
    ['gap', 'gap', 'Incident / gap'],
  ];
  for (const [spanKind, nodeKind, label] of representativeKinds) {
    const matching = spans.filter((span) => span.kind === spanKind);
    if (!matching.length && spanKind !== 'gap') continue;
    nodes.push({
      id: `node-${spanKind}`,
      kind: nodeKind,
      label,
      detail: matching.length ? `${matching.length} span${matching.length === 1 ? '' : 's'}` : 'explicitly not observed',
      trust: matching.some((span) => span.trust === 'authority') ? 'authority' : trustForTimelineSource(input.timelineSource),
      status: matching.some((span) => span.status === 'error') ? 'error' : matching.some((span) => span.status === 'warn') ? 'warn' : matching.length ? 'ok' : 'unknown',
      evidenceRefs: matching.flatMap((span) => span.evidenceRefs).slice(0, 4),
    });
  }
  if (matrix.length) {
    nodes.push({
      id: 'node-artifacts',
      kind: 'artifact',
      label: 'Artifact matrix',
      detail: `${matrix.filter((cell) => cell.state === 'ready').length}/${matrix.length} ready`,
      trust: matrix.some((cell) => cell.trust === 'authority') ? 'authority' : 'projection',
      status: matrix.some((cell) => cell.state === 'blocked' || cell.state === 'missing') ? 'warn' : 'ok',
      evidenceRefs: matrix.flatMap((cell) => cell.evidenceRef ? [cell.evidenceRef] : []).slice(0, 4),
    });
  }
  if (receipts.length) {
    nodes.push({
      id: 'node-receipts',
      kind: 'receipt',
      label: 'Proof receipts',
      detail: `${receipts.filter((receipt) => receipt.status === 'ok').length}/${receipts.length} ok`,
      trust: receipts.some((receipt) => receipt.trust === 'authority') ? 'authority' : 'projection',
      status: receipts.some((receipt) => receipt.status === 'error') ? 'error' : receipts.some((receipt) => receipt.status === 'warn') ? 'warn' : 'ok',
      evidenceRefs: receipts.flatMap((receipt) => receipt.evidenceRef ? [receipt.evidenceRef] : []).slice(0, 4),
    });
  }
  const ordered = ['source', 'node-operator', 'node-decision', 'node-read', 'node-edit', 'node-validation', 'node-render', 'node-artifacts', 'node-commit', 'node-receipts'];
  const edges: TraceEdge[] = [];
  for (let i = 0; i < ordered.length - 1; i += 1) {
    const from = ordered[i];
    const to = ordered[i + 1];
    if (!nodes.some((node) => node.id === from) || !nodes.some((node) => node.id === to)) continue;
    const kind: TraceEdgeKind =
      to === 'node-read' ? 'read_before'
        : to === 'node-edit' ? 'edited'
          : to === 'node-validation' || to === 'node-render' ? 'validated_by'
            : to === 'node-commit' ? 'committed_as'
              : to === 'node-artifacts' ? 'generated'
                : 'caused';
    edges.push({ id: `${from}-${to}`, from, to, kind, trust: trustForTimelineSource(input.timelineSource) });
  }
  const gap = nodes.find((node) => node.id === 'node-gap');
  if (gap) {
    edges.push({ id: 'node-gap-node-receipts', from: 'node-gap', to: 'node-receipts', kind: 'blocked_by', trust: gap.trust });
  }
  return { nodes, edges };
}

function buildProvenanceBadges(input: AgentTraceViewModelInput): AgentTraceViewModel['provenanceBadges'] {
  const badges: AgentTraceViewModel['provenanceBadges'] = [
    {
      label: input.timelineSource.replace(/_/g, ' '),
      trust: trustForTimelineSource(input.timelineSource),
      status: input.timelineSource === 'mission_index_fallback' ? 'warn' : input.timelineSource === 'none' ? 'missing' : 'ok',
      detail: 'timeline source currently driving the workbench',
    },
  ];
  if (input.row.source_newer_than_index || input.row.source_size_changed) {
    badges.push({ label: 'stale projection', trust: 'stale', status: 'warn', detail: 'source file changed after mission index projection' });
  }
  if (!input.row.session_file || input.row.source_missing) {
    badges.push({ label: 'raw missing', trust: 'missing', status: 'missing', detail: 'raw provider session is not authority-backed in this view' });
  } else {
    badges.push({ label: 'raw authority', trust: 'authority', status: 'ok', detail: compactPath(input.row.session_file) });
  }
  if (input.status?.dropped_count || input.status?.gap_count) {
    badges.push({ label: 'truncated/gapped', trust: 'truncated', status: 'warn', detail: `dropped ${input.status.dropped_count} · gaps ${input.status.gap_count}` });
  }
  if (input.events.length === 0) {
    badges.push({ label: 'no event spans', trust: 'fallback', status: 'warn', detail: 'view falls back to session-file or mission-index projections' });
  }
  return badges;
}

function buildUnknowns(input: AgentTraceViewModelInput): string[] {
  const unknowns: string[] = [];
  if (input.events.length === 0) unknowns.push('Per-command causality is unknowable until live events or session history hydrate.');
  if (input.timelineSource === 'mission_index_fallback') unknowns.push('Turn timing is synthesized from mission_index; no event-level parent/child lineage is present.');
  if (input.status?.dropped_count || input.status?.gap_count) unknowns.push('The live event store reports dropped events or stream gaps, so the waterfall may omit spans.');
  if (!input.row.session_file || input.row.source_missing) unknowns.push('Raw provider JSONL is unavailable from this UI state.');
  if (!input.events.some((event) => payloadText(event).toLowerCase().includes('commit'))) unknowns.push('Commit hash and dirty-tree exclusions are not bound unless the trace recorded a commit receipt.');
  if (!input.events.some((event) => payloadText(event).toLowerCase().includes('station_render'))) unknowns.push('Render timing is not authority-bound to this session unless a station_render event or manifest is linked.');
  return unknowns;
}

export function compileAgentTraceViewModel(input: AgentTraceViewModelInput): AgentTraceViewModel {
  const eventDerivedSpans = eventSpans(input.events);
  const baseTurnSpans = input.events.length ? [] : turnSpans(input.turns, input.timelineSource);
  const firstStart = Math.min(
    ...[...eventDerivedSpans, ...baseTurnSpans].map((span) => span.startMs).filter((n) => Number.isFinite(n) && n > 0),
    Date.now(),
  );
  const spans = [
    ...syntheticHydrationSpans(input, firstStart),
    ...baseTurnSpans,
    ...eventDerivedSpans,
  ].sort((a, b) => a.startMs - b.startMs || a.id.localeCompare(b.id));
  const artifactMatrix = buildArtifactMatrix(input);
  const receipts = buildReceipts(input, spans);
  const attention = buildAttention(input, artifactMatrix, receipts);
  const story = buildStory(input, spans, receipts, attention);
  const { nodes, edges } = buildNodesAndEdges(input, spans, artifactMatrix, receipts);
  const unknowns = buildUnknowns(input);
  return {
    schemaVersion: 'agent_trace_forensics_vm_v1',
    identity: {
      provider: input.row.provider,
      model: input.row.model || '—',
      title: input.row.short_label || input.row.title || input.row.session_id.slice(0, 12),
      sessionId: input.row.session_id,
      sessionFile: input.row.session_file ?? null,
      sourcePath: input.missionIndex?.source_path ?? null,
      promptHash: input.row.latest_completed_turn?.prompt_sha16 ?? null,
      timelineSource: input.timelineSource,
    },
    provenanceBadges: buildProvenanceBadges(input),
    story,
    spans,
    nodes,
    edges,
    artifactMatrix,
    receipts,
    attention,
    loadAnatomy: buildLoadAnatomy(input),
    unknowns,
    modeCounts: {
      story: story.length,
      waterfall: spans.length,
      causal: nodes.length,
      artifacts: artifactMatrix.length,
      receipts: receipts.length,
      attention: attention.length,
    },
  };
}
