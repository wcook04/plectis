// [PURPOSE] Compact progress-packet vocabulary + pure adapters that translate
// a StationLauncherSnapshot + OrchestrationEvent[] into a dense, render-
// agnostic row model. Consumed by LaneProgressRow and the /station/timeline
// surface today; designed to also feed ObserveRunStatus, ControlRoom, and
// MetaMissionsLens without inventing state.
//
// Doctrine:
//   pri_067 — one unified graph across runtime types: every lane projects
//     into the same status vocabulary so the cockpit renders one shape.
//   pri_083 — state machine over substrate: every status is derived from
//     backend projections; nothing is invented in the browser.
//   pri_108 — continuous live updates: packets carry updated_at + freshness
//     so shells can mark stale without re-polling.
//   pri_110 — staleness is alarm: lane packets collapse freshness.tone into
//     the status vocabulary when runtime activity is otherwise absent.
//
// Annex reference patterns (translated, not imported):
//   multica p002 — compact-progress packet: status + totals + lastSeen.
//   temporal-ui n001 — shared per-event-type status vocabulary.
//   dagster — per-runtime-lane structured-row dispatch.

import type {
  MetaMissionSummaryRow,
  MetaMissionsIndexResponse,
  ObserveSessionStatusResponse,
  OrchestrationEvent,
  StationLauncherSnapshot,
  WorldModelFreshness,
} from '../../api';
import type { AuthorityKind } from './AuthorityChip';

export type CompactProgressStatus =
  | 'running'
  | 'blocked'
  | 'pending'
  | 'success'
  | 'failure'
  | 'aborted'
  | 'skipped'
  | 'stale'
  | 'idle';

export interface CompactProgressAuthority {
  kind: AuthorityKind;
  target: string;
  label?: string;
}

export interface CompactProgressProgress {
  completed: number;
  total: number;
}

export interface CompactProgressMetric {
  label: string;
  value: string | number;
}

export interface CompactProgressPacket {
  /** Unique across lanes: `${lane_id}:${item_id}`. */
  id: string;
  /** Runtime-lane id (orchestration, observe_runtime, overnight_chain, ...). */
  lane_id: string;
  /** Operator-visible lane label. */
  lane_label: string;
  /** Item-level label (driver id, session slug, mission id, family, ...). */
  label: string;
  /** Secondary eyebrow below the label. */
  kicker?: string | null;
  status: CompactProgressStatus;
  progress?: CompactProgressProgress | null;
  started_at?: string | null;
  updated_at?: string | null;
  /** Short explanatory line (gate_reason, state, ...). */
  detail?: string | null;
  /** Terminal failure reason. */
  error?: string | null;
  authority?: CompactProgressAuthority | null;
  freshness?: WorldModelFreshness | null;
  metrics?: CompactProgressMetric[];
}

function isExpired(freshness: WorldModelFreshness | null | undefined): boolean {
  return freshness?.tone === 'expired';
}

/** Orchestration lane. Always emitted — it is the anchor. */
export function buildOrchestrationPacket(
  launcher: StationLauncherSnapshot,
): CompactProgressPacket {
  const orch = launcher.orchestration;
  const activeDriver = orch.active_driver ?? null;
  const hasLiveDriver =
    !!activeDriver && activeDriver !== 'no_active_runtime_phase';

  let status: CompactProgressStatus;
  if (orch.gate_reason) status = 'blocked';
  else if (hasLiveDriver) status = 'running';
  else if (isExpired(orch.freshness)) status = 'stale';
  else status = 'idle';

  return {
    id: 'orchestration:driver',
    lane_id: 'orchestration',
    lane_label: 'Orchestration',
    label: activeDriver ?? 'no active driver',
    kicker: orch.current_owner ?? null,
    status,
    updated_at: orch.updated_at ?? null,
    detail: orch.gate_reason ?? orch.next_command ?? null,
    authority: hasLiveDriver
      ? { kind: 'orchestration', target: activeDriver!, label: 'driver' }
      : null,
    freshness: orch.freshness ?? null,
  };
}

const OBSERVE_RUNNING_STATES = new Set([
  'generating',
  'dispatching',
  'synthesizing',
]);

