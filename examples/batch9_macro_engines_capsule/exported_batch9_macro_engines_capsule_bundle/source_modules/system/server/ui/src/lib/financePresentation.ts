import { Lane } from '../api';
import {
  asRecord,
  buildCalculatorRows,
  buildRowsFromMatrix,
  buildRowsFromObjectList,
} from '../components/views/dataViewUtils';
import {
  FEED_ARTIFACT_SPECS,
  type FeedArtifactEnvelope,
  type FeedArtifactSpec,
} from './financeArtifacts';
import {
  deriveCalculatorClusterInsights,
  type CalculatorClusterInsight,
} from './calculatorInsight';

export const FINANCE_FAMILIES = [
  'Equities',
  'ETF',
  'Flow',
  'Macro',
  'News',
  'Prediction',
  'Derived',
] as const;

export type FinanceFamily = (typeof FINANCE_FAMILIES)[number];
export type HealthTone = 'ok' | 'warn' | 'block' | 'unknown';
export type FreshnessTone = 'fresh' | 'lagging' | 'stale' | 'missing';

export interface PresentationFreshness {
  tone: FreshnessTone;
  label: string;
  ageSeconds: number | null;
  iso: string | null;
}

export interface AttentionFact {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral' | 'warning';
}

export interface AttentionPreviewRow {
  primary: string;
  secondary?: string | null;
  tertiary?: string | null;
  tone?: 'positive' | 'negative' | 'neutral' | 'warning';
}

export interface NewsItem {
  headline: string;
  source: string;
  time: string | null;
  url: string | null;
  rawText: string;
  affectedAssets: string[];
  category: string | null;
}

export interface NewsCluster {
  id: string;
  headline: string;
  normalizedHeadline: string;
  count: number;
  latestTime: string | null;
  sources: string[];
  topSource: string;
  affectedAssets: string[];
  summary: string;
  items: NewsItem[];
  freshness: PresentationFreshness;
  score: number;
}

export interface PredictionRepricing {
  id: string;
  category: string;
  bucket: string;
  question: string;
  outcome: string | null;
  probability: number | null;
  probabilityDelta: number | null;
  volume: number | null;
  conviction: number | null;
  expiry: string | null;
  marketSource: string;
  relatedAssets: string[];
  slug: string | null;
  score: number;
}

export interface AttentionDetailPayload {
  explanation: string;
  facts: AttentionFact[];
  previewRows: AttentionPreviewRow[];
  relatedNews: NewsCluster[];
  relatedPredictions: PredictionRepricing[];
  calculatorInsight?: CalculatorClusterInsight | null;
}

export interface AttentionEvent {
  id: string;
  rank: number;
  family: FinanceFamily;
  assetClass: string;
  tickerOrLabel: string;
  headline: string;
  primaryMetricLabel: string;
  primaryMetricValue: string;
  zScore: number | null;
  fiveDayMove: number | null;
  probability: number | null;
  probabilityDelta: number | null;
  relatedNews: number | string | null;
  confidence: number;
  freshness: PresentationFreshness;
  sourceNodeIds: string[];
  secondaryMetricValue: string | null;
  secondaryMetricLabel: string | null;
  detail: AttentionDetailPayload;
  score: number;
  lane: Lane;
}

export interface FamilySummary {
  family: FinanceFamily;
  lane: Lane;
  itemCount: number;
  topMover: string | null;
  strongestSignal: string | null;
  staleStatus: FreshnessTone;
  missingCoverage: string | null;
  status: string;
  asOf: string | null;
  sourceNodeId: string;
}

export interface DataHealth {
  overallTone: HealthTone;
  staleFamilies: FinanceFamily[];
  missingFamilies: FinanceFamily[];
  nonSuccessSources: string[];
  canonicalTime: string | null;
  selectedRunStatus: string | null;
  alertCount: number;
  alerts: string[];
}

export interface FinancePresentationModel {
  attentionEvents: AttentionEvent[];
  familySummaries: FamilySummary[];
  familySummaryMap: Record<string, FamilySummary>;
  health: DataHealth;
  newsClusters: NewsCluster[];
  predictionRepricings: PredictionRepricing[];
}

interface PresentationInput {
  artifacts: Record<string, FeedArtifactEnvelope>;
  canonicalTimeIso?: string | null;
  selectedRunStatus?: string | null;
}

const FOUR_HOURS_IN_SECONDS = 4 * 3600;
const TWELVE_HOURS_IN_SECONDS = 12 * 3600;

const STOPWORDS = new Set([
  'the',
  'and',
  'for',
  'with',
  'that',
  'this',
  'will',
  'from',
  'after',
  'before',
  'into',
  'over',
  'under',
  'than',
  'more',
  'less',
  'what',
  'when',
  'where',
  'which',
  'your',
  'their',
  'about',
  'market',
  'markets',
  'price',
  'said',
  'says',
]);

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function asQualityTone(value: unknown): HealthTone | null {
  return value === 'ok' || value === 'warn' || value === 'block' ? value : null;
}

function parseIsoToSeconds(value: string | null | undefined): number | null {
  if (!value) return null;
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return null;
  return Math.floor(parsed / 1000);
}

function formatCompactNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(digits)}B`;
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(digits)}M`;
  if (abs >= 1_000) return `${(value / 1_000).toFixed(digits)}K`;
  if (abs >= 100) return value.toFixed(0);
  if (abs >= 10) return value.toFixed(1);
  return value.toFixed(2);
}

function formatCurrencyCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return `${value >= 0 ? '+' : '-'}$${formatCompactNumber(Math.abs(value))}`;
}

function formatPercent(value: number | null | undefined, scale: 'ratio' | 'unit' = 'ratio'): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const percentage = scale === 'ratio' ? value * 100 : value;
  return `${percentage >= 0 ? '+' : ''}${percentage.toFixed(1)}%`;
}

