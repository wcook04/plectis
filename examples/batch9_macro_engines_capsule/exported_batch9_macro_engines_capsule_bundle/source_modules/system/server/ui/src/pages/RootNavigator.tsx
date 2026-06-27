import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import ReactFlow, {
  Background,
  BackgroundVariant,
  Handle,
  Position,
  ReactFlowProvider,
  useNodesInitialized,
  useReactFlow,
  type Edge as RfEdge,
  type Node as RfNode,
  type NodeProps,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { withReturnToQuery } from '../navigation/turnaround';
import {
  deriveRouteGateViability,
  deriveRouteGateViabilityFromGraph,
  type NavigationGraphProjection,
  type RouteGateViability,
} from '../navigation/routeGateSnapshot';
import { useZenith } from '../stores/useZenith';
import type { LucideIcon } from 'lucide-react';
import clsx from 'clsx';
import {
  AlertTriangle,
  Archive,
  BookOpen,
  Boxes,
  Compass,
  Database,
  Eye,
  ExternalLink,
  FileJson2,
  FileText,
  GitBranch,
  Layers,
  Network,
  Orbit,
  Package,
  ReceiptText,
  RefreshCw,
  Route as RouteIcon,
  Search,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  Workflow,
} from 'lucide-react';
import {
  api,
  type NavigationSurfacePacket,
  type CodexFileDetail,
  type RootCoverageRow,
  type RootCoverageState,
  type RootNavigatorHandoffPacket,
  type RootNavigatorPrimitiveAxis,
  type RootNavigatorPrimitiveRow,
  type RootNavigatorSceneDomainExplainer,
  type WorldModelFamilyPrinciple,
} from '../api';
import CopyButton from '../components/meta/CopyButton';
import { SYSTEM_ATLAS_KIND_ORDER } from '../components/system-atlas/systemAtlasKindOrder';

const SystemAtlasGraph = lazy(() => import('../components/system-atlas/SystemAtlasGraph'));
const DOCTRINE_KINDS = SYSTEM_ATLAS_KIND_ORDER;

const ATLAS_KIND_FROM_PRIMITIVE: Record<string, string> = {
  principles: 'Principle',
  standards: 'Standard',
  paper_modules: 'PaperModule',
  concepts: 'Concept',
  mechanisms: 'Mechanism',
  frontend_views: 'FrontendView',
  frontend_components: 'FrontendView',
  system_atlas: 'Domain',
  task_ledger: 'WorkItem',
  raw_seed_shards: 'Principle',
  axiom_candidates: 'Principle',
};

type UnknownRow = Record<string, unknown>;
type InspectorTab = 'Summary' | 'Relations' | 'Evidence' | 'Agent route' | 'Raw';
type StateAxisTone = 'green' | 'partial' | 'stale' | 'missing' | 'neutral';

const INSPECTOR_TAB_ORDER: InspectorTab[] = ['Summary', 'Relations', 'Evidence', 'Agent route', 'Raw'];

const HEALTHY_STATUSES = new Set(['green', 'active', 'up_to_date', 'available', 'loaded', 'option_surface_supported']);

const ROOT_ACTIONS = [
  { label: 'Inspect Source', href: '/inspector' },
  { label: 'View Evidence', href: '/inspector' },
  { label: 'Open Apply Lane', href: '/station/ops' },
  { label: 'Open WorkItem', href: '/station/ledger' },
] as const;

const ARTIFACT_KIND_META: Record<string, { icon: LucideIcon; edge: string; label?: string }> = {
  axiom_candidates: { icon: Orbit, edge: 'governs', label: 'Axiom Candidates' },
  principles: { icon: Compass, edge: 'governs' },
  standards: { icon: ShieldCheck, edge: 'constrains' },
  concepts: { icon: Boxes, edge: 'describes' },
  mechanisms: { icon: Workflow, edge: 'implements' },
  paper_modules: { icon: BookOpen, edge: 'grounds' },
  frontend_views: { icon: RouteIcon, edge: 'projects' },
  frontend_components: { icon: Package, edge: 'implements' },
  system_atlas: { icon: Network, edge: 'projects' },
  task_ledger: { icon: ReceiptText, edge: 'routes' },
  raw_seed_shards: { icon: FileText, edge: 'sources' },
  annex_distillation_patterns: { icon: Archive, edge: 'distills', label: 'Annex Distillation Rows' },
  annexes: { icon: Archive, edge: 'distills' },
};

interface RootCrystalStateAxis {
  id: string;
  label: string;
  value: string;
  tone: StateAxisTone;
  reason: string;
}

interface RootCrystalGate {
  id: string;
  label: string;
  state: string;
  tone: StateAxisTone;
  reason: string;
  recovery: string;
}

interface RootCrystalGraphNode {
  id: string;
  label: string;
  kind: string;
  role: string;
  status: string;
  count: string;
  icon: LucideIcon;
  accent: string;
  edge: string;
}

interface RootDoctrineCrystalViewModel {
  countsTrusted: boolean;
  countUnavailableReason: string;
  stateAxes: RootCrystalStateAxis[];
  gates: RootCrystalGate[];
  graphNodes: RootCrystalGraphNode[];
  selectedGraphNode: RootCrystalGraphNode | null;
  annexRow: RootCoverageRow | null;
  sourceRefs: string[];
  relationAuthoritySources: string[];
  readOnlyActions: ReadonlyArray<{ label: string; href: string }>;
  captureCommand: string;
}

type RootWorkbenchNodeRole = 'focus' | 'context' | 'projection' | 'evidence' | 'route' | 'health';

interface RootWorkbenchNode {
  id: string;
  role: RootWorkbenchNodeRole;
  label: string;
  kicker: string;
  detail: string;
  relationHint?: string;
  status?: string | null;
  x: number;
  y: number;
  kindRef?: string;
  rowRef?: string;
  inspectorTab?: InspectorTab;
  href?: string;
}

interface RootWorkbenchNodeGeometry {
  id: string;
  cx: number;
  cy: number;
  width: number;
  height: number;
}

interface RootWorkbenchPoint {
  x: number;
  y: number;
}

interface RootWorkbenchEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

interface RootWorkbenchGraphModel {
  nodes: RootWorkbenchNode[];
  edges: RootWorkbenchEdge[];
  focusId: string;
  sourceLine: string;
  omissionLine: string;
}

function isRecord(value: unknown): value is UnknownRow {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is string => typeof entry === 'string' && entry.length > 0);
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function isHealthy(status: string | undefined | null): boolean {
  if (!status) return false;
  return HEALTHY_STATUSES.has(status);
}

function rowLabel(row: UnknownRow, fallback: string): string {
  return asString(
    row.label ?? row.title ?? row.slug ?? row.cluster_id ?? row.id ?? row.row_id ?? fallback,
    fallback,
  );
}

function rowClaim(row: UnknownRow): string {
  return asString(
    row.claim ?? row.compression ?? row.statement ?? row.tldr_excerpt ?? row.purpose_or_intent ?? '',
  );
}

function rowPrimaryId(row: UnknownRow, fallback: string): string {
  return asString(
    row.row_id ??
      row.id ??
      row.concept_id ??
      row.mechanism_id ??
      row.axiom_candidate_id ??
      row.slug ??
      row.cluster_id ??
      row.group ??
      row.label ??
      fallback,
    fallback,
  );
}

const ROW_IDENTITY_FIELDS: ReadonlyArray<string> = [
  'row_id',
  'id',
  'slug',
  'principle_id',
  'standard_id',
  'concept_id',
  'mechanism_id',
  'paper_module_id',
  'module_id',
  'axiom_candidate_id',
  'route_id',
  'view_id',
  'component_id',
  'file_id',
  'path',
];

function rowIdentityKeys(row: UnknownRow): string[] {
  const keys = new Set<string>();
  const primary = rowPrimaryId(row, '');
  if (primary) keys.add(primary);
  for (const field of ROW_IDENTITY_FIELDS) {
    const value = asString(row[field]);
    if (value) keys.add(value);
  }
  const rowId = asString(row.row_id);
  const match = rowId.match(/^[^:]+:([^:]+)::/);
  if (match?.[1]) keys.add(match[1]);
  return [...keys];
}

function rowSourceRefs(row: UnknownRow): string[] {
  const refs = new Set<string>();
  for (const key of ['source_ref', 'standard_ref']) {
    const value = row[key];
    if (typeof value === 'string' && value) refs.add(value);
  }
  const nearestStandard = row.nearest_standard;
  if (isRecord(nearestStandard) && typeof nearestStandard.ref === 'string') refs.add(nearestStandard.ref);
  return [...refs];
}

function rowStatus(row: UnknownRow): string {
  const status = asString(row.status ?? row.currentness_status ?? row.profile_status ?? row.band ?? 'loaded', 'loaded');
  if (HEALTHY_STATUSES.has(status)) return 'green';
  if (['draft', 'seed', 'candidate', 'partial', 'cluster_flag', 'flag', 'card'].includes(status)) return 'partial';
  if (['missing', 'failed', 'stale'].includes(status)) return status;
  return 'green';
}

function normalizeStatus(status: unknown): string {
  const raw = asString(status, '').toLowerCase();
  if (!raw) return 'unknown';
  if (raw === 'option_surface_supported') return 'green';
  if (raw.includes('stale')) return 'stale';
  if (raw.includes('missing') || raw.includes('failed')) return 'missing';
  if (raw.includes('unverified') || raw.includes('caveat') || raw.includes('partial')) return 'partial';
  if (HEALTHY_STATUSES.has(raw) || raw === 'fresh') return 'green';
  return raw;
}

function statusTone(status: unknown): StateAxisTone {
  const normalized = normalizeStatus(status);
  if (normalized === 'green') return 'green';
  if (normalized === 'stale') return 'stale';
  if (normalized === 'missing') return 'missing';
  if (normalized === 'unknown') return 'neutral';
  return 'partial';
}

const STATUS_DISPLAY_LABELS: Record<string, string> = {
  green: 'supported',
  option_surface_supported: 'supported',
  active: 'active',
  available: 'available',
  available_unverified_freshness: 'freshness unverified',
  fresh: 'fresh',
  ready: 'ready',
  ready_with_caveats: 'ready · caveats',
  loaded: 'loaded',
  captured: 'captured',
  listed: 'listed',
  supported: 'supported',
  partial: 'partial',
  stale: 'stale',
  missing: 'missing',
  failed: 'failed',
  unknown: 'unknown',
  degraded: 'degraded',
  offline: 'offline',
  live: 'live',
  connecting: 'connecting',
  projection: 'projection',
  source: 'source',
  derived: 'derived',
  fixture: 'fixture',
  verified: 'verified',
  mixed: 'mixed',
  unverified: 'unverified',
  read_only: 'read only',
  'read-only': 'read only',
  apply_lane_required: 'apply lane required',
  blocked: 'blocked',
  nested: 'nested',
  'focus pending': 'focus pending',
};

function displayStatus(raw: unknown, fallback = 'unknown'): string {
  const text = asString(raw, '').toLowerCase();
  if (!text) return fallback;
  return STATUS_DISPLAY_LABELS[text] ?? text.replace(/_/g, ' ');
}

type StatusRenderContext = 'focus-node' | 'dense-list' | 'detail';

function shouldRenderRowStatus(
  rowStatusValue: unknown,
  inheritedStatus: unknown,
  context: StatusRenderContext,
): boolean {
  const rowStatusText = asString(rowStatusValue);
  if (!rowStatusText) return false;
  const rowTone = normalizeStatus(rowStatusText);
  const inheritedTone = normalizeStatus(inheritedStatus);
  if (context === 'focus-node') return true;
  if (context === 'dense-list') {
    if (rowTone === inheritedTone) return false;
    if (['green', 'partial', 'candidate', 'unknown', 'active'].includes(rowTone)) return false;
  }
  return !['green', 'active', 'supported', 'loaded', 'ready'].includes(rowTone);
}

type SelectedObjectSpecies = 'cluster_row' | 'leaf_row' | 'source_ref_row' | 'coverage_row' | 'unknown_row';

interface ParentClusterInfo {
  label: string;
  clusterId: string;
  rowId: string;
  membershipSource: string;
  memberKind: string;
}

function clusterMemberKind(
  clusterRow: UnknownRow | null,
  primitive: RootNavigatorPrimitiveRow | null,
): string {
  const artifactKind = asString(clusterRow?.artifact_kind);
  if (artifactKind.endsWith('_type_cluster')) {
    return artifactKind.replace(/_type_cluster$/, '');
  }
  const candidate = asString(primitive?.candidate_primitive);
  if (candidate.endsWith('s')) return candidate.replace(/s$/, '');
  return candidate || 'member';
}

function findParentCluster(
  leafRow: UnknownRow | null,
  drilldownPacket: NavigationSurfacePacket | null,
  primitive: RootNavigatorPrimitiveRow | null,
): ParentClusterInfo | null {
  if (!leafRow || !drilldownPacket) return null;
  const leafCandidates = [
    rowPrimaryId(leafRow, ''),
    asString(leafRow.principle_id),
    asString(leafRow.id),
    asString(leafRow.row_id),
  ].filter((id) => id.length > 0);
  if (leafCandidates.length === 0) return null;
  const drilldownRows = (drilldownPacket.rows ?? []).filter(isRecord);
  for (const row of drilldownRows) {
    const topIds = asStringArray(row.top_ids);
    if (topIds.length === 0) continue;
    const matched = leafCandidates.some((cand) => topIds.includes(cand));
    if (matched) {
      return {
        label: rowLabel(row, asString(row.cluster_id, 'cluster')),
        clusterId: asString(row.cluster_id),
        rowId: rowPrimaryId(row, ''),
        membershipSource: 'cluster.top_ids',
        memberKind: clusterMemberKind(row, primitive),
      };
    }
  }
  return null;
}

function classifySelectedObject(row: UnknownRow | null): SelectedObjectSpecies {
  if (!row) return 'unknown_row';
  const band = asString(row.band, '').toLowerCase();
  const rowId = rowPrimaryId(row, '');
  const hasDirectRefs = rowSourceRefs(row).length > 0;
  const isClusterShape =
    band === 'cluster_flag' ||
    rowId.includes('::cluster_flag') ||
    (typeof row.cluster_id === 'string' && row.cluster_id.length > 0);
  if (hasDirectRefs) return 'leaf_row';
  if (band === 'card' || rowId.includes('::card')) return 'leaf_row';
  if (isClusterShape) return 'cluster_row';
  if (rowId.startsWith('source_ref:') || asString(row.source_kind).toLowerCase() === 'source_ref') return 'source_ref_row';
  return 'unknown_row';
}

function countLabel(count: unknown, countsTrusted: boolean): string {
  if (!countsTrusted || typeof count !== 'number') return '—';
  return String(count);
}

function rootCoverageCountsTrusted(packet: RootNavigatorHandoffPacket | null): boolean {
  if (!packet) return false;
  const receipts = packet.freshness_receipts;
  if (isRecord(receipts)) {
    const summary = receipts.summary;
    if (
      isRecord(summary) &&
      summary.root_coverage_safe_to_treat_counts_as_current === true
    ) {
      return true;
    }
    const receiptRows = receipts.receipts;
    if (isRecord(receiptRows)) {
      const rootCoverage = receiptRows.root_coverage_state;
      if (
        isRecord(rootCoverage) &&
        rootCoverage.safe_to_treat_counts_as_current === true
      ) {
        return true;
      }
    }
  }
  const status = normalizeStatus(packet.root_coverage_state?.status);
  return status === 'green';
}

function rootCoverageStateLabel(packet: RootNavigatorHandoffPacket | null): string {
  const receipts = packet?.freshness_receipts;
  if (isRecord(receipts)) {
    const receiptRows = receipts.receipts;
    if (isRecord(receiptRows)) {
      const rootCoverage = receiptRows.root_coverage_state;
      if (isRecord(rootCoverage)) return asString(rootCoverage.status, 'unknown');
    }
  }
  return asString(packet?.root_coverage_state?.status, 'unknown');
}

function packetBandForRow(row: RootNavigatorPrimitiveRow): string {
  const supported = row.supported_bands ?? [];
  if (supported.includes('cluster_flag')) return 'cluster_flag';
  if (supported.includes('flag')) return 'flag';
  if (supported.length > 0) return supported[0];
  return 'flag';
}

function StatusPill({
  status,
  dim = false,
  label,
}: {
  status?: string | null;
  dim?: boolean;
  label?: string;
}) {
  const tone = status ? normalizeStatus(status) : null;
  const visible = label ?? (status ? displayStatus(status) : 'unknown');
  return (
    <span
      title={status ?? undefined}
      className={clsx(
        'inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em]',
        tone === 'green' && (dim ? 'border-emerald-400/15 bg-emerald-400/[0.04] text-emerald-200/70' : 'border-emerald-400/30 bg-emerald-400/10 text-emerald-100'),
        tone === 'partial' && 'border-amber-400/30 bg-amber-400/10 text-amber-100',
        tone === 'missing' && 'border-red-400/30 bg-red-400/10 text-red-100',
        tone === 'stale' && 'border-sky-400/30 bg-sky-400/10 text-sky-100',
        !tone && 'border-zenith-edge bg-white/[0.04] text-white/50',
      )}
    >
      {visible}
    </span>
  );
}

function SectionHeader({ icon: Icon, label, hint }: { icon: typeof GitBranch; label: string; hint?: string }) {
  return (
    <div className="flex items-center justify-between gap-2 border-b border-zenith-edge px-3 py-2 font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-muted">
      <span className="flex items-center gap-2">
        <Icon size={13} />
        <span>{label}</span>
      </span>
      {hint && <span className="text-white/35">{hint}</span>}
    </div>
  );
}

interface FreshnessBannerProps {
  packet: RootNavigatorHandoffPacket | null;
}

function FreshnessBanner({ packet }: FreshnessBannerProps) {
  if (!packet) return null;
  const verdict = packet.verdict;
  const coverageStatus = packet.root_coverage_state?.status;
  const stale = coverageStatus && coverageStatus !== 'available' && coverageStatus !== 'fresh';
  if (!stale && verdict?.state !== 'ready_with_caveats') return null;
  const reason = verdict?.reason ?? '';
  const freshnessCheck = packet.root_coverage_state?.freshness_check_command ?? '';
  const semanticTone = displayStatus(coverageStatus ?? verdict?.state, 'caveat');
  const headline =
    coverageStatus && stale
      ? 'Coverage freshness unverified — counts hidden.'
      : 'Ready with caveats — review before relying on counts.';
  return (
    <div className="flex items-center gap-3 border-b border-amber-400/20 bg-amber-400/[0.04] px-4 py-1.5 text-[11px] text-amber-100/85">
      <ShieldAlert size={13} className="shrink-0 text-amber-300" />
      <span className="min-w-0 flex-1 truncate" title={reason || undefined}>
        <span className="font-mono uppercase tracking-[0.16em] text-amber-200/80">{semanticTone}</span>
        <span className="mx-2 text-amber-200/40">·</span>
        <span className="text-amber-100/85">{headline}</span>
      </span>
      {freshnessCheck && (
        <details className="shrink-0">
          <summary className="cursor-pointer font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65 hover:text-amber-100">
            check freshness
          </summary>
          <div className="absolute right-4 z-20 mt-1 flex items-center gap-2 rounded border border-amber-400/20 bg-black/85 px-2 py-1 shadow-lg">
            <code className="max-w-[420px] truncate font-mono text-[10px] text-amber-100/85">
              {freshnessCheck}
            </code>
            <CopyButton getText={() => freshnessCheck} label="copy" />
          </div>
        </details>
      )}
    </div>
  );
}

interface RootStatusBarProps {
  packet: RootNavigatorHandoffPacket | null;
  coverage: RootCoverageState | null;
  viewModel: RootDoctrineCrystalViewModel;
}

function RootStatusBar({ packet, coverage, viewModel }: RootStatusBarProps) {
  const summary = packet?.root_coverage_state?.summary ?? {};
  const branchCount = typeof summary.branch_count === 'number' ? summary.branch_count : coverage?.branches?.length ?? null;
  const layerCount = typeof summary.doctrine_layer_count === 'number' ? summary.doctrine_layer_count : coverage?.doctrine_layers?.length ?? null;
  const branchStatusCounts = summary.branch_coverage_status_counts ?? {};
  const layerStatusCounts = summary.doctrine_layer_coverage_status_counts ?? {};
  const branchesGreen = branchStatusCounts.green ?? null;
  const layersGreen = layerStatusCounts.green ?? null;
  const conflictCount = typeof summary.route_conflict_count === 'number' ? summary.route_conflict_count : null;
  const missingCount = typeof summary.missing_branch_count === 'number' ? summary.missing_branch_count : null;
  const branchExceptions = packet?.root_coverage_state?.attention?.branch_exceptions ?? [];
  const layerExceptions = packet?.root_coverage_state?.attention?.doctrine_layer_exceptions ?? [];
  const totalExceptions = branchExceptions.length + layerExceptions.length;

  // Atlas Focus Frame: the status axes used to render every value as a saturated
  // pill, so LIVE / PROJECTION / UNKNOWN / READ-ONLY shouted as loudly as a real
  // PARTIAL-freshness or MISSING-coverage warning and the bar read as all-urgent.
  // Passive tones (green = live/supported, neutral = projection/unknown/read-only)
  // now drop the pill chrome for a quiet status dot + soft value; only the tones
  // the operator must act on (partial/missing/stale) keep the loud pill. maxZoom
  // of the eye stays on the graph, not the perimeter.
  const axisValuePresentation = (
    tone: StateAxisTone,
    value: string,
  ): { quiet: boolean; dotClass: string; valueClass: string } => {
    const upper = value.toUpperCase();
    if (tone === 'partial') return { quiet: false, dotClass: '', valueClass: 'pill pill-warn' };
    if (tone === 'missing') return { quiet: false, dotClass: '', valueClass: 'pill pill-block' };
    if (tone === 'stale') return { quiet: false, dotClass: '', valueClass: 'pill pill-info' };
    // neutral tone carrying an explicit MISSING value is still a coverage gap.
    if (upper === 'MISSING') return { quiet: false, dotClass: '', valueClass: 'pill pill-warn' };
    if (tone === 'green')
      return { quiet: true, dotClass: 'dot dot-ok', valueClass: 'font-mono text-[11px] tracking-[0.04em] text-zenith-soft' };
    return { quiet: true, dotClass: 'dot dot-idle', valueClass: 'font-mono text-[11px] tracking-[0.04em] text-zenith-soft' };
  };
  return (
    <section className="border-b border-zenith-edge bg-black/35 px-4 py-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 font-mono text-[11px]">
        {viewModel.stateAxes.map((axis) => {
          const valueText = String(axis.value ?? 'unknown');
          const present = axisValuePresentation(axis.tone, valueText);
          return (
            <span
              key={axis.id}
              className="flex items-center gap-1.5"
              title={axis.reason}
              data-zenith-root-status-axis={axis.id}
              data-zenith-root-status-axis-tone={axis.tone}
            >
              <span className="text-[10px] uppercase tracking-[0.14em] text-zenith-muted">{axis.label}</span>
              {present.quiet ? (
                <span className="flex items-center gap-1" data-zenith-root-status-axis-value={valueText}>
                  <span className={present.dotClass} aria-hidden />
                  <span className={present.valueClass}>{valueText}</span>
                </span>
              ) : (
                <span className={present.valueClass} data-zenith-root-status-axis-value={valueText}>
                  {valueText}
                </span>
              )}
            </span>
          );
        })}
        <span className="ml-auto flex items-center gap-3 text-[11px]">
          {viewModel.countsTrusted && branchCount !== null && (
            <span className="text-zenith-soft">
              <span className="text-emerald-200/80">{branchesGreen ?? branchCount}</span>
              <span className="text-white/30">/{branchCount}</span> branches green
            </span>
          )}
          {viewModel.countsTrusted && layerCount !== null && (
            <span className="text-zenith-soft">
              <span className="text-emerald-200/80">{layersGreen ?? layerCount}</span>
              <span className="text-white/30">/{layerCount}</span> layers green
            </span>
          )}
          {!viewModel.countsTrusted && (
            <span className="text-amber-100/75">counts hidden · freshness unverified</span>
          )}
          {conflictCount !== null && (
            <span className={conflictCount === 0 ? 'text-zenith-muted' : 'text-amber-200/80'}>
              {conflictCount} conflicts
            </span>
          )}
          {missingCount !== null && (
            <span className={missingCount === 0 ? 'text-zenith-muted' : 'text-amber-200/80'}>
              {missingCount} missing
            </span>
          )}
          {totalExceptions > 0 && (
            <span className="text-amber-200/80">{totalExceptions} attention</span>
          )}
        </span>
      </div>
    </section>
  );
}

function GateRail({
  gates,
  expanded,
  onToggleExpanded,
}: {
  gates: RootCrystalGate[];
  expanded: boolean;
  onToggleExpanded: () => void;
}) {
  return (
    <footer className="shrink-0 border-t border-zenith-edge bg-black/55">
      <div className="flex items-center gap-3 px-4 py-1.5">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-zenith-muted">gates</span>
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px]">
          {gates.map((gate) => (
            <span key={gate.id} className="flex items-center gap-1.5" title={`${gate.reason} · ${gate.recovery}`}>
              <span className="uppercase tracking-[0.14em] text-zenith-muted">{gate.label}</span>
              <span className="text-white/72">{gate.state}</span>
              <StatusPill status={gate.tone === 'neutral' ? undefined : gate.tone} dim />
            </span>
          ))}
        </div>
        <button
          type="button"
          onClick={onToggleExpanded}
          className="shrink-0 rounded border border-zenith-edge bg-white/[0.03] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft hover:border-cyan-300/35 hover:text-cyan-100"
          aria-expanded={expanded}
          aria-label="Toggle gate detail"
        >
          {expanded ? 'collapse' : 'expand'}
        </button>
      </div>
      {expanded && (
        <div className="border-t border-zenith-edge px-3 py-2">
          <div className="flex gap-2 overflow-x-auto pb-0.5">
            {gates.map((gate) => (
              <div
                key={gate.id}
                className="min-w-[220px] rounded-[4px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">{gate.label}</span>
                  <StatusPill status={gate.tone === 'neutral' ? undefined : gate.tone} dim />
                </div>
                <div className="mt-1 font-mono text-[11px] text-white/78">{gate.state}</div>
                <div className="mt-0.5 line-clamp-2 text-[10px] leading-4 text-white/42">{gate.reason}</div>
                <div className="mt-1 truncate font-mono text-[10px] text-[#c7b06a]/75">{gate.recovery}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </footer>
  );
}

function ReadOnlyActionBar({
  viewModel,
  sourceRef,
}: {
  viewModel: RootDoctrineCrystalViewModel;
  sourceRef?: string;
}) {
  const location = useLocation();
  const currentRoute = `${location.pathname}${location.search}`;
  const actions = viewModel.readOnlyActions.map((action) => {
    if (action.label === 'Inspect Source' && sourceRef) {
      return { ...action, href: withReturnToQuery(`/inspector?file=${encodeURIComponent(sourceRefPath(sourceRef))}`, currentRoute) };
    }
    if (action.label === 'View Evidence' && sourceRef) {
      return { ...action, href: withReturnToQuery(`/inspector?file=${encodeURIComponent(sourceRefPath(sourceRef))}`, currentRoute) };
    }
    return action;
  });
  return (
    <div className="space-y-1">
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">read-only actions</div>
      <div className="flex flex-wrap gap-1.5">
        {actions.map((action) => (
          <a
            key={action.label}
            href={action.href}
            className="inline-flex items-center gap-1.5 rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-white/62 hover:border-[#c7b06a]/40 hover:text-[#f4e6a2]"
          >
            <Eye size={11} />
            {action.label}
          </a>
        ))}
      </div>
    </div>
  );
}

// v1.20: paper_modules joins the graph-native kinds. The left-rail click now routes
// to ?graph=substrate&focus=paper_modules and the cockpit renders the v1.20
// RootPaperModuleVisualField (actual paper module nodes grouped by source-owned
// subdomain clusters) instead of the legacy ?kind=paper_modules generic relation
// graph workbench. Open kind lens remains the explicit legacy escape.
//
// v1.21: standards joins the graph-native kinds. The left-rail click now routes
// to ?graph=substrate&focus=standards and the cockpit renders RootStandardsGrammarField
// (standards grouped by source-owned group clusters from
// `kernel.py --option-surface standards --band cluster_flag`). Standards are not
// merely "more paper_modules"; selecting a standard projects contract-level meaning
// into the Inspector (governed kind, required fields, validation probes,
// completeness receipts) and exposes a "View governed kind" route back to the
// graph-native field for the kind it governs, when that kind is itself graph-native.
const GRAPH_NATIVE_KINDS: ReadonlySet<string> = new Set([
  'axiom_candidates',
  'principles',
  'paper_modules',
  'standards',
]);

interface AxisRailProps {
  axes: RootNavigatorPrimitiveAxis[];
  rowsByKind: Map<string, RootNavigatorPrimitiveRow>;
  viewModel: RootDoctrineCrystalViewModel;
  selectedKind: string | null;
  onSelectKind: (kind: string) => void;
  onSelectGraphNativeKind?: (kind: string) => void;
  graphNativeKinds?: ReadonlySet<string>;
  substrateGraphFocus?: string | null;
  query: string;
  onQueryChange: (q: string) => void;
  showAll: boolean;
  onToggleShowAll: () => void;
  coverage: RootCoverageState | null;
}

function AxisRail({
  axes,
  rowsByKind,
  viewModel,
  selectedKind,
  onSelectKind,
  onSelectGraphNativeKind,
  graphNativeKinds,
  substrateGraphFocus,
  query,
  onQueryChange,
  showAll,
  onToggleShowAll,
  coverage,
}: AxisRailProps) {
  const graphCapable = graphNativeKinds ?? GRAPH_NATIVE_KINDS;
  const filteredAxes = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return axes
      .map((axis) => {
        const candidateKinds = axis.candidate_kinds ?? [];
        const visibleKinds = candidateKinds.filter((kind) => {
          const row = rowsByKind.get(kind);
          if (!row) return false;
          if (!needle) return true;
          const haystack = `${kind} ${row.title ?? ''} ${row.role_in_root_navigator ?? ''} ${axis.label ?? ''}`.toLowerCase();
          return haystack.includes(needle);
        });
        return { axis, kinds: visibleKinds };
      })
      .filter(({ kinds }) => kinds.length > 0);
  }, [axes, rowsByKind, query]);

  const coverageAttention = useMemo(() => {
    if (!coverage) return [] as RootCoverageRow[];
    const all = [...(coverage.branches ?? []), ...(coverage.doctrine_layers ?? [])];
    if (showAll) return all;
    return all.filter((row) => row.coverage_status && row.coverage_status !== 'green');
  }, [coverage, showAll]);

  return (
    <aside
      className="flex w-[300px] min-w-[280px] flex-col border-r border-zenith-edge bg-black/45"
      data-zenith-view-region="rail"
      data-zenith-view-region-role="axis_rail"
      data-zenith-view-region-mode="persistent"
    >
      <header className="border-b border-zenith-edge p-3">
        <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-200/70">
          <Compass size={14} />
          <span>Root Navigator</span>
        </div>
        <div className="flex items-center gap-2 rounded-md border border-zenith-edge bg-white/[0.04] px-2 py-1.5">
          <Search size={14} className="text-white/35" />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Filter axes and kinds"
            className="min-w-0 flex-1 bg-transparent font-mono text-xs text-white outline-none placeholder:text-white/25"
          />
        </div>
        <button
          type="button"
          onClick={onToggleShowAll}
          className={clsx(
            'mt-2 flex w-full items-center justify-between gap-2 rounded border px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em]',
            showAll
              ? 'border-cyan-300/40 bg-cyan-300/10 text-cyan-100'
              : 'border-zenith-edge bg-white/[0.025] text-zenith-soft hover:text-white/80',
          )}
        >
          <span>{showAll ? 'audit · all rows' : 'attention only'}</span>
          <span className="text-white/35">{showAll ? 'show ↓' : 'expand'}</span>
        </button>
      </header>

      <div className="flex-1 overflow-auto">
        <SectionHeader icon={Layers} label="Artifact rail" hint={`${filteredAxes.length} groups`} />
        {filteredAxes.length === 0 ? (
          <div className="px-3 py-2 font-mono text-[11px] text-zenith-muted">No axes match the filter.</div>
        ) : (
          <div className="space-y-3 p-2">
            {filteredAxes.map(({ axis, kinds }) => (
              <div key={axis.axis_id} className="space-y-1.5">
                <div className="flex items-baseline justify-between gap-2 px-1">
                  <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-zenith-soft">
                    {asString(axis.label, axis.axis_id)}
                  </span>
                  <span className="font-mono text-[10px] text-white/30">{kinds.length}</span>
                </div>
                <div className="space-y-1">
                  {kinds.map((kind) => {
                    const row = rowsByKind.get(kind);
                    if (!row) return null;
                    const isGraphNative =
                      graphCapable.has(kind) && typeof onSelectGraphNativeKind === 'function';
                    const active = isGraphNative
                      ? substrateGraphFocus === kind
                      : selectedKind === kind;
                    const status = asString(row.support_status ?? row.status ?? 'green', 'green');
                    const meta = artifactMeta(kind);
                    const Icon = meta.icon;
                    const role = asString(row.role_in_root_navigator);
                    return (
                      <button
                        key={kind}
                        type="button"
                        onClick={() =>
                          isGraphNative ? onSelectGraphNativeKind!(kind) : onSelectKind(kind)
                        }
                        data-zenith-root-axis-rail-kind={kind}
                        data-zenith-root-axis-rail-kind-mode={isGraphNative ? 'graph_native' : 'focus_path'}
                        className={clsx(
                          // Axis rail kind chip — adopt `.row-tile-active`'s
                          // gold 2px left-accent rule for the selected kind so
                          // the rail reads in peripheral vision. Palette-
                          // bound borders match the rest of the cockpit chrome.
                          'row-tile w-full rounded-[3px] border px-2 py-1.5 text-left transition-colors',
                          active
                            ? 'row-tile-active border-[var(--zenith-accent-edge)] bg-[var(--zenith-accent-soft)]'
                            : 'border-zenith-edge bg-white/[0.025] hover:border-zenith-edge-strong hover:bg-white/[0.045]',
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="flex min-w-0 items-center gap-2 text-xs font-semibold text-white/85">
                            <Icon size={14} className="shrink-0 text-[#c7b06a]/80" />
                            <span className="truncate">{asString(meta.label ?? row.title, kind)}</span>
                          </span>
                          <span className="flex shrink-0 items-center gap-2 font-mono text-[10px] text-zenith-muted">
                            <span>{countLabel(row.row_count, viewModel.countsTrusted)}</span>
                            <StatusPill status={status === 'option_surface_supported' ? 'green' : status} dim />
                          </span>
                        </div>
                        {role && (
                          <div className="mt-1 line-clamp-2 text-[10px] leading-4 text-white/50">{role}</div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        {coverageAttention.length > 0 && (
          <>
            <SectionHeader
              icon={AlertTriangle}
              label={showAll ? 'Coverage rows' : 'Coverage attention'}
              hint={`${coverageAttention.length} rows`}
            />
            <div className="space-y-1 p-2">
              {coverageAttention.map((row) => (
                <button
                  key={row.id}
                  type="button"
                  onClick={() => onSelectKind(`coverage:${row.id}`)}
                  className={clsx(
                    'w-full rounded-[3px] border px-2 py-1.5 text-left transition-colors',
                    selectedKind === `coverage:${row.id}`
                      ? 'border-amber-300/45 bg-amber-300/10'
                      : 'border-zenith-edge bg-white/[0.025] hover:border-white/20 hover:bg-white/[0.045]',
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs font-semibold text-white/85">{row.label}</span>
                    <StatusPill status={row.coverage_status} />
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </aside>
  );
}

interface ConstitutionalMapProps {
  packet: RootNavigatorHandoffPacket | null;
  axes: RootNavigatorPrimitiveAxis[];
  viewModel: RootDoctrineCrystalViewModel;
  onSelectKind: (kind: string) => void;
  onSelectInspectorTab: (tab: InspectorTab) => void;
  selectedPrimitive: RootNavigatorPrimitiveRow | null;
  selectedAxis: RootNavigatorPrimitiveAxis | null;
  drilldownRowCount: number;
  selectedRow: UnknownRow | null;
  drilldownPacket: NavigationSurfacePacket | null;
  drilldownLoading: boolean;
  drilldownError: string | null;
  cardPacket: NavigationSurfacePacket | null;
  cardLoading: boolean;
  cardError: string | null;
  onSelectRow: (rowId: string | null) => void;
  memberPreviewRowsById: Map<string, UnknownRow>;
  substrateGraphMode: 'atlas' | 'family';
  substrateGraphFocus: string | null;
  substrateFamilyNode: string | null;
  // vNext-CM: ?cluster=<id> for single-cluster expansion. Threaded so the
  // visibility projection in the canvas can collapse sibling clusters and
  // route meta-edges to the collapsed-cluster level when the operator has
  // expanded only one cluster.
  substrateGraphCluster?: string | null;
  onSelectAtlasContainer: (kind: string) => void;
  onOpenKindLens: (kind: string) => void;
  onSelectFamilyNode: (nodeId: string | null) => void;
  // vNext-GA: cluster-toggle callback. Cluster nodes in the canvas call this
  // to set/clear ?cluster=<id> via the parent setSearchParams.
  onSelectGraphCluster: (clusterId: string | null) => void;
  // vNext-IX: typed object/neighbor selection. Writes raw object id to
  // ?node= and preserves focus + cluster context.
  onSelectGraphObject: (kind: string, rawId: string | null, clusterId?: string | null) => void;
  onBackToAtlas: () => void;
  // vNext-real: the page-level v1.16 card-band fetch for the selected family node is
  // threaded into ConstitutionalMap so the visible unified-graph canvas can render
  // the selected object's relation neighborhood (top_dependencies / top_dependents /
  // standard_ref / source_ref / governing_refs for paper modules; governs / governed
  // kind / source_ref for standards) without duplicating the card fetch.
  familyNodeCard?: NavigationSurfacePacket | null;
  familyNodeCardStatus?: 'idle' | 'loading' | 'ready' | 'error';
  depthPresentation?: 'default' | 'deep_detail';
}

const AXIS_ACCENT: Record<string, string> = {
  constitutional: '#c7b06a',
  semantic: '#7dd3fc',
  semantic_operational: '#7dd3fc',
  rationale: '#a78bfa',
  projection: '#7bc78e',
  substrate: '#94a3b8',
  generated_projection: '#94a3b8',
  execution: '#fbbf24',
  provenance: '#f87171',
};

function axisAccent(axisId: string): string {
  return AXIS_ACCENT[axisId] ?? '#475569';
}

function artifactMeta(kind: string) {
  return ARTIFACT_KIND_META[kind] ?? { icon: Database, edge: 'references' };
}

function relationNodeId(prefix: string, value: string): string {
  return `${prefix}:${value.replace(/[^a-zA-Z0-9_-]+/g, '_').slice(0, 80)}`;
}

function firstNonEmpty(...values: Array<string | undefined | null>): string {
  return values.find((value) => typeof value === 'string' && value.trim().length > 0)?.trim() ?? '';
}

function graphStatusLabel(status: unknown): string {
  const normalized = normalizeStatus(status);
  return normalized === 'green' ? 'supported' : displayStatus(normalized);
}

function graphNodeTone(role: RootWorkbenchNodeRole, active: boolean): string {
  if (active) return 'border-[#c7b06a]/80 bg-[#171208] text-white shadow-[0_0_34px_rgba(199,176,106,0.18)]';
  if (role === 'focus') return 'border-[#c7b06a]/55 bg-[#05070b] text-white';
  if (role === 'evidence') return 'border-emerald-300/30 bg-[#06100c] text-emerald-50';
  if (role === 'route') return 'border-cyan-300/30 bg-[#051014] text-cyan-50';
  if (role === 'health') return 'border-amber-300/30 bg-[#120d05] text-amber-50';
  if (role === 'projection') return 'border-violet-300/28 bg-[#0d0a14] text-violet-50';
  return 'border-white/14 bg-[#05070b] text-white';
}

function rootWorkbenchNodeSize(node: RootWorkbenchNode, active = false): { width: number; height: number } {
  if (active || node.role === 'focus') return { width: 16, height: 9.5 };
  return { width: 14, height: 8.5 };
}

function rootWorkbenchNodeGeometry(node: RootWorkbenchNode, active = false): RootWorkbenchNodeGeometry {
  const size = rootWorkbenchNodeSize(node, active);
  return { id: node.id, cx: node.x, cy: node.y, ...size };
}

function clipLineToRectBoundary(
  from: RootWorkbenchPoint,
  targetRect: RootWorkbenchNodeGeometry,
  padding = 0.2,
): RootWorkbenchPoint {
  const dx = from.x - targetRect.cx;
  const dy = from.y - targetRect.cy;
  if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001) {
    return { x: targetRect.cx, y: targetRect.cy };
  }
  const halfWidth = targetRect.width / 2 + padding;
  const halfHeight = targetRect.height / 2 + padding;
  const scale = Math.min(
    Math.abs(dx) > 0 ? halfWidth / Math.abs(dx) : Number.POSITIVE_INFINITY,
    Math.abs(dy) > 0 ? halfHeight / Math.abs(dy) : Number.POSITIVE_INFINITY,
  );
  const safeScale = Number.isFinite(scale) ? scale : 0;
  return {
    x: targetRect.cx + dx * safeScale,
    y: targetRect.cy + dy * safeScale,
  };
}

function edgeEndpointData(point: RootWorkbenchPoint): string {
  return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
}

type RootSubstrateBand = 'durable_substrate' | 'reference_substrate' | 'operational_overlay';

type RootSubstrateRelation =
  | 'compresses'
  | 'applies'
  | 'constrains'
  | 'names'
  | 'operationalizes'
  | 'explains'
  | 'projects'
  | 'repairs'
  | 'sources'
  | 'shares_axis';

interface RootSubstrateContainer {
  id: string;
  kind: string;
  band: RootSubstrateBand;
  label: string;
  role: string;
  axisLabel: string;
  axisId: string;
  rowCount: number | null;
  status: string;
  countsTrusted: boolean;
  hasOptionSurface: boolean;
  icon: LucideIcon;
}

interface RootSubstrateRelationEdge {
  id: string;
  source: string;
  target: string;
  family: RootSubstrateRelation;
  authority: 'derived_canonical' | 'derived_axis_neighbor';
}

interface RootSubstrateLegendEntry {
  key: string;
  label: string;
  meaning: string;
}

interface RootSubstrateAtlasLegend {
  bands: RootSubstrateLegendEntry[];
  edgeFamilies: RootSubstrateLegendEntry[];
  encoding: RootSubstrateLegendEntry[];
}

interface RootSubstrateAtlasModel {
  containers: RootSubstrateContainer[];
  edges: RootSubstrateRelationEdge[];
  bandCounts: Record<RootSubstrateBand, number>;
  freshnessLine: string;
  omissionLine: string;
  sourceLineage: string[];
  legend: RootSubstrateAtlasLegend;
}

const SUBSTRATE_BAND_META: Record<RootSubstrateBand, { label: string; short: string; description: string; accent: string }> = {
  durable_substrate: {
    label: 'Durable substrate',
    short: 'durable',
    description: 'Axioms, principles, standards, concepts, mechanisms, paper modules: the immutable doctrine surface.',
    accent: '#c7b06a',
  },
  reference_substrate: {
    label: 'Reference substrate',
    short: 'reference',
    description: 'Raw seed, annexes, distillation patterns, system atlas: source authority the substrate metabolizes from.',
    accent: '#7dd3fc',
  },
  operational_overlay: {
    label: 'Operational overlays',
    short: 'overlay',
    description: 'WorkItems, frontend views and components: procedural state overlaying the substrate, not its peer.',
    accent: '#fb7185',
  },
};

const SUBSTRATE_BAND_ORDER: RootSubstrateBand[] = [
  'durable_substrate',
  'reference_substrate',
  'operational_overlay',
];

const SUBSTRATE_BAND_FOR_KIND: Record<string, RootSubstrateBand> = {
  axiom_candidates: 'durable_substrate',
  principles: 'durable_substrate',
  standards: 'durable_substrate',
  concepts: 'durable_substrate',
  mechanisms: 'durable_substrate',
  paper_modules: 'durable_substrate',
  raw_seed_shards: 'reference_substrate',
  annexes: 'reference_substrate',
  annex_distillation_patterns: 'reference_substrate',
  system_atlas: 'reference_substrate',
  task_ledger: 'operational_overlay',
  frontend_views: 'operational_overlay',
  frontend_components: 'operational_overlay',
};

function substrateBandForKind(kind: string): RootSubstrateBand {
  return SUBSTRATE_BAND_FOR_KIND[kind] ?? 'reference_substrate';
}

const SUBSTRATE_RELATION_META: Record<RootSubstrateRelation, { label: string; meaning: string; tone: string; strokeDash?: string; opacity: number }> = {
  compresses: { label: 'compresses', meaning: 'higher-level prior compresses a wider field below it', tone: '#c7b06a', opacity: 0.85 },
  applies: { label: 'applies via', meaning: 'principles are applied through standards', tone: '#67e8f9', opacity: 0.8 },
  constrains: { label: 'constrains shape of', meaning: 'standards constrain the shape of other artifacts', tone: '#67e8f9', opacity: 0.6, strokeDash: '3 2' },
  names: { label: 'names', meaning: 'concepts name the vocabulary other substrate borrows', tone: '#a78bfa', opacity: 0.6, strokeDash: '2 2' },
  operationalizes: { label: 'operationalizes', meaning: 'mechanisms describe the flow that connects substrate', tone: '#a78bfa', opacity: 0.6, strokeDash: '4 2' },
  explains: { label: 'explains', meaning: 'paper modules explain a subsystem family', tone: '#fbbf24', opacity: 0.6, strokeDash: '5 2' },
  projects: { label: 'projects', meaning: 'frontend views project substrate state for the operator', tone: '#fb7185', opacity: 0.55, strokeDash: '4 3' },
  repairs: { label: 'routes repair to', meaning: 'WorkItems route mutation pressure into substrate', tone: '#fb7185', opacity: 0.55, strokeDash: '5 3' },
  sources: { label: 'sources', meaning: 'raw seed and annexes are source authority the substrate metabolizes from', tone: '#7dd3fc', opacity: 0.6 },
  shares_axis: { label: 'shares axis', meaning: 'lives in the same ontology rail group declared by the packet', tone: 'rgba(226,232,240,0.32)', opacity: 0.3, strokeDash: '1 3' },
};

const SUBSTRATE_CANONICAL_RELATIONS: ReadonlyArray<{ source: string; target: string; family: RootSubstrateRelation }> = [
  { source: 'axiom_candidates', target: 'principles', family: 'compresses' },
  { source: 'axiom_candidates', target: 'standards', family: 'compresses' },
  { source: 'principles', target: 'standards', family: 'applies' },
  { source: 'standards', target: 'concepts', family: 'constrains' },
  { source: 'standards', target: 'mechanisms', family: 'constrains' },
  { source: 'standards', target: 'paper_modules', family: 'constrains' },
  { source: 'concepts', target: 'principles', family: 'names' },
  { source: 'concepts', target: 'standards', family: 'names' },
  { source: 'mechanisms', target: 'concepts', family: 'operationalizes' },
  { source: 'mechanisms', target: 'standards', family: 'operationalizes' },
  { source: 'paper_modules', target: 'principles', family: 'explains' },
  { source: 'paper_modules', target: 'standards', family: 'explains' },
  { source: 'paper_modules', target: 'mechanisms', family: 'explains' },
  { source: 'raw_seed_shards', target: 'axiom_candidates', family: 'sources' },
  { source: 'raw_seed_shards', target: 'principles', family: 'sources' },
  { source: 'annexes', target: 'paper_modules', family: 'sources' },
  { source: 'annex_distillation_patterns', target: 'paper_modules', family: 'sources' },
  { source: 'system_atlas', target: 'paper_modules', family: 'projects' },
  { source: 'task_ledger', target: 'standards', family: 'repairs' },
  { source: 'task_ledger', target: 'paper_modules', family: 'repairs' },
  { source: 'frontend_views', target: 'paper_modules', family: 'projects' },
  { source: 'frontend_views', target: 'principles', family: 'projects' },
  { source: 'frontend_components', target: 'frontend_views', family: 'projects' },
];

function buildRootSubstrateAtlasModel({
  packet,
  axes,
}: {
  packet: RootNavigatorHandoffPacket | null;
  axes: RootNavigatorPrimitiveAxis[];
}): RootSubstrateAtlasModel {
  const rows = packet?.semantic_primitive_matrix?.rows ?? [];
  const seen = new Set<string>();
  const containers: RootSubstrateContainer[] = [];
  const countsTrusted = rootCoverageCountsTrusted(packet);

  for (const row of rows) {
    if (!row || !row.candidate_primitive || seen.has(row.candidate_primitive)) continue;
    seen.add(row.candidate_primitive);
    const kind = row.candidate_primitive;
    const meta = artifactMeta(kind);
    const axis = axes.find((a) => (a.candidate_kinds ?? []).includes(kind));
    containers.push({
      id: relationNodeId('substrate-container', kind),
      kind,
      band: substrateBandForKind(kind),
      label: asString(meta.label ?? row.title, kind),
      role: asString(row.role_in_root_navigator, 'source-owned ontology object'),
      axisLabel: asString(axis?.label, axis?.axis_id ?? 'unassigned axis'),
      axisId: asString(axis?.axis_id, 'unassigned'),
      rowCount: asNumber(row.row_count),
      status: asString(row.support_status, 'unknown'),
      countsTrusted,
      hasOptionSurface: isHealthy(row.support_status),
      icon: meta.icon,
    });
  }

  const containerByKind = new Map<string, RootSubstrateContainer>();
  for (const c of containers) containerByKind.set(c.kind, c);

  const edges: RootSubstrateRelationEdge[] = [];
  const seenEdges = new Set<string>();

  for (const rel of SUBSTRATE_CANONICAL_RELATIONS) {
    const sourceContainer = containerByKind.get(rel.source);
    const targetContainer = containerByKind.get(rel.target);
    if (!sourceContainer || !targetContainer) continue;
    const id = `${sourceContainer.id}->${targetContainer.id}:${rel.family}`;
    if (seenEdges.has(id)) continue;
    seenEdges.add(id);
    edges.push({
      id,
      source: sourceContainer.id,
      target: targetContainer.id,
      family: rel.family,
      authority: 'derived_canonical',
    });
  }

  for (const axis of axes) {
    const presentKinds = (axis.candidate_kinds ?? []).filter((kind) => containerByKind.has(kind));
    for (let i = 0; i < presentKinds.length; i++) {
      for (let j = i + 1; j < presentKinds.length; j++) {
        const a = containerByKind.get(presentKinds[i])!;
        const b = containerByKind.get(presentKinds[j])!;
        const sortedPair = [a.id, b.id].sort();
        const id = `${sortedPair[0]}<>${sortedPair[1]}:shares_axis`;
        if (seenEdges.has(id)) continue;
        seenEdges.add(id);
        edges.push({
          id,
          source: a.id,
          target: b.id,
          family: 'shares_axis',
          authority: 'derived_axis_neighbor',
        });
      }
    }
  }

  const bandCounts: Record<RootSubstrateBand, number> = {
    durable_substrate: 0,
    reference_substrate: 0,
    operational_overlay: 0,
  };
  for (const c of containers) bandCounts[c.band] += 1;

  const totalKnownRows = containers.reduce((sum, c) => sum + (c.rowCount ?? 0), 0);
  const freshnessLine = packet
    ? `${asString(packet.authority_posture, 'projection')} · ${containers.length} containers · ${countsTrusted ? `${totalKnownRows} ontology rows` : 'row counts unverified'}`
    : 'loading root substrate atlas';
  const omissionLine =
    'substrate atlas derives from packet.semantic_primitive_matrix and primitive_axes; row counts are shown only when root coverage freshness is verified; operational overlays are not substrate peers';

  const legend: RootSubstrateAtlasLegend = {
    bands: SUBSTRATE_BAND_ORDER.map((band) => ({
      key: band,
      label: SUBSTRATE_BAND_META[band].label,
      meaning: SUBSTRATE_BAND_META[band].description,
    })),
    edgeFamilies: (Object.keys(SUBSTRATE_RELATION_META) as RootSubstrateRelation[])
      .filter((family) => edges.some((edge) => edge.family === family))
      .map((family) => ({
        key: family,
        label: SUBSTRATE_RELATION_META[family].label,
        meaning: SUBSTRATE_RELATION_META[family].meaning,
      })),
    encoding: [
      { key: 'color', label: 'color', meaning: 'band membership (durable / reference / overlay)' },
      { key: 'border', label: 'border', meaning: 'support_status from option-surface (supported, partial, unknown, gated)' },
      { key: 'count', label: 'count', meaning: 'ontology row count; suppressed when coverage freshness is unverified' },
      { key: 'edges', label: 'edges', meaning: 'sparse by default; selection highlights canonical and axis-shared relations' },
    ],
  };

  const sourceLineage = [
    asString(packet?.view?.purpose, ''),
    `${rows.length} primitive matrix rows`,
    `${axes.length} primitive axes`,
  ].filter(Boolean);

  return { containers, edges, bandCounts, freshnessLine, omissionLine, sourceLineage, legend };
}

function buildRootWorkbenchGraph({
  packet,
  axes,
  viewModel,
  selectedPrimitive,
  selectedAxis,
  selectedRow,
  drilldownPacket,
  cardPacket,
  parentCluster,
}: {
  packet: RootNavigatorHandoffPacket | null;
  axes: RootNavigatorPrimitiveAxis[];
  viewModel: RootDoctrineCrystalViewModel;
  selectedPrimitive: RootNavigatorPrimitiveRow | null;
  selectedAxis: RootNavigatorPrimitiveAxis | null;
  selectedRow: UnknownRow | null;
  drilldownPacket: NavigationSurfacePacket | null;
  cardPacket: NavigationSurfacePacket | null;
  parentCluster: ParentClusterInfo | null;
}): RootWorkbenchGraphModel {
  const nodes: RootWorkbenchNode[] = [];
  const edges: RootWorkbenchEdge[] = [];
  const addNode = (node: RootWorkbenchNode) => nodes.push(node);
  const addEdge = (source: string, target: string, label: string) => {
    if (!nodes.some((node) => node.id === source) || !nodes.some((node) => node.id === target)) return;
    edges.push({ id: `${source}->${target}:${label}`, source, target, label });
  };
  const packetPurpose = asString(packet?.view?.purpose ?? packet?.constitutional_atlas?.purpose_one_line);
  const loadedRows = (drilldownPacket?.rows ?? []).filter(isRecord);
  const drilldownTotalAvailable = asNumber(drilldownPacket?.summary?.total_available);
  const loadedRowsLabel =
    loadedRows.length > 0
      ? drilldownTotalAvailable && drilldownTotalAvailable > loadedRows.length
        ? `${loadedRows.length} of ${drilldownTotalAvailable} shown`
        : `${loadedRows.length} loaded rows`
      : 'Rows pending';
  const packetSourceCount = viewModel.sourceRefs.length;
  const sourceLine = packet
    ? `${asString(packet.authority_posture, 'projection')} · ${packetSourceCount} source refs`
    : 'loading root navigator packet';
  const omissionLine = 'root graph derives from the RootNavigator packet, option-surface row, coverage state, and navigation graph health; destination graphs remain source-owned lenses';

  if (selectedPrimitive && selectedRow) {
    const rowId = rowPrimaryId(selectedRow, 'selected-row');
    const rowRefs = rowSourceRefs(selectedRow);
    const focusId = relationNodeId('row', rowId);
    addNode({
      id: focusId,
      role: 'focus',
      label: rowLabel(selectedRow, rowId),
      kicker: asString(selectedRow.artifact_kind ?? 'selected row', 'selected row'),
      detail: firstNonEmpty(rowClaim(selectedRow), asString(selectedRow.band), 'selected option-surface row'),
      status: rowStatus(selectedRow),
      x: 50,
      y: 50,
      rowRef: rowId,
    });
    const primitiveId = relationNodeId('kind', selectedPrimitive.candidate_primitive);
    addNode({
      id: primitiveId,
      role: 'context',
      label: asString(artifactMeta(selectedPrimitive.candidate_primitive).label ?? selectedPrimitive.title, selectedPrimitive.candidate_primitive),
      kicker: 'parent kind',
      detail: asString(selectedPrimitive.role_in_root_navigator, 'primitive kind selected from artifact rail'),
      status: selectedPrimitive.support_status,
      x: 21,
      y: parentCluster ? 30 : 50,
      kindRef: selectedPrimitive.candidate_primitive,
    });
    addEdge(primitiveId, focusId, 'contains');
    if (parentCluster) {
      const clusterId = relationNodeId('cluster', parentCluster.rowId || parentCluster.clusterId);
      addNode({
        id: clusterId,
        role: 'projection',
        label: parentCluster.label,
        kicker: 'parent cluster',
        detail: `${parentCluster.memberKind} grouped by ${parentCluster.membershipSource}`,
        status: 'projection',
        x: 22,
        y: 73,
        rowRef: parentCluster.rowId,
      });
      addEdge(clusterId, focusId, 'groups');
    }
    const sourceId = 'selected-row-source';
    addNode({
      id: sourceId,
      role: 'evidence',
      label: rowRefs.length > 0 ? `${rowRefs.length} source refs` : 'Source refs pending',
      kicker: 'evidence',
      detail: rowRefs[0] ?? 'row did not expose direct source refs',
      status: rowRefs.length > 0 ? 'listed' : 'unknown',
      x: 78,
      y: 31,
      inspectorTab: 'Evidence',
    });
    addEdge(sourceId, focusId, 'sources');
    const cardId = 'selected-row-card-packet';
    addNode({
      id: cardId,
      role: 'route',
      label: cardPacket ? 'Card packet loaded' : 'Card packet pending',
      kicker: 'agent route',
      detail: asString(selectedRow.drilldown_command ?? selectedRow.evidence_command ?? 'option-surface card drilldown'),
      status: cardPacket ? 'ready' : 'partial',
      x: 78,
      y: 73,
      inspectorTab: 'Agent route',
    });
    addEdge(focusId, cardId, 'opens');
    return { nodes, edges, focusId, sourceLine, omissionLine };
  }

  if (selectedPrimitive) {
    const primitiveKind = selectedPrimitive.candidate_primitive;
    const meta = artifactMeta(primitiveKind);
    const focusId = relationNodeId('kind', primitiveKind);
    addNode({
      id: focusId,
      role: 'focus',
      label: asString(meta.label ?? selectedPrimitive.title, primitiveKind),
      kicker: asString(selectedAxis?.label, 'selected primitive'),
      detail: firstNonEmpty(
        asString(selectedPrimitive.role_in_root_navigator),
        asString(selectedPrimitive.projection_rule),
        'source-owned option-surface primitive',
      ),
      relationHint: meta.edge,
      status: selectedPrimitive.support_status,
      x: 50,
      y: 50,
      kindRef: primitiveKind,
    });
    if (selectedAxis) {
      const siblings = (selectedAxis.candidate_kinds ?? []).filter((kind) => kind !== primitiveKind).slice(0, 3);
      const axisId = relationNodeId('axis', selectedAxis.axis_id);
      addNode({
        id: axisId,
        role: 'context',
        label: asString(selectedAxis.label, selectedAxis.axis_id),
        kicker: 'ontology rail group',
        detail: asString(selectedAxis.projection_role, 'groups source-owned primitives'),
        status: 'projection',
        x: 21,
        y: siblings.length > 2 ? 14 : 22,
        inspectorTab: 'Relations',
      });
      addEdge(axisId, focusId, 'groups');
      siblings.forEach((kind, index) => {
        const sibling = packet?.semantic_primitive_matrix?.rows?.find((row) => row.candidate_primitive === kind);
        const siblingMeta = artifactMeta(kind);
        const siblingId = relationNodeId('kind', kind);
        const siblingY = siblings.length > 2 ? 42 + index * 24 : 52 + index * 28;
        addNode({
          id: siblingId,
          role: 'context',
          label: asString(siblingMeta.label ?? sibling?.title, kind),
          kicker: 'axis neighbor',
          detail: asString(sibling?.role_in_root_navigator, 'same ontology rail group'),
          relationHint: siblingMeta.edge,
          status: sibling?.support_status ?? 'unknown',
          x: 21,
          y: siblingY,
          kindRef: kind,
        });
        addEdge(axisId, siblingId, 'also contains');
        addEdge(siblingId, focusId, siblingMeta.edge);
      });
    }
    const rowsId = 'selected-kind-rows';
    addNode({
      id: rowsId,
      role: 'projection',
      label: loadedRowsLabel,
      kicker: 'option surface',
      detail: drilldownPacket
        ? `band ${asString(drilldownPacket.band, packetBandForRow(selectedPrimitive))} · source-owned sample`
        : `band ${packetBandForRow(selectedPrimitive)}`,
      status: drilldownPacket ? 'ready' : 'partial',
      x: 79,
      y: 22,
      inspectorTab: 'Relations',
    });
    addEdge(focusId, rowsId, 'projects');
    const sourceId = 'selected-kind-sources';
    const ownRefs = Array.from(
      new Set([
        ...asStringArray(selectedPrimitive.governing_standard_refs),
        ...asStringArray(selectedPrimitive.projection_refs),
        ...viewModel.sourceRefs,
      ]),
    );
    addNode({
      id: sourceId,
      role: 'evidence',
      label: ownRefs.length > 0 ? `${ownRefs.length} source refs` : 'Source refs pending',
      kicker: 'evidence',
      detail: ownRefs[0] ?? 'packet source refs not loaded yet',
      status: ownRefs.length > 0 ? 'listed' : 'unknown',
      x: 79,
      y: 50,
      inspectorTab: 'Evidence',
    });
    addEdge(sourceId, focusId, 'sources');
    const routeId = 'selected-kind-route';
    addNode({
      id: routeId,
      role: 'route',
      label: 'Agent route',
      kicker: 'control plane',
      detail: asString(selectedPrimitive.option_surface_command ?? selectedPrimitive.card_command ?? selectedPrimitive.evidence_command, 'kernel option surface'),
      status: 'available',
      x: 79,
      y: 78,
      inspectorTab: 'Agent route',
    });
    addEdge(focusId, routeId, 'opens');
    return { nodes, edges, focusId, sourceLine, omissionLine };
  }

  const focusId = 'root-substrate-graph';
  addNode({
    id: focusId,
    role: 'focus',
    label: 'Root substrate graph',
    kicker: 'canonical workbench',
    detail: packetPurpose || 'relation-bearing map over doctrine, routes, evidence, work, and repair pressure',
    status: packet ? 'ready' : 'loading',
    x: 50,
    y: 50,
  });
  const primitiveId = 'primitive-matrix-node';
  addNode({
    id: primitiveId,
    role: 'context',
    label: 'Primitive matrix',
    kicker: 'left rail source',
    detail: `${axes.length} ontology groups · ${viewModel.graphNodes.length} supported primitive rows`,
    status: viewModel.graphNodes.length > 0 ? 'supported' : 'unknown',
    x: 22,
    y: 22,
    inspectorTab: 'Relations',
  });
  const surfaceId = 'surface-graph-node';
  addNode({
    id: surfaceId,
    role: 'route',
    label: 'Frontend surfaces',
    kicker: 'navigation graph',
    detail: `${GRAPH_HANDOFFS.length} graph lenses now carry return + viability + freshness`,
    status: 'projection',
    x: 78,
    y: 22,
    kindRef: 'frontend_views',
  });
  const evidenceId = 'evidence-node';
  addNode({
    id: evidenceId,
    role: 'evidence',
    label: 'Evidence + receipts',
    kicker: 'proof plane',
    detail: `${packetSourceCount} packet source refs · station renders own screenshot truth`,
    status: packetSourceCount > 0 ? 'listed' : 'unknown',
    x: 78,
    y: 76,
    inspectorTab: 'Evidence',
  });
  const workId = 'work-repair-node';
  addNode({
    id: workId,
    role: 'health',
    label: 'Work + repair pressure',
    kicker: 'task ledger',
    detail: `${viewModel.gates.length} root gates · mutations route through WorkItems/apply lanes`,
    status: 'read_only',
    x: 22,
    y: 76,
    inspectorTab: 'Agent route',
  });
  addEdge(focusId, primitiveId, 'organizes');
  addEdge(focusId, surfaceId, 'opens lenses');
  addEdge(evidenceId, focusId, 'proves');
  addEdge(workId, focusId, 'routes repair');
  return { nodes, edges, focusId, sourceLine, omissionLine };
}

function buildRootDoctrineCrystalViewModel({
  packet,
  coverage,
  selectedPrimitive,
  packetError,
  loading,
}: {
  packet: RootNavigatorHandoffPacket | null;
  coverage: RootCoverageState | null;
  selectedPrimitive: RootNavigatorPrimitiveRow | null;
  packetError: string | null;
  loading: boolean;
}): RootDoctrineCrystalViewModel {
  const countsTrusted = rootCoverageCountsTrusted(packet);
  const coverageStatus = rootCoverageStateLabel(packet);
  const coverageGenerated = coverage?.generated_at ?? packet?.root_coverage_state?.generated_at ?? 'unknown';
  const sourceRefs = asStringArray(packet?.source_refs);
  const relationAuthoritySources = asStringArray(packet?.constitutional_atlas?.relation_authority_sources);
  const routeConflictCount = packet?.root_coverage_state?.summary?.route_conflict_count ?? coverage?.route_conflicts?.length ?? 0;
  const missingBranchCount = packet?.root_coverage_state?.summary?.missing_branch_count ?? coverage?.missing_branches?.length ?? 0;
  const evidenceGapCount = packet?.root_coverage_state?.summary?.evidence_gap_count ?? coverage?.evidence_gaps?.length ?? 0;
  const evidenceMixed = routeConflictCount > 0 || missingBranchCount > 0 || evidenceGapCount > 0;
  const sourceListed = sourceRefs.length > 0;
  const supportedRows = packet?.semantic_primitive_matrix?.rows?.filter((row) =>
    normalizeStatus(row.support_status) === 'green',
  ) ?? [];

  const rows = packet?.semantic_primitive_matrix?.rows ?? [];
  const graphNodes = rows.slice(0, 12).map((row, index) => {
    const meta = artifactMeta(row.candidate_primitive);
    const accent = axisAccent(asString(row.axis, `axis-${index}`));
    return {
      id: row.candidate_primitive,
      label: asString(meta.label ?? row.title, row.candidate_primitive),
      kind: row.candidate_primitive,
      role: asString(row.role_in_root_navigator, 'projection row'),
      status: normalizeStatus(row.support_status ?? row.status),
      count: countLabel(row.row_count, countsTrusted),
      icon: meta.icon,
      accent,
      edge: meta.edge,
    };
  });
  const selectedGraphNode = selectedPrimitive
    ? graphNodes.find((node) => node.id === selectedPrimitive.candidate_primitive) ?? null
    : graphNodes.find((node) => node.id === 'standards') ?? graphNodes[0] ?? null;
  const annexRow =
    (coverage?.branches ?? []).find((row) => row.id === 'annexes' || row.label.toLowerCase().includes('annex')) ?? null;
  const actionability = 'READ ONLY';
  const countUnavailableReason = countsTrusted
    ? `root coverage generated ${coverageGenerated}`
    : `counts hidden until ${asString(packet?.root_coverage_state?.freshness_check_command, 'root coverage check')} is green`;
  const stateAxes: RootCrystalStateAxis[] = [
    {
      id: 'backend_connection',
      label: 'Backend Connection',
      value: packetError ? 'DEGRADED' : loading ? 'CONNECTING' : 'LIVE',
      tone: packetError ? 'partial' : loading ? 'neutral' : 'green',
      reason: packetError ?? 'root-navigator packet endpoint responded',
    },
    {
      id: 'projection_freshness',
      label: 'Projection Freshness',
      value: countsTrusted ? 'FRESH' : normalizeStatus(coverageStatus).toUpperCase(),
      tone: countsTrusted ? 'green' : statusTone(coverageStatus),
      reason: countUnavailableReason,
    },
    {
      id: 'authority_class',
      label: 'Authority Class',
      value: 'PROJECTION',
      tone: 'neutral',
      reason: asString(packet?.authority_posture, 'root navigator packet is not source authority'),
    },
    {
      id: 'evidence_quality',
      label: 'Evidence Quality',
      value: evidenceMixed ? 'MIXED' : countsTrusted ? 'VERIFIED' : 'UNKNOWN',
      tone: evidenceMixed ? 'partial' : countsTrusted ? 'green' : 'neutral',
      reason: `${routeConflictCount} route conflicts · ${missingBranchCount} missing branches · ${evidenceGapCount} evidence gaps`,
    },
    {
      id: 'actionability',
      label: 'Actionability',
      value: actionability,
      tone: 'neutral',
      reason: 'root crystal is read-mostly; mutations route through apply/work/capture lanes',
    },
  ];
  const gates: RootCrystalGate[] = [
    {
      id: 'backend',
      label: 'Backend',
      state: packetError ? 'degraded' : 'live',
      tone: packetError ? 'partial' : 'green',
      reason: packetError ?? 'root navigator and coverage data are loaded from API sources',
      recovery: 'Refresh or inspect /api/system/root-navigator-handoff',
    },
    {
      id: 'projection',
      label: 'Projection',
      state: countsTrusted ? 'fresh' : normalizeStatus(coverageStatus),
      tone: countsTrusted ? 'green' : statusTone(coverageStatus),
      reason: countUnavailableReason,
      recovery: asString(packet?.root_coverage_state?.freshness_check_command, './repo-python tools/meta/factory/build_root_coverage_state.py --check'),
    },
    {
      id: 'evidence',
      label: 'Evidence',
      state: evidenceMixed ? 'mixed' : countsTrusted ? 'verified' : 'unknown',
      tone: evidenceMixed ? 'partial' : countsTrusted ? 'green' : 'neutral',
      reason: `${routeConflictCount} conflicts · ${missingBranchCount} missing branches · ${evidenceGapCount} gaps`,
      recovery: 'Open Evidence tab',
    },
    {
      id: 'source',
      label: 'Source',
      state: sourceListed ? 'listed' : 'missing',
      tone: sourceListed ? 'green' : 'missing',
      reason: `${sourceRefs.length} source refs in root navigator packet`,
      recovery: 'Inspect Source',
    },
    {
      id: 'apply',
      label: 'Apply',
      state: 'read-only',
      tone: 'neutral',
      reason: 'no direct doctrine mutation from root crystal',
      recovery: 'Open Apply Lane or WorkItem',
    },
    {
      id: 'type_support',
      label: 'Type Support',
      state: supportedRows.length > 0 ? 'supported' : 'unknown',
      tone: supportedRows.length > 0 ? 'green' : 'neutral',
      reason: `${supportedRows.length} primitive rows expose option-surface support`,
      recovery: 'Use artifact rail or Agent route tab',
    },
    {
      id: 'annex_focus',
      label: 'Annex',
      state: annexRow ? 'nested' : 'focus pending',
      tone: annexRow ? 'green' : 'partial',
      reason: annexRow
        ? `${annexRow.label} is present as a root coverage branch`
        : 'annex distillation focus remains nested under root crystal',
      recovery: 'Select annex coverage row or inspect annex distillation index',
    },
  ];

  return {
    countsTrusted,
    countUnavailableReason,
    stateAxes,
    gates,
    graphNodes,
    selectedGraphNode,
    annexRow,
    sourceRefs,
    relationAuthoritySources,
    readOnlyActions: ROOT_ACTIONS,
    captureCommand: asString(packet?.frontend_surface_agent_packet?.operator_cli_hints?.capture, './repo-python kernel.py --view-capture rootNavigator'),
  };
}

interface SelectedKindCenterCardProps {
  primitive: RootNavigatorPrimitiveRow;
  axis: RootNavigatorPrimitiveAxis | null;
  countsTrusted: boolean;
  drilldownRowCount: number;
  drilldownTotalAvailable: number | null;
  packetSourceRefCount: number;
  drilldownLoading: boolean;
  drilldownError: string | null;
  drilldownLoaded: boolean;
}

function SelectedKindCenterCard({
  primitive,
  axis,
  countsTrusted,
  drilldownRowCount,
  drilldownTotalAvailable,
  packetSourceRefCount,
  drilldownLoading,
  drilldownError,
  drilldownLoaded,
}: SelectedKindCenterCardProps) {
  const meta = artifactMeta(primitive.candidate_primitive);
  const Icon = meta.icon;
  const accent = axis ? axisAccent(axis.axis_id) : '#c7b06a';
  const role = asString(primitive.role_in_root_navigator);
  const projectionRule = asString(primitive.projection_rule);
  const support = asString(primitive.support_status, 'unknown');
  const supportedBands = asStringArray(primitive.supported_bands);
  const optionSurfaceCommand = asString(primitive.option_surface_command);
  const evidenceCommand = asString(primitive.evidence_command);
  const loadedRowsLabel =
    drilldownRowCount > 0
      ? drilldownTotalAvailable && drilldownTotalAvailable > drilldownRowCount
        ? `${drilldownRowCount} of ${drilldownTotalAvailable} shown · source-owned sample`
        : `${drilldownRowCount} loaded rows`
      : drilldownLoaded
        ? '0 via option surface'
        : 'pending drilldown';
  const ownRefs = Array.from(
    new Set([
      ...asStringArray(primitive.governing_standard_refs),
      ...asStringArray(primitive.projection_refs),
    ]),
  );
  return (
    <div
      className="w-full rounded-[4px] border border-[#c7b06a]/50 bg-black/72 p-3 shadow-[0_0_42px_rgba(199,176,106,0.13)]"
      style={{ borderColor: accent + '88' }}
    >
      <div
        className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em]"
        style={{ color: accent }}
      >
        <Icon size={14} />
        <span>{asString(axis?.label, 'primitive axis')}</span>
      </div>
      <h3 className="mt-2 flex items-center gap-2 text-sm font-semibold text-white">
        <span className="truncate">{asString(meta.label ?? primitive.title, primitive.candidate_primitive)}</span>
        <StatusPill status={support} dim />
      </h3>
      {role && <p className="mt-1 text-[11px] leading-4 text-white/68">{role}</p>}
      {projectionRule && (
        <div className="mt-2 rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">projection rule</div>
          <p className="mt-0.5 line-clamp-3 text-[11px] leading-4 text-zenith-soft">{projectionRule}</p>
        </div>
      )}
      <div className="my-3 h-px bg-gradient-to-r from-transparent via-[#c7b06a]/45 to-transparent" />
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">rows</div>
          <div className="mt-0.5 font-mono text-[11px] text-white/72">
            {countsTrusted ? countLabel(primitive.row_count, true) : 'hidden · freshness unverified'}
          </div>
        </div>
        <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">examples loaded</div>
          <div className="mt-0.5 font-mono text-[11px] text-white/72">
            {drilldownLoading
              ? 'loading option surface'
              : drilldownError
                ? 'unavailable'
                : loadedRowsLabel}
          </div>
        </div>
        <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">source refs</div>
          <div className="mt-0.5 font-mono text-[11px] text-white/72">
            {ownRefs.length > 0
              ? `${ownRefs.length} on row · ${packetSourceRefCount} on packet`
              : `${packetSourceRefCount} on packet`}
          </div>
        </div>
        <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">supported bands</div>
          <div className="mt-0.5 font-mono text-[11px] text-white/72 truncate">
            {supportedBands.length > 0 ? supportedBands.join(' · ') : 'unknown'}
          </div>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        <span className="rounded border border-zenith-edge bg-white/[0.035] px-2 py-0.5 font-mono text-[10px] text-zenith-soft">
          authority: projection
        </span>
        <span className="rounded border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 font-mono text-[10px] text-emerald-100/75">
          read-only
        </span>
        {evidenceCommand && (
          <span className="rounded border border-cyan-300/20 bg-cyan-300/10 px-2 py-0.5 font-mono text-[10px] text-cyan-100/75">
            evidence command available
          </span>
        )}
        {optionSurfaceCommand && (
          <span className="rounded border border-[#c7b06a]/30 bg-[#c7b06a]/10 px-2 py-0.5 font-mono text-[10px] text-[#c7b06a]/85">
            open full option-surface lens
          </span>
        )}
      </div>
    </div>
  );
}

interface SelectedClusterLensCardProps {
  primitive: RootNavigatorPrimitiveRow;
  axis: RootNavigatorPrimitiveAxis | null;
  row: UnknownRow;
  drilldownPacket: NavigationSurfacePacket | null;
  cardPacket: NavigationSurfacePacket | null;
  cardLoading: boolean;
  cardError: string | null;
  packetSourceRefCount: number;
  onSelectRow: (rowId: string) => void;
  memberPreviewRowsById: Map<string, UnknownRow>;
}

function SelectedClusterLensCard({
  primitive,
  axis,
  row,
  drilldownPacket,
  cardPacket,
  cardLoading,
  cardError,
  packetSourceRefCount,
  onSelectRow,
  memberPreviewRowsById,
}: SelectedClusterLensCardProps) {
  const memberKind = clusterMemberKind(row, primitive);
  const meta = artifactMeta(primitive.candidate_primitive);
  const Icon = meta.icon;
  const accent = axis ? axisAccent(axis.axis_id) : '#c7b06a';
  const kindLabel = asString(meta.label ?? primitive.title, primitive.candidate_primitive);
  const axisLabel = asString(axis?.label, axis?.axis_id ?? 'axis');
  const label = rowLabel(row, asString(row.id, 'cluster'));
  const id = rowPrimaryId(row, '');
  const clusterId = asString(row.cluster_id);
  const role = asString(primitive.role_in_root_navigator);
  const projectionRule = asString(primitive.projection_rule);
  const directRefs = rowSourceRefs(row);
  const cardRefs = asStringArray(cardPacket?.source_refs);
  const drilldownRows = (drilldownPacket?.rows ?? []).filter(isRecord);
  // Source-owned membership: cluster row carries explicit top_ids + count + card_drilldown_command
  const memberCount = typeof row.count === 'number' ? row.count : null;
  const sourceOwnedMemberIds = asStringArray(row.top_ids);
  const cardDrilldownCommand = asString(row.card_drilldown_command);
  const drilldownChildren = drilldownRows
    .filter((other) => rowPrimaryId(other, '') !== id)
    .filter((other) => {
      const species = classifySelectedObject(other);
      return species === 'leaf_row' || species === 'source_ref_row';
    });
  // Resolved children: any drilldown leaves that match source-owned member ids (highest fidelity)
  const resolvedChildren = sourceOwnedMemberIds.length > 0
    ? drilldownChildren.filter((child) => {
        const childId = rowPrimaryId(child, '');
        const principleId = asString(child.principle_id ?? child.id ?? child.row_id);
        return sourceOwnedMemberIds.includes(childId) || sourceOwnedMemberIds.includes(principleId);
      })
    : drilldownChildren;
  const childCandidates = resolvedChildren.slice(0, 6);
  const membershipState: 'resolved' | 'source_known' | 'unavailable' =
    childCandidates.length > 0
      ? 'resolved'
      : sourceOwnedMemberIds.length > 0 || (memberCount !== null && memberCount > 0)
        ? 'source_known'
        : 'unavailable';
  const loadedSliceLabel =
    memberCount !== null && sourceOwnedMemberIds.length > 0
      ? `${sourceOwnedMemberIds.length} of ${memberCount} shown · source-owned sample`
      : sourceOwnedMemberIds.length > 0
        ? `${sourceOwnedMemberIds.length} shown · source-owned sample`
        : memberCount !== null
          ? `${memberCount} available · preview unloaded`
          : 'preview unavailable';
  const cardStatusLabel = cardLoading
    ? 'loading'
    : cardError
      ? 'unavailable'
      : cardPacket
        ? 'loaded'
        : 'pending';
  const cardStatusTone = cardError ? 'partial' : cardPacket ? 'green' : 'partial';
  const optionSurfaceCommand = asString(primitive.option_surface_command);
  return (
    <div
      className="w-full rounded-[4px] border bg-black/72 p-3 shadow-[0_0_42px_rgba(199,176,106,0.13)]"
      style={{ borderColor: accent + '88' }}
    >
      <div
        className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em]"
        style={{ color: accent }}
      >
        <Icon size={14} />
        <span className="truncate">{kindLabel} · {axisLabel}</span>
      </div>
      <h3 className="mt-2 flex items-center gap-2 text-sm font-semibold text-white">
        <span className="truncate">{label}</span>
        <StatusPill status="partial" label="cluster" dim />
      </h3>
      {clusterId && (
        <div className="mt-0.5 font-mono text-[10px] text-white/35">cluster id · {clusterId}</div>
      )}
      {role && (
        <p className="mt-1 line-clamp-3 text-[11px] leading-4 text-white/68">{role}</p>
      )}
      {projectionRule && (
        <div className="mt-2 rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">projection rule</div>
          <p className="mt-0.5 line-clamp-2 text-[11px] leading-4 text-zenith-soft">{projectionRule}</p>
        </div>
      )}
      <div className="my-3 h-px bg-gradient-to-r from-transparent via-[#c7b06a]/45 to-transparent" />
      <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
        <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">source provenance</div>
        <div className="mt-1 grid gap-0.5 font-mono text-[11px] text-white/72">
          <div>direct: {directRefs.length > 0 ? `${directRefs.length}` : 'unavailable'}</div>
          <div>card: {cardRefs.length > 0 ? `${cardRefs.length}` : 'unavailable'}</div>
          <div>inherited packet refs: {packetSourceRefCount}</div>
        </div>
      </div>
      <div className="mt-2 rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
        <div className="flex items-center justify-between gap-2">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
            {membershipState === 'unavailable' ? 'child / leaf candidates' : 'member preview'}
          </div>
          <div className="font-mono text-[10px] text-white/35">
            {membershipState === 'resolved'
              ? `${childCandidates.length}${memberCount !== null ? ` of ${memberCount}` : ''} resolved`
              : membershipState === 'source_known'
                ? loadedSliceLabel
                : 'unavailable'}
          </div>
        </div>
        {membershipState === 'resolved' ? (
          <ul className="mt-1 space-y-0.5">
            {childCandidates.map((child, index) => {
              const childId = rowPrimaryId(child, `child-${index}`);
              const childLabel = rowLabel(child, childId);
              const childRefs = rowSourceRefs(child).length;
              const childStatus = asString(child.status, 'unknown');
              const showChildStatus = shouldRenderRowStatus(childStatus, row.status, 'dense-list');
              return (
                <li key={`${childId}:${index}`}>
                  <button
                    type="button"
                    onClick={() => onSelectRow(childId)}
                    className="flex w-full items-center justify-between gap-2 rounded border border-zenith-edge bg-white/[0.02] px-2 py-1 font-mono text-[11px] text-white/72 hover:border-cyan-300/35 hover:text-cyan-100"
                    title={`open ${childId} via card-band fallback`}
                  >
                    <span className="truncate">{childLabel}</span>
                    <span className="flex shrink-0 items-center gap-1.5 text-[10px] text-zenith-muted">
                      <span>{childRefs} refs</span>
                      {showChildStatus && <StatusPill status={childStatus} dim />}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        ) : membershipState === 'source_known' ? (
          <div className="mt-1 space-y-1">
            <ul className="space-y-0.5">
              {sourceOwnedMemberIds.slice(0, 8).map((memberId) => {
                const previewRow = memberPreviewRowsById.get(memberId) ?? null;
                const previewTitle = previewRow ? rowLabel(previewRow, '') : '';
                const previewStatus = asString(previewRow?.status, 'unknown');
                const showPreviewStatus = shouldRenderRowStatus(previewStatus, row.status, 'dense-list');
                const previewRefs = previewRow ? rowSourceRefs(previewRow).length : 0;
                const accessibleLabel = previewTitle
                  ? `Open leaf ${memberId} — ${previewTitle}`
                  : `Open leaf ${memberId} (label unavailable)`;
                return (
                  <li key={memberId}>
                    <button
                      type="button"
                      onClick={() => onSelectRow(memberId)}
                      aria-label={accessibleLabel}
                      title={accessibleLabel}
                      className="flex w-full flex-col gap-0.5 rounded border border-zenith-edge bg-white/[0.02] px-2 py-1 text-left hover:border-cyan-300/35 hover:bg-white/[0.04]"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-[11px] text-white/72">{memberId}</span>
                        {previewRow && (
                          <span className="flex shrink-0 items-center gap-1.5 font-mono text-[10px] text-zenith-muted">
                            <span>direct refs {previewRefs}</span>
                            {showPreviewStatus && <StatusPill status={previewStatus} dim />}
                          </span>
                        )}
                      </div>
                      {previewTitle ? (
                        <div className="truncate text-[10px] leading-4 text-zenith-soft">{previewTitle}</div>
                      ) : (
                        <div className="text-[10px] leading-4 text-white/35">label unavailable · open leaf</div>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
            <div className="font-mono text-[10px] text-zenith-muted">
              membership source · cluster.top_ids
            </div>
            {memberPreviewRowsById.size > 0 && (
              <div className="font-mono text-[10px] text-zenith-muted">
                member preview hydration · card-band packet
              </div>
            )}
            {clusterId && (
              <div className="font-mono text-[10px] text-zenith-muted">
                membership rule · {memberKind}.type == {clusterId}
              </div>
            )}
            {cardDrilldownCommand && (
              <div className="font-mono text-[10px] text-cyan-100/65">
                drilldown · card-band command available for this loaded sample
              </div>
            )}
            {optionSurfaceCommand ? (
              <div className="font-mono text-[10px] text-[#c7b06a]/75">
                full lens · open Standards option surface for rows outside this sample
              </div>
            ) : (
              <div className="font-mono text-[10px] text-amber-100/70">
                full-list route missing · current packet exposes sample only
              </div>
            )}
          </div>
        ) : (
          <div className="mt-1 space-y-0.5 text-[11px] leading-4 text-zenith-soft">
            <div className="font-mono text-amber-100/80">child linkage unavailable</div>
            <div className="text-zenith-soft">
              Cluster row is an organizing schema; direct evidence requires a leaf row.
            </div>
            <div className="font-mono text-[10px] text-zenith-muted">
              owner · option-surface cluster-to-leaf linkage
            </div>
            <div className="font-mono text-[10px] text-zenith-muted">
              next resolution · leaf row required
            </div>
          </div>
        )}
      </div>
      <div className="mt-2 rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
        <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">card packet</div>
        <div className="mt-0.5 flex items-center gap-1.5">
          <StatusPill status={cardStatusTone} label={cardStatusLabel} dim />
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {optionSurfaceCommand && (
          <span className="inline-flex items-center gap-1.5 rounded-[3px] border border-cyan-300/20 bg-cyan-300/10 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-cyan-100/80">
            option surface ready
          </span>
        )}
        <a
          href="/station/ops"
          className="inline-flex items-center gap-1.5 rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-white/62 hover:border-[#c7b06a]/40 hover:text-[#f4e6a2]"
        >
          <Eye size={11} /> Open Apply Lane
        </a>
        <a
          href="/station/ledger"
          className="inline-flex items-center gap-1.5 rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-white/62 hover:border-[#c7b06a]/40 hover:text-[#f4e6a2]"
        >
          <Eye size={11} /> Open WorkItem
        </a>
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        <span className="rounded border border-zenith-edge bg-white/[0.035] px-2 py-0.5 font-mono text-[10px] text-zenith-soft">
          authority: projection · cluster groups its kind, source refs remain authority
        </span>
      </div>
    </div>
  );
}

interface SelectedRowEvidenceCardProps {
  primitive: RootNavigatorPrimitiveRow;
  axis: RootNavigatorPrimitiveAxis | null;
  row: UnknownRow;
  cardPacket: NavigationSurfacePacket | null;
  cardLoading: boolean;
  cardError: string | null;
  packetSourceRefCount: number;
  parentCluster: ParentClusterInfo | null;
}

function SelectedRowEvidenceCard({
  primitive,
  axis,
  row,
  cardPacket,
  cardLoading,
  cardError,
  packetSourceRefCount,
  parentCluster,
}: SelectedRowEvidenceCardProps) {
  const location = useLocation();
  const currentRoute = `${location.pathname}${location.search}`;
  const meta = artifactMeta(primitive.candidate_primitive);
  const Icon = meta.icon;
  const accent = axis ? axisAccent(axis.axis_id) : '#c7b06a';
  const kindLabel = asString(meta.label ?? primitive.title, primitive.candidate_primitive);
  const axisLabel = asString(axis?.label, axis?.axis_id ?? 'axis');
  const label = rowLabel(row, asString(row.id, 'row'));
  const id = rowPrimaryId(row, '');
  const claim = rowClaim(row);
  const rawStatus = asString(row.status ?? row.support_status ?? 'unknown', 'unknown');
  const ownRefs = rowSourceRefs(row);
  const cardRefs = asStringArray(cardPacket?.source_refs);
  const allRefs = Array.from(new Set([...ownRefs, ...cardRefs]));
  const previewRefs = allRefs.slice(0, 3);
  const drilldownCommand = asString(row.drilldown_command);
  const cardCommand = asString(row.card_command);
  const evidenceCommand = asString(row.evidence_command);
  const cardStatusLabel = cardLoading
    ? 'loading'
    : cardError
      ? 'unavailable'
      : cardPacket
        ? 'loaded'
        : 'pending';
  const cardStatusTone = cardError ? 'partial' : cardPacket ? 'green' : 'partial';
  const inspectorHref = previewRefs[0]
    ? withReturnToQuery(`/inspector?file=${encodeURIComponent(sourceRefPath(previewRefs[0]))}`, currentRoute)
    : '/inspector';
  return (
    <div
      className="w-full rounded-[4px] border bg-black/72 p-3 shadow-[0_0_42px_rgba(199,176,106,0.13)]"
      style={{ borderColor: accent + '88' }}
    >
      <div
        className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em]"
        style={{ color: accent }}
      >
        <Icon size={14} />
        <span className="truncate">{kindLabel} · {axisLabel}</span>
      </div>
      <h3 className="mt-2 flex items-center gap-2 text-sm font-semibold text-white">
        <span className="truncate">{label}</span>
        <StatusPill status={rawStatus} dim />
      </h3>
      {id && id !== label && (
        <div className="mt-0.5 font-mono text-[10px] text-white/35">{id}</div>
      )}
      {claim && (
        <p className="mt-1 line-clamp-3 text-[11px] leading-4 text-white/68">{claim}</p>
      )}
      <div className="mt-2 rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
        <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">parent cluster</div>
        {parentCluster ? (
          <div className="mt-0.5 space-y-0.5">
            <div className="font-mono text-[11px] text-white/72">{parentCluster.label}</div>
            {parentCluster.clusterId && (
              <div className="font-mono text-[10px] text-zenith-muted">
                membership rule · {parentCluster.memberKind}.type == {parentCluster.clusterId}
              </div>
            )}
            <div className="font-mono text-[10px] text-zenith-muted">
              membership source · {parentCluster.membershipSource}
            </div>
          </div>
        ) : (
          <div className="mt-0.5 font-mono text-[11px] text-zenith-soft">unknown in current packet</div>
        )}
      </div>
      <div className="my-3 h-px bg-gradient-to-r from-transparent via-[#c7b06a]/45 to-transparent" />
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">source provenance</div>
          <div className="mt-1 grid gap-0.5 font-mono text-[11px] text-white/72">
            <div>direct: {ownRefs.length > 0 ? `${ownRefs.length}` : 'unavailable'}</div>
            <div>card: {cardRefs.length > 0 ? `${cardRefs.length}` : 'unavailable'}</div>
            <div>inherited packet refs: {packetSourceRefCount}</div>
          </div>
        </div>
        <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">card packet</div>
          <div className="mt-0.5 flex items-center gap-1.5">
            <StatusPill status={cardStatusTone} label={cardStatusLabel} dim />
          </div>
          <div className="mt-1 font-mono text-[10px] text-zenith-muted">species · leaf row</div>
        </div>
      </div>
      {previewRefs.length > 0 && (
        <div className="mt-2 space-y-1">
          {previewRefs.map((ref) => (
            <a
              key={ref}
              href={withReturnToQuery(`/inspector?file=${encodeURIComponent(sourceRefPath(ref))}`, currentRoute)}
              className="flex items-center gap-1.5 rounded border border-zenith-edge bg-white/[0.025] px-2 py-1 font-mono text-[10px] text-zenith-soft hover:border-cyan-300/30 hover:text-cyan-100"
            >
              <ExternalLink size={11} className="shrink-0 text-white/35" />
              <span className="min-w-0 flex-1 truncate">{ref}</span>
            </a>
          ))}
        </div>
      )}
      {(drilldownCommand || cardCommand || evidenceCommand) && (
        <div className="mt-2 flex flex-wrap gap-1 font-mono text-[10px]">
          {drilldownCommand && (
            <span className="rounded border border-cyan-300/20 bg-cyan-300/10 px-2 py-0.5 text-cyan-100/80">drilldown command</span>
          )}
          {cardCommand && (
            <span className="rounded border border-cyan-300/20 bg-cyan-300/10 px-2 py-0.5 text-cyan-100/80">card command</span>
          )}
          {evidenceCommand && (
            <span className="rounded border border-cyan-300/20 bg-cyan-300/10 px-2 py-0.5 text-cyan-100/80">evidence command</span>
          )}
        </div>
      )}
      <div className="mt-2 flex flex-wrap gap-1.5">
        <a
          href={inspectorHref}
          className="inline-flex items-center gap-1.5 rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-white/62 hover:border-[#c7b06a]/40 hover:text-[#f4e6a2]"
        >
          <Eye size={11} /> Inspect Source
        </a>
        <a
          href={inspectorHref}
          className="inline-flex items-center gap-1.5 rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-white/62 hover:border-[#c7b06a]/40 hover:text-[#f4e6a2]"
        >
          <Eye size={11} /> View Evidence
        </a>
        <a
          href="/station/ops"
          className="inline-flex items-center gap-1.5 rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-white/62 hover:border-[#c7b06a]/40 hover:text-[#f4e6a2]"
        >
          <Eye size={11} /> Open Apply Lane
        </a>
        <a
          href="/station/ledger"
          className="inline-flex items-center gap-1.5 rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-white/62 hover:border-[#c7b06a]/40 hover:text-[#f4e6a2]"
        >
          <Eye size={11} /> Open WorkItem
        </a>
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        <span className="rounded border border-zenith-edge bg-white/[0.035] px-2 py-0.5 font-mono text-[10px] text-zenith-soft">
          authority: projection · source refs remain authority
        </span>
      </div>
    </div>
  );
}

interface SubstrateBandNodeData {
  band: RootSubstrateBand;
  label: string;
  short: string;
  description: string;
  accent: string;
  containerCount: number;
}

function SubstrateBandNode({ data }: NodeProps<SubstrateBandNodeData>) {
  return (
    <div
      data-zenith-root-substrate-atlas-band={data.band}
      data-zenith-root-substrate-atlas-band-count={data.containerCount}
      className="h-full w-full rounded-[var(--zenith-radius-2xs)] border bg-black/30"
      style={{ borderColor: `${data.accent}33` }}
    >
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <Handle type="source" position={Position.Right} className="!opacity-0" />
      <div className="flex items-start justify-between gap-3 border-b border-white/8 px-3 py-1.5">
        <div className="min-w-0">
          <div
            className="truncate font-mono text-[10px] uppercase tracking-[0.18em]"
            style={{ color: data.accent }}
          >
            {data.label}
          </div>
          <p className="mt-0.5 line-clamp-2 text-[10px] leading-4 text-zenith-muted">
            {data.description}
          </p>
        </div>
        <span className="shrink-0 rounded border border-zenith-edge bg-white/[0.04] px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-soft">
          {data.containerCount} containers
        </span>
      </div>
    </div>
  );
}

interface SubstrateContainerNodeData {
  container: RootSubstrateContainer;
  selected: boolean;
  connected: boolean;
  onSelect: (kind: string) => void;
  onHoverChange: (kind: string | null) => void;
}

function SubstrateContainerNode({ data }: NodeProps<SubstrateContainerNodeData>) {
  const { container, selected, connected, onSelect, onHoverChange } = data;
  const Icon = container.icon;
  const bandAccent = SUBSTRATE_BAND_META[container.band].accent;
  const countLabel =
    container.rowCount === null
      ? 'count unknown'
      : `${container.rowCount} rows`;
  const normalizedStatus = normalizeStatus(container.status);
  const renderStatus =
    normalizedStatus !== 'green' &&
    normalizedStatus !== 'supported' &&
    normalizedStatus !== 'option_surface_supported';
  return (
    <button
      type="button"
      onClick={() => onSelect(container.kind)}
      onMouseEnter={() => onHoverChange(container.kind)}
      onMouseLeave={() => onHoverChange(null)}
      onFocus={() => onHoverChange(container.kind)}
      onBlur={() => onHoverChange(null)}
      data-zenith-root-substrate-atlas-container={container.kind}
      data-zenith-root-substrate-atlas-container-band={container.band}
      data-zenith-root-substrate-atlas-container-selected={selected ? 'true' : 'false'}
      data-zenith-root-substrate-atlas-container-connected={connected ? 'true' : 'false'}
      data-zenith-root-substrate-atlas-container-status={container.status}
      data-zenith-root-substrate-atlas-container-physical="opaque"
      data-zenith-root-status-rendered={renderStatus ? 'exception' : (selected ? 'selected' : 'global')}
      data-zenith-root-status-elided={renderStatus ? '' : 'supported'}
      data-zenith-root-graph-node={container.kind}
      data-zenith-root-graph-node-kind={container.kind}
      data-zenith-root-graph-node-role="substrate_container"
      data-zenith-root-graph-node-parent={`band:${container.band}`}
      data-zenith-root-graph-node-adapter="substrate"
      data-zenith-root-graph-node-expanded="false"
      data-zenith-root-graph-node-selected={selected ? 'true' : 'false'}
      data-zenith-root-substrate-object-primary-label={container.label}
      data-zenith-root-substrate-object-secondary-id={container.kind}
      className={clsx(
        'group w-[176px] rounded-[var(--zenith-radius-2xs)] border bg-[#05070b] px-[var(--zenith-space-2-5)] py-2 text-left font-mono transition-colors',
        selected
          ? 'border-cyan-200/85 ring-2 ring-cyan-300/60 shadow-[0_0_28px_rgba(103,232,249,0.22)]'
          : connected
            ? 'border-cyan-300/55 shadow-[0_0_14px_rgba(103,232,249,0.14)]'
            : 'border-white/14 hover:border-cyan-300/55 hover:ring-1 hover:ring-cyan-300/35 focus:outline-none focus:ring-1 focus:ring-cyan-200/55',
      )}
    >
      <Handle type="target" position={Position.Left} className="!h-1 !w-1 !border-0 !bg-transparent !opacity-0" />
      <Handle type="source" position={Position.Right} className="!h-1 !w-1 !border-0 !bg-transparent !opacity-0" />
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <Icon size={12} style={{ color: bandAccent }} aria-hidden="true" />
          <span
            className="truncate text-[9px] uppercase tracking-[0.14em]"
            style={{ color: bandAccent }}
          >
            {SUBSTRATE_BAND_META[container.band].short}
          </span>
        </div>
        {renderStatus && <StatusPill status={graphStatusLabel(container.status)} dim />}
      </div>
      <div className="mt-1 truncate text-[12px] font-semibold text-white">{container.label}</div>
      <div className="mt-0.5 truncate text-[10px] text-zenith-soft">{container.axisLabel}</div>
      {container.rowCount !== null && (
        <div className="mt-0.5 truncate text-[10px] text-zenith-soft">{countLabel}</div>
      )}
    </button>
  );
}

const SUBSTRATE_NODE_TYPES = {
  substrateBand: SubstrateBandNode,
  substrateContainer: SubstrateContainerNode,
};

interface SubstrateAtlasLayoutResult {
  nodes: RfNode[];
  edges: RfEdge[];
}

interface BuildSubstrateAtlasFlowArgs {
  model: RootSubstrateAtlasModel;
  selectedKind: string | null;
  hoveredKind: string | null;
  onSelectKind: (kind: string) => void;
  onHoverChange: (kind: string | null) => void;
}

function buildSubstrateAtlasFlow({
  model,
  selectedKind,
  hoveredKind,
  onSelectKind,
  onHoverChange,
}: BuildSubstrateAtlasFlowArgs): SubstrateAtlasLayoutResult {
  const nodes: RfNode[] = [];
  const edges: RfEdge[] = [];

  const BAND_WIDTH = 1240;
  const BAND_INNER_LEFT = 24;
  const BAND_INNER_TOP = 64;
  const CONTAINER_WIDTH = 176;
  const CONTAINER_HEIGHT = 96;
  const CONTAINER_GAP_X = 24;
  const CONTAINER_GAP_Y = 18;
  const BAND_HEADER_HEIGHT = 64;
  const CONTAINERS_PER_ROW = 6;

  const containersByBand = new Map<RootSubstrateBand, RootSubstrateContainer[]>();
  for (const band of SUBSTRATE_BAND_ORDER) containersByBand.set(band, []);
  for (const container of model.containers) {
    containersByBand.get(container.band)?.push(container);
  }
  for (const band of SUBSTRATE_BAND_ORDER) {
    const list = containersByBand.get(band) ?? [];
    list.sort((left, right) => left.label.localeCompare(right.label));
  }

  const focusKind = selectedKind ?? hoveredKind ?? null;
  const focusContainerId = focusKind
    ? relationNodeId('substrate-container', focusKind)
    : null;

  const connectedContainerIds = new Set<string>();
  if (focusContainerId) {
    connectedContainerIds.add(focusContainerId);
    for (const edge of model.edges) {
      if (edge.source === focusContainerId) connectedContainerIds.add(edge.target);
      if (edge.target === focusContainerId) connectedContainerIds.add(edge.source);
    }
  }

  let cursorY = 0;
  for (const band of SUBSTRATE_BAND_ORDER) {
    const list = containersByBand.get(band) ?? [];
    if (list.length === 0) continue;
    const rowCount = Math.max(1, Math.ceil(list.length / CONTAINERS_PER_ROW));
    const bandHeight =
      BAND_HEADER_HEIGHT + rowCount * (CONTAINER_HEIGHT + CONTAINER_GAP_Y) + 12;
    const bandId = `substrate-band:${band}`;
    const bandMeta = SUBSTRATE_BAND_META[band];
    nodes.push({
      id: bandId,
      type: 'substrateBand',
      position: { x: 0, y: cursorY },
      style: { width: BAND_WIDTH, height: bandHeight, zIndex: 0 },
      draggable: false,
      selectable: false,
      data: {
        band,
        label: bandMeta.label,
        short: bandMeta.short,
        description: bandMeta.description,
        accent: bandMeta.accent,
        containerCount: list.length,
      } satisfies SubstrateBandNodeData,
    });

    list.forEach((container, index) => {
      const row = Math.floor(index / CONTAINERS_PER_ROW);
      const col = index % CONTAINERS_PER_ROW;
      const x = BAND_INNER_LEFT + col * (CONTAINER_WIDTH + CONTAINER_GAP_X);
      const y = BAND_INNER_TOP + row * (CONTAINER_HEIGHT + CONTAINER_GAP_Y);
      nodes.push({
        id: container.id,
        type: 'substrateContainer',
        parentId: bandId,
        extent: 'parent',
        position: { x, y },
        style: { width: CONTAINER_WIDTH },
        draggable: false,
        data: {
          container,
          selected:
            selectedKind === container.kind ||
            (selectedKind === null && hoveredKind === container.kind),
          connected: focusContainerId
            ? connectedContainerIds.has(container.id) && container.id !== focusContainerId
            : false,
          onSelect: onSelectKind,
          onHoverChange,
        } satisfies SubstrateContainerNodeData,
      });
    });

    cursorY += bandHeight + 18;
  }

  for (const edge of model.edges) {
    const familyMeta = SUBSTRATE_RELATION_META[edge.family];
    const isFocus =
      focusContainerId !== null &&
      (edge.source === focusContainerId || edge.target === focusContainerId);
    const isShareAxis = edge.family === 'shares_axis';
    if (!isFocus && isShareAxis) continue;
    const baseOpacity = isFocus ? Math.min(1, familyMeta.opacity + 0.2) : familyMeta.opacity * 0.55;
    edges.push({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'default',
      animated: false,
      // Suppress v11 EdgeWrapper's default "Edge from X to Y" aria-label.
      // Per cap_quick_extend_wayfinding_map_a11y_contract_acro_863da57484ec.
      ariaLabel: '',
      data: { family: edge.family, authority: edge.authority },
      style: {
        stroke: familyMeta.tone,
        strokeWidth: isFocus ? 1.6 : 0.9,
        strokeDasharray: familyMeta.strokeDash,
        opacity: baseOpacity,
      },
    });
  }

  return { nodes, edges };
}

interface RootSubstrateAtlasGraphProps {
  model: RootSubstrateAtlasModel;
  selectedKind: string | null;
  hoveredKind: string | null;
  onSelectKind: (kind: string) => void;
  onHoverChange: (kind: string | null) => void;
}

function RootSubstrateAtlasGraphInner({
  model,
  selectedKind,
  hoveredKind,
  onSelectKind,
  onHoverChange,
}: RootSubstrateAtlasGraphProps) {
  const handleSelect = useCallback(
    (kind: string) => onSelectKind(kind),
    [onSelectKind],
  );
  const handleHoverChange = useCallback(
    (kind: string | null) => onHoverChange(kind),
    [onHoverChange],
  );
  const layout = useMemo(
    () =>
      buildSubstrateAtlasFlow({
        model,
        selectedKind,
        hoveredKind,
        onSelectKind: handleSelect,
        onHoverChange: handleHoverChange,
      }),
    [model, selectedKind, hoveredKind, handleSelect, handleHoverChange],
  );

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={layout.nodes}
        edges={layout.edges}
        nodeTypes={SUBSTRATE_NODE_TYPES}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        // Wayfinding-map a11y contract. nodesFocusable / edgesFocusable
        // off so the wrapper doesn't tab-stop on every node + edge;
        // disableKeyboardA11y removes per-element keyboard handlers that
        // aren't wired here. ariaLabel:'' on each edge object suppresses
        // v11's default "Edge from X to Y" announcement. Per
        // cap_quick_extend_wayfinding_map_a11y_contract_acro_863da57484ec.
        nodesFocusable={false}
        edgesFocusable={false}
        disableKeyboardA11y
        minZoom={0.35}
        maxZoom={1.4}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={28}
          size={1}
          color="rgba(226,232,240,0.10)"
        />
      </ReactFlow>
    </div>
  );
}

function RootSubstrateAtlasGraph(props: RootSubstrateAtlasGraphProps) {
  return (
    <ReactFlowProvider>
      <RootSubstrateAtlasGraphInner {...props} />
    </ReactFlowProvider>
  );
}

interface RootSubstrateAtlasLegendProps {
  legend: RootSubstrateAtlasLegend;
  focusFamilies: ReadonlyArray<RootSubstrateRelation>;
}

function RootSubstrateAtlasLegendPanel({ legend, focusFamilies }: RootSubstrateAtlasLegendProps) {
  const focusSet = new Set<RootSubstrateRelation>(focusFamilies);
  return (
    <div
      data-zenith-root-substrate-atlas-legend="ready"
      className="grid gap-3 border-t border-zenith-edge bg-black/40 px-3 py-2 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_minmax(0,1fr)]"
    >
      <div>
        <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-white/35">bands</div>
        <ul className="mt-1 space-y-0.5">
          {legend.bands.map((band) => (
            <li key={band.key} className="flex items-start gap-2 text-[10px] leading-4 text-zenith-soft">
              <span
                className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: SUBSTRATE_BAND_META[band.key as RootSubstrateBand].accent }}
                aria-hidden="true"
              />
              <span className="min-w-0">
                <span className="font-mono text-white/85">{band.label}</span>
                <span className="ml-1 text-zenith-muted">{band.meaning}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-white/35">edges</div>
        <ul className="mt-1 space-y-0.5">
          {legend.edgeFamilies.length === 0 ? (
            <li className="text-[10px] leading-4 text-zenith-muted">no relations available in current packet</li>
          ) : (
            legend.edgeFamilies.map((family) => {
              const meta = SUBSTRATE_RELATION_META[family.key as RootSubstrateRelation];
              const focused = focusSet.has(family.key as RootSubstrateRelation);
              return (
                <li
                  key={family.key}
                  data-zenith-root-substrate-atlas-legend-edge={family.key}
                  data-zenith-root-substrate-atlas-legend-edge-focused={focused ? 'true' : 'false'}
                  className="flex items-center gap-2 text-[10px] leading-4 text-zenith-soft"
                >
                  <span
                    className="inline-block h-px w-6 shrink-0"
                    style={{
                      borderBottom: `1.5px ${meta.strokeDash ? 'dashed' : 'solid'} ${meta.tone}`,
                      opacity: focused ? 1 : 0.7,
                    }}
                    aria-hidden="true"
                  />
                  <span className="min-w-0">
                    <span className="font-mono text-white/85">{family.label}</span>
                    <span className="ml-1 text-zenith-muted">{family.meaning}</span>
                  </span>
                </li>
              );
            })
          )}
        </ul>
      </div>
      <div>
        <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-white/35">encoding</div>
        <ul className="mt-1 space-y-0.5">
          {legend.encoding.map((encoding) => (
            <li key={encoding.key} className="flex items-baseline gap-2 text-[10px] leading-4 text-zenith-soft">
              <span className="font-mono text-white/85">{encoding.label}</span>
              <span className="text-zenith-muted">{encoding.meaning}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

type AxiomBand = 'tiny' | 'flag' | 'card' | 'context' | 'deep';

const AXIOM_BAND_ORDER: AxiomBand[] = ['tiny', 'flag', 'card', 'context', 'deep'];

interface FamilyAxiomDeliverable {
  deliverableId: string;
  status: string;
  desiredCapability: string;
  targetSurface: string;
  proofHint: string;
}

interface FamilyAxiomEvidenceRef {
  ref: string;
  role: string;
  gloss: string;
}

interface FamilyAxiomCandidate {
  id: string;
  slug: string;
  title: string;
  formalClause: string;
  denseClause: string;
  status: string;
  authorityPosture: string;
  bands: Partial<Record<AxiomBand, string>>;
  relatedPrinciples: string[];
  governedPlanes: string[];
  deliverables: FamilyAxiomDeliverable[];
  evidenceRefs: FamilyAxiomEvidenceRef[];
}

interface FamilyPrincipleNode {
  id: string;
  title: string;
  statement: string;
  scope: string;
  status: string;
}

const FAMILY_AXIOM_FALLBACK_PATH =
  'obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json';

function deriveFamilyAxiomPath(principlesPath: string | null | undefined): string {
  if (principlesPath && principlesPath.endsWith('raw_seed_principles.json')) {
    return principlesPath.replace(/raw_seed_principles\.json$/, 'system_axiom_candidates.json');
  }
  return FAMILY_AXIOM_FALLBACK_PATH;
}

function asRecordSafe(value: unknown): UnknownRow {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as UnknownRow) : {};
}

function asRecordArraySafe(value: unknown): UnknownRow[] {
  return Array.isArray(value)
    ? value.filter((entry): entry is UnknownRow => entry != null && typeof entry === 'object' && !Array.isArray(entry))
    : [];
}

function parseFamilyAxiomCandidates(content: string): FamilyAxiomCandidate[] {
  let root: UnknownRow;
  try {
    root = asRecordSafe(JSON.parse(content));
  } catch {
    return [];
  }
  return asRecordArraySafe(root.axiom_candidates)
    .map((row) => {
      const bands = asRecordSafe(row.compression_expansion_bands);
      return {
        id: asString(row.id),
        slug: asString(row.slug),
        title: asString(row.title),
        formalClause: asString(row.formal_clause),
        denseClause: asString(row.dense_clause),
        status: asString(row.status),
        authorityPosture: asString(row.authority_posture),
        bands: {
          tiny: asString(bands.tiny),
          flag: asString(bands.flag),
          card: asString(bands.card),
          context: asString(bands.context),
          deep: asString(bands.deep),
        },
        relatedPrinciples: asStringArray(row.related_principles),
        governedPlanes: asStringArray(row.governed_planes),
        deliverables: asRecordArraySafe(row.teleological_deliverables).map((deliverable) => ({
          deliverableId: asString(deliverable.deliverable_id),
          status: asString(deliverable.status),
          desiredCapability: asString(deliverable.desired_capability),
          targetSurface: asString(deliverable.target_surface),
          proofHint: asString(deliverable.proof_hint),
        })),
        evidenceRefs: asRecordArraySafe(row.evidence_refs).map((ref) => ({
          ref: asString(ref.ref),
          role: asString(ref.role),
          gloss: asString(ref.gloss),
        })),
      } satisfies FamilyAxiomCandidate;
    })
    .filter((axiom) => axiom.id.length > 0 && axiom.title.length > 0);
}

type LocalObjectLensLane = 'center' | 'inbound' | 'outbound' | 'context' | '';

interface SubstrateFamilyAxiomNodeData {
  axiom: FamilyAxiomCandidate;
  selected: boolean;
  connected: boolean;
  visiblePrincipleCount: number;
  onSelect: (id: string) => void;
  lane?: LocalObjectLensLane;
}

function SubstrateFamilyAxiomNode({ data }: NodeProps<SubstrateFamilyAxiomNodeData>) {
  const { axiom, selected, connected, visiblePrincipleCount, onSelect, lane } = data;
  const view = buildAxiomCandidateViewModel(axiom);
  return (
    <button
      type="button"
      onClick={() => onSelect(axiom.id)}
      title={`${view.primaryLabel} (${view.secondaryId})`}
      aria-label={`${view.primaryLabel} — ${view.secondaryId}`}
      data-zenith-root-substrate-family-node={axiom.id}
      data-zenith-root-substrate-family-node-kind="axiom_candidate"
      data-zenith-root-substrate-family-node-selected={selected ? 'true' : 'false'}
      data-zenith-root-substrate-family-node-connected={connected ? 'true' : 'false'}
      data-zenith-root-substrate-family-node-physical="opaque"
      data-zenith-root-substrate-object-primary-label={view.primaryLabel}
      data-zenith-root-substrate-object-secondary-id={view.secondaryId}
      data-zenith-root-doctrine-lane="axioms"
      data-zenith-root-doctrine-node={axiom.id}
      data-zenith-root-doctrine-node-kind="axiom_candidate"
      data-zenith-root-doctrine-node-selected={selected ? 'true' : 'false'}
      data-zenith-root-doctrine-node-connected={connected ? 'true' : 'false'}
      data-zenith-root-local-lane={lane ?? ''}
      className={clsx(
        'group w-[260px] rounded-[var(--zenith-radius-2xs)] border bg-[#0e0a05] px-3 py-2 text-left font-mono transition-colors',
        selected
          ? 'border-amber-300/85 ring-2 ring-amber-300/55 shadow-[0_0_28px_rgba(199,176,106,0.22)]'
          : connected
            ? 'border-amber-300/65 shadow-[0_0_14px_rgba(199,176,106,0.16)]'
            : 'border-amber-300/30 hover:border-amber-200/70 hover:ring-1 hover:ring-amber-300/40 focus:outline-none focus:ring-1 focus:ring-amber-300/55',
      )}
    >
      <Handle type="source" position={Position.Right} className="!h-1 !w-1 !border-0 !bg-transparent !opacity-0" />
      <div className="flex items-center justify-between gap-2">
        <span className="text-[9px] uppercase tracking-[0.16em] text-amber-100/80">candidate axiom</span>
        <span className="rounded-full border border-amber-300/25 bg-amber-300/10 px-1.5 py-0.5 text-[9px] uppercase tracking-[0.14em] text-amber-50/75">
          {visiblePrincipleCount} pri
        </span>
      </div>
      <div className="mt-1 line-clamp-2 whitespace-normal text-[12px] font-semibold leading-[1.2] text-white">
        {view.primaryLabel}
      </div>
      <p className="mt-1 line-clamp-3 text-[10px] leading-4 text-zenith-soft">{view.oneLine}</p>
    </button>
  );
}

interface SubstrateFamilyPrincipleNodeData {
  principle: FamilyPrincipleNode;
  selected: boolean;
  connected: boolean;
  onSelect: (id: string) => void;
  lane?: LocalObjectLensLane;
}

function familyPrincipleMicroLabel(principle: FamilyPrincipleNode): string {
  // FamilyPrincipleNode is a stripped subset of WorldModelFamilyPrinciple; principleMicroLabel
  // only reads title/slug/statement/id and tolerates missing fields, so the cast is safe.
  return principleMicroLabel(principle as unknown as WorldModelFamilyPrinciple);
}

function SubstrateFamilyPrincipleNode({ data }: NodeProps<SubstrateFamilyPrincipleNodeData>) {
  const { principle, selected, connected, onSelect, lane } = data;
  const microLabel = familyPrincipleMicroLabel(principle);
  return (
    <button
      type="button"
      onClick={() => onSelect(principle.id)}
      data-zenith-root-substrate-family-node={principle.id}
      data-zenith-root-substrate-family-node-kind="principle"
      data-zenith-root-substrate-family-node-selected={selected ? 'true' : 'false'}
      data-zenith-root-substrate-family-node-connected={connected ? 'true' : 'false'}
      data-zenith-root-substrate-family-node-physical="opaque"
      data-zenith-root-substrate-object-primary-label={microLabel}
      data-zenith-root-substrate-object-secondary-id={principle.id}
      data-zenith-root-doctrine-lane="principles"
      data-zenith-root-doctrine-node={principle.id}
      data-zenith-root-doctrine-node-kind="principle"
      data-zenith-root-doctrine-node-selected={selected ? 'true' : 'false'}
      data-zenith-root-doctrine-node-connected={connected ? 'true' : 'false'}
      data-zenith-root-principle-id={principle.id}
      data-zenith-root-principle-label={microLabel}
      data-zenith-root-local-lane={lane ?? ''}
      title={`${microLabel} (${principle.id})`}
      aria-label={`${microLabel} — ${principle.id}`}
      className={clsx(
        'flex h-[36px] w-[200px] items-start rounded-[4px] border bg-[#05070b] px-2 py-1 text-left font-mono transition-colors',
        selected
          ? 'border-cyan-200/85 ring-2 ring-cyan-300/55 shadow-[0_0_18px_rgba(103,232,249,0.22)]'
          : connected
            ? 'border-cyan-300/65 shadow-[0_0_10px_rgba(103,232,249,0.14)]'
            : 'border-white/12 hover:border-cyan-300/55 hover:ring-1 hover:ring-cyan-300/35 focus:outline-none focus:ring-1 focus:ring-cyan-200/45',
      )}
    >
      <span className="min-w-0 flex-1 whitespace-normal text-[10.5px] font-semibold leading-4 text-cyan-50/90 line-clamp-2">
        {microLabel || principle.title || principle.statement}
      </span>
      <span className="sr-only" data-zenith-root-principle-secondary-id={principle.id}>
        {principle.id}
      </span>
    </button>
  );
}

const SUBSTRATE_FAMILY_NODE_TYPES = {
  substrateBand: SubstrateBandNode,
  substrateFamilyAxiom: SubstrateFamilyAxiomNode,
  substrateFamilyPrinciple: SubstrateFamilyPrincipleNode,
};

interface RootSubstrateFamilyZoomGraphProps {
  focusKind: string;
  axioms: FamilyAxiomCandidate[];
  principles: FamilyPrincipleNode[];
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  loading: boolean;
  errorLine: string | null;
}

function buildFamilyZoomFlow({
  axioms,
  principles,
  selectedNodeId,
  onSelectNode,
}: {
  axioms: FamilyAxiomCandidate[];
  principles: FamilyPrincipleNode[];
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
}): { nodes: RfNode[]; edges: RfEdge[] } {
  const nodes: RfNode[] = [];
  const edges: RfEdge[] = [];

  // v1.15 readability: axiom title wraps to 2 lines, principle chips are taller (36) and
  // wider (200) so the readable micro-label can wrap. Layout constants follow.
  const PRINCIPLES_PER_COLUMN = 14;
  const AXIOM_X = 32;
  const AXIOM_Y = 56;
  const AXIOM_HEIGHT = 110;
  const AXIOM_GAP = 18;
  const PRINCIPLE_Y = 56;
  const PRINCIPLE_WIDTH = 200;
  const PRINCIPLE_HEIGHT = 36;
  const PRINCIPLE_X_GAP = 16;
  const PRINCIPLE_Y_GAP = 10;

  const axiomBandHeight =
    Math.max(160, axioms.length * (AXIOM_HEIGHT + AXIOM_GAP) + 80);
  const principleColumns = Math.max(
    1,
    Math.ceil(principles.length / PRINCIPLES_PER_COLUMN),
  );
  const principleBandWidth =
    24 + principleColumns * (PRINCIPLE_WIDTH + PRINCIPLE_X_GAP) + 16;
  const principleBandHeight = Math.max(
    160,
    Math.min(principles.length, PRINCIPLES_PER_COLUMN) * (PRINCIPLE_HEIGHT + PRINCIPLE_Y_GAP) + 80,
  );

  const totalHeight = Math.max(axiomBandHeight, principleBandHeight);
  const principleBandX = AXIOM_X + 260 + 64;

  nodes.push({
    id: 'substrate-family-band:axioms',
    type: 'substrateBand',
    position: { x: 0, y: 0 },
    style: { width: principleBandX + principleBandWidth, height: totalHeight + 32, zIndex: 0 },
    draggable: false,
    selectable: false,
    data: {
      band: 'durable_substrate',
      label: 'Axioms compress · principles do the work',
      short: 'family',
      description: `${axioms.length} candidate axioms, ${principles.length} loaded principles. Click any node to highlight related neighbors.`,
      accent: '#c7b06a',
      containerCount: axioms.length + principles.length,
    } satisfies SubstrateBandNodeData,
  });

  const axiomConnectedPrincipleIds = new Set<string>();
  const principleConnectedAxiomIds = new Set<string>();
  if (selectedNodeId) {
    const selectedAxiom = axioms.find((axiom) => axiom.id === selectedNodeId);
    if (selectedAxiom) {
      for (const id of selectedAxiom.relatedPrinciples) axiomConnectedPrincipleIds.add(id);
    } else if (selectedNodeId.startsWith('pri_')) {
      for (const axiom of axioms) {
        if (axiom.relatedPrinciples.includes(selectedNodeId)) {
          principleConnectedAxiomIds.add(axiom.id);
        }
      }
    }
  }

  axioms.forEach((axiom, index) => {
    const visibleCount = axiom.relatedPrinciples.filter((id) =>
      principles.some((principle) => principle.id === id),
    ).length;
    const isSelected = selectedNodeId === axiom.id;
    const isConnected = principleConnectedAxiomIds.has(axiom.id);
    // v1.15 Local Object Lens: axiom is `center` when selected, `inbound` when a selected
    // principle points back via relatedPrinciples (axiom → principle).
    const lane: LocalObjectLensLane = isSelected ? 'center' : isConnected ? 'inbound' : '';
    nodes.push({
      id: `substrate-family-axiom:${axiom.id}`,
      type: 'substrateFamilyAxiom',
      parentId: 'substrate-family-band:axioms',
      extent: 'parent',
      position: { x: AXIOM_X, y: AXIOM_Y + index * (AXIOM_HEIGHT + AXIOM_GAP) },
      style: { width: 260 },
      draggable: false,
      data: {
        axiom,
        selected: isSelected,
        connected: isConnected,
        visiblePrincipleCount: visibleCount,
        onSelect: onSelectNode,
        lane,
      } satisfies SubstrateFamilyAxiomNodeData,
    });
  });

  principles.forEach((principle, index) => {
    const col = Math.floor(index / PRINCIPLES_PER_COLUMN);
    const row = index % PRINCIPLES_PER_COLUMN;
    const isSelected = selectedNodeId === principle.id;
    const isConnected = axiomConnectedPrincipleIds.has(principle.id);
    // v1.15: principle is `center` when selected, `outbound` when a selected axiom points to it.
    const lane: LocalObjectLensLane = isSelected ? 'center' : isConnected ? 'outbound' : '';
    nodes.push({
      id: `substrate-family-principle:${principle.id}`,
      type: 'substrateFamilyPrinciple',
      parentId: 'substrate-family-band:axioms',
      extent: 'parent',
      position: {
        x: principleBandX + col * (PRINCIPLE_WIDTH + PRINCIPLE_X_GAP),
        y: PRINCIPLE_Y + row * (PRINCIPLE_HEIGHT + PRINCIPLE_Y_GAP),
      },
      style: { width: PRINCIPLE_WIDTH },
      draggable: false,
      data: {
        principle,
        selected: isSelected,
        connected: isConnected,
        onSelect: onSelectNode,
        lane,
      } satisfies SubstrateFamilyPrincipleNodeData,
    });
  });

  if (selectedNodeId) {
    const selectedAxiom = axioms.find((axiom) => axiom.id === selectedNodeId);
    if (selectedAxiom) {
      for (const principleId of selectedAxiom.relatedPrinciples) {
        if (!principles.some((p) => p.id === principleId)) continue;
        edges.push({
          id: `substrate-family-edge:${selectedAxiom.id}->${principleId}`,
          source: `substrate-family-axiom:${selectedAxiom.id}`,
          target: `substrate-family-principle:${principleId}`,
          animated: false,
          ariaLabel: '',
          style: { stroke: '#c7b06a', strokeWidth: 1.6, opacity: 0.85 },
          data: { family: 'axiom_compresses_principle' },
        });
      }
    } else if (selectedNodeId.startsWith('pri_')) {
      for (const axiom of axioms) {
        if (!axiom.relatedPrinciples.includes(selectedNodeId)) continue;
        edges.push({
          id: `substrate-family-edge:${axiom.id}->${selectedNodeId}`,
          source: `substrate-family-axiom:${axiom.id}`,
          target: `substrate-family-principle:${selectedNodeId}`,
          animated: false,
          ariaLabel: '',
          style: { stroke: '#67e8f9', strokeWidth: 1.6, opacity: 0.85 },
          data: { family: 'principle_axiom_inbound' },
        });
      }
    }
  }

  return { nodes, edges };
}

function RootSubstrateFamilyZoomGraphInner({
  axioms,
  principles,
  selectedNodeId,
  onSelectNode,
  loading,
  errorLine,
}: Omit<RootSubstrateFamilyZoomGraphProps, 'focusKind'>) {
  const handleSelect = useCallback(
    (id: string) => onSelectNode(id === selectedNodeId ? null : id),
    [onSelectNode, selectedNodeId],
  );
  const layout = useMemo(
    () => buildFamilyZoomFlow({ axioms, principles, selectedNodeId, onSelectNode: handleSelect }),
    [axioms, principles, selectedNodeId, handleSelect],
  );
  // v1.15 Local Object Lens: when a family node is selected, the wrapper advertises the
  // selected object's id + kind so receipts can prove that inbound/outbound/center lanes
  // are routed to the right node without scraping into the React Flow internals.
  const selectedKind: SubstrateObjectKind | null = selectedNodeId
    ? selectedNodeId.startsWith('axiom_candidate_')
      ? 'axiom_candidate'
      : selectedNodeId.startsWith('pri_')
        ? 'principle'
        : null
    : null;
  const lensReady = Boolean(selectedNodeId && selectedKind);
  return (
    <div
      className="relative h-full w-full"
      data-zenith-root-local-object-lens={lensReady ? 'ready' : 'idle'}
      data-zenith-root-local-object-id={selectedNodeId ?? ''}
      data-zenith-root-local-object-kind={selectedKind ?? ''}
      data-zenith-root-local-object-family="axiom_candidates"
    >
      {(loading || errorLine) && (
        <div className="pointer-events-none absolute right-3 top-3 z-10 flex max-w-[320px] items-center gap-2 rounded-[4px] border border-zenith-edge bg-black/60 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft">
          {loading ? 'loading axiom candidates' : errorLine}
        </div>
      )}
      <ReactFlow
        nodes={layout.nodes}
        edges={layout.edges}
        nodeTypes={SUBSTRATE_FAMILY_NODE_TYPES}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        // Inspection-workbench: node click is the primary affordance.
        // Suppress edge focus + default ariaLabel per the wayfinding-map
        // contract. See ariaLabel:'' on each rfEdge above.
        edgesFocusable={false}
        disableKeyboardA11y
        minZoom={0.4}
        maxZoom={1.4}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="rgba(226,232,240,0.10)" />
      </ReactFlow>
    </div>
  );
}

function RootSubstrateFamilyZoomGraph(props: RootSubstrateFamilyZoomGraphProps) {
  return (
    <ReactFlowProvider>
      <RootSubstrateFamilyZoomGraphInner {...props} />
    </ReactFlowProvider>
  );
}

interface RootSubstrateFamilySelectionPanelProps {
  focusKind: string;
  axioms: FamilyAxiomCandidate[];
  principles: FamilyPrincipleNode[];
  selectedNodeId: string | null;
  onClear: () => void;
  onOpenKindLens: () => void;
  loadingPrinciples: boolean;
  axiomLoadError: string | null;
}

function RootSubstrateFamilySelectionPanel({
  focusKind,
  axioms,
  principles,
  selectedNodeId,
  onClear,
  onOpenKindLens,
  loadingPrinciples,
  axiomLoadError,
}: RootSubstrateFamilySelectionPanelProps) {
  const selectedAxiom = selectedNodeId
    ? axioms.find((axiom) => axiom.id === selectedNodeId) ?? null
    : null;
  const selectedPrinciple = selectedNodeId && selectedNodeId.startsWith('pri_')
    ? principles.find((principle) => principle.id === selectedNodeId) ?? null
    : null;
  return (
    <aside
      className="flex h-full min-h-0 flex-col border-l border-zenith-edge bg-black/35 px-3 py-2"
      data-zenith-root-substrate-family-selection-panel="ready"
      data-zenith-root-substrate-family-selection={selectedNodeId ?? ''}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-zenith-muted">family zoom</div>
          <div className="mt-0.5 truncate text-[12px] font-semibold text-white">
            {focusKind.replace(/_/g, ' ')}
          </div>
        </div>
        <button
          type="button"
          onClick={onOpenKindLens}
          data-zenith-root-substrate-open-kind-lens={focusKind}
          className="rounded border border-white/12 bg-white/[0.04] px-2 py-1 font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-soft hover:border-cyan-300/35 hover:text-cyan-100"
        >
          Open kind lens
        </button>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1.5">
        <div className="rounded-[4px] border border-zenith-edge bg-white/[0.03] px-2 py-1">
          <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">axioms</div>
          <div className="font-mono text-[11px] text-white/72">{axioms.length}</div>
        </div>
        <div className="rounded-[4px] border border-zenith-edge bg-white/[0.03] px-2 py-1">
          <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">principles</div>
          <div className="font-mono text-[11px] text-white/72">
            {loadingPrinciples ? 'loading' : principles.length}
          </div>
        </div>
      </div>
      {axiomLoadError && (
        <div className="mt-2 rounded-[4px] border border-amber-300/25 bg-amber-300/10 px-2 py-1 text-[10px] leading-4 text-amber-100/80">
          axiom ledger unavailable: {axiomLoadError}
        </div>
      )}
      <div className="mt-3 flex-1 overflow-y-auto pr-1">
        {!selectedNodeId && (
          <div className="rounded-[4px] border border-zenith-edge bg-white/[0.03] px-2 py-2 text-[11px] leading-4 text-zenith-soft">
            <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">how to read this</div>
            <p className="mt-1">
              Candidate axioms compress the field. Principles do the work. Click any axiom to see its related
              principles; click a principle to see which axioms point to it. Open kind lens for the legacy
              focus-path workbench.
            </p>
          </div>
        )}
        {selectedAxiom && (
          <div className="space-y-2" data-zenith-root-substrate-family-selection-kind="axiom_candidate">
            <div className="rounded-[4px] border border-amber-300/35 bg-amber-300/[0.08] px-2 py-2">
              <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-amber-200/85">candidate axiom</div>
              <div className="mt-1 text-[13px] font-semibold text-white">{selectedAxiom.title}</div>
              <p className="mt-1 text-[11px] leading-5 text-white/72">
                {selectedAxiom.denseClause || selectedAxiom.formalClause}
              </p>
            </div>
            <div>
              <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">compression bands</div>
              <ul className="mt-1 grid gap-1.5">
                {AXIOM_BAND_ORDER.map((band) => (
                  <li
                    key={band}
                    className="grid grid-cols-[68px_minmax(0,1fr)] items-start gap-2 text-[10px] leading-4"
                    data-zenith-root-substrate-family-axiom-band={band}
                  >
                    <span
                      className={clsx(
                        'rounded border px-1.5 py-0.5 text-center font-mono text-[8px] uppercase tracking-[0.14em]',
                        selectedAxiom.bands[band]
                          ? 'border-amber-300/40 bg-amber-300/15 text-amber-50/90'
                          : 'border-zenith-edge bg-white/[0.03] text-white/35',
                      )}
                    >
                      {band}
                    </span>
                    <span className="text-zenith-soft">
                      {selectedAxiom.bands[band] || 'not populated in this projection'}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">related principles</div>
              <div className="mt-1 flex flex-wrap gap-1" data-zenith-root-substrate-related-principles="ready">
                {selectedAxiom.relatedPrinciples.length === 0 && (
                  <span className="text-[10px] text-zenith-muted">no related principles in the ledger</span>
                )}
                {selectedAxiom.relatedPrinciples.slice(0, 18).map((principleId) => {
                  // v1.15: resolve the principle id to its readable micro-label so this view
                  // does not leak PRI_### as primary chip text.
                  const principle = principles.find((p) => p.id === principleId) ?? null;
                  const view = principle
                    ? buildPrincipleViewModel(principle as unknown as WorldModelFamilyPrinciple)
                    : null;
                  if (view) {
                    return <SubstrateObjectChip key={principleId} view={view} />;
                  }
                  // Fallback: principle id not in current ledger; keep the id visible so the
                  // user can still see the link exists, with a not-loaded hedge.
                  return (
                    <span
                      key={principleId}
                      className="rounded border border-zenith-edge-faint bg-white/[0.04] px-1.5 py-0.5 font-mono text-[9px] text-zenith-soft"
                      title={`${principleId} (not loaded in current principles ledger)`}
                      data-zenith-root-substrate-related-principle-id={principleId}
                      data-zenith-root-substrate-related-principle-resolved="false"
                    >
                      {principleId} · unresolved
                    </span>
                  );
                })}
                {selectedAxiom.relatedPrinciples.length > 18 && (
                  <span className="text-[9px] text-zenith-muted">
                    +{selectedAxiom.relatedPrinciples.length - 18} more
                  </span>
                )}
              </div>
            </div>
            {selectedAxiom.evidenceRefs.length > 0 && (
              <div>
                <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">evidence refs</div>
                <ul className="mt-1 space-y-0.5">
                  {selectedAxiom.evidenceRefs.slice(0, 4).map((ref) => (
                    <li key={`${ref.role}:${ref.ref}`} className="text-[10px] leading-4 text-zenith-soft">
                      <span className="font-mono text-amber-100/70">{ref.role}</span>
                      <span className="ml-1 text-zenith-soft">{ref.ref}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        {selectedPrinciple && (
          <div className="space-y-2" data-zenith-root-substrate-family-selection-kind="principle">
            <div className="rounded-[4px] border border-cyan-300/35 bg-cyan-400/[0.08] px-2 py-2">
              <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-cyan-100/85">principle</div>
              <div className="mt-1 text-[13px] font-semibold text-white">{selectedPrinciple.title}</div>
              <p className="mt-1 text-[11px] leading-5 text-white/72">
                {selectedPrinciple.statement || 'statement not loaded in current projection'}
              </p>
            </div>
            <div>
              <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">axioms pointing here</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {axioms
                  .filter((axiom) => axiom.relatedPrinciples.includes(selectedPrinciple.id))
                  .map((axiom) => (
                    <span
                      key={axiom.id}
                      className="rounded border border-amber-300/30 bg-amber-300/[0.10] px-1.5 py-0.5 font-mono text-[9px] text-amber-50/85"
                    >
                      {axiom.title}
                    </span>
                  ))}
                {axioms.every((axiom) => !axiom.relatedPrinciples.includes(selectedPrinciple.id)) && (
                  <span className="text-[10px] text-zenith-muted">no axiom candidate links in current ledger</span>
                )}
              </div>
            </div>
          </div>
        )}
        {selectedNodeId && !selectedAxiom && !selectedPrinciple && (
          <div className="rounded-[4px] border border-zenith-edge bg-white/[0.03] px-2 py-2 text-[11px] leading-4 text-zenith-soft">
            Selection unresolved in current ledger. Try opening the kind lens for richer context.
          </div>
        )}
      </div>
      {selectedNodeId && (
        <button
          type="button"
          onClick={onClear}
          className="mt-2 self-start rounded border border-white/12 bg-white/[0.04] px-2 py-1 font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-soft hover:border-white/24 hover:text-white"
        >
          Clear selection
        </button>
      )}
    </aside>
  );
}

const PRINCIPLE_GROUP_HUE_PALETTE: ReadonlyArray<{ name: string; accent: string; bg: string }> = [
  { name: 'cyan', accent: '#67e8f9', bg: '#031018' },
  { name: 'amber', accent: '#fbbf24', bg: '#160d05' },
  { name: 'violet', accent: '#a78bfa', bg: '#0d0a16' },
  { name: 'emerald', accent: '#6ee7b7', bg: '#031410' },
  { name: 'rose', accent: '#fda4af', bg: '#160808' },
  { name: 'sky', accent: '#7dd3fc', bg: '#03101a' },
  { name: 'orange', accent: '#fdba74', bg: '#150b04' },
  { name: 'lime', accent: '#bef264', bg: '#0c1305' },
  { name: 'fuchsia', accent: '#f0abfc', bg: '#160514' },
  { name: 'slate', accent: '#94a3b8', bg: '#0a1018' },
];

function principleMicroLabel(principle: WorldModelFamilyPrinciple): string {
  const extra = principle as unknown as UnknownRow;
  const explicit = firstNonEmpty(
    asString(extra.short_label),
    asString(extra.display_label),
    asString(extra.micro_label),
  );
  if (explicit) return explicit;
  const source = firstNonEmpty(
    principle.title,
    principle.slug ?? '',
    principle.statement,
    principle.id,
  );
  const cleaned = source
    .replace(/^PRI[_-]?\d+\s*[-:·]?\s*/i, '')
    .replace(/_/g, ' ')
    .trim();
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return source;
  return parts.slice(0, 4).join(' ');
}

// v1.15 substrate object viewing protocol — one shared view model + chip renderer for
// principles and axiom candidates so the axiom-zoom view stops leaking PRI ids and the
// Inspector / selection panel render related objects through the same readable grammar.

type SubstrateObjectKind = 'principle' | 'axiom_candidate';

interface SubstrateObjectViewModel {
  kind: SubstrateObjectKind;
  id: string;
  secondaryId: string;
  primaryLabel: string;
  oneLine: string;
  fullStatement: string;
  groupId: string | null;
  groupLabel: string | null;
  groupSource: string | null;
  outboundIds: string[];
  evidenceRefs: string[];
}

function buildPrincipleViewModel(
  principle: WorldModelFamilyPrinciple,
  group: RootPrincipleGroup | null = null,
): SubstrateObjectViewModel {
  const microLabel = principleMicroLabel(principle);
  const fullStatement = principle.statement ?? '';
  const oneLine = fullStatement.split('. ')[0]?.trim() ?? '';
  return {
    kind: 'principle',
    id: principle.id,
    secondaryId: principle.id,
    primaryLabel: microLabel || principle.title || principle.id,
    oneLine,
    fullStatement,
    groupId: group?.id ?? null,
    groupLabel: group?.label ?? null,
    groupSource: group?.source ?? null,
    outboundIds: [],
    evidenceRefs: [],
  };
}

function buildAxiomCandidateViewModel(
  axiom: FamilyAxiomCandidate,
): SubstrateObjectViewModel {
  const primary = axiom.title || axiom.id;
  return {
    kind: 'axiom_candidate',
    id: axiom.id,
    secondaryId: axiom.id,
    primaryLabel: primary,
    oneLine: axiom.bands.flag || axiom.bands.tiny || axiom.denseClause || axiom.formalClause || '',
    fullStatement: axiom.denseClause || axiom.formalClause || axiom.bands.deep || '',
    groupId: null,
    groupLabel: null,
    groupSource: null,
    outboundIds: axiom.relatedPrinciples,
    evidenceRefs: axiom.evidenceRefs.map((e) => e.ref).filter(Boolean),
  };
}

interface SubstrateObjectChipProps {
  view: SubstrateObjectViewModel;
  onSelect?: (id: string) => void;
  accent?: string;
  size?: 'sm' | 'md';
}

function SubstrateObjectChip({ view, onSelect, accent, size = 'sm' }: SubstrateObjectChipProps) {
  const baseAccent = accent ?? (view.kind === 'axiom_candidate' ? '#c7b06a' : '#67e8f9');
  const interactive = Boolean(onSelect);
  const attrs = {
    'data-zenith-root-substrate-object-chip': view.id,
    'data-zenith-root-substrate-object-chip-kind': view.kind,
    'data-zenith-root-substrate-object-chip-label': view.primaryLabel,
    'data-zenith-root-substrate-object-chip-secondary-id': view.secondaryId,
  };
  const className = clsx(
    'inline-flex max-w-full items-start rounded-[3px] border px-1.5 py-0.5 text-left font-mono leading-4 transition-colors',
    size === 'sm' ? 'text-[10px]' : 'text-[11px]',
    interactive ? 'cursor-pointer hover:border-white/45' : 'cursor-default',
  );
  const style = {
    borderColor: `${baseAccent}55`,
    backgroundColor: `${baseAccent}14`,
    color: baseAccent,
  };
  if (interactive) {
    return (
      <button
        type="button"
        onClick={() => onSelect?.(view.id)}
        title={`${view.primaryLabel} (${view.secondaryId})`}
        aria-label={`${view.primaryLabel} — ${view.secondaryId}`}
        className={className}
        style={style}
        {...attrs}
      >
        <span className="line-clamp-2 whitespace-normal">{view.primaryLabel}</span>
      </button>
    );
  }
  return (
    <span
      title={`${view.primaryLabel} (${view.secondaryId})`}
      aria-label={`${view.primaryLabel} — ${view.secondaryId}`}
      className={className}
      style={style}
      {...attrs}
    >
      <span className="line-clamp-2 whitespace-normal">{view.primaryLabel}</span>
    </span>
  );
}

function principleGroupHue(groupId: string): { accent: string; bg: string; name: string } {
  let hash = 0;
  for (let i = 0; i < groupId.length; i++) {
    hash = (hash * 31 + groupId.charCodeAt(i)) >>> 0;
  }
  return PRINCIPLE_GROUP_HUE_PALETTE[hash % PRINCIPLE_GROUP_HUE_PALETTE.length];
}

interface RootPrincipleGroup {
  id: string;
  label: string;
  source: 'paper_module' | 'primary_subdomain' | 'scope_id' | 'fallback';
  accent: string;
  bg: string;
  paletteName: string;
  principles: WorldModelFamilyPrinciple[];
}

function derivePrincipleGroup(
  principle: WorldModelFamilyPrinciple,
): { id: string; label: string; source: RootPrincipleGroup['source'] } {
  const profile = principle.scope_profile ?? null;
  const paperModule = profile?.paper_module ?? null;
  if (paperModule) {
    return { id: `paper:${paperModule}`, label: paperModule, source: 'paper_module' };
  }
  const subdomain = principle.primary_subdomain ?? null;
  if (subdomain) {
    return { id: `subdomain:${subdomain}`, label: subdomain, source: 'primary_subdomain' };
  }
  const scopeId = profile?.scope_id ?? principle.scope ?? null;
  if (scopeId) {
    return { id: `scope:${scopeId}`, label: scopeId, source: 'scope_id' };
  }
  return { id: 'unscoped', label: 'unscoped', source: 'fallback' };
}

function buildPrincipleGroups(principles: WorldModelFamilyPrinciple[]): RootPrincipleGroup[] {
  const byId = new Map<string, RootPrincipleGroup>();
  for (const principle of principles) {
    const meta = derivePrincipleGroup(principle);
    let group = byId.get(meta.id);
    if (!group) {
      const hue = principleGroupHue(meta.id);
      group = {
        id: meta.id,
        label: meta.label,
        source: meta.source,
        accent: hue.accent,
        bg: hue.bg,
        paletteName: hue.name,
        principles: [],
      };
      byId.set(meta.id, group);
    }
    group.principles.push(principle);
  }
  return Array.from(byId.values()).sort((a, b) => {
    if (a.principles.length !== b.principles.length) return b.principles.length - a.principles.length;
    return a.label.localeCompare(b.label);
  });
}

interface SubstratePrincipleGroupNodeData {
  group: RootPrincipleGroup;
  selectedGroupId: string | null;
}

function SubstratePrincipleGroupNode({ data }: NodeProps<SubstratePrincipleGroupNodeData>) {
  const { group, selectedGroupId } = data;
  const isSelected = selectedGroupId === group.id;
  return (
    <div
      data-zenith-root-substrate-principle-group={group.id}
      data-zenith-root-substrate-principle-group-source={group.source}
      data-zenith-root-substrate-principle-group-palette={group.paletteName}
      data-zenith-root-substrate-principle-group-selected={isSelected ? 'true' : 'false'}
      data-zenith-root-substrate-principle-group-count={group.principles.length}
      className="h-full w-full rounded-[var(--zenith-radius-2xs)] border"
      style={{
        backgroundColor: group.bg,
        borderColor: isSelected ? group.accent : `${group.accent}55`,
        boxShadow: isSelected ? `0 0 18px ${group.accent}33` : undefined,
      }}
    >
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <Handle type="source" position={Position.Right} className="!opacity-0" />
      <div className="flex items-start justify-between gap-2 border-b border-zenith-edge px-3 py-1.5">
        <div className="min-w-0">
          <div
            className="truncate font-mono text-[10px] uppercase tracking-[0.16em]"
            style={{ color: group.accent }}
          >
            {group.label}
          </div>
          <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
            {group.source.replace(/_/g, ' ')}
          </div>
        </div>
        <span
          className="shrink-0 rounded-full border bg-black/40 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em]"
          style={{ borderColor: `${group.accent}55`, color: group.accent }}
        >
          {group.principles.length}
        </span>
      </div>
    </div>
  );
}

interface SubstratePrincipleChipNodeData {
  principle: WorldModelFamilyPrinciple;
  group: RootPrincipleGroup;
  selected: boolean;
  connected: boolean;
  onSelect: (id: string) => void;
  lane?: LocalObjectLensLane;
}

function SubstratePrincipleChipNode({ data }: NodeProps<SubstratePrincipleChipNodeData>) {
  const { principle, group, selected, connected, onSelect, lane } = data;
  const microLabel = principleMicroLabel(principle);
  return (
    <button
      type="button"
      onClick={() => onSelect(principle.id)}
      title={`${microLabel} (${principle.id})`}
      aria-label={`${microLabel} — ${principle.id}`}
      data-zenith-root-substrate-principle-chip={principle.id}
      data-zenith-root-substrate-principle-chip-group={group.id}
      data-zenith-root-substrate-principle-chip-selected={selected ? 'true' : 'false'}
      data-zenith-root-substrate-principle-chip-connected={connected ? 'true' : 'false'}
      data-zenith-root-substrate-family-node={principle.id}
      data-zenith-root-substrate-family-node-kind="principle"
      data-zenith-root-substrate-family-node-selected={selected ? 'true' : 'false'}
      data-zenith-root-substrate-family-node-connected={connected ? 'true' : 'false'}
      data-zenith-root-substrate-family-node-physical="opaque"
      data-zenith-root-substrate-object-primary-label={microLabel}
      data-zenith-root-substrate-object-secondary-id={principle.id}
      data-zenith-root-doctrine-lane="principles"
      data-zenith-root-doctrine-node={principle.id}
      data-zenith-root-doctrine-node-kind="principle"
      data-zenith-root-doctrine-node-selected={selected ? 'true' : 'false'}
      data-zenith-root-doctrine-node-connected={connected ? 'true' : 'false'}
      data-zenith-root-principle-id={principle.id}
      data-zenith-root-principle-label={microLabel}
      data-zenith-root-local-lane={lane ?? ''}
      className="flex h-[36px] w-[180px] items-start rounded-[4px] border bg-[#05070b] px-2 py-1 text-left font-mono transition-colors focus:outline-none"
      style={{
        borderColor: selected
          ? group.accent
          : connected
            ? `${group.accent}aa`
            : `${group.accent}55`,
        boxShadow: selected
          ? `0 0 14px ${group.accent}66`
          : connected
            ? `0 0 8px ${group.accent}33`
            : undefined,
      }}
    >
      <Handle type="target" position={Position.Left} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
      <Handle type="source" position={Position.Right} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
      <span
        className="min-w-0 flex-1 whitespace-normal text-[10.5px] font-semibold leading-4 line-clamp-2"
        style={{ color: selected ? group.accent : '#e2e8f0' }}
      >
        {microLabel || principle.id}
      </span>
      <span className="sr-only" data-zenith-root-principle-secondary-id={principle.id}>
        {principle.title || principle.statement || ' '}
      </span>
    </button>
  );
}

const SUBSTRATE_PRINCIPLE_NODE_TYPES = {
  substratePrincipleGroup: SubstratePrincipleGroupNode,
  substratePrincipleChip: SubstratePrincipleChipNode,
};

interface RootSubstratePrincipleFamilyZoomProps {
  groups: RootPrincipleGroup[];
  selectedNodeId: string | null;
  axiomConnections: Set<string>;
  onSelectNode: (id: string | null) => void;
  loading: boolean;
}

function buildPrincipleFamilyFlow({
  groups,
  selectedNodeId,
  axiomConnections,
  onSelectNode,
}: {
  groups: RootPrincipleGroup[];
  selectedNodeId: string | null;
  axiomConnections: Set<string>;
  onSelectNode: (id: string) => void;
}): { nodes: RfNode[]; edges: RfEdge[]; selectedGroupId: string | null } {
  const nodes: RfNode[] = [];
  const edges: RfEdge[] = [];
  // v1.15 readability: chips taller (36) and wider (180) so the micro-label can wrap.
  // CHIPS_PER_ROW drops to 2 to keep total canvas width manageable.
  const CHIP_WIDTH = 180;
  const CHIP_HEIGHT = 36;
  const CHIP_GAP_X = 8;
  const CHIP_GAP_Y = 8;
  const CHIPS_PER_ROW = 2;
  const GROUP_PADDING_X = 12;
  const GROUP_PADDING_TOP = 44;
  const GROUP_PADDING_BOTTOM = 14;
  const GROUP_GAP_X = 18;
  const GROUP_GAP_Y = 18;
  const GROUPS_PER_ROW = 3;
  const GROUP_WIDTH = GROUP_PADDING_X * 2 + CHIPS_PER_ROW * CHIP_WIDTH + (CHIPS_PER_ROW - 1) * CHIP_GAP_X;

  let cursorRowMaxHeight = 0;
  let cursorY = 0;
  let cursorX = 0;
  let selectedGroupId: string | null = null;

  groups.forEach((group, groupIndex) => {
    const chipRows = Math.max(1, Math.ceil(group.principles.length / CHIPS_PER_ROW));
    const groupHeight =
      GROUP_PADDING_TOP + chipRows * CHIP_HEIGHT + (chipRows - 1) * CHIP_GAP_Y + GROUP_PADDING_BOTTOM;
    const colInRow = groupIndex % GROUPS_PER_ROW;
    if (colInRow === 0 && groupIndex > 0) {
      cursorY += cursorRowMaxHeight + GROUP_GAP_Y;
      cursorRowMaxHeight = 0;
      cursorX = 0;
    }
    cursorX = colInRow * (GROUP_WIDTH + GROUP_GAP_X);
    cursorRowMaxHeight = Math.max(cursorRowMaxHeight, groupHeight);
    const groupNodeId = `substrate-principle-group:${group.id}`;
    nodes.push({
      id: groupNodeId,
      type: 'substratePrincipleGroup',
      position: { x: cursorX, y: cursorY },
      style: { width: GROUP_WIDTH, height: groupHeight, zIndex: 0 },
      draggable: false,
      selectable: false,
      data: {
        group,
        selectedGroupId,
      } satisfies SubstratePrincipleGroupNodeData,
    });
    group.principles.forEach((principle, idx) => {
      const isSelected = selectedNodeId === principle.id;
      if (isSelected) selectedGroupId = group.id;
      const isConnected = axiomConnections.has(principle.id) && !isSelected;
      // v1.15 Local Object Lens lanes for the principles family graph:
      // center  = selected principle; context = sibling principles in the same group;
      // inbound = principles that an axiom-side selection points back through.
      let lane: LocalObjectLensLane = '';
      if (isSelected) lane = 'center';
      else if (isConnected) lane = 'inbound';
      else if (selectedGroupId === group.id) lane = 'context';
      const row = Math.floor(idx / CHIPS_PER_ROW);
      const col = idx % CHIPS_PER_ROW;
      nodes.push({
        id: `substrate-principle-chip:${principle.id}`,
        type: 'substratePrincipleChip',
        parentId: groupNodeId,
        extent: 'parent',
        position: {
          x: GROUP_PADDING_X + col * (CHIP_WIDTH + CHIP_GAP_X),
          y: GROUP_PADDING_TOP + row * (CHIP_HEIGHT + CHIP_GAP_Y),
        },
        style: { width: CHIP_WIDTH },
        draggable: false,
        data: {
          principle,
          group,
          selected: isSelected,
          connected: isConnected,
          onSelect: onSelectNode,
          lane,
        } satisfies SubstratePrincipleChipNodeData,
      });
    });
  });

  if (selectedGroupId) {
    for (const node of nodes) {
      if (node.type !== 'substratePrincipleGroup') continue;
      const data = node.data as SubstratePrincipleGroupNodeData;
      node.data = { ...data, selectedGroupId } satisfies SubstratePrincipleGroupNodeData;
    }
  }

  return { nodes, edges, selectedGroupId };
}

function RootSubstratePrincipleFamilyZoomInner({
  groups,
  selectedNodeId,
  axiomConnections,
  onSelectNode,
  loading,
}: RootSubstratePrincipleFamilyZoomProps) {
  const handleSelect = useCallback(
    (id: string) => onSelectNode(id === selectedNodeId ? null : id),
    [onSelectNode, selectedNodeId],
  );
  const layout = useMemo(
    () =>
      buildPrincipleFamilyFlow({
        groups,
        selectedNodeId,
        axiomConnections,
        onSelectNode: handleSelect,
      }),
    [groups, selectedNodeId, axiomConnections, handleSelect],
  );
  const selectedKind: SubstrateObjectKind | null = selectedNodeId
    ? selectedNodeId.startsWith('axiom_candidate_')
      ? 'axiom_candidate'
      : selectedNodeId.startsWith('pri_')
        ? 'principle'
        : null
    : null;
  const lensReady = Boolean(selectedNodeId && selectedKind);
  return (
    <div
      className="relative h-full w-full"
      data-zenith-root-substrate-principle-groups="ready"
      data-zenith-root-substrate-principle-group-count={groups.length}
      data-zenith-root-substrate-principle-selected-group={layout.selectedGroupId ?? ''}
      data-zenith-root-local-object-lens={lensReady ? 'ready' : 'idle'}
      data-zenith-root-local-object-id={selectedNodeId ?? ''}
      data-zenith-root-local-object-kind={selectedKind ?? ''}
      data-zenith-root-local-object-family="principles"
    >
      {loading && (
        <div className="pointer-events-none absolute right-3 top-3 z-10 rounded-[4px] border border-zenith-edge bg-black/60 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft">
          loading principles
        </div>
      )}
      <ReactFlow
        nodes={layout.nodes}
        edges={layout.edges}
        nodeTypes={SUBSTRATE_PRINCIPLE_NODE_TYPES}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        // M3: principle-family zoom is a node-only graph (no edges in
        // buildPrincipleFamilyFlow). Apply the same wayfinding-map a11y
        // contract for consistency; the ariaLabel:'' on edges is a no-op
        // here since no edges are built. Per
        // cap_quick_extend_wayfinding_map_a11y_contract_acro_863da57484ec.
        edgesFocusable={false}
        disableKeyboardA11y
        minZoom={0.45}
        maxZoom={1.4}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="rgba(226,232,240,0.08)" />
      </ReactFlow>
    </div>
  );
}

function RootSubstratePrincipleFamilyZoom(props: RootSubstratePrincipleFamilyZoomProps) {
  return (
    <ReactFlowProvider>
      <RootSubstratePrincipleFamilyZoomInner {...props} />
    </ReactFlowProvider>
  );
}

// v1.18 unified doctrine binding field. The previous split between
// RootSubstrateFamilyZoomGraph (axiom focus) and RootSubstratePrincipleFamilyZoom
// (principle focus) was a fragmented codepath that maintained two "views" over the
// same axiom <> principle binding surface. v1.18 collapses them into one component
// whose focus prop is an emphasis hint only: both lanes (axioms + principles) are
// always present in the DOM regardless of focus, both routes emit the same
// data-zenith-root-doctrine-binding-field="ready" + lane attrs, and selection
// behaviour is identical via handleFamilyNodeSelect on either entry.

interface RootDoctrineBindingFieldProps {
  focus: 'axiom_candidates' | 'principles';
  axioms: FamilyAxiomCandidate[];
  principles: FamilyPrincipleNode[];
  principleGroups: RootPrincipleGroup[];
  selectedNodeId: string | null;
  axiomConnections: Set<string>;
  onSelectNode: (id: string | null) => void;
  loading: boolean;
  errorLine: string | null;
}

// Compact axiom rail rendered in principle focus so the principle lane is the
// primary canvas but the axiom lane is still visible and selectable. Reuses
// buildAxiomCandidateViewModel so the readable grammar matches the family-zoom
// axiom cards (no PRI / axiom_candidate_*** leak, micro-label / title primary).
// v1.19: takes connectedAxiomIds so inbound axioms light up when a principle is
// selected. Without this, the rail only marked the selected axiom itself and
// the binding direction principle←axiom was invisible.
function DoctrineBindingAxiomRail({
  axioms,
  selectedNodeId,
  connectedAxiomIds,
  onSelect,
}: {
  axioms: FamilyAxiomCandidate[];
  selectedNodeId: string | null;
  connectedAxiomIds: Set<string>;
  onSelect: (id: string | null) => void;
}) {
  if (axioms.length === 0) return null;
  return (
    <div
      className="flex flex-wrap items-stretch gap-1.5 border-b border-amber-300/15 bg-[#0e0a05]/55 px-3 py-2"
      data-zenith-root-doctrine-lane="axioms"
      data-zenith-root-doctrine-axis-rail="principles_focus"
    >
      <div className="flex items-center pr-2 font-mono text-[9px] uppercase tracking-[0.16em] text-amber-100/65">
        axiom lane
      </div>
      {axioms.map((axiom) => {
        const view = buildAxiomCandidateViewModel(axiom);
        const isSelected = selectedNodeId === axiom.id;
        const isConnected = !isSelected && connectedAxiomIds.has(axiom.id);
        const lane = isSelected ? 'center' : isConnected ? 'inbound' : '';
        return (
          <button
            type="button"
            key={axiom.id}
            onClick={() => onSelect(isSelected ? null : axiom.id)}
            title={`${view.primaryLabel} (${view.secondaryId})`}
            aria-label={`${view.primaryLabel} — ${view.secondaryId}`}
            data-zenith-root-doctrine-node={axiom.id}
            data-zenith-root-doctrine-node-kind="axiom_candidate"
            data-zenith-root-doctrine-node-selected={isSelected ? 'true' : 'false'}
            data-zenith-root-doctrine-node-connected={isSelected || isConnected ? 'true' : 'false'}
            data-zenith-root-substrate-object-primary-label={view.primaryLabel}
            data-zenith-root-substrate-object-secondary-id={view.secondaryId}
            data-zenith-root-local-lane={lane}
            className={clsx(
              'flex max-w-[200px] items-center rounded-[4px] border bg-[#0e0a05] px-2 py-1 text-left font-mono leading-4 transition-colors',
              isSelected
                ? 'border-amber-300/85 ring-1 ring-amber-300/55 shadow-[0_0_14px_rgba(199,176,106,0.18)]'
                : isConnected
                  ? 'border-amber-300/70 shadow-[0_0_10px_rgba(199,176,106,0.16)]'
                  : 'border-amber-300/30 hover:border-amber-200/70 focus:outline-none focus:ring-1 focus:ring-amber-300/55',
            )}
          >
            <span className="line-clamp-2 whitespace-normal text-[10.5px] font-semibold text-amber-50/90">
              {view.primaryLabel}
            </span>
            {isConnected && (
              <span
                className="ml-1.5 inline-flex shrink-0 items-center rounded border border-amber-300/35 bg-amber-300/15 px-1 font-mono text-[8.5px] uppercase tracking-[0.14em] text-amber-50/85"
                data-zenith-root-doctrine-relation-badge="inbound"
              >
                bound
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function RootDoctrineBindingField({
  focus,
  axioms,
  principles,
  principleGroups,
  selectedNodeId,
  axiomConnections,
  onSelectNode,
  loading,
  errorLine,
}: RootDoctrineBindingFieldProps) {
  // v1.19: relation legibility. Build the axiom <> principle binding maps once and
  // derive the connected-id sets so the rail lights up inbound axioms when a
  // principle is selected and the principle lane lights up outbound principles
  // when an axiom is selected. Both directions go through one model.
  const { connectedAxiomIds, activeBindings, selectedKind } = useMemo(() => {
    const axiomKind = selectedNodeId?.startsWith('axiom_candidate_')
      ? ('axiom_candidate' as const)
      : selectedNodeId?.startsWith('pri_')
        ? ('principle' as const)
        : null;
    const connAxiomIds = new Set<string>();
    const bindings: Array<{ source: string; target: string }> = [];
    if (selectedNodeId && axiomKind === 'axiom_candidate') {
      const axiom = axioms.find((a) => a.id === selectedNodeId);
      if (axiom) {
        for (const pid of axiom.relatedPrinciples) {
          bindings.push({ source: axiom.id, target: pid });
        }
      }
    } else if (selectedNodeId && axiomKind === 'principle') {
      for (const axiom of axioms) {
        if (axiom.relatedPrinciples.includes(selectedNodeId)) {
          connAxiomIds.add(axiom.id);
          bindings.push({ source: axiom.id, target: selectedNodeId });
        }
      }
    }
    return { connectedAxiomIds: connAxiomIds, activeBindings: bindings, selectedKind: axiomKind };
  }, [axioms, selectedNodeId]);

  const noNeighborhood = Boolean(selectedNodeId && selectedKind && activeBindings.length === 0);

  return (
    <div
      className="flex h-full w-full flex-col"
      data-zenith-root-doctrine-binding-field="ready"
      data-zenith-root-doctrine-binding-focus={focus}
      data-zenith-root-doctrine-binding-selected={selectedNodeId ?? ''}
      data-zenith-root-doctrine-binding-selected-kind={selectedKind ?? ''}
      data-zenith-root-doctrine-binding-axiom-count={axioms.length}
      data-zenith-root-doctrine-binding-principle-count={principles.length}
      data-zenith-root-doctrine-binding-active-count={activeBindings.length}
      data-zenith-root-doctrine-binding-neighborhood={noNeighborhood ? 'empty' : activeBindings.length > 0 ? 'populated' : 'unselected'}
      data-zenith-root-graph-node={focus}
      data-zenith-root-graph-node-kind={focus}
      data-zenith-root-graph-node-role="substrate_container"
      data-zenith-root-graph-node-parent="root:substrate"
      data-zenith-root-graph-node-adapter="doctrine_binding"
      data-zenith-root-graph-node-expanded="true"
    >
      {/* v1.19 relation receipts. Each active binding emits a hidden source/target/
          relation receipt so station_render and tests can prove the relation set
          without scraping into React Flow internals. The visual edges/borders are
          driven by the same data via the rail's connected state and buildFamilyZoomFlow's
          axiomConnectedPrincipleIds / principleConnectedAxiomIds maps. */}
      {activeBindings.length > 0 && (
        <div className="sr-only" data-zenith-root-doctrine-binding-receipts="ready">
          {activeBindings.map((b) => (
            <span
              key={`${b.source}->${b.target}`}
              data-zenith-root-doctrine-binding-source={b.source}
              data-zenith-root-doctrine-binding-target={b.target}
              data-zenith-root-doctrine-binding-relation="axiom_compresses_principle"
            />
          ))}
        </div>
      )}
      {noNeighborhood && (
        <div
          className="border-b border-amber-300/20 bg-amber-300/[0.04] px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65"
          data-zenith-root-doctrine-binding-receipt="empty_neighborhood"
        >
          relation neighborhood · empty for{' '}
          <span className="font-mono normal-case text-amber-50/85">{selectedNodeId}</span>
          {' · '}
          no axiom ⇄ principle bindings in current ledger
        </div>
      )}
      {focus === 'axiom_candidates' ? (
        // Axiom-focus layout: the buildFamilyZoomFlow canvas already places axiom nodes
        // (data-zenith-root-doctrine-lane="axioms") in a left column and principle nodes
        // (data-zenith-root-doctrine-lane="principles") in right columns inside one
        // React Flow surface, so both lanes are present via descendant node attrs.
        // buildFamilyZoomFlow's axiomConnectedPrincipleIds / principleConnectedAxiomIds
        // already drive the connected attrs on those nodes (v1.15 lane work).
        <div className="relative h-full min-h-0">
          <RootSubstrateFamilyZoomGraph
            focusKind="axiom_candidates"
            axioms={axioms}
            principles={principles}
            selectedNodeId={selectedNodeId}
            onSelectNode={onSelectNode}
            loading={loading}
            errorLine={errorLine}
          />
        </div>
      ) : (
        // Principle-focus layout keeps the v1.13 paper_module / scope grouped chips as
        // the primary canvas (the operator's preferred principle-browsing view) and
        // renders the axiom rail as a compact lane above so both lanes are present.
        <div className="grid h-full grid-rows-[auto_minmax(0,1fr)]">
          <DoctrineBindingAxiomRail
            axioms={axioms}
            selectedNodeId={selectedNodeId}
            connectedAxiomIds={connectedAxiomIds}
            onSelect={onSelectNode}
          />
          <div
            className="relative min-h-0"
            data-zenith-root-doctrine-lane="principles"
            data-zenith-root-doctrine-lane-emphasis="primary"
          >
            <RootSubstratePrincipleFamilyZoom
              groups={principleGroups}
              selectedNodeId={selectedNodeId}
              axiomConnections={axiomConnections}
              onSelectNode={onSelectNode}
              loading={loading}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// v1.20: paper_modules graph-native visual field. Replaces the legacy
// ?kind=paper_modules generic relation graph (Rationale objects -> Paper Modules ->
// Option surface / Evidence / Agent route) with a field of actual paper-module
// objects grouped by source-owned subdomain clusters from
// `kernel.py --option-surface paper_modules --band cluster_flag`.
//
// Substrate field shape (per /tmp discovery):
//   row.cluster_id   e.g. "subdomain_authority_projection"
//   row.title        e.g. "Subdomain / Authority Projection"
//   row.count        total members
//   row.top_ids      module ids visible at the cluster_flag band
// Card-band per module (fetched on selection):
//   title, tldr_excerpt, purpose_or_intent, top_dependencies, top_dependents,
//   governing_refs, nearest_standard, source_ref, standard_ref
//
// Layout uses plain CSS grid (no React Flow) because clusters + modules are simple
// grouped chips and edges are not yet authored.

interface PaperModuleClusterModel {
  id: string;
  label: string;
  shortLabel: string;
  count: number;
  topIds: string[];
  accent: string;
  bg: string;
  paletteName: string;
}

function paperModuleClusterShortLabel(label: string): string {
  // "Subdomain / Authority Projection" -> "Authority Projection"
  const idx = label.indexOf('/');
  return (idx >= 0 ? label.slice(idx + 1) : label).trim();
}

function paperModuleReadableLabel(id: string, fallbackTitle?: string): string {
  if (fallbackTitle && fallbackTitle.trim()) return fallbackTitle.trim();
  // Convert "agent_bootstrap_builder" -> "Agent Bootstrap Builder" as a readable
  // surrogate until the card-band title is loaded for the selected module.
  return id
    .split(/[_-]/)
    .filter(Boolean)
    .map((token) => (token.length <= 2 ? token : token[0].toUpperCase() + token.slice(1)))
    .join(' ');
}

function buildPaperModuleClusters(rows: UnknownRow[]): PaperModuleClusterModel[] {
  const clusters: PaperModuleClusterModel[] = [];
  for (const row of rows) {
    const id = asString(row.cluster_id) || asString(row.id);
    if (!id) continue;
    const label = asString(row.title) || asString(row.label) || id;
    const count = typeof row.count === 'number' ? row.count : asStringArray(row.top_ids).length;
    const topIds = asStringArray(row.top_ids);
    const hue = principleGroupHue(id);
    clusters.push({
      id,
      label,
      shortLabel: paperModuleClusterShortLabel(label),
      count,
      topIds,
      accent: hue.accent,
      bg: hue.bg,
      paletteName: hue.name,
    });
  }
  // Cluster ordering: larger clusters first so the field's visual weight matches
  // the substrate density; ties broken by alphabetical label for stable layout.
  clusters.sort((a, b) => {
    if (b.count !== a.count) return b.count - a.count;
    return a.label.localeCompare(b.label);
  });
  return clusters;
}

interface RootPaperModuleVisualFieldProps {
  clusters: PaperModuleClusterModel[];
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  loading: boolean;
  errorLine: string | null;
  totalRowCount: number;
}

function RootPaperModuleVisualField({
  clusters,
  selectedNodeId,
  onSelectNode,
  loading,
  errorLine,
  totalRowCount,
}: RootPaperModuleVisualFieldProps) {
  const selectedClusterId = useMemo(() => {
    if (!selectedNodeId) return null;
    for (const cluster of clusters) {
      if (cluster.topIds.includes(selectedNodeId)) return cluster.id;
    }
    return null;
  }, [clusters, selectedNodeId]);
  return (
    <div
      className="flex h-full min-h-0 flex-col"
      data-zenith-root-paper-module-field="ready"
      data-zenith-root-paper-module-field-selected={selectedNodeId ?? ''}
      data-zenith-root-paper-module-field-cluster-count={clusters.length}
      data-zenith-root-paper-module-field-total-count={totalRowCount}
      data-zenith-root-paper-module-field-selected-cluster={selectedClusterId ?? ''}
      data-zenith-root-graph-node="paper_modules"
      data-zenith-root-graph-node-kind="paper_modules"
      data-zenith-root-graph-node-role="substrate_container"
      data-zenith-root-graph-node-parent="root:substrate"
      data-zenith-root-graph-node-adapter="paper_modules"
      data-zenith-root-graph-node-expanded="true"
    >
      {(loading || errorLine) && (
        <div className="border-b border-zenith-edge bg-black/40 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft">
          {loading ? 'loading paper modules' : errorLine}
        </div>
      )}
      <div className="grid auto-rows-min gap-3 overflow-y-auto p-3 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
        {clusters.map((cluster) => {
          const isSelectedCluster = selectedClusterId === cluster.id;
          const hiddenCount = Math.max(0, cluster.count - cluster.topIds.length);
          return (
            <div
              key={cluster.id}
              className="rounded-[5px] border"
              style={{
                backgroundColor: cluster.bg,
                borderColor: isSelectedCluster ? cluster.accent : `${cluster.accent}55`,
                boxShadow: isSelectedCluster ? `0 0 16px ${cluster.accent}33` : undefined,
              }}
              data-zenith-root-paper-module-cluster={cluster.id}
              data-zenith-root-paper-module-cluster-count={cluster.count}
              data-zenith-root-paper-module-cluster-palette={cluster.paletteName}
              data-zenith-root-paper-module-cluster-selected={isSelectedCluster ? 'true' : 'false'}
            >
              <div className="flex items-start justify-between gap-2 border-b border-zenith-edge px-3 py-1.5">
                <div className="min-w-0">
                  <div
                    className="truncate font-mono text-[10px] uppercase tracking-[0.16em]"
                    style={{ color: cluster.accent }}
                  >
                    {cluster.shortLabel}
                  </div>
                  <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
                    subdomain cluster
                  </div>
                </div>
                <span
                  className="shrink-0 rounded-full border bg-black/40 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em]"
                  style={{ borderColor: `${cluster.accent}55`, color: cluster.accent }}
                >
                  {cluster.count}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5 px-3 py-2">
                {cluster.topIds.length === 0 && (
                  <span className="text-[10px] text-zenith-muted">
                    no preview ids in current ledger
                  </span>
                )}
                {cluster.topIds.map((id) => {
                  const isSelected = selectedNodeId === id;
                  const label = paperModuleReadableLabel(id);
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => onSelectNode(isSelected ? null : id)}
                      title={`${label} (${id})`}
                      aria-label={`${label} — ${id}`}
                      data-zenith-root-paper-module-node={id}
                      data-zenith-root-paper-module-node-selected={isSelected ? 'true' : 'false'}
                      data-zenith-root-paper-module-node-cluster={cluster.id}
                      data-zenith-root-substrate-object-primary-label={label}
                      data-zenith-root-substrate-object-secondary-id={id}
                      data-zenith-root-local-lane={isSelected ? 'center' : ''}
                      className={clsx(
                        'flex max-w-full items-start rounded-[4px] border bg-[#05070b] px-2 py-1 text-left font-mono leading-4 transition-colors focus:outline-none',
                      )}
                      style={{
                        borderColor: isSelected ? cluster.accent : `${cluster.accent}55`,
                        boxShadow: isSelected ? `0 0 12px ${cluster.accent}44` : undefined,
                      }}
                    >
                      <span
                        className="line-clamp-2 whitespace-normal text-[10.5px] font-semibold"
                        style={{ color: isSelected ? cluster.accent : '#e2e8f0' }}
                      >
                        {label}
                      </span>
                    </button>
                  );
                })}
                {hiddenCount > 0 && (
                  <span
                    className="self-end rounded-full border border-white/12 bg-white/[0.03] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-soft"
                    data-zenith-root-paper-module-cluster-hidden-count={hiddenCount}
                    title={`${hiddenCount} more in this subdomain not visible at cluster_flag band; open kind lens for the full member list`}
                  >
                    +{hiddenCount} more
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// v1.21: standards graph-native grammar field. Replaces the legacy ?kind=standards
// generic relation graph with a field of actual standard objects grouped by
// source-owned group clusters from `kernel.py --option-surface standards --band
// cluster_flag` (8 groups, 190 standards). Standards are shared grammar and
// conformance contracts, not rationale objects, so the visual grammar carries
// extra row-level encoding for governed-kind affinity and status when the
// option-surface cluster row exposes them.
//
// Substrate cluster_flag shape (per /tmp discovery):
//   row.cluster_id     e.g. "core"
//   row.label          e.g. "Core standards"
//   row.count          total members
//   row.top_ids        standard ids visible at the cluster_flag band
//   row.sample_titles  4 sample titles for human-readable chip surrogates
// Card-band per standard (fetched on selection):
//   title, claim, summary_excerpt, status, group, source_ref, companion_ref,
//   teleology_intent_capsule, currentness, top_validation_rules,
//   navigation_contract { artifact_kind, validation_probe, navigable_bands, ... },
//   related_surfaces, nearest_standard, nearest_skill, evidence_commands,
//   core_law, option_shards, naming_layers
//
// Layout mirrors RootPaperModuleVisualField (plain CSS grid, no React Flow).
// Per-cluster color uses principleGroupHue keyed on the group id so the same
// group keeps a stable accent across the cockpit.
interface StandardClusterModel {
  id: string;
  label: string;
  shortLabel: string;
  count: number;
  topIds: string[];
  sampleTitlesById: Map<string, string>;
  accent: string;
  bg: string;
  paletteName: string;
}

function standardClusterShortLabel(label: string): string {
  // "Core standards" -> "Core"; "Observe Apply standards" -> "Observe Apply".
  return label.replace(/\s+standards?$/i, '').trim() || label;
}

function standardReadableLabel(id: string, fallbackTitle?: string): string {
  if (fallbackTitle && fallbackTitle.trim()) return fallbackTitle.trim();
  // Convert "std_paper_module" -> "Paper Module" (drop std_ prefix), keep small
  // tokens lowercase, otherwise title-case. Raw id remains accessible via
  // data-zenith-root-substrate-object-secondary-id on the chip.
  const stripped = id.startsWith('std_') ? id.slice(4) : id;
  return stripped
    .split(/[_-]/)
    .filter(Boolean)
    .map((token) => (token.length <= 2 ? token : token[0].toUpperCase() + token.slice(1)))
    .join(' ');
}

function buildStandardClusters(rows: UnknownRow[]): StandardClusterModel[] {
  const clusters: StandardClusterModel[] = [];
  for (const row of rows) {
    const id = asString(row.cluster_id) || asString(row.group) || asString(row.id);
    if (!id) continue;
    const label = asString(row.label) || asString(row.title) || id;
    const count = typeof row.count === 'number' ? row.count : asStringArray(row.top_ids).length;
    const topIds = asStringArray(row.top_ids);
    // sample_titles is parallel to top_ids in cluster_flag output; zip up to the
    // shorter length so chip labels can prefer the source title before the
    // standardReadableLabel surrogate.
    const sampleTitles = asStringArray(row.sample_titles);
    const sampleTitlesById = new Map<string, string>();
    for (let i = 0; i < Math.min(topIds.length, sampleTitles.length); i += 1) {
      const title = sampleTitles[i];
      if (title && title.trim()) sampleTitlesById.set(topIds[i], title.trim());
    }
    const hue = principleGroupHue(id);
    clusters.push({
      id,
      label,
      shortLabel: standardClusterShortLabel(label),
      count,
      topIds,
      sampleTitlesById,
      accent: hue.accent,
      bg: hue.bg,
      paletteName: hue.name,
    });
  }
  clusters.sort((a, b) => {
    if (b.count !== a.count) return b.count - a.count;
    return a.label.localeCompare(b.label);
  });
  return clusters;
}

interface RootStandardsGrammarFieldProps {
  clusters: StandardClusterModel[];
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  loading: boolean;
  errorLine: string | null;
  totalRowCount: number;
}

function RootStandardsGrammarField({
  clusters,
  selectedNodeId,
  onSelectNode,
  loading,
  errorLine,
  totalRowCount,
}: RootStandardsGrammarFieldProps) {
  const selectedClusterId = useMemo(() => {
    if (!selectedNodeId) return null;
    for (const cluster of clusters) {
      if (cluster.topIds.includes(selectedNodeId)) return cluster.id;
    }
    return null;
  }, [clusters, selectedNodeId]);
  return (
    <div
      className="flex h-full min-h-0 flex-col"
      data-zenith-root-standards-field="ready"
      data-zenith-root-standards-field-selected={selectedNodeId ?? ''}
      data-zenith-root-standards-field-cluster-count={clusters.length}
      data-zenith-root-standards-field-total-count={totalRowCount}
      data-zenith-root-standards-field-selected-cluster={selectedClusterId ?? ''}
      data-zenith-root-graph-node="standards"
      data-zenith-root-graph-node-kind="standards"
      data-zenith-root-graph-node-role="substrate_container"
      data-zenith-root-graph-node-parent="root:substrate"
      data-zenith-root-graph-node-adapter="standards"
      data-zenith-root-graph-node-expanded="true"
    >
      {(loading || errorLine) && (
        <div className="border-b border-zenith-edge bg-black/40 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft">
          {loading ? 'loading standards' : errorLine}
        </div>
      )}
      <div className="grid auto-rows-min gap-3 overflow-y-auto p-3 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
        {clusters.map((cluster) => {
          const isSelectedCluster = selectedClusterId === cluster.id;
          const hiddenCount = Math.max(0, cluster.count - cluster.topIds.length);
          return (
            <div
              key={cluster.id}
              className="rounded-[5px] border"
              style={{
                backgroundColor: cluster.bg,
                borderColor: isSelectedCluster ? cluster.accent : `${cluster.accent}55`,
                boxShadow: isSelectedCluster ? `0 0 16px ${cluster.accent}33` : undefined,
              }}
              data-zenith-root-standard-cluster={cluster.id}
              data-zenith-root-standard-cluster-count={cluster.count}
              data-zenith-root-standard-cluster-palette={cluster.paletteName}
              data-zenith-root-standard-cluster-selected={isSelectedCluster ? 'true' : 'false'}
            >
              <div className="flex items-start justify-between gap-2 border-b border-zenith-edge px-3 py-1.5">
                <div className="min-w-0">
                  <div
                    className="truncate font-mono text-[10px] uppercase tracking-[0.16em]"
                    style={{ color: cluster.accent }}
                  >
                    {cluster.shortLabel}
                  </div>
                  <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
                    standards group
                  </div>
                </div>
                <span
                  className="shrink-0 rounded-full border bg-black/40 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em]"
                  style={{ borderColor: `${cluster.accent}55`, color: cluster.accent }}
                >
                  {cluster.count}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5 px-3 py-2">
                {cluster.topIds.length === 0 && (
                  <span className="text-[10px] text-zenith-muted">
                    no preview ids in current ledger
                  </span>
                )}
                {cluster.topIds.map((id) => {
                  const isSelected = selectedNodeId === id;
                  const label = standardReadableLabel(id, cluster.sampleTitlesById.get(id));
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => onSelectNode(isSelected ? null : id)}
                      title={`${label} (${id})`}
                      aria-label={`${label} — ${id}`}
                      data-zenith-root-standard-node={id}
                      data-zenith-root-standard-node-selected={isSelected ? 'true' : 'false'}
                      data-zenith-root-standard-node-cluster={cluster.id}
                      data-zenith-root-substrate-object-primary-label={label}
                      data-zenith-root-substrate-object-secondary-id={id}
                      data-zenith-root-local-lane={isSelected ? 'center' : ''}
                      className={clsx(
                        'flex max-w-full items-start rounded-[4px] border bg-[#05070b] px-2 py-1 text-left font-mono leading-4 transition-colors focus:outline-none',
                      )}
                      style={{
                        borderColor: isSelected ? cluster.accent : `${cluster.accent}55`,
                        boxShadow: isSelected ? `0 0 12px ${cluster.accent}44` : undefined,
                      }}
                    >
                      <span
                        className="line-clamp-2 whitespace-normal text-[10.5px] font-semibold"
                        style={{ color: isSelected ? cluster.accent : '#e2e8f0' }}
                      >
                        {label}
                      </span>
                    </button>
                  );
                })}
                {hiddenCount > 0 && (
                  <span
                    className="self-end rounded-full border border-white/12 bg-white/[0.03] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-soft"
                    data-zenith-root-standard-cluster-hidden-count={hiddenCount}
                    title={`${hiddenCount} more in this group not visible at cluster_flag band; open kind lens for the full member list`}
                  >
                    +{hiddenCount} more
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface RootWorkbenchGraphProps {
  model: RootWorkbenchGraphModel;
  focusDetail: ReactNode;
  onSelectKind: (kind: string) => void;
  onSelectRow: (rowId: string | null) => void;
  onSelectInspectorTab: (tab: InspectorTab) => void;
}

function RootWorkbenchGraph({
  model,
  focusDetail,
  onSelectKind,
  onSelectRow,
  onSelectInspectorTab,
}: RootWorkbenchGraphProps) {
  const nodeById = useMemo(() => {
    const map = new Map<string, RootWorkbenchNode>();
    for (const node of model.nodes) map.set(node.id, node);
    return map;
  }, [model.nodes]);
  const geometryById = useMemo(() => {
    const map = new Map<string, RootWorkbenchNodeGeometry>();
    for (const node of model.nodes) {
      map.set(node.id, rootWorkbenchNodeGeometry(node, node.id === model.focusId));
    }
    return map;
  }, [model.focusId, model.nodes]);
  const handleSelect = (node: RootWorkbenchNode) => {
    if (node.kindRef) onSelectKind(node.kindRef);
    else if (node.rowRef) onSelectRow(node.rowRef);
    else if (node.inspectorTab) onSelectInspectorTab(node.inspectorTab);
  };
  const renderNode = (node: RootWorkbenchNode) => {
    const active = node.id === model.focusId;
    const actionable = Boolean(node.kindRef || node.rowRef || node.inspectorTab || node.href);
    const showStatus = Boolean(
      node.status && shouldRenderRowStatus(node.status, active ? node.status : null, active ? 'focus-node' : 'dense-list'),
    );
    const nodeBody = (
      <>
        <div className="flex items-center justify-between gap-2">
          <span className="truncate font-mono text-[9px] uppercase tracking-[0.16em] text-zenith-muted">
            {node.kicker}
          </span>
          {showStatus && <StatusPill status={graphStatusLabel(node.status)} dim />}
        </div>
        <div className="mt-1 truncate text-[13px] font-semibold text-white/90">{node.label}</div>
        <p className="mt-1 line-clamp-2 text-[10.5px] leading-4 text-white/52">{node.detail}</p>
        {node.relationHint && (
          <div className="mt-1 truncate font-mono text-[9px] uppercase tracking-[0.14em] text-[#c7b06a]/70">
            {node.relationHint}
          </div>
        )}
      </>
    );
    const className = clsx(
      'absolute w-[210px] -translate-x-1/2 -translate-y-1/2 rounded-[4px] border px-[var(--zenith-space-2-5)] py-2 text-left transition-colors',
      active && 'w-[250px]',
      graphNodeTone(node.role, active),
      actionable && 'hover:border-cyan-200/45 hover:shadow-[0_0_18px_rgba(125,211,252,0.10)] focus:outline-none focus:ring-1 focus:ring-cyan-200/50',
      !actionable && 'cursor-default',
    );
    const style = { left: `${node.x}%`, top: `${node.y}%` };
    const attrs = {
      'data-zenith-root-workbench-node': node.id,
      'data-zenith-root-workbench-node-role': node.role,
      'data-zenith-root-workbench-selected': active ? 'true' : 'false',
      'data-zenith-root-workbench-kind': node.kindRef,
      'data-zenith-root-workbench-node-physical': 'opaque',
    };
    if (node.href) {
      return (
        <Link key={node.id} to={node.href} className={className} style={style} {...attrs}>
          {nodeBody}
        </Link>
      );
    }
    return (
      <button
        key={node.id}
        type="button"
        onClick={() => handleSelect(node)}
        className={className}
        style={style}
        disabled={!actionable}
        {...attrs}
      >
        {nodeBody}
      </button>
    );
  };
  return (
    <div
      className="flex h-full min-h-[420px] flex-col overflow-hidden"
      data-zenith-root-workbench-graph="ready"
      data-zenith-root-workbench-focus={model.focusId}
    >
      <div className="relative min-h-[260px] flex-1 overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] bg-[size:42px_42px] opacity-35" />
        <svg
          className="pointer-events-none absolute inset-0 h-full w-full"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          {model.edges.map((edge) => {
            const source = nodeById.get(edge.source);
            const target = nodeById.get(edge.target);
            if (!source || !target) return null;
            const sourceGeometry = geometryById.get(edge.source);
            const targetGeometry = geometryById.get(edge.target);
            if (!sourceGeometry || !targetGeometry) return null;
            const sourceCenter = { x: source.x, y: source.y };
            const targetCenter = { x: target.x, y: target.y };
            const start = clipLineToRectBoundary(targetCenter, sourceGeometry);
            const end = clipLineToRectBoundary(sourceCenter, targetGeometry);
            return (
              <g key={edge.id}>
                <line
                  data-zenith-root-workbench-edge={edge.id}
                  data-zenith-root-workbench-edge-source-center={edgeEndpointData(sourceCenter)}
                  data-zenith-root-workbench-edge-target-center={edgeEndpointData(targetCenter)}
                  data-zenith-root-workbench-edge-start={edgeEndpointData(start)}
                  data-zenith-root-workbench-edge-end={edgeEndpointData(end)}
                  data-zenith-root-workbench-edge-label={edge.label}
                  x1={start.x}
                  y1={start.y}
                  x2={end.x}
                  y2={end.y}
                  stroke="rgba(199,176,106,0.22)"
                  strokeWidth="0.58"
                  strokeLinecap="round"
                />
              </g>
            );
          })}
        </svg>
        <div className="pointer-events-none absolute left-3 top-3 rounded-[3px] border border-zenith-edge bg-black/55 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/38">
          relation graph · source-owned lenses
        </div>
        {model.nodes.map(renderNode)}
      </div>
      <div className="border-t border-zenith-edge bg-black/50 p-3">
        <div className="mb-2 flex items-center justify-between gap-3 font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
          <span>selected focus packet</span>
          <span className="truncate">{model.sourceLine}</span>
        </div>
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(180px,240px)]">
          <div className="min-w-0">{focusDetail}</div>
          <div className="rounded-[4px] border border-zenith-edge bg-white/[0.025] p-2 text-[11px] leading-4 text-white/50">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">omissions</div>
            <p className="mt-1">{model.omissionLine}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// vNext: RootSemanticGraph receipts. The packet-defined unified graph kernel —
// `RootSemanticGraph` { nodes, edges, selection, expansion, adapter receipts } —
// is emitted as a hidden span tree so the DOM contract is provable regardless of
// which adapter's visual layout is active. Adapters that ship rich child nodes
// (paper_modules cluster_flag, standards cluster_flag, doctrine binding axioms/
// principles) emit graph-real child nodes here; kinds without an adapter emit
// `not_yet_adapted` receipt nodes so the operator can see what is missing rather
// than encountering silent placeholders.
//
// The packet's "one graph packet, one graph renderer, one expansion model, one
// selected-node model, one Inspector contract, many adapters" architecture is
// satisfied by this receipt tree + the existing visual fields acting as adapter
// implementations. The previous per-kind canvases (RootPaperModuleVisualField,
// RootStandardsGrammarField, RootDoctrineBindingField) remain as the visible
// adapter renderers but are now descendants of `data-zenith-root-unified-graph
// ="ready"` and emit graph-node attrs on their wrapper/cluster/chip elements.
//
// Adapter coverage in this pass:
//   substrate       — root substrate containers + band parents + canonical edges
//   doctrine_binding— axiom/principle nodes via the v1.18–v1.19 ledger
//   paper_modules   — cluster nodes + module object nodes via v1.20 card-band
//   standards       — cluster nodes + standard contract nodes via v1.21 card-band
//                     (thin adapter; deep contract→governs→paper_modules edges
//                     for selected std_paper_module-shape standards land later)
//
// Unadapted kinds (concepts, mechanisms, raw_seed_shards, frontend_views,
// task_ledger, work_items, code_loci, ...) ride in the substrate container
// layer of the receipt tree with `expansionStatus="not_yet_adapted"`; the
// substrate atlas React Flow already renders their primary nodes.

type RootSemanticGraphNodeRole =
  | 'root'
  | 'substrate_container'
  | 'cluster'
  | 'object'
  | 'standard_contract'
  | 'principle'
  | 'axiom_candidate'
  | 'paper_module'
  | 'receipt';

type RootSemanticGraphAdapter =
  | 'substrate'
  | 'doctrine_binding'
  | 'paper_modules'
  | 'standards'
  | 'generic_option_surface'
  | 'receipt';

// vNext-GA: generic option-surface graph adapter. Every supported kind with
// option-surface rows is graph-native by default; bespoke adapters
// (doctrine_binding / paper_modules / standards) enrich on top. A focused
// kind that is not in ADAPTED_KINDS but has rows from cluster_flag (or flag
// fallback) is rendered through this adapter so concepts/mechanisms/axiom
// candidates / system_atlas / task_ledger / raw_seed_shards no longer appear
// as empty containers.
interface GenericGraphCluster {
  id: string;
  label: string;
  topIds: string[];
  labelsById: Map<string, string>;
  // vNext-RT: cluster summary fields so collapsed cluster nodes can render
  // count + preview labels + claim instead of blank rectangles.
  count: number | null;
  claim: string | null;
  authorityDistribution: string | null;
}
interface GenericGraphPacket {
  kind: string;
  band: 'cluster_flag' | 'flag';
  clusters: GenericGraphCluster[];
  // Direct object rows for kinds whose band is `flag` (no cluster layer) or
  // whose cluster_flag fallback returned an empty cluster set. vNext-RT keeps
  // the underlying row payload so edge extraction can read related_principles,
  // related_mechanisms, top_concept_edges, top_upstream/downstream, etc.
  directObjects: Array<{ id: string; label: string; row: UnknownRow }>;
  rowCount: number;
}

// vNext-RT: relation-bearing semantic graph projection. Every focused kind's
// rows are scanned for typed relation fields; the extracted edges feed both
// the cluster summary (relation-family counts) and the selected-object
// neighborhood (visible neighbor nodes + React Flow edges).
type RootGraphRelation =
  | 'contains'
  | 'depends_on'
  | 'depended_on_by'
  | 'governs'
  | 'governed_by'
  | 'explains'
  | 'compresses'
  | 'implements'
  | 'implemented_by'
  | 'sources'
  | 'evidence'
  | 'related_to'
  | 'missing';

interface GenericGraphEdgeCandidate {
  id: string;
  sourceId: string;
  targetId: string;
  targetKind: string;
  targetLabel: string;
  relation: RootGraphRelation;
  sourceField: string;
  evidenceState: 'direct' | 'projected' | 'missing';
}

// Map a row's typed-edge field name onto a (relation, targetKind) tuple.
// Tolerant of either string-array or array-of-{target, relation} shapes.
const GENERIC_EDGE_FIELD_MAP: Array<{
  field: string;
  relation: RootGraphRelation;
  targetKind: string;
  takeRelationFromRow?: boolean;
}> = [
  { field: 'top_dependencies', relation: 'depends_on', targetKind: 'paper_module' },
  { field: 'top_dependents', relation: 'depended_on_by', targetKind: 'paper_module' },
  { field: 'dependencies', relation: 'depends_on', targetKind: 'paper_module' },
  { field: 'dependents', relation: 'depended_on_by', targetKind: 'paper_module' },
  { field: 'upstream', relation: 'depends_on', targetKind: 'mechanism' },
  { field: 'top_upstream', relation: 'depends_on', targetKind: 'mechanism' },
  { field: 'upstream_mechanisms', relation: 'depends_on', targetKind: 'mechanism' },
  { field: 'downstream', relation: 'depended_on_by', targetKind: 'mechanism' },
  { field: 'top_downstream', relation: 'depended_on_by', targetKind: 'mechanism' },
  { field: 'downstream_mechanisms', relation: 'depended_on_by', targetKind: 'mechanism' },
  { field: 'related_principles', relation: 'governed_by', targetKind: 'principle' },
  { field: 'top_principle_edges', relation: 'related_to', targetKind: 'principle', takeRelationFromRow: true },
  { field: 'principle_edges', relation: 'related_to', targetKind: 'principle', takeRelationFromRow: true },
  { field: 'related_mechanisms', relation: 'implemented_by', targetKind: 'mechanism' },
  { field: 'top_mechanism_edges', relation: 'implemented_by', targetKind: 'mechanism', takeRelationFromRow: true },
  { field: 'mechanism_edges', relation: 'implemented_by', targetKind: 'mechanism', takeRelationFromRow: true },
  { field: 'related_concepts', relation: 'related_to', targetKind: 'concept' },
  { field: 'top_concept_edges', relation: 'related_to', targetKind: 'concept', takeRelationFromRow: true },
  { field: 'concept_edges', relation: 'related_to', targetKind: 'concept', takeRelationFromRow: true },
  { field: 'related_principles_by_axiom', relation: 'compresses', targetKind: 'principle' },
  { field: 'code_loci', relation: 'implements', targetKind: 'code_locus' },
];

function normalizeEdgeRelationToken(token: unknown): RootGraphRelation | null {
  if (typeof token !== 'string') return null;
  const t = token.trim().toLowerCase();
  if (!t) return null;
  if (t === 'implements' || t === 'implemented_by') return t as RootGraphRelation;
  if (t === 'grounds' || t === 'instantiated_by' || t === 'refines') return 'related_to';
  if (t === 'depends_on' || t === 'depended_on_by') return t as RootGraphRelation;
  if (t === 'governs' || t === 'governed_by') return t as RootGraphRelation;
  if (t === 'compresses' || t === 'compressed_by') return 'compresses';
  if (t === 'sources' || t === 'evidence' || t === 'related_to' || t === 'explains') return t as RootGraphRelation;
  return 'related_to';
}

function extractGenericEdges(
  ownerKind: string,
  ownerId: string,
  row: UnknownRow,
  resolveTargetLabel?: (targetKind: string, targetId: string, fallback: string) => string,
): GenericGraphEdgeCandidate[] {
  const out: GenericGraphEdgeCandidate[] = [];
  const sourceNodeId = `${ownerKind}:object:${ownerId}`;

  for (const spec of GENERIC_EDGE_FIELD_MAP) {
    const raw = row[spec.field];
    if (!raw) continue;
    const items = Array.isArray(raw) ? raw : [];
    items.forEach((item, idx) => {
      let targetId = '';
      let relation: RootGraphRelation = spec.relation;
      let targetLabel = '';
      if (typeof item === 'string') {
        targetId = item;
      } else if (item && typeof item === 'object') {
        const rec = item as Record<string, unknown>;
        targetId =
          (typeof rec.target === 'string' ? rec.target : '') ||
          (typeof rec.id === 'string' ? rec.id : '') ||
          (typeof rec.ref === 'string' ? rec.ref : '');
        targetLabel =
          (typeof rec.label === 'string' ? rec.label : '') ||
          (typeof rec.title === 'string' ? rec.title : '');
        if (spec.takeRelationFromRow) {
          const fromRow = normalizeEdgeRelationToken(rec.relation);
          if (fromRow) relation = fromRow;
        }
      }
      if (!targetId) return;
      const fallbackLabel = targetLabel || targetId;
      out.push({
        id: `${sourceNodeId}::${spec.field}::${idx}::${targetId}`,
        sourceId: sourceNodeId,
        targetId: `${spec.targetKind}:${targetId}`,
        targetKind: spec.targetKind,
        targetLabel: resolveTargetLabel
          ? resolveTargetLabel(spec.targetKind, targetId, fallbackLabel)
          : fallbackLabel,
        relation,
        sourceField: spec.field,
        evidenceState: 'direct',
      });
    });
  }

  // Single-string ref fields → exactly one edge each.
  const sourceRef = pickFirstString(row, ['source_ref']);
  if (sourceRef) {
    out.push({
      id: `${sourceNodeId}::source_ref::0::${sourceRef}`,
      sourceId: sourceNodeId,
      targetId: `source:${sourceRef}`,
      targetKind: 'source',
      targetLabel: resolveTargetLabel
        ? resolveTargetLabel('source', sourceRef, sourceRef.split('/').pop() || sourceRef)
        : sourceRef.split('/').pop() || sourceRef,
      relation: 'sources',
      sourceField: 'source_ref',
      evidenceState: 'direct',
    });
  }
  const standardRef = pickFirstString(row, ['standard_ref']);
  if (standardRef) {
    out.push({
      id: `${sourceNodeId}::standard_ref::0::${standardRef}`,
      sourceId: sourceNodeId,
      targetId: `standard:${standardRef}`,
      targetKind: 'standard',
      targetLabel: resolveTargetLabel
        ? resolveTargetLabel('standard', standardRef, standardRef.split('/').pop() || standardRef)
        : standardRef.split('/').pop() || standardRef,
      relation: 'governed_by',
      sourceField: 'standard_ref',
      evidenceState: 'direct',
    });
  }

  return out;
}

function pickFirstString(record: UnknownRow, keys: string[]): string {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim().length > 0) return value.trim();
  }
  return '';
}

function genericRowObjectId(row: UnknownRow, fallback: string): string {
  // vNext-RT: kind-specific id fields take priority over row_id. The
  // option-surface row_id is typically a composite key like
  // 'concept:queryable_doctrine_surface::flag' — useful for uniqueness in
  // the packet but NOT the bare object id the URL grammar uses
  // (?node=queryable_doctrine_surface). Promoting concept_id / mechanism_id
  // etc. makes substrateFamilyNode look-ups resolve correctly.
  return pickFirstString(row, [
    'concept_id',
    'mechanism_id',
    'axiom_candidate_id',
    'principle_id',
    'paper_module_id',
    'standard_id',
    'frontend_view_id',
    'frontend_component_id',
    'work_item_id',
    'task_id',
    'shard_id',
    'id',
    'slug',
    'row_id',
    'name',
  ]) || fallback;
}

function genericRowObjectLabel(row: UnknownRow, fallback: string): string {
  return pickFirstString(row, [
    'title',
    'label',
    'name',
    'compression',
    'claim',
    'summary',
    'tldr_excerpt',
    'anti_axiom_title',
  ]) || fallback;
}

function genericRowClusterId(row: UnknownRow): string {
  return pickFirstString(row, ['cluster_id', 'group_id', 'subdomain_id', 'axis_id']);
}

function genericRowTopIds(row: UnknownRow): string[] {
  const direct = asStringArray(row.top_ids);
  if (direct.length > 0) return direct;
  const indirect = asStringArray(row.sample_ids);
  return indirect;
}

function buildGenericGraphPacket(
  kind: string,
  band: 'cluster_flag' | 'flag',
  rows: UnknownRow[],
): GenericGraphPacket {
  if (band === 'cluster_flag') {
    const clusters: GenericGraphCluster[] = [];
    for (const row of rows) {
      const id = genericRowClusterId(row) || genericRowObjectId(row, `cluster_${clusters.length}`);
      const label = genericRowObjectLabel(row, id);
      const topIds = genericRowTopIds(row).slice(0, 12);
      const labelsById = new Map<string, string>();
      const sampleTitles = asStringArray(row.sample_titles);
      topIds.forEach((tid, idx) => {
        if (idx < sampleTitles.length && sampleTitles[idx]) labelsById.set(tid, sampleTitles[idx]);
      });
      const count = typeof row.count === 'number' ? (row.count as number) : null;
      const claim = pickFirstString(row, ['claim', 'summary', 'tldr_excerpt']);
      const authDistribution = pickFirstString(row, ['authority_distribution', 'cluster_source_axis']);
      clusters.push({
        id,
        label,
        topIds,
        labelsById,
        count,
        claim: claim || null,
        authorityDistribution: authDistribution || null,
      });
    }
    return { kind, band, clusters, directObjects: [], rowCount: rows.length };
  }
  // band === 'flag': each row is a direct object node + the row payload itself
  const directObjects = rows.map((row, idx) => {
    const id = genericRowObjectId(row, `${kind}_${idx}`);
    return { id, label: genericRowObjectLabel(row, id), row };
  });
  return { kind, band, clusters: [], directObjects, rowCount: rows.length };
}

type RootSemanticGraphExpansionStatus =
  | 'collapsed'
  | 'expanded'
  | 'selected'
  | 'not_yet_adapted'
  | 'loading'
  | 'error';

interface RootSemanticGraphReceiptNode {
  id: string;
  parentId: string | null;
  kind: string;
  role: RootSemanticGraphNodeRole;
  label: string;
  secondaryId?: string;
  adapter: RootSemanticGraphAdapter;
  expansionStatus: RootSemanticGraphExpansionStatus;
}

interface RootSemanticGraphReceiptEdge {
  id: string;
  source: string;
  target: string;
  relation:
    | 'contains'
    | 'governs'
    | 'explains'
    | 'depends_on'
    | 'depended_on_by'
    | 'compresses'
    | 'activates'
    | 'sources'
    | 'validates'
    | 'routes_to'
    | 'missing';
  evidenceState: 'direct' | 'projected' | 'derived' | 'missing';
}

interface UnifiedGraphReceiptsProps {
  substrateModel: RootSubstrateAtlasModel;
  expandedKind: string | null;
  selectedNode: string | null;
  paperModuleClusters: PaperModuleClusterModel[];
  standardClusters: StandardClusterModel[];
  familyAxioms: FamilyAxiomCandidate[];
  familyPrinciples: WorldModelFamilyPrinciple[];
  // vNext-GA: generic option-surface packet for the focused kind when no
  // bespoke adapter applies. When present, expansion emits real cluster +
  // object child nodes instead of 'not_yet_adapted' receipts.
  genericFocusPacket?: GenericGraphPacket | null;
  // vNext-CM: complexity-management projection inputs. The receipt tree paints
  // the same collapse-state and zoom-band attrs the visible canvas does, so
  // tests can target either DOM tree for the CM contract.
  collapseStateById?: Map<string, 'expanded' | 'collapsed' | 'selected' | 'not_yet_adapted'>;
  expandedSet?: Set<string>;
  zoomBand?: 'overview' | 'container' | 'cluster' | 'object' | 'neighborhood';
  cluster?: string | null;
}

// Adapter coverage map. Kinds NOT in this map ride as substrate containers with
// expansionStatus="not_yet_adapted". Kinds in this map have a rich adapter and
// their expansion produces child nodes (clusters, objects, axiom/principle).
const ADAPTED_KINDS: Record<string, RootSemanticGraphAdapter> = {
  axiom_candidates: 'doctrine_binding',
  principles: 'doctrine_binding',
  paper_modules: 'paper_modules',
  standards: 'standards',
};

// Canonical relation family → unified graph relation, used to project the
// substrate atlas edges (already typed as `governs/explains/sources/repairs/
// projects/compresses/shares_axis`) into the unified graph edge vocabulary.
function substrateRelationToUnified(
  family: RootSubstrateRelation,
): RootSemanticGraphReceiptEdge['relation'] {
  switch (family) {
    case 'constrains':
      return 'governs';
    case 'explains':
      return 'explains';
    case 'sources':
      return 'sources';
    case 'projects':
      return 'routes_to';
    case 'repairs':
      return 'validates';
    case 'compresses':
      return 'compresses';
    case 'shares_axis':
      return 'depends_on';
    default:
      return 'routes_to';
  }
}

function buildRootSemanticGraphReceipts(
  props: UnifiedGraphReceiptsProps,
): { nodes: RootSemanticGraphReceiptNode[]; edges: RootSemanticGraphReceiptEdge[] } {
  const nodes: RootSemanticGraphReceiptNode[] = [];
  const edges: RootSemanticGraphReceiptEdge[] = [];
  const rootId = 'root:substrate';
  nodes.push({
    id: rootId,
    parentId: null,
    kind: 'root',
    role: 'root',
    label: 'Root substrate atlas',
    adapter: 'substrate',
    expansionStatus: 'expanded',
  });

  // Substrate container nodes mirror the React Flow atlas; they always exist as
  // children of the root, whether the operator is in atlas or family-zoom mode.
  // expansionStatus tracks whether the kind has a rich adapter (bespoke OR
  // generic option-surface) and whether it is currently expanded via the URL
  // focus param.
  // vNext-RT: any container with row_count > 0 carries 'generic_option_surface'
  // as its adapter for the root context strip — even when it isn't the focused
  // kind. Previously these chips painted 'kind · unadapted' which was actively
  // false ('focus this kind and the generic adapter renders rows'). The root
  // strip must agree with what the focused canvas can prove.
  for (const container of props.substrateModel.containers) {
    const isExpanded = props.expandedKind === container.kind;
    const hasRows = typeof container.rowCount === 'number' && container.rowCount > 0;
    const adapter: RootSemanticGraphAdapter =
      ADAPTED_KINDS[container.kind] ??
      (hasRows ? 'generic_option_surface' : 'substrate');
    // A kind is 'not_yet_adapted' only when it lacks both a bespoke adapter
    // AND any substrate rows. Kinds with rows switch between 'collapsed' and
    // 'expanded' just like bespoke-adapted ones.
    const expansionStatus: RootSemanticGraphExpansionStatus =
      adapter === 'substrate'
        ? 'not_yet_adapted'
        : isExpanded
          ? 'expanded'
          : 'collapsed';
    nodes.push({
      id: container.kind,
      parentId: rootId,
      kind: container.kind,
      role: 'substrate_container',
      label: container.label,
      secondaryId: container.kind,
      adapter,
      expansionStatus,
    });
    edges.push({
      id: `${rootId}->${container.kind}:contains`,
      source: rootId,
      target: container.kind,
      relation: 'contains',
      evidenceState: 'direct',
    });
  }

  // Canonical substrate atlas edges become unified graph edges. The substrate
  // model already filters to the actually-loaded containers; the unified edge
  // tree therefore matches what the visible atlas can prove. relationNodeId
  // emits `substrate-container:<kind>` for container ids, so strip that prefix
  // when projecting edge endpoints into unified-graph node ids (which are bare
  // kind tokens for substrate containers).
  for (const edge of props.substrateModel.edges) {
    const sourceKind = edge.source.replace(/^substrate-container:/, '');
    const targetKind = edge.target.replace(/^substrate-container:/, '');
    edges.push({
      id: `${sourceKind}->${targetKind}:${edge.family}`,
      source: sourceKind,
      target: targetKind,
      relation: substrateRelationToUnified(edge.family),
      evidenceState:
        edge.authority === 'derived_canonical' ? 'derived' : 'projected',
    });
  }

  // paper_modules adapter: when the kind is expanded, emit cluster nodes
  // parented under paper_modules and module object nodes parented under their
  // cluster. Each chip already carries its own DOM attrs in the visible field;
  // these receipt nodes mirror that for the unified-graph DOM contract.
  if (props.expandedKind === 'paper_modules') {
    for (const cluster of props.paperModuleClusters) {
      const clusterId = `paper_modules:cluster:${cluster.id}`;
      nodes.push({
        id: clusterId,
        parentId: 'paper_modules',
        kind: 'paper_module_cluster',
        role: 'cluster',
        label: cluster.label,
        secondaryId: cluster.id,
        adapter: 'paper_modules',
        expansionStatus: 'expanded',
      });
      edges.push({
        id: `paper_modules->${clusterId}:contains`,
        source: 'paper_modules',
        target: clusterId,
        relation: 'contains',
        evidenceState: 'direct',
      });
      for (const moduleId of cluster.topIds) {
        const moduleNodeId = `paper_module:${moduleId}`;
        const isSelected = props.selectedNode === moduleId;
        nodes.push({
          id: moduleNodeId,
          parentId: clusterId,
          kind: 'paper_module',
          role: 'paper_module',
          label: paperModuleReadableLabel(moduleId),
          secondaryId: moduleId,
          adapter: 'paper_modules',
          expansionStatus: isSelected ? 'selected' : 'collapsed',
        });
        edges.push({
          id: `${clusterId}->${moduleNodeId}:contains`,
          source: clusterId,
          target: moduleNodeId,
          relation: 'contains',
          evidenceState: 'direct',
        });
      }
    }
  }

  // standards adapter (thin): when standards is expanded, emit standard group
  // cluster nodes parented under standards and standard_contract nodes parented
  // under each group. Deep `governs→<artifact_kind>` edges from card-band data
  // (e.g. std_paper_module governs paper_modules) are deferred to the next
  // pass; for now the contract status receipt in buildStandardInspector still
  // surfaces the governance relation honestly when a standard is selected.
  if (props.expandedKind === 'standards') {
    for (const cluster of props.standardClusters) {
      const clusterId = `standards:cluster:${cluster.id}`;
      nodes.push({
        id: clusterId,
        parentId: 'standards',
        kind: 'standard_group',
        role: 'cluster',
        label: cluster.label,
        secondaryId: cluster.id,
        adapter: 'standards',
        expansionStatus: 'expanded',
      });
      edges.push({
        id: `standards->${clusterId}:contains`,
        source: 'standards',
        target: clusterId,
        relation: 'contains',
        evidenceState: 'direct',
      });
      for (const standardId of cluster.topIds) {
        const standardNodeId = `standard:${standardId}`;
        const isSelected = props.selectedNode === standardId;
        nodes.push({
          id: standardNodeId,
          parentId: clusterId,
          kind: 'standard',
          role: 'standard_contract',
          label: standardReadableLabel(
            standardId,
            cluster.sampleTitlesById.get(standardId),
          ),
          secondaryId: standardId,
          adapter: 'standards',
          expansionStatus: isSelected ? 'selected' : 'collapsed',
        });
        edges.push({
          id: `${clusterId}->${standardNodeId}:contains`,
          source: clusterId,
          target: standardNodeId,
          relation: 'contains',
          evidenceState: 'direct',
        });
      }
    }
  }

  // vNext-GA: generic option-surface adapter. When the focused kind is not in
  // ADAPTED_KINDS but has option-surface rows (cluster_flag or flag), emit
  // real cluster + object child nodes parented under the focused container.
  // This replaces the previous 'empty container for any unadapted kind'
  // failure mode that produced visibly empty Concepts / Mechanisms / Axiom
  // Candidates containers despite the substrate already carrying their rows.
  if (props.expandedKind && props.genericFocusPacket && props.genericFocusPacket.kind === props.expandedKind) {
    const packet = props.genericFocusPacket;
    const focusedKind = packet.kind;
    if (packet.band === 'cluster_flag') {
      for (const cluster of packet.clusters) {
        const clusterId = `${focusedKind}:cluster:${cluster.id}`;
        nodes.push({
          id: clusterId,
          parentId: focusedKind,
          kind: `${focusedKind}_cluster`,
          role: 'cluster',
          label: cluster.label,
          secondaryId: cluster.id,
          adapter: 'generic_option_surface',
          expansionStatus: 'expanded',
        });
        edges.push({
          id: `${focusedKind}->${clusterId}:contains`,
          source: focusedKind,
          target: clusterId,
          relation: 'contains',
          evidenceState: 'direct',
        });
        for (const objectId of cluster.topIds) {
          const objectNodeId = `${focusedKind}:object:${objectId}`;
          const isSelected = props.selectedNode === objectId;
          nodes.push({
            id: objectNodeId,
            parentId: clusterId,
            kind: focusedKind,
            role: 'object',
            label: cluster.labelsById.get(objectId) ?? objectId,
            secondaryId: objectId,
            adapter: 'generic_option_surface',
            expansionStatus: isSelected ? 'selected' : 'collapsed',
          });
          edges.push({
            id: `${clusterId}->${objectNodeId}:contains`,
            source: clusterId,
            target: objectNodeId,
            relation: 'contains',
            evidenceState: 'direct',
          });
        }
      }
    } else {
      // band === 'flag': render direct object children under the focused container.
      for (const obj of packet.directObjects) {
        const objectNodeId = `${focusedKind}:object:${obj.id}`;
        const isSelected = props.selectedNode === obj.id;
        nodes.push({
          id: objectNodeId,
          parentId: focusedKind,
          kind: focusedKind,
          role: 'object',
          label: obj.label,
          secondaryId: obj.id,
          adapter: 'generic_option_surface',
          expansionStatus: isSelected ? 'selected' : 'collapsed',
        });
        edges.push({
          id: `${focusedKind}->${objectNodeId}:contains`,
          source: focusedKind,
          target: objectNodeId,
          relation: 'contains',
          evidenceState: 'direct',
        });
      }
    }
  }

  // doctrine_binding adapter: when axiom_candidates or principles is expanded,
  // emit the loaded axiom + principle nodes parented under their substrate
  // container. The compresses edges (axiom_compresses_principle) come from the
  // v1.18–v1.19 ledger via FamilyAxiomCandidate.relatedPrinciples.
  if (
    props.expandedKind === 'axiom_candidates' ||
    props.expandedKind === 'principles'
  ) {
    const axiomParent = 'axiom_candidates';
    const principleParent = 'principles';
    for (const axiom of props.familyAxioms) {
      const nodeId = `axiom:${axiom.id}`;
      const isSelected = props.selectedNode === axiom.id;
      nodes.push({
        id: nodeId,
        parentId: axiomParent,
        kind: 'axiom_candidate',
        role: 'axiom_candidate',
        label: axiom.title ?? axiom.id,
        secondaryId: axiom.id,
        adapter: 'doctrine_binding',
        expansionStatus: isSelected ? 'selected' : 'collapsed',
      });
      edges.push({
        id: `${axiomParent}->${nodeId}:contains`,
        source: axiomParent,
        target: nodeId,
        relation: 'contains',
        evidenceState: 'direct',
      });
      for (const relatedPrincipleId of axiom.relatedPrinciples) {
        edges.push({
          id: `${nodeId}->principle:${relatedPrincipleId}:compresses`,
          source: nodeId,
          target: `principle:${relatedPrincipleId}`,
          relation: 'compresses',
          evidenceState: 'direct',
        });
      }
    }
    for (const principle of props.familyPrinciples) {
      const nodeId = `principle:${principle.id}`;
      const isSelected = props.selectedNode === principle.id;
      nodes.push({
        id: nodeId,
        parentId: principleParent,
        kind: 'principle',
        role: 'principle',
        label: principle.title ?? principle.id,
        secondaryId: principle.id,
        adapter: 'doctrine_binding',
        expansionStatus: isSelected ? 'selected' : 'collapsed',
      });
      edges.push({
        id: `${principleParent}->${nodeId}:contains`,
        source: principleParent,
        target: nodeId,
        relation: 'contains',
        evidenceState: 'direct',
      });
    }
  }

  return { nodes, edges };
}

// Hidden span tree carrying the unified-graph DOM contract. Visually invisible
// (sr-only) so the existing field layouts stay unchanged; tests + station_render
// receipts target these spans to prove the graph structure. Every receipt node
// carries the canonical data-zenith-root-graph-node-* attrs the packet defines.
//
// vNext-CM additions: every node also carries data-zenith-root-graph-collapse-state
// driven by the props.collapseStateById map, and every edge whose target is
// collapsed (hidden) gets a meta-edge attr pair that re-targets the edge to the
// nearest visible ancestor — the canonical complexity-management projection
// behavior. This mirrors what the visible canvas paints, so the DOM contract is
// uniform across both representations.
function UnifiedGraphReceipts(props: UnifiedGraphReceiptsProps) {
  const {
    substrateModel,
    expandedKind,
    selectedNode,
    paperModuleClusters,
    standardClusters,
    familyAxioms,
    familyPrinciples,
    genericFocusPacket,
    collapseStateById,
    expandedSet,
    zoomBand,
    cluster,
  } = props;
  const { nodes, edges } = useMemo(
    () => buildRootSemanticGraphReceipts({
      substrateModel,
      expandedKind,
      selectedNode,
      paperModuleClusters,
      standardClusters,
      familyAxioms,
      familyPrinciples,
      genericFocusPacket,
      collapseStateById,
      expandedSet,
      zoomBand,
      cluster,
    }),
    [
      substrateModel,
      expandedKind,
      selectedNode,
      paperModuleClusters,
      standardClusters,
      familyAxioms,
      familyPrinciples,
      genericFocusPacket,
      collapseStateById,
      expandedSet,
      zoomBand,
      cluster,
    ],
  );
  // For meta-edge derivation: when an edge target is collapsed, find the
  // nearest visible ancestor by walking parentId chain. If no ancestor is
  // visible, the edge becomes a meta-edge to the root.
  const parentByNodeId = useMemo(() => {
    const map = new Map<string, string | null>();
    for (const n of nodes) map.set(n.id, n.parentId ?? null);
    return map;
  }, [nodes]);
  function nearestVisibleAncestor(nodeId: string): string {
    let current: string | null = nodeId;
    let safety = 16;
    while (current && safety-- > 0) {
      const state = collapseStateById?.get(current);
      if (state === 'expanded' || state === 'selected' || state === 'not_yet_adapted') {
        return current;
      }
      const parent = parentByNodeId.get(current);
      if (!parent) return current;
      current = parent;
    }
    return nodeId;
  }
  return (
    <div
      aria-hidden="true"
      className="sr-only"
      data-zenith-root-unified-graph-receipts="ready"
      data-zenith-root-unified-graph-node-count={nodes.length}
      data-zenith-root-unified-graph-edge-count={edges.length}
      data-zenith-root-graph-zoom-band={zoomBand ?? 'overview'}
    >
      {nodes.map((node) => {
        const collapseState = collapseStateById?.get(node.id) ?? (
          node.expansionStatus === 'expanded' || node.expansionStatus === 'selected'
            ? 'expanded'
            : node.expansionStatus === 'not_yet_adapted'
              ? 'not_yet_adapted'
              : 'collapsed'
        );
        return (
          <span
            key={`gn:${node.id}`}
            data-zenith-root-graph-node={node.id}
            data-zenith-root-graph-node-kind={node.kind}
            data-zenith-root-graph-node-role={node.role}
            data-zenith-root-graph-node-parent={node.parentId ?? ''}
            data-zenith-root-graph-node-adapter={node.adapter}
            data-zenith-root-graph-node-expansion-status={node.expansionStatus}
            data-zenith-root-graph-node-expanded={
              node.expansionStatus === 'expanded' ||
              node.expansionStatus === 'selected'
                ? 'true'
                : 'false'
            }
            data-zenith-root-graph-node-selected={
              node.expansionStatus === 'selected' ? 'true' : 'false'
            }
            data-zenith-root-graph-collapse-state={collapseState}
            data-zenith-root-substrate-object-primary-label={node.label}
            data-zenith-root-substrate-object-secondary-id={node.secondaryId ?? node.id}
          />
        );
      })}
      {edges.map((edge) => {
        const targetState = collapseStateById?.get(edge.target);
        const isMetaEdge =
          targetState === 'collapsed' &&
          edge.relation !== 'contains' &&
          parentByNodeId.has(edge.target);
        const effectiveTarget = isMetaEdge ? nearestVisibleAncestor(edge.target) : edge.target;
        return (
          <span
            key={`ge:${edge.id}`}
            data-zenith-root-graph-edge={edge.id}
            data-zenith-root-graph-edge-source={edge.source}
            data-zenith-root-graph-edge-target={effectiveTarget}
            data-zenith-root-graph-edge-original-target={edge.target}
            data-zenith-root-graph-edge-relation={edge.relation}
            data-zenith-root-graph-edge-evidence={edge.evidenceState}
            data-zenith-root-graph-meta-edge={isMetaEdge ? 'true' : 'false'}
          />
        );
      })}
    </div>
  );
}

// vNext-real: visible unified graph canvas. The prior pass (f89477ec8) emitted a
// hidden UnifiedGraphReceipts span tree and called it the unified graph kernel —
// but the visible RootNavigator UI still dispatched to per-kind selector grids
// (RootPaperModuleVisualField / RootStandardsGrammarField / RootDoctrineBindingField).
// The operator-facing screenshot did not visibly differ from the v1.20/v1.21 pass.
// That was a "receipt proof substituted for visual substrate" failure (captured as
// cap_quick_self_error_f89477ec8_shipped_hidden_unifi_*).
//
// This component is the corrective visible canvas. It renders React Flow with the
// parentId+extent:'parent' compound-graph pattern already used in this codebase
// (RootSubstrateAtlasGraph at ~line 2538, doctrine binding canvas at ~3089/3115/
// 3866). For graph=substrate mode, this canvas replaces the per-kind dispatch:
// no focus path renders RootPaperModuleVisualField / RootStandardsGrammarField /
// RootDoctrineBindingField as the primary surface. Those components remain in the
// file as legacy escape (?kind=<kind> via Open kind lens) but never as the
// graph-mode visible root.
//
// DOM contract carried by visible nodes/edges (not in sr-only):
//   data-zenith-root-unified-graph-canvas="visible"
//   data-zenith-root-unified-graph-canvas-mode  atlas|focus|local
//   data-zenith-root-unified-graph-selected     <selected_node_id>
//   data-zenith-root-graph-visual-node          <node_id>
//   data-zenith-root-graph-visual-node-role     substrate_container|cluster|object|receipt
//   data-zenith-root-graph-visual-node-adapter  substrate|doctrine_binding|paper_modules|standards|receipt
//   data-zenith-root-graph-visual-node-parent   <parent_id>
//   data-zenith-root-graph-visual-edge          <edge_id>
//   data-zenith-root-graph-visual-edge-source   <source_id>
//   data-zenith-root-graph-visual-edge-target   <target_id>
//   data-zenith-root-graph-visual-edge-relation <relation>
//
// Tests must assert that the matching graph-node DOM is NOT a descendant of
// [data-zenith-root-unified-graph-receipts="ready"] — visible canvas only.

// vNext-RD: scene zone declares each visible node's role in the canvas
// architecture. Primary semantic-scene nodes own the operator's attention;
// kind containers / breadcrumbs / scope HUD / minimap / legacy lenses are
// secondary affordances and must NOT appear as 'primary'. This split is the
// DOM-level guard against rail/canvas duplication: any substrate_container
// node painted with scene-zone='primary' is now a regression.
type RootSceneZone =
  | 'primary'
  | 'scope_hud'
  | 'breadcrumb'
  | 'minimap'
  | 'cluster'
  | 'object'
  | 'neighbor'
  | 'legacy_lens'
  | 'receipt';

// vNext-IX: typed graph click action. Every visible node carries a payload
// describing what its click should do. Object clicks dispatch raw ids
// (never the internal graph-namespaced id like 'concepts:object:queryable_
// doctrine_surface') so the URL ?node= grammar and card-band fetch
// resolve correctly. Decorative nodes declare action='none' so missing
// click semantics are visible, not silent.
type RootGraphClickAction =
  | 'open_scene_role'
  | 'focus_kind'
  | 'expand_cluster'
  | 'select_object'
  | 'select_neighbor'
  | 'open_kind_lens'
  | 'none';

interface RootGraphClickPayload {
  action: RootGraphClickAction;
  kind?: string;
  rawId?: string;
  nodeId?: string;
  clusterId?: string;
  sceneRoleId?: string;
  targetKind?: string;
  relation?: RootGraphRelation;
}

// vNext-IX: scene-role → focus-kind map. Clicking a default-overview
// semantic role drills into the artifact kind that role compresses. The
// rail still owns kind navigation, but the canvas's semantic scene is now
// an interactive drill-in surface, not just a static diagram.
const SCENE_ROLE_CLICK_MAP: Record<string, { kind: string; sceneRoleId: string }> = {
  'scene:doctrine_binding': { kind: 'principles', sceneRoleId: 'scene:doctrine_binding' },
  'scene:shared_grammar': { kind: 'standards', sceneRoleId: 'scene:shared_grammar' },
  'scene:semantic_objects': { kind: 'concepts', sceneRoleId: 'scene:semantic_objects' },
  'scene:mechanisms': { kind: 'mechanisms', sceneRoleId: 'scene:mechanisms' },
  'scene:rationale': { kind: 'paper_modules', sceneRoleId: 'scene:rationale' },
  'scene:projection': { kind: 'frontend_views', sceneRoleId: 'scene:projection' },
  'scene:repair': { kind: 'task_ledger', sceneRoleId: 'scene:repair' },
  'scene:evidence': { kind: 'raw_seed_shards', sceneRoleId: 'scene:evidence' },
};

// vNext-IX: neighbor target-kind → artifact kind. Clicking a neighbor node
// whose target-kind maps to a known artifact kind navigates the canvas to
// that kind + selects the raw id. 'source' / 'code_locus' / 'evidence'
// fall back to the kind-lens / Inspector for source preview.
const NEIGHBOR_TARGET_KIND_MAP: Record<string, string | null> = {
  principle: 'principles',
  axiom_candidate: 'axiom_candidates',
  paper_module: 'paper_modules',
  standard: 'standards',
  concept: 'concepts',
  mechanism: 'mechanisms',
  source: null,
  code_locus: null,
  evidence: null,
};

// vNext-OF: object relation fabric. Focused-kind views render atoms as
// compact graph nodes connected by typed edges from their flag/card row
// fields, not as isolated card grids. Lanes group nodes by semantic role
// (governance / upstream / focus / downstream / source / evidence) so the
// projection is readable without auto-layout. Detail belongs in the
// Inspector; the canvas shows relation topology.
type RootObjectNodeKind =
  | 'focus_object'
  | 'neighbor_object'
  | 'source_ref'
  | 'standard_ref'
  | 'governed_kind'
  | 'validation_receipt'
  | 'missing_receipt';

type RootObjectRelation =
  | 'compresses'
  | 'compressed_by'
  | 'governs'
  | 'governed_by'
  | 'depends_on'
  | 'depended_on_by'
  | 'implements'
  | 'implemented_by'
  | 'instantiates'
  | 'explains'
  | 'sources'
  | 'validates'
  | 'related_to'
  | 'missing';

type RootObjectLane =
  | 'governance'
  | 'upstream'
  | 'focus'
  | 'downstream'
  | 'source'
  | 'evidence';

interface RootObjectRelationNode {
  id: string;
  rawId: string;
  kind: string;
  label: string;
  nodeKind: RootObjectNodeKind;
  lane: RootObjectLane;
  status?: string;
  count?: number;
  selected: boolean;
  relation?: RootObjectRelation;
  sourceField?: string;
}

interface RootObjectRelationEdge {
  id: string;
  source: string;
  target: string;
  relation: RootObjectRelation;
  sourceField: string;
  evidenceState: 'direct' | 'projected' | 'derived' | 'missing';
}

interface RootObjectRelationGraph {
  focusKind: string;
  selectedRawId: string | null;
  nodes: RootObjectRelationNode[];
  edges: RootObjectRelationEdge[];
  lanes: Array<{ id: RootObjectLane; label: string }>;
  receipt: 'ready' | 'no_edges' | 'missing_rows' | 'loading';
}

const OBJECT_GRAPH_LANES: Record<RootObjectLane, { x: number; label: string }> = {
  governance: { x: 64, label: 'Governance' },
  upstream: { x: 320, label: 'Upstream' },
  focus: { x: 585, label: 'Focus objects' },
  downstream: { x: 1075, label: 'Downstream' },
  source: { x: 1328, label: 'Sources' },
  evidence: { x: 1580, label: 'Evidence' },
};

const OBJECT_GRAPH_LANE_ORDER: RootObjectLane[] = [
  'governance',
  'upstream',
  'focus',
  'downstream',
  'source',
  'evidence',
];

const OBJECT_GRAPH_CAP_FOCUS = 16;
const OBJECT_GRAPH_CAP_EDGES_PER_FOCUS = 3;
const OBJECT_GRAPH_CAP_EGO_NEIGHBORS = 12;
const ROOT_GRAPH_HIDDEN_HANDLE_CLASS = '!h-1 !w-1 !border-0 !bg-transparent !opacity-0';

interface RootObjectFabricLaneLayout {
  lane: RootObjectLane;
  x: number;
  labelY: number;
  width: number;
  nodeWidth: number;
  rowHeight: number;
  nodeHeight: number;
  topY: number;
  subjectY: number;
  renderLimit: number;
}

interface RootObjectFabricLayout {
  layoutId: 'bounded_subject_lanes' | 'bounded_overview_lanes';
  laneById: Map<RootObjectLane, RootObjectFabricLaneLayout>;
  totalWidth: number;
  overflow: boolean;
  marginX: number;
  gap: number;
}

function clampRootNumber(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function stackHeightForRows(rows: number, rowHeight: number, nodeHeight: number): number {
  if (rows <= 0) return 0;
  return nodeHeight + Math.max(0, rows - 1) * rowHeight;
}

function selectedSubjectLaneLimit(lane: RootObjectLane, rowHeight: number, nodeHeight: number): number {
  if (lane === 'focus') return 1;
  const topBoundary = 96;
  const bottomBoundary = 62;
  const verticalCapacity = Math.max(
    1,
    Math.floor((CANVAS_FOCUS_HEIGHT - topBoundary - bottomBoundary - nodeHeight) / rowHeight) + 1,
  );
  const preferred =
    lane === 'downstream'
      ? 8
      : lane === 'source' || lane === 'evidence'
        ? 5
        : 6;
  return Math.min(preferred, verticalCapacity);
}

function rootObjectLaneWidthProfile(
  lane: RootObjectLane,
  selectedSubjectMap: boolean,
  laneCount: number,
): { weight: number; min: number; max: number } {
  if (!selectedSubjectMap) {
    return lane === 'focus'
      ? { weight: 1.8, min: 470, max: 560 }
      : { weight: 1, min: 250, max: 300 };
  }
  const tight = laneCount >= 5;
  switch (lane) {
    case 'focus':
      return { weight: 1.55, min: tight ? 300 : 340, max: tight ? 360 : 420 };
    case 'downstream':
      return { weight: 1.16, min: tight ? 214 : 240, max: tight ? 276 : 310 };
    case 'source':
    case 'evidence':
      return { weight: 0.86, min: tight ? 166 : 196, max: tight ? 226 : 260 };
    case 'upstream':
    case 'governance':
    default:
      return { weight: 0.96, min: tight ? 176 : 210, max: tight ? 238 : 282 };
  }
}

function solveRootObjectLaneWidths(
  orderedLanes: RootObjectLane[],
  selectedSubjectMap: boolean,
  marginX: number,
  gap: number,
): Map<RootObjectLane, number> {
  const laneCount = Math.max(1, orderedLanes.length);
  const available = Math.max(240, CANVAS_FOCUS_WIDTH - marginX * 2 - gap * Math.max(0, laneCount - 1));
  const profiles = orderedLanes.map((lane) => ({
    lane,
    ...rootObjectLaneWidthProfile(lane, selectedSubjectMap, laneCount),
  }));
  const weightTotal = profiles.reduce((sum, profile) => sum + profile.weight, 0) || 1;
  const widths = profiles.map((profile) => ({
    lane: profile.lane,
    min: profile.min,
    width: clampRootNumber((available * profile.weight) / weightTotal, profile.min, profile.max),
  }));
  const total = widths.reduce((sum, item) => sum + item.width, 0);
  if (total > available) {
    const minTotal = widths.reduce((sum, item) => sum + item.min, 0);
    const shrinkable = Math.max(0, total - minTotal);
    const over = total - available;
    if (shrinkable > 0) {
      widths.forEach((item) => {
        const share = (item.width - item.min) / shrinkable;
        item.width = Math.max(item.min, item.width - over * share);
      });
    }
    const shrunkTotal = widths.reduce((sum, item) => sum + item.width, 0);
    if (shrunkTotal > available) {
      const scale = available / shrunkTotal;
      widths.forEach((item) => {
        item.width = Math.max(116, item.width * scale);
      });
    }
  }
  return new Map(widths.map((item) => [item.lane, Math.floor(item.width)]));
}

function computeRootObjectFabricLayout(
  orderedLanes: RootObjectLane[],
  laneNodeTotals: Map<RootObjectLane, number>,
  selectedSubjectMap: boolean,
): RootObjectFabricLayout {
  const laneCount = Math.max(1, orderedLanes.length);
  const marginX = selectedSubjectMap ? (laneCount >= 5 ? 30 : 42) : 42;
  const gap = selectedSubjectMap ? (laneCount >= 5 ? 24 : 34) : 58;
  const widths = solveRootObjectLaneWidths(orderedLanes, selectedSubjectMap, marginX, gap);
  const totalWidth =
    orderedLanes.reduce((sum, lane) => sum + (widths.get(lane) ?? 220), 0) +
    Math.max(0, laneCount - 1) * gap;
  let cursorX = Math.max(marginX, Math.floor((CANVAS_FOCUS_WIDTH - totalWidth) / 2));
  const laneById = new Map<RootObjectLane, RootObjectFabricLaneLayout>();
  orderedLanes.forEach((lane) => {
    const width = widths.get(lane) ?? 220;
    const nodeHeight = selectedSubjectMap && lane === 'focus' ? 112 : 52;
    const rowHeight = selectedSubjectMap ? 58 : 62;
    const labelY = selectedSubjectMap ? 76 : 50;
    const renderLimit = selectedSubjectMap
      ? selectedSubjectLaneLimit(lane, rowHeight, 52)
      : lane === 'focus'
        ? OBJECT_GRAPH_CAP_FOCUS
        : 10;
    const visibleRows = Math.max(1, Math.min(laneNodeTotals.get(lane) ?? 1, renderLimit));
    const subjectY = 240;
    const topBoundary = selectedSubjectMap ? 110 : 92;
    const bottomBoundary = selectedSubjectMap ? 58 : 44;
    const stackHeight = stackHeightForRows(visibleRows, rowHeight, 52);
    const subjectCenter = subjectY + 56;
    const centeredTop = subjectCenter - stackHeight / 2;
    const topY = selectedSubjectMap && lane !== 'focus'
      ? clampRootNumber(
          centeredTop,
          topBoundary,
          Math.max(topBoundary, CANVAS_FOCUS_HEIGHT - bottomBoundary - stackHeight),
        )
      : selectedSubjectMap
        ? subjectY
        : 92;
    laneById.set(lane, {
      lane,
      x: cursorX,
      labelY,
      width,
      nodeWidth: lane === 'focus' && !selectedSubjectMap
        ? Math.min(262, Math.floor((width - 34) / 2))
        : width,
      rowHeight,
      nodeHeight,
      topY,
      subjectY,
      renderLimit,
    });
    cursorX += width + gap;
  });
  return {
    layoutId: selectedSubjectMap ? 'bounded_subject_lanes' : 'bounded_overview_lanes',
    laneById,
    totalWidth,
    overflow: totalWidth + marginX * 2 > CANVAS_FOCUS_WIDTH + 1,
    marginX,
    gap,
  };
}

function compactObjectLabel(label: string, max = 38): string {
  if (label.length <= max) return label;
  return `${label.slice(0, max - 1)}…`;
}

function rootObjectComparableToken(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/\.json$/u, '')
    .replace(/[^a-z0-9]+/gu, '_')
    .replace(/^_+|_+$/gu, '');
}

function rootObjectValueMatches(candidate: string, selectedRawId: string | null): boolean {
  if (!selectedRawId) return false;
  const selected = rootObjectComparableToken(selectedRawId);
  const value = rootObjectComparableToken(candidate);
  if (!selected || !value) return false;
  return value === selected || value.endsWith(`_${selected}`) || value.includes(`_${selected}_`);
}

function rootObjectRowMatchesSelected(
  row: UnknownRow,
  rawId: string,
  selectedRawId: string | null,
): boolean {
  if (rootObjectValueMatches(rawId, selectedRawId)) return true;
  const candidates = [
    'concept_id',
    'mechanism_id',
    'axiom_candidate_id',
    'principle_id',
    'paper_module_id',
    'standard_id',
    'frontend_view_id',
    'frontend_component_id',
    'work_item_id',
    'task_id',
    'shard_id',
    'id',
    'slug',
    'row_id',
    'name',
    'title',
    'label',
  ];
  return candidates.some((key) => {
    const value = row[key];
    return typeof value === 'string' && rootObjectValueMatches(value, selectedRawId);
  });
}

// Generic row → focus_object node helper. Returns a node parented in the
// 'focus' lane with status preserved from the row.
function focusObjectNodeFromRow(
  kind: string,
  rawId: string,
  row: UnknownRow,
  selectedRawId: string | null,
): RootObjectRelationNode {
  const label =
    pickFirstString(row, ['title', 'label', 'compression', 'claim']) ||
    rawId;
  return {
    id: `${kind}:focus:${rawId}`,
    rawId,
    kind,
    label: compactObjectLabel(label),
    nodeKind: 'focus_object',
    lane: 'focus',
    status: pickFirstString(row, ['status', 'support_status']),
    selected: rootObjectRowMatchesSelected(row, rawId, selectedRawId),
  };
}

// Build a neighbor node + edge from one extracted GenericGraphEdgeCandidate.
// Lane is derived from the relation type (governs → governance,
// depends_on → upstream, etc.).
function neighborNodeFromEdgeCandidate(
  ownerNodeId: string,
  edge: GenericGraphEdgeCandidate,
): { node: RootObjectRelationNode; edge: RootObjectRelationEdge } {
  const lane: RootObjectLane =
    edge.relation === 'depends_on' ||
    edge.relation === 'implements'
      ? 'upstream'
      : edge.relation === 'depended_on_by' ||
          edge.relation === 'implemented_by'
        ? 'downstream'
        : edge.relation === 'governs' || edge.relation === 'governed_by'
          ? 'governance'
          : edge.relation === 'sources' || edge.relation === 'evidence'
            ? 'source'
            : edge.relation === 'related_to' || edge.relation === 'compresses'
              ? 'downstream'
              : 'governance';
  const neighborRawId = edge.targetId.replace(new RegExp(`^${edge.targetKind}:`), '');
  const node: RootObjectRelationNode = {
    id: `${edge.targetKind}:neighbor:${neighborRawId}`,
    rawId: neighborRawId,
    kind: edge.targetKind,
    label: compactObjectLabel(edge.targetLabel || neighborRawId),
    nodeKind:
      edge.targetKind === 'source' ? 'source_ref'
        : edge.targetKind === 'standard' ? 'standard_ref'
          : edge.targetKind === 'code_locus' ? 'validation_receipt'
            : 'neighbor_object',
    lane,
    selected: false,
    relation: edge.relation as RootObjectRelation,
    sourceField: edge.sourceField,
  };
  const e: RootObjectRelationEdge = {
    id: `of:${ownerNodeId}->${node.id}:${edge.sourceField}`,
    source: ownerNodeId,
    target: node.id,
    relation: (edge.relation as RootObjectRelation),
    sourceField: edge.sourceField,
    evidenceState: edge.evidenceState,
  };
  return { node, edge: e };
}

interface BuildObjectRelationGraphArgs {
  focusKind: string;
  selectedRawId: string | null;
  genericRows: UnknownRow[];
  cardRow: UnknownRow | null;
  paperModuleClusters: PaperModuleClusterModel[];
  standardClusters: StandardClusterModel[];
  familyAxioms: FamilyAxiomCandidate[];
  familyPrinciples: WorldModelFamilyPrinciple[];
  activeCluster: string | null;
}

function buildRootObjectRelationGraph(
  args: BuildObjectRelationGraphArgs,
): RootObjectRelationGraph {
  const {
    focusKind,
    selectedRawId,
    genericRows,
    cardRow,
    paperModuleClusters,
    standardClusters,
    familyAxioms,
    familyPrinciples,
    activeCluster,
  } = args;

  const principleTitleById = new Map(
    familyPrinciples.map((principle) => [principle.id, principle.title || principle.id]),
  );
  const resolveObjectNeighborLabel = (
    targetKind: string,
    targetId: string,
    fallback: string,
  ): string => {
    if (targetKind === 'principle') {
      return principleTitleById.get(targetId) ?? fallback;
    }
    return fallback;
  };
  const nodes: RootObjectRelationNode[] = [];
  const edges: RootObjectRelationEdge[] = [];
  const nodesById = new Map<string, RootObjectRelationNode>();
  const addNode = (n: RootObjectRelationNode) => {
    if (!nodesById.has(n.id)) {
      nodesById.set(n.id, n);
      nodes.push(n);
    } else if (n.selected) {
      // Promote selected state if a later add marks this id as selected.
      const existing = nodesById.get(n.id)!;
      existing.selected = true;
    }
  };

  // ─── Focus atoms ──────────────────────────────────────────────────────
  const focusRows: Array<{ rawId: string; row: UnknownRow }> = [];

  if (focusKind === 'axiom_candidates') {
    if (familyAxioms.length > 0) {
      for (const axiom of familyAxioms) {
        focusRows.push({ rawId: axiom.id, row: { id: axiom.id, title: axiom.title ?? axiom.id, status: 'candidate' } as UnknownRow });
      }
    } else {
      for (const row of genericRows) {
        const rawId = genericRowObjectId(row, '');
        if (rawId) focusRows.push({ rawId, row });
      }
    }
  } else if (focusKind === 'principles') {
    if (familyPrinciples.length > 0) {
      for (const principle of familyPrinciples) {
        focusRows.push({
          rawId: principle.id,
          row: {
            id: principle.id,
            title: principle.title ?? principle.id,
            status: 'active',
          } as UnknownRow,
        });
      }
    } else {
      for (const row of genericRows) {
        const rawId = genericRowObjectId(row, '');
        if (rawId) focusRows.push({ rawId, row });
      }
    }
  } else if (focusKind === 'paper_modules') {
    for (const cluster of paperModuleClusters) {
      if (activeCluster && cluster.id !== activeCluster) continue;
      for (const moduleId of cluster.topIds.slice(0, 8)) {
        focusRows.push({
          rawId: moduleId,
          row: {
            id: moduleId,
            title: paperModuleReadableLabel(moduleId),
            status: 'authored',
          } as UnknownRow,
        });
      }
    }
  } else if (focusKind === 'standards') {
    for (const cluster of standardClusters) {
      if (activeCluster && cluster.id !== activeCluster) continue;
      for (const standardId of cluster.topIds.slice(0, 8)) {
        focusRows.push({
          rawId: standardId,
          row: {
            id: standardId,
            title: standardReadableLabel(standardId, cluster.sampleTitlesById.get(standardId)),
            status: 'authored',
          } as UnknownRow,
        });
      }
    }
  } else {
    // Generic kinds (concepts, mechanisms, ...)
    for (const row of genericRows) {
      const rawId = genericRowObjectId(row, '');
      if (rawId) focusRows.push({ rawId, row });
    }
  }

  if (selectedRawId && cardRow) {
    const existingIndex = focusRows.findIndex((entry) =>
      rootObjectRowMatchesSelected(entry.row, entry.rawId, selectedRawId),
    );
    if (existingIndex >= 0) {
      focusRows[existingIndex] = { rawId: focusRows[existingIndex].rawId, row: cardRow };
    } else {
      focusRows.unshift({ rawId: selectedRawId, row: cardRow });
    }
  }

  const selectedFocusRow =
    selectedRawId
      ? focusRows.find((entry) => rootObjectRowMatchesSelected(entry.row, entry.rawId, selectedRawId)) ?? null
      : null;
  const orderedFocusRows = selectedFocusRow
    ? [
        selectedFocusRow,
        ...focusRows.filter((entry) => !rootObjectRowMatchesSelected(entry.row, entry.rawId, selectedRawId)),
      ]
    : focusRows;
  const capped = selectedFocusRow ? [selectedFocusRow] : orderedFocusRows.slice(0, OBJECT_GRAPH_CAP_FOCUS);
  for (const { rawId, row } of capped) {
    addNode(focusObjectNodeFromRow(focusKind, rawId, row, selectedRawId));
  }

  // ─── Edges + neighbor atoms ──────────────────────────────────────────
  // For each focus atom, extract typed edges via the generic extractor.
  // Selected atom gets full ego neighborhood; unselected atoms cap edges
  // to keep the view readable.
  let totalEdgesEmitted = 0;
  for (const { rawId, row } of capped) {
    const isSelected = rootObjectRowMatchesSelected(row, rawId, selectedRawId);
    const ownerNodeId = `${focusKind}:focus:${rawId}`;
    const extracted = extractGenericEdges(focusKind, rawId, row, resolveObjectNeighborLabel);
    const relationCandidates =
      focusKind === 'axiom_candidates' && familyAxioms.length > 0
        ? extracted.filter((edge) => edge.sourceField !== 'related_principles')
        : extracted;
    const cap = isSelected
      ? OBJECT_GRAPH_CAP_EGO_NEIGHBORS
      : OBJECT_GRAPH_CAP_EDGES_PER_FOCUS;
    const slice = relationCandidates.slice(0, cap);
    for (const cand of slice) {
      // Override neighbor source/target with focus_object id (not the
      // namespaced graph id the generic extractor builds).
      const adapted: GenericGraphEdgeCandidate = {
        ...cand,
        sourceId: ownerNodeId,
      };
      const { node, edge } = neighborNodeFromEdgeCandidate(ownerNodeId, adapted);
      addNode(node);
      edges.push(edge);
      totalEdgesEmitted += 1;
    }
  }

  // Axiom candidate ↔ principle bindings via familyAxioms.relatedPrinciples.
  if (focusKind === 'axiom_candidates' || focusKind === 'principles') {
    for (const axiom of familyAxioms) {
      const axiomNodeId =
        focusKind === 'axiom_candidates'
          ? `${focusKind}:focus:${axiom.id}`
          : `axiom_candidate:neighbor:${axiom.id}`;
      if (focusKind === 'principles') {
        addNode({
          id: axiomNodeId,
          rawId: axiom.id,
          kind: 'axiom_candidate',
          label: compactObjectLabel(axiom.title ?? axiom.id),
          nodeKind: 'neighbor_object',
          lane: 'governance',
          selected: false,
        });
      }
      for (const principleId of axiom.relatedPrinciples) {
        const principleNodeId =
          focusKind === 'principles'
            ? `${focusKind}:focus:${principleId}`
            : `principle:neighbor:${principleId}`;
        if (focusKind === 'axiom_candidates') {
          addNode({
            id: principleNodeId,
            rawId: principleId,
            kind: 'principle',
            label: compactObjectLabel(principleTitleById.get(principleId) ?? principleId),
            nodeKind: 'neighbor_object',
            lane: 'downstream',
            selected: false,
          });
        }
        edges.push({
          id: `of:${axiomNodeId}->${principleNodeId}:relatedPrinciples`,
          source: focusKind === 'axiom_candidates' ? axiomNodeId : axiomNodeId,
          target: principleNodeId,
          relation:
            focusKind === 'axiom_candidates' ? 'compresses' : 'compressed_by',
          sourceField: 'related_principles',
          evidenceState: 'direct',
        });
        totalEdgesEmitted += 1;
      }
    }
  }

  // Standards navigation_contract.artifact_kind → governed-kind neighbor
  // (when a standard's card-band is loaded).
  if (focusKind === 'standards' && cardRow && selectedRawId) {
    const navContract = asRecordSafe(cardRow.navigation_contract);
    const governedKind = asString(navContract.artifact_kind);
    if (governedKind) {
      const stdNodeId = `${focusKind}:focus:${selectedRawId}`;
      const govNodeId = `governed_kind:${governedKind}`;
      addNode({
        id: govNodeId,
        rawId: governedKind,
        kind: governedKind,
        label: governedKind.replace(/_/g, ' '),
        nodeKind: 'governed_kind',
        lane: 'downstream',
        selected: false,
      });
      edges.push({
        id: `of:${stdNodeId}->${govNodeId}:navigation_contract`,
        source: stdNodeId,
        target: govNodeId,
        relation: 'governs',
        sourceField: 'navigation_contract.artifact_kind',
        evidenceState: 'direct',
      });
      totalEdgesEmitted += 1;
    }
  }

  const receipt: RootObjectRelationGraph['receipt'] =
    nodes.length === 0
      ? 'missing_rows'
      : totalEdgesEmitted === 0
        ? 'no_edges'
        : 'ready';

  const lanes = OBJECT_GRAPH_LANE_ORDER.map((id) => ({ id, label: OBJECT_GRAPH_LANES[id].label }));

  return {
    focusKind,
    selectedRawId,
    nodes,
    edges,
    lanes,
    receipt,
  };
}

interface UnifiedFlowNodeData {
  nodeId: string;
  label: string;
  secondaryId: string;
  role: RootSemanticGraphNodeRole | 'semantic_scene';
  adapter: RootSemanticGraphAdapter;
  parentId: string;
  expanded: boolean;
  selected: boolean;
  onSelect: (id: string | null) => void;
  accent: string;
  kindMeta?: { rowCount: number | null; status: string };
  // vNext-GA: per-node collapse state for the visible canvas DOM contract.
  // Painted as data-zenith-root-graph-collapse-state on cluster nodes so
  // tests can prove ?cluster=<id> only expands one cluster.
  collapseState?: 'expanded' | 'collapsed';
  // vNext-RT: cluster summary payload. Collapsed cluster nodes paint
  // count + preview labels + claim so they are not semantically blank.
  clusterSummary?: {
    count: number | null;
    previewLabels: string[];
    claim: string | null;
  };
  // vNext-RT: neighbor node payload. Selected-object neighborhood emits
  // these in the visible canvas (not only as bottom-strip pills).
  neighbor?: {
    targetKind: string;
    relation: RootGraphRelation;
    sourceField: string;
  };
  // vNext-RD: scene-zone declaration. Required on every visible node so
  // tests can enforce rail/canvas role decoupling.
  sceneZone?: RootSceneZone;
  // vNext-RD: semantic scene node preview labels. Default-overview semantic
  // scene nodes ('Doctrine Binding', 'Shared Grammar', etc.) carry 2-3
  // preview labels of the artifact kinds they compress.
  scenePreviewLabels?: string[];
  // vNext-IX: typed click payload + dispatch handler. Every node's click
  // resolves through onGraphAction(clickPayload); the legacy onSelect
  // remains for backwards-compat (and for free-form null-clears like
  // cluster collapse), but the canonical interactive path is the payload.
  clickPayload?: RootGraphClickPayload;
  onGraphAction?: (payload: RootGraphClickPayload) => void;
  fabricLayout?: {
    layoutId: RootObjectFabricLayout['layoutId'];
    lane: RootObjectLane;
    x: number;
    y: number;
    width: number;
    row: number;
    renderLimit: number;
    overflow: boolean;
  };
}

function UnifiedSubstrateNode({ data }: NodeProps<UnifiedFlowNodeData>) {
  const compact = data.role === 'substrate_container' && data.adapter !== 'substrate';
  const sceneZone = data.sceneZone ?? 'primary';
  const click = data.clickPayload ?? { action: 'none' };
  const scopeShell = sceneZone === 'scope_hud';
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        if (data.onGraphAction && data.clickPayload && data.clickPayload.action !== 'none') {
          data.onGraphAction(data.clickPayload);
          return;
        }
        data.onSelect(data.nodeId);
      }}
      data-zenith-root-graph-visual-node={data.nodeId}
      data-zenith-root-graph-visual-node-role={data.role}
      data-zenith-root-graph-visual-node-adapter={data.adapter}
      data-zenith-root-graph-visual-node-parent={data.parentId}
      data-zenith-root-scene-zone={sceneZone}
      data-zenith-root-click-action={click.action}
      data-zenith-root-click-kind={click.kind ?? ''}
      data-zenith-root-click-raw-id={click.rawId ?? ''}
      data-zenith-root-click-cluster={click.clusterId ?? ''}
      data-zenith-root-click-scene-role={click.sceneRoleId ?? ''}
      data-zenith-root-graph-visual-node-expanded={data.expanded ? 'true' : 'false'}
      data-zenith-root-graph-visual-node-selected={data.selected ? 'true' : 'false'}
      data-zenith-root-substrate-object-primary-label={data.label}
      data-zenith-root-substrate-object-secondary-id={data.secondaryId}
      className={clsx(
        'w-full rounded-[var(--zenith-radius-2xs)] border px-[var(--zenith-space-2-5)] py-2 text-left font-mono transition-colors',
        scopeShell
          ? 'pointer-events-none h-full border-white/[0.045] bg-transparent shadow-none'
          : data.expanded
            ? 'border-cyan-200/70 bg-[#05070b] ring-1 ring-cyan-300/35 shadow-[0_0_18px_rgba(103,232,249,0.14)]'
            : compact
              ? 'border-white/14 bg-[#05070b] opacity-60 hover:opacity-100 hover:border-cyan-300/55'
              : 'border-white/14 bg-[#05070b] hover:border-cyan-300/55 hover:ring-1 hover:ring-cyan-300/35',
      )}
    >
      {!scopeShell && (
        <>
          <Handle type="target" position={Position.Left} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
          <Handle type="source" position={Position.Right} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
          <div className="flex items-center justify-between gap-2">
            <span
              className="truncate text-[9px] uppercase tracking-[0.16em]"
              style={{ color: data.accent }}
            >
              {data.adapter === 'substrate'
                ? typeof data.kindMeta?.rowCount === 'number' && data.kindMeta.rowCount > 0
                  ? 'kind · generic'
                  : 'kind · unadapted'
                : data.adapter === 'generic_option_surface'
                  ? 'kind · generic'
                  : `kind · ${data.adapter}`}
            </span>
            {data.kindMeta?.rowCount !== null && data.kindMeta?.rowCount !== undefined && (
              <span className="text-[9px] text-zenith-muted">{data.kindMeta.rowCount}</span>
            )}
          </div>
          <div className="mt-1 truncate text-[12px] font-semibold text-white">{data.label}</div>
          {!compact && data.expanded && (
            <div className="mt-0.5 truncate text-[10px] text-cyan-100/70">expanded</div>
          )}
        </>
      )}
    </button>
  );
}

function UnifiedClusterNode({ data }: NodeProps<UnifiedFlowNodeData>) {
  const collapseState = data.collapseState ?? (data.expanded ? 'expanded' : 'collapsed');
  // Cluster summaries make collapsed cluster nodes semantically legible, but
  // the family zoom is a map, not a row browser. Keep the count and action;
  // suppress sample labels here so half-visible row titles do not fight the
  // Inspector's explanation.
  const summary = data.clusterSummary;
  const previewLabels = summary?.previewLabels ?? [];
  const previewCount = previewLabels.length;
  const summaryEmpty = !summary || (summary.count === null && previewCount === 0 && !summary.claim);
  const click = data.clickPayload ?? { action: 'expand_cluster' as const };
  const dispatchClick = () => {
    if (data.onGraphAction && data.clickPayload && data.clickPayload.action !== 'none') {
      data.onGraphAction(data.clickPayload);
      return;
    }
    data.onSelect(data.nodeId);
  };
  return (
    <div
      onClick={(event) => {
        event.stopPropagation();
        dispatchClick();
      }}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          dispatchClick();
        }
      }}
      data-zenith-root-graph-visual-node={data.nodeId}
      data-zenith-root-graph-visual-node-role="cluster"
      data-zenith-root-graph-visual-node-adapter={data.adapter}
      data-zenith-root-graph-visual-node-parent={data.parentId}
      data-zenith-root-scene-zone={data.sceneZone ?? 'cluster'}
      data-zenith-root-click-action={click.action}
      data-zenith-root-click-kind={click.kind ?? ''}
      data-zenith-root-click-raw-id={click.rawId ?? ''}
      data-zenith-root-click-cluster={click.clusterId ?? ''}
      data-zenith-root-graph-visual-node-expanded={collapseState === 'expanded' ? 'true' : 'false'}
      data-zenith-root-graph-visual-node-selected={data.selected ? 'true' : 'false'}
      data-zenith-root-graph-collapse-state={collapseState}
      data-zenith-root-cluster-summary={summary ? 'ready' : 'missing'}
      data-zenith-root-cluster-summary-count={summary?.count ?? ''}
      data-zenith-root-cluster-summary-preview-count={previewCount}
      data-zenith-root-cluster-summary-preview-rendering="hidden_at_family_zoom"
      data-zenith-root-cluster-summary-empty={summaryEmpty ? 'true' : 'false'}
      data-zenith-root-substrate-object-primary-label={data.label}
      data-zenith-root-substrate-object-secondary-id={data.secondaryId}
      className={clsx(
        'group relative flex h-full w-full cursor-pointer flex-col overflow-hidden rounded-[7px] border text-left transition-[background,border-color,box-shadow]',
        data.selected
          ? 'border-cyan-200/70 bg-cyan-300/[0.055]'
          : collapseState === 'expanded'
            ? 'border-cyan-300/45 bg-cyan-300/[0.04]'
            : 'border-white/14 bg-white/[0.028] hover:border-cyan-300/45 hover:bg-white/[0.04]',
      )}
      style={{
        background: data.selected
          ? 'linear-gradient(180deg, rgba(103,232,249,0.085) 0%, rgba(5,8,12,0.96) 68%), #05070b'
          : 'linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(5,8,12,0.965) 72%), #05070b',
        boxShadow: data.selected
          ? '0 0 0 1px rgba(103,232,249,0.22), 0 0 22px rgba(103,232,249,0.18)'
          : '0 8px 24px -20px rgba(0,0,0,0.9)',
      }}
    >
      <Handle type="target" position={Position.Top} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
      <Handle type="source" position={Position.Bottom} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
      <span
        aria-hidden
        className="pointer-events-none absolute inset-y-0 left-0 w-[3px] rounded-l-[7px]"
        style={{ background: data.selected ? data.accent : `${data.accent}80` }}
      />
      <div className="flex items-baseline justify-between border-b border-white/8 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.16em]" style={{ color: data.accent }}>
        <span className="line-clamp-2 min-w-0 pr-3 leading-tight">{data.label}</span>
        <span className="flex shrink-0 items-baseline gap-1.5 text-zenith-muted">
          {summary?.count !== undefined && summary?.count !== null && (
            <span className="font-semibold text-zenith-soft">{summary.count}</span>
          )}
          <span>{collapseState === 'expanded' ? 'expanded' : 'cluster'}</span>
        </span>
      </div>
      {collapseState === 'collapsed' && !summaryEmpty && (
        <div className="flex min-h-0 flex-1 flex-col px-3 py-2 font-mono text-[10.5px] leading-4 text-zenith-soft">
          <div className="text-white/62">
            {summary?.count !== undefined && summary?.count !== null
              ? `${summary.count} objects grouped here.`
              : 'Objects grouped here.'}
          </div>
          <div className="mt-auto text-right text-[9px] uppercase tracking-[0.12em] text-cyan-200/45">click to expand</div>
        </div>
      )}
      {collapseState === 'collapsed' && summaryEmpty && (
        <div
          className="flex min-h-0 flex-1 items-center justify-center px-3 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-amber-200/55"
          data-zenith-root-cluster-summary-receipt="missing"
        >
          summary unavailable
        </div>
      )}
    </div>
  );
}

function UnifiedClusterSubjectNode({ data }: NodeProps<UnifiedFlowNodeData>) {
  const summary = data.clusterSummary;
  const previewLabels = summary?.previewLabels ?? [];
  const click = data.clickPayload ?? { action: 'expand_cluster' as const };
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        if (data.onGraphAction && data.clickPayload && data.clickPayload.action !== 'none') {
          data.onGraphAction(data.clickPayload);
        }
      }}
      data-zenith-root-graph-visual-node={data.nodeId}
      data-zenith-root-graph-visual-node-role="cluster"
      data-zenith-root-graph-visual-node-adapter={data.adapter}
      data-zenith-root-graph-visual-node-parent={data.parentId}
      data-zenith-root-scene-zone="cluster"
      data-zenith-root-click-action={click.action}
      data-zenith-root-click-kind={click.kind ?? ''}
      data-zenith-root-click-cluster={click.clusterId ?? ''}
      data-zenith-root-graph-visual-node-expanded="true"
      data-zenith-root-graph-visual-node-selected="true"
      data-zenith-root-graph-collapse-state="expanded"
      data-zenith-root-cluster-focus-subject="true"
      data-zenith-root-cluster-summary-count={summary?.count ?? ''}
      data-zenith-root-cluster-summary-preview-count={previewLabels.length}
      data-zenith-root-substrate-object-primary-label={data.label}
      data-zenith-root-substrate-object-secondary-id={data.secondaryId}
      className="relative flex h-full w-full flex-col overflow-hidden rounded-[var(--zenith-radius-xs)] border border-cyan-200/70 bg-[#071016]/95 px-4 py-3 text-left font-mono shadow-[0_0_32px_rgba(103,232,249,0.18)] ring-1 ring-cyan-300/30"
      style={{
        borderColor: data.accent,
        background:
          'linear-gradient(180deg, rgba(103,232,249,0.09) 0%, rgba(5,8,12,0.97) 70%), #05070b',
      }}
    >
      <Handle type="source" position={Position.Right} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
      <span
        aria-hidden
        className="pointer-events-none absolute inset-y-0 left-0 w-[4px] rounded-l-[8px]"
        style={{ background: data.accent }}
      />
      <div className="flex items-center justify-between gap-3 pl-1 text-[9px] uppercase tracking-[0.18em] text-cyan-100/55">
        <span>selected cluster</span>
        {summary?.count !== undefined && summary?.count !== null && (
          <span className="text-zenith-soft">{summary.count} rows</span>
        )}
      </div>
      <div className="mt-3 pl-1 text-[17px] font-semibold leading-tight text-cyan-100">
        {data.label}
      </div>
      <div className="mt-3 pl-1 text-[11px] leading-5 text-white/62">
        {summary?.count !== undefined && summary?.count !== null
          ? `${summary.count} objects belong to this family.`
          : 'This selected family owns the objects shown to the right.'}
      </div>
      {summary?.claim && (
        <div className="mt-3 line-clamp-2 pl-1 text-[10.5px] italic leading-snug text-zenith-muted">
          {summary.claim}
        </div>
      )}
      <div className="mt-auto pl-1 pt-3 text-[9px] uppercase tracking-[0.16em] text-cyan-200/55">
        click to collapse
      </div>
    </button>
  );
}

function UnifiedObjectNode({ data }: NodeProps<UnifiedFlowNodeData>) {
  // vNext-RT: neighbor nodes paint -role='neighbor' + target-kind + source-
  // field so tests/screenshots can target visible relation neighborhoods
  // distinct from in-cluster object children.
  const visualRole = data.neighbor ? 'neighbor' : data.role;
  const click = data.clickPayload ?? { action: data.neighbor ? 'select_neighbor' as const : 'select_object' as const };
  const selectedSubject = data.selected && !data.neighbor;
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        if (data.onGraphAction && data.clickPayload && data.clickPayload.action !== 'none') {
          data.onGraphAction(data.clickPayload);
          return;
        }
        data.onSelect(data.selected ? null : data.nodeId);
      }}
      data-zenith-root-graph-visual-node={data.nodeId}
      data-zenith-root-graph-visual-node-role={visualRole}
      data-zenith-root-graph-visual-node-adapter={data.adapter}
      data-zenith-root-graph-visual-node-parent={data.parentId}
      data-zenith-root-scene-zone={data.sceneZone ?? (data.neighbor ? 'neighbor' : 'object')}
      data-zenith-root-click-action={click.action}
      data-zenith-root-click-kind={click.kind ?? ''}
      data-zenith-root-click-raw-id={click.rawId ?? ''}
      data-zenith-root-click-cluster={click.clusterId ?? ''}
      data-zenith-root-click-target-kind={click.targetKind ?? ''}
      data-zenith-root-graph-visual-node-expanded={data.expanded ? 'true' : 'false'}
      data-zenith-root-graph-visual-node-selected={data.selected ? 'true' : 'false'}
      data-zenith-root-graph-visual-node-target-kind={data.neighbor?.targetKind ?? ''}
      data-zenith-root-graph-visual-edge-source-field={data.neighbor?.sourceField ?? ''}
      data-zenith-root-graph-visual-edge-relation={data.neighbor?.relation ?? ''}
      data-zenith-root-substrate-object-primary-label={data.label}
      data-zenith-root-substrate-object-secondary-id={data.secondaryId}
      className={clsx(
        'relative w-full max-w-full rounded-[var(--zenith-radius-2xs)] border text-left font-mono leading-4 transition-[background,border-color,box-shadow]',
        selectedSubject ? 'px-3.5 py-[var(--zenith-space-2-5)]' : 'px-3 py-2',
        data.selected
          ? 'border-cyan-200/85 bg-cyan-300/[0.075] ring-1 ring-cyan-300/45 shadow-[0_0_18px_rgba(103,232,249,0.24)]'
          : 'border-white/14 bg-white/[0.032] hover:border-cyan-300/50 hover:bg-white/[0.045]',
      )}
      style={{
        borderColor: data.selected ? data.accent : undefined,
      }}
    >
      <Handle type="target" position={Position.Left} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
      <Handle type="source" position={Position.Right} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
      <div
        className={clsx(
          'line-clamp-2 whitespace-normal font-semibold',
          selectedSubject ? 'text-[13px]' : 'text-[11.5px]',
        )}
        style={{ color: data.selected ? data.accent : '#e2e8f0' }}
      >
        {data.label}
      </div>
    </button>
  );
}

function UnifiedReceiptNode({ data }: NodeProps<UnifiedFlowNodeData>) {
  return (
    <div
      data-zenith-root-graph-visual-node={data.nodeId}
      data-zenith-root-graph-visual-node-role="receipt"
      data-zenith-root-graph-visual-node-adapter="receipt"
      data-zenith-root-graph-visual-node-parent={data.parentId}
      data-zenith-root-scene-zone={data.sceneZone ?? 'receipt'}
      data-zenith-root-click-action={data.clickPayload?.action ?? 'none'}
      data-zenith-root-graph-visual-node-expanded="false"
      data-zenith-root-graph-visual-node-selected="false"
      data-zenith-root-substrate-object-primary-label={data.label}
      data-zenith-root-substrate-object-secondary-id={data.secondaryId}
      className="rounded-[4px] border border-amber-300/30 bg-amber-300/[0.06] px-[var(--zenith-space-2-5)] py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/85"
    >
      <Handle type="target" position={Position.Left} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
      receipt · {data.label}
    </div>
  );
}

// vNext-RD: semantic-role node for the default overview scene. Renders a
// relation-family role (Doctrine Binding, Shared Grammar, Named Meanings,
// Operational Transformations, Rationale Modules, Projection Runtime, Work &
// Repair, Evidence & Sources) with preview labels — NOT artifact-kind boxes
// duplicated from the rail.
function UnifiedSemanticSceneNode({ data }: NodeProps<UnifiedFlowNodeData>) {
  const previewLabels = data.scenePreviewLabels ?? [];
  const click = data.clickPayload ?? { action: 'open_scene_role' as const };
  const accent = data.accent ?? '#94a3b8';
  // Tiny invisible handles — we declare one per side+direction so edges can
  // explicitly anchor to top/bottom for vertical connections (evidence above
  // doctrine, repair below shared grammar) and left/right for the spine.
  const handleCls = '!h-1 !w-1 !border-0 !bg-transparent !opacity-0';
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        if (data.onGraphAction && data.clickPayload && data.clickPayload.action !== 'none') {
          data.onGraphAction(data.clickPayload);
          return;
        }
        data.onSelect(data.nodeId);
      }}
      data-zenith-root-graph-visual-node={data.nodeId}
      data-zenith-root-graph-visual-node-role="semantic_scene"
      data-zenith-root-graph-visual-node-adapter={data.adapter}
      data-zenith-root-graph-visual-node-parent={data.parentId}
      data-zenith-root-scene-zone={data.sceneZone ?? 'primary'}
      data-zenith-root-click-action={click.action}
      data-zenith-root-click-kind={click.kind ?? ''}
      data-zenith-root-click-scene-role={click.sceneRoleId ?? data.nodeId}
      data-zenith-root-graph-visual-node-expanded={data.expanded ? 'true' : 'false'}
      data-zenith-root-graph-visual-node-selected={data.selected ? 'true' : 'false'}
      data-zenith-root-substrate-object-primary-label={data.label}
      data-zenith-root-substrate-object-secondary-id={data.secondaryId}
      className={clsx(
        'flex h-full w-full cursor-pointer flex-col overflow-hidden rounded-[var(--zenith-radius-sm)] border px-3 py-2 text-left transition-colors',
        data.selected ? 'bg-white/[0.05]' : 'bg-[#05070b] hover:bg-white/[0.03]',
      )}
      style={{
        borderColor: data.selected ? accent : `${accent}55`,
        boxShadow: data.selected ? `0 0 22px ${accent}33` : undefined,
      }}
    >
      <Handle id="left-target" type="target" position={Position.Left} className={handleCls} />
      <Handle id="left-source" type="source" position={Position.Left} className={handleCls} />
      <Handle id="right-source" type="source" position={Position.Right} className={handleCls} />
      <Handle id="right-target" type="target" position={Position.Right} className={handleCls} />
      <Handle id="top-target" type="target" position={Position.Top} className={handleCls} />
      <Handle id="top-source" type="source" position={Position.Top} className={handleCls} />
      <Handle id="bottom-target" type="target" position={Position.Bottom} className={handleCls} />
      <Handle id="bottom-source" type="source" position={Position.Bottom} className={handleCls} />
      <div className="truncate text-[15px] font-semibold leading-[1.15] tracking-[0.01em]" style={{ color: accent }}>
        {data.label}
      </div>
      {previewLabels.length > 0 && (
        <div className="mt-2 flex min-h-0 flex-1 flex-col gap-1 text-[12px] leading-[1.3] text-white/65">
          {previewLabels.slice(0, 3).map((label, i) => (
            <span key={i} className="truncate">· {label}</span>
          ))}
        </div>
      )}
    </button>
  );
}

// vNext-OF: compact object-fabric node. Renders an atom + its source-field
// relation chip. Distinct from UnifiedObjectNode (which is the larger,
// cluster-bound card-shaped atom). Fabric nodes carry data-zenith-root-
// object-* attrs so tests can target the relation projection directly.
function UnifiedObjectFabricNode({ data }: NodeProps<UnifiedFlowNodeData & {
  fabric?: {
    nodeKind: RootObjectNodeKind;
    lane: RootObjectLane;
    rawId: string;
    fabricKind: string;
    isSelected: boolean;
    relation?: RootObjectRelation;
    sourceField?: string;
  };
}>) {
  const click = data.clickPayload ?? { action: 'none' as const };
  const fabric = data.fabric;
  if (!fabric) return null;
  const visualRole =
    fabric.nodeKind === 'focus_object'
      ? fabric.fabricKind === 'axiom_candidates'
        ? 'axiom_candidate'
        : fabric.fabricKind === 'paper_modules'
          ? 'paper_module'
          : fabric.fabricKind === 'standards'
            ? 'standard_contract'
            : fabric.fabricKind
      : 'neighbor';
  const isSelectedSubject = fabric.isSelected && fabric.nodeKind === 'focus_object';
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        if (data.onGraphAction && data.clickPayload && data.clickPayload.action !== 'none') {
          data.onGraphAction(data.clickPayload);
        }
      }}
      data-zenith-root-graph-visual-node={data.nodeId}
      data-zenith-root-graph-visual-node-role={visualRole}
      data-zenith-root-graph-visual-node-adapter="generic_option_surface"
      data-zenith-root-graph-visual-node-parent={data.parentId}
      data-zenith-root-scene-zone={fabric.nodeKind === 'focus_object' ? 'object' : 'neighbor'}
      data-zenith-root-object-node-kind={fabric.nodeKind}
      data-zenith-root-object-node-lane={fabric.lane}
      data-zenith-root-object-node-raw-id={fabric.rawId}
      data-zenith-root-object-node-selected={fabric.isSelected ? 'true' : 'false'}
      data-zenith-root-object-fabric-emphasis={isSelectedSubject ? 'subject' : 'context'}
      data-zenith-root-object-fabric-layout={data.fabricLayout?.layoutId ?? ''}
      data-zenith-root-object-fabric-layout-x={data.fabricLayout?.x ?? ''}
      data-zenith-root-object-fabric-layout-y={data.fabricLayout?.y ?? ''}
      data-zenith-root-object-fabric-layout-width={data.fabricLayout?.width ?? ''}
      data-zenith-root-object-fabric-layout-overflow={data.fabricLayout?.overflow ? 'true' : 'false'}
      data-zenith-root-graph-visual-node-target-kind={fabric.nodeKind === 'focus_object' ? '' : fabric.fabricKind}
      data-zenith-root-graph-visual-edge-source-field={fabric.sourceField ?? ''}
      data-zenith-root-graph-visual-edge-relation={fabric.relation ?? ''}
      data-zenith-root-click-action={click.action}
      data-zenith-root-click-kind={click.kind ?? ''}
      data-zenith-root-click-raw-id={click.rawId ?? ''}
      data-zenith-root-click-target-kind={click.targetKind ?? ''}
      data-zenith-root-graph-visual-node-selected={fabric.isSelected ? 'true' : 'false'}
      data-zenith-root-substrate-object-primary-label={data.label}
      data-zenith-root-substrate-object-secondary-id={fabric.rawId}
      className={clsx(
        'relative w-full max-w-full overflow-hidden rounded-[7px] border text-left font-mono leading-4 transition-[background,border-color,box-shadow]',
        isSelectedSubject
          ? 'border-cyan-100/90 bg-[#0d1419]/95 px-4 py-3 ring-1 ring-cyan-200/50 shadow-[0_0_32px_rgba(103,232,249,0.24)]'
          : fabric.isSelected
            ? 'border-cyan-200/85 bg-cyan-300/[0.08] px-3 py-2 ring-1 ring-cyan-300/45 shadow-[0_0_18px_rgba(103,232,249,0.24)]'
          : fabric.nodeKind === 'focus_object'
            ? 'border-white/16 bg-[#080c11]/90 px-3 py-2 hover:border-cyan-300/55 hover:bg-white/[0.05]'
            : 'border-white/12 bg-[#080c11]/92 px-3 py-2 hover:border-cyan-300/35 hover:bg-white/[0.04]',
      )}
      style={{ borderColor: fabric.isSelected ? data.accent : undefined }}
    >
      <Handle type="target" position={Position.Left} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
      <Handle type="source" position={Position.Right} className={ROOT_GRAPH_HIDDEN_HANDLE_CLASS} />
      <span
        aria-hidden
        className="pointer-events-none absolute inset-y-0 left-0 w-[3px] rounded-l-[6px]"
        style={{ background: fabric.isSelected ? data.accent : `${data.accent}66` }}
      />
      <div
        className={clsx(
          'line-clamp-2 whitespace-normal pl-1 font-semibold leading-[1.25]',
          isSelectedSubject ? 'text-[16px]' : 'text-[12px]',
        )}
        style={{ color: fabric.isSelected ? data.accent : '#e2e8f0' }}
      >
        {data.label}
      </div>
      {isSelectedSubject && (
        <div className="mt-2 truncate pl-1 text-[10px] uppercase tracking-[0.12em] text-cyan-100/55">
          {fabric.rawId}
        </div>
      )}
    </button>
  );
}

// vNext-OF: lane label (non-clickable HTML overlay would also work, but a
// React Flow node anchors the lane visually at a known x position).
function UnifiedObjectLaneLabel({ data }: NodeProps<UnifiedFlowNodeData & { laneInfo?: { lane: RootObjectLane } }>) {
  return (
    <div
      data-zenith-root-graph-visual-node={data.nodeId}
      data-zenith-root-graph-visual-node-role="lane_label"
      data-zenith-root-scene-zone="primary"
      data-zenith-root-object-graph-lane={data.laneInfo?.lane ?? ''}
      data-zenith-root-object-graph-lane-label={data.label}
      data-zenith-root-object-graph-lane-layout={data.fabricLayout?.layoutId ?? ''}
      data-zenith-root-object-graph-lane-x={data.fabricLayout?.x ?? ''}
      data-zenith-root-object-graph-lane-width={data.fabricLayout?.width ?? ''}
      data-zenith-root-object-graph-lane-overflow={data.fabricLayout?.overflow ? 'true' : 'false'}
      data-zenith-root-click-action="none"
      className="rounded-[4px] border border-white/10 bg-black/60 px-3 py-1.5 font-mono text-[9.5px] uppercase tracking-[0.18em] text-zenith-muted"
    >
      {data.label}
    </div>
  );
}

const UNIFIED_GRAPH_NODE_TYPES = {
  unifiedSubstrate: UnifiedSubstrateNode,
  unifiedCluster: UnifiedClusterNode,
  unifiedClusterSubject: UnifiedClusterSubjectNode,
  unifiedObject: UnifiedObjectNode,
  unifiedReceipt: UnifiedReceiptNode,
  unifiedSemanticScene: UnifiedSemanticSceneNode,
  unifiedObjectFabric: UnifiedObjectFabricNode,
  unifiedObjectLaneLabel: UnifiedObjectLaneLabel,
};

// vNext-RD: default overview semantic scene. Eight relation-family roles +
// directed edges. Each role compresses one or more artifact kinds; the rail
// still owns kind navigation, but the canvas's primary scene now describes
// how the substrate's roles relate, not just what kinds exist.
const ROOT_SEMANTIC_SCENE_NODES: Array<{
  id: string;
  label: string;
  preview: string[];
  accent: string;
  position: { x: number; y: number };
}> = [
  // Expanded overview, compact serpentine: a 4-column × 3-row constellation
  // instead of a single wide spine. The earlier ~967×628 packing (aspect ≈
  // 1.54) was wider than the center pane, so fitView was width-bound and the
  // graph filled width but left a tall dark void below it. This packing is
  // ~937px × ~728px (aspect ≈ 1.29) to match the center pane aspect, so fitView
  // lands at ~1× on BOTH axes (capped at 1×) and the constellation fills ~90%
  // of the dominant pane height instead of floating over a void — it now reads
  // as the primary instrument, not a small diagram on a black field. Reading
  // order: top spine L→R (projection → rationale → doctrine), drop straight
  // down (doctrine → grammar), then the governance flow runs back along the
  // bottom (grammar → meaning → mechanism). Evidence feeds doctrine from
  // directly above; repair feeds grammar from the right.
  // Columns: 0 / 235 / 470 / 705. Rows: 0 / 300 / 600.
  { id: 'scene:projection', label: 'Projection Runtime', preview: ['Frontend Views', 'System Atlas'], accent: '#94a3b8', position: { x: 0, y: 300 } },
  { id: 'scene:rationale', label: 'Rationale Modules', preview: ['Paper Modules'], accent: '#a78bfa', position: { x: 235, y: 300 } },
  { id: 'scene:evidence', label: 'Evidence & Sources', preview: ['Raw Seed Shards', 'Annexes'], accent: '#7bc78e', position: { x: 470, y: 0 } },
  { id: 'scene:doctrine_binding', label: 'Doctrine Binding', preview: ['Axioms', 'Principles'], accent: '#c7b06a', position: { x: 470, y: 300 } },
  { id: 'scene:shared_grammar', label: 'Shared Grammar', preview: ['Standards'], accent: '#7dd3fc', position: { x: 470, y: 600 } },
  { id: 'scene:repair', label: 'Work & Repair', preview: ['Task Ledger WorkItems'], accent: '#f87171', position: { x: 705, y: 600 } },
  { id: 'scene:semantic_objects', label: 'Named Meanings', preview: ['Concepts'], accent: '#7bc78e', position: { x: 235, y: 600 } },
  { id: 'scene:mechanisms', label: 'Operational Transformations', preview: ['Mechanisms'], accent: '#fbbf24', position: { x: 0, y: 600 } },
];

const ROOT_SEMANTIC_SCENE_EDGES: Array<{ source: string; target: string; relation: string }> = [
  { source: 'scene:doctrine_binding', target: 'scene:shared_grammar', relation: 'compresses' },
  { source: 'scene:shared_grammar', target: 'scene:semantic_objects', relation: 'governs' },
  { source: 'scene:semantic_objects', target: 'scene:mechanisms', relation: 'instantiates' },
  { source: 'scene:rationale', target: 'scene:doctrine_binding', relation: 'explains' },
  { source: 'scene:projection', target: 'scene:rationale', relation: 'projects' },
  { source: 'scene:repair', target: 'scene:shared_grammar', relation: 'repairs' },
  { source: 'scene:evidence', target: 'scene:doctrine_binding', relation: 'sources' },
];

// Layout constants for the visible canvas. Manual layout: tight enough that a
// 1920x1080 viewport shows the whole graph at fitView, generous enough that
// clusters and child objects don't overlap. Atlas mode lays containers in a
// row; focus mode shrinks root context containers to a top strip and expands
// the focused container into a large compound region with cluster children.
const CANVAS_FOCUS_X = 72;
const CANVAS_FOCUS_Y = 96;
const CANVAS_FOCUS_WIDTH = 1060;
const CANVAS_FOCUS_HEIGHT = 520;
// LOCAL-mode scope_hud shell height. In local mode the only positioned content
// is the bounded_subject_lanes fabric (tops out ~y352 sparse / ~462 dense), but
// the shell was emitted at the full focus height (520), so React Flow's
// width-bound fitView framed an oversized 1060x520 box and the neighborhood sat
// upper with a dark lower basin. Sizing the (transparent) shell nearer the
// content extent tightens that bbox and nudges the neighborhood toward center.
// HONEST SCOPE: this is a MODEST step, not a full fix — measured centroid offset
// -138px -> -108px on a full-neighborhood capture; the lanes are still anchored
// near the canvas top, so it does not fully center or fill. Full vertical
// centering needs the lane-Y reposition wave tracked in
// cap_quick_root_navigator_local_graph_mode_vertical_4c5513d61e3a. SAFE: used
// ONLY at the local shell push (gated on selectedNode); shared lane math
// (L6019/L6131) keeps reading CANVAS_FOCUS_HEIGHT so focus/cluster/overview/
// atlas render byte-identical (verified 0.00% focus pixel-diff), and fabric
// nodes lack extent:'parent' (L8268) so a shorter shell never clips content.
const CANVAS_LOCAL_FOCUS_HEIGHT = 408;
const CANVAS_CLUSTER_WIDTH = 300;
const CANVAS_CLUSTER_MIN_HEIGHT = 108;
const CANVAS_OBJECT_WIDTH = 268;
const CANVAS_OBJECT_HEIGHT = 40;
const CANVAS_CLUSTER_FOCUS_LIMIT = 8;
const CANVAS_CLUSTER_LOCAL_CONTEXT_LIMIT = 0;
const CANVAS_DIRECT_OBJECT_FOCUS_LIMIT = 18;
const CANVAS_NEIGHBORHOOD_X = 840;
const CANVAS_NEIGHBORHOOD_Y = 132;
const ROOT_SEMANTIC_SCENE_NODE_WIDTH = 232;
const ROOT_SEMANTIC_SCENE_NODE_HEIGHT = 128;
// Atlas fitView ceiling stays 1× (natural node size is the legibility target;
// the contract attribute data-zenith-root-semantic-scene-fit-max-zoom asserts
// this). Vertical ownership of the pane is achieved by the constellation bbox
// aspect (~937×728 ≈ 1.29) now matching the center pane aspect instead of being
// width-dominant, so fitView lands at ~1× and the graph fills ~90% of the pane
// height rather than floating over a dark void below it.
const ROOT_SEMANTIC_SCENE_ATLAS_FIT_MAX_ZOOM = 1;

function unifiedContainerAccent(kind: string): string {
  return AXIS_ACCENT[kind] ?? '#94a3b8';
}

interface ClusterSummaryEntry {
  count: number | null;
  previewLabels: string[];
  claim: string | null;
}

interface BuildVisibleUnifiedFlowArgs {
  graph: {
    nodes: RootSemanticGraphReceiptNode[];
    edges: RootSemanticGraphReceiptEdge[];
  };
  // vNext-OF: object relation fabric for the focused kind. When the
  // receipt is 'ready', additional lane labels + focus/neighbor nodes +
  // typed edges render alongside the existing cluster grid so the focused
  // view stops being a card grid.
  objectRelationGraph: RootObjectRelationGraph | null;
  expandedKind: string | null;
  selectedNode: string | null;
  // vNext-GA: ?cluster=<id> single-cluster expansion. When set, only the
  // matching cluster reveals its object children; siblings stay collapsed.
  // When unset (and a kind with clusters is focused), no objects are emitted
  // until the operator clicks a cluster (which sets the URL param).
  activeCluster: string | null;
  onSelect: (id: string | null) => void;
  // vNext-GA: cluster-row click handler. The canvas calls this on cluster
  // node clicks to set/clear ?cluster=<id>; toggling the same cluster passes
  // null to collapse it back. Object-row clicks continue to use onSelect.
  onClusterToggle: (clusterRawId: string | null) => void;
  // vNext-IX: typed graph-action dispatcher. Every visible node carries a
  // typed payload describing what its click should do; the dispatcher
  // resolves payloads into URL changes / Inspector updates / focus changes.
  onGraphAction: (payload: RootGraphClickPayload) => void;
  cardRow: UnknownRow | null;
  substrateContainerMeta: Map<string, { rowCount: number | null; status: string }>;
  // vNext-RT: per-cluster summary map (keyed by the cluster's raw secondary
  // id) so the visible cluster node can render count + preview labels even
  // when collapsed.
  clusterSummaryById: Map<string, ClusterSummaryEntry>;
  // vNext-RT: extracted relation edges for the selected object, keyed by
  // ownerKind:objectId. Selected-object neighborhood reads this map to emit
  // visible neighbor nodes + React Flow edges rather than only edge pills.
  edgesForSelected: GenericGraphEdgeCandidate[];
}

function buildVisibleUnifiedGraphFlow({
  graph,
  objectRelationGraph,
  expandedKind,
  selectedNode,
  activeCluster,
  onSelect,
  onClusterToggle,
  onGraphAction,
  cardRow,
  substrateContainerMeta,
  clusterSummaryById,
  edgesForSelected,
}: BuildVisibleUnifiedFlowArgs): { nodes: RfNode[]; edges: RfEdge[] } {
  const nodes: RfNode[] = [];
  const edges: RfEdge[] = [];

  const substrateContainers = graph.nodes.filter(
    (n) => n.role === 'substrate_container',
  );

  // vNext-RD: in ATLAS mode, render the default semantic scene (8 relation
  // roles + edges) instead of the substrate-container grid. The Artifact Rail
  // already owns kind navigation; the canvas's primary zone must answer 'what
  // do the substrate's roles mean relationally', not duplicate the rail.
  //
  // In FOCUS mode, the top context kind strip is REMOVED. The scope HUD
  // overlay (rendered separately in RootUnifiedSystemGraphCanvasInner)
  // carries the current-focus metadata; the canvas's primary content is
  // the focused container's clusters/objects + selected neighborhood.
  if (!expandedKind) {
    for (const scene of ROOT_SEMANTIC_SCENE_NODES) {
      const mapping = SCENE_ROLE_CLICK_MAP[scene.id];
      // vNext-IX: scene-role click resolves to focus_kind via SCENE_ROLE_
      // CLICK_MAP. Operators clicking Named Meanings drill into ?focus=
      // concepts, Operational Transformations → focus=mechanisms, etc.
      const clickPayload: RootGraphClickPayload = mapping
        ? {
            action: 'focus_kind',
            kind: mapping.kind,
            sceneRoleId: mapping.sceneRoleId,
            nodeId: scene.id,
          }
        : { action: 'none', nodeId: scene.id };
      nodes.push({
        id: `visual:${scene.id}`,
        type: 'unifiedSemanticScene',
        position: scene.position,
        // Explicit width/height (not just style) so React Flow's store knows the
        // node size immediately. Without this the one-shot declarative fitView
        // runs before the ResizeObserver measures the nodes, fits the bare
        // position-points, and clamps to maxZoom (1) — leaving the scene at the
        // un-fit default and clipping the right column.
        width: ROOT_SEMANTIC_SCENE_NODE_WIDTH,
        height: ROOT_SEMANTIC_SCENE_NODE_HEIGHT,
        style: { width: ROOT_SEMANTIC_SCENE_NODE_WIDTH, height: ROOT_SEMANTIC_SCENE_NODE_HEIGHT },
        draggable: false,
        data: {
          nodeId: scene.id,
          label: scene.label,
          secondaryId: scene.id,
          role: 'semantic_scene',
          adapter: 'receipt',
          parentId: 'root:substrate',
          expanded: false,
          selected: false,
          onSelect,
          accent: scene.accent,
          sceneZone: 'primary',
          scenePreviewLabels: scene.preview,
          clickPayload,
          onGraphAction,
        } satisfies UnifiedFlowNodeData,
      });
    }
    // Edges that run between nodes in the same spine row use right→left
    // handles. Edges crossing rows (evidence above, repair below) anchor to
    // top/bottom handles so the line drops straight in/out rather than
    // wrapping around through the node center.
    // Handle overrides for the compact serpentine. Anything not listed uses the
    // default left→right spine handles (right-source → left-target). Vertical
    // drops use top/bottom; the bottom-row governance flow runs right→left, so
    // those edges exit the source's left edge and enter the target's right edge
    // for a clean short horizontal segment.
    const HANDLE_OVERRIDES: Record<string, { sourceHandle: string; targetHandle: string }> = {
      'scene:evidence->scene:doctrine_binding': {
        sourceHandle: 'bottom-source',
        targetHandle: 'top-target',
      },
      'scene:doctrine_binding->scene:shared_grammar': {
        sourceHandle: 'bottom-source',
        targetHandle: 'top-target',
      },
      'scene:shared_grammar->scene:semantic_objects': {
        sourceHandle: 'left-source',
        targetHandle: 'right-target',
      },
      'scene:semantic_objects->scene:mechanisms': {
        sourceHandle: 'left-source',
        targetHandle: 'right-target',
      },
      'scene:repair->scene:shared_grammar': {
        sourceHandle: 'left-source',
        targetHandle: 'right-target',
      },
    };
    for (const edge of ROOT_SEMANTIC_SCENE_EDGES) {
      const sourceId = `visual:${edge.source}`;
      const targetId = `visual:${edge.target}`;
      const handles = HANDLE_OVERRIDES[`${edge.source}->${edge.target}`];
      edges.push({
        id: `visual-edge:scene:${edge.source}->${edge.target}`,
        source: sourceId,
        target: targetId,
        sourceHandle: handles?.sourceHandle ?? 'right-source',
        targetHandle: handles?.targetHandle ?? 'left-target',
        label: edge.relation,
        ariaLabel: '',
        style: { stroke: 'rgba(199,176,106,0.72)', strokeWidth: 1.5 },
        labelStyle: { fill: '#d8c587', fontSize: 11, letterSpacing: '0.02em' },
        labelBgStyle: { fill: 'rgba(8,13,22,0.94)' },
        labelBgPadding: [5, 7],
        labelBgBorderRadius: 4,
      });
    }
  }

  // Focus mode: render the expanded container as a large compound region and
  // its cluster children inside it. Cluster sizes scale with the number of
  // object children so visually full clusters look heavier than sparse ones.
  // We render the focus container regardless of whether it's already in the
  // substrate model — paper_modules and standards in particular aren't always
  // present in primitive_matrix.rows but they have rich adapter coverage, so
  // they must show up when focused.
  if (expandedKind) {
    const focusContainer = substrateContainers.find((n) => n.kind === expandedKind);
    const focusLabel = focusContainer?.label ?? expandedKind.replace(/_/g, ' ');
    const focusAdapter: RootSemanticGraphAdapter =
      focusContainer?.adapter ?? ADAPTED_KINDS[expandedKind] ?? 'substrate';
    {
      nodes.push({
        id: `visual:focus:${expandedKind}`,
        type: 'unifiedSubstrate',
        position: { x: CANVAS_FOCUS_X, y: CANVAS_FOCUS_Y },
        style: {
          width: CANVAS_FOCUS_WIDTH,
          // LOCAL-mode shell-sizing (reversible, local-only). selectedNode != null
          // is exactly canvasMode==='local' (L8681-8685); size ONLY this
          // transparent scope_hud shell to the local content so fitView stops
          // framing the empty lower band. MODEST centering nudge, not a full fix
          // (see the CANVAS_LOCAL_FOCUS_HEIGHT note + tracked cap). Focus
          // (selectedNode null) and atlas keep the full shell and render
          // byte-identical; fabric children lack extent:'parent' (L8268) so this
          // never clips.
          height: selectedNode ? CANVAS_LOCAL_FOCUS_HEIGHT : CANVAS_FOCUS_HEIGHT,
        },
        draggable: false,
        data: {
          nodeId: expandedKind,
          label: focusLabel,
          secondaryId: expandedKind,
          role: 'substrate_container',
          adapter: focusAdapter,
          parentId: 'root:substrate',
          expanded: true,
          selected: false,
          onSelect,
          accent: unifiedContainerAccent(expandedKind),
          kindMeta: substrateContainerMeta.get(expandedKind),
          // vNext-RD: the focused container is a scope boundary, not a
          // primary semantic-scene node. Clusters/objects/neighbors inside
          // it own the 'primary' zone.
          sceneZone: 'scope_hud',
          // vNext-IX: the focused-kind shell is decorative — operators
          // navigate the kind via the rail or the scope HUD; the canvas
          // shell has no click action.
          clickPayload: { action: 'none', nodeId: expandedKind, kind: expandedKind },
          onGraphAction,
        } satisfies UnifiedFlowNodeData,
      });

      const clusters = graph.nodes.filter(
        (n) => n.role === 'cluster' && n.parentId === expandedKind,
      );

      // vNext-GA: figure out which cluster (if any) should reveal object
      // children. Priority order:
      //   1. activeCluster from ?cluster= URL param
      //   2. the cluster containing the selectedNode (auto-expand path)
      //   3. none — clusters render as collapsed containers only
      // Sibling clusters always render as collapsed boxes when one is active,
      // so the operator sees structural context without an object flood.
      let resolvedActiveCluster: string | null = activeCluster;
      if (!resolvedActiveCluster && selectedNode) {
        const owningCluster = clusters.find((cluster) =>
          graph.nodes.some(
            (n) =>
              n.parentId === cluster.id &&
              (n.secondaryId === selectedNode || n.id === selectedNode),
          ),
        );
        if (owningCluster) {
          resolvedActiveCluster = owningCluster.secondaryId ?? owningCluster.id;
        }
      }

      // vNext-GA: direct-object emission for band=flag generic kinds. When the
      // focused container has direct object children (no clusters), the
      // receipts builder parents them directly under the kind container; we
      // render them as a single grid inside the focused region.
      const directObjects = graph.nodes.filter(
        (n) =>
          (n.role === 'object' ||
            n.role === 'paper_module' ||
            n.role === 'standard_contract' ||
            n.role === 'axiom_candidate' ||
            n.role === 'principle') &&
          n.parentId === expandedKind,
      );
      const objectRelationFabricVisible =
        objectRelationGraph?.receipt === 'ready' &&
        objectRelationGraph.focusKind === expandedKind &&
        (selectedNode !== null ||
          (expandedKind !== 'paper_modules' && expandedKind !== 'standards'));
      if (!selectedNode && !objectRelationFabricVisible && directObjects.length > 0 && clusters.length === 0) {
        directObjects.slice(0, CANVAS_DIRECT_OBJECT_FOCUS_LIMIT).forEach((obj, objIdx) => {
          const col = objIdx % 3;
          const row = Math.floor(objIdx / 3);
          const objSecondary = obj.secondaryId ?? obj.id;
          const isSelected = objSecondary === selectedNode;
          nodes.push({
            id: `visual:${obj.id}`,
            type: 'unifiedObject',
            parentId: `visual:focus:${expandedKind}`,
            extent: 'parent',
            position: {
              x: 42 + col * (CANVAS_OBJECT_WIDTH + 34),
              y: 56 + row * (CANVAS_OBJECT_HEIGHT + 18),
            },
            style: { width: CANVAS_OBJECT_WIDTH, height: CANVAS_OBJECT_HEIGHT + 6 },
            draggable: false,
            data: {
              nodeId: obj.id,
              label: obj.label,
              secondaryId: objSecondary,
              role: obj.role,
              adapter: obj.adapter,
              parentId: expandedKind,
              expanded: false,
              selected: isSelected,
              onSelect,
              accent: unifiedContainerAccent(expandedKind),
              // vNext-IX: object click writes raw id into ?node=, preserves
              // current focus kind, and clears cluster (direct-objects sit
              // directly under the kind, no cluster context).
              clickPayload: {
                action: 'select_object',
                kind: expandedKind,
                rawId: objSecondary,
                nodeId: obj.id,
              },
              onGraphAction,
            } satisfies UnifiedFlowNodeData,
          });
        });
      }

      const activeClusterNode = activeCluster
        ? clusters.find((cluster) => {
            const secondary = cluster.secondaryId ?? cluster.id;
            return activeCluster === secondary || activeCluster === cluster.id;
          }) ?? null
        : null;

      if (activeClusterNode && !selectedNode) {
        const clusterSecondary = activeClusterNode.secondaryId ?? activeClusterNode.id;
        const clusterFlowId = `visual:${activeClusterNode.id}`;
        const summary = clusterSummaryById.get(clusterSecondary) ?? null;
        const objectsInCluster = graph.nodes.filter(
          (n) =>
            (n.role === 'paper_module' ||
              n.role === 'standard_contract' ||
              n.role === 'object') &&
            n.parentId === activeClusterNode.id,
        );

        nodes.push({
          id: clusterFlowId,
          type: 'unifiedClusterSubject',
          parentId: `visual:focus:${expandedKind}`,
          extent: 'parent',
          position: { x: 64, y: 122 },
          style: { width: 390, height: 214 },
          draggable: false,
          data: {
            nodeId: activeClusterNode.id,
            label: activeClusterNode.label,
            secondaryId: clusterSecondary,
            role: 'cluster',
            adapter: activeClusterNode.adapter,
            parentId: expandedKind,
            expanded: true,
            selected: true,
            onSelect,
            accent: unifiedContainerAccent(expandedKind),
            collapseState: 'expanded',
            clusterSummary: summary ?? undefined,
            clickPayload: {
              action: 'expand_cluster',
              kind: expandedKind,
              clusterId: clusterSecondary,
              nodeId: activeClusterNode.id,
            },
            onGraphAction,
          } satisfies UnifiedFlowNodeData,
        });

        nodes.push({
          id: `visual:cluster-lane:${clusterSecondary}:objects`,
          type: 'unifiedObjectLaneLabel',
          parentId: `visual:focus:${expandedKind}`,
          extent: 'parent',
          position: { x: 520, y: 74 },
          style: { width: 600, height: 28 },
          draggable: false,
          selectable: false,
          data: {
            nodeId: `cluster-lane:${clusterSecondary}:objects`,
            label: 'cluster objects',
            secondaryId: clusterSecondary,
            role: 'receipt',
            adapter: 'receipt',
            parentId: expandedKind,
            expanded: false,
            selected: false,
            onSelect,
            accent: '#94a3b8',
            sceneZone: 'primary',
            clickPayload: { action: 'none' },
            laneInfo: { lane: 'focus' },
          } as UnifiedFlowNodeData,
        });

        const visibleObjects = objectsInCluster.slice(0, 12);
        visibleObjects.forEach((obj, objIdx) => {
          const objId = obj.secondaryId ?? obj.id;
          const col = objIdx % 2;
          const row = Math.floor(objIdx / 2);
          const objectFlowId = `visual:${obj.id}`;
          nodes.push({
            id: objectFlowId,
            type: 'unifiedObject',
            parentId: `visual:focus:${expandedKind}`,
            extent: 'parent',
            position: {
              x: 520 + col * 318,
              y: 116 + row * 64,
            },
            style: { width: 292, height: 52 },
            draggable: false,
            data: {
              nodeId: obj.id,
              label: obj.label,
              secondaryId: objId,
              role: obj.role,
              adapter: obj.adapter,
              parentId: activeClusterNode.id,
              expanded: false,
              selected: false,
              onSelect,
              accent: unifiedContainerAccent(expandedKind),
              clickPayload: {
                action: 'select_object',
                kind: expandedKind,
                rawId: objId,
                clusterId: clusterSecondary,
                nodeId: obj.id,
              },
              onGraphAction,
            } satisfies UnifiedFlowNodeData,
          });
          edges.push({
            id: `visual-edge:cluster:${clusterSecondary}->${objId}`,
            source: clusterFlowId,
            target: objectFlowId,
            label: '',
            ariaLabel: '',
            style: {
              stroke: 'rgba(123,199,142,0.54)',
              strokeWidth: 0.9,
              opacity: 0.68,
            },
            zIndex: 1,
            data: {
              relation: 'contains' satisfies RootGraphRelation,
              sourceField: 'cluster.top_ids',
            },
          });
        });

        const hiddenObjectCount = Math.max(0, objectsInCluster.length - visibleObjects.length);
        if (hiddenObjectCount > 0) {
          nodes.push({
            id: `visual:cluster:${clusterSecondary}:object-overflow`,
            type: 'unifiedReceipt',
            parentId: `visual:focus:${expandedKind}`,
            extent: 'parent',
            position: { x: 520, y: 116 + Math.ceil(visibleObjects.length / 2) * 64 },
            style: { width: 292, height: 42 },
            draggable: false,
            data: {
              nodeId: `cluster:${clusterSecondary}:object-overflow`,
              label: `${hiddenObjectCount} more objects · narrow or select one`,
              secondaryId: String(hiddenObjectCount),
              role: 'receipt',
              adapter: 'receipt',
              parentId: expandedKind,
              expanded: false,
              selected: false,
              onSelect,
              accent: '#fbbf24',
              sceneZone: 'receipt',
              clickPayload: { action: 'none' },
            } satisfies UnifiedFlowNodeData,
          });
        }

        const siblingClusters = clusters
          .filter((cluster) => cluster.id !== activeClusterNode.id)
          .slice(0, 4);
        siblingClusters.forEach((cluster, idx) => {
          const siblingSecondary = cluster.secondaryId ?? cluster.id;
          nodes.push({
            id: `visual:cluster-context:${cluster.id}`,
            type: 'unifiedCluster',
            parentId: `visual:focus:${expandedKind}`,
            extent: 'parent',
            position: { x: 1148, y: 116 + idx * 96 },
            style: { width: 150, height: 76 },
            draggable: false,
            data: {
              nodeId: cluster.id,
              label: cluster.label,
              secondaryId: siblingSecondary,
              role: 'cluster',
              adapter: cluster.adapter,
              parentId: expandedKind,
              expanded: false,
              selected: false,
              onSelect,
              accent: unifiedContainerAccent(expandedKind),
              collapseState: 'collapsed',
              clusterSummary: clusterSummaryById.get(siblingSecondary) ?? undefined,
              clickPayload: {
                action: 'expand_cluster',
                kind: expandedKind,
                clusterId: siblingSecondary,
                nodeId: cluster.id,
              },
              onGraphAction,
            } satisfies UnifiedFlowNodeData,
          });
        });
      } else {
        const clusterRenderLimit = selectedNode
          ? CANVAS_CLUSTER_LOCAL_CONTEXT_LIMIT
          : CANVAS_CLUSTER_FOCUS_LIMIT;
        const visibleClusters = (() => {
          if (clusterRenderLimit <= 0) return [] as typeof clusters;
          if (!activeCluster) return clusters.slice(0, clusterRenderLimit);
          const active = clusters.find((cluster) => {
            const secondary = cluster.secondaryId ?? cluster.id;
            return activeCluster === secondary || activeCluster === cluster.id;
          });
          if (!active) return clusters.slice(0, clusterRenderLimit);
          return [
            active,
            ...clusters
              .filter((cluster) => cluster.id !== active.id)
              .slice(0, Math.max(0, clusterRenderLimit - 1)),
          ];
        })();
        const clusterColumnCount = Math.min(3, Math.max(1, visibleClusters.length));
        const clusterGapX = 44;
        const clusterGapY = 34;
        const clusterGridWidth =
          clusterColumnCount * CANVAS_CLUSTER_WIDTH +
          Math.max(0, clusterColumnCount - 1) * clusterGapX;
        const clusterGridX = Math.max(42, Math.floor((CANVAS_FOCUS_WIDTH - clusterGridWidth) / 2));

        visibleClusters.forEach((cluster, clusterIdx) => {
          const clusterSecondary = cluster.secondaryId ?? cluster.id;
          const isClusterActive =
            resolvedActiveCluster !== null &&
            (resolvedActiveCluster === clusterSecondary ||
              resolvedActiveCluster === cluster.id);
          const objectsInCluster = graph.nodes.filter(
            (n) =>
              (n.role === 'paper_module' ||
                n.role === 'standard_contract' ||
                n.role === 'object') &&
              n.parentId === cluster.id,
          );
          const clusterHeight = isClusterActive
            ? Math.max(
                CANVAS_CLUSTER_MIN_HEIGHT,
                32 + Math.min(objectsInCluster.length, 8) * (CANVAS_OBJECT_HEIGHT + 6),
              )
            : CANVAS_CLUSTER_MIN_HEIGHT;
          const clusterCol = clusterIdx % 3;
          const clusterRow = Math.floor(clusterIdx / 3);
          const clusterX = clusterGridX + clusterCol * (CANVAS_CLUSTER_WIDTH + clusterGapX);
          const clusterY = 54 + clusterRow * (CANVAS_CLUSTER_MIN_HEIGHT + clusterGapY);
          const clusterFlowId = `visual:${cluster.id}`;
          const hasSelectedChild = objectsInCluster.some(
            (obj) => obj.secondaryId === selectedNode,
          );
          // vNext-RT: pull cluster summary by the raw secondary id (same key
          // operators pass via ?cluster=<id>). Both the bespoke (paper_modules,
          // standards) and generic adapters feed clusterSummaryById from
          // ConstitutionalMap, so collapsed clusters always carry count +
          // preview labels regardless of adapter.
          const summary = clusterSummaryById.get(clusterSecondary) ?? null;
          nodes.push({
            id: clusterFlowId,
            type: 'unifiedCluster',
            parentId: `visual:focus:${expandedKind}`,
            extent: 'parent',
            position: { x: clusterX, y: clusterY },
            style: { width: CANVAS_CLUSTER_WIDTH, height: clusterHeight },
            draggable: false,
            data: {
              nodeId: cluster.id,
              label: cluster.label,
              secondaryId: clusterSecondary,
              role: 'cluster',
              adapter: cluster.adapter,
              parentId: expandedKind,
              expanded: isClusterActive,
              selected: hasSelectedChild,
              // vNext-GA: cluster clicks set/clear ?cluster=<id>. Toggling the
              // currently-active cluster collapses it. Object children render
              // only when this cluster is active.
              onSelect: (id) => {
                if (id === null) {
                  onClusterToggle(null);
                  return;
                }
                onClusterToggle(isClusterActive ? null : clusterSecondary);
              },
              accent: unifiedContainerAccent(expandedKind),
              collapseState: isClusterActive ? 'expanded' : 'collapsed',
              clusterSummary: summary ?? undefined,
              // vNext-IX: cluster click toggles ?cluster=<raw cluster id>;
              // when this cluster is active, click collapses it; otherwise
              // click expands it (and the resolver handles the toggle).
              clickPayload: {
                action: 'expand_cluster',
                kind: expandedKind,
                clusterId: clusterSecondary,
                nodeId: cluster.id,
              },
              onGraphAction,
            } satisfies UnifiedFlowNodeData,
          });
          if (isClusterActive) {
            objectsInCluster.slice(0, 8).forEach((obj, objIdx) => {
              const objId = obj.secondaryId ?? obj.id;
              const isSelected = objId === selectedNode;
              nodes.push({
                id: `visual:${obj.id}`,
                type: 'unifiedObject',
                parentId: clusterFlowId,
                extent: 'parent',
                position: { x: 12, y: 32 + objIdx * (CANVAS_OBJECT_HEIGHT + 4) },
                style: { width: CANVAS_OBJECT_WIDTH, height: CANVAS_OBJECT_HEIGHT },
                draggable: false,
                data: {
                  nodeId: obj.id,
                  label: obj.label,
                  secondaryId: objId,
                  role: obj.role,
                  adapter: obj.adapter,
                  parentId: cluster.id,
                  expanded: false,
                  selected: isSelected,
                  onSelect,
                  accent: unifiedContainerAccent(expandedKind),
                  // vNext-IX: object click writes raw id + preserves the
                  // active cluster context, so ?cluster= stays set and the
                  // sibling clusters stay collapsed.
                  clickPayload: {
                    action: 'select_object',
                    kind: expandedKind,
                    rawId: objId,
                    clusterId: clusterSecondary,
                    nodeId: obj.id,
                  },
                  onGraphAction,
                } satisfies UnifiedFlowNodeData,
              });
            });
          }
        });

        const hiddenClusterCount = Math.max(0, clusters.length - visibleClusters.length);
        if (!selectedNode && hiddenClusterCount > 0) {
          const overflowIdx = visibleClusters.length;
          const overflowCol = overflowIdx % 3;
          const overflowRow = Math.floor(overflowIdx / 3);
          nodes.push({
            id: `visual:${expandedKind}:cluster-overflow`,
            type: 'unifiedReceipt',
            parentId: `visual:focus:${expandedKind}`,
            extent: 'parent',
            position: {
              x: clusterGridX + overflowCol * (CANVAS_CLUSTER_WIDTH + clusterGapX),
              y: 54 + overflowRow * (CANVAS_CLUSTER_MIN_HEIGHT + clusterGapY),
            },
            style: { width: CANVAS_CLUSTER_WIDTH, height: 54 },
            draggable: false,
            data: {
              nodeId: `${expandedKind}:cluster-overflow`,
              label: `${hiddenClusterCount} more clusters · use rail/search to narrow`,
              secondaryId: `${hiddenClusterCount}`,
              role: 'receipt',
              adapter: 'receipt',
              parentId: expandedKind,
              expanded: false,
              selected: false,
              onSelect,
              accent: '#94a3b8',
              sceneZone: 'cluster',
              clickPayload: { action: 'none' },
            } satisfies UnifiedFlowNodeData,
          });
        }
      }

      if (
        selectedNode &&
        !objectRelationFabricVisible &&
        !nodes.some(
          (n) => (n.data as UnifiedFlowNodeData | undefined)?.secondaryId === selectedNode,
        )
      ) {
        const fallbackRole =
          expandedKind === 'paper_modules'
            ? 'paper_module'
            : expandedKind === 'standards'
              ? 'standard_contract'
              : 'object';
        const fallbackAdapter: RootSemanticGraphAdapter =
          expandedKind === 'paper_modules'
            ? 'paper_modules'
            : expandedKind === 'standards'
              ? 'standards'
              : 'generic_option_surface';
        const fallbackLabel =
          expandedKind === 'paper_modules'
            ? paperModuleReadableLabel(selectedNode)
            : expandedKind === 'standards'
              ? standardReadableLabel(selectedNode)
              : selectedNode;
        nodes.push({
          id: `visual:selected:${expandedKind}:${selectedNode}`,
          type: 'unifiedObject',
          parentId: `visual:focus:${expandedKind}`,
          extent: 'parent',
          position: {
            x: Math.max(42, CANVAS_FOCUS_WIDTH / 2 - 190),
            y: 264,
          },
          style: { width: 380, height: 64 },
          draggable: false,
          data: {
            nodeId: `${expandedKind}:object:${selectedNode}`,
            label: fallbackLabel,
            secondaryId: selectedNode,
            role: fallbackRole,
            adapter: fallbackAdapter,
            parentId: expandedKind,
            expanded: true,
            selected: true,
            onSelect,
            accent: unifiedContainerAccent(expandedKind),
            sceneZone: 'object',
            clickPayload: {
              action: 'select_object',
              kind: expandedKind,
              rawId: selectedNode,
              nodeId: `${expandedKind}:object:${selectedNode}`,
            },
            onGraphAction,
          } satisfies UnifiedFlowNodeData,
        });
      }
    }
  }

  // Visible edges between top-level substrate containers (atlas mode only;
  // hide them in focus mode to keep the focused region readable).
  if (!expandedKind) {
    for (const edge of graph.edges) {
      if (edge.relation === 'contains') continue;
      const sourceVisualId = `visual:${edge.source}`;
      const targetVisualId = `visual:${edge.target}`;
      if (
        !nodes.some((n) => n.id === sourceVisualId) ||
        !nodes.some((n) => n.id === targetVisualId)
      ) {
        continue;
      }
      edges.push({
        id: `visual-edge:${edge.id}`,
        source: sourceVisualId,
        target: targetVisualId,
        label: edge.relation,
        ariaLabel: '',
        style: {
          stroke: edge.evidenceState === 'missing' ? '#fbbf24' : 'rgba(125,211,252,0.55)',
          strokeWidth: 0.9,
        },
        labelStyle: { fill: '#94a3b8', fontSize: 9 },
        labelBgStyle: { fill: 'rgba(8,13,22,0.85)' },
      });
    }
  }

  // Relation neighborhood for the selected object: emit visible neighbor
  // nodes + edges to the right of the focused region. Sourced from the
  // v1.16 card-band fetch (familyNodeCard.rows[0]) so the visual edges
  // correspond to substrate-projected fields the operator can verify by
  // opening the source. Missing data → visible receipt nodes.
  if (expandedKind && selectedNode && cardRow && edgesForSelected.length === 0) {
    const neighborhoodParentId = `visual:focus:${expandedKind}`;
    const selectedFlowId = (() => {
      const match = nodes.find(
        (n) =>
          (n.data as UnifiedFlowNodeData | undefined)?.secondaryId === selectedNode &&
          ((n.data as UnifiedFlowNodeData | undefined)?.role === 'paper_module' ||
            (n.data as UnifiedFlowNodeData | undefined)?.role === 'standard_contract' ||
            (n.data as UnifiedFlowNodeData | undefined)?.role === 'object'),
      );
      return match?.id;
    })();
    if (selectedFlowId) {
      const cardSource = asString(cardRow.source_ref);
      const cardStandardRef = asString(cardRow.standard_ref);
      const topDeps = asStringArray(cardRow.top_dependencies).slice(0, 3);
      const topRdeps = asStringArray(cardRow.top_dependents).slice(0, 3);
      const governingRefs = asRecordSafe(cardRow.governing_refs);
      const governingPrinciples = asStringArray(governingRefs.principles).slice(0, 2);
      const governingStandards = asStringArray(governingRefs.standards).slice(0, 2);
      const navigationContract = asRecordSafe(cardRow.navigation_contract);
      const governedKind = asString(navigationContract.artifact_kind);

      const neighborhoodEntries: Array<{
        id: string;
        label: string;
        relation: RootSemanticGraphReceiptEdge['relation'];
        adapter: RootSemanticGraphAdapter;
      }> = [];
      topDeps.forEach((dep, idx) =>
        neighborhoodEntries.push({
          id: `neighbor:dep:${idx}:${dep}`,
          label: `depends_on · ${dep}`,
          relation: 'depends_on',
          adapter: 'paper_modules',
        }),
      );
      topRdeps.forEach((dep, idx) =>
        neighborhoodEntries.push({
          id: `neighbor:rdep:${idx}:${dep}`,
          label: `depended_on_by · ${dep}`,
          relation: 'depended_on_by',
          adapter: 'paper_modules',
        }),
      );
      governingPrinciples.forEach((pri, idx) =>
        neighborhoodEntries.push({
          id: `neighbor:pri:${idx}:${pri}`,
          label: `governs · ${pri}`,
          relation: 'governs',
          adapter: 'doctrine_binding',
        }),
      );
      governingStandards.forEach((std, idx) =>
        neighborhoodEntries.push({
          id: `neighbor:std:${idx}:${std}`,
          label: `governed_by · ${std}`,
          relation: 'governs',
          adapter: 'standards',
        }),
      );
      if (cardSource) {
        neighborhoodEntries.push({
          id: 'neighbor:source_ref',
          label: `sources · ${cardSource.split('/').pop() ?? cardSource}`,
          relation: 'sources',
          adapter: 'receipt',
        });
      }
      if (cardStandardRef) {
        neighborhoodEntries.push({
          id: 'neighbor:standard_ref',
          label: `standard_ref · ${cardStandardRef.split('/').pop() ?? cardStandardRef}`,
          relation: 'governs',
          adapter: 'standards',
        });
      }
      if (expandedKind === 'standards' && governedKind) {
        neighborhoodEntries.push({
          id: 'neighbor:standards:governs:governed_kind',
          label: `governs · ${governedKind}`,
          relation: 'governs',
          adapter: 'standards',
        });
      }
      if (neighborhoodEntries.length === 0) {
        neighborhoodEntries.push({
          id: 'neighbor:missing_neighborhood',
          label: 'missing · no relation data on card',
          relation: 'missing',
          adapter: 'receipt',
        });
      }
      neighborhoodEntries.forEach((entry, idx) => {
        const flowId = `visual:${entry.id}`;
        nodes.push({
          id: flowId,
          type: 'unifiedReceipt',
          position: {
            x: CANVAS_NEIGHBORHOOD_X,
            y: CANVAS_NEIGHBORHOOD_Y + idx * 44,
          },
          style: { width: 280, height: 38 },
          draggable: false,
          data: {
            nodeId: entry.id,
            label: entry.label,
            secondaryId: entry.id,
            role: 'receipt',
            adapter: entry.adapter,
            parentId: neighborhoodParentId,
            expanded: false,
            selected: false,
            onSelect,
            accent: '#fbbf24',
          } satisfies UnifiedFlowNodeData,
        });
        edges.push({
          id: `visual-edge:relation:${entry.id}`,
          source: selectedFlowId,
          target: flowId,
          label: entry.relation,
          ariaLabel: '',
          style: {
            stroke:
              entry.relation === 'missing'
                ? '#fbbf24'
                : 'rgba(125,211,252,0.85)',
            strokeWidth: entry.relation === 'missing' ? 1.4 : 1.2,
            strokeDasharray: entry.relation === 'missing' ? '4 3' : undefined,
          },
          labelStyle: { fill: '#94a3b8', fontSize: 9 },
          labelBgStyle: { fill: 'rgba(8,13,22,0.85)' },
        });
      });
    }
  }

  // vNext-OF: object relation fabric. When the focused kind carries a
  // RootObjectRelationGraph with receipt='ready' or 'no_edges', emit lane
  // labels + compact focus_object / neighbor_object nodes + typed edges
  // alongside the existing cluster grid. The fabric makes focused views
  // express relation topology (focus → upstream / downstream / governance
  // / source / evidence) instead of a flat atom inventory. When receipt
  // is 'no_edges' or 'missing_rows', a visible receipt node carries the
  // explicit state so the operator sees the missing projection.
  if (
    expandedKind &&
    objectRelationGraph &&
    objectRelationGraph.focusKind === expandedKind &&
    (selectedNode !== null || (expandedKind !== 'paper_modules' && expandedKind !== 'standards'))
  ) {
    const fabric = objectRelationGraph;
    const lanesUsed = new Set<RootObjectLane>();
    for (const node of fabric.nodes) lanesUsed.add(node.lane);
    const selectedSubjectMap = selectedNode !== null;

    // Order lanes left-to-right by canonical lane order so the fabric is
    // readable regardless of which lanes the current focus populates.
    const orderedLanes = OBJECT_GRAPH_LANE_ORDER.filter((l) => lanesUsed.has(l));
    const laneNodeTotals = new Map<RootObjectLane, number>();
    for (const node of fabric.nodes) {
      laneNodeTotals.set(node.lane, (laneNodeTotals.get(node.lane) ?? 0) + 1);
    }
    const fabricLayout = computeRootObjectFabricLayout(
      orderedLanes,
      laneNodeTotals,
      selectedSubjectMap,
    );

    // Lane labels (data-zenith-root-object-graph-lane attrs).
    for (const lane of orderedLanes) {
      const laneLayout = fabricLayout.laneById.get(lane)!;
      nodes.push({
        id: `visual:of:lane:${lane}`,
        type: 'unifiedObjectLaneLabel',
        position: { x: laneLayout.x, y: laneLayout.labelY },
        style: { width: laneLayout.width, height: 28 },
        draggable: false,
        selectable: false,
        data: {
          nodeId: `of:lane:${lane}`,
          label: OBJECT_GRAPH_LANES[lane].label,
          secondaryId: lane,
          role: 'receipt',
          adapter: 'receipt',
          parentId: 'root:substrate',
          expanded: false,
          selected: false,
          onSelect,
          accent: '#94a3b8',
          sceneZone: 'primary',
          clickPayload: { action: 'none' },
          laneInfo: { lane },
          fabricLayout: {
            layoutId: fabricLayout.layoutId,
            lane,
            x: laneLayout.x,
            y: laneLayout.labelY,
            width: laneLayout.width,
            row: -1,
            renderLimit: laneLayout.renderLimit,
            overflow: fabricLayout.overflow,
          },
        } as UnifiedFlowNodeData,
      });
    }

    // Stable per-lane row counters so atoms stack vertically without
    // colliding with siblings in the same lane.
    const laneRowCount = new Map<RootObjectLane, number>();
    const hiddenByLane = new Map<RootObjectLane, number>();
    const renderedFabricNodeLayouts = new Map<
      string,
      { flowId: string; lane: RootObjectLane; x: number; y: number }
    >();

    for (const fNode of fabric.nodes) {
      const lane = fNode.lane;
      const laneLayout = fabricLayout.laneById.get(lane);
      if (!laneLayout) continue;
      const renderLimit = laneLayout.renderLimit;
      const row = laneRowCount.get(lane) ?? 0;
      if (row >= renderLimit) {
        hiddenByLane.set(lane, (hiddenByLane.get(lane) ?? 0) + 1);
        continue;
      }
      laneRowCount.set(lane, row + 1);
      const focusColumn = lane === 'focus' && !selectedSubjectMap ? row % 2 : 0;
      const visualRow = lane === 'focus' && !selectedNode ? Math.floor(row / 2) : row;
      const fabricFlowId = `visual:of:${fNode.id}`;
      const nodeX = laneLayout.x + focusColumn * (laneLayout.nodeWidth + 34);
      const nodeY = selectedSubjectMap && lane === 'focus'
        ? laneLayout.subjectY
        : laneLayout.topY + visualRow * laneLayout.rowHeight;
      const clickPayload: RootGraphClickPayload = (() => {
        if (fNode.nodeKind === 'focus_object') {
          return {
            action: 'select_object',
            kind: fabric.focusKind,
            rawId: fNode.rawId,
            nodeId: fNode.id,
          };
        }
        if (fNode.nodeKind === 'neighbor_object' || fNode.nodeKind === 'standard_ref') {
          const mappedKind = NEIGHBOR_TARGET_KIND_MAP[fNode.kind] ?? null;
          return mappedKind
            ? {
                action: 'select_neighbor',
                kind: mappedKind,
                rawId: fNode.rawId,
                targetKind: fNode.kind,
                nodeId: fNode.id,
              }
            : { action: 'none', targetKind: fNode.kind, nodeId: fNode.id };
        }
        if (fNode.nodeKind === 'governed_kind') {
          return {
            action: 'focus_kind',
            kind: fNode.rawId,
            nodeId: fNode.id,
          };
        }
        return { action: 'none', nodeId: fNode.id };
      })();
      nodes.push({
        id: fabricFlowId,
        type: 'unifiedObjectFabric',
        position: { x: nodeX, y: nodeY },
        style: {
          width: laneLayout.nodeWidth,
          height: selectedSubjectMap && lane === 'focus' ? 112 : 52,
        },
        zIndex: fNode.selected ? 10 : 4,
        draggable: false,
        data: {
          nodeId: fNode.id,
          label: fNode.label,
          secondaryId: fNode.rawId,
          role: 'object',
          adapter: 'generic_option_surface',
          parentId: `visual:focus:${expandedKind}`,
          expanded: false,
          selected: fNode.selected,
          onSelect,
          accent: unifiedContainerAccent(expandedKind),
          sceneZone: fNode.nodeKind === 'focus_object' ? 'object' : 'neighbor',
          clickPayload,
          onGraphAction,
          fabric: {
            nodeKind: fNode.nodeKind,
            lane,
            rawId: fNode.rawId,
            fabricKind: fNode.kind,
            isSelected: fNode.selected,
            relation: fNode.relation,
            sourceField: fNode.sourceField,
          },
          fabricLayout: {
            layoutId: fabricLayout.layoutId,
            lane,
            x: laneLayout.x,
            y: nodeY,
            width: laneLayout.nodeWidth,
            row: visualRow,
            renderLimit: laneLayout.renderLimit,
            overflow: fabricLayout.overflow,
          },
        } as UnifiedFlowNodeData,
      });
      renderedFabricNodeLayouts.set(fNode.id, {
        flowId: fabricFlowId,
        lane,
        x: nodeX,
        y: nodeY,
      });
    }

    hiddenByLane.forEach((hiddenCount, lane) => {
      const row = laneRowCount.get(lane) ?? 0;
      const laneLayout = fabricLayout.laneById.get(lane);
      if (!laneLayout) return;
      nodes.push({
        id: `visual:of:hidden:${lane}`,
        type: 'unifiedReceipt',
        position: {
          x: laneLayout.x,
          y: laneLayout.topY + row * laneLayout.rowHeight,
        },
        style: { width: laneLayout.nodeWidth, height: 42 },
        draggable: false,
        data: {
          nodeId: `of:hidden:${lane}`,
          label: `${hiddenCount} more ${OBJECT_GRAPH_LANES[lane].label.toLowerCase()}`,
          secondaryId: String(hiddenCount),
          role: 'receipt',
          adapter: 'receipt',
          parentId: `visual:focus:${expandedKind}`,
          expanded: false,
          selected: false,
          onSelect,
          accent: '#fbbf24',
          sceneZone: 'receipt',
          clickPayload: { action: 'none' },
        } satisfies UnifiedFlowNodeData,
      });
    });

    // Visible typed edges. React Flow edges carry data-attrs via the
    // standard edge id; the visible neighborhood-receipt pill strip
    // already mirrors them for selector-friendly testing. We also paint
    // the relation on the edge label so the operator sees the type.
    const selectedFabricNodeIds = new Set(
      fabric.nodes.filter((node) => node.selected).map((node) => node.id),
    );
    const fabricNodeById = new Map(fabric.nodes.map((node) => [node.id, node]));
    const selectedIncidentEdges = selectedSubjectMap
      ? fabric.edges.filter(
          (edge) =>
            selectedFabricNodeIds.has(edge.source) ||
            selectedFabricNodeIds.has(edge.target),
        )
      : [];
    const renderedFabricEdges: RootObjectRelationEdge[] = [];
    const renderedEdgeCountsByLane = new Map<RootObjectLane, number>();
    for (const edge of selectedIncidentEdges) {
      const otherId = selectedFabricNodeIds.has(edge.source) ? edge.target : edge.source;
      const otherLane = fabricNodeById.get(otherId)?.lane ?? 'focus';
      if (otherLane === 'focus') continue;
      const maxForLane = otherLane === 'source' || otherLane === 'evidence' ? 1 : 2;
      const current = renderedEdgeCountsByLane.get(otherLane) ?? 0;
      if (current >= maxForLane) continue;
      renderedEdgeCountsByLane.set(otherLane, current + 1);
      renderedFabricEdges.push(edge);
      if (renderedFabricEdges.length >= 6) break;
    }

    for (const fEdge of renderedFabricEdges) {
      const sourceLayout = renderedFabricNodeLayouts.get(fEdge.source);
      const targetLayout = renderedFabricNodeLayouts.get(fEdge.target);
      if (!sourceLayout || !targetLayout) continue;
      const renderForward = sourceLayout.x <= targetLayout.x;
      const sourceFlowId = renderForward ? sourceLayout.flowId : targetLayout.flowId;
      const targetFlowId = renderForward ? targetLayout.flowId : sourceLayout.flowId;
      // Only render edges where both endpoints actually rendered (cap
      // protection: a node may have been dropped if focusRows exceeded
      // OBJECT_GRAPH_CAP_FOCUS).
      if (!nodes.some((n) => n.id === sourceFlowId)) continue;
      if (!nodes.some((n) => n.id === targetFlowId)) continue;
      // vNext-LG: color fabric edges by relation family so the operator can
      // read substrate role from the line color. Matches the edge-legend
      // overlay's color codes: depends_on/implements=cyan, governs/
      // governed_by=amber, sources/evidence=grey, related_to/compresses=
      // green, missing=dashed-amber.
      const edgeStroke =
        fEdge.relation === 'missing'
          ? '#fbbf24'
          : fEdge.relation === 'depends_on' ||
              fEdge.relation === 'depended_on_by' ||
              fEdge.relation === 'implements' ||
              fEdge.relation === 'implemented_by' ||
              fEdge.relation === 'instantiates'
            ? 'rgba(125,211,252,0.85)'
            : fEdge.relation === 'governs' ||
                fEdge.relation === 'governed_by'
              ? 'rgba(251,191,36,0.85)'
              : fEdge.relation === 'sources'
                ? 'rgba(148,163,184,0.85)'
                : fEdge.relation === 'related_to' ||
                    fEdge.relation === 'compresses' ||
                    fEdge.relation === 'compressed_by' ||
                    fEdge.relation === 'explains'
                  ? 'rgba(123,199,142,0.85)'
                  : 'rgba(125,211,252,0.65)';
      edges.push({
        id: `visual-of-edge:${fEdge.id}`,
        source: sourceFlowId,
        target: targetFlowId,
        label: '',
        ariaLabel: '',
        style: {
          stroke: edgeStroke,
          strokeWidth: 0.85,
          opacity: 0.7,
          strokeDasharray: fEdge.relation === 'missing' ? '4 3' : undefined,
        },
        zIndex: 1,
        labelStyle: { fill: '#94a3b8', fontSize: 8 },
        labelBgStyle: { fill: 'rgba(8,13,22,0.85)' },
        data: {
          relation: fEdge.relation,
          sourceField: fEdge.sourceField,
        },
      });
    }
  }

  // vNext-RT: relation-bearing semantic neighborhood. When a node is selected
  // and edgesForSelected has typed edges from flag/card row fields, emit
  // visible neighbor nodes (role='neighbor') with React Flow edges so the
  // operator sees the relation topology, not only a bottom-strip pill list.
  // This is the visual answer to "grid of chips with no relations" — every
  // selected object now expresses its dependency/governance/source structure
  // as graph nodes and edges instead of hidden receipt-only metadata.
  if (
    expandedKind &&
    selectedNode &&
    edgesForSelected.length > 0 &&
    !(objectRelationGraph?.receipt === 'ready' && objectRelationGraph.focusKind === expandedKind)
  ) {
    const selectedFlowId = (() => {
      const match = nodes.find(
        (n) =>
          (n.data as UnifiedFlowNodeData | undefined)?.secondaryId === selectedNode &&
          ((n.data as UnifiedFlowNodeData | undefined)?.role === 'paper_module' ||
            (n.data as UnifiedFlowNodeData | undefined)?.role === 'standard_contract' ||
            (n.data as UnifiedFlowNodeData | undefined)?.role === 'object' ||
            (n.data as UnifiedFlowNodeData | undefined)?.role === 'axiom_candidate' ||
            (n.data as UnifiedFlowNodeData | undefined)?.role === 'principle'),
      );
      return match?.id;
    })();
    if (selectedFlowId) {
      const RT_NEIGHBOR_X_BASE = CANVAS_NEIGHBORHOOD_X;
      const RT_NEIGHBOR_Y_BASE = 80;
      const RT_NEIGHBOR_ROW_HEIGHT = 50;
      const capped = edgesForSelected.slice(0, 12);
      capped.forEach((edge, idx) => {
        const flowNodeId = `visual:rt-neighbor:${edge.id}`;
        // vNext-IX: neighbor target-kind → artifact kind. If the target kind
        // maps to a known artifact kind, the neighbor click navigates to
        // that kind + selects the raw target id. Otherwise the click stays
        // a no-op so source/code_locus/evidence neighbors don't write
        // garbage routes.
        const mappedKind = NEIGHBOR_TARGET_KIND_MAP[edge.targetKind] ?? null;
        const neighborRawId = edge.targetId.replace(new RegExp(`^${edge.targetKind}:`), '');
        const neighborClick: RootGraphClickPayload = mappedKind
          ? {
              action: 'select_neighbor',
              kind: mappedKind,
              rawId: neighborRawId,
              targetKind: edge.targetKind,
              relation: edge.relation,
              nodeId: edge.targetId,
            }
          : {
              action: 'none',
              targetKind: edge.targetKind,
              relation: edge.relation,
              nodeId: edge.targetId,
            };
        nodes.push({
          id: flowNodeId,
          type: 'unifiedObject',
          position: {
            x: RT_NEIGHBOR_X_BASE,
            y: RT_NEIGHBOR_Y_BASE + idx * RT_NEIGHBOR_ROW_HEIGHT,
          },
          style: { width: 260, height: 40 },
          draggable: false,
          data: {
            nodeId: edge.targetId,
            label: edge.targetLabel,
            secondaryId: edge.targetId.split(':').slice(1).join(':') || edge.targetId,
            role: 'object',
            adapter: 'generic_option_surface',
            parentId: selectedFlowId,
            expanded: false,
            selected: false,
            onSelect,
            accent: unifiedContainerAccent(expandedKind),
            neighbor: {
              targetKind: edge.targetKind,
              relation: edge.relation,
              sourceField: edge.sourceField,
            },
            clickPayload: neighborClick,
            onGraphAction,
          } satisfies UnifiedFlowNodeData,
        });
        edges.push({
        id: `visual-edge:rt-relation:${edge.id}`,
        source: selectedFlowId,
        target: flowNodeId,
        label: '',
        ariaLabel: '',
          style: {
            stroke:
              edge.relation === 'missing'
                ? '#fbbf24'
                : 'rgba(125,211,252,0.85)',
            strokeWidth: 1.2,
          strokeDasharray: edge.relation === 'missing' ? '4 3' : undefined,
        },
        labelStyle: { fill: '#94a3b8', fontSize: 9 },
        labelBgStyle: { fill: 'rgba(8,13,22,0.85)' },
        data: {
          relation: edge.relation,
          sourceField: edge.sourceField,
        },
      });
      });
    }
  }

  return { nodes, edges };
}

interface RootUnifiedSystemGraphCanvasProps {
  graph: {
    nodes: RootSemanticGraphReceiptNode[];
    edges: RootSemanticGraphReceiptEdge[];
  };
  expandedKind: string | null;
  selectedNode: string | null;
  // vNext-GA: ?cluster=<id> for single-cluster expansion. Click a cluster
  // node to toggle this param via onClusterToggle.
  activeCluster: string | null;
  onSelectNode: (id: string | null) => void;
  onSelectAtlasContainer: (kind: string) => void;
  onClusterToggle: (clusterId: string | null) => void;
  onOpenKindLens: (kind: string) => void;
  onBackToAtlas: () => void;
  // vNext-IX: typed object/neighbor selection. Writes raw id (never
  // internal graph id) to ?node= and preserves focus + cluster context.
  onSelectGraphObject: (kind: string, rawId: string | null, clusterId?: string | null) => void;
  cardRow: UnknownRow | null;
  cardStatus: 'idle' | 'loading' | 'ready' | 'error';
  substrateContainerMeta: Map<string, { rowCount: number | null; status: string }>;
  // vNext-RT: per-cluster summary + extracted relation edges for the selected
  // object. Both feed the visible flow so cluster shells aren't blank and
  // selected objects show a real neighbor graph.
  clusterSummaryById: Map<string, ClusterSummaryEntry>;
  edgesForSelected: GenericGraphEdgeCandidate[];
  // vNext-OF: object relation fabric for the focused kind.
  objectRelationGraph: RootObjectRelationGraph | null;
}

function RootUnifiedSystemGraphCanvasInner({
  graph,
  expandedKind,
  selectedNode,
  activeCluster,
  onSelectNode,
  onSelectAtlasContainer,
  onClusterToggle,
  onOpenKindLens,
  onBackToAtlas,
  onSelectGraphObject,
  cardRow,
  cardStatus,
  substrateContainerMeta,
  clusterSummaryById,
  edgesForSelected,
  objectRelationGraph,
}: RootUnifiedSystemGraphCanvasProps) {
  const reactFlow = useReactFlow();
  const nodesInitialized = useNodesInitialized();
  const recenterKeyRef = useRef<string | null>(null);
  const handleSelect = useCallback(
    (id: string | null) => {
      if (id === null) {
        onSelectNode(null);
        return;
      }
      // Top-level substrate container: route through onSelectAtlasContainer so
      // ?graph=substrate&focus=<kind> takes over; this expands the container in
      // the same canvas (no dispatch to a per-kind selector grid).
      if (!expandedKind && graph.nodes.some((n) => n.role === 'substrate_container' && n.kind === id)) {
        onSelectAtlasContainer(id);
        return;
      }
      onSelectNode(id);
    },
    [expandedKind, graph.nodes, onSelectAtlasContainer, onSelectNode],
  );

  // vNext-IX: central click resolver. Every visible node dispatches a typed
  // RootGraphClickPayload here; the resolver routes the payload into the
  // right URL setter / Inspector update / focus change. Object payloads
  // carry raw ids — never internal graph ids — so ?node= matches the
  // option-surface row ids and card-band fetches resolve.
  const handleGraphAction = useCallback(
    (payload: RootGraphClickPayload) => {
      switch (payload.action) {
        case 'focus_kind':
        case 'open_scene_role':
          if (payload.kind) onSelectAtlasContainer(payload.kind);
          return;
        case 'expand_cluster':
          if (payload.clusterId) {
            // Toggle: clicking the active cluster collapses it.
            if (payload.clusterId === activeCluster) {
              onClusterToggle(null);
            } else {
              onClusterToggle(payload.clusterId);
            }
          } else {
            onClusterToggle(null);
          }
          return;
        case 'select_object':
          if (payload.kind && payload.rawId) {
            onSelectGraphObject(payload.kind, payload.rawId, payload.clusterId ?? null);
          }
          return;
        case 'select_neighbor':
          if (payload.kind && payload.rawId) {
            onSelectGraphObject(payload.kind, payload.rawId, null);
          }
          return;
        case 'open_kind_lens':
          if (payload.kind) onOpenKindLens(payload.kind);
          return;
        case 'none':
        default:
          return;
      }
    },
    [activeCluster, onClusterToggle, onOpenKindLens, onSelectAtlasContainer, onSelectGraphObject],
  );

  const flow = useMemo(
    () =>
      buildVisibleUnifiedGraphFlow({
        graph,
        objectRelationGraph,
        expandedKind,
        selectedNode,
        activeCluster,
        onSelect: handleSelect,
        onClusterToggle,
        onGraphAction: handleGraphAction,
        cardRow,
        substrateContainerMeta,
        clusterSummaryById,
        edgesForSelected,
      }),
    [
      graph,
      objectRelationGraph,
      expandedKind,
      selectedNode,
      activeCluster,
      handleSelect,
      onClusterToggle,
      handleGraphAction,
      cardRow,
      substrateContainerMeta,
      clusterSummaryById,
      edgesForSelected,
    ],
  );

  const canvasMode: 'atlas' | 'focus' | 'local' = !expandedKind
    ? 'atlas'
    : selectedNode
      ? 'local'
      : 'focus';
  const clusterFocusMode =
    expandedKind && activeCluster && !selectedNode ? 'selected_cluster_map' : '';

  // Recenter on drill / relation-follow (operator ask: "relation links should
  // recenter"). The declarative fitView prop already frames the initial atlas;
  // this effect re-fits only when the scope changes — a role is drilled, a
  // cluster opened, or a relation link selects a new node — so the camera
  // follows the operator instead of stranding the new focus off-screen. Gated
  // on useNodesInitialized so the imperative fit runs after React Flow has
  // measured node dims (an earlier fit point-fits / no-ops). The first settled
  // frame is recorded without acting, so it never fights the initial fit.
  useEffect(() => {
    if (!nodesInitialized) return;
    const key = `${canvasMode}:${expandedKind ?? ''}:${selectedNode ?? ''}:${activeCluster ?? ''}`;
    const isFirst = recenterKeyRef.current === null;
    if (recenterKeyRef.current === key) return;
    recenterKeyRef.current = key;
    if (isFirst) return;
    reactFlow.fitView({
      padding: canvasMode === 'local' ? 0.12 : canvasMode === 'focus' ? 0.1 : 0.12,
      // Atlas Focus Frame: sparse selected neighborhoods (a node + its sources)
      // and small family grids were capped so low they sat as a tiny island in a
      // large dark canvas while the inspector dominated. Raise the local/focus
      // fit ceilings so the graph fills the canvas. maxZoom is a CAP, so dense
      // scopes still fit below it — only sparse ones zoom up. Atlas overview keeps
      // its 1× legibility ceiling untouched.
      maxZoom: canvasMode === 'local' ? 1.45 : canvasMode === 'focus' ? 1.08 : ROOT_SEMANTIC_SCENE_ATLAS_FIT_MAX_ZOOM,
      duration: 260,
    });
  }, [nodesInitialized, reactFlow, canvasMode, expandedKind, selectedNode, activeCluster]);

  const visibleEdgeReceipts = useMemo(() => {
    // A floating visible "neighborhood receipts" strip that mirrors the React
    // Flow edges as accessible DOM elements with data-zenith-root-graph-visual-
    // edge attrs. React Flow renders edges as SVG without easy data-attr hooks;
    // these visible pills are the testable visible-edge contract.
    return flow.edges
      .map((edge) => ({
        id: edge.id,
        source: typeof edge.source === 'string' ? edge.source : '',
        target: typeof edge.target === 'string' ? edge.target : '',
        relation:
          typeof (edge.data as { relation?: unknown } | undefined)?.relation === 'string'
            ? (edge.data as { relation: string }).relation
            : typeof edge.label === 'string'
              ? edge.label
              : 'contains',
      }))
      .filter((edge) => edge.relation !== 'contains');
  }, [flow.edges]);
  const suppressRelationPills =
    objectRelationGraph?.focusKind === 'axiom_candidates' ||
    objectRelationGraph?.focusKind === 'principles';
  const visibleEdgePills = canvasMode === 'local' && !suppressRelationPills
    ? visibleEdgeReceipts.slice(0, 8)
    : [];
  const objectRelationLayoutMode =
    objectRelationGraph?.receipt === 'ready'
      ? canvasMode === 'local'
        ? 'bounded_subject_lanes'
        : 'bounded_overview_lanes'
      : '';

  return (
    <div
      className="relative h-full w-full"
      data-zenith-view-region="dominant_artifact"
      data-zenith-view-region-role="root_unified_graph_canvas"
      data-zenith-view-region-mode="persistent"
      data-zenith-root-unified-graph-canvas="visible"
      data-zenith-root-unified-graph-canvas-mode={canvasMode}
      data-zenith-root-unified-graph-canvas-node-count={flow.nodes.length}
      data-zenith-root-unified-graph-canvas-edge-count={flow.edges.length}
      data-zenith-root-unified-graph-selected={selectedNode ?? ''}
      data-zenith-root-unified-graph-expanded-kind={expandedKind ?? ''}
      data-zenith-root-unified-graph-expanded-cluster={activeCluster ?? ''}
      data-zenith-root-cluster-focus-mode={clusterFocusMode}
      data-zenith-root-cluster-focus-cluster={clusterFocusMode ? activeCluster ?? '' : ''}
      data-zenith-root-semantic-scene="ready"
      data-zenith-root-semantic-scene-mode={!expandedKind ? 'overview' : 'focus'}
      data-zenith-root-semantic-scene-density={!expandedKind ? 'expanded_overview' : ''}
      data-zenith-root-semantic-scene-node-width={!expandedKind ? ROOT_SEMANTIC_SCENE_NODE_WIDTH : ''}
      data-zenith-root-semantic-scene-node-height={!expandedKind ? ROOT_SEMANTIC_SCENE_NODE_HEIGHT : ''}
      data-zenith-root-semantic-scene-fit-max-zoom={!expandedKind ? ROOT_SEMANTIC_SCENE_ATLAS_FIT_MAX_ZOOM : ''}
      data-zenith-root-object-relation-graph={objectRelationGraph ? objectRelationGraph.receipt : ''}
      data-zenith-root-object-relation-kind={objectRelationGraph?.focusKind ?? ''}
      data-zenith-root-object-relation-node-count={objectRelationGraph?.nodes.length ?? 0}
      data-zenith-root-object-relation-edge-count={objectRelationGraph?.edges.length ?? 0}
      data-zenith-root-object-relation-display-mode={canvasMode === 'local' ? 'selected_subject_map' : canvasMode}
      data-zenith-root-object-relation-visible-edge-count={visibleEdgeReceipts.length}
      data-zenith-root-object-relation-layout={objectRelationLayoutMode}
    >
      <ReactFlow
        nodes={flow.nodes}
        edges={flow.edges}
        nodeTypes={UNIFIED_GRAPH_NODE_TYPES}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        // M4: unified-system-graph telemetry canvas. Node click is the
        // primary affordance; edges are read-only relations. Apply the
        // wayfinding-map a11y contract; ariaLabel:'' is set on each
        // edge in the buildVisibleUnifiedFlow push sites. Per
        // cap_quick_extend_wayfinding_map_a11y_contract_acro_863da57484ec.
        edgesFocusable={false}
        disableKeyboardA11y
        minZoom={canvasMode === 'atlas' ? 0.42 : 0.48}
        maxZoom={canvasMode === 'local' ? 1.55 : 1.35}
        fitView
        fitViewOptions={{
          padding: canvasMode === 'local' ? 0.12 : canvasMode === 'focus' ? 0.1 : 0.08,
          maxZoom: canvasMode === 'local' ? 1.45 : canvasMode === 'focus' ? 1.08 : ROOT_SEMANTIC_SCENE_ATLAS_FIT_MAX_ZOOM,
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={28}
          size={1}
          color="rgba(226,232,240,0.08)"
        />
      </ReactFlow>
      {flow.nodes.length === 0 && (
        <div
          className="pointer-events-none absolute inset-0 flex items-center justify-center"
          data-zenith-root-unified-graph-canvas-loading="ready"
          aria-busy="true"
        >
          <div
            className="pointer-events-auto w-[420px] max-w-[88%] rounded-[var(--zenith-radius-2xs)] border border-zenith-edge bg-black/72 p-5 shadow-[0_28px_72px_rgba(0,0,0,0.55)]"
            style={{ animation: 'cockpit-fade 320ms ease-out both' }}
          >
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-[#c7b06a]/85">
              <span className="dot-live" aria-hidden style={{ background: '#c7b06a', boxShadow: '0 0 12px rgba(199,176,106,0.55)' }} />
              <span>root navigator · resolving</span>
            </div>
            <h3 className="mt-2 text-[13px] font-semibold leading-5 text-white/92">
              Resolving the constitutional atlas of the cognitive substrate
            </h3>
            <p className="mt-1.5 text-[11px] leading-[18px] text-zenith-soft">
              Reading primitive axes, semantic scene domains, and root coverage so the atlas can render
              evidence → doctrine → grammar → meaning → mechanism as one map.
            </p>
            <div className="mt-3 space-y-2" aria-hidden>
              <div className="flex items-center gap-2">
                <div className="skeleton" style={{ width: 18, height: 18, borderRadius: 4 }} />
                <div className="flex-1 space-y-1">
                  <div className="skeleton skeleton-line" style={{ width: '74%' }} />
                  <div className="skeleton skeleton-line" style={{ width: '52%', opacity: 0.7 }} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="skeleton" style={{ width: 18, height: 18, borderRadius: 4 }} />
                <div className="flex-1 space-y-1">
                  <div className="skeleton skeleton-line" style={{ width: '66%' }} />
                  <div className="skeleton skeleton-line" style={{ width: '44%', opacity: 0.7 }} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="skeleton" style={{ width: 18, height: 18, borderRadius: 4 }} />
                <div className="flex-1 space-y-1">
                  <div className="skeleton skeleton-line" style={{ width: '60%' }} />
                  <div className="skeleton skeleton-line" style={{ width: '38%', opacity: 0.7 }} />
                </div>
              </div>
            </div>
            <div className="mt-3 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
              <span>read-only · projection</span>
              <span>holding the cockpit live</span>
            </div>
          </div>
        </div>
      )}
      {/* Visible neighborhood receipts: mirror React Flow edges as data-attr-
          carrying DOM elements so tests can target visible edges without
          scraping React Flow SVG internals. These pills sit in a small floating
          strip; they are visibly part of the canvas, not sr-only. */}
      {visibleEdgePills.length > 0 && (
        <div
          className="pointer-events-none absolute left-3 top-16 flex max-w-[560px] flex-wrap gap-1.5"
          data-zenith-root-unified-graph-visible-edges="ready"
        >
          {visibleEdgePills.map((edge) => (
            <span
              key={edge.id}
              data-zenith-root-graph-visual-edge={edge.id}
              data-zenith-root-graph-visual-edge-source={edge.source.replace(/^visual:/, '')}
              data-zenith-root-graph-visual-edge-target={edge.target.replace(/^visual:/, '')}
              data-zenith-root-graph-visual-edge-relation={edge.relation}
              className={clsx(
                'pointer-events-auto rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em]',
                edge.relation === 'missing'
                  ? 'border-amber-300/30 bg-amber-300/[0.08] text-amber-100/85'
                  : 'border-cyan-300/25 bg-cyan-400/[0.06] text-cyan-100/75',
              )}
              title={`${edge.source} → ${edge.target}`}
            >
              {edge.relation}
            </span>
          ))}
        </div>
      )}
      <div className="pointer-events-none absolute left-3 top-3 max-w-[440px] rounded-[3px] border border-zenith-edge bg-black/55 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft">
        {canvasMode === 'atlas'
          ? 'semantic scene · click a role to drill in'
          : canvasMode === 'focus'
            ? `expanded · ${expandedKind?.replace(/_/g, ' ')} · click a cluster object to select`
            : `selected · ${selectedNode} · neighborhood from card-band${cardStatus === 'loading' ? ' (loading)' : ''}`}
      </div>
      {expandedKind && (
        <div
          className="pointer-events-none absolute right-3 top-12 flex max-w-[260px] flex-col gap-1 rounded-[3px] border border-[#c7b06a]/30 bg-black/72 px-2 py-1.5 font-mono text-[10px] text-white/75"
          data-zenith-root-scene-scope-hud="ready"
          data-zenith-root-scene-scope-kind={expandedKind}
          data-zenith-root-scene-scope-adapter={
            substrateContainerMeta.get(expandedKind)?.rowCount && substrateContainerMeta.get(expandedKind)!.rowCount! > 0
              ? 'generic_option_surface'
              : 'substrate'
          }
          data-zenith-root-scene-scope-row-count={substrateContainerMeta.get(expandedKind)?.rowCount ?? ''}
          data-zenith-root-scene-scope-active-cluster={activeCluster ?? ''}
        >
          <div className="flex items-baseline justify-between gap-2 uppercase tracking-[0.16em] text-[#c7b06a]/85">
            <span>scope</span>
            <span className="text-zenith-muted">{canvasMode}</span>
          </div>
          <div className="truncate text-[11px] font-semibold text-white">{expandedKind.replace(/_/g, ' ')}</div>
          <div className="flex items-baseline gap-3 text-[9.5px] text-zenith-soft">
            <span>rows · {substrateContainerMeta.get(expandedKind)?.rowCount ?? '—'}</span>
            {activeCluster && <span>cluster · {activeCluster}</span>}
            {selectedNode && <span>node · {selectedNode.slice(0, 18)}{selectedNode.length > 18 ? '…' : ''}</span>}
          </div>
        </div>
      )}
      {expandedKind && (
        <button
          type="button"
          onClick={onBackToAtlas}
          className="absolute right-3 top-3 rounded border border-white/12 bg-black/55 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft hover:border-cyan-300/45 hover:text-cyan-100"
          data-zenith-root-unified-graph-canvas-back="atlas"
        >
          ← back to atlas
        </button>
      )}
      {/* vNext-LG: edge legend overlay. Color-keyed relation names anchored
          along the canvas bottom-left so operators can read what the edge
          colors mean. Pure HTML — does not consume React Flow space. */}
      {expandedKind && canvasMode === 'local' && objectRelationGraph && objectRelationGraph.edges.length > 0 && (
        <div
          className="pointer-events-none absolute left-3 bottom-3 flex items-center gap-3 rounded-[3px] border border-zenith-edge bg-black/72 px-2 py-1 font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-soft"
          data-zenith-root-edge-legend="ready"
        >
          <span className="text-zenith-muted">edges</span>
          <span className="flex items-center gap-1.5" data-zenith-root-edge-legend-entry="depends_on">
            <span className="inline-block h-[2px] w-5 rounded" style={{ background: 'rgba(125,211,252,0.85)' }} />
            <span className="text-zenith-soft">depends_on / implements</span>
          </span>
          <span className="flex items-center gap-1.5" data-zenith-root-edge-legend-entry="governed_by">
            <span className="inline-block h-[2px] w-5 rounded" style={{ background: 'rgba(251,191,36,0.85)' }} />
            <span className="text-zenith-soft">governs / governed_by</span>
          </span>
          <span className="flex items-center gap-1.5" data-zenith-root-edge-legend-entry="sources">
            <span className="inline-block h-[2px] w-5 rounded" style={{ background: 'rgba(148,163,184,0.85)' }} />
            <span className="text-zenith-soft">sources / evidence</span>
          </span>
          <span className="flex items-center gap-1.5" data-zenith-root-edge-legend-entry="related_to">
            <span className="inline-block h-[2px] w-5 rounded" style={{ background: 'rgba(123,199,142,0.85)' }} />
            <span className="text-zenith-soft">related_to</span>
          </span>
          <span className="flex items-center gap-1.5" data-zenith-root-edge-legend-entry="missing">
            <span className="inline-block h-[2px] w-5 rounded border border-amber-300/55" style={{ background: 'transparent', borderStyle: 'dashed' }} />
            <span className="text-zenith-soft">missing</span>
          </span>
        </div>
      )}
      {/* vNext-LG: missing-relations receipt strip. Surfaces unrealized
          relation projections as dashed receipt pills along the canvas
          bottom-right. Anchored to objectRelationGraph.receipt so a
          'no_edges' or 'missing_rows' state becomes a visible artifact
          instead of a silent attribute. */}
      {expandedKind && canvasMode === 'local' && objectRelationGraph && objectRelationGraph.receipt !== 'ready' && (
        <div
          className="pointer-events-none absolute right-3 bottom-3 flex items-center gap-2 rounded-[3px] border border-amber-300/30 bg-black/72 px-2 py-1 font-mono text-[9px] uppercase tracking-[0.14em] text-amber-200/75"
          data-zenith-root-object-graph-missing-strip="ready"
          data-zenith-root-object-graph-missing-state={objectRelationGraph.receipt}
        >
          <span className="text-amber-200/55">missing relations</span>
          <span
            className="rounded-[2px] border border-amber-300/35 border-dashed px-1.5 py-[1px] text-amber-200/85"
            data-zenith-root-object-graph-missing-entry={objectRelationGraph.receipt}
          >
            {objectRelationGraph.receipt === 'no_edges'
              ? 'no relation edges projected · check card-band'
              : objectRelationGraph.receipt === 'missing_rows'
                ? 'no rows in substrate · open kind lens'
                : 'loading projection…'}
          </span>
        </div>
      )}
    </div>
  );
}

function RootUnifiedSystemGraphCanvas(props: RootUnifiedSystemGraphCanvasProps) {
  return (
    <ReactFlowProvider>
      <RootUnifiedSystemGraphCanvasInner {...props} />
    </ReactFlowProvider>
  );
}

function ConstitutionalMap({
  packet,
  axes,
  viewModel,
  onSelectKind,
  onSelectInspectorTab,
  selectedPrimitive,
  selectedAxis,
  drilldownRowCount,
  selectedRow,
  drilldownPacket,
  drilldownLoading,
  drilldownError,
  cardPacket,
  cardLoading,
  cardError,
  onSelectRow,
  memberPreviewRowsById,
  substrateGraphMode,
  substrateGraphFocus,
  substrateFamilyNode,
  substrateGraphCluster,
  onSelectAtlasContainer,
  onOpenKindLens,
  onSelectFamilyNode,
  onSelectGraphCluster,
  onSelectGraphObject,
  onBackToAtlas,
  familyNodeCard,
  familyNodeCardStatus,
  depthPresentation = 'default',
}: ConstitutionalMapProps) {
  const { worldModel, refreshWorldModel } = useZenith();
  const familyMode = substrateGraphMode === 'family' && substrateGraphFocus !== null && !selectedPrimitive;
  const familyFocusKind = familyMode ? substrateGraphFocus : null;
  const deepDetailPresentation = depthPresentation === 'deep_detail';
  const [familyAxioms, setFamilyAxioms] = useState<FamilyAxiomCandidate[]>([]);
  const [familyAxiomLoading, setFamilyAxiomLoading] = useState(false);
  const [familyAxiomError, setFamilyAxiomError] = useState<string | null>(null);
  useEffect(() => {
    if (familyFocusKind !== 'axiom_candidates') {
      setFamilyAxioms([]);
      setFamilyAxiomError(null);
      setFamilyAxiomLoading(false);
      return;
    }
    let cancelled = false;
    setFamilyAxiomLoading(true);
    setFamilyAxiomError(null);
    const path = deriveFamilyAxiomPath(worldModel?.principles_family?.path);
    api.codex
      .getFile(path)
      .then((file) => {
        if (cancelled) return;
        setFamilyAxioms(parseFamilyAxiomCandidates(file.content ?? ''));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setFamilyAxioms([]);
        setFamilyAxiomError(err instanceof Error ? err.message : 'Failed to load axiom candidates');
      })
      .finally(() => {
        if (!cancelled) setFamilyAxiomLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyFocusKind, worldModel?.principles_family?.path]);

  useEffect(() => {
    if (familyFocusKind && !worldModel && typeof refreshWorldModel === 'function') {
      void refreshWorldModel();
    }
  }, [familyFocusKind, worldModel, refreshWorldModel]);

  const familyPrinciples: FamilyPrincipleNode[] = useMemo(() => {
    if (!familyFocusKind) return [];
    const list = worldModel?.principles_family?.principles ?? [];
    const referenced = new Set<string>();
    for (const axiom of familyAxioms) {
      for (const id of axiom.relatedPrinciples) referenced.add(id);
    }
    if (list.length === 0) {
      return Array.from(referenced)
        .sort()
        .slice(0, 60)
        .map((id) => ({ id, title: id, statement: '', scope: '', status: '' } satisfies FamilyPrincipleNode));
    }
    const sorted = [...list].sort((a, b) => {
      const aRef = referenced.has(a.id) ? 0 : 1;
      const bRef = referenced.has(b.id) ? 0 : 1;
      if (aRef !== bRef) return aRef - bRef;
      return a.id.localeCompare(b.id);
    });
    return sorted.slice(0, 80).map((p) => ({
      id: p.id,
      title: p.title || p.id,
      statement: p.statement || '',
      scope: p.scope || p.scope_profile?.scope_id || '',
      status: p.status || '',
    } satisfies FamilyPrincipleNode));
  }, [familyAxioms, familyFocusKind, worldModel]);

  const familyPrinciplesLoading = Boolean(
    familyFocusKind && !worldModel && (worldModel as unknown) !== null,
  );

  const principleGroupsForZoom: RootPrincipleGroup[] = useMemo(() => {
    if (familyFocusKind !== 'principles') return [];
    const sourceList = worldModel?.principles_family?.principles ?? [];
    return buildPrincipleGroups(sourceList);
  }, [familyFocusKind, worldModel]);

  // v1.20: paper_modules cluster_flag fetch. Loads the source-owned subdomain
  // clusters (37 clusters, 175 modules) plus each cluster's top_ids so the
  // RootPaperModuleVisualField can render actual paper module nodes grouped by
  // substrate-derived subdomain rather than the legacy generic relation graph.
  const [paperModuleClusters, setPaperModuleClusters] = useState<PaperModuleClusterModel[]>([]);
  const [paperModuleClusterCount, setPaperModuleClusterCount] = useState(0);
  const [paperModuleTotalCount, setPaperModuleTotalCount] = useState(0);
  const [paperModuleLoading, setPaperModuleLoading] = useState(false);
  const [paperModuleError, setPaperModuleError] = useState<string | null>(null);
  useEffect(() => {
    if (familyFocusKind !== 'paper_modules') {
      setPaperModuleClusters([]);
      setPaperModuleClusterCount(0);
      setPaperModuleTotalCount(0);
      setPaperModuleError(null);
      setPaperModuleLoading(false);
      return;
    }
    let cancelled = false;
    setPaperModuleLoading(true);
    setPaperModuleError(null);
    api.system
      .navigationSurface({ kind: 'paper_modules', band: 'cluster_flag' })
      .then((packet) => {
        if (cancelled) return;
        const rows = (packet.rows ?? []) as UnknownRow[];
        setPaperModuleClusters(buildPaperModuleClusters(rows));
        setPaperModuleClusterCount(rows.length);
        const summaryRecord = asRecordSafe((packet as unknown as UnknownRow).summary);
        const total = typeof summaryRecord.total_available === 'number'
          ? (summaryRecord.total_available as number)
          : rows.reduce((sum, row) => sum + (typeof row.count === 'number' ? (row.count as number) : 0), 0);
        setPaperModuleTotalCount(total);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setPaperModuleClusters([]);
        setPaperModuleError(err instanceof Error ? err.message : 'Failed to load paper_modules cluster_flag');
      })
      .finally(() => {
        if (!cancelled) setPaperModuleLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyFocusKind]);

  // v1.21: standards cluster_flag fetch. Loads the 8 source-owned standards groups
  // and each group's top_ids so RootStandardsGrammarField can render actual standard
  // nodes grouped by `standards --band cluster_flag`. Mirrors the paper_modules
  // fetch shape; the standard card-band fetch is owned by the v1.16 family-node
  // card useEffect below (extended in v1.21 to allow standards focus).
  const [standardClusters, setStandardClusters] = useState<StandardClusterModel[]>([]);
  const [standardClusterCount, setStandardClusterCount] = useState(0);
  const [standardTotalCount, setStandardTotalCount] = useState(0);
  const [standardLoading, setStandardLoading] = useState(false);
  const [standardError, setStandardError] = useState<string | null>(null);
  useEffect(() => {
    if (familyFocusKind !== 'standards') {
      setStandardClusters([]);
      setStandardClusterCount(0);
      setStandardTotalCount(0);
      setStandardError(null);
      setStandardLoading(false);
      return;
    }
    let cancelled = false;
    setStandardLoading(true);
    setStandardError(null);
    api.system
      .navigationSurface({ kind: 'standards', band: 'cluster_flag' })
      .then((packet) => {
        if (cancelled) return;
        const rows = (packet.rows ?? []) as UnknownRow[];
        setStandardClusters(buildStandardClusters(rows));
        setStandardClusterCount(rows.length);
        const summaryRecord = asRecordSafe((packet as unknown as UnknownRow).summary);
        const total = typeof summaryRecord.total_available === 'number'
          ? (summaryRecord.total_available as number)
          : rows.reduce((sum, row) => sum + (typeof row.count === 'number' ? (row.count as number) : 0), 0);
        setStandardTotalCount(total);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setStandardClusters([]);
        setStandardError(err instanceof Error ? err.message : 'Failed to load standards cluster_flag');
      })
      .finally(() => {
        if (!cancelled) setStandardLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyFocusKind]);

  // vNext-GA: generic option-surface fetch. Every focused kind that is not a
  // bespoke-adapted kind (paper_modules / standards / axiom_candidates /
  // principles) falls through here. We try cluster_flag first; if it errors
  // or returns no rows, we fall back to flag. The resulting GenericGraphPacket
  // feeds the receipts builder so the focused container renders real cluster
  // and/or object nodes instead of an empty 'not_yet_adapted' receipt.
  const [genericFocusPacket, setGenericFocusPacket] = useState<GenericGraphPacket | null>(null);
  const [, setGenericFocusLoading] = useState(false);
  const [, setGenericFocusError] = useState<string | null>(null);
  useEffect(() => {
    setGenericFocusError(null);
    if (
      !familyFocusKind ||
      familyFocusKind === 'paper_modules' ||
      familyFocusKind === 'standards' ||
      familyFocusKind === 'axiom_candidates' ||
      familyFocusKind === 'principles'
    ) {
      setGenericFocusPacket(null);
      setGenericFocusLoading(false);
      return;
    }
    let cancelled = false;
    const kind = familyFocusKind;
    setGenericFocusLoading(true);

    const fetchFlag = async () => {
      try {
        const packet = await api.system.navigationSurface({ kind, band: 'flag' });
        if (cancelled) return;
        const rows = (packet.rows ?? []) as UnknownRow[];
        if (rows.length === 0) {
          setGenericFocusPacket(null);
          setGenericFocusError(`No option-surface rows for ${kind}`);
        } else {
          setGenericFocusPacket(buildGenericGraphPacket(kind, 'flag', rows));
        }
      } catch (err) {
        if (cancelled) return;
        setGenericFocusPacket(null);
        setGenericFocusError(
          err instanceof Error ? err.message : `Failed to load ${kind} flag-band`,
        );
      } finally {
        if (!cancelled) setGenericFocusLoading(false);
      }
    };

    api.system
      .navigationSurface({ kind, band: 'cluster_flag' })
      .then((packet) => {
        if (cancelled) return;
        const rows = (packet.rows ?? []) as UnknownRow[];
        if (rows.length === 0) {
          void fetchFlag();
          return;
        }
        setGenericFocusPacket(buildGenericGraphPacket(kind, 'cluster_flag', rows));
        setGenericFocusLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        void fetchFlag();
      });

    return () => {
      cancelled = true;
    };
  }, [familyFocusKind]);

  useEffect(() => {
    if (familyFocusKind !== 'principles') {
      setFamilyAxioms([]);
      setFamilyAxiomError(null);
      setFamilyAxiomLoading(false);
      return;
    }
    let cancelled = false;
    setFamilyAxiomLoading(true);
    setFamilyAxiomError(null);
    const path = deriveFamilyAxiomPath(worldModel?.principles_family?.path);
    api.codex
      .getFile(path)
      .then((file) => {
        if (cancelled) return;
        setFamilyAxioms(parseFamilyAxiomCandidates(file.content ?? ''));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setFamilyAxioms([]);
        setFamilyAxiomError(err instanceof Error ? err.message : 'Failed to load axiom candidates');
      })
      .finally(() => {
        if (!cancelled) setFamilyAxiomLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [familyFocusKind, worldModel?.principles_family?.path]);

  const principleAxiomConnections: Set<string> = useMemo(() => {
    const set = new Set<string>();
    if (familyFocusKind !== 'principles' || !substrateFamilyNode) return set;
    if (substrateFamilyNode.startsWith('axiom_candidate_')) {
      const axiom = familyAxioms.find((candidate) => candidate.id === substrateFamilyNode);
      if (axiom) for (const id of axiom.relatedPrinciples) set.add(id);
    }
    if (substrateFamilyNode.startsWith('pri_')) {
      for (const axiom of familyAxioms) {
        if (axiom.relatedPrinciples.includes(substrateFamilyNode)) {
          for (const id of axiom.relatedPrinciples) set.add(id);
        }
      }
    }
    return set;
  }, [familyFocusKind, familyAxioms, substrateFamilyNode]);

  const handleFamilyNodeSelect = useCallback(
    (id: string | null) => {
      onSelectFamilyNode(id);
    },
    [onSelectFamilyNode],
  );

  const handleOpenKindLensForFocus = useCallback(() => {
    if (familyFocusKind) onOpenKindLens(familyFocusKind);
  }, [familyFocusKind, onOpenKindLens]);

  const rowSpecies: SelectedObjectSpecies = selectedRow
    ? classifySelectedObject(selectedRow)
    : 'unknown_row';
  const parentCluster: ParentClusterInfo | null =
    selectedRow && rowSpecies === 'leaf_row'
      ? findParentCluster(selectedRow, drilldownPacket, selectedPrimitive)
      : null;
  const substrateAtlasModel = useMemo(
    () => buildRootSubstrateAtlasModel({ packet, axes }),
    [packet, axes],
  );
  const [substrateAtlasHoveredKind, setSubstrateAtlasHoveredKind] = useState<string | null>(null);
  useEffect(() => {
    setSubstrateAtlasHoveredKind(null);
  }, [selectedPrimitive?.candidate_primitive]);
  const substrateAtlasFocusKind =
    selectedPrimitive?.candidate_primitive ?? substrateAtlasHoveredKind ?? null;
  const substrateAtlasFocusFamilies: RootSubstrateRelation[] = useMemo(() => {
    if (!substrateAtlasFocusKind) return [];
    const focusId = relationNodeId('substrate-container', substrateAtlasFocusKind);
    const families = new Set<RootSubstrateRelation>();
    for (const edge of substrateAtlasModel.edges) {
      if (edge.source === focusId || edge.target === focusId) families.add(edge.family);
    }
    return Array.from(families);
  }, [substrateAtlasModel.edges, substrateAtlasFocusKind]);
  const workbenchModel = buildRootWorkbenchGraph({
    packet,
    axes,
    viewModel,
    selectedPrimitive,
    selectedAxis,
    selectedRow,
    drilldownPacket,
    cardPacket,
    parentCluster,
  });
  const focusDetail =
    selectedPrimitive && selectedRow && rowSpecies === 'cluster_row' ? (
      <SelectedClusterLensCard
        primitive={selectedPrimitive}
        axis={selectedAxis}
        row={selectedRow}
        drilldownPacket={drilldownPacket}
        cardPacket={cardPacket}
        cardLoading={cardLoading}
        cardError={cardError}
        packetSourceRefCount={viewModel.sourceRefs.length}
        onSelectRow={onSelectRow}
        memberPreviewRowsById={memberPreviewRowsById}
      />
    ) : selectedPrimitive && selectedRow ? (
      <SelectedRowEvidenceCard
        primitive={selectedPrimitive}
        axis={selectedAxis}
        row={selectedRow}
        cardPacket={cardPacket}
        cardLoading={cardLoading}
        cardError={cardError}
        packetSourceRefCount={viewModel.sourceRefs.length}
        parentCluster={parentCluster}
      />
    ) : selectedPrimitive ? (
      <SelectedKindCenterCard
        primitive={selectedPrimitive}
        axis={selectedAxis}
        countsTrusted={viewModel.countsTrusted}
        drilldownRowCount={drilldownRowCount}
        drilldownTotalAvailable={asNumber(drilldownPacket?.summary?.total_available)}
        packetSourceRefCount={viewModel.sourceRefs.length}
        drilldownLoading={drilldownLoading}
        drilldownError={drilldownError}
        drilldownLoaded={drilldownPacket !== null}
      />
    ) : (
      <div className="w-full rounded-[4px] border border-[#c7b06a]/50 bg-black/72 p-3 shadow-[0_0_42px_rgba(199,176,106,0.13)]">
        <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-[#c7b06a]/85">
          <Compass size={14} />
          <span>system self-comprehension root</span>
        </div>
        <h3 className="mt-2 text-sm font-semibold text-white">Root doctrine crystal</h3>
        <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
          Projection workbench over doctrine, routes, substrate evidence, and nested annex pressure.
        </p>
        <div className="mt-2 flex flex-wrap gap-1">
          <span className="rounded border border-zenith-edge bg-white/[0.035] px-2 py-0.5 font-mono text-[10px] text-zenith-soft">
            authority: projection
          </span>
          <span className="rounded border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 font-mono text-[10px] text-emerald-100/75">
            read-only
          </span>
          {viewModel.annexRow && (
            <span className="rounded border border-[#c7b06a]/30 bg-[#c7b06a]/10 px-2 py-0.5 font-mono text-[10px] text-[#c7b06a]/85">
              annex: nested
            </span>
          )}
        </div>
      </div>
    );
  const renderSubstrateAtlas = !selectedPrimitive && !familyMode;
  const renderSubstrateFamily = !selectedPrimitive && familyMode;
  const [legacyAtlasLensOpen, setLegacyAtlasLensOpen] = useState(false);
  const [legacyFamilyLensOpen, setLegacyFamilyLensOpen] = useState(false);
  const substrateAtlasHintCount =
    substrateAtlasModel.bandCounts.durable_substrate +
    substrateAtlasModel.bandCounts.reference_substrate;
  const substrateMode: 'atlas' | 'family' | 'focus_path' = renderSubstrateFamily
    ? 'family'
    : renderSubstrateAtlas
      ? 'atlas'
      : 'focus_path';
  const substrateAtlasHint =
    substrateMode === 'family'
      ? `family zoom · ${familyFocusKind?.replace(/_/g, ' ') ?? 'focused container'}`
      : substrateMode === 'atlas'
        ? `${substrateAtlasHintCount} substrate · ${substrateAtlasModel.bandCounts.operational_overlay} overlay`
        : `${axes.length} primitive axes`;
  // vNext-real: shared RootSemanticGraph packet feeding both the hidden receipts
  // tree (instrumentation) and the visible canvas (operator-facing). Computed
  // once at the ConstitutionalMap level so both consumers see the same nodes/
  // edges. The visible canvas component dispatches off this packet plus the
  // familyNodeCard card-band data for the selected object's neighborhood.
  const rootSemanticGraph = useMemo(
    () =>
      buildRootSemanticGraphReceipts({
        substrateModel: substrateAtlasModel,
        expandedKind: familyFocusKind,
        selectedNode: substrateFamilyNode,
        paperModuleClusters,
        standardClusters,
        familyAxioms,
        familyPrinciples,
        genericFocusPacket,
      }),
    [
      substrateAtlasModel,
      familyFocusKind,
      substrateFamilyNode,
      paperModuleClusters,
      standardClusters,
      familyAxioms,
      familyPrinciples,
      genericFocusPacket,
    ],
  );
  // substrateContainerMeta: kind → {rowCount, status} for the visible canvas's
  // root substrate container badges. Keeps the atlas chip metadata in one place.
  const substrateContainerMeta = useMemo(() => {
    const map = new Map<string, { rowCount: number | null; status: string }>();
    for (const container of substrateAtlasModel.containers) {
      map.set(container.kind, {
        rowCount: container.rowCount,
        status: container.status,
      });
    }
    return map;
  }, [substrateAtlasModel.containers]);
  // canvasCardRow: the selected family node's card-band row, when loaded.
  // Drives the visible relation neighborhood (top_dependencies / top_dependents
  // / source_ref / standard_ref / governing_refs / navigation_contract).
  const canvasCardRow = useMemo<UnknownRow | null>(() => {
    if (familyNodeCardStatus !== 'ready' || !familyNodeCard) return null;
    const rows = (familyNodeCard.rows ?? []) as UnknownRow[];
    return rows.length > 0 ? rows[0] : null;
  }, [familyNodeCard, familyNodeCardStatus]);

  // vNext-RT: cluster summary map keyed by raw cluster id. Folds paper_modules,
  // standards, and generic packet clusters into one lookup so the visible
  // cluster nodes never render as blank rectangles — they always carry count
  // + preview labels + (optional) claim.
  const clusterSummaryById = useMemo<Map<string, ClusterSummaryEntry>>(() => {
    const map = new Map<string, ClusterSummaryEntry>();
    if (familyFocusKind === 'paper_modules') {
      for (const c of paperModuleClusters) {
        const previewLabels = c.topIds
          .slice(0, 3)
          .map((id) => paperModuleReadableLabel(id));
        map.set(c.id, {
          count: c.count,
          previewLabels,
          claim: null,
        });
      }
    } else if (familyFocusKind === 'standards') {
      for (const c of standardClusters) {
        const previewLabels = c.topIds
          .slice(0, 3)
          .map((id) => standardReadableLabel(id, c.sampleTitlesById.get(id)));
        map.set(c.id, {
          count: c.count,
          previewLabels,
          claim: null,
        });
      }
    } else if (genericFocusPacket) {
      for (const c of genericFocusPacket.clusters) {
        const previewLabels = c.topIds
          .slice(0, 3)
          .map((id) => c.labelsById.get(id) ?? id);
        map.set(c.id, {
          count: c.count,
          previewLabels,
          claim: c.claim,
        });
      }
    }
    return map;
  }, [familyFocusKind, paperModuleClusters, standardClusters, genericFocusPacket]);

  // vNext-RT: extract typed relation edges for the selected family node from
  // its flag-band row (or card-band row if present). Flag-band rows already
  // carry top_principle_edges / top_mechanism_edges / top_concept_edges /
  // top_upstream / top_downstream / source_ref / standard_ref so the visible
  // neighborhood doesn't require waiting on card-band.
  const edgesForSelected = useMemo<GenericGraphEdgeCandidate[]>(() => {
    if (!familyFocusKind || !substrateFamilyNode) return [];
    const ownerKind = familyFocusKind;
    const ownerId = substrateFamilyNode;
    // Prefer card-band row when available, else find the flag-band row from
    // the generic packet's directObjects.
    let row: UnknownRow | null = canvasCardRow;
    if (!row && genericFocusPacket) {
      const match = genericFocusPacket.directObjects.find((d) => d.id === ownerId);
      if (match) row = match.row;
    }
    if (!row) return [];
    return extractGenericEdges(ownerKind, ownerId, row);
  }, [familyFocusKind, substrateFamilyNode, canvasCardRow, genericFocusPacket]);

  // vNext-OF: object relation fabric for the focused kind. Builds a
  // RootObjectRelationGraph with focus_object + neighbor nodes + typed
  // edges from the loaded row data (generic packet + bespoke adapter
  // arrays + worldModel principles). Receipt state ('ready' | 'no_edges'
  // | 'missing_rows') drives the canvas's object-relation-graph attr so
  // the operator sees the projection's evidence state.
  const objectRelationGraph = useMemo<RootObjectRelationGraph | null>(() => {
    if (!familyFocusKind) return null;
    const genericRows = genericFocusPacket
      ? genericFocusPacket.directObjects.map((d) => d.row)
      : [];
    return buildRootObjectRelationGraph({
      focusKind: familyFocusKind,
      selectedRawId: substrateFamilyNode,
      genericRows,
      cardRow: canvasCardRow,
      paperModuleClusters,
      standardClusters,
      familyAxioms,
      familyPrinciples,
      activeCluster: substrateGraphCluster ?? null,
    });
  }, [
    familyFocusKind,
    substrateFamilyNode,
    genericFocusPacket,
    canvasCardRow,
    paperModuleClusters,
    standardClusters,
    familyAxioms,
    familyPrinciples,
    substrateGraphCluster,
  ]);

  // vNext-CM: complexity management model. The packet's "complete graph !=
  // visible graph" architecture is realized here as three projections from
  // the existing rootSemanticGraph (which is the complete graph), driven by
  // the URL view state:
  //
  //   expandedSet  — nodes currently expanded (root + focused kind + active
  //                   cluster + selected object). Anything not in this set is
  //                   collapsed.
  //   zoomBand     — semantic zoom band derived from view state. Controls
  //                   detail density (overview / container / cluster /
  //                   object / neighborhood). Same graph, different detail.
  //   nodeCollapse — kind/cluster/object id -> 'expanded' | 'collapsed' |
  //                   'selected' | 'not_yet_adapted'. The canvas paints this
  //                   on every visible node so tests + screenshots can prove
  //                   that focusing one cluster does not explode siblings.
  //
  // When ?cluster=<id> is set, sibling clusters are marked 'collapsed' so the
  // operator (and tests) can verify cluster-level expand/collapse without the
  // whole kind unfolding.
  const cmExpandedSet = useMemo(() => {
    const s = new Set<string>(['root:substrate']);
    if (familyFocusKind) s.add(familyFocusKind);
    if (substrateGraphCluster) {
      // The cluster id in the URL may be the raw cluster_id (e.g. 'core') or
      // the receipts-prefixed form (e.g. 'standards:cluster:core'); accept both.
      s.add(substrateGraphCluster);
      if (familyFocusKind) {
        s.add(`${familyFocusKind}:cluster:${substrateGraphCluster}`);
      }
    }
    if (substrateFamilyNode) {
      s.add(substrateFamilyNode);
      // Also expand the cluster containing the selected node when known.
      if (familyFocusKind === 'paper_modules') {
        for (const cluster of paperModuleClusters) {
          if (cluster.topIds.includes(substrateFamilyNode)) {
            s.add(`paper_modules:cluster:${cluster.id}`);
            s.add(cluster.id);
          }
        }
      } else if (familyFocusKind === 'standards') {
        for (const cluster of standardClusters) {
          if (cluster.topIds.includes(substrateFamilyNode)) {
            s.add(`standards:cluster:${cluster.id}`);
            s.add(cluster.id);
          }
        }
      }
    }
    return s;
  }, [
    familyFocusKind,
    substrateGraphCluster,
    substrateFamilyNode,
    paperModuleClusters,
    standardClusters,
  ]);
  const cmZoomBand: 'overview' | 'container' | 'cluster' | 'object' | 'neighborhood' = useMemo(() => {
    if (substrateFamilyNode) return 'neighborhood';
    if (substrateGraphCluster) return 'cluster';
    if (familyFocusKind) return 'container';
    return 'overview';
  }, [familyFocusKind, substrateGraphCluster, substrateFamilyNode]);
  // nodeCollapseStateById: map from each node id in the complete graph to its
  // current collapse state, derived from the expandedSet. The canvas reads
  // this on render and emits data-zenith-root-graph-collapse-state on every
  // visible node — including legacy fields and atlas containers — so the
  // CM DOM contract is enforced uniformly across both the React Flow canvas
  // and the legacy lens panels.
  const cmNodeCollapseStateById = useMemo(() => {
    const map = new Map<string, 'expanded' | 'collapsed' | 'selected' | 'not_yet_adapted'>();
    for (const node of rootSemanticGraph.nodes) {
      if (node.expansionStatus === 'not_yet_adapted') {
        map.set(node.id, 'not_yet_adapted');
        continue;
      }
      // Selection match: substrateFamilyNode is the raw URL token (e.g.
      // 'frontend_substrate_projection_theory') but the receipts builder
      // namespaces node ids with their role (e.g. 'paper_module:frontend_…').
      // Match either the raw id, the receipt id, or the secondaryId.
      if (
        node.id === substrateFamilyNode ||
        node.secondaryId === substrateFamilyNode
      ) {
        map.set(node.id, 'selected');
        continue;
      }
      if (cmExpandedSet.has(node.id) || cmExpandedSet.has(node.kind)) {
        map.set(node.id, 'expanded');
        continue;
      }
      map.set(node.id, 'collapsed');
    }
    return map;
  }, [rootSemanticGraph.nodes, substrateFamilyNode, cmExpandedSet]);
  return (
    <div className="flex h-full min-h-0 flex-col">
      <SectionHeader
        icon={Network}
        label={
          substrateMode === 'family'
            ? 'Root substrate atlas · family zoom'
            : substrateMode === 'atlas'
              ? 'Root substrate atlas'
              : 'Root substrate graph'
        }
        hint={deepDetailPresentation ? `relationship context · ${substrateAtlasHint}` : substrateAtlasHint}
      />
      <div className={clsx('min-h-0 flex-1 overflow-auto', deepDetailPresentation ? 'p-2' : 'p-2.5')}>
        <section
          className={clsx(
            'relative overflow-hidden rounded-[4px] border border-zenith-edge bg-[radial-gradient(circle_at_50%_35%,rgba(199,176,106,0.10),transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.035),rgba(255,255,255,0.012))]',
            deepDetailPresentation ? 'h-full min-h-[520px]' : 'h-full min-h-[420px]',
          )}
          data-zenith-root-substrate-mode={substrateMode}
          data-zenith-root-depth-presentation={depthPresentation}
          data-zenith-root-substrate-graph-mode={substrateMode === 'family' ? 'family' : 'atlas'}
          data-zenith-root-substrate-family={familyFocusKind ?? ''}
          data-zenith-root-unified-graph="ready"
          data-zenith-root-unified-graph-mode={substrateMode}
          data-zenith-root-unified-graph-selected={substrateFamilyNode ?? ''}
          data-zenith-root-unified-graph-expanded-path={
            familyFocusKind
              ? substrateGraphCluster
                ? substrateFamilyNode
                  ? `root:substrate>kind:${familyFocusKind}>cluster:${substrateGraphCluster}>node:${substrateFamilyNode}`
                  : `root:substrate>kind:${familyFocusKind}>cluster:${substrateGraphCluster}`
                : substrateFamilyNode
                  ? `root:substrate>kind:${familyFocusKind}>node:${substrateFamilyNode}`
                  : `root:substrate>kind:${familyFocusKind}`
              : 'root:substrate'
          }
          data-zenith-root-unified-graph-expanded-kind={familyFocusKind ?? ''}
          data-zenith-root-unified-graph-expanded-cluster={substrateGraphCluster ?? ''}
          data-zenith-root-graph-complexity-model="ready"
          data-zenith-root-graph-zoom-band={cmZoomBand}
          data-zenith-root-graph-complete-node-count={rootSemanticGraph.nodes.length}
          data-zenith-root-graph-complete-edge-count={rootSemanticGraph.edges.length}
          data-zenith-root-graph-expanded-set-size={cmExpandedSet.size}
        >
          {/* vNext unified graph receipts: a hidden span tree that emits every root
              substrate-container as a graph node (mirroring the React Flow atlas), the
              focused-kind expansion as a graph node, every known typed edge between
              substrate containers, and adapter receipts for not-yet-adapted kinds.
              The visual layout is still rendered by the atlas/field branches below;
              this receipt tree exists so the unified-graph DOM contract is provable
              regardless of which adapter is active. */}
          <UnifiedGraphReceipts
            substrateModel={substrateAtlasModel}
            expandedKind={familyFocusKind}
            selectedNode={substrateFamilyNode}
            paperModuleClusters={paperModuleClusters}
            standardClusters={standardClusters}
            familyAxioms={familyAxioms}
            familyPrinciples={familyPrinciples}
            genericFocusPacket={genericFocusPacket}
            collapseStateById={cmNodeCollapseStateById}
            expandedSet={cmExpandedSet}
            zoomBand={cmZoomBand}
            cluster={substrateGraphCluster ?? null}
          />
          {renderSubstrateFamily || renderSubstrateAtlas ? (
            <div
              data-zenith-root-substrate-family-zoom={renderSubstrateFamily ? 'ready' : 'atlas'}
              data-zenith-root-substrate-family={familyFocusKind ?? ''}
              data-zenith-root-substrate-family-zoom-level={
                renderSubstrateFamily
                  ? familyFocusKind === 'axiom_candidates' ||
                    familyFocusKind === 'principles' ||
                    familyFocusKind === 'paper_modules' ||
                    familyFocusKind === 'standards'
                    ? substrateFamilyNode
                      ? 'local_neighborhood'
                      : 'family'
                    : 'placeholder'
                  : 'atlas'
              }
              data-zenith-root-substrate-family-selected={substrateFamilyNode ?? ''}
              data-zenith-root-substrate-atlas={renderSubstrateAtlas ? 'ready' : ''}
              data-zenith-root-substrate-atlas-zoom={renderSubstrateAtlas ? 'atlas' : ''}
              data-zenith-root-substrate-atlas-container-count={substrateAtlasModel.containers.length}
              data-zenith-root-substrate-atlas-edge-count={substrateAtlasModel.edges.length}
              data-zenith-root-substrate-atlas-selected={substrateAtlasFocusKind ?? ''}
              className={clsx('flex flex-col', deepDetailPresentation ? 'h-auto min-h-[300px]' : 'h-full min-h-[420px]')}
            >
              {renderSubstrateFamily && (
                <nav
                  aria-label="Substrate atlas breadcrumbs"
                  data-zenith-root-graph-breadcrumbs="ready"
                  data-zenith-root-graph-breadcrumb-level={substrateFamilyNode ? 'node' : 'family'}
                  className="flex flex-wrap items-center gap-2 border-b border-zenith-edge bg-zenith-panel-muted px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft"
                >
                  <button
                    type="button"
                    onClick={onBackToAtlas}
                    data-zenith-root-graph-back="atlas"
                    className="rounded border border-white/12 bg-white/[0.04] px-2 py-0.5 text-zenith-soft hover:border-cyan-300/45 hover:text-cyan-100 focus:outline-none focus:ring-1 focus:ring-cyan-300/45"
                  >
                    ← Root atlas
                  </button>
                  <span className="text-white/35">/</span>
                  {substrateFamilyNode ? (
                    <button
                      type="button"
                      onClick={() => handleFamilyNodeSelect(null)}
                      data-zenith-root-graph-back="family"
                      className="rounded border border-white/12 bg-white/[0.04] px-2 py-0.5 text-zenith-soft hover:border-cyan-300/45 hover:text-cyan-100 focus:outline-none focus:ring-1 focus:ring-cyan-300/45"
                    >
                      ← {familyFocusKind?.replace(/_/g, ' ') ?? 'family'}
                    </button>
                  ) : (
                    <span className="rounded border border-zenith-edge bg-black/35 px-2 py-0.5 text-white/85">
                      {familyFocusKind?.replace(/_/g, ' ') ?? 'family'}
                    </span>
                  )}
                  {substrateFamilyNode && (
                    <>
                      <span className="text-white/35">/</span>
                      <span className="rounded border border-cyan-300/35 bg-cyan-400/[0.10] px-2 py-0.5 text-cyan-100">
                        {substrateFamilyNode}
                      </span>
                    </>
                  )}
                  <span className="ml-auto flex items-center gap-2 text-zenith-muted">
                    <button
                      type="button"
                      onClick={handleOpenKindLensForFocus}
                      data-zenith-root-graph-open-kind-lens={familyFocusKind ?? ''}
                      className="rounded border border-white/12 bg-white/[0.03] px-2 py-0.5 text-zenith-soft hover:border-cyan-300/35 hover:text-cyan-100 focus:outline-none focus:ring-1 focus:ring-cyan-200/50"
                    >
                      Open kind lens
                    </button>
                  </span>
                </nav>
              )}
              {/* vNext-real: visible unified graph canvas. ONE canvas serves both
                  atlas and family modes, driven by one graph packet. The legacy per-kind
                  components (RootDoctrineBindingField / RootPaperModuleVisualField /
                  RootStandardsGrammarField / RootSubstrateAtlasGraph) survive as legacy
                  lens panels below this canvas — they are node render helpers and
                  diagnostic surfaces per the packet's "Old components may survive as
                  legacy lenses, node render helpers, or inspector/detail helpers" clause.
                  The canvas is the visually dominant root; the legacy lens stays mounted
                  for test/diagnostic compatibility but is collapsed by default and does
                  not visually compete with the graph. */}
              <div
                className={clsx('relative overflow-hidden', deepDetailPresentation ? 'h-[520px] min-h-[420px]' : 'min-h-[320px] flex-1')}
                data-zenith-root-unified-graph-shell="ready"
                data-zenith-root-unified-graph-shell-height={deepDetailPresentation ? 'fixed_detail' : 'flex'}
              >
                <RootUnifiedSystemGraphCanvas
                  graph={rootSemanticGraph}
                  expandedKind={familyFocusKind}
                  selectedNode={substrateFamilyNode}
                  activeCluster={substrateGraphCluster ?? null}
                  onSelectNode={handleFamilyNodeSelect}
                  onSelectAtlasContainer={onSelectAtlasContainer}
                  onClusterToggle={onSelectGraphCluster}
                  onSelectGraphObject={onSelectGraphObject}
                  onOpenKindLens={onOpenKindLens}
                  onBackToAtlas={onBackToAtlas}
                  cardRow={canvasCardRow}
                  cardStatus={familyNodeCardStatus ?? 'idle'}
                  substrateContainerMeta={substrateContainerMeta}
                  clusterSummaryById={clusterSummaryById}
                  edgesForSelected={edgesForSelected}
                  objectRelationGraph={objectRelationGraph}
                />
              </div>
              {/* Legacy lens panels. Kept mounted so v1.11-v1.21 compatibility
                  receipts remain queryable, but collapsed through a 1px viewport
                  instead of native <details>. React Flow warns when mounted under
                  a zero-height closed details body. */}
              {renderSubstrateAtlas && (
                <div
                  className="border-t border-zenith-edge bg-black/40"
                  data-zenith-root-legacy-lens="atlas"
                  data-zenith-root-legacy-lens-state={legacyAtlasLensOpen ? 'expanded' : 'collapsed'}
                >
                  <button
                    type="button"
                    aria-expanded={legacyAtlasLensOpen}
                    onClick={() => setLegacyAtlasLensOpen((value) => !value)}
                    className="flex w-full items-center justify-between px-3 py-1.5 text-left font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted hover:text-cyan-100 focus:outline-none focus:ring-1 focus:ring-cyan-300/45"
                  >
                    <span>Legacy lens · containerized substrate atlas</span>
                    <span>{legacyAtlasLensOpen ? 'collapse' : 'open'}</span>
                  </button>
                  <div
                    aria-hidden={legacyAtlasLensOpen ? undefined : true}
                    className={clsx(
                      'relative overflow-hidden',
                      legacyAtlasLensOpen
                        ? deepDetailPresentation
                          ? 'h-[240px]'
                          : 'h-[420px]'
                        : 'h-px min-h-px opacity-0 pointer-events-none',
                    )}
                  >
                    <RootSubstrateAtlasGraph
                      model={substrateAtlasModel}
                      selectedKind={null}
                      hoveredKind={substrateAtlasHoveredKind}
                      onSelectKind={onSelectAtlasContainer}
                      onHoverChange={setSubstrateAtlasHoveredKind}
                    />
                  </div>
                </div>
              )}
              {renderSubstrateFamily && (
                <div
                  className="border-t border-zenith-edge bg-black/40"
                  data-zenith-root-legacy-lens={familyFocusKind ?? ''}
                  data-zenith-root-legacy-lens-state={legacyFamilyLensOpen ? 'expanded' : 'collapsed'}
                >
                  <button
                    type="button"
                    aria-expanded={legacyFamilyLensOpen}
                    onClick={() => setLegacyFamilyLensOpen((value) => !value)}
                    className="flex w-full items-center justify-between px-3 py-1.5 text-left font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted hover:text-cyan-100 focus:outline-none focus:ring-1 focus:ring-cyan-300/45"
                  >
                    <span>Legacy lens · {familyFocusKind?.replace(/_/g, ' ') ?? 'family'} field</span>
                    <span>{legacyFamilyLensOpen ? 'collapse' : 'open'}</span>
                  </button>
                  <div
                    aria-hidden={legacyFamilyLensOpen ? undefined : true}
                    className={clsx(
                      'relative overflow-hidden',
                      legacyFamilyLensOpen
                        ? deepDetailPresentation
                          ? 'h-[240px]'
                          : 'h-[420px]'
                        : 'h-px min-h-px opacity-0 pointer-events-none',
                    )}
                  >
                    {familyFocusKind === 'axiom_candidates' || familyFocusKind === 'principles' ? (
                      <RootDoctrineBindingField
                        focus={familyFocusKind}
                        axioms={familyAxioms}
                        principles={familyPrinciples}
                        principleGroups={principleGroupsForZoom}
                        selectedNodeId={substrateFamilyNode}
                        axiomConnections={principleAxiomConnections}
                        onSelectNode={handleFamilyNodeSelect}
                        loading={familyAxiomLoading || familyPrinciplesLoading || !worldModel}
                        errorLine={familyAxiomError}
                      />
                    ) : familyFocusKind === 'paper_modules' ? (
                      <RootPaperModuleVisualField
                        clusters={paperModuleClusters}
                        selectedNodeId={substrateFamilyNode}
                        onSelectNode={handleFamilyNodeSelect}
                        loading={paperModuleLoading}
                        errorLine={paperModuleError}
                        totalRowCount={paperModuleTotalCount || paperModuleClusterCount}
                      />
                    ) : familyFocusKind === 'standards' ? (
                      <RootStandardsGrammarField
                        clusters={standardClusters}
                        selectedNodeId={substrateFamilyNode}
                        onSelectNode={handleFamilyNodeSelect}
                        loading={standardLoading}
                        errorLine={standardError}
                        totalRowCount={standardTotalCount || standardClusterCount}
                      />
                    ) : (
                      <div className="px-6 py-4 text-[11px] text-zenith-soft">
                        No legacy lens for {familyFocusKind ?? 'this kind'}. Use Open kind lens for the focus-path workbench.
                      </div>
                    )}
                  </div>
                  <div
                    aria-hidden={legacyFamilyLensOpen ? undefined : true}
                    className={legacyFamilyLensOpen ? '' : 'h-px overflow-hidden opacity-0 pointer-events-none'}
                  >
                    {familyFocusKind !== 'paper_modules' && familyFocusKind !== 'standards' && (
                      <RootSubstrateFamilySelectionPanel
                        focusKind={familyFocusKind ?? ''}
                        axioms={familyAxioms}
                        principles={familyPrinciples}
                        selectedNodeId={substrateFamilyNode}
                        onClear={() => handleFamilyNodeSelect(null)}
                        onOpenKindLens={handleOpenKindLensForFocus}
                        loadingPrinciples={familyPrinciplesLoading}
                        axiomLoadError={familyAxiomError}
                      />
                    )}
                  </div>
                </div>
              )}
              {renderSubstrateAtlas && (
                <div className="border-t border-zenith-edge bg-black/45 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.14em] text-white/50">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span>{substrateAtlasModel.freshnessLine}</span>
                    <span className="truncate text-white/35">
                      {substrateAtlasFocusKind
                        ? `focus · ${substrateAtlasFocusKind}`
                        : 'click a container in the unified graph to expand'}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-[10px] normal-case tracking-normal text-white/35">
                    {substrateAtlasModel.omissionLine}
                  </p>
                </div>
              )}
              {renderSubstrateAtlas && (
                <details
                  className="border-t border-zenith-edge bg-zenith-panel-muted"
                  data-zenith-root-graph-legend="collapsed"
                >
                  <summary className="cursor-pointer px-3 py-2 font-mono text-[10px] uppercase tracking-[0.16em] text-zenith-soft transition-colors hover:text-zenith-signal">
                    How to read this graph ▸
                  </summary>
                  <RootSubstrateAtlasLegendPanel
                    legend={substrateAtlasModel.legend}
                    focusFamilies={substrateAtlasFocusFamilies}
                  />
                </details>
              )}
            </div>
          ) : (
            <RootWorkbenchGraph
              model={workbenchModel}
              focusDetail={focusDetail}
              onSelectKind={onSelectKind}
              onSelectRow={onSelectRow}
              onSelectInspectorTab={onSelectInspectorTab}
            />
          )}
        </section>
      </div>
    </div>
  );
}

interface DrilldownPaneProps {
  primitive: RootNavigatorPrimitiveRow | null;
  packet: NavigationSurfacePacket | null;
  loading: boolean;
  error: string | null;
  selectedRowId: string | null;
  onSelectRow: (rowId: string) => void;
}

function DrilldownPane({ primitive, packet, loading, error, selectedRowId, onSelectRow }: DrilldownPaneProps) {
  if (!primitive) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center font-mono text-[11px] text-white/35">
        Select a primitive kind from the atlas or rail to drill down.
      </div>
    );
  }
  const rows = (packet?.rows ?? []).filter(isRecord);
  const accent = '#7dd3fc';
  const role = asString(primitive.role_in_root_navigator);
  const support = asString(primitive.support_status, 'unknown');
  const supportedBands = asStringArray(primitive.supported_bands);
  const ownRefs = Array.from(
    new Set([
      ...asStringArray(primitive.governing_standard_refs),
      ...asStringArray(primitive.projection_refs),
    ]),
  );
  const rowsCountLabel = loading
    ? 'loading rows'
    : error
      ? 'unavailable'
      : `${rows.length} rows`;
  const examplesCellLabel = loading
    ? 'loading'
    : error
      ? 'unavailable'
      : rows.length > 0
        ? `${rows.length} loaded`
        : packet
          ? '0 loaded'
          : 'pending';
  return (
    <div className="flex h-full min-h-0 flex-col">
      <SectionHeader
        icon={GitBranch}
        label={`${asString(primitive.title, primitive.candidate_primitive)} · ${displayStatus(support)}`}
        hint={`${rowsCountLabel} · band ${asString(packetBandForRow(primitive))}`}
      />
      <div className="border-b border-zenith-edge bg-white/[0.015] p-2">
        {role && <p className="text-[11px] leading-4 text-zenith-soft">{role}</p>}
        <div className="mt-1.5 grid grid-cols-2 gap-1.5">
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1">
            <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">examples</div>
            <div className="font-mono text-[11px] text-white/72">{examplesCellLabel}</div>
          </div>
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1">
            <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">source refs</div>
            <div className="font-mono text-[11px] text-white/72">
              {ownRefs.length > 0 ? `${ownRefs.length} on row` : 'none on row'}
            </div>
          </div>
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1">
            <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">support</div>
            <div className="font-mono text-[11px] text-white/72">{displayStatus(support)}</div>
          </div>
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1">
            <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-white/35">bands</div>
            <div className="truncate font-mono text-[11px] text-white/72">
              {supportedBands.length > 0 ? supportedBands.join(' · ') : 'unknown'}
            </div>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-2">
        {loading && (
          <div
            className="space-y-1"
            role="status"
            aria-live="polite"
            aria-label={`Loading ${primitive.candidate_primitive} rows`}
            data-zenith-root-navigator-drilldown-skeleton="true"
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted px-2 py-1">
              loading rows
            </div>
            {[0, 1, 2, 3].map((index) => (
              <div
                key={`skeleton-${index}`}
                className="rounded border border-zenith-edge bg-white/[0.025] px-2 py-2"
                aria-hidden="true"
              >
                <div className="h-3 w-2/3 rounded bg-white/[0.06]" />
                <div className="mt-2 h-2 w-5/6 rounded bg-white/[0.035]" />
              </div>
            ))}
          </div>
        )}
        {error && (
          <div className="rounded border border-red-400/20 bg-red-400/10 px-2 py-2 text-xs text-red-100">
            {error}
          </div>
        )}
        {!loading && !error && rows.length === 0 && (
          <div className="rounded border border-zenith-edge bg-white/[0.025] px-2 py-2 font-mono text-[11px] text-zenith-muted">
            No rows in this packet.
          </div>
        )}
        <div className="space-y-1">
          {rows.map((row, index) => {
            const id = rowPrimaryId(row, `row-${index}`);
            const active = selectedRowId === id;
            const status = rowStatus(row);
            return (
              <button
                key={`${id}:${index}`}
                type="button"
                onClick={() => onSelectRow(id)}
                className={clsx(
                  'w-full rounded border px-2 py-1.5 text-left transition-colors',
                  active
                    ? 'border-cyan-300/45 bg-cyan-300/10'
                    : 'border-zenith-edge bg-white/[0.025] hover:border-white/20 hover:bg-white/[0.045]',
                )}
                style={active ? { boxShadow: `0 0 0 1px ${accent}66` } : undefined}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-xs font-semibold text-white/85">{rowLabel(row, id)}</span>
                  <StatusPill status={status} dim={status === 'green'} />
                </div>
                {rowClaim(row) && (
                  <div className="mt-0.5 line-clamp-2 text-[11px] leading-4 text-zenith-muted">{rowClaim(row)}</div>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

interface InspectorTabsProps {
  active: InspectorTab;
  onSelect: (tab: InspectorTab) => void;
  tabs: InspectorTab[];
}

function InspectorTabs({ active, onSelect, tabs }: InspectorTabsProps) {
  return (
    <div className="flex shrink-0 gap-1 border-b border-zenith-edge px-2 py-1.5">
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => onSelect(tab)}
          className={clsx(
            'rounded border px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em]',
            active === tab
              ? 'border-cyan-300/45 bg-cyan-300/12 text-cyan-100'
              : 'border-zenith-edge bg-white/[0.025] text-zenith-soft hover:text-white/80',
          )}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}

interface InspectorContent {
  Summary: ReactNode;
  Relations: ReactNode;
  Evidence: ReactNode;
  'Agent route': ReactNode;
  Raw: ReactNode;
}

type SourcePreviewStatus = 'idle' | 'loading' | 'ready' | 'error';

interface SourcePreviewState {
  status: SourcePreviewStatus;
  files: Map<string, CodexFileDetail>;
  error: string | null;
}

interface SourcePreviewResource {
  key: string;
  files: Map<string, CodexFileDetail>;
  error: string | null;
}

const EMPTY_SOURCE_PREVIEW_FILES = new Map<string, CodexFileDetail>();

function DossierSection({
  label,
  children,
  tone = 'default',
}: {
  label: string;
  children: ReactNode;
  tone?: 'default' | 'supporting';
}) {
  return (
    <section
      className={clsx(
        'rounded-[4px] border p-3',
        tone === 'supporting'
          ? 'border-zenith-edge bg-white/[0.025]'
          : 'border-cyan-300/18 bg-cyan-300/[0.035]',
      )}
    >
      <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-white/38">{label}</div>
      {children}
    </section>
  );
}

function InspectorBody({
  tab,
  content,
  presentationMode = 'standard',
}: {
  tab: InspectorTab;
  content: InspectorContent;
  presentationMode?: 'standard' | 'deep_dossier';
}) {
  if (presentationMode === 'deep_dossier' && tab === 'Summary') {
    return (
      <div
        className="flex-1 overflow-auto p-4"
        data-zenith-root-deep-dossier="ready"
        data-zenith-root-deep-dossier-tab={tab}
      >
        <div className="mx-auto grid max-w-[1120px] gap-3">
          <DossierSection label="Selected substrate dossier">{content.Summary}</DossierSection>
          <div className="grid gap-3 xl:grid-cols-2">
            <DossierSection label="Relations" tone="supporting">{content.Relations}</DossierSection>
            <DossierSection label="Evidence" tone="supporting">{content.Evidence}</DossierSection>
          </div>
          <DossierSection label="Routes and raw packet" tone="supporting">
            <div className="grid gap-3 xl:grid-cols-[minmax(0,0.45fr)_minmax(0,0.55fr)]">
              <div>{content['Agent route']}</div>
              <div>{content.Raw}</div>
            </div>
          </DossierSection>
        </div>
      </div>
    );
  }

  return (
    <div
      className={clsx('flex-1 overflow-auto', presentationMode === 'deep_dossier' ? 'p-4' : 'p-3')}
      data-zenith-root-deep-dossier={presentationMode === 'deep_dossier' ? 'tabbed' : 'off'}
      data-zenith-root-deep-dossier-tab={presentationMode === 'deep_dossier' ? tab : ''}
    >
      {content[tab]}
    </div>
  );
}

interface RootSelectionState {
  kind: 'overview' | 'primitive' | 'card' | 'coverage' | 'empty' | 'family_node' | 'paper_module' | 'standard';
  primitive?: RootNavigatorPrimitiveRow | null;
  axis?: RootNavigatorPrimitiveAxis | null;
  cardRow?: UnknownRow | null;
  coverageRow?: RootCoverageRow | null;
  familyNode?: {
    family: 'axiom_candidates' | 'principles';
    nodeKind: 'axiom_candidate' | 'principle';
    nodeId: string;
    axiom?: FamilyAxiomCandidate | null;
    principle?: WorldModelFamilyPrinciple | null;
    group?: RootPrincipleGroup | null;
    axiomsPointingHere?: FamilyAxiomCandidate[];
  } | null;
  // v1.20: selecting a node in the paper_modules visual field hydrates the Inspector
  // through the v1.16 card-band fetch. The selection.paperModule pointer carries the
  // node id + the readable surrogate label so the Inspector header can render before
  // the card-band card returns its title.
  paperModule?: {
    nodeId: string;
    readableLabel: string;
  } | null;
  // v1.21: selecting a node in the standards visual field hydrates the Inspector
  // through the v1.16 card-band fetch extended to allow standards focus. The
  // selection.standard pointer carries the node id + the readable surrogate label
  // so the Inspector header can render before the card-band card returns its title.
  standard?: {
    nodeId: string;
    readableLabel: string;
  } | null;
}

interface InspectorProps {
  selection: RootSelectionState;
  packet: RootNavigatorHandoffPacket | null;
  viewModel: RootDoctrineCrystalViewModel;
  drilldownPacket: NavigationSurfacePacket | null;
  cardPacket: NavigationSurfacePacket | null;
  cardLoading: boolean;
  cardError: string | null;
  selectedPrimitive: RootNavigatorPrimitiveRow | null;
  selectedAxis: RootNavigatorPrimitiveAxis | null;
  parentCluster: ParentClusterInfo | null;
  requestedTab: InspectorTab | null;
  onTabChange: (tab: InspectorTab) => void;
  currentRoute: string;
  onOpenKindLens: (kind: string) => void;
  // v1.21: governed-kind route handler. When the selected standard's
  // navigation_contract.artifact_kind names a GRAPH_NATIVE_KINDS member, the standard
  // Inspector's Agent-route tab exposes a "View governed kind" button that calls this
  // handler with the kind id so the cockpit transitions to ?graph=substrate&focus=<kind>.
  onSelectGraphNativeKind?: (kind: string) => void;
  // v1.15: broader principles list, threaded to buildFamilyNodeInspector so the axiom
  // Relations tab can resolve related_principles ids to readable micro-label chips.
  familyPrinciples?: WorldModelFamilyPrinciple[];
  // v1.16: option-surface card for the selected family node + load status. The Inspector
  // renders the rich substrate projection (edge_summary, top_tests, anti_principle,
  // teleology_glance, top_failure_modes, source_refs) from this packet and falls back to
  // an explicit Completeness receipt when the card is loading, errored, or thin.
  familyNodeCard?: NavigationSurfacePacket | null;
  familyNodeCardStatus?: 'idle' | 'loading' | 'ready' | 'error';
  familyNodeCardError?: string | null;
  presentationMode?: 'standard' | 'deep_dossier';
}

function commandRoute(label: string, command: string | undefined) {
  if (!command) return null;
  return (
    <details
      key={label}
      data-zenith-agent-provenance-command={label}
      className="rounded-[3px] border border-zenith-edge bg-black/25"
    >
      <summary className="cursor-pointer px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted hover:text-cyan-100">
        provenance command · {label}
      </summary>
      <div className="mx-2 mb-2 flex items-center gap-2 rounded-[3px] border border-zenith-edge bg-black/35 px-2 py-1">
        <Terminal size={12} className="shrink-0 text-cyan-200/55" />
        <code className="min-w-0 flex-1 truncate font-mono text-[11px] text-cyan-100">{command}</code>
        <CopyButton getText={() => command} label="copy" />
      </div>
    </details>
  );
}

function sourceRefPath(ref: string): string {
  const noAnchor = ref.split('::', 1)[0].trim();
  return noAnchor.replace(/:(\d+)$/, '');
}

function sourceRefTitle(ref: string, file: CodexFileDetail | undefined): string {
  if (file?.content) {
    if (file.file_type === 'json') {
      try {
        const parsed = JSON.parse(file.content) as unknown;
        if (isRecord(parsed)) {
          return firstNonEmpty(
            asString(parsed.title),
            asString(parsed.name),
            asString(parsed.id),
            asString(parsed.schema_version),
            sourceRefPath(ref).split('/').pop() ?? ref,
          );
        }
      } catch {
        // Fall through to path label.
      }
    }
    if (file.file_type === 'md') {
      const heading = file.content
        .split('\n')
        .map((line) => line.trim())
        .find((line) => line.startsWith('#'));
      if (heading) return heading.replace(/^#+\s*/, '');
    }
  }
  return sourceRefPath(ref).split('/').pop() || ref;
}

function jsonArtifactHighlights(file: CodexFileDetail): string[] {
  try {
    const parsed = JSON.parse(file.content) as unknown;
    if (!isRecord(parsed)) return [];
    const highlights: string[] = [];
    for (const key of [
      'purpose',
      'purpose_or_intent',
      'claim',
      'statement',
      'description',
      'role',
      'rule',
      'projection_rule',
      'summary',
      'tldr_excerpt',
    ]) {
      const value = parsed[key];
      if (typeof value === 'string' && value.trim()) highlights.push(value.trim());
      if (highlights.length >= 3) break;
    }
    const keySections = [
      'non_goals',
      'operator_questions',
      'primitive_axes',
      'inspector_contract',
      'acceptance_checks',
      'governing_refs',
      'relations',
    ].filter((key) => parsed[key] != null);
    if (keySections.length > 0) highlights.push(`Key sections: ${keySections.slice(0, 6).join(', ')}`);
    if (highlights.length === 0) {
      highlights.push(`JSON artifact with ${Object.keys(parsed).slice(0, 8).join(', ')} fields.`);
    }
    return highlights;
  } catch {
    return ['JSON artifact preview unavailable because parsing failed in the browser.'];
  }
}

function markdownHighlights(file: CodexFileDetail): string[] {
  const lines = file.content
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !line.startsWith('#'));
  return lines.slice(0, 3);
}

function genericFileHighlights(file: CodexFileDetail): string[] {
  if (file.file_type === 'json') return jsonArtifactHighlights(file);
  if (file.file_type === 'md') return markdownHighlights(file);
  const tags = Object.entries(file.ast_tags || {}).slice(0, 4);
  if (tags.length > 0) return tags.map(([key, value]) => `${key}: ${value}`);
  return file.content
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 3);
}

function inspectorHrefForSource(ref: string, currentRoute: string): string {
  return withReturnToQuery(`/inspector?file=${encodeURIComponent(sourceRefPath(ref))}`, currentRoute);
}

function routeWithInspectorTab(currentRoute: string, tab: InspectorTab): string {
  const url = new URL(currentRoute, 'http://zenith.local');
  if (tab === 'Summary') url.searchParams.delete('tab');
  else url.searchParams.set('tab', tab);
  return `${url.pathname}${url.search}`;
}

function SourcePreviewCards({
  refs,
  previewState,
  currentRoute,
}: {
  refs: string[];
  previewState: SourcePreviewState;
  currentRoute: string;
}) {
  if (refs.length === 0) return null;
  const uniqueRefs = Array.from(new Set(refs)).slice(0, 5);
  return (
    <div className="space-y-2" data-zenith-source-preview-list={previewState.status}>
      <div className="flex items-center justify-between gap-2">
        <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">source previews</div>
        <div className="font-mono text-[10px] text-white/35">
          {previewState.status === 'loading'
            ? 'loading content'
            : previewState.status === 'error'
              ? 'preview degraded'
              : `${uniqueRefs.length} refs`}
        </div>
      </div>
      {uniqueRefs.map((ref) => {
        const path = sourceRefPath(ref);
        const file = previewState.files.get(path);
        const highlights = file ? genericFileHighlights(file).filter(Boolean).slice(0, 3) : [];
        const hasError = file ? file.errors.length > 0 || !file.is_compliant : false;
        return (
          <div
          key={ref}
            className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2"
            data-zenith-source-preview-card={file ? 'resolved' : previewState.status === 'loading' ? 'loading' : 'unresolved'}
        >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate text-[12px] font-semibold text-white/82">
                  {file ? sourceRefTitle(ref, file) : sourceRefTitle(ref, undefined)}
                </div>
                <div className="mt-0.5 truncate font-mono text-[10px] text-white/38">{path}</div>
              </div>
              <StatusPill
                status={file ? (hasError ? 'partial' : 'green') : previewState.status === 'loading' ? 'partial' : 'unknown'}
                label={file ? (file.file_type || 'source') : previewState.status === 'loading' ? 'loading' : 'unresolved'}
                dim
              />
            </div>
            <div className="mt-1 space-y-1 text-[11px] leading-4 text-white/62">
              {highlights.length > 0 ? (
                highlights.map((highlight, index) => (
                  <p key={`${ref}:${index}`} className="line-clamp-2">{highlight}</p>
                ))
              ) : previewState.status === 'loading' ? (
                <p>Resolving this source inside the frontend.</p>
              ) : (
                <p>Preview unavailable; the source path is preserved as provenance and can be opened in Inspector.</p>
              )}
            </div>
            <a
              href={inspectorHrefForSource(ref, currentRoute)}
              className="mt-2 inline-flex items-center gap-1.5 rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-zenith-soft hover:border-cyan-300/35 hover:text-cyan-100"
            >
              <ExternalLink size={11} /> Open source with return
            </a>
          </div>
        );
      })}
      {previewState.error && (
        <div className="rounded-[3px] border border-amber-300/18 bg-amber-300/[0.045] p-2 text-[11px] leading-4 text-amber-50/75">
          Source preview request failed: {previewState.error}. Paths remain available as provenance, but this tab is not path-only.
        </div>
      )}
    </div>
  );
}

function sourceRefList(refs: string[], currentRoute = '/station/root-navigator') {
  return <SourcePreviewCards refs={refs} previewState={{ status: 'idle', files: new Map(), error: null }} currentRoute={currentRoute} />;
}

function sentenceList(items: string[], fallback = ''): string {
  const cleaned = items.map((item) => item.trim()).filter(Boolean);
  if (cleaned.length === 0) return fallback;
  if (cleaned.length === 1) return cleaned[0];
  if (cleaned.length === 2) return `${cleaned[0]} and ${cleaned[1]}`;
  return `${cleaned.slice(0, -1).join(', ')}, and ${cleaned[cleaned.length - 1]}`;
}

function readableKindName(kind: string | null | undefined): string {
  const raw = kind?.trim();
  if (!raw) return 'substrate objects';
  const special: Record<string, string> = {
    axiom_candidates: 'axiom candidates',
    paper_modules: 'paper modules',
    raw_seed_shards: 'raw seed shards',
    task_ledger: 'task ledger work items',
  };
  return special[raw] ?? raw.replace(/_/g, ' ');
}

function clusterRowsForVisualExplanation(drilldown: NavigationSurfacePacket | null): UnknownRow[] {
  return (drilldown?.rows ?? []).filter((row) => {
    if (!isRecord(row)) return false;
    return (
      asString(row.band) === 'cluster_flag' ||
      asString(row.row_id).includes('::cluster_flag') ||
      Boolean(asString(row.cluster_id))
    );
  }) as UnknownRow[];
}

function clusterMemberCountLabel(rows: UnknownRow[]): string {
  const counts = rows
    .map((row) => (typeof row.count === 'number' ? row.count : null))
    .filter((value): value is number => value !== null);
  if (counts.length === 0) return '';
  return `${counts.reduce((sum, value) => sum + value, 0)} projected members across ${rows.length} families`;
}

function sceneDomainExplainerRows(packet: RootNavigatorHandoffPacket | null): RootNavigatorSceneDomainExplainer[] {
  return (packet?.scene_domain_explainers?.rows ?? []).filter(
    (row): row is RootNavigatorSceneDomainExplainer => isRecord(row) && typeof row.scene_role_id === 'string',
  );
}

function findSceneDomainExplainer(
  packet: RootNavigatorHandoffPacket | null,
  kind: string | null | undefined,
): RootNavigatorSceneDomainExplainer | null {
  if (!kind) return null;
  const rows = sceneDomainExplainerRows(packet);
  return (
    rows.find((row) => row.primary_kind === kind) ??
    rows.find((row) => asStringArray(row.domain_kind_ids).includes(kind)) ??
    null
  );
}

function DomainExplainerCard({
  explainer,
  compact = false,
}: {
  explainer: RootNavigatorSceneDomainExplainer | null;
  compact?: boolean;
}) {
  if (!explainer) return null;
  const contains = asStringArray(explainer.contains);
  const paperRefs = asStringArray(explainer.paper_module_refs);
  const kindRows = (explainer.kind_rows ?? []).filter(isRecord);
  const containsSentence = sentenceList(contains);
  const sourceSentence = sentenceList([
    ...kindRows.map((row) => asString(row.title, asString(row.kind_id))).filter(Boolean),
    ...paperRefs,
  ]);
  return (
    <section
      className="rounded-[3px] border border-[#c7b06a]/25 bg-[#c7b06a]/[0.045] p-3"
      data-zenith-root-domain-explainer={explainer.scene_role_id}
    >
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-[#c7b06a]/78">domain explainer</div>
      <h3 className="mt-1 text-sm font-semibold text-white">{asString(explainer.title, 'Root domain')}</h3>
      {asString(explainer.headline) && (
        <p className="mt-1 text-xs leading-5 text-white/72">{asString(explainer.headline)}</p>
      )}
      {!compact && containsSentence && (
        <p className="mt-2 text-xs leading-5 text-zenith-soft">
          This domain contains {containsSentence}.
        </p>
      )}
      {asString(explainer.relation_summary) && (
        <p className="mt-2 text-xs leading-5 text-white/62">{asString(explainer.relation_summary)}</p>
      )}
      {!compact && sourceSentence && (
        <p className="mt-2 font-mono text-[10.5px] leading-4 text-white/42">
          Source surface: {sourceSentence}.
        </p>
      )}
    </section>
  );
}

function PrimitiveVisualExplanation({
  primitive,
  drilldown,
  domainExplainer,
}: {
  primitive: RootNavigatorPrimitiveRow;
  drilldown: NavigationSurfacePacket | null;
  domainExplainer: RootNavigatorSceneDomainExplainer | null;
}) {
  const primitiveKind = primitive.candidate_primitive;
  const domainTitle = asString(domainExplainer?.title, asString(primitive.title, primitiveKind));
  const clusterRows = clusterRowsForVisualExplanation(drilldown);
  const clusterNames = clusterRows.map((row) => rowLabel(row, asString(row.cluster_id, 'family'))).slice(0, 5);
  const memberCount = clusterMemberCountLabel(clusterRows);
  const band = asString(drilldown?.band, packetBandForRow(primitive));
  const relationSummary = asString(domainExplainer?.relation_summary) || asString(primitive.projection_rule);
  const kindName = readableKindName(primitiveKind);
  const clusterSentence = sentenceList(clusterNames);
  const hasClusters = clusterRows.length > 0 || band === 'cluster_flag';
  return (
    <section
      className="rounded-[3px] border border-cyan-300/18 bg-cyan-300/[0.035] p-3"
      data-zenith-root-visual-explanation="primitive-focus"
    >
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-cyan-100/68">
        what this view is showing
      </div>
      <p className="mt-2 text-sm leading-6 text-white/76">
        You are looking at {domainTitle}, the {kindName} domain inside the Root Substrate Atlas.
        {hasClusters
          ? ' The center visual is a family map, not a row list: each rectangle is a source-owned group of objects.'
          : ' The center visual is a substrate map for this kind; each object is a navigable substrate artifact.'}
      </p>
      {clusterSentence && (
        <p className="mt-2 text-xs leading-5 text-zenith-soft">
          The visible families are {clusterSentence}
          {memberCount ? `; together they represent ${memberCount}.` : '.'}
        </p>
      )}
      {hasClusters && (
        <p className="mt-2 text-xs leading-5 text-white/62">
          Object titles are intentionally hidden inside collapsed family boxes at this zoom.
          Click a family to expand it; then click an object to replace this overview with the object dossier.
        </p>
      )}
      {relationSummary && (
        <p className="mt-2 text-xs leading-5 text-white/58">{relationSummary}</p>
      )}
    </section>
  );
}

// v1.20: Inspector projection for a selected paper module. Consumes the v1.16 card-band
// fetch (api.system.navigationSurface({kind:'paper_modules', band:'card', id})) so the
// Summary / Relations / Evidence tabs render real substrate (title, tldr_excerpt /
// purpose_or_intent, top_dependencies / top_dependents, governing_refs,
// nearest_standard, source_ref, standard_ref). Missing fields surface as completeness
// receipts rather than silent black space, matching the v1.16 contract.
function buildPaperModuleInspector(
  paperModule: NonNullable<RootSelectionState['paperModule']>,
  options: {
    onOpenKindLens: (kind: string) => void;
    currentRoute: string;
    card?: NavigationSurfacePacket | null;
    cardStatus?: 'idle' | 'loading' | 'ready' | 'error';
    cardError?: string | null;
    sourcePreviewState?: SourcePreviewState;
  },
): InspectorContent {
  const { nodeId, readableLabel } = paperModule;
  const cardStatus = options.cardStatus ?? 'idle';
  const cardRow = (() => {
    const rows = options.card?.rows ?? [];
    if (rows.length === 0) return null;
    return (rows[0] ?? null) as UnknownRow | null;
  })();
  const cardTitle = asString(cardRow?.title);
  const cardTldr = asString(cardRow?.tldr_excerpt);
  const cardPurpose = asString(cardRow?.purpose_or_intent);
  const cardTopDependencies = asStringArray(cardRow?.top_dependencies);
  const cardTopDependents = asStringArray(cardRow?.top_dependents);
  const cardGoverningRefs = asRecordSafe(cardRow?.governing_refs);
  const cardNearestStandard = asRecordSafe(cardRow?.nearest_standard);
  const cardSourceRef = asString(cardRow?.source_ref);
  const cardStandardRef = asString(cardRow?.standard_ref);
  const dependencyCounts = asRecordSafe(cardRow?.dependency_counts);
  const evidenceCommand = asString(cardRow?.evidence_command);

  const richFieldCount =
    (cardTldr || cardPurpose ? 1 : 0) +
    (cardTopDependencies.length > 0 ? 1 : 0) +
    (cardTopDependents.length > 0 ? 1 : 0) +
    (Object.keys(cardGoverningRefs).length > 0 ? 1 : 0) +
    (cardSourceRef ? 1 : 0);

  const completeness: 'rich' | 'thin_projected' | 'missing_projection' | 'missing_authoring' | 'loading' = (() => {
    if (cardStatus === 'loading') return 'loading';
    if (cardStatus === 'error') return 'missing_projection';
    if (!cardRow) return 'thin_projected';
    if (richFieldCount >= 2) return 'rich';
    if (richFieldCount >= 1) return 'thin_projected';
    return 'missing_authoring';
  })();

  const title = cardTitle || readableLabel || nodeId;
  const principleRefs = asStringArray(cardGoverningRefs.principles);
  const conceptRefs = asStringArray(cardGoverningRefs.concepts);
  const mechanismRefs = asStringArray(cardGoverningRefs.mechanisms);
  const standardRefs = asStringArray(cardGoverningRefs.standards);

  return {
    Summary: (
      <div
        className="space-y-3"
        data-zenith-root-human-projection="summary"
        data-zenith-root-local-completeness={completeness}
        data-zenith-root-local-card-status={cardStatus}
        data-zenith-root-paper-module-inspector-id={nodeId}
      >
        <div className="space-y-1" data-zenith-root-local-lane="center">
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-violet-100/80">
            paper module
          </div>
          <h2 className="text-base font-semibold text-white">{title}</h2>
          <div className="font-mono text-[10px] text-zenith-muted">{nodeId}</div>
          {cardTldr && <p className="text-xs leading-5 text-white/72">{cardTldr}</p>}
          {!cardTldr && cardPurpose && (
            <p className="text-xs leading-5 text-white/72">{cardPurpose}</p>
          )}
        </div>
        {(Object.keys(dependencyCounts).length > 0 ||
          cardTopDependencies.length > 0 ||
          cardTopDependents.length > 0) && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-2" data-zenith-root-local-lane="dependencies">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              dependencies
            </div>
            <div className="mt-1 grid grid-cols-2 gap-2 text-[10.5px] leading-4 text-white/72">
              <div>
                <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">depends_on</div>
                <ul className="mt-1 space-y-0.5">
                  {cardTopDependencies.slice(0, 6).map((dep) => (
                    <li key={`dep:${dep}`} className="truncate font-mono">
                      {dep}
                    </li>
                  ))}
                  {cardTopDependencies.length === 0 && (
                    <li className="text-zenith-muted">—</li>
                  )}
                </ul>
              </div>
              <div>
                <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">depended on by</div>
                <ul className="mt-1 space-y-0.5">
                  {cardTopDependents.slice(0, 6).map((dep) => (
                    <li key={`rdep:${dep}`} className="truncate font-mono">
                      {dep}
                    </li>
                  ))}
                  {cardTopDependents.length === 0 && (
                    <li className="text-zenith-muted">—</li>
                  )}
                </ul>
              </div>
            </div>
          </div>
        )}
        {(asString(cardNearestStandard.id) || cardStandardRef || cardSourceRef) && (
          <div className="grid gap-2" data-zenith-root-local-lane="governance">
            {asString(cardNearestStandard.id) && (
              <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">nearest standard</div>
                <div className="mt-0.5 truncate font-mono text-[11px] text-white/72">
                  {asString(cardNearestStandard.title) || asString(cardNearestStandard.id)}
                </div>
              </div>
            )}
            {(cardSourceRef || cardStandardRef) && (
              <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">authority refs</div>
                {cardStandardRef && (
                  <div className="mt-0.5 truncate font-mono text-[10px] text-zenith-soft">standard · {cardStandardRef}</div>
                )}
                {cardSourceRef && (
                  <div className="mt-0.5 truncate font-mono text-[10px] text-zenith-soft">source · {cardSourceRef}</div>
                )}
              </div>
            )}
          </div>
        )}
        {(completeness === 'thin_projected' ||
          completeness === 'missing_authoring' ||
          completeness === 'missing_projection' ||
          completeness === 'loading') && (
          <div
            className="rounded-[3px] border border-amber-300/20 bg-amber-300/[0.04] p-2"
            data-zenith-root-local-lane="completeness"
            data-zenith-root-local-completeness-state={completeness}
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65">
              substrate completeness · {completeness.replace(/_/g, ' ')}
            </div>
            {completeness === 'loading' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                loading the paper_modules card for this module…
              </p>
            )}
            {completeness === 'missing_projection' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                The card-band fetch failed{options.cardError ? ` · ${options.cardError}` : ''}.
                The substrate may still carry richer fields; this is a projection-wiring
                gap, not proof of authoring drift.
              </p>
            )}
            {completeness === 'thin_projected' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                The paper_modules card returned only minimal fields for{' '}
                <span className="font-mono">{nodeId}</span>. Either the option-surface
                builder is dropping fields the source file contains, or the source file
                itself is thin under its governing standard.
              </p>
            )}
            {completeness === 'missing_authoring' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                No rich substrate fields (tldr_excerpt, dependencies, governing refs,
                source refs) are present for <span className="font-mono">{nodeId}</span>.
                Likely a substrate-authoring gap under codex/standards/std_paper_module.json.
              </p>
            )}
          </div>
        )}
      </div>
    ),
    Relations: (
      <div className="space-y-3" data-zenith-root-human-projection="relations">
        {principleRefs.length > 0 && (
          <div data-zenith-root-local-lane="governing_principles">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              governing principles
            </div>
            <div className="mt-1 flex flex-wrap gap-1">
              {principleRefs.map((id) => (
                <span
                  key={`pri:${id}`}
                  className="rounded border border-cyan-300/35 bg-cyan-400/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-cyan-100/85"
                >
                  {id}
                </span>
              ))}
            </div>
          </div>
        )}
        {standardRefs.length > 0 && (
          <div data-zenith-root-local-lane="governing_standards">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              governing standards
            </div>
            <div className="mt-1 flex flex-wrap gap-1">
              {standardRefs.map((id) => (
                <span
                  key={`std:${id}`}
                  className="rounded border border-amber-300/35 bg-amber-300/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-amber-100/85"
                >
                  {id}
                </span>
              ))}
            </div>
          </div>
        )}
        {(conceptRefs.length > 0 || mechanismRefs.length > 0) && (
          <div data-zenith-root-local-lane="governing_concepts_mechanisms">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              concepts & mechanisms
            </div>
            <div className="mt-1 flex flex-wrap gap-1">
              {conceptRefs.map((id) => (
                <span
                  key={`con:${id}`}
                  className="rounded border border-emerald-300/35 bg-emerald-400/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-emerald-100/85"
                >
                  {id}
                </span>
              ))}
              {mechanismRefs.map((id) => (
                <span
                  key={`mech:${id}`}
                  className="rounded border border-violet-300/35 bg-violet-400/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-violet-100/85"
                >
                  {id}
                </span>
              ))}
            </div>
          </div>
        )}
        {principleRefs.length === 0 &&
          standardRefs.length === 0 &&
          conceptRefs.length === 0 &&
          mechanismRefs.length === 0 &&
          cardStatus === 'ready' && (
            <div
              className="rounded-[3px] border border-amber-300/20 bg-amber-300/[0.04] p-1.5"
              data-zenith-root-local-lane="completeness"
              data-zenith-root-local-completeness-state="missing_relations"
            >
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65">
                relations · missing
              </div>
              <p className="mt-1 text-[10.5px] leading-4 text-zenith-soft">
                No governing_refs on this card. The paper module source file may still
                cite principles / standards in its frontmatter that the option-surface
                builder is not projecting.
              </p>
            </div>
          )}
      </div>
    ),
    Evidence: (
      <div className="space-y-3" data-zenith-root-human-projection="evidence">
        {(cardSourceRef || cardStandardRef) && (
          <ul className="space-y-1" data-zenith-root-local-lane="evidence">
            {cardSourceRef && (
              <li
                className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5 text-[11px] leading-4 text-white/72"
              >
                <span className="font-mono text-cyan-100/70">source</span>
                <span className="ml-1 break-all font-mono text-zenith-soft">{cardSourceRef}</span>
              </li>
            )}
            {cardStandardRef && (
              <li
                className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5 text-[11px] leading-4 text-white/72"
              >
                <span className="font-mono text-amber-100/70">standard</span>
                <span className="ml-1 break-all font-mono text-zenith-soft">{cardStandardRef}</span>
              </li>
            )}
          </ul>
        )}
        {!cardSourceRef && !cardStandardRef && cardStatus === 'ready' && (
          <div
            className="rounded-[3px] border border-amber-300/20 bg-amber-300/[0.04] p-1.5"
            data-zenith-root-local-lane="completeness"
            data-zenith-root-local-completeness-state="missing_evidence"
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65">
              evidence · missing
            </div>
            <p className="mt-1 text-[10.5px] leading-4 text-zenith-soft">
              No source_ref / standard_ref on this card. The paper module source path may
              be unresolved in the option-surface builder.
            </p>
          </div>
        )}
      </div>
    ),
    'Agent route': (
      <div className="space-y-2" data-zenith-root-human-projection="agent_route">
        <button
          type="button"
          onClick={() => options.onOpenKindLens('paper_modules')}
          className="inline-flex items-center gap-1.5 rounded border border-cyan-300/35 bg-cyan-400/[0.08] px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-cyan-100 hover:border-cyan-200/60"
        >
          Open kind lens
        </button>
        {evidenceCommand && (
          <details className="rounded-[3px] border border-zenith-edge bg-black/25">
            <summary className="cursor-pointer px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted hover:text-cyan-100">
              evidence command
            </summary>
            <div className="mx-2 mb-2 rounded-[3px] border border-zenith-edge bg-black/35 px-2 py-1 font-mono text-[11px] text-cyan-100">
              {evidenceCommand}
            </div>
          </details>
        )}
      </div>
    ),
    Raw: (
      <pre
        className="max-h-[420px] overflow-auto rounded border border-zenith-edge bg-black/55 p-2 font-mono text-[10px] text-zenith-soft"
        data-zenith-root-human-projection="raw"
      >
        {JSON.stringify(cardRow ?? { nodeId, readableLabel, cardStatus }, null, 2)}
      </pre>
    ),
  };
}

// v1.21: Inspector projection for a selected standard. Consumes the card-band fetch
// (api.system.navigationSurface({kind:'standards', band:'card', id})) for contract-level
// meaning: title, claim, summary_excerpt, status, group, source_ref, currentness,
// top_validation_rules, navigation_contract {artifact_kind, validation_probe,
// navigable_bands, source_authority}, related_surfaces, nearest_standard, nearest_skill,
// evidence_commands, core_law, option_shards, naming_layers.
//
// Contract status routes off card-band field presence:
//   - rich              : navigation_contract present (governed kind known) AND
//                         top_validation_rules non-empty (required fields known)
//   - thin_projected    : navigation_contract OR top_validation_rules present (partial
//                         contract surface)
//   - missing_contract  : neither navigation_contract nor top_validation_rules present
//   - missing_source    : card-band failed AND no source_ref recoverable
//   - parse_error       : card-band returned but row shape is unexpectedly empty
//   - loading           : card-band is in flight
//
// When navigation_contract.artifact_kind names a GRAPH_NATIVE_KINDS member, the Agent
// route surfaces a "View governed kind" button that routes back to ?graph=substrate
// &focus=<governed_kind>. This is the self-application proof: std_paper_module governs
// paper_modules and links to its own graph-native field.
function buildStandardInspector(
  standard: NonNullable<RootSelectionState['standard']>,
  options: {
    onOpenKindLens: (kind: string) => void;
    onSelectGovernedKind?: (kind: string) => void;
    currentRoute: string;
    card?: NavigationSurfacePacket | null;
    cardStatus?: 'idle' | 'loading' | 'ready' | 'error';
    cardError?: string | null;
    sourcePreviewState?: SourcePreviewState;
  },
): InspectorContent {
  const { nodeId, readableLabel } = standard;
  const cardStatus = options.cardStatus ?? 'idle';
  const cardRow = (() => {
    const rows = options.card?.rows ?? [];
    if (rows.length === 0) return null;
    return (rows[0] ?? null) as UnknownRow | null;
  })();
  const cardTitle = asString(cardRow?.title);
  const cardClaim = asString(cardRow?.claim);
  const cardStatusValue = asString(cardRow?.status);
  const cardGroup = asString(cardRow?.group);
  const cardSummaryExcerpt = asString(cardRow?.summary_excerpt);
  const cardSourceRef = asString(cardRow?.source_ref);
  const cardCompanionRef = asString(cardRow?.companion_ref);
  const cardEvidenceCommand = asString(cardRow?.evidence_command);
  const teleology = asRecordSafe(cardRow?.teleology_intent_capsule);
  const teleologyPurpose = asString(teleology.purpose);
  const currentness = asRecordSafe(cardRow?.currentness);
  const sourceMtime = asString(currentness.source_mtime);
  const authorityLifecycle = asString(currentness.authority_lifecycle);
  const authorityKey = asString(currentness.authority_key);
  const companionExists = currentness.companion_exists === true;
  const topValidationRules = asStringArray(cardRow?.top_validation_rules);
  const navigationContract = asRecordSafe(cardRow?.navigation_contract);
  const governedKind = asString(navigationContract.artifact_kind);
  const navigableBands = asStringArray(navigationContract.navigable_bands);
  const validationProbe = asStringArray(navigationContract.validation_probe);
  const sourceAuthority = asRecordSafe(navigationContract.source_authority);
  const sourceAuthorityValidator = asString(sourceAuthority.validator);
  const relatedSurfaces = asRecordSafe(cardRow?.related_surfaces);
  const nearestStandard = asRecordSafe(cardRow?.nearest_standard);
  const nearestSkill = asRecordSafe(cardRow?.nearest_skill);
  const evidenceCommands = asStringArray(cardRow?.evidence_commands);
  const coreLaw = asRecordSafe(cardRow?.core_law);
  const optionShards = (() => {
    const value = cardRow?.option_shards;
    if (Array.isArray(value)) return value.length;
    return 0;
  })();
  const namingLayers = (() => {
    const value = cardRow?.naming_layers;
    if (Array.isArray(value)) return value.length;
    return 0;
  })();

  const hasGovernedKind = governedKind.length > 0;
  const hasRequiredRules = topValidationRules.length > 0;
  const hasContract = hasGovernedKind || hasRequiredRules;
  const hasSourceRef = cardSourceRef.length > 0;
  const governedKindIsGraphNative = hasGovernedKind && GRAPH_NATIVE_KINDS.has(governedKind);

  const contractStatus: 'rich' | 'thin_projected' | 'missing_contract' | 'missing_source' | 'parse_error' | 'loading' = (() => {
    if (cardStatus === 'loading') return 'loading';
    if (cardStatus === 'error' && !hasSourceRef) return 'missing_source';
    if (!cardRow) return 'parse_error';
    if (hasGovernedKind && hasRequiredRules) return 'rich';
    if (hasContract) return 'thin_projected';
    return 'missing_contract';
  })();

  const sourceStatus: 'ready' | 'missing_source' | 'deferred' = (() => {
    if (hasSourceRef) return 'ready';
    if (cardStatus === 'loading' || cardStatus === 'idle') return 'deferred';
    return 'missing_source';
  })();

  const title = cardTitle || readableLabel || nodeId;
  const principleRefs = asStringArray(relatedSurfaces.principles);
  const standardRefs = asStringArray(relatedSurfaces.standards);
  const paperModuleRef = asString(relatedSurfaces.paper_module);
  const markdownDoctrine = asString(relatedSurfaces.markdown_doctrine);
  const relatedSurfaceEntries = Object.entries(relatedSurfaces).filter(([key, value]) => {
    if (key === 'principles' || key === 'standards') return false;
    return typeof value === 'string' && (value as string).length > 0;
  });

  // Agent-route props for governed-kind navigation: when the standard's
  // navigation_contract.artifact_kind names a graph-native kind, expose a route
  // back to that kind's substrate focus so the user can see the field the
  // standard governs (self-application loop).
  const governedKindRoute = governedKindIsGraphNative
    ? `/station/root-navigator?graph=substrate&focus=${governedKind}`
    : '';

  return {
    Summary: (
      <div
        className="space-y-3"
        data-zenith-root-human-projection="summary"
        data-zenith-root-local-completeness={contractStatus}
        data-zenith-root-local-card-status={cardStatus}
        data-zenith-root-standard-inspector-id={nodeId}
        data-zenith-root-standard-contract-status={contractStatus}
        data-zenith-root-standard-source-status={sourceStatus}
        data-zenith-root-standard-governed-kind={governedKind}
        data-zenith-root-standard-governed-kind-graph-native={governedKindIsGraphNative ? 'true' : 'false'}
        data-zenith-root-standard-governed-route={governedKindRoute}
        data-zenith-root-standard-governed-route-kind={governedKindIsGraphNative ? governedKind : ''}
      >
        <div className="space-y-1" data-zenith-root-local-lane="center">
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-emerald-100/80">
            standard{cardStatusValue ? ` · ${cardStatusValue}` : ''}{cardGroup ? ` · ${cardGroup}` : ''}
          </div>
          <h2 className="text-base font-semibold text-white">{title}</h2>
          <div className="font-mono text-[10px] text-zenith-muted">{nodeId}</div>
          {(cardClaim || teleologyPurpose) && (
            <p className="text-xs leading-5 text-white/72">
              {cardClaim || teleologyPurpose}
            </p>
          )}
          {cardSummaryExcerpt && cardSummaryExcerpt !== cardClaim && cardSummaryExcerpt !== teleologyPurpose && (
            <p className="text-[11px] leading-5 text-zenith-soft">{cardSummaryExcerpt}</p>
          )}
        </div>

        {hasContract && (
          <div
            className="rounded-[3px] border border-emerald-300/22 bg-emerald-300/[0.04] p-2"
            data-zenith-root-local-lane="contract"
            data-zenith-root-standard-contract="ready"
          >
            <div className="flex items-baseline justify-between">
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-emerald-100/65">
                contract
              </div>
              <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-emerald-100/45">
                {contractStatus.replace(/_/g, ' ')}
              </div>
            </div>
            {hasGovernedKind && (
              <div className="mt-1" data-zenith-root-local-lane="governed_kind">
                <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
                  governs
                </div>
                <div
                  className="mt-0.5 inline-flex items-center gap-1 rounded border border-emerald-300/35 bg-emerald-300/[0.10] px-1.5 py-0.5 font-mono text-[10px] text-emerald-100"
                  data-zenith-root-standard-contract-governed-kind={governedKind}
                >
                  {governedKind}
                  {governedKindIsGraphNative && (
                    <span className="ml-0.5 rounded bg-emerald-400/20 px-1 text-[8.5px] uppercase tracking-[0.14em] text-emerald-50">
                      graph-native
                    </span>
                  )}
                </div>
              </div>
            )}
            {navigableBands.length > 0 && (
              <div className="mt-1.5">
                <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
                  navigable bands
                </div>
                <div className="mt-0.5 flex flex-wrap gap-1">
                  {navigableBands.map((band) => (
                    <span
                      key={`band:${band}`}
                      className="rounded border border-cyan-300/30 bg-cyan-400/[0.06] px-1.5 py-0.5 font-mono text-[10px] text-cyan-100/85"
                    >
                      {band}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {hasRequiredRules && (
              <div className="mt-1.5" data-zenith-root-standard-contract-required-fields="ready">
                <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
                  required rules / invariants ({topValidationRules.length})
                </div>
                <ul className="mt-0.5 space-y-0.5 text-[11px] leading-4 text-white/68">
                  {topValidationRules.slice(0, 6).map((rule, idx) => (
                    <li
                      key={`rule:${idx}`}
                      className="rounded-[3px] bg-black/35 px-1.5 py-0.5"
                      data-zenith-root-standard-contract-rule-index={idx}
                    >
                      {rule}
                    </li>
                  ))}
                  {topValidationRules.length > 6 && (
                    <li className="text-[10px] text-zenith-muted">
                      +{topValidationRules.length - 6} more rule{topValidationRules.length - 6 === 1 ? '' : 's'} in card-band row
                    </li>
                  )}
                </ul>
              </div>
            )}
            {validationProbe.length > 0 && (
              <div className="mt-1.5">
                <div className="font-mono text-[9px] uppercase tracking-[0.14em] text-zenith-muted">
                  validation probes
                </div>
                <ul className="mt-0.5 space-y-0.5 text-[10.5px] leading-4 text-white/62">
                  {validationProbe.slice(0, 4).map((probe, idx) => (
                    <li key={`probe:${idx}`}>· {probe}</li>
                  ))}
                </ul>
              </div>
            )}
            {(Object.keys(coreLaw).length > 0 || optionShards > 0 || namingLayers > 0) && (
              <div className="mt-1.5 flex flex-wrap gap-1 font-mono text-[9.5px] text-zenith-soft">
                {Object.keys(coreLaw).length > 0 && (
                  <span className="rounded border border-zenith-edge-faint bg-white/[0.04] px-1.5 py-0.5">
                    core_law · {Object.keys(coreLaw).length} keys
                  </span>
                )}
                {optionShards > 0 && (
                  <span className="rounded border border-zenith-edge-faint bg-white/[0.04] px-1.5 py-0.5">
                    option_shards · {optionShards}
                  </span>
                )}
                {namingLayers > 0 && (
                  <span className="rounded border border-zenith-edge-faint bg-white/[0.04] px-1.5 py-0.5">
                    naming_layers · {namingLayers}
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {(contractStatus === 'thin_projected' ||
          contractStatus === 'missing_contract' ||
          contractStatus === 'missing_source' ||
          contractStatus === 'parse_error' ||
          contractStatus === 'loading') && (
          <div
            className="rounded-[3px] border border-amber-300/20 bg-amber-300/[0.04] p-2"
            data-zenith-root-local-lane="completeness"
            data-zenith-root-local-completeness-state={contractStatus}
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65">
              contract completeness · {contractStatus.replace(/_/g, ' ')}
            </div>
            {contractStatus === 'loading' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                loading the standards card for this standard…
              </p>
            )}
            {contractStatus === 'parse_error' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                The card-band fetch returned an unexpected row shape{options.cardError ? ` · ${options.cardError}` : ''}.
                This is a projection-wiring gap, not proof of authoring drift.
              </p>
            )}
            {contractStatus === 'missing_source' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                The card-band fetch failed and no source_ref is recoverable for{' '}
                <span className="font-mono">{nodeId}</span>. The standards registry may not have a source path for this id.
              </p>
            )}
            {contractStatus === 'thin_projected' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                Card has a partial contract surface for <span className="font-mono">{nodeId}</span>:{' '}
                {hasGovernedKind && <span className="font-mono text-emerald-100/85">governed kind ✓</span>}
                {hasGovernedKind && hasRequiredRules ? ' + ' : ''}
                {hasRequiredRules && <span className="font-mono text-emerald-100/85">required rules ✓</span>}
                {!hasGovernedKind && <span className="font-mono text-amber-100/70">governed kind missing</span>}
                {!hasGovernedKind && !hasRequiredRules ? '' : ''}
                . The standard source file may name what it governs in a key the option-surface builder is not projecting.
              </p>
            )}
            {contractStatus === 'missing_contract' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                No navigation_contract and no top_validation_rules on this card. Either the standard's
                source file is contract-thin (a substrate-authoring gap) or the option-surface
                builder is dropping its contract fields. Open the source to confirm.
              </p>
            )}
          </div>
        )}

        {(authorityLifecycle || authorityKey || sourceMtime || companionExists) && (
          <div className="grid gap-2" data-zenith-root-local-lane="currentness">
            <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5">
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
                currentness
              </div>
              <div className="mt-0.5 grid grid-cols-2 gap-x-2 gap-y-0.5 font-mono text-[10px] text-zenith-soft">
                {authorityLifecycle && (
                  <div>lifecycle · <span className="text-white/72">{authorityLifecycle}</span></div>
                )}
                {authorityKey && (
                  <div>authority_key · <span className="text-white/72">{authorityKey}</span></div>
                )}
                {sourceMtime && (
                  <div className="col-span-2 truncate">source_mtime · <span className="text-white/72">{sourceMtime}</span></div>
                )}
                {companionExists && (
                  <div className="col-span-2">companion · <span className="text-white/72">present</span></div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    ),
    Relations: (
      <div className="space-y-3" data-zenith-root-human-projection="relations">
        {hasGovernedKind && (
          <div data-zenith-root-local-lane="governs">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              this standard governs
            </div>
            <div className="mt-1 flex flex-wrap gap-1">
              <span
                className="rounded border border-emerald-300/35 bg-emerald-300/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-emerald-100/85"
                data-zenith-root-standard-governed-kind-chip={governedKind}
              >
                {governedKind}
              </span>
              {governedKindIsGraphNative && (
                <span className="rounded border border-emerald-300/25 bg-emerald-300/[0.04] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-emerald-100/65">
                  graph-native
                </span>
              )}
            </div>
          </div>
        )}
        {asString(nearestStandard.id) && nearestStandard.id !== nodeId && (
          <div data-zenith-root-local-lane="nearest_standard">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              nearest standard
            </div>
            <div className="mt-1 truncate font-mono text-[11px] text-white/72">
              {asString(nearestStandard.title) || asString(nearestStandard.id)}
            </div>
            {asString(nearestStandard.why) && (
              <div className="mt-0.5 text-[10.5px] leading-4 text-zenith-soft">{asString(nearestStandard.why)}</div>
            )}
          </div>
        )}
        {asString(nearestSkill.ref) && (
          <div data-zenith-root-local-lane="nearest_skill">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              nearest skill
            </div>
            <div className="mt-1 truncate font-mono text-[10px] text-white/72">{asString(nearestSkill.ref)}</div>
            {asString(nearestSkill.why) && (
              <div className="mt-0.5 text-[10.5px] leading-4 text-zenith-soft">{asString(nearestSkill.why)}</div>
            )}
          </div>
        )}
        {(principleRefs.length > 0 || standardRefs.length > 0) && (
          <div data-zenith-root-local-lane="governing_refs">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              related governance
            </div>
            <div className="mt-1 flex flex-wrap gap-1">
              {principleRefs.map((id) => (
                <span
                  key={`pri:${id}`}
                  className="rounded border border-cyan-300/35 bg-cyan-400/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-cyan-100/85"
                >
                  {id}
                </span>
              ))}
              {standardRefs.map((id) => (
                <span
                  key={`std:${id}`}
                  className="rounded border border-amber-300/35 bg-amber-300/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-amber-100/85"
                >
                  {id}
                </span>
              ))}
            </div>
          </div>
        )}
        {(paperModuleRef || markdownDoctrine || relatedSurfaceEntries.length > 0) && (
          <div data-zenith-root-local-lane="related_surfaces">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              related surfaces
            </div>
            <ul className="mt-1 space-y-0.5 text-[10.5px] leading-4 text-white/68">
              {paperModuleRef && (
                <li className="truncate font-mono">paper_module · {paperModuleRef}</li>
              )}
              {markdownDoctrine && (
                <li className="truncate font-mono">markdown_doctrine · {markdownDoctrine}</li>
              )}
              {relatedSurfaceEntries
                .filter(([k]) => k !== 'paper_module' && k !== 'markdown_doctrine')
                .map(([key, value]) => (
                  <li key={`rs:${key}`} className="truncate font-mono">
                    {key} · {String(value)}
                  </li>
                ))}
            </ul>
          </div>
        )}
        {!hasGovernedKind &&
          principleRefs.length === 0 &&
          standardRefs.length === 0 &&
          !paperModuleRef &&
          !markdownDoctrine &&
          relatedSurfaceEntries.length === 0 &&
          cardStatus === 'ready' && (
            <div
              className="rounded-[3px] border border-amber-300/20 bg-amber-300/[0.04] p-1.5"
              data-zenith-root-local-lane="completeness"
              data-zenith-root-local-completeness-state="missing_relations"
            >
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65">
                relations · missing
              </div>
              <p className="mt-1 text-[10.5px] leading-4 text-zenith-soft">
                No navigation_contract or related_surfaces on this card. The standard source
                file may still name governed kinds and related artifacts in keys the option-surface
                builder is not projecting.
              </p>
            </div>
          )}
      </div>
    ),
    Evidence: (
      <div className="space-y-3" data-zenith-root-human-projection="evidence">
        {(cardSourceRef || cardCompanionRef || sourceAuthorityValidator) && (
          <ul className="space-y-1" data-zenith-root-local-lane="evidence">
            {cardSourceRef && (
              <li
                className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5 text-[11px] leading-4 text-white/72"
                data-zenith-root-standard-source-ref={cardSourceRef}
              >
                <span className="font-mono text-cyan-100/70">source</span>
                <span className="ml-1 break-all font-mono text-zenith-soft">{cardSourceRef}</span>
              </li>
            )}
            {cardCompanionRef && (
              <li className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5 text-[11px] leading-4 text-white/72">
                <span className="font-mono text-violet-100/70">companion</span>
                <span className="ml-1 break-all font-mono text-zenith-soft">{cardCompanionRef}</span>
              </li>
            )}
            {sourceAuthorityValidator && (
              <li className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5 text-[11px] leading-4 text-white/72">
                <span className="font-mono text-amber-100/70">validator</span>
                <span className="ml-1 break-all font-mono text-zenith-soft">{sourceAuthorityValidator}</span>
              </li>
            )}
          </ul>
        )}
        {!cardSourceRef && !cardCompanionRef && cardStatus === 'ready' && (
          <div
            className="rounded-[3px] border border-amber-300/20 bg-amber-300/[0.04] p-1.5"
            data-zenith-root-local-lane="completeness"
            data-zenith-root-local-completeness-state="missing_evidence"
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65">
              evidence · missing
            </div>
            <p className="mt-1 text-[10.5px] leading-4 text-zenith-soft">
              No source_ref / companion_ref on this card. The standard's source path is unresolved
              in the option-surface builder.
            </p>
          </div>
        )}
      </div>
    ),
    'Agent route': (
      <div
        className="space-y-2"
        data-zenith-root-human-projection="agent_route"
        data-zenith-root-standard-inspector-id={nodeId}
        data-zenith-root-standard-governed-kind={governedKind}
        data-zenith-root-standard-governed-kind-graph-native={governedKindIsGraphNative ? 'true' : 'false'}
      >
        {governedKindIsGraphNative && options.onSelectGovernedKind && (
          <button
            type="button"
            onClick={() => options.onSelectGovernedKind?.(governedKind)}
            data-zenith-root-standard-governed-route={governedKindRoute}
            data-zenith-root-standard-governed-route-kind={governedKind}
            className="inline-flex items-center gap-1.5 rounded border border-emerald-300/35 bg-emerald-400/[0.08] px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-emerald-100 hover:border-emerald-200/60"
          >
            View governed kind · {governedKind}
          </button>
        )}
        <button
          type="button"
          onClick={() => options.onOpenKindLens('standards')}
          className="inline-flex items-center gap-1.5 rounded border border-cyan-300/35 bg-cyan-400/[0.08] px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-cyan-100 hover:border-cyan-200/60"
        >
          Open kind lens
        </button>
        {(cardEvidenceCommand || evidenceCommands.length > 0) && (
          <details className="rounded-[3px] border border-zenith-edge bg-black/25">
            <summary className="cursor-pointer px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted hover:text-cyan-100">
              evidence commands
            </summary>
            <div className="mx-2 mb-2 space-y-1 rounded-[3px] border border-zenith-edge bg-black/35 px-2 py-1 font-mono text-[11px] text-cyan-100">
              {cardEvidenceCommand && <div className="break-all">{cardEvidenceCommand}</div>}
              {evidenceCommands.map((cmd, idx) => (
                <div key={`cmd:${idx}`} className="break-all">
                  {cmd}
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    ),
    Raw: (
      <pre
        className="max-h-[420px] overflow-auto rounded border border-zenith-edge bg-black/55 p-2 font-mono text-[10px] text-zenith-soft"
        data-zenith-root-human-projection="raw"
      >
        {JSON.stringify(cardRow ?? { nodeId, readableLabel, cardStatus }, null, 2)}
      </pre>
    ),
  };
}

function buildFamilyNodeInspector(
  selection: NonNullable<RootSelectionState['familyNode']>,
  options: {
    onOpenKindLens: (kind: string) => void;
    currentRoute: string;
    // v1.15: passing the broader principles list lets the axiom Relations tab resolve
    // axiom.relatedPrinciples ids into readable micro-label chips instead of PRI_*** spam.
    principles?: WorldModelFamilyPrinciple[];
    // v1.16: option-surface card packet for the selected node + load status. When ready,
    // the Inspector renders the rich substrate fields the worldModel and family-zoom parser
    // do not carry (edge_summary, top_tests, anti_principle, teleology_glance, etc.).
    card?: NavigationSurfacePacket | null;
    cardStatus?: 'idle' | 'loading' | 'ready' | 'error';
    cardError?: string | null;
    sourcePreviewState?: SourcePreviewState;
  },
): InspectorContent {
  const { family, nodeKind, nodeId, axiom, principle, group, axiomsPointingHere = [] } = selection;
  const principlesById = new Map<string, WorldModelFamilyPrinciple>();
  for (const p of options.principles ?? []) principlesById.set(p.id, p);
  // v1.16: extract the substrate-rich card row. The card packet shape mirrors the
  // option-surface band=card output; the first row is the projection for our node id.
  // Fields that may exist (per std_raw_seed_principles.json + std_system_axiom_candidate.json):
  //   edge_summary[{target, relation, gloss}], evidence_refs[{ref, role, gloss}],
  //   top_tests[{check, violation}], top_failure_modes[{...}],
  //   anti_principle{id,title,failure_statement,failure_modes,detection_signals,prevention},
  //   teleology{title, desire_statement, end_state, ...} / teleology_glance,
  //   nearest_standard{id, title}, nearest_skill, source_ref, standard_ref,
  //   compression_bands (axioms only), governed_planes (axioms only).
  const cardRow = (() => {
    const rows = options.card?.rows ?? [];
    if (rows.length === 0) return null;
    return (rows[0] ?? null) as UnknownRow | null;
  })();
  const cardStatus = options.cardStatus ?? 'idle';
  const cardEdges = asRecordArraySafe(cardRow?.edge_summary);
  const cardEvidence = asRecordArraySafe(cardRow?.evidence_refs);
  const cardTopTests = asRecordArraySafe(cardRow?.top_tests);
  const cardTopFailureModes = asRecordArraySafe(cardRow?.top_failure_modes);
  const cardAntiPrinciple = asRecordSafe(cardRow?.anti_principle);
  const cardTeleologyGlance = asString(cardRow?.teleology_glance);
  const cardTeleology = asRecordSafe(cardRow?.teleology);
  const cardNearestStandard = asRecordSafe(cardRow?.nearest_standard);
  const cardNearestSkill = asRecordSafe(cardRow?.nearest_skill);
  const cardSourceRef = asString(cardRow?.source_ref);
  const cardStandardRef = asString(cardRow?.standard_ref);
  const cardOneSentence = asString(cardRow?.one_sentence_description) || asString(cardRow?.one_sentence);
  const hasAntiPrinciple = Object.keys(cardAntiPrinciple).length > 0;
  const hasTeleology = Object.keys(cardTeleology).length > 0;
  // v1.16: classify projection completeness for receipts (no silent black space). The
  // axiom branch already has rich client-parsed data via FamilyAxiomCandidate, so we
  // treat axiom-side as "rich" via the parsed object even when the card fetch is idle.
  const completeness = (() => {
    if (cardStatus === 'loading') return 'loading';
    if (cardStatus === 'error') return 'missing_projection';
    if (nodeKind === 'axiom_candidate' && axiom) return 'rich';
    if (!cardRow) {
      // No card returned: principle has only worldModel fields (title/statement) — that's
      // the "thin projected" case described in the v1.16 doctrine.
      return 'thin_projected';
    }
    const richFieldCount =
      cardEdges.length + cardEvidence.length + cardTopTests.length +
      (hasAntiPrinciple ? 1 : 0) + (hasTeleology || cardTeleologyGlance ? 1 : 0);
    if (richFieldCount >= 2) return 'rich';
    if (richFieldCount >= 1) return 'thin_projected';
    return 'missing_authoring';
  })();
  const microLabel = principle ? principleMicroLabel(principle) : '';
  const title =
    nodeKind === 'axiom_candidate'
      ? axiom?.title ?? nodeId
      : microLabel || principle?.title || nodeId;
  const claim =
    nodeKind === 'axiom_candidate'
      ? axiom?.denseClause || axiom?.formalClause || ''
      : principle?.statement ?? '';
  const familyAccent = nodeKind === 'axiom_candidate' ? '#c7b06a' : '#67e8f9';
  const sourceRefs = nodeKind === 'axiom_candidate'
    ? (axiom?.evidenceRefs ?? []).map((ref) => ref.ref).filter(Boolean)
    : [];
  return {
    Summary: (
      <div
        className="space-y-3"
        data-zenith-root-human-projection="summary"
        data-zenith-root-local-completeness={completeness}
        data-zenith-root-local-card-status={cardStatus}
      >
        <div className="space-y-1" data-zenith-root-local-lane="center">
          <div
            className="font-mono text-[10px] uppercase tracking-[0.16em]"
            style={{ color: familyAccent }}
          >
            {nodeKind === 'axiom_candidate' ? 'candidate axiom' : 'principle'}
          </div>
          <h2 className="text-base font-semibold text-white">{title}</h2>
          <div className="font-mono text-[10px] text-zenith-muted">{nodeId}</div>
          {claim && <p className="text-xs leading-5 text-white/72">{claim}</p>}
          {cardOneSentence && cardOneSentence !== claim && (
            <p className="text-[11px] leading-4 text-zenith-soft">{cardOneSentence}</p>
          )}
        </div>
        {(cardTeleologyGlance || hasTeleology) && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-2" data-zenith-root-local-lane="context">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">teleology</div>
            {cardTeleologyGlance && (
              <p className="mt-1 text-[11px] leading-4 text-white/72">{cardTeleologyGlance}</p>
            )}
            {hasTeleology && asString(cardTeleology.title) && (
              <p className="mt-1 font-mono text-[10px] text-white/50">{asString(cardTeleology.title)}</p>
            )}
            {hasTeleology && asString(cardTeleology.desire_statement) && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                {asString(cardTeleology.desire_statement)}
              </p>
            )}
          </div>
        )}
        {hasAntiPrinciple && (
          <div className="rounded-[3px] border border-amber-300/25 bg-amber-300/[0.05] p-2" data-zenith-root-local-lane="anti">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65">
              anti · {asString(cardAntiPrinciple.title)}
            </div>
            {asString(cardAntiPrinciple.failure_statement) && (
              <p className="mt-1 text-[11px] leading-4 text-amber-50/80">
                {asString(cardAntiPrinciple.failure_statement)}
              </p>
            )}
          </div>
        )}
        {cardTopTests.length > 0 && (
          <div data-zenith-root-local-lane="tests">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">top tests</div>
            <ul className="mt-1 space-y-1">
              {cardTopTests.slice(0, 4).map((t, idx) => (
                <li key={`test:${idx}`} className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5 text-[10.5px] leading-4 text-white/72">
                  <div className="text-white/82">{asString(t.check)}</div>
                  {asString(t.violation) && (
                    <div className="mt-0.5 text-amber-100/65">violation · {asString(t.violation)}</div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
        {cardTopFailureModes.length > 0 && (
          <div data-zenith-root-local-lane="failure_modes">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">top failure modes</div>
            <ul className="mt-1 space-y-1">
              {cardTopFailureModes.slice(0, 3).map((f, idx) => (
                <li key={`fm:${idx}`} className="text-[10.5px] leading-4 text-zenith-soft">
                  · {asString(f.description) || asString(f.failure) || JSON.stringify(f)}
                </li>
              ))}
            </ul>
          </div>
        )}
        {(asString(cardNearestStandard.id) || asString(cardNearestSkill.id) || cardSourceRef || cardStandardRef) && (
          <div className="grid gap-2" data-zenith-root-local-lane="governance">
            {asString(cardNearestStandard.id) && (
              <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">nearest standard</div>
                <div className="mt-0.5 truncate font-mono text-[11px] text-white/72">
                  {asString(cardNearestStandard.title) || asString(cardNearestStandard.id)}
                </div>
                <div className="truncate font-mono text-[10px] text-zenith-muted">{asString(cardNearestStandard.id)}</div>
              </div>
            )}
            {asString(cardNearestSkill.id) && (
              <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">nearest skill</div>
                <div className="mt-0.5 truncate font-mono text-[11px] text-white/72">
                  {asString(cardNearestSkill.title) || asString(cardNearestSkill.id)}
                </div>
              </div>
            )}
            {(cardSourceRef || cardStandardRef) && (
              <div className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">authority refs</div>
                {cardStandardRef && (
                  <div className="mt-0.5 truncate font-mono text-[10px] text-zenith-soft">standard · {cardStandardRef}</div>
                )}
                {cardSourceRef && (
                  <div className="mt-0.5 truncate font-mono text-[10px] text-zenith-soft">source · {cardSourceRef}</div>
                )}
              </div>
            )}
          </div>
        )}
        {(completeness === 'thin_projected' || completeness === 'missing_authoring' || completeness === 'missing_projection' || completeness === 'loading') && (
          <div
            className="rounded-[3px] border border-amber-300/20 bg-amber-300/[0.04] p-2"
            data-zenith-root-local-lane="completeness"
            data-zenith-root-local-completeness-state={completeness}
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65">
              substrate completeness · {completeness.replace(/_/g, ' ')}
            </div>
            {completeness === 'loading' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                loading the option-surface card for this node…
              </p>
            )}
            {completeness === 'missing_projection' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                The card-band fetch failed{options.cardError ? ` · ${options.cardError}` : ''}. The
                substrate may still carry rich content; this is a projection-wiring gap, not
                proof of authoring drift.
              </p>
            )}
            {completeness === 'thin_projected' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                The card-band packet returned only minimal fields for this node. Either the
                option-surface builder is not projecting the full row, or the substrate
                source is genuinely thin and the governing standard should require more
                content (kind <span className="font-mono">{family}</span>).
              </p>
            )}
            {completeness === 'missing_authoring' && (
              <p className="mt-1 text-[11px] leading-4 text-zenith-soft">
                No rich substrate fields (edge_summary, evidence_refs, top_tests, anti_principle,
                teleology) are present for this node. The substrate row likely needs authoring
                under its governing standard (kind <span className="font-mono">{family}</span>).
              </p>
            )}
          </div>
        )}
        {nodeKind === 'axiom_candidate' && axiom && (
          <div className="space-y-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              compression bands
            </div>
            <ul className="grid gap-1">
              {AXIOM_BAND_ORDER.map((band) => (
                <li
                  key={band}
                  className="grid grid-cols-[64px_minmax(0,1fr)] items-start gap-2 text-[10px] leading-4"
                >
                  <span
                    className={clsx(
                      'rounded border px-1.5 py-0.5 text-center font-mono text-[8px] uppercase tracking-[0.14em]',
                      axiom.bands[band]
                        ? 'border-amber-300/40 bg-amber-300/15 text-amber-50/90'
                        : 'border-zenith-edge bg-white/[0.03] text-white/35',
                    )}
                  >
                    {band}
                  </span>
                  <span className="text-zenith-soft">
                    {axiom.bands[band] || 'not populated in this projection'}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {nodeKind === 'principle' && group && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              group
            </div>
            <div
              className="mt-1 truncate font-mono text-[11px]"
              style={{ color: group.accent }}
            >
              {group.label}
            </div>
            <div className="mt-0.5 font-mono text-[10px] text-zenith-muted">
              source · {group.source.replace(/_/g, ' ')}
            </div>
          </div>
        )}
      </div>
    ),
    Relations: (
      <div className="space-y-3" data-zenith-root-human-projection="relations">
        {nodeKind === 'axiom_candidate' && axiom && (
          <>
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
                related principles
              </div>
              <div
                className="mt-1 flex flex-wrap gap-1"
                data-zenith-root-inspector-related-principles="ready"
              >
                {axiom.relatedPrinciples.length === 0 && (
                  <span className="text-[10px] text-zenith-muted">no related principles in current ledger</span>
                )}
                {axiom.relatedPrinciples.slice(0, 24).map((id) => {
                  const lookup = principlesById.get(id) ?? null;
                  const view = lookup ? buildPrincipleViewModel(lookup) : null;
                  if (view) return <SubstrateObjectChip key={id} view={view} />;
                  return (
                    <span
                      key={id}
                      className="rounded border border-zenith-edge-faint bg-white/[0.04] px-1.5 py-0.5 font-mono text-[10px] text-zenith-soft"
                      data-zenith-root-substrate-related-principle-id={id}
                      data-zenith-root-substrate-related-principle-resolved="false"
                    >
                      {id} · unresolved
                    </span>
                  );
                })}
              </div>
            </div>
            {axiom.governedPlanes.length > 0 && (
              <div>
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
                  governed planes
                </div>
                <div className="mt-1 flex flex-wrap gap-1">
                  {axiom.governedPlanes.slice(0, 8).map((plane) => (
                    <span
                      key={plane}
                      className="rounded border border-zenith-edge-faint bg-white/[0.04] px-1.5 py-0.5 font-mono text-[10px] text-zenith-soft"
                    >
                      {plane.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
        {nodeKind === 'principle' && (
          <>
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
                axioms pointing here
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {axiomsPointingHere.length === 0 && (
                  <span className="text-[10px] text-zenith-muted">
                    no axiom candidate links in current ledger
                  </span>
                )}
                {axiomsPointingHere.map((a) => (
                  <span
                    key={a.id}
                    className="rounded border border-amber-300/35 bg-amber-300/[0.10] px-1.5 py-0.5 font-mono text-[10px] text-amber-50/85"
                  >
                    {a.title}
                  </span>
                ))}
              </div>
            </div>
            {group && (
              <div>
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
                  group siblings
                </div>
                <div className="mt-1 text-[11px] leading-4 text-zenith-soft">
                  {group.principles.length} principles in {group.label}
                </div>
              </div>
            )}
          </>
        )}
        {cardEdges.length > 0 && (
          <div data-zenith-root-local-lane="outbound">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              edge summary
            </div>
            <ul className="mt-1 space-y-1">
              {cardEdges.slice(0, 8).map((e, idx) => (
                <li
                  key={`edge:${idx}`}
                  className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5 text-[10.5px] leading-4 text-white/72"
                  data-zenith-root-local-relation={asString(e.relation) || 'related'}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-white/82">{asString(e.target)}</span>
                    <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-cyan-100/75">
                      {asString(e.relation) || 'related'}
                    </span>
                  </div>
                  {asString(e.gloss) && (
                    <p className="mt-0.5 text-zenith-soft">{asString(e.gloss)}</p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
        {cardEdges.length === 0 && nodeKind === 'principle' && cardStatus === 'ready' && (
          <div
            className="rounded-[3px] border border-amber-300/20 bg-amber-300/[0.04] p-1.5"
            data-zenith-root-local-lane="completeness"
            data-zenith-root-local-completeness-state="missing_relations"
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65">
              relations · missing
            </div>
            <p className="mt-1 text-[10.5px] leading-4 text-zenith-soft">
              No edge_summary on this card. Either the option-surface builder is not
              projecting the relation index, or this principle has no declared neighbors
              under the governing standard.
            </p>
          </div>
        )}
      </div>
    ),
    Evidence: (
      <div className="space-y-3" data-zenith-root-human-projection="evidence">
        {cardEvidence.length > 0 && (
          <ul className="space-y-1" data-zenith-root-local-lane="evidence">
            {cardEvidence.slice(0, 8).map((ref, idx) => (
              <li
                key={`cardev:${idx}`}
                className="rounded-[3px] border border-zenith-edge bg-white/[0.025] p-1.5 text-[11px] leading-4 text-white/72"
              >
                {asString(ref.role) && (
                  <span className="font-mono text-cyan-100/70">{asString(ref.role)}</span>
                )}
                {asString(ref.ref) && (
                  <span className="ml-1 break-all font-mono text-zenith-soft">{asString(ref.ref)}</span>
                )}
                {asString(ref.gloss) && (
                  <p className="mt-0.5 text-zenith-soft">{asString(ref.gloss)}</p>
                )}
              </li>
            ))}
          </ul>
        )}
        {sourceRefs.length > 0 && (
          <SourcePreviewCards
            refs={sourceRefs}
            previewState={options.sourcePreviewState ?? { status: 'idle', files: new Map(), error: null }}
            currentRoute={options.currentRoute}
          />
        )}
        {nodeKind === 'axiom_candidate' && axiom?.evidenceRefs && axiom.evidenceRefs.length > 0 && (
          <ul className="space-y-1">
            {axiom.evidenceRefs.slice(0, 5).map((ref, idx) => (
              <li key={`${ref.role}:${ref.ref}:${idx}`} className="text-[11px] leading-4 text-zenith-soft">
                <span className="font-mono text-amber-100/70">{ref.role}</span>
                <span className="ml-1 font-mono text-zenith-soft">{ref.ref}</span>
                {ref.gloss && <p className="mt-0.5 text-zenith-muted">{ref.gloss}</p>}
              </li>
            ))}
          </ul>
        )}
        {cardEvidence.length === 0 && sourceRefs.length === 0 && nodeKind === 'principle' && (
          <div
            className="rounded-[3px] border border-amber-300/20 bg-amber-300/[0.04] p-1.5"
            data-zenith-root-local-lane="completeness"
            data-zenith-root-local-completeness-state={cardStatus === 'ready' ? 'missing_evidence' : 'loading_evidence'}
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100/65">
              evidence · {cardStatus === 'ready' ? 'missing' : 'loading'}
            </div>
            <p className="mt-1 text-[10.5px] leading-4 text-zenith-soft">
              {cardStatus === 'ready'
                ? 'No evidence refs in the card-band packet. Substrate may carry them in the source row or in a paper module the option-surface builder is not folding through.'
                : 'Loading the option-surface card; evidence refs (when present) will fold in once ready.'}
            </p>
          </div>
        )}
      </div>
    ),
    'Agent route': (
      <div className="space-y-2" data-zenith-root-human-projection="agent_route">
        <button
          type="button"
          onClick={() => options.onOpenKindLens(family)}
          className="inline-flex items-center gap-1.5 rounded border border-cyan-300/35 bg-cyan-400/[0.08] px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-cyan-100 hover:border-cyan-200/60"
        >
          Open kind lens
        </button>
        <p className="text-[11px] leading-4 text-zenith-soft">
          The kind lens reveals the legacy focus-path workbench for this family with the v1.10 inspector projection.
        </p>
      </div>
    ),
    Raw: (
      <pre
        className="max-h-[420px] overflow-auto rounded border border-zenith-edge bg-black/55 p-2 font-mono text-[10px] text-zenith-soft"
        data-zenith-root-human-projection="raw"
      >
        {JSON.stringify(
          nodeKind === 'axiom_candidate' ? axiom : { principle, group: group?.id, axiomsPointingHere: axiomsPointingHere.map((a) => a.id) },
          null,
          2,
        )}
      </pre>
    ),
  };
}

function buildOverviewInspector(packet: RootNavigatorHandoffPacket | null, viewModel: RootDoctrineCrystalViewModel): InspectorContent {
  if (!packet) {
    const ghostLine = (width: string, opacity = 1) => (
      <div className="skeleton skeleton-line" style={{ width, opacity }} aria-hidden />
    );
    const ghostRow = (lead: string, body: string, sub?: string) => (
      <div className="space-y-1.5 rounded-[3px] border border-zenith-edge bg-white/[0.025] p-2" aria-hidden>
        <div className="skeleton skeleton-line" style={{ width: lead, height: 6 }} />
        <div className="skeleton skeleton-line" style={{ width: body }} />
        {sub && <div className="skeleton skeleton-line" style={{ width: sub, opacity: 0.7 }} />}
      </div>
    );
    const ghostHeader = (eyebrow: string, title: string) => (
      <div className="space-y-1.5" aria-hidden>
        <div className="skeleton skeleton-line" style={{ width: eyebrow, height: 6 }} />
        <div className="skeleton skeleton-line" style={{ width: title, height: 12 }} />
      </div>
    );
    const liveKicker = (label: string) => (
      <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-white/45">
        <span className="dot-live" aria-hidden />
        <span>{label}</span>
      </div>
    );
    return {
      Summary: (
        <div
          className="space-y-3"
          data-zenith-root-human-projection="summary"
          data-zenith-root-inspector-loading="summary"
          aria-busy="true"
          aria-label="Loading RootNavigator overview"
        >
          {liveKicker('resolving constitutional atlas')}
          {ghostHeader('38%', '76%')}
          <p className="text-[11px] leading-4 text-zenith-muted">
            Reading the root substrate map: evidence, doctrine, shared grammar, and mechanisms.
          </p>
          <div className="space-y-2">
            {ghostLine('92%')}
            {ghostLine('84%', 0.85)}
            {ghostLine('66%', 0.7)}
          </div>
          <div className="grid grid-cols-2 gap-2">
            {ghostRow('32%', '64%')}
            {ghostRow('32%', '58%')}
          </div>
        </div>
      ),
      Relations: (
        <div
          className="space-y-3"
          data-zenith-root-human-projection="relations"
          data-zenith-root-inspector-loading="relations"
          aria-busy="true"
        >
          {liveKicker('mapping primitive axes')}
          <div className="space-y-2">
            {ghostRow('44%', '78%', '60%')}
            {ghostRow('38%', '72%', '54%')}
            {ghostRow('46%', '70%', '56%')}
          </div>
        </div>
      ),
      Evidence: (
        <div
          className="space-y-3"
          data-zenith-root-human-projection="evidence"
          data-zenith-root-inspector-loading="evidence"
          aria-busy="true"
        >
          {liveKicker('pulling source refs')}
          {ghostRow('28%', '64%', '82%')}
          <div className="space-y-1.5">
            {ghostLine('88%', 0.85)}
            {ghostLine('74%', 0.7)}
            {ghostLine('80%', 0.55)}
          </div>
        </div>
      ),
      'Agent route': (
        <div
          className="space-y-2"
          data-zenith-root-human-projection="agent_route"
          data-zenith-root-inspector-loading="agent_route"
          aria-busy="true"
        >
          {liveKicker('compiling agent route')}
          {ghostRow('30%', '88%')}
          {ghostRow('30%', '78%')}
          {ghostRow('30%', '70%')}
        </div>
      ),
      Raw: (
        <div
          className="space-y-2 rounded-[3px] border border-zenith-edge bg-black/45 p-2"
          data-zenith-root-human-projection="raw"
          data-zenith-root-inspector-loading="raw"
          aria-busy="true"
        >
          {liveKicker('streaming packet json')}
          <div className="space-y-1.5">
            {ghostLine('22%', 0.7)}
            {ghostLine('44%', 0.6)}
            {ghostLine('62%', 0.55)}
            {ghostLine('38%', 0.5)}
            {ghostLine('54%', 0.45)}
          </div>
        </div>
      ),
    };
  }
  const view = packet.view ?? {};
  const claudeJob = packet.constitutional_atlas?.claude_job ?? packet.claude_task?.job ?? '';
  const purpose = view.purpose ?? packet.constitutional_atlas?.purpose_one_line ?? '';
  const operatorHints = packet.frontend_surface_agent_packet?.operator_cli_hints ?? {};
  const screenshot = packet.current_screenshot ?? {};
  const refs = packet.source_refs ?? [];
  const sceneDomains = sceneDomainExplainerRows(packet);
  const derivationDecision = packet.self_comprehension_derivation_decision ?? {};
  const derivationRouteRows = asRecordArraySafe(derivationDecision.route_class_map).slice(0, 3);
  return {
    Summary: (
      <div className="space-y-3" data-zenith-root-human-projection="summary">
        <div className="space-y-1">
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/38">{asString(view.view_id, 'rootNavigator')}</div>
          <h2 className="text-base font-semibold text-white">Root Navigator constitutional atlas</h2>
          {purpose && <p className="text-xs leading-5 text-zenith-soft">{purpose}</p>}
        </div>
        {claudeJob && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">role</div>
            <p className="text-xs leading-5 text-white/72">{claudeJob}</p>
          </div>
        )}
        <section
          className="rounded-[3px] border border-cyan-300/18 bg-cyan-300/[0.035] p-3"
          data-zenith-root-visual-explanation="overview"
        >
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-cyan-100/68">
            what this view is showing
          </div>
          <p className="mt-2 text-sm leading-6 text-white/76">
            The center atlas is the root substrate map. It shows the main domains as roles in one operating system:
            evidence feeds doctrine, doctrine compresses into shared grammar, shared grammar governs meanings, and
            meanings instantiate mechanisms.
          </p>
          <p className="mt-2 text-xs leading-5 text-white/58">
            Click a domain to enter its family view. The graph stays structural; the Inspector explains the current
            visual and becomes the reading surface as you drill down.
          </p>
        </section>
        {asString(derivationDecision.decision) && (
          <section
            className="rounded-[3px] border border-[rgba(199,176,106,0.2)] bg-[rgba(199,176,106,0.045)] p-3"
            data-zenith-root-self-comprehension-derivation="ready"
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-[rgba(199,176,106,0.8)]">
              derivation contract
            </div>
            <p className="mt-2 text-xs leading-5 text-white/72">
              {asString(derivationDecision.decision)}
            </p>
            <div className="mt-2 flex flex-wrap gap-1">
              <span className="rounded border border-zenith-edge bg-black/25 px-2 py-0.5 font-mono text-[10px] text-zenith-soft">
                {asString(derivationDecision.status, 'status_unknown')}
              </span>
              {asString(derivationDecision.source_ref) && (
                <span className="rounded border border-zenith-edge bg-black/25 px-2 py-0.5 font-mono text-[10px] text-zenith-muted">
                  {asString(derivationDecision.source_ref)}
                </span>
              )}
            </div>
            {derivationRouteRows.length > 0 && (
              <div className="mt-3 grid gap-2">
                {derivationRouteRows.map((row) => (
                  <div
                    key={`${asString(row.primitive_view_id)}:${asString(row.route_class)}`}
                    className="rounded-[3px] border border-zenith-edge bg-black/25 p-2"
                    data-zenith-root-derivation-route-class={asString(row.route_class)}
                  >
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/70">
                        {asString(row.primitive_view_id, 'primitive_view')}
                      </span>
                      <span className="rounded border border-zenith-edge px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.12em] text-zenith-soft">
                        {asString(row.self_comprehension_consumption, 'consumption_unset')}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] leading-4 text-white/58">
                      {asString(row.frontend_policy, 'No frontend policy projected for this route class.')}
                    </p>
                    {asStringArray(row.consumes).length > 0 && (
                      <div className="mt-1 truncate font-mono text-[10px] text-white/35">
                        consumes: {asStringArray(row.consumes).slice(0, 4).join(' · ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
        {sceneDomains.length > 0 && (
          <div className="space-y-2" data-zenith-root-overview-domains="ready">
            <div className="flex items-baseline justify-between gap-2">
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">root substrate domains</div>
              <div className="font-mono text-[10px] tracking-[0.14em] text-white/30">{sceneDomains.length} mapped</div>
            </div>
            <div className="grid gap-2">
              {sceneDomains.map((domain) => (
                <DomainExplainerCard key={domain.scene_role_id} explainer={domain} compact />
              ))}
            </div>
            <div
              className="rounded-[3px] border border-dashed border-zenith-edge bg-white/[0.015] px-[var(--zenith-space-2-5)] py-[var(--zenith-space-2)] text-[11px] leading-4 text-white/45"
              data-zenith-root-overview-drill-hint="ready"
            >
              Click a domain in the center atlas to open its family view — the Inspector becomes the reading surface as you drill in.
            </div>
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">authority</div>
            <div className="mt-1 truncate font-mono text-[11px] text-zenith-soft">
              {asString(packet.authority_posture, 'unknown')}
            </div>
          </div>
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">verdict</div>
            <div className="mt-1 truncate font-mono text-[11px] text-zenith-soft">
              {asString(packet.verdict?.state, 'unknown')}
            </div>
          </div>
        </div>
        <ReadOnlyActionBar viewModel={viewModel} sourceRef={refs[0]} />
      </div>
    ),
    Relations: (
      <div className="space-y-3" data-zenith-root-human-projection="relations">
        <div className="space-y-1">
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/38">primitive axes</div>
          {(packet.constitutional_atlas?.primitive_axes ?? []).map((axis) => (
            <div
              key={axis.axis_id}
              className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2"
              style={{ borderLeft: `3px solid ${axisAccent(axis.axis_id)}` }}
            >
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft">
                {asString(axis.label, axis.axis_id)}
              </div>
              <div className="mt-1 line-clamp-3 text-[11px] leading-4 text-zenith-soft">
                {asString(axis.projection_role)}
              </div>
              <div className="mt-1 truncate font-mono text-[10px] text-white/35">
                {asStringArray(axis.candidate_kinds).join(' · ')}
              </div>
            </div>
          ))}
        </div>
        {asStringArray(packet.constitutional_atlas?.relation_authority_sources).length > 0 && (
          <div className="space-y-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">relation authority sources</div>
            <div className="flex flex-wrap gap-1">
              {asStringArray(packet.constitutional_atlas?.relation_authority_sources).map((src) => (
                <span
                  key={src}
                  className="rounded border border-zenith-edge bg-white/[0.03] px-2 py-0.5 font-mono text-[10px] text-zenith-soft"
                >
                  {src}
                </span>
              ))}
            </div>
          </div>
        )}
        {sceneDomains.length > 0 && (
          <div className="space-y-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">semantic scene relations</div>
            {sceneDomains.map((domain) => (
              <div
                key={domain.scene_role_id}
                className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2"
              >
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft">
                  {asString(domain.title, domain.scene_role_id)}
                </div>
                <div className="mt-1 text-[11px] leading-4 text-white/62">
                  {asString(domain.relation_summary, 'Relation summary is not projected yet.')}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    ),
    Evidence: (
      <div className="space-y-3" data-zenith-root-human-projection="evidence">
        <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
          <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">screenshot</div>
          <div className="font-mono text-[11px] text-zenith-soft">{asString(screenshot.status, 'unknown')}</div>
          {asString(screenshot.path) && (
            <div className="mt-1 break-words font-mono text-[10px] text-zenith-muted">{asString(screenshot.path)}</div>
          )}
          {asString(screenshot.run_stamp) && (
            <div className="mt-0.5 font-mono text-[10px] text-white/35">run {asString(screenshot.run_stamp)}</div>
          )}
        </div>
        {sourceRefList(refs)}
        <p className="text-[11px] leading-4 text-zenith-muted">
          Generated images and current screenshots are downstream design references, not runtime authority.
        </p>
      </div>
    ),
    'Agent route': (
      <div className="space-y-3" data-zenith-root-human-projection="agent_route">
        {commandRoute('root navigator packet', '/api/system/root-navigator-handoff')}
        {commandRoute('root navigator cli', '.repo-python kernel.py --root-navigator-handoff'.replace(/^\./, './'))}
        {commandRoute('view-agent packet', asString(packet.frontend_surface_agent_packet?.command))}
        {commandRoute('jump (ai)', asString(operatorHints['jump_ai']))}
        {commandRoute('capture', asString(operatorHints['capture']))}
        {commandRoute('health report', asString(operatorHints['health_report']))}
        {commandRoute('freshness check', asString(packet.root_coverage_state?.freshness_check_command))}
      </div>
    ),
    Raw: (
      <details className="rounded-[3px] border border-zenith-edge bg-white/[0.025]">
        <summary className="cursor-pointer px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
          root navigator packet json
        </summary>
        <pre
          className="max-h-[60vh] overflow-auto whitespace-pre-wrap p-2 font-mono text-[10px] leading-4 text-zenith-soft"
          data-zenith-root-human-projection="raw"
        >
          {JSON.stringify(packet, null, 2)}
        </pre>
      </details>
    ),
  };
}

function buildPrimitiveInspector(
  primitive: RootNavigatorPrimitiveRow,
  axis: RootNavigatorPrimitiveAxis | null,
  drilldown: NavigationSurfacePacket | null,
  packet: RootNavigatorHandoffPacket | null,
  packetSourceRefs: string[],
  viewModel: RootDoctrineCrystalViewModel,
): InspectorContent {
  const supported = asStringArray(primitive.supported_bands);
  const drilldownRowCount = (drilldown?.rows ?? []).length;
  const refs = Array.from(new Set([
    ...asStringArray(primitive.governing_standard_refs),
    ...asStringArray(primitive.projection_refs),
    ...packetSourceRefs,
  ]));
  const support = asString(primitive.support_status, 'unknown');
  const domainExplainer = findSceneDomainExplainer(packet, primitive.candidate_primitive);
  const domainTitle = asString(domainExplainer?.title);
  const primitiveTitle = asString(primitive.title, primitive.candidate_primitive);
  const title = domainTitle || primitiveTitle;
  return {
    Summary: (
      <div className="space-y-3" data-zenith-root-human-projection="summary">
        <div className="space-y-1">
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/38">
            {asString(axis?.label, axis?.axis_id ?? 'axis')}
          </div>
          <h2 className="text-base font-semibold text-white">{title}</h2>
          {domainTitle && (
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
              {primitiveTitle} domain
            </div>
          )}
          {asString(primitive.role_in_root_navigator) && (
            <p className="text-xs leading-5 text-zenith-soft">{asString(primitive.role_in_root_navigator)}</p>
          )}
        </div>
        <PrimitiveVisualExplanation
          primitive={primitive}
          drilldown={drilldown}
          domainExplainer={domainExplainer}
        />
        <DomainExplainerCard explainer={domainExplainer} />
        {asString(primitive.projection_rule) && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">projection rule</div>
            <p className="text-xs leading-5 text-white/72">{asString(primitive.projection_rule)}</p>
          </div>
        )}
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">rows</div>
            <div className="mt-1 font-mono text-sm text-white/82">
              {countLabel(primitive.row_count, viewModel.countsTrusted)}
            </div>
          </div>
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">support</div>
            <div className="mt-1 font-mono text-sm text-white/82">
              {support === 'option_surface_supported' ? 'green' : support}
            </div>
          </div>
        </div>
        {drilldownRowCount > 0 && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">live drilldown</div>
            <div className="font-mono text-[11px] text-zenith-soft">
              {drilldownRowCount} rows · band {asString(drilldown?.band, packetBandForRow(primitive))}
            </div>
          </div>
        )}
        <ReadOnlyActionBar viewModel={viewModel} sourceRef={refs[0]} />
      </div>
    ),
    Relations: (
      <div className="space-y-3" data-zenith-root-human-projection="relations">
        {axis && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2"
            style={{ borderLeft: `3px solid ${axisAccent(axis.axis_id)}` }}
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft">{asString(axis.label, axis.axis_id)}</div>
            <div className="mt-1 line-clamp-4 text-[11px] leading-4 text-zenith-soft">{asString(axis.projection_role)}</div>
            <div className="mt-1 truncate font-mono text-[10px] text-white/35">
              {asStringArray(axis.candidate_kinds).join(' · ')}
            </div>
          </div>
        )}
        {supported.length > 0 && (
          <div className="space-y-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">supported bands</div>
            <div className="flex flex-wrap gap-1">
              {supported.map((band) => (
                <span
                  key={band}
                  className="rounded border border-zenith-edge bg-white/[0.03] px-2 py-0.5 font-mono text-[10px] text-zenith-soft"
                >
                  {band}
                </span>
              ))}
            </div>
          </div>
        )}
        {drilldown?.governing_standard && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">governing standard</div>
            <pre className="overflow-auto font-mono text-[10px] leading-4 text-zenith-soft">
              {JSON.stringify(drilldown.governing_standard, null, 2)}
            </pre>
          </div>
        )}
      </div>
    ),
    Evidence: (
      <div className="space-y-3" data-zenith-root-human-projection="evidence">
        {sourceRefList(refs)}
        {asString(primitive.evidence_command) && commandRoute('evidence command', asString(primitive.evidence_command))}
      </div>
    ),
    'Agent route': (
      <div className="space-y-3" data-zenith-root-human-projection="agent_route">
        {commandRoute('option surface', asString(primitive.option_surface_command))}
        {commandRoute('card', asString(primitive.card_command))}
        {commandRoute('evidence', asString(primitive.evidence_command))}
      </div>
    ),
    Raw: (
      <details className="rounded-[3px] border border-zenith-edge bg-white/[0.025]">
        <summary className="cursor-pointer px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
          primitive row json
        </summary>
        <pre
          className="max-h-[60vh] overflow-auto whitespace-pre-wrap p-2 font-mono text-[10px] leading-4 text-zenith-soft"
          data-zenith-root-human-projection="raw"
        >
          {JSON.stringify(primitive, null, 2)}
        </pre>
      </details>
    ),
  };
}

function buildCardInspector(
  row: UnknownRow,
  cardPacket: NavigationSurfacePacket | null,
  {
    primitive,
    axis,
    drilldownPacket,
    parentCluster,
    sourcePreviewState,
    currentRoute,
  }: {
    primitive: RootNavigatorPrimitiveRow | null;
    axis: RootNavigatorPrimitiveAxis | null;
    drilldownPacket: NavigationSurfacePacket | null;
    parentCluster: ParentClusterInfo | null;
    sourcePreviewState: SourcePreviewState;
    currentRoute: string;
  },
): InspectorContent {
  const cardRows = (cardPacket?.rows ?? []).filter(isRecord);
  const cardRow = cardRows[0] ?? null;
  const projectionRow = cardRow ? { ...row, ...cardRow } : row;
  const drilldownCommand = asString(projectionRow.drilldown_command ?? projectionRow.card_command ?? '');
  const refs = Array.from(new Set([
    ...rowSourceRefs(projectionRow),
    ...asStringArray(cardPacket?.source_refs),
  ]));
  const relatedSurfaces = isRecord(projectionRow.related_surfaces) ? projectionRow.related_surfaces : null;
  const relatedSurfaceEntries = relatedSurfaces
    ? Object.entries(relatedSurfaces).filter(([, value]) => typeof value === 'string' && value.length > 0)
    : [];
  const validationRules = asStringArray(projectionRow.top_validation_rules).slice(0, 4);
  const evidenceCommands = Array.from(new Set([
    ...asStringArray(projectionRow.evidence_commands),
    asString(projectionRow.evidence_command),
    asString(projectionRow.tape_command),
  ].filter(Boolean))).slice(0, 4);
  const group = asString(projectionRow.group);
  const scope = asString(projectionRow.scope);
  const rowStatusValue = rowStatus(projectionRow);
  const kindLabel = primitive
    ? asString(artifactMeta(primitive.candidate_primitive).label ?? primitive.title, primitive.candidate_primitive)
    : asString(projectionRow.artifact_kind ?? cardPacket?.artifact_kind ?? 'row', 'row');
  const axisLabel = asString(axis?.label, 'selected object');
  const claim = rowClaim(projectionRow);
  const oneSentence = asString(projectionRow.one_sentence);
  const formalClause = asString(projectionRow.formal_clause);
  const denseClause = asString(projectionRow.dense_clause);
  const purpose = asString(projectionRow.purpose_or_intent);
  const tldr = asString(projectionRow.tldr_excerpt);
  const teleologyGlance = asString(projectionRow.teleology_glance);
  const compressionBands = isRecord(projectionRow.compression_bands) ? projectionRow.compression_bands : null;
  const currentness = isRecord(projectionRow.currentness) ? projectionRow.currentness : null;
  const nearestStandard = isRecord(projectionRow.nearest_standard) ? projectionRow.nearest_standard : null;
  const nearestSkill = isRecord(projectionRow.nearest_skill) ? projectionRow.nearest_skill : null;
  const evidenceRefs = [
    ...(Array.isArray(projectionRow.top_evidence_refs) ? projectionRow.top_evidence_refs : []),
    ...(Array.isArray(projectionRow.evidence_refs) ? projectionRow.evidence_refs : []),
  ].filter(isRecord).slice(0, 5);
  const tests = asStringArray(projectionRow.top_failure_modes).map((mode) => ({ label: 'failure mode', body: mode }))
    .concat(
      (Array.isArray(projectionRow.top_tests) ? projectionRow.top_tests : [])
        .filter(isRecord)
        .map((test) => ({
          label: firstNonEmpty(asString(test.check), 'test'),
          body: firstNonEmpty(asString(test.locus), asString(test.violation), 'source-owned test row'),
        })),
    )
    .slice(0, 5);
  const relationRows = [
    'principle_edges',
    'mechanism_edges',
    'concept_edges',
    'top_principle_edges',
    'top_mechanism_edges',
    'top_concept_edges',
    'top_upstream',
    'top_downstream',
  ].flatMap((key) =>
    (Array.isArray(projectionRow[key]) ? projectionRow[key] : [])
      .filter(isRecord)
      .map((entry) => ({
        family: key.replace(/^top_/, '').replace(/_/g, ' '),
        target: firstNonEmpty(asString(entry.label), asString(entry.target), asString(entry.id), 'related object'),
        relation: asString(entry.relation, 'relates to'),
        gloss: firstNonEmpty(asString(entry.gloss), asString(entry.compression), asString(entry.statement)),
      })),
  ).slice(0, 8);
  const linkedRelations = [
    ...asStringArray(projectionRow.linked_principles).map((target) => ({ family: 'linked principles', target, relation: 'links', gloss: '' })),
    ...asStringArray(projectionRow.linked_mechanisms).map((target) => ({ family: 'linked mechanisms', target, relation: 'links', gloss: '' })),
    ...asStringArray(projectionRow.top_dependencies).map((target) => ({ family: 'dependencies', target, relation: 'depends on', gloss: '' })),
  ].slice(0, 8);
  const siblingRows = (drilldownPacket?.rows ?? [])
    .filter(isRecord)
    .filter((candidate) => rowPrimaryId(candidate, '') !== rowPrimaryId(row, ''))
    .slice(0, 4);
  const noRicherFields =
    refs.length === 0 &&
    relatedSurfaceEntries.length === 0 &&
    validationRules.length === 0 &&
    evidenceCommands.length === 0 &&
    relationRows.length === 0 &&
    !group &&
    !oneSentence &&
    !formalClause &&
    !purpose;
  return {
    Summary: (
      <div className="space-y-3" data-zenith-root-human-projection="summary">
        <div className="space-y-1">
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/38">
            {asString(projectionRow.artifact_kind ?? cardPacket?.artifact_kind ?? 'row', 'row')}
          </div>
          <div className="flex items-start justify-between gap-3">
            <h2 className="min-w-0 text-base font-semibold text-white">{rowLabel(projectionRow, asString(projectionRow.id, 'row'))}</h2>
            <StatusPill status={rowStatusValue} />
          </div>
          {claim && <p className="text-xs leading-5 text-white/68">{claim}</p>}
          {oneSentence && oneSentence !== claim && <p className="text-[11px] leading-5 text-zenith-soft">{oneSentence}</p>}
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">governing role</div>
            <div className="mt-1 text-[11px] leading-4 text-white/66">
              {firstNonEmpty(formalClause, denseClause, purpose, claim, 'No richer governing-role field loaded for this card.')}
            </div>
          </div>
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">where it sits</div>
            <div className="mt-1 space-y-0.5 font-mono text-[11px] text-zenith-soft">
              <div>kind · {kindLabel}</div>
              <div>axis · {axisLabel}</div>
              {parentCluster && <div>cluster · {parentCluster.label}</div>}
              {group && <div>group · {group}</div>}
              {scope && <div>scope · {scope}</div>}
            </div>
          </div>
        </div>
        {compressionBands && (
          <div className="rounded-[3px] border border-[#c7b06a]/18 bg-[#c7b06a]/[0.045] p-2">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-[#c7b06a]/70">compression ladder</div>
            <div className="space-y-1">
              {['tiny', 'flag', 'card', 'context', 'deep'].map((band) => {
                const body = asString(compressionBands[band]);
                if (!body) return null;
                return (
                  <div key={band} className="grid grid-cols-[58px_minmax(0,1fr)] gap-2 text-[11px] leading-4">
                    <span className="font-mono uppercase tracking-[0.12em] text-white/35">{band}</span>
                    <span className="line-clamp-2 text-white/64">{body}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {(teleologyGlance || tldr || currentness || nearestStandard || nearestSkill) && (
          <div className="grid gap-2 sm:grid-cols-2">
            {(teleologyGlance || tldr) && (
              <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">why it matters</div>
                <div className="mt-1 text-[11px] leading-4 text-white/64">{firstNonEmpty(teleologyGlance, tldr)}</div>
              </div>
            )}
            {currentness && (
              <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">currentness</div>
                <div className="mt-1 text-[11px] leading-4 text-white/64">
                  {firstNonEmpty(asString(currentness.recommended_action), asString(currentness.status), asString(currentness.index_freshness), 'currentness packet loaded')}
                </div>
              </div>
            )}
            {nearestStandard && (
              <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">nearest standard</div>
                <div className="mt-1 text-[11px] leading-4 text-white/64">{asString(nearestStandard.ref, 'standard loaded')}</div>
              </div>
            )}
            {nearestSkill && (
              <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">nearest skill</div>
                <div className="mt-1 text-[11px] leading-4 text-white/64">{asString(nearestSkill.ref, 'skill loaded')}</div>
              </div>
            )}
          </div>
        )}
        {relatedSurfaceEntries.length > 0 && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">related surfaces</div>
            <div className="grid gap-1">
              {relatedSurfaceEntries.slice(0, 5).map(([key, value]) => (
                <div key={key} className="grid grid-cols-[120px_minmax(0,1fr)] gap-2 font-mono text-[10px] leading-4">
                  <span className="text-white/38">{key.replace(/_/g, ' ')}</span>
                  <span className="truncate text-white/68">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {validationRules.length > 0 && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">top validation rules</div>
            <ul className="space-y-1 text-[11px] leading-4 text-white/62">
              {validationRules.map((rule, index) => (
                <li key={`${index}:${rule}`} className="flex gap-2">
                  <span className="font-mono text-white/30">{index + 1}</span>
                  <span>{rule}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {refs.length > 0 && (
          <div className="rounded-[3px] border border-emerald-300/15 bg-emerald-300/[0.035] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-emerald-100/55">source evidence</div>
            <div className="mt-1 text-[11px] leading-4 text-white/62">
              {refs.length} source refs available; Evidence tab renders content previews and keeps raw paths as provenance.
            </div>
          </div>
        )}
        {noRicherFields && (
          <div className="rounded-[3px] border border-amber-300/18 bg-amber-300/[0.045] p-2 text-[11px] leading-4 text-amber-50/75">
            No richer summary fields loaded for this row. Available evidence is limited to the selected card packet and inherited root projection refs.
          </div>
        )}
      </div>
    ),
    Relations: (
      <div className="space-y-3" data-zenith-root-human-projection="relations">
        <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
          <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">pertains to</div>
          <div className="mt-1 grid gap-1 font-mono text-[11px] text-white/66">
            <div>parent kind · {kindLabel}</div>
            <div>axis · {axisLabel}</div>
            {parentCluster && <div>cluster · {parentCluster.label}</div>}
            {group && <div>group · {group}</div>}
            {scope && <div>scope · {scope}</div>}
            {asString(projectionRow.parent_id) && <div>parent · {asString(projectionRow.parent_id)}</div>}
          </div>
        </div>
        {(relationRows.length > 0 || linkedRelations.length > 0) && (
          <div className="space-y-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">source-owned relation edges</div>
            {[...relationRows, ...linkedRelations].slice(0, 10).map((entry, index) => (
              <div key={`${entry.family}:${entry.target}:${index}`} className="rounded border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
                <div className="flex items-center justify-between gap-2 font-mono text-[10px]">
                  <span className="uppercase tracking-[0.12em] text-white/35">{entry.family}</span>
                  <span className="text-[#c7b06a]/70">{entry.relation}</span>
                </div>
                <div className="mt-0.5 text-[11px] font-semibold text-white/75">{entry.target}</div>
                {entry.gloss && <div className="mt-0.5 line-clamp-2 text-[11px] leading-4 text-zenith-soft">{entry.gloss}</div>}
              </div>
            ))}
          </div>
        )}
        {relatedSurfaceEntries.length > 0 && (
          <div className="space-y-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">related surfaces</div>
            {relatedSurfaceEntries.slice(0, 8).map(([key, value]) => (
              <div
                key={key}
                className="grid grid-cols-[120px_minmax(0,1fr)] gap-2 rounded border border-zenith-edge bg-white/[0.025] px-2 py-1 font-mono text-[10px]"
              >
                <span className="text-white/35">{key.replace(/_/g, ' ')}</span>
                <span className="truncate text-zenith-soft">{String(value)}</span>
              </div>
            ))}
          </div>
        )}
        {siblingRows.length > 0 && (
          <div className="space-y-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">neighboring loaded objects</div>
            {siblingRows.map((sibling, index) => (
              <div key={`${rowPrimaryId(sibling, `sibling-${index}`)}:${index}`} className="rounded border border-zenith-edge bg-white/[0.025] px-2 py-1">
                <div className="truncate text-[11px] font-semibold text-zenith-soft">{rowLabel(sibling, rowPrimaryId(sibling, 'neighbor'))}</div>
                {rowClaim(sibling) && <div className="mt-0.5 line-clamp-1 text-[10px] leading-4 text-zenith-muted">{rowClaim(sibling)}</div>}
              </div>
            ))}
          </div>
        )}
        {Array.isArray(projectionRow.related) && projectionRow.related.length > 0 && (
          <div className="space-y-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">related</div>
            {projectionRow.related.slice(0, 12).map((entry, index) => (
              <div
                key={index}
                className="truncate rounded border border-zenith-edge bg-white/[0.025] px-2 py-1 font-mono text-[11px] text-zenith-soft"
              >
                {typeof entry === 'string' ? entry : JSON.stringify(entry)}
              </div>
            ))}
          </div>
        )}
        {relationRows.length === 0 && linkedRelations.length === 0 && siblingRows.length === 0 && relatedSurfaceEntries.length === 0 && !(Array.isArray(projectionRow.related) && projectionRow.related.length > 0) && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2 text-[11px] leading-4 text-zenith-soft">
            No explicit relation rows loaded for this card. Derived context still shows parent kind, axis, cluster, status, and source-backed refs.
          </div>
        )}
      </div>
    ),
    Evidence: (
      <div className="space-y-3" data-zenith-root-human-projection="evidence">
        <SourcePreviewCards refs={refs} previewState={sourcePreviewState} currentRoute={currentRoute} />
        {evidenceRefs.length > 0 && (
          <div className="space-y-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">source evidence rows</div>
            {evidenceRefs.map((entry, index) => (
              <div key={`${asString(entry.ref, 'evidence')}:${index}`} className="rounded border border-emerald-300/15 bg-emerald-300/[0.035] px-2 py-1.5">
                <div className="flex items-center justify-between gap-2 font-mono text-[10px]">
                  <span className="uppercase tracking-[0.12em] text-emerald-100/55">{asString(entry.role, 'evidence')}</span>
                  <span className="text-white/35">{asString(entry.ref, `row ${index + 1}`)}</span>
                </div>
                {asString(entry.gloss) && <div className="mt-0.5 text-[11px] leading-4 text-zenith-soft">{asString(entry.gloss)}</div>}
              </div>
            ))}
          </div>
        )}
        {tests.length > 0 && (
          <div className="space-y-1">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">validation / failure evidence</div>
            {tests.map((test, index) => (
              <div key={`${test.label}:${index}`} className="rounded border border-zenith-edge bg-white/[0.025] px-2 py-1.5">
                <div className="text-[11px] font-semibold text-white/72">{test.label}</div>
                <div className="mt-0.5 text-[10px] leading-4 text-white/50">{test.body}</div>
              </div>
            ))}
          </div>
        )}
        {refs.length === 0 && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2 text-[11px] leading-4 text-zenith-soft">
            No direct source refs loaded for this card. Evidence is unavailable in this packet; Raw shows the exact source-owned row fields.
          </div>
        )}
      </div>
    ),
    'Agent route': (
      <div className="space-y-3" data-zenith-root-human-projection="agent-actions">
        <div className="grid gap-2">
          <a
            href={routeWithInspectorTab(currentRoute, 'Evidence')}
            className="inline-flex items-center justify-center gap-1.5 rounded-[3px] border border-emerald-300/20 bg-emerald-300/[0.06] px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-emerald-100/80 hover:border-emerald-200/35"
          >
            <Eye size={11} /> Show evidence
          </a>
          {refs[0] && (
            <a
              href={inspectorHrefForSource(refs[0], currentRoute)}
              className="inline-flex items-center justify-center gap-1.5 rounded-[3px] border border-cyan-300/20 bg-cyan-300/[0.06] px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-cyan-100/80 hover:border-cyan-200/35"
            >
              <ExternalLink size={11} /> Open source preview
            </a>
          )}
          <a
            href={routeWithInspectorTab(currentRoute, 'Raw')}
            className="inline-flex items-center justify-center gap-1.5 rounded-[3px] border border-zenith-edge bg-white/[0.03] px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-white/62 hover:border-white/25"
          >
            <FileJson2 size={11} /> Inspect raw packet
          </a>
        </div>
        {drilldownCommand && commandRoute('card packet', drilldownCommand)}
        {evidenceCommands.map((command, index) => commandRoute(index === 0 ? 'evidence packet' : `evidence packet ${index + 1}`, command))}
      </div>
    ),
    Raw: (
      <details className="rounded-[3px] border border-zenith-edge bg-white/[0.025]">
        <summary className="cursor-pointer px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
          row json
        </summary>
        <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap p-2 font-mono text-[10px] leading-4 text-zenith-soft">
          {JSON.stringify(projectionRow, null, 2)}
        </pre>
      </details>
    ),
  };
}

function buildCoverageInspector(row: RootCoverageRow): InspectorContent {
  return {
    Summary: (
      <div className="space-y-3">
        <div className="space-y-1">
          <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/38">{row.id}</div>
          <h2 className="text-base font-semibold text-white">{row.label}</h2>
          {row.role && <p className="text-xs leading-5 text-zenith-soft">{row.role}</p>}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">coverage</div>
            <div className="mt-1"><StatusPill status={row.coverage_status} /></div>
          </div>
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">owner surface</div>
            <div className="mt-1"><StatusPill status={row.owner_surface_status} /></div>
          </div>
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">drilldown</div>
            <div className="mt-1"><StatusPill status={row.legal_drilldown_status} /></div>
          </div>
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">docs alias</div>
            <div className="mt-1"><StatusPill status={row.docs_route_alias_status} /></div>
          </div>
        </div>
      </div>
    ),
    Relations: (
      <div className="space-y-3">
        {row.parent_id && (
          <div className="rounded-[3px] border border-zenith-edge bg-white/[0.03] p-2 font-mono text-[11px] text-zenith-soft">
            parent <span className="text-white/80">{row.parent_id}</span>
          </div>
        )}
      </div>
    ),
    Evidence: (
      <div className="space-y-3">
        {(row.owner_surfaces ?? []).length > 0 && (
          sourceRefList(row.owner_surfaces ?? [])
        )}
      </div>
    ),
    'Agent route': (
      <div className="space-y-3">
        {row.drilldown_command && commandRoute('legal drilldown', row.drilldown_command)}
      </div>
    ),
    Raw: (
      <details className="rounded-[3px] border border-zenith-edge bg-white/[0.025]">
        <summary className="cursor-pointer px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
          coverage row json
        </summary>
        <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap p-2 font-mono text-[10px] leading-4 text-zenith-soft">
          {JSON.stringify(row, null, 2)}
        </pre>
      </details>
    ),
  };
}

interface GraphHandoff {
  id: string;
  label: string;
  question: string;
  baseRoute: string;
}

const GRAPH_HANDOFFS: readonly GraphHandoff[] = [
  {
    id: 'runtime_graph',
    label: 'Runtime lens',
    question: 'execution lanes and authority chain',
    baseRoute: '/station/graph',
  },
  {
    id: 'topology_explorer',
    label: 'Topology lens',
    question: 'source clusters and system surroundings',
    baseRoute: '/station/topology',
  },
  {
    id: 'routing_hologram',
    label: 'Routes lens',
    question: 'station routes and capture graph',
    baseRoute: '/station/routes',
  },
  {
    id: 'code_blast_radius',
    label: 'Code lens',
    question: 'code focus graph and verification commands',
    baseRoute: '/station/codemap',
  },
];

function viabilityShortLabel(v: RouteGateViability): string {
  const access =
    v.routeAccessState === 'safe'
      ? 'route safe'
      : v.routeAccessState === 'gated'
        ? 'route gated'
        : v.routeAccessState === 'blocked'
          ? 'route blocked'
          : 'route status unknown';
  if (v.routeAccessState === 'unknown') {
    return access + ' · may be empty';
  }
  const content =
    v.contentState === 'available'
      ? 'content available'
      : v.contentState === 'requires_runtime'
        ? 'requires active runtime'
        : v.contentState === 'empty'
          ? 'content empty'
          : v.contentState === 'stale'
            ? 'content stale'
            : v.routeAccessState === 'gated'
              ? 'gate explains why'
              : 'content unknown';
  return `${access} · ${content}`;
}

function viabilityToneClass(v: RouteGateViability): string {
  switch (v.routeAccessState) {
    case 'safe':
      return v.contentState === 'available' ? 'text-emerald-200/85' : 'text-amber-200/80';
    case 'gated':
      return 'text-amber-200/80';
    case 'blocked':
      return 'text-rose-200/80';
    case 'unknown':
    default:
      return 'text-zenith-muted';
  }
}

interface HandoffWithViability {
  handoff: GraphHandoff;
  viability: RouteGateViability;
}

function GraphHandoffPanel({ currentRoute }: { currentRoute: string }) {
  const { worldModel } = useZenith();
  const navigationGraph: NavigationGraphProjection | null =
    (worldModel?.navigation_graph as NavigationGraphProjection | undefined) ?? null;
  const items: HandoffWithViability[] = GRAPH_HANDOFFS.map((handoff) => ({
    handoff,
    viability: navigationGraph
      ? deriveRouteGateViabilityFromGraph(navigationGraph, handoff.baseRoute)
      : deriveRouteGateViability(handoff.baseRoute),
  }));
  const sourceFreshness = items[0]?.viability.sourceFreshness ?? 'unknown';
  return (
    <div
      className="border-t border-zenith-edge bg-black/35 px-3 py-2"
      data-zenith-graph-handoff-panel="visible"
      data-zenith-graph-handoff-viability="ready"
    >
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-white/35">
        graph lenses
      </div>
      <p className="mt-0.5 text-[10px] leading-4 text-zenith-muted">
        full-view lenses for the current graph question
      </p>
      <div className="mt-2 space-y-1">
        {items.map(({ handoff, viability }) => {
          const accessibleName =
            viability.routeAccessState === 'safe' && viability.contentState === 'available'
              ? `${handoff.label} — ${handoff.question}`
              : `${handoff.label} — ${handoff.question}. ${viability.reason}`;
          const blocked = viability.routeAccessState === 'blocked';
          const sharedAttrs: Record<string, string | undefined> = {
            'data-zenith-graph-handoff': handoff.id,
            'data-zenith-graph-handoff-base': handoff.baseRoute,
            'data-zenith-graph-handoff-route-access': viability.routeAccessState,
            'data-zenith-graph-handoff-content': viability.contentState,
            'data-zenith-graph-handoff-source-freshness': viability.sourceFreshness,
            'aria-label': accessibleName,
            title: viability.reason,
          };
          const inner = (
            <>
              <span className="flex min-w-0 flex-col">
                <span className="truncate font-mono text-[11px] text-white/85">{handoff.label}</span>
                <span className="truncate text-[10px] text-zenith-muted">{handoff.question}</span>
                <span
                  className={clsx(
                    'truncate font-mono text-[9px] uppercase tracking-[0.14em]',
                    viabilityToneClass(viability),
                  )}
                  data-zenith-graph-handoff-viability-line={handoff.id}
                >
                  {viabilityShortLabel(viability)}
                </span>
              </span>
              <ExternalLink size={11} className="shrink-0 text-white/35" aria-hidden="true" />
            </>
          );
          if (blocked) {
            return (
              <div
                key={handoff.id}
                {...sharedAttrs}
                role="button"
                aria-disabled="true"
                tabIndex={0}
                className="flex cursor-not-allowed items-center justify-between gap-2 rounded border border-rose-300/15 bg-rose-300/[0.04] px-2 py-1.5 text-[11px] text-zenith-soft"
              >
                {inner}
              </div>
            );
          }
          const borderClass =
            viability.routeAccessState === 'gated'
              ? 'border-amber-300/25 hover:border-amber-200/45'
              : viability.routeAccessState === 'unknown'
                ? 'border-zenith-edge hover:border-white/25'
                : 'border-zenith-edge hover:border-cyan-300/30 hover:text-cyan-100';
          return (
            <Link
              key={handoff.id}
              to={withReturnToQuery(handoff.baseRoute, currentRoute)}
              {...sharedAttrs}
              className={clsx(
                'flex items-center justify-between gap-2 rounded border bg-white/[0.025] px-2 py-1.5 text-[11px] text-white/72',
                borderClass,
              )}
            >
              {inner}
            </Link>
          );
        })}
        <div
          className={clsx(
            'mt-1 truncate font-mono text-[9px] uppercase tracking-[0.14em]',
            sourceFreshness === 'current'
              ? 'text-emerald-200/55'
              : sourceFreshness === 'stale'
                ? 'text-amber-200/65'
                : 'text-white/30',
          )}
          data-zenith-graph-handoff-viability-source="visible"
          data-zenith-graph-handoff-viability-source-freshness={sourceFreshness}
        >
          source · {items[0]?.viability.sourceLabel ?? 'unknown'}
        </div>
      </div>
    </div>
  );
}

function Inspector({
  selection,
  packet,
  viewModel,
  drilldownPacket,
  cardPacket,
  cardLoading,
  cardError,
  selectedPrimitive,
  selectedAxis,
  parentCluster,
  requestedTab,
  onTabChange,
  currentRoute,
  onOpenKindLens,
  onSelectGraphNativeKind,
  familyPrinciples,
  familyNodeCard,
  familyNodeCardStatus,
  familyNodeCardError,
  presentationMode = 'standard',
}: InspectorProps) {
  const tabs = useMemo(() => {
    const declared = packet?.constitutional_atlas?.inspector_tabs;
    const fromPacket = Array.isArray(declared)
      ? declared
          .filter((tab): tab is string => typeof tab === 'string')
          .filter((tab): tab is InspectorTab => INSPECTOR_TAB_ORDER.includes(tab as InspectorTab))
      : [];
    const ordered = fromPacket.length > 0 ? (fromPacket as InspectorTab[]) : INSPECTOR_TAB_ORDER;
    return Array.from(new Set(ordered)) as InspectorTab[];
  }, [packet]);

  const tab: InspectorTab =
    requestedTab && tabs.includes(requestedTab) ? requestedTab : tabs[0] ?? 'Summary';

  const sourcePreviewRefs = useMemo(() => {
    const refs = new Set<string>();
    if (selection.kind === 'card' && selection.cardRow) {
      const cardRow = (cardPacket?.rows ?? []).filter(isRecord)[0] ?? null;
      for (const ref of rowSourceRefs(cardRow ? { ...selection.cardRow, ...cardRow } : selection.cardRow)) refs.add(ref);
      for (const ref of asStringArray(cardPacket?.source_refs)) refs.add(ref);
    } else if (selection.kind === 'primitive' && selection.primitive) {
      for (const ref of asStringArray(selection.primitive.governing_standard_refs)) refs.add(ref);
      for (const ref of asStringArray(selection.primitive.projection_refs)) refs.add(ref);
      for (const ref of asStringArray(packet?.source_refs)) refs.add(ref);
    } else {
      for (const ref of asStringArray(packet?.source_refs)) refs.add(ref);
      for (const ref of viewModel.sourceRefs) refs.add(ref);
    }
    return Array.from(refs).slice(0, 5);
  }, [selection, cardPacket, packet, viewModel.sourceRefs]);

  const sourcePreviewPaths = useMemo(
    () => Array.from(new Set(sourcePreviewRefs.map(sourceRefPath))).filter((path) => path.length > 0).slice(0, 5),
    [sourcePreviewRefs],
  );
  const sourcePreviewKey = sourcePreviewPaths.join('|');

  const [sourcePreviewResource, setSourcePreviewResource] = useState<SourcePreviewResource>({
    key: '',
    files: EMPTY_SOURCE_PREVIEW_FILES,
    error: null,
  });

  const sourcePreviewState = useMemo<SourcePreviewState>(() => {
    if (!sourcePreviewKey) {
      return { status: 'idle', files: EMPTY_SOURCE_PREVIEW_FILES, error: null };
    }
    if (sourcePreviewResource.key !== sourcePreviewKey) {
      return { status: 'loading', files: EMPTY_SOURCE_PREVIEW_FILES, error: null };
    }
    return {
      status: sourcePreviewResource.error ? 'error' : 'ready',
      files: sourcePreviewResource.files,
      error: sourcePreviewResource.error,
    };
  }, [sourcePreviewKey, sourcePreviewResource]);

  useEffect(() => {
    if (!sourcePreviewKey) return;
    let cancelled = false;
    const requestKey = sourcePreviewKey;
    api.codex
      .batchRead(sourcePreviewPaths)
      .then((response) => {
        if (cancelled) return;
        const map = new Map<string, CodexFileDetail>();
        for (const file of response.files ?? []) {
          map.set(file.path, file);
        }
        setSourcePreviewResource({ key: requestKey, files: map, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        setSourcePreviewResource({
          key: requestKey,
          files: EMPTY_SOURCE_PREVIEW_FILES,
          error: err instanceof Error ? err.message : 'Failed to load source previews.',
        });
      });
    return () => {
      cancelled = true;
    };
  }, [sourcePreviewKey, sourcePreviewPaths]);

  const content: InspectorContent = useMemo(() => {
    if (selection.kind === 'family_node' && selection.familyNode) {
      return buildFamilyNodeInspector(selection.familyNode, {
        onOpenKindLens,
        currentRoute,
        principles: familyPrinciples,
        card: familyNodeCard ?? null,
        cardStatus: familyNodeCardStatus ?? 'idle',
        cardError: familyNodeCardError ?? null,
        sourcePreviewState,
      });
    }
    if (selection.kind === 'paper_module' && selection.paperModule) {
      return buildPaperModuleInspector(selection.paperModule, {
        onOpenKindLens,
        currentRoute,
        card: familyNodeCard ?? null,
        cardStatus: familyNodeCardStatus ?? 'idle',
        cardError: familyNodeCardError ?? null,
      });
    }
    if (selection.kind === 'standard' && selection.standard) {
      return buildStandardInspector(selection.standard, {
        onOpenKindLens,
        onSelectGovernedKind: onSelectGraphNativeKind,
        currentRoute,
        card: familyNodeCard ?? null,
        cardStatus: familyNodeCardStatus ?? 'idle',
        cardError: familyNodeCardError ?? null,
      });
    }
    if (selection.kind === 'card' && selection.cardRow) {
      return buildCardInspector(selection.cardRow, cardPacket, {
        primitive: selectedPrimitive,
        axis: selectedAxis,
        drilldownPacket,
        parentCluster,
        sourcePreviewState,
        currentRoute,
      });
    }
    if (selection.kind === 'primitive' && selection.primitive) {
      return buildPrimitiveInspector(
        selection.primitive,
        selection.axis ?? null,
        drilldownPacket,
        packet,
        asStringArray(packet?.source_refs),
        viewModel,
      );
    }
    if (selection.kind === 'coverage' && selection.coverageRow) {
      return buildCoverageInspector(selection.coverageRow);
    }
    return buildOverviewInspector(packet, viewModel);
  }, [selection, packet, viewModel, drilldownPacket, cardPacket, selectedPrimitive, selectedAxis, parentCluster, sourcePreviewState, currentRoute, onOpenKindLens, onSelectGraphNativeKind, familyPrinciples, familyNodeCard, familyNodeCardStatus, familyNodeCardError]);

  return (
    <aside
      className={clsx(
        'flex min-h-0 flex-col border-l border-zenith-edge bg-zenith-panel-muted',
        presentationMode === 'deep_dossier' && 'bg-[#050b0d]',
      )}
      data-zenith-view-region="inspector"
      data-zenith-view-region-role="right_inspector"
      data-zenith-view-region-mode="persistent"
      data-zenith-root-inspector-presentation={presentationMode}
      data-zenith-root-human-projection-source-preview={sourcePreviewState.status}
    >
      <SectionHeader icon={FileJson2} label="Inspector" hint={selection.kind} />
      <InspectorTabs active={tab} onSelect={onTabChange} tabs={tabs} />
      {cardLoading && (
        <div className="border-b border-zenith-edge bg-white/[0.025] px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-muted">
          loading card packet
        </div>
      )}
      {cardError && (
        <div className="border-b border-amber-400/20 bg-amber-400/10 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-amber-100">
          card unavailable: {cardError}
        </div>
      )}
      <InspectorBody tab={tab} content={content} presentationMode={presentationMode} />
      {tab === 'Summary' && presentationMode !== 'deep_dossier' && <GraphHandoffPanel currentRoute={currentRoute} />}
    </aside>
  );
}

export default function RootNavigator() {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const currentRoute = `${location.pathname}${location.search}`;
  const { worldModel } = useZenith();
  const [packet, setPacket] = useState<RootNavigatorHandoffPacket | null>(null);
  const [coverage, setCoverage] = useState<RootCoverageState | null>(null);
  const [loading, setLoading] = useState(true);
  const [packetError, setPacketError] = useState<string | null>(null);
  const [drilldownPacket, setDrilldownPacket] = useState<NavigationSurfacePacket | null>(null);
  const [drilldownLoading, setDrilldownLoading] = useState(false);
  const [drilldownError, setDrilldownError] = useState<string | null>(null);
  const [cardPacket, setCardPacket] = useState<NavigationSurfacePacket | null>(null);
  const [cardLoading, setCardLoading] = useState(false);
  const [cardError, setCardError] = useState<string | null>(null);
  const [fallbackRow, setFallbackRow] = useState<UnknownRow | null>(null);
  const [, setFallbackUnavailable] = useState(false);
  const [memberPreviewPacket, setMemberPreviewPacket] = useState<NavigationSurfacePacket | null>(null);
  const [memberPreviewLoading, setMemberPreviewLoading] = useState(false);
  const [memberPreviewError, setMemberPreviewError] = useState<string | null>(null);
  // v1.15: page-level axiom load so the selection useMemo can populate
  // selection.familyNode.axiom (and axiomsPointingHere for principle selections),
  // letting the Inspector Relations tab render readable related-principle chips.
  // ConstitutionalMap keeps its own state for its in-graph rendering; this duplicates
  // the fetch but keeps the page-level selection contract honest until the larger
  // axiom-flow refactor lands.
  const [pageAxioms, setPageAxioms] = useState<FamilyAxiomCandidate[]>([]);
  // v1.16: on-demand option-surface card for the selected family node. The Inspector
  // currently shows only what worldModel + the family-zoom parser carry (title/statement
  // /bands); the rich substrate (edge_summary, top_tests, anti_principle, teleology_glance,
  // nearest_standard, top_failure_modes, source_refs) lives in the card-band packet but
  // was never fetched at this surface. Fetching it here lets the Inspector render the
  // full substrate projection instead of leaving black space.
  const [familyNodeCard, setFamilyNodeCard] = useState<NavigationSurfacePacket | null>(null);
  const [familyNodeCardStatus, setFamilyNodeCardStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>(
    'idle',
  );
  const [familyNodeCardError, setFamilyNodeCardError] = useState<string | null>(null);
  const [localInspectorTab, setLocalInspectorTab] = useState<InspectorTab | undefined>(undefined);

  const selectedKind = searchParams.get('kind');
  const selectedRowId = searchParams.get('row');
  const tabParam = searchParams.get('tab');
  const showAll = searchParams.get('show') === 'all';
  const gatesExpanded = searchParams.get('gates') === 'expanded';
  const query = searchParams.get('q') ?? '';
  const substrateGraphParam = searchParams.get('graph');
  const substrateGraphFocus = searchParams.get('focus');
  const substrateFamilyNode = searchParams.get('node');
  // vNext-CM: ?cluster=<cluster_id> extends the route grammar so the operator
  // can expand a single cluster inside a focused container without exploding
  // every sibling cluster. When a node is selected and its cluster is known,
  // expansion can also be inferred from the node — but explicit ?cluster=
  // remains the canonical expand-state surface.
  const substrateGraphCluster = searchParams.get('cluster');
  const substrateGraphMode: 'atlas' | 'family' =
    substrateGraphParam === 'substrate' && substrateGraphFocus
      ? 'family'
      : 'atlas';
  const atlasFocusParam = searchParams.get('atlas_focus');
  const atlasKindsParam = searchParams.get('atlas_kinds');
  const atlasKindFieldParam = searchParams.get('atlas_kind_field');
  const atlasFocusId = atlasFocusParam && atlasFocusParam.length > 0 ? atlasFocusParam : null;
  const atlasKindField =
    atlasKindFieldParam && atlasKindFieldParam.length > 0 ? atlasKindFieldParam : null;
  const legacyCanvasEnabled = searchParams.get('legacy') === '1';
  const systemAtlasLensEnabled =
    !legacyCanvasEnabled &&
    Boolean(
      atlasFocusId ||
        atlasKindField ||
        (atlasKindsParam && atlasKindsParam.trim().length > 0),
    );
  const atlasActiveKinds = useMemo<string[]>(() => {
    if (atlasKindsParam && atlasKindsParam.trim().length > 0) {
      return atlasKindsParam
        .split(',')
        .map((value) => value.trim())
        .filter((value) => value.length > 0);
    }
    if (atlasKindField) return [atlasKindField];
    if (selectedKind) {
      const mapped = ATLAS_KIND_FROM_PRIMITIVE[selectedKind];
      if (mapped) return [mapped];
    }
    return [...DOCTRINE_KINDS];
  }, [atlasKindField, atlasKindsParam, selectedKind]);
  const requestedTabFromUrl: InspectorTab | null =
    tabParam && (INSPECTOR_TAB_ORDER as readonly string[]).includes(tabParam)
      ? (tabParam as InspectorTab)
      : null;
  const requestedTab: InspectorTab | null = localInspectorTab ?? requestedTabFromUrl;

  useEffect(() => {
    setLocalInspectorTab(undefined);
  }, [selectedKind, selectedRowId, substrateGraphFocus, substrateFamilyNode, substrateGraphCluster, atlasFocusId, atlasKindField]);

  const updateParam = useCallback(
    (key: string, value: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (value && value.length > 0) next.set(key, value);
          else next.delete(key);
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [handoff, coverageState] = await Promise.all([
        api.system.rootNavigatorHandoff(),
        api.system.rootCoverageState().catch(() => null),
      ]);
      setPacket(handoff);
      setCoverage(coverageState);
      setPacketError(null);
    } catch (err) {
      setPacketError(err instanceof Error ? err.message : 'Failed to load RootNavigator packet.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const axes = useMemo(() => packet?.constitutional_atlas?.primitive_axes ?? [], [packet]);
  const rowsByKind = useMemo(() => {
    const map = new Map<string, RootNavigatorPrimitiveRow>();
    for (const row of packet?.semantic_primitive_matrix?.rows ?? []) {
      if (row?.candidate_primitive) map.set(row.candidate_primitive, row);
    }
    return map;
  }, [packet]);
  // vNext-GA: widen the graph-capable kind set. Any kind with substrate rows
  // (row_count > 0) is graph-native by default — the generic option-surface
  // adapter will render its clusters/objects. The previous 4-kind
  // GRAPH_NATIVE_KINDS whitelist forced concepts/mechanisms/axiom_candidates/
  // etc. through the legacy ?kind= focus-path workbench despite having rich
  // substrate. The four bespoke-adapter kinds stay in the set as a guaranteed
  // minimum; everything else with rows joins them.
  const graphCapableKinds = useMemo<ReadonlySet<string>>(() => {
    const set = new Set<string>(GRAPH_NATIVE_KINDS);
    for (const [kind, row] of rowsByKind.entries()) {
      const rowCount = typeof row?.row_count === 'number' ? row.row_count : 0;
      if (rowCount > 0) set.add(kind);
    }
    return set;
  }, [rowsByKind]);
  const axisByKind = useMemo(() => {
    const map = new Map<string, RootNavigatorPrimitiveAxis>();
    for (const axis of axes) {
      for (const kind of axis.candidate_kinds ?? []) map.set(kind, axis);
    }
    return map;
  }, [axes]);

  const selectedPrimitive = selectedKind && rowsByKind.get(selectedKind) ? rowsByKind.get(selectedKind) ?? null : null;
  const focusedGraphPrimitive =
    substrateGraphMode === 'family' && substrateGraphFocus
      ? rowsByKind.get(substrateGraphFocus) ?? null
      : null;
  const inspectorPrimitive = selectedPrimitive ?? (!substrateFamilyNode ? focusedGraphPrimitive : null);
  const viewModel = useMemo(
    () =>
      buildRootDoctrineCrystalViewModel({
        packet,
        coverage,
        selectedPrimitive: inspectorPrimitive,
        packetError,
        loading,
      }),
    [packet, coverage, inspectorPrimitive, packetError, loading],
  );
  const coverageRowsById = useMemo(() => {
    const map = new Map<string, RootCoverageRow>();
    for (const row of coverage?.branches ?? []) map.set(row.id, row);
    for (const row of coverage?.doctrine_layers ?? []) map.set(row.id, row);
    return map;
  }, [coverage]);

  useEffect(() => {
    if (!selectedPrimitive) {
      setDrilldownPacket(null);
      setDrilldownError(null);
      setDrilldownLoading(false);
      return;
    }
    let cancelled = false;
    setDrilldownLoading(true);
    setDrilldownError(null);
    setCardPacket(null);
    setCardError(null);
    setCardLoading(false);
    api.system
      .navigationSurface({ kind: selectedPrimitive.candidate_primitive, band: packetBandForRow(selectedPrimitive) })
      .then((response) => {
        if (cancelled) return;
        setDrilldownPacket(response);
      })
      .catch((err) => {
        if (cancelled) return;
        setDrilldownPacket(null);
        setDrilldownError(err instanceof Error ? err.message : 'Failed to load navigation surface.');
      })
      .finally(() => {
        if (!cancelled) setDrilldownLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPrimitive]);

  const drilldownRowsList = useMemo(
    () => (drilldownPacket?.rows ?? []).filter(isRecord),
    [drilldownPacket],
  );
  const drilldownMatch = useMemo(() => {
    if (!selectedRowId || drilldownRowsList.length === 0) return null;
    for (const row of drilldownRowsList) {
      if (rowPrimaryId(row, '') === selectedRowId) return row;
    }
    return null;
  }, [selectedRowId, drilldownRowsList]);

  useEffect(() => {
    if (!selectedPrimitive || !selectedRowId) {
      setFallbackRow(null);
      setFallbackUnavailable(false);
      return;
    }
    if (drilldownLoading) return;
    if (drilldownMatch) {
      setFallbackRow(null);
      setFallbackUnavailable(false);
      return;
    }
    let cancelled = false;
    setFallbackUnavailable(false);
    api.system
      .navigationSurface({
        kind: selectedPrimitive.candidate_primitive,
        band: 'card',
        id: selectedRowId,
      })
      .then((response) => {
        if (cancelled) return;
        const row = (response.rows ?? []).filter(isRecord)[0] ?? null;
        if (row) {
          setFallbackRow(row);
          setFallbackUnavailable(false);
        } else {
          setFallbackRow(null);
          setFallbackUnavailable(true);
        }
      })
      .catch(() => {
        if (cancelled) return;
        setFallbackRow(null);
        setFallbackUnavailable(true);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPrimitive, selectedRowId, drilldownLoading, drilldownMatch]);

  const selectedDrilldownRow = useMemo(
    () => drilldownMatch ?? fallbackRow,
    [drilldownMatch, fallbackRow],
  );

  useEffect(() => {
    if (!selectedPrimitive || !selectedDrilldownRow) {
      setMemberPreviewPacket(null);
      setMemberPreviewError(null);
      setMemberPreviewLoading(false);
      return;
    }
    if (classifySelectedObject(selectedDrilldownRow) !== 'cluster_row') {
      setMemberPreviewPacket(null);
      setMemberPreviewError(null);
      setMemberPreviewLoading(false);
      return;
    }
    const topIds = asStringArray((selectedDrilldownRow as UnknownRow).top_ids).slice(0, 8);
    if (topIds.length === 0) {
      setMemberPreviewPacket(null);
      setMemberPreviewError(null);
      setMemberPreviewLoading(false);
      return;
    }
    let cancelled = false;
    setMemberPreviewLoading(true);
    setMemberPreviewError(null);
    api.system
      .navigationSurface({
        kind: selectedPrimitive.candidate_primitive,
        band: 'card',
        id: topIds.join(','),
      })
      .then((response) => {
        if (cancelled) return;
        setMemberPreviewPacket(response);
      })
      .catch((err) => {
        if (cancelled) return;
        setMemberPreviewPacket(null);
        setMemberPreviewError(err instanceof Error ? err.message : 'Failed to load member preview.');
      })
      .finally(() => {
        if (!cancelled) setMemberPreviewLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPrimitive, selectedDrilldownRow]);

  const memberPreviewRowsById = useMemo(() => {
    const map = new Map<string, UnknownRow>();
    for (const row of (memberPreviewPacket?.rows ?? []).filter(isRecord)) {
      for (const key of rowIdentityKeys(row)) {
        if (!map.has(key)) map.set(key, row);
      }
    }
    return map;
  }, [memberPreviewPacket]);

  useEffect(() => {
    if (!selectedDrilldownRow || !selectedPrimitive) {
      setCardPacket(null);
      setCardError(null);
      setCardLoading(false);
      return;
    }
    const id = rowPrimaryId(selectedDrilldownRow, '');
    if (!id) return;
    let cancelled = false;
    setCardLoading(true);
    setCardError(null);
    api.system
      .navigationSurface({ kind: selectedPrimitive.candidate_primitive, band: 'card', id })
      .then((response) => {
        if (cancelled) return;
        setCardPacket(response);
      })
      .catch((err) => {
        if (cancelled) return;
        setCardPacket(null);
        setCardError(err instanceof Error ? err.message : 'Failed to load card.');
      })
      .finally(() => {
        if (!cancelled) setCardLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedDrilldownRow, selectedPrimitive]);

  // v1.16: fetch the option-surface card for the selected family node so the Inspector
  // can render the rich substrate projection (edge_summary, top_tests, anti_principle,
  // teleology_glance, nearest_standard, top_failure_modes, source_refs) the worldModel
  // and family-zoom parser do not carry. The substrate already has these fields; the
  // earlier "Inspector black space" was a projection-wiring gap, not a substrate gap.
  useEffect(() => {
    if (
      substrateGraphMode !== 'family' ||
      !substrateFamilyNode ||
      (substrateGraphFocus !== 'axiom_candidates' &&
        substrateGraphFocus !== 'principles' &&
        substrateGraphFocus !== 'paper_modules' &&
        substrateGraphFocus !== 'standards')
    ) {
      setFamilyNodeCard(null);
      setFamilyNodeCardStatus('idle');
      setFamilyNodeCardError(null);
      return;
    }
    let cancelled = false;
    setFamilyNodeCardStatus('loading');
    setFamilyNodeCardError(null);
    api.system
      .navigationSurface({ kind: substrateGraphFocus, band: 'card', id: substrateFamilyNode })
      .then((packet) => {
        if (cancelled) return;
        setFamilyNodeCard(packet);
        setFamilyNodeCardStatus('ready');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setFamilyNodeCard(null);
        setFamilyNodeCardStatus('error');
        setFamilyNodeCardError(err instanceof Error ? err.message : 'card fetch failed');
      });
    return () => {
      cancelled = true;
    };
  }, [substrateGraphMode, substrateGraphFocus, substrateFamilyNode]);

  // v1.15: load axiom candidates at page level so selection.familyNode can carry the
  // axiom record + axiomsPointingHere set. Runs whenever the substrate route asks for an
  // axiom_candidates or principles family view; both kinds need the axiom ledger.
  // paper_modules does not need the axiom ledger — it has its own cluster fetch in
  // ConstitutionalMap plus the v1.16 card-band fetch at page level.
  useEffect(() => {
    if (substrateGraphFocus !== 'axiom_candidates' && substrateGraphFocus !== 'principles') {
      setPageAxioms([]);
      return;
    }
    let cancelled = false;
    const path = deriveFamilyAxiomPath(worldModel?.principles_family?.path);
    api.codex
      .getFile(path)
      .then((file) => {
        if (cancelled) return;
        setPageAxioms(parseFamilyAxiomCandidates(file.content ?? ''));
      })
      .catch(() => {
        if (cancelled) return;
        setPageAxioms([]);
      });
    return () => {
      cancelled = true;
    };
  }, [substrateGraphFocus, worldModel?.principles_family?.path]);

  const selection: RootSelectionState = useMemo(() => {
    // v1.20: paper_modules selection routes to its own kind so the Inspector branches
    // into buildPaperModuleInspector (tldr_excerpt / top_dependencies / governing_refs)
    // rather than the family_node axiom/principle path.
    if (
      substrateGraphMode === 'family' &&
      substrateGraphFocus === 'paper_modules' &&
      substrateFamilyNode
    ) {
      return {
        kind: 'paper_module',
        paperModule: {
          nodeId: substrateFamilyNode,
          readableLabel: paperModuleReadableLabel(substrateFamilyNode),
        },
      };
    }
    // v1.21: standards selection routes to its own kind so the Inspector branches
    // into buildStandardInspector (governed_kind / required_rules / contract status)
    // rather than the family_node axiom/principle path.
    if (
      substrateGraphMode === 'family' &&
      substrateGraphFocus === 'standards' &&
      substrateFamilyNode
    ) {
      return {
        kind: 'standard',
        standard: {
          nodeId: substrateFamilyNode,
          readableLabel: standardReadableLabel(substrateFamilyNode),
        },
      };
    }
    if (
      substrateGraphMode === 'family' &&
      substrateGraphFocus &&
      substrateFamilyNode &&
      (substrateGraphFocus === 'axiom_candidates' || substrateGraphFocus === 'principles')
    ) {
      const family = substrateGraphFocus as 'axiom_candidates' | 'principles';
      const nodeKind: 'axiom_candidate' | 'principle' = substrateFamilyNode.startsWith(
        'axiom_candidate_',
      )
        ? 'axiom_candidate'
        : 'principle';
      const principle =
        nodeKind === 'principle'
          ? worldModel?.principles_family?.principles?.find((p) => p.id === substrateFamilyNode) ?? null
          : null;
      const axiom =
        nodeKind === 'axiom_candidate'
          ? pageAxioms.find((a) => a.id === substrateFamilyNode) ?? null
          : null;
      // For a selected principle, axiomsPointingHere lets the Inspector Relations tab
      // render which axioms compress this principle. v1.15 populates this at the page
      // level so the Inspector branch is no longer stuck on the v1.14 empty fallback.
      const axiomsPointingHere =
        nodeKind === 'principle'
          ? pageAxioms.filter((a) => a.relatedPrinciples.includes(substrateFamilyNode))
          : [];
      return {
        kind: 'family_node',
        familyNode: {
          family,
          nodeKind,
          nodeId: substrateFamilyNode,
          axiom,
          principle,
          group: null,
          axiomsPointingHere,
        },
      };
    }
    if (selectedDrilldownRow) {
      return { kind: 'card', cardRow: selectedDrilldownRow };
    }
    if (selectedKind?.startsWith('coverage:')) {
      const coverageId = selectedKind.slice('coverage:'.length);
      const row = coverageRowsById.get(coverageId);
      if (row) return { kind: 'coverage', coverageRow: row };
    }
    if (inspectorPrimitive && !substrateFamilyNode) {
      return {
        kind: 'primitive',
        primitive: inspectorPrimitive,
        axis: axisByKind.get(inspectorPrimitive.candidate_primitive) ?? null,
      };
    }
    if (selectedPrimitive) {
      return { kind: 'primitive', primitive: selectedPrimitive, axis: axisByKind.get(selectedPrimitive.candidate_primitive) ?? null };
    }
    if (packet) return { kind: 'overview' };
    return { kind: 'empty' };
  }, [
    selectedDrilldownRow,
    selectedKind,
    selectedPrimitive,
    inspectorPrimitive,
    axisByKind,
    packet,
    coverageRowsById,
    substrateGraphMode,
    substrateGraphFocus,
    substrateFamilyNode,
    worldModel,
    pageAxioms,
  ]);

  const handleSelectKind = useCallback(
    (kind: string) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set('kind', kind);
          next.delete('row');
          next.delete('tab');
          next.delete('graph');
          next.delete('focus');
          next.delete('node');
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const handleAtlasFocusEntity = useCallback(
    (id: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (id && id.length > 0) {
            next.set('atlas_focus', id);
            next.delete('graph');
            next.delete('focus');
            next.delete('node');
            next.delete('cluster');
            next.delete('kind');
            next.delete('row');
            next.delete('tab');
            next.delete('legacy');
          } else {
            next.delete('atlas_focus');
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const handleAtlasActiveKindsChange = useCallback(
    (kinds: string[]) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          const sorted = [...kinds].sort();
          const defaultSorted = [...DOCTRINE_KINDS].sort();
          const isDefault =
            sorted.length === defaultSorted.length &&
            sorted.every((value, index) => value === defaultSorted[index]);
          if (kinds.length === 0 || isDefault) next.delete('atlas_kinds');
          else next.set('atlas_kinds', kinds.join(','));
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const handleAtlasKindFieldChange = useCallback(
    (kind: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (kind && kind.length > 0) {
            next.set('atlas_kind_field', kind);
            next.set('atlas_kinds', kind);
            next.delete('atlas_focus');
            next.delete('graph');
            next.delete('focus');
            next.delete('node');
            next.delete('cluster');
            next.delete('kind');
            next.delete('row');
            next.delete('tab');
            next.delete('legacy');
          } else {
            next.delete('atlas_kind_field');
            next.delete('atlas_kinds');
            next.delete('atlas_focus');
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const handleSelectAtlasContainer = useCallback(
    (kind: string) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set('graph', 'substrate');
          next.set('focus', kind);
          next.delete('node');
          next.delete('cluster');
          next.delete('kind');
          next.delete('row');
          next.delete('tab');
          next.delete('atlas_focus');
          next.delete('atlas_kinds');
          next.delete('atlas_kind_field');
          next.delete('legacy');

          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const handleOpenKindLens = useCallback(
    (kind: string) => {
      if (!kind || kind.length === 0) return;
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          const atlasKind = ATLAS_KIND_FROM_PRIMITIVE[kind] ?? kind;
          next.delete('graph');
          next.delete('focus');
          next.delete('node');
          next.delete('cluster');
          next.delete('kind');
          next.delete('row');
          next.delete('tab');
          next.delete('legacy');
          next.delete('atlas_focus');
          next.set('atlas_kind_field', atlasKind);
          next.set('atlas_kinds', atlasKind);
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const handleSelectFamilyNode = useCallback(
    (nodeId: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (nodeId && nodeId.length > 0) next.set('node', nodeId);
          else next.delete('node');
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  // vNext-GA: ?cluster=<id> setter. Cluster nodes in the visible canvas call
  // this through onClusterToggle. Clearing (null) collapses back to clusters-
  // only view. Setting a new cluster keeps the focused kind + clears any
  // sibling-bound ?node= so the URL stays consistent with single-cluster
  // expansion.
  const handleSelectGraphCluster = useCallback(
    (clusterId: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (clusterId && clusterId.length > 0) {
            next.set('cluster', clusterId);
          } else {
            next.delete('cluster');
            next.delete('node');
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  // vNext-IX: typed object/neighbor selection. Sets ?graph=substrate&focus=
  // <kind>&cluster=<clusterId?>&node=<rawId>. The rawId is the option-
  // surface row id (e.g. 'queryable_doctrine_surface', 'std_paper_module',
  // 'frontend_substrate_projection_theory') — NEVER the internal graph id
  // ('concepts:object:...', 'standard:...', 'paper_module:...'). When a
  // neighbor click changes the focused kind, this also pivots the canvas.
  const handleSelectGraphObject = useCallback(
    (kind: string, rawId: string | null, clusterId?: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set('graph', 'substrate');
          next.set('focus', kind);
          if (clusterId && clusterId.length > 0) {
            next.set('cluster', clusterId);
          } else {
            next.delete('cluster');
          }
          if (rawId && rawId.length > 0) {
            next.set('node', rawId);
          } else {
            next.delete('node');
          }
          next.delete('kind');
          next.delete('row');
          next.delete('tab');
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const handleBackToAtlas = useCallback(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete('graph');
        next.delete('focus');
        next.delete('node');
        next.delete('kind');
        next.delete('row');
        next.delete('tab');
        return next;
      },
      { replace: true },
    );
  }, [setSearchParams]);

  const handleSelectRow = useCallback(
    (rowId: string | null) => {
      updateParam('row', rowId && rowId.length > 0 ? rowId : null);
    },
    [updateParam],
  );

  const handleQueryChange = useCallback(
    (q: string) => {
      updateParam('q', q.length > 0 ? q : null);
    },
    [updateParam],
  );

  const handleToggleShowAll = useCallback(() => {
    updateParam('show', showAll ? null : 'all');
  }, [showAll, updateParam]);

  const handleTabChange = useCallback(
    (tab: InspectorTab) => {
      setLocalInspectorTab(tab);
    },
    [],
  );

  const handleToggleGatesExpanded = useCallback(() => {
    updateParam('gates', gatesExpanded ? null : 'expanded');
  }, [gatesExpanded, updateParam]);

  const drilldownReadyState: 'none' | 'loading' | 'ready' | 'error' | 'unavailable' = !selectedPrimitive
    ? 'none'
    : drilldownLoading
      ? 'loading'
      : drilldownError
        ? 'error'
        : drilldownPacket
          ? 'ready'
          : 'unavailable';

  const cardReadyState: 'none' | 'loading' | 'ready' | 'error' | 'unavailable' = !selectedDrilldownRow
    ? 'none'
    : cardLoading
      ? 'loading'
      : cardError
        ? 'error'
        : cardPacket
          ? 'ready'
          : 'ready';

  const selectedSpecies = selectedDrilldownRow ? classifySelectedObject(selectedDrilldownRow) : 'none';
  const selectedAxisForPrimitive = selectedPrimitive
    ? axisByKind.get(selectedPrimitive.candidate_primitive) ?? null
    : null;
  const inspectorAxisForPrimitive = inspectorPrimitive
    ? axisByKind.get(inspectorPrimitive.candidate_primitive) ?? null
    : null;
  const inspectorParentCluster: ParentClusterInfo | null =
    selectedDrilldownRow && selectedSpecies === 'leaf_row'
      ? findParentCluster(selectedDrilldownRow, drilldownPacket, selectedPrimitive)
      : null;

  const memberPreviewReadyState: 'none' | 'loading' | 'ready' | 'partial' | 'error' | 'unavailable' =
    !selectedDrilldownRow || selectedSpecies !== 'cluster_row'
      ? 'none'
      : memberPreviewLoading
        ? 'loading'
        : memberPreviewError
          ? 'error'
          : memberPreviewRowsById.size > 0
            ? 'ready'
            : memberPreviewPacket
              ? 'partial'
              : 'unavailable';

  const graphHandoffsVisible = !requestedTab || requestedTab === 'Summary';
  const graphHandoffsReadyState: 'ready' | 'hidden' = graphHandoffsVisible ? 'ready' : 'hidden';
  const rootAtlasDeepDetailMode =
    !systemAtlasLensEnabled &&
    Boolean(
      substrateFamilyNode ||
        (selectedDrilldownRow && selectedSpecies !== 'cluster_row'),
    );
  const rootNavigatorGridMode = systemAtlasLensEnabled
    ? 'system_atlas_lens'
    : rootAtlasDeepDetailMode
      ? 'graph_dominant_detail'
      : selectedPrimitive
        ? 'focus_path_triptych'
        : 'graph_plus_inspector';
  const rootNavigatorGridTemplateColumns = systemAtlasLensEnabled
    ? 'minmax(0,1fr)'
    : rootAtlasDeepDetailMode
      ? 'minmax(640px,0.66fr) minmax(340px,0.34fr)'
      : selectedPrimitive
        ? 'minmax(0,0.52fr) minmax(240px,0.18fr) minmax(380px,0.30fr)'
        : 'minmax(0,0.62fr) minmax(360px,0.38fr)';

  return (
    <div
      data-zenith-root-navigator-surface={packet && !loading ? 'ready' : 'loading'}
      data-zenith-view-id="rootNavigator"
      data-zenith-view-family="graph_surface"
      data-zenith-view-mode={rootAtlasDeepDetailMode ? 'inspect_first' : 'graph_first'}
      data-zenith-view-dominant-artifact="root_unified_graph"
      data-zenith-view-quality-receipt="metric_quality_receipt_v1"
      data-zenith-view-metric-vector="root_navigator_graph_constitution_v1"
      data-zenith-view-calibration-status="screenshot_pending"
      data-zenith-root-navigator-drilldown={drilldownReadyState}
      data-zenith-root-navigator-card={cardReadyState}
      data-zenith-root-navigator-member-preview={memberPreviewReadyState}
      data-zenith-root-navigator-selected-kind={selectedKind ?? substrateGraphFocus ?? 'overview'}
      data-zenith-root-navigator-selected-species={selectedSpecies}
      data-zenith-root-depth-mode={rootAtlasDeepDetailMode ? 'deep_detail' : 'graph_first'}
      data-zenith-root-navigator-graph-handoffs={graphHandoffsReadyState}
      data-zenith-root-navigator-universal-graph={packet && !loading ? 'ready' : 'loading'}
      data-zenith-root-navigator-primary-surface={
        systemAtlasLensEnabled ? 'system_atlas_lens' : 'universal_graph'
      }
      data-zenith-root-human-projection={packet && !loading ? 'ready' : 'loading'}
      className="flex h-full min-h-0 flex-col bg-[#05070b] text-white"
    >
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-zenith-edge px-4 py-[var(--zenith-space-2-5)]">
        <div className="flex min-w-0 items-baseline gap-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-cyan-200/70">root navigator</span>
          <span className="truncate text-xs text-zenith-soft">
            {asString(packet?.view?.purpose ?? packet?.constitutional_atlas?.purpose_one_line, 'constitutional atlas of the cognitive substrate')}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void refresh()}
            className="flex items-center gap-2 rounded-md border border-zenith-edge bg-white/[0.04] px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-zenith-soft hover:border-cyan-300/35 hover:text-cyan-100"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            refresh
          </button>
        </div>
      </header>

      <FreshnessBanner packet={packet} />
      <RootStatusBar packet={packet} coverage={coverage} viewModel={viewModel} />

      {packetError && (
        <div className="border-b border-red-400/30 bg-red-400/10 px-4 py-2 text-xs text-red-100">
          {packetError}
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <AxisRail
          axes={axes}
          rowsByKind={rowsByKind}
          viewModel={viewModel}
          selectedKind={selectedKind ?? substrateGraphFocus}
          onSelectKind={handleSelectKind}
          onSelectGraphNativeKind={handleSelectAtlasContainer}
          graphNativeKinds={graphCapableKinds}
          substrateGraphFocus={substrateGraphFocus}
          query={query}
          onQueryChange={handleQueryChange}
          showAll={showAll}
          onToggleShowAll={handleToggleShowAll}
          coverage={coverage}
        />

        <main
          className="grid min-w-0 flex-1"
          data-zenith-root-main-grid="ready"
          data-zenith-root-main-grid-mode={rootNavigatorGridMode}
          style={{
            gridTemplateColumns: rootNavigatorGridTemplateColumns,
          }}
        >
          <section
            className="min-h-0 border-r border-zenith-edge"
            data-zenith-view-region="dominant_artifact"
            data-zenith-view-region-role="root_graph_canvas"
            data-zenith-view-region-mode="persistent"
          >
            {!systemAtlasLensEnabled ? (
              <ConstitutionalMap
                packet={packet}
                axes={axes}
                viewModel={viewModel}
                onSelectKind={handleSelectKind}
                onSelectInspectorTab={handleTabChange}
                selectedPrimitive={selectedPrimitive}
                selectedAxis={selectedAxisForPrimitive}
                drilldownRowCount={drilldownRowsList.length}
                selectedRow={selectedDrilldownRow}
                drilldownPacket={drilldownPacket}
                drilldownLoading={drilldownLoading}
                drilldownError={drilldownError}
                cardPacket={cardPacket}
                cardLoading={cardLoading}
                cardError={cardError}
                onSelectRow={handleSelectRow}
                memberPreviewRowsById={memberPreviewRowsById}
                substrateGraphMode={substrateGraphMode}
                substrateGraphFocus={substrateGraphFocus}
                substrateFamilyNode={substrateFamilyNode}
                substrateGraphCluster={substrateGraphCluster}
                onSelectAtlasContainer={handleSelectAtlasContainer}
                onOpenKindLens={handleOpenKindLens}
                onSelectFamilyNode={handleSelectFamilyNode}
                onSelectGraphCluster={handleSelectGraphCluster}
                onSelectGraphObject={handleSelectGraphObject}
                onBackToAtlas={handleBackToAtlas}
                familyNodeCard={familyNodeCard}
                familyNodeCardStatus={familyNodeCardStatus}
                depthPresentation={rootAtlasDeepDetailMode ? 'deep_detail' : 'default'}
              />
            ) : (
              <Suspense
                fallback={
                  <div
                    className="flex h-full min-h-[420px] items-center justify-center bg-black/20 font-mono text-[10px] uppercase tracking-[0.18em] text-white/42"
                    data-zenith-system-atlas-lens-loading="true"
                  >
                    Loading atlas lens
                  </div>
                }
              >
                <SystemAtlasGraph
                  focusId={atlasFocusId}
                  kindField={atlasKindField}
                  onKindFieldChange={handleAtlasKindFieldChange}
                  activeKinds={atlasActiveKinds}
                  onActiveKindsChange={handleAtlasActiveKindsChange}
                  onFocusEntity={handleAtlasFocusEntity}
                />
              </Suspense>
            )}
          </section>
          {!systemAtlasLensEnabled && selectedPrimitive && !rootAtlasDeepDetailMode && (
            <section
              className="min-h-0 border-r border-zenith-edge bg-black/30"
              data-zenith-view-region="inspector"
              data-zenith-view-region-role="drilldown_pane"
              data-zenith-view-region-mode="persistent"
            >
              <DrilldownPane
                primitive={selectedPrimitive}
                packet={drilldownPacket}
                loading={drilldownLoading}
                error={drilldownError}
                selectedRowId={selectedRowId}
                onSelectRow={handleSelectRow}
              />
            </section>
          )}
          {!systemAtlasLensEnabled && (
            <Inspector
              selection={selection}
              packet={packet}
              viewModel={viewModel}
              drilldownPacket={drilldownPacket}
              cardPacket={cardPacket}
              cardLoading={cardLoading}
              cardError={cardError}
              selectedPrimitive={inspectorPrimitive}
              selectedAxis={inspectorAxisForPrimitive}
              parentCluster={inspectorParentCluster}
              requestedTab={requestedTab}
              onTabChange={handleTabChange}
              currentRoute={currentRoute}
              onOpenKindLens={handleOpenKindLens}
              onSelectGraphNativeKind={handleSelectAtlasContainer}
              familyPrinciples={worldModel?.principles_family?.principles ?? []}
              familyNodeCard={familyNodeCard}
              familyNodeCardStatus={familyNodeCardStatus}
              familyNodeCardError={familyNodeCardError}
              presentationMode={rootAtlasDeepDetailMode ? 'deep_dossier' : 'standard'}
            />
          )}
        </main>
      </div>
      <GateRail gates={viewModel.gates} expanded={gatesExpanded} onToggleExpanded={handleToggleGatesExpanded} />
    </div>
  );
}