/**
 * Map an observe-session runtime state into the shared 9-state vocabulary.
 * Used by both the launcher-driven `buildObservePacket` (thin view from
 * StationLauncherSnapshot) and the full `buildObserveRuntimePackets`
 * (consumed by ObserveRunStatus). Kept pure so it can be unit-tested.
 */
export function classifyObserveRuntimeState(
  state: string | null | undefined,
): CompactProgressStatus {
  if (!state) return 'idle';
  if (OBSERVE_RUNNING_STATES.has(state)) return 'running';
  if (state === 'awaiting_review') return 'blocked';
  if (state === 'completed') return 'success';
  if (state === 'error') return 'failure';
  if (state === 'aborted') return 'aborted';
  if (state === 'idle') return 'idle';
  return 'idle';
}

/** Observe-session lane. Emits only when observe_id is bound. */
export function buildObservePacket(
  launcher: StationLauncherSnapshot,
): CompactProgressPacket | null {
  const or = launcher.observe_runtime;
  if (!or.observe_id) return null;
  const state = (or.state ?? 'idle').toString();

  let status = classifyObserveRuntimeState(state);
  // Launcher snapshot lacks an explicit 'error' field — fall back to
  // 'pending' when the session is idle-but-incomplete so the timeline
  // distinguishes abandoned-mid-run from genuinely-idle.
  if (
    status === 'idle' &&
    or.total_groups > 0 &&
    or.completed_groups < or.total_groups
  ) {
    status = 'pending';
  }

  const metrics: CompactProgressMetric[] = [];
  if (or.retryable_group_labels.length) {
    metrics.push({ label: 'retryable', value: or.retryable_group_labels.length });
  }
  if (or.can_continue) {
    metrics.push({ label: 'resume', value: 'ready' });
  }

  return {
    id: `observe_runtime:${or.observe_id}`,
    lane_id: 'observe_runtime',
    lane_label: 'Observe runtime',
    label: or.session_slug ?? or.observe_id,
    kicker: or.provider ?? null,
    status,
    progress:
      or.total_groups > 0
        ? { completed: or.completed_groups, total: or.total_groups }
        : null,
    detail: state,
    metrics,
  };
}

function classifyOvernightTerminal(
  terminal: string | null | undefined,
  lastError: string | null | undefined,
): CompactProgressStatus | null {
  if (terminal === 'succeeded') return 'success';
  if (
    terminal === 'failed' ||
    terminal === 'exited_unknown' ||
    !!lastError
  ) {
    return 'failure';
  }
  return null;
}

/** Overnight chain lane — active only when chain_id is bound. */
export function buildOvernightChainPacket(
  launcher: StationLauncherSnapshot,
): CompactProgressPacket | null {
  const c = launcher.overnight_chain;
  if (!c.chain_id) return null;
  const { completed_steps, total_steps, current_step_id } = c.progress;
  let status: CompactProgressStatus;
  if (c.is_running) status = 'running';
  else {
    status =
      classifyOvernightTerminal(c.terminal_status, c.last_error) ??
      (total_steps > 0 && completed_steps < total_steps ? 'pending' : 'idle');
  }

  return {
    id: `overnight_chain:${c.chain_run_id ?? c.chain_id}`,
    lane_id: 'overnight_chain',
    lane_label: 'Overnight chain',
    label: c.chain_id,
    kicker: current_step_id ?? c.terminal_status ?? null,
    status,
    progress:
      total_steps > 0
        ? { completed: completed_steps, total: total_steps }
        : null,
    updated_at: c.last_updated ?? null,
    error: c.last_error ?? null,
    detail: c.terminal_status ?? null,
  };
}

