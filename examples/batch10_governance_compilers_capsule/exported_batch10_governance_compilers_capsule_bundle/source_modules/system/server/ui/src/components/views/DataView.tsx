/* eslint-disable react-refresh/only-export-components */
import { useEffect, useMemo, useReducer, useState } from 'react';
import {
  Activity,
  Database,
  type LucideIcon,
  Loader2,
  Newspaper,
  Sigma,
  TrendingUp,
} from 'lucide-react';
import { Lane, api, type TemporalContext } from '../../api';
import ArtifactViewer from '../ArtifactViewer';
import { useZenith } from '../../stores/useZenith';
import {
  asRecord,
  asArray,
  buildRowsFromMatrix,
  buildRowsFromObjectList,
  collectColumns,
  normalizeDatasetKey,
  buildCalculatorRows,
} from './dataViewUtils';
import { resolveAdapter } from './adapters/registry';
import type { ValueFormatHint, SummaryKpi } from './adapters/types';
import { viewReducer, initialViewState } from './ViewState';
import LaneCard from './LaneCard';
import DatasetCard, { MetadataPanel, SchemaPanel } from './DatasetCard';
import TableView from './TableView';
import NewsFeedView from './NewsFeedView';
import PredictionMarketView from './PredictionMarketView';
import ConfigStrip from './ConfigStrip';
import { loadFeedArtifacts, type FeedArtifactEnvelope } from '../../lib/financeArtifacts';
import type { FamilySummary } from '../../lib/financePresentation';
import clsx from 'clsx';

type DataRunSource = 'history' | 'latest-green' | 'latest' | 'none';

interface DataViewProps {
  missionName: string;
  displayRunId: string | null;
  runSource: DataRunSource;
  historyMode: boolean;
  temporalContext?: TemporalContext | null;
  visible?: boolean;
  suppressIdentity?: boolean;
  showToolbar?: boolean;
  showEmptyLanes?: boolean;
  searchQuery?: string;
  onSearchQueryChange?: (query: string) => void;
  laneSummaries?: Partial<Record<Lane, FamilySummary>>;
  /**
   * Optional lane allow-list. When provided, only lanes in this list render.
   * Used by the Finance Data Hub family-chip filter. When undefined (default),
   * all lanes in LANE_ORDER render as before.
   */
  visibleLanes?: Lane[];
}

interface ToolDataset {
  id: string;
  nodeId: string;
  lane: Lane;
  title: string;
  displayTitle?: string;
  displaySubtitle?: string | null;
  columns: string[];
  rows: Array<Record<string, unknown>>;
  timestamp: number | null;
  metadata: Record<string, unknown> | null;
  // adapter-provided hints — undefined in legacy path, populated in adapterV2 path
  defaultSort?: { column: string; direction: 'asc' | 'desc' };
  defaultColumns?: string[];
  valueFormatHints?: Record<string, ValueFormatHint>;
  summaryKpis?: SummaryKpi[];
}

type SortDirection = 'desc' | 'asc';

const LANE_ORDER: Lane[] = [
  Lane.SPINE,
  Lane.STOCK,
  Lane.ETF,
  Lane.STOCKGRID,
  Lane.MACRO,
  Lane.NEWS,
  Lane.POLYMARKET,
  Lane.CALCULATOR,
];

const LANE_LABEL: Record<Lane, string> = {
  [Lane.STOCK]: 'Stock',
  [Lane.ETF]: 'ETF',
  [Lane.STOCKGRID]: 'Stockgrid',
  [Lane.MACRO]: 'Macro',
  [Lane.NEWS]: 'News',
  [Lane.POLYMARKET]: 'Polymarket',
  [Lane.CALCULATOR]: 'Calculator',
  [Lane.SPINE]: 'Oracle',
};

const LANE_ACCENT: Record<Lane, string> = {
  [Lane.STOCK]: 'text-emerald-400',
  [Lane.ETF]: 'text-teal-400',
  [Lane.STOCKGRID]: 'text-cyan-400',
  [Lane.MACRO]: 'text-blue-400',
  [Lane.NEWS]: 'text-orange-400',
  [Lane.POLYMARKET]: 'text-fuchsia-400',
  [Lane.CALCULATOR]: 'text-amber-400',
  [Lane.SPINE]: 'text-neutral-400',
};

const LANE_ICON: Record<Lane, LucideIcon> = {
  [Lane.STOCK]: TrendingUp,
  [Lane.ETF]: Database,
  [Lane.STOCKGRID]: TrendingUp,
  [Lane.MACRO]: Database,
  [Lane.NEWS]: Newspaper,
  [Lane.POLYMARKET]: Sigma,
  [Lane.CALCULATOR]: Sigma,
  [Lane.SPINE]: Activity,
};

const ARTIFACT_FALLBACK_NODES: Array<{ nodeId: string; lane: Lane; label: string }> = [
  { nodeId: 'global_stock_feed', lane: Lane.STOCK, label: 'Stock feed artifact' },
  { nodeId: 'global_etf_feed', lane: Lane.ETF, label: 'ETF feed artifact' },
  { nodeId: 'global_stockgrid_feed', lane: Lane.STOCKGRID, label: 'Stockgrid artifact' },
  { nodeId: 'global_macro_feed', lane: Lane.MACRO, label: 'Macro feed artifact' },
  { nodeId: 'global_news_feed', lane: Lane.NEWS, label: 'News feed artifact' },
  { nodeId: 'global_polymarket_feed', lane: Lane.POLYMARKET, label: 'Polymarket feed artifact' },
  { nodeId: 'global_calculator_feed', lane: Lane.CALCULATOR, label: 'Calculator feed artifact' },
];

const TICKER_MAP_REF_PATH = 'codex/refs/stockgrid_ticker_map.json';
const DEFAULT_ROW_LIMIT = 50;
const DEFAULT_STALE_AFTER_DAYS = 1;
const DEFAULT_TEXT_CLAMP_LINES = 3;
const DEFAULT_TEXT_CLAMP_MIN_CHARS = 100;
const DEFAULT_MAX_TABLE_HEIGHT_PX = 420;
const DEFAULT_AUTO_COLLAPSE_MULTI_DATASET = true;
const LIVE_HOLOGRAM_RETRY_ATTEMPTS = 6;
const LIVE_HOLOGRAM_RETRY_DELAY_MS = 350;

