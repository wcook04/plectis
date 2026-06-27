// [PURPOSE] Work Atlas — hero lattice over the WorkItem cartography packet.
//
// Wave 1B. Consumes /api/world-model/task-ledger/cartography/workitem
// (workitem_cartography_v0) and renders one mark per WorkItem on a
// lifecycle x grouping lattice. The Atlas is observation-only: marks are
// clickable and update the existing URL `object=work_item:<id>` pipeline,
// but no mutation lives here.
//
// Honesty rules enforced by the renderer:
//   - `atlas_marks_ready` gates the lattice render. If false, show
//     consumer notes / unavailable banner instead.
//   - `overview_complete === false` is EXPECTED (graph layer is bounded).
//     It does NOT block the lattice; surface as a small hint instead.
//   - `carryover_label_absent` must be true. Refuse to render any
//     `carryover` overlay even if the legend somehow advertises one.
//   - `unrouted_overlay_present` must be true. Mark `route.status==unknown`
//     items via the `unrouted` overlay glyph.
//
// Rendering choice: pure SVG, not ReactFlow. The cap_cartography graph
// renderer already uses ReactFlow for ~96 cap nodes; that layout flips to
// summary mode at >=250 nodes / >=400 edges. The Atlas universe is ~2k
// marks; SVG with deterministic packing keeps it readable and avoids the
// auto-layout summary fallback.
//
// Wave 1B explicitly skips:
//   - selected-object neighborhood graph (Wave 1C)
//   - Carryover Bridge (Wave 2; needs origin_phase substrate first)
//   - Metabolism River (Wave 3)
//   - actor/family/route_status grouping toggles (planned, not v0)
//   - canvas/WebGL fallback (only if SVG profiling fails)

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  api,
  type TaskLedgerCartographyAtlasMark,
  type TaskLedgerCartographyPayloadResponse,
} from '../../api';
import PanelSourceHeader from './PanelSourceHeader';
import {
  ROUTE_REASON_KIND_TONE,
  ROUTE_REASON_LABEL,
  ROUTE_REASON_SHORT_CODE,
} from './routeReasonVocab';

interface WorkAtlasProps {
  selectedWorkItemId?: string | null;
  onSelectedWorkItemChange?: (id: string, source: 'click') => void;
  // Optional callback fired once the cartography payload is fetched. Lets a
  // parent lens (e.g. WorkLens) read atlas_marks for a global mini-dossier
  // without re-issuing the cartography fetch. Pure observation; renderer
  // remains the owner of payload state.
  onPayloadLoaded?: (payload: TaskLedgerCartographyPayloadResponse) => void;
  // WorkItem ids that are currently visible in the active Work Ledger queue
  // slice. Used to derive the `queue_visible` operability lane vs the global-
  // open / unrouted / terminal lanes. Default to an empty set if the parent
  // has not yet loaded its queue.
  queueIds?: ReadonlySet<string>;
  // Selected aggregate cell (lane × state). Controlled by parent so a single
  // right-rail inspector can render the cell summary alongside the queue
  // dossier and global mini-dossier inspectors.
  selectedCell?: AtlasCellId | null;
  onSelectedCellChange?: (cell: AtlasCellId | null) => void;
  // Wave 1G — coordinated neighborhood highlight. When the right-rail
  // inspector has fetched a per-WorkItem neighborhood, the parent passes
  // the focus + upstream + downstream id sets so the Atlas can show
  // per-cell badges (D=depends_on count in cell, U=unlocks count in
  // cell) and outline the focus cell. Pure read; the Atlas does not
  // fetch the neighborhood itself.
  neighborhoodHighlight?: {
    focusId: string;
    upstreamIds: ReadonlySet<string>;
    downstreamIds: ReadonlySet<string>;
  } | null;
}

const LIFECYCLE_STATES: readonly string[] = [
  'captured',
  'shaping',
  'shaped',
  'execution',
  'signoff',
  'done',
  'propagated',
  'retired',
];

const STATE_TONE: Record<string, { fill: string; stroke: string }> = {
  captured: { fill: '#3a3320', stroke: '#c7b06a' },
  shaping: { fill: '#3b3622', stroke: '#d4c275' },
  shaped: { fill: '#3b3622', stroke: '#d4c275' },
  execution: { fill: '#1f3a26', stroke: '#7bc78e' },
  signoff: { fill: '#1f3a26', stroke: '#7bc78e' },
  done: { fill: '#1a3a1a', stroke: '#5fb872' },
  propagated: { fill: '#1a3a1a', stroke: '#5fb872' },
  retired: { fill: '#2a2a2a', stroke: '#777' },
  blocked: { fill: '#3a1f1f', stroke: '#e57373' },
  unknown: { fill: '#1f1f1f', stroke: '#555' },
};

const MARK_SIZE_PX = 5;
const MARK_GAP_PX = 1.5;
const CELL_PADDING_PX = 6;
const CELL_LABEL_HEIGHT_PX = 18;
const ROW_LABEL_WIDTH_PX = 130;
const COL_LABEL_HEIGHT_PX = 22;
const MARK_HALO_STROKE = 1.25;

function toneFor(state: string | undefined): { fill: string; stroke: string } {
  if (!state) return STATE_TONE.unknown;
  return STATE_TONE[state] ?? STATE_TONE.unknown;
}

function compactCount(value: number | null | undefined): string {
  const count = typeof value === 'number' && Number.isFinite(value) ? value : 0;
  if (count >= 1000) return `${(count / 1000).toFixed(count >= 10000 ? 0 : 1)}k`;
  return String(count);
}

function columnOrder(): string[] {
  return [...LIFECYCLE_STATES, 'other'];
}

// Operability lanes (default Y-axis for Wave 1C.5 semantic Atlas).
// Order encodes triage precedence: most actionable on top, most archived at
// the bottom. Lane assignment is `deriveLane` and is winner-take-first: a
// mark lands in the first lane whose predicate matches.
const OPERABILITY_LANES: readonly string[] = [
  'queue_visible',
  'blocked',
  'stale',
  'signoff_required',
  'high_unlock',
  'unrouted',
  'global_open',
  'terminal',
  'unknown',
] as const;

type OperabilityLane = (typeof OPERABILITY_LANES)[number];

const LANE_LABEL: Record<OperabilityLane, string> = {
  queue_visible: 'queue visible',
  blocked: 'blocked',
  stale: 'stale',
  signoff_required: 'signoff required',
  high_unlock: 'high unlock',
  unrouted: 'unrouted',
  global_open: 'global open',
  terminal: 'done · propagated · retired',
  unknown: 'unknown',
};

const TERMINAL_STATES = new Set(['done', 'propagated', 'retired']);