/** Overnight queue lane — active only when queue_id is bound. */
export function buildOvernightQueuePacket(
  launcher: StationLauncherSnapshot,
): CompactProgressPacket | null {
  const q = launcher.overnight_queue;
  if (!q || !q.queue_id) return null;
  const { completed_items, total_items, current_item_id } = q.progress;
  let status: CompactProgressStatus;
  if (q.is_running) status = 'running';
  else {
    status =
      classifyOvernightTerminal(q.terminal_status, q.last_error) ??
      (total_items > 0 && completed_items < total_items ? 'pending' : 'idle');
  }

  return {
    id: `overnight_queue:${q.queue_run_id ?? q.queue_id}`,
    lane_id: 'overnight_queue',
    lane_label: 'Overnight queue',
    label: q.queue_id,
    kicker: current_item_id ?? q.terminal_status ?? null,
    status,
    progress:
      total_items > 0
        ? { completed: completed_items, total: total_items }
        : null,
    updated_at: q.last_updated ?? null,
    error: q.last_error ?? null,
    detail: q.terminal_status ?? null,
  };
}

/** Meta-mission lane — one rollup packet (not per-mission). */
export function buildMetaMissionsPacket(
  launcher: StationLauncherSnapshot,
): CompactProgressPacket | null {
  const mm = launcher.meta_missions;
  if (!mm) return null;
  const active = mm.totals.active_missions ?? 0;
  const running = mm.totals.running_total ?? 0;
  const failed = mm.totals.failed_total ?? 0;
  const urgent = mm.urgent.length;
  const total = mm.totals.total_runs ?? 0;

  if (active === 0 && running === 0 && urgent === 0 && total === 0) {
    return null;
  }

  let status: CompactProgressStatus;
  if (running > 0) status = 'running';
  else if (urgent > 0) status = 'blocked';
  else if (failed > 0) status = 'failure';
  else status = 'idle';

  const topUrgent = mm.urgent[0];
  const topRunning = mm.missions.find((m) => m.metrics.running_total > 0);
  const labelSource = topUrgent ?? topRunning ?? null;

  const metrics: CompactProgressMetric[] = [
    { label: 'active', value: active },
    { label: 'running', value: running },
  ];
  if (urgent > 0) metrics.push({ label: 'urgent', value: urgent });
  if (failed > 0) metrics.push({ label: 'failed', value: failed });
  metrics.push({ label: 'runs', value: total });

  return {
    id: 'meta_missions:rollup',
    lane_id: 'meta_missions',
    lane_label: 'Meta missions',
    label: labelSource?.mission_id ?? `${active} active`,
    kicker: labelSource?.status ?? null,
    status,
    progress:
      active > 0
        ? { completed: Math.max(active - running, 0), total: active }
        : null,
    updated_at: mm.generated_at ?? null,
    detail: topUrgent?.error ?? null,
    metrics,
  };
}

/** Raw-seed pipeline lane — active while the family substrate exists. */
export function buildRawSeedPipelinePacket(
  launcher: StationLauncherSnapshot,
): CompactProgressPacket | null {
  const rsp = launcher.raw_seed_pipeline;
  if (!rsp.family_dir && !rsp.family_number) return null;

  const pendingWork =
    rsp.paragraphs_without_atoms +
    rsp.pending_routing_shards +
    rsp.fresh_pending_bins +
    rsp.surface_queue_entries;

  let status: CompactProgressStatus;
  if (rsp.effective_active_workers > 0 && rsp.queue_depth > 0) {
    status = 'running';
  } else if (pendingWork > 0) {
    status = 'pending';
  } else {
    status = 'idle';
  }

  return {
    id: `raw_seed_pipeline:${rsp.family_number ?? rsp.family_dir ?? 'active'}`,
    lane_id: 'raw_seed_pipeline',
    lane_label: 'Raw-seed pipeline',
    label: rsp.family_number ?? rsp.family_dir ?? 'active family',
    kicker: rsp.provider ?? null,
    status,
    progress:
      rsp.total_paragraphs > 0
        ? {
            completed: Math.max(
              rsp.total_paragraphs - rsp.paragraphs_without_atoms,
              0,
            ),
            total: rsp.total_paragraphs,
          }
        : null,
    updated_at: rsp.last_updated ?? null,
    detail: pendingWork > 0 ? `${pendingWork} pending items` : 'drained',
    metrics: [
      { label: 'paragraphs', value: rsp.total_paragraphs },
      { label: 'shards pending', value: rsp.pending_routing_shards },
      { label: 'bins pending', value: rsp.fresh_pending_bins },
      { label: 'queue depth', value: rsp.queue_depth },
      { label: 'workers', value: rsp.effective_active_workers },
    ],
  };
}