const DEFAULT_COLUMN_ALIASES: Record<string, string> = {
  tkr: 'Ticker',
  sec: 'Sector',
  flow: 'Flow',
  sv: 'Short Vol %',
  wr: 'Win Rate %',
  flg: 'Flags',
  q: 'Question',
  o: 'Outcome',
  p: 'Probability',
  c: '24h Δ',
  v: '24h Volume',
  s: 'Conviction',
  slug: 'Market ID',
  identity: 'Identity',
  vol_20d: '20D Vol',
  chg_5d: '5D Δ',
  chg_63d: '63D Δ',
  z_short: '20D Z',
  z_long: '63D Z',
  source_label: 'Source',
  source_handle: 'Handle',
  time: 'Time',
};

// asRecord and asArray imported from dataViewUtils

function asPositiveInt(value: unknown, fallback: number): number {
  const parsed = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return Math.floor(parsed);
}

function asBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (normalized === 'true') return true;
    if (normalized === 'false') return false;
  }
  return fallback;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function normalizeColumnAliases(value: unknown): Record<string, string> {
  const raw = asRecord(value);
  if (!raw) return {};

  const aliases: Record<string, string> = {};
  Object.entries(raw).forEach(([column, alias]) => {
    if (typeof alias !== 'string') return;
    const normalizedColumn = column.trim().toLowerCase();
    const normalizedAlias = alias.trim();
    if (!normalizedColumn || !normalizedAlias) return;
    aliases[normalizedColumn] = normalizedAlias;
  });
  return aliases;
}

function normalizeLane(value: unknown): Lane {
  if (typeof value !== 'string') return Lane.SPINE;
  const candidate = value.toUpperCase();
  return (Object.values(Lane) as string[]).includes(candidate)
    ? (candidate as Lane)
    : Lane.SPINE;
}

function titleCase(value: string): string {
  return value
    .split(/[_/]+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');
}

function humanizeDatasetTitle(dataset: ToolDataset): {
  displayTitle: string;
  displaySubtitle: string | null;
} {
  const suffix = dataset.title.includes('/') ? dataset.title.split('/').slice(1).join('/').trim() : null;
  const normalizedSuffix = suffix?.toLowerCase() ?? null;
  const suffixLabel =
    normalizedSuffix && normalizedSuffix !== 'main' && normalizedSuffix !== 'items'
      ? titleCase(normalizedSuffix)
      : null;

  const byNodeId: Record<string, string> = {
    global_stock_feed: 'Equity Monitor',
    global_etf_feed: 'ETF Monitor',
    global_stockgrid_feed: 'Flow Monitor',
    global_macro_feed: 'Macro Monitor',
    global_news_feed: 'News Context',
    global_polymarket_feed: 'Prediction Repricing',
    global_calculator_feed: 'Derived Signals',
  };

  const base = byNodeId[dataset.nodeId] ?? titleCase(dataset.nodeId.replace(/^global_/, '').replace(/_feed$/, ''));
  return {
    displayTitle: suffixLabel ? `${base} · ${suffixLabel}` : base,
    displaySubtitle: dataset.nodeId,
  };
}

function enhanceLegacyDataset(dataset: ToolDataset): ToolDataset {
  const title = humanizeDatasetTitle(dataset);
  if (dataset.defaultSort || dataset.defaultColumns || dataset.valueFormatHints) {
    return {
      ...dataset,
      displayTitle: dataset.displayTitle ?? title.displayTitle,
      displaySubtitle: dataset.displaySubtitle ?? title.displaySubtitle,
    };
  }

  const hints: ToolDataset['valueFormatHints'] = {};
  let defaultColumns = dataset.columns;
  let defaultSort: ToolDataset['defaultSort'] = dataset.defaultSort;

  if (dataset.lane === Lane.STOCK || dataset.lane === Lane.ETF) {
    defaultSort = { column: 'Z_Short', direction: 'desc' };
    defaultColumns = ['Ticker', 'Identity', 'Price', 'Chg_5d', 'Z_Short'];
    hints.Z_Short = { type: 'z_score' };
    hints.Z_Long = { type: 'z_score' };
    hints.Chg_5d = { type: 'delta_percent' };
    hints.Chg_63d = { type: 'delta_percent' };
    hints.Price = { type: 'currency', decimals: 2 };
  } else if (dataset.lane === Lane.STOCKGRID) {
    defaultSort = { column: 'flow', direction: 'desc' };
    defaultColumns = ['tkr', 'sec', 'flow', 'sv', 'wr', 'flg'];
    hints.flow = { type: 'compact_currency' };
    hints.sv = { type: 'percent', decimals: 0 };
    hints.wr = { type: 'percent', decimals: 0 };
  } else if (dataset.lane === Lane.MACRO) {
    defaultSort = { column: 'z_score', direction: 'desc' };
    defaultColumns = ['ticker', 'Proxy', 'pct_change', 'z_score'];
    hints.pct_change = { type: 'delta_percent' };
    hints.z_score = { type: 'z_score' };
    hints.z = { type: 'z_score' };
  } else if (dataset.lane === Lane.NEWS) {
    defaultSort = { column: 'time', direction: 'desc' };
    defaultColumns = ['time', 'source_label', 'text', 'url'];
    hints.time = { type: 'datetime', precision: 'time' };
    hints.text = { type: 'text_truncate', maxChars: 220 };
    hints.url = { type: 'text_truncate', maxChars: 60 };
  } else if (dataset.lane === Lane.POLYMARKET) {
    defaultSort = { column: 'c', direction: 'desc' };
    defaultColumns = ['q', 'p', 'c', 'v', 's'];
    hints.p = { type: 'probability' };
    hints.c = { type: 'probability_delta' };
    hints.v = { type: 'compact_currency' };
    hints.s = { type: 'compact_number', decimals: 2 };
  } else if (dataset.lane === Lane.CALCULATOR) {
    defaultColumns = ['Cluster', 'Opportunity Score', 'Energy', 'Polarity', 'Dominant_Signal', 'Signal Quality', 'Size'];
    defaultSort = { column: 'Opportunity Score', direction: 'desc' };
    hints['Opportunity Score'] = { type: 'compact_number', decimals: 2 };
    hints.Energy = { type: 'compact_number', decimals: 2 };
    hints.Polarity = { type: 'compact_number', decimals: 2 };
    hints['Signal Quality'] = { type: 'pct_ratio' };
    hints.Size = { type: 'integer' };
  }

  return {
    ...dataset,
    defaultSort,
    defaultColumns,
    valueFormatHints: hints,
    displayTitle: title.displayTitle,
    displaySubtitle: title.displaySubtitle,
  };
}

// buildRowsFromMatrix, buildRowsFromObjectList, collectColumns imported from dataViewUtils

function getMetadataIdentityMap(datasets: ToolDataset[]): Record<string, string> {
  const out: Record<string, string> = {};
  datasets.forEach((dataset) => {
    const identityMap = asRecord(dataset.metadata?.identity_map);
    if (!identityMap) return;
    Object.entries(identityMap).forEach(([ticker, identity]) => {
      if (typeof identity !== 'string') return;
      const normalizedTicker = ticker.trim().toUpperCase();
      if (!normalizedTicker) return;
      out[normalizedTicker] = identity.trim();
    });
  });
  return out;
}

function normalizeComparableValue(value: unknown): number | string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'boolean') return value ? 1 : 0;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const numeric = Number(trimmed);
    if (!Number.isNaN(numeric) && /^-?\d+(\.\d+)?$/.test(trimmed)) return numeric;
    return trimmed.toLowerCase();
  }
  if (Array.isArray(value)) return value.map((item) => String(item)).join('|').toLowerCase();
  return JSON.stringify(value).toLowerCase();
}

