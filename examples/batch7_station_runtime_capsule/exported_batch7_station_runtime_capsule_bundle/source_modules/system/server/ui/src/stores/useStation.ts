// [PURPOSE] Focused store slice for the Zenith station: launcher snapshot,
// attention snapshot, topology index/search cache, and auto-refresh polling.
// Keeps useZenith lean and lets station surfaces subscribe narrowly without
// pulling the full mission/runtime state.
//
// Doctrine: pri_058 (observability + freshness), pri_061 (control surface),
// pri_062 (operator decision load), pri_070 (active driver + handoff).
import { create } from 'zustand';
import {
  api,
  ApiRequestError,
  type AttentionSnapshot,
  type LaunchableOperationsResponse,
  type LaunchOperationPreview,
  type LaunchOperationResult,
  type ReactionsSnapshot,
  type ReconciliationProjection,
  type StationLauncherOperation,
  type StationLauncherSnapshot,
  type TopologyIndex,
  type TopologySearchResponse,
  type WakeBarriersSnapshot,
} from '../api';
import { reportSurfaceError, resetSurfaceError } from '../lib/surfaceErrors';

export type LiveUpdateState = 'live' | 'catching_up' | 'paused' | 'stale';
export type LiveUpdateSource = 'poll' | 'observe' | 'manual';

interface TopologyCacheEntry {
  index: TopologyIndex | null;
  searches: Record<string, TopologySearchResponse>;
  error?: string | null;
  attempted?: boolean;
}

export interface StationLiveUpdates {
  paused: boolean;
  status: LiveUpdateState;
  lastSuccessfulRefreshAt: number | null;
  lastSignalAt: number | null;
  inFlight: boolean;
  source: LiveUpdateSource | null;
}

type StationState = {
  launcher: StationLauncherSnapshot | null;
  launcherLoading: boolean;
  launcherError: string | null;
  launcherLoadedAt: number | null;
  launcherWarming: boolean;
  launcherWarmingReason: string | null;
  operationsCatalog: StationLauncherOperation[] | null;
  operationsCatalogLoading: boolean;
  operationsCatalogError: string | null;
  operationsCatalogLoadedAt: number | null;
  operationsCatalogWarming: boolean;
  operationsCatalogWarmingReason: string | null;
  opsLauncherSnapshot: LaunchableOperationsResponse | null;
  attention: AttentionSnapshot | null;
  attentionLoading: boolean;
  attentionError: string | null;
  attentionLoadedAt: number | null;
  attentionWarming: boolean;
  attentionWarmingReason: string | null;
  reactions: ReactionsSnapshot | null;
  reactionsLoading: boolean;
  reactionsError: string | null;
  reactionsLoadedAt: number | null;
  wakeBarriers: WakeBarriersSnapshot | null;
  wakeBarriersLoading: boolean;
  wakeBarriersError: string | null;
  wakeBarriersLoadedAt: number | null;
  reconciliation: ReconciliationProjection | null;
  reconciliationLoading: boolean;
  reconciliationError: string | null;
  reconciliationLoadedAt: number | null;
  lastRefreshRequest: number | null;
  liveUpdates: StationLiveUpdates;

  topology: Record<string, TopologyCacheEntry>;

  refreshLauncher: (opts?: { force?: boolean }) => Promise<StationLauncherSnapshot | null>;
  refreshOperationsCatalog: (opts?: { force?: boolean }) => Promise<StationLauncherOperation[] | null>;
  refreshAttention: (opts?: { force?: boolean }) => Promise<AttentionSnapshot | null>;
  refreshReactions: (opts?: { force?: boolean }) => Promise<ReactionsSnapshot | null>;
  refreshWakeBarriers: (opts?: { force?: boolean }) => Promise<WakeBarriersSnapshot | null>;
  refreshReconciliation: (opts?: { force?: boolean }) => Promise<ReconciliationProjection | null>;
  previewOperation: (
    operationId: string,
    parameters?: Record<string, unknown>,
  ) => Promise<LaunchOperationPreview>;
  launchOperationById: (
    operationId: string,
    parameters?: Record<string, unknown>,
    actorId?: string,
  ) => Promise<NonNullable<LaunchOperationResult['result']>>;
  setLiveUpdatesPaused: (paused: boolean) => void;
  markLiveUpdateSignal: (source: LiveUpdateSource) => void;
  beginLiveUpdate: (source: LiveUpdateSource) => void;
  completeLiveUpdate: (success: boolean) => void;
  refreshLiveUpdateStatus: () => LiveUpdateState;
  setReactionsState: (body: { target: 'engine' | 'reaction'; armed: boolean; reaction_id?: string }) => Promise<ReactionsSnapshot | null>;
  orchestrationRefresh: () => Promise<AttentionSnapshot | null>;
  loadTopology: (phaseRef: string, opts?: { force?: boolean }) => Promise<TopologyIndex | null>;
  searchTopology: (
    phaseRef: string,
    params: { query?: string; group?: string; cluster?: string; kind?: string; limit?: number },
  ) => Promise<TopologySearchResponse | null>;
};

