// [PURPOSE] Cockpit workstream board — Surface 2.
//
// Pass 1 placeholder: groups the world-model `recent_changes` feed by
// `active_driver` so the operator can see "what is moving, by whom" without
// wading through raw events. Pass 2 replaces this with
// `/api/cockpit/workstreams` which classifies sessions against
// `family_charter.json` + path heuristics into named workstreams.
//
// Today's data does NOT carry workstream tags, so the board honestly labels
// itself "by driver" and surfaces an unclassified bucket for entries with
// no driver attribution.
import clsx from 'clsx';
import { ChevronRight, Users } from 'lucide-react';
import type {
  AttentionRecentChange,
  AttentionSnapshot,
} from '../../api';
import { PanelHead } from '../world/cellHelpers';
import { ageLabel, toneClasses } from '../world/cellHelpers.utils';

type WorkstreamRow = {
  key: string;
  driver: string;
  count: number;
  latestIso: string | null;
  latestSummary: string | null;
  gateReason: string | null;
};

function groupByDriver(changes: AttentionRecentChange[]): WorkstreamRow[] {
  const order: string[] = [];
  const map = new Map<string, WorkstreamRow>();
  for (const change of changes) {
    const driver = change.active_driver?.trim() || 'unclassified';
    const key = driver.toLowerCase();
    const existing = map.get(key);
    if (existing) {
      existing.count += 1;
      if (change.recorded_at && (!existing.latestIso || change.recorded_at > existing.latestIso)) {
        existing.latestIso = change.recorded_at;
        existing.latestSummary = change.summary ?? existing.latestSummary;
        existing.gateReason = change.gate_reason ?? existing.gateReason;
      }
    } else {
      order.push(key);
      map.set(key, {
        key,
        driver,
        count: 1,
        latestIso: change.recorded_at ?? null,
        latestSummary: change.summary ?? null,
        gateReason: change.gate_reason ?? null,
      });
    }
  }
  // sort by recency desc; unclassified always last
  return order
    .map((k) => map.get(k)!)
    .sort((a, b) => {
      if (a.driver === 'unclassified' && b.driver !== 'unclassified') return 1;
      if (a.driver !== 'unclassified' && b.driver === 'unclassified') return -1;
      const aTs = a.latestIso ?? '';
      const bTs = b.latestIso ?? '';
      return bTs.localeCompare(aTs);
    });
}

export default function WorkstreamBoard({
  attention,
}: {
  attention: AttentionSnapshot | null;
}) {
  const recentChanges = attention?.recent_changes ?? [];
  const rows = groupByDriver(recentChanges);
  const totalEvents = recentChanges.length;

  return (
    <section data-cockpit-section="workstreams" className="panel flex flex-col">
      <PanelHead
        kicker="Workstreams"
        title={
          rows.length === 0
            ? 'No recent activity'
            : `${rows.length} driver${rows.length === 1 ? '' : 's'} · ${totalEvents} event${totalEvents === 1 ? '' : 's'}`
        }
        trailing={
          <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/35">
            <Users size={10} className="mr-1 inline" />
            grouped by driver · pass 2 = workstream classifier
          </span>
        }
      />
      <div className="panel-body">
        {rows.length === 0 ? (
          <div className="px-3 py-3 text-[11.5px] text-white/50">
            No orchestration events captured yet. Workstream rollup endpoint lands in Pass 2.
          </div>
        ) : (
          <ul className="panel-divide">
            {rows.map((row) => {
              const isUnclassified = row.driver === 'unclassified';
              return (
                <li key={row.key} className="row-tile items-center">
                  <span
                    className={clsx(
                      'mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full',
                      isUnclassified ? 'bg-white/30' : 'bg-cyan-300/80',
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={clsx(
                          'font-mono text-[11px] uppercase tracking-[0.16em]',
                          isUnclassified ? 'text-white/55' : 'text-white/90',
                        )}
                      >
                        {row.driver}
                      </span>
                      <span className="rounded-full border border-white/[0.10] bg-white/[0.04] px-1.5 py-px font-mono text-[9px] tabular-nums text-white/65">
                        ×{row.count}
                      </span>
                      {row.gateReason && (
                        <span
                          className={clsx(
                            'rounded-full border px-1.5 py-px font-mono text-[9px] uppercase tracking-[0.16em]',
                            toneClasses('warn'),
                          )}
                        >
                          {row.gateReason.replace(/_/g, ' ')}
                        </span>
                      )}
                      <span className="ml-auto font-mono text-[9px] uppercase tracking-[0.2em] text-white/45">
                        {ageLabel(row.latestIso)}
                      </span>
                    </div>
                    {row.latestSummary && (
                      <div className="mt-0.5 line-clamp-2 text-[11px] leading-snug text-white/65">
                        {row.latestSummary}
                      </div>
                    )}
                  </div>
                  <ChevronRight size={11} className="shrink-0 text-white/25" />
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
