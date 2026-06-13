/**
 * Live Agent Instrument view model — pure adapter over the backend semantic
 * camera (agent_observability_animation.py). It consumes only backend-owned
 * primitives (channels, kinds, status, priority, quality, claim_state,
 * generated_state, proof.kind/scope) and never parses summaries, commands,
 * file names, or canonical_type text. If the live instrument needs a fact,
 * the backend must emit it; this adapter only shapes it for the visual layer.
 */

import type {
  AgentAnimationActor,
  AgentAnimationAttentionItem,
  AgentAnimationBackpressure,
  AgentAnimationChannel,
  AgentAnimationChannelManifest,
  AgentAnimationCounter,
  AgentAnimationCursor,
  AgentAnimationDeltaOp,
  AgentAnimationEdge,
  AgentAnimationEvent,
  AgentAnimationFileImpact,
  AgentAnimationFlow,
  AgentAnimationNode,
  AgentAnimationProofReceipt,
  AgentAnimationPulse,
  AgentAnimationQualityEnvelope,
  AgentAnimationSegment,
  AgentAnimationSpan,
  AgentAnimationTrack,
  AgentObservabilityAnimationDeltaResponse,
  AgentObservabilityAnimationResponse,
} from '../../api';

/* --------------------------------------------------------------- VM types */

export interface ActorVM {
  id: string;
  sessionId: string;
  provider: string;
  providerLabel: string;
  title: string;
  status: string;
  heartbeat: AgentAnimationActor['heartbeat'];
  lagMs: number | null;
  currentAction: string;
  cwd: string | null;
  eventCount: number;
  touchedFiles: string[];
  sourceRefs: string[];
  attentionCount: number;
  attentionTopSeverity: 'block' | 'warn' | 'info' | null;
  proofPassCount: number;
  proofFailCount: number;
  proofRunningCount: number;
  fileEditCount: number;
  fileReadCount: number;
  fileCollisionCount: number;
  qualityNotes: string[];
  rankBucket: number;
  rankReason: string;
  raw: AgentAnimationActor;
}

export interface LaneSegmentVM extends AgentAnimationSegment {
  visibleByChannel: boolean;
}

export interface LaneVM {
  trackId: string;
  actorId: string;
  sessionId: string;
  provider: string;
  providerLabel: string;
  laneIndex: number;
  segments: LaneSegmentVM[];
  visibleSegments: LaneSegmentVM[];
  segmentsByChannel: Record<string, LaneSegmentVM[]>;
  activeChannelCount: number;
}

export interface FileImpactVM extends AgentAnimationFileImpact {
  isCollision: boolean;
  isGenerated: boolean;
  isOwnedSelf: boolean;
}

export interface ProofReceiptVM extends AgentAnimationProofReceipt {
  scopeBucket: 'owned' | 'unowned' | 'generated' | 'unknown';
  statusBucket: 'pass' | 'fail' | 'running' | 'blocked' | 'observed' | 'unknown';
}

export interface ChannelVM extends AgentAnimationChannelManifest {
  visible: boolean;
}

/**
 * Readiness envelope synthesized from backend semantic-camera fields.
 * Every reason here is a typed-field condition (cursor / backpressure /
 * data_quality / actor.quality.missingness). No summary/regex/string
 * parsing — if a fact is missing, the backend must emit it.
 */
export interface StreamHealthVM {
  degraded: boolean;
  snapshotRequired: boolean;
  staleActorCount: number;
  lostActorCount: number;
  unknownActorCount: number;
  degradedReasons: string[];
  attentionSuppressionReasons: string[];
  attentionUnderfiring: boolean;
  historySaturationRatio: number | null;
  deltaOpSaturationRatio: number | null;
  droppedEventCount: number;
  droppedOpCount: number;
  gapCount: number;
}

/**
 * Repo-impact grouping over file_impacts, keyed by path. Collapses the
 * "197 files with 600 TOUCH rows" shape into one decision row per file
 * with operation-multiset, collision count, generated state, and the
 * stable claim_state for that path.
 */
export interface FileImpactGroupVM {
  path: string;
  operationCounts: Record<string, number>;
  totalEventCount: number;
  collisionCount: number;
  ownedSelfCount: number;
  generatedState: string;
  claimState: string;
  isCollision: boolean;
  isGenerated: boolean;
  isOwnedSelf: boolean;
  channels: string[];
  actorIds: string[];
  firstSeq: number | null;
  lastSeq: number | null;
  representative: FileImpactVM;
}

/**
 * Proof-receipt authority summary. Surfaces "unknown" as a typed missingness
 * defect rather than collapsing it with pass/fail/running/observed.
 */
export interface ProofAuthoritySummary {
  totalReceipts: number;
  byStatus: Record<ProofReceiptVM['statusBucket'], number>;
  byScope: Record<ProofReceiptVM['scopeBucket'], number>;
  unknownStatusCount: number;
  unknownScopeCount: number;
  missingnessRatio: number;
}

/**
 * Provider health: explains the operator-visible "Unknown" provider bucket
 * as a backend ingestion missingness (no source_runtime tag), not a vague
 * label. Derived strictly from typed provider/source_runtime fields.
 */
export interface ProviderHealthVM {
  provider: string;
  providerLabel: string;
  actorCount: number;
  isUnknown: boolean;
  explanation: string | null;
}

