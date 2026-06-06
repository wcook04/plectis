// [PURPOSE] Station launchpad — orient, prioritize, route. Not a log surface.
//
// This page answers four questions fast:
//   1. Where am I?          (identity strip)
//   2. What needs attention? (deduped rollups, left)
//   3. What should I do?     (bounded next actions, below)
//   4. Where can I jump?     (compact chip strip at the bottom)
//
// Doctrine references:
//   pri_058 (everything visible at once), pri_062 (bounded decision load),
//   pri_110 (stale alarms), pri_104 (observability as safety).
//
// Design principles:
//   - One source of truth per incident. The alarm shows *age only*; the
//     attention panel shows what to do. We never paint the same sentence
//     into four panels.
//   - Recent tape is *grouped* by root summary, so 10 identical manual-
//     review events collapse into one row with a count.
//   - Primary navigation lives in Exoskeleton. This page adds a compact
//     jump strip for deep surfaces (Graph, Topology, Routes, Doctrine,
//     Drift, Archives) — chips, not tiles, to avoid chrome bloat.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import {
  Activity,
  ArrowRight,
  ChevronRight,
  Clock,
  Copy,
  Check,
  Pin,
  Play,
  RefreshCw,
  Signal,
  Workflow,
} from 'lucide-react';
import type {
  AttentionRecentChange,
  LaunchOperationResult,
  StationLauncherAlert,
  StationLauncherOperation,
  StationLauncherSnapshot,
  VantageResponse,
  VantageWorkSpineItem,
} from '../api';
import { api } from '../api';
import { useStation } from '../stores/useStation';
import { useZenith } from '../stores/useZenith';
import { getUiRuntimeContext, getZenithHostBridge, requestHostCommandPalette } from '../runtime';
import StaleAlarm from '../components/world/StaleAlarm';
import StateGuard from '../components/world/StateGuard';
import LiveUpdateBadge from '../components/world/LiveUpdateBadge';
import {
  buildDefaultOperationParams,
  launchStationOperation,
  operationResultPreview,
} from '../components/world/operationLaunchUtils';
import SurfaceMenuBar from '../components/navigation/SurfaceMenuBar';
import {
  PanelHead,
  SnapCell,
} from '../components/world/cellHelpers';
import {
  ageLabel,
  toneClasses,
  type Tone,
} from '../components/world/cellHelpers.utils';
import {
  getHomeTileSurfaces,
  getSurfaceEntryRoute,
  getSurfaceLabelForRoute,
  getShellSurfaceGroups,
  resolveSurfaceFromAlert,
  type SurfaceDefinition,
} from '../navigation/surfaces';
import {
  readRecentSurfaces,
  rememberRecentSurface,
  type RecentSurface,
} from '../navigation/recentSurfaces';
import { isCaptureModeEnabled, useCaptureBudgetBlocker, useCaptureDiagnostic } from '../lib/captureMode';

// ---------------------------------------------------------------------------
// Small building blocks
// ---------------------------------------------------------------------------

async function copyText(text: string): Promise<boolean> {
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return false;
    }
  }
  return false;
}

type HomeLayoutMode = 'standard' | 'compact-height';

function resolveHomeLayoutMode(width: number, height: number): HomeLayoutMode {
  return width >= 1280 && height <= 940 ? 'compact-height' : 'standard';
}

function readHomeViewportMetrics(): { width: number; height: number } {
  if (typeof window === 'undefined') {
    return { width: 0, height: 0 };
  }
  return { width: window.innerWidth, height: window.innerHeight };
}