function formatMacroDisplayChange(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const magnitude = Math.abs(value);
  if (magnitude >= 1_000) {
    return `${value >= 0 ? '+' : ''}${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
  }
  if (magnitude >= 100) return `${value >= 0 ? '+' : ''}${value.toFixed(1)}`;
  if (magnitude >= 10) return `${value >= 0 ? '+' : ''}${value.toFixed(2)}`;
  if (magnitude >= 1) return `${value >= 0 ? '+' : ''}${value.toFixed(3)}`;
  return `${value >= 0 ? '+' : ''}${value.toFixed(4)}`;
}

function formatProbability(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const percentage = value > 1 ? value : value * 100;
  return `${percentage.toFixed(1)}%`;
}

function formatZScore(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}z`;
}

function extractHeadline(text: string): string {
  const compact = text.replace(/\s+/g, ' ').trim();
  if (!compact) return 'Headline unavailable';
  const delimiters = ['. ', '。', '！', '!', '? ', '？', ' — ', ' - ', ' | ', '\n'];
  const matchIndex = delimiters
    .map((delimiter) => compact.indexOf(delimiter))
    .filter((index) => index > 0)
    .sort((left, right) => left - right)[0];
  if (typeof matchIndex === 'number' && matchIndex > 0 && matchIndex < 140) {
    return compact.slice(0, matchIndex + 1).trim();
  }
  return compact.length > 140 ? `${compact.slice(0, 137)}…` : compact;
}

function normalizeHeadlineFingerprint(headline: string): string {
  const normalized = headline
    .normalize('NFKD')
    .replace(/[#*_`~]/g, ' ')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
  const tokens = normalized
    .split(' ')
    .map((token) => token.trim())
    .filter((token) => token.length > 1 && !STOPWORDS.has(token))
    .slice(0, 8);
  if (tokens.length >= 3) return tokens.join(' ');
  return normalized.slice(0, 32);
}

function extractKeywords(text: string): string[] {
  const uppercaseTokens = text.match(/\b[A-Z]{2,6}\b/g) ?? [];
  const keywordTokens = text
    .normalize('NFKD')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length >= 3 && !STOPWORDS.has(token.toLowerCase()))
    .slice(0, 8);
  const combined = [...uppercaseTokens, ...keywordTokens];
  return [...new Set(combined)].slice(0, 8);
}

function extractAffectedAssets(row: Record<string, unknown>, fallbackText: string): string[] {
  const keys = ['assets', 'asset', 'tickers', 'symbols', 'tags'];
  const values: string[] = [];
  keys.forEach((key) => {
    const value = row[key];
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (typeof item === 'string' && item.trim()) values.push(item.trim());
      });
      return;
    }
    if (typeof value === 'string' && value.trim()) values.push(value.trim());
  });
  if (typeof row.category === 'string' && row.category.trim()) values.push(row.category.trim());
  if (values.length > 0) return [...new Set(values)].slice(0, 6);
  return extractKeywords(fallbackText).slice(0, 4);
}

function estimateFreshness(
  asOfIso: string | null | undefined,
  canonicalTimeIso: string | null | undefined,
): PresentationFreshness {
  const iso = asOfIso ?? null;
  const canonicalSeconds = parseIsoToSeconds(canonicalTimeIso);
  const asOfSeconds = parseIsoToSeconds(iso);

  if (asOfSeconds === null) {
    return { tone: 'missing', label: 'missing', ageSeconds: null, iso };
  }

  if (canonicalSeconds === null) {
    return { tone: 'fresh', label: 'ready', ageSeconds: 0, iso };
  }

  const ageSeconds = Math.max(0, canonicalSeconds - asOfSeconds);
  if (ageSeconds <= FOUR_HOURS_IN_SECONDS) {
    return { tone: 'fresh', label: 'in sync', ageSeconds, iso };
  }
  if (ageSeconds <= TWELVE_HOURS_IN_SECONDS) {
    return {
      tone: 'lagging',
      label: `lag ${Math.round(ageSeconds / 3600)}h`,
      ageSeconds,
      iso,
    };
  }
  return {
    tone: 'stale',
    label: `stale ${Math.round(ageSeconds / 3600)}h`,
    ageSeconds,
    iso,
  };
}

function confidenceForEvent(
  base: number,
  status: string | null,
  freshness: PresentationFreshness,
): number {
  let next = base;
  if (status && status !== 'success') next -= 0.25;
  if (freshness.tone === 'lagging') next -= 0.1;
  if (freshness.tone === 'stale') next -= 0.2;
  if (freshness.tone === 'missing') next -= 0.25;
  return Math.max(0.2, Math.min(0.98, Number(next.toFixed(2))));
}

function topSummaryFromWarnings(metadata: Record<string, unknown> | null): string | null {
  const quality = asRecord(metadata?.quality);
  const qualityTone = asQualityTone(quality?.tone);
  const qualityReasons = Array.isArray(quality?.reasons)
    ? quality.reasons.filter((reason): reason is string => typeof reason === 'string' && reason.trim().length > 0)
    : [];
  if ((qualityTone === 'warn' || qualityTone === 'block') && qualityReasons.length > 0) {
    return qualityReasons[0];
  }
  const diagnostics = asRecord(metadata?.diagnostics);
  if (!diagnostics) return null;
  const joinHitRateEligible = asNumber(diagnostics.join_hit_rate_eligible);
  if (joinHitRateEligible !== null && joinHitRateEligible < 0.2) {
    return `eligible join hit-rate ${(joinHitRateEligible * 100).toFixed(1)}%`;
  }
  const joinHitRate = asNumber(diagnostics.join_hit_rate);
  if (joinHitRate !== null && joinHitRate < 0.2) {
    return `join hit-rate ${(joinHitRate * 100).toFixed(1)}%`;
  }
  const warnings = Array.isArray(diagnostics.warnings)
    ? diagnostics.warnings.filter((warning): warning is string => typeof warning === 'string')
    : [];
  if (warnings.length > 0) return warnings[0];
  return null;
}

function createFamilySummary(
  spec: FeedArtifactSpec,
  itemCount: number,
  status: string | null,
  asOf: string | null,
  canonicalTimeIso: string | null | undefined,
  topMover: string | null,
  strongestSignal: string | null,
  missingCoverage: string | null,
): FamilySummary {
  const freshness = estimateFreshness(asOf, canonicalTimeIso);
  return {
    family: spec.family as FinanceFamily,
    lane: spec.lane,
    itemCount,
    topMover,
    strongestSignal,
    staleStatus: itemCount === 0 ? 'missing' : freshness.tone,
    missingCoverage,
    status: status ?? 'missing',
    asOf,
    sourceNodeId: spec.nodeId,
  };
}

function artifactDisplayStatus(
  envelope: FeedArtifactEnvelope | null,
  metadata: Record<string, unknown> | null,
): string | null {
  const quality = asRecord(metadata?.quality);
  const qualityTone = asQualityTone(quality?.tone);
  if (qualityTone === 'warn' || qualityTone === 'block') return qualityTone;
  return asString(envelope?.status) ?? asString(metadata?.status);
}