// ---------------------------------------------------------------------------
// Observe-session packets — full ObserveSessionStatusResponse projection.
// Consumed by ObserveRunStatus (and any future surface that polls
// /api/meta/observe/runtime/status). Distinct from buildObservePacket above,
// which is the thin launcher-rollup view. Keep both: launcher gives the
// cockpit-wide glance; this gives the session-local drill-down.
// ---------------------------------------------------------------------------

/** Map an observe-group status into the shared vocabulary. A pending group
 *  whose dependencies are not yet met is reported as 'blocked' so the
 *  operator can distinguish "queued but waiting on upstream" from "queued and
 *  ready to dispatch". */
export function classifyObserveGroupStatus(
  status: string | null | undefined,
  dependenciesMet: boolean | null | undefined,
): CompactProgressStatus {
  if (!status) return 'idle';
  if (status === 'running') return 'running';
  if (status === 'success') return 'success';
  if (status === 'failure') return 'failure';
  if (status === 'aborted') return 'aborted';
  if (status === 'skipped') return 'skipped';
  if (status === 'pending') {
    return dependenciesMet === false ? 'blocked' : 'pending';
  }
  return 'idle';
}

const GROUP_STATUS_PRIORITY: Record<CompactProgressStatus, number> = {
  running: 0,
  failure: 1,
  aborted: 1,
  blocked: 2,
  pending: 4,
  stale: 5,
  skipped: 6,
  success: 7,
  idle: 8,
};

// ---------------------------------------------------------------------------
// Meta-mission packets — full MetaMissionsIndexResponse projection.
// Consumed by MetaMissionsLens (/meta-missions career browser). Distinct from
// buildMetaMissionsPacket below, which is the thin launcher-rollup view
// produced from StationMetaMissionsSlice for /station/timeline.
// ---------------------------------------------------------------------------

/**
 * Classify one MetaMissionSummaryRow into the shared 9-state vocabulary.
 *
 * Prioritisation (highest wins):
 *   - `metrics.running_total > 0`            → `running`
 *   - last_run.status ∈ {failed,aborted,…}   → terminal mapping
 *   - registry `status === 'planned'`        → `pending`
 *   - fall through                           → `idle`
 *
 * This is deliberate: the registry status field (`active` / `planned`) tells
 * the operator whether the surface is published, but the operator-visible
 * state the operator cares about is *what this mission's runs are doing*.
 * So running_total and last_run.status dominate; registry-status is the
 * tiebreaker for "never-run planned careers".
 */
export function classifyMetaMissionStatus(
  row: MetaMissionSummaryRow,
): CompactProgressStatus {
  const metrics = row.metrics;
  if ((metrics?.running_total ?? 0) > 0) return 'running';

  const lastStatus = metrics?.last_run?.status ?? null;
  if (lastStatus === 'failed') return 'failure';
  if (lastStatus === 'aborted') return 'aborted';
  if (lastStatus === 'graceful_stop' || lastStatus === 'interrupted') {
    return 'blocked';
  }
  if (lastStatus === 'skipped') return 'skipped';
  if (lastStatus === 'succeeded') return 'success';

  if (row.status === 'planned') return 'pending';
  return 'idle';
}

/**
 * Build one packet for a single mission summary row. Metrics chosen to
 * give the operator runs-count / running / failed / success-rate without
 * reopening the detail pane — mirrors the old SummaryCard chip grid.
 */
