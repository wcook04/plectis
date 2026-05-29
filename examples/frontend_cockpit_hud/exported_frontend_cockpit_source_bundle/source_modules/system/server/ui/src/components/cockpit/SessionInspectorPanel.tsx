// [PURPOSE] Cockpit session inspector — Surface 3.
//
// Pass 1 placeholder: today's world model does not project per-session detail
// (files read/wrote, milestones, errors, write-conflict risk). The inspector
// renders a transparent empty state that describes exactly what is missing
// and which Pass adds it, plus the closest available signal: the next move
// surfaced by the attention snapshot.
//
// Pass 2 wires `/api/cockpit/sessions/{session_id}` here. Pass 3 (deferred)
// adds the milestone timeline + collapsed waterfall.
import clsx from 'clsx';
import { Activity, AlertTriangle, ArrowRight, CheckCircle2, Inbox, Hourglass, RadioTower } from 'lucide-react';
import type { AttentionNextMove, AttentionSnapshot, VantageResponse } from '../../api';
import { PanelHead } from '../world/cellHelpers';
import { toneClasses, type Tone } from '../world/cellHelpers.utils';

function readinessTone(state: string | null | undefined): Tone {
  const normalized = (state ?? '').toLowerCase();
  if (['blocked'].includes(normalized)) return 'block';
  if (['claimed', 'active', 'ready', 'shaping', 'captured'].includes(normalized)) return 'ok';
  if (['done', 'signoff', 'retired'].includes(normalized)) return 'warn';
  return 'neutral';
}

function workItemTypeLabel(
  id: string | null | undefined,
  workItemType: string | null | undefined,
  candidateWorkItemType: string | null | undefined,
) {
  const explicitType = workItemType ?? candidateWorkItemType;
  if (explicitType) return explicitType;
  const normalizedId = (id ?? '').toLowerCase();
  if (normalizedId.startsWith('task_')) return 'task';
  if (normalizedId.startsWith('cap_')) return 'cap';
  return 'untyped';
}

function contractLabel(contract: string) {
  return contract.replace(/_contract$/u, '').replace(/_/gu, ' ');
}

function NextMoveRow({ move }: { move: AttentionNextMove }) {
  return (
    <div className={clsx('rounded-[12px] border px-3 py-2', toneClasses('neutral'))}>
      <div className="flex items-center gap-1.5">
        <ArrowRight size={11} className="text-zenith-soft" />
        <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-zenith-soft">next move</span>
        {move.owner && (
          <span className="rounded-full border border-white/[0.12] bg-white/[0.03] px-1.5 py-px font-mono text-[9px] uppercase tracking-[0.16em] text-white/70">
            {move.owner}
          </span>
        )}
      </div>
      {move.summary && (
        <div className="mt-1 text-[12px] leading-snug text-white/85">{move.summary}</div>
      )}
      {move.command && (
        <div className="mt-1 truncate font-mono text-[10.5px] text-zenith-soft" title={move.command}>
          {move.command}
        </div>
      )}
    </div>
  );
}