function collectArtifactMetadata(
  spec: FeedArtifactSpec,
  artifacts: Record<string, FeedArtifactEnvelope>,
): {
  envelope: FeedArtifactEnvelope | null;
  metadata: Record<string, unknown> | null;
  status: string | null;
  asOf: string | null;
} {
  const envelope = artifacts[spec.nodeId] ?? null;
  const metadata = asRecord(envelope?.metadata);
  return {
    envelope,
    metadata,
    status: artifactDisplayStatus(envelope, metadata),
    asOf: asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
  };
}

export function clusterNewsRows(
  rows: Array<Record<string, unknown>>,
  asOfIso: string | null | undefined,
  canonicalTimeIso: string | null | undefined,
): NewsCluster[] {
  if (rows.length === 0) return [];

  const clusters = new Map<string, NewsCluster>();

  rows.forEach((row, index) => {
    const rawText = asString(row.text) ?? '';
    const headline = extractHeadline(rawText);
    const normalizedHeadline = normalizeHeadlineFingerprint(headline);
    const source = asString(row.source_label) ?? asString(row.source_handle) ?? 'Unknown';
    const time = asString(row.time);
    const url = asString(row.url);
    const category = asString(row.category);
    const affectedAssets = extractAffectedAssets(row, rawText);
    const item: NewsItem = {
      headline,
      source,
      time,
      url,
      rawText,
      affectedAssets,
      category,
    };
    const existing = clusters.get(normalizedHeadline);
    if (!existing) {
      clusters.set(normalizedHeadline, {
        id: `news:${index}:${normalizedHeadline}`,
        headline,
        normalizedHeadline,
        count: 1,
        latestTime: time,
        sources: [source],
        topSource: source,
        affectedAssets,
        summary: rawText.length > 180 ? `${rawText.slice(0, 177)}…` : rawText,
        items: [item],
        freshness: estimateFreshness(asOfIso, canonicalTimeIso),
        score: 1,
      });
      return;
    }

    existing.count += 1;
    existing.items.push(item);
    if (time && (!existing.latestTime || time > existing.latestTime)) existing.latestTime = time;
    if (!existing.sources.includes(source)) existing.sources.push(source);
    affectedAssets.forEach((asset) => {
      if (!existing.affectedAssets.includes(asset)) existing.affectedAssets.push(asset);
    });
    existing.score = existing.count;
  });

  return [...clusters.values()]
    .map((cluster) => {
      const sourceCounts = new Map<string, number>();
      cluster.items.forEach((item) => {
        sourceCounts.set(item.source, (sourceCounts.get(item.source) ?? 0) + 1);
      });
      const [topSource = cluster.sources[0] ?? 'Unknown'] =
        [...sourceCounts.entries()].sort((left, right) => right[1] - left[1])[0] ?? [];
      return {
        ...cluster,
        topSource,
        score: cluster.count * 3 + Math.min(cluster.affectedAssets.length, 3),
      };
    })
    .sort((left, right) => {
      if (right.score !== left.score) return right.score - left.score;
      return (right.latestTime ?? '').localeCompare(left.latestTime ?? '');
    });
}

export function clusterNewsItems(
  envelope: FeedArtifactEnvelope | null,
  canonicalTimeIso: string | null | undefined,
): NewsCluster[] {
  if (!envelope?.data) return [];
  const rows = buildRowsFromObjectList(envelope.data.items);
  return clusterNewsRows(
    rows,
    asString(envelope.metadata?.as_of) ?? asString(envelope.metadata?.timestamp_iso),
    canonicalTimeIso,
  );
}

export function extractPredictionRows(envelope: FeedArtifactEnvelope | null): PredictionRepricing[] {
  if (!envelope?.data) return [];
  const rows: PredictionRepricing[] = [];

  const rootEntries = Array.isArray(envelope.data)
    ? envelope.data
    : Object.entries(envelope.data).map(([key, value]) => ({ key, value }));

  rootEntries.forEach((entry, rootIndex) => {
    const record = asRecord(entry);
    if (!record) return;
    const category = asString(record.key) ?? `category_${rootIndex + 1}`;
    const bucketRecord = asRecord(record.value);
    if (!bucketRecord) return;

    Object.entries(bucketRecord).forEach(([bucket, rawSection]) => {
      const section = asRecord(rawSection);
      if (!section) return;
      const matrixRows = buildRowsFromMatrix(section.columns, section.rows);
      matrixRows.forEach((row, rowIndex) => {
        const question = asString(row.q);
        if (!question) return;
        const probability = asNumber(row.p);
        const probabilityDelta = asNumber(row.c);
        const volume = asNumber(row.v);
        const conviction = asNumber(row.s);
        const relatedAssets = extractKeywords(question).slice(0, 5);
        rows.push({
          id: `prediction:${category}:${bucket}:${rowIndex}`,
          category,
          bucket,
          question,
          outcome: asString(row.o),
          probability,
          probabilityDelta,
          volume,
          conviction,
          expiry: asString(row.expiry) ?? null,
          marketSource: `${category} / ${bucket}`,
          relatedAssets,
          slug: asString(row.slug),
          score:
            Math.abs(probabilityDelta ?? 0) * 120 +
            (conviction ?? 0) * 25 +
            Math.log10((volume ?? 1) + 1) * 8,
        });
      });
    });
  });

  return rows.sort((left, right) => right.score - left.score);
}

function matchRelatedNews(clusters: NewsCluster[], keywords: string[]): NewsCluster[] {
  if (keywords.length === 0) return [];
  const normalizedKeywords = keywords.map((keyword) => keyword.toLowerCase());
  return clusters
    .map((cluster) => {
      const haystack = `${cluster.headline} ${cluster.summary} ${cluster.affectedAssets.join(' ')}`.toLowerCase();
      const score = normalizedKeywords.reduce(
        (sum, keyword) => sum + (haystack.includes(keyword) ? 1 : 0),
        0,
      );
      return { cluster, score };
    })
    .filter((entry) => entry.score > 0)
    .sort((left, right) => right.score - left.score || right.cluster.score - left.cluster.score)
    .slice(0, 3)
    .map((entry) => entry.cluster);
}

