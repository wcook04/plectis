// [PURPOSE] Intelligence v0.6 — human-readable market cockpit.
//
// v0.5 inverted the hierarchy but stayed too boxy and too literal. The
// operator's v0.6 packet (2026-05-14) demands:
//   - compact ticker tape, not large per-symbol cards;
//   - signal-tape rows that read like financial observations (title +
//     why_interesting from substrate), not raw machine tags;
//   - entity normalization (no more `equity:ARM`);
//   - non-time-series visual encodings: microbars, diverging z-score
//     strips, flow-leaderboard bars, probability dots; never fake
//     line charts when no time series exists;
//   - selected-situation explainer: what it means / why it surfaced /
//     key numbers / what would change it / related;
//   - diagnostics demoted out of the primary viewport.
//
// The substrate already emits the human fields (latest_quant_presentation_mart
// .ranked_observations: title + why_interesting + caveats +
// disconfirming_checks + score.{confidence, display_readiness,
// interestingness}; stockgrid_flow_board with ticker/company/sector/flow_usd/
// conviction/signal_value/win_rate; macro_regime_board with bucket/
// average_z_score/top_series; prediction_market_event_board with
// event_title/question/probability/volume/probability_change/spread/topic;
// situation_detail_index with card.title + evidence_edges/counterevidence_edges
// each carrying reason_code + metric + weight + target_entity_id).
//
// v0.6 is therefore a React composition pass over the existing read model
// and worldModel.market_feeds. No frontend finance computation; no fake
// time series; no Bloomberg clone; no /station promotion; no
// generic DossierShell.

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import clsx from 'clsx';

import { api, type MarketBrowsePlane, type MarketDashboardReadModel, type MarketFeedRun } from '../../api';

// -------- structural helpers ----------------------------------------------

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
    (entry): entry is UnknownRecord => entry != null && typeof entry === 'object',
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

// -------- entity + label normalization ------------------------------------

interface NormalizedEntity {
  raw: string;
  kind: 'equity' | 'etf' | 'macro' | 'event' | 'provider' | 'theme' | 'other';
  label: string;
  hint: string | null;
}

function normalizeEntity(raw: string): NormalizedEntity {
  if (raw.startsWith('equity:')) {
    return { raw, kind: 'equity', label: raw.slice(7), hint: null };
  }
  if (raw.startsWith('etf:')) {
    return { raw, kind: 'etf', label: raw.slice(4), hint: null };
  }
  if (raw.startsWith('macro_series:')) {
    const slug = raw.slice(13);
    return {
      raw,
      kind: 'macro',
      label: slug
        .replace(/_/g, ' ')
        .replace(/\b([a-z])/g, (m) => m.toUpperCase()),
      hint: slug,
    };
  }
  if (raw.startsWith('prediction_market_event:')) {
    const slug = raw.slice(24);
    return { raw, kind: 'event', label: slug.slice(0, 28), hint: slug };
  }
  if (raw.startsWith('provider:')) {
    return { raw, kind: 'provider', label: raw.slice(9), hint: null };
  }
  if (raw.startsWith('theme:')) {
    return { raw, kind: 'theme', label: raw.slice(6), hint: null };
  }
  return { raw, kind: 'other', label: raw, hint: null };
}

// Translate a raw machine reason_code into a single operator-meaningful
// English fragment. Keeps the internal code accessible in tooltips.
const REASON_CODE_TRANSLATIONS: Record<string, string> = {
  STOCKGRID_FLOW_TOP: 'Top of Stockgrid flow board',
  FLOW_SALIENCE_NOT_RECOMMENDATION: 'Flow salience, not a recommendation',
  PREDICTION_MARKET_EVENT_LIQUIDITY: 'Prediction-market liquidity is notable',
  EVENT_MARKET_NOT_FORECAST: 'Event market, not a forecast',
  MACRO_BUCKET_DISPLACED: 'Macro bucket displaced from baseline',
  MACRO_SEMANTICS_DECLARED: 'Macro context declared',
  TOP_ABS_5D_MOVE: 'Largest absolute 5-day equity move in the run',
  PRICE_ACTION_SALIENCE: 'Price-action salience',
  COVERAGE_OR_MISSINGNESS_GAP: 'Coverage gap — lane is empty',
  EMPTY_LANE_NOT_MARKET_SIGNAL: 'Empty lane is not a market signal',
  PROVIDER_DRIFT_FETCH_FAILURES: 'Provider drift: fetch failures',
  PROVIDER_DRIFT_DECLARED: 'Provider drift declared',
  CROSS_ASSET_THEME_ARM_ENERGY: 'ARM × Energy cross-asset theme',
  CROSS_ASSET_THEME_DECLARED: 'Cross-asset theme declared',
};

function translateReasonCode(code: string | null | undefined): string {
  if (!code) return '—';
  return REASON_CODE_TRANSLATIONS[code] ?? code.replace(/_/g, ' ').toLowerCase();
}

// Plain-English operator labels for backend state words.
const STATE_LABELS: Record<string, string> = {
  salience_observation: 'observation, not validated',
  signal_candidate: 'candidate signal',
  data_fact: 'data fact',
  validated_signal: 'validated',
  data_quality_warning: 'data-quality warning',
  risk_context: 'risk context',
  run_evidence_ready: 'feed evidence ready',
  internal_dashboard_evidence: 'dashboard observation only',
  external_use_blocked: 'not for external use',
  degraded: 'needs more signal',
  ready: 'ready',
  in_sync: 'in sync',
  stale: 'stale',
};

function stateLabel(value: string | null | undefined): string {
  if (!value) return '—';
  return STATE_LABELS[value] ?? value.replace(/_/g, ' ');
}

// -------- formatters ------------------------------------------------------

function fmtPct(value: number | null, signed = true): string {
  if (value == null) return '—';
  const sign = signed && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

function fmtPrice(value: number | null): string {
  if (value == null) return '—';
  const abs = Math.abs(value);
  if (abs >= 1000) return value.toFixed(1);
  if (abs >= 100) return value.toFixed(2);
  return value.toFixed(2);
}

function fmtUsdCompact(value: number | null): string {
  if (value == null) return '—';
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

function parseDate(iso: string | null): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.valueOf()) ? null : d;
}

// Calendar-day delta. Operator-named rename 2026-05-14: prior name
// `tradingDaysBetween` was misleading — no market calendar is applied
// here. The UI label always says "calendar days" / "d behind".
function calendarDaysBetween(earlier: Date, later: Date): number {
  const ms = later.getTime() - earlier.getTime();
  return Math.max(0, Math.round(ms / (1000 * 60 * 60 * 24)));
}

// -------- types -----------------------------------------------------------

export type MarketSelectionChangeSource = 'click' | 'default' | 'url_fallback';
type MarketSelectionDisplaySource = 'url' | 'default' | 'url_fallback' | 'local';

export interface MarketCockpitProps {
  readModel: MarketDashboardReadModel | null;
  worldModelMarketFeeds: UnknownRecord | null;
  selectedSituationId?: string | null;
  selectedRunId?: string | null;
  latestRunId?: string | null;
  objectToken?: string | null;
  onSelectedSituationChange?: (id: string, source: MarketSelectionChangeSource) => void;
  onRunChange?: (runId: string | null) => void;
  pinnedLoading?: boolean;
  pinnedError?: string | null;
  // When a FEEDS refresh is in flight and MarketsLens is showing the
  // last-good read model, this is the in-flight run id. The status
  // strip surfaces "refresh in progress: RUN_..." without blanking the
  // cockpit.
  activeRefreshRunId?: string | null;
}

interface RankedObs {
  id: string;
  rank: number | null;
  title: string;
  whyInteresting: string | null;
  entities: NormalizedEntity[];
  primaryMetricName: string | null;
  primaryMetricValue: number | null;
  reasons: string[];
  reasonCodes: string[];
  caveats: string[];
  disconfirming: string[];
  confidence: number | null;
  interestingness: number | null;
  displayReadiness: number | null;
  displayState: string | null;
  claimLevel: string | null;
  safeUseLevel: string | null;
}

interface FlowRow {
  ticker: string;
  company: string;
  sector: string | null;
  flowUsd: number | null;
  netUsd: number | null;
  conviction: number | null;
  signalValue: number | null;
  winRate: number | null;
  direction: number | null;
}

interface MacroBucketRow {
  bucket: string;
  averageZ: number | null;
  seriesCount: number | null;
  vintageStatus: string | null;
  topSeries: Array<{
    ticker: string;
    label: string;
    z: number | null;
    recentChange: number | null;
    obsDate: string | null;
  }>;
}

interface EventRow {
  id: string;
  title: string;
  question: string | null;
  topic: string | null;
  probability: number | null;
  probabilityChange: number | null;
  volume: number | null;
  spread: number | null;
}

interface CoverageRow {
  feedId: string;
  label: string;
  rows: number | null;
  freshness: string | null;
  quality: string | null;
  fetchSuccessRate: number | null;
  drifts: string[];
  emptyReason: string | null;
}

interface SituationCardRow {
  id: string;
  title: string;
  situationType: string | null;
  horizon: string | null;
  primaryEntities: NormalizedEntity[];
  displayState: string | null;
  claimLevel: string | null;
  confidence: number | null;
  evidenceCount: number;
  counterevidenceCount: number;
}

interface BreadthGroupRow {
  label: string;
  detail: string | null;
  primary: string | null;
  count: number | null;
  tone: 'ok' | 'warn' | 'block' | 'neutral';
}

// v0.8: backend-built market interpretation slice. The backend now emits
// rows × columns × cells (market_field), market_pulse facts, deterministic
// signal_cards, visual_specs naming primitives, and data_quality that
// demotes signal-only / empty / stale defects. The frontend renders this
// directly; it does not arrange backend rows into panels.
interface HmcRow {
  id: string;
  kind: string;
  label: string;
  subtitle: string | null;
  group: string | null;
}
interface HmcColumn {
  id: string;
  label: string;
  kind: string;
}
interface HmcCell {
  rowId: string;
  columnId: string;
  value: number | null;
  normalized: number;
  direction: number;
  tone: 'pos' | 'neg' | 'neutral' | 'ok' | 'warn' | 'block';
  label: string | null;
  metricName: string | null;
  metricValue: number | null;
  confidence: number | null;
  completeness: number;
  situationIds: string[];
  observationIds: string[];
}
interface HmcSignalCard {
  id: string;
  title: string;
  oneLine: string | null;
  keyNumbers: Array<{ label: string; value: string }>;
  watchpoint: string | null;
  caveat: string | null;
  linkedRowId: string | null;
  linkedSituationIds: string[];
}
interface HmcPulseFact {
  label: string;
  value: string;
  tone: 'pos' | 'neg' | 'neutral' | 'ok' | 'warn' | 'block';
  interpretation: string | null;
  caveat: string | null;
}
interface HmcDataQualityRow {
  lane: string;
  state: string;
  rows: number | null;
  problem: string;
  action: string;
}
interface HmcGlobalState {
  id: string;
  label: string;
  lane: string | null;
  tone: 'pos' | 'neg' | 'neutral' | 'ok' | 'warn' | 'block';
  scope: string | null;
  promotedTo: string | null;
}
interface HmcMetricSpec {
  id: string;
  label: string;
  unit: string;
  encoding: string;
}
interface HmcPlaneRow {
  id: string;
  label: string;
  subtitle: string | null;
  metrics: Record<string, number | null>;
  topSeries?: UnknownRecord[];
}
interface HmcVisualPlane {
  id: string;
  title: string;
  primitive: string;
  rows: HmcPlaneRow[];
  metricSpecs: HmcMetricSpec[];
  legend: string | null;
  interpretation: string | null;
  applicability: string;
  emptyPolicy: string | null;
}
interface HumanMarketCockpit {
  schemaVersion: string;
  rows: HmcRow[];
  columns: HmcColumn[];
  cells: HmcCell[];
  signalCards: HmcSignalCard[];
  marketPulse: HmcPulseFact[];
  dataQuality: HmcDataQualityRow[];
  visualPlanes: HmcVisualPlane[];
  globalStates: HmcGlobalState[];
  columnLegends: Record<string, string>;
  applicabilityByKey: Map<string, string>; // `${row_id}::${column_id}` -> state
  // v0.10 workspace
  workspace: HmcWorkspace | null;
}

interface HmcPlaneNavEntry {
  id: string;
  label: string;
  rowCount: number;
  status: string;
  primitive: string;
  defaultSort: { column: string | null; direction: string | null };
  feedId: string | null;
  entityKind: string | null;
}
interface HmcDisplayColumn {
  id: string;
  label: string;
  kind: string;
}
interface HmcWorkspace {
  // v0.10.1: workspace.runId is the run the bundle is composed from.
  // The frontend MUST use this for active-plane fetches, NOT the UI's
  // selectedRunId/latestRunId — otherwise plane_nav (built from the
  // bundle run) and the active route (called with the in-flight run)
  // disagree and the active plane shows "0 rows" while nav says 457.
  runId: string | null;
  defaultPlaneId: string | null;
  planeNav: HmcPlaneNavEntry[];
  activePlanePreview: {
    planeId: string | null;
    rows: UnknownRecord[];
    columns: HmcDisplayColumn[];
    rowCountTotal: number;
    sort: { column: string | null; direction: string | null };
  };
  layoutContract: {
    primaryPlaneMinRows: number;
    fillAvailableViewport: boolean;
    rightExplainerWidth: number;
    collapseSignalCardsWhenSpaceConstrained: boolean;
  };
}

// -------- substrate parsers -----------------------------------------------

function parseRankedObservations(quantMart: UnknownRecord | null): RankedObs[] {
  if (!quantMart) return [];
  return asArrayOfRecords(quantMart.ranked_observations)
    .map((raw): RankedObs | null => {
      const id = asString(raw.observation_id) ?? asString(raw.id);
      if (!id) return null;
      const primary = asRecord(raw.primary_metric);
      const score = asRecord(raw.score);
      const entityIds = Array.isArray(raw.entities)
        ? raw.entities.filter((value): value is string => typeof value === 'string')
        : [];
      const reasons = Array.isArray(raw.reasons)
        ? raw.reasons.filter((v): v is string => typeof v === 'string')
        : [];
      const reasonCodes = Array.isArray(raw.reason_codes)
        ? raw.reason_codes.filter((v): v is string => typeof v === 'string')
        : [];
      const caveats = Array.isArray(raw.caveats)
        ? raw.caveats.filter((v): v is string => typeof v === 'string')
        : [];
      const disconfirming = Array.isArray(raw.disconfirming_checks)
        ? raw.disconfirming_checks.filter((v): v is string => typeof v === 'string')
        : [];
      return {
        id,
        rank: asNumber(raw.rank),
        title: asString(raw.title) ?? id,
        whyInteresting: asString(raw.why_interesting),
        entities: entityIds.map(normalizeEntity),
        primaryMetricName: asString(primary?.name),
        primaryMetricValue: asNumber(primary?.value),
        reasons,
        reasonCodes,
        caveats,
        disconfirming,
        confidence: asNumber(score?.confidence),
        interestingness: asNumber(score?.interestingness),
        displayReadiness: asNumber(score?.display_readiness),
        displayState: asString(raw.display_state),
        claimLevel: asString(raw.claim_level),
        safeUseLevel: asString(raw.safe_use_level),
      };
    })
    .filter((row): row is RankedObs => row !== null)
    .sort((a, b) => (a.rank ?? Infinity) - (b.rank ?? Infinity));
}

function parseFlowBoard(quantMart: UnknownRecord | null): FlowRow[] {
  if (!quantMart) return [];
  return asArrayOfRecords(quantMart.stockgrid_flow_board)
    .map((raw): FlowRow | null => {
      const tickerRaw = asString(raw.ticker) ?? asString(raw.entity_id);
      if (!tickerRaw) return null;
      const ticker = tickerRaw.replace(/^equity:/, '');
      const sectorRaw = raw.sector;
      const sector =
        typeof sectorRaw === 'string' && sectorRaw.trim() ? sectorRaw : null;
      return {
        ticker,
        company: asString(raw.company) ?? ticker,
        sector,
        flowUsd: asNumber(raw.flow_usd),
        netUsd: asNumber(raw.net_usd),
        conviction: asNumber(raw.conviction),
        signalValue: asNumber(raw.signal_value),
        winRate: asNumber(raw.win_rate),
        direction: asNumber(raw.direction),
      };
    })
    .filter((row): row is FlowRow => row !== null);
}

function parseMacroBoard(quantMart: UnknownRecord | null): MacroBucketRow[] {
  if (!quantMart) return [];
  return asArrayOfRecords(quantMart.macro_regime_board)
    .map((raw): MacroBucketRow => ({
      bucket: asString(raw.bucket) ?? 'unknown',
      averageZ: asNumber(raw.average_z_score),
      seriesCount: asNumber(raw.series_count),
      vintageStatus: asString(raw.vintage_status),
      topSeries: asArrayOfRecords(raw.top_series).slice(0, 3).map((s) => {
        const t = asString(s.ticker) ?? asString(s.entity_id) ?? '—';
        return {
          ticker: t,
          label: t
            .replace(/^macro_series:/, '')
            .replace(/_/g, ' ')
            .replace(/\b([a-z])/g, (m) => m.toUpperCase()),
          z: asNumber(s.z_score),
          recentChange: asNumber(s.recent_change),
          obsDate: asString(s.latest_observation_date),
        };
      }),
    }))
    .sort((a, b) => {
      const left = a.averageZ == null ? 0 : Math.abs(a.averageZ);
      const right = b.averageZ == null ? 0 : Math.abs(b.averageZ);
      return right - left;
    });
}