export interface LiveInstrumentVM {
  generatedAt: string;
  authorityBoundary: string;
  window: AgentObservabilityAnimationResponse['window'];
  summary: AgentObservabilityAnimationResponse['summary'];
  providerLegend: Array<{ source_runtime: string; label: string }>;
  channels: ChannelVM[];
  visibleChannelIds: Set<string>;
  cursor: AgentAnimationCursor;
  backpressure: AgentAnimationBackpressure;
  dataQuality: AgentObservabilityAnimationResponse['data_quality'];
  snapshotRequired: boolean;
  snapshotReason: string | null;
  staleStream: boolean;
  degradedStream: boolean;
  actors: ActorVM[];
  lanes: LaneVM[];
  attention: AgentAnimationAttentionItem[];
  attentionByActor: Map<string, AgentAnimationAttentionItem[]>;
  fileImpacts: FileImpactVM[];
  fileImpactsByActor: Map<string, FileImpactVM[]>;
  proofReceipts: ProofReceiptVM[];
  proofReceiptsByActor: Map<string, ProofReceiptVM[]>;
  counters: AgentAnimationCounter[];
  countersByName: Record<string, AgentAnimationCounter>;
  flows: AgentAnimationFlow[];
  selectedActor: ActorVM | null;
  selectedActorLane: LaneVM | null;
  selectedActorAttention: AgentAnimationAttentionItem[];
  selectedActorFileImpacts: FileImpactVM[];
  selectedActorProofReceipts: ProofReceiptVM[];
  selectedActorEvents: AgentAnimationEvent[];
  events: AgentAnimationEvent[];
  emptyReason: 'no_active_actors' | 'no_events' | 'snapshot_required' | null;
  /** Readiness envelope: degradation / suppression reasons synthesized from backend fields. */
  streamHealth: StreamHealthVM;
  /** Repo impact collapsed by path; replaces the raw N-per-event blast for operator decision use. */
  fileImpactGroups: FileImpactGroupVM[];
  /** Proof receipt authority taxonomy — pass/fail/running/observed/unknown stay distinct. */
  proofAuthority: ProofAuthoritySummary;
  /** Per-provider actor counts with backend-grounded explanation for the 'unknown' bucket. */
  providerHealth: ProviderHealthVM[];
}

export interface LiveInstrumentVMInput {
  scene: AgentObservabilityAnimationResponse;
  selectedChannelIds?: Iterable<string> | null;
  selectedActorId?: string | null;
}

/* ------------------------------------------------- delta merge (replayable) */

function cloneScene(scene: AgentObservabilityAnimationResponse): AgentObservabilityAnimationResponse {
  return {
    ...scene,
    summary: { ...scene.summary },
    actors: scene.actors.map((actor) => ({ ...actor })),
    tracks: scene.tracks.map((track) => ({
      ...track,
      segments: (Array.isArray(track.segments) ? track.segments : []).map((segment) => ({ ...segment })),
    })),
    events: scene.events.map((event) => ({ ...event })),
    nodes: scene.nodes.map((node) => ({ ...node })),
    edges: scene.edges.map((edge) => ({ ...edge })),
    spans: scene.spans.map((span) => ({ ...span })),
    flows: scene.flows.map((flow) => ({ ...flow })),
    counters: scene.counters.map((counter) => ({ ...counter })),
    file_impacts: scene.file_impacts.map((impact) => ({ ...impact })),
    proof_receipts: scene.proof_receipts.map((receipt) => ({ ...receipt })),
    pulses: scene.pulses.map((pulse) => ({ ...pulse })),
    attention: scene.attention.map((item) => ({ ...item })),
    channels: scene.channels.map((channel) => ({ ...channel })),
    cursor: { ...scene.cursor },
    backpressure: { ...scene.backpressure },
    data_quality: { ...scene.data_quality },
  };
}

function upsertById<T extends { id?: string }>(list: T[], item: T): T[] {
  const id = String(item.id ?? '');
  if (!id) {
    return [...list, item];
  }
  const index = list.findIndex((existing) => String(existing.id ?? '') === id);
  if (index < 0) {
    return [...list, item];
  }
  const next = [...list];
  next[index] = item;
  return next;
}

function upsertTrack(list: AgentAnimationTrack[], item: AgentAnimationTrack): AgentAnimationTrack[] {
  const id = String(item.id ?? '');
  const itemSegments = Array.isArray(item.segments) ? item.segments : null;
  const normalizedItem = { ...item, segments: itemSegments ?? [] };
  if (!id) {
    return [...list, normalizedItem];
  }
  const index = list.findIndex((existing) => String(existing.id ?? '') === id);
  if (index < 0) {
    return [...list, normalizedItem];
  }
  const existing = list[index];
  const next = [...list];
  next[index] = {
    ...existing,
    ...item,
    segments: itemSegments ?? (Array.isArray(existing.segments) ? existing.segments : []),
  };
  return next;
}

function upsertSegmentInTracks(
  tracks: AgentAnimationTrack[],
  sessionId: string,
  segment: AgentAnimationSegment,
): AgentAnimationTrack[] {
  return tracks.map((track) => {
    if (track.session_id !== sessionId) return track;
    const currentSegments = Array.isArray(track.segments) ? track.segments : [];
    const segIndex = currentSegments.findIndex((existing) => existing.id === segment.id);
    if (segIndex < 0) {
      return { ...track, segments: [...currentSegments, segment] };
    }
    const segments = [...currentSegments];
    segments[segIndex] = segment;
    return { ...track, segments };
  });
}

