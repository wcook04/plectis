// [PURPOSE] Work lens — WorkItems/CAPs as live state.
//
// Operator directive 2026-05-13: WorkItems/CAPs are not just System KPIs —
// they are live state. Surface: current_next + highest-priority items +
// clusters (by_state, by_actor, by_family) + selected dossier.
//
// Source priority (per operator):
//   1. api.worldModel.workLedgerOverview() — typed WorkLedgerOverviewResponse
//   2. api.worldModel.taskLedgerProjection() — global WorkItem/CAP operating picture
//   3. useZenith().worldModel.orchestration.work_spine — current_next + buckets
//
// Anti-goal: control creep. This lens observes. Mutation flows live in
// CLI capture / quick-capture / scoped commits, not in cockpit chrome.

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import clsx from 'clsx';
import {
  api,
  type TaskLedgerCartographyAtlasMark,
  type TaskLedgerCartographyPayloadResponse,
  type TaskLedgerCartographyRouteResolutionAffordance,
  type TaskLedgerProjectionResponse,
  type WorkItemDossierPayloadResponse,
  type WorkItemNeighborhoodPayloadResponse,
  type WorkLedgerOverviewResponse,
} from '../../api';
import PanelSourceHeader from './PanelSourceHeader';
import WorkAtlas, { type AtlasCellId } from './WorkAtlas';
import {
  LANE_RELATIONSHIP_PREFIX,
  LANE_RELATIONSHIP_TONE,
  RESOLUTION_DISPOSITION_LABEL,
  RESOLUTION_STATUS_TONE,
  ROUTE_REASON_KIND_TONE,
  ROUTE_REASON_LABEL,
  ROUTE_REASON_SHORT_CODE,
} from './routeReasonVocab';
import NeighborhoodInspector from './NeighborhoodInspector';

interface WorkItemRow {
  id: string;
  title: string;
  state: string;
  workItemType: string | null;
  actor: string | null;
  family: string | null;
  isStale: boolean;
}

type WorkSelectionChangeSource = 'click' | 'default' | 'url_fallback';
type WorkSelectionDisplaySource = 'url' | 'default' | 'url_fallback' | 'local';

interface WorkLensProps {
  selectedWorkItemId?: string | null;
  objectToken?: string | null;
  onSelectedWorkItemChange?: (id: string, source: WorkSelectionChangeSource) => void;
  // Wave 2F — addressable resolution drillthrough. selectedRouteReason
  // is read from URL (?route_reason=<key>) by Intelligence.tsx and
  // round-tripped via onSelectedRouteReasonChange when the operator
  // clicks a reason row in the Unrouted Breakdown panel.
  selectedRouteReason?: string | null;
  onSelectedRouteReasonChange?: (
    reason: string | null,
    source: WorkSelectionChangeSource,
  ) => void;
}

interface MassSegment {
  id: string;
  label: string;
  count: number;
  kind: 'state' | 'type';
}

const WORK_LEDGER_OVERVIEW_TIMEOUT_MS = 12000;
const WORK_LEDGER_OVERVIEW_WARM_RETRY_DELAYS_MS = [750, 1500, 3000, 5000];
const WORK_ITEM_DOSSIER_TIMEOUT_MS = 4500;
const WORK_ATLAS_TERMINAL_STATES = new Set(['done', 'propagated', 'retired']);

let cachedWorkLedgerOverview: WorkLedgerOverviewResponse | null = null;

// eslint-disable-next-line react-refresh/only-export-components
export function __resetWorkLensCacheForTests(): void {
  cachedWorkLedgerOverview = null;
}