function getCaseInsensitive(record: Record<string, unknown>, key: string): unknown {
  if (key in record) return record[key];
  const resolvedKey = Object.keys(record).find(
    (candidate) => candidate.toLowerCase() === key.toLowerCase(),
  );
  return resolvedKey ? record[resolvedKey] : undefined;
}

function getColumnDefinition(
  metadata: Record<string, unknown> | null,
  column: string,
): Record<string, unknown> | null {
  const definitions = asRecord(metadata?.definitions);
  if (!definitions) return null;
  return asRecord(getCaseInsensitive(definitions, column));
}

function resolveSortValue(
  value: unknown,
  column: string,
  metadata: Record<string, unknown> | null,
): number | string | null {
  const normalizedColumn = column.toLowerCase();
  if (normalizedColumn === 'sec') {
    const definition = getColumnDefinition(metadata, column);
    const encoding =
      typeof definition?.encoding === 'string' ? definition.encoding.toLowerCase() : '';
    const sectorMap = asRecord(metadata?.sector_map);
    const secValue = typeof value === 'number' ? value : Number(value);
    if (encoding === 'integer_enum' && sectorMap && Number.isFinite(secValue)) {
      const matched = Object.entries(sectorMap).find(([, idRaw]) => Number(idRaw) === secValue);
      if (matched) return matched[0].toLowerCase();
    }
  }
  return normalizeComparableValue(value);
}

function compareByColumn(
  left: unknown,
  right: unknown,
  column: string,
  metadata: Record<string, unknown> | null,
  direction: SortDirection,
): number {
  const leftValue = resolveSortValue(left, column, metadata);
  const rightValue = resolveSortValue(right, column, metadata);

  if (leftValue === null && rightValue === null) return 0;
  if (leftValue === null) return 1;
  if (rightValue === null) return -1;

  let result = 0;
  if (typeof leftValue === 'number' && typeof rightValue === 'number') {
    result = leftValue - rightValue;
  } else {
    result = String(leftValue).localeCompare(String(rightValue), undefined, {
      numeric: true,
      sensitivity: 'base',
    });
  }
  return direction === 'asc' ? result : -result;
}

function parsePeriodMonths(periodRaw: unknown): number | null {
  if (typeof periodRaw !== 'string') return null;
  const period = periodRaw.trim().toLowerCase();
  if (!period) return null;
  if (period === 'max') return 999;

  const monthMatch = period.match(/^(\d+)\s*mo$/);
  if (monthMatch) return Number(monthMatch[1]);
  const yearMatch = period.match(/^(\d+)\s*y$/);
  if (yearMatch) return Number(yearMatch[1]) * 12;
  return null;
}

function getDatasetQualityNotes(dataset: ToolDataset): string[] {
  const notes: string[] = [];
  const diagnostics = asRecord(dataset.metadata?.diagnostics);
  if (!diagnostics) return notes;

  const period = diagnostics.period;
  const months = parsePeriodMonths(period);
  if (months !== null && months < 6) {
    notes.push(`Diagnostic period is ${String(period)}; long-horizon metrics may be sparse.`);
  }

  const joinHitRateRaw = diagnostics.join_hit_rate;
  if (
    typeof joinHitRateRaw === 'number' &&
    Number.isFinite(joinHitRateRaw) &&
    joinHitRateRaw < 0.8
  ) {
    notes.push(
      `Join hit-rate is ${(joinHitRateRaw * 100).toFixed(1)}%; coverage is degraded.`,
    );
  }

  const unmatchedSample = asArray(diagnostics.unmatched_tickers_sample);
  if (unmatchedSample.length > 0) {
    notes.push(
      `Unmatched tickers sample: ${unmatchedSample
        .slice(0, 5)
        .map((item) => String(item))
        .join(', ')}`,
    );
  }

  return notes;
}

// normalizeDatasetKey imported from dataViewUtils

function normalizePolymarketRows(dataRecord: Record<string, unknown>): Array<{
  title: string;
  rows: Array<Record<string, unknown>>;
}> {
  const datasets: Array<{ title: string; rows: Array<Record<string, unknown>> }> = [];

  Object.entries(dataRecord).forEach(([category, bucketRaw]) => {
    const bucket = asRecord(bucketRaw);
    if (!bucket) return;

    Object.entries(bucket).forEach(([sectionName, sectionRaw]) => {
      const section = asRecord(sectionRaw);
      if (!section) return;
      const rows = buildRowsFromMatrix(section.columns, section.rows);
      if (rows.length === 0) return;
      datasets.push({
        title: `${category} / ${sectionName}`,
        rows,
      });
    });
  });

  return datasets;
}