function useHomeLayoutMode(): HomeLayoutMode {
  const [mode, setMode] = useState<HomeLayoutMode>(() => {
    const { width, height } = readHomeViewportMetrics();
    return resolveHomeLayoutMode(width, height);
  });

  useEffect(() => {
    const handleResize = () => {
      const { width, height } = readHomeViewportMetrics();
      setMode(resolveHomeLayoutMode(width, height));
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return mode;
}

// ---------------------------------------------------------------------------
// Incident rollup — one row = one actionable issue. No prose.
// ---------------------------------------------------------------------------

function alertTone(tone: StationLauncherAlert['tone']): Tone {
  if (tone === 'block') return 'block';
  if (tone === 'warn') return 'warn';
  if (tone === 'ok') return 'ok';
  return 'neutral';
}

function shortAlertLabel(label: string): string {
  // Strip the long instructional tail — the header carries the object, the
  // action button carries the fix. Keep it tight.
  const cut = label.indexOf('.');
  if (cut > 0 && cut < label.length - 1) return label.slice(0, cut);
  return label;
}

function IncidentRow({
  alert,
  onCopy,
  onOpen,
}: {
  alert: StationLauncherAlert;
  onCopy: (id: string, cmd: string) => void;
  onOpen?: (alert: StationLauncherAlert) => void;
}) {
  const tone = alertTone(alert.tone);
  const [copied, setCopied] = useState(false);
  const destination = resolveSurfaceFromAlert(alert);
  // Primary action is a navigation to the relevant surface — never Copy.
  // Copy is demoted to a secondary affordance for operators who want the CLI.
  const primaryLabel = `Open ${destination.label.toLowerCase()}`;
  return (
    <div
      className={clsx(
        'flex flex-col gap-1.5 rounded-[var(--zenith-radius-lg)] border px-3 py-[var(--zenith-space-2-5)]',
        toneClasses(tone),
      )}
    >
      <div className="flex items-start gap-2">
        <span
          aria-hidden
          className={clsx(
            'mt-1 h-1.5 w-1.5 rounded-full',
            tone === 'block' ? 'bg-rose-300 animate-pulse' :
            tone === 'warn' ? 'bg-amber-300' :
            tone === 'ok' ? 'bg-emerald-300' : 'bg-white/40',
          )}
        />
        <div className="min-w-0 flex-1">
          <div className="font-display text-[14px] uppercase tracking-[0.04em] text-white">
            {shortAlertLabel(alert.label)}
          </div>
          {alert.detail && (
            <div className="mt-0.5 line-clamp-2 text-[12px] leading-5 text-white/70">
              {alert.detail}
            </div>
          )}
        </div>
      </div>
      {(onOpen || alert.command) && (
        <div className="flex items-center gap-1.5">
          {onOpen && (
            <button
              type="button"
              onClick={() => onOpen(alert)}
              className="inline-flex items-center gap-1 rounded-full border border-white/25 bg-white/[0.08] px-[var(--zenith-space-2-5)] py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-white hover:border-white/40 hover:bg-white/[0.14]"
            >
              {primaryLabel} <ArrowRight size={10} />
            </button>
          )}
          {alert.command && (
            <button
              type="button"
              onClick={async () => {
                const ok = await copyText(alert.command!);
                if (ok) {
                  setCopied(true);
                  onCopy(alert.id, alert.command!);
                  window.setTimeout(() => setCopied(false), 1400);
                }
              }}
              title={alert.command}
              className="inline-flex shrink-0 items-center gap-1 rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-white/60 transition-colors hover:border-white/25 hover:text-white/85"
            >
              {copied ? <Check size={10} /> : <Copy size={10} />}
              {copied ? 'ok' : 'copy cmd'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Grouped recent changes — dedupe by summary slug, show count + latest age.
// ---------------------------------------------------------------------------

type RecentGroup = {
  key: string;
  summary: string;
  count: number;
  latestIso: string | null;
  driver: string | null;
  gateReason: string | null;
};

function summaryFingerprint(summary: string | null | undefined): string {
  const raw = (summary || '').trim().toLowerCase();
  if (!raw) return 'empty';
  // Normalize whitespace and trim to first 80 chars — enough to group the
  // repeated "missing review packet" family without collapsing distinct events.
  return raw.replace(/\s+/g, ' ').slice(0, 80);
}

function groupRecentChanges(
  changes: AttentionRecentChange[],
  limit = 3,
): RecentGroup[] {
  const order: string[] = [];
  const map = new Map<string, RecentGroup>();
  for (const change of changes) {
    const summary = change.summary ?? '—';
    const key = summaryFingerprint(summary);
    const existing = map.get(key);
    if (existing) {
      existing.count += 1;
      if (change.recorded_at && (!existing.latestIso || change.recorded_at > existing.latestIso)) {
        existing.latestIso = change.recorded_at;
      }
    } else {
      order.push(key);
      map.set(key, {
        key,
        summary,
        count: 1,
        latestIso: change.recorded_at ?? null,
        driver: change.active_driver ?? null,
        gateReason: change.gate_reason ?? null,
      });
    }
  }
  return order.slice(0, limit).map((k) => map.get(k)!);
}

// ---------------------------------------------------------------------------
// Snapshot derivation
// ---------------------------------------------------------------------------

type SnapshotCell = {
  label: string;
  value: string;
  detail?: string | null;
  tone: Tone;
};

type BridgeSummary = {
  status: 'live' | 'connected' | 'degraded' | 'gated';
  detail: string;
  tone: Tone;
};

function summarizeBridge(launcher: StationLauncherSnapshot): BridgeSummary {
  const providerCount = Math.max(0, launcher.bridge.provider_count ?? 0);
  const liveProviderCount = Math.max(0, launcher.bridge.live_provider_count ?? 0);
  const transportReady = launcher.bridge.browser_running && launcher.bridge.cdp_reachable;

  if (!transportReady) {
    return {
      status: 'gated',
      detail: `${liveProviderCount}/${providerCount} providers`,
      tone: 'warn',
    };
  }
  if (providerCount > 0 && liveProviderCount === 0) {
    return {
      status: 'degraded',
      detail: `${liveProviderCount}/${providerCount} providers live`,
      tone: 'warn',
    };
  }
  if (providerCount === 0) {
    return {
      status: 'connected',
      detail: 'provider inventory pending',
      tone: 'neutral',
    };
  }
  return {
    status: 'live',
    detail: `${liveProviderCount}/${providerCount} providers live`,
    tone: 'ok',
  };
}

function buildSnapshotCells(launcher: StationLauncherSnapshot): SnapshotCell[] {
  const phaseId = launcher.active_phase.phase_id ?? '—';
  const cycle = launcher.active_phase.cycle ?? '—';
  const gateRaw = launcher.orchestration.gate_reason;
  const gateNorm = (gateRaw ?? '').trim().toLowerCase();
  const gateActive = Boolean(gateRaw) && gateNorm !== '' && gateNorm !== 'none' && gateNorm !== '—' && gateNorm !== '-';
  const gate = gateActive ? gateRaw!.replace(/_/g, ' ') : 'clear';
  const bridge = summarizeBridge(launcher);
  const missionsReady = launcher.missions.ready;
  const missionsTotal = launcher.missions.total;
  const driverId = launcher.current_driver.actor_id || launcher.orchestration.active_driver || 'unclaimed';
  const handoffId = launcher.next_handoff.actor_id || 'none';
  const freshnessLabel = launcher.orchestration.freshness?.label ?? 'unknown';
  const freshnessTone = launcher.orchestration.freshness?.tone;

  const rsp = launcher.raw_seed_pipeline;
  const rsFresh = rsp.fresh_pending_bins ?? 0;
  const rsRoute = rsp.pending_routing_bins ?? 0;
  const rsTotal = rsp.total_bins ?? 0;
  const rsShards = rsp.atomized_shards ?? 0;
  const rsBlocked = rsFresh > 0 || rsRoute > 0;
  const rsDetail =
    rsFresh > 0
      ? `${rsFresh} fresh · ${rsRoute} route`
      : rsRoute > 0
        ? `${rsRoute} bins pending route`
        : `${rsShards}/${rsTotal} atomized`;

  return [
    {
      label: 'Control plane',
      value: freshnessLabel,
      detail: `gate · ${gate}`,
      tone: freshnessTone === 'expired' ? 'warn' : gateActive ? 'block' : 'ok',
    },
    {
      label: 'Phase',
      value: String(phaseId),
      detail: `cycle ${cycle}`,
      tone: 'neutral',
    },
    {
      label: 'Driver',
      value: driverId,
      detail: `next · ${handoffId}`,
      tone: launcher.current_driver.actor_id ? 'ok' : 'warn',
    },
    {
      label: 'Bridge',
      value: bridge.status,
      detail: bridge.detail,
      tone: bridge.tone,
    },
    {
      label: 'Missions',
      value: `${missionsReady}/${missionsTotal} ready`,
      detail: launcher.missions.blocked > 0 ? `${launcher.missions.blocked} blocked` : 'no blocks',
      tone: launcher.missions.blocked > 0 ? 'warn' : 'ok',
    },
    {
      label: 'Raw seed',
      value: rsBlocked ? rsDetail : 'coverage live',
      detail: rsBlocked ? 'route / review pending' : rsTotal > 0 ? `${rsTotal} bins` : 'no bins queued',
      tone: rsBlocked ? 'warn' : 'ok',
    },
  ];
}

// ---------------------------------------------------------------------------
// Shared surface registry — shell menus, home tiles, and recent-route labels
// all come from the same definitions.
// ---------------------------------------------------------------------------

const SHELL_GROUPS = getShellSurfaceGroups();
const HOME_TILES = getHomeTileSurfaces();

type LauncherTileBadge = { text: string; tone: Tone } | null;

function badgeForSurface(
  surface: SurfaceDefinition,
  launcher: StationLauncherSnapshot,
  operationCount: number,
): LauncherTileBadge {
  if (surface.id === 'approvals') {
    const pending = launcher.approvals?.total_pending ?? 0;
    return pending > 0
      ? { text: `${pending} pending`, tone: 'warn' }
      : { text: 'clear', tone: 'ok' };
  }

  if (surface.id === 'ops') {
    return {
      text: `${operationCount} ops`,
      tone: 'neutral',
    };
  }

  if (surface.id === 'launchpad') {
    const bridge = summarizeBridge(launcher);
    return {
      text: `bridge ${bridge.status}`,
      tone: bridge.tone,
    };
  }

  if (surface.id === 'missions') {
    const ready = launcher.missions?.ready ?? 0;
    const total = launcher.missions?.total ?? 0;
    const blocked = launcher.missions?.blocked ?? 0;
    return {
      text: blocked > 0 ? `${blocked} blocked` : `${ready}/${total} ready`,
      tone: blocked > 0 ? 'warn' : 'ok',
    };
  }

  if (surface.id === 'annexes') {
    const receipts = launcher.raw_seed_pipeline.surface_queue_entries ?? 0;
    return receipts > 0
      ? { text: `${receipts} queued`, tone: 'warn' }
      : { text: 'browse', tone: 'neutral' };
  }

  return null;
}

function LauncherTile({
  surface,
  launcher,
  operationCount,
  onNavigate,
}: {
  surface: SurfaceDefinition;
  launcher: StationLauncherSnapshot;
  operationCount: number;
  onNavigate: (route: string, label: string) => void;
}) {
  const Icon = surface.icon;
  const badge = badgeForSurface(surface, launcher, operationCount);
  const route = getSurfaceEntryRoute(surface) ?? surface.route;
  return (
    <button
      type="button"
      onClick={() => onNavigate(route, surface.label)}
      className="group flex h-[72px] flex-col justify-between gap-0.5 rounded-[var(--zenith-radius-sm)] border border-white/[0.10] bg-white/[0.02] px-[var(--zenith-space-2-5)] py-1.5 text-left transition-all hover:border-white/35 hover:bg-white/[0.06] focus:outline-none focus:ring-1 focus:ring-white/30"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <Icon size={12} className="shrink-0 text-white/70 group-hover:text-white" />
          <span className="truncate font-display text-[12.5px] uppercase tracking-[0.04em] text-white">
            {surface.label}
          </span>
        </div>
        {badge && (
          <span
            className={clsx(
              'shrink-0 rounded-full border px-1.5 py-[1px] font-mono text-[8.5px] uppercase tracking-[0.16em]',
              toneClasses(badge.tone),
            )}
          >
            {badge.text}
          </span>
        )}
      </div>
      <p className="line-clamp-2 text-[10.5px] leading-[1.3] text-white/50">
        {surface.purpose}
      </p>
    </button>
  );
}

function ApprovalsSummaryCard({
  launcher,
  onNavigate,
  compact = false,
}: {
  launcher: StationLauncherSnapshot;
  onNavigate: (route: string, label: string) => void;
  compact?: boolean;
}) {
  const approvals = launcher.approvals;
  const pending = approvals?.total_pending ?? 0;
  const decide = approvals?.action_kind_counts?.decide ?? 0;
  const reviewOnly = approvals?.action_kind_counts?.review_only ?? 0;
  const top = approvals?.top_records?.[0] ?? null;

  return (
    <section className={clsx('panel flex flex-col', compact ? 'min-h-0 flex-1' : 'shrink-0')}>
      <PanelHead
        kicker="Approvals"
        title={pending > 0 ? `${pending} pending` : 'Inbox clear'}
        trailing={
          <button
            type="button"
            onClick={() => onNavigate('/station/approvals', 'Approvals')}
            className="inline-flex items-center gap-1 rounded-full border border-zenith-edge-faint bg-white/[0.04] px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/80 transition-colors hover:border-white/30 hover:text-white"
          >
            Open <ArrowRight size={11} />
          </button>
        }
      />
      <div className="panel-body-padded flex flex-col gap-[var(--zenith-space-2-5)]">
        <div className="grid gap-1.5 sm:grid-cols-3">
          <div className="rounded-[var(--zenith-radius-md)] border border-white/[0.10] bg-black/20 px-3 py-2">
            <div className="panel-kicker">Pending</div>
            <div className="mt-1 font-display text-[20px] uppercase tracking-[0.05em] text-white">
              {pending}
            </div>
          </div>
          <div className="rounded-[var(--zenith-radius-md)] border border-white/[0.10] bg-black/20 px-3 py-2">
            <div className="panel-kicker">Direct</div>
            <div className="mt-1 font-display text-[20px] uppercase tracking-[0.05em] text-white">
              {decide}
            </div>
          </div>
          <div className="rounded-[var(--zenith-radius-md)] border border-white/[0.10] bg-black/20 px-3 py-2">
            <div className="panel-kicker">Review only</div>
            <div className="mt-1 font-display text-[20px] uppercase tracking-[0.05em] text-white">
              {reviewOnly}
            </div>
          </div>
        </div>
        {top ? (
          <div className="rounded-[var(--zenith-radius-lg)] border border-white/[0.10] bg-[linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] px-3 py-[var(--zenith-space-2-5)]">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="panel-kicker">Next up</span>
              <span className="rounded-full border border-white/[0.12] bg-white/[0.03] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.16em] text-white/75">
                {(top.severity ?? 'P3').toUpperCase()}
              </span>
              <span className="rounded-full border border-white/[0.12] bg-white/[0.03] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.16em] text-white/75">
                {top.action_kind === 'decide' ? 'direct decision' : 'review only'}
              </span>
            </div>
            <div className="mt-2 font-display text-[16px] uppercase tracking-[0.04em] text-white">
              {top.title}
            </div>
            <p className="mt-1 text-[12px] leading-5 text-[var(--zenith-soft)]">
              {top.detail}
            </p>
          </div>
        ) : (
          <div className={clsx('rounded-[var(--zenith-radius-md)] border px-3 py-2 text-[12px]', toneClasses('ok'))}>
            No approval rows are waiting.
          </div>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Continue where you left off — 3 most recently visited surfaces.
// ---------------------------------------------------------------------------

function ContinueCard({
  recent,
  onNavigate,
  compact = false,
}: {
  recent: RecentSurface[];
  onNavigate: (route: string, label: string) => void;
  compact?: boolean;
}) {
  if (recent.length === 0) {
    const suggestions = getHomeTileSurfaces().slice(0, 3);
    return (
      <section className={clsx('panel flex flex-col', compact ? 'min-h-0 flex-1' : 'shrink-0')}>
        <PanelHead
          kicker="Suggested"
          title="Start here"
          trailing={
            <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted">
              no recent
            </span>
          }
        />
        <div className={compact ? 'panel-body' : undefined}>
          <ul className="panel-divide">
            {suggestions.map((surface) => {
              const Icon = surface.icon;
              const route = getSurfaceEntryRoute(surface) ?? surface.route;
              return (
                <li key={route}>
                  <button
                    type="button"
                    onClick={() => onNavigate(route, surface.label)}
                    className="row-tile w-full items-center text-left hover:bg-white/[0.03]"
                  >
                    <Icon size={11} className="shrink-0 text-zenith-muted" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate font-mono text-[11.5px] text-white/90">
                          {surface.label}
                        </span>
                        <span className="ml-auto shrink-0 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted">
                          suggest
                        </span>
                      </div>
                      <div className="truncate font-mono text-[9.5px] text-zenith-muted">
                        {route}
                      </div>
                    </div>
                    <ChevronRight size={11} className="shrink-0 text-white/30" />
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </section>
    );
  }
  return (
    <section className={clsx('panel flex flex-col', compact ? 'min-h-0 flex-1' : 'shrink-0')}>
      <PanelHead kicker="Continue" title="Where you left off" />
      <div className={compact ? 'panel-body' : undefined}>
        <ul className="panel-divide">
          {recent.slice(0, 3).map((item) => (
            <li key={item.route}>
              <button
                type="button"
                onClick={() => onNavigate(item.route, item.label)}
                className="row-tile w-full items-center text-left hover:bg-white/[0.03]"
              >
                <Clock size={11} className="shrink-0 text-zenith-muted" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate font-mono text-[11.5px] text-white/90">
                      {item.label}
                    </span>
                    <span className="ml-auto shrink-0 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted">
                      {ageLabel(new Date(item.at).toISOString())}
                    </span>
                  </div>
                  <div className="truncate font-mono text-[9.5px] text-zenith-muted">
                    {item.route}
                  </div>
                </div>
                <ChevronRight size={11} className="shrink-0 text-white/30" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Pinned procedures — three fixed ops, one-click launch, always accessible.
// ---------------------------------------------------------------------------

const PINNED_OP_IDS = [
  'overnight_raw_seed_chain_launch',
  'raw_seed_route_review',
  'raw_seed_sync_handoff_launch',
];

function PinnedOpsCard({
  operations,
  loading,
  excludeIds,
  launchingOperationId,
  onLaunch,
  onOpenOps,
  compact = false,
}: {
  operations: StationLauncherOperation[];
  loading: boolean;
  excludeIds: Set<string>;
  launchingOperationId: string | null;
  onLaunch: (op: StationLauncherOperation) => void;
  onOpenOps: () => void;
  compact?: boolean;
}) {
  const pinned: StationLauncherOperation[] = [];
  const seen = new Set<string>();
  for (const id of PINNED_OP_IDS) {
    if (excludeIds.has(id) || seen.has(id)) continue;
    const op = operations.find((o) => o.operation_id === id);
    if (op) {
      pinned.push(op);
      seen.add(op.operation_id);
    }
  }
  // Top up from remaining ops so the card isn't hollow.
  for (const op of operations) {
    if (pinned.length >= 6) break;
    if (excludeIds.has(op.operation_id) || seen.has(op.operation_id)) continue;
    pinned.push(op);
    seen.add(op.operation_id);
  }
  if (pinned.length === 0) {
    return (
      <section className={clsx('panel flex flex-col', compact ? 'min-h-0 flex-1' : 'shrink-0')}>
        <PanelHead
          title="Quick launch"
          trailing={
            <button
              onClick={onOpenOps}
              className="inline-flex items-center gap-1 rounded-full border border-zenith-edge-faint bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-white/80 hover:border-white/30 hover:text-white"
            >
              Ops deck <ArrowRight size={10} />
            </button>
          }
        />
        {loading ? (
          <ul className="panel-divide" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <li key={i} className="row-tile items-center">
                <div className="h-2.5 w-2.5 shrink-0 rounded-sm bg-white/[0.06] animate-pulse" />
                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="h-3 w-2/5 rounded bg-white/[0.06] animate-pulse" />
                  <div className="h-2 w-3/5 rounded bg-white/[0.04] animate-pulse" />
                </div>
                <div className="h-5 w-14 shrink-0 rounded-full bg-white/[0.05] animate-pulse" />
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    );
  }
  return (
    <section className={clsx('panel flex flex-col', compact ? 'min-h-0 flex-1' : 'shrink-0')}>
      <PanelHead
        title="Quick launch"
        trailing={
          <button
            onClick={onOpenOps}
            className="inline-flex items-center gap-1 rounded-full border border-zenith-edge-faint bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-white/80 hover:border-white/30 hover:text-white"
          >
            All ops <ArrowRight size={10} />
          </button>
        }
      />
      <div className={compact ? 'panel-body' : undefined}>
        <ul className="panel-divide">
          {pinned.map((op) => {
            const busy = launchingOperationId === op.operation_id;
            return (
              <li key={op.operation_id} className="row-tile items-center">
                <Pin size={11} className="shrink-0 text-zenith-muted" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate font-mono text-[11.5px] text-white/90">
                      {op.label}
                    </span>
                  </div>
                  {op.description_short && (
                    <div className="line-clamp-1 text-[10.5px] leading-[1.3] text-zenith-muted">
                      {op.description_short}
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => onLaunch(op)}
                  disabled={launchingOperationId != null}
                  className="inline-flex shrink-0 items-center gap-1 rounded-full border border-white/20 bg-white/[0.06] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.16em] text-white hover:border-white/35 hover:bg-white/[0.12] disabled:cursor-wait disabled:opacity-60"
                >
                  {busy ? <Activity size={10} className="animate-pulse" /> : <Play size={10} />}
                  {busy ? 'run' : 'launch'}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Pulse — small live-data panel showing the pipeline heartbeat.
// ---------------------------------------------------------------------------

function PulseCard({ launcher }: { launcher: StationLauncherSnapshot }) {
  const rsp = launcher.raw_seed_pipeline;
  const bridge = summarizeBridge(launcher);
  const freshIso = launcher.orchestration.freshness?.iso ?? null;
  const shards = rsp.atomized_shards ?? 0;
  const total = rsp.total_bins ?? 0;
  const coverage = total > 0 ? Math.round((shards / total) * 100) : 0;
  const stats: Array<{ label: string; value: string; tone: Tone }> = [
    {
      label: 'last event',
      value: ageLabel(freshIso),
      tone: 'neutral',
    },
    {
      label: 'bridge',
      value:
        bridge.status === 'connected'
          ? 'engine ready'
          : `${launcher.bridge.live_provider_count}/${launcher.bridge.provider_count} live`,
      tone: bridge.tone,
    },
    {
      label: 'coverage',
      value: total > 0 ? `${coverage}%` : '—',
      tone: coverage >= 80 ? 'ok' : coverage >= 40 ? 'warn' : 'neutral',
    },
    {
      label: 'shards',
      value: `${shards}/${total}`,
      tone: 'neutral',
    },
  ];
  return (
    <section className="panel shrink-0">
      <PanelHead
        title="Pipeline heartbeat"
        trailing={
          <span className="inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted">
            <Signal
              size={10}
              className={bridge.tone === 'ok' ? 'text-emerald-300' : bridge.tone === 'neutral' ? 'text-white/50' : 'text-amber-300'}
            />
            {bridge.status}
          </span>
        }
      />
      <div className="panel-body-padded grid grid-cols-4 gap-1.5">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className={clsx('min-w-0 rounded-[var(--zenith-radius-xs)] border px-2 py-1.5', toneClasses(stat.tone))}
          >
            <div className="font-mono text-[8.5px] uppercase tracking-[0.18em] text-zenith-soft">
              {stat.label}
            </div>
            <div className="mt-0.5 truncate font-mono text-[12px] leading-tight text-white">
              {stat.value}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

type VantageResponseWithEnvelope = VantageResponse & {
  constitution_workspace?: {
    current_state?: Record<string, unknown> | null;
  } | null;
  frontier_delta?: {
    status?: string | null;
  } | null;
  surface_contract?: {
    command?: string | null;
  } | null;
};

function stringField(record: Record<string, unknown> | null | undefined, key: string): string | null {
  const value = record?.[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function VantageFlagCard({
  payload,
  loading,
  error,
  onRefresh,
  onNavigate,
}: {
  payload: VantageResponse | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  onNavigate: (route: string, label: string) => void;
}) {
  const packet = payload as VantageResponseWithEnvelope | null;
  const currentState = packet?.constitution_workspace?.current_state ?? payload?.current_state ?? null;
  const activePhase = stringField(currentState, 'active_phase_id') ?? 'unknown';
  const topAction = payload?.where_to_act_now?.[0] ?? null;
  const tensionCount = payload?.open_tensions?.length ?? 0;
  const actionCount = payload?.where_to_act_now?.length ?? 0;
  const sourceCommand = packet?.surface_contract?.command ?? './repo-python kernel.py --vantage --band flag';

  return (
    <section className="panel shrink-0" data-capture-label="kernel_vantage_flag">
      <PanelHead
        kicker="Kernel"
        title="Vantage"
        trailing={
          <div className="flex items-center gap-1.5">
            <span
              className={clsx(
                'pill',
                error ? 'pill-block' : payload?.ok ? 'pill-ok' : loading ? 'pill' : 'pill-warn',
              )}
            >
              {error ? 'failed' : payload?.status ?? (loading ? 'loading' : 'pending')}
            </span>
            <button
              type="button"
              onClick={onRefresh}
              className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-zenith-edge-faint bg-white/[0.04] text-zenith-soft transition-colors hover:border-white/30 hover:text-white"
              aria-label="Refresh kernel vantage"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : undefined} />
            </button>
            <button
              type="button"
              onClick={() => onNavigate('/station/vantage', 'Vantage')}
              className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-zenith-edge-faint bg-white/[0.04] text-zenith-soft transition-colors hover:border-white/30 hover:text-white"
              aria-label="Open Vantage"
            >
              <ArrowRight size={12} />
            </button>
          </div>
        }
      />
      <div className="panel-body-padded space-y-2">
        {error ? (
          <div className="rounded-[var(--zenith-radius-md)] border border-rose-400/25 bg-rose-500/[0.08] px-3 py-2 text-[11.5px] leading-5 text-rose-100">
            Vantage route failed. {error}
          </div>
        ) : loading && !payload ? (
          <div className="rounded-[var(--zenith-radius-md)] border border-white/[0.10] bg-black/20 px-3 py-2 font-mono text-[11px] uppercase tracking-[0.18em] text-zenith-muted">
            Loading kernel vantage flag packet
          </div>
        ) : null}

        <div className="grid grid-cols-3 gap-1.5">
          <div className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
            <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">
              phase
            </div>
            <div className="truncate font-mono text-[12px] text-white/85">
              {activePhase}
            </div>
          </div>
          <div className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
            <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">
              actions
            </div>
            <div className="truncate font-mono text-[12px] text-white/85">
              {actionCount}
            </div>
          </div>
          <div className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
            <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">
              tensions
            </div>
            <div className="truncate font-mono text-[12px] text-white/85">
              {tensionCount}
            </div>
          </div>
        </div>

        {topAction && (
          <div className="rounded-[var(--zenith-radius-md)] border border-white/[0.10] bg-black/20 px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              <div className="truncate font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted">
                {topAction.kind?.replace(/[_-]/g, ' ') ?? 'next action'}
              </div>
              <span className="font-mono text-[9px] text-zenith-muted">
                p{topAction.priority ?? '-'}
              </span>
            </div>
            {topAction.reason && (
              <div className="mt-1 line-clamp-2 text-[11.5px] leading-4 text-[var(--zenith-soft)]">
                {topAction.reason}
              </div>
            )}
            {topAction.command && (
              <div className="mt-1 truncate rounded-[var(--zenith-radius-xs)] bg-white/[0.035] px-2 py-1 font-mono text-[9.5px] text-white/42">
                {topAction.command}
              </div>
            )}
          </div>
        )}

        <div
          className="truncate font-mono text-[9px] uppercase tracking-[0.16em] text-zenith-muted"
          title={`${sourceCommand} / /api/world-model/vantage`}
        >
          {sourceCommand} / /api/world-model/vantage
        </div>
      </div>
    </section>
  );
}

function readinessTone(state: string | null | undefined): Tone {
  const normalized = (state ?? '').toLowerCase();
  if (['done', 'signoff', 'retired'].includes(normalized)) return 'warn';
  if (['claimed', 'active', 'ready', 'shaping', 'captured'].includes(normalized)) return 'ok';
  if (['blocked'].includes(normalized)) return 'block';
  return 'neutral';
}

type WorkSpineQueueItem = VantageWorkSpineItem & {
  sequence?: number | null;
  source_ref?: string | null;
  queue_role?: string | null;
};
type WorkSpineCurrentNext = NonNullable<NonNullable<VantageResponse['work_spine']>['current_next']>;

function positiveCount(value: number | null | undefined): number {
  return typeof value === 'number' && value > 0 ? value : 0;
}

function queueItemEvidenceLabel(item: WorkSpineQueueItem): string {
  if (item.source_ref) return item.source_ref.split('/').pop() ?? item.source_ref;
  const sourceViews = item.source_views?.filter(Boolean) ?? [];
  if (sourceViews.length > 0) return sourceViews.slice(0, 2).join(' / ');
  return 'task_ledger card';
}

function queueItemDependencyLine(item: WorkSpineQueueItem): string {
  const dependency = item.dependency_status;
  if (!dependency) return queueItemEvidenceLabel(item);
  const parts: string[] = [];
  if (dependency.schedulable != null) parts.push(dependency.schedulable ? 'schedulable' : 'waiting');
  if (dependency.hard_dep_count != null) parts.push(`${dependency.hard_dep_count} hard`);
  const unsatisfied = positiveCount(dependency.unsatisfied_dep_count);
  const dangling = positiveCount(dependency.dangling_dep_count);
  const downstream = positiveCount(dependency.downstream_unlock_count);
  if (unsatisfied > 0) parts.push(`${unsatisfied} unsatisfied`);
  if (dangling > 0) parts.push(`${dangling} dangling`);
  if (downstream > 0) parts.push(`${downstream} unlocks`);
  return parts.length > 0 ? parts.join(' · ') : queueItemEvidenceLabel(item);
}

function queueItemActionLabel(item: WorkSpineQueueItem): string {
  const state = (item.state ?? '').toLowerCase();
  const dependency = item.dependency_status;
  const unsatisfied = positiveCount(dependency?.unsatisfied_dep_count);
  const dangling = positiveCount(dependency?.dangling_dep_count);
  const missingContracts =
    item.contract_status?.missing_contracts?.length ?? item.missing_contracts?.length ?? 0;
  if (unsatisfied > 0) return `clear ${unsatisfied} deps`;
  if (dangling > 0) return `repair ${dangling} deps`;
  if (missingContracts > 0) return `shape ${missingContracts} contracts`;
  if (item.signoff_required || ['done', 'signoff'].includes(state)) return 'sign off';
  if (dependency?.schedulable === true && ['captured', 'shaping', 'ready'].includes(state)) return 'claim next';
  if (positiveCount(dependency?.downstream_unlock_count) > 0) return 'finish unlock';
  return item.recommended_action ?? 'open detail';
}

function collectOperatorQueueItems(
  workSpine: VantageResponse['work_spine'] | null | undefined,
  current: WorkSpineCurrentNext | null | undefined,
): WorkSpineQueueItem[] {
  const items: WorkSpineQueueItem[] = [];
  const seen = new Set<string>();
  const pushItem = (item: WorkSpineQueueItem | null | undefined, role: string) => {
    if (!item?.id || seen.has(item.id)) return;
    seen.add(item.id);
    items.push({ ...item, queue_role: role });
  };

  pushItem(current as WorkSpineQueueItem | null | undefined, 'current_next');
  for (const bucketKey of ['top_ready', 'blockers', 'signoff_needs', 'bridge_assignable', 'active_wip']) {
    const bucket = workSpine?.buckets?.[bucketKey];
    if (!bucket) continue;
    for (const item of bucket.sample_items ?? []) {
      pushItem(item, bucket.label ?? bucketKey.replace(/_/g, ' '));
      if (items.length >= 4) return items;
    }
  }
  return items.slice(0, 4);
}

function LaunchReadinessCard({
  payload,
  onNavigate,
}: {
  payload: VantageResponse | null;
  onNavigate: (route: string, label: string) => void;
}) {
  const workSpine = payload?.work_spine ?? null;
  const current = workSpine?.current_next ?? null;
  const command =
    current?.drilldown_command ??
    workSpine?.drilldown_command ??
    './repo-python kernel.py --option-surface task_ledger --band cluster_flag';
  const sourceRef =
    current?.source_ref ??
    workSpine?.source_refs?.find((ref) => ref.includes('frontend_demo_readiness_queue')) ??
    workSpine?.source_refs?.[0] ??
    'frontend_demo_readiness_queue.json';
  const sourceName = sourceRef.split('/').pop() ?? sourceRef;
  const bucketEntries = Object.entries(workSpine?.totals ?? {}).slice(0, 4);
  const operatorQueueItems = collectOperatorQueueItems(workSpine, current);
  const tone = readinessTone(current?.state);

  return (
    <section className="panel shrink-0" data-capture-label="frontend_launch_readiness_queue">
      <PanelHead
        kicker="Launch readiness"
        title="Frontend queue"
        trailing={
          <button
            type="button"
            onClick={() => onNavigate('/station/ledger', 'Ledger')}
            className="inline-flex items-center gap-1 rounded-full border border-zenith-edge-faint bg-white/[0.04] px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/80 transition-colors hover:border-white/30 hover:text-white"
          >
            Ledger <ArrowRight size={11} />
          </button>
        }
      />
      <div className="panel-body-padded space-y-2">
        <div className={clsx('rounded-[var(--zenith-radius-md)] border px-3 py-[var(--zenith-space-2-5)]', toneClasses(tone))}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted">
                current_next
              </div>
              <div className="mt-1 line-clamp-2 text-[13px] leading-5 text-white">
                {current?.title ?? 'No active launch-readiness WorkItem published.'}
              </div>
            </div>
            <span className="shrink-0 rounded-full border border-zenith-edge-faint bg-black/20 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-soft">
              {current?.state ?? 'unknown'}
            </span>
          </div>
          <div className="mt-2 grid grid-cols-3 gap-1.5">
            <div className="min-w-0 rounded-[var(--zenith-radius-xs)] border border-white/10 bg-black/20 px-2 py-1">
              <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">id</div>
              <div className="truncate font-mono text-[10.5px] text-white/80">{current?.id ?? 'none'}</div>
            </div>
            <div className="min-w-0 rounded-[var(--zenith-radius-xs)] border border-white/10 bg-black/20 px-2 py-1">
              <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">sequence</div>
              <div className="truncate font-mono text-[10.5px] text-white/80">
                {current?.sequence ?? '—'}
              </div>
            </div>
            <div className="min-w-0 rounded-[var(--zenith-radius-xs)] border border-white/10 bg-black/20 px-2 py-1">
              <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">source</div>
              <div className="truncate font-mono text-[10.5px] text-white/80" title={sourceRef}>
                {sourceName}
              </div>
            </div>
          </div>
        </div>

        {bucketEntries.length > 0 && (
          <div className="grid grid-cols-2 gap-1.5 md:grid-cols-4">
            {bucketEntries.map(([bucket, count]) => (
              <div key={bucket} className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
                <div className="truncate font-mono text-[8px] uppercase tracking-[0.16em] text-zenith-muted">
                  {bucket.replace(/_/g, ' ')}
                </div>
                <div className="mt-0.5 font-mono text-[12px] text-white/82">
                  {count}
                </div>
              </div>
            ))}
          </div>
        )}

        {operatorQueueItems.length > 0 && (
          <div className="space-y-1.5" data-capture-label="operator_frontend_queue_actions">
            <div className="flex items-center justify-between gap-2">
              <div className="font-mono text-[8.5px] uppercase tracking-[0.18em] text-zenith-muted">
                operator queue
              </div>
              <div className="font-mono text-[8.5px] uppercase tracking-[0.16em] text-white/38">
                detail-bound
              </div>
            </div>
            {operatorQueueItems.map((item) => {
              const detailCommand = item.drilldown_command ?? command;
              const itemId = item.id ?? 'unknown';
              return (
                <div
                  key={itemId}
                  className="rounded-[var(--zenith-radius-sm)] border border-white/[0.10] bg-black/20 px-[var(--zenith-space-2-5)] py-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex min-w-0 items-center gap-1.5">
                        <span className="shrink-0 rounded-full border border-white/[0.10] bg-white/[0.035] px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-[0.14em] text-white/55">
                          {queueItemActionLabel(item)}
                        </span>
                        <span className="truncate font-mono text-[8px] uppercase tracking-[0.14em] text-zenith-muted">
                          {item.queue_role ?? 'task'}
                        </span>
                      </div>
                      <div className="mt-1 line-clamp-1 text-[11.5px] leading-4 text-white/86">
                        {item.title ?? itemId}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => onNavigate('/station/ledger', 'Ledger')}
                      aria-label={`Open ${itemId} detail`}
                      title={detailCommand}
                      className="shrink-0 rounded-full border border-zenith-edge-faint bg-white/[0.04] px-2 py-0.5 font-mono text-[8.5px] uppercase tracking-[0.16em] text-white/70 transition-colors hover:border-white/30 hover:text-white"
                    >
                      Detail
                    </button>
                  </div>
                  <div className="mt-1 grid grid-cols-[minmax(0,1fr)_minmax(0,0.75fr)] gap-1.5">
                    <div className="truncate font-mono text-[9px] text-white/45" title={queueItemDependencyLine(item)}>
                      {queueItemDependencyLine(item)}
                    </div>
                    <div className="truncate text-right font-mono text-[9px] text-white/38" title={queueItemEvidenceLabel(item)}>
                      {queueItemEvidenceLabel(item)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="truncate rounded-[var(--zenith-radius-xs)] bg-white/[0.035] px-2 py-1 font-mono text-[9.5px] text-white/42" title={command}>
          {command}
        </div>
      </div>
    </section>
  );
}

function PhaseTodoHudCard({
  launcher,
  payload,
  onNavigate,
}: {
  launcher: StationLauncherSnapshot;
  payload: VantageResponse | null;
  onNavigate: (route: string, label: string) => void;
}) {
  const workSpine = payload?.work_spine ?? null;
  const current = workSpine?.current_next ?? null;
  const activePhase = launcher.active_phase;
  const phaseId = activePhase.phase_id ?? 'unknown';
  const phaseStage = activePhase.stage ?? 'stage pending';
  const phaseCycle = activePhase.cycle != null ? `cycle ${activePhase.cycle}` : 'cycle pending';
  const gateRaw = launcher.orchestration.gate_reason?.trim();
  const gateLabel = gateRaw && !['none', '—', '-'].includes(gateRaw.toLowerCase())
    ? gateRaw.replace(/_/g, ' ')
    : 'clear';
  const bucketOrder = ['top_ready', 'signoff_needs', 'blockers', 'active_wip'];
  const buckets = bucketOrder.map((key) => ({
    key,
    label: workSpine?.buckets?.[key]?.label ?? key.replace(/_/g, ' '),
    count: workSpine?.buckets?.[key]?.count ?? workSpine?.totals?.[key] ?? 0,
  }));
  const bridgeBucket = workSpine?.buckets?.bridge_assignable ?? null;
  const currentTitle = current?.title?.toLowerCase() ?? '';
  const currentIsBridgePacket =
    current?.candidate_work_item_type === 'bridge_action' ||
    current?.work_item_type === 'bridge_action' ||
    (currentTitle.includes('bridge') && currentTitle.includes('packet'));
  const bridgeItem = bridgeBucket?.sample_items?.[0] ?? (currentIsBridgePacket ? current : null);
  const bridgeCount = bridgeBucket?.count ?? workSpine?.totals?.bridge_assignable ?? 0;
  const bridgePosture = bridgeCount > 0 ? `${bridgeCount} ready` : currentIsBridgePacket ? 'active' : '0 ready';
  const bridgeCommand =
    bridgeItem?.drilldown_command ??
    bridgeBucket?.omission_receipt?.drilldown_command ??
    './repo-python kernel.py --option-surface task_ledger --band card --ids cap_012';
  const command =
    current?.drilldown_command ??
    workSpine?.drilldown_command ??
    './repo-python kernel.py --option-surface task_ledger --band cluster_flag';
  const tone = gateLabel === 'clear' ? readinessTone(current?.state) : 'warn';

  return (
    <section className="panel shrink-0" data-capture-label="phase_latest_todo_hud">
      <PanelHead
        kicker="Phase"
        title="Todo HUD"
        trailing={
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => onNavigate('/station/phase', 'Phase')}
              className="inline-flex items-center gap-1 rounded-full border border-zenith-edge-faint bg-white/[0.04] px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/80 transition-colors hover:border-white/30 hover:text-white"
            >
              Phase <ArrowRight size={11} />
            </button>
            <button
              type="button"
              onClick={() => onNavigate('/station/ledger', 'Ledger')}
              className="inline-flex items-center gap-1 rounded-full border border-zenith-edge-faint bg-white/[0.04] px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/80 transition-colors hover:border-white/30 hover:text-white"
            >
              Ledger <ArrowRight size={11} />
            </button>
          </div>
        }
      />
      <div className="panel-body-padded space-y-2">
        <div className="grid grid-cols-3 gap-1.5">
          <div className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
            <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">
              active phase
            </div>
            <div className="truncate font-mono text-[12px] text-white/85" title={activePhase.title ?? undefined}>
              {phaseId}
            </div>
          </div>
          <div className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
            <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">
              lifecycle
            </div>
            <div className="truncate font-mono text-[12px] text-white/85" title={`${phaseStage} · ${phaseCycle}`}>
              {phaseStage}
            </div>
          </div>
          <div className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
            <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">
              gate
            </div>
            <div className="truncate font-mono text-[12px] text-white/85">
              {gateLabel}
            </div>
          </div>
        </div>

        <div
          className="rounded-[var(--zenith-radius-sm)] border border-sky-300/20 bg-sky-300/[0.055] px-3 py-2"
          data-capture-label="bridge_packet_hud"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="font-mono text-[8.5px] uppercase tracking-[0.18em] text-sky-100/45">
                bridge packet
              </div>
              <div className="mt-1 line-clamp-2 text-[12.5px] leading-5 text-white/90">
                {bridgeItem?.title ?? 'No bridge/HUD packet queued.'}
              </div>
            </div>
            <span className="shrink-0 rounded-full border border-sky-200/20 bg-black/20 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-sky-100/70">
              {bridgePosture}
            </span>
          </div>
          <div className="mt-2 flex min-w-0 items-center justify-between gap-2">
            <div
              className="min-w-0 truncate font-mono text-[9.5px] text-sky-100/45"
              title={bridgeItem?.id ?? undefined}
            >
              {bridgeItem?.id ?? 'none'} · {bridgeItem?.state ?? 'clear'} · Task Ledger advisory only
            </div>
            <button
              type="button"
              onClick={() => onNavigate('/station/ledger', 'Ledger')}
              className="shrink-0 rounded-full border border-sky-200/20 bg-white/[0.035] px-2 py-0.5 font-mono text-[8.5px] uppercase tracking-[0.16em] text-sky-100/75 transition-colors hover:border-sky-100/35 hover:text-white"
              title={bridgeCommand}
            >
              Ledger
            </button>
          </div>
        </div>

        <div className={clsx('rounded-[var(--zenith-radius-md)] border px-3 py-[var(--zenith-space-2-5)]', toneClasses(tone))}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted">
                latest todo
              </div>
              <div className="mt-1 line-clamp-2 text-[13px] leading-5 text-white">
                {current?.title ?? 'No active Task Ledger current_next published.'}
              </div>
            </div>
            <span className="shrink-0 rounded-full border border-zenith-edge-faint bg-black/20 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-soft">
              {current?.state ?? 'unknown'}
            </span>
          </div>
          <div className="mt-2 truncate font-mono text-[9.5px] text-zenith-muted" title={current?.id ?? undefined}>
            {current?.id ?? 'none'} · {phaseCycle}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-1.5 md:grid-cols-4">
          {buckets.map((bucket) => (
            <div key={bucket.key} className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
              <div className="truncate font-mono text-[8px] uppercase tracking-[0.16em] text-zenith-muted">
                {bucket.label}
              </div>
              <div className="mt-0.5 font-mono text-[12px] text-white/82">
                {bucket.count}
              </div>
            </div>
          ))}
        </div>

        <div className="truncate rounded-[var(--zenith-radius-xs)] bg-white/[0.035] px-2 py-1 font-mono text-[9.5px] text-white/42" title={command}>
          {command}
        </div>
      </div>
    </section>
  );
}

type SystemFactRow = {
  id?: string;
  label?: string;
  summary?: string;
  operator_ui_use?: string;
  type_b_use?: string;
  source_refs?: string[];
};

function metricValue(summary: Record<string, unknown> | undefined, key: string): string {
  const value = summary?.[key];
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'string' && value.trim()) return value;
  return '0';
}

function actorAxisFact(launcher: StationLauncherSnapshot): SystemFactRow | null {
  const facts = launcher.system_facts?.facts;
  if (!Array.isArray(facts)) return null;
  return (
    (facts as SystemFactRow[]).find(
      (fact) => fact.id === 'actor_axes' || fact.label === 'Type A/B axes',
    ) ?? null
  );
}

function driverSurface(driverId: string | null | undefined): string {
  const raw = (driverId ?? '').trim().toLowerCase();
  if (!raw) return 'unknown';
  if (raw.includes('codex')) return 'codex';
  if (raw.includes('claude')) return 'claude_code';
  if (raw.includes('bridge')) return 'bridge_runtime';
  if (raw.includes('operator') || raw.includes('human')) return 'operator_chrome_hud';
  return raw;
}

type AxisRow = {
  label: string;
  value: string;
};

function AxisCard({
  title,
  tone,
  rows,
}: {
  title: string;
  tone: Tone;
  rows: AxisRow[];
}) {
  return (
    <div className={clsx('rounded-[var(--zenith-radius-md)] border px-[var(--zenith-space-2-5)] py-2', toneClasses(tone))}>
      <div className="font-display text-[12px] uppercase tracking-[0.08em] text-white">
        {title}
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1">
        {rows.map((row) => (
          <div key={`${title}-${row.label}`} className="min-w-0">
            <dt className="truncate font-mono text-[8px] uppercase tracking-[0.16em] text-zenith-muted">
              {row.label}
            </dt>
            <dd className="truncate font-mono text-[10.5px] text-white/82" title={row.value}>
              {row.value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function ActorPairingHud({
  launcher,
  payload,
  routeLabel,
  onNavigate,
}: {
  launcher: StationLauncherSnapshot;
  payload: VantageResponse | null;
  routeLabel: string;
  onNavigate: (route: string, label: string) => void;
}) {
  const driverId = launcher.current_driver.actor_id || launcher.orchestration.active_driver || 'unknown';
  const activePhase = launcher.active_phase.phase_id ?? 'unknown';
  const currentNext = payload?.work_spine?.current_next?.id ?? 'unknown';
  const currentNextTitle = payload?.work_spine?.current_next?.title ?? null;
  const fact = actorAxisFact(launcher);
  const sourceRef =
    fact?.source_refs?.[0] ??
    'codex/doctrine/concepts/con_016_intelligence_delegation_cascade.json::actor_axes';
  const tabPacket = `tab=${routeLabel}; subphase=${activePhase}; current_next=${currentNext}`;

  const typeARows: AxisRow[] = [
    { label: 'substrate', value: 'Type A' },
    { label: 'class', value: 'unknown' },
    { label: 'surface', value: driverSurface(driverId) },
    { label: 'role', value: 'controller' },
    { label: 'context', value: 'live_substrate' },
    { label: 'lane', value: 'substrate_execution' },
    { label: 'budget', value: 'unknown' },
    { label: 'driver', value: driverId },
  ];
  const typeBRows: AxisRow[] = [
    { label: 'substrate', value: 'Type B' },
    { label: 'class', value: 'high' },
    { label: 'surface', value: 'operator_chrome_hud' },
    { label: 'role', value: 'operator_visible_cognitive_actor' },
    { label: 'context', value: 'operator_hud + injected_context' },
    { label: 'lane', value: 'operator_decision' },
    { label: 'budget', value: 'high' },
    { label: 'authority', value: 'candidate_or_decision' },
  ];

  return (
    <section className="panel shrink-0" data-capture-label="actor_pairing_hud">
      <PanelHead
        kicker="HUD"
        title="Actor pairing"
        trailing={
          <button
            type="button"
            onClick={() => onNavigate('/station/phase', 'Phase')}
            className="inline-flex items-center gap-1 rounded-full border border-zenith-edge-faint bg-white/[0.04] px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/80 transition-colors hover:border-white/30 hover:text-white"
          >
            Phase <ArrowRight size={11} />
          </button>
        }
      />
      <div className="panel-body-padded space-y-2">
        <div className="grid grid-cols-3 gap-1.5">
          <div className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
            <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">
              tab
            </div>
            <div className="truncate font-mono text-[12px] text-white/85">{routeLabel}</div>
          </div>
          <div className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
            <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">
              subphase
            </div>
            <div className="truncate font-mono text-[12px] text-white/85">{activePhase}</div>
          </div>
          <div className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
            <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">
              workitem
            </div>
            <div className="truncate font-mono text-[12px] text-white/85" title={currentNextTitle ?? undefined}>
              {currentNext}
            </div>
          </div>
        </div>
        <div className="grid gap-1.5 md:grid-cols-2">
          <AxisCard title="Active Type A" tone="ok" rows={typeARows} />
          <AxisCard title="Paired Type B" tone="neutral" rows={typeBRows} />
        </div>
        <div className="truncate font-mono text-[9.5px] text-white/42" title={tabPacket}>
          {tabPacket}
        </div>
        <div className="truncate font-mono text-[9px] uppercase tracking-[0.16em] text-zenith-muted" title={sourceRef}>
          {sourceRef}
        </div>
      </div>
    </section>
  );
}

function SystemFactsCard({ launcher }: { launcher: StationLauncherSnapshot }) {
  const factsPayload = launcher.system_facts ?? null;
  const summary = factsPayload?.summary as Record<string, unknown> | undefined;
  const facts = Array.isArray(factsPayload?.facts)
    ? (factsPayload.facts as SystemFactRow[]).slice(0, 4)
    : [];
  const status = typeof factsPayload?.status === 'string' ? factsPayload.status : 'ready';
  const sourceRefs = Array.isArray(factsPayload?.source_refs)
    ? factsPayload.source_refs.filter((ref): ref is string => typeof ref === 'string' && ref.trim().length > 0)
    : [];
  const sourceLabel = sourceRefs[0] ?? 'state/system_atlas/system_facts_at_a_glance.json';
  const metrics = [
    ['entities', metricValue(summary, 'entity_count')],
    ['findings', metricValue(summary, 'finding_count')],
    ['modules', metricValue(summary, 'paper_module_count')],
    ['standards', metricValue(summary, 'standard_count')],
  ];

  return (
    <section className="panel shrink-0">
      <PanelHead
        kicker="Generated"
        title="System facts"
        trailing={
          <span
            className={clsx(
              'pill',
              status === 'ready' ? 'pill-ok' : 'pill-warn',
            )}
            title={sourceLabel}
          >
            {status}
          </span>
        }
      />
      <div className="panel-body-padded space-y-2">
        <div className="grid grid-cols-4 gap-1.5">
          {metrics.map(([label, value]) => (
            <div key={label} className="rounded-[var(--zenith-radius-xs)] border border-white/[0.12] bg-white/[0.035] px-2 py-1">
              <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-zenith-muted">
                {label}
              </div>
              <div className="truncate font-mono text-[12px] text-white/85">
                {value}
              </div>
            </div>
          ))}
        </div>
        {facts.length === 0 ? (
          <div className="rounded-[var(--zenith-radius-sm)] border border-amber-400/25 bg-amber-500/[0.08] px-3 py-2 text-[11.5px] text-amber-100/85">
            System facts projection missing.
          </div>
        ) : (
          <ul className="space-y-1.5">
            {facts.map((fact) => (
              <li key={fact.id ?? fact.label} className="rounded-[var(--zenith-radius-sm)] border border-white/[0.12] bg-black/20 px-[var(--zenith-space-2-5)] py-2">
                <div className="truncate font-mono text-[9px] uppercase tracking-[0.18em] text-zenith-muted">
                  {fact.label ?? fact.id ?? 'fact'}
                </div>
                <div className="mt-0.5 line-clamp-2 text-[11.5px] leading-4 text-[var(--zenith-soft)]">
                  {fact.operator_ui_use || fact.summary || fact.type_b_use}
                </div>
              </li>
            ))}
          </ul>
        )}
        <div className="truncate font-mono text-[9px] uppercase tracking-[0.16em] text-zenith-muted" title={sourceLabel}>
          {sourceLabel}
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function HomeStation() {
  const captureMode = isCaptureModeEnabled();
  const layoutMode = useHomeLayoutMode();
  const compactHeight = layoutMode === 'compact-height';
  const location = useLocation();
  const navigate = useNavigate();
  const {
    launcher,
    launcherLoading,
    launcherError,
    operationsCatalog,
    operationsCatalogLoading,
    refreshOperationsCatalog,
    attention,
    liveUpdates,
  } = useStation();
  const refreshStationRuntimeSurface = useZenith((state) => state.refreshStationRuntimeSurface);
  const startStationRuntimeRefresh = useZenith((state) => state.startStationRuntimeRefresh);

  const homeBootstrapOverBudget = useCaptureBudgetBlocker(
    (!launcher && !launcherError) || launcherLoading,
    'home-bootstrap',
  );
  useCaptureDiagnostic(
    launcherError && !launcher ? 'http_error' : null,
    launcherError || null,
  );

  const [launchingOperationId, setLaunchingOperationId] = useState<string | null>(null);
  const launchingOperationRef = useRef(false);
  const [operationParams, setOperationParams] = useState<Record<string, Record<string, string>>>({});
  const [featuredError, setFeaturedError] = useState<string | null>(null);
  const [featuredResult, setFeaturedResult] = useState<LaunchOperationResult['result'] | null>(null);
  const [recentExpanded, setRecentExpanded] = useState(false);
  const [recentSurfaces, setRecentSurfaces] = useState<RecentSurface[]>(() => readRecentSurfaces());
  const [vantage, setVantage] = useState<VantageResponse | null>(null);
  const [vantageLoading, setVantageLoading] = useState(false);
  const [vantageError, setVantageError] = useState<string | null>(null);
  const runtime = getUiRuntimeContext();
  const hostBridge = getZenithHostBridge();
  const canOpenSurfaceLens =
    runtime.mode === 'embedded'
    && runtime.hostCapabilities.openLens
    && typeof hostBridge?.openLens === 'function';

  const handleNavigate = useCallback(
    (route: string, label?: string) => {
      const finalLabel = label ?? getSurfaceLabelForRoute(route);
      rememberRecentSurface(route, finalLabel);
      setRecentSurfaces(readRecentSurfaces());
      navigate(route);
    },
    [navigate],
  );

  const handleOpenLens = useCallback(
    (surface: SurfaceDefinition) => {
      if (!canOpenSurfaceLens) return;
      const route = getSurfaceEntryRoute(surface) ?? surface.route;
      rememberRecentSurface(route, surface.label);
      setRecentSurfaces(readRecentSurfaces());
      void hostBridge?.openLens?.(route, { activate: false, source: 'surface_menu' });
    },
    [canOpenSurfaceLens, hostBridge],
  );

  const refreshStationSurface = useCallback(
    async (source: 'poll' | 'manual' | 'observe', force = true, allowInCapture = false) =>
      refreshStationRuntimeSurface(source, { force, allowInCapture, captureMode }),
    [captureMode, refreshStationRuntimeSurface],
  );

  const refreshVantage = useCallback(async () => {
    setVantageLoading(true);
    try {
      const packet = await api.worldModel.vantage({ band: 'flag' });
      setVantage(packet);
      setVantageError(null);
    } catch (err) {
      setVantageError(err instanceof Error ? err.message : 'Failed to load vantage.');
    } finally {
      setVantageLoading(false);
    }
  }, []);

  useEffect(() => {
    return startStationRuntimeRefresh({ captureMode });
  }, [captureMode, startStationRuntimeRefresh]);

  useEffect(() => {
    void refreshVantage();
  }, [refreshVantage]);

  const familyNumber = launcher?.family.family_number ?? null;
  const familyTitle = launcher?.family.title ?? 'No active family';
  const phaseId = launcher?.active_phase.phase_id ?? null;
  const launcherOperations = useMemo(
    () => (launcher?.operations?.length ? launcher.operations : operationsCatalog ?? []),
    [launcher?.operations, operationsCatalog],
  );

  useEffect(() => {
    if (!launcherOperations.length) return;
    setOperationParams((prev) => {
      const next: Record<string, Record<string, string>> = {};
      for (const op of launcherOperations) {
        const defaults = buildDefaultOperationParams(op, familyNumber);
        next[op.operation_id] = { ...defaults, ...(prev[op.operation_id] ?? {}) };
      }
      return next;
    });
  }, [familyNumber, launcherOperations]);

  useEffect(() => {
    if (captureMode || !launcher || launcher.operations?.length || operationsCatalog || operationsCatalogLoading) {
      return;
    }
    void refreshOperationsCatalog({ force: false });
  }, [
    captureMode,
    launcher,
    operationsCatalog,
    operationsCatalogLoading,
    refreshOperationsCatalog,
  ]);

  // Featured raw-seed action: one CTA chosen by pipeline pressure.
  const routeReviewOp = useMemo(
    () =>
      launcherOperations.find((o) => o.operation_id === 'raw_seed_route_review') ?? null,
    [launcherOperations],
  );
  const syncHandoffOp = useMemo(
    () =>
      launcherOperations.find(
        (o) => o.operation_id === 'raw_seed_sync_handoff_launch',
      ) ?? null,
    [launcherOperations],
  );
  const featuredOp = useMemo(() => {
    if ((launcher?.raw_seed_pipeline.fresh_pending_bins ?? 0) > 0) return syncHandoffOp;
    if ((launcher?.raw_seed_pipeline.pending_routing_bins ?? 0) > 0) return routeReviewOp;
    return syncHandoffOp ?? routeReviewOp;
  }, [
    launcher?.raw_seed_pipeline.fresh_pending_bins,
    launcher?.raw_seed_pipeline.pending_routing_bins,
    routeReviewOp,
    syncHandoffOp,
  ]);

  const runOperation = async (
    operation: StationLauncherOperation,
    parameters?: Record<string, string>,
    captureFeatured = false,
  ) => {
    if (launchingOperationRef.current) return;
    launchingOperationRef.current = true;
    setLaunchingOperationId(operation.operation_id);
    if (captureFeatured) {
      setFeaturedError(null);
      setFeaturedResult(null);
    }
    try {
      const result = await launchStationOperation(operation, parameters);
      if (captureFeatured) setFeaturedResult(result);
      void refreshStationSurface('manual');
    } catch (e) {
      if (captureFeatured) {
        setFeaturedError(e instanceof Error ? e.message : 'Failed to launch operation');
      }
      console.error('[station.home] operation launch failed', e);
    } finally {
      launchingOperationRef.current = false;
      setLaunchingOperationId(null);
    }
  };

  if (launcherError && !launcher) {
    return (
      <div data-zenith-home-surface="ready" className="dashboard-shell flex items-center justify-center text-white">
        <div className="max-w-md rounded-[20px] border border-rose-400/30 bg-rose-500/10 px-5 py-4 text-sm">
          <span className="panel-kicker">Launcher unavailable</span>
          <p className="mt-2 text-rose-100">{launcherError}</p>
          <button
            onClick={() => void refreshStationSurface('manual')}
            disabled={captureMode}
            className="mt-3 rounded-full border border-zenith-edge-faint px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.2em] text-white hover:bg-white/[0.06]"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!launcher && launcherLoading) {
    if (homeBootstrapOverBudget) {
      return (
        <div
          data-zenith-home-surface="ready"
          className="dashboard-shell flex items-center justify-center text-white"
        >
          <div className="max-w-md rounded-[20px] border border-amber-400/30 bg-amber-500/10 px-5 py-4 text-sm text-amber-100">
            <span className="panel-kicker">Home bootstrap over budget</span>
            <p className="mt-2">
              The launcher deck has not resolved within the 3s budget. Capture can proceed because
              this surface is explicitly degraded, not silently loading.
            </p>
            <button
              onClick={() => void refreshStationSurface('manual')}
              disabled={captureMode}
              className="mt-3 rounded-full border border-amber-300/30 px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.2em] text-amber-100 hover:bg-amber-500/[0.08]"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }
    return (
      <div className="dashboard-shell flex items-center justify-center p-4 text-white/70">
        <div className="w-full max-w-md">
          <StateGuard
            data={null}
            loading
            error={null}
            onRetry={() => void refreshStationSurface('manual')}
          >
            {() => null}
          </StateGuard>
        </div>
      </div>
    );
  }
  if (!launcher) return null;

  const orchestrationIso = launcher.orchestration.freshness?.iso ?? null;
  const snapshotCells = buildSnapshotCells(launcher);

  // Incidents: up to 3 deduped alerts. The alarm strip handles staleness;
  // the featured action panel handles raw-seed pressure. We skip raw-seed
  // alerts here so the operator doesn't see the same sentence twice.
  // Also suppress gate-hold alerts when gate_reason is null — a "GATE ACTIVE
  // / none" card is a trust-breaker, not a signal.
  // Treat literal-string "none"/"—"/"-" as "no gate" — the backend emits it
  // as a sentinel, and "GATE ACTIVE / none" is a trust-breaker.
  const gateReasonRaw = launcher.orchestration.gate_reason;
  const isEmptyDetail = (d?: string | null) => {
    if (!d) return true;
    const norm = d.trim().toLowerCase();
    return norm === '' || norm === 'none' || norm === '—' || norm === '-';
  };
  const hasGateReason = Boolean(gateReasonRaw) && !isEmptyDetail(gateReasonRaw);
  const rollupAlerts = (launcher.alerts ?? [])
    .filter((a) => !a.id.startsWith('raw_seed_') && !a.id.startsWith('routing_'))
    // Suppress gate alerts when the backend hasn't supplied a reason — a
    // "GATE ACTIVE / none" tile is a trust-breaker, not a signal.
    .filter((a) => {
      const label = a.label?.toLowerCase() ?? '';
      const gateIsh = a.id === 'gate_hold' || label.includes('gate');
      return !(gateIsh && !hasGateReason && isEmptyDetail(a.detail));
    })
    .slice(0, 3);
  const rawSeedAlerts = (launcher.alerts ?? []).filter(
    (a) => a.id.startsWith('raw_seed_') || a.id.startsWith('routing_'),
  );
  const primaryIncidents = rollupAlerts.length > 0 ? rollupAlerts : rawSeedAlerts.slice(0, 1);

  const recentChanges = attention?.recent_changes ?? [];
  const recentGroups = groupRecentChanges(recentChanges, recentExpanded ? 12 : 3);

  const attentionCount = (launcher.alerts ?? []).length;

  const featuredLabel = featuredOp?.label ?? 'Raw-seed routing';
  const featuredCopy =
    featuredOp?.operation_id === 'raw_seed_sync_handoff_launch'
      ? launcher.raw_seed_pipeline.fresh_pending_bins > 0
        ? `${launcher.raw_seed_pipeline.fresh_pending_bins} fresh bin(s) ready for post-sync handoff.`
        : 'Fresh sync pressure low. Handoff stays one click away.'
      : launcher.raw_seed_pipeline.pending_routing_bins > 0
        ? `${launcher.raw_seed_pipeline.pending_routing_bins} bin(s) ready for next routing pass.`
        : 'Routing pressure low. Bounded review stays one click away.';
  const featuredParams = featuredOp
    ? operationParams[featuredOp.operation_id] ??
      buildDefaultOperationParams(featuredOp, familyNumber)
    : {};
  const featuredPreview = operationResultPreview(featuredResult);
  const featuredButtonLabel =
    featuredOp?.operation_id === 'raw_seed_sync_handoff_launch' ? 'Run handoff' : 'Route now';
  const showFeaturedStrip = Boolean(
    featuredOp
      || launcher.raw_seed_pipeline.fresh_pending_bins > 0
      || launcher.raw_seed_pipeline.pending_routing_bins > 0,
  );

  const embedded = runtime.mode === 'embedded';
  const homeSurfaceReady = vantage || vantageError ? 'ready' : 'loading';

  return (
    <div
      data-testid="home-station-root"
      data-zenith-home-surface={homeSurfaceReady}
      data-zenith-home-layout={layoutMode}
      className="dashboard-shell text-white"
    >
      <div className={clsx('flex h-full w-full flex-col', compactHeight ? 'gap-1.5 p-2' : 'gap-2 p-2.5')}>
        {/* Row 1 — alarm strip (only when stale past threshold). Skipped in
            embedded mode: the native toolbar already surfaces backend /
            phase / attention freshness, so duplicating here is noise. */}
        {!embedded && orchestrationIso && (
          <StaleAlarm
            iso={orchestrationIso}
            label="Orchestration"
            thresholds={{
              fresh: 60_000,
              stale: 15 * 60 * 1000,
              alarm: 60 * 60 * 1000,
            }}
            onClick={() => void refreshStationSurface('manual')}
          />
        )}

        {/* Row 2 — identity strip. In embedded mode the native toolbar owns
            family/phase/gate/attention/refresh, so we collapse this row to
            the page title plus the quick-jump trigger. */}
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <h1 className="sr-only">Atlas — {familyTitle}</h1>
          <div className="flex min-w-0 items-center gap-2">
            {!embedded && (
              <>
                <span className="panel-kicker">Atlas</span>
                {familyNumber && <span className="pill">family {familyNumber}</span>}
                {phaseId && <span className="pill">phase {phaseId}</span>}
                {launcher.active_phase.cycle != null && (
                  <span className="pill">cycle {launcher.active_phase.cycle}</span>
                )}
                {hasGateReason ? (
                  <span className="pill pill-block">
                    gate · {launcher.orchestration.gate_reason!.replace(/_/g, ' ')}
                  </span>
                ) : (
                  <span className="pill pill-ok">gate clear</span>
                )}
              </>
            )}
            <span
              className={clsx(
                'truncate font-mono text-white/75',
                embedded ? 'text-[13px]' : 'ml-1 text-[12px]',
              )}
              title={familyTitle}
            >
              {familyTitle}
            </span>
          </div>
          <div className="flex items-center gap-1.5" data-capture-label="live_update_posture">
            <button
              type="button"
              onClick={() => requestHostCommandPalette()}
              className="inline-flex items-center gap-1 rounded-full border border-white/[0.18] bg-black/25 px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-white/75 transition-colors hover:border-white/35 hover:text-white"
            >
              Quick jump <span className="text-zenith-muted">⌘K</span>
            </button>
            {!embedded && (
              <>
                <LiveUpdateBadge state={liveUpdates.status} compact />
                <span
                  className={clsx(
                    'pill',
                    attentionCount > 0 ? 'pill-warn' : 'pill-ok',
                  )}
                >
                  {attentionCount} attention
                </span>
                <button
                  onClick={() => void refreshStationSurface('manual')}
                  disabled={captureMode}
                  className="inline-flex items-center gap-1 rounded-full border border-zenith-edge-faint bg-white/[0.04] px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-white/80 transition-colors hover:border-white/30 hover:text-white"
                >
                  <RefreshCw size={10} /> refresh
                </button>
              </>
            )}
          </div>
        </header>

        {/* Row 2.5 — registry-backed grouped navigation. Same source of truth
            as the shell, so labels/routes cannot drift. */}
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <SurfaceMenuBar
            groups={SHELL_GROUPS}
            pathname={location.pathname}
            variant="panel"
            canOpenLens={canOpenSurfaceLens}
            onNavigate={(surface) =>
              handleNavigate(getSurfaceEntryRoute(surface) ?? surface.route, surface.label)
            }
            onOpenLens={handleOpenLens}
          />
          <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-zenith-muted">
            grouped surfaces
          </span>
        </div>

        {/* Row 3 — snapshot strip. 6 tight cells, one row. */}
        <section
          className="grid shrink-0 grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-6"
          data-capture-label="phase_roll_up"
        >
          {snapshotCells.map((cell) => (
            <SnapCell key={cell.label} {...cell} />
          ))}
        </section>

        {/* Row 4 — MAIN BODY. Two-archetype layout:
            LEFT (col-8) : compact launcher tiles (destinations, 72px)
                           → Continue-where-you-left-off
                           → Pinned procedures (fills leftover height)
            RIGHT (col-4): Attention (live panel, shrink-0)
                           → Recent (live panel, flex-1 scroll)
                           → Pulse (live panel, shrink-0)
            Every card has a job; no hollow symmetry. */}
        <div
          className={clsx(
            'grid min-h-0 flex-1 grid-cols-12 items-start',
            compactHeight ? 'gap-2 overflow-y-auto pr-1' : 'gap-[var(--zenith-space-2-5)]',
          )}
        >
          <div
            className="col-span-12 flex min-h-0 flex-col gap-2 lg:col-span-8"
            data-capture-label="operation_launchers"
          >
            <section className="grid shrink-0 grid-cols-2 gap-1.5 md:grid-cols-3">
              {HOME_TILES.map((surface) => (
                <LauncherTile
                  key={surface.id}
                  surface={surface}
                  launcher={launcher}
                  operationCount={launcherOperations.length}
                  onNavigate={handleNavigate}
                />
              ))}
            </section>

            <LaunchReadinessCard
              payload={vantage}
              onNavigate={handleNavigate}
            />

            <PhaseTodoHudCard
              launcher={launcher}
              payload={vantage}
              onNavigate={handleNavigate}
            />

            <VantageFlagCard
              payload={vantage}
              loading={vantageLoading}
              error={vantageError}
              onRefresh={() => void refreshVantage()}
              onNavigate={handleNavigate}
            />

            <ActorPairingHud
              launcher={launcher}
              payload={vantage}
              routeLabel={getSurfaceLabelForRoute(location.pathname)}
              onNavigate={handleNavigate}
            />

            <ApprovalsSummaryCard
              launcher={launcher}
              onNavigate={handleNavigate}
              compact={compactHeight}
            />

            <ContinueCard
              recent={recentSurfaces}
              onNavigate={handleNavigate}
              compact={compactHeight}
            />

            <PinnedOpsCard
              operations={launcherOperations}
              loading={operationsCatalogLoading}
              excludeIds={new Set(featuredOp ? [featuredOp.operation_id] : [])}
              launchingOperationId={launchingOperationId}
              onLaunch={(op) => void runOperation(op, operationParams[op.operation_id])}
              onOpenOps={() => handleNavigate('/station/ops', 'Ops')}
              compact={compactHeight}
            />
          </div>

          <div className="col-span-12 flex min-h-0 flex-col gap-2 lg:col-span-4">
            <section className="panel shrink-0" data-capture-label="attention_signals">
              <PanelHead
                kicker="Attention"
                title={
                  primaryIncidents.length === 0
                    ? 'Clear'
                    : `${primaryIncidents.length} rollup${primaryIncidents.length === 1 ? '' : 's'}`
                }
              />
              <div className="panel-body-padded flex flex-col gap-1.5">
                {primaryIncidents.length === 0 ? (
                  <div
                    className={clsx(
                      'flex items-center gap-2 rounded-[var(--zenith-radius-md)] border px-3 py-2 text-[12px]',
                      toneClasses('ok'),
                    )}
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" />
                    All clear.
                  </div>
                ) : (
                  primaryIncidents.map((alert) => (
                    <IncidentRow
                      key={alert.id}
                      alert={alert}
                      onCopy={(_id, cmd) => {
                        void navigator.clipboard.writeText(cmd).catch((err) => {
                          console.warn('[HomeStation] clipboard write failed:', err);
                        });
                      }}
                      onOpen={() => {
                        const destination = resolveSurfaceFromAlert(alert);
                        handleNavigate(destination.route, destination.label);
                      }}
                    />
                  ))
                )}
              </div>
            </section>

            <section className={clsx('panel flex flex-col', compactHeight ? 'min-h-0 flex-1' : 'shrink-0')}>
              <PanelHead
                kicker="Recent"
                title="Since you last looked"
                trailing={
                  recentChanges.length > 3 && (
                    <button
                      onClick={() => setRecentExpanded((v) => !v)}
                      className="inline-flex items-center gap-1 rounded-full border border-zenith-edge-faint bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-white/80 hover:border-white/30 hover:text-white"
                    >
                      {recentExpanded ? 'Collapse' : 'View all'}
                    </button>
                  )
                }
              />
              <div
                className={clsx(
                  'panel-body overflow-y-auto',
                  compactHeight ? 'min-h-0' : recentExpanded ? 'max-h-[420px]' : 'max-h-[240px]',
                )}
              >

                {recentGroups.length === 0 ? (
                  <div className="px-3 py-3 text-[11.5px] text-white/50">
                    No recent orchestration events captured.
                  </div>
                ) : (
                  <ul className="panel-divide">
                    {recentGroups.map((group) => (
                      <li key={group.key} className="row-tile">
                        <Activity size={11} className="mt-0.5 shrink-0 text-white/50" />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-zenith-soft">
                              {group.driver ?? 'driver'}
                            </span>
                            {group.gateReason && (
                              <span className="rounded-full border border-amber-400/30 bg-amber-500/10 px-1.5 py-px font-mono text-[8.5px] uppercase tracking-[0.18em] text-amber-100">
                                {group.gateReason.replace(/_/g, ' ')}
                              </span>
                            )}
                            {group.count > 1 && <span className="pill">×{group.count}</span>}
                            <span className="ml-auto font-mono text-[9px] uppercase tracking-[0.2em] text-zenith-muted">
                              {ageLabel(group.latestIso)}
                            </span>
                          </div>
                          <div className="mt-0.5 line-clamp-2 text-[11.5px] leading-4 text-[var(--zenith-soft)]">
                            {group.summary}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </section>

            <SystemFactsCard launcher={launcher} />

            <PulseCard launcher={launcher} />
          </div>
        </div>

        {/* Row 4 — featured action as a single hero strip. The biggest
            lever the pipeline has right now, surfaced once. */}
        {showFeaturedStrip && (
          <section className="shrink-0 rounded-[var(--zenith-radius-region)] border border-amber-400/25 bg-amber-500/[0.07] px-3 py-[var(--zenith-space-2-5)] pr-[112px]">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
              <span className="pill pill-warn">featured</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <span className="font-display text-[14px] uppercase tracking-[0.04em] text-white">
                    {featuredLabel}
                  </span>
                  <span className="truncate font-mono text-[11px] text-white/60">
                    {featuredCopy}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                {featuredOp ? (
                  <button
                    type="button"
                    onClick={() => void runOperation(featuredOp, featuredParams, true)}
                    disabled={launchingOperationId != null}
                    className="inline-flex items-center gap-1.5 rounded-full border border-amber-300/30 bg-amber-400/15 px-[var(--zenith-space-2-5)] py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-amber-50 hover:border-amber-200/50 hover:bg-amber-400/25 disabled:cursor-wait disabled:opacity-60"
                  >
                    {launchingOperationId === featuredOp.operation_id ? (
                      <Activity size={11} className="animate-pulse" />
                    ) : (
                      <Workflow size={11} />
                    )}
                    {featuredButtonLabel}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleNavigate('/station/ops', 'Ops')}
                    className="inline-flex items-center gap-1 rounded-full border border-amber-300/30 bg-amber-400/15 px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-amber-50 hover:border-amber-200/50 hover:bg-amber-400/25"
                  >
                    Open Ops <ArrowRight size={10} />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() =>
                    handleNavigate(
                      featuredOp ? `/station/ops?operation=${featuredOp.operation_id}` : '/station/ops',
                      'Ops',
                    )
                  }
                  className="inline-flex items-center gap-1 rounded-full border border-zenith-edge-faint bg-white/[0.04] px-[var(--zenith-space-2-5)] py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white hover:border-white/30"
                >
                  Open Ops <ArrowRight size={10} />
                </button>
                {featuredResult && featuredOp && (
                  <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-soft">
                    Last route launch
                  </span>
                )}
              </div>
            </div>
            {featuredError && (
              <div className="mt-2 rounded-[var(--zenith-radius-sm)] border border-rose-400/25 bg-rose-500/[0.08] px-[var(--zenith-space-2-5)] py-1.5 text-[11px] leading-4 text-rose-100">
                {featuredError}
              </div>
            )}
            {featuredResult && (
              <pre className="mt-2 max-h-[48px] overflow-auto rounded-[var(--zenith-radius-sm)] border border-white/[0.12] bg-black/30 px-[var(--zenith-space-2-5)] py-1.5 font-mono text-[10.5px] leading-[1.35] text-white/75">
                {featuredPreview}
              </pre>
            )}
          </section>
        )}

      </div>
    </div>
  );
}