const STATION_CACHE_MS = 10_000;
const LIVE_UPDATE_STALE_MS = 15_000;
export const STATION_LAUNCHER_WARMING_RETRY_MS = 2_000;
export const OPERATIONS_CATALOG_WARMING_RETRY_MS = 2_000;
export const ATTENTION_WARMING_RETRY_MS = 2_000;
type OperationLaunchResult = NonNullable<LaunchOperationResult['result']>;

const operationLaunchesInFlight = new Map<string, Promise<OperationLaunchResult>>();
let stationLauncherWarmingRetry: ReturnType<typeof setTimeout> | null = null;
let operationsCatalogWarmingRetry: ReturnType<typeof setTimeout> | null = null;
let attentionWarmingRetry: ReturnType<typeof setTimeout> | null = null;

export function isStationLauncherWarming(
  payload: StationLauncherSnapshot | null | undefined,
): boolean {
  const cacheStatus = payload?.diagnostics?.cache?.status;
  if (typeof cacheStatus === 'string' && cacheStatus.toLowerCase() === 'warming') {
    return true;
  }
  return Boolean(payload?.alerts?.some((alert) => alert.id === 'station_launcher:warming'));
}

function stationLauncherWarmingReason(
  payload: StationLauncherSnapshot | null | undefined,
): string | null {
  const reason = payload?.diagnostics?.cache?.reason;
  if (typeof reason === 'string' && reason.trim()) {
    return reason.trim();
  }
  const alertDetail = payload?.alerts?.find((alert) => alert.id === 'station_launcher:warming')
    ?.detail;
  return typeof alertDetail === 'string' && alertDetail.trim() ? alertDetail.trim() : null;
}

export function clearStationLauncherWarmingRetry(): void {
  if (stationLauncherWarmingRetry == null) return;
  clearTimeout(stationLauncherWarmingRetry);
  stationLauncherWarmingRetry = null;
}

function scheduleStationLauncherWarmingRetry(refresh: () => Promise<unknown>): void {
  if (stationLauncherWarmingRetry != null) return;
  stationLauncherWarmingRetry = setTimeout(() => {
    stationLauncherWarmingRetry = null;
    void refresh();
  }, STATION_LAUNCHER_WARMING_RETRY_MS);
}

export function isOperationsCatalogWarming(
  payload: LaunchableOperationsResponse | null | undefined,
): boolean {
  const cacheStatus = payload?.diagnostics?.cache?.status;
  if (typeof cacheStatus === 'string' && cacheStatus.toLowerCase() === 'warming') {
    return true;
  }
  return Boolean(payload?.alerts?.some((alert) => alert.id === 'operations_catalog:warming'));
}

function operationsCatalogWarmingReason(
  payload: LaunchableOperationsResponse | null | undefined,
): string | null {
  const reason = payload?.diagnostics?.cache?.reason;
  if (typeof reason === 'string' && reason.trim()) {
    return reason.trim();
  }
  const alertDetail = payload?.alerts?.find((alert) => alert.id === 'operations_catalog:warming')
    ?.detail;
  return typeof alertDetail === 'string' && alertDetail.trim() ? alertDetail.trim() : null;
}