function matchRelatedPredictions(
  repricings: PredictionRepricing[],
  keywords: string[],
): PredictionRepricing[] {
  if (keywords.length === 0) return [];
  const normalizedKeywords = keywords.map((keyword) => keyword.toLowerCase());
  return repricings
    .map((repricing) => {
      const haystack = `${repricing.question} ${repricing.marketSource} ${repricing.relatedAssets.join(' ')}`.toLowerCase();
      const score = normalizedKeywords.reduce(
        (sum, keyword) => sum + (haystack.includes(keyword) ? 1 : 0),
        0,
      );
      return { repricing, score };
    })
    .filter((entry) => entry.score > 0)
    .sort((left, right) => right.score - left.score || right.repricing.score - left.repricing.score)
    .slice(0, 3)
    .map((entry) => entry.repricing);
}

function describeClusterSummary(cluster: NewsCluster): string {
  const assetLabel =
    cluster.affectedAssets.length > 0 ? ` · ${cluster.affectedAssets.slice(0, 3).join(', ')}` : '';
  return `${cluster.topSource} · ${cluster.count} linked items${assetLabel}`;
}

function buildEquityEvents(
  spec: FeedArtifactSpec,
  envelope: FeedArtifactEnvelope | null,
  canonicalTimeIso: string | null | undefined,
  newsClusters: NewsCluster[],
  predictionRows: PredictionRepricing[],
): { events: AttentionEvent[]; summary: FamilySummary } {
  const metadata = asRecord(envelope?.metadata);
  const status = artifactDisplayStatus(envelope, metadata);
  const rows = envelope?.data ? buildRowsFromMatrix(envelope.data.columns, envelope.data.rows) : [];
  const freshness = estimateFreshness(
    asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
    canonicalTimeIso,
  );

  const ranked = rows
    .map((row) => {
      const ticker = asString(row.Ticker) ?? '?';
      const identity = asString(row.Identity) ?? asString(row.Proxy) ?? 'Identity unavailable';
      const price = asNumber(row.Price);
      const fiveDayMove = asNumber(row.Chg_5d);
      const zScore = asNumber(row.Z_Short);
      const keywords = [ticker, ...extractKeywords(identity)];
      const relatedNews = matchRelatedNews(newsClusters, keywords);
      const relatedPredictions = matchRelatedPredictions(predictionRows, keywords);
      const score = Math.abs(zScore ?? 0) * 14 + Math.abs(fiveDayMove ?? 0) * 1.8;
      return {
        ticker,
        identity,
        price,
        fiveDayMove,
        zScore,
        keywords,
        relatedNews,
        relatedPredictions,
        score,
      };
    })
    .filter((row) => row.zScore !== null || row.fiveDayMove !== null)
    .sort((left, right) => right.score - left.score);

  const events = ranked.slice(0, 3).map<AttentionEvent>((row, index) => ({
    id: `${spec.nodeId}:equity:${row.ticker}:${index}`,
    rank: 0,
    family: spec.family as FinanceFamily,
    assetClass: spec.family === 'ETF' ? 'ETF' : 'Equity',
    tickerOrLabel: row.ticker,
    headline:
      row.zScore !== null
        ? `${row.ticker} deviates materially from short-term trend`
        : `${row.ticker} is driving cross-asset attention`,
    primaryMetricLabel: row.zScore !== null ? '20d z-score' : '5d move',
    primaryMetricValue:
      row.zScore !== null ? formatZScore(row.zScore) : formatPercent(row.fiveDayMove, 'unit'),
    zScore: row.zScore,
    fiveDayMove: row.fiveDayMove,
    probability: null,
    probabilityDelta: null,
    relatedNews: row.relatedNews.length > 0 ? row.relatedNews[0].headline : row.relatedNews.length,
    confidence: confidenceForEvent(0.86, status, freshness),
    freshness,
    sourceNodeIds: [
      spec.nodeId,
      ...(row.relatedNews.length > 0 ? ['global_news_feed'] : []),
      ...(row.relatedPredictions.length > 0 ? ['global_polymarket_feed'] : []),
    ],
    secondaryMetricValue:
      row.fiveDayMove !== null ? formatPercent(row.fiveDayMove, 'unit') : null,
    secondaryMetricLabel: row.fiveDayMove !== null ? '5d move' : null,
    detail: {
      explanation: `${row.ticker} is the strongest ${spec.family === 'ETF' ? 'ETF' : 'equity'} dislocation in the selected snapshot, driven by ${row.zScore !== null ? `${formatZScore(row.zScore)} versus the 20-day trend` : 'price displacement'}${row.fiveDayMove !== null ? ` and a ${formatPercent(row.fiveDayMove, 'unit')} move over five sessions` : ''}.`,
      facts: [
        { label: 'Identity', value: row.identity },
        { label: 'Price', value: row.price !== null ? `$${row.price.toFixed(2)}` : '—' },
        { label: '5D', value: formatPercent(row.fiveDayMove, 'unit'), tone: row.fiveDayMove && row.fiveDayMove >= 0 ? 'positive' : row.fiveDayMove ? 'negative' : 'neutral' },
        { label: '20D z', value: formatZScore(row.zScore) },
      ],
      previewRows: ranked.slice(0, 4).map((preview) => ({
        primary: preview.ticker,
        secondary: formatZScore(preview.zScore),
        tertiary: formatPercent(preview.fiveDayMove, 'unit'),
        tone:
          (preview.fiveDayMove ?? 0) > 0
            ? 'positive'
            : (preview.fiveDayMove ?? 0) < 0
              ? 'negative'
              : 'neutral',
      })),
      relatedNews: row.relatedNews,
      relatedPredictions: row.relatedPredictions,
    },
    score: row.score,
    lane: spec.lane,
  }));

  const top = ranked[0];
  return {
    events,
    summary: createFamilySummary(
      spec,
      rows.length,
      status,
      asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
      canonicalTimeIso,
      top ? `${top.ticker} ${formatZScore(top.zScore)}` : null,
      top && top.fiveDayMove !== null ? `${formatPercent(top.fiveDayMove, 'unit')} in 5d` : null,
      topSummaryFromWarnings(metadata),
    ),
  };
}