function parseEvents(quantMart: UnknownRecord | null): EventRow[] {
  if (!quantMart) return [];
  return asArrayOfRecords(quantMart.prediction_market_event_board)
    .map((raw): EventRow | null => {
      const id =
        asString(raw.entity_id) ?? asString(raw.event_id) ?? asString(raw.slug);
      if (!id) return null;
      return {
        id,
        title: asString(raw.event_title) ?? asString(raw.question) ?? id,
        question: asString(raw.question),
        topic: asString(raw.topic),
        probability: asNumber(raw.probability),
        probabilityChange: asNumber(raw.probability_change),
        volume: asNumber(raw.volume),
        spread: asNumber(raw.spread),
      };
    })
    .filter((row): row is EventRow => row !== null);
}

function parseCoverage(quantMart: UnknownRecord | null): CoverageRow[] {
  if (!quantMart) return [];
  const coverage = asRecord(quantMart.coverage);
  const driftList = asArrayOfRecords(quantMart.provider_drift_monitor);
  const missList = asArrayOfRecords(quantMart.missingness_board);
  const driftById = new Map<string, UnknownRecord>();
  for (const row of driftList) {
    const id = asString(row.provider_id);
    if (id) driftById.set(id, row);
  }
  const missById = new Map<string, UnknownRecord>();
  for (const row of missList) {
    const id = asString(row.feed_id);
    if (id) missById.set(id, row);
  }
  return asArrayOfRecords(coverage?.feeds).map((raw) => {
    const feedId = asString(raw.feed_id) ?? 'unknown';
    const drift = driftById.get(feedId);
    const miss = missById.get(feedId);
    return {
      feedId,
      label: asString(raw.label) ?? feedId,
      rows: asNumber(raw.rows) ?? asNumber(raw.items_count),
      freshness: asString(raw.freshness),
      quality: asString(raw.quality),
      fetchSuccessRate: asNumber(drift?.fetch_success_rate),
      drifts: Array.isArray(drift?.drift_flags)
        ? (drift!.drift_flags as unknown[]).filter(
            (v): v is string => typeof v === 'string',
          )
        : [],
      emptyReason: asString(miss?.empty_reason),
    };
  });
}

function parseHumanMarketCockpit(
  worldModelMarketFeeds: UnknownRecord | null,
): HumanMarketCockpit | null {
  const raw = asRecord(worldModelMarketFeeds?.human_market_cockpit);
  if (!raw) return null;
  const field = asRecord(raw.market_field) ?? null;
  const rows = asArrayOfRecords(field?.rows).map((r): HmcRow => ({
    id: asString(r.id) ?? '',
    kind: asString(r.kind) ?? 'other',
    label: asString(r.label) ?? asString(r.id) ?? '',
    subtitle: asString(r.subtitle),
    group: asString(r.group),
  })).filter((r) => r.id);
  const columns = asArrayOfRecords(field?.columns).map((c): HmcColumn => ({
    id: asString(c.id) ?? '',
    label: asString(c.label) ?? asString(c.id) ?? '',
    kind: asString(c.kind) ?? 'magnitude',
  })).filter((c) => c.id);
  const cells = asArrayOfRecords(field?.cells).map((c): HmcCell => {
    const toneRaw = asString(c.tone) ?? 'neutral';
    const toneSafe: HmcCell['tone'] =
      toneRaw === 'pos' || toneRaw === 'neg' || toneRaw === 'ok' ||
      toneRaw === 'warn' || toneRaw === 'block' ? toneRaw : 'neutral';
    return {
      rowId: asString(c.row_id) ?? '',
      columnId: asString(c.column_id) ?? '',
      value: asNumber(c.value),
      normalized: asNumber(c.normalized) ?? 0,
      direction: asNumber(c.direction) ?? 0,
      tone: toneSafe,
      label: asString(c.label),
      metricName: asString(c.metric_name),
      metricValue: asNumber(c.metric_value),
      confidence: asNumber(c.confidence),
      completeness: asNumber(c.completeness) ?? 0,
      situationIds: Array.isArray(c.situation_ids)
        ? c.situation_ids.filter((s): s is string => typeof s === 'string')
        : [],
      observationIds: Array.isArray(c.observation_ids)
        ? c.observation_ids.filter((s): s is string => typeof s === 'string')
        : [],
    };
  });
  const cardsRaw = asArrayOfRecords(raw.signal_cards);
  const signalCards: HmcSignalCard[] = cardsRaw.map((c): HmcSignalCard => ({
    id: asString(c.id) ?? '',
    title: asString(c.title) ?? '',
    oneLine: asString(c.one_line),
    keyNumbers: asArrayOfRecords(c.key_numbers).map((k) => ({
      label: asString(k.label) ?? '',
      value: asString(k.value) ?? '',
    })).filter((k) => k.label),
    watchpoint: asString(c.watchpoint),
    caveat: asString(c.caveat),
    linkedRowId: asString(c.linked_matrix_row_id),
    linkedSituationIds: Array.isArray(c.linked_situation_ids)
      ? c.linked_situation_ids.filter((s): s is string => typeof s === 'string')
      : [],
  })).filter((c) => c.id);
  const pulseRaw = asArrayOfRecords(raw.market_pulse);
  const marketPulse: HmcPulseFact[] = pulseRaw.map((p): HmcPulseFact => {
    const toneRaw = asString(p.tone) ?? 'neutral';
    const toneSafe: HmcPulseFact['tone'] =
      toneRaw === 'pos' || toneRaw === 'neg' || toneRaw === 'ok' ||
      toneRaw === 'warn' || toneRaw === 'block' ? toneRaw : 'neutral';
    return {
      label: asString(p.label) ?? '',
      value: asString(p.value) ?? '',
      tone: toneSafe,
      interpretation: asString(p.interpretation),
      caveat: asString(p.caveat),
    };
  }).filter((p) => p.label);
  const dqRaw = asArrayOfRecords(raw.data_quality);
  const dataQuality: HmcDataQualityRow[] = dqRaw.map((d): HmcDataQualityRow => ({
    lane: asString(d.lane) ?? '',
    state: asString(d.state) ?? 'unknown',
    rows: asNumber(d.rows),
    problem: asString(d.problem) ?? '',
    action: asString(d.action) ?? '',
  })).filter((d) => d.lane);
  // v0.9: parse visual_planes, global_states, column_legends, applicability.
  const visualPlanes: HmcVisualPlane[] = asArrayOfRecords(raw.visual_planes).map((p): HmcVisualPlane => {
    const planeRowsRaw = asArrayOfRecords(p.rows);
    const planeRows: HmcPlaneRow[] = planeRowsRaw.map((r): HmcPlaneRow => {
      const metricsRecord = asRecord(r.metrics) ?? {};
      const metrics: Record<string, number | null> = {};
      for (const [k, v] of Object.entries(metricsRecord)) {
        metrics[k] = typeof v === 'number' && Number.isFinite(v) ? v : null;
      }
      return {
        id: asString(r.id) ?? '',
        label: asString(r.label) ?? asString(r.id) ?? '',
        subtitle: asString(r.subtitle),
        metrics,
        topSeries: asArrayOfRecords(r.top_series),
      };
    });
    return {
      id: asString(p.id) ?? '',
      title: asString(p.title) ?? '',
      primitive: asString(p.primitive) ?? '',
      rows: planeRows,
      metricSpecs: asArrayOfRecords(p.metric_specs).map((m): HmcMetricSpec => ({
        id: asString(m.id) ?? '',
        label: asString(m.label) ?? '',
        unit: asString(m.unit) ?? '',
        encoding: asString(m.encoding) ?? '',
      })),
      legend: asString(p.legend),
      interpretation: asString(p.interpretation),
      applicability: asString(p.applicability) ?? 'primary',
      emptyPolicy: asString(p.empty_policy),
    };
  });

  const globalStates: HmcGlobalState[] = asArrayOfRecords(raw.global_states).map((g): HmcGlobalState => {
    const toneRaw = asString(g.tone) ?? 'neutral';
    const toneSafe: HmcGlobalState['tone'] =
      toneRaw === 'pos' || toneRaw === 'neg' || toneRaw === 'ok' ||
      toneRaw === 'warn' || toneRaw === 'block' ? toneRaw : 'neutral';
    return {
      id: asString(g.id) ?? '',
      label: asString(g.label) ?? '',
      lane: asString(g.lane),
      tone: toneSafe,
      scope: asString(g.scope),
      promotedTo: asString(g.promoted_to),
    };
  }).filter((g) => g.id);

  const legendsRecord = asRecord(raw.column_legends) ?? {};
  const columnLegends: Record<string, string> = {};
  for (const [k, v] of Object.entries(legendsRecord)) {
    if (typeof v === 'string') columnLegends[k] = v;
  }

  const applicabilityByKey = new Map<string, string>();
  const applicabilityCells = asArrayOfRecords(
    asRecord(raw.applicability)?.matrix_cells,
  );
  for (const a of applicabilityCells) {
    const rid = asString(a.row_id);
    const cid = asString(a.column_id);
    const state = asString(a.state);
    if (rid && cid && state) applicabilityByKey.set(`${rid}::${cid}`, state);
  }

  // v0.10 workspace parsing.
  const wsRaw = asRecord(raw.workspace);
  let workspace: HmcWorkspace | null = null;
  if (wsRaw) {
    const nav: HmcPlaneNavEntry[] = asArrayOfRecords(wsRaw.plane_nav).map((p): HmcPlaneNavEntry => {
      const ds = asRecord(p.default_sort) ?? {};
      return {
        id: asString(p.id) ?? '',
        label: asString(p.label) ?? '',
        rowCount: asNumber(p.row_count) ?? 0,
        status: asString(p.status) ?? 'unknown',
        primitive: asString(p.primitive) ?? 'ranked_table',
        defaultSort: {
          column: asString(ds.column),
          direction: asString(ds.direction),
        },
        feedId: asString(p.feed_id),
        entityKind: asString(p.entity_kind),
      };
    }).filter((p) => p.id);
    const previewRaw = asRecord(wsRaw.active_plane_preview) ?? {};
    const previewCols = asArrayOfRecords(previewRaw.columns).map((c): HmcDisplayColumn => ({
      id: asString(c.id) ?? '',
      label: asString(c.label) ?? '',
      kind: asString(c.kind) ?? 'label',
    }));
    const previewRows = asArrayOfRecords(previewRaw.rows);
    const previewSort = asRecord(previewRaw.sort) ?? {};
    const layoutRaw = asRecord(wsRaw.layout_contract) ?? {};
    workspace = {
      // v0.10.1: parse workspace.run_id so MarketWorkspace can fetch
      // active-plane pages against the bundle's run rather than the UI's
      // in-flight / latest run id.
      runId: asString(wsRaw.run_id),
      defaultPlaneId: asString(wsRaw.default_plane_id),
      planeNav: nav,
      activePlanePreview: {
        planeId: asString(previewRaw.plane_id),
        rows: previewRows,
        columns: previewCols,
        rowCountTotal: asNumber(previewRaw.row_count_total) ?? 0,
        sort: {
          column: asString(previewSort.column),
          direction: asString(previewSort.direction),
        },
      },
      layoutContract: {
        primaryPlaneMinRows: asNumber(layoutRaw.primary_plane_min_rows) ?? 25,
        fillAvailableViewport: asBool(layoutRaw.fill_available_viewport) ?? true,
        rightExplainerWidth: asNumber(layoutRaw.right_explainer_width) ?? 320,
        collapseSignalCardsWhenSpaceConstrained:
          asBool(layoutRaw.collapse_signal_cards_when_space_constrained) ?? true,
      },
    };
  }

  return {
    schemaVersion: asString(raw.schema_version) ?? '',
    rows,
    columns,
    cells,
    signalCards,
    marketPulse,
    dataQuality,
    visualPlanes,
    globalStates,
    columnLegends,
    applicabilityByKey,
    workspace,
  };
}

function parseSituationCards(readModel: MarketDashboardReadModel | null): SituationCardRow[] {
  const queue = asRecord(readModel?.situation_queue);
  return asArrayOfRecords(queue?.items)
    .map((raw): SituationCardRow | null => {
      const id =
        asString(raw.situation_id) ?? asString(raw.id) ?? asString(raw.card_id);
      if (!id) return null;
      const primaryEntities = Array.isArray(raw.primary_entities)
        ? raw.primary_entities.filter((v): v is string => typeof v === 'string')
        : [];
      return {
        id,
        title: asString(raw.title) ?? id,
        situationType: asString(raw.situation_type),
        horizon: asString(raw.horizon),
        primaryEntities: primaryEntities.map(normalizeEntity),
        displayState: asString(raw.display_state),
        claimLevel: asString(raw.claim_level),
        confidence: asNumber(raw.confidence_overall) ?? asNumber(raw.confidence),
        evidenceCount: asNumber(raw.evidence_count) ?? 0,
        counterevidenceCount: asNumber(raw.counterevidence_count) ?? 0,
      };
    })
    .filter((row): row is SituationCardRow => row !== null);
}

// -------- visual primitives -----------------------------------------------

// Compact magnitude microbar — width is `magnitude` (0..1). Renders inline.
function Microbar({
  magnitude,
  tone = 'neutral',
  width = 60,
}: {
  magnitude: number | null;
  tone?: 'pos' | 'neg' | 'neutral';
  width?: number;
}) {
  if (magnitude == null) {
    return (
      <span
        className="inline-block h-1.5 rounded-full bg-white/[0.08]"
        style={{ width: `${width}px` }}
      />
    );
  }
  const clamped = Math.max(0, Math.min(1, magnitude));
  const color =
    tone === 'pos'
      ? 'bg-emerald-300/85'
      : tone === 'neg'
        ? 'bg-rose-300/85'
        : 'bg-sky-300/70';
  return (
    <span
      className="relative inline-block h-1.5 overflow-hidden rounded-full bg-white/[0.08]"
      style={{ width: `${width}px` }}
    >
      <span
        className={clsx('absolute inset-y-0 left-0 rounded-full', color)}
        style={{ width: `${clamped * 100}%` }}
      />
    </span>
  );
}

// Diverging bar from a centered zero baseline. `value` is in some unit
// space; `peak` is the absolute extent that maps to half-width.
function DivergingBar({
  value,
  peak,
  width = 110,
}: {
  value: number | null;
  peak: number;
  width?: number;
}) {
  if (value == null || peak <= 0) {
    return (
      <span
        className="inline-block h-1.5 rounded-sm bg-white/[0.06]"
        style={{ width: `${width}px` }}
      />
    );
  }
  const half = width / 2;
  const ratio = Math.max(-1, Math.min(1, value / peak));
  const pixels = Math.abs(ratio) * half;
  const positive = ratio >= 0;
  return (
    <span
      className="relative inline-block h-2 rounded-sm bg-white/[0.06]"
      style={{ width: `${width}px` }}
    >
      <span className="absolute inset-y-0 left-1/2 w-px bg-white/30" />
      <span
        className={clsx(
          'absolute inset-y-0 rounded-sm',
          positive ? 'bg-emerald-300/75' : 'bg-rose-300/75',
        )}
        style={{
          left: positive ? `${half}px` : `${half - pixels}px`,
          width: `${pixels}px`,
        }}
      />
    </span>
  );
}

// Probability dot — 0..1 horizontal positioned dot. Volume scales the dot.
function ProbabilityDot({
  probability,
  volume,
  width = 80,
}: {
  probability: number | null;
  volume: number | null;
  width?: number;
}) {
  if (probability == null) {
    return (
      <span
        className="inline-block h-3 rounded-sm bg-white/[0.05]"
        style={{ width: `${width}px` }}
      />
    );
  }
  const ratio = Math.max(0, Math.min(1, probability));
  const left = ratio * (width - 6);
  const volRatio =
    volume == null ? 0.3 : Math.max(0.2, Math.min(1, Math.log10(volume + 1) / 7));
  const dotPx = 4 + volRatio * 4;
  return (
    <span
      className="relative inline-block h-3 rounded-sm bg-white/[0.05]"
      style={{ width: `${width}px` }}
    >
      <span className="absolute inset-y-0 left-1/2 w-px bg-white/20" />
      <span
        className="absolute top-1/2 -translate-y-1/2 rounded-full bg-sky-300/80"
        style={{ left: `${left}px`, width: `${dotPx}px`, height: `${dotPx}px` }}
      />
    </span>
  );
}

function StatusPill({
  tone,
  children,
}: {
  tone: 'ok' | 'warn' | 'block' | 'neutral';
  children: React.ReactNode;
}) {
  return (
    <span
      className={clsx(
        'inline-block whitespace-nowrap rounded-full border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.12em]',
        tone === 'ok'
          ? 'border-emerald-300/30 bg-emerald-300/[0.08] text-emerald-100'
          : tone === 'warn'
            ? 'border-amber-300/30 bg-amber-300/[0.08] text-amber-100'
            : tone === 'block'
              ? 'border-rose-300/30 bg-rose-300/[0.08] text-rose-100'
              : 'border-zenith-edge bg-white/[0.04] text-white/72',
      )}
    >
      {children}
    </span>
  );
}

// -------- sub-sections ----------------------------------------------------