export function clearOperationsCatalogWarmingRetry(): void {
  if (operationsCatalogWarmingRetry == null) return;
  clearTimeout(operationsCatalogWarmingRetry);
  operationsCatalogWarmingRetry = null;
}

function scheduleOperationsCatalogWarmingRetry(refresh: () => Promise<unknown>): void {
  if (operationsCatalogWarmingRetry != null) return;
  operationsCatalogWarmingRetry = setTimeout(() => {
    operationsCatalogWarmingRetry = null;
    void refresh();
  }, OPERATIONS_CATALOG_WARMING_RETRY_MS);
}

export function isAttentionWarming(payload: AttentionSnapshot | null | undefined): boolean {
  const cacheStatus = payload?.diagnostics?.cache?.status;
  if (typeof cacheStatus === 'string' && cacheStatus.toLowerCase() === 'warming') {
    return true;
  }
  return Boolean(payload?.attention_items?.some((item) => item.id === 'attention:warming'));
}

function attentionWarmingReason(payload: AttentionSnapshot | null | undefined): string | null {
  const reason = payload?.diagnostics?.cache?.reason;
  if (typeof reason === 'string' && reason.trim()) {
    return reason.trim();
  }
  const itemDetail = payload?.attention_items?.find((item) => item.id === 'attention:warming')
    ?.detail;
  return typeof itemDetail === 'string' && itemDetail.trim() ? itemDetail.trim() : null;
}

export function clearAttentionWarmingRetry(): void {
  if (attentionWarmingRetry == null) return;
  clearTimeout(attentionWarmingRetry);
  attentionWarmingRetry = null;
}

function scheduleAttentionWarmingRetry(refresh: () => Promise<unknown>): void {
  if (attentionWarmingRetry != null) return;
  attentionWarmingRetry = setTimeout(() => {
    attentionWarmingRetry = null;
    void refresh();
  }, ATTENTION_WARMING_RETRY_MS);
}

function operationLaunchKey(
  operationId: string,
  parameters?: Record<string, unknown>,
  actorId = 'human_operator',
): string {
  const stableParameters = Object.fromEntries(
    Object.entries(parameters ?? {}).sort(([left], [right]) => left.localeCompare(right)),
  );
  return JSON.stringify({ actorId, operationId, parameters: stableParameters });
}

function deriveLiveUpdateStatus(
  state: Pick<StationLiveUpdates, 'paused' | 'inFlight' | 'lastSuccessfulRefreshAt'>,
  now: number = Date.now(),
): LiveUpdateState {
  if (state.inFlight) return 'catching_up';
  if (state.paused) return 'paused';
  if (!state.lastSuccessfulRefreshAt) return 'stale';
  return now - state.lastSuccessfulRefreshAt <= LIVE_UPDATE_STALE_MS ? 'live' : 'stale';
}