function buildFlowEvents(
  spec: FeedArtifactSpec,
  envelope: FeedArtifactEnvelope | null,
  canonicalTimeIso: string | null | undefined,
  newsClusters: NewsCluster[],
  predictionRows: PredictionRepricing[],
): { events: AttentionEvent[]; summary: FamilySummary } {
  const metadata = asRecord(envelope?.metadata);
  const status = artifactDisplayStatus(envelope, metadata);
  const rows = envelope?.data ? buildRowsFromMatrix(envelope.data.columns, envelope.data.rows) : [];
  const freshness = estimateFreshness(
    asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
    canonicalTimeIso,
  );
  const sectorMap = asRecord(metadata?.sector_map);

  const ranked = rows
    .map((row) => {
      const ticker = asString(row.tkr) ?? '?';
      const flow = asNumber(row.flow);
      const shortVol = asNumber(row.sv);
      const winRate = asNumber(row.wr);
      const flags = asNumber(row.flg);
      const sectorId = asNumber(row.sec);
      const sector =
        sectorId !== null && sectorMap
          ? Object.entries(sectorMap).find(([, value]) => Number(value) === sectorId)?.[0] ?? 'Unknown'
          : asString(row.sec) ?? 'Unknown';
      const keywords = [ticker, sector];
      const score = Math.abs(flow ?? 0) / 2_500 + (flags ?? 0) * 2 + (winRate ?? 0) / 40;
      return {
        ticker,
        flow,
        shortVol,
        winRate,
        flags,
        sector,
        relatedNews: matchRelatedNews(newsClusters, keywords),
        relatedPredictions: matchRelatedPredictions(predictionRows, keywords),
        score,
      };
    })
    .filter((row) => row.flow !== null)
    .sort((left, right) => right.score - left.score);

  const events = ranked.slice(0, 3).map<AttentionEvent>((row, index) => ({
    id: `${spec.nodeId}:flow:${row.ticker}:${index}`,
    rank: 0,
    family: spec.family as FinanceFamily,
    assetClass: 'Flow',
    tickerOrLabel: row.ticker,
    headline: `${row.ticker} is printing the strongest flow imbalance`,
    primaryMetricLabel: 'Net flow',
    primaryMetricValue: formatCurrencyCompact(row.flow),
    zScore: null,
    fiveDayMove: null,
    probability: null,
    probabilityDelta: null,
    relatedNews: row.relatedNews.length > 0 ? row.relatedNews[0].headline : row.relatedNews.length,
    confidence: confidenceForEvent(0.78, status, freshness),
    freshness,
    sourceNodeIds: [
      spec.nodeId,
      ...(row.relatedNews.length > 0 ? ['global_news_feed'] : []),
      ...(row.relatedPredictions.length > 0 ? ['global_polymarket_feed'] : []),
    ],
    secondaryMetricValue: null,
    secondaryMetricLabel: null,
    detail: {
      explanation: `${row.ticker} is leading the flow tape with ${formatCurrencyCompact(row.flow)}${row.flags ? ` and signal flags ${row.flags}` : ''}. Coverage quality matters here because this feed can degrade when auxiliary joins miss.`,
      facts: [
        { label: 'Sector', value: row.sector },
        { label: 'Short vol', value: row.shortVol !== null ? `${row.shortVol.toFixed(0)}%` : '—' },
        { label: 'Win rate', value: row.winRate !== null ? `${row.winRate.toFixed(0)}%` : '—' },
        { label: 'Flags', value: row.flags !== null ? String(row.flags) : '—' },
      ],
      previewRows: ranked.slice(0, 4).map((preview) => ({
        primary: preview.ticker,
        secondary: formatCurrencyCompact(preview.flow),
        tertiary: preview.sector,
        tone:
          (preview.flow ?? 0) > 0
            ? 'positive'
            : (preview.flow ?? 0) < 0
              ? 'negative'
              : 'neutral',
      })),
      relatedNews: row.relatedNews,
      relatedPredictions: row.relatedPredictions,
    },
    score: row.score,
    lane: spec.lane,
  }));

  const top = ranked[0];
  return {
    events,
    summary: createFamilySummary(
      spec,
      rows.length,
      status,
      asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
      canonicalTimeIso,
      top ? `${top.ticker} ${formatCurrencyCompact(top.flow)}` : null,
      top ? `${top.sector}${top.flags ? ` · flags ${top.flags}` : ''}` : null,
      topSummaryFromWarnings(metadata),
    ),
  };
}