function applyOp(scene: AgentObservabilityAnimationResponse, op: AgentAnimationDeltaOp): AgentObservabilityAnimationResponse {
  const payload = (op.payload ?? {}) as Record<string, unknown>;
  switch (op.op) {
    case 'actor_upsert':
      return { ...scene, actors: upsertById(scene.actors, payload as unknown as AgentAnimationActor) };
    case 'track_upsert':
      return { ...scene, tracks: upsertTrack(scene.tracks, payload as unknown as AgentAnimationTrack) };
    case 'segment_upsert': {
      const segment = payload as unknown as AgentAnimationSegment;
      const sessionId = String(op.session_id ?? (payload.session_id as string | undefined) ?? '');
      const next = upsertSegmentInTracks(scene.tracks, sessionId, segment);
      return { ...scene, tracks: next };
    }
    case 'event_append': {
      const event = payload as unknown as AgentAnimationEvent;
      const next = upsertById(scene.events, event).sort((a, b) => a.seq - b.seq);
      return { ...scene, events: next };
    }
    case 'node_upsert':
      return { ...scene, nodes: upsertById(scene.nodes, payload as unknown as AgentAnimationNode) };
    case 'edge_upsert':
      return { ...scene, edges: upsertById(scene.edges, payload as unknown as AgentAnimationEdge) };
    case 'pulse_emit':
      return { ...scene, pulses: [...scene.pulses, payload as unknown as AgentAnimationPulse] };
    case 'attention_upsert':
      return { ...scene, attention: upsertById(scene.attention, payload as unknown as AgentAnimationAttentionItem) };
    case 'span_upsert':
      return { ...scene, spans: upsertById(scene.spans, payload as unknown as AgentAnimationSpan) };
    case 'flow_upsert':
      return { ...scene, flows: upsertById(scene.flows, payload as unknown as AgentAnimationFlow) };
    case 'counter_update':
      return { ...scene, counters: upsertById(scene.counters, payload as unknown as AgentAnimationCounter) };
    case 'file_impact_upsert':
      return { ...scene, file_impacts: upsertById(scene.file_impacts, payload as unknown as AgentAnimationFileImpact) };
    case 'proof_receipt_upsert':
      return { ...scene, proof_receipts: upsertById(scene.proof_receipts, payload as unknown as AgentAnimationProofReceipt) };
    case 'quality_update':
      return {
        ...scene,
        data_quality: { ...scene.data_quality, ...(payload as unknown as AgentObservabilityAnimationResponse['data_quality']) },
      };
    default:
      return scene;
  }
}

export interface ApplyDeltaResult {
  scene: AgentObservabilityAnimationResponse;
  snapshotRequired: boolean;
  snapshotReason: string | null;
}

/**
 * Union channel manifests across a delta instead of replacing. Each delta
 * rebuilds its manifest from only the events since the cursor, so a 1-2s slice
 * would otherwise SHRINK the channel set to whatever it happened to contain —
 * the visible cause of the floor "cycling through channels" and hiding every
 * segment off the surviving channel. Merging keeps the set monotonic within a
 * scene lifetime and keeps each channel's count at the larger of the two so a
 * sparse slice does not flicker a count down to zero.
 */
function mergeChannelManifests(
  base: AgentAnimationChannelManifest[],
  incoming: AgentAnimationChannelManifest[],
): AgentAnimationChannelManifest[] {
  if (incoming.length === 0) return base;
  const byId = new Map<string, AgentAnimationChannelManifest>();
  const order: string[] = [];
  for (const ch of base) {
    byId.set(String(ch.id), { ...ch });
    order.push(String(ch.id));
  }
  for (const ch of incoming) {
    const id = String(ch.id);
    const existing = byId.get(id);
    if (existing) {
      existing.event_count = Math.max(existing.event_count ?? 0, ch.event_count ?? 0);
      existing.label = ch.label || existing.label;
      existing.visible_by_default = ch.visible_by_default;
    } else {
      byId.set(id, { ...ch });
      order.push(id);
    }
  }
  return order.map((id) => byId.get(id) as AgentAnimationChannelManifest);
}

export function applyAnimationDelta(
  scene: AgentObservabilityAnimationResponse,
  delta: AgentObservabilityAnimationDeltaResponse,
): ApplyDeltaResult {
  if (delta.snapshot_required) {
    return {
      scene,
      snapshotRequired: true,
      snapshotReason: delta.snapshot_reason ?? 'snapshot_required',
    };
  }
  const base = cloneScene(scene);
  // Layer delta-level data quality first so newer counts win for fields the
  // ops do not specifically touch; subsequent quality_update ops then take
  // precedence for the fields they explicitly carry.
  base.data_quality = { ...base.data_quality, ...delta.data_quality };
  const merged = delta.ops.reduce<AgentObservabilityAnimationResponse>((acc, op) => applyOp(acc, op), base);
  return {
    scene: {
      ...merged,
      generated_at: delta.generated_at,
      cursor: delta.cursor,
      backpressure: delta.backpressure,
      channels: mergeChannelManifests(merged.channels, delta.channels),
    },
    snapshotRequired: false,
    snapshotReason: null,
  };
}

/* ------------------------------------------------------- VM construction */

function statusBucket(status: string | undefined): ProofReceiptVM['statusBucket'] {
  switch (status) {
    case 'pass':
      return 'pass';
    case 'fail':
      return 'fail';
    case 'running':
      return 'running';
    case 'blocked':
      return 'blocked';
    case 'observed':
      return 'observed';
    default:
      return 'unknown';
  }
}

