// [PURPOSE] Cockpit top bar — Surface 1.
//
// One-line operational truth: phase, gate, runtime state, orchestrator
// freshness, severity chip, and primary operator actions (refresh / ack /
// pause intake / open raw trace). Replaces the user's critique of
// "ACTIVITY 734 / SESSIONS 38" undifferentiated counters with a single
// readable header.
//
// In Pass 1 this consumes the existing `launcher` + `attention` snapshots.
// Pass 2 will replace the data wiring with `/api/cockpit/station`.
import clsx from 'clsx';
import {
  Activity,
  CheckCircle2,
  Pause,
  Play,
  RefreshCw,
  Terminal,
  TriangleAlert,
} from 'lucide-react';
import type {
  AttentionSnapshot,
  StationLauncherAlert,
  StationLauncherSnapshot,
} from '../../api';
import { SnapCell } from '../world/cellHelpers';
import { ageLabel, ageSeconds, toneClasses, type Tone } from '../world/cellHelpers.utils';

type Severity = 'clear' | 'watch' | 'degraded' | 'blocked';

const SEVERITY_TONE: Record<Severity, Tone> = {
  clear: 'ok',
  watch: 'neutral',
  degraded: 'warn',
  blocked: 'block',
};

const SEVERITY_LABEL: Record<Severity, string> = {
  clear: 'CLEAR',
  watch: 'WATCH',
  degraded: 'DEGRADED',
  blocked: 'BLOCKED',
};

function deriveSeverity(
  alerts: StationLauncherAlert[],
  attention: AttentionSnapshot | null,
): { severity: Severity; reason: string } {
  if (alerts.some((a) => a.tone === 'block')) {
    const a = alerts.find((x) => x.tone === 'block')!;
    return { severity: 'blocked', reason: a.label };
  }
  const banner = attention?.banner;
  if (banner?.tone === 'block') {
    return { severity: 'blocked', reason: banner.title };
  }
  if (alerts.some((a) => a.tone === 'warn')) {
    const a = alerts.find((x) => x.tone === 'warn')!;
    return { severity: 'degraded', reason: a.label };
  }
  if (banner?.tone === 'warn') {
    return { severity: 'degraded', reason: banner.title };
  }
  if (alerts.length > 0) {
    return { severity: 'watch', reason: `${alerts.length} signal${alerts.length === 1 ? '' : 's'}` };
  }
  return { severity: 'clear', reason: 'all signals quiet' };
}

function describeBridge(launcher: StationLauncherSnapshot): { label: string; tone: Tone } {
  const transportReady = launcher.bridge.browser_running && launcher.bridge.cdp_reachable;
  const live = Math.max(0, launcher.bridge.live_provider_count ?? 0);
  const total = Math.max(0, launcher.bridge.provider_count ?? 0);
  if (!transportReady) return { label: `transport down · ${live}/${total}`, tone: 'warn' };
  if (total > 0 && live === 0) return { label: `${live}/${total} providers live`, tone: 'warn' };
  if (total === 0) return { label: 'engine ready', tone: 'neutral' };
  return { label: `${live}/${total} providers live`, tone: 'ok' };
}