function buildMacroEvents(
  spec: FeedArtifactSpec,
  envelope: FeedArtifactEnvelope | null,
  canonicalTimeIso: string | null | undefined,
  newsClusters: NewsCluster[],
  predictionRows: PredictionRepricing[],
): { events: AttentionEvent[]; summary: FamilySummary } {
  const metadata = asRecord(envelope?.metadata);
  const status = artifactDisplayStatus(envelope, metadata);
  const rows = envelope?.data ? buildRowsFromMatrix(envelope.data.columns, envelope.data.rows) : [];
  const freshness = estimateFreshness(
    asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
    canonicalTimeIso,
  );

  const ranked = rows
    .map((row) => {
      const label = asString(row.ticker) ?? asString(row.Proxy) ?? '?';
      const recentChange = asNumber(row.recent_change);
      const pctChange = asNumber(row.pct_change);
      const recentChangeLabel =
        asString(row.recent_change_label) ??
        (pctChange !== null ? 'Legacy change' : 'Recent change');
      const displayChange =
        asString(row.display_change) ??
        (recentChange === null && pctChange !== null ? formatPercent(pctChange, 'ratio') : null);
      const zScore = asNumber(row.z_score);
      const keywords = extractKeywords(label);
      const moveMagnitude =
        recentChange !== null
          ? Math.log10(Math.abs(recentChange) + 1)
          : pctChange !== null
            ? Math.abs(pctChange) * 4
            : 0;
      return {
        label,
        recentChange,
        pctChange,
        recentChangeLabel,
        displayChange,
        zScore,
        score: Math.abs(zScore ?? 0) * 12 + moveMagnitude * 4,
        relatedNews: matchRelatedNews(newsClusters, keywords),
        relatedPredictions: matchRelatedPredictions(predictionRows, keywords),
      };
    })
    .filter((row) => row.zScore !== null || row.recentChange !== null || row.pctChange !== null)
    .sort((left, right) => right.score - left.score);

  const events = ranked.slice(0, 3).map<AttentionEvent>((row, index) => ({
    id: `${spec.nodeId}:macro:${row.label}:${index}`,
    rank: 0,
    family: spec.family as FinanceFamily,
    assetClass: 'Macro',
    tickerOrLabel: row.label,
    headline: `${row.label} is the strongest macro outlier`,
    primaryMetricLabel: 'Signal z-score',
    primaryMetricValue: formatZScore(row.zScore),
    zScore: row.zScore,
    fiveDayMove: row.recentChange ?? row.pctChange,
    probability: null,
    probabilityDelta: null,
    relatedNews: row.relatedNews.length > 0 ? row.relatedNews[0].headline : row.relatedNews.length,
    confidence: confidenceForEvent(0.82, status, freshness),
    freshness,
    sourceNodeIds: [
      spec.nodeId,
      ...(row.relatedNews.length > 0 ? ['global_news_feed'] : []),
      ...(row.relatedPredictions.length > 0 ? ['global_polymarket_feed'] : []),
    ],
    secondaryMetricValue:
      row.displayChange ??
      (row.recentChange !== null ? formatMacroDisplayChange(row.recentChange) : null),
    secondaryMetricLabel:
      row.recentChange !== null || row.pctChange !== null ? row.recentChangeLabel : null,
    detail: {
      explanation: `${row.label} is leading the macro board on standardized dispersion${row.recentChange !== null ? ` with ${(row.displayChange ?? formatMacroDisplayChange(row.recentChange))} on the last observation` : row.pctChange !== null ? ` with ${formatPercent(row.pctChange, 'ratio')} from the historical baseline` : ''}.`,
      facts: [
        { label: 'Signal', value: formatZScore(row.zScore) },
        {
          label: row.recentChangeLabel,
          value:
            row.displayChange ??
            (row.recentChange !== null ? formatMacroDisplayChange(row.recentChange) : '—'),
          tone:
            (row.recentChange ?? row.pctChange) && (row.recentChange ?? row.pctChange)! >= 0
              ? 'positive'
              : (row.recentChange ?? row.pctChange)
                ? 'negative'
                : 'neutral',
        },
      ],
      previewRows: ranked.slice(0, 4).map((preview) => ({
        primary: preview.label,
        secondary: formatZScore(preview.zScore),
        tertiary:
          preview.displayChange ??
          (preview.recentChange !== null ? formatMacroDisplayChange(preview.recentChange) : '—'),
        tone:
          (preview.recentChange ?? preview.pctChange ?? 0) > 0
            ? 'positive'
            : (preview.recentChange ?? preview.pctChange ?? 0) < 0
              ? 'negative'
              : 'neutral',
      })),
      relatedNews: row.relatedNews,
      relatedPredictions: row.relatedPredictions,
    },
    score: row.score,
    lane: spec.lane,
  }));

  const top = ranked[0];
  return {
    events,
    summary: createFamilySummary(
      spec,
      rows.length,
      status,
      asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
      canonicalTimeIso,
      top ? `${top.label} ${formatZScore(top.zScore)}` : null,
      top && (top.recentChange !== null || top.pctChange !== null)
        ? `${top.displayChange ?? (top.recentChange !== null ? formatMacroDisplayChange(top.recentChange) : '—')} ${top.recentChangeLabel.toLowerCase()}`
        : null,
      topSummaryFromWarnings(metadata),
    ),
  };
}

function buildNewsEvents(
  spec: FeedArtifactSpec,
  envelope: FeedArtifactEnvelope | null,
  canonicalTimeIso: string | null | undefined,
): { events: AttentionEvent[]; summary: FamilySummary; clusters: NewsCluster[] } {
  const metadata = asRecord(envelope?.metadata);
  const status = artifactDisplayStatus(envelope, metadata);
  const clusters = clusterNewsItems(envelope, canonicalTimeIso);
  const freshness = estimateFreshness(
    asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
    canonicalTimeIso,
  );

  const events = clusters.slice(0, 3).map<AttentionEvent>((cluster, index) => ({
    id: `${spec.nodeId}:news:${cluster.id}:${index}`,
    rank: 0,
    family: spec.family as FinanceFamily,
    assetClass: 'News',
    tickerOrLabel: cluster.affectedAssets[0] ?? cluster.topSource,
    headline: cluster.headline,
    primaryMetricLabel: 'Coverage',
    primaryMetricValue: `${cluster.count} hits`,
    zScore: null,
    fiveDayMove: null,
    probability: null,
    probabilityDelta: null,
    relatedNews: cluster.count,
    confidence: confidenceForEvent(0.72, status, freshness),
    freshness: cluster.freshness,
    sourceNodeIds: [spec.nodeId],
    secondaryMetricValue: null,
    secondaryMetricLabel: null,
    detail: {
      explanation: `${cluster.headline} is the densest narrative cluster in the selected news tape, spanning ${cluster.count} linked items across ${cluster.sources.length} sources.`,
      facts: [
        { label: 'Top source', value: cluster.topSource },
        { label: 'Items', value: String(cluster.count) },
        { label: 'Assets', value: cluster.affectedAssets.slice(0, 4).join(', ') || '—' },
      ],
      previewRows: cluster.items.slice(0, 4).map((item) => ({
        primary: item.source,
        secondary: item.time,
        tertiary: item.headline,
        tone: 'neutral',
      })),
      relatedNews: [cluster],
      relatedPredictions: [],
    },
    score: cluster.score * 4,
    lane: spec.lane,
  }));

  const top = clusters[0];
  return {
    events,
    clusters,
    summary: createFamilySummary(
      spec,
      clusters.reduce((sum, cluster) => sum + cluster.count, 0),
      status,
      asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
      canonicalTimeIso,
      top ? `${top.count} linked items` : null,
      top ? describeClusterSummary(top) : null,
      topSummaryFromWarnings(metadata),
    ),
  };
}