function scopeBucket(scope: string | undefined): ProofReceiptVM['scopeBucket'] {
  switch (scope) {
    case 'owned_surface':
    case 'owned_files':
      return 'owned';
    case 'full_repo_or_frontend':
      return 'unowned';
    case 'generated_projection':
      return 'generated';
    default:
      return 'unknown';
  }
}

function severityRank(severity: string | undefined): number {
  if (severity === 'block') return 3;
  if (severity === 'warn') return 2;
  if (severity === 'info') return 1;
  return 0;
}

function topSeverity(items: AgentAnimationAttentionItem[]): ActorVM['attentionTopSeverity'] {
  if (items.length === 0) return null;
  let best: number = 0;
  let top: ActorVM['attentionTopSeverity'] = null;
  for (const item of items) {
    const rank = severityRank(item.severity);
    if (rank > best) {
      best = rank;
      top = (item.severity === 'block' || item.severity === 'warn' || item.severity === 'info')
        ? item.severity
        : null;
    }
  }
  return top;
}

function qualityNotesForActor(actor: AgentAnimationActor): string[] {
  const notes: string[] = [];
  if (actor.heartbeat === 'stale') notes.push('stale_heartbeat');
  if (actor.heartbeat === 'lost') notes.push('lost_heartbeat');
  if (actor.heartbeat === 'unknown') notes.push('heartbeat_unknown');
  if (actor.mid_turn === true) notes.push('mid_turn');
  if (actor.currently_live === false) notes.push('not_currently_live');
  const declared = actor.quality?.missingness ?? [];
  for (const note of declared) {
    if (note && !notes.includes(note)) notes.push(note);
  }
  return notes;
}

function defaultVisibleChannelSet(channels: AgentAnimationChannelManifest[]): Set<string> {
  return new Set(channels.filter((channel) => channel.visible_by_default).map((channel) => String(channel.id)));
}

/* --------------------------------------------- readiness envelope synthesis */

const SATURATION_NOTABLE_RATIO = 0.5;
const SATURATION_HIGH_RATIO = 0.9;

function deltaOpSaturationRatio(backpressure: AgentAnimationBackpressure): number | null {
  if (!backpressure || !backpressure.max_ops_per_delta || backpressure.max_ops_per_delta <= 0) return null;
  const ratio = backpressure.op_count / backpressure.max_ops_per_delta;
  return Number.isFinite(ratio) ? Math.max(0, Math.min(1, ratio)) : null;
}

function buildStreamHealth(
  scene: AgentObservabilityAnimationResponse,
  actors: ActorVM[],
  attention: AgentAnimationAttentionItem[],
): StreamHealthVM {
  const bp = scene.backpressure;
  const dq = scene.data_quality;
  const droppedEventCount = Number(dq.dropped_count ?? bp.dropped_event_count ?? 0);
  const droppedOpCount = Number(bp.dropped_op_count ?? 0);
  const gapCount = Number(dq.gap_count ?? bp.gap_count ?? 0);
  const historySaturation = typeof bp.history_saturation_ratio === 'number' ? bp.history_saturation_ratio : null;
  const opSaturation = deltaOpSaturationRatio(bp);

  const degradedReasons: string[] = [];
  if (droppedEventCount > 0) degradedReasons.push(`dropped_events:${droppedEventCount}`);
  if (droppedOpCount > 0) degradedReasons.push(`dropped_ops:${droppedOpCount}`);
  if (gapCount > 0) degradedReasons.push(`stream_gaps:${gapCount}`);
  if (historySaturation != null && historySaturation >= SATURATION_HIGH_RATIO) degradedReasons.push('history_saturation_high');
  if (opSaturation != null && opSaturation >= SATURATION_HIGH_RATIO) degradedReasons.push('delta_op_saturation_high');
  if (dq.snapshot_required) degradedReasons.push('snapshot_required');
  for (const note of dq.projection_notes ?? []) {
    if (note && !degradedReasons.includes(`projection:${note}`)) degradedReasons.push(`projection:${note}`);
  }
  if (bp.degraded && degradedReasons.length === 0) {
    // Backend flagged degraded but no specific signal — surface that as its own reason rather than hiding it.
    degradedReasons.push('backend_degraded_unspecified');
  }

  const staleActorCount = actors.filter((a) => a.heartbeat === 'stale').length;
  const lostActorCount = actors.filter((a) => a.heartbeat === 'lost').length;
  const unknownActorCount = actors.filter((a) => a.heartbeat === 'unknown').length;

  // Attention suppression policy: when stream is degraded but the attention queue is empty,
  // a justification reason MUST be emitted from typed fields, otherwise the queue is under-firing.
  const attentionUnderfiring = bp.degraded && attention.length === 0
    && droppedEventCount === 0 && droppedOpCount === 0 && gapCount === 0
    && !dq.snapshot_required;
  const attentionSuppressionReasons: string[] = [];
  if (bp.degraded && attention.length === 0) {
    if (droppedEventCount === 0 && droppedOpCount === 0 && gapCount === 0 && !dq.snapshot_required) {
      attentionSuppressionReasons.push('degraded_without_loss_or_gap');
    }
    if (historySaturation != null && historySaturation >= SATURATION_NOTABLE_RATIO && historySaturation < SATURATION_HIGH_RATIO) {
      attentionSuppressionReasons.push('history_saturation_notable_below_high');
    }
    if (opSaturation != null && opSaturation >= SATURATION_NOTABLE_RATIO && opSaturation < SATURATION_HIGH_RATIO) {
      attentionSuppressionReasons.push('delta_op_saturation_notable_below_high');
    }
  }

  return {
    degraded: Boolean(bp.degraded),
    snapshotRequired: Boolean(dq.snapshot_required),
    staleActorCount,
    lostActorCount,
    unknownActorCount,
    degradedReasons,
    attentionSuppressionReasons,
    attentionUnderfiring,
    historySaturationRatio: historySaturation,
    deltaOpSaturationRatio: opSaturation,
    droppedEventCount,
    droppedOpCount,
    gapCount,
  };
}