export default function SessionInspectorPanel({
  attention,
  vantage,
  vantageLoading = false,
  vantageError = null,
}: {
  attention: AttentionSnapshot | null;
  vantage?: VantageResponse | null;
  vantageLoading?: boolean;
  vantageError?: string | null;
}) {
  const nextMoves = attention?.next_moves ?? [];
  const banner = attention?.banner;
  const workSpine = vantage?.work_spine ?? null;
  const currentNext = workSpine?.current_next ?? null;
  const sourceRef =
    currentNext?.source_ref ??
    workSpine?.source_refs?.find((ref) => ref.includes('frontend_demo_readiness_queue')) ??
    workSpine?.source_refs?.[0] ??
    'frontend_demo_readiness_queue.json';
  const sourceName = sourceRef.split('/').pop() ?? sourceRef;
  const command =
    currentNext?.drilldown_command ??
    workSpine?.drilldown_command ??
    './repo-python kernel.py --option-surface task_ledger --band card';
  const currentTone = readinessTone(currentNext?.state);
  const currentType = workItemTypeLabel(
    currentNext?.id,
    currentNext?.work_item_type,
    currentNext?.candidate_work_item_type,
  );
  const contractStatus = currentNext?.contract_status;
  const missingContracts = currentNext?.missing_contracts ?? contractStatus?.missing_contracts ?? [];
  const hasAllContracts = Boolean(
    currentNext &&
      contractStatus?.has_completion_contract &&
      contractStatus?.has_integration_contract &&
      contractStatus?.has_satisfaction_contract,
  );
  const recommendedAction = currentNext?.recommended_action;

  return (
    <section data-cockpit-section="session-inspector" className="panel flex flex-col">
      <PanelHead
        kicker="Session inspector"
        title="No session selected"
        trailing={
          <span className="inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-[0.2em] text-white/35">
            <Hourglass size={10} /> pass 2 wires per-session detail
          </span>
        }
      />
      <div className="panel-body-padded flex flex-col gap-2.5">
        <div
          data-cockpit-section="launch-readiness-current"
          className={clsx('rounded-[12px] border px-3 py-2.5', toneClasses(currentTone))}
        >
          <div className="flex items-center gap-1.5">
            <RadioTower size={11} className="text-white/60" />
            <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-zenith-soft">
              launch queue
            </span>
            <span className="ml-auto truncate font-mono text-[9px] uppercase tracking-[0.16em] text-zenith-muted" title={sourceRef}>
              {sourceName}
            </span>
          </div>
          {vantageLoading && !currentNext ? (
            <div className="mt-1.5 text-[12px] leading-snug text-white/60">
              Loading kernel Vantage work spine.
            </div>
          ) : vantageError && !currentNext ? (
            <div className="mt-1.5 text-[12px] leading-snug text-amber-100">
              Vantage queue unavailable: {vantageError}
            </div>
          ) : (
            <>
              <div className="mt-1.5 line-clamp-2 text-[13px] leading-snug text-white">
                {currentNext?.title ?? 'No active launch-readiness WorkItem published.'}
              </div>
              <div className="mt-2 grid grid-cols-3 gap-1.5">
                <div className="min-w-0 rounded-[8px] border border-white/10 bg-black/20 px-2 py-1">
                  <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-white/40">id</div>
                  <div className="truncate font-mono text-[10.5px] text-white/80">{currentNext?.id ?? 'none'}</div>
                </div>
                <div className="min-w-0 rounded-[8px] border border-white/10 bg-black/20 px-2 py-1">
                  <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-white/40">state</div>
                  <div className="truncate font-mono text-[10.5px] text-white/80">{currentNext?.state ?? 'unknown'}</div>
                </div>
                <div className="min-w-0 rounded-[8px] border border-white/10 bg-black/20 px-2 py-1">
                  <div className="font-mono text-[8px] uppercase tracking-[0.18em] text-white/40">type</div>
                  <div className="truncate font-mono text-[10.5px] text-white/80">
                    {currentType}
                  </div>
                </div>
              </div>
              {(missingContracts.length > 0 || hasAllContracts || recommendedAction) && (
                <div className="mt-2 rounded-[8px] border border-white/10 bg-black/20 px-2 py-1.5">
                  {(missingContracts.length > 0 || hasAllContracts) && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      {missingContracts.length > 0 ? (
                        <>
                          <AlertTriangle size={11} className="shrink-0 text-amber-200/80" />
                          <span className="font-mono text-[8px] uppercase tracking-[0.18em] text-amber-100/75">
                            contracts missing
                          </span>
                          {missingContracts.map((contract) => (
                            <span
                              key={contract}
                              className="rounded-full border border-amber-200/20 bg-amber-200/10 px-1.5 py-px font-mono text-[9px] uppercase tracking-[0.12em] text-amber-50/85"
                            >
                              {contractLabel(contract)}
                            </span>
                          ))}
                        </>
                      ) : (
                        <>
                          <CheckCircle2 size={11} className="shrink-0 text-emerald-200/80" />
                          <span className="font-mono text-[8px] uppercase tracking-[0.18em] text-emerald-100/75">
                            contracts shaped
                          </span>
                        </>
                      )}
                    </div>
                  )}
                  {recommendedAction && (
                    <div className="mt-1 line-clamp-2 text-[11px] leading-snug text-white/60">
                      {recommendedAction}
                    </div>
                  )}
                </div>
              )}
              <div className="mt-2 truncate rounded-[8px] bg-white/[0.035] px-2 py-1 font-mono text-[9.5px] text-white/42" title={command}>
                {command}
              </div>
            </>
          )}
        </div>

        <div className={clsx('rounded-[12px] border px-3 py-2.5 text-[11.5px] leading-snug', toneClasses('neutral'))}>
          <div className="flex items-center gap-1.5">
            <Inbox size={11} className="text-zenith-soft" />
            <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-zenith-soft">
              not yet wired
            </span>
          </div>
          <p className="mt-1.5 text-white/75">
            Per-session detail (read/write counts, milestones, conflict risk,
            severity, last meaningful event) lands when{' '}
            <span className="font-mono text-white">/api/cockpit/sessions/&#123;id&#125;</span> ships
            in Pass 2. The substrate already exists in{' '}
            <span className="font-mono text-white/85">metabolism_blackboard.files_touched_json</span>
            ; only the projection is missing.
          </p>
        </div>

        {banner && (banner.summary || banner.title) && (
          <div className={clsx(
            'rounded-[12px] border px-3 py-2',
            banner.tone === 'block' ? toneClasses('block') : banner.tone === 'warn' ? toneClasses('warn') : toneClasses('ok'),
          )}>
            <div className="flex items-center gap-1.5">
              <Activity size={11} />
              <span className="font-mono text-[9px] uppercase tracking-[0.2em]">banner</span>
            </div>
            <div className="mt-1 font-display text-[13px] leading-tight uppercase tracking-[0.04em]">
              {banner.title}
            </div>
            {banner.summary && (
              <div className="mt-0.5 text-[11.5px] leading-snug opacity-85">{banner.summary}</div>
            )}
          </div>
        )}

        {nextMoves.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-zenith-muted">
              what the attention surface suggests
            </span>
            {nextMoves.slice(0, 3).map((move, idx) => (
              <NextMoveRow key={idx} move={move} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