function isQueueVisible(
  mark: TaskLedgerCartographyAtlasMark,
  queueIds: ReadonlySet<string>,
): boolean {
  // Forward-compatible: prefer a backend-stamped overlay flag if the
  // cartography projection has been upgraded to join Work Ledger queue
  // membership (substrate gap captured separately). Until then, fall back
  // to id-set membership — which only matches when atlas_mark.id and
  // Work Ledger row.id share a namespace, an invariant the current
  // substrate does NOT hold (atlas_marks use cap_*/descriptive ids, Work
  // Ledger uses td_*).
  const overlayQueueVisible = (mark.overlays as Record<string, unknown> | undefined)
    ?.queue_visible;
  if (overlayQueueVisible === true) return true;
  return queueIds.has(mark.id);
}

function deriveLane(
  mark: TaskLedgerCartographyAtlasMark,
  queueIds: ReadonlySet<string>,
): OperabilityLane {
  if (isQueueVisible(mark, queueIds)) return 'queue_visible';
  const o = mark.overlays ?? {};
  if (o.blocked) return 'blocked';
  if (o.stale) return 'stale';
  if (o.signoff_required) return 'signoff_required';
  if (o.high_unlock) return 'high_unlock';
  if (o.unrouted) return 'unrouted';
  const state = mark.state ?? 'unknown';
  if (TERMINAL_STATES.has(state)) return 'terminal';
  if (state === 'unknown') return 'unknown';
  return 'global_open';
}

type AtlasFilterMode =
  | 'all'
  | 'unfinished'
  | 'unrouted'
  | 'blocked'
  | 'signoff';

const FILTER_LABEL: Record<AtlasFilterMode, string> = {
  all: 'all',
  unfinished: 'unfinished',
  unrouted: 'unrouted',
  blocked: 'blocked',
  signoff: 'signoff',
};

function passesFilter(
  mark: TaskLedgerCartographyAtlasMark,
  mode: AtlasFilterMode,
): boolean {
  const o = mark.overlays ?? {};
  switch (mode) {
    case 'all':
      return true;
    case 'unfinished':
      return !TERMINAL_STATES.has(mark.state ?? 'unknown');
    case 'unrouted':
      return Boolean(o.unrouted);
    case 'blocked':
      return Boolean(o.blocked);
    case 'signoff':
      return Boolean(o.signoff_required);
  }
}

type AtlasRenderMode = 'aggregate' | 'marks';

interface CellAggregate {
  lane: OperabilityLane;
  state: string;
  count: number;
  dominantType: string | null;
  overlays: {
    unrouted: number;
    blocked: number;
    stale: number;
    signoff_required: number;
    high_unlock: number;
  };
  topMark: TaskLedgerCartographyAtlasMark | null;
  // Wave 2A — route provenance per cell. Histogram over primary
  // route_reason keys for marks where overlays.unrouted is true. topReason
  // is null when the cell contains zero unrouted marks; the badge renders
  // only when topReason is non-null AND topReasonCount > 0.
  routeReasonHistogram: Record<string, number>;
  topReason: string | null;
  topReasonCount: number;
  topReasonKind: string | null;
}

// Wave 2A vocabulary lives in routeReasonVocab.ts so both this file and
// WorkLens.tsx can import without violating the fast-refresh constraint.

function bucketByLaneAndState(
  marks: ReadonlyArray<TaskLedgerCartographyAtlasMark>,
  queueIds: ReadonlySet<string>,
): Map<OperabilityLane, Map<string, TaskLedgerCartographyAtlasMark[]>> {
  const buckets = new Map<OperabilityLane, Map<string, TaskLedgerCartographyAtlasMark[]>>();
  for (const lane of OPERABILITY_LANES) {
    buckets.set(lane, new Map());
  }
  for (const mark of marks) {
    const lane = deriveLane(mark, queueIds);
    const state = LIFECYCLE_STATES.includes(mark.state ?? '')
      ? (mark.state ?? 'unknown')
      : 'other';
    const row = buckets.get(lane)!;
    let cell = row.get(state);
    if (!cell) {
      cell = [];
      row.set(state, cell);
    }
    cell.push(mark);
  }
  return buckets;
}

function aggregateCell(
  lane: OperabilityLane,
  state: string,
  marks: ReadonlyArray<TaskLedgerCartographyAtlasMark>,
): CellAggregate {
  const overlays = {
    unrouted: 0,
    blocked: 0,
    stale: 0,
    signoff_required: 0,
    high_unlock: 0,
  };
  const typeCount = new Map<string, number>();
  // Wave 2A — primary route_reason histogram for marks where unrouted=true.
  // Walks the same per-mark loop as the overlays counter so the cost stays
  // O(marks) per cell.
  const reasonCount = new Map<string, number>();
  const reasonKind = new Map<string, string>();
  let topMark: TaskLedgerCartographyAtlasMark | null = null;
  let topUnlocks = -1;
  for (const m of marks) {
    const o = m.overlays ?? {};
    if (o.unrouted) overlays.unrouted += 1;
    if (o.blocked) overlays.blocked += 1;
    if (o.stale) overlays.stale += 1;
    if (o.signoff_required) overlays.signoff_required += 1;
    if (o.high_unlock) overlays.high_unlock += 1;
    const t = m.work_item_type ?? 'unknown';
    typeCount.set(t, (typeCount.get(t) ?? 0) + 1);
    const unlocks = m.edge_summary?.downstream_unlock_count ?? 0;
    if (unlocks > topUnlocks) {
      topUnlocks = unlocks;
      topMark = m;
    }
    if (o.unrouted) {
      const explanation = m.route_explanation;
      const reason = explanation?.route_reason ?? 'unknown_reason';
      reasonCount.set(reason, (reasonCount.get(reason) ?? 0) + 1);
      if (explanation?.reason_kind) reasonKind.set(reason, explanation.reason_kind);
    }
  }
  let dominantType: string | null = null;
  let dominantTypeCount = 0;
  for (const [t, c] of typeCount) {
    if (c > dominantTypeCount) {
      dominantType = t;
      dominantTypeCount = c;
    }
  }
  // Pick the dominant route reason inside this cell. Ties: stable iteration
  // order over insertion order (matches Map semantics in modern V8 / WebKit).
  let topReason: string | null = null;
  let topReasonCount = 0;
  for (const [reason, c] of reasonCount) {
    if (c > topReasonCount) {
      topReason = reason;
      topReasonCount = c;
    }
  }
  const topReasonKind = topReason ? (reasonKind.get(topReason) ?? null) : null;
  return {
    lane,
    state,
    count: marks.length,
    dominantType,
    overlays,
    topMark,
    routeReasonHistogram: Object.fromEntries(reasonCount),
    topReason,
    topReasonCount,
    topReasonKind,
  };
}

export interface AtlasCellId {
  lane: OperabilityLane;
  state: string;
}

function cellMarksPerRow(count: number): { cols: number; rows: number } {
  if (count <= 1) return { cols: 1, rows: 1 };
  const cols = Math.max(1, Math.ceil(Math.sqrt(count * 1.6)));
  const rows = Math.max(1, Math.ceil(count / cols));
  return { cols, rows };
}