function buildFileImpactGroups(impacts: FileImpactVM[]): FileImpactGroupVM[] {
  const groups = new Map<string, FileImpactGroupVM>();
  for (const impact of impacts) {
    const path = impact.path;
    if (!path) continue;
    let group = groups.get(path);
    if (!group) {
      group = {
        path,
        operationCounts: {},
        totalEventCount: 0,
        collisionCount: 0,
        ownedSelfCount: 0,
        generatedState: impact.generated_state,
        claimState: impact.claim_state,
        isCollision: false,
        isGenerated: false,
        isOwnedSelf: false,
        channels: [],
        actorIds: [],
        firstSeq: null,
        lastSeq: null,
        representative: impact,
      };
      groups.set(path, group);
    }
    const op = String(impact.operation || 'touch');
    group.operationCounts[op] = (group.operationCounts[op] ?? 0) + 1;
    group.totalEventCount += 1;
    if (impact.isCollision) group.collisionCount += 1;
    if (impact.isOwnedSelf) group.ownedSelfCount += 1;
    // Generated/claim states are taken from the strongest signal: collision > self > unclaimed; generated > source.
    if (impact.generated_state === 'generated_projection' && group.generatedState !== 'generated_projection') {
      group.generatedState = 'generated_projection';
    }
    if (impact.claim_state === 'owned_by_other') group.claimState = 'owned_by_other';
    else if (impact.claim_state === 'owned_by_self' && group.claimState !== 'owned_by_other') group.claimState = 'owned_by_self';
    const ch = String(impact.channel ?? '');
    if (ch && !group.channels.includes(ch)) group.channels.push(ch);
    const actor = impact.actor_id ?? '';
    if (actor && !group.actorIds.includes(actor)) group.actorIds.push(actor);
    if (typeof impact.seq === 'number') {
      if (group.firstSeq == null || impact.seq < group.firstSeq) group.firstSeq = impact.seq;
      if (group.lastSeq == null || impact.seq > group.lastSeq) group.lastSeq = impact.seq;
    }
  }
  // Re-derive booleans from the rolled-up state.
  for (const group of groups.values()) {
    group.isCollision = group.claimState === 'owned_by_other';
    group.isGenerated = group.generatedState === 'generated_projection';
    group.isOwnedSelf = group.claimState === 'owned_by_self';
  }
  // Order: collisions first, then by event count desc, then path.
  return [...groups.values()].sort((a, b) => {
    if (a.isCollision !== b.isCollision) return a.isCollision ? -1 : 1;
    if (a.totalEventCount !== b.totalEventCount) return b.totalEventCount - a.totalEventCount;
    return a.path.localeCompare(b.path);
  });
}

function buildProofAuthoritySummary(receipts: ProofReceiptVM[]): ProofAuthoritySummary {
  const byStatus: Record<ProofReceiptVM['statusBucket'], number> = {
    pass: 0, fail: 0, running: 0, blocked: 0, observed: 0, unknown: 0,
  };
  const byScope: Record<ProofReceiptVM['scopeBucket'], number> = {
    owned: 0, unowned: 0, generated: 0, unknown: 0,
  };
  for (const receipt of receipts) {
    byStatus[receipt.statusBucket] += 1;
    byScope[receipt.scopeBucket] += 1;
  }
  const total = receipts.length;
  const unknownStatusCount = byStatus.unknown;
  const unknownScopeCount = byScope.unknown;
  const missingnessRatio = total === 0 ? 0 : (unknownStatusCount + unknownScopeCount) / (total * 2);
  return {
    totalReceipts: total,
    byStatus,
    byScope,
    unknownStatusCount,
    unknownScopeCount,
    missingnessRatio,
  };
}

function buildProviderHealth(actors: ActorVM[], legend: Array<{ source_runtime: string; label: string }>): ProviderHealthVM[] {
  const counts = new Map<string, { provider: string; providerLabel: string; actorCount: number }>();
  for (const actor of actors) {
    const key = actor.provider;
    const row = counts.get(key) ?? { provider: actor.provider, providerLabel: actor.providerLabel, actorCount: 0 };
    row.actorCount += 1;
    counts.set(key, row);
  }
  // Include legend entries with zero actors so the provider roster still reflects the backend declaration.
  for (const entry of legend) {
    if (!counts.has(entry.source_runtime)) {
      counts.set(entry.source_runtime, { provider: entry.source_runtime, providerLabel: entry.label, actorCount: 0 });
    }
  }
  const result: ProviderHealthVM[] = [];
  for (const row of counts.values()) {
    const isUnknown =
      row.provider === 'unknown' ||
      row.providerLabel === 'Unknown' ||
      row.provider === '' ||
      row.providerLabel === '';
    const explanation = isUnknown && row.actorCount > 0
      ? 'session_lacks_source_runtime_tag_in_ingestion'
      : null;
    result.push({
      provider: row.provider,
      providerLabel: row.providerLabel || row.provider || 'Unknown',
      actorCount: row.actorCount,
      isUnknown,
      explanation,
    });
  }
  result.sort((a, b) => {
    if (a.isUnknown !== b.isUnknown) return a.isUnknown ? 1 : -1;
    if (a.actorCount !== b.actorCount) return b.actorCount - a.actorCount;
    return a.providerLabel.localeCompare(b.providerLabel);
  });
  return result;
}