function formatTemporalLabel(value: string | null | undefined): string {
  if (!value) return 'unknown';
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  return new Date(parsed).toLocaleString();
}

export function parseToolDatasets(
  runId: string,
  runHologram: unknown,
  toolRuns: Record<string, unknown>,
  options?: { adapterV2?: boolean },
): ToolDataset[] {
  const result: ToolDataset[] = [];
  const hologram = asRecord(runHologram);
  const nodes = asArray(hologram?.nodes);
  const adapterV2 = options?.adapterV2 === true;

  nodes.forEach((nodeRaw) => {
    const node = asRecord(nodeRaw);
    if (!node || node.type !== 'tool') return;

    const nodeId = typeof node.id === 'string' ? node.id : null;
    if (!nodeId) return;

    const toolRunRecord = asRecord(toolRuns[nodeId]);
    if (!toolRunRecord) return;

    const lane = normalizeLane(node.lane);
    const titleBase =
      typeof node.id === 'string' ? node.id : `${lane.toLowerCase()}_dataset`;
    const metadata = asRecord(toolRunRecord.metadata);
    const tsFromMetadata =
      typeof metadata?.timestamp === 'number' ? metadata.timestamp : null;
    const timestamp = tsFromMetadata;

    const dataRecord = asRecord(toolRunRecord.data);
    if (!dataRecord) return;

    if (adapterV2) {
      const toolName =
        typeof metadata?.tool === 'string' ? metadata.tool : lane.toLowerCase();
      const schemaVersion =
        typeof metadata?.data_schema_version === 'string'
          ? metadata.data_schema_version
          : undefined;
      const adapter = resolveAdapter(toolName, schemaVersion);
      const shapes = adapter.parse({ runId, nodeId, lane, titleBase, metadata, dataRecord });
      shapes.forEach((shape) => {
        result.push({
          id: `${runId}:${nodeId}:${shape.suffix}`,
          nodeId,
          lane,
          title: shape.title,
          columns: shape.columns,
          rows: shape.rows,
          timestamp,
          metadata,
          defaultSort: shape.defaultSort,
          defaultColumns: shape.defaultColumns,
          valueFormatHints: shape.valueFormatHints,
          summaryKpis: shape.summaryKpis,
        });
      });
      return;
    }

    // Legacy branch — unchanged
    const pushDataset = (
      suffix: string,
      rows: Array<Record<string, unknown>>,
      columns?: string[],
      titleOverride?: string,
    ) => {
      if (rows.length === 0) return;
      const resolvedColumns = columns && columns.length > 0 ? columns : collectColumns(rows);
      const filteredColumns = resolvedColumns.filter(
        (column) => column.toLowerCase() !== 'error',
      );
      const visibleColumns = filteredColumns.length > 0 ? filteredColumns : resolvedColumns;
      result.push({
        id: `${runId}:${nodeId}:${suffix}`,
        nodeId,
        lane,
        title: titleOverride || `${titleBase} ${suffix}`,
        columns: visibleColumns,
        rows,
        timestamp,
        metadata,
      });
    };

    const matrixRows = buildRowsFromMatrix(dataRecord.columns, dataRecord.rows);
    if (matrixRows.length > 0) {
      const columns = asArray(dataRecord.columns).map((col) => String(col));
      pushDataset('main', matrixRows, columns, `${titleBase} / main`);
    }

    if (lane === Lane.MACRO) {
      const fredRows = buildRowsFromMatrix(dataRecord.fred_columns, dataRecord.fred_rows);
      if (fredRows.length > 0) {
        const fredColumns = asArray(dataRecord.fred_columns).map((col) => String(col));
        pushDataset('fred', fredRows, fredColumns, `${titleBase} / fred`);
      }
    }

    if (lane === Lane.NEWS) {
      const newsRows = buildRowsFromObjectList(dataRecord.items);
      pushDataset('items', newsRows, ['time', 'url', 'text'], `${titleBase} / items`);
    }

    if (lane === Lane.CALCULATOR) {
      const stockRows = buildCalculatorRows(dataRecord.stock);
      pushDataset(
        'stock',
        stockRows,
        ['Cluster', 'Energy', 'Size', 'Members'],
        `${titleBase} / stock`,
      );

      const macroRows = buildCalculatorRows(dataRecord.macro);
      pushDataset(
        'macro',
        macroRows,
        ['Cluster', 'Energy', 'Size', 'Members'],
        `${titleBase} / macro`,
      );
    }

    if (lane === Lane.POLYMARKET) {
      const polyDatasets = normalizePolymarketRows(dataRecord);
      polyDatasets.forEach((dataset) => {
        const deterministicKey = normalizeDatasetKey(dataset.title);
        pushDataset(
          `poly_${deterministicKey}`,
          dataset.rows,
          collectColumns(dataset.rows),
          `${titleBase} / ${dataset.title}`,
        );
      });
    }

    if (
      matrixRows.length === 0 &&
      lane !== Lane.CALCULATOR &&
      lane !== Lane.POLYMARKET &&
      lane !== Lane.NEWS
    ) {
      const fallbackRows = buildRowsFromObjectList(dataRecord.rows);
      pushDataset(
        'fallback',
        fallbackRows,
        collectColumns(fallbackRows),
        `${titleBase} / rows`,
      );
    }
  });

  return result.map((dataset) => enhanceLegacyDataset(dataset));
}

export function parseArtifactFallbackDatasets(
  runId: string,
  artifacts: Record<string, FeedArtifactEnvelope>,
  options?: { adapterV2?: boolean },
): ToolDataset[] {
  const nodes = Object.entries(artifacts).map(([nodeId, envelope]) => ({
    id: nodeId,
    type: 'tool',
    lane: envelope.lane,
  }));

  return parseToolDatasets(runId, { nodes }, artifacts, options);
}