function MarkLegend({
  payload,
}: {
  payload: TaskLedgerCartographyPayloadResponse;
}) {
  const states = Object.keys(STATE_TONE).filter((s) => s !== 'unknown');
  const carryoverLabelOK =
    payload.consumption_contract?.drilldown_contract?.carryover_label_absent === true;
  const unroutedOverlayOK =
    payload.consumption_contract?.drilldown_contract?.unrouted_overlay_present === true;
  return (
    <div className="flex flex-wrap items-center gap-3 text-[10px] uppercase tracking-[0.14em] text-white/55">
      <span>color · state</span>
      <div className="flex flex-wrap gap-1.5">
        {states.map((state) => {
          const tone = toneFor(state);
          return (
            <span key={state} className="flex items-center gap-1">
              <span
                aria-hidden
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ backgroundColor: tone.fill, border: `1px solid ${tone.stroke}` }}
              />
              <span>{state}</span>
            </span>
          );
        })}
      </div>
      <span className="text-white/35">·</span>
      <span>halo</span>
      <span className="flex items-center gap-1">
        <span
          aria-hidden
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{
            backgroundColor: '#1f1f1f',
            boxShadow: '0 0 0 1.25px #fbbf24',
          }}
        />
        <span>unrouted</span>
      </span>
      <span className="flex items-center gap-1">
        <span
          aria-hidden
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{
            backgroundColor: '#1f1f1f',
            boxShadow: '0 0 0 1.25px #e57373',
          }}
        />
        <span>blocked</span>
      </span>
      <span className="flex items-center gap-1">
        <span
          aria-hidden
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{
            backgroundColor: '#1f1f1f',
            boxShadow: '0 0 0 1.25px #7bc78e',
          }}
        />
        <span>signoff</span>
      </span>
      {!carryoverLabelOK && (
        <span className="rounded-full border border-rose-300/30 px-2 py-0.5 normal-case text-rose-200">
          carryover label present in packet — refused
        </span>
      )}
      {!unroutedOverlayOK && (
        <span className="rounded-full border border-amber-300/30 px-2 py-0.5 normal-case text-amber-200">
          unrouted overlay missing in legend
        </span>
      )}
    </div>
  );
}

const EMPTY_QUEUE_IDS: ReadonlySet<string> = new Set();
let cachedWorkAtlasPayload: TaskLedgerCartographyPayloadResponse | null = null;

export function __resetWorkAtlasCacheForTests(): void {
  cachedWorkAtlasPayload = null;
}