function StatusStrip({
  readModel,
  marketFeeds,
  selectedRunId,
  latestRunId,
  onRunChange,
  pinnedLoading,
  pinnedError,
  activeRefreshRunId,
}: {
  readModel: MarketDashboardReadModel | null;
  marketFeeds: UnknownRecord | null;
  selectedRunId: string | null | undefined;
  latestRunId: string | null | undefined;
  onRunChange?: (runId: string | null) => void;
  pinnedLoading?: boolean;
  pinnedError?: string | null;
  activeRefreshRunId?: string | null;
}) {
  const summary = asRecord(marketFeeds?.summary);
  const marketClock = asRecord(marketFeeds?.market_clock);
  const tickerSnapshot = asRecord(marketFeeds?.latest_ticker_snapshot);
  const evidenceCard = asRecord(marketFeeds?.latest_evidence_card);
  const feedRunsRaw = Array.isArray(marketFeeds?.feed_runs)
    ? (marketFeeds!.feed_runs as MarketFeedRun[])
    : [];

  const todayMarketDate = asString(marketClock?.today_market_date);
  const todayFirePoints = asArrayOfRecords(marketClock?.today);
  const openPoint = todayFirePoints.find((pt) => asString(pt.fire_point) === 'open');
  const closePoint = todayFirePoints.find((pt) => asString(pt.fire_point) === 'close');
  const openCaptured = asBool(openPoint?.passed) === true && asString(openPoint?.fired_at_utc);
  const closeCaptured = asBool(closePoint?.passed) === true && asString(closePoint?.fired_at_utc);

  const snapshotDate = asString(tickerSnapshot?.market_date);
  const clockDate = parseDate(todayMarketDate);
  const snapDate = parseDate(snapshotDate);
  const snapSkew = snapDate && clockDate ? calendarDaysBetween(snapDate, clockDate) : null;
  const snapStale = snapSkew != null && snapSkew > 1;

  const latestFreshness = asRecord(summary?.latest_freshness);
  const ageLabel = asString(latestFreshness?.label);
  const ageStale = asString(latestFreshness?.tone) === 'stale';

  const effectiveRunId = selectedRunId ?? latestRunId ?? asString(readModel?.run_id);
  const isPinned = Boolean(selectedRunId && selectedRunId !== latestRunId);

  const overview = asRecord(readModel?.overview);
  const safeUse = asString(overview?.safe_use_level);

  // News lane state — read off coverage to phrase honestly.
  const coverage = asRecord(
    asRecord(marketFeeds?.latest_quant_presentation_mart)?.coverage,
  );
  const newsRows = asArrayOfRecords(coverage?.feeds).find(
    (f) => asString(f.feed_id) === 'global_news_feed',
  );
  const newsRowsCount = asNumber(newsRows?.rows);
  const newsHonest =
    newsRowsCount == null
      ? null
      : newsRowsCount === 0
        ? 'news 0 rows · fetch unknown'
        : `news ${newsRowsCount} rows`;

  const evidenceAsOf = asString(evidenceCard?.as_of);

  return (
    <section
      data-zenith-cockpit-status-strip="ready"
      className="rounded-[10px] border border-zenith-edge-faint bg-black/35 px-3 py-1.5"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] leading-5 text-white/72">
        <span className="font-mono text-white/82">
          Market <span className="text-white/30">·</span>{' '}
          {todayMarketDate ?? '—'} NY
        </span>
        <span className="font-mono text-zenith-muted">·</span>
        <span className="font-mono">
          run age{' '}
          <span className={clsx('tabular-nums', ageStale ? 'text-amber-200' : 'text-white/82')}>
            {ageLabel ?? '—'}
          </span>
        </span>
        <span className="font-mono text-zenith-muted">·</span>
        <span className="font-mono">
          ticker snapshot{' '}
          <span className={clsx('tabular-nums', snapStale ? 'text-rose-200' : 'text-white/82')}>
            {snapshotDate ?? '—'}
          </span>
          {snapSkew != null && snapSkew > 0 && (
            <span className={clsx('ml-1', snapStale ? 'text-rose-200' : 'text-zenith-soft')}>
              ({snapSkew}d behind)
            </span>
          )}
        </span>
        {newsHonest && (
          <>
            <span className="font-mono text-zenith-muted">·</span>
            <span
              className={clsx(
                'font-mono',
                newsRowsCount === 0 ? 'text-rose-200' : 'text-white/82',
              )}
            >
              {newsHonest}
            </span>
          </>
        )}
        <span className="font-mono text-zenith-muted">·</span>
        <StatusPill tone={openCaptured ? 'ok' : 'neutral'}>
          open {openCaptured ? 'captured' : 'pending'}
        </StatusPill>
        <StatusPill tone={closeCaptured ? 'warn' : 'neutral'}>
          close {closeCaptured ? 'captured' : 'pending'}
        </StatusPill>
        <span className="font-mono text-zenith-soft">
          run <span className="font-mono text-white/82">{effectiveRunId ?? '—'}</span>{' '}
          {isPinned ? '(pinned)' : '(latest)'}
        </span>
        {activeRefreshRunId && (
          <StatusPill tone="warn">
            refresh in progress · {activeRefreshRunId}
          </StatusPill>
        )}
        {safeUse && <StatusPill tone="neutral">safe use · {stateLabel(safeUse)}</StatusPill>}
        <span className="ml-auto flex items-center gap-2">
          {pinnedLoading && <StatusPill tone="warn">loading pinned</StatusPill>}
          {pinnedError && <StatusPill tone="block">pinned error</StatusPill>}
          <label className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.12em] text-zenith-muted">
            <span>pin</span>
            <select
              value={selectedRunId ?? ''}
              onChange={(event) => onRunChange?.(event.target.value || null)}
              className="rounded-[6px] border border-zenith-edge-faint bg-black/45 px-1.5 py-0.5 font-mono text-[11px] text-white/82 outline-none focus:border-emerald-300/45"
            >
              <option value="">latest</option>
              {feedRunsRaw.slice(0, 24).map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {run.run_id}{run.ready ? ' · ready' : ''}
                </option>
              ))}
            </select>
          </label>
          {evidenceAsOf && (
            <span className="font-mono text-[10px] text-zenith-muted">
              evidence as of {evidenceAsOf.replace('T', ' ').slice(0, 16)}
            </span>
          )}
        </span>
      </div>
    </section>
  );
}

function TickerTape({ marketFeeds }: { marketFeeds: UnknownRecord | null }) {
  const tickerSnapshot = asRecord(marketFeeds?.latest_ticker_snapshot);
  const preview = asArrayOfRecords(tickerSnapshot?.ticker_preview);

  if (preview.length === 0) {
    return (
      <section className="rounded-[10px] border border-zenith-edge-faint bg-black/30 px-3 py-1.5 text-[11px] text-zenith-soft">
        No ticker snapshot in this run.
      </section>
    );
  }

  // For the microbar peak we look at the max absolute change% in the row set.
  const maxAbsChange =
    Math.max(
      0.1,
      ...preview
        .map((r) => Math.abs(asNumber(r.change_pct) ?? 0))
        .filter((v) => Number.isFinite(v)),
    ) || 1;

  return (
    <section
      data-zenith-cockpit-ticker-tape="ready"
      className="rounded-[10px] border border-zenith-edge-faint bg-black/35"
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-1.5">
        {preview.slice(0, 10).map((row, idx) => {
          const symbol = asString(row.symbol) ?? `T${idx}`;
          const price = asNumber(row.price);
          const changePct = asNumber(row.change_pct);
          const label = asString(row.label);
          const tone: 'pos' | 'neg' | 'neutral' =
            changePct == null ? 'neutral' : changePct > 0 ? 'pos' : changePct < 0 ? 'neg' : 'neutral';
          const colorClass =
            tone === 'pos' ? 'text-emerald-100' : tone === 'neg' ? 'text-rose-100' : 'text-white/72';
          return (
            <span
              key={symbol}
              className="flex items-center gap-1.5 font-mono text-[12px] tabular-nums text-white/82"
              title={label ?? symbol}
            >
              <span className="text-white/82">{symbol}</span>
              <span className="text-white">{fmtPrice(price)}</span>
              <span className={colorClass}>{fmtPct(changePct)}</span>
              <Microbar
                magnitude={changePct == null ? null : Math.abs(changePct) / maxAbsChange}
                tone={tone}
                width={32}
              />
            </span>
          );
        })}
      </div>
    </section>
  );
}