export function buildMetaMissionPacket(
  row: MetaMissionSummaryRow,
): CompactProgressPacket {
  const metrics = row.metrics;
  const lastRun = metrics?.last_run ?? null;
  const total = metrics?.total_runs ?? 0;
  const running = metrics?.running_total ?? 0;
  const failed = metrics?.failed_total ?? 0;
  const succeeded = metrics?.succeeded_total ?? 0;
  const successRate = metrics?.success_rate ?? null;

  const status = classifyMetaMissionStatus(row);

  const packetMetrics: CompactProgressMetric[] = [];
  if (total > 0) packetMetrics.push({ label: 'runs', value: total });
  if (running > 0) packetMetrics.push({ label: 'running', value: running });
  if (failed > 0) packetMetrics.push({ label: 'failed', value: failed });
  if (typeof successRate === 'number' && Number.isFinite(successRate)) {
    packetMetrics.push({
      label: 'success',
      value: `${Math.round(successRate * 100)}%`,
    });
  }
  if (row.runtime_surface) {
    packetMetrics.push({ label: 'surface', value: row.runtime_surface });
  }
  if (row.supports_resume) {
    packetMetrics.push({ label: 'resume', value: 'yes' });
  }
  if (lastRun?.status) {
    packetMetrics.push({ label: 'last', value: lastRun.status });
  }

  return {
    id: `meta_mission:${row.mission_id}`,
    lane_id: 'meta_missions',
    lane_label: 'Mission',
    label: row.title || row.mission_id,
    kicker: row.mission_id,
    status,
    progress:
      total > 0 ? { completed: succeeded, total } : null,
    updated_at: lastRun?.finished_at ?? lastRun?.started_at ?? null,
    detail: lastRun?.status ?? null,
    error: lastRun?.error ?? null,
    metrics: packetMetrics,
  };
}

/**
 * One rollup packet summarising the entire mission registry. Emitted at the
 * top of the sidebar so the operator reads "total runs / running now /
 * failed recently / active careers" before drilling into any row.
 */
export function buildMetaMissionsRollupPacket(
  index: MetaMissionsIndexResponse | null | undefined,
): CompactProgressPacket | null {
  if (!index) return null;
  const summaries = index.summaries ?? [];
  if (summaries.length === 0) return null;

  let totalRuns = 0;
  let running = 0;
  let failed = 0;
  let succeeded = 0;
  let planned = 0;
  let active = 0;
  let blocked = 0;
  let recentlyFailed = 0;
  for (const row of summaries) {
    const metrics = row.metrics;
    totalRuns += metrics?.total_runs ?? 0;
    running += metrics?.running_total ?? 0;
    failed += metrics?.failed_total ?? 0;
    succeeded += metrics?.succeeded_total ?? 0;
    if (row.status === 'planned') planned += 1;
    else if (row.status === 'active') active += 1;
    const last = metrics?.last_run?.status ?? null;
    if (last === 'graceful_stop' || last === 'interrupted') blocked += 1;
    if (last === 'failed' || last === 'aborted') recentlyFailed += 1;
  }

  let status: CompactProgressStatus;
  if (running > 0) status = 'running';
  else if (recentlyFailed > 0) status = 'failure';
  else if (blocked > 0) status = 'blocked';
  else if (active > 0) status = 'idle';
  else if (planned > 0) status = 'pending';
  else status = 'idle';

  const rollupMetrics: CompactProgressMetric[] = [
    { label: 'careers', value: summaries.length },
    { label: 'active', value: active },
  ];
  if (planned > 0) rollupMetrics.push({ label: 'planned', value: planned });
  if (running > 0) rollupMetrics.push({ label: 'running', value: running });
  if (recentlyFailed > 0) {
    rollupMetrics.push({ label: 'recent failures', value: recentlyFailed });
  }
  if (blocked > 0) rollupMetrics.push({ label: 'blocked', value: blocked });
  if (failed > 0) rollupMetrics.push({ label: 'failed total', value: failed });
  rollupMetrics.push({ label: 'runs total', value: totalRuns });

  return {
    id: 'meta_missions:rollup_full',
    lane_id: 'meta_missions',
    lane_label: 'Meta missions',
    label: `${summaries.length} careers`,
    kicker: index.registry_version ?? null,
    status,
    progress:
      totalRuns > 0 ? { completed: succeeded, total: totalRuns } : null,
    updated_at: index.generated_at ?? null,
    metrics: rollupMetrics,
  };
}