/**
 * Provider identity grammar: a persistent chroma layer keyed off source_runtime +
 * label. Severity stays encoded by status/proof/attention; provider is identity,
 * not severity (operator priority controls order; provider controls chroma).
 */
export type ProviderIdentity = 'openai' | 'claude' | 'gemini' | 'unknown' | 'infra';

export function providerIdentity(source: string | undefined, label: string | undefined): ProviderIdentity {
  const s = `${source ?? ''} ${label ?? ''}`.toLowerCase();
  if (s.includes('claude') || s.includes('anthropic')) return 'claude';
  if (s.includes('codex') || s.includes('openai') || s.includes('gpt')) return 'openai';
  if (s.includes('gemini') || s.includes('google')) return 'gemini';
  if (s.includes('station') || s.includes('metabolism') || s.includes('bridge') || s.includes('operator') || s.includes('infra')) return 'infra';
  return 'unknown';
}

const RANK_ACTIVE_STATUSES = new Set(['editing', 'validating', 'rendering', 'committing', 'tool_running', 'model_turn', 'working', 'waiting_operator']);

/**
 * Operator-priority rank: a bucket + a human-legible reason for WHY a row ranks
 * where it does. Display-only and consistent with the actors.sort order below
 * (which is intentionally left intact). 0 = attention-now (loudest) … 5 = archive.
 */
export function deriveRank(a: {
  heartbeat: ActorVM['heartbeat'];
  status: string;
  attentionTopSeverity: ActorVM['attentionTopSeverity'];
  attentionCount: number;
  proofFailCount: number;
  raw: AgentAnimationActor;
}): { bucket: number; reason: string } {
  const activeStatus = RANK_ACTIVE_STATUSES.has(a.status);
  const live = a.heartbeat === 'live';
  const currentlyActive = live && (a.raw.currently_live === true || a.raw.mid_turn === true || activeStatus);
  const blocked = a.attentionTopSeverity === 'block' || a.status === 'blocked' || a.status === 'error';
  if (currentlyActive && (blocked || a.proofFailCount > 0)) {
    return { bucket: 0, reason: blocked ? 'tool error' : 'proof failing' };
  }
  if (currentlyActive) {
    if (activeStatus) return { bucket: 1, reason: a.status.replace(/_/g, ' ') };
    if (a.raw.mid_turn === true) return { bucket: 1, reason: 'mid turn' };
    return { bucket: 1, reason: 'live' };
  }
  if (live) return { bucket: 2, reason: a.raw.mid_turn === true ? 'mid turn' : 'live idle' };
  if (a.attentionCount > 0) {
    return { bucket: 3, reason: a.attentionTopSeverity === 'block' ? 'attention block' : a.proofFailCount > 0 ? 'proof failing' : 'attention' };
  }
  if (a.heartbeat === 'stale') return { bucket: 4, reason: 'heartbeat stale' };
  if (a.heartbeat === 'lost') return { bucket: 4, reason: 'heartbeat lost' };
  return { bucket: 5, reason: 'archive' };
}

