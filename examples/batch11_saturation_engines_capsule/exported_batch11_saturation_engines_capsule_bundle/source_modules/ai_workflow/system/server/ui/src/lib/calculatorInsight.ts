import { asArray, asRecord } from '../components/views/dataViewUtils';

export type CalculatorMetricBucket = 'directional' | 'dispersion' | 'risk' | 'structural' | 'unknown';
export type CalculatorInsightTone = 'positive' | 'negative' | 'neutral' | 'warning';

export interface CalculatorBucketDriver {
  bucket: CalculatorMetricBucket;
  label: string;
  value: number;
  share: number;
}

export interface CalculatorScoreComponent {
  key: string;
  label: string;
  value: number | null;
  description: string | null;
}

export interface CalculatorMetricEvidence {
  key: string;
  label: string;
  bucket: CalculatorMetricBucket;
  raw: number | null;
  normalized: number | null;
  description: string | null;
}

export interface CalculatorDiagnosticNote {
  label: string;
  value: string;
  tone: CalculatorInsightTone;
}

export interface CalculatorClusterInsight {
  id: string;
  laneKey: string;
  modeLabel: string;
  cluster: string;
  label: string;
  rank: number;
  members: string[];
  size: number | null;
  thesis: {
    opportunityScore: number | null;
    energy: number | null;
    polarity: number | null;
    dominantSignal: string | null;
    directionLabel: string;
  };
  drivers: CalculatorBucketDriver[];
  scoreFormula: CalculatorScoreComponent[];
  confidence: CalculatorScoreComponent[];
  evidence: CalculatorMetricEvidence[];
  diagnostics: CalculatorDiagnosticNote[];
  provenance: {
    schemaVersion: string | null;
    asOf: string | null;
    rankMethod: string | null;
  };
  nextInspectionHints: string[];
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function humanizeKey(value: string): string {
  return value.replace(/_/g, ' ');
}

function titleLabel(value: string): string {
  return humanizeKey(value)
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');
}

function normalizeBucket(value: unknown): CalculatorMetricBucket | null {
  if (
    value === 'directional' ||
    value === 'dispersion' ||
    value === 'risk' ||
    value === 'structural'
  ) {
    return value;
  }
  return null;
}

function inferBucket(metricKey: string): CalculatorMetricBucket {
  const key = metricKey.trim().toLowerCase();
  if (!key) return 'unknown';
  if (key.includes('sample_size') || key.includes('price_level') || key.includes('price_dispersion')) {
    return 'structural';
  }
  if (key.includes('vol_') || key.includes('volatility')) return 'risk';
  if (key.includes('dispersion')) return 'dispersion';
  return 'directional';
}

function getMetricSemantics(
  metadata: Record<string, unknown> | null,
  metricKey: string,
): Record<string, unknown> | null {
  const catalog = asRecord(metadata?.metric_semantics);
  if (!catalog) return null;
  return asRecord(catalog[metricKey]) ?? asRecord(catalog[metricKey.toLowerCase()]);
}

function metricBucket(metadata: Record<string, unknown> | null, metricKey: string): CalculatorMetricBucket {
  const semantics = getMetricSemantics(metadata, metricKey);
  return normalizeBucket(semantics?.bucket) ?? inferBucket(metricKey);
}

function metricDescription(metadata: Record<string, unknown> | null, metricKey: string): string | null {
  const semantics = getMetricSemantics(metadata, metricKey);
  const description = asString(semantics?.description);
  if (description) return description;
  const legend = asRecord(metadata?.legend);
  return asString(legend?.[metricKey]) ?? asString(legend?.[metricKey.toLowerCase()]);
}

function metricValue(record: Record<string, unknown>, key: string): number | null {
  return asNumber(record[key]) ?? asNumber(record[humanizeKey(key)]);
}

function scoreComponent(
  metrics: Record<string, unknown>,
  key: string,
  label: string,
  description: string | null,
): CalculatorScoreComponent {
  return {
    key,
    label,
    value: asNumber(metrics[key]),
    description,
  };
}

function driverShare(value: number, total: number): number {
  if (total <= 0) return 0;
  return Math.max(0, Math.min(1, value / total));
}

function buildDrivers(metrics: Record<string, unknown>): CalculatorBucketDriver[] {
  const driverDefs: Array<[CalculatorMetricBucket, string, string]> = [
    ['directional', 'Directional', 'Directional_Energy'],
    ['dispersion', 'Dispersion', 'Dispersion_Energy'],
    ['risk', 'Risk', 'Risk_Energy'],
    ['structural', 'Structural', 'Structural_Energy'],
  ];
  const values = driverDefs.map(([bucket, label, key]) => ({
    bucket,
    label,
    value: asNumber(metrics[key]) ?? 0,
  }));
  const total = values.reduce((sum, driver) => sum + Math.max(driver.value, 0), 0);
  return values.map((driver) => ({
    ...driver,
    share: driverShare(Math.max(driver.value, 0), total),
  }));
}

function buildEvidence(
  payload: Record<string, unknown>,
  metadata: Record<string, unknown> | null,
): CalculatorMetricEvidence[] {
  const raw = asRecord(payload.metrics_raw) ?? {};
  const normalized = asRecord(payload.metrics_norm) ?? {};
  const keys = new Set([...Object.keys(raw), ...Object.keys(normalized)]);
  return [...keys]
    .map((key) => ({
      key,
      label: titleLabel(key),
      bucket: metricBucket(metadata, key),
      raw: asNumber(raw[key]),
      normalized: asNumber(normalized[key]),
      description: metricDescription(metadata, key),
    }))
    .sort((left, right) => Math.abs(right.normalized ?? 0) - Math.abs(left.normalized ?? 0));
}

function buildDiagnostics(metadata: Record<string, unknown> | null): CalculatorDiagnosticNote[] {
  const diagnostics = asRecord(metadata?.diagnostics);
  if (!diagnostics) return [];
  const notes: CalculatorDiagnosticNote[] = [];
  const warnings = asArray(diagnostics.warnings)
    .map((item) => String(item).trim())
    .filter(Boolean);
  warnings.slice(0, 3).forEach((warning) => {
    notes.push({ label: 'Warning', value: warning, tone: 'warning' });
  });

  const imputedUses =
    asNumber(diagnostics.imputed_metric_use_count) ?? asNumber(diagnostics.imputed_nan_count);
  if (imputedUses && imputedUses > 0) {
    notes.push({
      label: 'Imputation',
      value: `${imputedUses.toLocaleString()} metric input uses imputed`,
      tone: 'warning',
    });
  }

  const droppedRows = asNumber(diagnostics.dropped_row_count) ?? asNumber(diagnostics.dropped_rows);
  if (droppedRows && droppedRows > 0) {
    notes.push({
      label: 'Dropped rows',
      value: `${droppedRows.toLocaleString()} source rows removed`,
      tone: 'warning',
    });
  }

  return notes;
}

function confidenceComponents(metrics: Record<string, unknown>): CalculatorScoreComponent[] {
  return [
    scoreComponent(metrics, 'Signal_Quality', 'Signal quality', 'Combined purity, member quality, and size confidence.'),
    scoreComponent(metrics, 'Size_Confidence', 'Size confidence', 'Effective breadth-adjusted cluster size confidence.'),
    scoreComponent(metrics, 'Cohesion', 'Cohesion', 'Mean member alignment with the cluster centroid.'),
    scoreComponent(metrics, 'Participation_Rate', 'Participation', 'Share of members aligned with the cluster centroid.'),
    scoreComponent(metrics, 'Effective_Breadth', 'Breadth', 'Distribution breadth of member contribution.'),
  ];
}

function scoreFormula(metrics: Record<string, unknown>): CalculatorScoreComponent[] {
  const cohesion = asNumber(metrics.Cohesion) ?? 0;
  const participation = asNumber(metrics.Participation_Rate) ?? 0;
  const memberQuality = Math.sqrt(Math.max(0, cohesion * participation));
  return [
    scoreComponent(metrics, 'Thrust_Score', 'Thrust', 'Directional energy after concentration and breadth weighting.'),
    scoreComponent(metrics, 'Purity', 'Purity', 'Share of useful directional energy after non-directional penalties.'),
    { key: 'Member_Quality', label: 'Member quality', value: memberQuality, description: 'Derived from cohesion and participation.' },
    scoreComponent(metrics, 'Size_Confidence', 'Size confidence', 'Effective breadth-adjusted cluster size confidence.'),
  ];
}

function directionLabel(polarity: number | null): string {
  if (polarity === null || Math.abs(polarity) < 0.001) return 'balanced';
  return polarity > 0 ? 'pro-risk / upside' : 'defensive / downside';
}

function modeLabel(laneKey: string): string {
  if (laneKey.toLowerCase() === 'macro') return 'Regime lens';
  if (laneKey.toLowerCase() === 'etf') return 'ETF thesis lens';
  return 'Equity thesis lens';
}

function buildNextInspectionHints(
  insightLabel: string,
  evidence: CalculatorMetricEvidence[],
  confidence: CalculatorScoreComponent[],
): string[] {
  const strongest = evidence[0];
  const weakestConfidence = confidence
    .filter((component) => component.value !== null)
    .sort((left, right) => (left.value ?? 1) - (right.value ?? 1))[0];
  return [
    strongest
      ? `Inspect ${strongest.label} (${strongest.bucket}) against raw member rows.`
      : `Inspect ${insightLabel} source rows.`,
    weakestConfidence
      ? `Check ${weakestConfidence.label.toLowerCase()} before treating the rank as stable.`
      : 'Check confidence components before treating the rank as stable.',
  ];
}

export function deriveCalculatorClusterInsights(envelope: {
  metadata?: unknown;
  data?: Record<string, unknown> | null;
} | null | undefined): CalculatorClusterInsight[] {
  const metadata = asRecord(envelope?.metadata);
  const data = asRecord(envelope?.data);
  if (!data) return [];

  const diagnostics = buildDiagnostics(metadata);
  const schemaVersion = asString(metadata?.data_schema_version) ?? asString(metadata?.schema_version);
  const asOf = asString(metadata?.as_of) ?? asString(metadata?.timestamp_iso);
  const legend = asRecord(metadata?.legend);
  const rankMethod = asString(legend?.rank_method);
  const insights: CalculatorClusterInsight[] = [];

  Object.entries(data).forEach(([laneKey, laneBlock]) => {
    asArray(laneBlock).forEach((entry, index) => {
      if (!Array.isArray(entry) || entry.length < 2) return;
      const cluster = String(entry[0]);
      const payload = asRecord(entry[1]);
      if (!payload) return;

      const members = asArray(payload.members).map((member) => String(member));
      const metrics = asRecord(payload.metrics) ?? {};
      const evidence = buildEvidence(payload, metadata);
      const confidence = confidenceComponents(metrics);
      const label = humanizeKey(cluster);
      const polarity = asNumber(payload.Polarity);
      const opportunityScore = metricValue(metrics, 'Opportunity_Score');
      const energy = asNumber(payload.Energy);

      insights.push({
        id: `${laneKey}:${cluster}:${index}`,
        laneKey,
        modeLabel: modeLabel(laneKey),
        cluster,
        label,
        rank: index + 1,
        members,
        size: asNumber(payload.Size) ?? members.length,
        thesis: {
          opportunityScore,
          energy,
          polarity,
          dominantSignal: asString(payload.Dominant_Signal),
          directionLabel: directionLabel(polarity),
        },
        drivers: buildDrivers(metrics),
        scoreFormula: scoreFormula(metrics),
        confidence,
        evidence,
        diagnostics,
        provenance: {
          schemaVersion,
          asOf,
          rankMethod,
        },
        nextInspectionHints: buildNextInspectionHints(label, evidence, confidence),
      });
    });
  });

  return insights.sort((left, right) => {
    const leftScore = left.thesis.opportunityScore ?? left.thesis.energy ?? 0;
    const rightScore = right.thesis.opportunityScore ?? right.thesis.energy ?? 0;
    return rightScore - leftScore;
  });
}