interface BuildMetaMissionPacketsOptions {
  /** Hard cap on mission packets (excluding the rollup packet). Missions above
   *  the cap collapse into a single "+N more" summary packet with a
   *  status-count breakdown so the tail still reports totals. */
  missionLimit?: number;
  /** Whether to emit the rollup packet at the head of the sequence. Default
   *  true — the rollup gives operator a single-glance count summary before
   *  drilling into individual rows. */
  includeRollup?: boolean;
}

/**
 * Build the ordered packet sequence for a MetaMissionsIndexResponse.
 *
 * Returns `[]` when index is null (caller renders an empty-state shell).
 * Otherwise emits:
 *   1. Optional rollup packet summarising the whole registry.
 *   2. Mission packets, prioritized by runtime status so the operator sees
 *      running and failing careers first. Within a status bucket, missions
 *      with more recent last_run timestamps come first.
 *   3. If missions.length > missionLimit, one "+N more" summary packet
 *      carrying a status-count breakdown of the hidden tail.
 */
export function buildMetaMissionPackets(
  index: MetaMissionsIndexResponse | null | undefined,
  options: BuildMetaMissionPacketsOptions = {},
): CompactProgressPacket[] {
  if (!index) return [];
  const { missionLimit = 24, includeRollup = true } = options;
  const summaries = index.summaries ?? [];
  if (summaries.length === 0) return [];

  const ranked = [...summaries]
    .map((row, idx) => ({
      row,
      idx,
      packetStatus: classifyMetaMissionStatus(row),
    }))
    .sort((a, b) => {
      const pa = GROUP_STATUS_PRIORITY[a.packetStatus] ?? 9;
      const pb = GROUP_STATUS_PRIORITY[b.packetStatus] ?? 9;
      if (pa !== pb) return pa - pb;
      const ta =
        a.row.metrics?.last_run?.finished_at ??
        a.row.metrics?.last_run?.started_at ??
        '';
      const tb =
        b.row.metrics?.last_run?.finished_at ??
        b.row.metrics?.last_run?.started_at ??
        '';
      if (ta !== tb) return tb.localeCompare(ta); // most recent first
      return a.idx - b.idx;
    });

  const visible = ranked.slice(0, Math.max(0, missionLimit));
  const hidden = ranked.slice(Math.max(0, missionLimit));

  const packets: CompactProgressPacket[] = [];
  if (includeRollup) {
    const rollup = buildMetaMissionsRollupPacket(index);
    if (rollup) packets.push(rollup);
  }
  for (const { row } of visible) {
    packets.push(buildMetaMissionPacket(row));
  }
  if (hidden.length > 0) {
    const statusCounts = hidden.reduce<Record<CompactProgressStatus, number>>(
      (acc, { packetStatus }) => {
        acc[packetStatus] = (acc[packetStatus] ?? 0) + 1;
        return acc;
      },
      {} as Record<CompactProgressStatus, number>,
    );
    const summaryMetrics: CompactProgressMetric[] = Object.entries(statusCounts)
      .sort(([a], [b]) => {
        const pa = GROUP_STATUS_PRIORITY[a as CompactProgressStatus] ?? 9;
        const pb = GROUP_STATUS_PRIORITY[b as CompactProgressStatus] ?? 9;
        return pa - pb;
      })
      .map(([s, count]) => ({ label: s, value: count }));
    packets.push({
      id: 'meta_missions:tail_summary',
      lane_id: 'meta_missions',
      lane_label: 'Missions',
      label: `+${hidden.length} more`,
      kicker: `hidden · top ${missionLimit} shown above`,
      status: 'idle',
      metrics: summaryMetrics,
    });
  }

  return packets;
}

interface BuildObserveRuntimePacketsOptions {
  /** Hard cap on emitted group packets. Groups above the cap collapse into a
   *  single "+N more" summary packet with a status-count breakdown. */
  groupLimit?: number;
}

/**
 * Build the ordered packet sequence for one observe runtime session.
 *
 * Returns `[]` when status is null (caller renders an empty-state shell).
 * Otherwise emits:
 *   1. One session-level packet (wave/progress/error/can_continue metrics).
 *   2. Up to `groupLimit` group-level packets, prioritized by status so the
 *      operator sees active and failing groups first. Retryable groups are
 *      pulled forward within their status bucket.
 *   3. If groups.length > groupLimit, one "+N more" summary packet carrying a
 *      by-status breakdown so the hidden tail still reports totals.
 */