// v0.6.1 fallback: when ranked_observations is empty (e.g. fresh refresh
// has not finished building the quant_mart), render rows derived from the
// read model's situation_queue + situation_detail_index so the cockpit
// browse area never goes blank while a detail pane is populated.
function SituationSignalFallback({
  situations,
  readModel,
  onSelect,
}: {
  situations: SituationCardRow[];
  readModel: MarketDashboardReadModel | null;
  onSelect?: (id: string) => void;
}) {
  if (situations.length === 0) {
    return (
      <section className="rounded-[10px] border border-zenith-edge-faint bg-black/30 p-3 text-[11px] leading-5 text-zenith-muted">
        No ranked observations and no situations in this run.
      </section>
    );
  }
  const detailIndex = asRecord(readModel?.situation_detail_index);
  return (
    <section
      data-zenith-cockpit-signal-fallback="ready"
      className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">
          Signal Tape · {situations.length} situations
        </span>
        <span className="font-mono text-zenith-muted">
          fallback · ranked observations not yet projected
        </span>
      </header>
      <ul className="min-h-0 flex-1 divide-y divide-white/[0.04] overflow-y-auto">
        {situations.slice(0, 10).map((row) => {
          const tone: 'ok' | 'warn' | 'block' | 'neutral' =
            row.displayState === 'ready'
              ? 'ok'
              : row.displayState === 'degraded'
                ? 'warn'
                : 'neutral';
          const detail = asRecord(detailIndex?.[row.id]);
          const evidenceEdges = asArrayOfRecords(detail?.evidence_edges);
          const firstReason = evidenceEdges.length > 0
            ? translateReasonCode(asString(evidenceEdges[0].reason_code))
            : null;
          return (
            <li key={row.id}>
              <button
                type="button"
                onClick={() => onSelect?.(row.id)}
                className="grid w-full grid-cols-[minmax(0,1fr)_72px] items-start gap-2 px-3 py-2 text-left transition-colors hover:bg-white/[0.03]"
              >
                <span className="min-w-0">
                  <span className="block truncate text-[12px] leading-5 text-white">
                    {row.title}
                  </span>
                  {firstReason && (
                    <span className="mt-0.5 block truncate text-[11px] leading-5 text-zenith-soft">
                      {firstReason}
                    </span>
                  )}
                  <span className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[10px] uppercase tracking-[0.12em] text-zenith-soft">
                    {row.primaryEntities.slice(0, 3).map((e) => (
                      <span
                        key={e.raw}
                        className="font-mono text-white/72"
                        title={e.hint ?? e.raw}
                      >
                        {e.label}
                      </span>
                    ))}
                    {row.horizon && <StatusPill tone="neutral">{row.horizon}</StatusPill>}
                    {row.claimLevel && (
                      <StatusPill tone="neutral">{stateLabel(row.claimLevel)}</StatusPill>
                    )}
                    <StatusPill tone={tone}>{stateLabel(row.displayState)}</StatusPill>
                  </span>
                </span>
                <span className="text-right font-mono text-[10px] uppercase tracking-[0.12em] text-zenith-muted">
                  <span className="text-emerald-200">{row.evidenceCount}E</span>
                  <span className="mx-0.5 text-white/30">/</span>
                  <span className="text-rose-200">{row.counterevidenceCount}C</span>
                  {row.confidence != null && (
                    <span className="mt-0.5 block text-zenith-soft">
                      c {row.confidence.toFixed(2)}
                    </span>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function SignalTape({
  rows,
  onSelect,
}: {
  rows: RankedObs[];
  onSelect?: (id: string) => void;
}) {
  if (rows.length === 0) {
    return (
      <section className="rounded-[10px] border border-zenith-edge-faint bg-black/30 p-3 text-[11px] leading-5 text-zenith-muted">
        No ranked observations in this run.
      </section>
    );
  }
  return (
    <section
      data-zenith-cockpit-signal-tape="ready"
      className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">Signal Tape · {rows.length} observations</span>
        <span className="font-mono text-zenith-muted">
          ranked · flow / event / macro / price
        </span>
      </header>
      <ul className="min-h-0 flex-1 divide-y divide-white/[0.04] overflow-y-auto">
        {rows.slice(0, 10).map((row) => {
          const tone: 'ok' | 'warn' | 'block' | 'neutral' =
            row.displayState === 'ready'
              ? 'ok'
              : row.displayState === 'degraded'
                ? 'warn'
                : 'neutral';
          const primaryLabel = row.primaryMetricName
            ? row.primaryMetricName.replace(/_/g, ' ')
            : null;
          const isUsdMetric =
            row.primaryMetricName != null &&
            /flow|volume|usd|value/.test(row.primaryMetricName);
          const primaryFormatted =
            row.primaryMetricValue == null
              ? '—'
              : isUsdMetric
                ? fmtUsdCompact(row.primaryMetricValue)
                : row.primaryMetricValue.toFixed(2);
          return (
            <li key={row.id}>
              <button
                type="button"
                onClick={() => onSelect?.(row.id)}
                className="grid w-full grid-cols-[28px_minmax(0,1fr)_140px] items-start gap-3 px-3 py-2 text-left transition-colors hover:bg-white/[0.03]"
              >
                <span className="mt-0.5 font-mono text-[14px] tabular-nums text-white/72">
                  {row.rank ?? '—'}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-[12px] leading-5 text-white">
                    {row.title}
                  </span>
                  {row.whyInteresting && (
                    <span className="mt-0.5 block truncate text-[11px] leading-5 text-zenith-soft">
                      {row.whyInteresting}
                    </span>
                  )}
                  <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] uppercase tracking-[0.10em] text-zenith-soft">
                    {row.entities.slice(0, 3).map((e) => (
                      <span
                        key={e.raw}
                        className="font-mono text-white/72"
                        title={e.hint ?? e.raw}
                      >
                        {e.label}
                      </span>
                    ))}
                    {row.claimLevel && <StatusPill tone="neutral">{stateLabel(row.claimLevel)}</StatusPill>}
                    <StatusPill tone={tone}>{stateLabel(row.displayState)}</StatusPill>
                  </span>
                </span>
                <span className="flex flex-col items-end gap-1 font-mono text-[11px] tabular-nums text-white/82">
                  <span title={primaryLabel ?? ''}>{primaryFormatted}</span>
                  <span className="flex items-center gap-1">
                    <Microbar
                      magnitude={row.interestingness}
                      tone={tone === 'ok' ? 'pos' : 'neutral'}
                      width={70}
                    />
                  </span>
                  <span className="text-[9px] uppercase tracking-[0.12em] text-zenith-muted">
                    c {row.confidence != null ? row.confidence.toFixed(2) : '—'}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function FlowLeaderboard({
  rows,
  suppressSignalOnly,
}: {
  rows: FlowRow[];
  // v0.8: when hmc.data_quality already names `stockgrid_signal_only`,
  // hide the per-row signal-value watchlist from the primary flow panel —
  // it lives in DataQualityStrip as a demoted defect, not as market signal.
  suppressSignalOnly?: boolean;
}) {
  if (rows.length === 0) return null;
  const withFlow = rows.filter((r) => r.flowUsd != null);
  const withSignalOnly = suppressSignalOnly
    ? []
    : rows.filter((r) => r.flowUsd == null && r.signalValue != null);

  // Honest empty / sparse state — operator's "do not silently show an anemic
  // top 6 with two rows" rule.
  if (withFlow.length === 0 && withSignalOnly.length === 0) {
    return (
      <section className="rounded-[10px] border border-zenith-edge-faint bg-black/30 px-3 py-2 text-[11px] leading-5 text-zenith-muted">
        <span className="font-mono text-white/82">Flow Leaders</span> · no
        flow_usd or signal_value rows in this run.
      </section>
    );
  }

  const peak = Math.max(0, ...withFlow.map((r) => Math.abs(r.flowUsd ?? 0)));
  const topFlow = withFlow
    .slice()
    .sort((a, b) => Math.abs(b.flowUsd ?? 0) - Math.abs(a.flowUsd ?? 0))
    .slice(0, 6);
  const topSignal = withSignalOnly
    .slice()
    .sort((a, b) => Math.abs(b.signalValue ?? 0) - Math.abs(a.signalValue ?? 0))
    .slice(0, 6);
  const signalPeak = Math.max(
    0,
    ...topSignal.map((r) => Math.abs(r.signalValue ?? 0)),
  );

  return (
    <section className="rounded-[10px] border border-zenith-edge-faint bg-black/30">
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">
          Flow Leaders · {withFlow.length} full-flow · {withSignalOnly.length} signal-only
        </span>
        <span className="font-mono text-zenith-muted">
          stockgrid · salience, not a recommendation
        </span>
      </header>
      {topFlow.length > 0 && (
        <ul className="divide-y divide-white/[0.04]">
          {topFlow.map((row) => {
            const flowTone: 'pos' | 'neg' | 'neutral' =
              row.flowUsd == null ? 'neutral' : row.flowUsd >= 0 ? 'pos' : 'neg';
            return (
              <li key={`flow-${row.ticker}`} className="grid grid-cols-[44px_minmax(0,1fr)_72px] items-center gap-2 px-3 py-1.5 text-[11px] leading-5 text-white/82">
                <span className="font-mono text-white">{row.ticker}</span>
                <span className="flex items-center gap-2">
                  <DivergingBar value={row.flowUsd} peak={peak} width={120} />
                  <span className="truncate text-[10px] text-zenith-soft">
                    {row.company}
                    {row.sector ? ` · ${row.sector}` : ''}
                  </span>
                </span>
                <span
                  className={clsx(
                    'text-right font-mono tabular-nums',
                    flowTone === 'pos'
                      ? 'text-emerald-100'
                      : flowTone === 'neg'
                        ? 'text-rose-100'
                        : 'text-white/72',
                  )}
                >
                  {fmtUsdCompact(row.flowUsd)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {topSignal.length > 0 && (
        <>
          <div className="border-y border-zenith-edge-soft bg-black/20 px-3 py-1 font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
            Signal-value watchlist · flow_usd missing for these rows
          </div>
          <ul className="divide-y divide-white/[0.04]">
            {topSignal.map((row) => (
              <li
                key={`sig-${row.ticker}`}
                className="grid grid-cols-[44px_minmax(0,1fr)_72px] items-center gap-2 px-3 py-1.5 text-[11px] leading-5 text-white/82"
              >
                <span className="font-mono text-white">{row.ticker}</span>
                <span className="flex items-center gap-2">
                  <Microbar
                    magnitude={
                      signalPeak > 0
                        ? Math.abs(row.signalValue ?? 0) / signalPeak
                        : 0
                    }
                    tone="neutral"
                    width={120}
                  />
                  <span className="truncate text-[10px] text-zenith-soft">
                    signal value · no company / sector enrichment in this row
                  </span>
                </span>
                <span className="text-right font-mono tabular-nums text-white/72">
                  {row.signalValue != null ? row.signalValue.toFixed(1) : '—'}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function MacroPressureStrips({ rows }: { rows: MacroBucketRow[] }) {
  if (rows.length === 0) return null;
  const peak = Math.max(
    0.5,
    ...rows.map((r) => (r.averageZ == null ? 0 : Math.abs(r.averageZ))),
  );
  return (
    <section className="rounded-[10px] border border-zenith-edge-faint bg-black/30">
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">Macro Pressure</span>
        <span className="font-mono text-zenith-muted">z-score deviation by bucket</span>
      </header>
      <ul className="divide-y divide-white/[0.04]">
        {rows.slice(0, 6).map((bucket) => (
          <li
            key={bucket.bucket}
            className="grid grid-cols-[78px_120px_minmax(0,1fr)_56px] items-center gap-2 px-3 py-1.5 text-[11px] leading-5 text-white/82"
          >
            <span className="font-mono uppercase tracking-[0.12em] text-white/82">
              {bucket.bucket}
            </span>
            <DivergingBar value={bucket.averageZ} peak={peak} width={110} />
            <span className="truncate font-mono text-[10px] text-zenith-soft">
              {bucket.topSeries
                .map((s) => `${s.label}${s.z != null ? ` ${s.z.toFixed(1)}` : ''}`)
                .join(' · ') || '—'}
            </span>
            <span className="text-right font-mono tabular-nums text-white/82">
              {bucket.averageZ == null ? '—' : bucket.averageZ.toFixed(2)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function EventWatchlist({ rows }: { rows: EventRow[] }) {
  if (rows.length === 0) return null;
  const top = rows
    .slice()
    .sort((a, b) => (b.volume ?? 0) - (a.volume ?? 0))
    .slice(0, 6);
  return (
    <section className="rounded-[10px] border border-zenith-edge-faint bg-black/30">
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">Event Watchlist</span>
        <span className="font-mono text-zenith-muted">probability × volume · not a forecast</span>
      </header>
      <ul className="divide-y divide-white/[0.04]">
        {top.map((row) => (
          <li
            key={row.id}
            className="grid grid-cols-[minmax(0,1fr)_88px_72px] items-center gap-2 px-3 py-1.5 text-[11px] leading-5 text-white/82"
          >
            <span className="min-w-0">
              <span className="block truncate text-white/82">{row.title}</span>
              <span className="mt-0.5 flex flex-wrap items-center gap-2 text-[9px] uppercase tracking-[0.12em] text-zenith-muted">
                {row.topic && <span className="font-mono">{row.topic}</span>}
                {row.probabilityChange != null && (
                  <span
                    className={clsx(
                      row.probabilityChange > 0
                        ? 'text-emerald-200'
                        : row.probabilityChange < 0
                          ? 'text-rose-200'
                          : 'text-zenith-soft',
                    )}
                  >
                    Δp {row.probabilityChange > 0 ? '+' : ''}
                    {row.probabilityChange.toFixed(3)}
                  </span>
                )}
              </span>
            </span>
            <ProbabilityDot probability={row.probability} volume={row.volume} width={86} />
            <span className="text-right font-mono tabular-nums text-white/82">
              {fmtUsdCompact(row.volume)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

// v0.10 PlaneNav: tabs over the 6 browse planes with row counts.
// Operator's "overview first, then zoom" — clicking a tab changes the
// active plane in MarketWorkspace.
function PlaneNav({
  workspace,
  activePlaneId,
  onSelectPlane,
}: {
  workspace: HmcWorkspace;
  activePlaneId: string | null;
  onSelectPlane: (planeId: string) => void;
}) {
  return (
    <section
      data-zenith-cockpit-plane-nav="ready"
      className="rounded-[10px] border border-zenith-edge-faint bg-black/35"
    >
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">Market workspace · planes</span>
        <span className="font-mono text-zenith-muted">
          {workspace.planeNav.reduce((s, p) => s + p.rowCount, 0)} rows total
        </span>
      </header>
      <div className="flex flex-wrap gap-1 px-3 py-1.5">
        {workspace.planeNav.map((plane) => {
          const active = plane.id === activePlaneId;
          const empty = plane.rowCount === 0;
          return (
            <button
              key={plane.id}
              type="button"
              onClick={() => onSelectPlane(plane.id)}
              className={clsx(
                'flex items-center gap-1.5 rounded-[6px] border px-2 py-1 font-mono text-[11px] uppercase tracking-[0.10em] transition-colors',
                active
                  ? 'border-emerald-300/40 bg-emerald-300/[0.1] text-emerald-100'
                  : empty
                    ? 'border-rose-300/20 bg-rose-300/[0.04] text-rose-200/65 hover:bg-rose-300/[0.08]'
                    : 'border-zenith-edge bg-white/[0.03] text-white/72 hover:bg-white/[0.06]',
              )}
              title={`${plane.label} · ${plane.rowCount} rows · status ${plane.status}`}
            >
              <span>{plane.label}</span>
              <span className="tabular-nums text-zenith-soft">{plane.rowCount}</span>
              {empty && plane.status !== 'ok' && (
                <StatusPill tone="block">{plane.status}</StatusPill>
              )}
            </button>
          );
        })}
      </div>
    </section>
  );
}

// v0.10.3 plane-aware elastic grid spec. The fixed-width colSpec used in
// v0.10.1 stranded the active table in the left half of the workspace —
// macro/flow/event/news rows surfaced microscopic bars while the right
// half of the panel rendered as a black void. This map gives each plane
// a column ratio that fills the available band: identity columns get a
// minmax floor; metric bars (diverging_*, magnitude, probability) get
// fr-weighted minmax growth slots so DivergingBar/Microbar widths
// stretch to fit.
const PLANE_LAYOUT: Record<string, Record<string, string>> = {
  equity_universe_plane: {
    Ticker: '72px',
    Identity: 'minmax(220px, 2.2fr)',
    Category: 'minmax(110px, 0.8fr)',
    Price: '78px',
    Chg_5d: 'minmax(170px, 1.2fr)',
    Z_Short: 'minmax(170px, 1.2fr)',
    Vol_20d: 'minmax(130px, 0.9fr)',
  },
  etf_universe_plane: {
    Ticker: '78px',
    Identity: 'minmax(240px, 2.4fr)',
    Category: 'minmax(110px, 0.8fr)',
    Price: '78px',
    Chg_5d: 'minmax(190px, 1.4fr)',
    Z_Short: 'minmax(190px, 1.4fr)',
  },
  macro_series_plane: {
    ticker: 'minmax(170px, 1.4fr)',
    Proxy: 'minmax(100px, 0.7fr)',
    z_score: 'minmax(240px, 1.8fr)',
    recent_change: 'minmax(240px, 1.8fr)',
    display_change: 'minmax(110px, 0.7fr)',
    end: 'minmax(110px, 0.7fr)',
  },
  event_universe_plane: {
    q: 'minmax(360px, 2.6fr)',
    _table_path: 'minmax(130px, 0.9fr)',
    p: 'minmax(170px, 1.1fr)',
    c: 'minmax(150px, 1fr)',
    v: 'minmax(140px, 0.9fr)',
    s: 'minmax(120px, 0.8fr)',
  },
  flow_universe_plane: {
    tkr: '78px',
    sec: 'minmax(120px, 0.8fr)',
    flow: 'minmax(260px, 2fr)',
    sv: 'minmax(190px, 1.3fr)',
    wr: 'minmax(150px, 1fr)',
    flg: '78px',
  },
  news_universe_plane: {
    time: '94px',
    source_label: 'minmax(120px, 0.7fr)',
    category: 'minmax(110px, 0.7fr)',
    text: 'minmax(520px, 3.4fr)',
    url: '44px',
  },
};

function gridSpecForPlane(
  planeId: string | null,
  columns: HmcDisplayColumn[],
): string {
  const overrides = (planeId && PLANE_LAYOUT[planeId]) || {};
  return columns
    .map((c) => {
      const override = overrides[c.id];
      if (override) return override;
      switch (c.kind) {
        case 'label':
          return 'minmax(72px, 0.6fr)';
        case 'tag':
          return 'minmax(100px, 0.7fr)';
        case 'price':
          return '78px';
        case 'percent':
          return 'minmax(130px, 1fr)';
        case 'probability':
          return 'minmax(160px, 1fr)';
        case 'usd_compact':
          return 'minmax(110px, 0.8fr)';
        case 'date':
        case 'datetime':
          return 'minmax(94px, 0.6fr)';
        case 'magnitude':
          return 'minmax(140px, 1fr)';
        case 'diverging_z':
        case 'diverging_magnitude':
        case 'diverging_usd':
          return 'minmax(190px, 1.4fr)';
        case 'topic':
          return 'minmax(120px, 0.8fr)';
        case 'url':
          return '44px';
        case 'label_truncated':
          return 'minmax(220px, 2fr)';
        default:
          return 'minmax(140px, 1fr)';
      }
    })
    .join(' ');
}

// v0.10 MarketWorkspace: the active plane fills the workspace with a
// dense, sortable, paged table. Inline bars/dots encode magnitude per
// column kind so the rows are perceivable preattentively before the
// operator reads any prose. Row click sets selection and updates
// the right-rail explainer.
//
// v0.10.3 utilization:
//   • elastic colSpec (gridSpecForPlane) — no more dead black band
//     after the last metric column
//   • cursor-paged scroll: pages[] state, next_cursor follow-up
//     fetches via IntersectionObserver sentinel and a Load more button
//   • rowKey-owned-by-child: the row key (planeId::entityValue::idx) is
//     produced inside MarketWorkspace and passed back through
//     onSelectRow so the parent's selectedRowKey always matches what
//     the table is keying off (the v0.10.1 ::${entityId}-only key was
//     a known mismatch — active styling never landed)
//   • default first-row selection so the right-rail inspector is
//     populated before any click
function MarketWorkspace({
  workspace,
  activePlaneId,
  selectedRowKey,
  onSelectRow,
  runId,
}: {
  workspace: HmcWorkspace;
  activePlaneId: string;
  selectedRowKey: string | null;
  onSelectRow: (
    rowKey: string,
    entityId: string,
    row: UnknownRecord,
    columns: HmcDisplayColumn[],
  ) => void;
  runId: string | null;
}) {
  const planeMeta = workspace.planeNav.find((p) => p.id === activePlaneId);
  const isPreviewPlane = workspace.activePlanePreview.planeId === activePlaneId;
  // v0.10.3: pages is an append-only list of cursor-paged responses.
  // First page lands via the activePlaneId effect; later pages are
  // appended by IntersectionObserver + Load more. Reset on plane swap
  // and on runId change.
  const [pages, setPages] = useState<MarketBrowsePlane[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sentinelRef = useRef<HTMLLIElement | null>(null);

  useEffect(() => {
    if (!activePlaneId) return;
    let cancelled = false;
    setPages([]);
    setLoading(true);
    setError(null);
    api.marketIntelligence
      .workspacePlane(activePlaneId, { limit: 80, runId: runId ?? undefined })
      .then((data) => {
        if (cancelled) return;
        setPages([data]);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setPages([]);
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activePlaneId, runId]);

  const firstPage = pages[0] ?? null;
  const lastPage = pages.length > 0 ? pages[pages.length - 1] : null;
  const nextCursor =
    typeof lastPage?.next_cursor === 'number' && lastPage.next_cursor != null
      ? lastPage.next_cursor
      : null;

  const fetchedRows = useMemo<UnknownRecord[]>(() => {
    if (pages.length === 0) return [];
    return pages.flatMap((p) => (p.rows as UnknownRecord[] | undefined) ?? []);
  }, [pages]);

  // While the first fetch is in flight, render from the embedded preview
  // so the workspace never goes blank. Once any real page lands, switch
  // to the paged rows. Wrapping in useMemo gives downstream useMemo hooks
  // (peaks, colSpec) stable references — the bare conditional re-created
  // these arrays every render and tripped react-hooks/exhaustive-deps.
  const rows = useMemo<UnknownRecord[]>(
    () =>
      fetchedRows.length > 0
        ? fetchedRows
        : isPreviewPlane
          ? workspace.activePlanePreview.rows
          : [],
    [fetchedRows, isPreviewPlane, workspace.activePlanePreview.rows],
  );
  const columns = useMemo<HmcDisplayColumn[]>(
    () =>
      (firstPage?.columns as HmcDisplayColumn[] | undefined) ??
      (isPreviewPlane ? workspace.activePlanePreview.columns : []),
    [firstPage, isPreviewPlane, workspace.activePlanePreview.columns],
  );
  const rowCountTotal =
    firstPage?.row_count_total ??
    (isPreviewPlane ? workspace.activePlanePreview.rowCountTotal : 0);

  const loadMore = useCallback(() => {
    if (!activePlaneId) return;
    if (nextCursor == null) return;
    if (loading || loadingMore) return;
    setLoadingMore(true);
    api.marketIntelligence
      .workspacePlane(activePlaneId, {
        limit: 80,
        runId: runId ?? undefined,
        cursor: nextCursor,
      })
      .then((data) => {
        setPages((prev) => [...prev, data]);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoadingMore(false));
  }, [activePlaneId, nextCursor, runId, loading, loadingMore]);

  // IntersectionObserver-driven infinite scroll. The sentinel is a
  // zero-height list item at the bottom of the rendered rows; when it
  // crosses the viewport the next cursor fires. The Load more button
  // below is a deterministic fallback for browsers / jsdom that do not
  // implement IntersectionObserver.
  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;
    const node = sentinelRef.current;
    if (!node) return;
    if (nextCursor == null) return;
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          loadMore();
        }
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [loadMore, nextCursor, rows.length]);

  // Pre-compute peak magnitudes per column for diverging/microbar encoding.
  const peaks = useMemo<Record<string, number>>(() => {
    const out: Record<string, number> = {};
    for (const c of columns) {
      let peak = 0;
      for (const row of rows) {
        const v = row[c.id];
        if (typeof v === 'number' && Number.isFinite(v)) {
          if (Math.abs(v) > peak) peak = Math.abs(v);
        }
      }
      out[c.id] = peak || 1;
    }
    return out;
  }, [columns, rows]);

  // v0.10.3: plane-aware elastic colSpec. Replaces the fixed-pixel
  // ladder that left a black band on the right side of flow/macro/
  // event/news planes.
  const colSpec = useMemo(
    () => gridSpecForPlane(activePlaneId, columns),
    [activePlaneId, columns],
  );

  const renderCell = (column: HmcDisplayColumn, row: UnknownRecord) => {
    const raw = row[column.id];
    const value =
      typeof raw === 'number' && Number.isFinite(raw)
        ? raw
        : typeof raw === 'string'
          ? raw
          : null;
    switch (column.kind) {
      case 'label':
      case 'tag':
      case 'topic':
        return <span className="truncate font-mono text-white/82">{value == null ? '—' : String(value)}</span>;
      case 'label_truncated':
        return (
          <span className="truncate text-white/72" title={value == null ? '' : String(value)}>
            {value == null ? '—' : String(value)}
          </span>
        );
      case 'url':
        return (
          <span className="truncate font-mono text-[11px] text-sky-300/75">
            {value == null ? '—' : String(value).slice(0, 32)}
          </span>
        );
      case 'date':
      case 'datetime':
        return (
          <span className="truncate font-mono tabular-nums text-[11px] text-zenith-soft">
            {value == null ? '—' : String(value).replace('T', ' ').slice(0, 16)}
          </span>
        );
      case 'price':
        return (
          <span className="block truncate text-right font-mono tabular-nums text-white/82">
            {typeof value === 'number' ? value.toFixed(2) : '—'}
          </span>
        );
      case 'percent':
        return (
          <span className="block truncate text-right font-mono tabular-nums text-white/72">
            {typeof value === 'number' ? `${value.toFixed(1)}%` : '—'}
          </span>
        );
      case 'probability':
        return (
          <span className="flex items-center gap-1.5">
            <ProbabilityDot
              probability={typeof value === 'number' ? value : null}
              volume={null}
              width={60}
            />
            <span className="text-right font-mono tabular-nums text-white/82">
              {typeof value === 'number' ? value.toFixed(2) : '—'}
            </span>
          </span>
        );
      case 'usd_compact':
        return (
          <span className="block truncate text-right font-mono tabular-nums text-white/72">
            {typeof value === 'number' ? fmtUsdCompact(value) : '—'}
          </span>
        );
      case 'diverging_z':
      case 'diverging_magnitude':
      case 'diverging_usd': {
        const peak = peaks[column.id] || 1;
        const v = typeof value === 'number' ? value : null;
        return (
          <span className="flex items-center gap-1.5">
            <DivergingBar value={v} peak={peak} width={84} />
            <span
              className={clsx(
                'text-right font-mono tabular-nums',
                v == null
                  ? 'text-zenith-soft'
                  : v > 0
                    ? 'text-emerald-100'
                    : v < 0
                      ? 'text-rose-100'
                      : 'text-white/72',
              )}
            >
              {column.kind === 'diverging_usd' && typeof v === 'number'
                ? fmtUsdCompact(v)
                : typeof v === 'number'
                  ? `${v > 0 ? '+' : ''}${v.toFixed(2)}`
                  : '—'}
            </span>
          </span>
        );
      }
      case 'magnitude': {
        const peak = peaks[column.id] || 1;
        const v = typeof value === 'number' ? value : null;
        return (
          <span className="flex items-center gap-1.5">
            <Microbar
              magnitude={v != null ? Math.min(1, Math.abs(v) / peak) : null}
              tone="neutral"
              width={50}
            />
            <span className="text-right font-mono tabular-nums text-white/72">
              {typeof v === 'number' ? v.toFixed(2) : '—'}
            </span>
          </span>
        );
      }
      default:
        return <span className="truncate text-white/72">{value == null ? '—' : String(value)}</span>;
    }
  };

  // v0.10.1: column status + density readiness gating. A plane is
  // "ok" only if it actually has rows visible AND the first column
  // (entity_id) carries a non-empty label on most visible rows.
  const primaryColumnId = columns[0]?.id ?? null;
  const primaryColumnNonempty =
    primaryColumnId
      ? rows.filter((r) => {
          const v = (r as Record<string, unknown>)[primaryColumnId];
          return v !== null && v !== undefined && v !== '';
        }).length >= Math.min(rows.length, 5)
      : false;
  const columnStatus =
    rows.length >= 25 && primaryColumnNonempty
      ? 'ok'
      : rows.length > 0
        ? 'thin'
        : 'bad';
  const density: 'dense' | 'sparse' | 'empty' =
    rows.length === 0 ? 'empty' : rows.length >= 25 ? 'dense' : 'sparse';
  const rowCountRaw =
    typeof firstPage?.row_count_raw === 'number'
      ? firstPage.row_count_raw
      : rowCountTotal;
  const filteredOut =
    typeof firstPage?.filtered_out_count === 'number'
      ? firstPage.filtered_out_count
      : 0;

  // v0.10.3: scroll + fill readiness. A "ready" workspace shows at least
  // 25 rows, has at least 5 columns, and either (a) has finished loading
  // every page (no nextCursor) or (b) the IntersectionObserver sentinel
  // is rendered. `fill=full` is the stricter gate: ≥25 rows AND ≥5
  // columns; station_render's market readiness selector reads this.
  const fill: 'full' | 'partial' | 'empty' =
    rows.length === 0
      ? 'empty'
      : rows.length >= 25 && columns.length >= 5
        ? 'full'
        : 'partial';
  const scrollReady: 'ready' | 'pending' =
    rows.length >= 25 ? 'ready' : 'pending';

  // v0.10.3: default-select the first row when rows arrive and the
  // parent has not pinned a selection yet. The right-rail row inspector
  // then has content before any click. We compute the candidate rowKey
  // first so the same key shape is consumed on click and on default.
  const buildRowKey = (entityValue: string, idx: number) =>
    `${activePlaneId}::${entityValue}::${idx}`;
  const firstRowEntity =
    rows.length > 0 && primaryColumnId
      ? (rows[0][primaryColumnId] as string | undefined) ?? 'row-0'
      : null;
  const firstRowKey =
    firstRowEntity != null ? buildRowKey(firstRowEntity, 0) : null;

  useEffect(() => {
    if (selectedRowKey) return;
    if (!firstRowKey || rows.length === 0 || columns.length === 0) return;
    onSelectRow(firstRowKey, firstRowEntity ?? '', rows[0], columns);
    // intentionally narrow deps: only the very first arrival triggers
    // default selection; later page appends or plane swaps re-enter via
    // selectedRowKey reset by the parent.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [firstRowKey]);

  return (
    <section
      data-zenith-cockpit-market-workspace="ready"
      data-zenith-cockpit-workspace-run={runId ?? 'none'}
      data-zenith-cockpit-active-plane={activePlaneId}
      data-zenith-cockpit-active-plane-rows={String(rowCountTotal)}
      data-zenith-cockpit-active-plane-rows-raw={String(rowCountRaw)}
      data-zenith-cockpit-active-plane-filtered-out={String(filteredOut)}
      data-zenith-cockpit-active-plane-visible-rows={String(rows.length)}
      data-zenith-cockpit-active-plane-column-status={columnStatus}
      data-zenith-cockpit-active-plane-density={density}
      data-zenith-cockpit-active-plane-fill={fill}
      data-zenith-cockpit-active-plane-scroll={scrollReady}
      data-zenith-cockpit-active-plane-loaded-rows={String(rows.length)}
      data-zenith-cockpit-active-plane-next-cursor={
        nextCursor == null ? 'none' : String(nextCursor)
      }
      className="flex min-h-[420px] flex-1 flex-col rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">
          {planeMeta?.label ?? activePlaneId}
          {' · '}
          {rowCountTotal} rows
          {rows.length < rowCountTotal && rowCountTotal > 0 ? ` · showing ${rows.length}` : ''}
          {filteredOut > 0
            ? ` · ${filteredOut} heterogeneous row${filteredOut === 1 ? '' : 's'} filtered`
            : ''}
        </span>
        <span className="font-mono text-zenith-muted">
          {planeMeta?.feedId ?? ''}
          {planeMeta?.defaultSort.column
            ? ` · sort ${planeMeta.defaultSort.column} ${planeMeta.defaultSort.direction ?? 'desc'}`
            : ''}
        </span>
      </header>
      {loading && rows.length === 0 ? (
        <div className="px-3 py-4 text-[11px] text-zenith-muted">Loading plane…</div>
      ) : error && rows.length === 0 ? (
        <div className="px-3 py-4 text-[11px] text-rose-200">
          Plane failed to load: {error}
        </div>
      ) : rows.length === 0 ? (
        <div className="space-y-1 px-3 py-4 font-mono text-[10px] leading-4 text-zenith-soft">
          <div className="text-white/72">No rows for this run/plane.</div>
          <div>Workspace bundle run: <span className="text-white/72">{runId ?? '—'}</span></div>
          <div>
            Route resolved run:{' '}
            <span className="text-white/72">{firstPage?.run_id ?? '—'}</span>
          </div>
          <div>
            Raw rows: <span className="text-white/72">{rowCountRaw}</span> · filtered out:{' '}
            <span className="text-white/72">{filteredOut}</span>
          </div>
          <div>
            Extraction status:{' '}
            <span className="text-white/72">
              {String(
                (firstPage?.extraction_status as Record<string, unknown> | undefined)?.status ?? '—',
              )}
            </span>
          </div>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <div
            className="grid w-full gap-2 border-b border-zenith-edge-soft px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-zenith-muted"
            style={{ gridTemplateColumns: colSpec }}
          >
            {columns.map((c) => (
              <span key={c.id} className="truncate">
                {c.label}
              </span>
            ))}
          </div>
          <div
            className="min-h-0 flex-1 overflow-auto"
            data-zenith-cockpit-active-plane-scroll-container="ready"
          >
            <ul>
              {rows.map((row, idx) => {
                const entityCol = columns[0]?.id ?? '';
                const entityValue =
                  entityCol && typeof row[entityCol] === 'string'
                    ? (row[entityCol] as string)
                    : `row-${idx}`;
                const rowKey = buildRowKey(entityValue, idx);
                const active = rowKey === selectedRowKey;
                return (
                  <li key={rowKey}>
                    <button
                      type="button"
                      onClick={() => onSelectRow(rowKey, entityValue, row, columns)}
                      className={clsx(
                        'grid w-full items-center gap-2 px-3 py-1 text-[11px] leading-5 transition-colors',
                        active ? 'bg-white/[0.07]' : 'hover:bg-white/[0.03]',
                      )}
                      style={{ gridTemplateColumns: colSpec }}
                    >
                      {columns.map((c) => (
                        <span key={c.id} className="min-w-0 truncate">
                          {renderCell(c, row)}
                        </span>
                      ))}
                    </button>
                  </li>
                );
              })}
              {nextCursor != null && (
                <li
                  ref={sentinelRef}
                  data-zenith-cockpit-active-plane-scroll-sentinel="ready"
                  className="h-1"
                />
              )}
            </ul>
            {nextCursor != null && (
              <div className="flex items-center justify-center border-t border-zenith-edge-soft px-3 py-1.5">
                <button
                  type="button"
                  onClick={loadMore}
                  disabled={loadingMore}
                  data-zenith-cockpit-active-plane-load-more="ready"
                  className="rounded-[6px] border border-zenith-edge bg-white/[0.03] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.10em] text-white/72 transition-colors hover:bg-white/[0.06] disabled:opacity-50"
                >
                  {loadingMore ? 'Loading…' : `Load more (next ${nextCursor})`}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

// v0.10.3 RowInspector. Browse mode demotes ARM/situation language to a
// secondary panel; the active selected row is what the operator is
// currently reading. The inspector lists every non-internal column
// from the selected row with its label and renderer-aware formatting.
function RowInspector({
  planeId,
  columns,
  row,
}: {
  planeId: string | null;
  columns: HmcDisplayColumn[];
  row: UnknownRecord | null;
}) {
  if (!row || !planeId) {
    return (
      <section
        data-zenith-cockpit-row-inspector="empty"
        className="rounded-[10px] border border-zenith-edge-faint bg-black/30 px-3 py-2 font-mono text-[10px] text-zenith-muted"
      >
        Select a row to inspect.
      </section>
    );
  }
  const entries: { col: HmcDisplayColumn; value: unknown }[] = columns
    .filter((c) => c.id !== '_table_path')
    .map((c) => ({ col: c, value: row[c.id] }));
  return (
    <section
      data-zenith-cockpit-row-inspector="ready"
      data-zenith-cockpit-row-inspector-plane={planeId}
      className="flex flex-col gap-1 rounded-[10px] border border-emerald-300/25 bg-emerald-300/[0.04] px-3 py-2"
    >
      <header className="flex items-baseline justify-between font-mono text-[10px] uppercase tracking-[0.14em]">
        <span className="text-emerald-100">
          Selected row
        </span>
        <span className="text-zenith-muted">{planeId}</span>
      </header>
      <dl className="mt-1 grid gap-1 font-mono text-[11px] leading-5">
        {entries.map(({ col, value }) => {
          const display =
            value == null
              ? '—'
              : typeof value === 'number'
                ? Number.isFinite(value)
                  ? value.toFixed(2)
                  : '—'
                : String(value);
          const tone =
            typeof value === 'number'
              ? value > 0
                ? 'text-emerald-100'
                : value < 0
                  ? 'text-rose-100'
                  : 'text-white/82'
              : 'text-white/82';
          const isUrl = col.kind === 'url' && typeof value === 'string' && value.length > 0;
          return (
            <div
              key={col.id}
              className="flex items-baseline justify-between gap-3 border-b border-zenith-edge-soft pb-1 last:border-0"
            >
              <dt className="shrink-0 text-[10px] uppercase tracking-[0.10em] text-zenith-muted">
                {col.label}
              </dt>
              <dd className={clsx('min-w-0 truncate text-right', tone)}>
                {isUrl ? (
                  <a
                    href={display}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="text-sky-200 hover:text-sky-100"
                  >
                    {display.slice(0, 64)}
                  </a>
                ) : (
                  display
                )}
              </dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}

// v0.9 typed visual planes. Operator named this layer the "visual
// semantics compiler" — the backend emits typed planes with column
// legends, applicability, and global states so the frontend renders
// a market field without repeating tokens like "confidence" or "news
// dark" inside every cell. These planes are the PRIMARY surface in
// v0.9; the universal matrix below is demoted to diagnostics.

function PlaneHeader({
  plane,
  trailing,
}: {
  plane: HmcVisualPlane;
  trailing?: React.ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-center gap-2 border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
      <span className="font-mono text-white/82">
        {plane.title} · {plane.rows.length} rows
      </span>
      {plane.legend && (
        <span className="font-mono text-zenith-muted">legend · {plane.legend}</span>
      )}
      {plane.interpretation && (
        <span className="font-mono normal-case tracking-normal text-amber-100/70">
          {plane.interpretation}
        </span>
      )}
      <span className="ml-auto font-mono text-white/35">
        primitive · {plane.primitive}
      </span>
      {trailing}
    </header>
  );
}

function EquityFlowPlane({
  plane,
  onSelectRow,
}: {
  plane: HmcVisualPlane;
  onSelectRow: (rowId: string, situationIds: string[]) => void;
}) {
  if (plane.rows.length === 0) return null;
  const peak = Math.max(
    1,
    ...plane.rows.map((r) => Math.abs((r.metrics.flow_usd ?? 0) as number)),
  );
  return (
    <section
      data-zenith-cockpit-plane="equity_flow_plane"
      className="rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <PlaneHeader plane={plane} />
      <ul className="divide-y divide-white/[0.04]">
        {plane.rows.map((row) => {
          const flowUsd = row.metrics.flow_usd ?? null;
          const conviction = row.metrics.conviction ?? null;
          const tone: 'pos' | 'neg' | 'neutral' =
            flowUsd == null ? 'neutral' : flowUsd >= 0 ? 'pos' : 'neg';
          return (
            <li key={row.id}>
              <button
                type="button"
                onClick={() => onSelectRow(row.id, [])}
                className="grid w-full grid-cols-[60px_minmax(0,1fr)_88px_72px] items-center gap-2 px-3 py-1.5 text-left text-[11px] leading-5 transition-colors hover:bg-white/[0.03]"
                title={row.subtitle ?? row.id}
              >
                <span className="font-mono text-white">{row.label}</span>
                <span className="flex items-center gap-2">
                  <DivergingBar value={flowUsd} peak={peak} width={140} />
                  <span className="truncate text-[10px] text-zenith-soft">
                    {row.subtitle ?? '—'}
                  </span>
                </span>
                <span
                  className={clsx(
                    'text-right font-mono tabular-nums',
                    tone === 'pos'
                      ? 'text-emerald-100'
                      : tone === 'neg'
                        ? 'text-rose-100'
                        : 'text-white/72',
                  )}
                >
                  {flowUsd != null ? fmtUsdCompact(flowUsd) : '—'}
                </span>
                <span className="flex items-center gap-1 font-mono text-[10px] text-zenith-soft">
                  <Microbar
                    magnitude={
                      conviction != null
                        ? Math.max(0, Math.min(1, conviction / 100))
                        : null
                    }
                    tone="neutral"
                    width={40}
                  />
                  <span className="tabular-nums">
                    {conviction != null ? conviction.toFixed(1) : '—'}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function MacroPressurePlane({
  plane,
  onSelectRow,
}: {
  plane: HmcVisualPlane;
  onSelectRow: (rowId: string, situationIds: string[]) => void;
}) {
  if (plane.rows.length === 0) return null;
  const peak = Math.max(
    0.5,
    ...plane.rows.map((r) => Math.abs((r.metrics.average_z_score ?? 0) as number)),
  );
  return (
    <section
      data-zenith-cockpit-plane="macro_pressure_plane"
      className="rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <PlaneHeader plane={plane} />
      <ul className="divide-y divide-white/[0.04]">
        {plane.rows.map((row) => {
          const z = row.metrics.average_z_score ?? null;
          const topSeries = (row.topSeries ?? []).slice(0, 3);
          return (
            <li key={row.id}>
              <button
                type="button"
                onClick={() => onSelectRow(row.id, [])}
                className="grid w-full grid-cols-[90px_140px_minmax(0,1fr)_56px] items-center gap-2 px-3 py-1.5 text-left text-[11px] leading-5 transition-colors hover:bg-white/[0.03]"
              >
                <span className="font-mono uppercase tracking-[0.12em] text-white/82">
                  {row.label}
                </span>
                <DivergingBar value={z} peak={peak} width={130} />
                <span className="flex flex-wrap gap-x-2 truncate font-mono text-[10px] text-zenith-soft">
                  {topSeries.map((s, idx) => {
                    const ticker =
                      typeof s.ticker === 'string' ? s.ticker : '—';
                    const sz =
                      typeof s.z_score === 'number' ? s.z_score : null;
                    return (
                      <span key={`${row.id}-ts-${idx}`}>
                        {ticker.replace(/_/g, ' ')}
                        {sz != null ? ` ${sz.toFixed(2)}` : ''}
                      </span>
                    );
                  })}
                </span>
                <span
                  className={clsx(
                    'text-right font-mono tabular-nums',
                    z == null
                      ? 'text-zenith-soft'
                      : Math.abs(z) >= 2
                        ? 'text-amber-200'
                        : Math.abs(z) >= 1
                          ? 'text-emerald-200'
                          : 'text-white/72',
                  )}
                >
                  {z != null ? `${z >= 0 ? '+' : ''}${z.toFixed(2)}σ` : '—'}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function EventLiquidityPlane({
  plane,
  onSelectRow,
}: {
  plane: HmcVisualPlane;
  onSelectRow: (rowId: string, situationIds: string[]) => void;
}) {
  if (plane.rows.length === 0) return null;
  return (
    <section
      data-zenith-cockpit-plane="event_liquidity_plane"
      className="rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <PlaneHeader plane={plane} />
      <ul className="divide-y divide-white/[0.04]">
        {plane.rows.map((row) => {
          const prob = row.metrics.probability ?? null;
          const vol = row.metrics.volume ?? null;
          const dp = row.metrics.probability_change ?? null;
          return (
            <li key={row.id}>
              <button
                type="button"
                onClick={() => onSelectRow(row.id, [])}
                className="grid w-full grid-cols-[minmax(0,1fr)_92px_88px_56px] items-center gap-2 px-3 py-1.5 text-left text-[11px] leading-5 transition-colors hover:bg-white/[0.03]"
              >
                <span className="min-w-0">
                  <span className="block truncate text-white/82">{row.label}</span>
                  {row.subtitle && (
                    <span className="block truncate font-mono text-[10px] uppercase tracking-[0.12em] text-zenith-muted">
                      {row.subtitle}
                    </span>
                  )}
                </span>
                <ProbabilityDot probability={prob} volume={vol} width={90} />
                <span className="text-right font-mono tabular-nums text-white/82">
                  {vol != null ? fmtUsdCompact(vol) : '—'}
                </span>
                <span
                  className={clsx(
                    'text-right font-mono tabular-nums',
                    dp == null
                      ? 'text-zenith-soft'
                      : dp > 0
                        ? 'text-emerald-200'
                        : dp < 0
                          ? 'text-rose-200'
                          : 'text-zenith-soft',
                  )}
                >
                  {dp != null
                    ? `${dp > 0 ? '+' : ''}${dp.toFixed(3)}`
                    : '—'}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function DataQualityPlane({
  plane,
  globalStates,
}: {
  plane: HmcVisualPlane;
  globalStates: HmcGlobalState[];
}) {
  // Render rows as compact lane-health tape. Each row already carries a
  // `state` / `problem` / `action` from data_quality. Global states are
  // appended (deduped by lane) so the user sees "news dark" exactly once.
  const rows = plane.rows as unknown as HmcDataQualityRow[];
  const lanesSeen = new Set(rows.map((r) => r.lane));
  return (
    <section
      data-zenith-cockpit-plane="data_quality_plane"
      className="rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <PlaneHeader plane={plane} />
      <ul className="divide-y divide-white/[0.04]">
        {rows.map((row, idx) => (
          <li
            key={`${row.lane}-${idx}`}
            className="grid grid-cols-[130px_60px_minmax(0,1fr)_minmax(0,1fr)] items-baseline gap-2 px-3 py-1.5 text-[11px] leading-5 text-white/72"
          >
            <span className="font-mono text-white/82">{row.lane}</span>
            <StatusPill
              tone={
                row.state === 'dark' || row.state === 'drift'
                  ? 'block'
                  : row.state === 'stale' || row.state === 'incomplete'
                    ? 'warn'
                    : 'neutral'
              }
            >
              {row.state}
            </StatusPill>
            <span className="truncate text-white/72">{row.problem}</span>
            <span className="truncate text-zenith-muted">{row.action}</span>
          </li>
        ))}
        {globalStates
          .filter((g) => !g.lane || !lanesSeen.has(g.lane))
          .map((g, idx) => (
            <li
              key={`${g.id}-${idx}`}
              className="grid grid-cols-[130px_60px_minmax(0,1fr)_minmax(0,1fr)] items-baseline gap-2 px-3 py-1.5 text-[11px] leading-5 text-white/72"
            >
              <span className="font-mono text-white/82">{g.lane ?? g.id}</span>
              <StatusPill
                tone={
                  g.tone === 'block' || g.tone === 'neg'
                    ? 'block'
                    : g.tone === 'warn'
                      ? 'warn'
                      : 'neutral'
                }
              >
                global
              </StatusPill>
              <span className="truncate text-white/72">{g.label}</span>
              <span className="truncate text-zenith-muted">{g.promotedTo ?? ''}</span>
            </li>
          ))}
      </ul>
    </section>
  );
}

// v0.8 Market Insight Matrix. The dominant visual surface. Rows are
// entities/themes/events; columns are signal lanes (price/flow/macro/
// event/news/coverage/quality); cells encode normalized magnitude +
// direction + tone backend-derived. Clicking a row triggers
// selection (drives the explainer panel).
function MarketInsightMatrix({
  hmc,
  selectedRowId,
  onSelectRow,
}: {
  hmc: HumanMarketCockpit;
  selectedRowId: string | null;
  onSelectRow: (rowId: string, situationIds: string[]) => void;
}) {
  const cellsByRow = useMemo(() => {
    const m = new Map<string, HmcCell[]>();
    for (const cell of hmc.cells) {
      const arr = m.get(cell.rowId) ?? [];
      arr.push(cell);
      m.set(cell.rowId, arr);
    }
    return m;
  }, [hmc]);
  const columns = hmc.columns;
  if (hmc.rows.length === 0 || columns.length === 0) return null;
  const cellWidth = `repeat(${columns.length}, minmax(60px, 1fr))`;
  return (
    <section
      data-zenith-cockpit-market-matrix="ready"
      data-zenith-cockpit-market-matrix-rows={hmc.rows.length}
      data-zenith-cockpit-market-matrix-cols={columns.length}
      className="rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">
          Market Insight Matrix · {hmc.rows.length} rows × {columns.length} lanes
        </span>
        <span className="font-mono text-zenith-muted">
          source · human_market_cockpit.market_field · linked explainer
        </span>
      </header>
      <div className="overflow-auto">
        <div
          className="grid w-full min-w-[640px] gap-1 px-3 py-2 text-[10px] leading-5"
          style={{ gridTemplateColumns: `minmax(160px, 1.2fr) ${cellWidth}` }}
        >
          <div className="font-mono uppercase tracking-[0.12em] text-zenith-muted">
            entity / theme / event
          </div>
          {columns.map((col) => (
            <div
              key={col.id}
              className="text-center font-mono uppercase tracking-[0.12em] text-zenith-muted"
              title={col.kind}
            >
              {col.label}
            </div>
          ))}
          {hmc.rows.map((row) => {
            const cells = cellsByRow.get(row.id) ?? [];
            const cellByCol = new Map<string, HmcCell>();
            for (const c of cells) cellByCol.set(c.columnId, c);
            const active = row.id === selectedRowId;
            const situationIds = cells.flatMap((c) => c.situationIds).filter(Boolean);
            return (
              <React.Fragment key={row.id}>
                <button
                  type="button"
                  onClick={() => onSelectRow(row.id, situationIds)}
                  className={clsx(
                    'min-w-0 truncate rounded-[6px] px-2 py-1 text-left text-[11px] transition-colors',
                    active
                      ? 'bg-white/[0.07] text-white'
                      : 'text-white/82 hover:bg-white/[0.03]',
                  )}
                  title={row.subtitle ?? row.id}
                >
                  <span className="block truncate font-mono text-white/82">
                    {row.label}
                  </span>
                  {row.subtitle && (
                    <span className="mt-0.5 block truncate font-mono text-[9.5px] text-zenith-muted">
                      {row.subtitle}
                    </span>
                  )}
                </button>
                {columns.map((col) => {
                  const cell = cellByCol.get(col.id);
                  const intensity = cell
                    ? Math.max(0.0, Math.min(1.0, Math.abs(cell.normalized)))
                    : 0;
                  const tone = cell?.tone ?? 'neutral';
                  const bg =
                    !cell || cell.value == null
                      ? 'bg-white/[0.02]'
                      : tone === 'pos' || tone === 'ok'
                        ? 'bg-emerald-300'
                        : tone === 'neg' || tone === 'block'
                          ? 'bg-rose-300'
                          : tone === 'warn'
                            ? 'bg-amber-300'
                            : 'bg-sky-300';
                  return (
                    <button
                      type="button"
                      key={`${row.id}:${col.id}`}
                      onClick={() => onSelectRow(row.id, situationIds)}
                      className={clsx(
                        'relative flex h-9 min-w-0 items-center justify-center overflow-hidden rounded-[4px] border text-center',
                        active
                          ? 'border-zenith-edge-strong'
                          : 'border-zenith-edge-soft hover:border-zenith-edge',
                      )}
                      title={cell?.label ?? '—'}
                    >
                      <span
                        className={clsx('absolute inset-0', bg)}
                        style={{
                          opacity: cell && cell.value != null ? 0.08 + intensity * 0.55 : 0,
                        }}
                      />
                      <span className="relative truncate font-mono tabular-nums text-[11px] text-white/85">
                        {cell?.label ?? ''}
                      </span>
                    </button>
                  );
                })}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function MarketPulseStrip({ pulse }: { pulse: HmcPulseFact[] }) {
  if (pulse.length === 0) return null;
  return (
    <section
      data-zenith-cockpit-market-pulse="ready"
      className="rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">Market Pulse · {pulse.length}</span>
        <span className="font-mono text-zenith-muted">
          source · human_market_cockpit.market_pulse
        </span>
      </header>
      <div className="flex flex-wrap gap-x-4 gap-y-1 px-3 py-1.5 text-[11px] leading-5 text-white/82">
        {pulse.map((p, idx) => (
          <span key={`${p.label}-${idx}`} className="flex items-center gap-1.5" title={p.caveat ?? ''}>
            <span className="font-mono uppercase tracking-[0.12em] text-zenith-soft">
              {p.label}
            </span>
            <span
              className={clsx(
                'font-mono tabular-nums',
                p.tone === 'block'
                  ? 'text-rose-200'
                  : p.tone === 'warn'
                    ? 'text-amber-200'
                    : p.tone === 'pos' || p.tone === 'ok'
                      ? 'text-emerald-200'
                      : p.tone === 'neg'
                        ? 'text-rose-200'
                        : 'text-white/82',
              )}
            >
              {p.value}
            </span>
            {p.interpretation && (
              <span className="font-mono text-[10px] text-zenith-muted">{p.interpretation}</span>
            )}
          </span>
        ))}
      </div>
    </section>
  );
}

function SignalCardsStack({
  cards,
  onSelectRow,
}: {
  cards: HmcSignalCard[];
  onSelectRow: (rowId: string | null, situationIds: string[]) => void;
}) {
  if (cards.length === 0) return null;
  return (
    <section
      data-zenith-cockpit-signal-cards="ready"
      data-zenith-cockpit-signal-cards-count={cards.length}
      className="rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">Signal Cards · {cards.length}</span>
        <span className="font-mono text-zenith-muted">
          source · human_market_cockpit.signal_cards · deterministic templates
        </span>
      </header>
      <ul className="divide-y divide-white/[0.04]">
        {cards.map((card) => (
          <li key={card.id}>
            <button
              type="button"
              onClick={() => onSelectRow(card.linkedRowId, card.linkedSituationIds)}
              className="grid w-full grid-cols-1 gap-1 px-3 py-2 text-left text-[11px] leading-5 transition-colors hover:bg-white/[0.03]"
            >
              <span className="text-[12px] font-medium text-white">
                {card.title}
              </span>
              {card.oneLine && (
                <span className="text-white/72">{card.oneLine}</span>
              )}
              {card.keyNumbers.length > 0 && (
                <span className="flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-[10px] text-zenith-soft">
                  {card.keyNumbers.map((kn, idx) => (
                    <span key={`${card.id}-kn-${idx}`}>
                      <span className="uppercase tracking-[0.12em] text-zenith-muted">
                        {kn.label}
                      </span>{' '}
                      <span className="text-white/82 tabular-nums">{kn.value}</span>
                    </span>
                  ))}
                </span>
              )}
              {card.watchpoint && (
                <span className="text-[10px] leading-4 text-amber-100/75">
                  watchpoint · {card.watchpoint}
                </span>
              )}
              {card.caveat && (
                <span className="text-[10px] leading-4 text-zenith-muted">
                  caveat · {card.caveat}
                </span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function DataQualityStrip({ rows }: { rows: HmcDataQualityRow[] }) {
  if (rows.length === 0) return null;
  return (
    <section
      data-zenith-cockpit-data-quality="ready"
      className="rounded-[10px] border border-zenith-edge-faint bg-black/25"
    >
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">Data Quality · {rows.length} issues</span>
        <span className="font-mono text-zenith-muted">
          source · human_market_cockpit.data_quality (defects demoted out of market panels)
        </span>
      </header>
      <ul className="divide-y divide-white/[0.04]">
        {rows.map((row, idx) => (
          <li
            key={`${row.lane}-${idx}`}
            className="grid grid-cols-[120px_60px_minmax(0,1fr)_minmax(0,1fr)] items-baseline gap-2 px-3 py-1.5 text-[11px] leading-5 text-white/72"
            title={row.action}
          >
            <span className="font-mono text-white/82">{row.lane}</span>
            <StatusPill
              tone={
                row.state === 'dark' || row.state === 'drift'
                  ? 'block'
                  : row.state === 'stale' || row.state === 'incomplete'
                    ? 'warn'
                    : 'neutral'
              }
            >
              {row.state}
            </StatusPill>
            <span className="truncate text-white/72">{row.problem}</span>
            <span className="truncate text-zenith-muted">{row.action}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

// v0.6.1 Market Breadth panel. Renders compact group-level summary rows
// from existing substrate (coverage feeds, situation overview counts,
// flow leaderboard top, macro buckets, event topics). Operator's "breadth
// browser" request: show the data landscape in browsable groups and
// averages, not as more KPI boxes.
function MarketBreadth({
  coverage,
  situations,
  flow,
  macro,
  events,
  ranked,
  readModel,
}: {
  coverage: CoverageRow[];
  situations: SituationCardRow[];
  flow: FlowRow[];
  macro: MacroBucketRow[];
  events: EventRow[];
  ranked: RankedObs[];
  readModel: MarketDashboardReadModel | null;
}) {
  const overview = asRecord(readModel?.overview);
  const displayStateCounts = asRecord(overview?.display_state_counts);
  const claimLevelCounts = asRecord(overview?.claim_level_counts);

  const rows = useMemo<BreadthGroupRow[]>(() => {
    const out: BreadthGroupRow[] = [];

    for (const cov of coverage) {
      const isEmpty = cov.rows === 0;
      out.push({
        label: cov.label,
        detail: cov.feedId,
        primary:
          cov.rows == null
            ? '—'
            : isEmpty
              ? '0'
              : cov.rows.toLocaleString(),
        count: cov.rows,
        tone: isEmpty ? 'block' : 'ok',
      });
    }

    if (situations.length > 0) {
      const ready = situations.filter((s) => s.displayState === 'ready').length;
      const degraded = situations.filter((s) => s.displayState === 'degraded').length;
      out.push({
        label: 'Situations',
        detail: `display state · ${ready} ready · ${degraded} degraded`,
        primary: String(situations.length),
        count: situations.length,
        tone: ready > 0 ? 'ok' : 'warn',
      });
    }

    if (ranked.length > 0) {
      const meanInterest =
        ranked.reduce((s, r) => s + (r.interestingness ?? 0), 0) / ranked.length;
      out.push({
        label: 'Ranked obs',
        detail: `mean interestingness ${meanInterest.toFixed(2)}`,
        primary: String(ranked.length),
        count: ranked.length,
        tone: 'ok',
      });
    }

    if (flow.length > 0) {
      const flowSum = flow.reduce(
        (s, r) => s + Math.abs(r.flowUsd ?? 0),
        0,
      );
      const topFlow = flow
        .slice()
        .sort((a, b) => Math.abs(b.flowUsd ?? 0) - Math.abs(a.flowUsd ?? 0))[0];
      out.push({
        label: 'Flow board',
        detail: topFlow ? `top · ${topFlow.ticker}` : 'no top row',
        primary: fmtUsdCompact(flowSum) + ' Σ|flow|',
        count: flow.length,
        tone: 'ok',
      });
    }

    if (macro.length > 0) {
      const topBucket = macro[0];
      out.push({
        label: 'Macro buckets',
        detail: topBucket
          ? `top · ${topBucket.bucket}${
              topBucket.averageZ != null
                ? ` (z ${topBucket.averageZ.toFixed(2)})`
                : ''
            }`
          : 'no top bucket',
        primary: String(macro.length),
        count: macro.length,
        tone: 'ok',
      });
    }

    if (events.length > 0) {
      const topVolume = events
        .slice()
        .sort((a, b) => (b.volume ?? 0) - (a.volume ?? 0))[0];
      out.push({
        label: 'Events',
        detail: topVolume
          ? `top vol · ${fmtUsdCompact(topVolume.volume)}`
          : 'no top event',
        primary: String(events.length),
        count: events.length,
        tone: 'ok',
      });
    }

    if (displayStateCounts) {
      for (const [state, raw] of Object.entries(displayStateCounts)) {
        const n = asNumber(raw);
        if (n == null) continue;
        out.push({
          label: `Overview · ${state}`,
          detail: 'overview.display_state_counts',
          primary: String(n),
          count: n,
          tone: state === 'ready' ? 'ok' : state === 'degraded' ? 'warn' : 'neutral',
        });
      }
    }
    if (claimLevelCounts) {
      for (const [level, raw] of Object.entries(claimLevelCounts)) {
        const n = asNumber(raw);
        if (n == null) continue;
        out.push({
          label: `Claim · ${stateLabel(level)}`,
          detail: 'overview.claim_level_counts',
          primary: String(n),
          count: n,
          tone: 'neutral',
        });
      }
    }
    return out;
  }, [
    coverage,
    situations,
    flow,
    macro,
    events,
    ranked,
    displayStateCounts,
    claimLevelCounts,
  ]);

  if (rows.length === 0) return null;

  return (
    <section
      data-zenith-cockpit-market-breadth="ready"
      className="rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">
          Market Breadth · {rows.length} groups
        </span>
        <span className="font-mono text-zenith-muted">
          coverage · situations · flow · macro · events
        </span>
      </header>
      <div className="flex flex-wrap gap-x-3 gap-y-1 px-3 py-1.5 text-[11px] leading-5 text-white/82">
        {rows.map((row, idx) => (
          <span
            key={`${row.label}-${idx}`}
            className="flex items-center gap-1.5"
            title={row.detail ?? ''}
          >
            <span className="font-mono uppercase tracking-[0.12em] text-zenith-soft">
              {row.label}
            </span>
            <span className="font-mono tabular-nums text-white/82">{row.primary}</span>
            {row.detail && (
              <span className="font-mono text-[10px] text-zenith-muted">{row.detail}</span>
            )}
            <StatusPill tone={row.tone}>{row.count == null ? '—' : '✓'}</StatusPill>
          </span>
        ))}
      </div>
    </section>
  );
}

function CoverageHealth({ rows }: { rows: CoverageRow[] }) {
  if (rows.length === 0) {
    // Render honest empty state instead of nothing. Operator atomicity fix
    // 2026-05-14: during an active FEEDS refresh, latest_quant_presentation_mart
    // may have zero coverage rows; the cockpit still has a valid read model
    // (via last-good fallback), so render the lane bar with an empty message
    // rather than disappearing.
    return (
      <section className="rounded-[10px] border border-zenith-edge-faint bg-black/30 px-3 py-1.5 text-[11px] leading-5 text-zenith-soft">
        <span className="font-mono text-white/82">Data Health</span> · no coverage
        rows in the current presentation mart (refresh likely in progress).
      </section>
    );
  }
  return (
    <section
      data-zenith-cockpit-coverage-matrix="ready"
      className="rounded-[10px] border border-zenith-edge-faint bg-black/30"
    >
      <header className="flex items-center justify-between border-b border-zenith-edge-soft px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
        <span className="font-mono text-white/82">Data Health · {rows.length} lanes</span>
        <span className="font-mono text-zenith-muted">rows · fetch % · status</span>
      </header>
      <div className="flex flex-wrap gap-x-4 gap-y-1 px-3 py-1.5 font-mono text-[11px] leading-5 text-white/72">
        {rows.map((row) => {
          const empty = row.rows === 0;
          const drifting = (row.drifts.length ?? 0) > 0;
          const tone: 'ok' | 'warn' | 'block' | 'neutral' = empty
            ? 'block'
            : drifting
              ? 'warn'
              : 'ok';
          const status =
            row.feedId === 'global_news_feed' && empty
              ? 'no rows · fetch unknown'
              : empty
                ? `empty · ${row.emptyReason ?? 'zero rows'}`
                : drifting
                  ? `drift · ${row.drifts.join(', ')}`
                  : 'working';
          const fetchLabel =
            row.fetchSuccessRate == null
              ? null
              : `${(row.fetchSuccessRate * 100).toFixed(1)}%`;
          return (
            <span
              key={row.feedId}
              className="flex items-center gap-1.5"
              title={row.feedId}
            >
              <span className="text-white/82">{row.label}</span>
              <span className="tabular-nums text-white/82">{row.rows ?? '—'}</span>
              {fetchLabel && <span className="text-zenith-muted">{fetchLabel}</span>}
              <StatusPill tone={tone}>{status}</StatusPill>
            </span>
          );
        })}
      </div>
    </section>
  );
}

function SituationExplainer({
  readModel,
  selectedId,
  selectionSource,
  selectionReason,
  rankedById,
}: {
  readModel: MarketDashboardReadModel | null;
  selectedId: string | null;
  selectionSource: MarketSelectionDisplaySource;
  selectionReason: string | null;
  rankedById: Map<string, RankedObs>;
}) {
  const detailIndex = asRecord(readModel?.situation_detail_index);
  const detail = selectedId ? asRecord(detailIndex?.[selectedId]) : null;
  const card = asRecord(detail?.card);

  if (!selectedId) {
    return (
      <section className="shrink-0 rounded-[10px] border border-zenith-edge-faint bg-black/30 p-3 text-[12px] leading-5 text-zenith-soft">
        Select a situation row to inspect what it means, why it surfaced, the
        key numbers, and what would change the state.
      </section>
    );
  }
  if (!detail || !card) {
    return (
      <section className="shrink-0 rounded-[10px] border border-zenith-edge-faint bg-black/30 p-3 text-[12px] leading-5 text-zenith-soft">
        No detail projected for situation <span className="font-mono">{selectedId}</span>.
      </section>
    );
  }

  const title = asString(card.title) ?? selectedId;
  const horizon = asString(card.horizon);
  const claimLevel = asString(card.claim_level);
  const displayState = asString(card.display_state);
  const safeUseLevel = asString(card.safe_use_level);
  const primaryEntitiesRaw = Array.isArray(card.primary_entities)
    ? card.primary_entities.filter((v): v is string => typeof v === 'string')
    : [];
  const primaryEntities = primaryEntitiesRaw.map(normalizeEntity);

  // Match the situation to a ranked observation by primary entity to pull
  // why_interesting + caveats + disconfirming as the "What this means" copy.
  const matchedRanked = primaryEntities
    .map((e) =>
      Array.from(rankedById.values()).find((r) =>
        r.entities.some((re) => re.raw === e.raw),
      ),
    )
    .find((row): row is RankedObs => row !== null && row !== undefined);

  const evidenceEdges = asArrayOfRecords(detail.evidence_edges);
  const counterEdges = asArrayOfRecords(detail.counterevidence_edges);

  const regimeContext = asRecord(detail.regime_context);
  const riskContext = asRecord(detail.risk_context);
  const relatedSituations = asArrayOfRecords(detail.related_situations);

  const statusSentence =
    claimLevel === 'validated_signal'
      ? 'Status: validated by backend.'
      : claimLevel === 'data_quality_warning'
        ? 'Status: data-quality warning — lane needs data to load before becoming actionable.'
        : claimLevel === 'data_fact'
          ? 'Status: data fact pulled from feeds.'
          : 'Status: observation only — needs external confirmation before promotion.';

  // Render numeric metric rows from evidence_edges' metric field.
  const numericMetrics: Array<{ label: string; value: string }> = [];
  if (matchedRanked?.primaryMetricName && matchedRanked.primaryMetricValue != null) {
    const isUsd = /flow|volume|usd|value/.test(matchedRanked.primaryMetricName);
    numericMetrics.push({
      label: matchedRanked.primaryMetricName.replace(/_/g, ' '),
      value: isUsd
        ? fmtUsdCompact(matchedRanked.primaryMetricValue)
        : matchedRanked.primaryMetricValue.toFixed(2),
    });
  }
  for (const edge of evidenceEdges) {
    const metric = asRecord(edge.metric);
    if (!metric) continue;
    for (const [k, v] of Object.entries(metric)) {
      if (typeof v !== 'number' || !Number.isFinite(v)) continue;
      if (numericMetrics.length >= 6) break;
      const isUsd = /flow|volume|usd|value/.test(k);
      const isPct = /pct|rate|ratio|probability/.test(k);
      numericMetrics.push({
        label: k.replace(/_/g, ' '),
        value: isUsd
          ? fmtUsdCompact(v)
          : isPct
            ? v.toFixed(3)
            : Math.abs(v) >= 1000
              ? v.toLocaleString()
              : v.toFixed(2),
      });
    }
  }
  if (matchedRanked?.reasons) {
    for (const reason of matchedRanked.reasons) {
      const eqIdx = reason.indexOf('=');
      if (eqIdx <= 0) continue;
      if (numericMetrics.length >= 8) break;
      const k = reason.slice(0, eqIdx);
      const v = reason.slice(eqIdx + 1);
      if (numericMetrics.find((m) => m.label === k.replace(/_/g, ' '))) continue;
      numericMetrics.push({ label: k.replace(/_/g, ' '), value: v });
    }
  }

  return (
    <section
      data-zenith-cockpit-selected-situation={selectedId}
      className="flex max-h-[360px] shrink-0 flex-col gap-3 overflow-y-auto rounded-[10px] border border-emerald-300/20 bg-emerald-300/[0.03] p-3"
    >
      <header>
        <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
          Selected · {selectedId}
        </div>
        <div className="mt-1 text-[14px] leading-6 text-white">{title}</div>
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px] uppercase tracking-[0.12em] text-zenith-soft">
          {primaryEntities.slice(0, 3).map((e) => (
            <span key={e.raw} className="font-mono text-white/82" title={e.hint ?? e.raw}>
              {e.label}
            </span>
          ))}
          {horizon && <StatusPill tone="neutral">horizon · {horizon}</StatusPill>}
          {claimLevel && <StatusPill tone="neutral">{stateLabel(claimLevel)}</StatusPill>}
          {displayState && (
            <StatusPill tone={displayState === 'ready' ? 'ok' : 'warn'}>
              {stateLabel(displayState)}
            </StatusPill>
          )}
          {safeUseLevel && (
            <StatusPill tone="neutral">safe use · {stateLabel(safeUseLevel)}</StatusPill>
          )}
        </div>
        {selectionReason && selectionSource === 'url_fallback' && (
          <div className="mt-2 text-[11px] leading-5 text-amber-100/85">{selectionReason}</div>
        )}
      </header>

      <div className="rounded-[10px] border border-zenith-edge-soft bg-black/30 px-2.5 py-1.5 text-[11px] leading-5 text-white/82">
        {statusSentence}
      </div>

      <div className="grid gap-2 lg:grid-cols-2">
        <div className="rounded-[10px] border border-zenith-edge-soft bg-black/25 p-2.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
            What this means
          </div>
          <div className="mt-1 text-[11px] leading-5 text-white/82">
            {matchedRanked?.whyInteresting ?? title}
          </div>
          {matchedRanked?.caveats && matchedRanked.caveats.length > 0 && (
            <ul className="mt-1 grid gap-0.5 text-[10px] leading-5 text-amber-200/75">
              {matchedRanked.caveats.slice(0, 2).map((c, i) => (
                <li key={`c-${i}`}>· {c}</li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-[10px] border border-zenith-edge-soft bg-black/25 p-2.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
            Why it surfaced
          </div>
          {evidenceEdges.length === 0 ? (
            <div className="mt-1 text-[11px] text-zenith-muted">no evidence edges projected</div>
          ) : (
            <ul className="mt-1 grid gap-0.5 text-[11px] leading-5 text-white/82">
              {evidenceEdges.slice(0, 3).map((edge, idx) => {
                const code = asString(edge.reason_code);
                const weight = asNumber(edge.weight);
                return (
                  <li key={`e-${idx}`} className="flex items-center gap-2">
                    <span className="flex-1 truncate">· {translateReasonCode(code)}</span>
                    {weight != null && (
                      <Microbar magnitude={weight} tone="pos" width={42} />
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      <div className="rounded-[10px] border border-zenith-edge-soft bg-black/25 p-2.5">
        <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
          Key numbers
        </div>
        {numericMetrics.length === 0 ? (
          <div className="mt-1 text-[11px] text-zenith-muted">no numeric metrics in this situation</div>
        ) : (
          <ul className="mt-1 grid grid-cols-2 gap-1 text-[11px] leading-5 text-white/82">
            {numericMetrics.slice(0, 8).map((m, i) => (
              <li key={`m-${i}`} className="flex items-center justify-between gap-2">
                <span className="truncate text-[10px] uppercase tracking-[0.10em] text-zenith-soft">
                  {m.label}
                </span>
                <span className="font-mono tabular-nums text-white/82">{m.value}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-[10px] border border-zenith-edge-soft bg-black/25 p-2.5">
        <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/75">
          What would change the state
        </div>
        {matchedRanked?.disconfirming && matchedRanked.disconfirming.length > 0 ? (
          <ul className="mt-1 grid gap-0.5 text-[11px] leading-5 text-white/82">
            {matchedRanked.disconfirming.slice(0, 4).map((d, i) => (
              <li key={`d-${i}`}>· {d}</li>
            ))}
          </ul>
        ) : counterEdges.length > 0 ? (
          <ul className="mt-1 grid gap-0.5 text-[11px] leading-5 text-white/82">
            {counterEdges.slice(0, 3).map((edge, idx) => {
              const code = asString(edge.reason_code);
              return <li key={`ce-${idx}`}>· {translateReasonCode(code)}</li>;
            })}
          </ul>
        ) : (
          <div className="mt-1 text-[11px] text-zenith-muted">
            promotion requires external validation refs to land
          </div>
        )}
      </div>

      {(regimeContext || riskContext || relatedSituations.length > 0) && (
        <div className="rounded-[10px] border border-zenith-edge-soft bg-black/25 p-2.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
            Related context
          </div>
          <ul className="mt-1 grid gap-0.5 text-[11px] leading-5 text-white/82">
            {regimeContext && asString(regimeContext.top_bucket) && (
              <li>
                · Regime bucket: <span className="font-mono text-white/82">{asString(regimeContext.top_bucket)}</span>
                {asNumber(regimeContext.average_z_score) != null && (
                  <span className="ml-1 text-zenith-soft">
                    (avg z {asNumber(regimeContext.average_z_score)!.toFixed(2)})
                  </span>
                )}
              </li>
            )}
            {riskContext && asString(riskContext.asset_class) && (
              <li>
                · Asset class: <span className="font-mono text-white/82">{asString(riskContext.asset_class)}</span>
              </li>
            )}
            {relatedSituations.slice(0, 3).map((s, i) => {
              const sId = asString(s.situation_id) ?? asString(s.id) ?? `r-${i}`;
              const sLabel = asString(s.title) ?? sId;
              return <li key={`rel-${i}`}>· {sLabel}</li>;
            })}
          </ul>
        </div>
      )}
    </section>
  );
}

function DiagnosticsDrawer({
  readModel,
}: {
  readModel: MarketDashboardReadModel | null;
}) {
  const [open, setOpen] = useState(false);
  const validationDebt = asRecord(readModel?.validation_debt);
  const blocked = asArrayOfRecords(validationDebt?.blocked_promotions);
  const provenance = asRecord(readModel?.provenance_index);
  const builders = asArrayOfRecords(provenance?.builders);
  const lineage = asArrayOfRecords(provenance?.lineage);
  const graph = asRecord(readModel?.graph_slice);
  const nodeCount = asArrayOfRecords(graph?.nodes).length;
  const edgeCount = asArrayOfRecords(graph?.edges).length;
  const drilldown = asRecord(readModel?.drilldown_index);
  const sourceRefs = asArrayOfRecords(drilldown?.source_refs);

  return (
    <section className="rounded-[10px] border border-zenith-edge-soft bg-black/25">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-[10px] uppercase tracking-[0.12em] text-zenith-muted hover:text-white/82"
      >
        <span className="font-mono">
          Diagnostics · audit / provenance / graph / validation debt
        </span>
        <span className="font-mono text-zenith-muted">
          {blocked.length} blocked · {builders.length}/{lineage.length} prov · {nodeCount}n/{edgeCount}e · {sourceRefs.length} refs · {open ? 'hide' : 'show'}
        </span>
      </button>
      {open && (
        <div className="grid gap-3 border-t border-zenith-edge-soft px-3 py-2 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-[8px] border border-zenith-edge-soft bg-black/25 p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
              Promotion gaps ({blocked.length})
            </div>
            {blocked.length === 0 ? (
              <div className="mt-1 text-[11px] text-zenith-muted">none</div>
            ) : (
              <ul className="mt-1 grid gap-0.5 text-[11px] text-white/72">
                {blocked.slice(0, 6).map((row, idx) => (
                  <li key={`b-${idx}`}>
                    · {asString(row.situation_id) ?? asString(row.id) ?? `entry ${idx + 1}`}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="rounded-[8px] border border-zenith-edge-soft bg-black/25 p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
              Provenance ({builders.length} builders · {lineage.length} steps)
            </div>
            <ul className="mt-1 grid gap-0.5 font-mono text-[10px] text-white/72">
              {builders.slice(0, 6).map((row, idx) => (
                <li key={`bld-${idx}`} className="truncate">
                  {asString(row.name) ?? asString(row.id) ?? `builder ${idx + 1}`}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-[8px] border border-zenith-edge-soft bg-black/25 p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
              Graph slice
            </div>
            <div className="mt-1 font-mono text-[11px] text-white/72">
              {nodeCount} nodes · {edgeCount} edges
            </div>
            <div className="mt-1 font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">
              graph mode disabled — typed edges not yet projected
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

// -------- selection logic + top-level -------------------------------------

function objectTokenIssue(objectToken: string | null | undefined): string | null {
  const token = typeof objectToken === 'string' ? objectToken.trim() : '';
  if (!token) return null;
  const separator = token.indexOf(':');
  if (separator <= 0 || separator === token.length - 1) {
    return `URL object token is malformed: ${token}`;
  }
  const kind = token.slice(0, separator);
  if (kind !== 'situation') {
    return `URL object ${kind} ignored; expected situation`;
  }
  return null;
}

export default function MarketCockpit({
  readModel,
  worldModelMarketFeeds,
  selectedSituationId = null,
  selectedRunId = null,
  latestRunId = null,
  objectToken = null,
  onSelectedSituationChange,
  onRunChange,
  pinnedLoading,
  pinnedError,
  activeRefreshRunId = null,
}: MarketCockpitProps) {
  const quantMart = asRecord(worldModelMarketFeeds?.latest_quant_presentation_mart);

  const ranked = useMemo(() => parseRankedObservations(quantMart), [quantMart]);
  const flow = useMemo(() => parseFlowBoard(quantMart), [quantMart]);
  const macro = useMemo(() => parseMacroBoard(quantMart), [quantMart]);
  const events = useMemo(() => parseEvents(quantMart), [quantMart]);
  const coverage = useMemo(() => parseCoverage(quantMart), [quantMart]);
  const situations = useMemo(() => parseSituationCards(readModel), [readModel]);
  // v0.8: backend-built interpretation slice. When present, the matrix +
  // market pulse + signal cards + data quality all come from here, and
  // FlowLeaderboard's signal-value watchlist is suppressed in favour of
  // the demoted data_quality summary.
  // v0.9: hmc now also carries visual_planes (typed planes), global_states
  // (lane-level constants raised out of cells), column_legends (so cell
  // labels don't repeat metric words), and applicability (so the matrix
  // can render non-applicable cells as faded, not silent black boxes).
  const hmc = useMemo(
    () => parseHumanMarketCockpit(worldModelMarketFeeds),
    [worldModelMarketFeeds],
  );
  const hmcHasSignalOnlyDemotion = useMemo(
    () => hmc?.dataQuality.some((d) => d.lane === 'stockgrid_signal_only') ?? false,
    [hmc],
  );
  const visualPlanesReady = (hmc?.visualPlanes?.length ?? 0) >= 3;
  const planeById = useMemo(() => {
    const m = new Map<string, HmcVisualPlane>();
    for (const p of hmc?.visualPlanes ?? []) m.set(p.id, p);
    return m;
  }, [hmc]);
  // v0.10: workspace readiness — plane_nav present with >= 5 planes and
  // at least one populated plane with row_count_total >= primaryPlaneMinRows.
  const workspaceReady = useMemo(() => {
    const ws = hmc?.workspace;
    if (!ws) return false;
    if (ws.planeNav.length < 5) return false;
    const min = ws.layoutContract.primaryPlaneMinRows ?? 25;
    return ws.planeNav.some((p) => p.status === 'ok' && p.rowCount >= min);
  }, [hmc]);
  // The previous shape stored an `activePlaneId` state and seeded its
  // initial value from `hmc.workspace.defaultPlaneId` inside a useEffect.
  // That tripped react-hooks/set-state-in-effect because the effect's
  // sole job was a synchronous setState cascade. Modeling the active
  // plane as `user override OR workspace default` removes the effect:
  // the user override is the only mutable state; the public alias is
  // derived from override + default, so the workspace-default kicks in
  // automatically as soon as `workspaceReady` flips.
  const [userActivePlaneId, setUserActivePlaneId] = useState<string | null>(null);
  const activePlaneId: string | null =
    userActivePlaneId ?? (workspaceReady ? hmc?.workspace?.defaultPlaneId ?? null : null);
  const setActivePlaneId = setUserActivePlaneId;
  const [activeRowKey, setActiveRowKey] = useState<string | null>(null);
  const [activeRowData, setActiveRowData] = useState<UnknownRecord | null>(null);
  // v0.10.3: lift active-plane columns so RowInspector can render the
  // selected row with proper labels/kinds without re-fetching.
  const [activeRowColumns, setActiveRowColumns] = useState<HmcDisplayColumn[]>([]);

  const rankedById = useMemo(() => {
    const m = new Map<string, RankedObs>();
    for (const r of ranked) m.set(r.id, r);
    return m;
  }, [ranked]);

  // Operator-named fix 2026-05-14: prefer drilldown-based mapping over
  // entity-overlap heuristic. situation_detail_index[sid].drilldown
  // .mart_observation_ids contains the explicit observation->situation
  // edges the backend already emits.
  const situationByObservationId = useMemo(() => {
    const m = new Map<string, string>();
    const index = asRecord(readModel?.situation_detail_index);
    if (!index) return m;
    for (const [sid, raw] of Object.entries(index)) {
      const detail = asRecord(raw);
      const drilldown = asRecord(detail?.drilldown);
      const obsIds = Array.isArray(drilldown?.mart_observation_ids)
        ? (drilldown!.mart_observation_ids as unknown[]).filter(
            (v): v is string => typeof v === 'string',
          )
        : [];
      for (const obsId of obsIds) {
        if (!m.has(obsId)) m.set(obsId, sid);
      }
    }
    return m;
  }, [readModel]);

  const [localSelectedId, setLocalSelectedId] = useState<string | null>(null);

  const selection = useMemo(() => {
    const tokenIssue = objectTokenIssue(objectToken);
    if (selectedSituationId && situations.some((row) => row.id === selectedSituationId)) {
      return {
        id: selectedSituationId,
        source: 'url' as const,
        reason: null as string | null,
      };
    }
    if (selectedSituationId && situations.length > 0) {
      return {
        id: situations[0].id,
        source: 'url_fallback' as const,
        reason: `URL requested situation:${selectedSituationId}, but that situation is not present in this run. Showing the top row.`,
      };
    }
    if (localSelectedId && situations.some((row) => row.id === localSelectedId)) {
      return {
        id: localSelectedId,
        source: 'local' as const,
        reason: null as string | null,
      };
    }
    if (situations.length > 0) {
      return {
        id: situations[0].id,
        source: tokenIssue ? ('url_fallback' as const) : ('default' as const),
        reason: tokenIssue,
      };
    }
    return {
      id: null,
      source: tokenIssue ? ('url_fallback' as const) : ('default' as const),
      reason: tokenIssue,
    };
  }, [objectToken, situations, localSelectedId, selectedSituationId]);

  // Propagate default/url_fallback selection back up to the page so the
  // URL stays object-addressable. v0.4 invariant, regressed in earlier
  // v0.6 attempt; restored 2026-05-14 per operator note.
  useEffect(() => {
    if (!selection.id) return;
    if (selection.source === 'default' || selection.source === 'url_fallback') {
      onSelectedSituationChange?.(selection.id, selection.source);
    }
  }, [onSelectedSituationChange, selection.id, selection.source]);

  // When a ranked observation is clicked, prefer the drilldown map. Fall
  // back to entity overlap and finally to raw id.
  const handleRankedSelect = (rankedId: string) => {
    const drillTarget = situationByObservationId.get(rankedId);
    if (drillTarget) {
      setLocalSelectedId(drillTarget);
      onSelectedSituationChange?.(drillTarget, 'click');
      return;
    }
    const obs = rankedById.get(rankedId);
    if (obs) {
      const match = situations.find((s) =>
        s.primaryEntities.some((e) => obs.entities.some((re) => re.raw === e.raw)),
      );
      if (match) {
        setLocalSelectedId(match.id);
        onSelectedSituationChange?.(match.id, 'click');
        return;
      }
    }
    setLocalSelectedId(rankedId);
    onSelectedSituationChange?.(rankedId, 'click');
  };

  // v0.8 render-gate semantics: lane-diagnostics-ready requires either
  //   a backend human_market_cockpit market_field with rows AND cells,
  //   OR (v0.6.1 fallback) at least one breadth substrate populated.
  const hmcReady = Boolean(hmc && hmc.rows.length > 0 && hmc.cells.length > 0);
  const hasBreadth =
    hmcReady ||
    ranked.length > 0 ||
    situations.length > 0 ||
    flow.length > 0 ||
    macro.length > 0 ||
    events.length > 0 ||
    coverage.length > 0;
  const useFallback = !hmcReady && ranked.length === 0 && situations.length > 0;
  const laneDiagnosticsReady = hasBreadth ? 'ready' : 'pending';
  const displayBundleReady = hasBreadth ? 'ready' : 'pending';

  // Handler used by matrix and signal-cards to drive selection. When a
  // backend-emitted card or matrix cell carries a linked situation_id,
  // route selection through onSelectedSituationChange so the explainer
  // panel and URL state update together (v0.4 invariant).
  const handleMatrixOrCardSelect = (
    rowId: string | null,
    situationIds: string[],
  ) => {
    const target = situationIds.find((s) => situations.some((c) => c.id === s));
    if (target) {
      setLocalSelectedId(target);
      onSelectedSituationChange?.(target, 'click');
      return;
    }
    if (rowId) {
      setLocalSelectedId(rowId);
      onSelectedSituationChange?.(rowId, 'click');
    }
  };

  return (
    <div
      data-zenith-market-cockpit="ready"
      data-zenith-market-cockpit-version="v0_10_3"
      // v0.8: gate also reflects "backend human_market_cockpit has a
      // non-empty market_field" — the dominant visual surface.
      data-zenith-intelligence-lane-diagnostics={laneDiagnosticsReady}
      data-zenith-market-display-bundle={displayBundleReady}
      data-zenith-market-cockpit-hmc={hmcReady ? 'ready' : 'absent'}
      data-zenith-market-cockpit-visual-planes={visualPlanesReady ? 'ready' : 'absent'}
      data-zenith-market-workspace={workspaceReady ? 'ready' : 'absent'}
      data-zenith-market-workspace-utilization={workspaceReady ? 'dense' : 'sparse'}
      className="flex min-h-full flex-col gap-2"
    >
      <StatusStrip
        readModel={readModel}
        marketFeeds={worldModelMarketFeeds}
        selectedRunId={selectedRunId}
        latestRunId={latestRunId}
        onRunChange={onRunChange}
        pinnedLoading={pinnedLoading}
        pinnedError={pinnedError}
        activeRefreshRunId={activeRefreshRunId}
      />
      <TickerTape marketFeeds={worldModelMarketFeeds} />
      {hmcReady && hmc ? (
        <MarketPulseStrip pulse={hmc.marketPulse} />
      ) : (
        <MarketBreadth
          coverage={coverage}
          situations={situations}
          flow={flow}
          macro={macro}
          events={events}
          ranked={ranked}
          readModel={readModel}
        />
      )}

      {hmcReady && hmc && workspaceReady && hmc.workspace ? (
        // v0.10 PRIMARY: market browse workspace fills the viewport.
        // Plane nav exposes all 6 universes; active plane renders dense
        // sortable rows; right rail carries explainer + signal cards.
        <div
          data-zenith-cockpit-stage="workspace"
          className="flex min-h-[520px] flex-col gap-2"
        >
          <PlaneNav
            workspace={hmc.workspace}
            activePlaneId={activePlaneId}
            onSelectPlane={(planeId) => {
              setActivePlaneId(planeId);
              setActiveRowKey(null);
              setActiveRowData(null);
              setActiveRowColumns([]);
            }}
          />
          <div className="grid min-h-0 flex-1 grid-cols-12 gap-2">
            <div
              data-zenith-cockpit-primary-column="workspace-table"
              className="col-span-12 flex min-h-0 flex-col gap-2 overflow-hidden lg:col-span-8"
            >
              {activePlaneId && (
                <MarketWorkspace
                  workspace={hmc.workspace}
                  activePlaneId={activePlaneId}
                  selectedRowKey={activeRowKey}
                  onSelectRow={(rowKey, entityId, row, columns) => {
                    // v0.10.3: row key is owned by the table (planeId +
                    // entityValue + idx). The parent just persists it
                    // so active-row styling matches what the table is
                    // keying off.
                    setActiveRowKey(rowKey);
                    setActiveRowData(row);
                    setActiveRowColumns(columns);
                    // Map plane entity to a situation if one shares it; else
                    // surface the raw entity id through the explainer.
                    const matched = situations.find((s) =>
                      s.primaryEntities.some((e) => e.label === entityId || e.raw.endsWith(`:${entityId}`)),
                    );
                    if (matched) {
                      setLocalSelectedId(matched.id);
                      onSelectedSituationChange?.(matched.id, 'click');
                    }
                  }}
                  // v0.10.1: bind to workspace.runId — the run the bundle is
                  // composed from. Falling back to selectedRunId/latestRunId
                  // pulled the in-flight FEEDS run id into the active-plane
                  // fetch and produced "Equity Universe · 0 rows" while
                  // plane_nav (from the bundle run) said 457.
                  runId={hmc.workspace.runId ?? null}
                />
              )}
            </div>
            <div
              data-zenith-cockpit-right-rail="row_inspector_first"
              className="col-span-12 flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-contain pr-1 lg:col-span-4"
            >
              {/*
                v0.10.3 right rail: RowInspector first. ARM / situation
                explainer is browsing context, not the primary object,
                so it demotes to a secondary panel unless the selected
                row maps to a situation (then it is the linked panel).
              */}
              <RowInspector
                planeId={activePlaneId}
                columns={activeRowColumns}
                row={activeRowData}
              />
              <SituationExplainer
                readModel={readModel}
                selectedId={selection.id}
                selectionSource={selection.source}
                selectionReason={selection.reason}
                rankedById={rankedById}
              />
              <SignalCardsStack
                cards={hmc.signalCards}
                onSelectRow={handleMatrixOrCardSelect}
              />
            </div>
          </div>
        </div>
      ) : hmcReady && hmc && visualPlanesReady ? (
        // v0.9 PRIMARY: typed visual planes are the dominant surface.
        // Universal matrix is demoted to a collapsible diagnostics drawer
        // at the bottom (rendered after CoverageHealth).
        <div
          data-zenith-cockpit-stage="visual-planes"
          className="grid min-h-[520px] grid-cols-12 gap-2"
        >
          <div className="col-span-12 flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-contain pr-1 lg:col-span-8">
            {planeById.get('equity_flow_plane') && (
              <EquityFlowPlane
                plane={planeById.get('equity_flow_plane')!}
                onSelectRow={handleMatrixOrCardSelect}
              />
            )}
            {planeById.get('macro_pressure_plane') && (
              <MacroPressurePlane
                plane={planeById.get('macro_pressure_plane')!}
                onSelectRow={handleMatrixOrCardSelect}
              />
            )}
            {planeById.get('event_liquidity_plane') && (
              <EventLiquidityPlane
                plane={planeById.get('event_liquidity_plane')!}
                onSelectRow={handleMatrixOrCardSelect}
              />
            )}
          </div>
          <div className="col-span-12 flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-contain pr-1 lg:col-span-4">
            <SituationExplainer
              readModel={readModel}
              selectedId={selection.id}
              selectionSource={selection.source}
              selectionReason={selection.reason}
              rankedById={rankedById}
            />
            <SignalCardsStack
              cards={hmc.signalCards}
              onSelectRow={handleMatrixOrCardSelect}
            />
          </div>
        </div>
      ) : hmcReady && hmc ? (
        // v0.8 fallback: matrix + side panels when visual_planes have not
        // attached yet.
        <div
          data-zenith-cockpit-stage="matrix-fallback"
          className="grid min-h-[520px] grid-cols-12 gap-2"
        >
          <div className="col-span-12 flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-contain pr-1 lg:col-span-8">
            <MarketInsightMatrix
              hmc={hmc}
              selectedRowId={localSelectedId}
              onSelectRow={handleMatrixOrCardSelect}
            />
            <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
              <FlowLeaderboard rows={flow} suppressSignalOnly={hmcHasSignalOnlyDemotion} />
              <MacroPressureStrips rows={macro} />
            </div>
            <EventWatchlist rows={events} />
          </div>
          <div className="col-span-12 flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-contain pr-1 lg:col-span-4">
            <SituationExplainer
              readModel={readModel}
              selectedId={selection.id}
              selectionSource={selection.source}
              selectionReason={selection.reason}
              rankedById={rankedById}
            />
            <SignalCardsStack
              cards={hmc.signalCards}
              onSelectRow={handleMatrixOrCardSelect}
            />
          </div>
        </div>
      ) : (
        <div
          data-zenith-cockpit-stage="legacy-fallback"
          className="grid min-h-[420px] grid-cols-12 gap-2"
        >
          <div className="col-span-12 flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-contain pr-1 lg:col-span-5">
            {useFallback ? (
              <SituationSignalFallback
                situations={situations}
                readModel={readModel}
                onSelect={(id) => {
                  setLocalSelectedId(id);
                  onSelectedSituationChange?.(id, 'click');
                }}
              />
            ) : (
              <SignalTape rows={ranked} onSelect={handleRankedSelect} />
            )}
          </div>
          <div className="col-span-12 flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-contain pr-1 lg:col-span-4">
            <FlowLeaderboard rows={flow} />
            <MacroPressureStrips rows={macro} />
            <EventWatchlist rows={events} />
          </div>
          <div className="col-span-12 flex min-h-0 flex-col gap-2 overflow-y-auto overscroll-contain pr-1 lg:col-span-3">
            <SituationExplainer
              readModel={readModel}
              selectedId={selection.id}
              selectionSource={selection.source}
              selectionReason={selection.reason}
              rankedById={rankedById}
            />
          </div>
        </div>
      )}

      <CoverageHealth rows={coverage} />
      {visualPlanesReady && hmc && planeById.get('data_quality_plane') ? (
        // v0.9: DataQualityPlane handles signal-only + global states.
        <DataQualityPlane
          plane={planeById.get('data_quality_plane')!}
          globalStates={hmc.globalStates}
        />
      ) : (
        hmcReady && hmc && <DataQualityStrip rows={hmc.dataQuality} />
      )}
      <DiagnosticsDrawer readModel={readModel} />
      {visualPlanesReady && hmc && (
        // v0.9: universal MarketInsightMatrix demoted to a diagnostics
        // surface below the drawer. It is still useful when an operator
        // wants to inspect cross-lane cells, but it is no longer the
        // primary visual.
        <details className="rounded-[10px] border border-zenith-edge-soft bg-black/20 px-3 py-2">
          <summary className="cursor-pointer text-[10px] uppercase tracking-[0.14em] text-zenith-muted hover:text-white/82">
            Diagnostics · universal market field (matrix)
          </summary>
          <div className="mt-2">
            <MarketInsightMatrix
              hmc={hmc}
              selectedRowId={localSelectedId}
              onSelectRow={handleMatrixOrCardSelect}
            />
          </div>
        </details>
      )}
    </div>
  );
}