function buildPredictionEvents(
  spec: FeedArtifactSpec,
  envelope: FeedArtifactEnvelope | null,
  canonicalTimeIso: string | null | undefined,
  newsClusters: NewsCluster[],
): { events: AttentionEvent[]; summary: FamilySummary; repricings: PredictionRepricing[] } {
  const metadata = asRecord(envelope?.metadata);
  const status = artifactDisplayStatus(envelope, metadata);
  const repricings = extractPredictionRows(envelope);
  const freshness = estimateFreshness(
    asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
    canonicalTimeIso,
  );

  const events = repricings.slice(0, 4).map<AttentionEvent>((repricing, index) => {
    const relatedNews = matchRelatedNews(newsClusters, [
      ...repricing.relatedAssets,
      ...extractKeywords(repricing.question),
    ]);
    return {
      id: `${spec.nodeId}:prediction:${repricing.id}:${index}`,
      rank: 0,
      family: spec.family as FinanceFamily,
      assetClass: 'Prediction',
      tickerOrLabel: repricing.relatedAssets[0] ?? repricing.category,
      headline: repricing.question,
      primaryMetricLabel: '24h repricing',
      primaryMetricValue: formatPercent(repricing.probabilityDelta, 'ratio'),
      zScore: null,
      fiveDayMove: null,
      probability: repricing.probability,
      probabilityDelta: repricing.probabilityDelta,
      relatedNews: relatedNews.length > 0 ? relatedNews[0].headline : relatedNews.length,
      confidence: confidenceForEvent(0.76, status, freshness),
      freshness,
      sourceNodeIds: [spec.nodeId, ...(relatedNews.length > 0 ? ['global_news_feed'] : [])],
      secondaryMetricValue:
        repricing.probabilityDelta !== null
          ? `${repricing.probabilityDelta >= 0 ? '+' : ''}${(repricing.probabilityDelta * 100).toFixed(1)} pts`
          : null,
      secondaryMetricLabel: repricing.probabilityDelta !== null ? 'repricing' : null,
      detail: {
        explanation: `${repricing.question} is the sharpest prediction-market repricing in the selected snapshot${repricing.volume !== null ? ` on ${formatCurrencyCompact(repricing.volume)} of 24h volume` : ''}.`,
        facts: [
          { label: 'Probability', value: formatProbability(repricing.probability) },
          { label: '24h Δ', value: formatPercent(repricing.probabilityDelta, 'ratio'), tone: (repricing.probabilityDelta ?? 0) >= 0 ? 'positive' : 'negative' },
          { label: 'Volume', value: repricing.volume !== null ? `$${formatCompactNumber(repricing.volume)}` : '—' },
          { label: 'Bucket', value: repricing.marketSource },
        ],
        previewRows: repricings.slice(0, 4).map((preview) => ({
          primary: preview.question,
          secondary: formatProbability(preview.probability),
          tertiary: formatPercent(preview.probabilityDelta, 'ratio'),
          tone:
            (preview.probabilityDelta ?? 0) > 0
              ? 'positive'
              : (preview.probabilityDelta ?? 0) < 0
                ? 'negative'
                : 'neutral',
        })),
        relatedNews,
        relatedPredictions: repricings
          .filter((candidate) => candidate.id !== repricing.id)
          .slice(0, 3),
      },
      score: repricing.score,
      lane: spec.lane,
    };
  });

  const top = repricings[0];
  return {
    events,
    repricings,
    summary: createFamilySummary(
      spec,
      repricings.length,
      status,
      asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
      canonicalTimeIso,
      top ? formatPercent(top.probabilityDelta, 'ratio') : null,
      top ? `${top.question.slice(0, 52)}${top.question.length > 52 ? '…' : ''}` : null,
      topSummaryFromWarnings(metadata),
    ),
  };
}

function buildDerivedEvents(
  spec: FeedArtifactSpec,
  envelope: FeedArtifactEnvelope | null,
  canonicalTimeIso: string | null | undefined,
  newsClusters: NewsCluster[],
  predictionRows: PredictionRepricing[],
): { events: AttentionEvent[]; summary: FamilySummary } {
  const metadata = asRecord(envelope?.metadata);
  const status = artifactDisplayStatus(envelope, metadata);
  const rows: Array<Record<string, unknown>> = envelope?.data
    ? Object.entries(envelope.data).flatMap(([laneKey, block]) =>
        buildCalculatorRows(block).map((row) => ({ ...row, Lane: laneKey })),
      )
    : [];
  const insights = deriveCalculatorClusterInsights(envelope);
  const freshness = estimateFreshness(
    asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
    canonicalTimeIso,
  );

  const ranked = insights
    .map((insight) => {
      const keywords = [
        insight.cluster,
        insight.thesis.dominantSignal ?? '',
        insight.laneKey,
        ...insight.members.slice(0, 8),
      ];
      const score = (insight.thesis.opportunityScore ?? 0) * 5 + (insight.thesis.energy ?? 0);
      return {
        insight,
        score,
        relatedNews: matchRelatedNews(newsClusters, keywords),
        relatedPredictions: matchRelatedPredictions(predictionRows, keywords),
      };
    })
    .sort((left, right) => right.score - left.score);

  const events = ranked.slice(0, 3).map<AttentionEvent>((row, index) => {
    const insight = row.insight;
    const signalQuality =
      insight.confidence.find((component) => component.key === 'Signal_Quality')?.value ?? null;
    const opportunity = insight.thesis.opportunityScore;
    const polarity = insight.thesis.polarity;
    const strongestEvidence = insight.evidence[0];
    return {
      id: `${spec.nodeId}:derived:${insight.laneKey}:${insight.cluster}:${index}`,
      rank: 0,
      family: spec.family as FinanceFamily,
      assetClass: insight.modeLabel,
      tickerOrLabel: insight.label,
      headline: `${insight.label} is the top ${insight.modeLabel.toLowerCase()}`,
      primaryMetricLabel: 'Opportunity',
      primaryMetricValue: opportunity !== null ? opportunity.toFixed(2) : '—',
      zScore: null,
      fiveDayMove: null,
      probability: null,
      probabilityDelta: null,
      relatedNews: row.relatedNews.length > 0 ? row.relatedNews[0].headline : row.relatedNews.length,
      confidence: confidenceForEvent(signalQuality ?? 0.7, status, freshness),
      freshness,
      sourceNodeIds: [spec.nodeId, ...(row.relatedNews.length > 0 ? ['global_news_feed'] : [])],
      secondaryMetricValue: signalQuality !== null ? `${Math.round(signalQuality * 100)}%` : null,
      secondaryMetricLabel: signalQuality !== null ? 'signal quality' : null,
      detail: {
        explanation: `${insight.label} ranks by Opportunity_Score, with ${insight.thesis.directionLabel} polarity and ${strongestEvidence ? strongestEvidence.label : insight.thesis.dominantSignal ?? 'the dominant signal'} carrying the strongest normalized evidence.`,
        facts: [
          { label: 'Opportunity', value: opportunity !== null ? opportunity.toFixed(2) : '—' },
          { label: 'Energy', value: insight.thesis.energy !== null ? insight.thesis.energy.toFixed(2) : '—' },
          {
            label: 'Polarity',
            value: polarity !== null ? polarity.toFixed(2) : '—',
            tone: (polarity ?? 0) > 0 ? 'positive' : (polarity ?? 0) < 0 ? 'negative' : 'neutral',
          },
          { label: 'Dominant signal', value: insight.thesis.dominantSignal ?? '—' },
        ],
        previewRows: ranked.slice(0, 4).map((preview) => ({
          primary: preview.insight.label,
          secondary:
            preview.insight.thesis.opportunityScore !== null
              ? preview.insight.thesis.opportunityScore.toFixed(2)
              : '—',
          tertiary: preview.insight.thesis.dominantSignal ?? preview.insight.laneKey,
          tone:
            (preview.insight.thesis.polarity ?? 0) > 0
              ? 'positive'
              : (preview.insight.thesis.polarity ?? 0) < 0
                ? 'negative'
                : 'neutral',
        })),
        relatedNews: row.relatedNews,
        relatedPredictions: row.relatedPredictions,
        calculatorInsight: insight,
      },
      score: row.score,
      lane: spec.lane,
    };
  });

  const top = ranked[0];
  return {
    events,
    summary: createFamilySummary(
      spec,
      rows.length,
      status,
      asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso),
      canonicalTimeIso,
      top && top.insight.thesis.opportunityScore !== null
        ? `${top.insight.label} ${top.insight.thesis.opportunityScore.toFixed(2)}`
        : null,
      top ? `${top.insight.thesis.dominantSignal ?? 'signal unknown'} · ${top.insight.size ?? 0} members` : null,
      topSummaryFromWarnings(metadata),
    ),
  };
}