export function buildObserveRuntimePackets(
  status: ObserveSessionStatusResponse | null | undefined,
  options: BuildObserveRuntimePacketsOptions = {},
): CompactProgressPacket[] {
  if (!status) return [];
  const { groupLimit = 8 } = options;
  const sessionKey =
    status.observe_id ?? status.session_slug ?? 'session';

  // ─── Session-level packet ───────────────────────────────────────────
  let sessionStatus = classifyObserveRuntimeState(status.state);
  // Promote to failure if backend reported a top-level error but the
  // state field didn't already flip (defensive — backend usually sets both).
  if (status.error && sessionStatus !== 'aborted' && sessionStatus !== 'failure') {
    sessionStatus = 'failure';
  }

  const waveIdx = status.wave_index ?? 0;
  const waveTotal = status.wave_total ?? 0;
  const errorCount = status.error_count ?? 0;
  const retryable = status.retryable_group_labels?.length ?? 0;
  const pending = status.pending_group_labels?.length ?? 0;

  const sessionMetrics: CompactProgressMetric[] = [];
  if (status.kind) sessionMetrics.push({ label: 'kind', value: status.kind });
  if (status.launch_profile) {
    sessionMetrics.push({ label: 'profile', value: status.launch_profile });
  }
  if (waveTotal > 0) {
    sessionMetrics.push({ label: 'wave', value: `${waveIdx + 1}/${waveTotal}` });
  }
  if (status.provider_transport) {
    sessionMetrics.push({ label: 'transport', value: status.provider_transport });
  }
  if (status.effective_workers != null) {
    const req = status.requested_workers ?? '-';
    sessionMetrics.push({
      label: 'workers',
      value: `${status.effective_workers}/${req}`,
    });
  }
  if (errorCount > 0) sessionMetrics.push({ label: 'errors', value: errorCount });
  if (retryable > 0) sessionMetrics.push({ label: 'retryable', value: retryable });
  if (pending > 0) sessionMetrics.push({ label: 'pending', value: pending });
  if (status.can_continue) {
    sessionMetrics.push({
      label: 'resume',
      value: status.continue_mode ?? 'ready',
    });
  }

  const sessionPacket: CompactProgressPacket = {
    id: `observe_runtime_session:${sessionKey}`,
    lane_id: 'observe_runtime',
    lane_label: 'Observe runtime',
    label: status.session_slug ?? status.observe_id ?? 'observe session',
    kicker: status.provider ?? null,
    status: sessionStatus,
    progress:
      status.total_groups > 0
        ? { completed: status.completed_groups, total: status.total_groups }
        : null,
    started_at: status.started_at ?? null,
    updated_at: status.updated_at ?? null,
    detail: status.state,
    error: status.error ?? null,
    metrics: sessionMetrics,
  };

  // ─── Group-level packets ───────────────────────────────────────────
  const groups = status.groups ?? [];
  if (groups.length === 0) return [sessionPacket];

  const ranked = [...groups]
    .map((group, index) => ({
      group,
      index,
      packetStatus: classifyObserveGroupStatus(
        group.status,
        group.dependencies_met,
      ),
    }))
    .sort((a, b) => {
      const pa = GROUP_STATUS_PRIORITY[a.packetStatus] ?? 9;
      const pb = GROUP_STATUS_PRIORITY[b.packetStatus] ?? 9;
      if (pa !== pb) return pa - pb;
      // Within the same bucket: retryable first, then wave order.
      if (a.group.retryable !== b.group.retryable) {
        return a.group.retryable ? -1 : 1;
      }
      return a.index - b.index;
    });

  const visible = ranked.slice(0, Math.max(0, groupLimit));
  const hidden = ranked.slice(Math.max(0, groupLimit));

  const groupPackets: CompactProgressPacket[] = visible.map(
    ({ group, packetStatus }) => {
      const metrics: CompactProgressMetric[] = [
        { label: 'deps', value: group.dependencies_met ? 'met' : 'blocked' },
        { label: 'retry', value: group.retryable ? 'yes' : 'no' },
      ];
      if (group.depends_on && group.depends_on.length > 0) {
        metrics.push({ label: 'depends_on', value: group.depends_on.length });
      }
      return {
        id: `observe_runtime_group:${sessionKey}:${group.label}`,
        lane_id: 'observe_runtime',
        lane_label: 'Observe group',
        label: group.label,
        kicker:
          waveTotal > 0
            ? `${group.role} · wave ${group.wave_index + 1}`
            : group.role,
        status: packetStatus,
        detail: group.retry_reason ?? group.response_path ?? null,
        error: group.error ?? null,
        metrics,
      };
    },
  );

  const packets: CompactProgressPacket[] = [sessionPacket, ...groupPackets];

  if (hidden.length > 0) {
    const statusCounts = hidden.reduce<Record<CompactProgressStatus, number>>(
      (acc, { packetStatus }) => {
        acc[packetStatus] = (acc[packetStatus] ?? 0) + 1;
        return acc;
      },
      {} as Record<CompactProgressStatus, number>,
    );
    const summaryMetrics: CompactProgressMetric[] = Object.entries(statusCounts)
      .sort(([a], [b]) => {
        const pa = GROUP_STATUS_PRIORITY[a as CompactProgressStatus] ?? 9;
        const pb = GROUP_STATUS_PRIORITY[b as CompactProgressStatus] ?? 9;
        return pa - pb;
      })
      .map(([s, count]) => ({ label: s, value: count }));
    packets.push({
      id: `observe_runtime_group_summary:${sessionKey}`,
      lane_id: 'observe_runtime',
      lane_label: 'Observe groups',
      label: `+${hidden.length} more`,
      kicker: `hidden · top ${groupLimit} shown above`,
      status: 'idle',
      metrics: summaryMetrics,
    });
  }

  return packets;
}