export function buildLiveInstrumentViewModel(input: LiveInstrumentVMInput): LiveInstrumentVM {
  const { scene } = input;
  const explicitVisible = input.selectedChannelIds == null ? null : new Set(Array.from(input.selectedChannelIds, (id) => String(id)));
  const visibleChannelIds = explicitVisible ?? defaultVisibleChannelSet(scene.channels);

  const channels: ChannelVM[] = scene.channels.map((channel) => ({
    ...channel,
    visible: visibleChannelIds.has(String(channel.id)),
  }));

  // Index attention / file_impacts / proof_receipts by actor.
  const attentionByActor = new Map<string, AgentAnimationAttentionItem[]>();
  for (const item of scene.attention) {
    const key = item.actor_id ?? (item.session_id ? `actor:${item.session_id}` : '');
    if (!key) continue;
    const list = attentionByActor.get(key) ?? [];
    list.push(item);
    attentionByActor.set(key, list);
  }

  const fileImpactsByActor = new Map<string, FileImpactVM[]>();
  const fileImpacts: FileImpactVM[] = scene.file_impacts.map((impact) => {
    const vm: FileImpactVM = {
      ...impact,
      isCollision: impact.claim_state === 'owned_by_other',
      isGenerated: impact.generated_state === 'generated_projection',
      isOwnedSelf: impact.claim_state === 'owned_by_self',
    };
    const key = vm.actor_id ?? (vm.session_id ? `actor:${vm.session_id}` : '');
    if (key) {
      const list = fileImpactsByActor.get(key) ?? [];
      list.push(vm);
      fileImpactsByActor.set(key, list);
    }
    return vm;
  });

  const proofReceiptsByActor = new Map<string, ProofReceiptVM[]>();
  const proofReceipts: ProofReceiptVM[] = scene.proof_receipts.map((receipt) => {
    const vm: ProofReceiptVM = {
      ...receipt,
      scopeBucket: scopeBucket(receipt.scope),
      statusBucket: statusBucket(receipt.status),
    };
    const key = vm.actor_id ?? (vm.session_id ? `actor:${vm.session_id}` : '');
    if (key) {
      const list = proofReceiptsByActor.get(key) ?? [];
      list.push(vm);
      proofReceiptsByActor.set(key, list);
    }
    return vm;
  });

  // Build actor VMs with attention/proof/file counts that come from backend-owned facts.
  const actors: ActorVM[] = scene.actors.map((actor) => {
    const myAttention = attentionByActor.get(actor.id) ?? [];
    const myProofs = proofReceiptsByActor.get(actor.id) ?? [];
    const myFiles = fileImpactsByActor.get(actor.id) ?? [];
    const base = {
      id: actor.id,
      sessionId: actor.session_id,
      provider: actor.provider,
      providerLabel: actor.provider_label,
      title: actor.title,
      status: actor.status,
      heartbeat: actor.heartbeat,
      lagMs: actor.lag_ms ?? null,
      currentAction: actor.current_action,
      cwd: actor.cwd ?? null,
      eventCount: actor.event_count,
      touchedFiles: [...actor.touched_files],
      sourceRefs: [...actor.source_refs],
      attentionCount: myAttention.length,
      attentionTopSeverity: topSeverity(myAttention),
      proofPassCount: myProofs.filter((p) => p.statusBucket === 'pass').length,
      proofFailCount: myProofs.filter((p) => p.statusBucket === 'fail' || p.statusBucket === 'blocked').length,
      proofRunningCount: myProofs.filter((p) => p.statusBucket === 'running').length,
      fileEditCount: myFiles.filter((f) => f.operation === 'write' || f.operation === 'patch').length,
      fileReadCount: myFiles.filter((f) => f.operation === 'read').length,
      fileCollisionCount: myFiles.filter((f) => f.isCollision).length,
      qualityNotes: qualityNotesForActor(actor),
      raw: actor,
    };
    const rank = deriveRank(base);
    return { ...base, rankBucket: rank.bucket, rankReason: rank.reason };
  });

  // Sort actors: actually-live work first, then attention within the same activity band.
  // Historical stale/lost blockers remain visible through attention chips, but they must
  // not bury the active floor at the bottom of the roster.
  const heartbeatRank = (h: AgentAnimationActor['heartbeat']) =>
    h === 'live' ? 0 : h === 'unknown' ? 1 : h === 'stale' ? 2 : h === 'lost' ? 3 : 4;
  const activeStatuses = new Set(['editing', 'validating', 'rendering', 'committing', 'tool_running', 'model_turn', 'working', 'waiting_operator']);
  const activityRank = (actor: ActorVM): number => {
    const activeStatus = activeStatuses.has(actor.status);
    if (actor.heartbeat === 'live' && (actor.raw.currently_live === true || actor.raw.mid_turn === true || activeStatus)) return 0;
    if (actor.heartbeat === 'live') return 1;
    if (actor.raw.currently_live === true && activeStatus) return 2;
    return 3 + heartbeatRank(actor.heartbeat);
  };
  actors.sort((a, b) => {
    const activityDiff = activityRank(a) - activityRank(b);
    if (activityDiff !== 0) return activityDiff;
    const sevDiff = severityRank(b.attentionTopSeverity ?? undefined) - severityRank(a.attentionTopSeverity ?? undefined);
    if (sevDiff !== 0) return sevDiff;
    const hDiff = heartbeatRank(a.heartbeat) - heartbeatRank(b.heartbeat);
    if (hDiff !== 0) return hDiff;
    const lagDiff = (a.lagMs ?? Number.MAX_SAFE_INTEGER) - (b.lagMs ?? Number.MAX_SAFE_INTEGER);
    if (lagDiff !== 0) return lagDiff;
    const provDiff = a.providerLabel.localeCompare(b.providerLabel);
    if (provDiff !== 0) return provDiff;
    return a.sessionId.localeCompare(b.sessionId);
  });

  const trackBySession = new Map<string, AgentAnimationTrack>();
  for (const track of scene.tracks) trackBySession.set(track.session_id, track);

  const lanes: LaneVM[] = actors.map((actor) => {
    const track = trackBySession.get(actor.sessionId);
    const rawSegments: AgentAnimationSegment[] = track?.segments ?? [];
    const segments: LaneSegmentVM[] = rawSegments.map((segment) => ({
      ...segment,
      visibleByChannel: visibleChannelIds.has(String(segment.channel)),
    }));
    const visibleSegments = segments.filter((segment) => segment.visibleByChannel);
    const segmentsByChannel: Record<string, LaneSegmentVM[]> = {};
    for (const seg of segments) {
      const key = String(seg.channel);
      if (!segmentsByChannel[key]) segmentsByChannel[key] = [];
      segmentsByChannel[key].push(seg);
    }
    return {
      trackId: track?.id ?? `track:${actor.sessionId}`,
      actorId: actor.id,
      sessionId: actor.sessionId,
      provider: actor.provider,
      providerLabel: actor.providerLabel,
      laneIndex: track?.lane_index ?? 0,
      segments,
      visibleSegments,
      segmentsByChannel,
      activeChannelCount: Object.keys(segmentsByChannel).length,
    };
  });

  const events = [...scene.events].sort((a, b) => a.seq - b.seq);
  const countersByName: Record<string, AgentAnimationCounter> = {};
  for (const counter of scene.counters) countersByName[counter.name] = counter;

  const selectedActorId = input.selectedActorId ?? actors[0]?.id ?? null;
  const selectedActor = selectedActorId ? actors.find((actor) => actor.id === selectedActorId) ?? null : null;
  const selectedActorLane = selectedActor ? lanes.find((lane) => lane.actorId === selectedActor.id) ?? null : null;
  const selectedActorAttention = selectedActor ? attentionByActor.get(selectedActor.id) ?? [] : [];
  const selectedActorFileImpacts = selectedActor ? fileImpactsByActor.get(selectedActor.id) ?? [] : [];
  const selectedActorProofReceipts = selectedActor ? proofReceiptsByActor.get(selectedActor.id) ?? [] : [];
  const selectedActorEvents = selectedActor
    ? events.filter((event) => event.actor_id === selectedActor.id)
    : [];

  const snapshotRequired = Boolean(scene.data_quality.snapshot_required);
  let emptyReason: LiveInstrumentVM['emptyReason'] = null;
  if (snapshotRequired) emptyReason = 'snapshot_required';
  else if (actors.length === 0) emptyReason = 'no_active_actors';
  else if (events.length === 0) emptyReason = 'no_events';

  const staleStream = actors.some((actor) => actor.heartbeat === 'stale' || actor.heartbeat === 'lost');
  const degradedStream = Boolean(scene.backpressure.degraded);
  const sortedAttention = [...scene.attention].sort((a, b) => a.rank - b.rank);
  const streamHealth = buildStreamHealth(scene, actors, sortedAttention);
  const fileImpactGroups = buildFileImpactGroups(fileImpacts);
  const proofAuthority = buildProofAuthoritySummary(proofReceipts);
  const providerHealth = buildProviderHealth(actors, scene.provider_legend);

  return {
    generatedAt: scene.generated_at,
    authorityBoundary: scene.authority_boundary,
    window: scene.window,
    summary: scene.summary,
    providerLegend: scene.provider_legend,
    channels,
    visibleChannelIds,
    cursor: scene.cursor,
    backpressure: scene.backpressure,
    dataQuality: scene.data_quality,
    snapshotRequired,
    snapshotReason: snapshotRequired ? 'data_quality.snapshot_required' : null,
    staleStream,
    degradedStream,
    actors,
    lanes,
    attention: sortedAttention,
    attentionByActor,
    fileImpacts,
    fileImpactsByActor,
    proofReceipts,
    proofReceiptsByActor,
    counters: scene.counters,
    countersByName,
    flows: scene.flows,
    selectedActor,
    selectedActorLane,
    selectedActorAttention,
    selectedActorFileImpacts,
    selectedActorProofReceipts,
    selectedActorEvents,
    events,
    emptyReason,
    streamHealth,
    fileImpactGroups,
    proofAuthority,
    providerHealth,
  };
}

