// [PURPOSE] Cockpit attention queue — Surface 1 (right column).
//
// Lists what needs me, sorted by actionability. Combines two existing
// data sources without inventing new ones:
//   - `attention.attention_items[]` (kind/score/title/detail/command) — the
//     world-model-projected attention queue
//   - `launcher.alerts[]` (id/tone/label/detail/command) — launcher-surfaced
//     incidents
//
// Pass 2 will replace this with `/api/cockpit/attention` carrying P0–P3
// priority directly. Today we map tone → severity bucket as a placeholder so
// the UI is honest about what it is showing.
import clsx from 'clsx';
import { ArrowRight, Copy, Check, Bell } from 'lucide-react';
import { useState } from 'react';
import type {
  AttentionItem,
  AttentionSnapshot,
  StationLauncherAlert,
} from '../../api';
import { PanelHead } from '../world/cellHelpers';
import { toneClasses, type Tone } from '../world/cellHelpers.utils';

type Bucket = 'P1' | 'P2' | 'P3';

const BUCKET_TONE: Record<Bucket, Tone> = {
  P1: 'block',
  P2: 'warn',
  P3: 'neutral',
};

const BUCKET_LABEL: Record<Bucket, string> = {
  P1: 'P1 · operator needed',
  P2: 'P2 · watch',
  P3: 'P3 · informational',
};

type CockpitAttentionRow = {
  key: string;
  bucket: Bucket;
  title: string;
  detail?: string | null;
  source: 'attention' | 'alert';
  command?: string | null;
};

function rowFromAlert(alert: StationLauncherAlert): CockpitAttentionRow {
  // launcher tones map: block → P1, warn → P2, info/ok → P3
  const bucket: Bucket = alert.tone === 'block' ? 'P1' : alert.tone === 'warn' ? 'P2' : 'P3';
  return {
    key: `alert:${alert.id}`,
    bucket,
    title: alert.label,
    detail: alert.detail ?? null,
    source: 'alert',
    command: alert.command ?? null,
  };
}

function rowFromAttentionItem(item: AttentionItem): CockpitAttentionRow {
  // Placeholder bucketing on `kind` until Pass 2 lands real P-scoring.
  const bucket: Bucket =
    item.kind === 'gate' || item.kind === 'driver_block' || item.kind === 'bridge'
      ? 'P1'
      : item.kind === 'cycle_degraded' || item.kind === 'drift' || item.kind === 'work_ledger'
        ? 'P2'
        : 'P3';
  return {
    key: `item:${item.id}`,
    bucket,
    title: item.title,
    detail: item.detail ?? null,
    source: 'attention',
    command: item.command ?? null,
  };
}

const BUCKET_ORDER: Bucket[] = ['P1', 'P2', 'P3'];

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

function AttentionRow({ row }: { row: CockpitAttentionRow }) {
  const tone = BUCKET_TONE[row.bucket];
  const [copied, setCopied] = useState(false);
  return (
    <div
      className={clsx(
        'flex flex-col gap-1.5 rounded-[12px] border px-3 py-2',
        toneClasses(tone),
      )}
    >
      <div className="flex items-start gap-2">
        <span
          className={clsx(
            'mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full',
            tone === 'block' ? 'bg-rose-300 animate-pulse' : tone === 'warn' ? 'bg-amber-300' : 'bg-white/45',
          )}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/55">
              {row.bucket}
            </span>
            <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/40">
              · {row.source}
            </span>
          </div>
          <div className="mt-0.5 font-display text-[13px] leading-tight uppercase tracking-[0.04em] text-white">
            {row.title}
          </div>
          {row.detail && (
            <div className="mt-0.5 line-clamp-2 text-[11.5px] leading-snug text-white/70">
              {row.detail}
            </div>
          )}
        </div>
      </div>
      {row.command && (
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            title={row.command}
            onClick={async () => {
              const ok = await copyText(row.command!);
              if (ok) {
                setCopied(true);
                window.setTimeout(() => setCopied(false), 1400);
              }
            }}
            className="inline-flex items-center gap-1 rounded-full border border-white/15 bg-white/[0.04] px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-white/70 transition-colors hover:border-white/35 hover:text-white"
          >
            {copied ? <Check size={10} /> : <Copy size={10} />}
            {copied ? 'copied' : 'copy command'}
          </button>
          <span className="truncate font-mono text-[10px] text-white/40" title={row.command}>
            {row.command}
          </span>
        </div>
      )}
    </div>
  );
}

export default function AttentionQueue({
  attention,
  alerts,
  onOpenAlert,
}: {
  attention: AttentionSnapshot | null;
  alerts: StationLauncherAlert[];
  onOpenAlert?: (alert: StationLauncherAlert) => void;
}) {
  const rows: CockpitAttentionRow[] = [
    ...alerts.map(rowFromAlert),
    ...(attention?.attention_items ?? []).map(rowFromAttentionItem),
  ];

  // Dedupe by title — the launcher and attention surfaces sometimes carry the
  // same incident in two shapes; show it once with the higher severity.
  const seen = new Map<string, CockpitAttentionRow>();
  for (const row of rows) {
    const fingerprint = (row.title || '').trim().toLowerCase();
    if (!fingerprint) continue;
    const existing = seen.get(fingerprint);
    if (!existing || BUCKET_ORDER.indexOf(row.bucket) < BUCKET_ORDER.indexOf(existing.bucket)) {
      seen.set(fingerprint, row);
    }
  }
  const merged = Array.from(seen.values()).sort(
    (a, b) => BUCKET_ORDER.indexOf(a.bucket) - BUCKET_ORDER.indexOf(b.bucket),
  );

  const buckets: Record<Bucket, CockpitAttentionRow[]> = { P1: [], P2: [], P3: [] };
  for (const row of merged) buckets[row.bucket].push(row);

  const total = merged.length;
  void onOpenAlert; // wired for parity; alerts are read-only in Pass 1.

  return (
    <section
      data-cockpit-section="attention"
      className="panel flex flex-col"
    >
      <PanelHead
        kicker="Needs attention"
        title={total === 0 ? 'Clear' : `${total} signal${total === 1 ? '' : 's'}`}
        trailing={<Bell size={11} className="text-white/45" />}
      />
      <div className="panel-body-padded flex flex-col gap-2.5">
        {total === 0 ? (
          <div className={clsx('rounded-[12px] border px-3 py-2 text-[12px]', toneClasses('ok'))}>
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" />
              All signals quiet. Refresh to recheck.
            </div>
          </div>
        ) : (
          BUCKET_ORDER.map((bucket) => {
            const items = buckets[bucket];
            if (items.length === 0) return null;
            return (
              <div key={bucket} className="flex flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/45">
                    {BUCKET_LABEL[bucket]}
                  </span>
                  <span className="font-mono text-[9px] tabular-nums text-white/35">
                    ×{items.length}
                  </span>
                  <span className="ml-auto font-mono text-[9px] uppercase tracking-[0.2em] text-white/30">
                    <ArrowRight size={9} className="inline" /> drill in (pass 2)
                  </span>
                </div>
                {items.map((row) => (
                  <AttentionRow key={row.key} row={row} />
                ))}
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