export default function WorkAtlas({
  selectedWorkItemId = null,
  onSelectedWorkItemChange,
  onPayloadLoaded,
  queueIds = EMPTY_QUEUE_IDS,
  selectedCell = null,
  onSelectedCellChange,
  neighborhoodHighlight = null,
}: WorkAtlasProps) {
  const [filterMode, setFilterMode] = useState<AtlasFilterMode>('all');
  const [renderMode, setRenderMode] = useState<AtlasRenderMode>('aggregate');
  const [payload, setPayload] = useState<TaskLedgerCartographyPayloadResponse | null>(
    () => cachedWorkAtlasPayload,
  );
  const [loading, setLoading] = useState(() => cachedWorkAtlasPayload === null);
  const [error, setError] = useState<string | null>(null);
  // Hold the latest onPayloadLoaded in a ref so the cartography fetch fires
  // exactly once on mount without triggering React's exhaustive-deps refire
  // when a parent passes an inline callback.
  const onPayloadLoadedRef = useRef(onPayloadLoaded);
  useEffect(() => {
    onPayloadLoadedRef.current = onPayloadLoaded;
  }, [onPayloadLoaded]);

  useEffect(() => {
    let cancelled = false;
    const hasCachedPayload = cachedWorkAtlasPayload !== null;
    api.worldModel
      .taskLedgerCartography('workitem', {
        include: [
          'summary',
          'atlas_marks',
          'clusters',
          'nodes',
          'edges',
          'legend',
          'levels',
          'overflow_index',
          'omission_receipt',
          'warnings',
          'queue_membership',
        ],
      })
      .then((data) => {
        if (cancelled) return;
        cachedWorkAtlasPayload = data;
        setPayload(data);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (!hasCachedPayload) {
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (payload) onPayloadLoadedRef.current?.(payload);
  }, [payload]);

  const atlasReady = payload?.consumption_contract?.readiness?.atlas_marks_ready === true;
  const overviewGraphReady =
    payload?.consumption_contract?.readiness?.overview_graph_ready === true;
  const overviewComplete = payload?.consumption_contract?.readiness?.overview_complete === true;
  const carryoverLabelAbsent =
    payload?.consumption_contract?.drilldown_contract?.carryover_label_absent === true;

  const allMarks = useMemo<TaskLedgerCartographyAtlasMark[]>(() => {
    if (!payload?.available || !atlasReady) return [];
    if (!carryoverLabelAbsent) return []; // refuse to render under bogus legend
    return payload.atlas_marks ?? [];
  }, [payload, atlasReady, carryoverLabelAbsent]);

  // Apply the active filter pill. Filter is operability-only for now; group
  // axis swap (type/actor/family/route) is deferred — operability lanes are
  // the only Y-axis until that toggle ships.
  const marks = useMemo<TaskLedgerCartographyAtlasMark[]>(
    () => allMarks.filter((m) => passesFilter(m, filterMode)),
    [allMarks, filterMode],
  );

  // Operability lanes are the Y-axis. Replaces the old type-census layout
  // (work_item_type × lifecycle state), which produced a giant captured/
  // capture block dominated by triage backlog and hid the actionable rows.
  const buckets = useMemo(() => bucketByLaneAndState(marks, queueIds), [marks, queueIds]);
  const rows = useMemo(
    () => OPERABILITY_LANES.filter((lane) => (buckets.get(lane)?.size ?? 0) > 0),
    [buckets],
  );
  const columns = useMemo(() => columnOrder(), []);

  // Aggregate stats per cell. Drives the default semantic render: each cell
  // becomes one rect with a count + dominant overlays, not N tiny mark dots.
  const cellAggregates = useMemo(() => {
    const out = new Map<string, CellAggregate>();
    for (const lane of rows) {
      const row = buckets.get(lane) ?? new Map();
      for (const state of columns) {
        const cellMarks = row.get(state) ?? [];
        out.set(`${lane}|${state}`, aggregateCell(lane, state, cellMarks));
      }
    }
    return out;
  }, [rows, columns, buckets]);

  // Wave 1G — per-cell neighborhood highlight counts. For each cell in
  // the operability lattice, count marks that are: focus (1 cell only),
  // upstream depends_on, downstream unlocks. Track missing-from-atlas
  // counts honestly so the operator sees when a highlighted id has no
  // atlas_mark to land on (retired / external / outside Task Ledger).
  const neighborhoodHighlightByCell = useMemo(() => {
    type CellHighlight = {
      focus: boolean;
      upstream: number;
      downstream: number;
    };
    const empty = {
      cells: new Map<string, CellHighlight>(),
      totalCells: 0,
      omittedCount: 0,
      mappedCount: 0,
    };
    if (!neighborhoodHighlight) return empty;
    const { focusId, upstreamIds, downstreamIds } = neighborhoodHighlight;
    const cells = new Map<string, CellHighlight>();
    const ensure = (key: string): CellHighlight => {
      let h = cells.get(key);
      if (!h) {
        h = { focus: false, upstream: 0, downstream: 0 };
        cells.set(key, h);
      }
      return h;
    };
    const marksById = new Map<string, TaskLedgerCartographyAtlasMark>();
    for (const m of marks) marksById.set(m.id, m);
    let mapped = 0;
    let omitted = 0;
    const stampCell = (
      mark: TaskLedgerCartographyAtlasMark,
      kind: 'focus' | 'upstream' | 'downstream',
    ) => {
      const lane = deriveLane(mark, queueIds);
      const state = LIFECYCLE_STATES.includes(mark.state ?? '')
        ? (mark.state ?? 'unknown')
        : 'other';
      const cell = ensure(`${lane}|${state}`);
      if (kind === 'focus') cell.focus = true;
      else if (kind === 'upstream') cell.upstream += 1;
      else cell.downstream += 1;
    };
    const focusMark = marksById.get(focusId);
    if (focusMark) {
      stampCell(focusMark, 'focus');
      mapped += 1;
    } else {
      omitted += 1;
    }
    for (const id of upstreamIds) {
      const m = marksById.get(id);
      if (m) {
        stampCell(m, 'upstream');
        mapped += 1;
      } else {
        omitted += 1;
      }
    }
    for (const id of downstreamIds) {
      const m = marksById.get(id);
      if (m) {
        stampCell(m, 'downstream');
        mapped += 1;
      } else {
        omitted += 1;
      }
    }
    return {
      cells,
      totalCells: cells.size,
      omittedCount: omitted,
      mappedCount: mapped,
    };
  }, [neighborhoodHighlight, marks, queueIds]);

  const totalFilteredMarks = marks.length;
  const largestCellCount = useMemo(() => {
    let max = 0;
    for (const agg of cellAggregates.values()) {
      if (agg.count > max) max = agg.count;
    }
    return Math.max(1, max);
  }, [cellAggregates]);

  // Wave 2A — route provenance summary derived from atlas_marks. Single
  // pass; reused by root attrs and the always-visible summary panel
  // (WorkLens consumes the same atlas_marks via cartographyPayload).
  const routeProvenanceSummary = useMemo(() => {
    const reasonCount = new Map<string, number>();
    const reasonKind = new Map<string, string>();
    let explained = 0;
    let unknown = 0;
    let unroutedTotal = 0;
    let marksWithExplanation = 0;
    for (const m of marks) {
      if (m.route_explanation) marksWithExplanation += 1;
      if (!m.overlays?.unrouted) continue;
      unroutedTotal += 1;
      const reason = m.route_explanation?.route_reason ?? 'unknown_reason';
      reasonCount.set(reason, (reasonCount.get(reason) ?? 0) + 1);
      if (m.route_explanation?.reason_kind) {
        reasonKind.set(reason, m.route_explanation.reason_kind);
      }
      if (reason === 'unknown_reason') unknown += 1;
      else explained += 1;
    }
    // Sort reasons by count descending; deterministic tiebreaker on key.
    const ranked = Array.from(reasonCount.entries()).sort(
      (a, b) => b[1] - a[1] || a[0].localeCompare(b[0]),
    );
    const ready = marks.length > 0 && (marksWithExplanation === marks.length);
    return {
      ready,
      unroutedTotal,
      explained,
      unknown,
      reasonCount: Object.fromEntries(reasonCount),
      reasonKind: Object.fromEntries(reasonKind),
      ranked, // [reason, count][]
      distinctReasonCount: reasonCount.size,
    };
  }, [marks]);

  // Queue-membership honesty: read the backend-stamped queue_membership
  // block (workitem_cartography_v0.queue_membership) so the footer can
  // distinguish queue rows from mapped queue rows from unique work_item
  // ids from stamped atlas marks — four genuinely different units that
  // the prior footer collapsed into one. Falls back to a derived count
  // off the cartography lane when the backend payload pre-dates Wave 1D.5.
  const backendMembership = payload?.queue_membership;
  // Distinguish "backend block reached the UI" from "frontend derived a
  // state from the queue_visible lane alone". The station_render proof
  // gates on this attribute so a future regression that silently drops
  // the queue_membership payload field cannot pass the readiness check.
  const queueMembershipSource: 'backend' | 'derived' = backendMembership
    ? 'backend'
    : 'derived';
  const stampedFromLane = useMemo(() => {
    const laneMap = buckets.get('queue_visible');
    if (!laneMap) return 0;
    let total = 0;
    for (const cellMarks of laneMap.values()) total += cellMarks.length;
    return total;
  }, [buckets]);
  const queueRowCount =
    backendMembership?.queue_row_count ?? queueIds.size;
  const mappedQueueRowCount =
    backendMembership?.mapped_queue_row_count ?? 0;
  const uniqueWorkItemIdCount =
    backendMembership?.unique_work_item_id_count ?? 0;
  const stampedAtlasMarkCount =
    backendMembership?.stamped_atlas_mark_count ?? stampedFromLane;
  const unjoinedQueueRowCount =
    backendMembership?.unjoined_queue_row_count ??
    Math.max(queueRowCount - mappedQueueRowCount, 0);
  const queueMembership:
    | 'mapped_full'
    | 'mapped_partial'
    | 'unavailable'
    | 'empty' = (() => {
    const backendState = backendMembership?.coverage_state;
    if (backendState) return backendState;
    if (queueRowCount === 0) return 'empty';
    if (stampedAtlasMarkCount > 0)
      return unjoinedQueueRowCount === 0 ? 'mapped_full' : 'mapped_partial';
    return 'unavailable';
  })();

  const handleCellSelect = (lane: OperabilityLane, state: string, count: number) => {
    if (count === 0) {
      // Clicking an empty cell deselects to keep the inspector honest.
      onSelectedCellChange?.(null);
      return;
    }
    if (selectedCell && selectedCell.lane === lane && selectedCell.state === state) {
      onSelectedCellChange?.(null);
      return;
    }
    onSelectedCellChange?.({ lane, state });
  };

  // Compute per-cell layout. In aggregate mode each cell is a uniform
  // density-tinted rect with a count label; in marks mode the original
  // packed mark grid is preserved (kept as an explicit toggle for proof /
  // debug, never the default).
  const layout = useMemo(() => {
    const rowDims = new Map<
      OperabilityLane,
      { cols: number; rows: number; height: number; width: number }
    >();
    const AGGREGATE_CELL_HEIGHT = 56;
    const AGGREGATE_CELL_WIDTH = 92;
    if (renderMode === 'aggregate') {
      for (const lane of rows) {
        rowDims.set(lane, {
          cols: 1,
          rows: 1,
          height: AGGREGATE_CELL_HEIGHT,
          width: AGGREGATE_CELL_WIDTH,
        });
      }
    } else {
      const rowMaxCount = new Map<OperabilityLane, number>();
      for (const lane of rows) {
        const row = buckets.get(lane) ?? new Map();
        let maxN = 0;
        for (const state of columns) {
          maxN = Math.max(maxN, row.get(state)?.length ?? 0);
        }
        rowMaxCount.set(lane, maxN);
      }
      for (const [lane, maxN] of rowMaxCount) {
        const dims = cellMarksPerRow(maxN);
        const widthPerCell =
          dims.cols * (MARK_SIZE_PX + MARK_GAP_PX) - MARK_GAP_PX + 2 * CELL_PADDING_PX;
        const heightPerCell =
          dims.rows * (MARK_SIZE_PX + MARK_GAP_PX) -
          MARK_GAP_PX +
          2 * CELL_PADDING_PX +
          CELL_LABEL_HEIGHT_PX;
        rowDims.set(lane, {
          cols: dims.cols,
          rows: dims.rows,
          height: Math.max(heightPerCell, 36),
          width: Math.max(widthPerCell, 56),
        });
      }
    }
    const colWidth = Math.max(
      ...Array.from(rowDims.values()).map((d) => d.width),
      renderMode === 'aggregate' ? AGGREGATE_CELL_WIDTH : 72,
    );
    let yCursor = COL_LABEL_HEIGHT_PX;
    const rowOffsets = new Map<OperabilityLane, number>();
    for (const lane of rows) {
      rowOffsets.set(lane, yCursor);
      yCursor += (rowDims.get(lane)?.height ?? 36) + 4;
    }
    const totalHeight = yCursor + 6;
    const totalWidth = ROW_LABEL_WIDTH_PX + colWidth * columns.length + 12;
    return { rowDims, rowOffsets, colWidth, totalHeight, totalWidth };
  }, [rows, columns, buckets, renderMode]);

  if (loading) {
    return (
      <section className="rounded-[14px] border border-white/[0.08] bg-black/30 p-3">
        <PanelSourceHeader
          title="Work Atlas"
          kicker="cartography · v0.1"
          sourceLabel="/api/world-model/task-ledger/cartography/workitem"
          schemaVersion="task_ledger_cartography_payload_v1"
          freshness="loading"
          freshnessTone="loading"
          claimBoundary="lattice render of workitem_cartography_v0 atlas_marks; observation only"
        />
        <div className="mt-3 text-[12px] text-white/45">loading work atlas payload…</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-[14px] border border-rose-300/25 bg-rose-300/[0.05] p-3">
        <PanelSourceHeader
          title="Work Atlas"
          kicker="cartography · v0.1"
          sourceLabel="/api/world-model/task-ledger/cartography/workitem"
          freshness="error"
          freshnessTone="block"
        />
        <div className="mt-3 text-[12px] text-rose-200/80">cartography route error · {error}</div>
      </section>
    );
  }

  if (!payload?.available || !atlasReady) {
    const consumerNotes = payload?.consumption_contract?.consumer_notes ?? [];
    return (
      <section className="rounded-[14px] border border-amber-300/30 bg-amber-300/[0.05] p-3">
        <PanelSourceHeader
          title="Work Atlas"
          kicker="cartography · v0.1"
          sourceLabel="/api/world-model/task-ledger/cartography/workitem"
          freshness="atlas not ready"
          freshnessTone="warn"
          claimBoundary="lattice render gated on atlas_marks_ready"
        />
        <div className="mt-3 space-y-1 text-[12px] text-amber-100">
          <div>
            atlas_marks_ready ·{' '}
            <span className="font-mono text-amber-50">
              {String(payload?.consumption_contract?.readiness?.atlas_marks_ready ?? 'unknown')}
            </span>
          </div>
          {payload?.reason && <div className="text-amber-200/80">reason · {payload.reason}</div>}
          {consumerNotes.map((note, i) => (
            <div key={`note:${i}`} className="text-amber-200/80">
              · {note}
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (!carryoverLabelAbsent) {
    return (
      <section className="rounded-[14px] border border-rose-300/30 bg-rose-300/[0.05] p-3">
        <PanelSourceHeader
          title="Work Atlas"
          kicker="cartography · v0.1"
          sourceLabel="/api/world-model/task-ledger/cartography/workitem"
          freshness="legend rejected"
          freshnessTone="block"
          claimBoundary="renderer refuses payload that advertises a carryover label"
        />
        <div className="mt-3 text-[12px] text-rose-200/80">
          consumption_contract.drilldown_contract.carryover_label_absent is not true. Refusing to
          render lattice — carryover semantics do not exist in the substrate yet, so any carryover
          overlay would be a beautiful lie. Fix the cartography legend before this Atlas can render.
        </div>
      </section>
    );
  }

  const summary = payload.summary as Record<string, unknown> | undefined;
  const sourceWorkItemCount = (summary?.source_work_item_count as number | undefined) ?? marks.length;
  const overviewBoundedNote = !overviewComplete
    ? 'graph layer bounded by design · atlas_marks remains full universe'
    : null;

  return (
    <section
      data-zenith-work-atlas={atlasReady ? 'ready' : 'pending'}
      data-zenith-work-atlas-mark-count={marks.length}
      data-zenith-work-atlas-semantic-mode={renderMode}
      data-zenith-work-atlas-filter={filterMode}
      data-zenith-work-atlas-selected-cell={selectedCell ? 'present' : 'idle'}
      data-zenith-work-atlas-selected-cell-lane={selectedCell?.lane ?? undefined}
      data-zenith-work-atlas-selected-cell-state={selectedCell?.state ?? undefined}
      data-zenith-work-atlas-queue-membership={queueMembership}
      data-zenith-work-atlas-queue-membership-source={queueMembershipSource}
      data-zenith-work-atlas-neighborhood-highlight={
        neighborhoodHighlight ? 'ready' : 'idle'
      }
      data-zenith-work-atlas-neighborhood-focus={
        neighborhoodHighlight?.focusId ?? undefined
      }
      data-zenith-work-atlas-neighborhood-highlight-count={
        neighborhoodHighlightByCell.mappedCount
      }
      data-zenith-work-atlas-neighborhood-highlight-omitted-count={
        neighborhoodHighlightByCell.omittedCount
      }
      data-zenith-work-atlas-neighborhood-highlight-cell-count={
        neighborhoodHighlightByCell.totalCells
      }
      data-zenith-work-route-provenance={
        routeProvenanceSummary.ready ? 'ready' : 'unavailable'
      }
      data-zenith-work-route-provenance-explained-count={
        routeProvenanceSummary.explained
      }
      data-zenith-work-route-provenance-unknown-count={
        routeProvenanceSummary.unknown
      }
      data-zenith-work-route-provenance-unrouted-total={
        routeProvenanceSummary.unroutedTotal
      }
      data-zenith-work-route-provenance-reason-count={
        routeProvenanceSummary.distinctReasonCount
      }
      data-zenith-work-route-provenance-top-reason={
        routeProvenanceSummary.ranked[0]?.[0] ?? undefined
      }
      data-zenith-work-route-provenance-top-reason-count={
        routeProvenanceSummary.ranked[0]?.[1] ?? undefined
      }
      data-zenith-work-route-provenance-source={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_present
          ? 'cartography_inline'
          : 'unavailable'
      }
      data-zenith-work-route-provenance-schema={payload.schema_version}
      data-zenith-work-route-provenance-carryover-status={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_carryover_status ?? 'not_evaluated'
      }
      data-zenith-work-route-provenance-evidence={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_evidence_present
          ? 'ready'
          : 'incomplete'
      }
      data-zenith-work-route-provenance-evidence-ok-count={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_evidence_ok_count
      }
      data-zenith-work-route-provenance-evidence-missing-count={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_evidence_missing_count
      }
      data-zenith-work-route-resolution={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_resolution_present
          ? 'ready'
          : 'incomplete'
      }
      data-zenith-work-route-resolution-reason-with-remedy-count={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_resolution_reason_with_remedy_count
      }
      data-zenith-work-route-resolution-reason-without-remedy-count={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_resolution_reason_without_remedy_count
      }
      data-zenith-work-route-resolution-lane-semantics={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_resolution_lane_semantics_present
          ? 'ready'
          : 'incomplete'
      }
      data-zenith-work-route-resolution-exact-view-count={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_resolution_lane_audit?.exact_view_count
      }
      data-zenith-work-route-resolution-broad-view-count={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_resolution_lane_audit?.broad_view_count
      }
      data-zenith-work-route-resolution-partial-view-count={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_resolution_lane_audit?.partial_view_count
      }
      data-zenith-work-route-resolution-target-lane-count={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_resolution_lane_audit?.target_lane_count
      }
      data-zenith-work-route-resolution-benign-count={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_resolution_lane_audit?.benign_count
      }
      data-zenith-work-route-resolution-fallback-count={
        payload.consumption_contract?.drilldown_contract
          ?.route_provenance_resolution_lane_audit?.fallback_count
      }
      data-zenith-work-atlas-queue-row-count={queueRowCount}
      data-zenith-work-atlas-mapped-queue-row-count={mappedQueueRowCount}
      data-zenith-work-atlas-unique-work-item-id-count={uniqueWorkItemIdCount}
      data-zenith-work-atlas-visible-mark-count={stampedAtlasMarkCount}
      data-zenith-work-atlas-unjoined-queue-row-count={unjoinedQueueRowCount}
      className="rounded-[14px] border border-white/[0.08] bg-black/30 p-3"
    >
      <PanelSourceHeader
        title="Work Atlas"
        kicker="cartography · v0.2"
        sourceLabel="/api/world-model/task-ledger/cartography/workitem"
        schemaVersion={payload.schema_version ?? 'workitem_cartography_v0'}
        freshness={`${marks.length} of ${allMarks.length} marks`}
        freshnessTone="ok"
        claimBoundary="operability lattice over workitem_cartography_v0; observation only"
        trailing={
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/45">
            {compactCount(sourceWorkItemCount)} workitems · {rows.length} lanes ·{' '}
            {overviewGraphReady ? 'graph ready' : 'graph not ready'}
          </span>
        }
      />

      {/* Control strip — first cut of the operator's "group / filter / mode"
          spec. Group-axis swap (operability ↔ type/actor/family/route) is
          deferred; operability is the default and only axis until then. */}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.14em]">
        <span className="text-white/45">group · operability lane</span>
        <span className="text-white/25">·</span>
        <span className="text-white/45">filter ·</span>
        <div className="flex flex-wrap gap-1">
          {(Object.keys(FILTER_LABEL) as AtlasFilterMode[]).map((mode) => {
            const active = mode === filterMode;
            return (
              <button
                key={`filter:${mode}`}
                type="button"
                onClick={() => setFilterMode(mode)}
                className={
                  active
                    ? 'rounded-full border border-emerald-300/40 bg-emerald-300/[0.08] px-2 py-0.5 text-emerald-100'
                    : 'rounded-full border border-white/15 px-2 py-0.5 text-white/55 hover:border-white/30 hover:text-white/75'
                }
              >
                {FILTER_LABEL[mode]}
              </button>
            );
          })}
        </div>
        <span className="text-white/25">·</span>
        <span className="text-white/45">mode ·</span>
        <div className="flex gap-1">
          {(['aggregate', 'marks'] as AtlasRenderMode[]).map((mode) => {
            const active = mode === renderMode;
            return (
              <button
                key={`mode:${mode}`}
                type="button"
                onClick={() => setRenderMode(mode)}
                className={
                  active
                    ? 'rounded-full border border-emerald-300/40 bg-emerald-300/[0.08] px-2 py-0.5 text-emerald-100'
                    : 'rounded-full border border-white/15 px-2 py-0.5 text-white/55 hover:border-white/30 hover:text-white/75'
                }
              >
                {mode}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-2">
        <MarkLegend payload={payload} />
      </div>
      {overviewBoundedNote && (
        <div className="mt-1.5 text-[10px] uppercase tracking-[0.14em] text-white/45">
          · {overviewBoundedNote}
        </div>
      )}

      <div className="mt-3 overflow-auto">
        <svg
          width={layout.totalWidth}
          height={layout.totalHeight}
          role="img"
          aria-label={
            renderMode === 'aggregate'
              ? `Work Atlas operability lattice — aggregate cells across ${rows.length} lanes and ${columns.length} lifecycle states`
              : `Work Atlas operability lattice — ${marks.length} marks across ${rows.length} lanes and ${columns.length} lifecycle states`
          }
          style={{ display: 'block' }}
        >
          {/* Column headers (lifecycle states) */}
          {columns.map((state, ci) => {
            const x = ROW_LABEL_WIDTH_PX + ci * layout.colWidth + layout.colWidth / 2;
            return (
              <text
                key={`col:${state}`}
                x={x}
                y={COL_LABEL_HEIGHT_PX - 6}
                textAnchor="middle"
                fontSize="9"
                fill="rgba(255,255,255,0.55)"
                style={{ fontFamily: 'var(--font-mono)', letterSpacing: '0.14em', textTransform: 'uppercase' }}
              >
                {state}
              </text>
            );
          })}
          {/* Row labels + cells */}
          {rows.map((lane) => {
            const yOffset = layout.rowOffsets.get(lane) ?? 0;
            const dims = layout.rowDims.get(lane) ?? {
              cols: 1,
              rows: 1,
              height: 36,
              width: 56,
            };
            const row = buckets.get(lane) ?? new Map<string, TaskLedgerCartographyAtlasMark[]>();
            const rowMarkCount = Array.from(row.values()).reduce((s, c) => s + c.length, 0);
            return (
              <g key={`row:${lane}`}>
                <text
                  x={ROW_LABEL_WIDTH_PX - 8}
                  y={yOffset + dims.height / 2}
                  textAnchor="end"
                  fontSize="10"
                  style={{ fontFamily: 'var(--font-mono)' }}
                  fill="rgba(255,255,255,0.78)"
                  dominantBaseline="middle"
                >
                  {LANE_LABEL[lane]}
                </text>
                <text
                  x={ROW_LABEL_WIDTH_PX - 8}
                  y={yOffset + dims.height / 2 + 12}
                  textAnchor="end"
                  fontSize="9"
                  style={{ fontFamily: 'var(--font-mono)' }}
                  fill="rgba(255,255,255,0.4)"
                  dominantBaseline="middle"
                >
                  {rowMarkCount}
                </text>
                {columns.map((state, ci) => {
                  const cellX = ROW_LABEL_WIDTH_PX + ci * layout.colWidth;
                  const cellMarks = row.get(state) ?? [];
                  const agg =
                    cellAggregates.get(`${lane}|${state}`) ??
                    aggregateCell(lane, state, cellMarks);
                  const cellIsSelected =
                    !!selectedCell &&
                    selectedCell.lane === lane &&
                    selectedCell.state === state;
                  if (renderMode === 'aggregate') {
                    // Density-tinted aggregate cell. Empty cells render as a
                    // faint scaffold so the lattice stays legible.
                    const density = agg.count / largestCellCount;
                    const stateTone = toneFor(state);
                    const fillOpacity =
                      agg.count === 0 ? 0.015 : 0.18 + density * 0.72;
                    const overlayMarks: string[] = [];
                    if (agg.overlays.blocked > 0) overlayMarks.push('B');
                    if (agg.overlays.unrouted > 0) overlayMarks.push('U');
                    if (agg.overlays.stale > 0) overlayMarks.push('S');
                    if (agg.overlays.signoff_required > 0) overlayMarks.push('SO');
                    if (agg.overlays.high_unlock > 0) overlayMarks.push('HU');
                    // Wave 1G — neighborhood highlight badge for this cell.
                    const cellHighlight =
                      neighborhoodHighlightByCell.cells.get(`${lane}|${state}`);
                    const highlightBadgeParts: string[] = [];
                    if (cellHighlight?.focus) highlightBadgeParts.push('F');
                    if (cellHighlight?.upstream)
                      highlightBadgeParts.push(`D${cellHighlight.upstream}`);
                    if (cellHighlight?.downstream)
                      highlightBadgeParts.push(`U${cellHighlight.downstream}`);
                    const isFocusCell = cellHighlight?.focus === true;
                    // Wave 2A — per-cell route-reason badge. Bottom-right
                    // corner; renders only when the cell carries unrouted
                    // marks AND aggregateCell picked a topReason. Short
                    // code mapped from canonical key via ROUTE_REASON_SHORT_CODE.
                    const reasonShortCode = agg.topReason
                      ? (ROUTE_REASON_SHORT_CODE[agg.topReason] ?? '??')
                      : null;
                    const reasonKindTone = agg.topReasonKind
                      ? (ROUTE_REASON_KIND_TONE[agg.topReasonKind] ??
                          ROUTE_REASON_KIND_TONE.actionable)
                      : ROUTE_REASON_KIND_TONE.actionable;
                    return (
                      <g
                        key={`cell:${lane}:${state}`}
                        data-zenith-work-atlas-cell={`${lane}|${state}`}
                        data-zenith-work-atlas-cell-unrouted-count={
                          agg.overlays.unrouted || undefined
                        }
                        data-zenith-work-atlas-cell-route-reason-top={
                          agg.topReason ?? undefined
                        }
                        data-zenith-work-atlas-cell-route-reason-top-count={
                          agg.topReasonCount || undefined
                        }
                        data-zenith-work-atlas-cell-route-reason-distinct={
                          Object.keys(agg.routeReasonHistogram).length ||
                          undefined
                        }
                      >
                        <rect
                          x={cellX + 2}
                          y={yOffset + 2}
                          width={layout.colWidth - 4}
                          height={dims.height - 4}
                          fill={agg.count === 0 ? 'rgba(255,255,255,0.015)' : stateTone.fill}
                          fillOpacity={fillOpacity}
                          stroke={
                            isFocusCell
                              ? '#fbbf24'
                              : cellIsSelected
                                ? '#fff'
                                : agg.count === 0
                                  ? 'rgba(255,255,255,0.04)'
                                  : stateTone.stroke
                          }
                          strokeWidth={isFocusCell ? 1.6 : cellIsSelected ? 1.3 : 0.6}
                          rx={2}
                          cursor={agg.count > 0 ? 'pointer' : 'default'}
                          onClick={() => handleCellSelect(lane, state, agg.count)}
                        >
                          <title>
                            {`${LANE_LABEL[lane]} · ${state}\n` +
                              `count: ${agg.count}\n` +
                              `dominant type: ${agg.dominantType ?? '—'}\n` +
                              `overlays: blocked=${agg.overlays.blocked} unrouted=${agg.overlays.unrouted} stale=${agg.overlays.stale} signoff=${agg.overlays.signoff_required} high_unlock=${agg.overlays.high_unlock}\n` +
                              (agg.topReason
                                ? `route reason · top: ${ROUTE_REASON_LABEL[agg.topReason] ?? agg.topReason} (${agg.topReasonCount} of ${agg.overlays.unrouted})\n`
                                : '') +
                              `top mark: ${agg.topMark?.id ?? '—'}`}
                          </title>
                        </rect>
                        {agg.count > 0 && (
                          <>
                            <text
                              x={cellX + 8}
                              y={yOffset + 18}
                              fontSize="13"
                              style={{ fontFamily: 'var(--font-mono)' }}
                              fontWeight={600}
                              fill="rgba(255,255,255,0.92)"
                              pointerEvents="none"
                            >
                              {agg.count}
                            </text>
                            {agg.dominantType && (
                              <text
                                x={cellX + 8}
                                y={yOffset + 32}
                                fontSize="9"
                                style={{ fontFamily: 'var(--font-mono)' }}
                                fill="rgba(255,255,255,0.6)"
                                pointerEvents="none"
                              >
                                {agg.dominantType}
                              </text>
                            )}
                            {highlightBadgeParts.length > 0 && (
                              <text
                                x={cellX + layout.colWidth - 6}
                                y={yOffset + 14}
                                fontSize="9"
                                style={{ fontFamily: 'var(--font-mono)' }}
                                fontWeight={600}
                                textAnchor="end"
                                fill={
                                  isFocusCell
                                    ? '#fbbf24'
                                    : 'rgba(125,199,228,0.92)'
                                }
                                pointerEvents="none"
                              >
                                {highlightBadgeParts.join('·')}
                              </text>
                            )}
                            {overlayMarks.length > 0 && (
                              <text
                                x={cellX + 8}
                                y={yOffset + dims.height - 8}
                                fontSize="8"
                                style={{ fontFamily: 'var(--font-mono)' }}
                                fill="rgba(255,255,255,0.55)"
                                pointerEvents="none"
                              >
                                {overlayMarks.join(' ')}
                              </text>
                            )}
                            {/* Wave 2A — route-reason badge (bottom-right). */}
                            {reasonShortCode && agg.overlays.unrouted > 0 && (
                              <text
                                x={cellX + layout.colWidth - 6}
                                y={yOffset + dims.height - 8}
                                fontSize="8"
                                style={{ fontFamily: 'var(--font-mono)' }}
                                fontWeight={600}
                                textAnchor="end"
                                fill={reasonKindTone.text}
                                pointerEvents="none"
                              >
                                {`${reasonShortCode}·${agg.topReasonCount}`}
                              </text>
                            )}
                          </>
                        )}
                      </g>
                    );
                  }
                  // marks mode — original packed mark grid, preserved as a
                  // debug/proof toggle. Not the default after Wave 1C.5.
                  return (
                    <g key={`cell:${lane}:${state}`}>
                      <rect
                        x={cellX}
                        y={yOffset}
                        width={layout.colWidth - 2}
                        height={dims.height - 2}
                        fill="rgba(255,255,255,0.015)"
                        stroke={
                          cellIsSelected ? '#fff' : 'rgba(255,255,255,0.04)'
                        }
                        strokeWidth={cellIsSelected ? 1.0 : 0.5}
                        cursor={cellMarks.length > 0 ? 'pointer' : 'default'}
                        onClick={() => handleCellSelect(lane, state, cellMarks.length)}
                      />
                      {cellMarks.length > 0 && (
                        <text
                          x={cellX + 4}
                          y={yOffset + 12}
                          fontSize="9"
                          style={{ fontFamily: 'var(--font-mono)' }}
                          fill="rgba(255,255,255,0.5)"
                          pointerEvents="none"
                        >
                          {cellMarks.length}
                        </text>
                      )}
                      {cellMarks.map((mark, idx) => {
                        const col = idx % dims.cols;
                        const r = Math.floor(idx / dims.cols);
                        const mx = cellX + CELL_PADDING_PX + col * (MARK_SIZE_PX + MARK_GAP_PX);
                        const my =
                          yOffset +
                          CELL_LABEL_HEIGHT_PX +
                          CELL_PADDING_PX +
                          r * (MARK_SIZE_PX + MARK_GAP_PX);
                        const tone = toneFor(mark.state);
                        const overlays = mark.overlays ?? {};
                        const haloColor = overlays.blocked
                          ? '#e57373'
                          : overlays.unrouted
                            ? '#fbbf24'
                            : overlays.signoff_required
                              ? '#7bc78e'
                              : null;
                        const isSelected = mark.id === selectedWorkItemId;
                        return (
                          <g key={mark.id}>
                            {haloColor && (
                              <rect
                                x={mx - 1}
                                y={my - 1}
                                width={MARK_SIZE_PX + 2}
                                height={MARK_SIZE_PX + 2}
                                rx={1}
                                fill="transparent"
                                stroke={haloColor}
                                strokeWidth={MARK_HALO_STROKE}
                                pointerEvents="none"
                              />
                            )}
                            <rect
                              data-zenith-atlas-mark={mark.id}
                              data-zenith-atlas-mark-selected={isSelected ? 'true' : 'false'}
                              x={mx}
                              y={my}
                              width={MARK_SIZE_PX}
                              height={MARK_SIZE_PX}
                              rx={1}
                              fill={tone.fill}
                              stroke={isSelected ? '#fff' : tone.stroke}
                              strokeWidth={isSelected ? 1.4 : 0.6}
                              cursor="pointer"
                              onClick={() => onSelectedWorkItemChange?.(mark.id, 'click')}
                            >
                              <title>
                                {`${mark.title ?? mark.id}\n` +
                                  `id: ${mark.id}\n` +
                                  `state: ${mark.state ?? 'unknown'}\n` +
                                  `type: ${mark.work_item_type ?? 'unknown'}\n` +
                                  `actor: ${mark.actor ?? 'unassigned'}\n` +
                                  `family: ${mark.family ?? 'unknown'}\n` +
                                  `route: ${mark.route?.status ?? 'unknown'}\n` +
                                  `unlocks: ${mark.edge_summary?.downstream_unlock_count ?? 0}`}
                              </title>
                            </rect>
                          </g>
                        );
                      })}
                    </g>
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/40">
        <span>showing {totalFilteredMarks} marks</span>
        <span>· largest cell {largestCellCount}</span>
        <span>· queue rows {queueRowCount}</span>
        <span>· mapped rows {mappedQueueRowCount}</span>
        <span>· unique work items {uniqueWorkItemIdCount}</span>
        <span>
          ·{' '}
          <span className="text-white/55">
            atlas-visible marks {stampedAtlasMarkCount}
          </span>
        </span>
        {queueMembership === 'empty' && (
          <span className="rounded-full border border-white/15 bg-white/[0.04] px-2 py-0.5 normal-case tracking-normal text-white/60">
            queue empty · no Work Ledger rows to map
          </span>
        )}
        {queueMembership === 'unavailable' && (
          <span className="rounded-full border border-rose-300/40 bg-rose-300/[0.08] px-2 py-0.5 normal-case tracking-normal text-rose-100">
            queue join unavailable · 0 of {queueRowCount} queue rows carry a
            canonical work_item id (id-namespace gap; not a queue-empty signal)
          </span>
        )}
        {queueMembership === 'mapped_partial' && (
          <span className="rounded-full border border-amber-300/40 bg-amber-300/[0.08] px-2 py-0.5 normal-case tracking-normal text-amber-100">
            queue join partial · {mappedQueueRowCount} of {queueRowCount} queue
            rows carry a canonical work_item id ({stampedAtlasMarkCount} atlas
            marks stamped from {uniqueWorkItemIdCount} unique ids); {unjoinedQueueRowCount}{' '}
            unjoined rows pending Wave 1D.5 creation-time propagation
          </span>
        )}
        {queueMembership === 'mapped_full' && (
          <span className="rounded-full border border-emerald-300/40 bg-emerald-300/[0.08] px-2 py-0.5 normal-case tracking-normal text-emerald-100">
            queue join mapped · all {queueRowCount} queue rows carry a canonical
            work_item id ({stampedAtlasMarkCount} atlas marks stamped from{' '}
            {uniqueWorkItemIdCount} unique ids)
          </span>
        )}
      </div>
    </section>
  );
}