function rankEvents(events: AttentionEvent[]): AttentionEvent[] {
  return [...events]
    .sort((left, right) => right.score - left.score)
    .slice(0, 10)
    .map((event, index) => ({ ...event, rank: index + 1 }));
}

function buildHealth(
  familySummaries: FamilySummary[],
  canonicalTimeIso: string | null | undefined,
  selectedRunStatus: string | null | undefined,
): DataHealth {
  const staleFamilies = familySummaries
    .filter((summary) => summary.staleStatus === 'lagging' || summary.staleStatus === 'stale')
    .map((summary) => summary.family);
  const missingFamilies = familySummaries
    .filter((summary) => summary.itemCount === 0 || summary.status === 'missing')
    .map((summary) => summary.family);
  const nonSuccessSources = familySummaries
    .filter((summary) => summary.status !== 'success' && summary.status !== 'missing')
    .map((summary) => summary.family);

  const alerts: string[] = [];
  if (selectedRunStatus && selectedRunStatus !== 'green') {
    alerts.push(`Selected run is ${selectedRunStatus.toUpperCase()}`);
  }
  if (staleFamilies.length > 0) {
    alerts.push(`Freshness lag in ${staleFamilies.join(', ')}`);
  }
  if (missingFamilies.length > 0) {
    alerts.push(`Coverage missing in ${missingFamilies.join(', ')}`);
  }
  familySummaries.forEach((summary) => {
    if (summary.missingCoverage) {
      alerts.push(`${summary.family}: ${summary.missingCoverage}`);
    }
  });
  if (!canonicalTimeIso) {
    alerts.push('Canonical time missing');
  }

  let overallTone: HealthTone = 'ok';
  if (!selectedRunStatus && familySummaries.length === 0) overallTone = 'unknown';
  if (selectedRunStatus === 'red' || missingFamilies.length >= 2) overallTone = 'block';
  else if (
    selectedRunStatus === 'amber' ||
    staleFamilies.length > 0 ||
    nonSuccessSources.length > 0 ||
    familySummaries.some((summary) => Boolean(summary.missingCoverage))
  ) {
    overallTone = 'warn';
  }

  return {
    overallTone,
    staleFamilies,
    missingFamilies,
    nonSuccessSources,
    canonicalTime: canonicalTimeIso ?? null,
    selectedRunStatus: selectedRunStatus ?? null,
    alertCount: alerts.length,
    alerts,
  };
}

export function deriveFinancePresentation({
  artifacts,
  canonicalTimeIso = null,
  selectedRunStatus = null,
}: PresentationInput): FinancePresentationModel {
  const newsSpec = FEED_ARTIFACT_SPECS.find((spec) => spec.family === 'News')!;
  const predictionSpec = FEED_ARTIFACT_SPECS.find((spec) => spec.family === 'Prediction')!;
  const newsEnvelope = artifacts[newsSpec.nodeId] ?? null;
  const predictionEnvelope = artifacts[predictionSpec.nodeId] ?? null;
  const newsClusters = clusterNewsItems(newsEnvelope, canonicalTimeIso);
  const predictionRepricings = extractPredictionRows(predictionEnvelope);

  const allEvents: AttentionEvent[] = [];
  const familySummaries: FamilySummary[] = [];

  FEED_ARTIFACT_SPECS.forEach((spec) => {
    const { envelope } = collectArtifactMetadata(spec, artifacts);
    if (spec.family === 'Equities' || spec.family === 'ETF') {
      const result = buildEquityEvents(
        spec,
        envelope,
        canonicalTimeIso,
        newsClusters,
        predictionRepricings,
      );
      allEvents.push(...result.events);
      familySummaries.push(result.summary);
      return;
    }
    if (spec.family === 'Flow') {
      const result = buildFlowEvents(
        spec,
        envelope,
        canonicalTimeIso,
        newsClusters,
        predictionRepricings,
      );
      allEvents.push(...result.events);
      familySummaries.push(result.summary);
      return;
    }
    if (spec.family === 'Macro') {
      const result = buildMacroEvents(
        spec,
        envelope,
        canonicalTimeIso,
        newsClusters,
        predictionRepricings,
      );
      allEvents.push(...result.events);
      familySummaries.push(result.summary);
      return;
    }
    if (spec.family === 'News') {
      const result = buildNewsEvents(spec, envelope, canonicalTimeIso);
      allEvents.push(...result.events);
      familySummaries.push(result.summary);
      return;
    }
    if (spec.family === 'Prediction') {
      const result = buildPredictionEvents(spec, envelope, canonicalTimeIso, newsClusters);
      allEvents.push(...result.events);
      familySummaries.push(result.summary);
      return;
    }
    if (spec.family === 'Derived') {
      const result = buildDerivedEvents(
        spec,
        envelope,
        canonicalTimeIso,
        newsClusters,
        predictionRepricings,
      );
      allEvents.push(...result.events);
      familySummaries.push(result.summary);
    }
  });

  const rankedEvents = rankEvents(allEvents);
  const familySummaryMap = Object.fromEntries(
    familySummaries.map((summary) => [summary.family, summary]),
  );

  return {
    attentionEvents: rankedEvents,
    familySummaries,
    familySummaryMap,
    newsClusters,
    predictionRepricings,
    health: buildHealth(familySummaries, canonicalTimeIso, selectedRunStatus),
  };
}