export const useStation = create<StationState>((set, get) => ({
  launcher: null,
  launcherLoading: false,
  launcherError: null,
  launcherLoadedAt: null,
  launcherWarming: false,
  launcherWarmingReason: null,
  operationsCatalog: null,
  operationsCatalogLoading: false,
  operationsCatalogError: null,
  operationsCatalogLoadedAt: null,
  operationsCatalogWarming: false,
  operationsCatalogWarmingReason: null,
  opsLauncherSnapshot: null,
  attention: null,
  attentionLoading: false,
  attentionError: null,
  attentionLoadedAt: null,
  attentionWarming: false,
  attentionWarmingReason: null,
  reactions: null,
  reactionsLoading: false,
  reactionsError: null,
  reactionsLoadedAt: null,
  wakeBarriers: null,
  wakeBarriersLoading: false,
  wakeBarriersError: null,
  wakeBarriersLoadedAt: null,
  reconciliation: null,
  reconciliationLoading: false,
  reconciliationError: null,
  reconciliationLoadedAt: null,
  lastRefreshRequest: null,
  liveUpdates: {
    paused: false,
    status: 'stale',
    lastSuccessfulRefreshAt: null,
    lastSignalAt: null,
    inFlight: false,
    source: null,
  },
  topology: {},

  refreshLauncher: async ({ force = false } = {}) => {
    const now = Date.now();
    const last = get().launcherLoadedAt ?? 0;
    if (!force && get().launcher && !get().launcherWarming && now - last < STATION_CACHE_MS) {
      return get().launcher;
    }
    if (get().launcherLoading) return get().launcher;
    set({ launcherLoading: true, launcherError: null });

    // Cold-boot resilience: if the user opens the UI before uvicorn is
    // accepting connections, the first fetch fails with `network_unavailable`
    // and the banner sticks. Quietly retry with bounded backoff for ~10s
    // before surfacing the error — only on the *initial* load (no launcher
    // snapshot yet), so a real outage mid-session still surfaces immediately.
    const isInitialLoad = get().launcher == null;
    const backoffsMs = isInitialLoad ? [500, 1000, 2000, 4000, 4000] : [0];

    let lastError: unknown = null;
    for (let attempt = 0; attempt < backoffsMs.length; attempt += 1) {
      try {
        const snap = await api.station.launcher();
        resetSurfaceError('station.launcher');
        const warming = isStationLauncherWarming(snap);
        if (warming) {
          scheduleStationLauncherWarmingRetry(() =>
            get().refreshLauncher({ force: true }),
          );
        } else {
          clearStationLauncherWarmingRetry();
        }
        set({
          launcher: snap,
          launcherLoadedAt: warming ? null : Date.now(),
          launcherLoading: false,
          launcherWarming: warming,
          launcherWarmingReason: warming ? stationLauncherWarmingReason(snap) : null,
        });
        return snap;
      } catch (e) {
        lastError = e;
        const isNetworkUnavailable =
          e instanceof ApiRequestError && e.kind === 'network_unavailable';
        const moreAttemptsLeft = attempt < backoffsMs.length - 1;
        if (!isNetworkUnavailable || !moreAttemptsLeft || !isInitialLoad) break;
        await new Promise((r) => setTimeout(r, backoffsMs[attempt]));
      }
    }
    clearStationLauncherWarmingRetry();
    const message = reportSurfaceError('station.launcher', lastError, 'Failed to load station launcher');
    set({
      launcherError: message,
      launcherLoading: false,
      launcherWarming: false,
      launcherWarmingReason: null,
    });
    return null;
  },

  refreshOperationsCatalog: async ({ force = false } = {}) => {
    const now = Date.now();
    const last = get().operationsCatalogLoadedAt ?? 0;
    if (
      !force &&
      get().operationsCatalog &&
      !get().operationsCatalogWarming &&
      now - last < STATION_CACHE_MS
    ) {
      return get().operationsCatalog;
    }
    if (get().operationsCatalogLoading) return get().operationsCatalog;
    set({ operationsCatalogLoading: true, operationsCatalogError: null });
    try {
      const payload = await api.worldModel.operations();
      resetSurfaceError('station.operations');
      const nextCatalog = payload.operations ?? [];
      const warming = isOperationsCatalogWarming(payload);
      if (warming) {
        scheduleOperationsCatalogWarmingRetry(() =>
          get().refreshOperationsCatalog({ force: true }),
        );
      } else {
        clearOperationsCatalogWarmingRetry();
      }
      set({
        operationsCatalog: nextCatalog,
        operationsCatalogLoadedAt: warming ? null : Date.now(),
        operationsCatalogLoading: false,
        operationsCatalogError: payload.error ?? null,
        operationsCatalogWarming: warming,
        operationsCatalogWarmingReason: warming ? operationsCatalogWarmingReason(payload) : null,
        opsLauncherSnapshot: payload,
      });
      return nextCatalog;
    } catch (e) {
      clearOperationsCatalogWarmingRetry();
      const message = reportSurfaceError(
        'station.operations',
        e,
        'Failed to load operations catalog',
      );
      set({
        operationsCatalogError: message,
        operationsCatalogLoading: false,
        operationsCatalogWarming: false,
        operationsCatalogWarmingReason: null,
      });
      return null;
    }
  },

  // NOTE: refreshAttention fan-writes reactions + wakeBarriers into the store
  // as a side effect of a single /api/world-model/attention fetch (the union
  // payload carries `snap.reactions`; see AttentionSnapshot in api.ts). Callers
  // that mount the Reactions or Orchestration panels should prefer this over
  // refreshReactions / refreshWakeBarriers to avoid redundant mount-site
  // fetches. The explicit refreshReactions / refreshWakeBarriers handles
  // below remain valid for force-refresh flows after setReactionsState and
  // for callers that need reaction-only telemetry.
  refreshAttention: async ({ force = false } = {}) => {
    const now = Date.now();
    const last = get().attentionLoadedAt ?? 0;
    if (!force && get().attention && !get().attentionWarming && now - last < STATION_CACHE_MS) {
      return get().attention;
    }
    if (get().attentionLoading) return get().attention;
    set({ attentionLoading: true, attentionError: null });
    // Bracket liveUpdates only when not already in-flight; the
    // `refreshStationRuntimeSurface` wrapper already brackets its
    // multi-refresh waves. Skipping when `inFlight=true` keeps the chip
    // status monotonic across nested callers (avoids premature flip to
    // `live` while sibling refreshes are still pending).
    const ownsBracket = !get().liveUpdates.inFlight;
    if (ownsBracket) {
      get().beginLiveUpdate('manual');
    }
    try {
      const snap = await api.worldModel.attention();
      resetSurfaceError('station.attention');
      const warming = isAttentionWarming(snap);
      if (warming) {
        scheduleAttentionWarmingRetry(() =>
          get().refreshAttention({ force: true }),
        );
      } else {
        clearAttentionWarmingRetry();
      }
      set({
        attention: snap,
        attentionLoadedAt: warming ? null : Date.now(),
        attentionLoading: false,
        attentionWarming: warming,
        attentionWarmingReason: warming ? attentionWarmingReason(snap) : null,
        reactions: snap.reactions ?? get().reactions,
        reactionsLoadedAt: snap.reactions ? Date.now() : get().reactionsLoadedAt,
        wakeBarriers: snap.reactions
          ? {
              schema: 'wake_barriers_v1',
              generated_at: snap.reactions.generated_at,
              engine_armed: snap.reactions.engine_armed,
              engine_status: snap.reactions.engine_status,
              items: snap.reactions.awaiting_barriers,
            }
          : get().wakeBarriers,
        wakeBarriersLoadedAt: snap.reactions ? Date.now() : get().wakeBarriersLoadedAt,
      });
      if (ownsBracket) get().completeLiveUpdate(!warming);
      return snap;
    } catch (e) {
      clearAttentionWarmingRetry();
      const message = reportSurfaceError(
        'station.attention',
        e,
        'Failed to load attention snapshot',
      );
      set({
        attentionError: message,
        attentionLoading: false,
        attentionWarming: false,
        attentionWarmingReason: null,
      });
      if (ownsBracket) get().completeLiveUpdate(false);
      return null;
    }
  },

  refreshReactions: async ({ force = false } = {}) => {
    const now = Date.now();
    const last = get().reactionsLoadedAt ?? 0;
    if (!force && get().reactions && now - last < STATION_CACHE_MS) {
      return get().reactions;
    }
    if (get().reactionsLoading) return get().reactions;
    set({ reactionsLoading: true, reactionsError: null });
    try {
      const snap = await api.worldModel.reactions();
      resetSurfaceError('station.reactions');
      set({
        reactions: snap,
        reactionsLoadedAt: Date.now(),
        reactionsLoading: false,
        wakeBarriers: {
          schema: 'wake_barriers_v1',
          generated_at: snap.generated_at,
          engine_armed: snap.engine_armed,
          engine_status: snap.engine_status,
          items: snap.awaiting_barriers,
        },
        wakeBarriersLoadedAt: Date.now(),
        wakeBarriersError: null,
      });
      return snap;
    } catch (e) {
      const message = reportSurfaceError(
        'station.reactions',
        e,
        'Failed to load reactions snapshot',
      );
      set({ reactionsError: message, reactionsLoading: false });
      return null;
    }
  },

  refreshWakeBarriers: async ({ force = false } = {}) => {
    const now = Date.now();
    const last = get().wakeBarriersLoadedAt ?? 0;
    if (!force && get().wakeBarriers && now - last < STATION_CACHE_MS) {
      return get().wakeBarriers;
    }
    if (get().wakeBarriersLoading) return get().wakeBarriers;
    set({ wakeBarriersLoading: true, wakeBarriersError: null });
    try {
      const snap = await api.worldModel.wakeBarriers();
      resetSurfaceError('station.wakeBarriers');
      set({
        wakeBarriers: snap,
        wakeBarriersLoadedAt: Date.now(),
        wakeBarriersLoading: false,
      });
      return snap;
    } catch (e) {
      const message = reportSurfaceError(
        'station.wakeBarriers',
        e,
        'Failed to load wake barriers',
      );
      set({ wakeBarriersError: message, wakeBarriersLoading: false });
      return null;
    }
  },

  // pri_119: cold-start reconciliation projection. Polled exactly like
  // reactions/wake-barriers (10s STATION_CACHE_MS, force flag for force-refresh
  // after operator-fire flows). Read-only — no setReconciliationState
  // counterpart because reconciliation has no FastAPI mutation surface.
  refreshReconciliation: async ({ force = false } = {}) => {
    const now = Date.now();
    const last = get().reconciliationLoadedAt ?? 0;
    if (!force && get().reconciliation && now - last < STATION_CACHE_MS) {
      return get().reconciliation;
    }
    if (get().reconciliationLoading) return get().reconciliation;
    set({ reconciliationLoading: true, reconciliationError: null });
    try {
      const snap = await api.worldModel.reconciliation();
      resetSurfaceError('station.reconciliation');
      set({
        reconciliation: snap,
        reconciliationLoadedAt: Date.now(),
        reconciliationLoading: false,
      });
      return snap;
    } catch (e) {
      const message = reportSurfaceError(
        'station.reconciliation',
        e,
        'Failed to load reconciliation snapshot',
      );
      set({ reconciliationError: message, reconciliationLoading: false });
      return null;
    }
  },

  previewOperation: async (operationId, parameters) => {
    const res = await api.worldModel.previewOperation({
      operation_id: operationId,
      parameters,
    });
    if (!res.ok || !res.preview) {
      throw new Error(res.error || 'Failed to preview operation');
    }
    return res.preview;
  },

  launchOperationById: async (operationId, parameters, actorId = 'human_operator') => {
    const launchKey = operationLaunchKey(operationId, parameters, actorId);
    const existingLaunch = operationLaunchesInFlight.get(launchKey);
    if (existingLaunch) return existingLaunch;

    const launchPromise = (async () => {
      const res = await api.worldModel.launchOperation({
        operation_id: operationId,
        parameters,
        actor_id: actorId,
      });
      if (!res.ok || !res.result) {
        throw new Error(res.error || 'Operation failed');
      }
      await Promise.allSettled([
        get().refreshLauncher({ force: true }),
        get().refreshAttention({ force: true }),
        get().refreshOperationsCatalog({ force: true }),
      ]);
      return res.result;
    })();

    operationLaunchesInFlight.set(launchKey, launchPromise);
    try {
      return await launchPromise;
    } finally {
      operationLaunchesInFlight.delete(launchKey);
    }
  },

  setLiveUpdatesPaused: (paused) => {
    set((state) => {
      const liveUpdates = {
        ...state.liveUpdates,
        paused,
      };
      return {
        liveUpdates: {
          ...liveUpdates,
          status: deriveLiveUpdateStatus(liveUpdates),
        },
      };
    });
  },

  markLiveUpdateSignal: (source) => {
    set((state) => ({
      liveUpdates: {
        ...state.liveUpdates,
        lastSignalAt: Date.now(),
        source,
      },
    }));
  },

  beginLiveUpdate: (source) => {
    set((state) => ({
      liveUpdates: {
        ...state.liveUpdates,
        inFlight: true,
        lastSignalAt: Date.now(),
        source,
        status: 'catching_up',
      },
    }));
  },

  completeLiveUpdate: (success) => {
    set((state) => {
      const lastSuccessfulRefreshAt = success
        ? Date.now()
        : state.liveUpdates.lastSuccessfulRefreshAt;
      const liveUpdates = {
        ...state.liveUpdates,
        inFlight: false,
        lastSuccessfulRefreshAt,
      };
      return {
        liveUpdates: {
          ...liveUpdates,
          status: deriveLiveUpdateStatus(liveUpdates),
        },
      };
    });
  },

  refreshLiveUpdateStatus: () => {
    const status = deriveLiveUpdateStatus(get().liveUpdates);
    set((state) => ({
      liveUpdates: {
        ...state.liveUpdates,
        status,
      },
    }));
    return status;
  },

  setReactionsState: async (body) => {
    try {
      const snap = await api.worldModel.setReactionsState(body);
      resetSurfaceError('station.reactions.state');
      set({
        reactions: snap,
        reactionsLoadedAt: Date.now(),
        reactionsError: null,
        wakeBarriers: {
          schema: 'wake_barriers_v1',
          generated_at: snap.generated_at,
          engine_armed: snap.engine_armed,
          engine_status: snap.engine_status,
          items: snap.awaiting_barriers,
        },
        wakeBarriersLoadedAt: Date.now(),
        wakeBarriersError: null,
      });
      return snap;
    } catch (e) {
      const message = reportSurfaceError(
        'station.reactions.state',
        e,
        'Failed to update reactions state',
      );
      set({ reactionsError: message });
      return null;
    }
  },

  orchestrationRefresh: async () => {
    set({ lastRefreshRequest: Date.now() });
    try {
      const res = await api.worldModel.orchestrationRefresh();
      if (res?.snapshot) {
        resetSurfaceError('station.refresh');
        set({
          attention: res.snapshot,
          attentionLoadedAt: Date.now(),
          attentionError: null,
        });
        if ((res.snapshot as AttentionSnapshot)?.reactions) {
          const reactions = (res.snapshot as AttentionSnapshot).reactions as ReactionsSnapshot;
          set({
            reactions,
            reactionsLoadedAt: Date.now(),
            reactionsError: null,
            wakeBarriers: {
              schema: 'wake_barriers_v1',
              generated_at: reactions.generated_at,
              engine_armed: reactions.engine_armed,
              engine_status: reactions.engine_status,
              items: reactions.awaiting_barriers,
            },
            wakeBarriersLoadedAt: Date.now(),
          });
        }
        return res.snapshot;
      }
      return null;
    } catch (e) {
      const message = reportSurfaceError(
        'station.refresh',
        e,
        'Failed to refresh orchestration',
      );
      set({ attentionError: message });
      return null;
    }
  },

  loadTopology: async (phaseRef, { force = false } = {}) => {
    const existing = get().topology[phaseRef];
    if (existing?.index && !force) return existing.index;
    try {
      const index = await api.worldModel.topologyIndex(phaseRef);
      resetSurfaceError(`station.topology:${phaseRef}`);
      set((s) => ({
        topology: {
          ...s.topology,
          [phaseRef]: {
            index,
            searches: existing?.searches ?? {},
            error: null,
            attempted: true,
          },
        },
      }));
      return index;
    } catch (e) {
      const message = reportSurfaceError(
        `station.topology:${phaseRef}`,
        e,
        'Failed to load topology',
      );
      set((s) => ({
        topology: {
          ...s.topology,
          [phaseRef]: {
            index: null,
            searches: existing?.searches ?? {},
            error: message,
            attempted: true,
          },
        },
      }));
      return null;
    }
  },

  searchTopology: async (phaseRef, params) => {
    const key = JSON.stringify(params);
    const existing = get().topology[phaseRef];
    const cached = existing?.searches?.[key];
    if (cached) return cached;
    try {
      const res = await api.worldModel.topologySearch(phaseRef, params);
      resetSurfaceError(`station.topology.search:${phaseRef}`);
      set((s) => {
        const prev = s.topology[phaseRef] ?? { index: null, searches: {} };
        return {
          topology: {
            ...s.topology,
            [phaseRef]: {
              index: prev.index,
              searches: { ...prev.searches, [key]: res },
            },
          },
        };
      });
      return res;
    } catch (e) {
      reportSurfaceError(
        `station.topology.search:${phaseRef}`,
        e,
        'Failed to search topology',
      );
      return null;
    }
  },
}));