/* --------------------------------------------- presentation-only utilities */

export interface CoalescedAttention {
  key: string;
  label: string;
  severity: string;
  count: number;
  representativeId: string;
  members: AgentAnimationAttentionItem[];
}

/**
 * Collapse identical attention chips (same severity + label) into one entry
 * with a count, so a fleet of lost-heartbeat sessions reads as "Heartbeat lost
 * ×7" instead of seven identical chips. Display-only: every underlying item is
 * preserved in `members` — the count never drops a real item. Group order
 * follows first appearance, so the rank-sorted input keeps loudest-first.
 */
export function coalesceAttention(items: AgentAnimationAttentionItem[]): CoalescedAttention[] {
  const order: string[] = [];
  const groups = new Map<string, CoalescedAttention>();
  for (const item of items) {
    const label = item.label || item.kind || 'attention';
    const severity = item.severity || 'info';
    const key = `${severity}::${label}`;
    let group = groups.get(key);
    if (!group) {
      group = { key, label, severity, count: 0, representativeId: item.id, members: [] };
      groups.set(key, group);
      order.push(key);
    }
    group.count += 1;
    group.members.push(item);
  }
  return order.map((key) => groups.get(key) as CoalescedAttention);
}

export function formatLagMs(lagMs: number | null | undefined): string {
  if (lagMs == null || !Number.isFinite(lagMs) || lagMs < 0) return '—';
  if (lagMs < 1000) return `${Math.round(lagMs)}ms`;
  const s = lagMs / 1000;
  if (s < 60) return `${s.toFixed(s < 10 ? 1 : 0)}s`;
  const m = s / 60;
  if (m < 60) return `${Math.floor(m)}m ${Math.round(s - Math.floor(m) * 60)}s`;
  const h = m / 60;
  return `${Math.floor(h)}h ${Math.round(m - Math.floor(h) * 60)}m`;
}

export function channelOrder(): string[] {
  return [
    'attention',
    'session_lifecycle',
    'model',
    'tool_io',
    'file_io',
    'proof',
    'artifact',
    'quality',
    'infrastructure',
  ];
}

export function sortChannels(channels: ChannelVM[]): ChannelVM[] {
  const order = channelOrder();
  const rank = (id: string) => {
    const i = order.indexOf(id);
    return i < 0 ? order.length : i;
  };
  return [...channels].sort((a, b) => rank(String(a.id)) - rank(String(b.id)) || String(a.id).localeCompare(String(b.id)));
}

export type AnimationQuality = AgentAnimationQualityEnvelope | undefined;

export function qualityIsAuthoritative(quality: AnimationQuality): boolean {
  if (!quality) return false;
  return quality.authority === 'raw' || quality.authority === 'canonical_event';
}

export type AgentAnimationChannelId = AgentAnimationChannel;