/**
 * Canonical timeline packet sequence for a station launcher snapshot.
 * Null lanes (no active chain/queue/observe) are filtered out.
 */
export function buildStationTimelinePackets(
  launcher: StationLauncherSnapshot | null,
): CompactProgressPacket[] {
  if (!launcher) return [];
  const candidates: Array<CompactProgressPacket | null> = [
    buildOrchestrationPacket(launcher),
    buildObservePacket(launcher),
    buildOvernightChainPacket(launcher),
    buildOvernightQueuePacket(launcher),
    buildMetaMissionsPacket(launcher),
    buildRawSeedPipelinePacket(launcher),
  ];
  return candidates.filter(
    (p): p is CompactProgressPacket => p !== null,
  );
}

// ---------------------------------------------------------------------------
// Orchestration event rail — fold OrchestrationEvent[] into the same status
// vocabulary so one renderer can draw lane rows AND event rows consistently.
// ---------------------------------------------------------------------------

export interface CompactProgressEvent {
  id: string;
  recorded_at: string;
  label: string;
  detail?: string | null;
  status: CompactProgressStatus;
  active_driver?: string | null;
}

const EVENT_KIND_STATUS: Record<string, CompactProgressStatus> = {
  gate_acknowledged: 'success',
  operation_launched: 'running',
  operation_completed: 'success',
  operation_failed: 'failure',
  reaction_fired: 'running',
};

export function classifyOrchestrationEvent(
  event: OrchestrationEvent,
): CompactProgressStatus {
  if (event.gate_reason) return 'blocked';
  const mapped = EVENT_KIND_STATUS[event.kind];
  if (mapped) return mapped;
  if (
    event.active_driver &&
    event.active_driver !== 'no_active_runtime_phase'
  ) {
    return 'running';
  }
  return 'idle';
}

export function buildOrchestrationEventRail(
  events: OrchestrationEvent[],
  limit = 12,
): CompactProgressEvent[] {
  return events.slice(0, limit).map((event) => ({
    id: event.event_id,
    recorded_at: event.recorded_at,
    label: event.summary ?? event.kind,
    detail: event.gate_reason ?? event.next_handoff?.command ?? null,
    status: classifyOrchestrationEvent(event),
    active_driver: event.active_driver ?? null,
  }));
}