function isAbortLike(error: unknown): boolean {
  return (
    (typeof DOMException !== 'undefined'
      && error instanceof DOMException
      && error.name === 'AbortError')
    || (error instanceof Error && error.name === 'AbortError')
  );
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function isWorkLedgerOverviewWarming(overview: WorkLedgerOverviewResponse | null): boolean {
  const serving = asRecord(overview?.serving);
  const servingState = asString(serving?.state);
  const servedFrom = asString(serving?.served_from);
  return servingState === 'warming' || servedFrom === 'warming_shell';
}

function isWorkLedgerOverviewRefreshPending(overview: WorkLedgerOverviewResponse | null): boolean {
  const serving = asRecord(overview?.serving);
  if (!serving) return false;
  return isWorkLedgerOverviewWarming(overview)
    || (
      asString(serving.served_from) === 'disk_last_good'
      && serving.refresh_in_flight === true
    );
}

function workLedgerOverviewSliceDisclosure(overview: WorkLedgerOverviewResponse | null): string | null {
  const serving = asRecord(overview?.serving);
  if (!serving) return null;
  const servedFrom = asString(serving.served_from);
  const refreshInFlight = serving.refresh_in_flight === true;
  const lastGoodDisclosure =
    servedFrom === 'disk_last_good'
      ? `serving last-good Work Ledger snapshot${refreshInFlight ? ' · refresh in flight' : ''}`
      : null;
  const actorTruncated = serving.open_by_actor_truncated === true;
  const familyTruncated = serving.open_by_family_truncated === true;
  if (!actorTruncated && !familyTruncated) return lastGoodDisclosure;
  const actorReturned = asNumber(serving.open_by_actor_returned);
  const actorTotal = asNumber(serving.open_by_actor_total);
  const familyReturned = asNumber(serving.open_by_family_returned);
  const familyTotal = asNumber(serving.open_by_family_total);
  const returned = actorReturned ?? familyReturned;
  const total = actorTotal ?? familyTotal;
  if (returned === null || total === null || total <= returned) {
    return lastGoodDisclosure ? `${lastGoodDisclosure} · backend slice capped` : 'backend slice capped';
  }
  const sliceDisclosure = `backend slice · ${compactCount(returned)} of ${compactCount(total)} open rows`;
  return lastGoodDisclosure ? `${lastGoodDisclosure} · ${sliceDisclosure}` : sliceDisclosure;
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function asCountRecord(value: unknown): Record<string, number> {
  const record = asRecord(value);
  if (!record) return {};
  const out: Record<string, number> = {};
  for (const [key, raw] of Object.entries(record)) {
    const count = asNumber(raw);
    if (count !== null) out[key] = count;
  }
  return out;
}

function compactCount(value: number | null | undefined): string {
  const count = typeof value === 'number' && Number.isFinite(value) ? value : 0;
  if (count >= 1000) return `${(count / 1000).toFixed(count >= 10000 ? 0 : 1)}k`;
  return String(count);
}

function terminalState(state: string): boolean {
  const normalized = state.toLowerCase();
  return normalized === 'done'
    || normalized === 'propagated'
    || normalized === 'retired'
    || normalized === 'completed';
}

function countSegments(
  counts: Record<string, number>,
  kind: 'state' | 'type',
  limit = 10,
): MassSegment[] {
  return Object.entries(counts)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
    .map(([label, count]) => ({
      id: `${kind}:${label}`,
      label,
      count,
      kind,
    }));
}

function readWorkItemRow(raw: unknown, defaultActor: string | null, isStale: boolean): WorkItemRow | null {
  const record = asRecord(raw);
  if (!record) return null;
  const id =
    asString(record.id) ??
    asString(record.td_id) ??
    asString(record.subject_id) ??
    asString(record.work_item_id) ??
    asString(record.thread_id);
  if (!id) return null;
  return {
    id,
    title:
      asString(record.title) ??
      asString(record.statement) ??
      asString(record.summary) ??
      asString(record.label) ??
      id,
    state: asString(record.state) ?? asString(record.status) ?? 'unknown',
    workItemType: asString(record.work_item_type) ?? asString(record.kind),
    actor: asString(record.actor) ?? asString(record.owner) ?? defaultActor,
    family: asString(record.family_id) ?? asString(record.family) ?? asString(record.phase_id),
    isStale,
  };
}

function flattenOpenBy(
  records: Record<string, unknown[]> | undefined,
  isStale: boolean,
): WorkItemRow[] {
  if (!records) return [];
  const out: WorkItemRow[] = [];
  for (const [actor, list] of Object.entries(records)) {
    if (!Array.isArray(list)) continue;
    for (const entry of list) {
      const row = readWorkItemRow(entry, actor, isStale);
      if (row) out.push(row);
    }
  }
  return out;
}

function mergeWorkItemRows(primary: WorkItemRow, duplicate: WorkItemRow): WorkItemRow {
  return {
    id: primary.id,
    title: primary.title && primary.title !== primary.id ? primary.title : duplicate.title,
    state: primary.state && primary.state !== 'unknown' ? primary.state : duplicate.state,
    workItemType: primary.workItemType ?? duplicate.workItemType,
    actor: primary.actor ?? duplicate.actor,
    family: primary.family ?? duplicate.family,
    isStale: primary.isStale || duplicate.isStale,
  };
}

function dedupeWorkItemRows(rows: WorkItemRow[]): WorkItemRow[] {
  const byId = new Map<string, WorkItemRow>();
  const orderedIds: string[] = [];
  for (const row of rows) {
    const existing = byId.get(row.id);
    if (existing) {
      byId.set(row.id, mergeWorkItemRows(existing, row));
      continue;
    }
    byId.set(row.id, row);
    orderedIds.push(row.id);
  }
  return orderedIds.map((id) => byId.get(id)).filter((row): row is WorkItemRow => Boolean(row));
}

function stateTone(state: string): 'ok' | 'warn' | 'block' | 'neutral' {
  const lower = state.toLowerCase();
  if (lower.includes('execution') || lower.includes('active') || lower.includes('claimed')) return 'ok';
  if (lower.includes('blocked') || lower.includes('failed') || lower.includes('stale')) return 'block';
  if (lower.includes('captured') || lower.includes('inbox') || lower.includes('shaping')) return 'warn';
  return 'neutral';
}

function segmentTone(segment: MassSegment): 'ok' | 'warn' | 'block' | 'neutral' {
  if (segment.kind === 'state') return stateTone(segment.label);
  const lower = segment.label.toLowerCase();
  if (lower.includes('cap') || lower.includes('task') || lower.includes('meta')) return 'ok';
  if (lower.includes('bug') || lower.includes('residual')) return 'block';
  if (lower.includes('capture')) return 'warn';
  return 'neutral';
}

function segmentClass(segment: MassSegment, active: boolean): string {
  const tone = segmentTone(segment);
  const activeRing = active ? 'ring-2 ring-white/50 ring-inset' : '';
  if (tone === 'ok') return clsx('bg-emerald-300/65 hover:bg-emerald-200/80', activeRing);
  if (tone === 'warn') return clsx('bg-amber-300/70 hover:bg-amber-200/85', activeRing);
  if (tone === 'block') return clsx('bg-rose-300/70 hover:bg-rose-200/85', activeRing);
  return clsx('bg-white/30 hover:bg-white/45', activeRing);
}

function workAtlasLaneForMark(
  mark: TaskLedgerCartographyAtlasMark,
  queueIds: ReadonlySet<string>,
): string {
  const overlays = mark.overlays ?? {};
  if (overlays.queue_visible === true || queueIds.has(mark.id)) return 'queue_visible';
  if (overlays.blocked) return 'blocked';
  if (overlays.stale) return 'stale';
  if (overlays.signoff_required) return 'signoff_required';
  if (overlays.high_unlock) return 'high_unlock';
  if (overlays.unrouted) return 'unrouted';
  const state = mark.state ?? 'unknown';
  if (WORK_ATLAS_TERMINAL_STATES.has(state)) return 'terminal';
  if (state === 'unknown') return 'unknown';
  return 'global_open';
}

// eslint-disable-next-line react-refresh/only-export-components
export function __workLensLaneForMarkForTests(
  mark: TaskLedgerCartographyAtlasMark,
  queueIds: ReadonlySet<string> = new Set(),
): string {
  return workAtlasLaneForMark(mark, queueIds);
}

function objectTokenIssue(objectToken: string | null | undefined, expectedKind: string): string | null {
  const token = typeof objectToken === 'string' ? objectToken.trim() : '';
  if (!token) return null;
  const separator = token.indexOf(':');
  if (separator <= 0 || separator === token.length - 1) {
    return `URL object token is malformed: ${token}`;
  }
  const kind = token.slice(0, separator);
  if (kind !== expectedKind) {
    return `URL object ${kind} ignored; expected ${expectedKind}`;
  }
  return null;
}

function selectionSourceLabel(source: WorkSelectionDisplaySource): string {
  if (source === 'url') return 'URL';
  if (source === 'url_fallback') return 'URL fallback';
  if (source === 'default') return 'default top row';
  return 'click/local';
}

function ClusterChip({ label, count }: { label: string; count: number }) {
  return (
    <div className="rounded-[10px] border border-white/[0.08] bg-white/[0.03] px-2 py-1.5">
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
        {label}
      </div>
      <div className="mt-0.5 font-mono text-[14px] tabular-nums text-white">
        {count}
      </div>
    </div>
  );
}

function MassBar({
  segments,
  selectedId,
  onSelect,
}: {
  segments: MassSegment[];
  selectedId: string | null;
  onSelect: (segment: MassSegment) => void;
}) {
  const total = segments.reduce((sum, segment) => sum + segment.count, 0);
  if (total <= 0) {
    return (
      <div className="h-8 rounded-[10px] border border-white/[0.06] bg-white/[0.03]" />
    );
  }
  return (
    <div className="flex h-8 overflow-hidden rounded-[10px] border border-white/[0.08] bg-black/40">
      {segments.map((segment) => {
        const percent = (segment.count / total) * 100;
        return (
          <button
            key={segment.id}
            type="button"
            title={`${segment.label}: ${segment.count}`}
            onClick={() => onSelect(segment)}
            className={clsx(
              'min-w-[10px] border-r border-black/35 transition-colors last:border-r-0',
              segmentClass(segment, selectedId === segment.id),
            )}
            style={{ width: `${Math.max(percent, 1.5)}%` }}
          >
            <span className="sr-only">
              {segment.label} {segment.count}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function WorkOperatingPicture({
  projection,
  projectionLoading,
  projectionError,
  overview,
  phaseId,
  selectedSegmentId,
  onSelectedSegmentChange,
}: {
  projection: TaskLedgerProjectionResponse | null;
  projectionLoading: boolean;
  projectionError: string | null;
  overview: WorkLedgerOverviewResponse | null;
  phaseId: string | null;
  selectedSegmentId: string | null;
  onSelectedSegmentChange: (id: string | null) => void;
}) {
  const states = asCountRecord(projection?.counts.states);
  const types = asCountRecord(projection?.counts.types);
  const stateSegments = countSegments(states, 'state');
  const typeSegments = countSegments(types, 'type', 8);
  const totalWorkItems = projection?.counts.work_items ?? 0;
  const terminalCount = Object.entries(states).reduce(
    (sum, [state, count]) => sum + (terminalState(state) ? count : 0),
    0,
  );
  const unfinishedCount = Math.max(0, totalWorkItems - terminalCount);
  const workLedgerCounts = asRecord(overview?.counts);
  const openThreads = asNumber(workLedgerCounts?.open_threads) ?? 0;
  const threadCount = asNumber(workLedgerCounts?.threads) ?? 0;
  const unknownRoutes = asNumber(projection?.projection_honesty?.unknown_route_count) ?? 0;
  const phaseScope = asString(projection?.projection_honesty?.phase_scope);
  const selectedSegment = [...stateSegments, ...typeSegments].find(
    (segment) => segment.id === selectedSegmentId,
  );

  const handleSelect = (segment: MassSegment) => {
    onSelectedSegmentChange(selectedSegmentId === segment.id ? null : segment.id);
  };

  return (
    <section className="rounded-[14px] border border-white/[0.08] bg-black/30 p-3">
      <PanelSourceHeader
        title="global work mass"
        kicker="task ledger"
        sourceLabel="/api/world-model/task-ledger/projection"
        schemaVersion="task_ledger_projection_v1"
        freshness={
          projection
            ? `${compactCount(totalWorkItems)} WorkItems`
            : projectionLoading
              ? 'loading'
              : 'degraded'
        }
        freshnessTone={projection ? 'ok' : projectionLoading ? 'loading' : 'warn'}
        claimBoundary="events.jsonl authority · active phase is a viewport"
        trailing={
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
            {phaseId ? `active window ${phaseId}` : 'global'}
          </span>
        }
      />
      <div className="mt-3 grid grid-cols-4 gap-2">
        <ClusterChip label="workitems" count={totalWorkItems} />
        <ClusterChip label="unfinished" count={unfinishedCount} />
        <ClusterChip label="wl open" count={openThreads} />
        <ClusterChip label="unknown route" count={unknownRoutes} />
      </div>
      <div className="mt-3 grid gap-3">
        <div>
          <div className="mb-1 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
            <span>lifecycle state</span>
            <span>{compactCount(totalWorkItems)} total</span>
          </div>
          <MassBar
            segments={stateSegments}
            selectedId={selectedSegmentId}
            onSelect={handleSelect}
          />
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
            <span>work type</span>
            <span>{compactCount(typeSegments.reduce((sum, segment) => sum + segment.count, 0))} shown</span>
          </div>
          <MassBar
            segments={typeSegments}
            selectedId={selectedSegmentId}
            onSelect={handleSelect}
          />
        </div>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-[minmax(0,1fr)_160px]">
        <div className="rounded-[10px] border border-white/[0.06] bg-black/25 px-2.5 py-2 text-[11px] leading-5 text-white/68">
          {phaseScope ??
            (projectionError
              ? 'Support projection unavailable in this take; Work Atlas and queue evidence remain live.'
              : 'Global Task Ledger rows are shown before the Work Ledger execution-thread slice.')}
        </div>
        <div className="rounded-[10px] border border-white/[0.06] bg-black/25 px-2.5 py-2 text-right font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
          {threadCount} wl threads
          <br />
          {openThreads} open
        </div>
      </div>
      {selectedSegment && (
        <div className="mt-2 rounded-[10px] border border-white/[0.08] bg-white/[0.03] px-2.5 py-2">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
            selected {selectedSegment.kind}
          </div>
          <div className="mt-1 flex items-baseline justify-between gap-3">
            <div className="min-w-0 truncate text-[12px] text-white/82">{selectedSegment.label}</div>
            <div className="font-mono text-[18px] tabular-nums text-white">
              {selectedSegment.count}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function DossierField({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: string;
  tone?: 'ok' | 'warn' | 'block' | 'neutral';
}) {
  const toneClass =
    tone === 'ok'
      ? 'border-emerald-300/25 bg-emerald-300/[0.05]'
      : tone === 'warn'
        ? 'border-amber-300/25 bg-amber-300/[0.05]'
        : tone === 'block'
          ? 'border-rose-300/25 bg-rose-300/[0.05]'
          : 'border-white/[0.06] bg-white/[0.02]';
  return (
    <div className={clsx('rounded-[10px] border px-2 py-1.5', toneClass)}>
      <div className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/45">
        {label}
      </div>
      <div className="mt-0.5 text-[11px] leading-4 text-white/82">{value}</div>
    </div>
  );
}

function CurrentWorkStrip({
  projection,
  projectionLoading,
  projectionError,
}: {
  projection: TaskLedgerProjectionResponse | null;
  projectionLoading: boolean;
  projectionError: string | null;
}) {
  const currentNext = projection?.current_next ?? null;
  // current_next.label is the human-readable next move; work_item.title carries
  // the actual subject if a work item is bound. Prefer the bound subject when
  // present so the strip reads as "do X" rather than "go inspect X".
  const boundTitle = asString(
    asRecord(currentNext?.work_item as unknown)?.title,
  );
  const headline = boundTitle ?? asString(currentNext?.label);
  const tone: 'ok' | 'warn' | 'loading' =
    !projection ? 'loading' : currentNext?.tone === 'warn' ? 'warn' : 'ok';
  const queueRecord = asRecord(currentNext?.queue as unknown);
  const queueBucket = asString(queueRecord?.bucket);
  const queuePath = asString(queueRecord?.path);
  const queueState = asString(queueRecord?.state);
  const views = projection?.counts.views ?? {};
  const topReady =
    asNumber((views as Record<string, unknown>).ready_by_rank) ??
    asNumber((views as Record<string, unknown>).schedulable_by_rank);
  const blockers =
    asNumber((views as Record<string, unknown>).blocked) ??
    asNumber((views as Record<string, unknown>).dependency_blocked);
  const wip = asNumber((views as Record<string, unknown>).active_wip);

  return (
    <section className="rounded-[14px] border border-white/[0.08] bg-black/30 p-3">
      <PanelSourceHeader
        title="current work"
        kicker="vantage"
        sourceLabel="/api/world-model/task-ledger/projection · current_next + counts.views"
        schemaVersion="task_ledger_projection_v1"
        freshness={projection ? 'loaded' : projectionLoading ? 'loading' : 'degraded'}
        freshnessTone={projection ? tone : projectionLoading ? 'loading' : 'warn'}
        claimBoundary="observation only · mutation lives in task_ledger_apply"
      />
      <div className="mt-2 text-[12px] leading-5 text-white/82">
        {headline ??
          (projectionError
            ? 'support projection unavailable; use Work Atlas and queue dossier for this take'
            : 'no current_next resolved in this snapshot')}
      </div>
      {(queueBucket || queuePath || queueState) && (
        <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/40">
          {queueBucket ? `bucket · ${queueBucket}` : ''}
          {queueState ? ` · state ${queueState}` : ''}
          {queuePath ? ` · ${queuePath}` : ''}
        </div>
      )}
      <div className="mt-3 grid grid-cols-3 gap-2">
        <ClusterChip label="top ready" count={topReady ?? 0} />
        <ClusterChip label="blockers" count={blockers ?? 0} />
        <ClusterChip label="wip" count={wip ?? 0} />
      </div>
    </section>
  );
}

// useWorkItemDossier — fetch the WorkItem dossier composing narrative,
// contracts, execution, source-view membership, cartography mark, neighborhood,
// and recent events. Backed by GET /api/world-model/task-ledger/dossier/{id}
// (added in commit dbddf318f). Cancels in-flight requests on id changes.
function useWorkItemDossier(workItemId: string | null): {
  dossier: WorkItemDossierPayloadResponse | null;
  loading: boolean;
  error: string | null;
} {
  const [dossier, setDossier] = useState<WorkItemDossierPayloadResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pattern B — reset to idle state via render-time prev-prop comparison when
  // workItemId clears. Avoids setState-in-effect cascading-renders for the
  // pure-derived "no id, no dossier" branch.
  const [lastWorkItemId, setLastWorkItemId] = useState(workItemId);
  if (workItemId !== lastWorkItemId) {
    setLastWorkItemId(workItemId);
    if (!workItemId) {
      setDossier(null);
      setLoading(false);
      setError(null);
    }
  }

  useEffect(() => {
    if (!workItemId) {
      return;
    }
    let cancelled = false;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      if (cancelled) return;
      controller.abort();
      setLoading(false);
    }, WORK_ITEM_DOSSIER_TIMEOUT_MS);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async-fetch loading flag; tri-state loading/data/error has no derived-state equivalent
    setLoading(true);
    setError(null);
    api.worldModel
      .workItemDossier(workItemId, { event_limit: 12 }, { signal: controller.signal })
      .then((data) => {
        window.clearTimeout(timeoutId);
        if (cancelled) return;
        setDossier(data);
      })
      .catch((err: unknown) => {
        window.clearTimeout(timeoutId);
        if (cancelled) return;
        if (isAbortLike(err)) {
          setError(null);
          return;
        }
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        window.clearTimeout(timeoutId);
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [workItemId]);

  return { dossier, loading, error };
}

// Internal helpers used by WorkItemDossierPanel.
function relativeTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const ts = Date.parse(iso);
  if (!Number.isFinite(ts)) return iso;
  const deltaSec = Math.round((Date.now() - ts) / 1000);
  if (deltaSec < 60) return `${deltaSec}s ago`;
  const min = Math.round(deltaSec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 48) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 60) return `${day}d ago`;
  return iso.slice(0, 10);
}

function shortHash(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const v = value.trim();
  if (!v) return null;
  return v.length > 12 ? v.slice(0, 12) : v;
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  const out: string[] = [];
  for (const entry of value) {
    if (typeof entry === 'string' && entry.trim()) out.push(entry);
  }
  return out;
}

function DossierSection({
  label,
  trailing,
  children,
  tone = 'neutral',
}: {
  label: string;
  trailing?: string | null;
  children: ReactNode;
  tone?: 'ok' | 'warn' | 'block' | 'neutral';
}) {
  const toneEdge =
    tone === 'ok'
      ? 'border-emerald-300/25'
      : tone === 'warn'
        ? 'border-amber-300/25'
        : tone === 'block'
          ? 'border-rose-300/25'
          : 'border-white/[0.08]';
  return (
    <section className={clsx('mt-2 rounded-[10px] border bg-black/30 p-2.5', toneEdge)}>
      <div className="flex items-baseline justify-between gap-2">
        <div className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-white/50">
          {label}
        </div>
        {trailing && (
          <div className="truncate font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/35">
            {trailing}
          </div>
        )}
      </div>
      <div className="mt-1.5 text-[11.5px] leading-5 text-white/82">{children}</div>
    </section>
  );
}

function ChipList({
  items,
  tone = 'neutral',
  monospaced = true,
  max = 12,
}: {
  items: string[];
  tone?: 'ok' | 'warn' | 'block' | 'neutral';
  monospaced?: boolean;
  max?: number;
}) {
  if (items.length === 0) return null;
  const toneClass =
    tone === 'ok'
      ? 'border-emerald-300/30 bg-emerald-300/[0.06] text-emerald-100'
      : tone === 'warn'
        ? 'border-amber-300/30 bg-amber-300/[0.06] text-amber-100'
        : tone === 'block'
          ? 'border-rose-300/30 bg-rose-300/[0.06] text-rose-100'
          : 'border-white/[0.10] bg-white/[0.03] text-white/72';
  const shown = items.slice(0, max);
  const overflow = items.length - shown.length;
  return (
    <div className="flex flex-wrap gap-1">
      {shown.map((item) => (
        <span
          key={item}
          className={clsx(
            'rounded-full border px-1.5 py-0.5 text-[9.5px] tracking-[0.06em]',
            monospaced ? 'font-mono' : '',
            toneClass,
          )}
        >
          {item}
        </span>
      ))}
      {overflow > 0 && (
        <span className="rounded-full border border-white/[0.08] bg-white/[0.02] px-1.5 py-0.5 font-mono text-[9.5px] text-white/45">
          +{overflow}
        </span>
      )}
    </div>
  );
}

// WorkItemDossierPanel — rich per-WorkItem drilldown that replaces the previous
// thin id/state/actor/family chips with the actual content of the item:
// narrative (statement/problem/impact/acceptance/recommended_action), ranking +
// source-view "why this next" rationale, execution receipt + commit + closeout,
// satisfaction & integration contracts, source-view membership, and a recent-
// events timeline. Loading/error/missing states are explicit; falls back to a
// hedged "not in ledger.json yet" line rather than empty silence.
function WorkItemDossierPanel({
  dossier,
  loading,
  error,
  workItemId,
}: {
  dossier: WorkItemDossierPayloadResponse | null;
  loading: boolean;
  error: string | null;
  workItemId: string | null;
}) {
  if (!workItemId) return null;
  if (loading && !dossier) {
    return (
      <div
        data-zenith-work-dossier-panel="pending"
        className="mt-2 rounded-[10px] border border-white/[0.06] bg-black/20 px-2.5 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-white/45"
      >
        dossier detail pending · {workItemId}
      </div>
    );
  }
  if (error) {
    return (
      <div
        data-zenith-work-dossier-panel="error"
        className="mt-2 rounded-[10px] border border-rose-300/30 bg-rose-300/[0.05] px-2.5 py-2 text-[11px] leading-5 text-rose-100"
      >
        dossier · error · {error}
      </div>
    );
  }
  if (!dossier) return null;
  if (!dossier.available) {
    return (
      <div
        data-zenith-work-dossier-panel="unavailable"
        className="mt-2 rounded-[10px] border border-amber-300/25 bg-amber-300/[0.05] px-2.5 py-2 text-[11px] leading-5 text-amber-100"
      >
        dossier unavailable · {dossier.reason ?? 'not present in ledger.json'}
      </div>
    );
  }

  const narrative = dossier.narrative ?? {};
  const focus = dossier.focus ?? {};
  const ranking = dossier.ranking ?? {};
  const execution = dossier.execution ?? {};
  const contracts = dossier.contracts ?? {};
  const events = dossier.recent_events ?? [];
  const sourceViews = dossier.source_view_membership ?? [];

  const recommendedAction =
    narrative.recommended_action ?? (focus as { recommended_action?: string | null }).recommended_action;

  // Why-now: pick first source-view membership that carries an explicit
  // why_this_next/why_recommended explanation (execution_menu has it; raw census
  // views don't).
  const whyView = sourceViews.find(
    (v) =>
      (v.why_this_next && v.why_this_next.length > 0) ||
      (v.why_recommended && v.why_recommended.trim().length > 0),
  );

  const sat = (contracts.satisfaction_contract ?? {}) as Record<string, unknown>;
  const integ = (contracts.integration_contract ?? {}) as Record<string, unknown>;
  const satPrinciples = asStringList(sat.principle_refs);
  const satAxioms = asStringList(sat.axiom_refs);
  const satRawSeeds = asStringList(sat.raw_seed_refs);
  const satVoice = asStringList(sat.operator_voice_refs);
  const integSurfaces = asStringList(integ.candidate_surfaces);
  const integGroundedRaw = (integ.exact_surfaces_discovered ?? []) as Array<
    Record<string, unknown>
  >;
  const integGrounded = integGroundedRaw
    .map((row) => {
      const path = typeof row.path === 'string' ? row.path : null;
      if (!path) return null;
      const status = typeof row.status === 'string' ? row.status : null;
      return status ? `${path} · ${status}` : path;
    })
    .filter((s): s is string => s !== null);

  const latestReceipt =
    (execution.latest_execution_receipt as Record<string, unknown> | null) ?? null;
  const latestCommit =
    shortHash(latestReceipt?.commit_hash) ??
    shortHash((execution.commit_refs ?? [])[0]);
  const txState = (execution.transaction_state ?? null) as string | null;
  const closeoutState =
    typeof latestReceipt?.closeout_state === 'string'
      ? (latestReceipt.closeout_state as string)
      : null;
  const txId =
    typeof latestReceipt?.transaction_id === 'string'
      ? (latestReceipt.transaction_id as string)
      : null;
  const receiptCount = (execution.execution_receipts ?? []).length;
  const hasExecution = Boolean(latestReceipt || txState || latestCommit || receiptCount);

  const focusActor =
    (focus as { actor?: string | null }).actor ??
    (focus as { owner?: string | null }).owner ??
    null;
  const focusCreatedAt = (focus as { created_at?: string | null }).created_at ?? null;
  const focusUpdatedAt = (focus as { updated_at?: string | null }).updated_at ?? null;
  const focusConfidence =
    typeof (focus as { confidence?: number | null }).confidence === 'number'
      ? (focus as { confidence: number }).confidence
      : null;
  const focusTags = asStringList((focus as { tags?: unknown }).tags);

  return (
    <div
      data-zenith-work-dossier-panel="ready"
      data-zenith-work-dossier-panel-id={dossier.work_item_id}
      data-zenith-work-dossier-panel-event-count={events.length}
      data-zenith-work-dossier-panel-source-view-count={sourceViews.length}
      data-zenith-work-dossier-panel-has-receipt={latestReceipt ? 'yes' : 'no'}
      className="mt-2"
    >
      {/* Narrative — statement is the headline answer to "what is this WorkItem
          really about?". Problem / impact / acceptance / recommended_action are
          conditionally rendered so empty rows do not bloat the panel. */}
      {(narrative.statement ||
        narrative.problem ||
        narrative.impact ||
        narrative.acceptance ||
        recommendedAction) && (
        <DossierSection label="narrative">
          {narrative.statement && (
            <div className="text-[12.5px] leading-5 text-white">{narrative.statement}</div>
          )}
          {narrative.problem && (
            <div className="mt-1.5">
              <span className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-white/40">
                problem ·{' '}
              </span>
              {narrative.problem}
            </div>
          )}
          {narrative.impact && (
            <div className="mt-1">
              <span className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-white/40">
                impact ·{' '}
              </span>
              {narrative.impact}
            </div>
          )}
          {narrative.acceptance && (
            <div className="mt-1">
              <span className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-white/40">
                acceptance ·{' '}
              </span>
              {narrative.acceptance}
            </div>
          )}
          {recommendedAction && (
            <div className="mt-2 rounded-[8px] border border-emerald-300/25 bg-emerald-300/[0.06] px-2 py-1.5 text-[11.5px] text-emerald-100">
              <span className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-emerald-200/80">
                do next ·{' '}
              </span>
              {recommendedAction}
            </div>
          )}
        </DossierSection>
      )}

      {/* Why-now — pulled from execution_menu (or any source-view that carries
          an explicit "why this next" trail). Skipped when no view has rationale,
          rather than rendering an empty heading. */}
      {(ranking.rank != null || whyView) && (
        <DossierSection
          label="why now"
          trailing={whyView ? `via ${whyView.view_id}` : null}
        >
          <div className="flex flex-wrap items-center gap-2 text-[11px]">
            {ranking.rank != null && (
              <span className="rounded-full border border-emerald-300/30 bg-emerald-300/[0.06] px-2 py-0.5 font-mono text-[10px] text-emerald-100">
                rank · {ranking.rank}
              </span>
            )}
            {whyView?.why_recommended && (
              <span className="text-white/72">{whyView.why_recommended}</span>
            )}
          </div>
          {whyView?.why_this_next && whyView.why_this_next.length > 0 && (
            <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-[11px] text-white/72">
              {whyView.why_this_next.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
        </DossierSection>
      )}

      {/* Execution — latest receipt + commit + closeout shape. Hedged "no
          execution receipt yet" rather than silently rendering nothing so the
          operator knows the item exists in the ledger but has no run yet. */}
      <DossierSection
        label="execution"
        trailing={receiptCount > 0 ? `${receiptCount} receipts` : null}
        tone={
          txState === 'validated_commit_landed'
            ? 'ok'
            : txState && txState.includes('fail')
              ? 'block'
              : 'neutral'
        }
      >
        {hasExecution ? (
          <div className="grid gap-1">
            <div className="flex flex-wrap items-center gap-1.5 text-[10.5px] text-white/72">
              {txState && (
                <span
                  className={clsx(
                    'rounded-full border px-1.5 py-0.5 font-mono text-[9.5px]',
                    txState === 'validated_commit_landed'
                      ? 'border-emerald-300/30 text-emerald-100'
                      : 'border-white/[0.12] text-white/72',
                  )}
                >
                  {txState}
                </span>
              )}
              {closeoutState && (
                <span className="rounded-full border border-white/[0.12] px-1.5 py-0.5 font-mono text-[9.5px] text-white/72">
                  closeout · {closeoutState}
                </span>
              )}
              {latestCommit && (
                <span className="rounded-full border border-cyan-300/30 bg-cyan-300/[0.05] px-1.5 py-0.5 font-mono text-[9.5px] text-cyan-100">
                  commit · {latestCommit}
                </span>
              )}
            </div>
            {txId && (
              <div className="truncate font-mono text-[10px] text-white/45">{txId}</div>
            )}
          </div>
        ) : (
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/40">
            no execution receipt recorded
          </div>
        )}
      </DossierSection>

      {/* Contracts — satisfaction (what principles/axioms/raw-seed lines this
          WorkItem serves) + integration (where it lands on disk). Empty
          contracts collapse to nothing so a freshly captured item doesn't show
          two blank rows. */}
      {(satPrinciples.length > 0 ||
        satAxioms.length > 0 ||
        satRawSeeds.length > 0 ||
        satVoice.length > 0 ||
        integGrounded.length > 0 ||
        integSurfaces.length > 0) && (
        <DossierSection label="contracts">
          {(satPrinciples.length > 0 ||
            satAxioms.length > 0 ||
            satRawSeeds.length > 0 ||
            satVoice.length > 0) && (
            <div className="grid gap-1.5">
              <div className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-white/40">
                satisfaction
              </div>
              {satPrinciples.length > 0 && (
                <ChipList items={satPrinciples} tone="ok" />
              )}
              {satAxioms.length > 0 && <ChipList items={satAxioms} tone="warn" />}
              {satRawSeeds.length > 0 && (
                <ChipList items={satRawSeeds.map((s) => s.slice(0, 56))} tone="neutral" />
              )}
              {satVoice.length > 0 && (
                <ChipList items={satVoice} tone="neutral" max={6} />
              )}
            </div>
          )}
          {(integGrounded.length > 0 || integSurfaces.length > 0) && (
            <div className="mt-2 grid gap-1">
              <div className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-white/40">
                integration
              </div>
              {integGrounded.length > 0 ? (
                <ul className="space-y-0.5 font-mono text-[10.5px] text-white/72">
                  {integGrounded.slice(0, 6).map((row) => (
                    <li key={row} className="truncate">
                      {row}
                    </li>
                  ))}
                  {integGrounded.length > 6 && (
                    <li className="text-white/45">+{integGrounded.length - 6} more</li>
                  )}
                </ul>
              ) : (
                <ul className="space-y-0.5 font-mono text-[10.5px] text-white/55">
                  {integSurfaces.slice(0, 6).map((row) => (
                    <li key={row} className="truncate">
                      {row}
                    </li>
                  ))}
                  {integSurfaces.length > 6 && (
                    <li className="text-white/35">+{integSurfaces.length - 6} more</li>
                  )}
                </ul>
              )}
            </div>
          )}
        </DossierSection>
      )}

      {/* Source-view membership — answers "which projection lists this row,
          and as what kind?". Tiny chip cloud; deduped/limited. */}
      {sourceViews.length > 0 && (
        <DossierSection
          label="source views"
          trailing={`${sourceViews.length} surfaces`}
        >
          <ChipList
            items={sourceViews.map((v) => v.view_id)}
            tone="neutral"
            max={16}
          />
        </DossierSection>
      )}

      {/* Recent events — append-only ledger tail for this subject. Always shows
          event_type + when + who; payload_preview is intentionally one or two
          keys only (the panel is a teaser, not a transcript). */}
      {events.length > 0 && (
        <DossierSection label="recent events" trailing={`${events.length} shown`}>
          <ul className="grid gap-1.5">
            {events.slice(0, 8).map((ev, i) => {
              const previewEntries = Object.entries(ev.payload_preview ?? {}).slice(0, 2);
              return (
                <li
                  key={ev.event_id ?? `${ev.event_type}-${i}`}
                  className="rounded-[8px] border border-white/[0.05] bg-white/[0.02] px-2 py-1.5"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-white/55">
                    <span className="text-white/82">{ev.event_type ?? 'unknown'}</span>
                    <span className="text-white/45">
                      {relativeTime(ev.created_at)} · {ev.created_by ?? '—'}
                    </span>
                  </div>
                  {previewEntries.length > 0 && (
                    <div className="mt-1 font-mono text-[10px] leading-4 text-white/55">
                      {previewEntries.map(([key, value]) => {
                        const valueStr =
                          typeof value === 'string'
                            ? value.length > 96
                              ? `${value.slice(0, 96)}…`
                              : value
                            : typeof value === 'object' && value !== null
                              ? JSON.stringify(value).slice(0, 96)
                              : String(value);
                        return (
                          <div key={key} className="truncate">
                            <span className="text-white/35">{key} · </span>
                            <span>{valueStr}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </DossierSection>
      )}

      {/* Identity tail — actor / created_at / confidence / tags. Kept at the
          bottom so the operator's eye lands on narrative + why-now + execution
          first, with provenance metadata as a calm afterword. */}
      {(focusActor || focusCreatedAt || focusUpdatedAt || focusConfidence != null || focusTags.length > 0) && (
        <DossierSection label="identity">
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/55">
            {focusActor && (
              <span>
                actor ·{' '}
                <span className="normal-case tracking-normal text-white/82">{focusActor}</span>
              </span>
            )}
            {focusCreatedAt && (
              <span>
                captured · <span className="text-white/82">{relativeTime(focusCreatedAt)}</span>
              </span>
            )}
            {focusUpdatedAt && focusUpdatedAt !== focusCreatedAt && (
              <span>
                updated · <span className="text-white/82">{relativeTime(focusUpdatedAt)}</span>
              </span>
            )}
            {focusConfidence != null && (
              <span>
                confidence ·{' '}
                <span className="text-white/82">{focusConfidence.toFixed(2)}</span>
              </span>
            )}
          </div>
          {focusTags.length > 0 && (
            <div className="mt-1.5">
              <ChipList items={focusTags} tone="neutral" max={10} monospaced={false} />
            </div>
          )}
        </DossierSection>
      )}
    </div>
  );
}

export default function WorkLens({
  selectedWorkItemId = null,
  objectToken = null,
  onSelectedWorkItemChange,
  selectedRouteReason: selectedRouteReasonFromUrl = null,
  onSelectedRouteReasonChange,
}: WorkLensProps = {}) {
  const [overview, setOverview] = useState<WorkLedgerOverviewResponse | null>(
    () => cachedWorkLedgerOverview,
  );
  const [taskProjection, setTaskProjection] = useState<TaskLedgerProjectionResponse | null>(null);
  const [loading, setLoading] = useState(() => cachedWorkLedgerOverview === null);
  const [projectionLoading, setProjectionLoading] = useState(false);
  const [projectionError, setProjectionError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedMassSegmentId, setSelectedMassSegmentId] = useState<string | null>(null);
  // Cartography payload mirrored from WorkAtlas via onPayloadLoaded so the
  // global mini-dossier can resolve arbitrary atlas_mark fields by id without
  // a second fetch. WorkAtlas remains the canonical owner of the fetch.
  const [cartographyPayload, setCartographyPayload] =
    useState<TaskLedgerCartographyPayloadResponse | null>(null);
  // Selected aggregate cell (lane × state) on the Atlas. Lifted to WorkLens
  // so the right-rail inspector can switch between queue dossier, global
  // mini-dossier, cell inspector, and idle states under one slot.
  const [selectedAtlasCell, setSelectedAtlasCell] = useState<AtlasCellId | null>(null);
  // Wave 1G: mirror the per-WorkItem neighborhood payload from
  // NeighborhoodInspector so the Atlas can render aggregate-cell
  // highlights for focus + upstream + downstream marks. Single fetch
  // owner remains NeighborhoodInspector; WorkLens only holds the
  // payload for cross-component coordination.
  const [selectedNeighborhood, setSelectedNeighborhood] =
    useState<WorkItemNeighborhoodPayloadResponse | null>(null);
  const warmingRetryCountRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    let timedOut = false;
    const hasCachedOverview = cachedWorkLedgerOverview !== null;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
      if (cancelled) return;
      if (!hasCachedOverview) {
        setOverview(null);
        setError(`Work Ledger overview timed out after ${WORK_LEDGER_OVERVIEW_TIMEOUT_MS / 1000}s.`);
      }
      setLoading(false);
    }, WORK_LEDGER_OVERVIEW_TIMEOUT_MS);
    api.worldModel
      .workLedgerOverview({}, { signal: controller.signal })
      .then((workLedger) => {
        window.clearTimeout(timeoutId);
        if (cancelled) return;
        cachedWorkLedgerOverview = workLedger;
        setOverview(workLedger);
        setError(null);
      })
      .catch((err: unknown) => {
        window.clearTimeout(timeoutId);
        if (timedOut) return;
        if (cancelled) return;
        if (!hasCachedOverview) {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled && !timedOut) setLoading(false);
      });
    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (loading || error) return;
    if (!isWorkLedgerOverviewRefreshPending(overview)) {
      warmingRetryCountRef.current = 0;
      return;
    }
    const retryIndex = warmingRetryCountRef.current;
    if (retryIndex >= WORK_LEDGER_OVERVIEW_WARM_RETRY_DELAYS_MS.length) return;
    warmingRetryCountRef.current += 1;

    let cancelled = false;
    const controller = new AbortController();
    const retryDelay = WORK_LEDGER_OVERVIEW_WARM_RETRY_DELAYS_MS[retryIndex];
    const retryTimeout = window.setTimeout(() => {
      api.worldModel
        .workLedgerOverview({}, { signal: controller.signal })
        .then((workLedger) => {
          if (cancelled) return;
          cachedWorkLedgerOverview = workLedger;
          setOverview(workLedger);
          setError(null);
        })
        .catch((err: unknown) => {
          if (cancelled || isAbortLike(err)) return;
          // Keep the typed warming shell on screen; a retry failure is not an
          // empty queue or a route error while the backend prewarm is in flight.
        });
    }, retryDelay);

    return () => {
      cancelled = true;
      window.clearTimeout(retryTimeout);
      controller.abort();
    };
  }, [error, loading, overview]);

  useEffect(() => {
    if (loading || error) return;
    let cancelled = false;
    const controller = new AbortController();
    let projectionTimeout: ReturnType<typeof setTimeout> | null = null;
    const startDelay = setTimeout(() => {
      if (cancelled) return;
      setProjectionLoading(true);
      projectionTimeout = setTimeout(() => {
        controller.abort();
      }, 8000);
      api.worldModel
        .taskLedgerProjection({ limit: 8 }, { signal: controller.signal })
        .then((taskLedger) => {
          if (cancelled) return;
          setTaskProjection(taskLedger);
          setProjectionError(null);
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setProjectionError(err instanceof Error ? err.message : String(err));
        })
        .finally(() => {
          if (projectionTimeout) clearTimeout(projectionTimeout);
          if (!cancelled) setProjectionLoading(false);
        });
    }, 1600);
    return () => {
      cancelled = true;
      clearTimeout(startDelay);
      if (projectionTimeout) clearTimeout(projectionTimeout);
      controller.abort();
    };
  }, [error, loading]);

  const openItems = useMemo<WorkItemRow[]>(() => {
    if (!overview) return [];
    return flattenOpenBy(overview.open_by_actor as Record<string, unknown[]> | undefined, false);
  }, [overview]);

  const staleItems = useMemo<WorkItemRow[]>(() => {
    if (!overview) return [];
    const rows = (overview.stale_open as unknown[] | undefined) ?? [];
    return rows
      .map((entry) => readWorkItemRow(entry, null, true))
      .filter((row): row is WorkItemRow => row !== null);
  }, [overview]);

  const recentlyClosed = useMemo<WorkItemRow[]>(() => {
    if (!overview) return [];
    const rows = (overview.recently_closed as unknown[] | undefined) ?? [];
    return rows
      .map((entry) => readWorkItemRow(entry, null, false))
      .filter((row): row is WorkItemRow => row !== null);
  }, [overview]);

  const handoffCandidates = useMemo<WorkItemRow[]>(() => {
    if (!overview) return [];
    const raw = overview.handoff_candidates as Record<string, unknown> | undefined;
    if (!raw) return [];
    const rows = (raw.items as unknown[] | undefined) ?? [];
    return rows
      .map((entry) => readWorkItemRow(entry, null, false))
      .filter((row): row is WorkItemRow => row !== null);
  }, [overview]);

  const allOpen = useMemo(
    () => dedupeWorkItemRows([...openItems, ...staleItems]),
    [openItems, staleItems],
  );
  const overviewSliceDisclosure = useMemo(
    () => workLedgerOverviewSliceDisclosure(overview),
    [overview],
  );

  // Global selection identity: the WorkItem id the operator has actually
  // committed to via URL or local Atlas click, regardless of whether it
  // happens to live in this Work Ledger queue slice. The Work Atlas universe
  // exceeds the queue, so we must not collapse a global pick to the queue top
  // — that would re-create the exact failure mode the Atlas exists to close.
  const globalSelectedWorkItemId: string | null =
    selectedWorkItemId ?? selectedId ?? null;
  const globalSelectionOutsideQueue =
    globalSelectedWorkItemId !== null &&
    !allOpen.some((row) => row.id === globalSelectedWorkItemId);
  // Resolve the selected atlas_mark for the global mini-dossier. Sourced from
  // the cartography payload mirror, so we get the same row-grain identity the
  // Atlas itself renders (state, work_item_type, actor, family, route status,
  // overlays, edge_summary). Null until the cartography fetch resolves.
  const globalSelectedMark = useMemo<TaskLedgerCartographyAtlasMark | null>(() => {
    if (!cartographyPayload?.atlas_marks || !globalSelectedWorkItemId) return null;
    return (
      cartographyPayload.atlas_marks.find((m) => m.id === globalSelectedWorkItemId) ??
      null
    );
  }, [cartographyPayload, globalSelectedWorkItemId]);

  // Wave 1G — neighborhood highlight sets. Drives WorkAtlas's aggregate-
  // cell badges so the operator sees where the selected WorkItem's local
  // topology sits inside the global map. focusId is the selected mark;
  // upstream/downstream come from the detail route's neighbors[]. When
  // no neighborhood is loaded the highlight is implicitly idle.
  const atlasNeighborhoodHighlight = useMemo(() => {
    if (!selectedNeighborhood || !selectedNeighborhood.available) return null;
    const focusId = selectedNeighborhood.work_item_id;
    const upstream = new Set<string>();
    const downstream = new Set<string>();
    for (const n of selectedNeighborhood.neighbors ?? []) {
      if (
        n.relation_to_focus === 'depends_on' ||
        n.relation_to_focus === 'reverse_unlocks'
      ) {
        upstream.add(n.id);
      } else if (
        n.relation_to_focus === 'unlocks' ||
        n.relation_to_focus === 'reverse_depends_on'
      ) {
        downstream.add(n.id);
      }
    }
    return {
      focusId,
      upstreamIds: upstream as ReadonlySet<string>,
      downstreamIds: downstream as ReadonlySet<string>,
    };
  }, [selectedNeighborhood]);

  // queueIds is a legacy fallback for WorkAtlas's `queue_visible` lane. The
  // canonical signal is the backend-stamped `mark.overlays.queue_visible`
  // crosswalk because Work Ledger td_* ids and Task Ledger mark ids are
  // separate namespaces.
  const queueIds = useMemo<ReadonlySet<string>>(
    () => new Set(allOpen.map((r) => r.id)),
    [allOpen],
  );

  // Marks inside the currently selected aggregate cell — the substrate for
  // the cell inspector when nothing else is selected. Top-N by downstream
  // unlocks gives the operator the highest-leverage entry points first.
  const cellInspectorMarks = useMemo<TaskLedgerCartographyAtlasMark[]>(() => {
    if (!selectedAtlasCell || !cartographyPayload?.atlas_marks) return [];
    const lane = selectedAtlasCell.lane;
    const state = selectedAtlasCell.state;
    const matches = cartographyPayload.atlas_marks.filter((m) => {
      // Re-derive lane locally to mirror WorkAtlas.deriveLane precedence.
      const markLane = workAtlasLaneForMark(m, queueIds);
      if (markLane !== lane) return false;
      const markState =
        m.state && ['captured', 'shaping', 'shaped', 'execution', 'signoff', 'done', 'propagated', 'retired'].includes(m.state)
          ? m.state
          : 'other';
      return markState === state;
    });
    matches.sort(
      (a, b) =>
        (b.edge_summary?.downstream_unlock_count ?? 0) -
        (a.edge_summary?.downstream_unlock_count ?? 0),
    );
    return matches;
  }, [selectedAtlasCell, cartographyPayload, queueIds]);

  // Wave 2A — global unrouted summary panel. Always-visible right-rail
  // section that renders the top-N route reasons across the full atlas.
  // Independent of the inspector mode; gives proof shape without forcing
  // the operator to click a cell.
  const unroutedGlobalSummary = useMemo(() => {
    const empty = {
      ready: false,
      unroutedTotal: 0,
      explainedCount: 0,
      unknownCount: 0,
      ranked: [] as Array<{ reason: string; count: number; kind: string | null }>,
      distinctReasonCount: 0,
    };
    if (!cartographyPayload?.atlas_marks) return empty;
    const reasonCount = new Map<string, number>();
    const reasonKind = new Map<string, string>();
    let total = 0;
    let explained = 0;
    let unknown = 0;
    for (const m of cartographyPayload.atlas_marks) {
      if (!m.overlays?.unrouted) continue;
      total += 1;
      const reason = m.route_explanation?.route_reason ?? 'unknown_reason';
      reasonCount.set(reason, (reasonCount.get(reason) ?? 0) + 1);
      if (m.route_explanation?.reason_kind) {
        reasonKind.set(reason, m.route_explanation.reason_kind);
      }
      if (reason === 'unknown_reason') unknown += 1;
      else explained += 1;
    }
    const ranked = Array.from(reasonCount.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([reason, count]) => ({
        reason,
        count,
        kind: reasonKind.get(reason) ?? null,
      }));
    return {
      ready: total > 0,
      unroutedTotal: total,
      explainedCount: explained,
      unknownCount: unknown,
      ranked,
      distinctReasonCount: reasonCount.size,
    };
  }, [cartographyPayload]);

  // Wave 2B — resolution affordance map pulled from consumption_contract.
  // Single source of truth: backend stamps every present reason with a
  // resolution_disposition + resolution_status + owner_view. UI looks it up
  // by reason key when rendering the row; falls back to a safe "inspect"
  // shape when the payload pre-dates Wave 2B.
  const unroutedResolutionSummary = useMemo(() => {
    const contract = cartographyPayload?.consumption_contract
      ?.drilldown_contract as
      | {
          route_provenance_resolution_present?: boolean;
          route_provenance_resolution_affordances?: Record<
            string,
            TaskLedgerCartographyRouteResolutionAffordance
          >;
          route_provenance_resolution_reason_with_remedy_count?: number;
          route_provenance_resolution_reason_without_remedy_count?: number;
          route_provenance_resolution_status_counts?: Record<string, number>;
          route_provenance_resolution_disposition_counts?: Record<string, number>;
        }
      | undefined;
    const affordances = contract?.route_provenance_resolution_affordances ?? {};
    const withRemedyCount =
      contract?.route_provenance_resolution_reason_with_remedy_count ?? 0;
    const withoutRemedyCount =
      contract?.route_provenance_resolution_reason_without_remedy_count ?? 0;
    return {
      present: Boolean(contract?.route_provenance_resolution_present),
      affordances,
      withRemedyCount,
      withoutRemedyCount,
      totalReasonCount: withRemedyCount + withoutRemedyCount,
      statusCounts:
        contract?.route_provenance_resolution_status_counts ?? {},
      dispositionCounts:
        contract?.route_provenance_resolution_disposition_counts ?? {},
    };
  }, [cartographyPayload]);

  // Wave 2A — per-cell route-reason histogram. Sibling of cellInspectorMarks;
  // operates on the same filtered list so the breakdown is locked to the
  // selected cell. ranked is sorted by count desc with deterministic
  // alphabetical tiebreaker.
  const cellInspectorRouteBreakdown = useMemo(() => {
    const empty = {
      ready: false,
      cellUnroutedCount: 0,
      ranked: [] as Array<{
        reason: string;
        count: number;
        kind: string | null;
        exampleId: string | null;
        exampleTitle: string | null;
      }>,
    };
    if (!selectedAtlasCell || cellInspectorMarks.length === 0) return empty;
    const reasonCount = new Map<string, number>();
    const reasonKind = new Map<string, string>();
    const reasonExample = new Map<string, { id: string; title: string }>();
    let cellUnrouted = 0;
    for (const m of cellInspectorMarks) {
      if (!m.overlays?.unrouted) continue;
      cellUnrouted += 1;
      const reason = m.route_explanation?.route_reason ?? 'unknown_reason';
      reasonCount.set(reason, (reasonCount.get(reason) ?? 0) + 1);
      if (m.route_explanation?.reason_kind) {
        reasonKind.set(reason, m.route_explanation.reason_kind);
      }
      if (!reasonExample.has(reason)) {
        reasonExample.set(reason, {
          id: m.id,
          title: m.title || m.id,
        });
      }
    }
    const ranked = Array.from(reasonCount.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([reason, count]) => ({
        reason,
        count,
        kind: reasonKind.get(reason) ?? null,
        exampleId: reasonExample.get(reason)?.id ?? null,
        exampleTitle: reasonExample.get(reason)?.title ?? null,
      }));
    return {
      ready: cellUnrouted > 0,
      cellUnroutedCount: cellUnrouted,
      ranked,
    };
  }, [selectedAtlasCell, cellInspectorMarks]);

  const selection = useMemo(() => {
    const tokenIssue = objectTokenIssue(objectToken, 'work_item');
    if (
      selectedWorkItemId &&
      allOpen.some((row) => row.id === selectedWorkItemId)
    ) {
      return {
        id: selectedWorkItemId,
        source: 'url' as const,
        reason: null,
      };
    }
    if (selectedWorkItemId && allOpen.length > 0) {
      return {
        id: null,
        source: 'url_fallback' as const,
        reason: `URL requested work_item:${selectedWorkItemId}, but that object is not present in this Work Ledger queue slice. Keeping the global Atlas selection instead.`,
      };
    }
    if (selectedId && allOpen.some((row) => row.id === selectedId)) {
      return {
        id: selectedId,
        source: 'local' as const,
        reason: null,
      };
    }
    if (selectedId && allOpen.length > 0) {
      return {
        id: null,
        source: 'local' as const,
        reason: `Selected work_item:${selectedId} is not present in this Work Ledger queue slice. Keeping the global Atlas selection instead.`,
      };
    }
    if (allOpen.length > 0) {
      return {
        id: allOpen[0].id,
        source: tokenIssue ? 'url_fallback' as const : 'default' as const,
        reason: tokenIssue,
      };
    }
    return {
      id: null,
      source: tokenIssue ? 'url_fallback' as const : 'default' as const,
      reason: tokenIssue,
    };
  }, [allOpen, objectToken, selectedId, selectedWorkItemId]);

  const clustersByState = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of allOpen) {
      counts.set(item.state, (counts.get(item.state) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [allOpen]);

  const clustersByActor = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of allOpen) {
      const actor = item.actor ?? 'unassigned';
      counts.set(actor, (counts.get(actor) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [allOpen]);

  const counts = asRecord(overview?.counts);
  const phaseId = asString(overview?.phase_id);
  const familyId = asString(overview?.family_id);
  const overviewWarming = isWorkLedgerOverviewWarming(overview);
  const workSurfaceState = loading ? 'loading' : error ? 'error' : overviewWarming ? 'warming' : 'ready';

  const selectedItem = useMemo(() => {
    if (!selection.id) return null;
    return allOpen.find((row) => row.id === selection.id) ?? null;
  }, [allOpen, selection.id]);

  const recordingProofMode = selectedItem
    ? 'queue_dossier'
    : unroutedGlobalSummary.ready && unroutedResolutionSummary.present
      ? 'route_provenance'
      : 'pending';

  // Dossier focus id — drives the rich per-WorkItem panel rendered in the
  // right rail. Resolves to the selected queue row, the out-of-queue global
  // atlas selection, or null when only a cell or nothing is selected. The
  // hook handles cancellation on id changes so rapid clicks don't race.
  const dossierFocusId: string | null =
    selectedItem?.id ?? (globalSelectionOutsideQueue ? globalSelectedWorkItemId : null);
  const {
    dossier: focusDossier,
    loading: focusDossierLoading,
    error: focusDossierError,
  } = useWorkItemDossier(dossierFocusId);

  const handleSelect = (id: string) => {
    setSelectedId(id);
    onSelectedWorkItemChange?.(id, 'click');
  };

  return (
    <div
      data-zenith-intelligence-work={workSurfaceState}
      data-zenith-work-recording-proof={
        !loading && !error && !overviewWarming && recordingProofMode !== 'pending' ? 'ready' : 'pending'
      }
      data-zenith-work-recording-proof-mode={recordingProofMode}
      data-zenith-cockpit-version="v0_5"
      className="flex min-h-0 flex-1 flex-col gap-3"
    >
      <section className="rounded-[12px] border border-white/[0.08] bg-black/30 px-3 py-2">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/45">
          What this lens answers
        </div>
        <div className="mt-1 text-[12px] leading-5 text-white/82">
          What should Type A do next? Why is this item ranked first? What is
          blocked or stale? What just closed? Click a row to inspect its dossier.
          Mutation lives in <span className="font-mono">task_ledger_apply</span>{' '}
          quick-capture, not in this lens.
        </div>
      </section>
      <div className="grid min-h-0 flex-1 grid-cols-12 gap-3">
      <section className="col-span-12 flex min-h-0 flex-col gap-3 lg:col-span-7">
        {/* Atlas is the stage. The cartography universe is the primary visual;
            Work Ledger queue, current work strip, and operating-picture cards
            sit below as coordinated drilldowns, not as competing heroes. */}
        <div
          data-zenith-work-atlas-stage="hero"
          className="rounded-[14px] border border-white/[0.08] bg-black/30"
        >
          <WorkAtlas
            // Use the named global selection identity (not the queue-resolved
            // `selection.id`) so the Atlas keeps highlighting global marks that
            // live outside this Work Ledger queue slice.
            selectedWorkItemId={globalSelectedWorkItemId ?? selection.id}
            onSelectedWorkItemChange={(id) => handleSelect(id)}
            onPayloadLoaded={setCartographyPayload}
            queueIds={queueIds}
            selectedCell={selectedAtlasCell}
            onSelectedCellChange={setSelectedAtlasCell}
            neighborhoodHighlight={atlasNeighborhoodHighlight}
          />
        </div>

        {/* Operating picture + current work strip demoted to a compact side-by-
            side band below the Atlas. They retain their internal data-zenith
            attrs and ready signals; only visual weight changes. */}
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <WorkOperatingPicture
            projection={taskProjection}
            projectionLoading={projectionLoading}
            projectionError={projectionError}
            overview={overview}
            phaseId={phaseId}
            selectedSegmentId={selectedMassSegmentId}
            onSelectedSegmentChange={setSelectedMassSegmentId}
          />
          <CurrentWorkStrip
            projection={taskProjection}
            projectionLoading={projectionLoading}
            projectionError={projectionError}
          />
        </div>

        <section
          data-zenith-work-priority-queue="contained"
          className="flex max-h-[520px] min-h-[260px] flex-col rounded-[14px] border border-white/[0.08] bg-black/30 p-3"
        >
          <PanelSourceHeader
            title="priority queue · open by actor"
            kicker="work ledger"
            sourceLabel="/api/world-model/work-ledger/overview"
            schemaVersion="work_ledger_overview_v1"
            freshness={loading || overviewWarming ? 'backend warming' : `${allOpen.length} open`}
            freshnessTone={loading || overviewWarming ? 'loading' : 'ok'}
            claimBoundary="ranked by ledger order; not a productivity score"
            trailing={
              <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
                {phaseId ? `phase ${phaseId}` : ''}
                {familyId ? ` · family ${familyId}` : ''}
              </span>
            }
          />
          {error ? (
            <div className="mt-3 text-[12px] text-rose-200/80">error · {error}</div>
          ) : overviewWarming ? (
            <div className="mt-3 text-[12px] text-zenith-accent/80">
              backend warming · Work Ledger overview refresh is in flight
            </div>
          ) : loading ? (
            <div className="mt-3 text-[12px] text-white/45">loading work ledger overview…</div>
          ) : allOpen.length === 0 ? (
            <div className="mt-3 text-[12px] text-white/45">
              no open Work Ledger threads in this family projection
            </div>
          ) : (
            <>
              {overviewSliceDisclosure && (
                <div
                  className="mt-3 rounded border border-amber-300/20 bg-amber-300/[0.08] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/75"
                  data-zenith-work-overview-slice-disclosure="true"
                >
                  {overviewSliceDisclosure}
                </div>
              )}
              <ul
                data-zenith-work-priority-queue-list="scroll"
                className="mt-3 min-h-0 flex-1 divide-y divide-white/[0.04] overflow-y-auto overscroll-contain pr-1"
              >
                {allOpen.slice(0, 500).map((row) => {
                  const tone = stateTone(row.state);
                  const active = row.id === selection.id;
                  return (
                    <li key={row.id} data-zenith-work-queue-row-id={row.id}>
                      <button
                        type="button"
                        onClick={() => handleSelect(row.id)}
                        className={clsx(
                          'grid w-full grid-cols-[minmax(0,1fr)_72px_88px] items-center gap-2 px-2 py-2 text-left text-[12px] transition-colors',
                          active ? 'bg-white/[0.06]' : 'hover:bg-white/[0.03]',
                        )}
                      >
                        <div className="min-w-0">
                          <div className="truncate text-white/82">{row.title}</div>
                          <div className="mt-0.5 flex flex-wrap gap-1.5 font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/45">
                            <span>{row.id}</span>
                            {row.actor && <span>· {row.actor}</span>}
                            {row.family && <span>· {row.family}</span>}
                            {row.isStale && (
                              <span className="text-amber-200">· stale</span>
                            )}
                          </div>
                        </div>
                        <span className="text-right font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
                          {row.workItemType ?? '—'}
                        </span>
                        <span
                          className={clsx(
                            'rounded-full border px-2 py-0.5 text-center font-mono text-[9.5px] uppercase tracking-[0.14em]',
                            tone === 'ok'
                              ? 'border-emerald-300/30 text-emerald-100'
                              : tone === 'warn'
                                ? 'border-amber-300/30 text-amber-100'
                                : tone === 'block'
                                  ? 'border-rose-300/30 text-rose-100'
                                  : 'border-white/15 text-white/55',
                          )}
                        >
                          {row.state}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </section>
      </section>

      <aside className="col-span-12 flex min-h-0 flex-col gap-3 lg:col-span-5">
        {/* Selected dossier owns the top of the right rail (v0.2 directive:
            object-centric workbench — the selected object is the point). */}
        {(() => {
          // Right-rail single-inspector decision. Priority:
          //   1. Queue selection → queue dossier (object that lives in the
          //      active Work Ledger queue slice).
          //   2. Out-of-queue global selection → global mini-dossier sourced
          //      from atlas_marks, regardless of whether the cartography
          //      payload has resolved the mark yet (loading state shown).
          //   3. Atlas aggregate-cell selection → cell inspector.
          //   4. Otherwise → idle inspector.
          // Only ONE of these renders at a time; the bug fixed here is the
          // previous structure showing an idle "Select a work item" header
          // above an unrelated amber mini-dossier.
          const inspectorMode = selectedItem
            ? 'queue_dossier'
            : globalSelectionOutsideQueue
              ? 'global_mini_dossier'
              : selectedAtlasCell
                ? 'cell_inspector'
                : 'idle';
          const headerTitle =
            inspectorMode === 'queue_dossier'
              ? 'Selected work item'
              : inspectorMode === 'global_mini_dossier'
                ? 'Global Atlas selection'
                : inspectorMode === 'cell_inspector'
                  ? `Cell · ${selectedAtlasCell?.lane.replace(/_/g, ' ') ?? ''} × ${selectedAtlasCell?.state ?? ''}`
                  : 'Select a work item';
          const headerKicker =
            inspectorMode === 'cell_inspector'
              ? 'atlas cell · v0.1'
              : inspectorMode === 'global_mini_dossier'
                ? 'global inspector · v0.1'
                : 'dossier · v0.1';
          const headerFreshness =
            inspectorMode === 'queue_dossier'
              ? 'selected'
              : inspectorMode === 'global_mini_dossier'
                ? globalSelectedMark
                  ? 'global mark'
                  : 'resolving'
                : inspectorMode === 'cell_inspector'
                  ? `${cellInspectorMarks.length} marks`
                  : 'idle';
          const headerTone: 'ok' | 'warn' | 'loading' | 'neutral' =
            inspectorMode === 'queue_dossier'
              ? 'ok'
              : inspectorMode === 'global_mini_dossier'
                ? 'warn'
                : inspectorMode === 'cell_inspector'
                  ? 'ok'
                  : 'neutral';
          return (
        <>
        {/* Wave 2A — global unrouted summary. Always-visible right-rail
            section. Renders when the cartography payload reports any
            unrouted marks; gives the operator a one-glance histogram of
            the dominant route reasons without forcing a cell click. */}
        {unroutedGlobalSummary.ready && (
          <section
            data-zenith-work-unrouted-summary="ready"
            data-zenith-work-unrouted-summary-unrouted-total={
              unroutedGlobalSummary.unroutedTotal
            }
            data-zenith-work-unrouted-summary-explained-count={
              unroutedGlobalSummary.explainedCount
            }
            data-zenith-work-unrouted-summary-unknown-count={
              unroutedGlobalSummary.unknownCount
            }
            data-zenith-work-unrouted-summary-reason-count={
              unroutedGlobalSummary.distinctReasonCount
            }
            data-zenith-work-unrouted-summary-top-reason={
              unroutedGlobalSummary.ranked[0]?.reason ?? undefined
            }
            data-zenith-work-unrouted-summary-top-reason-count={
              unroutedGlobalSummary.ranked[0]?.count ?? undefined
            }
            className="rounded-[14px] border border-amber-300/25 bg-amber-300/[0.03] p-3"
          >
            <PanelSourceHeader
              title="Unrouted breakdown"
              kicker="route provenance · v0.2"
              sourceLabel="workitem_cartography_v1.atlas_marks.route_explanation"
              freshness={`${unroutedGlobalSummary.unroutedTotal} unrouted · ${unroutedGlobalSummary.explainedCount} explained · ${unroutedResolutionSummary.withRemedyCount}/${unroutedResolutionSummary.totalReasonCount} mapped to lane`}
              freshnessTone={
                unroutedResolutionSummary.withoutRemedyCount === 0 &&
                unroutedGlobalSummary.unknownCount === 0
                  ? 'ok'
                  : 'warn'
              }
              claimBoundary="reason taxonomy derived from existing diagnostic views; lane chips link to read-only Task Ledger surfaces; carryover not evaluated"
            />
            <div className="mt-2 grid gap-2">
              {unroutedGlobalSummary.ranked.slice(0, 6).map((row) => {
                const label = ROUTE_REASON_LABEL[row.reason] ?? row.reason;
                const code = ROUTE_REASON_SHORT_CODE[row.reason] ?? '??';
                const tone =
                  (row.kind &&
                    ROUTE_REASON_KIND_TONE[row.kind]) ||
                  ROUTE_REASON_KIND_TONE.actionable;
                const pct = (
                  (row.count / Math.max(1, unroutedGlobalSummary.unroutedTotal)) *
                  100
                ).toFixed(0);
                const affordance =
                  unroutedResolutionSummary.affordances[row.reason];
                const dispositionLabel =
                  RESOLUTION_DISPOSITION_LABEL[
                    affordance?.resolution_disposition ?? ''
                  ] ?? (affordance?.resolution_disposition ?? 'inspect');
                const statusTone =
                  RESOLUTION_STATUS_TONE[
                    affordance?.resolution_status ?? 'absent'
                  ];
                // Wave 2D — lane_relationship-aware chip language. The
                // prefix ("view" / "contains" / "partial" / "target" /
                // "benign" / "no lane") names HOW the owner_view relates
                // to the reason-id set, not just THAT a lane exists. The
                // backend measured this; we never imply membership.
                const relationship =
                  affordance?.lane_relationship ??
                  (affordance?.resolution_status === 'benign'
                    ? 'benign_no_remediation'
                    : 'fallback_no_owner_view');
                const relationshipPrefix =
                  LANE_RELATIONSHIP_PREFIX[relationship] ??
                  affordance?.lane_relationship_label ??
                  'no lane';
                const relationshipTone =
                  LANE_RELATIONSHIP_TONE[relationship] ??
                  LANE_RELATIONSHIP_TONE.fallback_no_owner_view;
                const overlapCount =
                  affordance?.owner_view_overlap_count ?? null;
                const ownerItemCount =
                  affordance?.owner_view_item_count ?? null;
                // Wave 2F — active row tracking. The summary row reflects
                // the URL-selected reason so the operator sees which row
                // the drillthrough panel is following. Click round-trips
                // through onSelectedRouteReasonChange (Intelligence.tsx
                // writes the URL param) so URL stays canonical.
                const isActiveRouteReason =
                  !!selectedRouteReasonFromUrl &&
                  selectedRouteReasonFromUrl === row.reason;
                const handleRowClick = () => {
                  if (!onSelectedRouteReasonChange) return;
                  onSelectedRouteReasonChange(
                    isActiveRouteReason ? null : row.reason,
                    'click',
                  );
                };
                return (
                  <div
                    key={`unrouted-summary:${row.reason}`}
                    className={
                      'grid grid-cols-[28px_minmax(0,1fr)_60px] items-start gap-2 rounded text-[11px] ' +
                      (isActiveRouteReason
                        ? 'border border-cyan-300/60 bg-cyan-300/[0.07] px-1 py-0.5'
                        : 'border border-transparent hover:bg-white/[0.03]') +
                      (onSelectedRouteReasonChange ? ' cursor-pointer' : '')
                    }
                    role={onSelectedRouteReasonChange ? 'button' : undefined}
                    tabIndex={onSelectedRouteReasonChange ? 0 : undefined}
                    onClick={onSelectedRouteReasonChange ? handleRowClick : undefined}
                    onKeyDown={
                      onSelectedRouteReasonChange
                        ? (e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              handleRowClick();
                            }
                          }
                        : undefined
                    }
                    data-zenith-work-unrouted-summary-row={row.reason}
                    data-zenith-work-unrouted-summary-row-route-reason={row.reason}
                    data-zenith-work-unrouted-summary-row-active={
                      isActiveRouteReason ? 'true' : undefined
                    }
                    data-zenith-work-unrouted-summary-row-resolution-status={
                      affordance?.resolution_status ?? 'absent'
                    }
                    data-zenith-work-unrouted-summary-row-resolution-disposition={
                      affordance?.resolution_disposition ?? 'inspect'
                    }
                    data-zenith-work-unrouted-summary-row-owner={
                      affordance?.owner_view ?? undefined
                    }
                    data-zenith-work-unrouted-summary-row-lane-relationship={
                      relationship
                    }
                    data-zenith-work-unrouted-summary-row-overlap-count={
                      overlapCount ?? undefined
                    }
                    data-zenith-work-unrouted-summary-row-owner-item-count={
                      ownerItemCount ?? undefined
                    }
                  >
                    <span
                      className="rounded px-1 py-0.5 text-center font-mono text-[10px] font-semibold"
                      style={{
                        backgroundColor: tone.fill,
                        color: tone.text,
                      }}
                    >
                      {code}
                    </span>
                    <div className="min-w-0">
                      <div className="truncate text-white/82">{label}</div>
                      <div className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/45">
                        {row.kind ?? 'actionable'}
                      </div>
                      {affordance && (
                        <div className="mt-1 flex flex-wrap items-center gap-1 font-mono text-[9.5px] uppercase tracking-[0.14em]">
                          <span
                            className="rounded px-1 py-0.5"
                            style={{
                              backgroundColor: statusTone.fill,
                              color: statusTone.text,
                            }}
                          >
                            {affordance.resolution_status}
                          </span>
                          <span className="text-white/60">
                            · {dispositionLabel}
                          </span>
                          <span
                            className="rounded px-1 py-0.5"
                            style={{
                              backgroundColor: relationshipTone.fill,
                              color: relationshipTone.text,
                            }}
                          >
                            {relationshipPrefix}
                            {affordance.owner_view
                              ? `: ${affordance.owner_view}`
                              : ''}
                          </span>
                          {affordance.owner_view &&
                            ownerItemCount !== null &&
                            overlapCount !== null && (
                              <span
                                className="text-white/40"
                                title={
                                  relationship === 'target_lane_not_current_member'
                                    ? `target lane: ${overlapCount}/${row.count} reason rows currently in ${affordance.owner_view}; owner view holds ${ownerItemCount} rows`
                                    : `${overlapCount}/${row.count} reason rows are in ${affordance.owner_view}; owner view holds ${ownerItemCount} rows`
                                }
                              >
                                · {overlapCount}/{row.count} in owner ·{' '}
                                {ownerItemCount} total
                              </span>
                            )}
                          {!affordance.owner_view &&
                            affordance.resolution_status === 'benign' && (
                              <span className="text-white/45">
                                · no remediation needed
                              </span>
                            )}
                        </div>
                      )}
                      {affordance?.next_action_label && (
                        <div
                          className="mt-0.5 truncate text-[10px] text-white/55"
                          title={affordance.mutation_lane_hint ?? undefined}
                        >
                          {affordance.next_action_label}
                        </div>
                      )}
                    </div>
                    <div className="text-right font-mono text-[10px] tabular-nums text-white/75">
                      {row.count}
                      <span className="ml-1 text-white/35">· {pct}%</span>
                    </div>
                  </div>
                );
              })}
              {unroutedGlobalSummary.ranked.length > 6 && (
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/40">
                  · {unroutedGlobalSummary.ranked.length - 6} more reasons
                </div>
              )}
            </div>
            {/* Wave 2D + 2F — read-only addressable drillthrough panel.
                The selected reason is URL-driven (route_reason query
                param) with fallback to the top reason from the
                histogram. Clicking a histogram row updates the URL via
                onSelectedRouteReasonChange so the drillthrough follows.
                Each sample row uses the backend-materialized card_route
                (Task Ledger card surface) and remains read-only:
                handleSelect refocuses the dossier; no mutation. */}
            {(() => {
              const rankedReasons = unroutedGlobalSummary.ranked.map((r) => r.reason);
              const urlSelected = (selectedRouteReasonFromUrl ?? '').trim();
              const urlSelectionValid =
                urlSelected !== '' && rankedReasons.includes(urlSelected);
              const drillReason =
                (urlSelectionValid ? urlSelected : null) ??
                rankedReasons[0] ??
                null;
              const drillSelectionSource: 'url' | 'default' = urlSelectionValid
                ? 'url'
                : 'default';
              if (!drillReason) return null;
              const drillAffordance =
                unroutedResolutionSummary.affordances[drillReason];
              if (!drillAffordance) return null;
              const drillRelationship =
                drillAffordance.lane_relationship ??
                (drillAffordance.resolution_status === 'benign'
                  ? 'benign_no_remediation'
                  : 'fallback_no_owner_view');
              const drillRelationshipTone =
                LANE_RELATIONSHIP_TONE[drillRelationship] ??
                LANE_RELATIONSHIP_TONE.fallback_no_owner_view;
              const drillPrefix =
                LANE_RELATIONSHIP_PREFIX[drillRelationship] ?? 'no lane';
              const drillMode = (() => {
                switch (drillRelationship) {
                  case 'exact_reason_view':
                    return 'exact';
                  case 'broad_owner_view_contains_reason_rows':
                    return 'broad';
                  case 'partial_owner_view_contains_some_reason_rows':
                    return 'partial';
                  case 'target_lane_not_current_member':
                    return 'target';
                  case 'benign_no_remediation':
                    return 'benign';
                  default:
                    return 'fallback';
                }
              })();
              const drillReasonCount = drillAffordance.primary_count ?? 0;
              const drillOverlap =
                drillAffordance.owner_view_overlap_count ?? null;
              const drillOwnerCount =
                drillAffordance.owner_view_item_count ?? null;
              // Wave 2F — prefer the backend-materialized drillthrough
              // block when present. Fall back to id-only samples for
              // v1 payloads predating Wave 2F.
              const drillBlock = drillAffordance.drillthrough;
              const materializedReasonRows = drillBlock?.reason_sample_rows ?? [];
              const materializedOverlapRows = drillBlock?.owner_overlap_rows ?? [];
              const allRoutesMaterialized =
                (materializedReasonRows.length > 0 ||
                  materializedOverlapRows.length > 0) &&
                [...materializedReasonRows, ...materializedOverlapRows].every(
                  (row) => row.route_materialized && Boolean(row.card_route),
                );
              const ownerSurfaceRoute =
                drillBlock?.owner_surface_route ??
                drillAffordance.option_surface_ref ??
                null;
              const reasonSampleIdsFallback = (
                drillAffordance.sample_ids ?? []
              ).slice(0, 3);
              const overlapSampleIdsFallback = (
                drillAffordance.owner_view_overlap_sample_ids ?? []
              ).slice(0, 3);
              return (
                <div
                  data-zenith-work-route-resolution-drillthrough="ready"
                  data-zenith-work-route-resolution-drillthrough-selection={drillSelectionSource}
                  data-zenith-work-route-resolution-drillthrough-reason={drillReason}
                  data-zenith-work-route-resolution-drillthrough-mode={drillMode}
                  data-zenith-work-route-resolution-drillthrough-relationship={
                    drillRelationship
                  }
                  data-zenith-work-route-resolution-drillthrough-owner={
                    drillAffordance.owner_view ?? undefined
                  }
                  data-zenith-work-route-resolution-drillthrough-overlap-count={
                    drillOverlap ?? undefined
                  }
                  data-zenith-work-route-resolution-drillthrough-owner-item-count={
                    drillOwnerCount ?? undefined
                  }
                  data-zenith-work-route-resolution-drillthrough-owner-surface={
                    ownerSurfaceRoute ? 'present' : 'none'
                  }
                  data-zenith-work-route-resolution-drillthrough-card-routes={
                    allRoutesMaterialized ? 'ready' : 'pending'
                  }
                  data-zenith-work-route-resolution-drillthrough-sample-count={
                    materializedReasonRows.length + materializedOverlapRows.length
                  }
                  className="mt-3 rounded-[10px] border border-cyan-300/20 bg-cyan-300/[0.03] p-2"
                >
                  <div className="mb-1 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-cyan-100/75">
                    <span>
                      drillthrough ·{' '}
                      {drillSelectionSource === 'url'
                        ? 'selected reason'
                        : 'top reason'}
                    </span>
                    <span
                      className="rounded px-1 py-0.5 normal-case tracking-normal"
                      style={{
                        backgroundColor: drillRelationshipTone.fill,
                        color: drillRelationshipTone.text,
                      }}
                    >
                      {drillPrefix}
                      {drillAffordance.owner_view
                        ? `: ${drillAffordance.owner_view}`
                        : ''}
                    </span>
                  </div>
                  <div className="text-[11px] text-white/80">
                    {ROUTE_REASON_LABEL[drillReason] ?? drillReason}
                  </div>
                  <dl className="mt-1 grid grid-cols-[120px_minmax(0,1fr)] gap-x-2 gap-y-0.5 font-mono text-[10px] tabular-nums text-white/70">
                    <dt className="text-white/45">reason count</dt>
                    <dd>{drillReasonCount}</dd>
                    {drillOwnerCount !== null && (
                      <>
                        <dt className="text-white/45">owner items</dt>
                        <dd>{drillOwnerCount}</dd>
                      </>
                    )}
                    {drillOverlap !== null && (
                      <>
                        <dt className="text-white/45">overlap</dt>
                        <dd>
                          {drillOverlap}/{drillReasonCount}
                          {drillRelationship ===
                            'target_lane_not_current_member' && (
                            <span className="ml-1 text-cyan-200/70">
                              · target lane · 0 current members expected
                            </span>
                          )}
                        </dd>
                      </>
                    )}
                    {drillAffordance.next_action_label && (
                      <>
                        <dt className="text-white/45">next action</dt>
                        <dd
                          title={
                            drillAffordance.mutation_lane_hint ?? undefined
                          }
                        >
                          {drillAffordance.next_action_label}
                        </dd>
                      </>
                    )}
                    {drillAffordance.mutation_policy && (
                      <>
                        <dt className="text-white/45">mutation policy</dt>
                        <dd className="text-white/55">
                          {drillAffordance.mutation_policy}
                        </dd>
                      </>
                    )}
                    {ownerSurfaceRoute && (
                      <>
                        <dt className="text-white/45">owner surface</dt>
                        <dd
                          className="truncate text-cyan-200/80"
                          title={ownerSurfaceRoute}
                        >
                          {ownerSurfaceRoute}
                        </dd>
                      </>
                    )}
                  </dl>
                  {materializedReasonRows.length > 0 && (
                    <div className="mt-2 grid gap-1">
                      <div className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/40">
                        reason samples · click to focus
                      </div>
                      {materializedReasonRows.map((row) => (
                        <button
                          key={`drill-reason:${row.id}`}
                          type="button"
                          onClick={() => handleSelect(row.id)}
                          data-zenith-work-route-resolution-drillthrough-sample={row.id}
                          data-zenith-work-route-resolution-drillthrough-sample-card-route={
                            row.card_route ? 'present' : 'missing'
                          }
                          data-zenith-work-route-resolution-drillthrough-sample-kind={
                            row.sample_kind
                          }
                          className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-baseline gap-2 text-left hover:bg-white/[0.03]"
                          title={row.card_route ?? undefined}
                        >
                          <span className="truncate text-[10.5px] text-cyan-200/80">
                            {row.title || row.id}
                          </span>
                          <span className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/35">
                            {row.id}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                  {materializedOverlapRows.length > 0 &&
                    drillRelationship !== 'target_lane_not_current_member' && (
                      <div className="mt-2 grid gap-1">
                        <div className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/40">
                          owner-view overlap samples
                        </div>
                        {materializedOverlapRows.map((row) => (
                          <button
                            key={`drill-owner:${row.id}`}
                            type="button"
                            onClick={() => handleSelect(row.id)}
                            data-zenith-work-route-resolution-drillthrough-overlap-sample={row.id}
                            data-zenith-work-route-resolution-drillthrough-sample-card-route={
                              row.card_route ? 'present' : 'missing'
                            }
                            data-zenith-work-route-resolution-drillthrough-sample-kind={
                              row.sample_kind
                            }
                            className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-baseline gap-2 text-left hover:bg-white/[0.03]"
                            title={row.card_route ?? undefined}
                          >
                            <span className="truncate text-[10.5px] text-emerald-200/80">
                              {row.title || row.id}
                            </span>
                            <span className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/35">
                              {row.id}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  {materializedReasonRows.length === 0 &&
                    reasonSampleIdsFallback.length > 0 && (
                      <div className="mt-2 grid gap-1">
                        <div className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/40">
                          reason samples (legacy · routes unmaterialized)
                        </div>
                        {reasonSampleIdsFallback.map((sid) => (
                          <button
                            key={`drill-reason-fallback:${sid}`}
                            type="button"
                            onClick={() => handleSelect(sid)}
                            data-zenith-work-route-resolution-drillthrough-sample={sid}
                            data-zenith-work-route-resolution-drillthrough-sample-card-route="missing"
                            data-zenith-work-route-resolution-drillthrough-sample-kind="reason_sample"
                            className="block w-full truncate text-left font-mono text-[10px] text-cyan-200/70 hover:text-cyan-100"
                          >
                            · {sid}
                          </button>
                        ))}
                      </div>
                    )}
                  {materializedOverlapRows.length === 0 &&
                    overlapSampleIdsFallback.length > 0 &&
                    drillRelationship !== 'target_lane_not_current_member' && (
                      <div className="mt-2 grid gap-1">
                        <div className="font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/40">
                          owner-view overlap samples (legacy · routes unmaterialized)
                        </div>
                        {overlapSampleIdsFallback.map((sid) => (
                          <button
                            key={`drill-owner-fallback:${sid}`}
                            type="button"
                            onClick={() => handleSelect(sid)}
                            data-zenith-work-route-resolution-drillthrough-overlap-sample={sid}
                            data-zenith-work-route-resolution-drillthrough-sample-card-route="missing"
                            data-zenith-work-route-resolution-drillthrough-sample-kind="owner_overlap_sample"
                            className="block w-full truncate text-left font-mono text-[10px] text-emerald-200/70 hover:text-emerald-100"
                          >
                            · {sid}
                          </button>
                        ))}
                      </div>
                    )}
                </div>
              );
            })()}
            <div
              className="mt-2 rounded border border-white/[0.06] bg-black/30 px-2 py-1 font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/45"
              data-zenith-work-carryover-disclosure="not_evaluated"
            >
              carryover not evaluated — origin/current scope unavailable
            </div>
          </section>
        )}
        <section
          data-zenith-work-selected={selectedItem ? 'present' : 'idle'}
          data-zenith-work-inspector={inspectorMode}
          className={clsx(
            'rounded-[14px] border p-3 transition-colors',
            inspectorMode === 'queue_dossier'
              ? 'border-emerald-300/25 bg-emerald-300/[0.04]'
              : inspectorMode === 'global_mini_dossier'
                ? 'border-amber-300/30 bg-amber-300/[0.05]'
                : inspectorMode === 'cell_inspector'
                  ? 'border-cyan-300/25 bg-cyan-300/[0.04]'
                  : 'border-white/[0.08] bg-black/30',
          )}
        >
          <PanelSourceHeader
            title={headerTitle}
            kicker={headerKicker}
            sourceLabel={
              inspectorMode === 'cell_inspector'
                ? 'workitem_cartography_v0.atlas_marks (cell slice)'
                : inspectorMode === 'global_mini_dossier'
                  ? 'workitem_cartography_v0.atlas_marks'
                  : 'open_by_actor row + worldModel.orchestration.work_spine'
            }
            freshness={headerFreshness}
            freshnessTone={headerTone}
            claimBoundary={
              inspectorMode === 'queue_dossier'
                ? 'observation only — mutation lives in task_ledger_apply'
                : inspectorMode === 'global_mini_dossier'
                  ? 'observation only — full neighborhood graph deferred to Wave 1C+'
                  : inspectorMode === 'cell_inspector'
                    ? 'top marks by downstream unlock count; click to inspect'
                    : null
            }
          />
          {inspectorMode === 'global_mini_dossier' && (
            <div
              data-zenith-work-global-selection-outside-queue="ready"
              data-zenith-work-global-selection-id={
                globalSelectedWorkItemId ?? undefined
              }
              data-zenith-work-mini-dossier={
                globalSelectedMark ? 'present' : 'pending'
              }
              data-zenith-work-mini-dossier-id={
                globalSelectedMark?.id ?? undefined
              }
              className="mt-2 rounded-[10px] border border-amber-300/25 bg-amber-300/[0.05] p-3"
            >
              <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-amber-200">
                <span className="rounded-full border border-amber-300/40 bg-amber-300/[0.07] px-1.5 py-0.5">
                  outside queue
                </span>
                <span>· atlas selection</span>
              </div>
              {globalSelectedMark ? (
                <div className="mt-2 grid gap-1.5">
                  <div className="text-[13px] leading-5 text-amber-50">
                    {globalSelectedMark.title || globalSelectedMark.id}
                  </div>
                  <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-200/70">
                    {globalSelectedMark.id}
                  </div>
                  <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1 text-[10.5px] uppercase tracking-[0.14em] text-amber-200/80">
                    <span>
                      state ·{' '}
                      <span className="font-mono normal-case tracking-normal text-amber-50">
                        {globalSelectedMark.state ?? 'unknown'}
                      </span>
                    </span>
                    <span>
                      type ·{' '}
                      <span className="font-mono normal-case tracking-normal text-amber-50">
                        {globalSelectedMark.work_item_type ?? 'unknown'}
                      </span>
                    </span>
                    <span>
                      actor ·{' '}
                      <span className="font-mono normal-case tracking-normal text-amber-50">
                        {globalSelectedMark.actor ?? 'unassigned'}
                      </span>
                    </span>
                    <span>
                      family ·{' '}
                      <span className="font-mono normal-case tracking-normal text-amber-50">
                        {globalSelectedMark.family ?? 'unknown'}
                      </span>
                    </span>
                    <span>
                      route ·{' '}
                      <span className="font-mono normal-case tracking-normal text-amber-50">
                        {globalSelectedMark.route?.status ?? 'unknown'}
                      </span>
                    </span>
                    <span>
                      unlocks ·{' '}
                      <span className="font-mono normal-case tracking-normal text-amber-50">
                        {globalSelectedMark.edge_summary?.downstream_unlock_count ?? 0}
                      </span>
                    </span>
                  </div>
                  {(globalSelectedMark.overlays?.unrouted ||
                    globalSelectedMark.overlays?.blocked ||
                    globalSelectedMark.overlays?.stale ||
                    globalSelectedMark.overlays?.signoff_required ||
                    globalSelectedMark.overlays?.high_unlock) && (
                    <div className="mt-1 flex flex-wrap gap-1 font-mono text-[9.5px] uppercase tracking-[0.14em]">
                      {globalSelectedMark.overlays?.unrouted && (
                        <span className="rounded-full border border-amber-300/40 px-1.5 py-0.5 text-amber-100">
                          unrouted
                        </span>
                      )}
                      {globalSelectedMark.overlays?.blocked && (
                        <span className="rounded-full border border-rose-300/40 px-1.5 py-0.5 text-rose-100">
                          blocked
                        </span>
                      )}
                      {globalSelectedMark.overlays?.stale && (
                        <span className="rounded-full border border-amber-300/40 px-1.5 py-0.5 text-amber-100">
                          stale
                        </span>
                      )}
                      {globalSelectedMark.overlays?.signoff_required && (
                        <span className="rounded-full border border-cyan-300/40 px-1.5 py-0.5 text-cyan-100">
                          signoff required
                        </span>
                      )}
                      {globalSelectedMark.overlays?.high_unlock && (
                        <span className="rounded-full border border-emerald-300/40 px-1.5 py-0.5 text-emerald-100">
                          high unlock
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="mt-2 font-mono text-[10px] tracking-[0.14em] text-amber-200/70">
                  global mark not mirrored yet · {globalSelectedWorkItemId}
                </div>
              )}
              <div className="mt-2 text-[10.5px] leading-5 text-amber-100/70">
                Not present in this Work Ledger queue slice — global atlas
                selection. Rich dossier loads from the typed ledger below.
              </div>
              {/* Rich per-WorkItem dossier for out-of-queue global atlas
                  selections. Same backend route; the panel handles 404 /
                  unavailable gracefully when an atlas mark predates ledger
                  presence. */}
              <WorkItemDossierPanel
                dossier={focusDossier}
                loading={focusDossierLoading}
                error={focusDossierError}
                workItemId={globalSelectedWorkItemId}
              />
            </div>
          )}
          {inspectorMode === 'queue_dossier' && selectedItem && (
            <div className="mt-2 grid gap-2">
              <div className="text-[13px] leading-5 text-white">{selectedItem.title}</div>
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
                {selectedItem.id}
              </div>
              <div className="flex flex-wrap gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
                <span className="rounded-full border border-white/[0.08] bg-white/[0.03] px-2 py-0.5">
                  selection · {selectionSourceLabel(selection.source)}
                </span>
                {selection.reason && (
                  <span className="min-w-0 break-words rounded-[8px] border border-amber-300/25 bg-amber-300/[0.06] px-2 py-0.5 normal-case tracking-normal text-amber-100">
                    {selection.reason}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px] leading-5 text-white/72">
                <DossierField label="state" value={selectedItem.state} tone={stateTone(selectedItem.state)} />
                <DossierField
                  label="type"
                  value={selectedItem.workItemType ?? '—'}
                />
                <DossierField
                  label="actor"
                  value={selectedItem.actor ?? 'unassigned'}
                />
                <DossierField
                  label="family"
                  value={selectedItem.family ?? '—'}
                />
                <DossierField
                  label="stale"
                  value={selectedItem.isStale ? 'yes · stale_open' : 'no'}
                  tone={selectedItem.isStale ? 'warn' : 'neutral'}
                />
                <DossierField
                  label="priority signal"
                  value="display order · open_by_actor (no backend rank)"
                />
              </div>
              <div className="rounded-[10px] border border-white/[0.06] bg-black/30 p-2 font-mono text-[10px] uppercase tracking-[0.14em] text-white/40">
                drilldown · ./repo-python kernel.py --option-surface task_ledger --band card --ids {selectedItem.id}
              </div>
              {/* Rich per-WorkItem dossier — narrative, why-now, execution
                  receipt, satisfaction/integration contracts, source-view
                  membership, recent-event timeline. Backed by
                  /api/world-model/task-ledger/dossier/{id}. */}
              <WorkItemDossierPanel
                dossier={focusDossier}
                loading={focusDossierLoading}
                error={focusDossierError}
                workItemId={selectedItem.id}
              />
            </div>
          )}
          {inspectorMode === 'cell_inspector' && selectedAtlasCell && (
            <div
              data-zenith-work-cell-inspector="present"
              data-zenith-work-cell-inspector-lane={selectedAtlasCell.lane}
              data-zenith-work-cell-inspector-state={selectedAtlasCell.state}
              className="mt-2 grid gap-2"
            >
              <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-cyan-200">
                <span className="rounded-full border border-cyan-300/40 bg-cyan-300/[0.07] px-1.5 py-0.5">
                  atlas cell
                </span>
                <span>
                  · {selectedAtlasCell.lane.replace(/_/g, ' ')} × {selectedAtlasCell.state}
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedAtlasCell(null)}
                  className="ml-auto rounded-full border border-white/15 px-2 py-0.5 text-white/55 hover:border-white/30 hover:text-white/85"
                >
                  clear
                </button>
              </div>
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-cyan-200/70">
                {cellInspectorMarks.length} marks · top by downstream unlocks
              </div>
              {cellInspectorMarks.length === 0 ? (
                <div className="text-[11px] leading-5 text-white/55">
                  no marks in this cell — empty cells are kept on the lattice so
                  the operability axis stays legible.
                </div>
              ) : (
                <ul className="divide-y divide-white/[0.05]">
                  {cellInspectorMarks.slice(0, 8).map((mark) => (
                    <li key={mark.id}>
                      <button
                        type="button"
                        onClick={() => handleSelect(mark.id)}
                        className="grid w-full grid-cols-[minmax(0,1fr)_64px] items-center gap-2 px-1 py-1.5 text-left text-[11.5px] hover:bg-white/[0.04]"
                      >
                        <div className="min-w-0">
                          <div className="truncate text-white/82">
                            {mark.title || mark.id}
                          </div>
                          <div className="mt-0.5 flex flex-wrap gap-1.5 font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/45">
                            <span>{mark.id}</span>
                            {mark.work_item_type && <span>· {mark.work_item_type}</span>}
                            {mark.actor && <span>· {mark.actor}</span>}
                          </div>
                        </div>
                        <span className="text-right font-mono text-[10px] uppercase tracking-[0.14em] text-cyan-100">
                          {mark.edge_summary?.downstream_unlock_count ?? 0} ▲
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {cellInspectorMarks.length > 8 && (
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/40">
                  · {cellInspectorMarks.length - 8} more not shown (Wave 1D+
                  scroll/pagination)
                </div>
              )}
            </div>
          )}
          {inspectorMode === 'idle' && (
            <div className="mt-2 text-[11px] leading-5 text-white/55">
              Click an Atlas cell to inspect its marks, or a priority-queue row
              for the queue dossier. URL-token global selections show their
              mini-dossier here automatically.
            </div>
          )}
          {/* Wave 1E — Neighborhood inspector. Renders below the dossier body
              when the active inspector has a single-object focus. Cell
              inspector and idle have no single focus, so nothing renders. */}
          {(inspectorMode === 'queue_dossier' || inspectorMode === 'global_mini_dossier') && (
            <NeighborhoodInspector
              payload={cartographyPayload}
              focusWorkItemId={
                inspectorMode === 'queue_dossier'
                  ? selectedItem?.id ?? null
                  : globalSelectedMark?.id ?? null
              }
              onSelectNeighbor={(id) => handleSelect(id)}
              onNeighborhoodLoaded={setSelectedNeighborhood}
            />
          )}
          {/* Wave 2A — per-cell unrouted breakdown. Renders only when the
              cell inspector is active AND the cell contains unrouted marks;
              shows the route_reason histogram inside the cell with one
              example mark per reason. Carryover disclosure is reiterated
              here so the operator sees it adjacent to the per-cell rows. */}
          {inspectorMode === 'cell_inspector' &&
            selectedAtlasCell &&
            cellInspectorRouteBreakdown.ready && (
              <div
                data-zenith-work-unrouted-breakdown="ready"
                data-zenith-work-unrouted-breakdown-cell={`${selectedAtlasCell.lane}|${selectedAtlasCell.state}`}
                data-zenith-work-unrouted-breakdown-cell-unrouted-count={
                  cellInspectorRouteBreakdown.cellUnroutedCount
                }
                data-zenith-work-unrouted-breakdown-reason-count={
                  cellInspectorRouteBreakdown.ranked.length
                }
                data-zenith-work-unrouted-breakdown-top-reason={
                  cellInspectorRouteBreakdown.ranked[0]?.reason ?? undefined
                }
                data-zenith-work-unrouted-breakdown-top-reason-count={
                  cellInspectorRouteBreakdown.ranked[0]?.count ?? undefined
                }
                className="mt-3 rounded-[10px] border border-amber-300/25 bg-amber-300/[0.03] p-2"
              >
                <div className="mb-1 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/75">
                  <span>route reason · cell breakdown</span>
                  <span className="text-amber-100/55">
                    {cellInspectorRouteBreakdown.cellUnroutedCount} unrouted in
                    cell
                  </span>
                </div>
                <ul className="grid gap-1">
                  {cellInspectorRouteBreakdown.ranked.slice(0, 5).map((row) => {
                    const label = ROUTE_REASON_LABEL[row.reason] ?? row.reason;
                    const code = ROUTE_REASON_SHORT_CODE[row.reason] ?? '??';
                    const tone =
                      (row.kind && ROUTE_REASON_KIND_TONE[row.kind]) ||
                      ROUTE_REASON_KIND_TONE.actionable;
                    const affordance =
                      unroutedResolutionSummary.affordances[row.reason];
                    const cellRelationship =
                      affordance?.lane_relationship ??
                      (affordance?.resolution_status === 'benign'
                        ? 'benign_no_remediation'
                        : 'fallback_no_owner_view');
                    const cellRelationshipPrefix =
                      LANE_RELATIONSHIP_PREFIX[cellRelationship] ??
                      affordance?.lane_relationship_label ??
                      'no lane';
                    const cellRelationshipTone =
                      LANE_RELATIONSHIP_TONE[cellRelationship] ??
                      LANE_RELATIONSHIP_TONE.fallback_no_owner_view;
                    return (
                      <li
                        key={`cell-breakdown:${row.reason}`}
                        data-zenith-work-unrouted-breakdown-row={row.reason}
                        data-zenith-work-unrouted-breakdown-row-resolution-status={
                          affordance?.resolution_status ?? 'absent'
                        }
                        data-zenith-work-unrouted-breakdown-row-owner={
                          affordance?.owner_view ?? undefined
                        }
                        data-zenith-work-unrouted-breakdown-row-lane-relationship={
                          cellRelationship
                        }
                        className="grid grid-cols-[28px_minmax(0,1fr)_36px] items-start gap-2 text-[11px]"
                      >
                        <span
                          className="rounded px-1 py-0.5 text-center font-mono text-[10px] font-semibold"
                          style={{
                            backgroundColor: tone.fill,
                            color: tone.text,
                          }}
                        >
                          {code}
                        </span>
                        <div className="min-w-0">
                          <div className="truncate text-white/82">{label}</div>
                          {affordance && (
                            <div className="flex flex-wrap items-center gap-1 font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/55">
                              <span>
                                {RESOLUTION_DISPOSITION_LABEL[
                                  affordance.resolution_disposition
                                ] ?? affordance.resolution_disposition}
                              </span>
                              <span
                                className="rounded px-1 py-0.5"
                                style={{
                                  backgroundColor: cellRelationshipTone.fill,
                                  color: cellRelationshipTone.text,
                                }}
                              >
                                {cellRelationshipPrefix}
                                {affordance.owner_view
                                  ? `: ${affordance.owner_view}`
                                  : ''}
                              </span>
                            </div>
                          )}
                          {row.exampleId && (
                            <button
                              type="button"
                              onClick={() => handleSelect(row.exampleId!)}
                              className="block w-full truncate text-left font-mono text-[9.5px] uppercase tracking-[0.14em] text-cyan-200/60 hover:text-cyan-100"
                            >
                              · {row.exampleId}
                            </button>
                          )}
                        </div>
                        <div className="text-right font-mono text-[10px] text-white/75">
                          {row.count}
                        </div>
                      </li>
                    );
                  })}
                </ul>
                {cellInspectorRouteBreakdown.ranked.length > 5 && (
                  <div className="mt-1 font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/40">
                    · {cellInspectorRouteBreakdown.ranked.length - 5} more
                    reasons
                  </div>
                )}
                <div
                  className="mt-2 rounded border border-white/[0.06] bg-black/30 px-2 py-1 font-mono text-[9.5px] uppercase tracking-[0.14em] text-white/45"
                  data-zenith-work-carryover-disclosure="not_evaluated"
                >
                  carryover not evaluated — origin/current scope unavailable
                </div>
              </div>
            )}
        </section>
        </>
          );
        })()}

        <section className="rounded-[14px] border border-white/[0.08] bg-black/30 p-3">
          <PanelSourceHeader
            title="clusters · by state"
            kicker="work ledger"
            sourceLabel="work_ledger_overview.open_by_actor"
            freshness={loading ? 'loading' : 'live'}
            freshnessTone={loading ? 'loading' : 'ok'}
            claimBoundary="state names are ledger fields, not invented heuristics"
          />
          {clustersByState.length === 0 ? (
            <div className="mt-3 text-[11px] leading-5 text-white/45">
              no state buckets in this scope
            </div>
          ) : (
            <div className="mt-3 grid grid-cols-2 gap-2">
              {clustersByState.slice(0, 8).map(([state, count]) => (
                <ClusterChip key={`state:${state}`} label={state} count={count} />
              ))}
            </div>
          )}
        </section>

        <section className="rounded-[14px] border border-white/[0.08] bg-black/30 p-3">
          <PanelSourceHeader
            title="clusters · by actor"
            kicker="work ledger"
            sourceLabel="work_ledger_overview.open_by_actor"
            freshness={loading ? 'loading' : 'live'}
            freshnessTone={loading ? 'loading' : 'ok'}
          />
          {clustersByActor.length === 0 ? (
            <div className="mt-3 text-[11px] leading-5 text-white/45">
              no actor buckets in this scope
            </div>
          ) : (
            <div className="mt-3 grid grid-cols-2 gap-2">
              {clustersByActor.slice(0, 6).map(([actor, count]) => (
                <ClusterChip key={`actor:${actor}`} label={actor} count={count} />
              ))}
            </div>
          )}
        </section>

        {recentlyClosed.length > 0 && (
          <section className="rounded-[14px] border border-white/[0.08] bg-black/30 p-3">
            <PanelSourceHeader
              title="recently closed"
              kicker="work ledger"
              sourceLabel="work_ledger_overview.recently_closed"
              freshness={`${recentlyClosed.length} entries`}
              freshnessTone="ok"
            />
            <ul className="mt-2 divide-y divide-white/[0.04]">
              {recentlyClosed.slice(0, 6).map((row) => (
                <li key={`closed:${row.id}`} className="px-1 py-1.5">
                  <div className="truncate text-[12px] text-white/72">{row.title}</div>
                  <div className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-white/40">
                    {row.id} · {row.state}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {handoffCandidates.length > 0 && (
          <section className="rounded-[14px] border border-white/[0.08] bg-black/30 p-3">
            <PanelSourceHeader
              title="handoff candidates"
              kicker="work ledger"
              sourceLabel="work_ledger_overview.handoff_candidates"
              freshness={`${handoffCandidates.length} candidates`}
              freshnessTone="warn"
              claimBoundary="cross-agent handoff suggestions; not auto-assignment"
            />
            <ul className="mt-2 divide-y divide-white/[0.04]">
              {handoffCandidates.slice(0, 6).map((row) => (
                <li key={`handoff:${row.id}`} className="px-1 py-1.5">
                  <div className="truncate text-[12px] text-white/72">{row.title}</div>
                  <div className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-white/40">
                    {row.id} · {row.actor ?? 'unassigned'}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {counts && (
          <section className="rounded-[14px] border border-white/[0.08] bg-black/30 p-3 text-[11px] leading-5 text-white/55">
            <PanelSourceHeader
              title="ledger counts"
              sourceLabel="work_ledger_overview.counts"
              freshness="live"
              freshnessTone="ok"
            />
            <pre className="mt-2 overflow-auto rounded-[10px] border border-white/[0.05] bg-black/30 px-2 py-1.5 font-mono text-[10px] leading-4 text-white/72">
              {JSON.stringify(counts, null, 2)}
            </pre>
          </section>
        )}
      </aside>
      </div>
    </div>
  );
}