export default function StationTopBar({
  launcher,
  attention,
  alerts,
  livePaused,
  refreshing,
  ackPending,
  onRefresh,
  onTogglePause,
  onAcknowledge,
}: {
  launcher: StationLauncherSnapshot;
  attention: AttentionSnapshot | null;
  alerts: StationLauncherAlert[];
  livePaused: boolean;
  refreshing: boolean;
  ackPending: boolean;
  onRefresh: () => void;
  onTogglePause: () => void;
  onAcknowledge: () => void;
}) {
  const phaseId = launcher.active_phase.phase_id ?? '—';
  const cycle = launcher.active_phase.cycle;
  const familyNumber = launcher.family.family_number ?? null;
  const gateRaw = launcher.orchestration.gate_reason;
  const gateNorm = (gateRaw ?? '').trim().toLowerCase();
  const gateActive =
    Boolean(gateRaw) && gateNorm !== '' && gateNorm !== 'none' && gateNorm !== '—' && gateNorm !== '-';
  const gateLabel = gateActive ? gateRaw!.replace(/_/g, ' ') : 'clear';

  const orchestrationIso = launcher.orchestration.freshness?.iso ?? null;
  const orchestrationAgeS = ageSeconds(orchestrationIso);
  const orchestrationStale = orchestrationAgeS != null && orchestrationAgeS > 15 * 60;

  const driverId = launcher.current_driver.actor_id ?? launcher.orchestration.active_driver ?? 'unclaimed';
  const handoffId = launcher.next_handoff.actor_id ?? 'none';

  const bridge = describeBridge(launcher);
  const { severity, reason } = deriveSeverity(alerts, attention);
  const sevTone = SEVERITY_TONE[severity];

  const phaseDetail = cycle != null ? `cycle ${cycle}` : 'no cycle';

  // Attention freshness as a stand-in for "metabolism freshness" — the
  // dedicated metabolism cell lands in Pass 2 with /api/cockpit/station.
  const attentionAgeIso = attention?.generated_at ?? null;
  const attentionAgeS = ageSeconds(attentionAgeIso);

  return (
    <section
      data-cockpit-section="top-bar"
      className="shrink-0 rounded-[14px] border border-white/[0.10] bg-[linear-gradient(135deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01))] px-3 py-2.5"
    >
      {/* Row 1 — operational truth one-liner */}
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
        <span className="font-display text-[14px] uppercase tracking-[0.06em] text-white">
          {familyNumber ? `Family ${familyNumber} · ` : ''}Phase {phaseId}
        </span>
        <span className="font-mono text-[11px] text-white/60">·</span>
        <span
          className={clsx(
            'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em]',
            gateActive ? toneClasses('block') : toneClasses('ok'),
          )}
        >
          {gateActive ? <TriangleAlert size={10} /> : <CheckCircle2 size={10} />}
          gate · {gateLabel}
        </span>
        <span className="font-mono text-[11px] text-white/60">·</span>
        <span className="font-mono text-[11px] text-white/70">
          driver <span className="text-white">{driverId}</span>
        </span>
        <span className="font-mono text-[11px] text-white/40">→ next {handoffId}</span>
        <span
          className={clsx(
            'ml-auto inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10.5px] uppercase tracking-[0.2em]',
            toneClasses(sevTone),
          )}
          title={reason}
        >
          <Activity size={11} />
          {SEVERITY_LABEL[severity]}
          <span className="ml-1 text-white/55">·</span>
          <span className="text-white/85 normal-case tracking-normal">{reason}</span>
        </span>
      </div>

      {/* Row 2 — six-cell snapshot strip */}
      <div className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-6">
        <SnapCell label="Phase" value={String(phaseId)} detail={phaseDetail} tone="neutral" />
        <SnapCell
          label="Orchestrator"
          value={ageLabel(orchestrationIso)}
          detail={orchestrationStale ? 'stale heartbeat' : 'live'}
          tone={orchestrationStale ? 'warn' : 'ok'}
        />
        <SnapCell
          label="Attention"
          value={attentionAgeIso ? ageLabel(attentionAgeIso) : '—'}
          detail={attentionAgeS != null && attentionAgeS > 60 ? 'cache cold' : 'live'}
          tone={attentionAgeS != null && attentionAgeS > 5 * 60 ? 'warn' : 'ok'}
        />
        <SnapCell
          label="Bridge"
          value={bridge.label}
          detail={launcher.bridge.cdp_reachable ? 'cdp reachable' : 'cdp unreachable'}
          tone={bridge.tone}
        />
        <SnapCell
          label="Driver"
          value={driverId}
          detail={`next · ${handoffId}`}
          tone={launcher.current_driver.actor_id ? 'ok' : 'warn'}
        />
        <SnapCell
          label="Ack"
          value={ackPending ? 'pending' : 'cleared'}
          detail={gateActive ? 'gate hold open' : 'no gate'}
          tone={ackPending ? 'warn' : 'ok'}
        />
      </div>

      {/* Row 3 — operator action buttons */}
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/[0.04] px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/85 transition-colors hover:border-white/35 hover:text-white disabled:cursor-wait disabled:opacity-60"
        >
          <RefreshCw size={11} className={refreshing ? 'animate-spin' : ''} />
          refresh
        </button>
        <button
          type="button"
          onClick={onTogglePause}
          className={clsx(
            'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em] transition-colors',
            livePaused
              ? 'border-amber-400/30 bg-amber-500/[0.10] text-amber-100 hover:border-amber-200/50'
              : 'border-white/15 bg-white/[0.04] text-white/85 hover:border-white/35 hover:text-white',
          )}
        >
          {livePaused ? <Play size={11} /> : <Pause size={11} />}
          {livePaused ? 'resume' : 'pause intake'}
        </button>
        <button
          type="button"
          onClick={onAcknowledge}
          disabled={!ackPending}
          className={clsx(
            'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.18em] transition-colors',
            ackPending
              ? 'border-emerald-400/30 bg-emerald-500/[0.10] text-emerald-100 hover:border-emerald-200/50'
              : 'border-white/15 bg-white/[0.03] text-white/40',
          )}
          title={ackPending ? 'Acknowledge gate / banner' : 'No ack pending'}
        >
          <CheckCircle2 size={11} />
          ack
        </button>
        <span className="ml-auto inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-[0.18em] text-white/35">
          <Terminal size={10} /> raw trace below
        </span>
      </div>
    </section>
  );
}