export default function DataView({
  missionName,
  displayRunId,
  runSource: _runSource,
  historyMode,
  temporalContext,
  visible = true,
  suppressIdentity = false,
  showToolbar = true,
  showEmptyLanes = true,
  searchQuery,
  onSearchQueryChange,
  laneSummaries,
  visibleLanes,
}: DataViewProps) {
  void _runSource;
  const uiConfig = useZenith((state) => state.uiConfig);
  const featureFlags = asRecord(uiConfig?.feature_flags);
  const adapterV2Enabled = featureFlags?.adapter_v2 === true;
  const dataViewConfig = asRecord(uiConfig?.data_view);
  const defaultRowLimit = asPositiveInt(dataViewConfig?.default_row_limit, DEFAULT_ROW_LIMIT);
  const staleAfterDays = asPositiveInt(
    dataViewConfig?.stale_after_days,
    DEFAULT_STALE_AFTER_DAYS,
  );
  const textClampLines = asPositiveInt(
    dataViewConfig?.text_clamp_lines,
    DEFAULT_TEXT_CLAMP_LINES,
  );
  const textClampMinChars = asPositiveInt(
    dataViewConfig?.text_clamp_min_chars,
    DEFAULT_TEXT_CLAMP_MIN_CHARS,
  );
  const maxTableHeightPx = asPositiveInt(
    dataViewConfig?.max_table_height_px,
    DEFAULT_MAX_TABLE_HEIGHT_PX,
  );
  const autoCollapseMultiDataset = asBoolean(
    dataViewConfig?.auto_collapse_multi_dataset,
    DEFAULT_AUTO_COLLAPSE_MULTI_DATASET,
  );
  const columnAliases = {
    ...DEFAULT_COLUMN_ALIASES,
    ...normalizeColumnAliases(dataViewConfig?.column_aliases),
  };

  // ── unified view state ───────────────────────────────────────────────────
  const [vs, dispatch] = useReducer(viewReducer, undefined, initialViewState);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);
  const [artifactFallbackMode, setArtifactFallbackMode] = useState(false);
  const [datasets, setDatasets] = useState<ToolDataset[]>([]);
  const [rawToolRunsByNodeId, setRawToolRunsByNodeId] = useState<Record<string, unknown>>({});
  const [tickerMap, setTickerMap] = useState<Record<string, string>>({});
  const effectiveSearchQuery = searchQuery ?? vs.searchQuery;

  // Reset view state on run change (preserve density + search)
  useEffect(() => {
    dispatch({ type: 'RESET' });
  }, [displayRunId]);

  // Initialise per-dataset collapse + row-limit when datasets load
  useEffect(() => {
    const datasetsPerLane = new Map<string, number>();
    datasets.forEach((d) => {
      datasetsPerLane.set(d.lane, (datasetsPerLane.get(d.lane) ?? 0) + 1);
    });

    datasets.forEach((dataset) => {
      const laneCount = datasetsPerLane.get(dataset.lane) ?? 0;
      const shouldCollapse =
        autoCollapseMultiDataset &&
        laneCount > 1 &&
        dataset.lane !== Lane.NEWS &&
        dataset.lane !== Lane.POLYMARKET;
      // Only set if not already set (don't override user interaction)
      if (!(dataset.id in vs.collapsedByDataset)) {
        dispatch({ type: 'SET_DATASET_COLLAPSED', datasetId: dataset.id, collapsed: shouldCollapse });
      }
      if (!(dataset.id in vs.visibleRowLimitByDataset)) {
        dispatch({ type: 'SET_ROW_LIMIT', datasetId: dataset.id, limit: defaultRowLimit });
      }
    });
  }, [
    autoCollapseMultiDataset,
    datasets,
    defaultRowLimit,
    vs.collapsedByDataset,
    vs.visibleRowLimitByDataset,
  ]);

  // Ticker map: prefer metadata.identity_map, fallback to codex ref file
  useEffect(() => {
    let cancelled = false;
    if (!visible) {
      return () => {
        cancelled = true;
      };
    }
    const metadataIdentityMap = getMetadataIdentityMap(datasets);

    if (Object.keys(metadataIdentityMap).length > 0) {
      setTickerMap(metadataIdentityMap);
      return () => {
        cancelled = true;
      };
    }

    const loadRefTickerMap = async () => {
      try {
        const file = await api.codex.getFile(TICKER_MAP_REF_PATH);
        const parsed = JSON.parse(file.content || '{}');
        if (!cancelled && parsed && typeof parsed === 'object') {
          const normalized: Record<string, string> = {};
          Object.entries(parsed as Record<string, unknown>).forEach(([ticker, identity]) => {
            if (typeof identity !== 'string') return;
            const normalizedTicker = ticker.trim().toUpperCase();
            if (!normalizedTicker) return;
            normalized[normalizedTicker] = identity.trim();
          });
          setTickerMap(normalized);
          return;
        }
      } catch {
        // Fall through to empty map
      }
      if (!cancelled) setTickerMap({});
    };

    void loadRefTickerMap();

    return () => {
      cancelled = true;
    };
  }, [datasets, visible]);

  // Data loading
  useEffect(() => {
    let cancelled = false;

    const loadData = async () => {
      if (!visible) {
        setLoading(false);
        return;
      }
      if (!displayRunId) {
        setDatasets([]);
        setRawToolRunsByNodeId({});
        setError(null);
        setFallbackNotice(null);
        setArtifactFallbackMode(false);
        return;
      }

      setLoading(true);
      setError(null);
      setFallbackNotice(null);
      setArtifactFallbackMode(false);

      try {
        const attemptLimit = historyMode ? 1 : LIVE_HOLOGRAM_RETRY_ATTEMPTS;
        let runHologram: unknown = null;

        for (let attempt = 0; attempt < attemptLimit; attempt += 1) {
          if (cancelled) return;
          try {
            runHologram = await api.runHolographic.getRunHologram(displayRunId);
            break;
          } catch {
            if (attempt < attemptLimit - 1) {
              await sleep(LIVE_HOLOGRAM_RETRY_DELAY_MS);
            }
          }
        }

        if (!runHologram) {
          try {
            const artifacts = await loadFeedArtifacts(displayRunId);
            const fallbackDatasets = parseArtifactFallbackDatasets(displayRunId, artifacts, {
              adapterV2: adapterV2Enabled,
            });

            if (!cancelled && fallbackDatasets.length > 0) {
              setDatasets(fallbackDatasets);
              setRawToolRunsByNodeId(artifacts);
              setFallbackNotice(
                'Holographic payload unavailable for this run. Rendering structured datasets from raw feed artifacts.',
              );
              setArtifactFallbackMode(false);
              return;
            }
          } catch {
            // Fall through to raw artifact viewer fallback below.
          }

          if (!cancelled) {
            setDatasets([]);
            setRawToolRunsByNodeId({});
            setFallbackNotice(null);
            setArtifactFallbackMode(true);
          }
          return;
        }

        const runRecord = asRecord(runHologram);
        const nodes = asArray(runRecord?.nodes)
          .map((nodeRaw) => asRecord(nodeRaw))
          .filter((node): node is Record<string, unknown> => Boolean(node))
          .filter((node) => node.type === 'tool' && typeof node.id === 'string');

        const toolRunEntries = await Promise.all(
          nodes.map(async (node) => {
            const nodeId = String(node.id);
            try {
              const payload = await api.runHolographic.getToolRun(displayRunId, nodeId);
              return [nodeId, payload] as const;
            } catch {
              return [nodeId, null] as const;
            }
          }),
        );

        const toolRuns = Object.fromEntries(toolRunEntries);
        const nextDatasets = parseToolDatasets(displayRunId, runHologram, toolRuns, {
          adapterV2: adapterV2Enabled,
        });

        if (!cancelled) {
          setDatasets(nextDatasets);
          setRawToolRunsByNodeId(toolRuns);
          setFallbackNotice(null);
          setArtifactFallbackMode(false);
        }
      } catch (err: unknown) {
        try {
          const artifacts = await loadFeedArtifacts(displayRunId);
          const fallbackDatasets = parseArtifactFallbackDatasets(displayRunId, artifacts, {
            adapterV2: adapterV2Enabled,
          });

          if (!cancelled && fallbackDatasets.length > 0) {
            setDatasets(fallbackDatasets);
            setRawToolRunsByNodeId(artifacts);
            setFallbackNotice(
              'Holographic payload unavailable for this run. Rendering structured datasets from raw feed artifacts.',
            );
            setArtifactFallbackMode(false);
            setError(null);
            return;
          }
        } catch {
          // Fall through to raw artifact viewer fallback below.
        }

        if (!cancelled) {
          setDatasets([]);
          setRawToolRunsByNodeId({});
          setFallbackNotice(null);
          setArtifactFallbackMode(true);
          setError(
            (err instanceof Error ? err.message : null) ||
            'Holographic payload unavailable and raw artifact parsing failed. Falling back to raw artifacts.',
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void loadData();

    return () => {
      cancelled = true;
    };
  }, [displayRunId, visible, adapterV2Enabled, historyMode]);

  // ── filtered lane panels ─────────────────────────────────────────────────
  const lanePanels = useMemo(() => {
    const query = effectiveSearchQuery.trim().toLowerCase();
    const laneAllowList = visibleLanes && visibleLanes.length > 0
      ? new Set<Lane>(visibleLanes)
      : null;
    const orderedLanes = laneAllowList
      ? LANE_ORDER.filter((lane) => laneAllowList.has(lane))
      : LANE_ORDER;
    return orderedLanes.map((lane) => {
      const laneDatasets = datasets
        .filter((dataset) => dataset.lane === lane)
        .map((dataset) => {
          if (!query) return dataset;
          const filteredRows = dataset.rows.filter((row) =>
            Object.values(row).some((value) =>
              String(value ?? '').toLowerCase().includes(query),
            ),
          );
          return { ...dataset, rows: filteredRows };
        })
        .filter((dataset) => dataset.rows.length > 0 || !query);

      const recordCount = laneDatasets.reduce((sum, d) => sum + d.rows.length, 0);
      return { lane, datasets: laneDatasets, recordCount };
    }).filter((panel) => showEmptyLanes || panel.datasets.length > 0);
  }, [datasets, effectiveSearchQuery, showEmptyLanes, visibleLanes]);

  const totalDatasets = lanePanels.reduce((sum, lp) => sum + lp.datasets.length, 0);
  const totalRows = lanePanels.reduce((sum, lp) => sum + lp.recordCount, 0);
  const asOfLabel = temporalContext?.horizon_label || temporalContext?.target_time_iso || null;
  const primaryLineage = temporalContext?.lineage?.primary ?? null;
  const truthLineage = temporalContext?.lineage?.truth ?? null;
  const primaryRootTime = primaryLineage?.canonical_time_iso || primaryLineage?.root_data_as_of_iso || primaryLineage?.root_run_timestamp_iso || null;
  const truthRootTime = truthLineage?.canonical_time_iso || truthLineage?.root_data_as_of_iso || truthLineage?.root_run_timestamp_iso || null;

  // ── sort helper ───────────────────────────────────────────────────────────
  function sortedRows(dataset: ToolDataset): Array<Record<string, unknown>> {
    const sort = vs.sortByDataset[dataset.id];
    if (!sort) return dataset.rows;
    return dataset.rows
      .map((row, index) => ({ row, index }))
      .sort((left, right) => {
        const compared = compareByColumn(
          left.row[sort.column],
          right.row[sort.column],
          sort.column,
          dataset.metadata,
          sort.direction,
        );
        return compared === 0 ? left.index - right.index : compared;
      })
      .map((entry) => entry.row);
  }

  // ── no run state ─────────────────────────────────────────────────────────
  if (!displayRunId) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-[var(--zenith-bg)]">
        <div className="text-center">
          <Database size={48} className="mx-auto mb-4 text-zenith-muted" />
          <p className="font-mono text-sm text-zenith-soft">No run data available</p>
          <p className="mt-2 font-mono text-xs text-zenith-muted">
            Execute a run to view data panels
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full overflow-y-auto p-4">
      <div className="max-w-[1400px] mx-auto">
        {/* ── header ── */}
        {showToolbar && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {!suppressIdentity && (
              <div className="kicker-mono mr-2 flex flex-wrap items-center gap-2 tabular-nums">
                <span className="text-zenith-soft">{missionName.toUpperCase()}</span>
                {historyMode && <span className="text-amber-300/80">archive</span>}
                {asOfLabel && <span className="text-cyan-300/80">as of {asOfLabel}</span>}
                <span>{totalDatasets}ds</span>
                <span>{totalRows.toLocaleString()}r</span>
              </div>
            )}
            <input
              value={effectiveSearchQuery}
              onChange={(event) => {
                if (onSearchQueryChange) {
                  onSearchQueryChange(event.target.value);
                  return;
                }
                dispatch({ type: 'SET_SEARCH', query: event.target.value });
              }}
              placeholder="Filter rows…"
              className="motion-fast min-w-[220px] max-w-[520px] flex-1 rounded border border-zenith-edge-soft bg-black/30 px-2 py-1 font-mono text-[11px] text-zenith-soft focus:border-zenith-edge-strong focus:outline-none"
            />
            <div className="flex items-center gap-1 font-mono text-[9px]">
              <button
                onClick={() => {
                  LANE_ORDER.forEach((lane) => {
                    dispatch({ type: 'SET_LANE_COLLAPSED', lane, collapsed: true });
                  });
                  datasets.forEach((dataset) => {
                    dispatch({
                      type: 'SET_DATASET_COLLAPSED',
                      datasetId: dataset.id,
                      collapsed: true,
                    });
                  });
                }}
                className="motion-fast rounded border border-zenith-edge-soft px-2 py-1 text-zenith-muted hover:border-zenith-edge-strong hover:text-zenith-text"
              >
                MIN
              </button>
              <button
                onClick={() => {
                  LANE_ORDER.forEach((lane) => {
                    dispatch({ type: 'SET_LANE_COLLAPSED', lane, collapsed: false });
                  });
                  datasets.forEach((dataset) => {
                    dispatch({
                      type: 'SET_DATASET_COLLAPSED',
                      datasetId: dataset.id,
                      collapsed: false,
                    });
                  });
                }}
                className="motion-fast rounded border border-zenith-edge-soft px-2 py-1 text-zenith-muted hover:border-zenith-edge-strong hover:text-zenith-text"
              >
                MAX
              </button>
              <button
                onClick={() =>
                  dispatch({
                    type: 'SET_DENSITY',
                    density: vs.density === 'compact' ? 'comfortable' : 'compact',
                  })
                }
                className="motion-fast rounded border border-zenith-edge-soft px-2 py-1 text-zenith-muted hover:border-zenith-edge-strong hover:text-zenith-text"
                title="Toggle row density"
              >
                {vs.density === 'compact' ? '·' : '═'}
              </button>
            </div>
          </div>
        )}
        {!suppressIdentity && (primaryLineage?.root_run_id || truthLineage?.root_run_id) && (
          <div className="mb-3 flex flex-wrap gap-2 font-mono text-[10px] tabular-nums text-zenith-muted">
            {primaryLineage?.root_run_id && (
              <span>
                <span className="text-cyan-300/80">primary</span>{' '}
                {formatTemporalLabel(primaryRootTime)} · {primaryLineage.root_run_id.slice(-12)}
                {primaryLineage.lineage_depth > 0 ? ` · ${primaryLineage.lineage_depth}hop` : ''}
              </span>
            )}
            {truthLineage?.root_run_id && (
              <span>
                <span className="text-blue-300/80">truth</span>{' '}
                {formatTemporalLabel(truthRootTime)} · {truthLineage.root_run_id.slice(-12)}
              </span>
            )}
          </div>
        )}

        {/* ── loading / error / empty states ── */}
        {loading && (
          <div className="mb-2 flex items-center gap-2 font-mono text-[11px] text-zenith-muted">
            <Loader2 size={12} className="animate-spin" />
            Loading tool outputs…
          </div>
        )}

        {error && (
          <div className="mb-2 font-mono text-[11px] text-rose-200">
            <span className="text-rose-300">● </span>
            {error}
          </div>
        )}

        {fallbackNotice && (
          <div className="mb-2 font-mono text-[11px] text-amber-100">
            <span className="text-amber-300">● </span>
            Holographic payload unavailable — using raw artifacts
          </div>
        )}

        {!loading && !error && !artifactFallbackMode && totalDatasets === 0 && (
          <div className="mb-2 font-mono text-[11px] text-zenith-muted">
            No tool-run panels for this run.
          </div>
        )}

        {/* ── artifact fallback ── */}
        {artifactFallbackMode && displayRunId && (
          <div className="space-y-4 pb-8">
            <div className="rounded border border-amber-400/30 bg-amber-500/[0.07] p-4 font-mono text-sm text-amber-100">
              Holographic payload was unavailable for this run. Showing raw artifact views by
              lane.
            </div>
            {ARTIFACT_FALLBACK_NODES.filter(
              (artifact) => !visibleLanes || visibleLanes.includes(artifact.lane),
            ).map((artifact) => (
              <section
                key={artifact.nodeId}
                className="overflow-hidden rounded-[var(--zenith-radius-region)] border border-zenith-edge bg-zenith-panel-muted"
              >
                <div className="flex items-center justify-between border-b border-zenith-edge px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold uppercase tracking-wide text-zenith-text">
                      {LANE_LABEL[artifact.lane]}
                    </span>
                    <span className="font-mono text-[11px] text-zenith-muted">
                      {artifact.label}
                    </span>
                  </div>
                  <span className="font-mono text-[11px] text-zenith-muted">
                    {artifact.nodeId}
                  </span>
                </div>
                <div className="p-3">
                  <ArtifactViewer
                    runId={displayRunId}
                    nodeId={artifact.nodeId}
                    nodeType="tool"
                  />
                </div>
              </section>
            ))}
          </div>
        )}

        {/* ── main lane panels ── */}
        {!artifactFallbackMode && (
          <div className="space-y-4 pb-8">
            {lanePanels.map(({ lane, datasets: laneDatasets }) => {
              const Icon = LANE_ICON[lane];
              const isLaneCollapsed = vs.collapsedByLane[lane] === true;

              return (
                <LaneCard
                  key={lane}
                  lane={lane}
                  label={LANE_LABEL[lane]}
                  accentClass={LANE_ACCENT[lane]}
                  Icon={Icon}
                  familySummary={laneSummaries?.[lane] ?? null}
                  datasets={laneDatasets}
                  isCollapsed={isLaneCollapsed}
                  onToggle={() =>
                    dispatch({
                      type: 'SET_LANE_COLLAPSED',
                      lane,
                      collapsed: !isLaneCollapsed,
                    })
                  }
                >
                  {laneDatasets.length === 0 ? (
                    loading ? (
                      <div className="flex items-center gap-2 font-mono text-xs text-zenith-muted">
                        <span className="dot-live" />
                        Loading feed data…
                      </div>
                    ) : effectiveSearchQuery.trim() ? (
                      <div className="rounded border border-dashed border-zenith-edge px-3 py-2 font-mono text-[9px] text-zenith-muted">
                        No rows match the current filter. Clear the search to show all data.
                      </div>
                    ) : (
                      <div className="rounded border border-dashed border-zenith-edge px-3 py-2 font-mono text-[9px] text-zenith-muted">
                        No feed data produced. The tool node for this lane may not have executed
                        or returned an empty response.
                      </div>
                    )
                  ) : (
                    laneDatasets.map((dataset) => {
                      const mode = vs.modeByDataset[dataset.id] ?? 'table';
                      const isDatasetCollapsed = vs.collapsedByDataset[dataset.id] !== false;
                      const qualityNotes = getDatasetQualityNotes(dataset);
                      const rowLimit =
                        vs.visibleRowLimitByDataset[dataset.id] ?? defaultRowLimit;
                      const theSort = vs.sortByDataset[dataset.id];
                      const sorted = sortedRows(dataset);
                      const title = humanizeDatasetTitle(dataset);

                      return (
                        <DatasetCard
                          key={dataset.id}
                          dataset={dataset}
                          displayTitle={dataset.displayTitle ?? title.displayTitle}
                          displaySubtitle={dataset.displaySubtitle ?? title.displaySubtitle}
                          mode={mode}
                          isCollapsed={isDatasetCollapsed}
                          staleAfterDays={staleAfterDays}
                          onModeChange={(m) =>
                            dispatch({
                              type: 'SET_DATASET_MODE',
                              datasetId: dataset.id,
                              mode: m,
                            })
                          }
                          onToggleCollapsed={() =>
                            dispatch({
                              type: 'SET_DATASET_COLLAPSED',
                              datasetId: dataset.id,
                              collapsed: !isDatasetCollapsed,
                            })
                          }
                        >
                          {mode !== 'table' && (
                            <div className="border-b border-zenith-edge-soft bg-black/25 px-3 py-2">
                              <div className="flex flex-wrap gap-1">
                                {(['metadata', 'raw', 'schema', 'config'] as const).map((tab) => (
                                  <button
                                    key={`${dataset.id}:${tab}`}
                                    type="button"
                                    onClick={() =>
                                      dispatch({
                                        type: 'SET_DATASET_MODE',
                                        datasetId: dataset.id,
                                        mode: tab,
                                      })
                                    }
                                    className={clsx(
                                      'motion-fast rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.14em]',
                                      mode === tab
                                        ? 'border-zenith-edge-strong bg-white/[0.09] text-zenith-text'
                                        : 'border-zenith-edge-soft text-zenith-muted hover:border-zenith-edge hover:text-zenith-soft',
                                    )}
                                  >
                                    {tab}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}

                          {mode === 'metadata' && (
                            <MetadataPanel
                              dataset={dataset}
                              rawPayload={rawToolRunsByNodeId[dataset.nodeId] ?? null}
                            />
                          )}

                          {mode === 'raw' && (
                            <div
                              className="overflow-auto p-3"
                              style={{ maxHeight: `${maxTableHeightPx}px` }}
                            >
                              <pre className="whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-zenith-soft">
                                {JSON.stringify(
                                  rawToolRunsByNodeId[dataset.nodeId] ?? dataset.rows,
                                  null,
                                  2,
                                )}
                              </pre>
                            </div>
                          )}

                          {mode === 'schema' && <SchemaPanel dataset={dataset} />}

                          {mode === 'config' && <ConfigStrip metadata={dataset.metadata} />}

                          {mode === 'table' && (
                            <>
                              {qualityNotes.length > 0 && (
                                <div className="mx-3 mt-3 space-y-1 rounded border border-amber-400/30 bg-amber-500/[0.07] px-3 py-2 font-mono text-[11px] text-amber-100">
                                  {qualityNotes.map((note, noteIdx) => (
                                    <div key={`${dataset.id}:quality:${noteIdx}`}>{note}</div>
                                  ))}
                                </div>
                              )}
                              {dataset.lane === Lane.NEWS ? (
                                <NewsFeedView
                                  dataset={dataset}
                                  canonicalTimeIso={
                                    primaryLineage?.canonical_time_iso ??
                                    temporalContext?.data_as_of_iso ??
                                    null
                                  }
                                />
                              ) : dataset.lane === Lane.POLYMARKET ? (
                                <PredictionMarketView dataset={dataset} />
                              ) : (
                                <TableView
                                  dataset={dataset}
                                  density={vs.density}
                                  sort={theSort}
                                  visibleRowLimit={rowLimit}
                                  defaultRowLimit={defaultRowLimit}
                                  totalRows={sorted.length}
                                  expandedTextCells={vs.expandedTextCells}
                                  columnAliases={columnAliases}
                                  tickerMap={tickerMap}
                                  maxTableHeightPx={maxTableHeightPx}
                                  textClampLines={textClampLines}
                                  textClampMinChars={textClampMinChars}
                                  canonicalTimeIso={
                                    primaryLineage?.canonical_time_iso ??
                                    temporalContext?.data_as_of_iso ??
                                    null
                                  }
                                  onSort={(col) =>
                                    dispatch({
                                      type: 'SET_SORT',
                                      datasetId: dataset.id,
                                      column: col,
                                    })
                                  }
                                  onLoadMore={() =>
                                    dispatch({
                                      type: 'SET_ROW_LIMIT',
                                      datasetId: dataset.id,
                                      limit: rowLimit + defaultRowLimit,
                                    })
                                  }
                                  onLoadAll={() =>
                                    dispatch({
                                      type: 'SET_ROW_LIMIT',
                                      datasetId: dataset.id,
                                      limit: sorted.length,
                                    })
                                  }
                                  onExpandTextCell={(cellKey) =>
                                    dispatch({ type: 'EXPAND_TEXT_CELL', cellKey })
                                  }
                                />
                              )}
                            </>
                          )}
                        </DatasetCard>
                      );
                    })
                  )}
                </LaneCard>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
