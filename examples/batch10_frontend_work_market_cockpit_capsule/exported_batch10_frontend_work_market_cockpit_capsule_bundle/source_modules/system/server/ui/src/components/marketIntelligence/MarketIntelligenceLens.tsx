import { useEffect, useState } from 'react';
import clsx from 'clsx';
import { CandlestickChart } from 'lucide-react';

import { useZenith } from '../../stores/useZenith';
import type { MarketDashboardReadModel } from '../../api';
import FinanceAssuranceStrip from '../finance/FinanceAssuranceStrip';
import BrowseEmptyState from '../world/BrowseEmptyState';

// Backend payload fields are `{[key: string]: unknown}` in the generated
// TypeScript contract because the Pydantic models keep `extra=allow`. This
// component narrows them structurally at the boundary and never mutates the
// projection — the cockpit reads the read model and renders it. Finance
// semantics, trust, evidence, and validation belong to the backend; the UI
// surfaces them without re-inventing them.

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown): UnknownRecord | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as UnknownRecord;
  }
  return null;
}

function asArrayOfRecords(value: unknown): UnknownRecord[] {
  if (!Array.isArray(value)) return [];
  return value.filter(
    (item): item is UnknownRecord => item != null && typeof item === 'object',
  );
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function asBool(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null;
}

function formatCount(value: unknown): string {
  const n = asNumber(value);
  return n == null ? '—' : String(n);
}

type MarketReadinessState =
  | 'populated'
  | 'resting'
  | 'stale'
  | 'fallback'
  | 'missing'
  | 'invalid';

interface SituationCard {
  id: string;
  title: string;
  type: string | null;
  horizon: string | null;
  claimLevel: string | null;
  validationState: string | null;
  displayState: string | null;
  entities: string[];
  evidenceCount: number;
  counterevidenceCount: number;
  confidence: number | null;
}

type MarketSelectionChangeSource = 'click' | 'default' | 'url_fallback';
type MarketSelectionDisplaySource = 'url' | 'default' | 'url_fallback' | 'local';

function readQueueItem(raw: UnknownRecord): SituationCard | null {
  const id =
    asString(raw.situation_id) ??
    asString(raw.id) ??
    asString(raw.card_id);
  if (!id) return null;

  const entities = Array.isArray(raw.entities)
    ? raw.entities.filter((value): value is string => typeof value === 'string')
    : Array.isArray(raw.primary_entities)
      ? raw.primary_entities.filter((value): value is string => typeof value === 'string')
      : [];

  const evidence = asArrayOfRecords(raw.evidence);
  const counterevidence = asArrayOfRecords(raw.counterevidence);

  return {
    id,
    title:
      asString(raw.title) ??
      asString(raw.thesis) ??
      asString(raw.label) ??
      id,
    type: asString(raw.type) ?? asString(raw.situation_type),
    horizon: asString(raw.horizon),
    claimLevel: asString(raw.claim_level),
    validationState: asString(raw.validation_state),
    displayState: asString(raw.display_state),
    entities,
    evidenceCount: asNumber(raw.evidence_count) ?? evidence.length,
    counterevidenceCount: asNumber(raw.counterevidence_count) ?? counterevidence.length,
    confidence: asNumber(raw.confidence) ?? asNumber(raw.confidence_score),
  };
}

function statusToneClass(status: string | null): string {
  if (!status) return 'border-white/15 bg-white/[0.05] text-white/70';
  const lower = status.toLowerCase();
  if (lower === 'in_sync' || lower === 'ready' || lower === 'ok') {
    return 'border-emerald-300/30 bg-emerald-300/10 text-emerald-100';
  }
  if (lower.includes('stale') || lower.includes('degraded')) {
    return 'border-amber-300/30 bg-amber-300/10 text-amber-100';
  }
  if (lower.includes('missing') || lower.includes('unavailable') || lower.includes('error')) {
    return 'border-rose-300/30 bg-rose-300/10 text-rose-100';
  }
  return 'border-white/15 bg-white/[0.05] text-white/72';
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

function selectionSourceLabel(source: MarketSelectionDisplaySource): string {
  if (source === 'url') return 'selection · URL';
  if (source === 'url_fallback') return 'selection · URL fallback';
  if (source === 'default') return 'selection · default top';
  return 'selection · local';
}

function TrustStrip({
  readModel,
  routeReady,
}: {
  readModel: MarketDashboardReadModel | null;
  routeReady: boolean | null;
}) {
  const overview = asRecord(readModel?.overview);
  const projectionStatus = asRecord(readModel?.projection_status);
  const authorityBoundary = asRecord(readModel?.authority_boundary);
  const freshness = asRecord(overview?.freshness);

  const status = asString(projectionStatus?.status) ?? 'unknown';
  const safeUse = asString(overview?.safe_use_level) ?? asString(authorityBoundary?.safe_use_level);
  const inputWatermark = asString(freshness?.input_watermark);

  const situationCount =
    asNumber(overview?.situation_count) ??
    readQueueLength(readModel) ??
    null;
  const validatedSignalCount = asNumber(overview?.validated_signal_count) ?? 0;
  const runId = asString(readModel?.run_id);

  const boundaryText =
    asString(authorityBoundary?.summary) ??
    asString(authorityBoundary?.statement) ??
    'Situations are not trading recommendations; backend projection over market_situation_graph_v0.';

  return (
    <section
      data-zenith-market-intelligence-trust="ready"
      className="rounded-[14px] border border-white/[0.08] bg-black/35 px-4 py-3"
    >
      <div className="flex flex-wrap items-center gap-3 text-[11px] uppercase tracking-[0.16em] text-zenith-muted">
        <span className="font-mono">market intelligence cockpit</span>
        <span aria-hidden className="text-white/20">·</span>
        <span className="font-mono text-white/72">run {runId ?? '—'}</span>
        {inputWatermark && (
          <>
            <span aria-hidden className="text-white/20">·</span>
            <span className="font-mono text-white/56">input {inputWatermark}</span>
          </>
        )}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <TrustStat
          kicker="projection status"
          value={status}
          tone={statusToneClass(status)}
          textValue
        />
        <TrustStat
          kicker="situations"
          value={situationCount == null ? '—' : String(situationCount)}
        />
        <TrustStat
          kicker="validated signals"
          value={String(validatedSignalCount)}
          hint="0 by design — validation debt below"
        />
        <TrustStat
          kicker="route ready"
          value={routeReady == null ? '—' : routeReady ? 'yes' : 'no'}
          tone={
            routeReady == null
              ? 'border-white/15 bg-white/[0.05] text-white/72'
              : routeReady
                ? 'border-emerald-300/30 bg-emerald-300/10 text-emerald-100'
                : 'border-amber-300/30 bg-amber-300/10 text-amber-100'
          }
          textValue
        />
      </div>
      <div className="mt-3 grid gap-2 text-[11px] leading-5 text-zenith-soft sm:grid-cols-[1fr_auto] sm:items-center">
        <span>{boundaryText}</span>
        {safeUse && (
          <span className="justify-self-start rounded-full border border-white/[0.08] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-white/68 sm:justify-self-end">
            safe use · {safeUse}
          </span>
        )}
      </div>
    </section>
  );
}

function TrustStat({
  kicker,
  value,
  tone,
  hint,
  textValue,
}: {
  kicker: string;
  value: string;
  tone?: string;
  hint?: string;
  textValue?: boolean;
}) {
  return (
    <div
      className={clsx(
        'rounded-[12px] border px-3 py-2',
        tone ?? 'border-white/[0.08] bg-white/[0.04] text-white/82',
      )}
    >
      <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-muted">{kicker}</div>
      <div
        className={clsx(
          'mt-1 font-mono tabular-nums',
          textValue ? 'text-[12px] uppercase tracking-[0.12em]' : 'text-[18px]',
        )}
      >
        {value}
      </div>
      {hint && <div className="mt-1 text-[10px] leading-4 text-zenith-muted">{hint}</div>}
    </div>
  );
}

function readQueueLength(readModel: MarketDashboardReadModel | null): number | null {
  const queue = asRecord(readModel?.situation_queue);
  if (!queue) return null;
  const items = Array.isArray(queue.items) ? queue.items : null;
  return items ? items.length : null;
}

function readProjectionStatus(readModel: MarketDashboardReadModel | null): string {
  return asString(asRecord(readModel?.projection_status)?.status) ?? 'missing';
}

function readContractVersion(readModel: MarketDashboardReadModel | null): string {
  return asString(readModel?.schema_version) ?? 'missing';
}

function readApiContractVersion(readModel: MarketDashboardReadModel | null): string {
  return asString(asRecord(readModel?.api_contract)?.contract_version) ?? 'missing';
}

function readSafeUseLevel(readModel: MarketDashboardReadModel | null): string {
  const overview = asRecord(readModel?.overview);
  const authorityBoundary = asRecord(readModel?.authority_boundary);
  return (
    asString(overview?.safe_use_level) ??
    asString(authorityBoundary?.safe_use_level) ??
    'unknown'
  );
}

function readValidationDebtCount(readModel: MarketDashboardReadModel | null): number {
  const debt = asRecord(readModel?.validation_debt);
  if (!debt) return 0;
  return (
    asArrayOfRecords(debt.blocked_promotions).length +
    asArrayOfRecords(debt.needed_for_promotion).length
  );
}

function routeReadyAttr(routeReady: boolean | null): 'true' | 'false' | 'unknown' {
  if (routeReady === true) return 'true';
  if (routeReady === false) return 'false';
  return 'unknown';
}

function marketReadinessState({
  readModel,
  routeReady,
  queueLength,
}: {
  readModel: MarketDashboardReadModel | null;
  routeReady: boolean | null;
  queueLength: number;
}): MarketReadinessState {
  if (!readModel) return 'missing';
  if (readContractVersion(readModel) !== 'market_dashboard_read_model_v0') {
    return 'invalid';
  }
  if (
    !asRecord(readModel.projection_status) ||
    !asRecord(readModel.overview) ||
    !asRecord(readModel.situation_queue)
  ) {
    return 'invalid';
  }
  if (routeReady === false) return 'missing';

  const status = readProjectionStatus(readModel);
  if (status !== 'in_sync') {
    const lower = status.toLowerCase();
    if (lower.includes('stale')) return 'stale';
    if (lower.includes('schema') || lower.includes('invalid') || lower.includes('mismatch')) {
      return 'invalid';
    }
    if (lower.includes('missing') || lower.includes('unavailable')) return 'missing';
    return 'fallback';
  }

  return queueLength > 0 ? 'populated' : 'resting';
}

function SituationQueuePanel({
  readModel,
  selectedId,
  onSelect,
}: {
  readModel: MarketDashboardReadModel | null;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const queue = asRecord(readModel?.situation_queue);
  const itemsRaw = asArrayOfRecords(queue?.items);
  const items = itemsRaw
    .map(readQueueItem)
    .filter((item): item is SituationCard => item !== null);

  return (
    <section className="rounded-[14px] border border-white/[0.08] bg-black/30">
      <header className="flex items-center justify-between border-b border-white/[0.06] px-3 py-2">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-muted">
          situation queue
        </div>
        <div className="font-mono text-[11px] tabular-nums text-zenith-soft">
          {items.length}
        </div>
      </header>
      {items.length === 0 ? (
        <div className="px-3 py-4 text-[12px] leading-5 text-zenith-muted">
          No situations in this run. The cockpit waits for the dashboard read
          model to land before surfacing situation cards.
        </div>
      ) : (
        <ul className="divide-y divide-white/[0.05]">
          {items.map((item) => {
            const active = item.id === selectedId;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelect(item.id)}
                  className={clsx(
                    'grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-3 py-2.5 text-left transition-colors',
                    active ? 'bg-white/[0.06]' : 'hover:bg-white/[0.03]',
                  )}
                >
                  <div className="min-w-0">
                    <div className="truncate text-[12px] leading-5 text-white">{item.title}</div>
                    <div className="mt-1 flex flex-wrap gap-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-soft">
                      {item.type && <Pill>{item.type}</Pill>}
                      {item.horizon && <Pill>{item.horizon}</Pill>}
                      {item.claimLevel && <Pill>{item.claimLevel}</Pill>}
                      {item.validationState && <Pill>{item.validationState}</Pill>}
                      {item.displayState && (
                        <Pill tone={item.displayState === 'ready' ? 'positive' : 'caution'}>
                          {item.displayState}
                        </Pill>
                      )}
                    </div>
                  </div>
                  <div className="text-right font-mono text-[10px] uppercase tracking-[0.12em] text-zenith-soft">
                    <div>
                      <span className="text-emerald-200">{item.evidenceCount}E</span>
                      <span className="mx-0.5 text-white/30">/</span>
                      <span className="text-rose-200">{item.counterevidenceCount}C</span>
                    </div>
                    {item.confidence != null && (
                      <div className="mt-0.5 text-white/60">
                        c {item.confidence.toFixed(2)}
                      </div>
                    )}
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function Pill({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone?: 'positive' | 'caution' | 'neutral';
}) {
  return (
    <span
      className={clsx(
        'rounded-full border px-2 py-0.5 font-mono',
        tone === 'positive'
          ? 'border-emerald-300/30 bg-emerald-300/10 text-emerald-100'
          : tone === 'caution'
            ? 'border-amber-300/30 bg-amber-300/10 text-amber-100'
            : 'border-white/[0.10] bg-white/[0.04] text-white/72',
      )}
    >
      {children}
    </span>
  );
}

function SituationDetailPanel({
  readModel,
  selectedId,
  selectionSource,
  selectionReason,
}: {
  readModel: MarketDashboardReadModel | null;
  selectedId: string | null;
  selectionSource: MarketSelectionDisplaySource;
  selectionReason: string | null;
}) {
  const index = asRecord(readModel?.situation_detail_index);
  const detail = selectedId ? asRecord(index?.[selectedId]) : null;

  const thesis =
    asString(detail?.thesis) ??
    asString(detail?.title) ??
    asString(detail?.summary);
  const claimLevel = asString(detail?.claim_level);
  const horizon = asString(detail?.horizon);
  const validationState = asString(detail?.validation_state);
  const displayContract = asRecord(detail?.display_contract);
  const displayState = asString(detail?.display_state) ?? asString(displayContract?.state);
  const safeUseLevel =
    asString(detail?.safe_use_level) ??
    asString(displayContract?.safe_use_level);

  const evidence = asArrayOfRecords(detail?.evidence);
  const counterevidence = asArrayOfRecords(detail?.counterevidence);
  const riskContext = asArrayOfRecords(detail?.risk_context);
  const regimeContext = asArrayOfRecords(detail?.regime_context);
  const sourceRefs = asArrayOfRecords(detail?.source_refs);

  if (!selectedId) {
    return (
      <section className="rounded-[14px] border border-white/[0.08] bg-black/30 px-4 py-5 text-[12px] leading-5 text-zenith-muted">
        Select a situation to inspect its thesis, evidence, counterevidence,
        and source refs.
      </section>
    );
  }

  if (!detail) {
    return (
      <section className="rounded-[14px] border border-white/[0.08] bg-black/30 px-4 py-5 text-[12px] leading-5 text-zenith-soft">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-muted">
          selected situation · {selectedId}
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-soft">
          <Pill tone={selectionSource === 'url_fallback' ? 'caution' : 'neutral'}>
            {selectionSourceLabel(selectionSource)}
          </Pill>
        </div>
        {selectionReason && (
          <div className="mt-2 text-[11px] leading-5 text-amber-100/75">
            {selectionReason}
          </div>
        )}
        <div className="mt-3">
          No detail available for situation <span className="font-mono">{selectedId}</span>.
        </div>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-3 rounded-[14px] border border-white/[0.08] bg-black/30 p-3">
      <header className="border-b border-white/[0.06] pb-2">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-muted">
          selected situation · {selectedId}
        </div>
        <div className="mt-1 text-[14px] leading-6 text-white">{thesis ?? selectedId}</div>
        <div className="mt-2 flex flex-wrap gap-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-soft">
          <Pill tone={selectionSource === 'url_fallback' ? 'caution' : 'neutral'}>
            {selectionSourceLabel(selectionSource)}
          </Pill>
          {claimLevel && <Pill>claim · {claimLevel}</Pill>}
          {horizon && <Pill>horizon · {horizon}</Pill>}
          {validationState && <Pill>validation · {validationState}</Pill>}
          {displayState && <Pill>display · {displayState}</Pill>}
          {safeUseLevel && <Pill>safe use · {safeUseLevel}</Pill>}
        </div>
        {selectionReason && (
          <div className="mt-2 text-[11px] leading-5 text-amber-100/75">
            {selectionReason}
          </div>
        )}
      </header>

      <div className="grid gap-3 lg:grid-cols-2">
        <EvidenceList kicker="evidence" tone="positive" rows={evidence} />
        <EvidenceList kicker="counterevidence" tone="caution" rows={counterevidence} />
      </div>

      <AuthorityBoundaryBlock
        evidenceCount={evidence.length}
        counterevidenceCount={counterevidence.length}
        sourceRefCount={sourceRefs.length}
        validationState={validationState}
        displayState={displayState}
        safeUseLevel={safeUseLevel}
      />

      {(riskContext.length > 0 || regimeContext.length > 0) && (
        <div className="grid gap-3 lg:grid-cols-2">
          {riskContext.length > 0 && (
            <EvidenceList kicker="risk context" rows={riskContext} />
          )}
          {regimeContext.length > 0 && (
            <EvidenceList kicker="regime context" rows={regimeContext} />
          )}
        </div>
      )}

      {sourceRefs.length > 0 && (
        <div className="rounded-[12px] border border-white/[0.06] bg-black/20 p-3">
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-muted">
            source refs ({sourceRefs.length})
          </div>
          <ul className="mt-2 grid gap-1.5 text-[11px] leading-5 text-white/72">
            {sourceRefs.map((ref, idx) => {
              const refId = asString(ref.id) ?? asString(ref.source_ref_id);
              const feedId =
                asString(ref.feed_id) ?? asString(ref.provider) ?? asString(ref.source);
              const path = asString(ref.table_path) ?? asString(ref.path);
              return (
                <li
                  key={`${refId ?? 'ref'}:${idx}`}
                  className="grid grid-cols-[minmax(0,1fr)_auto] gap-2 rounded-[10px] border border-white/[0.05] bg-white/[0.02] px-2 py-1.5"
                >
                  <span className="min-w-0 truncate font-mono text-white/82">
                    {refId ?? `ref ${idx + 1}`}
                  </span>
                  <span className="text-right font-mono text-[10px] uppercase tracking-[0.12em] text-zenith-muted">
                    {feedId ?? ''}
                    {path ? ` · ${path}` : ''}
                  </span>
                </li>
              );
            })}
          </ul>
          <div className="mt-2 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
            arbitrary file read disabled · drilldown returns metadata only
          </div>
        </div>
      )}
    </section>
  );
}

function AuthorityBoundaryBlock({
  evidenceCount,
  counterevidenceCount,
  sourceRefCount,
  validationState,
  displayState,
  safeUseLevel,
}: {
  evidenceCount: number;
  counterevidenceCount: number;
  sourceRefCount: number;
  validationState: string | null;
  displayState: string | null;
  safeUseLevel: string | null;
}) {
  const hasPromotedEvidence = evidenceCount + counterevidenceCount > 0;
  const validated = validationState === 'validated_signal';
  return (
    <div className="rounded-[12px] border border-amber-300/15 bg-amber-300/[0.04] p-3">
      <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-amber-100/75">
        authority boundary
      </div>
      <div className="mt-2 grid gap-1.5 text-[11px] leading-5 text-white/72 sm:grid-cols-2">
        <BoundaryRow
          label="provenance"
          value={
            sourceRefCount > 0
              ? `source refs (${sourceRefCount}) are provenance, not validation-grade evidence`
              : 'no source refs projected for this situation'
          }
        />
        <BoundaryRow
          label="evidence"
          value={
            hasPromotedEvidence
              ? `${evidenceCount} support / ${counterevidenceCount} weakens rows promoted by backend`
              : 'no support or weakening evidence has been promoted for this situation'
          }
        />
        <BoundaryRow
          label="validation"
          value={
            validated
              ? 'backend emitted validated_signal'
              : `promotion blocked until external validation refs land (${validationState ?? 'state unknown'})`
          }
        />
        <BoundaryRow
          label="safe use"
          value={safeUseLevel ?? displayState ?? 'observation only until backend emits safe-use state'}
        />
      </div>
    </div>
  );
}

function BoundaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[10px] border border-white/[0.06] bg-black/25 px-2 py-1.5">
      <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/42">
        {label}
      </div>
      <div className="mt-0.5 text-white/78">{value}</div>
    </div>
  );
}

function EvidenceList({
  kicker,
  tone,
  rows,
}: {
  kicker: string;
  tone?: 'positive' | 'caution';
  rows: UnknownRecord[];
}) {
  return (
    <div
      className={clsx(
        'rounded-[12px] border bg-black/20 p-3',
        tone === 'positive'
          ? 'border-emerald-300/15'
          : tone === 'caution'
            ? 'border-amber-300/15'
            : 'border-white/[0.06]',
      )}
    >
      <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-muted">
        {kicker} ({rows.length})
      </div>
      {rows.length === 0 ? (
        <div className="mt-2 text-[11px] leading-5 text-zenith-muted">none recorded</div>
      ) : (
        <ul className="mt-2 grid gap-1.5 text-[11px] leading-5 text-white/72">
          {rows.map((row, idx) => {
            const label =
              asString(row.label) ??
              asString(row.title) ??
              asString(row.statement) ??
              asString(row.summary) ??
              asString(row.id) ??
              `row ${idx + 1}`;
            const reasonCode = asString(row.reason_code) ?? asString(row.kind);
            const severity = asString(row.severity);
            return (
              <li key={`${kicker}:${idx}`} className="grid gap-1 rounded-[10px] border border-white/[0.05] bg-white/[0.02] px-2 py-1.5">
                <span className="text-white/85">{label}</span>
                {(reasonCode || severity) && (
                  <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
                    {reasonCode ?? ''}
                    {reasonCode && severity ? ' · ' : ''}
                    {severity ?? ''}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function ValidationDebtPanel({ readModel }: { readModel: MarketDashboardReadModel | null }) {
  const debt = asRecord(readModel?.validation_debt);
  const blocked = asArrayOfRecords(debt?.blocked_promotions);
  const needed = asArrayOfRecords(debt?.needed_for_promotion);
  const summary = asString(debt?.summary);

  return (
    <section className="rounded-[14px] border border-white/[0.08] bg-black/30 p-3">
      <header className="border-b border-white/[0.06] pb-2">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-muted">
          validation debt
        </div>
        <div className="mt-1 text-[11px] leading-5 text-zenith-soft">
          {summary ??
            'Validated signals require external validation refs. Until they land, situations remain salience/observation only.'}
        </div>
      </header>

      <div className="mt-3 grid gap-2 text-[11px] leading-5 text-white/72">
        <div className="rounded-[10px] border border-white/[0.05] bg-white/[0.02] px-2 py-1.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
            blocked promotions ({blocked.length})
          </div>
          {blocked.length === 0 ? (
            <div className="mt-1 text-zenith-muted">none</div>
          ) : (
            <ul className="mt-1 grid gap-1">
              {blocked.map((row, idx) => (
                <li key={`blocked:${idx}`} className="grid gap-0.5">
                  <span className="truncate text-white/82">
                    {asString(row.situation_id) ??
                      asString(row.id) ??
                      asString(row.candidate_id) ??
                      `entry ${idx + 1}`}
                  </span>
                  {asString(row.reason) && (
                    <span className="font-mono text-[9px] uppercase tracking-[0.12em] text-zenith-muted">
                      {asString(row.reason)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
        {needed.length > 0 && (
          <div className="rounded-[10px] border border-white/[0.05] bg-white/[0.02] px-2 py-1.5">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
              needed for promotion ({needed.length})
            </div>
            <ul className="mt-1 grid gap-0.5">
              {needed.map((row, idx) => (
                <li key={`needed:${idx}`} className="truncate text-white/82">
                  {asString(row.label) ??
                    asString(row.requirement) ??
                    asString(row.id) ??
                    `requirement ${idx + 1}`}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function ProvenanceAndGraphPanel({
  readModel,
}: {
  readModel: MarketDashboardReadModel | null;
}) {
  const provenance = asRecord(readModel?.provenance_index);
  const builders = asArrayOfRecords(provenance?.builders);
  const lineage = asArrayOfRecords(provenance?.lineage);

  const graph = asRecord(readModel?.graph_slice);
  const nodeCount = asArrayOfRecords(graph?.nodes).length;
  const edgeCount = asArrayOfRecords(graph?.edges).length;

  const drilldown = asRecord(readModel?.drilldown_index);
  const sourceRefs = asArrayOfRecords(drilldown?.source_refs);

  return (
    <section className="rounded-[14px] border border-white/[0.08] bg-black/30 p-3">
      <header className="border-b border-white/[0.06] pb-2">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-muted">
          provenance · graph · drilldown
        </div>
      </header>

      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        <Stat kicker="graph nodes" value={formatCount(nodeCount)} />
        <Stat kicker="graph edges" value={formatCount(edgeCount)} />
        <Stat kicker="source refs" value={formatCount(sourceRefs.length)} />
      </div>

      {(builders.length > 0 || lineage.length > 0) && (
        <div className="mt-3 grid gap-2 text-[11px] leading-5 text-white/72">
          {builders.length > 0 && (
            <div className="rounded-[10px] border border-white/[0.05] bg-white/[0.02] px-2 py-1.5">
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
                builders ({builders.length})
              </div>
              <ul className="mt-1 grid gap-0.5">
                {builders.slice(0, 6).map((row, idx) => (
                  <li key={`builder:${idx}`} className="truncate font-mono text-white/82">
                    {asString(row.name) ?? asString(row.id) ?? `builder ${idx + 1}`}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {lineage.length > 0 && (
            <div className="rounded-[10px] border border-white/[0.05] bg-white/[0.02] px-2 py-1.5">
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
                lineage ({lineage.length})
              </div>
              <ul className="mt-1 grid gap-0.5">
                {lineage.slice(0, 6).map((row, idx) => (
                  <li key={`lineage:${idx}`} className="truncate text-white/82">
                    {asString(row.label) ?? asString(row.id) ?? `step ${idx + 1}`}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Stat({ kicker, value }: { kicker: string; value: string }) {
  return (
    <div className="rounded-[10px] border border-white/[0.06] bg-white/[0.03] px-2 py-1.5">
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">{kicker}</div>
      <div className="mt-0.5 font-mono text-[14px] tabular-nums text-white">{value}</div>
    </div>
  );
}

export interface MarketIntelligenceLensProps {
  /**
   * Override the world-model embedding with a directly-fetched read model
   * (e.g. /api/market/intelligence/latest). When present, takes priority
   * over worldModel.latest_market_dashboard_read_model. See Intelligence
   * MarketsLens for the fallback ladder. Per cap
   * cap_quick_intelligence_v0_2_markets_read_model_loa_47528fc23b3f.
   */
  readModelOverride?: MarketDashboardReadModel | null;
  /**
   * Override the route-ready signal when supplying a read model from a
   * source other than worldModel.
   */
  routeReadyOverride?: boolean | null;
  selectedSituationId?: string | null;
  objectToken?: string | null;
  onSelectedSituationChange?: (id: string, source: MarketSelectionChangeSource) => void;
}

export default function MarketIntelligenceLens({
  readModelOverride = null,
  routeReadyOverride = null,
  selectedSituationId = null,
  objectToken = null,
  onSelectedSituationChange,
}: MarketIntelligenceLensProps = {}) {
  const { worldModel } = useZenith();
  const readModel =
    readModelOverride ??
    ((worldModel?.latest_market_dashboard_read_model ?? null) as
      | MarketDashboardReadModel
      | null);
  const routeReady =
    routeReadyOverride !== null
      ? routeReadyOverride
      : asBool(worldModel?.latest_market_dashboard_route_ready);

  // React Compiler handles memoization for the queue projection + selection
  // resolution. Manual useMemo wrappers were tripping
  // react-hooks/preserve-manual-memoization because the deps could be mutated
  // (read model + queue items both flow from the world model store). Letting
  // the compiler memoize keeps the projection cheap and lint-clean.
  const queueItems: SituationCard[] = (() => {
    const queue = asRecord(readModel?.situation_queue);
    return asArrayOfRecords(queue?.items)
      .map(readQueueItem)
      .filter((item): item is SituationCard => item !== null);
  })();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selection = ((): {
    id: string | null;
    source: 'url' | 'url_fallback' | 'local' | 'default';
    reason: string | null;
  } => {
    const tokenIssue = objectTokenIssue(objectToken, 'situation');
    if (
      selectedSituationId &&
      queueItems.some((item) => item.id === selectedSituationId)
    ) {
      return {
        id: selectedSituationId,
        source: 'url',
        reason: null,
      };
    }
    if (selectedSituationId && queueItems.length > 0) {
      return {
        id: queueItems[0].id,
        source: 'url_fallback',
        reason: `URL requested situation:${selectedSituationId}, but that object is not present in this run. Showing the top situation instead.`,
      };
    }
    if (selectedId && queueItems.some((item) => item.id === selectedId)) {
      return {
        id: selectedId,
        source: 'local',
        reason: null,
      };
    }
    if (queueItems.length > 0) {
      return {
        id: queueItems[0].id,
        source: tokenIssue ? 'url_fallback' : 'default',
        reason: tokenIssue,
      };
    }
    return {
      id: null,
      source: tokenIssue ? 'url_fallback' : 'default',
      reason: tokenIssue,
    };
  })();

  useEffect(() => {
    if (!selection.id) return;
    if (selection.source === 'default' || selection.source === 'url_fallback') {
      onSelectedSituationChange?.(selection.id, selection.source);
    }
  }, [onSelectedSituationChange, selection.id, selection.source]);

  const handleSelect = (id: string) => {
    setSelectedId(id);
    onSelectedSituationChange?.(id, 'click');
  };

  // Wave 13 — meaningful resting state. The pre-Wave-13 path rendered the
  // 12-col observation grid even when the run had zero situations, which
  // produced the screenshot-visible "sparse tile field with one thin
  // panel" empty state on /station/market-intelligence (acceptance matrix
  // render 20260516T231123_466626000Z; captured separately at
  // cap_quick on market_intelligence empty-state legibility). When the
  // queue is empty, the cockpit should explain itself — what it watches,
  // what controls when situations appear — rather than render a near-
  // empty grid that reads as "loading" or "broken".
  const semanticState = marketReadinessState({
    readModel,
    routeReady,
    queueLength: queueItems.length,
  });
  const isResting = semanticState !== 'populated';
  const situationCount = readQueueLength(readModel) ?? queueItems.length;
  const projectionStatus = readProjectionStatus(readModel);
  const contractVersion = readContractVersion(readModel);
  const apiContractVersion = readApiContractVersion(readModel);
  const safeUseLevel = readSafeUseLevel(readModel);
  const validationDebtCount = readValidationDebtCount(readModel);

  return (
    <div
      data-zenith-market-intelligence-surface="ready"
      data-zenith-market-intelligence-state={semanticState}
      data-zenith-market-intelligence-contract={contractVersion}
      data-zenith-market-intelligence-api-contract={apiContractVersion}
      data-zenith-market-intelligence-route-ready={routeReadyAttr(routeReady)}
      data-zenith-market-intelligence-safe-use-level={safeUseLevel}
      data-zenith-market-intelligence-situation-count={String(situationCount)}
      data-zenith-market-intelligence-validation-debt-count={String(validationDebtCount)}
      data-zenith-market-intelligence-projection-status={projectionStatus}
      className="flex min-h-0 flex-1 flex-col gap-3"
    >
      <TrustStrip readModel={readModel} routeReady={routeReady} />
      <FinanceAssuranceStrip readModel={readModel} surface="marketIntelligence" />

      {isResting ? (
        <BrowseEmptyState
          icon={CandlestickChart}
          kicker="Market intelligence · resting"
          title="Observation surface waiting on the situation queue"
          summary="No situations are currently surfaced by the market dashboard read model. The cockpit ranks signals as soon as the latest_market_dashboard_read_model_v0 projection lands a non-empty situation queue. Until then, the trust strip above reports projection status, run identity, and freshness so the resting state stays honest about why nothing is yet ranked."
          meta={[
            'projection · market_dashboard_read_model_v0',
            'source · latest_market_dashboard_read_model',
            'live route · /station/market-intelligence',
            'situations are observations · not trades',
          ]}
        />
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-12 gap-3">
          <div className="col-span-12 min-h-0 lg:col-span-4">
            <SituationQueuePanel
              readModel={readModel}
              selectedId={selection.id}
              onSelect={handleSelect}
            />
          </div>
          <div className="col-span-12 min-h-0 lg:col-span-5">
            <SituationDetailPanel
              readModel={readModel}
              selectedId={selection.id}
              selectionSource={selection.source}
              selectionReason={selection.reason}
            />
          </div>
          <div className="col-span-12 flex min-h-0 flex-col gap-3 lg:col-span-3">
            <ValidationDebtPanel readModel={readModel} />
            <ProvenanceAndGraphPanel readModel={readModel} />
          </div>
        </div>
      )}
    </div>
  );
}
